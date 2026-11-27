"""Límites por número con el canal abierto (spec 031, T004, data-model §3)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from proyecto_modelos_lenguaje.agent.config import ChannelsConfig
from proyecto_modelos_lenguaje.channels.limits import limit_decision, operators

CONFIG = ChannelsConfig()  # 20 cada 10 min y 100 por día
START = datetime(2026, 11, 28, 15, 0, tzinfo=UTC)


def _run(count: int, *, step: timedelta = timedelta(seconds=1), usage=None, start=START):
    decisions = []
    now = start
    for _ in range(count):
        decision, usage = limit_decision(usage, now, CONFIG, operator=False)
        decisions.append(decision)
        now += step
    return decisions, usage, now


def test_the_short_window_allows_twenty_then_one_notice_then_silence() -> None:
    decisions, usage, _now = _run(60)
    assert decisions[:20] == ["allow"] * 20
    assert decisions[20] == "notify_rate"
    assert set(decisions[21:]) == {"silent"}
    assert decisions.count("allow") <= 20 and decisions.count("notify_rate") == 1  # SC-003
    later, _usage, _now = _run(1, usage=usage, start=START + timedelta(minutes=10))
    assert later == ["allow"]


def test_the_daily_cap_notifies_once_and_resets_the_next_day() -> None:
    # Un mensaje cada 2,5 min (4 por ventana): nunca toca el límite corto, sí el diario.
    decisions, usage, _now = _run(110, step=timedelta(minutes=2, seconds=30))
    assert decisions.count("allow") == 100
    assert decisions.count("notify_daily") == 1 and "notify_rate" not in decisions
    assert decisions[decisions.index("notify_daily") + 1 :] == ["silent"] * 9
    tomorrow, _usage, _now = _run(1, usage=usage, start=START + timedelta(days=1, hours=1))
    assert tomorrow == ["allow"]


def test_operators_are_never_limited() -> None:
    usage = None
    for _ in range(200):
        decision, usage = limit_decision(usage, START, CONFIG, operator=True)
        assert decision == "allow"
    assert usage.window_count == 0 and usage.day_count == 0


def test_operators_list_ignores_blanks(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VALERIA_OPERATORS", " wa-aaaaaaaaaaaaaaaa, ,wa-bbbbbbbbbbbbbbbb ,")
    assert operators() == {"wa-aaaaaaaaaaaaaaaa", "wa-bbbbbbbbbbbbbbbb"}
    monkeypatch.delenv("VALERIA_OPERATORS")
    assert operators() == frozenset()
