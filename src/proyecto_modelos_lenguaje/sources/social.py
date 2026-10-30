"""Public social profile discovery (seeds only)."""

from __future__ import annotations

from dataclasses import dataclass

from .base import SeedOnlySource


@dataclass(slots=True)
class SocialSource(SeedOnlySource):
    """Profiles are captured as single public pages; no link following."""
