"""Unit tests for conflict detection."""

from __future__ import annotations

from proyecto_modelos_lenguaje.gold.conflicts import detect_conflicts
from proyecto_modelos_lenguaje.gold.models import (
    Evidence,
    Fact,
    KnowledgeUnit,
    make_fact_id,
    make_unit_id,
)


def _evidence(authority: str, url: str) -> Evidence:
    return Evidence(
        chunk_id="doc_0123456789abcdef-s000-c0000",
        doc_id="doc_0123456789abcdef",
        artifact_id=1,
        content_hash="a" * 64,
        url=url,
        title="Manuelita",
        section_path=["Manuelita"],
        page_start=None,
        page_end=None,
        time_start=None,
        time_end=None,
        authority=authority,
        published_at=None,
        retrieved_at="2026-10-30T00:00:00Z",
        score=0.9,
    )


def _unit(index: int, text: str, authority: str = "first_party") -> KnowledgeUnit:
    doc_id = "doc_0123456789abcdef"
    unit_id = make_unit_id(doc_id, "doc_0123456789abcdef-s000-c0000", index)
    return KnowledgeUnit(
        schema_version="1.0",
        unit_id=unit_id,
        topic_id="productos",
        topic_title="Productos",
        text=text,
        unit_type="fact",
        language="es",
        authority=authority,
        confidence=0.9,
        status="current",
        entity_ids=["ent_0123456789abcdef"],
        coverage_item_ids=["O-01"],
        evidence=[_evidence(authority, "https://example.test")],
        fact_id=None,
        text_hash="b" * 64,
        quality_flags=[],
        url="https://example.test",
        title="Manuelita",
        section_path=["Productos"],
        page_start=None,
        page_end=None,
        time_start=None,
        time_end=None,
        published_at=None,
        retrieved_at="2026-10-30T00:00:00Z",
        license_note="Uso académico.",
    )


def _fact(unit: KnowledgeUnit, value: str, year: int, authority: str) -> Fact:
    fact_id = make_fact_id("ent_0123456789abcdef", "capacidad", value, unit.unit_id)
    return Fact(
        schema_version="1.0",
        fact_id=fact_id,
        subject_id="ent_0123456789abcdef",
        subject_label="Manuelita",
        attribute="capacidad",
        value=value,
        value_normalized=value,
        unit="toneladas",
        year=year,
        unit_id=unit.unit_id,
        evidence=unit.evidence,
        status="current",
    )


def test_official_source_wins() -> None:
    official = _unit(1, "Manuelita tiene 125.000 toneladas.", "first_party")
    third = _unit(2, "Manuelita tiene 120.000 toneladas.", "third_party")
    facts = [
        _fact(official, "125.000", 2024, "first_party"),
        _fact(third, "120.000", 2023, "third_party"),
    ]
    conflicts = detect_conflicts(facts, {official.unit_id: official, third.unit_id: third})
    assert len(conflicts) == 1
    assert conflicts[0].status == "resolved"
    assert conflicts[0].reason == "official_source"
    assert conflicts[0].preferred_unit_id == official.unit_id
    assert third.status == "historical"


def test_unresolved_conflict_is_disputed() -> None:
    left = _unit(1, "Manuelita tiene 125.000 toneladas.", "first_party")
    right = _unit(2, "Manuelita tiene 120.000 toneladas.", "first_party")
    facts = [
        _fact(left, "125.000", 2024, "first_party"),
        _fact(right, "120.000", 2024, "first_party"),
    ]
    conflicts = detect_conflicts(facts, {left.unit_id: left, right.unit_id: right})
    assert conflicts[0].status == "disputed"
    assert conflicts[0].preferred_unit_id is None
    assert left.status == "disputed"
    assert right.status == "disputed"
