"""Estado del canal en SQLite (spec 024, T015)."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.channels.store import ChannelStore


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 28, 13, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


def test_thread_survives_reopen(tmp_path: Path) -> None:
    path = tmp_path / "channels.sqlite3"
    store = ChannelStore(path)
    thread = store.ensure_user("wa-0123456789abcdef", "whatsapp", "+57 ••• ••• 4567")
    assert store.ensure_user("wa-0123456789abcdef", "whatsapp", "+57 ••• ••• 4567") == thread
    store.close()
    reopened = ChannelStore(path)  # reinicio del servicio
    assert reopened.ensure_user("wa-0123456789abcdef", "whatsapp", "x") == thread
    tables = {
        row[0]
        for row in sqlite3.connect(path).execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )
    }
    assert {"channel_users", "channel_threads", "channel_seen", "channel_pending"} <= tables


def test_new_thread_closes_previous(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    first = store.ensure_user("wa-a", "whatsapp", "m")
    second = store.new_thread("wa-a")
    assert second != first
    assert store.ensure_user("wa-a", "whatsapp", "m") == second
    threads = dict(store.threads("wa-a"))
    assert threads[first] is not None and threads[second] is None


def test_dedupe_and_purge(tmp_path: Path) -> None:
    clock = Clock()
    store = ChannelStore(tmp_path / "c.sqlite3", clock=clock)
    assert store.seen("m1") is False
    assert store.seen("m1") is True
    clock.now += timedelta(hours=49)
    assert store.seen("m2") is False  # purga m1
    assert store.seen("m1") is False


def test_no_phone_numbers_stored(tmp_path: Path) -> None:
    path = tmp_path / "c.sqlite3"
    store = ChannelStore(path)
    store.ensure_user("wa-a", "whatsapp", "+57 ••• ••• 4567")
    store.seen("3EB0C4")
    dump = "\n".join(sqlite3.connect(path).iterdump())
    assert "3001234567" not in dump and "3EB0C4" not in dump


def test_pending_lifecycle(tmp_path: Path) -> None:
    clock = Clock()
    store = ChannelStore(tmp_path / "c.sqlite3", clock=clock)
    pending = store.set_pending("t1", "act-1", "save_profile", "Guardar perfil", ttl_minutes=10)
    assert pending.expires_at == clock.now + timedelta(minutes=10)
    assert store.get_pending("t1") is not None and store.pending_count() == 1
    clock.now += timedelta(minutes=11)
    assert store.get_pending("t1").expired(clock.now)  # type: ignore[union-attr]
    store.resolve_pending("t1", "expired")
    assert store.get_pending("t1") is None and store.pending_count() == 0
    with pytest.raises(ValueError):
        store.resolve_pending("t1", "pending")
