"""API v1 de planificación para la consola web (spec 026; contracts/planning-api.md).

Reglas:

- En la web, la consola es de libre elección (spec 027, R3): ninguna ruta exige autorización.
  ``/access`` se conserva por compatibilidad y siempre responde ``authorized: true``. Cada llamada
  conserva el seudónimo de quien la hizo (``planner_user``).
- Las cifras salen de ``planning.optimize``, la misma función de la herramienta y del CLI (R6).
- Guardar es de dos pasos con vencimiento (R9): el plan se recalcula en el servidor y solo se
  escribe tras ``yes``, con ``actions.save_proposal`` (mismo archivo que la acción del agente).
- Cada llamada deja una línea en ``<state>/planning/console.jsonl`` sin IP ni texto sin redactar.
"""

from __future__ import annotations

import json
import re
import secrets
import time
from collections import OrderedDict
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from pydantic import ValidationError

from .agent.actions import save_proposal
from .agent.config import load_agent_config, resolve_state_dir
from .agent.planning import (
    DECISION_PHRASE,
    SYNTHETIC_LABEL,
    PlanningError,
    PlanResult,
    Scenario,
    compare,
    fmt,
    load_plant,
    optimize,
    snapshot,
)
from .agent.privacy import redact_pii
from .api_errors import ApiV1Error
from .api_models import (
    PendingProposalModel,
    PlanningAccess,
    ProposalDecision,
    ProposalOutcome,
    ProposalRequest,
)

router = APIRouter(prefix="/api/v1/planning", tags=["planificación v1"])

USER_PATTERN = re.compile(r"^[A-Za-z0-9-]{1,64}$")
PROPOSAL_TTL = timedelta(minutes=5)
MAX_PENDING = 100
ACCESS_TEXT = "Planificación abierta en la web. Los datos de planta son sintéticos."
REGENERATE = "uv run python scripts/generate_planning_data.py --seed 2026 --version v1"


# --------------------------------------------------------------------------- identidad y acceso


def web_user(request: Request) -> str:
    """Seudónimo anónimo de la sesión web (el mismo ``user_id`` del chat)."""
    supplied = request.headers.get("X-User-Id", "").strip()
    return supplied if USER_PATTERN.match(supplied) else "anon"


def planner_user(request: Request) -> str:
    """Seudónimo para el registro de la consola. En la web no hay barrera (spec 027)."""
    return web_user(request)


# --------------------------------------------------------------------------- registro


def _console_log() -> Any:
    state_dir = resolve_state_dir(load_agent_config().state_env_var)
    path = state_dir / "planning" / "console.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


def _log_event(
    endpoint: str,
    user: str,
    *,
    scenario: dict[str, Any] | None,
    plan_id: str | None,
    status: str,
    duration_ms: int,
) -> None:
    event = {
        "ts": datetime.now(UTC).isoformat(),
        "endpoint": endpoint,
        "user": user,
        "scenario": scenario or {},
        "plan_id": plan_id,
        "status": status,
        "duration_ms": duration_ms,
        "synthetic": True,
    }
    try:
        with _console_log().open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(event, ensure_ascii=False) + "\n")
    except OSError:  # el registro nunca tumba la consola
        pass


@contextmanager
def _timed() -> Iterator[Callable[[], int]]:
    start = time.perf_counter()
    yield lambda: int((time.perf_counter() - start) * 1000)


# --------------------------------------------------------------------------- cálculo


def _scenario(raw: dict[str, Any]) -> Scenario:
    try:
        return Scenario.model_validate(raw)
    except ValidationError as exc:
        raise ApiV1Error(
            "invalid_scenario", scenario_error_message(exc.errors()), status_code=422
        ) from exc


def scenario_error_message(errors: list[Any]) -> str:
    """Texto en español con el campo y el rango válido (sin detalles internos)."""
    parts = []
    for error in errors[:3]:
        location = [str(p) for p in error.get("loc", ()) if p not in ("body", "scenario")]
        field = ".".join(location) or "escenario"
        ctx = error.get("ctx") or {}
        if error.get("type") == "extra_forbidden":
            parts.append(f"«{field}» no es un control del escenario")
        elif "ge" in ctx or "le" in ctx:
            low, high = ctx.get("ge", "—"), ctx.get("le", "—")
            parts.append(f"«{field}» debe estar entre {low} y {high}")
        else:
            parts.append(f"«{field}» no es válido")
    return "El escenario no es válido: " + "; ".join(parts) + ". Corrige el valor y recalcula."


def _plant():
    try:
        return load_plant()
    except PlanningError as exc:
        raise ApiV1Error(
            "plant_data_missing",
            f"No están los datos sintéticos de planificación. Genéralos con `{REGENERATE}`.",
            status_code=503,
            action="regenerar datos",
        ) from exc


def _optimize(scenario: Scenario) -> PlanResult:
    data = _plant()
    try:
        return optimize(scenario, data)
    except PlanningError as exc:
        raise ApiV1Error(
            "planning_failed",
            "El optimizador no pudo calcular este escenario. Ajusta los controles y recalcula.",
            status_code=500,
            retryable=True,
            action="reintentar",
        ) from exc


def _plan_payload(plan: PlanResult) -> dict[str, Any]:
    return {**plan.to_dict(card=True), "label": SYNTHETIC_LABEL, "decision_phrase": DECISION_PHRASE}


def plan_summary(plan: PlanResult) -> str:
    total = plan.mix["x_s"] + plan.mix["x_e"]
    sugar = 100 * plan.mix["x_s"] / total if total else 0.0
    text = (
        f"Azúcar {fmt(sugar)} % y etanol {fmt(100 - sugar)} % de la caña; "
        f"{fmt(plan.products['sugar'])} t de azúcar, {fmt(plan.products['ethanol'])} L de etanol "
        f"y {fmt(plan.products['power'])} MWh exportados."
    )
    if plan.status != "optimal":
        text += " No cumple todos los compromisos."
    return text


# --------------------------------------------------------------------------- propuestas


@dataclass
class PendingProposal:
    confirmation_id: str
    plan_id: str
    plan: dict[str, Any]
    scenario: dict[str, Any]
    user: str
    note: str | None
    created_at: datetime
    expires_at: datetime


class PendingProposals:
    """Propuestas por confirmar, en memoria del proceso (5 min, máximo 100)."""

    def __init__(self) -> None:
        self._items: OrderedDict[str, PendingProposal] = OrderedDict()
        self.clock: Callable[[], datetime] = lambda: datetime.now(UTC)

    def __len__(self) -> int:
        return len(self._items)

    def clear(self) -> None:
        self._items.clear()

    def add(self, item: PendingProposal) -> None:
        self._items[item.confirmation_id] = item
        while len(self._items) > MAX_PENDING:
            self._items.popitem(last=False)

    def take(self, confirmation_id: str) -> PendingProposal:
        item = self._items.pop(confirmation_id, None)
        if item is None:
            raise ApiV1Error(
                "proposal_not_found",
                "Esa propuesta no existe o ya se decidió. Calcula el plan de nuevo para guardarlo.",
                status_code=404,
            )
        if self.clock() > item.expires_at:
            raise ApiV1Error(
                "proposal_expired",
                "La propuesta venció; vuelve a calcular el plan.",
                status_code=410,
                action="recalcular",
            )
        return item


PENDING = PendingProposals()


# --------------------------------------------------------------------------- endpoints


@router.get("/access", response_model=PlanningAccess)
def access() -> PlanningAccess:
    return PlanningAccess(authorized=True, reason=ACCESS_TEXT)


@router.get("/state")
def state(user: str = Depends(planner_user)) -> dict[str, Any]:
    with _timed() as elapsed:
        view = snapshot(_plant())
    _log_event("state", user, scenario=None, plan_id=None, status="ok", duration_ms=elapsed())
    return view


@router.post("/plan")
def plan(raw: dict[str, Any], user: str = Depends(planner_user)) -> dict[str, Any]:
    scenario = _scenario(raw)
    with _timed() as elapsed:
        result = _optimize(scenario)
    _log_event(
        "plan",
        user,
        scenario=scenario.model_dump(exclude_none=True),
        plan_id=result.plan_id,
        status=result.status,
        duration_ms=elapsed(),
    )
    return _plan_payload(result)


@router.post("/compare")
def compare_plans(raw: dict[str, Any], user: str = Depends(planner_user)) -> dict[str, Any]:
    scenario = _scenario(raw)
    with _timed() as elapsed:
        base = _optimize(Scenario())
        result = _optimize(scenario)
        payload = compare(base, result, _plant())
    _log_event(
        "compare",
        user,
        scenario=scenario.model_dump(exclude_none=True),
        plan_id=result.plan_id,
        status=result.status,
        duration_ms=elapsed(),
    )
    return {**payload, "label": SYNTHETIC_LABEL, "decision_phrase": DECISION_PHRASE}


@router.post("/proposals", status_code=202, response_model=PendingProposalModel)
def create_proposal(
    body: ProposalRequest, user: str = Depends(planner_user)
) -> PendingProposalModel:
    scenario = _scenario(body.scenario)
    with _timed() as elapsed:
        result = _optimize(scenario)
    now = PENDING.clock()
    item = PendingProposal(
        confirmation_id=secrets.token_urlsafe(16),
        plan_id=result.plan_id,
        plan=result.to_dict(card=False),
        scenario=scenario.model_dump(exclude_none=True),
        user=user,
        note=redact_pii(body.note.strip()) if body.note and body.note.strip() else None,
        created_at=now,
        expires_at=now + PROPOSAL_TTL,
    )
    PENDING.add(item)
    _log_event(
        "proposals",
        user,
        scenario=item.scenario,
        plan_id=item.plan_id,
        status="pending",
        duration_ms=elapsed(),
    )
    return PendingProposalModel(
        confirmation_id=item.confirmation_id,
        plan_id=item.plan_id,
        summary=plan_summary(result),
        expires_at=item.expires_at.isoformat(),
        question="¿Guardar esta propuesta para revisión del equipo de planta?",
    )


@router.post("/proposals/{confirmation_id}", response_model=ProposalOutcome)
def decide_proposal(
    confirmation_id: str, body: ProposalDecision, user: str = Depends(planner_user)
) -> ProposalOutcome:
    with _timed() as elapsed:
        item = PENDING.take(confirmation_id)
        if body.decision == "yes":
            state_dir = resolve_state_dir(load_agent_config().state_env_var)
            save_proposal(
                {"plan_id": item.plan_id, "note": item.note},
                user_id=item.user,
                last_plan=item.plan,
                state_dir=state_dir,
            )
            outcome = ProposalOutcome(
                status="saved",
                plan_id=item.plan_id,
                message=f"Propuesta guardada. {DECISION_PHRASE}",
            )
        else:
            outcome = ProposalOutcome(
                status="discarded",
                plan_id=item.plan_id,
                message="Propuesta descartada. No se guardó nada.",
            )
    _log_event(
        "proposals/decision",
        user,
        scenario=item.scenario,
        plan_id=item.plan_id,
        status=outcome.status,
        duration_ms=elapsed(),
    )
    return outcome


def error_handler(_request: Request, exc: ApiV1Error) -> JSONResponse:
    from .api_errors import error_response

    return error_response(
        exc.code,
        exc.message,
        retryable=exc.retryable,
        action=exc.action,
        status_code=exc.status_code,
    )
