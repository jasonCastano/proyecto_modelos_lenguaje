"""Planificación industrial sobre datos sintéticos (spec 025, idea 7.4; research R6–R12).

Modelo lineal semanal de una planta de caña: cuánta caña va a la línea de azúcar (``x_s``) y
cuánta a jugo directo para etanol (``x_e``), cuánto bagazo se quema (``b``), cuánto vapor se
genera (``v``) y cuánta energía se exporta (``g``). Ecuaciones en ``data-model.md`` §4.

Reglas (constitución 2.0.0, reglas 18–20):

- Los datos son **sintéticos** (``data/synthetic/planificacion/<versión>``) y toda salida lo dice.
- Las cifras salen de aquí (simulador y ``scipy.optimize.linprog`` con HiGHS), nunca del modelo de
  lenguaje: ``check_answer`` verifica que cada número de la respuesta esté en las salidas de las
  herramientas y, si no, la respuesta se reemplaza por el ``plan_card``.
- Si el escenario no tiene solución, un LP elástico reporta el faltante de cada compromiso sin
  relajar nunca una capacidad física.
- El agente recomienda; el equipo de planta decide.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from ..config import PROJECT_ROOT

DATA_ROOT = PROJECT_ROOT / "data" / "synthetic" / "planificacion"
DEFAULT_VERSION = "v1"
SYNTHETIC_LABEL = "Datos sintéticos de demostración"
DECISION_PHRASE = "El agente recomienda; el equipo de planta decide."
PLAN_ID = re.compile(r"\bp-[0-9a-f]{8}\b")
ACTIVE_SLACK = 1e-6
SOLVER_TIME_LIMIT = 5.0
PENALTY_FACTOR = 1_000.0  # faltante: 10³ × precio unitario ÷ prioridad (R8)
PlantId = Literal["cana"]
Product = Literal["sugar", "ethanol", "power"]
PRODUCT_LABELS = {"sugar": "azúcar", "ethanol": "etanol", "power": "energía exportada"}
PRODUCT_UNITS = {"sugar": "t", "ethanol": "L", "power": "MWh"}


class PlanningError(RuntimeError):
    """Datos de planta ausentes o inválidos, o el solver falló."""


# --------------------------------------------------------------------------- formato es-CO


def fmt(value: float, decimals: int = 0) -> str:
    """Número con punto de miles y coma decimal (``46750.5`` → ``46.750,5``)."""
    text = f"{round(value):,}" if decimals == 0 else f"{value:,.{decimals}f}"
    return text.replace(",", "_").replace(".", ",").replace("_", ".")


def fmt_millions(value: float) -> str:
    return f"COP {fmt(value / 1e6)} millones"


# --------------------------------------------------------------------------- datos


@dataclass(frozen=True, slots=True)
class PlantModel:
    plant_id: str
    mill_capacity: float
    distillery_capacity: float
    boiler_capacity: float
    turbine_capacity: float
    quality_ref: float
    sugar_yield: float
    molasses_yield: float
    ethanol_from_molasses: float
    ethanol_from_juice: float
    bagasse_yield: float
    steam_per_bagasse: float
    steam_sugar: float
    steam_ethanol: float
    power_per_steam: float
    power_use: float
    price_sugar: float
    price_ethanol: float
    price_power: float
    cost_cane: float


@dataclass(frozen=True, slots=True)
class Equipment:
    id: str
    kind: str
    status: str
    capacity_factor: float


@dataclass(frozen=True, slots=True)
class Commitment:
    id: str
    product: str
    min_quantity: float
    priority: int
    counterparty: str


@dataclass(frozen=True, slots=True)
class PlantState:
    week: str
    cane_available: float
    cane_quality: float
    equipment: tuple[Equipment, ...]
    inventories: dict[str, float]
    current_mix: dict[str, float]

    def factor(self, kind: str) -> float:
        factors = [item.capacity_factor for item in self.equipment if item.kind == kind]
        return min(factors) if factors else 1.0


@dataclass(frozen=True, slots=True)
class PlantData:
    version: str
    seed: int
    model: PlantModel
    state: PlantState
    commitments: tuple[Commitment, ...]
    procedures: tuple[dict[str, str], ...]
    directory: Path

    def required(self, product: str) -> float:
        return sum(c.min_quantity for c in self.commitments if c.product == product)

    def priority(self, product: str) -> int:
        levels = [c.priority for c in self.commitments if c.product == product]
        return min(levels) if levels else 3


def _read_json(path: Path) -> dict[str, Any]:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise PlanningError(f"No pude leer {path.name}: {exc}") from exc
    if payload.get("synthetic") is not True:
        raise PlanningError(f"{path.name} no está marcado como sintético.")
    return payload


def _procedures(directory: Path) -> tuple[dict[str, str], ...]:
    rows: list[dict[str, str]] = []
    for path in sorted((directory / "procedures").glob("*.md")):
        text = path.read_text(encoding="utf-8")
        meta: dict[str, str] = {}
        body = text
        if text.startswith("---"):
            _, header, body = text.split("---", 2)
            for line in header.strip().splitlines():
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip().strip('"')
        if meta.get("synthetic") != "true":
            raise PlanningError(f"{path.name} no está marcado como sintético.")
        rows.append(
            {
                "id": meta.get("id", path.stem),
                "title": meta.get("title", path.stem),
                "text": " ".join(body.split()),
            }
        )
    return tuple(rows)


def load_plant(version: str = DEFAULT_VERSION, *, root: Path | None = None) -> PlantData:
    """Carga los datos sintéticos de la planta de caña de una versión."""
    directory = (root or DATA_ROOT) / version
    if not directory.is_dir():
        raise PlanningError(
            f"No hay datos de planificación en {directory}. Genera con "
            "`uv run python scripts/generate_planning_data.py --seed 2026 --version v1`."
        )
    return _load_cached(str(directory))


@lru_cache(maxsize=4)
def _load_cached(directory_text: str) -> PlantData:
    directory = Path(directory_text)
    plant = _read_json(directory / "plant_cana.json")
    state = _read_json(directory / "state.json")
    commitments = _read_json(directory / "commitments.json")
    names = {f.name for f in PlantModel.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    model = PlantModel(**{k: plant[k] for k in names if k != "plant_id"}, plant_id="cana")
    equipment = tuple(Equipment(**item) for item in state["equipment"])
    return PlantData(
        version=str(plant["version"]),
        seed=int(plant["seed"]),
        model=model,
        state=PlantState(
            week=state["week"],
            cane_available=float(state["cane_available"]),
            cane_quality=float(state["cane_quality"]),
            equipment=equipment,
            inventories=dict(state["inventories"]),
            current_mix=dict(state["current_mix"]),
        ),
        commitments=tuple(Commitment(**item) for item in commitments["commitments"]),
        procedures=_procedures(directory),
        directory=directory,
    )


# --------------------------------------------------------------------------- escenario


class Scenario(BaseModel):
    """Escenario semanal (data-model §3). Los ``None`` toman el estado de la planta."""

    model_config = ConfigDict(extra="forbid")

    plant_id: PlantId = "cana"
    cane_available: float | None = Field(default=None, ge=0, description="t de caña disponibles.")
    cane_delta_pct: float | None = Field(
        default=None,
        ge=-50,
        le=50,
        description="Cambio % de la caña disponible (−15 = 15 % menos).",
    )
    cane_quality: float | None = Field(default=None, ge=9, le=16, description="Pol % de la caña.")
    steam_limit: float | None = Field(
        default=None, ge=0, description="Límite adicional de vapor (t/semana)."
    )
    prioritize: Literal["margin", "power"] = "margin"
    price_sugar_pct: float | None = Field(
        default=None, ge=-50, le=50, description="Cambio % del precio del azúcar (spec 026)."
    )
    price_ethanol_pct: float | None = Field(
        default=None, ge=-50, le=50, description="Cambio % del precio del etanol (spec 026)."
    )
    price_power_pct: float | None = Field(
        default=None, ge=-50, le=50, description="Cambio % del precio de la energía (spec 026)."
    )


PRICE_FIELDS = {
    "sugar": "price_sugar_pct",
    "ethanol": "price_ethanol_pct",
    "power": "price_power_pct",
}


def resolve(data: PlantData, scenario: Scenario) -> dict[str, float | None]:
    m, s = data.model, data.state
    cane = scenario.cane_available if scenario.cane_available is not None else s.cane_available
    if scenario.cane_delta_pct is not None:
        cane = cane * (1 + scenario.cane_delta_pct / 100)
    quality = scenario.cane_quality if scenario.cane_quality is not None else s.cane_quality
    boiler = m.boiler_capacity * s.factor("caldera")
    if scenario.steam_limit is not None:
        boiler = min(boiler, scenario.steam_limit)
    resolved: dict[str, float | None] = {
        "cane": max(cane, 0.0),
        "quality": quality,
        "k": quality / m.quality_ref,
        "mill_cap": m.mill_capacity * s.factor("molino"),
        "distillery_cap": m.distillery_capacity * s.factor("destileria"),
        "boiler_cap": boiler,
        "turbine_cap": m.turbine_capacity * s.factor("turbogenerador"),
        "steam_limit": scenario.steam_limit,
        "delta_pct": scenario.cane_delta_pct,
    }
    # Spec 026 (R7): solo aparecen si el escenario los cambia, así los planes vigentes no cambian.
    for product, field_name in PRICE_FIELDS.items():
        pct = getattr(scenario, field_name)
        if pct is not None:
            base = getattr(m, f"price_{product}")
            resolved[f"price_{product}"] = base * (1 + pct / 100)
    return resolved


def prices_of(data: PlantData, r: dict[str, float | None]) -> dict[str, float]:
    """Precios efectivos del escenario: el del modelo salvo que el escenario lo cambie."""
    m = data.model
    return {
        product: float(r.get(f"price_{product}") or getattr(m, f"price_{product}"))
        for product in PRICE_FIELDS
    }


def plan_id_for(data: PlantData, scenario: Scenario) -> str:
    dumped = scenario.model_dump()
    for field_name in PRICE_FIELDS.values():  # sin precios, el plan_id de la spec 025 no cambia
        if dumped.get(field_name) is None:
            dumped.pop(field_name, None)
    payload = json.dumps(
        {"scenario": dumped, "version": data.version, "week": data.state.week},
        sort_keys=True,
    )
    return "p-" + hashlib.sha256(payload.encode("utf-8")).hexdigest()[:8]


# --------------------------------------------------------------------------- balances


def products(m: PlantModel, k: float, x_s: float, x_e: float) -> tuple[float, float]:
    sugar = m.sugar_yield * k * x_s
    ethanol = m.ethanol_from_molasses * m.molasses_yield * x_s + m.ethanol_from_juice * k * x_e
    return sugar, ethanol


def margin_of(
    m: PlantModel,
    sugar: float,
    ethanol: float,
    power: float,
    cane: float,
    prices: dict[str, float] | None = None,
) -> float:
    p = prices or {"sugar": m.price_sugar, "ethanol": m.price_ethanol, "power": m.price_power}
    return p["sugar"] * sugar + p["ethanol"] * ethanol + p["power"] * power - m.cost_cane * cane


@dataclass(frozen=True, slots=True)
class SimulationResult:
    x_s: float
    x_e: float
    sugar: float
    ethanol: float
    bagasse: float
    steam_generated: float
    steam_demand: float
    power_generated: float
    power_used: float
    power_export: float
    margin: float
    violations: tuple[dict[str, Any], ...]
    data_version: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "x_s": self.x_s,
            "x_e": self.x_e,
            "sugar": self.sugar,
            "ethanol": self.ethanol,
            "bagasse": self.bagasse,
            "steam_generated": self.steam_generated,
            "steam_demand": self.steam_demand,
            "power_generated": self.power_generated,
            "power_used": self.power_used,
            "power_export": self.power_export,
            "margin": self.margin,
            "violations": list(self.violations),
            "data_version": self.data_version,
            "synthetic": True,
        }


def simulate(data: PlantData, scenario: Scenario, sugar_share: float) -> SimulationResult:
    """Balance de un reparto fijo de la caña (no optimiza); reporta violaciones sin fallar."""
    if not 0 <= sugar_share <= 1:
        raise PlanningError("sugar_share debe estar entre 0 y 1.")
    m = data.model
    r = resolve(data, scenario)
    cane = min(float(r["cane"]), float(r["mill_cap"]))  # type: ignore[arg-type]
    x_s, x_e = sugar_share * cane, (1 - sugar_share) * cane
    k = float(r["k"])  # type: ignore[arg-type]
    sugar, ethanol = products(m, k, x_s, x_e)
    bagasse = m.bagasse_yield * cane
    steam_cap = min(m.steam_per_bagasse * bagasse, float(r["boiler_cap"]))  # type: ignore[arg-type]
    demand = m.steam_sugar * x_s + m.steam_ethanol * ethanol
    power_used = m.power_use * cane
    generated = min(m.power_per_steam * steam_cap, float(r["turbine_cap"]))  # type: ignore[arg-type]
    export = generated - power_used
    violations: list[dict[str, Any]] = []
    if ethanol > float(r["distillery_cap"]) + 1e-6:  # type: ignore[arg-type]
        violations.append(_violation("capacidad de destilería", ethanol - r["distillery_cap"], "L"))
    if demand > steam_cap + 1e-6:
        violations.append(_violation("vapor disponible", demand - steam_cap, "t de vapor"))
    for product, produced in (("sugar", sugar), ("ethanol", ethanol), ("power", export)):
        required = data.required(product)
        if produced + 1e-6 < required:
            violations.append(
                _violation(
                    f"compromiso de {PRODUCT_LABELS[product]}",
                    required - produced,
                    PRODUCT_UNITS[product],
                )
            )
    return SimulationResult(
        x_s=x_s,
        x_e=x_e,
        sugar=sugar,
        ethanol=ethanol,
        bagasse=bagasse,
        steam_generated=steam_cap,
        steam_demand=demand,
        power_generated=generated,
        power_used=power_used,
        power_export=export,
        margin=margin_of(m, sugar, ethanol, max(export, 0.0), cane, prices_of(data, r)),
        violations=tuple(violations),
        data_version=data.version,
    )


def _violation(constraint: str, excess: Any, unit: str) -> dict[str, Any]:
    return {"constraint": constraint, "excess": float(excess), "unit": unit}


# --------------------------------------------------------------------------- programa lineal

# Restricciones ≤ en el orden de la matriz: (nombre, unidad del dual, ¿se reporta?)
CONSTRAINTS: tuple[tuple[str, str, bool], ...] = (
    ("caña disponible y molienda", "COP por t de caña", True),
    ("capacidad de destilería", "COP por L de etanol", True),
    ("bagazo disponible", "COP por t de bagazo", False),
    ("vapor por bagazo", "COP por t de vapor", False),
    ("capacidad de calderas", "COP por t de vapor", True),
    ("demanda de vapor", "COP por t de vapor", False),
    ("balance eléctrico", "COP por MWh", False),
    ("capacidad del turbogenerador", "COP por MWh", True),
    ("compromiso de azúcar", "COP por t de azúcar comprometida", True),
    ("compromiso de etanol", "COP por L de etanol comprometido", True),
    ("compromiso de energía", "COP por MWh comprometido", True),
)
COMMITMENT_ROWS = {"sugar": 8, "ethanol": 9, "power": 10}


def _matrix(data: PlantData, r: dict[str, float | None]) -> tuple[list[list[float]], list[float]]:
    m = data.model
    k = float(r["k"])  # type: ignore[arg-type]
    eth_s = m.ethanol_from_molasses * m.molasses_yield
    eth_e = m.ethanol_from_juice * k
    cane_cap = min(float(r["cane"]), float(r["mill_cap"]))  # type: ignore[arg-type]
    rows = [
        [1, 1, 0, 0, 0],
        [eth_s, eth_e, 0, 0, 0],
        [-m.bagasse_yield, -m.bagasse_yield, 1, 0, 0],
        [0, 0, -m.steam_per_bagasse, 1, 0],
        [0, 0, 0, 1, 0],
        [m.steam_sugar + m.steam_ethanol * eth_s, m.steam_ethanol * eth_e, 0, -1, 0],
        [m.power_use, m.power_use, 0, -m.power_per_steam, 1],
        [m.power_use, m.power_use, 0, 0, 1],
        [-m.sugar_yield * k, 0, 0, 0, 0],
        [-eth_s, -eth_e, 0, 0, 0],
        [0, 0, 0, 0, -1],
    ]
    rhs = [
        cane_cap,
        float(r["distillery_cap"]),  # type: ignore[arg-type]
        0.0,
        0.0,
        float(r["boiler_cap"]),  # type: ignore[arg-type]
        0.0,
        0.0,
        float(r["turbine_cap"]),  # type: ignore[arg-type]
        -data.required("sugar"),
        -data.required("ethanol"),
        -data.required("power"),
    ]
    return rows, rhs


def _objective(data: PlantData, r: dict[str, float | None]) -> list[float]:
    m = data.model
    k = float(r["k"])  # type: ignore[arg-type]
    p = prices_of(data, r)
    eth_s = m.ethanol_from_molasses * m.molasses_yield
    eth_e = m.ethanol_from_juice * k
    return [
        -(p["sugar"] * m.sugar_yield * k + p["ethanol"] * eth_s - m.cost_cane),
        -(p["ethanol"] * eth_e - m.cost_cane),
        0.0,
        0.0,
        -p["power"],
    ]


def _linprog(c: list[float], rows: list[list[float]], rhs: list[float]) -> Any:
    from scipy.optimize import linprog

    try:
        return linprog(
            c, A_ub=rows, b_ub=rhs, method="highs", options={"time_limit": SOLVER_TIME_LIMIT}
        )
    except (ValueError, RuntimeError) as exc:  # pragma: no cover - errores del solver
        raise PlanningError(f"El optimizador falló: {exc}") from exc


@dataclass
class PlanResult:
    plan_id: str
    status: Literal["optimal", "infeasible_relaxed"]
    scenario: dict[str, Any]
    resolved: dict[str, Any]
    mix: dict[str, float]
    products: dict[str, float]
    margin: float
    binding: dict[str, Any] | None
    sensitivity: list[dict[str, Any]]
    shortfalls: list[dict[str, Any]]
    alternatives: list[dict[str, Any]] = field(default_factory=list)
    assumptions: list[str] = field(default_factory=list)
    week: str = ""
    data_version: str = ""
    plan_card: str = ""
    assumptions_note: str = ""

    def to_dict(self, *, card: bool = True) -> dict[str, Any]:
        payload = {
            "plan_id": self.plan_id,
            "status": self.status,
            "scenario": self.scenario,
            "resolved": self.resolved,
            "mix": self.mix,
            "products": self.products,
            "margin": self.margin,
            "binding": self.binding,
            "sensitivity": self.sensitivity,
            "shortfalls": self.shortfalls,
            "alternatives": self.alternatives,
            "assumptions": self.assumptions,
            "week": self.week,
            "data_version": self.data_version,
            "synthetic": True,
        }
        if card:
            payload["plan_card"] = self.plan_card
        return payload


def _solve(
    data: PlantData, r: dict[str, float | None]
) -> tuple[Any, list[list[float]], list[float]]:
    rows, rhs = _matrix(data, r)
    result = _linprog(_objective(data, r), rows, rhs)
    return result, rows, rhs


def _elastic(data: PlantData, r: dict[str, float | None]) -> Any:
    """LP con faltantes ≥ 0 por compromiso, penalizados (R8); capacidades intactas."""
    m = data.model
    rows, rhs = _matrix(data, r)
    prices = {"sugar": m.price_sugar, "ethanol": m.price_ethanol, "power": m.price_power}
    extended = [[*row, 0.0, 0.0, 0.0] for row in rows]
    for column, product in enumerate(("sugar", "ethanol", "power")):
        extended[COMMITMENT_ROWS[product]][5 + column] = -1.0
    c = _objective(data, r) + [
        PENALTY_FACTOR * prices[p] / data.priority(p) for p in ("sugar", "ethanol", "power")
    ]
    return _linprog(c, extended, rhs)


def _products_from(data: PlantData, r: dict[str, float | None], x: Any) -> dict[str, float]:
    sugar, ethanol = products(data.model, float(r["k"]), float(x[0]), float(x[1]))  # type: ignore[arg-type]
    return {"sugar": sugar, "ethanol": ethanol, "power": float(x[4])}


def _sensitivity(result: Any, rows: list[list[float]], rhs: list[float]) -> list[dict[str, Any]]:
    marginals = getattr(getattr(result, "ineqlin", None), "marginals", None)
    slack = getattr(result, "slack", None)
    if marginals is None or slack is None:
        return []
    items: list[dict[str, Any]] = []
    for index, (name, unit, report) in enumerate(CONSTRAINTS):
        dual = -float(marginals[index])
        if not report or slack[index] > ACTIVE_SLACK * max(1.0, abs(rhs[index])) or dual <= 1e-9:
            continue
        items.append(
            {
                "constraint": name,
                "dual": dual,
                "unit": unit,
                "weight": dual * abs(rhs[index]),
                "commitment": name.startswith("compromiso"),
            }
        )
    # Primero los compromisos activos (la pregunta de negocio), luego las capacidades; dentro de
    # cada grupo, por valor económico (dual × lado derecho).
    items.sort(key=lambda item: (not item["commitment"], -item["weight"]))
    return items


def _power_first(data: PlantData, r: dict[str, float | None]) -> dict[str, Any] | None:
    """Alternativa «priorizar energía»: máxima exportación y, con ella, el mejor margen."""
    rows, rhs = _matrix(data, r)
    first = _linprog([0, 0, 0, 0, -1.0], rows, rhs)
    if first.status != 0:
        return None
    best_power = float(first.x[4])
    rows2 = [*rows, [0, 0, 0, 0, -1.0]]
    rhs2 = [*rhs, -(best_power * (1 - 1e-09))]
    second = _linprog(_objective(data, r), rows2, rhs2)
    if second.status != 0:
        return None
    return {"x": second.x, "margin": -float(second.fun)}


def optimize(scenario: Scenario, data: PlantData | None = None) -> PlanResult:
    """Plan de máximo margen (o de máxima energía) con sensibilidad y alternativas (R6–R8)."""
    data = data or load_plant()
    r = resolve(data, scenario)
    result, rows, rhs = _solve(data, r)
    status: Literal["optimal", "infeasible_relaxed"] = "optimal"
    shortfalls: list[dict[str, Any]] = []
    if result.status == 2:
        status = "infeasible_relaxed"
        result = _elastic(data, r)
        if result.status != 0:
            raise PlanningError("No fue posible optimizar ni con faltantes.")
        for column, product in enumerate(("sugar", "ethanol", "power")):
            missing = float(result.x[5 + column])
            if missing > 1e-6:
                ids = [c.id for c in data.commitments if c.product == product]
                shortfalls.append(
                    {
                        "commitment_id": ", ".join(ids),
                        "product": product,
                        "missing": missing,
                        "unit": PRODUCT_UNITS[product],
                    }
                )
    elif result.status != 0:
        raise PlanningError(f"No fue posible optimizar (estado {result.status}).")
    x = result.x
    produced = _products_from(data, r, x)
    margin = margin_of(
        data.model,
        produced["sugar"],
        produced["ethanol"],
        produced["power"],
        float(x[0] + x[1]),
        prices_of(data, r),
    )
    sensitivity = [] if status != "optimal" else _sensitivity(result, rows, rhs)
    plan = PlanResult(
        plan_id=plan_id_for(data, scenario),
        status=status,
        scenario=scenario.model_dump(exclude_none=True),
        resolved={key: value for key, value in r.items() if value is not None},
        mix={
            "x_s": float(x[0]),
            "x_e": float(x[1]),
            "b": float(x[2]),
            "v": float(x[3]),
            "g": float(x[4]),
        },
        products=produced,
        margin=margin,
        binding=sensitivity[0] if sensitivity else None,
        sensitivity=sensitivity,
        shortfalls=shortfalls,
        week=data.state.week,
        data_version=data.version,
    )
    if scenario.prioritize == "power" and status == "optimal":
        alt = _power_first(data, r)
        if alt is not None:
            power_products = _products_from(data, r, alt["x"])
            if power_products["power"] > produced["power"] + 1e-6:
                plan.alternatives.append(
                    {
                        "name": "máximo margen",
                        "margin": margin,
                        "products": produced,
                        "delta_vs_best": margin - alt["margin"],
                    }
                )
                plan.mix = {
                    "x_s": float(alt["x"][0]),
                    "x_e": float(alt["x"][1]),
                    "b": float(alt["x"][2]),
                    "v": float(alt["x"][3]),
                    "g": float(alt["x"][4]),
                }
                plan.products, plan.margin = power_products, alt["margin"]
            else:
                plan.assumptions_note = (
                    "priorizar energía no cambia el plan: la exportación ya es la máxima posible"
                )
    elif status == "optimal":
        alt = _power_first(data, r)
        if alt is not None:
            alt_products = _products_from(data, r, alt["x"])
            if alt_products["power"] > produced["power"] + 1e-6:
                plan.alternatives.append(
                    {
                        "name": "priorizar energía",
                        "margin": alt["margin"],
                        "products": alt_products,
                        "delta_vs_best": alt["margin"] - margin,
                    }
                )
    current = data.state.current_mix
    total = current.get("x_s", 0.0) + current.get("x_e", 0.0)
    if total > 0:
        sim = simulate(data, scenario, current.get("x_s", 0.0) / total)
        plan.alternatives.append(
            {
                "name": "mezcla actual",
                "margin": sim.margin,
                "products": {"sugar": sim.sugar, "ethanol": sim.ethanol, "power": sim.power_export},
                "delta_vs_best": sim.margin - plan.margin,
                "violations": [v["constraint"] for v in sim.violations],
            }
        )
    plan.assumptions = [
        *([plan.assumptions_note] if plan.assumptions_note else []),
        "modelo lineal semanal; rendimientos proporcionales a la caña y a su calidad",
        "precios, costos, capacidades y contratos sintéticos (no son datos de Manuelita)",
        "no incluye tiempos de transición ni mantenimientos no declarados en el estado",
    ]
    plan.plan_card = plan_card(plan)
    return plan


# --------------------------------------------------------------------------- consola (spec 026)

CAPACITY_AREAS = (
    ("molino", "mill_capacity", "t de caña"),
    ("destileria", "distillery_capacity", "L de etanol"),
    ("caldera", "boiler_capacity", "t de vapor"),
    ("turbogenerador", "turbine_capacity", "MWh"),
)
RANGE_FIELDS = (
    "cane_delta_pct",
    "cane_available",
    "cane_quality",
    "steam_limit",
    "price_sugar_pct",
    "price_ethanol_pct",
    "price_power_pct",
)


def scenario_ranges() -> dict[str, dict[str, float]]:
    """Límites de los controles del escenario, leídos del esquema de ``Scenario`` (sin duplicar)."""
    properties = Scenario.model_json_schema()["properties"]
    ranges: dict[str, dict[str, float]] = {}
    for name in RANGE_FIELDS:
        options = properties[name].get("anyOf", [properties[name]])
        numeric = next(o for o in options if o.get("type") == "number")
        bounds = {"min": numeric["minimum"]}
        if "maximum" in numeric:
            bounds["max"] = numeric["maximum"]
        ranges[name] = bounds
    return ranges


def snapshot(data: PlantData) -> dict[str, Any]:
    """Estado de planta para la consola web (data-model §3). Siempre sintético."""
    m, s = data.model, data.state
    capacities = []
    for area, attribute, unit in CAPACITY_AREAS:
        nominal = float(getattr(m, attribute))
        factor = s.factor(area)
        capacities.append(
            {
                "area": area,
                "nominal": nominal,
                "factor": factor,
                "effective": nominal * factor,
                "unit": unit,
            }
        )
    return {
        "week": s.week,
        "data_version": data.version,
        "seed": data.seed,
        "cane_available": s.cane_available,
        "cane_quality": s.cane_quality,
        "capacities": capacities,
        "equipment": [
            {
                "id": e.id,
                "kind": e.kind,
                "status": e.status,
                "capacity_factor": e.capacity_factor,
            }
            for e in s.equipment
        ],
        "inventories": dict(s.inventories),
        "current_mix": dict(s.current_mix),
        "commitments": [
            {
                "id": c.id,
                "product": c.product,
                "min_quantity": c.min_quantity,
                "unit": PRODUCT_UNITS.get(c.product, ""),
                "priority": c.priority,
                "counterparty": c.counterparty,
            }
            for c in data.commitments
        ],
        "prices": {"sugar": m.price_sugar, "ethanol": m.price_ethanol, "power": m.price_power},
        "ranges": scenario_ranges(),
        "synthetic": True,
        "label": SYNTHETIC_LABEL,
    }


def _share(plan: PlanResult, key: str) -> float:
    total = plan.mix["x_s"] + plan.mix["x_e"]
    return 100 * plan.mix[key] / total if total > 0 else 0.0


def _gap(plan: PlanResult, data: PlantData, product: str) -> float:
    return max(0.0, data.required(product) - plan.products.get(product, 0.0))


def compare(
    base: PlanResult, scenario: PlanResult, data: PlantData | None = None
) -> dict[str, Any]:
    """Diferencias entre dos planes por destino, producto, compromiso y margen (R8)."""
    data = data or load_plant()
    mix_delta = {
        name: {
            "tonnes": scenario.mix[key] - base.mix[key],
            "points": _share(scenario, key) - _share(base, key),
        }
        for name, key in (("sugar", "x_s"), ("ethanol", "x_e"))
    }
    products_delta = [
        {
            "product": product,
            "base": base.products.get(product, 0.0),
            "scenario": scenario.products.get(product, 0.0),
            "delta": scenario.products.get(product, 0.0) - base.products.get(product, 0.0),
            "unit": PRODUCT_UNITS[product],
        }
        for product in ("sugar", "ethanol", "power")
    ]
    commitments = []
    for product in ("sugar", "ethanol", "power"):
        ids = [c.id for c in data.commitments if c.product == product]
        if not ids:
            continue
        gap_base, gap_scenario = _gap(base, data, product), _gap(scenario, data, product)
        tolerance = 1e-6 * max(1.0, data.required(product))
        commitments.append(
            {
                "id": ", ".join(ids),
                "product": product,
                "required": data.required(product),
                "unit": PRODUCT_UNITS[product],
                "met_base": gap_base <= tolerance,
                "met_scenario": gap_scenario <= tolerance,
                "gap_base": gap_base if gap_base > tolerance else 0.0,
                "gap_scenario": gap_scenario if gap_scenario > tolerance else 0.0,
            }
        )
    return {
        "base": base.to_dict(),
        "scenario": scenario.to_dict(),
        "mix_delta": mix_delta,
        "products_delta": products_delta,
        "commitments": commitments,
        "margin_delta": scenario.margin - base.margin,
        "synthetic": True,
    }


# --------------------------------------------------------------------------- presentación


def _pct(value: float | None) -> str:
    if value is None:
        return ""
    sign = "−" if value < 0 else "+"
    return f" ({sign}{fmt(abs(value), 0 if float(value).is_integer() else 1)} %)"


def plan_card(plan: PlanResult) -> str:
    """Resumen del plan con cifras renderizadas en código (R12)."""
    r = plan.resolved
    p = plan.products
    title = "Plan recomendado" if plan.status == "optimal" else "Plan de menor incumplimiento"
    lines = [
        f"{title} · semana {plan.week} · {SYNTHETIC_LABEL} ({plan.data_version})",
        f"Escenario: caña {fmt(r['cane'])} t{_pct(r.get('delta_pct'))}, "
        f"calidad {fmt(r['quality'], 1)} pol.",
        f"• Caña a azúcar: {fmt(plan.mix['x_s'])} t · a jugo para etanol: {fmt(plan.mix['x_e'])} t",
        f"• Azúcar: {fmt(p['sugar'])} t · Etanol: {fmt(p['ethanol'])} L · "
        f"Energía exportada: {fmt(p['power'])} MWh",
        f"• Margen total: {fmt_millions(plan.margin)}",
    ]
    if plan.status != "optimal":
        for item in plan.shortfalls:
            lines.append(
                f"• No alcanza el compromiso de {PRODUCT_LABELS[item['product']]}: faltan "
                f"{fmt(item['missing'])} {item['unit']} ({item['commitment_id']})."
            )
        lines.append("• No se supuso capacidad adicional: las capacidades físicas no se relajan.")
    elif plan.sensitivity:
        limits = "; ".join(
            f"{item['constraint']} (cada unidad que se relaje suma {fmt(item['dual'])} "
            f"{item['unit']})"
            for item in plan.sensitivity[:2]
        )
        lines.append(f"• Limita: {limits}.")
    for alt in plan.alternatives:
        delta = alt["delta_vs_best"]
        sign = "−" if delta < 0 else "+"
        extra = ""
        if alt.get("violations"):
            extra = f"; incumple: {', '.join(alt['violations'])}"
        lines.append(
            f"• Alternativa «{alt['name']}»: margen {fmt_millions(alt['margin'])} "
            f"({sign}{fmt(abs(delta) / 1e6)} millones), energía {fmt(alt['products']['power'])} "
            f"MWh{extra}."
        )
    lines.append("Supuestos: " + "; ".join(plan.assumptions) + ".")
    lines.append(DECISION_PHRASE)
    lines.append(f"plan_id: {plan.plan_id}")
    return "\n".join(lines)


def simulation_card(result: SimulationResult, sugar_share: float) -> str:
    lines = [
        f"Simulación ({SYNTHETIC_LABEL}, {result.data_version}) con {fmt(sugar_share * 100)} % "
        "de la caña a azúcar:",
        f"• Caña a azúcar: {fmt(result.x_s)} t · a jugo: {fmt(result.x_e)} t",
        f"• Azúcar: {fmt(result.sugar)} t · Etanol: {fmt(result.ethanol)} L · "
        f"Energía exportada: {fmt(result.power_export)} MWh",
        f"• Vapor: demanda {fmt(result.steam_demand)} t frente a {fmt(result.steam_generated)} t "
        "disponibles",
        f"• Margen: {fmt_millions(result.margin)}",
    ]
    if result.violations:
        lines.append(
            "• Incumple: "
            + "; ".join(
                f"{v['constraint']} (exceso {fmt(v['excess'])} {v['unit']})"
                for v in result.violations
            )
        )
    else:
        lines.append("• Cumple capacidades y compromisos.")
    return "\n".join(lines)


# --------------------------------------------------------------------------- validador (R12)

NUMBER = re.compile(r"(?<![\w.,])[−-]?\d+(?:[.,]\d+)*")
SMALL_FREE = 10


def _candidates(token: str) -> set[Decimal]:
    """Interpretaciones de un número escrito en es-CO o en inglés."""
    text = token.replace("−", "-")
    options = {
        text.replace(".", "").replace(",", "."),  # es-CO: 46.750,5
        text.replace(",", ""),  # inglés: 46,750.5
    }
    values: set[Decimal] = set()
    for option in options:
        try:
            values.add(abs(Decimal(option)))
        except InvalidOperation:
            continue
    return values


def numbers_in(text: str) -> list[str]:
    cleaned = PLAN_ID.sub(" ", text)
    cleaned = re.sub(r"\b\d{4}-W\d{2}\b", " ", cleaned)
    return [match.group(0).rstrip(".,") for match in NUMBER.finditer(cleaned)]


def _grounded(value: Decimal, known: set[Decimal]) -> bool:
    if value <= SMALL_FREE:
        return True
    if value in known:
        return True
    for number in known:
        for decimals in (0, 1, 2):
            quantum = Decimal(1).scaleb(-decimals)
            if number.quantize(quantum) == value:
                return True
        if number and math.isclose(float(value), float(number), rel_tol=5e-4):
            return True
    return False


@dataclass(frozen=True, slots=True)
class AnswerCheck:
    ok: bool
    ungrounded: tuple[str, ...]
    missing_label: bool
    missing_decision: bool


def check_answer(answer: str, sources: list[str] | tuple[str, ...]) -> AnswerCheck:
    """¿Cada número de la respuesta está en las salidas de herramientas (o la pregunta)?"""
    known: set[Decimal] = set()
    for source in sources:
        for token in numbers_in(source):
            known |= _candidates(token)
    ungrounded = tuple(
        token
        for token in numbers_in(answer)
        if not any(_grounded(value, known) for value in _candidates(token))
    )
    folded = answer.lower()
    missing_label = "datos sintéticos" not in folded
    missing_decision = "el equipo de planta decide" not in folded
    return AnswerCheck(
        ok=not ungrounded and not missing_label and not missing_decision,
        ungrounded=ungrounded,
        missing_label=missing_label,
        missing_decision=missing_decision,
    )


# --------------------------------------------------------------------------- procedimientos


def search_procedures(data: PlantData, query: str, limit: int = 4) -> list[dict[str, str]]:
    """BM25 simplificado en memoria sobre los procedimientos sintéticos (R11)."""
    from ..retrieval import tokenize

    docs = [(row, tokenize(f"{row['title']} {row['text']}")) for row in data.procedures]
    if not docs:
        return []
    terms = set(tokenize(query))
    if not terms:
        return []
    n = len(docs)
    avg = sum(len(tokens) for _, tokens in docs) / n
    scores: list[tuple[float, dict[str, str]]] = []
    for row, tokens in docs:
        score = 0.0
        for term in terms:
            tf = tokens.count(term)
            if not tf:
                continue
            df = sum(1 for _, other in docs if term in other)
            idf = math.log(1 + (n - df + 0.5) / (df + 0.5))
            score += idf * tf * 2.2 / (tf + 1.2 * (0.25 + 0.75 * len(tokens) / avg))
        if score > 0:
            scores.append((score, row))
    scores.sort(key=lambda item: (-item[0], item[1]["id"]))
    return [row for _, row in scores[:limit]]
