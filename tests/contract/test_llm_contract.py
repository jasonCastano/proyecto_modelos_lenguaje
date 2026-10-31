"""Contract tests for the DeepSeek provider configuration (T013, T022)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.llm import load_llm_config, main

SCHEMA_PATH = (
    Path(__file__).resolve().parents[2]
    / "specs"
    / "010-deepseek-api-model"
    / "contracts"
    / "provider-config.schema.json"
)


def _validator() -> Draft202012Validator:
    return Draft202012Validator(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_schema_file_is_valid() -> None:
    Draft202012Validator.check_schema(json.loads(SCHEMA_PATH.read_text(encoding="utf-8")))


def test_config_matches_the_contract() -> None:
    config = load_llm_config(PROJECT_ROOT / "config" / "llm.toml")
    _validator().validate(config.to_dict())


def test_config_file_has_required_values() -> None:
    config = load_llm_config(PROJECT_ROOT / "config" / "llm.toml")
    assert config.provider == "deepseek"
    assert config.model
    assert config.base_url.startswith("https://")
    assert config.api_key_env == "DEEPSEEK_API_KEY"
    assert int(config.default_context_pack) <= config.context_window
    assert 5 <= config.timeout_seconds <= 300
    assert 0 <= config.max_retries <= 3
    assert config.cost_per_1k_input >= 0
    assert config.cost_per_1k_output >= 0


def test_env_example_documents_the_key_without_a_value() -> None:
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert "DEEPSEEK_API_KEY=" in text
    assert "OLLAMA" not in text.upper()
    assert "sk-" not in text
    for line in text.splitlines():
        if line.startswith("DEEPSEEK_API_KEY="):
            assert line.strip() == "DEEPSEEK_API_KEY="


def test_gitignore_protects_env_and_allows_example() -> None:
    text = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
    assert "!.env.example" in text


def test_print_config_payload_shape(tmp_path: Path, capsys, monkeypatch) -> None:
    monkeypatch.setenv("DEEPSEEK_API_KEY", "sk-test")
    root = tmp_path
    config_dir = root / "config"
    config_dir.mkdir()
    (config_dir / "llm.toml").write_text(
        (PROJECT_ROOT / "config" / "llm.toml").read_text(encoding="utf-8"),
        encoding="utf-8",
    )
    assert main(["--print-config"], project_root=root) == 0
    payload = json.loads(capsys.readouterr().out)
    assert set(payload) == {
        "provider",
        "model",
        "base_url",
        "api_key_env",
        "api_key_present",
        "temperature",
        "top_p",
        "max_output_tokens",
        "context_window",
        "default_context_pack",
        "timeout_seconds",
        "max_retries",
        "retry_backoff_seconds",
        "cost_per_1k_input",
        "cost_per_1k_output",
        "language",
    }
    _validator().validate(payload)


def test_config_does_not_accept_secret_fields() -> None:
    text = (PROJECT_ROOT / "config" / "llm.toml").read_text(encoding="utf-8")
    assert "api_key =" not in text
    assert "sk-" not in text


@pytest.mark.parametrize("field", ["api_key", "token", "secret", "password"])
def test_forbidden_field_names_are_documented_and_rejected(field: str) -> None:
    from proyecto_modelos_lenguaje.llm import FORBIDDEN_KEYS

    assert field in FORBIDDEN_KEYS
