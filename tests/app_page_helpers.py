"""Helpers so AppTest can render a medallion page in a fresh script context."""

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


def render_page(page: str, *, incomplete: bool = False) -> None:
    """Render one medallion page outside the navigation router."""
    import app as streamlit_app

    metrics = sample_metrics(
        data_status="incomplete" if incomplete else "complete",
        detail="Falta git lfs pull" if incomplete else None,
    )
    getattr(streamlit_app, f"render_{page}_page")(metrics)


def render_page_from_env() -> None:
    """Render the page selected by ``PML_TEST_PAGE`` (used from AppTest scripts)."""
    import os

    render_page(
        os.environ["PML_TEST_PAGE"],
        incomplete=os.environ.get("PML_TEST_INCOMPLETE") == "1",
    )
