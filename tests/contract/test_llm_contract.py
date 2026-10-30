"""Contract tests for the Ollama LLM configuration."""

from __future__ import annotations

import json
from pathlib import Path

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.llm import load_llm_config


def test_config_file_has_required_contract() -> None:
    config = load_llm_config(PROJECT_ROOT / "config" / "llm.toml")
    assert config.provider == "ollama"
    assert config.model
    assert config.base_url.startswith("http")
    assert 0.0 <= config.temperature <= 1.0
    assert 0.0 < config.top_p <= 1.0
    assert 128 <= config.max_output_tokens <= 8192
    assert 2048 <= config.context_window <= 131072
    assert config.default_context_pack in {"8000", "32000"}
    assert int(config.default_context_pack) <= config.context_window
    assert 1 <= config.timeout_seconds <= 600
    assert 0 <= config.max_retries <= 5


def test_env_example_has_no_real_values() -> None:
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "OLLAMA_BASE_URL" in text
    assert "sk-" not in text
    assert "api_key=" not in text.lower()


def test_gitignore_protects_env_and_allows_example() -> None:
    text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
    assert "!.env.example" in text


def test_print_config_payload_shape(tmp_path: Path, capsys) -> None:
    from proyecto_modelos_lenguaje import llm

    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "llm.toml").write_text(
        (PROJECT_ROOT / "config" / "llm.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert llm.main(["--print-config"], project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {
        "provider",
        "model",
        "base_url",
        "temperature",
        "top_p",
        "max_output_tokens",
        "context_window",
        "default_context_pack",
        "timeout_seconds",
        "max_retries",
        "retry_backoff_seconds",
        "keep_alive",
        "seed",
        "language",
    }
