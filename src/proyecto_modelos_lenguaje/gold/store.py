"""Atomic storage and incremental state for the gold layer."""

from __future__ import annotations

import json
import os
import re
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any

RUN_ID_PATTERN = re.compile(r"^\d{4}-\d{2}-gold-\d{2}$")


class GoldStateError(ValueError):
    """Raised for invalid run identifiers or inconsistent state."""


def validate_run_id(run_id: str) -> str:
    if not RUN_ID_PATTERN.fullmatch(run_id):
        raise GoldStateError(f"invalid run_id '{run_id}'; expected YYYY-MM-gold-NN")
    return run_id


def prepare_output(root: Path) -> dict[str, Path]:
    root.mkdir(parents=True, exist_ok=True)
    meta = root / "_meta"
    meta.mkdir(parents=True, exist_ok=True)
    (meta / "cache").mkdir(parents=True, exist_ok=True)
    (root / "topics").mkdir(parents=True, exist_ok=True)
    (root / "reports").mkdir(parents=True, exist_ok=True)
    return {
        "root": root,
        "meta": meta,
        "state": meta / "state.jsonl",
        "cache": meta / "cache",
        "units": root / "knowledge_units.jsonl",
        "facts": root / "facts.jsonl",
        "entities": root / "entities.jsonl",
        "conflicts": root / "conflicts.jsonl",
        "faq": root / "faq_seeds.jsonl",
        "coverage_json": root / "coverage.json",
        "coverage_md": root / "coverage.md",
        "glossary": root / "glossary.md",
        "manifest": root / "manifest.json",
        "topics": root / "topics",
        "reports": root / "reports",
    }


def _atomic_replace(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="wb", dir=path.parent, prefix=".tmp-", suffix=".part", delete=False
        ) as handle:
            temporary = Path(handle.name)
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
    except BaseException:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
        raise


def write_text(path: Path, text: str) -> None:
    _atomic_replace(path, text.encode("utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    write_text(path, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


def write_jsonl(path: Path, records: Iterable[dict[str, Any]]) -> int:
    lines = [json.dumps(record, ensure_ascii=False) for record in records]
    payload = "\n".join(lines)
    if payload:
        payload += "\n"
    _atomic_replace(path, payload.encode("utf-8"))
    return len(lines)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if line:
                records.append(json.loads(line))
    return records


def read_state(path: Path) -> dict[str, dict[str, Any]]:
    return {str(record["doc_id"]): record for record in read_jsonl(path)}


def merge_state(
    existing: dict[str, dict[str, Any]], new_records: Iterable[dict[str, Any]]
) -> list[dict[str, Any]]:
    merged = dict(existing)
    for record in new_records:
        merged[str(record["doc_id"])] = record
    return [merged[key] for key in sorted(merged)]


def cache_path(cache_dir: Path, doc_id: str, text_hash: str, config_hash: str) -> Path:
    return cache_dir / f"{doc_id}-{text_hash[:12]}-{config_hash[:12]}.json"


def read_cache(
    cache_dir: Path, doc_id: str, text_hash: str, config_hash: str
) -> dict[str, Any] | None:
    path = cache_path(cache_dir, doc_id, text_hash, config_hash)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None


def write_cache(
    cache_dir: Path,
    doc_id: str,
    text_hash: str,
    config_hash: str,
    payload: dict[str, Any],
) -> None:
    write_json(cache_path(cache_dir, doc_id, text_hash, config_hash), payload)


def output_size(paths: Iterable[Path]) -> int:
    return sum(path.stat().st_size for path in paths if path.is_file())
