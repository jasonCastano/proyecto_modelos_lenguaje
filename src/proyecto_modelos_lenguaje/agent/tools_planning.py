"""Herramientas de planificación industrial del catálogo (spec 025, números 21–25).

Contrato: ``specs/025-agentes-manuelita-idea7/contracts/planning-tools.md``. Ruta ``planning``,
perfil ``planificador``. Toda salida empieza con la etiqueta de datos sintéticos y las cifras salen
de ``planning.py`` (simulador y programación lineal), nunca del modelo de lenguaje.

``simulate_production_scenario`` y ``optimize_production_plan`` no van al MCP
(``mcp_allowed=False``):
en el modo degradado no se planifica (constitución, regla 20; research R16).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .catalog import ToolArgsError, ToolContext, ToolSpec
from .guard import neutralize
from .planning import (
    PRODUCT_LABELS,
    PRODUCT_UNITS,
    PlanningError,
    Scenario,
    fmt,
    load_plant,
    optimize,
    search_procedures,
    simulate,
    simulation_card,
)

PLANNING = frozenset({"planning"})


def _prefix(version: str) -> str:
    return f"[Datos sintéticos de demostración · {version}]"


def _data():
    try:
        return load_plant()
    except PlanningError as exc:
        raise ToolArgsError(str(exc)) from exc


# --------------------------------------------------------------------------- 21 estado


class GetPlantStateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: Literal["cana"] = Field(default="cana", description="Planta: cana.")


def get_plant_state_impl(ctx: ToolContext, args: GetPlantStateArgs) -> str:
    ctx.trace.calls += 1
    data = _data()
    m, s = data.model, data.state
    lines = [
        f"{_prefix(data.version)} Estado de la planta de caña · semana {s.week}",
        f"- Caña disponible: {fmt(s.cane_available)} t · calidad {fmt(s.cane_quality, 1)} pol",
        f"- Capacidades por semana: molienda {fmt(m.mill_capacity)} t; destilería "
        f"{fmt(m.distillery_capacity)} L; calderas {fmt(m.boiler_capacity)} t de vapor; "
        f"turbogenerador {fmt(m.turbine_capacity)} MWh",
        "- Equipos: "
        + "; ".join(f"{e.id} {e.status} (factor {fmt(e.capacity_factor, 2)})" for e in s.equipment),
        f"- Inventarios: azúcar {fmt(s.inventories.get('sugar_t', 0))} t; etanol "
        f"{fmt(s.inventories.get('ethanol_l', 0))} L; "
        f"miel {fmt(s.inventories.get('molasses_t', 0))} t",
        f"- Mezcla actual: {fmt(s.current_mix.get('x_s', 0))} t de caña a azúcar y "
        f"{fmt(s.current_mix.get('x_e', 0))} t a jugo para etanol",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- 22 compromisos


class GetCommitmentsArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: Literal["cana"] = Field(default="cana", description="Planta: cana.")
    product: Literal["sugar", "ethanol", "power"] | None = Field(
        default=None, description="Filtra por producto: sugar, ethanol o power."
    )


def get_commitments_impl(ctx: ToolContext, args: GetCommitmentsArgs) -> str:
    ctx.trace.calls += 1
    data = _data()
    rows = [c for c in data.commitments if args.product in (None, c.product)]
    if not rows:
        return f"{_prefix(data.version)} Sin resultados: no hay compromisos de ese producto."
    lines = [f"{_prefix(data.version)} Compromisos de la semana {data.state.week}:"]
    lines += [
        f"- {c.id}: {PRODUCT_LABELS[c.product]} mínimo {fmt(c.min_quantity)} "
        f"{PRODUCT_UNITS[c.product]} · prioridad {c.priority} · {c.counterparty}"
        for c in rows
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- 23 procedimientos


class SearchProceduresArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=3, max_length=200, description="Qué restricción o regla buscar.")


def search_procedures_impl(ctx: ToolContext, args: SearchProceduresArgs) -> str:
    ctx.trace.calls += 1
    data = _data()
    found = search_procedures(data, args.query)
    if not found:
        return f"{_prefix(data.version)} Sin resultados en los procedimientos operativos."
    lines = [f"{_prefix(data.version)} Procedimientos operativos (citar como [S#]):"]
    for row in found:
        label = f"S{len(ctx.trace.procedures) + 1}"
        text = neutralize(row["text"]).text
        ctx.trace.procedures.append({"label": label, "id": row["id"], "title": row["title"]})
        lines.append(f"[{label}] {row['id']} · {row['title']}: {text}")
    return "\n".join(lines)


# --------------------------------------------------------------------------- 24 simulación


class SimulateScenarioArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: Literal["cana"] = "cana"
    cane_available: float | None = Field(default=None, ge=0, description="t de caña disponibles.")
    cane_delta_pct: float | None = Field(
        default=None, ge=-50, le=50, description="Cambio % de la caña (−15 = 15 % menos)."
    )
    cane_quality: float | None = Field(default=None, ge=9, le=16, description="Pol % de la caña.")
    steam_limit: float | None = Field(default=None, ge=0, description="Límite de vapor (t).")
    sugar_share: float = Field(ge=0, le=1, description="Fracción de la caña a azúcar (0 a 1).")


def simulate_impl(ctx: ToolContext, args: SimulateScenarioArgs) -> str:
    ctx.trace.calls += 1
    data = _data()
    scenario = Scenario(**args.model_dump(exclude={"sugar_share"}))
    try:
        result = simulate(data, scenario, args.sugar_share)
    except PlanningError as exc:
        raise ToolArgsError(str(exc)) from exc
    return f"{_prefix(data.version)} {simulation_card(result, args.sugar_share)}"


# --------------------------------------------------------------------------- 25 optimización


class OptimizePlanArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    plant_id: Literal["cana"] = "cana"
    cane_available: float | None = Field(default=None, ge=0, description="t de caña disponibles.")
    cane_delta_pct: float | None = Field(
        default=None, ge=-50, le=50, description="Cambio % de la caña (−15 = 15 % menos)."
    )
    cane_quality: float | None = Field(default=None, ge=9, le=16, description="Pol % de la caña.")
    steam_limit: float | None = Field(default=None, ge=0, description="Límite de vapor (t).")
    prioritize: Literal["margin", "power"] = Field(
        default="margin", description="margin (máximo margen) o power (máxima energía)."
    )


def optimize_impl(ctx: ToolContext, args: OptimizePlanArgs) -> str:
    ctx.trace.calls += 1
    data = _data()
    try:
        plan = optimize(Scenario(**args.model_dump()), data)
    except PlanningError as exc:
        raise ToolArgsError(f"no fue posible optimizar: {exc}") from exc
    ctx.trace.plans.append(plan.to_dict())
    return f"{_prefix(data.version)}\n{plan.plan_card}"


SPECS: tuple[ToolSpec, ...] = (
    ToolSpec(
        21,
        "get_plant_state",
        "Estado SINTÉTICO de la planta de caña: caña disponible y calidad, capacidades, equipos, "
        "inventarios y mezcla actual. Solo para planificación (datos de demostración).",
        GetPlantStateArgs,
        "read",
        PLANNING,
        "data/synthetic/planificacion/<v>/state.json + plant_cana.json",
        get_plant_state_impl,
    ),
    ToolSpec(
        22,
        "get_commitments",
        "Compromisos SINTÉTICOS de la semana (azúcar, etanol y energía) con cantidad mínima, "
        "prioridad y contraparte genérica. Solo para planificación.",
        GetCommitmentsArgs,
        "read",
        PLANNING,
        "data/synthetic/planificacion/<v>/commitments.json",
        get_commitments_impl,
    ),
    ToolSpec(
        23,
        "search_operating_procedures",
        "Busca en los procedimientos operativos SINTÉTICOS de la planta (prioridades, vapor, "
        "molienda, aprobación de planes) y devuelve fragmentos citables [S#].",
        SearchProceduresArgs,
        "read",
        PLANNING,
        "data/synthetic/planificacion/<v>/procedures/*.md (BM25 en memoria)",
        search_procedures_impl,
    ),
    ToolSpec(
        24,
        "simulate_production_scenario",
        "Simula un reparto fijo de la caña entre azúcar y etanol: balances de azúcar, etanol, "
        "vapor y energía, margen y restricciones incumplidas. Datos sintéticos; cifras en código.",
        SimulateScenarioArgs,
        "read",
        PLANNING,
        "simulador lineal (agent/planning.py)",
        simulate_impl,
        mcp_allowed=False,
    ),
    ToolSpec(
        25,
        "optimize_production_plan",
        "Optimiza el programa de producción de la semana (programación lineal): plan de máximo "
        "margen, restricción que limita, alternativas y plan_id. Datos sintéticos; cifras en "
        "código.",
        OptimizePlanArgs,
        "read",
        PLANNING,
        "scipy.optimize.linprog (HiGHS) sobre agent/planning.py",
        optimize_impl,
        mcp_allowed=False,
    ),
)
