"""Límites por número con el canal abierto (spec 031, data-model §3).

Lógica pura, sin E/S: el puente lee el uso del almacén, decide y lo guarda. Todo va por seudónimo
(``wa-<16 hex>``); nunca por número. Los operadores (``VALERIA_OPERATORS``) no tienen límites.

Orden de la decisión por mensaje:

1. operador → ``allow`` (sin contar);
2. tope diario alcanzado → ``notify_daily`` la primera vez, luego ``silent``;
3. límite de la ventana corta alcanzado → ``notify_rate`` la primera vez, luego ``silent``;
4. si no → ``allow`` e incrementa los dos contadores.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from typing import Literal

from ..agent.config import ChannelsConfig

Decision = Literal["allow", "notify_rate", "notify_daily", "silent"]
OPERATORS_ENV = "VALERIA_OPERATORS"


def operators() -> frozenset[str]:
    """Seudónimos de los números de prueba del equipo (``VALERIA_OPERATORS``, por comas)."""
    raw = os.environ.get(OPERATORS_ENV, "")
    return frozenset(item.strip() for item in raw.split(",") if item.strip())


@dataclass(frozen=True, slots=True)
class Usage:
    window_start: datetime
    window_count: int
    window_notified: bool
    day: str  # YYYY-MM-DD en hora local
    day_count: int
    day_notified: bool


def local_day(now: datetime) -> str:
    return now.astimezone().strftime("%Y-%m-%d")


def _fresh(now: datetime) -> Usage:
    return Usage(now, 0, False, local_day(now), 0, False)


def _current(usage: Usage | None, now: datetime, config: ChannelsConfig) -> Usage:
    """Uso con la ventana y el día reiniciados si ya vencieron."""
    if usage is None:
        return _fresh(now)
    if now - usage.window_start >= timedelta(minutes=config.rate_window_minutes):
        usage = replace(usage, window_start=now, window_count=0, window_notified=False)
    today = local_day(now)
    if usage.day != today:
        usage = replace(usage, day=today, day_count=0, day_notified=False)
    return usage


def limit_decision(
    usage: Usage | None, now: datetime, config: ChannelsConfig, *, operator: bool
) -> tuple[Decision, Usage]:
    """Decisión para el mensaje actual y el uso actualizado (para guardarlo)."""
    current = _current(usage, now, config)
    if operator:
        return "allow", current
    if current.day_count >= config.daily_max_messages:
        if current.day_notified:
            return "silent", current
        return "notify_daily", replace(current, day_notified=True)
    if current.window_count >= config.rate_max_messages:
        if current.window_notified:
            return "silent", current
        return "notify_rate", replace(current, window_notified=True)
    counted = replace(
        current, window_count=current.window_count + 1, day_count=current.day_count + 1
    )
    return "allow", counted
