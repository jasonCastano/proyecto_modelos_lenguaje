"""Estado del canal con el uso del día (spec 031, T020, FR-010)."""

from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

from proyecto_modelos_lenguaje.channels.journal import recent_stats

NOW = datetime(2026, 11, 28, 17, 0, tzinfo=UTC)


def _row(user: str, status: str, event: str | None = None, *, ts: datetime = NOW) -> str:
    record = {"channel": "whatsapp", "user_id": user, "status": status, "event": event,
              "latency_ms": 900, "ts": ts.isoformat(timespec="seconds")}  # fmt: skip
    return json.dumps(record)


def test_people_limited_and_blocked_today(tmp_path: Path) -> None:
    rows = [
        _row("wa-aaaaaaaaaaaaaaaa", "answered"),
        _row("wa-aaaaaaaaaaaaaaaa", "answered"),
        _row("wa-bbbbbbbbbbbbbbbb", "answered"),
        _row("wa-bbbbbbbbbbbbbbbb", "busy", "rate_limited"),
        _row("wa-cccccccccccccccc", "answered"),
        _row("wa-dddddddddddddddd", "ignored", "blocked"),
        _row("wa-eeeeeeeeeeeeeeee", "answered", ts=NOW - timedelta(days=2)),  # otro día
    ]
    (tmp_path / "channels.jsonl").write_text("\n".join(rows) + "\n", encoding="utf-8")
    stats = recent_stats(tmp_path, now=NOW)["whatsapp"]
    assert stats["people_today"] == 3
    assert stats["limited_today"] == 1 and stats["blocked_today"] == 1
