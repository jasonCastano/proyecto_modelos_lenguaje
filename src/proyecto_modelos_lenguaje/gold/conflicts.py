"""Conflict detection and resolution over extracted facts."""

from __future__ import annotations

from collections import defaultdict

from .models import (
    Conflict,
    ConflictValue,
    Fact,
    KnowledgeUnit,
    QualityFlag,
    make_conflict_id,
)

_AUTHORITY = {"first_party": 0, "open_data": 1, "third_party": 2}


def _authority_rank(value: str) -> int:
    return _AUTHORITY.get(value, 3)


def _fact_year(fact: Fact) -> int:
    return fact.year or 0


def detect_conflicts(facts: list[Fact], units: dict[str, KnowledgeUnit]) -> list[Conflict]:
    groups: dict[tuple[str, str], list[Fact]] = defaultdict(list)
    for fact in facts:
        groups[(fact.subject_id, fact.attribute)].append(fact)

    conflicts: list[Conflict] = []
    for (subject_id, attribute), group in sorted(groups.items()):
        distinct = {fact.value_normalized for fact in group}
        if len(distinct) < 2:
            continue
        ordered = sorted(
            group,
            key=lambda fact: (
                _authority_rank(fact.evidence[0].authority),
                -_fact_year(fact),
                -len(fact.evidence),
                fact.unit_id,
            ),
        )
        top = ordered[0]
        second = ordered[1]
        top_rank = _authority_rank(top.evidence[0].authority)
        second_rank = _authority_rank(second.evidence[0].authority)
        if top_rank < second_rank:
            status, reason = "resolved", "official_source"
        elif _fact_year(top) > _fact_year(second):
            status, reason = "resolved", "newer_date"
        elif len(top.evidence) > len(second.evidence):
            status, reason = "resolved", "more_evidence"
        else:
            status, reason = "disputed", "unresolved"
        values = [
            ConflictValue(
                value=fact.value,
                value_normalized=fact.value_normalized,
                unit=fact.unit,
                year=fact.year,
                authority=fact.evidence[0].authority,
                unit_id=fact.unit_id,
                url=fact.evidence[0].url,
            )
            for fact in ordered
        ]
        conflicts.append(
            Conflict(
                schema_version="1.0",
                conflict_id=make_conflict_id(subject_id, attribute),
                subject_id=subject_id,
                attribute=attribute,
                values=values,
                preferred_unit_id=top.unit_id if status == "resolved" else None,
                status=status,
                reason=reason,
            )
        )
        the_units = [units[fact.unit_id] for fact in ordered if fact.unit_id in units]
        for unit in the_units:
            if QualityFlag.CONFLICTING.value not in unit.quality_flags:
                unit.quality_flags.append(QualityFlag.CONFLICTING.value)
            if status == "disputed":
                unit.status = "disputed"
            elif unit.unit_id == top.unit_id:
                unit.status = "current"
            else:
                unit.status = "historical"
    return sorted(conflicts, key=lambda item: item.conflict_id)
