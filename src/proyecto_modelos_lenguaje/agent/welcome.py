"""Bienvenida de Valer-IA Caña (spec 018, research R1, ``prompts/welcome.md``).

La plantilla es determinista: no pasa por el modelo de lenguaje. Cada ``[U#]`` se resuelve
contra una unidad del corpus oro, y la sección «citations» declara qué datos debe contener esa
unidad (una prueba lo verifica).
"""

from __future__ import annotations

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


def parse_citations(block: str) -> list[dict[str, Any]]:
    """``- U1: unit_id | url | título | dato | dato`` → etiqueta, unidad, URL, título y datos."""
    rows: list[dict[str, Any]] = []
    for line in block.splitlines():
        match = CITATION_LINE.match(line.strip())
        if not match:
            continue
        fields = [field.strip() for field in (match.group(3) or "").split("|") if field.strip()]
        url = fields[0] if fields and fields[0].startswith("http") else ""
        rest = fields[1:] if url else fields
        title = rest[0] if url and rest else ""
        facts = rest[1:] if url and rest else rest
        rows.append(
            {
                "label": match.group(1),
                "unit_id": match.group(2),
                "url": url,
                "title": title,
                "facts": facts,
            }
        )
    return rows


@lru_cache(maxsize=2)
def load_welcome(project_root: Path | None = None) -> dict[str, Any]:
    """Texto, versión y citas de la bienvenida (no lee el oro: las citas vienen declaradas)."""
    version, sections = load_sections("welcome", project_root=project_root)
    text = sections.get("text", "").strip()
    assistant = sections.get("assistant", "").strip()
    declared = parse_citations(sections.get("citations", ""))
    if not text or not assistant or not declared:
        raise TaskError("invalid_config", "prompts/welcome.md incompleto.", task="welcome")
    labels = set(LABEL.findall(text))
    if labels - {row["label"] for row in declared} or any(not row["url"] for row in declared):
        raise TaskError("invalid_config", "La bienvenida tiene citas incompletas.", task="welcome")
    citations = [
        {"label": row["label"], "unit_id": row["unit_id"], "url": row["url"], "title": row["title"]}
        for row in declared
    ]
    return {"assistant": assistant, "version": version, "text": text, "citations": citations}
