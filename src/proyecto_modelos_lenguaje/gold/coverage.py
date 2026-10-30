"""Coverage matrix for the 24 required information items."""

from __future__ import annotations

from collections import Counter
from typing import Any

from .config import CoverageConfig
from .models import Conflict, CoverageEntry, KnowledgeUnit
from .taxonomy import Taxonomy

_SOURCE_HINTS = {
    "identity": "Sitio oficial, informe de gestión o comunicado corporativo.",
    "offer": "Catálogo, ficha técnica o página de producto oficial.",
    "digital_presence": "Sitio oficial, canal de YouTube o sala de prensa.",
    "hard_data": "Informe financiero, Supersociedades, SECOP o datos abiertos.",
}


def build_coverage(
    units: list[KnowledgeUnit],
    conflicts: list[Conflict],
    taxonomy: Taxonomy,
    config: CoverageConfig,
) -> list[CoverageEntry]:
    by_item: dict[str, list[KnowledgeUnit]] = {}
    for item_id in taxonomy.coverage_items:
        by_item[item_id] = []
    for unit in units:
        for item_id in unit.coverage_item_ids:
            by_item.setdefault(item_id, []).append(unit)

    conflict_by_unit: dict[str, list[str]] = {}
    for conflict in conflicts:
        for value in conflict.values:
            conflict_by_unit.setdefault(value.unit_id, []).append(conflict.conflict_id)

    entries: list[CoverageEntry] = []
    for item_id in sorted(by_item):
        item = taxonomy.coverage_items[item_id]
        item_units = sorted(by_item[item_id], key=lambda unit: unit.unit_id)
        authority = Counter(unit.authority for unit in item_units)
        official = authority.get("first_party", 0)
        if not item_units:
            status = "missing"
            gap = "Sin unidades verificables en la base de conocimiento."
        elif (
            len(item_units) >= config.covered_min_units and official >= config.covered_min_official
        ):
            status = "covered"
            gap = None
        else:
            status = "partial"
            if official == 0:
                gap = "Solo hay evidencia de fuentes de terceros."
            else:
                gap = f"Evidencia insuficiente: {len(item_units)} unidades."
        conflicts_for_item = sorted(
            {
                conflict_id
                for unit in item_units
                for conflict_id in conflict_by_unit.get(unit.unit_id, [])
            }
        )
        entries.append(
            CoverageEntry(
                item_id=item_id,
                name=item.name,
                category=item.category,
                status=status,
                unit_ids=[unit.unit_id for unit in item_units],
                authority_counts=dict(sorted(authority.items())),
                conflict_ids=conflicts_for_item,
                gap_reason=gap,
                recommendation=None if status == "covered" else _SOURCE_HINTS.get(item.category),
            )
        )
    return entries


def coverage_summary(entries: list[CoverageEntry]) -> dict[str, int]:
    counts = Counter(entry.status for entry in entries)
    return {
        "covered": counts.get("covered", 0),
        "partial": counts.get("partial", 0),
        "missing": counts.get("missing", 0),
    }


def render_coverage_markdown(entries: list[CoverageEntry], run_id: str) -> str:
    summary = coverage_summary(entries)
    total = len(entries)
    covered_pct = (summary["covered"] / total * 100) if total else 0.0
    lines = [
        f"# Cobertura de los 24 ítems — {run_id}",
        "",
        f"- Cubiertos: {summary['covered']}",
        f"- Parciales: {summary['partial']}",
        f"- Faltantes: {summary['missing']}",
        f"- Total: {total}",
        f"- Porcentaje cubierto: {covered_pct:.1f}%",
        "",
        "| Ítem | Categoría | Estado | Unidades | Fuentes oficiales | Conflictos |",
        "|------|-----------|--------|---------:|------------------:|-----------:|",
    ]
    for entry in entries:
        official = entry.authority_counts.get("first_party", 0)
        lines.append(
            f"| {entry.item_id} | {entry.category} | {entry.status} | "
            f"{len(entry.unit_ids)} | {official} | {len(entry.conflict_ids)} |"
        )
    missing = [entry for entry in entries if entry.status != "covered"]
    if missing:
        lines.extend(["", "## Vacíos priorizados", ""])
        for entry in sorted(missing, key=lambda item: (item.status != "missing", item.item_id)):
            lines.append(
                f"- **{entry.item_id} — {entry.name}** ({entry.status}): "
                f"{entry.gap_reason or 'Revisar evidencia.'} "
                f"{entry.recommendation or ''}".strip()
            )
    return "\n".join(lines) + "\n"


def coverage_payload(entries: list[CoverageEntry], run_id: str) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "run_id": run_id,
        "items": [entry.to_dict() for entry in entries],
    }
