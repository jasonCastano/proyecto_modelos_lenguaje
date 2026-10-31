"""Optional integration test against a real Ollama model (T045).

Skipped by default: set ``OLLAMA_RUN_INTEGRATION=1`` and keep Ollama running with the configured
model downloaded.
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.llm import LLMConfigError, build_chat_model, load_llm_config
from proyecto_modelos_lenguaje.retrieval import load_gold_units
from proyecto_modelos_lenguaje.tasks import answer_question, generate_faq, summarize_corpus

RUN_INTEGRATION = os.getenv("OLLAMA_RUN_INTEGRATION") == "1"
GOLD_DIR = Path(__file__).resolve().parents[2] / "data" / "gold"
LFS_POINTER = "version https://git-lfs"


def _gold_available() -> bool:
    path = GOLD_DIR / "knowledge_units.jsonl"
    if not path.is_file():
        return False
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        return not handle.read(64).startswith(LFS_POINTER)


pytestmark = [
    pytest.mark.skipif(
        not RUN_INTEGRATION,
        reason="define OLLAMA_RUN_INTEGRATION=1 para ejecutarla",
    ),
    pytest.mark.skipif(
        not _gold_available(),
        reason="data/gold no está materializado: ejecuta `git lfs pull` o el pipeline de oro",
    ),
]


def _model():
    try:
        config = load_llm_config()
    except LLMConfigError as exc:  # pragma: no cover - depende del entorno local
        pytest.skip(f"configuración del modelo no disponible: {exc}")
    return build_chat_model(config)


def test_qa_summary_and_faq_with_the_real_model() -> None:
    units = load_gold_units(GOLD_DIR)
    model = _model()

    qa_result = answer_question("¿Qué productos ofrece Manuelita?", model=model, units=units)
    assert qa_result.status in {"ok", "fallback"}
    assert qa_result.latency_seconds >= 0
    if qa_result.status == "ok":
        assert qa_result.citations

    summary_result = summarize_corpus(model=model, units=units)
    assert summary_result.status in {"ok", "fallback", "error"}
    assert summary_result.prompt_version

    faq_items = generate_faq(limit=10, model=model, units=units)
    assert 10 <= len(faq_items) <= 20
    assert all(item.status in {"ready", "review", "missing_evidence"} for item in faq_items)
