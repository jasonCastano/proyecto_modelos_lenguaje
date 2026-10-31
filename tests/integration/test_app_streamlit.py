"""Integration tests for the Streamlit app in demo mode."""

from __future__ import annotations

import re

import pytest
import streamlit as st
from streamlit.testing.v1 import AppTest

import proyecto_modelos_lenguaje.app_metrics as app_metrics
import proyecto_modelos_lenguaje.llm as llm
from proyecto_modelos_lenguaje.app_metrics import AppMetrics, load_app_metrics
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

pytestmark = pytest.mark.skipif(
    load_app_metrics().data_status != "complete",
    reason="Gold data is not materialized (run `git lfs pull`).",
)


def _app(monkeypatch, *, demo: bool = True) -> AppTest:
    st.cache_data.clear()
    if demo:
        monkeypatch.setenv("PML_DEMO", "1")
    else:
        monkeypatch.delenv("PML_DEMO", raising=False)
    return AppTest.from_file(PROJECT_ROOT / "app.py").run(timeout=60)


def test_app_shell_has_four_tabs(monkeypatch) -> None:
    at = _app(monkeypatch)
    assert not at.exception
    assert [tab.label for tab in at.tabs] == ["Consulta", "Resumen", "FAQ", "Métricas"]
    assert at.sidebar.toggle[0].value is True
    assert any("Panel" in header.value for header in at.sidebar.header)


def test_qa_demo_mode_returns_citation_or_fallback(monkeypatch) -> None:
    at = _app(monkeypatch)
    at.chat_input[0].set_value("¿Qué productos ofrece Manuelita?").run(timeout=60)
    assert not at.exception
    text = "\n".join(item.value for item in at.markdown)
    assert "[U1]" in text or "No hay evidencia suficiente" in text
    history = at.session_state["chat_history"]
    assert len(history) == 2
    assert history[1]["role"] == "assistant"
    assert history[1]["result"] is not None or history[1]["error"] is not None


def test_summary_and_faq_demo_mode(monkeypatch) -> None:
    at = _app(monkeypatch)
    summary_button = next(button for button in at.button if button.label == "Generar resumen")
    summary_button.click()
    at.run(timeout=60)
    assert not at.exception
    summary_text = "\n".join(item.value for item in at.markdown)
    assert "Fuentes" in summary_text
    citations = set(re.findall(r"\[U\d+\]", summary_text))
    assert 8 <= len(citations) <= 12

    faq_button = next(button for button in at.button if button.label == "Generar FAQ")
    faq_button.click()
    at.run(timeout=60)
    assert not at.exception
    assert 10 <= len(at.expander) <= 20
    questions = [expander.label for expander in at.expander]
    assert len(questions) == len(set(questions))


def test_empty_question_is_rejected(monkeypatch) -> None:
    at = _app(monkeypatch)
    at.chat_input[0].set_value("   ").run(timeout=60)
    assert not at.exception
    assert any("Escribe una pregunta" in warning.value for warning in at.warning)


def test_app_handles_incomplete_data(monkeypatch) -> None:
    incomplete = AppMetrics(
        active_artifacts=0,
        canonical_documents=0,
        aliases=0,
        chunks=0,
        units=0,
        facts=0,
        entities=0,
        conflicts=0,
        coverage_covered=0,
        coverage_total=24,
        silver_tokens=0,
        gold_tokens=0,
        skipped=0,
        omissions=0,
        silver_run="unknown",
        gold_run="unknown",
        data_status="incomplete",
        detail="falta knowledge_units.jsonl",
    )
    monkeypatch.setattr(app_metrics, "load_app_metrics", lambda **_kwargs: incomplete)
    at = _app(monkeypatch)
    assert not at.exception
    assert any("Los datos de oro no están completos" in warning.value for warning in at.warning)


def test_app_reports_unavailable_model(monkeypatch) -> None:
    def unavailable(_config):
        raise llm.LLMUnavailableError("connection refused")

    monkeypatch.setattr(llm, "health_check", unavailable)
    at = _app(monkeypatch, demo=False)
    assert not at.exception
    assert any("Proveedor no disponible" in warning.value for warning in at.sidebar.warning)
