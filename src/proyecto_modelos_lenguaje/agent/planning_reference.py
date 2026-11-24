"""Óptimo de referencia por búsqueda exhaustiva en malla (spec 025, R9, FR-020).

Valida el optimizador del agente con un método que **no comparte solver ni formulación matricial**:
recorre una malla de ``(x_s, x_e)`` y, para cada par, resuelve ``b``, ``v`` y ``g`` en forma
cerrada (se quema todo el bagazo que admite la caldera y se exporta todo lo que permite el
turbogenerador, porque la energía tiene precio positivo). No importa ``scipy`` ni
``planning.optimize``; solo lee los datos y el escenario.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .planning import PlantData, Scenario, resolve

DEFAULT_POINTS = 2001
CHUNK_ROWS = 128


@dataclass(frozen=True, slots=True)
class Reference:
    feasible: bool
    margin: float | None
    x_s: float | None
    x_e: float | None
    grid_step: float  # t de caña entre puntos de la malla


def reference_optimum(
    data: PlantData, scenario: Scenario, *, points: int = DEFAULT_POINTS
) -> Reference:
    m = data.model
    r = resolve(data, scenario)
    k = float(r["k"])  # type: ignore[arg-type]
    cane_cap = min(float(r["cane"]), float(r["mill_cap"]))  # type: ignore[arg-type]
    boiler = float(r["boiler_cap"])  # type: ignore[arg-type]
    turbine = float(r["turbine_cap"])  # type: ignore[arg-type]
    distillery = float(r["distillery_cap"])  # type: ignore[arg-type]
    need_s, need_e, need_g = (data.required(p) for p in ("sugar", "ethanol", "power"))
    axis = np.linspace(0.0, cane_cap, points)
    step = float(axis[1] - axis[0]) if points > 1 else 0.0
    best = (-np.inf, None, None)
    for start in range(0, points, CHUNK_ROWS):
        x_s = axis[start : start + CHUNK_ROWS][:, None]
        x_e = axis[None, :]
        total = x_s + x_e
        sugar = m.sugar_yield * k * x_s
        ethanol = m.ethanol_from_molasses * m.molasses_yield * x_s + m.ethanol_from_juice * k * x_e
        steam = np.minimum(m.steam_per_bagasse * m.bagasse_yield * total, boiler)
        demand = m.steam_sugar * x_s + m.steam_ethanol * ethanol
        power = np.minimum(m.power_per_steam * steam, turbine) - m.power_use * total
        feasible = (
            (total <= cane_cap * (1 + 1e-12))
            & (ethanol <= distillery + 1e-9)
            & (demand <= steam + 1e-9)
            & (power >= -1e-9)
            & (sugar >= need_s - 1e-9)
            & (ethanol >= need_e - 1e-9)
            & (power >= need_g - 1e-9)
        )
        if not feasible.any():
            continue
        margin = (
            m.price_sugar * sugar
            + m.price_ethanol * ethanol
            + m.price_power * power
            - m.cost_cane * total
        )
        margin = np.where(feasible, margin, -np.inf)
        index = np.unravel_index(int(np.argmax(margin)), margin.shape)
        value = float(margin[index])
        if value > best[0]:
            best = (value, float(x_s[index[0], 0]), float(x_e[0, index[1]]))
    if best[1] is None:
        return Reference(False, None, None, None, step)
    return Reference(True, best[0], best[1], best[2], step)
