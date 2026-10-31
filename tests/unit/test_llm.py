"""Unit tests for the DeepSeek provider configuration and error policy (T014, T021, T026, T030)."""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje import llm
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

REAL_CONFIG = (PROJECT_ROOT / "config" / "llm.toml").read_text(encoding="utf-8")


def _root(tmp_path: Path, text: str = REAL_CONFIG) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "llm.toml").write_text(text, encoding="utf-8")
    return tmp_path


def _config(tmp_path: Path, text: str = REAL_CONFIG, **env: str) -> llm.ProviderConfig:
    for key, value in env.items():
        os.environ[key] = value
    try:
        return llm.load_llm_config("config/llm.toml", project_root=_root(tmp_path, text))
    finally:
        for key in env:
            os.environ.pop(key, None)


def test_load_config_defaults(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert config.provider == "deepseek"
    assert config.model == "deepseek-flash"
    assert config.base_url == "https://api.deepseek.com/v1"
    assert config.api_key_env == "DEEPSEEK_API_KEY"
    assert config.temperature == 0.1
    assert config.max_output_tokens == 1024
    assert config.context_window == 65536
    assert config.default_context_pack == "8000"
    assert config.timeout_seconds == 60
    assert config.max_retries == 1
    assert config.cost_per_1k_input == 0.0
    assert config.cost_configured is False


@pytest.mark.parametrize(
    ("original", "replacement"),
    [
        ("temperature = 0.1", "temperature = 2.0"),
        ("top_p = 0.9", "top_p = 0.0"),
        ("max_output_tokens = 1024", "max_output_tokens = 64"),
        ("context_window = 65536", "context_window = 1000"),
        ("timeout_seconds = 60", "timeout_seconds = 1"),
        ("max_retries = 1", "max_retries = 9"),
        ("retry_backoff_seconds = 2.0", "retry_backoff_seconds = 99.0"),
        ("cost_per_1k_input = 0.0", "cost_per_1k_input = -1.0"),
        ('language = "es"', 'language = "fr"'),
        ('default_context_pack = "8000"', 'default_context_pack = "16000"'),
    ],
)
def test_load_config_rejects_out_of_range(tmp_path: Path, original: str, replacement: str) -> None:
    text = REAL_CONFIG.replace(original, replacement)
    with pytest.raises(llm.LLMConfigError):
        _config(tmp_path, text)


def test_load_config_rejects_bad_provider(tmp_path: Path) -> None:
    text = REAL_CONFIG.replace('provider = "deepseek"', 'provider = "openai"')
    with pytest.raises(llm.LLMConfigError):
        _config(tmp_path, text)


def test_load_config_rejects_pack_above_window(tmp_path: Path) -> None:
    text = REAL_CONFIG.replace('default_context_pack = "8000"', 'default_context_pack = "32000"')
    text = text.replace("context_window = 65536", "context_window = 8192")
    with pytest.raises(llm.LLMConfigError):
        _config(tmp_path, text)


def test_load_config_rejects_secret_fields(tmp_path: Path) -> None:
    text = REAL_CONFIG.replace(
        'api_key_env = "DEEPSEEK_API_KEY"', 'api_key_env = "DEEPSEEK_API_KEY"\napi_key = "sk-123"'
    )
    with pytest.raises(llm.LLMConfigError, match="api_key"):
        _config(tmp_path, text)


def test_load_config_rejects_invalid_env_name(tmp_path: Path) -> None:
    text = REAL_CONFIG.replace('api_key_env = "DEEPSEEK_API_KEY"', 'api_key_env = "token"')
    with pytest.raises(llm.LLMConfigError):
        _config(tmp_path, text)


def test_env_overrides_base_url_and_model(tmp_path: Path) -> None:
    config = _config(
        tmp_path,
        DEEPSEEK_BASE_URL="https://proxy.example.test/v1",
        DEEPSEEK_MODEL="deepseek-chat",
    )
    assert config.base_url == "https://proxy.example.test/v1"
    assert config.model == "deepseek-chat"


def test_api_key_presence_and_accessor(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    config = _config(tmp_path)
    assert config.api_key_present is False
    with pytest.raises(llm.LLMConfigError, match="DEEPSEEK_API_KEY"):
        config.api_key()

    monkeypatch.setenv("DEEPSEEK_API_KEY", "   ")
    assert config.api_key_present is False

    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    assert config.api_key_present is True
    assert config.api_key() == "sk-test"


def test_to_dict_never_contains_the_key(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-super-secret")
    payload = _config(tmp_path).to_dict()
    assert payload["api_key_env"] == "DEEPSEEK_API_KEY"
    assert payload["api_key_present"] is True
    assert "sk-super-secret" not in json.dumps(payload)
    assert "api_key" not in {key for key in payload if key != "api_key_env"}


def test_cost_estimation(tmp_path: Path) -> None:
    free = _config(tmp_path)
    assert llm.estimate_cost(1000, 500, free) == 0.0
    assert free.format_cost(0.0) == "costo no configurado"

    text = REAL_CONFIG.replace("cost_per_1k_input = 0.0", "cost_per_1k_input = 0.5").replace(
        "cost_per_1k_output = 0.0", "cost_per_1k_output = 1.5"
    )
    paid = _config(tmp_path, text)
    assert paid.cost_configured is True
    assert llm.estimate_cost(2000, 1000, paid) == pytest.approx(2.5)
    assert paid.format_cost(2.5) == "2.5000 USD"


class _Message:
    def __init__(self, usage_metadata=None, response_metadata=None) -> None:
        self.usage_metadata = usage_metadata
        self.response_metadata = response_metadata or {}


def test_usage_tokens_reads_provider_metadata() -> None:
    assert llm.usage_tokens(_Message({"input_tokens": 12, "output_tokens": 7})) == (12, 7)
    assert llm.usage_tokens(
        _Message(response_metadata={"token_usage": {"prompt_tokens": 30, "completion_tokens": 9}})
    ) == (30, 9)
    assert llm.usage_tokens(_Message()) is None


class _FlakyModel:
    def __init__(self, failures: int, error: Exception) -> None:
        self.failures = failures
        self.error = error
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        if self.calls <= self.failures:
            raise self.error
        return "ok"


def test_retries_transient_errors(tmp_path: Path) -> None:
    config = _config(
        tmp_path, REAL_CONFIG.replace("retry_backoff_seconds = 2.0", "retry_backoff_seconds = 0.0")
    )
    model = _FlakyModel(1, llm.LLMRateLimitError("429"))
    assert llm.invoke_with_retries(model, "hola", config) == "ok"
    assert model.calls == 2


def test_does_not_retry_auth_errors(tmp_path: Path) -> None:
    config = _config(tmp_path, REAL_CONFIG.replace("max_retries = 1", "max_retries = 3"))
    model = _FlakyModel(5, llm.LLMAuthError("401"))
    with pytest.raises(llm.LLMAuthError):
        llm.invoke_with_retries(model, "hola", config)
    assert model.calls == 1


def test_exhausted_retries_raise(tmp_path: Path) -> None:
    config = _config(
        tmp_path, REAL_CONFIG.replace("retry_backoff_seconds = 2.0", "retry_backoff_seconds = 0.0")
    )
    model = _FlakyModel(10, llm.LLMUnavailableError("down"))
    with pytest.raises(llm.LLMUnavailableError):
        llm.invoke_with_retries(model, "hola", config)
    assert model.calls == 2


def test_health_check_ok(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(llm, "_fetch_models", lambda _config: ["deepseek-flash", "deepseek-chat"])
    result = llm.health_check(config)
    assert result["ok"] is True
    assert result["model"] == "deepseek-flash"
    assert result["latency_ms"] >= 0


def test_health_check_missing_model(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(llm, "_fetch_models", lambda _config: ["otro-modelo"])
    with pytest.raises(llm.LLMModelMissingError):
        llm.health_check(config)


def test_health_check_auth_error(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)

    def _fail(_config):
        raise llm.LLMAuthError("clave inválida")

    monkeypatch.setattr(llm, "_fetch_models", _fail)
    with pytest.raises(llm.LLMAuthError):
        llm.health_check(config)


def test_print_config_has_no_secret(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-super-secret")
    root = _root(tmp_path)
    assert llm.main(["--print-config"], project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["provider"] == "deepseek"
    assert payload["api_key_present"] is True
    assert "sk-super-secret" not in json.dumps(payload)


def test_check_reports_missing_key(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)

    def _fail(_config):
        raise llm.LLMConfigError("Falta la clave del proveedor.")

    monkeypatch.setattr(llm, "_fetch_models", _fail)
    root = _root(tmp_path)
    assert llm.main(["--check"], project_root=root) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["code"] == "config_missing_key"


def test_check_ok(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(llm, "_fetch_models", lambda _config: ["deepseek-flash"])
    root = _root(tmp_path)
    assert llm.main(["--check"], project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["model"] == "deepseek-flash"


def test_demo_mode_does_not_touch_the_provider(tmp_path: Path, monkeypatch) -> None:
    """The demo model must not read the API key nor build the remote client."""
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    model = llm.build_fake_model(["respuesta de prueba"])
    assert model.invoke("hola").content == "respuesta de prueba"


def test_secret_is_absent_from_the_repository_config() -> None:
    text = (PROJECT_ROOT / "config" / "llm.toml").read_text(encoding="utf-8")
    assert "sk-" not in text
    assert "api_key =" not in text
    assert "DEEPSEEK_API_KEY" in text
