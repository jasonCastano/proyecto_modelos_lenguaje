"""Muestra fija de 30 consultas para la evaluación del Módulo 3 (spec 024, T070, research R16).

Uso::

    uv run python scripts/sample_module3_queries.py [--seed 2026] [--size 30]

Toma las preguntas **puntuables** de ``tests/fixtures/rag/eval_questions.jsonl`` (con unidades
esperadas y que no son repreguntas), elige ``size`` con ``random.Random(seed)`` **antes** de
evaluar y escribe ``tests/fixtures/rag/module3_queries.jsonl`` con ``id``, ``question``,
``expected_unit_ids``, ``topic_id`` (tema de la primera unidad esperada en el oro) y
``source_question_id``. La misma semilla produce siempre el mismo archivo.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "tests" / "fixtures" / "rag" / "eval_questions.jsonl"
TARGET = ROOT / "tests" / "fixtures" / "rag" / "module3_queries.jsonl"
GOLD_FILES = (
    ROOT / "tests" / "fixtures" / "rag" / "gold_sample.jsonl",
    ROOT / "data" / "gold" / "knowledge_units.jsonl",
)
SEED = 2026
SIZE = 30


def _jsonl(path: Path) -> list[dict]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _topics(needed: set[str]) -> dict[str, str]:
    """Tema de cada unidad: primero la muestra de prueba y, si falta, el oro completo."""
    topics: dict[str, str] = {}
    for path in GOLD_FILES:
        if not path.is_file() or needed <= topics.keys():
            continue
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                if not line.strip():
                    continue
                unit = json.loads(line)
                unit_id = str(unit.get("unit_id", ""))
                if unit_id in needed and unit_id not in topics:
                    topics[unit_id] = str(unit.get("topic_id", ""))
    return topics


def scored_questions(rows: list[dict]) -> list[dict]:
    return [row for row in rows if row.get("expected_unit_ids") and row.get("type") != "follow_up"]


def sample_queries(rows: list[dict], *, seed: int = SEED, size: int = SIZE) -> list[dict]:
    scored = scored_questions(rows)
    if len(scored) < size:
        raise ValueError(f"solo hay {len(scored)} preguntas puntuables; se piden {size}")
    chosen = random.Random(seed).sample(scored, size)
    chosen.sort(key=lambda row: str(row["question_id"]))
    needed = {str(unit) for row in chosen for unit in row["expected_unit_ids"]}
    topics = _topics(needed)
    queries = []
    for number, row in enumerate(chosen, start=1):
        expected = [str(unit) for unit in row["expected_unit_ids"]]
        topic = next((topics[unit] for unit in expected if topics.get(unit)), "")
        queries.append(
            {
                "id": f"m3-{number:02d}",
                "question": row["question"],
                "expected_unit_ids": expected,
                "topic_id": topic,
                "source_question_id": str(row["question_id"]),
                "type": row.get("type", "paraphrase"),
            }
        )
    return queries


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--size", type=int, default=SIZE)
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--out", type=Path, default=TARGET)
    args = parser.parse_args(argv)
    queries = sample_queries(_jsonl(args.source), seed=args.seed, size=args.size)
    missing = [query["id"] for query in queries if not query["topic_id"]]
    if missing:
        print(f"aviso: sin topic_id para {', '.join(missing)}", file=sys.stderr)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(
        "".join(json.dumps(query, ensure_ascii=False) + "\n" for query in queries),
        encoding="utf-8",
    )
    print(f"{len(queries)} consultas escritas en {args.out} (semilla {args.seed})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
