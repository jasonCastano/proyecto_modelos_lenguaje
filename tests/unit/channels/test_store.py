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


# ---------------------------------------------------------- spec 028 (T014, data-model)


def test_reply_format_per_thread_defaults_to_auto(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    thread = store.ensure_user("wa-1", "whatsapp", "+57***01")
    assert store.get_reply_format(thread) == "auto"

    store.set_reply_format(thread, "text")
    assert store.get_reply_format(thread) == "text"
    with pytest.raises(ValueError):
        store.set_reply_format(thread, "fax")

    fresh = store.new_thread("wa-1")  # «empecemos de nuevo» vuelve a «auto»
    assert store.get_reply_format(fresh) == "auto"


def test_reply_format_survives_thread_adoption(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    placeholder = store.ensure_user("wa-1", "whatsapp", "+57***01")
    store.set_reply_format(placeholder, "voice")
    store.adopt_thread("wa-1", placeholder, "real-thread")
    assert store.get_reply_format("real-thread") == "voice"


def test_last_route_is_remembered(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    thread = store.ensure_user("wa-1", "whatsapp", "+57***01")
    assert store.get_last_route(thread) is None
    store.set_last_route(thread, "planning")
    assert store.get_last_route(thread) == "planning"


def test_pending_can_be_superseded(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    thread = store.ensure_user("wa-1", "whatsapp", "+57***01")
    store.set_pending(thread, "a1", "save_preference", "Guardar", ttl_minutes=10)
    store.resolve_pending(thread, "superseded")
    assert store.get_pending(thread) is None


def test_migrates_a_spec_024_database(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE channel_threads (thread_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
        "created_at TEXT NOT NULL, closed_at TEXT, started INTEGER NOT NULL DEFAULT 0);"
        "INSERT INTO channel_threads VALUES ('t1', 'wa-1', '2026-11-24', NULL, 1);"
    )
    db.commit()
    db.close()

    store = ChannelStore(path)

    assert store.get_reply_format("t1") == "auto" and store.get_last_route("t1") is None


# --- spec 031: uso por seudónimo y bloqueados (T006) ---


def test_usage_round_trips(tmp_path: Path) -> None:
    from proyecto_modelos_lenguaje.channels.limits import Usage

    store = ChannelStore(tmp_path / "channels.sqlite3")
    assert store.get_usage("wa-0123456789abcdef") is None
    usage = Usage(datetime(2026, 11, 28, 15, 0, tzinfo=UTC), 3, True, "2026-11-28", 7, False)
    store.save_usage("wa-0123456789abcdef", usage)
    store.save_usage("wa-0123456789abcdef", usage)  # actualizar no duplica
    assert store.get_usage("wa-0123456789abcdef") == usage


def test_block_and_unblock(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "channels.sqlite3")
    assert store.block("wa-0123456789abcdef") is True
    assert store.block("wa-0123456789abcdef") is False  # no duplica
    assert store.is_blocked("wa-0123456789abcdef")
    assert [user for user, _at in store.blocked()] == ["wa-0123456789abcdef"]
    assert store.unblock("wa-0123456789abcdef") is True
    assert store.unblock("wa-ffffffffffffffff") is False
    assert not store.is_blocked("wa-0123456789abcdef")


def test_an_older_database_gains_the_new_tables(tmp_path: Path) -> None:
    path = tmp_path / "channels.sqlite3"
    old = sqlite3.connect(path)
    old.executescript(
        "CREATE TABLE channel_users (user_id TEXT PRIMARY KEY, channel TEXT NOT NULL, "
        "masked TEXT NOT NULL, first_seen TEXT NOT NULL, last_seen TEXT NOT NULL, "
        "active_thread_id TEXT NOT NULL);"
        "INSERT INTO channel_users VALUES ('wa-0123456789abcdef', 'whatsapp', 'x', 'a', 'b', 'h1');"
    )
    old.commit()
    old.close()
    store = ChannelStore(path)
    assert store.ensure_user("wa-0123456789abcdef", "whatsapp", "x") == "h1"  # el hilo se conserva
    assert store.block("wa-0123456789abcdef") is True


# --- spec 032: inicio de conversación y presentación (T005) ---

USER = "wa-0123456789abcdef"


def test_existing_threads_count_as_introduced_after_migration(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE channel_threads (thread_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
        "created_at TEXT NOT NULL, closed_at TEXT, started INTEGER NOT NULL DEFAULT 0);"
        "INSERT INTO channel_threads VALUES ('t1', 'wa-1', '2026-11-24', NULL, 1);"
    )
    db.commit()
    db.close()

    store = ChannelStore(path)

    assert store.is_introduced("t1")  # nadie recibe la presentación a mitad de conversación


def test_new_threads_start_without_introduction(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    first = store.ensure_user(USER, "whatsapp", "x")
    assert not store.is_introduced(first)
    store.mark_introduced(first)
    assert store.is_introduced(first)
    second = store.new_thread(USER)
    assert not store.is_introduced(second)


def test_adopt_thread_keeps_the_introduction_flag(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    placeholder = store.ensure_user(USER, "whatsapp", "x")
    store.adopt_thread(USER, placeholder, "servicio-1")
    assert not store.is_introduced("servicio-1")
    store.mark_introduced("servicio-1")
    assert store.is_introduced("servicio-1")


def test_open_conversation_reports_first_contact_and_inactivity(tmp_path: Path) -> None:
    clock = Clock()
    path = tmp_path / "c.sqlite3"
    store = ChannelStore(path, clock=clock)

    first, reason = store.open_conversation(USER, "whatsapp", "x", idle_hours=12)
    assert reason == "first_contact"

    clock.now += timedelta(hours=11)
    same, reason = store.open_conversation(USER, "whatsapp", "x", idle_hours=12)
    assert (same, reason) == (first, None)

    clock.now += timedelta(hours=12, minutes=1)  # 12 h después del último mensaje
    fresh, reason = store.open_conversation(USER, "whatsapp", "x", idle_hours=12)
    assert reason == "inactivity" and fresh != first
    assert not store.is_introduced(fresh)
    closed = (
        sqlite3.connect(path)
        .execute("SELECT closed_at FROM channel_threads WHERE thread_id = ?", (first,))
        .fetchone()
    )
    assert closed[0] is not None
    assert store.ensure_user(USER, "whatsapp", "x") == fresh  # el hilo nuevo queda activo


# --- spec 034: uso de stickers por hilo (T006) --------------------------------------------------


def test_sticker_usage_survives_adoption(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    placeholder = store.ensure_user(USER, "whatsapp", "x")
    assert store.count_answered(placeholder) == 1
    store.record_sticker(placeholder, "valeria-hola", 1)
    store.adopt_thread(USER, placeholder, "servicio-1")
    assert store.count_answered("servicio-1") == 2
    usage = store.sticker_usage("servicio-1", 2)
    assert usage.sent == ("valeria-hola",) and usage.last_sticker_turn == 1 and usage.turn_no == 2


def test_an_older_database_gains_the_sticker_table(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE channel_threads (thread_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
        "created_at TEXT NOT NULL, closed_at TEXT, started INTEGER NOT NULL DEFAULT 0);"
        "INSERT INTO channel_threads VALUES ('t1', 'wa-1', '2026-11-24', NULL, 1);"
    )
    db.commit()
    db.close()
    store = ChannelStore(path)
    assert store.sticker_usage("t1", 1).sent == () and store.count_answered("t1") == 1


# --- spec 037: último sticker, situación y «sin stickers» (T003) ------------------------------


def test_spec037_usage_reports_last_sticker_situation_and_off(tmp_path: Path) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3")
    thread = store.ensure_user(USER, "whatsapp", "x")
    store.record_sticker(thread, "valeria-bienvenido", 1, "greeting_first_contact")
    store.record_sticker(thread, "valeria-listo", 2, "useful_answer")
    usage = store.sticker_usage(thread, 3)
    assert usage.last_sticker == "valeria-listo" and usage.last_situation == "useful_answer"
    assert usage.sent == ("valeria-bienvenido", "valeria-listo") and usage.off is False
    store.set_stickers_off(thread)
    store.adopt_thread(USER, thread, "servicio-1")
    again = store.sticker_usage("servicio-1", 4)
    assert again.off is True and again.last_sticker == "valeria-listo"


def test_spec037_an_older_sticker_table_gains_the_situation(tmp_path: Path) -> None:
    path = tmp_path / "old.sqlite3"
    db = sqlite3.connect(path)
    db.executescript(
        "CREATE TABLE channel_threads (thread_id TEXT PRIMARY KEY, user_id TEXT NOT NULL, "
        "created_at TEXT NOT NULL, closed_at TEXT, started INTEGER NOT NULL DEFAULT 0);"
        "INSERT INTO channel_threads VALUES ('t1', 'wa-1', '2026-11-24', NULL, 1);"
        "CREATE TABLE channel_stickers (thread_id TEXT NOT NULL, sticker TEXT NOT NULL, "
        "turn_no INTEGER NOT NULL, sent_at TEXT NOT NULL);"
        "INSERT INTO channel_stickers VALUES ('t1', 'valeria-hola', 1, '2026-11-24');"
    )
    db.commit()
    db.close()
    store = ChannelStore(path)
    usage = store.sticker_usage("t1", 2)
    assert usage.sent == ("valeria-hola",) and usage.last_situation is None and usage.off is False
