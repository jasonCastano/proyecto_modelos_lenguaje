"""Bienvenida de Valer-IA Caña (spec 018, research R1, ``prompts/welcome.md``).

La plantilla es determinista: no pasa por el modelo de lenguaje. Cada ``[U#]`` se resuelve
contra una unidad del corpus oro, y la sección «citations» declara qué datos debe contener esa
unidad (una prueba lo verifica).
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from ..tasks import TaskError
from .prompts import load_sections

LABEL = re.compile(r"\[(U\d+)\]")
CITATION_LINE = re.compile(r"^-\s*(U\d+)\s*:\s*(\S+)\s*(?:\|\s*(.*))?$")


def gold_units_path() -> Path:
    gold_dir = os.environ.get("PML_GOLD_DIR")
    base = Path(gold_dir) if gold_dir else PROJECT_ROOT / "data" / "gold"
    return base / "knowledge_units.jsonl"


def _find_units(unit_ids: set[str]) -> dict[str, dict[str, Any]]:
    found: dict[str, dict[str, Any]] = {}
    path = gold_units_path()
    if not path.is_file():
        return found
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not any(unit_id in line for unit_id in unit_ids - found.keys()):
                continue
            unit = json.loads(line)
            if unit.get("unit_id") in unit_ids:
                found[unit["unit_id"]] = unit
            if len(found) == len(unit_ids):
                break
    return found


def parse_citations(block: str) -> list[dict[str, Any]]:
    """``- U1: unit_id | dato | dato`` → etiqueta, unidad y datos que debe contener."""
    rows: list[dict[str, Any]] = []
    for line in block.splitlines():
        match = CITATION_LINE.match(line.strip())
        if match:
            facts = [fact.strip() for fact in (match.group(3) or "").split("|") if fact.strip()]
            rows.append({"label": match.group(1), "unit_id": match.group(2), "facts": facts})
    return rows


@lru_cache(maxsize=2)
def load_welcome(project_root: Path | None = None) -> dict[str, Any]:
    """Texto, versión y citas resueltas de la bienvenida."""
    version, sections = load_sections("welcome", project_root=project_root)
    text = sections.get("text", "").strip()
    assistant = sections.get("assistant", "").strip()
    declared = parse_citations(sections.get("citations", ""))
    if not text or not assistant or not declared:
        raise TaskError("invalid_config", "prompts/welcome.md incompleto.", task="welcome")
    labels = set(LABEL.findall(text))
    if labels - {row["label"] for row in declared}:
        raise TaskError(
            "invalid_config", "La bienvenida cita etiquetas sin unidad.", task="welcome"
        )
    units = _find_units({row["unit_id"] for row in declared})
    citations = []
    for row in declared:
        unit = units.get(row["unit_id"])
        if unit is None:
            raise TaskError(
                "invalid_config", f"La unidad {row['unit_id']} no está en el oro.", task="welcome"
            )
        citations.append(
            {
                "label": row["label"],
                "unit_id": row["unit_id"],
                "url": unit.get("url") or "",
                "title": unit.get("title") or "",
            }
        )
    return {"assistant": assistant, "version": version, "text": text, "citations": citations}
