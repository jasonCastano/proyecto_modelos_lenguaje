"""Schema loaders for gold contract tests."""

from __future__ import annotations

import json
from pathlib import Path

CONTRACTS = Path(__file__).resolve().parents[3] / "specs" / "004-gold-medallion-layer" / "contracts"


def load_schema(name: str) -> dict:
    return json.loads((CONTRACTS / name).read_text(encoding="utf-8"))
