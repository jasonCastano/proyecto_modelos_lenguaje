"""Minimal Streamlit app used to audit the Metrics tab data states.

Run with ``streamlit run tests/visual/metrics_fixture_app.py`` and set
``PML_METRICS_STATE`` to ``complete``, ``incomplete`` or ``unknown``.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as streamlit_app  # noqa: E402
from tests.app_page_helpers import sample_metrics  # noqa: E402

STATE = os.getenv("PML_METRICS_STATE", "complete").strip().lower()
if STATE not in {"complete", "incomplete", "unknown"}:
    STATE = "complete"

st.set_page_config(page_title="Auditoría de métricas", page_icon="🌱", layout="wide")
streamlit_app.inject_brand_styles()
detail = None if STATE == "complete" else "Falta git lfs pull"
metrics = sample_metrics(data_status=STATE, detail=detail)
streamlit_app._data_warning(metrics)
streamlit_app.render_metrics(metrics)
