"""Provider integration tests with a simulated HTTP transport (no network, no quota).

Covers US1 (responses), US4 (tokens) and US5 (error mapping and retries).
"""

from __future__ import annotations

import json
from typing import Any

import httpx
import pytest
from langchain_openai import ChatOpenAI

from proyecto_modelos_lenguaje import llm
from proyecto_modelos_lenguaje.retrieval import GoldUnit
from proyecto_modelos_lenguaje.tasks import TaskError, answer_question
from tests.tasks_helpers import make_units

CONFIG = llm.ProviderConfig(
    provider="deepseek",
    model="deepseek-flash",
    base_url="https://api.deepseek.com/v1",
    api_key_env="DEEPSEEK_API_KEY",
    temperature=0.1,
    top_p=0.9,
    max_output_tokens=256,
    context_window=65536,
    default_context_pack="8000",
    timeout_seconds=5,
    max_retries=1,
    retry_backoff_seconds=0.0,
    cost_per_1k_input=0.5,
    cost_per_1k_output=1.5,
    language="es",
)


def _units() -> list[GoldUnit]:
    return [GoldUnit.from_dict(item) for item in make_units()]


def _completion(content: str, *, prompt_tokens: int = 120, completion_tokens: int = 30) -> dict:
    return {
        "id": "chatcmpl-test",
        "object": "chat.completion",
        "created": 0,
        "model": "deepseek-flash",
        "choices": [
            {
                "index": 0,
                "message": {"role": "assistant", "content": content},
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": prompt_tokens + completion_tokens,
        },
    }


def _model(handler) -> ChatOpenAI:
    return ChatOpenAI(
        model=CONFIG.model,
        base_url=CONFIG.base_url,
        api_key="sk-test",
        temperature=CONFIG.temperature,
        max_tokens=CONFIG.max_output_tokens,
        timeout=CONFIG.timeout_seconds,
        max_retries=CONFIG.max_retries,
        http_client=httpx.Client(transport=httpx.MockTransport(handler)),
    )


def test_qa_returns_citations_with_the_provider(monkeypatch) -> None:
    seen: list[dict[str, Any]] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(json.loads(request.content))
        return httpx.Response(200, json=_completion("Manuelita produce azúcar [U1]."))

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    result = answer_question(
        "¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units()
    )

    assert result.status == "ok"
    assert result.citations
    assert result.model == "deepseek-flash"
    assert result.input_tokens == 120
    assert result.output_tokens == 30
    assert seen, "el proveedor recibió la petición"


def test_payload_contains_only_the_selected_evidence(monkeypatch) -> None:
    captured: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request.content.decode("utf-8"))
        return httpx.Response(200, json=_completion("Respuesta [U1]."))

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    answer_question("¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units())
    payload = "".join(captured)
    assert "Manuelita produce azúcar" in payload
    assert "sk-test" not in payload


def test_fallback_does_not_call_the_provider(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:  # pragma: no cover - must not run
        raise AssertionError("no debería llamarse al proveedor")

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    result = answer_question("fútbol baloncesto tenis", model=_model(handler), units=_units())
    assert result.status == "fallback"
    assert result.citations == ()


def test_auth_error_is_a_controlled_error(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(401, json={"error": {"message": "invalid api key"}})

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with pytest.raises(TaskError) as error:
        answer_question("¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units())
    assert error.value.code == "model_error"
    assert "clave" in error.value.message.lower()
    assert "sk-test" not in error.value.message


def test_rate_limit_is_retried_once(monkeypatch) -> None:
    calls: list[int] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(1)
        if len(calls) == 1:
            return httpx.Response(429, json={"error": {"message": "rate limit"}})
        return httpx.Response(200, json=_completion("Respuesta [U1]."))

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    result = answer_question(
        "¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units()
    )
    assert result.status == "ok"
    assert len(calls) == 2


def test_model_missing_is_reported(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404, json={"error": {"message": "model not found"}})

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with pytest.raises(TaskError) as error:
        answer_question("¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units())
    assert error.value.code == "model_error"
    assert "modelo" in error.value.message.lower()


def test_timeout_maps_to_model_timeout(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("slow provider", request=request)

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with pytest.raises(TaskError) as error:
        answer_question("¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units())
    assert error.value.code == "model_timeout"


def test_server_error_is_reported(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(500, json={"error": {"message": "boom"}})

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with pytest.raises(TaskError) as error:
        answer_question("¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units())
    assert error.value.code == "model_error"
    assert "disponible" in error.value.message.lower()


def test_empty_answer_is_rejected(monkeypatch) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=_completion(""))

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    with pytest.raises(TaskError) as error:
        answer_question("¿Qué productos ofrece Manuelita?", model=_model(handler), units=_units())
    assert error.value.code == "model_error"


def test_classification_covers_provider_errors() -> None:
    assert isinstance(llm.classify_error(TimeoutError("slow")), llm.LLMTimeoutError)
    assert isinstance(llm.classify_error(RuntimeError("boom")), llm.LLMUnavailableError)
