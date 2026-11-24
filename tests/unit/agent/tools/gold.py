"""Marca para pruebas que leen la capa oro real (Git LFS; el CI no la descarga)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT

GOLD_UNITS = PROJECT_ROOT / "data" / "gold" / "knowledge_units.jsonl"


def gold_is_downloaded() -> bool:
    if not GOLD_UNITS.is_file():
        return False
    with GOLD_UNITS.open(encoding="utf-8") as handle:
        return not handle.read(200).startswith("version https://git-lfs")


requires_gold = pytest.mark.skipif(
    not gold_is_downloaded(), reason="Requiere la capa oro (Git LFS)."
)
