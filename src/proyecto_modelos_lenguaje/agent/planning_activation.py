"""Evaluación de la activación del planificador por contexto (spec 028, T045, SC-007).

La decisión es de reglas (``router.planning_decision``), así que la evaluación es determinista y sin
red: 15 consultas de planificación, 15 parecidas que no lo son y repreguntas que solo deben seguir
en planificación cuando el turno anterior fue ``planning``. El conjunto se fijó antes de medir
(``tests/fixtures/agent/planning_activation.jsonl``, regla 21).
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from .router import planning_decision

FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "agent" / "planning_activation.jsonl"
TARGET = 14  # ≥ 14/15 en cada lado (SC-007)


@dataclass(frozen=True, slots=True)
class ActivationResult:
    case_id: str
    text: str
    expected: bool
    follow_up: bool
    activated: bool
    activated_without_context: bool

    @property
    def hit(self) -> bool:
        if self.follow_up:  # sigue con contexto y no se dispara solo por sí misma
            return self.activated
        return self.activated == self.expected


def load_cases(path: Path = FIXTURE) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def evaluate(cases: list[dict[str, Any]] | None = None) -> list[ActivationResult]:
    results = []
    for case in cases if cases is not None else load_cases():
        follow_up = bool(case.get("follow_up"))
        previous = "planning" if follow_up else None
        results.append(
            ActivationResult(
                case_id=str(case["id"]),
                text=str(case["text"]),
                expected=bool(case["expected"]),
                follow_up=follow_up,
                activated=planning_decision(case["text"], previous_route=previous) is not None,
                activated_without_context=planning_decision(case["text"]) is not None,
            )
        )
    return results


def summarize(results: list[ActivationResult]) -> dict[str, Any]:
    positives = [r for r in results if not r.follow_up and r.expected]
    negatives = [r for r in results if not r.follow_up and not r.expected]
    follow_ups = [r for r in results if r.follow_up]
    hits_pos = sum(r.hit for r in positives)
    hits_neg = sum(r.hit for r in negatives)
    return {
        "planning_hits": hits_pos,
        "planning_total": len(positives),
        "non_planning_hits": hits_neg,
        "non_planning_total": len(negatives),
        "follow_up_hits": sum(r.hit for r in follow_ups),
        "follow_up_total": len(follow_ups),
        "false_positives": [r.case_id for r in negatives if not r.hit],
        "false_negatives": [r.case_id for r in positives if not r.hit],
        "meets_target": hits_pos >= TARGET and hits_neg >= TARGET,
    }


def render_markdown(results: list[ActivationResult], summary: dict[str, Any]) -> str:
    stamp = datetime.now(UTC).date().isoformat()
    rows = "\n".join(
        f"| {r.case_id} | {r.text} | {'sí' if r.expected else 'no'} | "
        f"{'sí' if r.activated else 'no'} | {'✅' if r.hit else '❌'} |"
        for r in results
    )
    meets = "✅ cumple" if summary["meets_target"] else "❌ no cumple"
    measures = [
        (
            "Consultas de planificación que activan el planificador",
            f"{summary['planning_hits']}/{summary['planning_total']}",
        ),
        (
            "Consultas parecidas que **no** lo activan",
            f"{summary['non_planning_hits']}/{summary['non_planning_total']}",
        ),
        (
            "Repreguntas que siguen en planificación (turno anterior `planning`)",
            f"{summary['follow_up_hits']}/{summary['follow_up_total']}",
        ),
        ("Falsos positivos", ", ".join(summary["false_positives"]) or "ninguno"),
        ("Falsos negativos", ", ".join(summary["false_negatives"]) or "ninguno"),
    ]
    table = "\n".join(f"| {name} | {value} |" for name, value in measures)
    reading = (
        "La activación es de **reglas** (`router.planning_decision`): sin modelo, determinista y "
        "sin costo. Se activa para cualquier persona, en la web y en WhatsApp, **solo en ese "
        "turno** (y en la repregunta inmediata de un escenario), sin cambiar el perfil de la "
        "conversación. Las preguntas informativas que comparten palabras con la planificación "
        "(«programas con cultivadores de caña», «¿cuánta caña molió en 2022?») no la activan: así "
        "un falso positivo no deja a un visitante «atrapado» en la planificación. Las repreguntas "
        "(«¿y si baja 20 %?») solo cuentan cuando el turno anterior fue de planificación."
    )
    header = (
        f"**Fecha**: {stamp} · **Comando**: `uv run python -m proyecto_modelos_lenguaje.agent "
        "evaluate --planning-activation --markdown` · **Conjunto**: "
        "`tests/fixtures/agent/planning_activation.jsonl` (fijado antes de medir) · "
        f"**Meta (SC-007)**: ≥ {TARGET}/15 en cada lado."
    )
    return (
        "# Evaluación: activación del planificador por contexto (spec 028)\n\n"
        f"{header}\n\n## Resultado: {meets}\n\n| Medida | Valor |\n|---|---|\n{table}\n\n"
        f"## Lectura\n\n{reading}\n\n## Casos\n\n"
        f"| id | Consulta | Esperado | Activó | |\n|---|---|---|---|---|\n{rows}\n"
    )


def report(results: list[ActivationResult], summary: dict[str, Any]) -> dict[str, Any]:
    return {"summary": summary, "results": [asdict(r) | {"hit": r.hit} for r in results]}
