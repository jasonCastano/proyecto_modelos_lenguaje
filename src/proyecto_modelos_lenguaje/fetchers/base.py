"""Fetcher protocol shared by HTTP, browser and API adapters."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable


@dataclass(frozen=True, slots=True)
class FetchResponse:
    url: str
    final_url: str
    status: int
    headers: Mapping[str, str] = field(default_factory=dict)
    body: bytes = b""
    error: str | None = None

    @property
    def ok(self) -> bool:
        return self.error is None and 200 <= self.status < 300


@runtime_checkable
class Fetcher(Protocol):
    async def fetch(self, url: str, *, timeout: float | None = None) -> FetchResponse: ...

    async def aclose(self) -> None: ...
