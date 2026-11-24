"""Puente del canal con un ChatService falso (spec 024, T016, T045, T060)."""

from __future__ import annotations

import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from proyecto_modelos_lenguaje.agent.config import ChannelsConfig
from proyecto_modelos_lenguaje.channels.bridge import (
    BUSY_TEXT,
    UNSUPPORTED_TEXT,
    ChannelBridge,
    InboundMessage,
    decision_of,
)
from proyecto_modelos_lenguaje.channels.store import ChannelStore

SALT = "sal-de-prueba-0123456789"
PHONE = "+573001234567"


@dataclass
class Outcome:
    thread_id: str
    turn: dict[str, Any]
    status: str = "answered"
    pending_action: dict[str, Any] | None = None


@dataclass
class FakeService:
    calls: list[dict[str, Any]] = field(default_factory=list)
    resumes: list[dict[str, Any]] = field(default_factory=list)
    propose: str | None = None
    fail: bool = False
    gate: threading.Event | None = None

    def send(self, message: str, **kwargs: Any) -> Outcome:
        self.calls.append({"message": message, **kwargs})
        if self.gate is not None:
            self.gate.wait(2)
        if self.fail:
            raise RuntimeError("Traceback interno")
        if self.propose:
            return Outcome(
                kwargs["thread_id"],
                {"route": {"route": "direct"}},
                "pending_approval",
                {"action_id": "act-1", "tool": self.propose, "args": {"name": "Ana"}},
            )
        turn = {
            "route": {"route": "documental"},
            "answer": f"Respuesta a «{message}» [U1].",
            "citations": [{"label": "U1", "url": "https://manuelita.com", "title": "Informe"}],
            "tools": [{"name": "search_documents", "ok": True, "duration_ms": 12}],
            "plan_steps": ["buscar en documentos", "responder con cita"],
        }
        return Outcome(kwargs["thread_id"], turn)

    def resume(self, thread_id: str, **kwargs: Any) -> Outcome:
        self.resumes.append({"thread_id": thread_id, **kwargs})
        answer = "Guardé tu perfil." if kwargs["decision"] == "approve" else ""
        return Outcome(thread_id, {"route": {"route": "direct"}, "answer": answer})


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 28, 13, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture()
def clock() -> Clock:
    return Clock()


@pytest.fixture()
def service() -> FakeService:
    return FakeService()


@pytest.fixture()
def bridge(tmp_path: Path, service: FakeService, clock: Clock) -> ChannelBridge:
    store = ChannelStore(tmp_path / "channels.sqlite3", clock=clock)
    return ChannelBridge(
        service,
        store,
        ChannelsConfig(),
        salt=SALT,
        mode="demo",
        log_dir=tmp_path / "logs",
        workspace=tmp_path / "workspace",
    )


def msg(text: str | None, message_id: str, kind: str = "text") -> InboundMessage:
    return InboundMessage("whatsapp", message_id, PHONE, kind, text)  # type: ignore[arg-type]


def test_answers_in_a_stable_thread(bridge: ChannelBridge, service: FakeService) -> None:
    first = bridge.handle(msg("¿Qué produce Manuelita?", "m1"))
    second = bridge.handle(msg("¿y en Perú?", "m2"))
    assert first.status == second.status == "answered"
    assert first.thread_id == second.thread_id
    assert first.route == "documental" and first.tools == ["search_documents"]
    assert "[1]" in first.messages[0] and "Fuentes:" in first.messages[-1]
    assert service.calls[0]["variant"] == "agent" and service.calls[0]["mode"] == "demo"
    assert service.calls[0]["user_id"].startswith("wa-")


def test_duplicate_is_ignored(bridge: ChannelBridge, service: FakeService) -> None:
    bridge.handle(msg("hola", "m1"))
    again = bridge.handle(msg("hola", "m1"))
    assert again.status == "ignored" and again.messages == []
    assert len(service.calls) == 1


def test_busy_while_a_turn_runs(bridge: ChannelBridge, service: FakeService) -> None:
    service.gate = threading.Event()
    results = {}
    worker = threading.Thread(target=lambda: results.setdefault("a", bridge.handle(msg("a", "m1"))))
    worker.start()
    while not service.calls:
        pass
    busy = bridge.handle(msg("b", "m2"))
    service.gate.set()
    worker.join()
    assert busy.status == "busy" and BUSY_TEXT in busy.messages[0]
    assert results["a"].status == "answered"


def test_non_text_is_unsupported(bridge: ChannelBridge, service: FakeService) -> None:
    reply = bridge.handle(msg(None, "m1", "image"))
    assert reply.status == "unsupported" and UNSUPPORTED_TEXT in reply.messages[0]
    assert service.calls == []


def test_errors_are_short_and_clean(bridge: ChannelBridge, service: FakeService) -> None:
    service.fail = True
    reply = bridge.handle(msg("hola", "m1"))
    assert reply.status == "error"
    assert "Traceback" not in " ".join(reply.messages)


def test_help_and_trace_commands(bridge: ChannelBridge) -> None:
    assert "/nuevo" in bridge.handle(msg("/ayuda", "m1")).messages[0]
    assert "Todavía no" in bridge.handle(msg("/traza", "m2")).messages[0]
    bridge.handle(msg("¿Qué produce Manuelita?", "m3"))
    trace = bridge.handle(msg("/traza", "m4")).messages[0]
    assert "documental" in trace and "search_documents" in trace and "1. buscar" in trace


def test_logs_have_no_text_nor_number(bridge: ChannelBridge, tmp_path: Path) -> None:
    bridge.handle(msg("¿Qué produce Manuelita?", "3EB0C4"))
    log = (tmp_path / "logs" / "channels.jsonl").read_text(encoding="utf-8")
    record = json.loads(log.splitlines()[-1])
    assert record["user_id"].startswith("wa-") and record["status"] == "answered"
    assert "Manuelita" not in log and "3001234567" not in log and "3EB0C4" not in log
    daily = next((tmp_path / "workspace" / "memory").glob("*.md")).read_text(encoding="utf-8")
    assert "search_documents" in daily and "3001234567" not in daily


# --- confirmación por SÍ/NO (T045) ---------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "expected"),
    [("SÍ", "approve"), ("si, dale", "approve"), ("ok", "approve"), ("No", "reject"),
     ("cancelar", "reject"), ("¿qué guardarás?", None), ("sí claro que sí por favor hazlo", None)],
)  # fmt: skip
def test_decision_of(text: str, expected: str | None) -> None:
    assert decision_of(text) == expected


def test_write_requires_yes(bridge: ChannelBridge, service: FakeService) -> None:
    service.propose = "save_profile"
    pending = bridge.handle(msg("Me llamo Ana", "m1"))
    assert pending.status == "pending_approval" and "*SÍ*" in pending.messages[0]
    service.propose = None
    reminder = bridge.handle(msg("¿qué vas a guardar?", "m2"))
    assert reminder.status == "pending_approval" and len(service.calls) == 1
    done = bridge.handle(msg("sí", "m3"))
    assert done.status == "approval_resolved" and "Guardé" in done.messages[0]
    assert service.resumes[-1]["decision"] == "approve"
    assert bridge.store.get_pending(done.thread_id) is None  # type: ignore[arg-type]


def test_no_rejects(bridge: ChannelBridge, service: FakeService) -> None:
    service.propose = "save_profile"
    bridge.handle(msg("Me llamo Ana", "m1"))
    done = bridge.handle(msg("no", "m2"))
    assert done.status == "approval_resolved" and "no hice ningún cambio" in done.messages[0]
    assert service.resumes[-1]["decision"] == "reject"


def test_pending_expires(bridge: ChannelBridge, service: FakeService, clock: Clock) -> None:
    service.propose = "save_profile"
    bridge.handle(msg("Me llamo Ana", "m1"))
    service.propose = None
    clock.now += timedelta(minutes=11)
    reply = bridge.handle(msg("¿Qué produce Manuelita?", "m2"))
    assert service.resumes[-1]["decision"] == "reject"
    assert reply.status == "answered" and "venció" in reply.messages[0]


# --- memoria por comandos (T060, T062) -----------------------------------------------------


def test_new_thread_command(bridge: ChannelBridge, service: FakeService) -> None:
    first = bridge.handle(msg("hola", "m1"))
    new = bridge.handle(msg("/nuevo", "m2"))
    after = bridge.handle(msg("hola otra vez", "m3"))
    assert new.thread_id != first.thread_id and after.thread_id == new.thread_id
    assert service.calls[-1]["user_id"] == service.calls[0]["user_id"]  # el perfil se conserva


def test_forget_command_proposes_forget_memory(bridge: ChannelBridge, service: FakeService) -> None:
    service.propose = "forget_memory"
    reply = bridge.handle(msg("/olvidar", "m1"))
    assert reply.status == "pending_approval"
    assert "Olvida todos mis datos" in service.calls[-1]["message"]
