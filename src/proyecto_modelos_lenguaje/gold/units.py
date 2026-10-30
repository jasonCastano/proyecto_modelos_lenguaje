"""Extractive knowledge units and duplicate consolidation."""

from __future__ import annotations

import hashlib

from .config import UnitsConfig
from .inputs import SilverChunk, SilverDocument
from .models import (
    Evidence,
    KnowledgeUnit,
    QualityFlag,
    UnitType,
    make_unit_id,
)
from .taxonomy import Taxonomy
from .text import jaccard, normalize_for_hash, shingles, split_sentences


def _evidence(chunk: SilverChunk) -> Evidence:
    score = 0.95 if chunk.authority == "first_party" else 0.7
    return Evidence(
        chunk_id=chunk.chunk_id,
        doc_id=chunk.doc_id,
        artifact_id=chunk.artifact_id,
        content_hash=chunk.content_hash,
        url=chunk.url,
        title=chunk.title,
        section_path=list(chunk.section_path),
        page_start=chunk.page_start,
        page_end=chunk.page_end,
        time_start=chunk.time_start,
        time_end=chunk.time_end,
        authority=chunk.authority,
        published_at=None,
        retrieved_at=chunk.retrieved_at,
        score=score,
    )


def build_units(
    document: SilverDocument,
    chunks: list[SilverChunk],
    taxonomy: Taxonomy,
    config: UnitsConfig,
) -> list[KnowledgeUnit]:
    units: list[KnowledgeUnit] = []
    for chunk in chunks:
        sentences = split_sentences(
            chunk.text,
            min_chars=config.min_sentence_chars,
            max_chars=config.max_unit_chars,
        )
        for index, sentence in enumerate(sentences):
            match = taxonomy.classify(sentence)
            flags: list[str] = []
            if match.uncertain:
                flags.append(QualityFlag.TOPIC_UNCERTAIN.value)
            if len(sentence) < config.min_sentence_chars:
                flags.append(QualityFlag.SHORT_UNIT.value)
            if document.language == "en":
                flags.append(QualityFlag.ENGLISH_CONTENT.value)
            if document.authority == "third_party":
                flags.append(QualityFlag.LOW_AUTHORITY.value)
            units.append(
                KnowledgeUnit(
                    schema_version="1.0",
                    unit_id=make_unit_id(document.doc_id, chunk.chunk_id, index),
                    topic_id=match.topic.topic_id,
                    topic_title=match.topic.title,
                    text=sentence,
                    unit_type=UnitType.PASSAGE.value,
                    language=document.language,
                    authority=document.authority,
                    confidence=0.9 if not match.uncertain else 0.5,
                    status="current",
                    entity_ids=[],
                    coverage_item_ids=taxonomy.assign_items(match.topic, sentence),
                    evidence=[_evidence(chunk)],
                    fact_id=None,
                    text_hash=hashlib.sha256(normalize_for_hash(sentence).encode()).hexdigest(),
                    quality_flags=flags,
                    url=chunk.url,
                    title=document.title,
                    section_path=list(chunk.section_path),
                    page_start=chunk.page_start,
                    page_end=chunk.page_end,
                    time_start=chunk.time_start,
                    time_end=chunk.time_end,
                    published_at=document.published_at,
                    retrieved_at=chunk.retrieved_at,
                    license_note=chunk.license_note,
                )
            )
    return units


def _merge_evidence(left: KnowledgeUnit, right: KnowledgeUnit) -> list[Evidence]:
    evidence = {item.chunk_id: item for item in left.evidence}
    for item in right.evidence:
        evidence.setdefault(item.chunk_id, item)
    return [evidence[key] for key in sorted(evidence)]


def deduplicate_units(
    units: list[KnowledgeUnit],
    *,
    threshold: float = 0.90,
    shingle_size: int = 5,
) -> list[KnowledgeUnit]:
    """Merge exact and near-duplicate units, preserving every evidence."""
    unique: dict[str, KnowledgeUnit] = {}
    for unit in sorted(units, key=lambda item: item.unit_id):
        existing = unique.get(unit.text_hash)
        if existing is None:
            unique[unit.text_hash] = unit
        else:
            existing.evidence = _merge_evidence(existing, unit)

    candidates = sorted(unique.values(), key=lambda item: item.unit_id)
    shingle_sets = {unit.unit_id: shingles(unit.text, shingle_size) for unit in candidates}
    removed: set[str] = set()
    for index, left in enumerate(candidates):
        if left.unit_id in removed:
            continue
        for right in candidates[index + 1 :]:
            if right.unit_id in removed or left.topic_id != right.topic_id:
                continue
            ratio = len(left.text) / max(1, len(right.text))
            if ratio < 0.6 or ratio > 1.67:
                continue
            if jaccard(shingle_sets[left.unit_id], shingle_sets[right.unit_id]) >= threshold:
                left.evidence = _merge_evidence(left, right)
                removed.add(right.unit_id)
    return [unit for unit in candidates if unit.unit_id not in removed]


def attach_entities(units: list[KnowledgeUnit], taxonomy: Taxonomy) -> None:
    for unit in units:
        specs = taxonomy.find_entities(unit.text)
        unit.entity_ids = sorted({spec.entity_id for spec in specs})


def attach_fact(unit: KnowledgeUnit, fact_id: str | None) -> None:
    if fact_id:
        unit.unit_type = UnitType.FACT.value
        unit.fact_id = fact_id
    else:
        unit.unit_type = UnitType.PASSAGE.value
        unit.fact_id = None
