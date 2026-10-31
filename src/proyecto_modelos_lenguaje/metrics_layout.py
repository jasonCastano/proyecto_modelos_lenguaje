"""Layout constants for the Metrics tab.

The module is deliberately dependency-free so the app, the visual audit and the
tests share the same viewport matrix and breakpoints.
"""

from __future__ import annotations

from dataclasses import dataclass

KPI_KEY = "metrics-kpis"
METRICS_VIEW_KEY = "metrics-view"
METRICS_BREAKPOINTS = {"wide": 1200, "compact": 640}


@dataclass(frozen=True, slots=True)
class ViewportProfile:
    """One viewport used to verify the Metrics tab."""

    name: str
    width: int
    height: int
    zoom: float = 1.0
    sidebar_open: bool = True
    device_scale_factor: int = 1

    @property
    def expected_columns(self) -> int:
        return expected_columns(self.width)


def expected_columns(width: int) -> int:
    """Return the KPI column count for a CSS viewport width."""
    if width >= METRICS_BREAKPOINTS["wide"]:
        return 4
    if width > METRICS_BREAKPOINTS["compact"]:
        return 2
    return 1


VIEWPORTS: tuple[ViewportProfile, ...] = (
    ViewportProfile("movil-pequeno", 360, 640, sidebar_open=False),
    ViewportProfile("movil", 390, 844, sidebar_open=False),
    ViewportProfile("tableta-vertical", 768, 1024),
    ViewportProfile("tableta-horizontal", 1024, 768),
    ViewportProfile("escritorio", 1440, 900),
    ViewportProfile("escritorio-amplio", 1920, 1080),
    ViewportProfile(
        "zoom-200",
        683,
        384,
        zoom=2.0,
        device_scale_factor=2,
    ),
)


def profile_by_name(name: str) -> ViewportProfile:
    """Return a viewport profile by name; raise ``KeyError`` when unknown."""
    for profile in VIEWPORTS:
        if profile.name == name:
            return profile
    raise KeyError(name)
