"""Acción de escritura request_human_contact (T033, spec 024)."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent.actions import (
    ARG_SCHEMAS,
    TOOL_DESCRIPTIONS,
    WRITE_TOOLS,
    ActionArgsError,
    execute_action,
    validate_args,
)
from proyecto_modelos_lenguaje.agent.catalog import ToolArgsError, ToolContext, get_spec, run_read
from proyecto_modelos_lenguaje.agent.models import PendingAction

USER = "wa-3f9a1c"  # seudónimo del canal, nunca el número


@pytest.fixture()
def state_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    monkeypatch.setenv("MANUELITA_STATE_DIR", str(tmp_path))
    return tmp_path


def _execute(args: dict) -> str:
    return execute_action(
        "request_human_contact", args, store=None, user_id=USER, turns=[], ttl_days=30
    )


def test_is_a_write_tool_that_requires_approval() -> None:
    # Arrange
    spec = get_spec("request_human_contact")

    # Act / Assert
    assert spec.kind == "write" and spec.requires_approval and not spec.mcp
    assert spec.number == 20
    assert "request_human_contact" in WRITE_TOOLS  # HumanInTheLoopMiddleware lo interrumpe
    assert "request_human_contact" in TOOL_DESCRIPTIONS and "request_human_contact" in ARG_SCHEMAS
    assert PendingAction(action_id="a1", tool="request_human_contact").tool
    with pytest.raises(ToolArgsError, match="aprobación"):
        run_read(spec, ToolContext(), {"topic": "empleo", "preferred_channel": "email"})


@pytest.mark.parametrize(
    "args",
    [
        {"topic": "ab", "preferred_channel": "email"},
        {"topic": "x" * 121, "preferred_channel": "email"},
        {"topic": "vacantes", "preferred_channel": "telegram"},
        {"topic": "vacantes", "preferred_channel": "email", "name": ""},
        {"topic": "vacantes", "preferred_channel": "email", "name": "n" * 81},
        {"topic": "vacantes", "preferred_channel": "email", "user_id": "otro"},
    ],
)
def test_invalid_args_are_rejected_and_nothing_is_written(state_dir: Path, args: dict) -> None:
    # Act / Assert
    with pytest.raises(ActionArgsError):
        _execute(args)
    assert not (state_dir / "contacts.jsonl").exists()


def test_approved_request_is_registered_with_the_pseudonymous_user(state_dir: Path) -> None:
    # Act
    reply = _execute(
        {"topic": "Quiero enviar mi hoja de vida", "preferred_channel": "email", "name": "Ana"}
    )

    # Assert
    lines = (state_dir / "contacts.jsonl").read_text(encoding="utf-8").splitlines()
    record = json.loads(lines[0])
    assert len(lines) == 1
    assert record["user_id"] == USER
    assert record["topic"] == "Quiero enviar mi hoja de vida"
    assert record["preferred_channel"] == "email"
    assert record["purpose"] == "empleo"
    assert record["name"] == "Ana"
    assert datetime.fromisoformat(record["created_at"]).tzinfo is not None
    assert "https://www.manuelita.com/vacantes" in reply
    assert "Registré tu solicitud" in reply


def test_contact_data_in_the_topic_is_redacted(state_dir: Path) -> None:
    # Act
    _execute({"topic": "Llámenme al 3001234567 o ana@correo.com", "preferred_channel": "llamada"})

    # Assert
    record = json.loads((state_dir / "contacts.jsonl").read_text(encoding="utf-8"))
    assert "3001234567" not in record["topic"]
    assert "ana@correo.com" not in record["topic"]


def test_rejected_request_writes_nothing(state_dir: Path) -> None:
    # Arrange: rechazar es no llamar a execute_action; solo se validan los argumentos propuestos
    proposed = validate_args(
        "request_human_contact", {"topic": "proveedores de caña", "preferred_channel": "whatsapp"}
    )

    # Assert
    assert proposed["name"] is None
    assert not (state_dir / "contacts.jsonl").exists()
