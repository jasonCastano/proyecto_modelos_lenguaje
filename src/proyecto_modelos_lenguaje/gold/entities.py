"""Entity assignment and canonical entity payloads."""

from __future__ import annotations

from .models import Entity, KnowledgeUnit
from .taxonomy import Taxonomy
from .units import attach_entities


def build_entities(units: list[KnowledgeUnit], taxonomy: Taxonomy) -> list[Entity]:
    attach_entities(units, taxonomy)
    unit_ids: dict[str, list[str]] = {}
    descriptions: dict[str, str] = {}
    for unit in units:
        for entity_id in unit.entity_ids:
            unit_ids.setdefault(entity_id, []).append(unit.unit_id)
            descriptions.setdefault(entity_id, unit.text[:240])
    return taxonomy.entity_payloads(unit_ids, descriptions)
