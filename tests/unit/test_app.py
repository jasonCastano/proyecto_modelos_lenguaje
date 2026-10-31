"""Unit tests for the Streamlit app helpers."""

from __future__ import annotations

from pathlib import Path

import app as streamlit_app
from streamlit.testing.v1 import AppTest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.llm import (
    LLMConfigError,
    LLMModelMissingError,
    LLMResponseError,
    LLMUnavailableError,
)
from proyecto_modelos_lenguaje.retrieval import RetrievalError
from proyecto_modelos_lenguaje.tasks import FALLBACK_ANSWER, Citation, TaskError


def _citation():
    return Citation(
        label="U1",
        unit_id="unit_0123456789abcdef",
        title="Manuelita — Productos",
        url="https://www.manuelita.com/manuelita-productos",
        section_path=("Productos", "Azúcar"),
        page_start=3,
        page_end=None,
        time_start=None,
        time_end=None,
        authority="first_party",
        citation="Manuelita — Productos — https://www.manuelita.com/manuelita-productos",
    )


def test_citation_markdown_is_clickable() -> None:
    markdown = streamlit_app.citation_markdown(_citation())
    assert "[U1]" in markdown
    assert "Manuelita — Productos" in markdown
    assert "https://www.manuelita.com/manuelita-productos" in markdown


def test_citation_location_includes_section_and_page() -> None:
    location = streamlit_app.citation_location(_citation())
    assert "sección: Productos > Azúcar" in location
    assert "p. 3" in location


def test_demo_mode_uses_scripted_model() -> None:
    model = streamlit_app.model_for("qa", True)
    assert model is not None
    assert streamlit_app.current_model_status(True) == "demo"


def test_question_validation_rejects_empty_and_long() -> None:
    assert streamlit_app.validate_question("   ") == "Escribe una pregunta antes de enviar."
    long_question = "¿" + "a" * streamlit_app.QA_MAX_CHARS + "?"
    assert "supera 500 caracteres" in (streamlit_app.validate_question(long_question) or "")
    assert streamlit_app.validate_question("¿Qué productos ofrece Manuelita?") is None


def test_summary_pack_options() -> None:
    assert streamlit_app.SUMMARY_PACKS == ("8000", "32000")


def test_faq_status_badges() -> None:
    assert streamlit_app.faq_status_badge("ready") == ("success", "Lista")
    assert streamlit_app.faq_status_badge("review") == ("warning", "Revisar")
    assert streamlit_app.faq_status_badge("missing_evidence") == ("info", "Sin evidencia")


def test_error_messages_are_actionable() -> None:
    assert "Ollama" in streamlit_app.error_message(LLMUnavailableError("down"))
    assert "ollama pull" in streamlit_app.error_message(LLMModelMissingError("missing"))
    assert "Reintenta" in streamlit_app.error_message(LLMResponseError("empty"))
    assert "git lfs pull" in streamlit_app.error_message(RetrievalError("no data"))
    assert "config/llm.toml" in streamlit_app.error_message(LLMConfigError("bad"))
    assert "controlado" in streamlit_app.error_message(RuntimeError("unexpected"))
    error = TaskError("empty_question", "La pregunta no puede estar vacía.", task="qa")
    assert streamlit_app.error_message(error) == "La pregunta no puede estar vacía."


def test_model_status_maps_health(monkeypatch) -> None:
    monkeypatch.setattr(streamlit_app, "DEMO_ENV", False)
    monkeypatch.setattr(streamlit_app, "model_health_cached", lambda: {"ok": True})
    assert streamlit_app.current_model_status(False) == "ollama_ready"
    monkeypatch.setattr(
        streamlit_app,
        "model_health_cached",
        lambda: {"ok": False, "error": "LLMModelMissingError"},
    )
    assert streamlit_app.current_model_status(False) == "model_missing"
    monkeypatch.setattr(
        streamlit_app,
        "model_health_cached",
        lambda: {"ok": False, "error": "LLMUnavailableError"},
    )
    assert streamlit_app.current_model_status(False) == "ollama_unavailable"


def test_render_result_fallback_is_visible() -> None:
    def script() -> None:
        from app import render_result

        from proyecto_modelos_lenguaje.tasks import FALLBACK_ANSWER, TaskResult

        render_result(
            TaskResult(
                task="qa",
                status="fallback",
                answer=FALLBACK_ANSWER,
                fallback=True,
                model="scripted",
                prompt_version="1.0",
            )
        )

    at = AppTest.from_function(script).run()
    assert not at.exception
    assert any(FALLBACK_ANSWER in info.value for info in at.info)


def test_app_source_avoids_unsafe_html_and_absolute_paths() -> None:
    source = (PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    assert "unsafe_allow_html=True" not in source
    assert "C:\\" not in source
    assert "Traceback" not in source


def test_app_is_importable_without_running_streamlit() -> None:
    assert callable(streamlit_app.main)
    assert Path(streamlit_app.__file__).name == "app.py"
