"""Pruebas de la configuración del agente y del directorio de estado (T013)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.config import (
    AgentConfigError,
    load_agent_config,
    resolve_state_dir,
)
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

VALID_TOML = """
[router]
min_confidence = 0.6
llm_temperature = 0.0

[agent]
tool_call_limit = 3
model_call_limit = 5
chain_top_k = 8

[memory]
summarize_after_tokens = 6000
keep_last_messages = 6
preference_ttl_days = 30

[structured]
path = "data/module2/structured"

[state]
env_var = "MANUELITA_STATE_DIR"
"""


def _write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "agent.toml"
    path.write_text(text, encoding="utf-8")
    return path


def test_repository_config_loads_with_research_values() -> None:
    # Act
    config = load_agent_config()

    # Assert
    assert config.router.min_confidence == 0.6
    assert config.agent.tool_call_limit == 3
    assert config.agent.model_call_limit == 5
    assert config.memory.preference_ttl_days == 30
    assert config.structured_path == PROJECT_ROOT / "data" / "module2" / "structured"
    assert config.state_env_var == "MANUELITA_STATE_DIR"


def test_relative_structured_path_resolves_against_project_root(tmp_path: Path) -> None:
    # Arrange
    path = _write(tmp_path, VALID_TOML)

    # Act
    config = load_agent_config(path, project_root=tmp_path)

    # Assert
    assert config.structured_path == tmp_path / "data" / "module2" / "structured"


@pytest.mark.parametrize(
    ("old", "new", "message"),
    [
        ("min_confidence = 0.6", "min_confidence = 1.2", "router.min_confidence"),
        ("min_confidence = 0.6", "min_confidence = true", "router.min_confidence"),
        ("tool_call_limit = 3", "tool_call_limit = 0", "agent.tool_call_limit"),
        ("chain_top_k = 8", 'chain_top_k = "8"', "agent.chain_top_k"),
        ('env_var = "MANUELITA_STATE_DIR"', 'env_var = ""', "state.env_var"),
    ],
)
def test_invalid_values_are_rejected(tmp_path: Path, old: str, new: str, message: str) -> None:
    # Arrange
    path = _write(tmp_path, VALID_TOML.replace(old, new))

    # Act / Assert
    with pytest.raises(AgentConfigError, match=message):
        load_agent_config(path, project_root=tmp_path)


def test_missing_section_and_missing_file_are_clear_errors(tmp_path: Path) -> None:
    # Arrange
    without_memory = VALID_TOML.split("[memory]")[0]

    # Act / Assert
    with pytest.raises(AgentConfigError, match=r"\[memory\]"):
        load_agent_config(_write(tmp_path, without_memory), project_root=tmp_path)
    with pytest.raises(AgentConfigError, match="No existe"):
        load_agent_config(tmp_path / "missing.toml", project_root=tmp_path)


def test_state_dir_respects_environment_variable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Arrange
    outside = tmp_path / "estado"
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(outside))

    # Act
    resolved = resolve_state_dir(project_root=tmp_path / "repo")

    # Assert
    assert resolved == outside.resolve()


def test_state_dir_inside_repository_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(PROJECT_ROOT / "data" / "estado"))

    # Act / Assert
    with pytest.raises(AgentConfigError, match="dentro del repositorio"):
        resolve_state_dir()


def test_default_state_dir_is_outside_repository(monkeypatch: pytest.MonkeyPatch) -> None:
    # Arrange
    monkeypatch.delenv("MANUELITA_STATE_DIR", raising=False)

    # Act
    resolved = resolve_state_dir()

    # Assert
    assert resolved.name == "manuelita-rag"
    assert PROJECT_ROOT.resolve() not in resolved.parents
