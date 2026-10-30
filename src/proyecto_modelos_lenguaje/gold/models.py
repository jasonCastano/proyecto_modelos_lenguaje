"""Data model for the gold layer."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

LICENSE_NOTE = (
    "Uso académico. Contenido público de su fuente original; se cita la URL y la fecha de captura."
)


class UnitType(StrEnum):
    PASSAGE = "passage"
    FACT = "fact"


class UnitStatus(StrEnum):
    CURRENT = "current"
    HISTORICAL = "historical"
    DISPUTED = "disputed"
    AMBIGUOUS = "ambiguous"


class EntityType(StrEnum):
    COMPANY = "company"
    SUBSIDIARY = "subsidiary"
    BRAND = "brand"
    PRODUCT = "product"
    SITE = "site"
    PERSON = "person"
    CERTIFICATION = "certification"
    OTHER = "other"


class ConflictStatus(StrEnum):
    RESOLVED = "resolved"
    DISPUTED = "disputed"


class CoverageStatus(StrEnum):
    COVERED = "covered"
    PARTIAL = "partial"
    MISSING = "missing"


class FAQStatus(StrEnum):
    READY = "ready"
    REVIEW = "review"
    MISSING_EVIDENCE = "missing_evidence"


class QualityFlag(StrEnum):
    TOPIC_UNCERTAIN = "topic_uncertain"
    AMBIGUOUS_VALUE = "ambiguous_value"
    CONFLICTING = "conflicting"
    SHORT_UNIT = "short_unit"
    DUPLICATE_UNIT = "duplicate_unit"
    ENGLISH_CONTENT = "english_content"
    LOW_AUTHORITY = "low_authority"


def _hash(prefix: str, value: str, length: int = 16) -> str:
    return f"{prefix}_{hashlib.sha256(value.encode()).hexdigest()[:length]}"


def make_unit_id(doc_id: str, chunk_id: str, index: int) -> str:
    return _hash("unit", f"{doc_id}:{chunk_id}:{index}")


def make_fact_id(subject_id: str, attribute: str, value: str, unit_id: str) -> str:
    return _hash("fact", f"{subject_id}:{attribute}:{value}:{unit_id}")


def make_entity_id(canonical_name: str) -> str:
    return _hash("ent", canonical_name.strip().lower())


def make_conflict_id(subject_id: str, attribute: str) -> str:
    return _hash("conf", f"{subject_id}:{attribute}")


def make_seed_id(question: str) -> str:
    return _hash("faq", question.strip().lower())


@dataclass(slots=True)
class Evidence:
    chunk_id: str
    doc_id: str
    artifact_id: int
    content_hash: str
    url: str
    title: str
    section_path: list[str]
    page_start: int | None
    page_end: int | None
    time_start: float | None
    time_end: float | None
    authority: str
    published_at: str | None
    retrieved_at: str
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "url": self.url,
            "title": self.title,
            "section_path": list(self.section_path),
            "page_start": self.page_start,
            "page_end": self.page_end,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "authority": self.authority,
            "published_at": self.published_at,
            "retrieved_at": self.retrieved_at,
            "score": self.score,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Evidence:
        return cls(**payload)


@dataclass(slots=True)
class KnowledgeUnit:
    schema_version: str
    unit_id: str
    topic_id: str
    topic_title: str
    text: str
    unit_type: str
    language: str
    authority: str
    confidence: float
    status: str
    entity_ids: list[str]
    coverage_item_ids: list[str]
    evidence: list[Evidence]
    fact_id: str | None
    text_hash: str
    quality_flags: list[str]
    url: str
    title: str
    section_path: list[str]
    page_start: int | None
    page_end: int | None
    time_start: float | None
    time_end: float | None
    published_at: str | None
    retrieved_at: str
    license_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "unit_id": self.unit_id,
            "topic_id": self.topic_id,
            "topic_title": self.topic_title,
            "text": self.text,
            "unit_type": self.unit_type,
            "language": self.language,
            "authority": self.authority,
            "confidence": self.confidence,
            "status": self.status,
            "entity_ids": list(self.entity_ids),
            "coverage_item_ids": list(self.coverage_item_ids),
            "evidence": [item.to_dict() for item in self.evidence],
            "fact_id": self.fact_id,
            "text_hash": self.text_hash,
            "quality_flags": list(self.quality_flags),
            "url": self.url,
            "title": self.title,
            "section_path": list(self.section_path),
            "page_start": self.page_start,
            "page_end": self.page_end,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "published_at": self.published_at,
            "retrieved_at": self.retrieved_at,
            "license_note": self.license_note,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> KnowledgeUnit:
        data = dict(payload)
        data["evidence"] = [Evidence.from_dict(item) for item in data["evidence"]]
        return cls(**data)


@dataclass(slots=True)
class Fact:
    schema_version: str
    fact_id: str
    subject_id: str
    subject_label: str
    attribute: str
    value: str
    value_normalized: str
    unit: str | None
    year: int | None
    unit_id: str
    evidence: list[Evidence]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "fact_id": self.fact_id,
            "subject_id": self.subject_id,
            "subject_label": self.subject_label,
            "attribute": self.attribute,
            "value": self.value,
            "value_normalized": self.value_normalized,
            "unit": self.unit,
            "year": self.year,
            "unit_id": self.unit_id,
            "evidence": [item.to_dict() for item in self.evidence],
            "status": self.status,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Fact:
        data = dict(payload)
        data["evidence"] = [Evidence.from_dict(item) for item in data["evidence"]]
        return cls(**data)


@dataclass(slots=True)
class Entity:
    schema_version: str
    entity_id: str
    canonical_name: str
    aliases: list[str]
    entity_type: str
    description: str | None
    unit_ids: list[str]
    coverage_item_ids: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "aliases": list(self.aliases),
            "entity_type": self.entity_type,
            "description": self.description,
            "unit_ids": list(self.unit_ids),
            "coverage_item_ids": list(self.coverage_item_ids),
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> Entity:
        return cls(**payload)


@dataclass(slots=True)
class Topic:
    topic_id: str
    title: str
    description: str
    coverage_item_ids: list[str]
    order: int
    unit_count: int = 0
    status: str = "empty"


@dataclass(slots=True)
class ConflictValue:
    value: str
    value_normalized: str
    unit: str | None
    year: int | None
    authority: str
    unit_id: str
    url: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "value_normalized": self.value_normalized,
            "unit": self.unit,
            "year": self.year,
            "authority": self.authority,
            "unit_id": self.unit_id,
            "url": self.url,
        }


@dataclass(slots=True)
class Conflict:
    schema_version: str
    conflict_id: str
    subject_id: str
    attribute: str
    values: list[ConflictValue]
    preferred_unit_id: str | None
    status: str
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "conflict_id": self.conflict_id,
            "subject_id": self.subject_id,
            "attribute": self.attribute,
            "values": [item.to_dict() for item in self.values],
            "preferred_unit_id": self.preferred_unit_id,
            "status": self.status,
            "reason": self.reason,
        }


@dataclass(slots=True)
class CoverageEntry:
    item_id: str
    name: str
    category: str
    status: str
    unit_ids: list[str]
    authority_counts: dict[str, int]
    conflict_ids: list[str]
    gap_reason: str | None
    recommendation: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "name": self.name,
            "category": self.category,
            "status": self.status,
            "unit_ids": list(self.unit_ids),
            "authority_counts": dict(self.authority_counts),
            "conflict_ids": list(self.conflict_ids),
            "gap_reason": self.gap_reason,
            "recommendation": self.recommendation,
        }


@dataclass(slots=True)
class ContextBlock:
    unit_id: str
    text: str
    citation: str
    tokens: int
    topic_id: str
    authority: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "unit_id": self.unit_id,
            "text": self.text,
            "citation": self.citation,
            "tokens": self.tokens,
            "topic_id": self.topic_id,
            "authority": self.authority,
        }


@dataclass(slots=True)
class ContextPack:
    schema_version: str
    pack_id: str
    task: str
    budget_tokens: int
    tokens: int
    unit_ids: list[str]
    blocks: list[ContextBlock]
    coverage_item_ids: list[str]
    omitted_units: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "pack_id": self.pack_id,
            "task": self.task,
            "budget_tokens": self.budget_tokens,
            "tokens": self.tokens,
            "unit_ids": list(self.unit_ids),
            "blocks": [block.to_dict() for block in self.blocks],
            "coverage_item_ids": list(self.coverage_item_ids),
            "omitted_units": self.omitted_units,
        }


@dataclass(slots=True)
class FAQSeed:
    schema_version: str
    seed_id: str
    question: str
    topic_id: str
    coverage_item_id: str | None
    evidence_unit_ids: list[str]
    status: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "seed_id": self.seed_id,
            "question": self.question,
            "topic_id": self.topic_id,
            "coverage_item_id": self.coverage_item_id,
            "evidence_unit_ids": list(self.evidence_unit_ids),
            "status": self.status,
        }


@dataclass(slots=True)
class GoldManifest:
    run_id: str
    config_hash: str
    taxonomy_hash: str
    created_at: str
    input_documents: int
    input_chunks: int
    knowledge_units: int
    facts: int
    entities: int
    conflicts: int
    faq_seeds: int
    files: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "config_hash": self.config_hash,
            "taxonomy_hash": self.taxonomy_hash,
            "created_at": self.created_at,
            "input_documents": self.input_documents,
            "input_chunks": self.input_chunks,
            "knowledge_units": self.knowledge_units,
            "facts": self.facts,
            "entities": self.entities,
            "conflicts": self.conflicts,
            "faq_seeds": self.faq_seeds,
            "files": list(self.files),
        }


@dataclass(slots=True)
class GoldReport:
    schema_version: str
    run_id: str
    started_at: str
    finished_at: str
    status: str
    config_hash: str
    input_documents: int
    input_chunks: int
    processed: int
    skipped: int
    failed: int
    units: int
    facts: int
    entities: int
    conflicts: int
    coverage: dict[str, int]
    context_packs: int
    tokens: int
    duration_seconds: float
    quality_flags: dict[str, int]
    skip_reasons: dict[str, int]
    failure_reasons: dict[str, int]
    report_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "config_hash": self.config_hash,
            "input_documents": self.input_documents,
            "input_chunks": self.input_chunks,
            "processed": self.processed,
            "skipped": self.skipped,
            "failed": self.failed,
            "units": self.units,
            "facts": self.facts,
            "entities": self.entities,
            "conflicts": self.conflicts,
            "coverage": dict(self.coverage),
            "context_packs": self.context_packs,
            "tokens": self.tokens,
            "duration_seconds": self.duration_seconds,
            "quality_flags": dict(self.quality_flags),
            "skip_reasons": dict(self.skip_reasons),
            "failure_reasons": dict(self.failure_reasons),
            "report_paths": list(self.report_paths),
        }


def validate_unit(unit: KnowledgeUnit) -> None:
    if not unit.unit_id.startswith("unit_") or len(unit.unit_id) != 21:
        raise ValueError(f"invalid unit_id: {unit.unit_id}")
    if not unit.text.strip():
        raise ValueError(f"{unit.unit_id}: empty text")
    if not unit.evidence:
        raise ValueError(f"{unit.unit_id}: evidence is required")
    if not unit.topic_id or not unit.topic_title:
        raise ValueError(f"{unit.unit_id}: topic is required")
    if not unit.url or not unit.title or not unit.section_path:
        raise ValueError(f"{unit.unit_id}: lineage is incomplete")


def validate_pack(pack: ContextPack) -> None:
    if pack.tokens > pack.budget_tokens:
        raise ValueError(f"{pack.pack_id}: tokens exceed budget")
    if len(set(pack.unit_ids)) != len(pack.unit_ids):
        raise ValueError(f"{pack.pack_id}: duplicated units")
    for block in pack.blocks:
        if not block.citation:
            raise ValueError(f"{pack.pack_id}: block without citation")
