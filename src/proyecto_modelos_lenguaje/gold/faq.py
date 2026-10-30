"""Deterministic FAQ seed generation."""

from __future__ import annotations

from .models import CoverageEntry, Entity, FAQSeed, KnowledgeUnit, Topic, make_seed_id
from .text import normalize_for_hash


def build_faq_seeds(
    units: list[KnowledgeUnit],
    coverage_entries: list[CoverageEntry],
    topics: list[Topic],
    entities: list[Entity],
) -> list[FAQSeed]:
    by_question: dict[str, FAQSeed] = {}
    unit_by_topic: dict[str, list[KnowledgeUnit]] = {}
    unit_by_item: dict[str, list[KnowledgeUnit]] = {}
    for unit in units:
        unit_by_topic.setdefault(unit.topic_id, []).append(unit)
        for item_id in unit.coverage_item_ids:
            unit_by_item.setdefault(item_id, []).append(unit)

    def add(
        question: str, topic_id: str, item_id: str | None, evidence: list[str], status: str
    ) -> None:
        key = normalize_for_hash(question)
        if key in by_question or not evidence:
            return
        by_question[key] = FAQSeed(
            schema_version="1.0",
            seed_id=make_seed_id(question),
            question=question,
            topic_id=topic_id,
            coverage_item_id=item_id,
            evidence_unit_ids=sorted(set(evidence))[:5],
            status=status,
        )

    for entry in coverage_entries:
        item_units = unit_by_item.get(entry.item_id, [])
        if not item_units:
            continue
        status = "ready" if entry.status == "covered" else "review"
        add(
            f"¿Qué información tiene Manuelita sobre {entry.name.lower()}?",
            item_units[0].topic_id,
            entry.item_id,
            [unit.unit_id for unit in item_units],
            status,
        )

    for topic in topics:
        topic_units = unit_by_topic.get(topic.topic_id, [])
        if not topic_units or topic.topic_id == "general":
            continue
        add(
            f"¿Qué hace Manuelita en {topic.title.lower()}?",
            topic.topic_id,
            topic.coverage_item_ids[0] if topic.coverage_item_ids else None,
            [unit.unit_id for unit in topic_units],
            "ready" if topic.status == "covered" else "review",
        )

    entity_units: dict[str, list[KnowledgeUnit]] = {}
    for unit in units:
        for entity_id in unit.entity_ids:
            entity_units.setdefault(entity_id, []).append(unit)
    for entity in entities:
        if entity.canonical_name == "Manuelita":
            continue
        evidence = entity_units.get(entity.entity_id, [])
        if not evidence:
            continue
        add(
            f"¿Qué relación tiene {entity.canonical_name} con Manuelita?",
            evidence[0].topic_id,
            None,
            [unit.unit_id for unit in evidence],
            "review",
        )
    return sorted(by_question.values(), key=lambda seed: seed.seed_id)
