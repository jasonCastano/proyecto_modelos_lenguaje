"""Contract tests for the Metrics layout CSS, DOM hooks and audit schema."""

from __future__ import annotations

import json

from jsonschema import Draft202012Validator

from proyecto_modelos_lenguaje.brand import brand_css
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.metrics_layout import KPI_KEY, METRICS_BREAKPOINTS, METRICS_VIEW_KEY

SCHEMA_PATH = (
    PROJECT_ROOT / "specs" / "010-metrics-panel-layout" / "contracts" / "layout-audit.schema.json"
)


def _css() -> str:
    return brand_css()


def test_css_scopes_the_grid_to_the_metrics_container() -> None:
    css = _css()
    assert f'.st-key-{KPI_KEY} [data-testid="stHorizontalBlock"]' in css
    assert f'.st-key-{KPI_KEY} [data-testid="stColumn"]' in css
    assert "minmax(0, 1fr)" in css
    assert "min-width: 0" in css


def test_css_declares_the_three_breakpoints() -> None:
    css = _css()
    assert "grid-template-columns: repeat(4, minmax(0, 1fr));" in css
    compact = METRICS_BREAKPOINTS["compact"]
    wide = METRICS_BREAKPOINTS["wide"]
    assert f"@media (max-width: {compact}px)" in css
    assert f"@media (max-width: {wide - 1}px)" in css
    assert "grid-template-columns: repeat(2, minmax(0, 1fr));" in css
    assert "grid-template-columns: minmax(0, 1fr);" in css


def test_css_wraps_values_without_ellipsis() -> None:
    css = _css()
    assert "stMetricValue" in css
    assert "stMetricLabel" in css
    assert "white-space: normal" in css
    assert "overflow-wrap: anywhere" in css
    assert "text-overflow: clip" in css
    assert "font-variant-numeric: tabular-nums" in css


def test_css_preserves_material_icons() -> None:
    css = _css()
    assert '[data-testid="stIconMaterial"]' in css
    assert '"Material Symbols Rounded"' in css


def test_css_keeps_charts_separated() -> None:
    css = _css()
    assert "stVegaLiteChart" in css
    assert "min-height: 260px" in css
    assert f".st-key-{METRICS_VIEW_KEY}" in css


def test_app_uses_the_container_keys() -> None:
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "st.container(key=KPI_KEY)" in source
    assert "st.container(key=METRICS_VIEW_KEY)" in source
    assert "unsafe_allow_html=True" not in source


def test_audit_schema_accepts_a_minimal_report() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    sample = {
        "schema_version": "1.0",
        "generated_at": "2026-10-31T12:00:00Z",
        "app_url": "http://localhost:8501",
        "browser": "chrome 1.64",
        "viewports": [
            {
                "name": "escritorio",
                "width": 1440,
                "height": 900,
                "zoom": 1.0,
                "columns": 4,
                "horizontal_scroll": False,
                "screenshots": ["escritorio.png"],
                "passed": True,
            }
        ],
        "data_states": [
            {
                "state": "complete",
                "warning_visible": False,
                "warning_separate": True,
                "passed": True,
            }
        ],
        "findings": [],
        "passed": True,
    }
    Draft202012Validator(schema).validate(sample)
