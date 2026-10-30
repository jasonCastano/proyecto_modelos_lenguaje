"""Silver pipeline orchestration: extract, clean, structure, deduplicate and chunk."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import time
from collections import Counter
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT, load_config
from ..storage import sha256_bytes
from ..utils import utcnow
from .bronze import BronzeArtifact, load_artifacts, read_artifact_bytes
from .chunking import chunk_document
from .cleaning import CLEANING_VERSION, clean_document, estimate_tokens, sha256_text
from .config import SilverConfig, load_silver_config
from .dedup import deduplicate
from .extractors.registry import extract
from .models import (
    ExtractedBlock,
    ExtractedDocument,
    ProcessingRecord,
    QualityFlag,
    RunReport,
    SilverDocument,
    make_doc_id,
    validate_chunk,
    validate_document,
)
from .reporting import write_markdown, write_report
from .sections import build_sections
from .state import (
    SilverStateError,
    atomic_write_jsonl,
    merge_state,
    output_size,
    prepare_output,
    read_cache,
    read_jsonl,
    read_state,
    validate_run_id,
    write_cache,
    write_chunks,
    write_documents,
)

TOOL_VERSION = "0.2.0"


def _git_commit() -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], text=True, stderr=subprocess.DEVNULL
        ).strip()
    except Exception:
        return None


def _published(value: str | None) -> str | None:
    if not value:
        return None
    text = str(value).strip()
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}", text):
        return f"{text}T00:00:00Z"
    if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:Z|[+-]\d{2}:\d{2})", text):
        return text
    return None


def _cache_payload(document: ExtractedDocument) -> dict[str, Any]:
    return {
        "title": document.title,
        "blocks": [
            {
                "text": block.text,
                "level": block.level,
                "page": block.page,
                "time_start": block.time_start,
                "time_end": block.time_end,
            }
            for block in document.blocks
        ],
        "metadata": document.metadata,
        "skip_reason": document.skip_reason,
        "flags": sorted(document.flags),
    }


def _from_cache(payload: dict[str, Any]) -> ExtractedDocument:
    return ExtractedDocument(
        title=payload.get("title"),
        blocks=[
            ExtractedBlock(
                text=item["text"],
                level=int(item.get("level", 0)),
                page=item.get("page"),
                time_start=item.get("time_start"),
                time_end=item.get("time_end"),
            )
            for item in payload.get("blocks", [])
        ],
        metadata=dict(payload.get("metadata") or {}),
        skip_reason=payload.get("skip_reason"),
        flags=set(payload.get("flags") or []),
    )


def _relative(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return path.resolve().as_posix()


class SilverPipeline:
    """Deterministic bronze-to-silver pipeline."""

    def __init__(
        self,
        *,
        bronze_db: Path,
        bronze_dir: Path,
        config: SilverConfig,
        project_root: Path = PROJECT_ROOT,
        tool_version: str = TOOL_VERSION,
    ) -> None:
        self.bronze_db = bronze_db
        self.bronze_dir = bronze_dir
        self.config = config
        self.project_root = project_root
        self.tool_version = tool_version

    @classmethod
    def from_paths(
        cls,
        *,
        sources_config: str | Path = "config/sources.toml",
        silver_config: str | Path = "config/silver.toml",
        project_root: Path = PROJECT_ROOT,
    ) -> SilverPipeline:
        app = load_config(sources_config, project_root=project_root)
        config = load_silver_config(silver_config, project_root=project_root)
        return cls(
            bronze_db=app.settings.bronze_dir / "_meta" / "bronze.sqlite3",
            bronze_dir=app.settings.bronze_dir,
            config=config,
            project_root=project_root,
        )

    def build(
        self,
        run_id: str,
        *,
        limit: int | None = None,
        source: str | None = None,
        force: bool = False,
    ) -> dict[str, Any]:
        validate_run_id(run_id)
        started = time.perf_counter()
        started_at = utcnow()
        paths = prepare_output(self.config.output.root)
        partial = limit is not None or source is not None
        if partial:
            run_root = paths["meta"] / "smoke" / run_id
            paths = dict(paths)
            paths["documents"] = run_root / "documents.jsonl"
            paths["chunks"] = run_root / "chunks.jsonl"
            paths["markdown"] = run_root / "markdown"
        report_dir = paths["reports"] / run_id
        if report_dir.exists() and not force:
            raise SilverStateError(f"run {run_id} already exists; use --force or a new run id")
        free = shutil.disk_usage(paths["root"]).free
        if free < 100_000_000:
            raise SilverStateError(
                f"insufficient disk space for silver output: {free} bytes available"
            )
        state = {} if force else read_state(paths["state"])
        artifacts = load_artifacts(self.bronze_db, source_id=source, limit=limit)

        documents: list[SilverDocument] = []
        records: list[ProcessingRecord] = []
        skip_reasons: Counter[str] = Counter()
        failure_reasons: Counter[str] = Counter()
        by_source: Counter[str] = Counter()
        by_media: Counter[str] = Counter()

        for artifact in artifacts:
            by_source[artifact.source_id] += 1
            by_media[artifact.media_type] += 1
            try:
                document, record = self._process_artifact(artifact, paths, state=state, force=force)
                records.append(record)
                if document is not None:
                    documents.append(document)
                elif record.status == "skipped":
                    skip_reasons[record.reason or "skipped"] += 1
                elif record.status == "failed":
                    failure_reasons[record.reason or "failed"] += 1
            except Exception as exc:
                reason = f"{type(exc).__name__}: {exc}"[:300]
                failure_reasons[type(exc).__name__] += 1
                records.append(
                    ProcessingRecord(
                        artifact_id=artifact.artifact_id,
                        content_hash=artifact.content_hash,
                        config_hash=self.config.config_hash,
                        status="failed",
                        reason=reason,
                        doc_id=None,
                        documents=0,
                        chunks=0,
                        quality_flags=[],
                        processed_at=utcnow(),
                    )
                )
                if self.config.run.fail_fast:
                    raise

        _alias_map, groups = deduplicate(documents, config=self.config.dedup)
        chunks = []
        chunks_per_doc: Counter[str] = Counter()
        markdown_files: list[Path] = []
        for document in documents:
            if document.status != "canonical":
                continue
            document_chunks = chunk_document(document, config=self.config.chunking)
            for chunk in document_chunks:
                validate_chunk(chunk, document, max_tokens=self.config.chunking.max_tokens)
            chunks.extend(document_chunks)
            chunks_per_doc[document.doc_id] = len(document_chunks)
            validate_document(document)

        for document in documents:
            if document.status == "canonical" and self.config.output.markdown:
                path = Path(write_markdown(document, paths["markdown"]))
                document.markdown_path = _relative(path, self.project_root)
                markdown_files.append(path)

        write_documents(paths["documents"], documents)
        write_chunks(paths["chunks"], chunks)

        updated_records = []
        for record in records:
            if record.doc_id:
                record.chunks = chunks_per_doc.get(record.doc_id, 0)
            updated_records.append(record.to_dict())
        merged = merge_state(state, updated_records)
        atomic_write_jsonl(paths["state"], merged)

        canonical = [document for document in documents if document.status == "canonical"]
        aliases = [document for document in documents if document.status == "alias"]
        quality_flags: Counter[str] = Counter()
        section_coverage = {"with_title": 0, "without_title": 0}
        for document in documents:
            quality_flags.update(document.quality_flags)
            for section in document.sections:
                key = "without_title" if section.title == "sin sección" else "with_title"
                section_coverage[key] += 1

        finished_at = utcnow()
        report = RunReport(
            schema_version="1.0",
            run_id=run_id,
            started_at=started_at,
            finished_at=finished_at,
            status="completed" if not failure_reasons else "completed_with_failures",
            config_hash=self.config.config_hash,
            cleaning_version=CLEANING_VERSION,
            tool_version=self.tool_version,
            git_commit=_git_commit(),
            input_artifacts=len(artifacts),
            processed=sum(1 for record in records if record.status == "processed"),
            skipped=sum(1 for record in records if record.status == "skipped"),
            failed=sum(1 for record in records if record.status == "failed"),
            documents=len(documents),
            canonical_documents=len(canonical),
            alias_documents=len(aliases),
            chunks=len(chunks),
            duplicates_exact=sum(1 for group in groups if group.kind == "exact"),
            duplicates_near=sum(1 for group in groups if group.kind == "near"),
            tokens_in=sum(document.token_count for document in documents),
            tokens_out=sum(chunk.token_count for chunk in chunks),
            bytes_out=output_size([paths["documents"], paths["chunks"], *markdown_files]),
            duration_seconds=round(time.perf_counter() - started, 3),
            by_source=dict(sorted(by_source.items())),
            by_media_type=dict(sorted(by_media.items())),
            by_status=dict(sorted(Counter(record.status for record in records).items())),
            skip_reasons=dict(sorted(skip_reasons.items())),
            failure_reasons=dict(sorted(failure_reasons.items())),
            quality_flags=dict(sorted(quality_flags.items())),
            section_coverage=section_coverage,
            report_paths=[],
        )
        report.report_paths = [
            _relative(Path(path), self.project_root)
            for path in write_report(report, paths["reports"])
        ]
        # Rewrite the report after adding its own paths.
        write_report(report, paths["reports"])
        return report.to_dict()

    def _process_artifact(
        self,
        artifact: BronzeArtifact,
        paths: dict[str, Path],
        *,
        state: dict[int, dict[str, Any]],
        force: bool,
    ) -> tuple[SilverDocument | None, ProcessingRecord]:
        previous = state.get(artifact.artifact_id)
        cache = None
        if (
            not force
            and previous
            and previous.get("content_hash") == artifact.content_hash
            and previous.get("config_hash") == self.config.config_hash
            and previous.get("status") in {"processed", "skipped"}
        ):
            cache = read_cache(paths["cache"], artifact.content_hash, self.config.config_hash)
        if cache is None:
            data = read_artifact_bytes(artifact, self.bronze_dir)
            if sha256_bytes(data) != artifact.content_hash:
                raise ValueError(f"hash mismatch for artifact {artifact.artifact_id}")
            extracted = extract(
                artifact,
                data,
                table_line_ratio=self.config.quality.table_line_ratio,
                repeated_line_ratio=self.config.quality.repeated_line_ratio,
            )
            document = clean_document(
                extracted,
                declared_language=artifact.language,
                min_text_chars=self.config.quality.min_text_chars,
                min_alpha_ratio=self.config.quality.min_alpha_ratio,
                min_tokens=self.config.language.min_tokens,
            )
            write_cache(
                paths["cache"],
                artifact.content_hash,
                self.config.config_hash,
                _cache_payload(document),
            )
        else:
            document = _from_cache(cache)

        if document.skip_reason:
            return None, self._record(artifact, "skipped", document.skip_reason, document.flags)
        if QualityFlag.NO_TEXT.value in document.flags:
            return None, self._record(artifact, "skipped", "no_text", document.flags)
        if not document.text.strip():
            return None, self._record(artifact, "skipped", "no_text", document.flags)

        doc_id = make_doc_id(artifact.url_canonical, artifact.content_hash)
        sections, has_headings = build_sections(
            doc_id=doc_id,
            blocks=document.blocks,
            document_title=document.title,
            outline=document.metadata.get("outline")
            if isinstance(document.metadata.get("outline"), list)
            else None,
        )
        if not sections:
            return None, self._record(artifact, "skipped", "no_sections", document.flags)
        flags = set(document.flags)
        if not has_headings:
            flags.add(QualityFlag.NO_SECTION.value)
        text = "\n\n".join(block.text for block in document.blocks if block.text.strip())
        language = str(document.metadata.get("language") or "und")
        language_method = str(document.metadata.get("language_method") or "unknown")
        published = _published(artifact.published_at) or _published(
            document.metadata.get("date")
            if isinstance(document.metadata.get("date"), str)
            else None
        )
        title = document.title or artifact.title or "Documento sin título"
        silver = SilverDocument(
            schema_version="1.0",
            doc_id=doc_id,
            artifact_id=artifact.artifact_id,
            campaign_id=artifact.campaign_id,
            content_hash=artifact.content_hash,
            text_hash=sha256_text(text),
            source_id=artifact.source_id,
            authority=artifact.authority,
            url=artifact.url_original,
            url_canonical=artifact.url_canonical,
            title=title,
            published_at=published,
            retrieved_at=artifact.retrieved_at,
            language=language,
            language_method=language_method,
            category=artifact.category,
            media_type=artifact.media_type,
            cleaning_version=CLEANING_VERSION,
            config_hash=self.config.config_hash,
            status="canonical",
            canonical_doc_id=None,
            duplicate_of=None,
            aliases=[],
            quality_flags=sorted(flags),
            sections=sections,
            text=text,
            char_count=len(text),
            token_count=estimate_tokens(text, self.config.chunking.chars_per_token),
            license_note=(
                "Uso académico. Contenido público de su fuente original; "
                "se cita la URL y la fecha de captura."
            ),
            markdown_path=None,
            version=artifact.version,
            blocks=document.blocks,
        )
        return silver, self._record(
            artifact, "processed", None, silver.quality_flags, doc_id=doc_id
        )

    def _record(
        self,
        artifact: BronzeArtifact,
        status: str,
        reason: str | None,
        flags: set[str] | list[str],
        *,
        doc_id: str | None = None,
    ) -> ProcessingRecord:
        return ProcessingRecord(
            artifact_id=artifact.artifact_id,
            content_hash=artifact.content_hash,
            config_hash=self.config.config_hash,
            status=status,
            reason=reason,
            doc_id=doc_id,
            documents=1 if doc_id else 0,
            chunks=0,
            quality_flags=sorted(flags),
            processed_at=utcnow(),
        )

    def verify_run(self, run_id: str, *, sample: int = 50, seed: int = 1) -> dict[str, Any]:
        validate_run_id(run_id)
        paths = prepare_output(self.config.output.root)
        smoke = paths["meta"] / "smoke" / run_id
        documents_path = smoke / "documents.jsonl" if smoke.is_dir() else paths["documents"]
        chunks_path = smoke / "chunks.jsonl" if smoke.is_dir() else paths["chunks"]
        documents = read_jsonl(documents_path)
        chunks = read_jsonl(chunks_path)
        failures: list[str] = []
        by_id = {document["doc_id"]: document for document in documents}
        sections_by_doc = {
            document["doc_id"]: {section["section_id"] for section in document["sections"]}
            for document in documents
        }
        if len(by_id) != len(documents):
            failures.append("duplicate doc_id values")
        seen_chunks: set[str] = set()
        for document in documents:
            try:
                validate_document(_document_from_dict(document))
            except ValueError as exc:
                failures.append(str(exc))
        for chunk in chunks:
            chunk_id = chunk["chunk_id"]
            if chunk_id in seen_chunks:
                failures.append(f"duplicate chunk_id: {chunk_id}")
            seen_chunks.add(chunk_id)
            doc = by_id.get(chunk["doc_id"])
            if doc is None:
                failures.append(f"{chunk_id}: missing document")
                continue
            if chunk["section_id"] not in sections_by_doc.get(chunk["doc_id"], set()):
                failures.append(f"{chunk_id}: missing section")
            start, end = int(chunk["char_start"]), int(chunk["char_end"])
            if not 0 <= start < end <= len(doc["text"]):
                failures.append(f"{chunk_id}: invalid offsets")
            elif doc["text"][start:end] != chunk["text"]:
                failures.append(f"{chunk_id}: text mismatch")
            if int(chunk["token_count"]) > self.config.chunking.max_tokens:
                failures.append(f"{chunk_id}: token limit")
        artifacts = {artifact.artifact_id: artifact for artifact in load_artifacts(self.bronze_db)}
        import random

        randomizer = random.Random(seed)
        sampled = randomizer.sample(documents, min(sample, len(documents))) if documents else []
        for document in sampled:
            artifact = artifacts.get(int(document["artifact_id"]))
            if artifact is None:
                failures.append(f"{document['doc_id']}: artifact not active")
                continue
            if artifact.content_hash != document["content_hash"]:
                failures.append(f"{document['doc_id']}: content_hash mismatch")
            if artifact.url_canonical != document["url_canonical"]:
                failures.append(f"{document['doc_id']}: url mismatch")
        return {
            "run_id": run_id,
            "sampled": len(sampled),
            "documents": len(documents),
            "chunks": len(chunks),
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
        smoke = paths["meta"] / "smoke" / latest.parent.name
        documents_path = smoke / "documents.jsonl" if smoke.is_dir() else paths["documents"]
        chunks_path = smoke / "chunks.jsonl" if smoke.is_dir() else paths["chunks"]
        return {
            "status": payload.get("status"),
            "run_id": payload.get("run_id"),
            "documents": payload.get("documents"),
            "chunks": payload.get("chunks"),
            "processed": payload.get("processed"),
            "skipped": payload.get("skipped"),
            "failed": payload.get("failed"),
            "documents_path": documents_path.as_posix(),
            "chunks_path": chunks_path.as_posix(),
        }

    def report(self, run_id: str) -> dict[str, Any]:
        path = prepare_output(self.config.output.root)["reports"] / run_id / "quality.json"
        if not path.is_file():
            raise FileNotFoundError(f"report not found for run {run_id}")
        return json.loads(path.read_text(encoding="utf-8"))


def _document_from_dict(payload: dict[str, Any]) -> SilverDocument:
    from .models import Section

    return SilverDocument(
        schema_version=payload["schema_version"],
        doc_id=payload["doc_id"],
        artifact_id=int(payload["artifact_id"]),
        campaign_id=payload["campaign_id"],
        content_hash=payload["content_hash"],
        text_hash=payload["text_hash"],
        source_id=payload["source_id"],
        authority=payload["authority"],
        url=payload["url"],
        url_canonical=payload["url_canonical"],
        title=payload["title"],
        published_at=payload["published_at"],
        retrieved_at=payload["retrieved_at"],
        language=payload["language"],
        language_method=payload["language_method"],
        category=payload["category"],
        media_type=payload["media_type"],
        cleaning_version=payload["cleaning_version"],
        config_hash=payload["config_hash"],
        status=payload["status"],
        canonical_doc_id=payload["canonical_doc_id"],
        duplicate_of=payload["duplicate_of"],
        aliases=list(payload["aliases"]),
        quality_flags=list(payload["quality_flags"]),
        sections=[
            Section(
                section_id=section["section_id"],
                title=section["title"],
                path=list(section["path"]),
                level=int(section["level"]),
                order=int(section["order"]),
                char_start=int(section["char_start"]),
                char_end=int(section["char_end"]),
                page_start=section["page_start"],
                page_end=section["page_end"],
                time_start=section["time_start"],
                time_end=section["time_end"],
            )
            for section in payload["sections"]
        ],
        text=payload["text"],
        char_count=int(payload["char_count"]),
        token_count=int(payload["token_count"]),
        license_note=payload["license_note"],
        markdown_path=payload["markdown_path"],
    )
