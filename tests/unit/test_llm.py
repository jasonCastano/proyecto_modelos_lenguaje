"""Unit tests for the Ollama LLM configuration and adapter."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje import llm
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

REAL_CONFIG = (PROJECT_ROOT / "config" / "llm.toml").read_text(encoding="utf-8")


def _root(tmp_path: Path, text: str = REAL_CONFIG) -> Path:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    (config_dir / "llm.toml").write_text(text, encoding="utf-8")
    return tmp_path


def _config(tmp_path: Path, text: str = REAL_CONFIG) -> llm.LLMConfig:
    return llm.load_llm_config("config/llm.toml", project_root=_root(tmp_path, text))


def test_load_config_defaults(tmp_path: Path) -> None:
    config = _config(tmp_path)
    assert config.provider == "ollama"
    assert config.model == "llama3.1:8b"
    assert config.base_url == "http://localhost:11434"
    assert config.temperature == 0.1
    assert config.max_output_tokens == 1024
    assert config.context_window == 16384
    assert config.default_context_pack == "8000"
    assert config.timeout_seconds == 120
    assert config.seed == 42


def test_load_config_rejects_out_of_range(tmp_path: Path) -> None:
    text = REAL_CONFIG.replace("temperature = 0.1", "temperature = 2.0")
    with pytest.raises(llm.LLMConfigError):
        _config(tmp_path, text)


def test_load_config_rejects_bad_provider(tmp_path: Path) -> None:
    text = REAL_CONFIG.replace('provider = "ollama"', 'provider = "openai"')
    with pytest.raises(llm.LLMConfigError):
        _config(tmp_path, text)


def test_load_config_rejects_context_pack_above_window(tmp_path: Path) -> None:
    text = REAL_CONFIG.replace('default_context_pack = "8000"', 'default_context_pack = "32000"')
    text = text.replace("context_window = 16384", "context_window = 8192")
    with pytest.raises(llm.LLMConfigError):
        _config(tmp_path, text)


def test_env_overrides_base_url_and_model(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("OLLAMA_BASE_URL", "http://127.0.0.1:9999")
    monkeypatch.setenv("OLLAMA_MODEL", "llama3.2:3b")
    config = _config(tmp_path)
    assert config.base_url == "http://127.0.0.1:9999"
    assert config.model == "llama3.2:3b"


def test_build_chat_model_uses_ollama(tmp_path: Path) -> None:
    config = _config(tmp_path)
    model = llm.build_chat_model(config)
    assert model.model == "llama3.1:8b"  # type: ignore[attr-defined]
    assert model.base_url == "http://localhost:11434"  # type: ignore[attr-defined]
    assert model.temperature == 0.1  # type: ignore[attr-defined]
    assert model.num_ctx == 16384  # type: ignore[attr-defined]
    assert model.num_predict == 1024  # type: ignore[attr-defined]


def test_fake_model_is_deterministic() -> None:
    model = llm.build_fake_model(["respuesta fija"])
    first = model.invoke("hola")
    second = model.invoke("hola")
    assert first.content == "respuesta fija"
    assert second.content == "respuesta fija"


class _FlakyModel:
    def __init__(self, failures: int) -> None:
        self.failures = failures
        self.calls = 0

    def invoke(self, _messages):
        self.calls += 1
        if self.calls <= self.failures:
            raise RuntimeError("fallo transitorio")
        return "ok"


def test_invoke_with_retries_eventually_succeeds(tmp_path: Path) -> None:
    config = _config(tmp_path)
    model = _FlakyModel(failures=1)
    assert llm.invoke_with_retries(model, "hola", config) == "ok"
    assert model.calls == 2


def test_invoke_with_retries_exhausts(tmp_path: Path) -> None:
    config = _config(tmp_path)
    model = _FlakyModel(failures=10)
    with pytest.raises(llm.LLMResponseError):
        llm.invoke_with_retries(model, "hola", config)


def test_health_check_ok(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(llm, "_fetch_tags", lambda _config: ["llama3.1:8b"])
    result = llm.health_check(config)
    assert result["ok"] is True
    assert result["model"] == "llama3.1:8b"
    assert result["latency_ms"] >= 0


def test_health_check_missing_model(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)
    monkeypatch.setattr(llm, "_fetch_tags", lambda _config: ["otro:modelo"])
    with pytest.raises(llm.LLMModelMissingError):
        llm.health_check(config)


def test_health_check_unavailable(tmp_path: Path, monkeypatch) -> None:
    config = _config(tmp_path)

    def _fail(_config: llm.LLMConfig) -> list[str]:
        raise llm.LLMUnavailableError("sin servidor")

    monkeypatch.setattr(llm, "_fetch_tags", _fail)
    with pytest.raises(llm.LLMUnavailableError):
        llm.health_check(config)


def test_main_print_config_has_no_secrets(tmp_path: Path, capsys) -> None:
    root = _root(tmp_path)
    assert llm.main(["--print-config"], project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["provider"] == "ollama"
    assert "api_key" not in payload
    assert "token" not in payload


def test_main_check_ok(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _root(tmp_path)
    monkeypatch.setattr(llm, "_fetch_tags", lambda _config: ["llama3.1:8b"])
    assert llm.main(["--check"], project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True


def test_main_check_reports_unavailable(tmp_path: Path, monkeypatch, capsys) -> None:
    root = _root(tmp_path)

    def _fail(_config: llm.LLMConfig) -> list[str]:
        raise llm.LLMUnavailableError("Ollama no responde")

    monkeypatch.setattr(llm, "_fetch_tags", _fail)
    assert llm.main(["--check"], project_root=root) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["error"] == "LLMUnavailableError"
