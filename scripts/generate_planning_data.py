"""Genera los datos SINTÉTICOS de planificación industrial (spec 025, R10, T022).

Uso:
    uv run python scripts/generate_planning_data.py --seed 2026 --version v1          # escribe
    uv run python scripts/generate_planning_data.py --seed 2026 --version v1 --check  # verifica

Escribe ``data/synthetic/planificacion/<versión>/``: ``plant_cana.json``, ``state.json``,
``commitments.json``, ``procedures/*.md`` y ``DATA_CARD.md``. Todo es determinista con la semilla:
regenerar no cambia ningún byte (``--check`` sale con 1 si cambiaría alguno).

Nada de esto describe la operación real de Manuelita. Los órdenes de magnitud se anclan en cifras
públicas citadas en la ficha (cogeneración del Informe de Sostenibilidad 2023-2024).

Calibración (``contracts/planning-tools.md``): los compromisos son el 97 % de lo que produce la
mezcla de referencia (85 % de la caña a azúcar) con 15 % menos de caña. Así la semana base es
factible con holgura ≥ 10 %, −15 % es factible con algún compromiso activo y −35 % no lo es.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT_ROOT = ROOT / "data" / "synthetic" / "planificacion"
WEEK = "2026-W48"
REFERENCE_SHARE = 0.85
COMMITMENT_FACTOR = 0.97
CALIBRATION_DELTA = -0.15

NOMINAL = {
    "mill_capacity": (60_000.0, 0),
    "distillery_capacity": (2_000_000.0, -3),
    "boiler_capacity": (40_000.0, -1),
    "turbine_capacity": (4_000.0, 0),
    "quality_ref": (13.0, 1),
    "sugar_yield": (0.115, 4),
    "molasses_yield": (0.035, 4),
    "ethanol_from_molasses": (280.0, 0),
    "ethanol_from_juice": (80.0, 1),
    "bagasse_yield": (0.28, 3),
    "steam_per_bagasse": (2.2, 2),
    "steam_sugar": (0.50, 3),
    "steam_ethanol": (0.003, 5),
    "power_per_steam": (0.095, 4),
    "power_use": (0.03, 4),
    "price_sugar": (1_900_000.0, -3),
    "price_ethanol": (2_600.0, 0),
    "price_power": (350_000.0, -3),
    "cost_cane": (120_000.0, -3),
}
FIXED = {"mill_capacity", "quality_ref", "turbine_capacity"}

PROCEDURES = (
    (
        "PO-01",
        "Prioridad de compromisos",
        "Cuando la caña disponible no alcanza para todos los compromisos de la semana, primero se "
        "cumple el compromiso de prioridad 1, luego el de prioridad 2 y por último el de "
        "prioridad 3. "
        "Toda propuesta que deje un compromiso sin cumplir se escala al jefe de planta antes del "
        "cierre del día.",
    ),
    (
        "PO-02",
        "Desvío de jugo a destilería",
        "El jugo de caña puede enviarse directo a la destilería para producir etanol cuando el "
        "compromiso de etanol no se cubre con la miel de la línea de azúcar. El desvío se ajusta "
        "por "
        "turno y no requiere parar molinos.",
    ),
    (
        "PO-03",
        "Operación con caña de baja calidad",
        "Con caña de pol inferior a 12, el rendimiento de azúcar por tonelada baja en proporción "
        "a la "
        "calidad. Se recomienda revisar la mezcla azúcar-etanol y la programación de cosecha con "
        "campo.",
    ),
    (
        "PO-04",
        "Límite de vapor de calderas",
        "La generación de vapor no puede superar la capacidad de las calderas ni el vapor que "
        "permite "
        "el bagazo disponible. La línea de azúcar y la destilería consumen vapor; si la demanda "
        "supera "
        "la oferta, se reduce la molienda o se cambia la mezcla.",
    ),
    (
        "PO-05",
        "Exportación de energía comprometida",
        "La energía exportada a la red es la generada por el turbogenerador menos el consumo de la "
        "fábrica. El compromiso semanal de energía se vigila a diario y cualquier desvío se "
        "informa "
        "al operador de red.",
    ),
    (
        "PO-06",
        "Mantenimiento del turbogenerador",
        "Un turbogenerador degradado reduce la capacidad de generación según su factor de "
        "capacidad. "
        "Los mantenimientos se programan fuera de las semanas con compromisos de energía altos.",
    ),
    (
        "PO-07",
        "Capacidad de molienda",
        "La molienda semanal no supera la capacidad nominal de los molinos multiplicada por su "
        "factor "
        "de disponibilidad. La caña que no se muele en la semana se reprograma con el área de "
        "campo.",
    ),
    (
        "PO-08",
        "Inventario de miel",
        "La miel de la línea de azúcar se envía a la destilería en la misma semana. El inventario "
        "inicial de miel sirve como amortiguador y no se cuenta como producción nueva.",
    ),
    (
        "PO-09",
        "Cambios de mezcla azúcar-etanol",
        "Los cambios de mezcla entre azúcar y etanol se aplican al inicio de turno. El modelo "
        "semanal "
        "no incluye tiempos de transición; el equipo de planta los evalúa antes de aprobar un "
        "plan.",
    ),
    (
        "PO-10",
        "Aprobación de planes de producción",
        "Un plan de producción recomendado por herramientas de análisis es una propuesta: el jefe "
        "de "
        "planta y el área comercial lo revisan y lo aprueban antes de cambiar la operación.",
    ),
)


def _perturb(rng: random.Random, key: str) -> float:
    value, decimals = NOMINAL[key]
    if key not in FIXED:
        value *= 1 + rng.uniform(-0.03, 0.03)
    return round(value, decimals) if decimals > 0 else float(round(value, decimals))


def _production(plant: dict, cane: float, quality: float, share: float) -> dict[str, float]:
    k = quality / plant["quality_ref"]
    x_s, x_e = share * cane, (1 - share) * cane
    sugar = plant["sugar_yield"] * k * x_s
    ethanol = (
        plant["ethanol_from_molasses"] * plant["molasses_yield"] * x_s
        + plant["ethanol_from_juice"] * k * x_e
    )
    steam = min(
        plant["steam_per_bagasse"] * plant["bagasse_yield"] * cane, plant["boiler_capacity"]
    )
    power = min(plant["power_per_steam"] * steam, plant["turbine_capacity"])
    return {"sugar": sugar, "ethanol": ethanol, "power": power - plant["power_use"] * cane}


def build(seed: int, version: str) -> dict[str, str]:
    """Contenido de cada archivo (ruta relativa → texto)."""
    rng = random.Random(seed)
    plant = {key: _perturb(rng, key) for key in NOMINAL}
    cane = float(round(55_000 * (1 + rng.uniform(-0.02, 0.02)), -1))
    quality = round(13.2 + rng.uniform(-0.2, 0.2), 1)
    header = {"synthetic": True, "seed": seed, "version": version}
    plant_doc = {
        **header,
        "plant_id": "cana",
        "description": (
            "Planta de caña SINTÉTICA para demostrar la planificación (no es Manuelita)."
        ),
        **plant,
        "units": {
            "capacities": "por semana (t caña, L etanol, t vapor, MWh)",
            "prices": "COP netos sintéticos por t de azúcar, L de etanol y MWh exportado",
            "cost_cane": "COP por t de caña procesada",
        },
        "sources": [
            {
                "use": (
                    "orden de magnitud de la cogeneración (≈ 200.000 MWh/año ≈ 3.800 MWh/semana)"
                ),
                "citation": "Informe de Sostenibilidad Manuelita 2023-2024, p. 57 y 124",
                "url": "https://www.manuelita.com/wp-content/uploads/2025/06/"
                "Informe-de-Sostenibilidad-Manuelita-2023-2024.pdf",
            }
        ],
    }
    state_doc = {
        **header,
        "week": WEEK,
        "cane_available": cane,
        "cane_quality": quality,
        "equipment": [
            {"id": "molino-1", "kind": "molino", "status": "ok", "capacity_factor": 1.0},
            {"id": "destileria-1", "kind": "destileria", "status": "ok", "capacity_factor": 1.0},
            {"id": "caldera-1", "kind": "caldera", "status": "ok", "capacity_factor": 1.0},
            {"id": "turbo-1", "kind": "turbogenerador", "status": "ok", "capacity_factor": 1.0},
        ],
        "inventories": {"sugar_t": 1_200.0, "ethanol_l": 150_000.0, "molasses_t": 300.0},
        "current_mix": {"x_s": round(0.9 * cane, 1), "x_e": round(0.1 * cane, 1)},
    }
    reference = _production(plant, cane * (1 + CALIBRATION_DELTA), quality, REFERENCE_SHARE)
    commitments_doc = {
        **header,
        "week": WEEK,
        "commitments": [
            {
                "id": "c-azucar-1",
                "product": "sugar",
                "min_quantity": float(round(COMMITMENT_FACTOR * reference["sugar"], -1)),
                "priority": 1,
                "counterparty": "Cliente industrial A",
            },
            {
                "id": "c-etanol-1",
                "product": "ethanol",
                "min_quantity": float(round(COMMITMENT_FACTOR * reference["ethanol"], -3)),
                "priority": 2,
                "counterparty": "Mayorista de combustibles B",
            },
            {
                "id": "c-energia-1",
                "product": "power",
                "min_quantity": float(round(COMMITMENT_FACTOR * reference["power"], 0)),
                "priority": 3,
                "counterparty": "Comercializador de energía C",
            },
        ],
    }
    files: dict[str, str] = {
        "plant_cana.json": _json(plant_doc),
        "state.json": _json(state_doc),
        "commitments.json": _json(commitments_doc),
    }
    for proc_id, title, text in PROCEDURES:
        files[f"procedures/{proc_id.lower()}.md"] = (
            f'---\nid: {proc_id}\ntitle: "{title}"\nsynthetic: true\n---\n\n'
            f"# {proc_id} · {title}\n\n"
            f"{text}\n"
        )
    files["DATA_CARD.md"] = _card(seed, version)
    return files


def _json(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def _card(seed: int, version: str) -> str:
    return f"""# Ficha de datos — planificación industrial SINTÉTICA ({version})

- **Naturaleza**: datos **sintéticos** generados por
  `scripts/generate_planning_data.py --seed {seed} --version {version}`. No describen la
  operación, los contratos, los precios ni las capacidades reales de Manuelita.
- **Uso permitido**: demostrar el agente de planificación industrial de la plataforma
  (spec 025, idea 7.4) y evaluarlo con `tests/fixtures/agent/planning_scenarios.jsonl`.
- **Uso prohibido**: citarlos como datos de Manuelita, mezclarlos con el corpus público
  (capa oro) o tomar decisiones reales con ellos (constitución 2.0.0, regla 18).
- **Contenido**: `plant_cana.json` (capacidades, rendimientos, precios y costos),
  `state.json` (semana {WEEK}, caña disponible, calidad, equipos, inventarios y mezcla
  actual), `commitments.json` (compromisos semanales con contrapartes genéricas) y
  `procedures/` (10 procedimientos operativos citables como `[S#]`).
- **Anclaje de magnitud**: la cogeneración pública de Manuelita (≈ 200.000 MWh/año; Informe
  de Sostenibilidad 2023-2024, p. 57 y 124) orienta el orden de magnitud semanal de la
  energía. Los demás valores son plausibles para un ingenio mediano y se perturban ±3 %.
- **Calibración**: compromisos = 97 % de la producción con 85 % de la caña a azúcar y
  15 % menos de caña.
- **Reproducibilidad**: `--check` falla si regenerar cambiaría algún byte.
- **Datos personales**: ninguno.
"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--version", default="v1")
    parser.add_argument("--check", action="store_true", help="Solo verifica; no escribe.")
    parser.add_argument("--out", default=str(OUT_ROOT), help="Directorio raíz de salida.")
    args = parser.parse_args(argv)
    out = Path(args.out) / args.version
    files = build(args.seed, args.version)
    if args.check:
        changed = [
            rel
            for rel, text in files.items()
            if not (out / rel).is_file() or (out / rel).read_text(encoding="utf-8") != text
        ]
        if changed:
            print(f"Regenerar cambiaría: {', '.join(changed)}")
            return 1
        print(f"OK: {len(files)} archivos idénticos en {out}")
        return 0
    for rel, text in files.items():
        path = out / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8", newline="\n")
    print(f"Escribí {len(files)} archivos en {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
