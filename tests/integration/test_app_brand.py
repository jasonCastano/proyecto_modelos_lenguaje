"""Integration tests for the brand identity inside the Streamlit app (T012, T018, T024, T027)."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT

APP_PATH = PROJECT_ROOT / "app.py"


def _run_app(monkeypatch: pytest.MonkeyPatch) -> AppTest:
    monkeypatch.setenv("PML_DEMO", "1")
    return AppTest.from_file(str(APP_PATH), default_timeout=120).run()


def _html_values(app: AppTest) -> list[str]:
    return [str(element.value) for element in app.get("html")]


def test_app_runs_and_injects_the_stylesheet(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run_app(monkeypatch)
    assert not app.exception
    values = _html_values(app)
    assert any("<style>" in value and "--pml-forest" in value for value in values)


def test_header_shows_the_institutional_signature(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run_app(monkeypatch)
    header = next(value for value in _html_values(app) if "pml-header" in value)
    assert "Grupo Manuelita" in header
    assert "Ingenio Manuelita" in header
    assert "RAG Ingenio Manuelita" in header
    assert "progreso y bienestar" in header
    assert "No afiliado" in header


def test_status_bar_shows_data_model_and_demo(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run_app(monkeypatch)
    bar = next(value for value in _html_values(app) if "pml-status" in value)
    assert "Datos" in bar
    assert "Modo demo" in bar
    assert "is-demo" in bar


def test_footer_declares_academic_scope(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run_app(monkeypatch)
    footer = next(value for value in _html_values(app) if "pml-footer" in value)
    assert "No afiliado" in footer
    assert "titulares" in footer


def test_four_tabs_are_preserved(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run_app(monkeypatch)
    assert [tab.label for tab in app.tabs] == ["Consulta", "Resumen", "FAQ", "Métricas"]


def test_citations_render_as_cards(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PML_DEMO", "1")

    def script() -> None:
        from app import render_citations

        from proyecto_modelos_lenguaje.tasks import Citation

        render_citations(
            [
                Citation(
                    label="U1",
                    unit_id="unit_0123456789abcdef",
                    title="Manuelita — Productos",
                    url="https://www.manuelita.com/manuelita-productos",
                    section_path=("Productos",),
                    page_start=None,
                    page_end=None,
                    time_start=None,
                    time_end=None,
                    authority="first_party",
                    citation="Manuelita — Productos",
                )
            ]
        )

    app = AppTest.from_function(script).run()
    assert not app.exception
    markup = next(str(element.value) for element in app.get("html"))
    assert "pml-source" in markup
    assert "[U1]" in markup
    assert "https://www.manuelita.com/manuelita-productos" in markup


def test_status_items_cover_data_and_model(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PML_DEMO", "1")
    import app as streamlit_app

    class _Complete:
        data_status = "complete"

    class _Incomplete:
        data_status = "incomplete"

    complete = streamlit_app.status_items(_Complete(), "demo")
    assert complete[0][0] == "ok"
    assert "demo" in [item[0] for item in complete]

    incomplete = streamlit_app.status_items(_Incomplete(), "provider_ready")
    assert incomplete[0][0] == "error"
    assert incomplete[1] == ("ok", "✓", "Proveedor listo")
    assert all(len(item) == 3 and item[1] and item[2] for item in complete + incomplete)


def test_app_source_keeps_the_security_rule(monkeypatch: pytest.MonkeyPatch) -> None:
    source = Path(APP_PATH).read_text(encoding="utf-8")
    assert "unsafe_allow_html" not in source
    assert "C:\\" not in source
