"""Spec 026 (data-model §3): vista del estado de planta para la consola."""

from __future__ import annotations

from proyecto_modelos_lenguaje.agent.planning import Scenario, load_plant, snapshot


def test_snapshot_has_capacities_commitments_prices_and_label() -> None:
    data = load_plant()
    view = snapshot(data)
    assert view["synthetic"] is True
    assert view["week"] == data.state.week
    assert view["data_version"] == data.version
    areas = {c["area"] for c in view["capacities"]}
    assert areas == {"molino", "destileria", "caldera", "turbogenerador"}
    for cap in view["capacities"]:
        assert {"nominal", "factor", "effective", "unit"} <= set(cap)
        assert abs(cap["effective"] - cap["nominal"] * cap["factor"]) < 1e-6
    assert len(view["commitments"]) == len(data.commitments)
    assert all(c["unit"] for c in view["commitments"])
    assert set(view["prices"]) == {"sugar", "ethanol", "power"}


def test_snapshot_ranges_come_from_the_scenario_schema() -> None:
    view = snapshot(load_plant())
    schema = Scenario.model_json_schema()["properties"]
    ranges = view["ranges"]
    assert ranges["cane_delta_pct"] == {"min": -50, "max": 50}
    for name, bounds in ranges.items():
        options = schema[name].get("anyOf", [schema[name]])
        numeric = next(o for o in options if o.get("type") == "number")
        assert bounds["min"] == numeric.get("minimum")
        assert bounds.get("max") == numeric.get("maximum")
