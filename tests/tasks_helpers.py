"""Synthetic gold layer for the Module 1 task tests.

The real ``data/gold/`` directory is produced by the gold pipeline and is not versioned. These
helpers build a small, schema-faithful gold layer so unit, contract and integration tests run
offline and deterministically.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from proyecto_modelos_lenguaje.silver.cleaning import estimate_tokens

TOPICS: tuple[tuple[str, str], ...] = (
    ("topic_identidad", "Identidad y propósito corporativo"),
    ("topic_productos", "Productos y operaciones"),
    ("topic_sostenibilidad", "Sostenibilidad y medio ambiente"),
    ("topic_territorio", "Presencia territorial y cifras"),
)

UNIT_TEXTS: tuple[tuple[str, str], ...] = (
    (
        "topic_identidad",
        "Manuelita es una organización agroindustrial colombiana con más de un siglo de historia.",
    ),
    (
        "topic_identidad",
        "La casa matriz del Grupo Manuelita se encuentra en Palmira, Valle del Cauca.",
    ),
    (
        "topic_identidad",
        "La misión de Manuelita es generar progreso y bienestar en las comunidades donde opera.",
    ),
    (
        "topic_identidad",
        "Manuelita opera como holding con filiales dedicadas a azúcar, palma y logística.",
    ),
    (
        "topic_productos",
        "Manuelita produce azúcar, etanol y biocombustibles en sus ingenios.",
    ),
    (
        "topic_productos",
        "La línea de alimentos incluye azúcar refinada y productos derivados de la caña.",
    ),
    (
        "topic_productos",
        "La filial de palma produce aceite de palma crudo y palmiste.",
    ),
    (
        "topic_productos",
        "Manuelita comercializa energía eléctrica generada a partir de bagazo de caña.",
    ),
    (
        "topic_sostenibilidad",
        "Manuelita mide su desempeño ambiental con indicadores de agua, energía y emisiones.",
    ),
    (
        "topic_sostenibilidad",
        "La compañía adelanta programas de reforestación y conservación de cuencas.",
    ),
    (
        "topic_sostenibilidad",
        "Manuelita reporta avances en economía circular y aprovechamiento de residuos.",
    ),
    (
        "topic_sostenibilidad",
        "Las certificaciones ambientales de Manuelita cubren varios de sus ingenios.",
    ),
    (
        "topic_territorio",
        "Manuelita tiene presencia en Colombia, Perú, Chile y Brasil.",
    ),
    (
        "topic_territorio",
        "El ingenio del Valle del Cauca procesa miles de toneladas de caña por día.",
    ),
    (
        "topic_territorio",
        "Manuelita emplea a miles de personas de forma directa e indirecta.",
    ),
    (
        "topic_territorio",
        "Las ventas del Grupo Manuelita se reportan anualmente en sus informes públicos.",
    ),
)

ENTITIES: tuple[dict[str, Any], ...] = (
    {
        "entity_id": "ent_0000000000000001",
        "canonical_name": "Manuelita",
        "aliases": ["Grupo Manuelita"],
        "entity_type": "company",
    },
    {
        "entity_id": "ent_0000000000000002",
        "canonical_name": "azúcar",
        "aliases": ["azucar"],
        "entity_type": "product",
    },
    {
        "entity_id": "ent_0000000000000003",
        "canonical_name": "etanol",
        "aliases": [],
        "entity_type": "product",
    },
    {
        "entity_id": "ent_0000000000000004",
        "canonical_name": "Palmira",
        "aliases": ["Palmira, Valle del Cauca"],
        "entity_type": "site",
    },
)


def unit_id(index: int) -> str:
    return f"unit_{index:016x}"


def make_unit(
    index: int,
    topic_id: str,
    topic_title: str,
    text: str,
    *,
    authority: str = "first_party",
    status: str = "current",
    quality_flags: list[str] | None = None,
    entity_ids: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "unit_id": unit_id(index),
        "topic_id": topic_id,
        "topic_title": topic_title,
        "text": text,
        "unit_type": "passage",
        "language": "es",
        "authority": authority,
        "confidence": 0.9,
        "status": status,
        "entity_ids": entity_ids or ["ent_0000000000000001"],
        "coverage_item_ids": ["I-01"],
        "evidence": [
            {
                "chunk_id": f"doc_{index:016x}-s000-c0000",
                "doc_id": f"doc_{index:016x}",
                "artifact_id": 1,
                "content_hash": "a" * 64,
                "url": f"https://example.test/manuelita/{index}",
                "title": f"Manuelita — documento {index}",
                "section_path": [topic_title],
                "page_start": None,
                "page_end": None,
                "time_start": None,
                "time_end": None,
                "authority": authority,
                "published_at": "2025-01-01",
                "retrieved_at": "2026-10-30T00:00:00Z",
                "score": 1.0,
            }
        ],
        "fact_id": None,
        "text_hash": "b" * 64,
        "quality_flags": quality_flags or [],
        "url": f"https://example.test/manuelita/{index}",
        "title": f"Manuelita — documento {index}",
        "section_path": [topic_title],
        "page_start": None,
        "page_end": None,
        "time_start": None,
        "time_end": None,
        "published_at": "2025-01-01",
        "retrieved_at": "2026-10-30T00:00:00Z",
        "license_note": "Uso académico.",
    }


def make_units() -> list[dict[str, Any]]:
    titles = dict(TOPICS)
    units: list[dict[str, Any]] = []
    for index, (topic_id, text) in enumerate(UNIT_TEXTS, start=1):
        units.append(make_unit(index, topic_id, titles[topic_id], text))
    return units


def _pack(units: list[dict[str, Any]], budget: int) -> dict[str, Any]:
    blocks: list[dict[str, Any]] = []
    total = 0
    for unit in units:
        tokens = estimate_tokens(unit["text"])
        if total + tokens > budget:
            break
        total += tokens
        blocks.append(
            {
                "unit_id": unit["unit_id"],
                "text": unit["text"],
                "citation": (
                    f"{unit['title']} — {unit['url']} "
                    f"(sección: {' > '.join(unit['section_path'])})"
                ),
                "tokens": tokens,
                "topic_id": unit["topic_id"],
                "authority": unit["authority"],
            }
        )
    return {
        "schema_version": "1.0",
        "pack_id": f"pack_summary_{budget}",
        "task": "summary",
        "budget_tokens": budget,
        "tokens": total,
        "unit_ids": [block["unit_id"] for block in blocks],
        "blocks": blocks,
        "coverage_item_ids": ["I-01"],
        "omitted_units": len(units) - len(blocks),
    }


def make_seeds(units: list[dict[str, Any]]) -> list[dict[str, Any]]:
    questions = [
        "¿Qué productos ofrece Manuelita?",
        "¿Dónde está la casa matriz de Manuelita?",
        "¿Cuál es la misión de Manuelita?",
        "¿En qué países tiene presencia Manuelita?",
        "¿Qué filiales tiene el Grupo Manuelita?",
        "¿Cómo gestiona Manuelita su impacto ambiental?",
        "¿Qué certificaciones ambientales tiene Manuelita?",
        "¿Qué es la economía circular en Manuelita?",
        "¿Cuántas personas emplea Manuelita?",
        "¿Qué energía comercializa Manuelita?",
        "¿Qué produce la filial de palma?",
        "¿Qué historia tiene Manuelita?",
        "¿Cómo reporta Manuelita sus ventas?",
        "¿Qué productos ofrece Manuelita?",
    ]
    seeds: list[dict[str, Any]] = []
    for index, question in enumerate(questions, start=1):
        evidence = [units[(index - 1) % len(units)]["unit_id"]]
        seeds.append(
            {
                "schema_version": "1.0",
                "seed_id": f"faq_{index:016x}",
                "question": question,
                "topic_id": units[(index - 1) % len(units)]["topic_id"],
                "coverage_item_id": "I-01",
                "evidence_unit_ids": evidence,
                "status": "ready",
            }
        )
    seeds.append(
        {
            "schema_version": "1.0",
            "seed_id": "faq_00000000000000ff",
            "question": "¿Qué premios internacionales ha recibido Manuelita?",
            "topic_id": "topic_identidad",
            "coverage_item_id": None,
            "evidence_unit_ids": [],
            "status": "missing_evidence",
        }
    )
    return seeds


def write_gold(root: Path) -> Path:
    """Write a complete synthetic gold layer under ``root/data/gold``."""
    gold = root / "data" / "gold"
    gold.mkdir(parents=True, exist_ok=True)
    units = make_units()

    _write_jsonl(gold / "knowledge_units.jsonl", units)
    _write_jsonl(gold / "entities.jsonl", [dict(item) for item in ENTITIES])
    _write_jsonl(gold / "faq_seeds.jsonl", make_seeds(units))
    _write_json(gold / "context_8000.json", _pack(units[:12], 8000))
    _write_json(gold / "context_32000.json", _pack(units, 32000))
    _write_json(
        gold / "coverage.json",
        {
            "schema_version": "1.0",
            "items": [
                {
                    "item_id": "I-01",
                    "name": "Identidad corporativa",
                    "category": "identity",
                    "status": "covered",
                    "unit_ids": [unit["unit_id"] for unit in units],
                    "authority_counts": {"first_party": len(units)},
                    "conflict_ids": [],
                    "gap_reason": None,
                    "recommendation": None,
                }
            ],
        },
    )
    return gold


def write_empty_pack(root: Path, *, pack: str = "8000") -> Path:
    """Write a gold layer whose requested context pack has no blocks."""
    gold = write_gold(root)
    _write_json(
        gold / f"context_{pack}.json",
        {
            "schema_version": "1.0",
            "pack_id": f"pack_summary_{pack}",
            "task": "summary",
            "budget_tokens": int(pack),
            "tokens": 0,
            "unit_ids": [],
            "blocks": [],
            "coverage_item_ids": [],
            "omitted_units": len(UNIT_TEXTS),
        },
    )
    return gold


def _write_jsonl(path: Path, records: list[dict[str, Any]]) -> None:
    path.write_text(
        "".join(json.dumps(record, ensure_ascii=False) + "\n" for record in records),
        encoding="utf-8",
    )


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
