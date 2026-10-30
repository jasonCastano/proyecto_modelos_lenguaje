"""Optional integration test against a real Ollama server."""

from __future__ import annotations

import os

import pytest

from proyecto_modelos_lenguaje.llm import health_check, load_llm_config

pytestmark = pytest.mark.skipif(
    os.getenv("OLLAMA_RUN_INTEGRATION") != "1",
    reason="Set OLLAMA_RUN_INTEGRATION=1 with a local Ollama server to run this test.",
)


def test_ollama_model_is_available() -> None:
    result = health_check(load_llm_config())
    assert result["ok"] is True
    assert result["model"]
