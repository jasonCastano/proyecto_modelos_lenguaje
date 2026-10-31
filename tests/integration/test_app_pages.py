"""Integration tests for the four interface views: Consulta, Resumen, FAQ and Métricas."""

from __future__ import annotations

import json
from collections.abc import Callable
from pathlib import Path

from streamlit.testing.v1 import AppTest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT


def _metrics_script() -> None:
    from tests.app_page_helpers import render_metrics_view

    render_metrics_view()


def _warning_script() -> None:
    from tests.app_page_helpers import render_data_warning

    render_data_warning(True)


def _chat_script() -> None:
    from tests.app_page_helpers import render_chat_view

    render_chat_view()


def _payload_script() -> None:
    from tests.app_page_helpers import capture_session_payload

    capture_session_payload()


def _reset_script() -> None:
    from tests.app_page_helpers import reset_and_capture

    reset_and_capture()


def _run(script: Callable[[], None]) -> AppTest:
    app = AppTest.from_function(script, default_timeout=120).run(timeout=120)
    assert not app.exception
    return app


def _texts(app: AppTest, element: str) -> list[str]:
    values: list[str] = []
    for item in app.get(element):
        for attribute in ("value", "body", "label"):
            if hasattr(item, attribute):
                values.append(str(getattr(item, attribute)))
    return values


def test_metrics_view_shows_cards_and_medallion_layers() -> None:
    app = _run(_metrics_script)
    labels = [str(item.label) for item in app.get("metric")]
    for expected in ("Documentos", "Fragmentos", "Unidades", "Hechos", "Cobertura"):
        assert expected in labels
    values = [str(item.value) for item in app.get("metric")]
    assert "15.211" in values
    assert "24/24" in values
    assert "Arquitectura medallion" in " ".join(_texts(app, "markdown"))


def test_metrics_view_has_charts() -> None:
    app = _run(_metrics_script)
    charts = app.get("arrow_vega_lite_chart") + app.get("vega_lite_chart")
    assert len(charts) >= 2


def test_metrics_view_explains_each_layer() -> None:
    app = _run(_metrics_script)
    expanders = [str(item.label) for item in app.get("expander")]
    assert any("Bronce" in label for label in expanders)
    assert any("Plata" in label for label in expanders)
    assert any("Oro" in label for label in expanders)


def test_missing_corpus_shows_actionable_warning() -> None:
    app = _run(_warning_script)
    assert app.warning
    assert any("git lfs pull" in str(item.value) for item in app.warning)


def test_chat_shows_suggestions_and_input() -> None:
    app = _run(_chat_script)
    labels = [str(button.label) for button in app.get("button")]
    assert any(label == "¿Qué productos ofrece Manuelita?" for label in labels)
    assert len(app.chat_input) == 1


def test_chat_appends_user_and_assistant_turns() -> None:
    app = AppTest.from_function(_chat_script, default_timeout=120).run(timeout=120)
    app.chat_input[0].set_value("¿Qué productos ofrece Manuelita?").run(timeout=120)
    history = app.session_state["chat_history"]
    assert len(history) == 2
    assert history[0]["role"] == "user"
    assert history[0]["content"] == "¿Qué productos ofrece Manuelita?"
    assert history[1]["role"] == "assistant"


def test_session_payload_is_portable_json() -> None:
    app = _run(_payload_script)
    payload = json.loads(app.session_state["captured_payload"])
    assert payload["schema_version"] == "1.0"
    assert {"corpus", "chat", "summary", "faq"} <= set(payload)
    assert payload["chat"][0]["question"].startswith("¿Qué productos")
    assert payload["corpus"]["units"] == 15211
    text = json.dumps(payload, ensure_ascii=False)
    assert "C:\\\\" not in text
    assert "data\\\\" not in text


def test_reset_session_keeps_only_brand_flag() -> None:
    app = _run(_reset_script)
    keys = app.session_state["captured_keys"]
    assert "_pml_brand_styles" in keys
    assert "chat_history" not in keys
    assert "summary_result" not in keys


def test_four_tabs_are_declared() -> None:
    source = Path(PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert 'st.tabs(["Consulta", "Resumen", "FAQ", "Métricas"])' in source
    assert "st.navigation" not in source
