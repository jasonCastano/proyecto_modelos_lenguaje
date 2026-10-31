"""API tests for the Manuelita web experience."""

from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

import proyecto_modelos_lenguaje.api as api
from proyecto_modelos_lenguaje.api_models import (
    CorpusMetric,
    EvidenceLink,
    ShowcaseResponse,
    ShowcaseSection,
)
from proyecto_modelos_lenguaje.llm import load_llm_config
from proyecto_modelos_lenguaje.tasks import Citation as TaskCitation
from proyecto_modelos_lenguaje.tasks import FAQItem, TaskError, TaskResult

client = TestClient(api.app)


def _citation() -> TaskCitation:
    return TaskCitation(
        label="U1",
        unit_id="unit-1",
        title="Manuelita — Productos",
        url="https://www.manuelita.com/manuelita-productos",
        section_path=("Productos",),
        page_start=3,
        page_end=None,
        time_start=None,
        time_end=None,
        authority="first_party",
        citation="Manuelita — Productos",
    )


def _ok_result() -> TaskResult:
    return TaskResult(
        task="qa",
        status="ok",
        answer="Manuelita ofrece azúcar y derivados.",
        citations=(_citation(),),
        used_unit_ids=("unit-1",),
        model="deepseek-flash",
        prompt_version="1.0",
        latency_seconds=0.5,
        input_tokens=10,
        output_tokens=5,
    )


def _patch_model(monkeypatch) -> None:
    monkeypatch.setattr(api, "_model", lambda *_args: object())
    monkeypatch.setattr(api, "_units", lambda: ())
    monkeypatch.setattr(api, "_entity_index", lambda: None)
    monkeypatch.setattr(api, "_seeds", lambda: ())
    monkeypatch.setattr(api, "_cost", lambda *_args: None)


def test_root_is_served() -> None:
    response = client.get("/")
    assert response.status_code == 200
    assert response.text


def test_health_without_key(monkeypatch) -> None:
    config = replace(load_llm_config(), api_key_env="PML_TEST_MISSING_KEY")
    monkeypatch.delenv("PML_TEST_MISSING_KEY", raising=False)
    monkeypatch.setattr(api, "load_llm_config", lambda: config)
    payload = client.get("/api/health").json()
    assert payload["configured"] is False
    assert payload["ok"] is False
    assert payload["demo_available"] is True


def test_health_with_probe(monkeypatch) -> None:
    config = replace(load_llm_config(), api_key_env="PML_TEST_KEY")
    monkeypatch.setenv("PML_TEST_KEY", "present")
    monkeypatch.setattr(api, "load_llm_config", lambda: config)
    monkeypatch.setattr(
        api,
        "health_check",
        lambda _config: {"latency_ms": 12.5, "detail": "modelo disponible"},
    )
    payload = client.get("/api/health?probe=true").json()
    assert payload["ok"] is True
    assert payload["configured"] is True
    assert payload["latency_ms"] == 12.5


def test_showcase_contract(monkeypatch) -> None:
    sample = ShowcaseResponse(
        generated_at="2026-10-31T15:00:00Z",
        data_status="complete",
        sections=[
            ShowcaseSection(
                id="data",
                order=2,
                title="Corpus",
                body="Datos públicos.",
                status="done",
                metrics=[],
                evidence=[EvidenceLink(label="Ficha", href="docs/data_card.md", kind="report")],
            )
        ],
        metrics=[
            CorpusMetric(
                key="units",
                label="Unidades",
                value=15211,
                unit="unidades",
                source="data/gold/quality.json",
                status="complete",
            )
        ],
    )
    monkeypatch.setattr(api, "build_showcase", lambda: sample)
    payload = client.get("/api/showcase")
    assert payload.status_code == 200
    assert payload.json()["data_status"] == "complete"
    assert payload.json()["metrics"][0]["value"] == 15211


def test_ask_returns_citations(monkeypatch) -> None:
    _patch_model(monkeypatch)
    monkeypatch.setattr(api, "answer_question", lambda *_args, **_kwargs: _ok_result())
    response = client.post("/api/ask", json={"question": "¿Qué productos ofrece Manuelita?"})
    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ok"
    assert payload["citations"][0]["label"] == "U1"
    assert "DEEPSEEK_API_KEY" not in response.text


def test_ask_fallback_without_citations(monkeypatch) -> None:
    _patch_model(monkeypatch)
    result = TaskResult(
        task="qa",
        status="fallback",
        answer="No hay evidencia suficiente en el corpus para responder.",
        fallback=True,
        model="scripted",
    )
    monkeypatch.setattr(api, "answer_question", lambda *_args, **_kwargs: result)
    payload = client.post("/api/ask", json={"question": "¿Precio actual?"}).json()
    assert payload["status"] == "fallback"
    assert payload["citations"] == []


def test_ask_rejects_blank_question() -> None:
    response = client.post("/api/ask", json={"question": "   "})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "empty_question"


def test_ask_rejects_long_question() -> None:
    response = client.post("/api/ask", json={"question": "a" * 501})
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "question_too_long"


def test_ask_maps_timeout(monkeypatch) -> None:
    _patch_model(monkeypatch)

    def fail(*_args, **_kwargs):
        raise TaskError("model_timeout", "timeout", task="qa")

    monkeypatch.setattr(api, "answer_question", fail)
    response = client.post("/api/ask", json={"question": "¿Qué productos?"})
    assert response.status_code in {422, 504}
    assert response.json()["error"]["code"] == "model_timeout"


def test_summary_and_faq(monkeypatch) -> None:
    _patch_model(monkeypatch)
    summary = TaskResult(
        task="summary",
        status="fallback",
        answer="No hay evidencia suficiente.",
        fallback=True,
        model="scripted",
    )
    item = FAQItem(
        question="¿Qué productos ofrece Manuelita?",
        answer="Azúcar y derivados.",
        citations=(_citation(),),
        status="ready",
        model="scripted",
    )
    monkeypatch.setattr(api, "summarize_corpus", lambda **_kwargs: summary)
    monkeypatch.setattr(api, "generate_faq", lambda **_kwargs: (item,))

    summary_response = client.post("/api/summary", json={"pack": "8000"})
    assert summary_response.status_code == 200
    assert summary_response.json()["status"] == "fallback"

    faq_response = client.post("/api/faq", json={"limit": 12})
    assert faq_response.status_code == 200
    assert faq_response.json()["items"][0]["question"].startswith("¿Qué")
