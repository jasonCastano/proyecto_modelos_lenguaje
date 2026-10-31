"""Helpers so AppTest can render the app views in a fresh script context."""

from __future__ import annotations

from typing import Any

from proyecto_modelos_lenguaje.app_metrics import AppMetrics


def sample_metrics(**overrides: Any) -> AppMetrics:
    """Deterministic metrics that look like the real corpus."""
    payload: dict[str, Any] = {
        "active_artifacts": 557,
        "canonical_documents": 226,
        "aliases": 41,
        "chunks": 3810,
        "units": 15211,
        "facts": 860,
        "entities": 120,
        "conflicts": 14,
        "coverage_covered": 24,
        "coverage_total": 24,
        "silver_tokens": 1_900_000,
        "gold_tokens": 980_000,
        "skipped": 26347,
        "omissions": 87,
        "silver_run": "2026-10-silver-01",
        "gold_run": "2026-10-gold-01",
        "data_status": "complete",
        "detail": None,
    }
    payload.update(overrides)
    return AppMetrics(**payload)


def render_metrics_view() -> None:
    """Render the Métricas tab with deterministic data."""
    import app as streamlit_app

    streamlit_app.render_metrics(sample_metrics())


def render_data_warning(incomplete: bool) -> None:
    """Render the corpus warning used above the tabs."""
    import app as streamlit_app

    metrics = sample_metrics(
        data_status="incomplete" if incomplete else "complete",
        detail="Falta git lfs pull" if incomplete else None,
    )
    streamlit_app._data_warning(metrics)


def render_chat_view() -> None:
    """Render the Consulta tab (chat) with the demo model."""
    import app as streamlit_app
    import streamlit as st

    for key, value in {
        "chat_history": [],
        "pending_question": "",
        "last_question": "",
        "last_result": None,
        "qa_result": None,
        "qa_error": None,
    }.items():
        st.session_state.setdefault(key, value)
    streamlit_app.render_chat(demo_mode=True, data_ready=True)


def capture_session_payload() -> None:
    """Serialise the session (including a failed turn) into session state."""
    import app as streamlit_app
    import streamlit as st

    st.session_state["chat_history"] = [
        {"role": "user", "content": "¿Qué productos ofrece Manuelita?"},
        {"role": "assistant", "result": None, "error": RuntimeError("boom")},
    ]
    st.session_state["captured_payload"] = streamlit_app._session_payload(sample_metrics())


def reset_and_capture() -> None:
    """Clear the session and report which keys survived."""
    import app as streamlit_app
    import streamlit as st

    st.session_state["chat_history"] = [{"role": "user", "content": "hola"}]
    st.session_state["summary_result"] = None
    st.session_state["_pml_brand_styles"] = True
    streamlit_app._reset_session()
    st.session_state["captured_keys"] = sorted(st.session_state.keys())
