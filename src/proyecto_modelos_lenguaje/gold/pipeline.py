"""Gold pipeline orchestration: units, entities, facts, conflicts, coverage and context."""

from __future__ import annotations

import hashlib
import json
import random
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT
from ..silver.cleaning import estimate_tokens
from ..utils import utcnow
from .config import GoldConfig, load_gold_config
from .conflicts import detect_conflicts
from .context_pack import build_context_packs, render_context_markdown
from .coverage import (
    build_coverage,
    coverage_payload,
    coverage_summary,
    render_coverage_markdown,
)
from .entities import build_entities
from .facts import extract_facts
from .faq import build_faq_seeds
from .inputs import SilverDocument, load_silver_input
from .models import (
    GoldManifest,
    GoldReport,
    KnowledgeUnit,
    validate_pack,
    validate_unit,
)
from .reporting import write_report
from .store import (
    GoldStateError,
    merge_state,
    prepare_output,
    read_cache,
    read_jsonl,
    read_state,
    validate_run_id,
    write_cache,
    write_json,
    write_jsonl,
    write_text,
)
from .taxonomy import Taxonomy, load_taxonomy
from .topics import build_topics, render_glossary, write_topic_pages
from .units import build_units, deduplicate_units

TOOL_VERSION = "0.3.0"


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


class GoldPipeline:
    def __init__(
        self,
        *,
        silver_dir: Path,
        config: GoldConfig,
        taxonomy: Taxonomy,
        project_root: Path = PROJECT_ROOT,
        tool_version: str = TOOL_VERSION,
    ) -> None:
        self.silver_dir = silver_dir
        self.config = config
        self.taxonomy = taxonomy
        self.project_root = project_root
        self.tool_version = tool_version

    @classmethod
    def from_paths(
        cls,
        *,
        silver_dir: str | Path = "data/silver",
        config_path: str | Path = "config/gold.toml",
        taxonomy_path: str | Path = "config/gold_taxonomy.toml",
        project_root: Path = PROJECT_ROOT,
    ) -> GoldPipeline:
        config = load_gold_config(config_path, taxonomy_path, project_root=project_root)
        taxonomy = load_taxonomy(
            config.taxonomy_path,
            coverage_path=config.path.parent / "coverage-items.toml",
            min_score=config.topics.min_score,
        )
        silver = Path(silver_dir)
        if not silver.is_absolute():
            silver = project_root / silver
        return cls(
            silver_dir=silver,
            config=config,
            taxonomy=taxonomy,
            project_root=project_root,
        )

    def build(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        topic: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        validate_run_id(run_id)
        started = time.perf_counter()
        started_at = utcnow()
        paths = prepare_output(self.config.output.root)
        paths["context_root"] = paths["root"]
        partial = limit is not None or topic is not None
        if partial:
            run_root = paths["meta"] / "smoke" / run_id
            paths = dict(paths)
            paths["context_root"] = run_root
            paths["units"] = run_root / "knowledge_units.jsonl"
            paths["facts"] = run_root / "facts.jsonl"
            paths["entities"] = run_root / "entities.jsonl"
            paths["conflicts"] = run_root / "conflicts.jsonl"
            paths["faq"] = run_root / "faq_seeds.jsonl"
            paths["coverage_json"] = run_root / "coverage.json"
            paths["coverage_md"] = run_root / "coverage.md"
            paths["glossary"] = run_root / "glossary.md"
            paths["manifest"] = run_root / "manifest.json"
            paths["topics"] = run_root / "topics"
            paths["state"] = run_root / "state.jsonl"
            paths["cache"] = run_root / "cache"
        report_dir = paths["reports"] / run_id
        if report_dir.exists() and not force:
            raise GoldStateError(f"run {run_id} already exists; use --force or a new run id")
        free = shutil.disk_usage(paths["root"]).free
        if free < 100_000_000:
            raise GoldStateError(f"insufficient disk space: {free} bytes available")

        documents, chunks_by_doc = load_silver_input(self.silver_dir)
        if limit is not None:
            documents = documents[:limit]
        state = {} if force else read_state(paths["state"])
        units: list[KnowledgeUnit] = []
        records: list[dict[str, Any]] = []
        skip_reasons: Counter[str] = Counter()
        failure_reasons: Counter[str] = Counter()

        for document in documents:
            try:
                document_units = self._process_document(
                    document,
                    chunks_by_doc.get(document.doc_id, []),
                    paths,
                    state=state,
                    force=force,
                )
                if not document_units:
                    skip_reasons["no_units"] += 1
                    records.append(self._record(document, "skipped", "no_units", 0, 0))
                else:
                    units.extend(document_units)
                    records.append(
                        self._record(document, "processed", None, len(document_units), 0)
                    )
            except Exception as exc:
                failure_reasons[type(exc).__name__] += 1
                records.append(self._record(document, "failed", str(exc)[:300], 0, 0))
                if self.config.run.fail_fast:
                    raise

        units = deduplicate_units(
            units,
            threshold=self.config.units.dedup_threshold,
            shingle_size=self.config.units.dedup_shingle_size,
        )
        if topic:
            units = [unit for unit in units if unit.topic_id == topic]
        entities = build_entities(units, self.taxonomy)
        facts = []
        for unit in units:
            facts.extend(extract_facts(unit, self.taxonomy))
        conflicts = detect_conflicts(facts, {unit.unit_id: unit for unit in units})
        coverage_entries = build_coverage(units, conflicts, self.taxonomy, self.config.coverage)
        topics = build_topics(units, self.taxonomy)
        packs = build_context_packs(units, coverage_entries, self.config.context)
        faq_seeds = build_faq_seeds(
            units,
            coverage_entries,
            topics,
            entities,
        )

        for unit in units:
            validate_unit(unit)
        for pack in packs:
            validate_pack(pack)

        paths["topics"].mkdir(parents=True, exist_ok=True)
        write_jsonl(
            paths["units"],
            [unit.to_dict() for unit in sorted(units, key=lambda item: item.unit_id)],
        )
        write_jsonl(
            paths["facts"],
            [fact.to_dict() for fact in sorted(facts, key=lambda item: item.fact_id)],
        )
        write_jsonl(
            paths["entities"],
            [entity.to_dict() for entity in sorted(entities, key=lambda item: item.canonical_name)],
        )
        write_jsonl(
            paths["conflicts"],
            [
                conflict.to_dict()
                for conflict in sorted(conflicts, key=lambda item: item.conflict_id)
            ],
        )
        write_jsonl(paths["faq"], [seed.to_dict() for seed in faq_seeds])
        write_json(
            paths["coverage_json"],
            coverage_payload(coverage_entries, run_id),
        )
        write_text(paths["coverage_md"], render_coverage_markdown(coverage_entries, run_id))
        write_text(paths["glossary"], render_glossary(entities))
        write_topic_pages(topics, units, paths["topics"])
        for pack in packs:
            write_text(
                paths["context_root"] / f"context_{pack.budget_tokens}.md",
                render_context_markdown(pack),
            )
            write_json(
                paths["context_root"] / f"context_{pack.budget_tokens}.json",
                pack.to_dict(),
            )
            write_jsonl(
                paths["context_root"] / f"context_{pack.budget_tokens}.jsonl",
                [block.to_dict() for block in pack.blocks],
            )

        updated_records = []
        chunks_per_doc: Counter[str] = Counter()
        for unit in units:
            chunks_per_doc[unit.evidence[0].doc_id] += 1
        for record in records:
            record["units"] = chunks_per_doc.get(str(record["doc_id"]), record["units"])
            updated_records.append(record)
        write_jsonl(paths["state"], merge_state(state, updated_records))

        quality_flags: Counter[str] = Counter()
        for unit in units:
            quality_flags.update(unit.quality_flags)
        finished_at = utcnow()
        report = GoldReport(
            schema_version="1.0",
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            status="completed" if not failure_reasons else "completed_with_failures",
            config_hash=self.config.config_hash,
            input_documents=len(documents),
            input_chunks=sum(len(chunks_by_doc.get(document.doc_id, [])) for document in documents),
            processed=sum(1 for record in records if record["status"] == "processed"),
            skipped=sum(1 for record in records if record["status"] == "skipped"),
            failed=sum(1 for record in records if record["status"] == "failed"),
            units=len(units),
            facts=len(facts),
            entities=len(entities),
            conflicts=len(conflicts),
            coverage=coverage_summary(coverage_entries),
            context_packs=len(packs),
            tokens=sum(
                estimate_tokens(unit.text, self.config.context.chars_per_token) for unit in units
            ),
            duration_seconds=round(time.perf_counter() - started, 3),
            quality_flags=dict(sorted(quality_flags.items())),
            skip_reasons=dict(sorted(skip_reasons.items())),
            failure_reasons=dict(sorted(failure_reasons.items())),
            report_paths=[],
        )
        report.report_paths = [
            _relative(Path(path), self.project_root)
            for path in write_report(report, paths["reports"])
        ]
        write_report(report, paths["reports"])

        manifest = GoldManifest(
            run_id=run_id,
            config_hash=self.config.config_hash,
            taxonomy_hash=self.config.taxonomy_hash,
            created_at=finished_at,
            input_documents=len(documents),
            input_chunks=report.input_chunks,
            knowledge_units=len(units),
            facts=len(facts),
            entities=len(entities),
            conflicts=len(conflicts),
            faq_seeds=len(faq_seeds),
            files=[
                _file_entry(path, self.project_root)
                for path in (
                    paths["units"],
                    paths["facts"],
                    paths["entities"],
                    paths["conflicts"],
                    paths["faq"],
                    paths["coverage_json"],
                    paths["coverage_md"],
                    paths["glossary"],
                    *paths["topics"].glob("*.md"),
                    *paths["context_root"].glob("context_*.md"),
                    *paths["context_root"].glob("context_*.json"),
                    *paths["context_root"].glob("context_*.jsonl"),
                )
            ],
        )
        write_json(paths["manifest"], manifest.to_dict())
        return report.to_dict()

    def _process_document(
        self,
        document: SilverDocument,
        chunks: list[Any],
        paths: dict[str, Path],
        *,
        state: dict[str, dict[str, Any]],
        force: bool,
    ) -> list[KnowledgeUnit]:
        previous = state.get(document.doc_id)
        cache = None
        if (
            not force
            and previous
            and previous.get("text_hash") == document.text_hash
            and previous.get("config_hash") == self.config.config_hash
            and previous.get("status") == "processed"
        ):
            cache = read_cache(
                paths["cache"], document.doc_id, document.text_hash, self.config.config_hash
            )
        if cache is not None:
            return [KnowledgeUnit.from_dict(item) for item in cache.get("units", [])]
        if not chunks:
            return []
        units = build_units(document, chunks, self.taxonomy, self.config.units)
        write_cache(
            paths["cache"],
            document.doc_id,
            document.text_hash,
            self.config.config_hash,
            {"units": [unit.to_dict() for unit in units]},
        )
        return units

    def _record(
        self,
        document: SilverDocument,
        status: str,
        reason: str | None,
        units: int,
        facts: int,
    ) -> dict[str, Any]:
        return {
            "doc_id": document.doc_id,
            "text_hash": document.text_hash,
            "config_hash": self.config.config_hash,
            "status": status,
            "reason": reason,
            "units": units,
            "facts": facts,
            "processed_at": utcnow(),
        }

    def verify_run(self, run_id: str, *, sample: int = 50, seed: int = 1) -> dict[str, Any]:
        validate_run_id(run_id)
        paths = prepare_output(self.config.output.root)
        smoke = paths["meta"] / "smoke" / run_id
        root = smoke if smoke.is_dir() else paths["root"]
        units = read_jsonl(root / "knowledge_units.jsonl")
        facts = read_jsonl(root / "facts.jsonl") if (root / "facts.jsonl").is_file() else []
        conflicts = (
            read_jsonl(root / "conflicts.jsonl") if (root / "conflicts.jsonl").is_file() else []
        )
        coverage = (
            json.loads((root / "coverage.json").read_text(encoding="utf-8"))
            if (root / "coverage.json").is_file()
            else {}
        )
        coverage_items = coverage.get("items", []) if isinstance(coverage, dict) else []
        failures: list[str] = []
        seen: set[str] = set()
        for unit in units:
            unit_id = unit["unit_id"]
            if unit_id in seen:
                failures.append(f"duplicate unit_id: {unit_id}")
            seen.add(unit_id)
            if not unit.get("evidence"):
                failures.append(f"{unit_id}: no evidence")
            if not unit.get("url") or not unit.get("title") or not unit.get("section_path"):
                failures.append(f"{unit_id}: incomplete lineage")
        for conflict in conflicts:
            if len(conflict.get("values", [])) < 2:
                failures.append(f"{conflict.get('conflict_id')}: conflict with less than 2 values")
        if len(coverage_items) != 24:
            failures.append(f"coverage items: expected 24, found {len(coverage_items)}")
        for budget in self.config.context.budgets:
            pack_path = root / f"context_{budget}.md"
            if not pack_path.is_file():
                failures.append(f"missing context pack {budget}")
        randomizer = random.Random(seed)
        sampled = randomizer.sample(units, min(sample, len(units))) if units else []
        for unit in sampled:
            evidence = unit["evidence"][0]
            if not evidence.get("chunk_id") or not evidence.get("url"):
                failures.append(f"{unit['unit_id']}: evidence without chunk/url")
        return {
            "run_id": run_id,
            "sampled": len(sampled),
            "units": len(units),
            "facts": len(facts),
            "conflicts": len(conflicts),
            "coverage_items": len(coverage_items),
            "passed": not failures,
            "failures": failures,
        }

    def status(self, run_id: str | None = None) -> dict[str, Any]:
        paths = prepare_output(self.config.output.root)
        reports = sorted(paths["reports"].glob("*/quality.json"))
        if run_id:
            reports = [path for path in reports if path.parent.name == run_id]
        else:
            full = [
                path
                for path in reports
                if not (paths["meta"] / "smoke" / path.parent.name).is_dir()
            ]
            reports = full or reports
        if not reports:
            return {"status": "missing", "reports": []}
        latest = reports[-1]
        payload = json.loads(latest.read_text(encoding="utf-8"))
        return {
            "status": payload.get("status"),
            "run_id": payload.get("run_id"),
            "units": payload.get("units"),
            "facts": payload.get("facts"),
            "conflicts": payload.get("conflicts"),
            "coverage": payload.get("coverage"),
            "context_packs": payload.get("context_packs"),
            "tokens": payload.get("tokens"),
        }

    def report(self, run_id: str) -> dict[str, Any]:
        path = prepare_output(self.config.output.root)["reports"] / run_id / "quality.json"
        if not path.is_file():
            raise FileNotFoundError(f"report not found for run {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))


def _file_entry(path: Path, project_root: Path) -> dict[str, Any]:
    data = path.read_bytes()
    return {
        "path": _relative(path, project_root),
        "sha256": hashlib.sha256(data).hexdigest(),
        "bytes": len(data),
    }
