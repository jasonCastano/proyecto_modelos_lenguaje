"""Optional Playwright audit for the Metrics tab.

These tests only run when ``PML_VISUAL_AUDIT=1`` is set and a Streamlit app is
available at ``PML_VISUAL_AUDIT_URL``. The default suite never needs a browser.
"""

from __future__ import annotations

import os
import subprocess
import sys

import pytest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.metrics_layout import VIEWPORTS

pytest.importorskip("playwright")
pytestmark = pytest.mark.skipif(
    os.getenv("PML_VISUAL_AUDIT") != "1",
    reason="Visual audit disabled; set PML_VISUAL_AUDIT=1 and start the app.",
)


@pytest.mark.parametrize("profile", VIEWPORTS, ids=[profile.name for profile in VIEWPORTS])
def test_metrics_viewport_passes(profile, tmp_path) -> None:
    url = os.getenv("PML_VISUAL_AUDIT_URL", "http://localhost:8501")
    browser = os.getenv("PML_VISUAL_BROWSER", "auto")
    result = subprocess.run(
        [
            sys.executable,
            str(PROJECT_ROOT / "scripts" / "audit_metrics_layout.py"),
            "--url",
            url,
            "--output",
            str(tmp_path),
            "--profile",
            profile.name,
            "--browser",
            browser,
        ],
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
