"""Unit tests for the metrics layout constants and breakpoints."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.metrics_layout import (
    KPI_KEY,
    METRICS_BREAKPOINTS,
    METRICS_VIEW_KEY,
    VIEWPORTS,
    ViewportProfile,
    expected_columns,
    profile_by_name,
)


def test_long_values_keep_all_digits() -> None:
    from app import _money

    assert _money(1_447_841) == "1.447.841"
    assert _money(1_000_109) == "1.000.109"


def test_container_keys_are_stable() -> None:
    assert KPI_KEY == "metrics-kpis"
    assert METRICS_VIEW_KEY == "metrics-view"
    assert METRICS_BREAKPOINTS == {"wide": 1200, "compact": 640}


@pytest.mark.parametrize(
    ("width", "columns"),
    [
        (360, 1),
        (390, 1),
        (640, 1),
        (641, 2),
        (768, 2),
        (1024, 2),
        (1199, 2),
        (1200, 4),
        (1440, 4),
        (1920, 4),
    ],
)
def test_expected_columns_follow_breakpoints(width: int, columns: int) -> None:
    assert expected_columns(width) == columns


def test_viewport_matrix_is_complete() -> None:
    assert len(VIEWPORTS) == 7
    assert [profile.name for profile in VIEWPORTS] == [
        "movil-pequeno",
        "movil",
        "tableta-vertical",
        "tableta-horizontal",
        "escritorio",
        "escritorio-amplio",
        "zoom-200",
    ]
    assert all(isinstance(profile, ViewportProfile) for profile in VIEWPORTS)
    assert VIEWPORTS[0].sidebar_open is False
    assert VIEWPORTS[2].sidebar_open is True
    assert VIEWPORTS[-1].zoom == 2.0
    assert VIEWPORTS[-1].device_scale_factor == 2


def test_each_viewport_declares_expected_columns() -> None:
    expected = {
        "movil-pequeno": 1,
        "movil": 1,
        "tableta-vertical": 2,
        "tableta-horizontal": 2,
        "escritorio": 4,
        "escritorio-amplio": 4,
        "zoom-200": 2,
    }
    assert {profile.name: profile.expected_columns for profile in VIEWPORTS} == expected


def test_profile_lookup() -> None:
    profile = profile_by_name("escritorio")
    assert profile.width == 1440
    assert profile.height == 900
    with pytest.raises(KeyError):
        profile_by_name("desconocido")
