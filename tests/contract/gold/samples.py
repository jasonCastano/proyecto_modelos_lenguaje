"""Sample records for gold contract tests."""

from __future__ import annotations


def samples() -> dict[str, dict]:
    evidence = {
        "chunk_id": "doc_0123456789abcdef-s000-c0000",
        "doc_id": "doc_0123456789abcdef",
        "artifact_id": 1,
        "content_hash": "a" * 64,
        "url": "https://www.manuelita.com/",
        "title": "Manuelita",
        "section_path": ["Manuelita"],
        "page_start": None,
        "page_end": None,
        "time_start": None,
        "time_end": None,
        "authority": "first_party",
        "published_at": None,
        "retrieved_at": "2026-10-30T00:00:00Z",
        "score": 0.9,
    }
    entity = {
        "schema_version": "1.0",
        "entity_id": "ent_0123456789abcdef",
        "canonical_name": "Manuelita",
        "aliases": ["Ingenio Manuelita"],
        "entity_type": "company",
        "description": "Organización agroindustrial.",
        "unit_ids": ["unit_0123456789abcdef"],
        "coverage_item_ids": ["I-01"],
    }
    unit = {
        "schema_version": "1.0",
        "unit_id": "unit_0123456789abcdef",
        "topic_id": "identidad",
        "topic_title": "Identidad",
        "text": "Manuelita es una organización agroindustrial.",
        "unit_type": "passage",
        "language": "es",
        "authority": "first_party",
        "confidence": 0.9,
        "status": "current",
        "entity_ids": [entity["entity_id"]],
        "coverage_item_ids": ["I-01"],
        "evidence": [evidence],
        "fact_id": None,
        "text_hash": "b" * 64,
        "quality_flags": [],
        "url": evidence["url"],
        "title": evidence["title"],
        "section_path": evidence["section_path"],
        "page_start": None,
        "page_end": None,
        "time_start": None,
        "time_end": None,
        "published_at": None,
        "retrieved_at": evidence["retrieved_at"],
        "license_note": "Uso académico.",
    }
    fact = {
        "schema_version": "1.0",
        "fact_id": "fact_0123456789abcdef",
        "subject_id": entity["entity_id"],
        "subject_label": "Manuelita",
        "attribute": "capacidad de planta",
        "value": "125.000 toneladas",
        "value_normalized": "125000 toneladas",
        "unit": "toneladas",
        "year": 2024,
        "unit_id": unit["unit_id"],
        "evidence": [evidence],
        "status": "current",
    }
    conflict = {
        "schema_version": "1.0",
        "conflict_id": "conf_0123456789abcdef",
        "subject_id": entity["entity_id"],
        "attribute": "capacidad de planta",
        "values": [
            {
                "value": "125.000 toneladas",
                "value_normalized": "125000 toneladas",
                "unit": "toneladas",
                "year": 2024,
                "authority": "first_party",
                "unit_id": unit["unit_id"],
                "url": evidence["url"],
            },
            {
                "value": "120.000 toneladas",
                "value_normalized": "120000 toneladas",
                "unit": "toneladas",
                "year": 2023,
                "authority": "third_party",
                "unit_id": unit["unit_id"],
                "url": evidence["url"],
            },
        ],
        "preferred_unit_id": unit["unit_id"],
        "status": "resolved",
        "reason": "official_source",
    }
    ids = [f"I-{n:02d}" for n in range(1, 7)] + [f"O-{n:02d}" for n in range(1, 7)]
    ids += [f"D-{n:02d}" for n in range(1, 7)] + [f"H-{n:02d}" for n in range(1, 7)]
    coverage = {
        "schema_version": "1.0",
        "run_id": "2026-10-gold-01",
        "items": [
            {
                "item_id": item_id,
                "name": "Item",
                "category": "identity",
                "status": "partial",
                "unit_ids": [unit["unit_id"]],
                "authority_counts": {"first_party": 1},
                "conflict_ids": [],
                "gap_reason": None,
                "recommendation": None,
            }
            for item_id in ids
        ],
    }
    context = {
        "schema_version": "1.0",
        "pack_id": "pack_summary_8000",
        "task": "summary",
        "budget_tokens": 8000,
        "tokens": 100,
        "unit_ids": [unit["unit_id"]],
        "blocks": [
            {
                "unit_id": unit["unit_id"],
                "text": unit["text"],
                "citation": "Manuelita — https://www.manuelita.com/",
                "tokens": 100,
                "topic_id": "identidad",
                "authority": "first_party",
            }
        ],
        "coverage_item_ids": ["I-01"],
        "omitted_units": 0,
    }
    faq = {
        "schema_version": "1.0",
        "seed_id": "faq_0123456789abcdef",
        "question": "¿Qué es Manuelita?",
        "topic_id": "identidad",
        "coverage_item_id": "I-01",
        "evidence_unit_ids": [unit["unit_id"]],
        "status": "ready",
    }
    report = {
        "schema_version": "1.0",
        "run_id": "2026-10-gold-01",
        "started_at": "2026-10-30T00:00:00Z",
        "finished_at": "2026-10-30T00:01:00Z",
        "status": "completed",
        "config_hash": "c" * 64,
        "input_documents": 404,
        "input_chunks": 3810,
        "processed": 404,
        "skipped": 0,
        "failed": 0,
        "units": 1000,
        "facts": 100,
        "entities": 50,
        "conflicts": 2,
        "coverage": {"covered": 20, "partial": 3, "missing": 1},
        "context_packs": 2,
        "tokens": 40000,
        "duration_seconds": 10.0,
        "quality_flags": {},
        "skip_reasons": {},
        "failure_reasons": {},
        "report_paths": ["data/gold/reports/2026-10-gold-01/quality.json"],
    }
    return {
        "knowledge-unit.schema.json": unit,
        "fact.schema.json": fact,
        "entity.schema.json": entity,
        "conflict.schema.json": conflict,
        "coverage.schema.json": coverage,
        "context-pack.schema.json": context,
        "faq-seed.schema.json": faq,
        "run-report.schema.json": report,
    }
