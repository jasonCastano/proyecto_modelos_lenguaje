"""Genera la batería de planificación con su óptimo de referencia (spec 025, R9, T025).

Uso:
    uv run python scripts/generate_planning_battery.py --seed 2026 [--check]

Escribe ``tests/fixtures/agent/planning_scenarios.jsonl``: 12 escenarios (10 factibles y 2 sin
solución) fijados ANTES de evaluar (principio V). El óptimo de referencia sale de
``planning_reference`` (malla), no del optimizador del agente.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from proyecto_modelos_lenguaje.agent.planning import Scenario, load_plant
from proyecto_modelos_lenguaje.agent.planning_reference import reference_optimum

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "tests" / "fixtures" / "agent" / "planning_scenarios.jsonl"

# (id, escenario, pregunta). Las preguntas son las que el planificador escribiría.
SCENARIOS: tuple[tuple[str, dict, str], ...] = (
    ("p01", {}, "Planifica la producción de esta semana con la caña disponible."),
    (
        "p02",
        {"cane_delta_pct": -15},
        "Tenemos 15 % menos caña esta semana. Evalúa cómo cumplir los compromisos de azúcar y "
        "etanol "
        "y mantener el suministro de energía.",
    ),
    (
        "p03",
        {"cane_delta_pct": -10},
        "Llega un 10 % menos de caña esta semana, ¿cómo repartimos entre azúcar y etanol?",
    ),
    (
        "p04",
        {"cane_delta_pct": -5},
        "Con 5 % menos de caña, ¿cuál es el mejor programa de producción?",
    ),
    (
        "p05",
        {"cane_delta_pct": 10},
        "Si llega 10 % más de caña, ¿qué programa de producción maximiza el margen?",
    ),
    (
        "p06",
        {"cane_quality": 12.0},
        "La caña viene con pol de 12. ¿Cómo ajustamos el programa de producción de la semana?",
    ),
    (
        "p07",
        {"cane_quality": 14.5},
        "La calidad de la caña subió a 14,5 de pol. ¿Qué programa de producción recomiendas?",
    ),
    (
        "p08",
        {"steam_limit": 30000},
        "Tenemos una restricción de vapor de 30.000 toneladas esta semana. ¿Cómo queda el "
        "programa?",
    ),
    (
        "p09",
        {"cane_delta_pct": -12, "cane_quality": 13.8},
        "Hay 12 % menos de caña pero con pol de 13,8. Planifica azúcar, etanol y energía.",
    ),
    (
        "p10",
        {"cane_delta_pct": 5, "steam_limit": 32000},
        "Con 5 % más de caña y un límite de vapor de 32.000 toneladas, ¿cuál es el plan de "
        "producción?",
    ),
    (
        "p11",
        {"cane_delta_pct": -35},
        "Esta semana tenemos 35 % menos caña. ¿Podemos cumplir todos los compromisos?",
    ),
    (
        "p12",
        {"cane_delta_pct": -25, "steam_limit": 15000},
        "Con 25 % menos de caña y vapor limitado a 15.000 toneladas, ¿cómo cumplimos los "
        "contratos?",
    ),
)
EXPECTED_INFEASIBLE = 2


def build(seed: int) -> list[str]:
    random.seed(seed)  # la batería es fija; la semilla queda registrada por trazabilidad
    data = load_plant()
    lines: list[str] = []
    infeasible = 0
    for case_id, scenario_args, question in SCENARIOS:
        scenario = Scenario(**scenario_args)
        ref = reference_optimum(data, scenario)
        infeasible += not ref.feasible
        lines.append(
            json.dumps(
                {
                    "id": case_id,
                    "question": question,
                    "scenario": scenario_args,
                    "feasible": ref.feasible,
                    "reference_margin": ref.margin,
                    "reference_mix": {"x_s": ref.x_s, "x_e": ref.x_e} if ref.feasible else None,
                    "grid_step": ref.grid_step,
                    "data_version": data.version,
                    "seed": seed,
                },
                ensure_ascii=False,
            )
        )
    if infeasible != EXPECTED_INFEASIBLE:
        raise SystemExit(
            f"La batería debe tener {EXPECTED_INFEASIBLE} escenarios sin solución y tiene "
            f"{infeasible}; revisa la calibración de los datos."
        )
    return lines


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args(argv)
    text = "\n".join(build(args.seed)) + "\n"
    if args.check:
        current = OUT.read_text(encoding="utf-8") if OUT.is_file() else ""
        if current != text:
            print("La batería cambiaría al regenerarla.")
            return 1
        print("OK: batería idéntica.")
        return 0
    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"Escribí {len(SCENARIOS)} escenarios en {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
