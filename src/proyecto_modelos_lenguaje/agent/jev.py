"""Gatekeeper System One (Jev de TypeSafe) para el enrutador (spec 022).

Jev no redacta: responde preguntas tipadas (Choice, Score, Noul) con probabilidades. El enrutador
lo consulta **una vez por turno** entre las reglas y el clasificador LLM (``research.md`` R3, R4):

- ``route`` (Choice): ruta del mensaje; si su probabilidad alcanza ``route_threshold`` decide Jev.
- ``scope`` (Choice): motivo cuando la ruta es ``out_of_scope``.
- ``annoyance`` (Score): nivel de molestia del visitante (0–3).
- ``crisis`` (Noul): probabilidad de riesgo para la vida o la integridad de alguien.

Reglas de seguridad (R6, R7, R8):

- ``assess`` nunca lanza excepciones: todo fallo es ``GateOutcome(status="failed")`` y el turno
  sigue con el clasificador actual.
- El texto se enmascara con ``privacy.redact_pii`` antes de salir del servidor.
- La crisis es la **unión** de la detección determinista y la de Jev; Jev nunca la anula.
- La clave ``TYPESAFE_API_KEY`` se lee del entorno y no se guarda en ningún campo serializable.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from ..config import PROJECT_ROOT
from .config import JevConfig
from .models import Route, ScopeReason
from .privacy import redact_pii

logger = logging.getLogger(__name__)

API_KEY_ENV = "TYPESAFE_API_KEY"
SYSTEMONE_PATH = "/v1/systemone"
MODELS_PATH = "/v1/models"
# Precio reportado por terceros (0,042 USD por millón de tokens de entrada; la salida es gratis).
# Solo se usa si la respuesta no trae ``usage.cost``.
INPUT_PRICE_PER_TOKEN = 0.042 / 1_000_000

ROUTES: tuple[Route, ...] = (
    "direct",
    "documental",
    "structured",
    "mixed",
    "out_of_scope",
    "clarify",
)
SCOPE_REASONS: tuple[ScopeReason, ...] = (
    "off_topic",
    "abuse",
    "harmful",
    "third_party",
    "prompt_extraction",
    "advice",
)
ANNOYANCE_LEVELS = ("calmado", "inconforme", "molesto", "muy molesto")
PROMPT_SECTIONS = ("route", "scope", "annoyance", "crisis")

GateStatus = Literal["ok", "failed", "skipped"]
GateReason = Literal[
    "timeout",
    "network",
    "http_401",
    "http_402",
    "http_422",
    "http_429",
    "http_5xx",
    "http_other",
    "invalid_response",
    "refusal",
    "disabled",
    "no_key",
    "smalltalk",
    "write_intent",
]


class JevError(RuntimeError):
    """Error interno del gatekeeper; nunca sale de ``assess``."""

    def __init__(self, reason: GateReason, detail: str = "") -> None:
        super().__init__(detail or reason)
        self.reason: GateReason = reason


# ---------------------------------------------------------------- modelos (data-model.md)


class GateDecision(BaseModel):
    """Ruta elegida por Jev con la probabilidad de cada opción."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route: Route
    probabilities: dict[str, float]
    confidence: float = Field(ge=0.0, le=1.0)
    alternative: Route | None = None
    scope_reason: ScopeReason | None = None


class GateSignals(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    crisis_probability: float | None = Field(default=None, ge=0.0, le=1.0)
    annoyance: float | None = Field(default=None, ge=0.0, le=3.0)

    @property
    def annoyance_level(self) -> int | None:
        return None if self.annoyance is None else round(self.annoyance)


class GateOutcome(BaseModel):
    """Resultado de una consulta; lo único que ve el resto del sistema."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    status: GateStatus
    reason: GateReason | None = None
    decision: GateDecision | None = None
    signals: GateSignals | None = None
    latency_ms: int = Field(default=0, ge=0)
    cost: float | None = Field(default=None, ge=0.0)
    model: str | None = None

    @classmethod
    def skipped(cls, reason: GateReason) -> GateOutcome:
        return cls(status="skipped", reason=reason)

    def accepted(self, threshold: float) -> bool:
        """``True`` si la ruta de Jev decide el turno (umbral inclusivo, research R5)."""
        return (
            self.status == "ok"
            and self.decision is not None
            and self.decision.confidence >= threshold
        )

    def trace(self, threshold: float) -> dict[str, Any]:
        """Bloque ``jev`` del registro del turno (FR-021): sin texto del visitante ni clave."""
        decision = self.decision
        return {
            "status": self.status,
            "reason": self.reason,
            "route": decision.route if decision else None,
            "confidence": round(decision.confidence, 4) if decision else None,
            "alternative": decision.alternative if decision else None,
            "scope_reason": decision.scope_reason if decision else None,
            "accepted": self.accepted(threshold),
            "crisis_probability": self.signals.crisis_probability if self.signals else None,
            "annoyance": self.signals.annoyance if self.signals else None,
            "latency_ms": self.latency_ms,
            "cost": self.cost,
            "model": self.model,
        }


class JevGate(Protocol):
    config: JevConfig

    def assess(self, message: str, history: Sequence[str] = ()) -> GateOutcome: ...


# ---------------------------------------------------------------- prompts/jev.md (research R11)

_SECTION = re.compile(r"^##\s+(\w+)\s*$", re.MULTILINE)
_OPTION = re.compile(r"^-\s+`([^`]+)`:\s*(.+)$")
_VERSION = re.compile(r"<!--\s*prompt_version:\s*([\w.]+)\s*-->")


@dataclass(frozen=True, slots=True)
class GateQuestion:
    name: str
    instructions: str
    options: tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class GatePrompts:
    version: str
    sha256: str
    questions: dict[str, GateQuestion] = field(default_factory=dict)


class JevPromptError(ValueError):
    """``prompts/jev.md`` falta o no tiene el formato esperado."""


def parse_gate_prompts(text: str) -> GatePrompts:
    version = _VERSION.search(text)
    if version is None:
        raise JevPromptError("prompts/jev.md no declara prompt_version.")
    parts = _SECTION.split(text)
    questions: dict[str, GateQuestion] = {}
    for name, body in zip(parts[1::2], parts[2::2], strict=True):
        instructions: list[str] = []
        options: list[tuple[str, str]] = []
        reading = False
        for raw in body.strip().splitlines():
            line = raw.strip()
            option = _OPTION.match(line)
            if option:
                options.append((option.group(1), option.group(2).strip()))
                reading = False
            elif line.lower().startswith("instrucciones:"):
                instructions.append(line.split(":", 1)[1].strip())
                reading = True
            elif reading and line:
                instructions.append(line)
            else:
                reading = False
        if not instructions or not options:
            raise JevPromptError(f"La sección «{name}» de prompts/jev.md está incompleta.")
        questions[name] = GateQuestion(name, " ".join(instructions), tuple(options))
    missing = [name for name in PROMPT_SECTIONS if name not in questions]
    if missing:
        raise JevPromptError(f"prompts/jev.md no tiene las secciones: {', '.join(missing)}.")
    expected = {
        "route": list(ROUTES),
        "scope": list(SCOPE_REASONS),
        "annoyance": list(ANNOYANCE_LEVELS),
        "crisis": ["true", "false"],
    }
    for name, keys in expected.items():
        found = [key for key, _ in questions[name].options]
        if sorted(found) != sorted(keys) or (name == "annoyance" and found != keys):
            raise JevPromptError(f"La sección «{name}» debe tener exactamente: {', '.join(keys)}.")
    return GatePrompts(
        version=version.group(1),
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        questions=questions,
    )


@lru_cache(maxsize=4)
def load_gate_prompts(project_root: Path | None = None) -> GatePrompts:
    path = Path(project_root or PROJECT_ROOT) / "prompts" / "jev.md"
    if not path.is_file():
        raise JevPromptError("No existe prompts/jev.md.")
    return parse_gate_prompts(path.read_text(encoding="utf-8"))


def build_questions(prompts: GatePrompts, signals: Sequence[str]) -> dict[str, Any]:
    """Preguntas del contrato §1, solo las de ``[jev].signals``."""
    questions: dict[str, Any] = {}
    for name in signals:
        question = prompts.questions[name]
        if name == "annoyance":
            questions[name] = {
                "type": "score",
                "instructions": question.instructions,
                "criteria": [f"{key}: {text}" for key, text in question.options],
            }
        elif name == "crisis":
            criteria = dict(question.options)
            questions[name] = {
                "type": "noul",
                "instructions": question.instructions,
                "criteria": {"true": criteria["true"], "false": criteria["false"]},
            }
        else:
            questions[name] = {
                "type": "choice",
                "instructions": question.instructions,
                "criteria": dict(question.options),
            }
    return questions


# ---------------------------------------------------------------- estado enviado (research R7)


def build_state(message: str, history: Sequence[str], max_chars: int) -> dict[str, Any]:
    """Mensaje e historial enmascarados; se recorta primero el historial (más antiguo primero)."""
    clean_message = redact_pii(message or "")[:max_chars]
    clean_history = [redact_pii(item) for item in history if item]
    while clean_history and len(clean_message) + sum(map(len, clean_history)) > max_chars:
        clean_history.pop(0)
    return {"mensaje": clean_message, "historial": clean_history}


# ---------------------------------------------------------------- respuesta (contrato §2)


def _probabilities(answer: Mapping[str, Any], keys: Sequence[str], name: str) -> dict[str, float]:
    raw = answer.get("probabilities")
    if not isinstance(raw, Mapping):
        raise JevError("invalid_response", f"{name} sin probabilities")
    probabilities: dict[str, float] = {}
    for key, value in raw.items():
        if key not in keys:
            raise JevError("invalid_response", f"{name}: opción desconocida")
        if isinstance(value, bool) or not isinstance(value, (int, float)) or value < 0:
            raise JevError("invalid_response", f"{name}: probabilidad inválida")
        probabilities[str(key)] = float(value)
    total = sum(probabilities.values())
    if abs(total - 1.0) > 0.01:
        raise JevError("invalid_response", f"{name}: probabilidades que no suman 1")
    return {key: probabilities.get(key, 0.0) for key in keys}


def _answer(answers: Mapping[str, Any], name: str, kind: str) -> Mapping[str, Any] | None:
    answer = answers.get(name)
    if answer is None:
        return None
    if not isinstance(answer, Mapping):
        raise JevError("invalid_response", f"{name} no es un objeto")
    if answer.get("type") == "refusal":
        raise JevError("refusal", name)
    if answer.get("type") != kind:
        raise JevError("invalid_response", f"{name} no es {kind}")
    return answer


def parse_response(payload: Any, config: JevConfig) -> tuple[GateDecision, GateSignals, str | None]:
    """Valida la respuesta y la convierte en decisión y señales (lanza ``JevError``)."""
    if not isinstance(payload, Mapping) or not isinstance(payload.get("answers"), Mapping):
        raise JevError("invalid_response", "respuesta sin answers")
    answers = payload["answers"]
    route_answer = _answer(answers, "route", "choice")
    if route_answer is None:
        raise JevError("invalid_response", "respuesta sin route")
    probabilities = _probabilities(route_answer, ROUTES, "route")
    ranked = sorted(probabilities.items(), key=lambda item: item[1], reverse=True)
    route = route_answer.get("choice") or ranked[0][0]
    if route not in ROUTES:
        raise JevError("invalid_response", "route: opción desconocida")
    alternative = next((key for key, value in ranked if key != route and value > 0), None)
    scope_reason: str | None = None
    if route == "out_of_scope" and config.uses("scope"):
        scope_answer = _answer(answers, "scope", "choice")
        if scope_answer is not None:
            choice = scope_answer.get("choice")
            if choice not in SCOPE_REASONS:
                scope_probs = _probabilities(scope_answer, SCOPE_REASONS, "scope")
                choice = max(scope_probs, key=scope_probs.__getitem__)
            scope_reason = str(choice)
    crisis: float | None = None
    if config.uses("crisis"):
        crisis_answer = _answer(answers, "crisis", "noul")
        if crisis_answer is not None:
            value = crisis_answer.get("noul")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 1
            ):
                raise JevError("invalid_response", "crisis: noul inválido")
            crisis = float(value)
    annoyance: float | None = None
    if config.uses("annoyance"):
        score_answer = _answer(answers, "annoyance", "score")
        if score_answer is not None:
            value = score_answer.get("score")
            if (
                isinstance(value, bool)
                or not isinstance(value, (int, float))
                or not 0 <= value <= 3
            ):
                raise JevError("invalid_response", "annoyance: score inválido")
            annoyance = float(value)
    try:
        decision = GateDecision(
            route=route,
            probabilities=probabilities,
            confidence=probabilities[route],
            alternative=alternative,
            scope_reason=scope_reason,
        )
        signals = GateSignals(crisis_probability=crisis, annoyance=annoyance)
    except ValidationError as exc:
        raise JevError("invalid_response", "modelo inválido") from exc
    model = payload.get("model")
    return decision, signals, model if isinstance(model, str) else None


def _cost(payload: Mapping[str, Any]) -> float | None:
    usage = payload.get("usage")
    if not isinstance(usage, Mapping):
        return None
    cost = usage.get("cost")
    if isinstance(cost, (int, float)) and not isinstance(cost, bool) and cost >= 0:
        return float(cost)
    tokens = usage.get("input_tokens")
    if isinstance(tokens, int) and not isinstance(tokens, bool) and tokens >= 0:
        return round(tokens * INPUT_PRICE_PER_TOKEN, 9)
    return None


def _http_reason(status: int) -> GateReason:
    known: dict[int, GateReason] = {
        401: "http_401",
        402: "http_402",
        422: "http_422",
        429: "http_429",
    }
    if status in known:
        return known[status]
    return "http_5xx" if status >= 500 else "http_other"


# ---------------------------------------------------------------- cliente real (research R1, R8)


def _load_env() -> None:
    try:
        from dotenv import load_dotenv
    except ImportError:  # pragma: no cover - python-dotenv es dependencia del proyecto
        return
    load_dotenv(PROJECT_ROOT / ".env", override=False)


def read_api_key(environ: Mapping[str, str] | None = None) -> str | None:
    if environ is None:
        _load_env()
        environ = os.environ
    key = (environ.get(API_KEY_ENV) or "").strip()
    return key or None


class TypeSafeJevGate:
    """Cliente HTTP de Jev: una solicitud por turno, sin reintentos (``httpx``)."""

    __slots__ = ("_api_key", "_transport", "config", "prompts")

    def __init__(
        self,
        config: JevConfig,
        api_key: str,
        *,
        prompts: GatePrompts | None = None,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self.config = config
        self.prompts = prompts or load_gate_prompts()
        self._api_key = api_key
        self._transport = transport

    def __repr__(self) -> str:  # la clave nunca aparece
        return f"TypeSafeJevGate(model={self.config.model!r}, base_url={self.config.base_url!r})"

    def request_body(self, message: str, history: Sequence[str]) -> dict[str, Any]:
        return {
            "model": self.config.model,
            "state": build_state(message, history, self.config.max_input_chars),
            "questions": build_questions(self.prompts, self.config.signals),
        }

    def _client(self) -> httpx.Client:
        return httpx.Client(
            base_url=self.config.base_url,
            timeout=httpx.Timeout(self.config.timeout_seconds),
            transport=self._transport,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
        )

    def assess(self, message: str, history: Sequence[str] = ()) -> GateOutcome:
        started = time.perf_counter()

        def elapsed() -> int:
            return int((time.perf_counter() - started) * 1000)

        try:
            body = self.request_body(message, history)
            with self._client() as client:
                response = client.post(SYSTEMONE_PATH, json=body)
            if response.status_code >= 400:
                raise JevError(_http_reason(response.status_code))
            payload = response.json()
            decision, signals, model = parse_response(payload, self.config)
            return GateOutcome(
                status="ok",
                decision=decision,
                signals=signals,
                latency_ms=elapsed(),
                cost=_cost(payload),
                model=model or self.config.model,
            )
        except JevError as exc:
            reason = exc.reason
        except httpx.TimeoutException:
            reason = "timeout"
        except httpx.HTTPError:
            reason = "network"
        except json.JSONDecodeError, ValueError, TypeError, KeyError:
            reason = "invalid_response"
        except Exception:
            logger.exception("Fallo inesperado del gatekeeper Jev")
            reason = "invalid_response"
        logger.info("Jev no disponible para este turno (%s)", reason)
        return GateOutcome(status="failed", reason=reason, latency_ms=elapsed())


# ---------------------------------------------------------------- simulación (research R12)


class FakeJevGate:
    """Gatekeeper determinista para demo y pruebas: sin red ni clave.

    Por defecto deriva la ruta de la heurística del enrutador, la crisis del léxico de la spec 019
    y la molestia de ``detect_sentiment``. ``outcomes`` permite inyectar respuestas o fallos.
    """

    def __init__(
        self,
        config: JevConfig | None = None,
        *,
        confidence: float = 0.9,
        outcomes: Mapping[str, GateOutcome] | None = None,
        default: GateOutcome | None = None,
    ) -> None:
        self.config = config or JevConfig(enabled=True)
        self.confidence = confidence
        self.outcomes = dict(outcomes or {})
        self.default = default
        self.calls: list[tuple[str, tuple[str, ...]]] = []

    def assess(self, message: str, history: Sequence[str] = ()) -> GateOutcome:
        self.calls.append((message, tuple(history)))
        if message in self.outcomes:
            return self.outcomes[message]
        if self.default is not None:
            return self.default
        from . import care
        from .router import heuristic_decision

        heuristic = heuristic_decision(message, history)
        rest = (1.0 - self.confidence) / (len(ROUTES) - 1)
        probabilities = {
            route: self.confidence if route == heuristic.route else rest for route in ROUTES
        }
        sentiment, _ = care.detect_sentiment(message)
        annoyance = {"angry": 3.0, "frustrated": 2.0, "distressed": 2.0}.get(sentiment, 0.0)
        return GateOutcome(
            status="ok",
            decision=GateDecision(
                route=heuristic.route,
                probabilities=probabilities,
                confidence=self.confidence,
                alternative=heuristic.alternative,
                scope_reason="off_topic" if heuristic.route == "out_of_scope" else None,
            ),
            signals=GateSignals(
                crisis_probability=0.95 if care.detect_crisis(message) else 0.01,
                annoyance=annoyance,
            ),
            latency_ms=0,
            cost=0.0,
            model=f"{self.config.model}-simulado",
        )


def fake_outcome(
    route: Route,
    confidence: float,
    *,
    crisis: float | None = None,
    annoyance: float | None = None,
    scope_reason: ScopeReason | None = None,
) -> GateOutcome:
    """Atajo para pruebas: resultado ``ok`` con la probabilidad dada para ``route``."""
    rest = (1.0 - confidence) / (len(ROUTES) - 1)
    probabilities = {key: confidence if key == route else rest for key in ROUTES}
    ranked = sorted((k for k in ROUTES if k != route), key=probabilities.__getitem__, reverse=True)
    return GateOutcome(
        status="ok",
        decision=GateDecision(
            route=route,
            probabilities=probabilities,
            confidence=confidence,
            alternative=ranked[0] if rest > 0 else None,
            scope_reason=scope_reason,
        ),
        signals=GateSignals(crisis_probability=crisis, annoyance=annoyance),
        model="jev-test",
    )


# ---------------------------------------------------------------- construcción (research R9)

_ANNOUNCED: set[str] = set()


def _announce(message: str) -> None:
    """Registra el estado del gatekeeper una sola vez por proceso (T026)."""
    if message not in _ANNOUNCED:
        _ANNOUNCED.add(message)
        logger.info(message)


def build_gate(
    config: JevConfig,
    *,
    demo: bool = False,
    environ: Mapping[str, str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> JevGate | None:
    """Gatekeeper según la configuración: ``None`` si está desactivado o falta la clave."""
    if not config.enabled:
        _announce("Jev desactivado en configuración ([jev].enabled = false).")
        return None
    if demo:
        _announce("Jev en modo demostración (simulado, sin red).")
        return FakeJevGate(config)
    api_key = read_api_key(environ)
    if api_key is None:
        _announce(f"Jev desactivado: falta {API_KEY_ENV} en el entorno o en .env.")
        return None
    try:
        gate = TypeSafeJevGate(config, api_key, transport=transport)
    except JevPromptError as exc:
        _announce(f"Jev desactivado: {exc}")
        return None
    _announce(f"Jev activo, modelo {config.model}.")
    return gate


def gate_status_info(
    config: JevConfig, *, demo: bool = False, environ: Mapping[str, str] | None = None
) -> dict[str, Any]:
    """Estado del gatekeeper para ``/api/observability`` (sin la clave ni su existencia parcial).

    ``state``: ``disabled`` (configuración), ``simulated`` (modo demo), ``no_key`` (activo sin
    clave, funciona como desactivado) o ``active``.
    """
    if not config.enabled:
        state = "disabled"
    elif demo:
        state = "simulated"
    elif read_api_key(environ) is None:
        state = "no_key"
    else:
        state = "active"
    return {
        "state": state,
        "model": config.model,
        "route_threshold": config.route_threshold,
        "signals": list(config.signals),
    }


def gate_status(config: JevConfig, environ: Mapping[str, str] | None = None) -> str:
    """Texto corto del estado para el CLI y la API."""
    if not config.enabled:
        return "desactivado en configuración"
    if read_api_key(environ) is None:
        return f"desactivado: falta {API_KEY_ENV}"
    return f"activo, modelo {config.model}"


# ---------------------------------------------------------------- señales de atención (R6)

_SENTIMENT_RANK = {
    "neutral": 0,
    "satisfied": 0,
    "confused": 1,
    "frustrated": 2,
    "angry": 3,
    "distressed": 4,
}


def merge_signals(
    signals: dict[str, Any] | None, outcome: GateOutcome | None, config: JevConfig
) -> dict[str, Any] | None:
    """Fusiona las señales de Jev con las de ``care.analyze`` (research R6).

    - Crisis = detección determinista **o** ``P(crisis) ≥ crisis_threshold``; nunca se anula.
    - Molestia ≥ 2 sube la emoción a ``frustrated`` y 3 a ``angry``, sin rebajar una emoción más
      intensa ya detectada.
    """
    if signals is None or outcome is None or outcome.status != "ok" or outcome.signals is None:
        return signals
    merged = dict(signals)
    gate = outcome.signals
    if config.uses("crisis") and gate.crisis_probability is not None:
        merged["jev_crisis_probability"] = gate.crisis_probability
        if gate.crisis_probability >= config.crisis_threshold and not merged.get("crisis"):
            merged["crisis"] = True
            merged["jev_crisis"] = True
    if config.uses("annoyance") and gate.annoyance is not None:
        merged["jev_annoyance"] = gate.annoyance
        level = gate.annoyance_level or 0
        proposed = "angry" if level >= 3 else "frustrated" if level >= 2 else None
        current = str(merged.get("sentiment") or "neutral")
        if proposed and _SENTIMENT_RANK[proposed] > _SENTIMENT_RANK.get(current, 0):
            merged["sentiment"] = proposed
    return merged


# ---------------------------------------------------------------- chequeo (FR-014)


def health_check(
    config: JevConfig,
    *,
    environ: Mapping[str, str] | None = None,
    transport: httpx.BaseTransport | None = None,
) -> dict[str, Any]:
    """Verifica clave, red y versión fijada con ``GET /v1/models``; nunca incluye la clave."""
    result: dict[str, Any] = {
        "ok": False,
        "model": config.model,
        "base_url": config.base_url,
        "latency_ms": 0,
        "detail": "",
    }
    api_key = read_api_key(environ)
    if api_key is None:
        result["detail"] = f"Falta {API_KEY_ENV}: añádela a .env (https://console.typesafe.ai)."
        return result
    started = time.perf_counter()
    try:
        with httpx.Client(
            base_url=config.base_url,
            timeout=httpx.Timeout(max(config.timeout_seconds, 5.0)),
            transport=transport,
            headers={"Authorization": f"Bearer {api_key}"},
        ) as client:
            response = client.get(MODELS_PATH)
        result["latency_ms"] = int((time.perf_counter() - started) * 1000)
        if response.status_code >= 400:
            code = response.status_code
            result["detail"] = f"El servicio respondió {code} ({_http_reason(code)})."
            return result
        available = _model_ids(response.json())
        if config.model not in available:
            # La cuenta puede listar solo los alias (``jev-latest``) y aun así aceptar la versión
            # fija: se verifica con una pregunta mínima y se compara el ``model`` que responde.
            probe = client_probe(config, api_key, transport)
            if probe == config.model:
                available.add(config.model)
    except httpx.HTTPError as exc:
        result["detail"] = f"Sin conexión con {config.base_url} ({type(exc).__name__})."
        return result
    except json.JSONDecodeError, ValueError:
        result["detail"] = "Respuesta inválida de /v1/models."
        return result
    result["available"] = sorted(available)
    if config.model in available:
        result["ok"] = True
        result["detail"] = "modelo disponible"
    else:
        result["detail"] = f"La versión fijada {config.model} no está disponible para esta cuenta."
    return result


def client_probe(
    config: JevConfig, api_key: str, transport: httpx.BaseTransport | None = None
) -> str | None:
    """Pregunta mínima (Noul) para confirmar la versión; devuelve el ``model`` que respondió."""
    body = {
        "model": config.model,
        "state": {"mensaje": "Hola"},
        "questions": {"ping": {"type": "noul", "instructions": "¿El mensaje es un saludo?"}},
    }
    with httpx.Client(
        base_url=config.base_url,
        timeout=httpx.Timeout(max(config.timeout_seconds, 5.0)),
        transport=transport,
        headers={"Authorization": f"Bearer {api_key}"},
    ) as client:
        response = client.post(SYSTEMONE_PATH, json=body)
    if response.status_code >= 400:
        return None
    model = response.json().get("model")
    return model if isinstance(model, str) else None


def _model_ids(payload: Any) -> set[str]:
    items = (
        payload.get("data") or payload.get("models") if isinstance(payload, Mapping) else payload
    )
    ids: set[str] = set()
    for item in items or []:
        if isinstance(item, str):
            ids.add(item)
        elif isinstance(item, Mapping):
            for key in ("id", "name", "model"):
                if isinstance(item.get(key), str):
                    ids.add(item[key])
    return ids
