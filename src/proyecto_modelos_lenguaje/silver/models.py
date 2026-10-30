"""Data model for the silver layer."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any

LICENSE_NOTE = (
    "Uso académico. Contenido público de su fuente original; se cita la URL y la fecha de captura."
)


class DocumentStatus(StrEnum):
    CANONICAL = "canonical"
    ALIAS = "alias"


class ProcessStatus(StrEnum):
    PROCESSED = "processed"
    SKIPPED = "skipped"
    FAILED = "failed"


class QualityFlag(StrEnum):
    NO_TEXT = "no_text"
    SCANNED_PDF = "scanned_pdf"
    ENCRYPTED_PDF = "encrypted_pdf"
    LOW_TEXT_DENSITY = "low_text_density"
    TABLE_HEAVY = "table_heavy"
    MULTI_COLUMN_SUSPECT = "multi_column_suspect"
    ENCODING_REPAIRED = "encoding_repaired"
    NO_SECTION = "no_section"
    SHORT_SECTION = "short_section"
    EXACT_DUPLICATE = "exact_duplicate"
    NEAR_DUPLICATE = "near_duplicate"
    LANGUAGE_UNKNOWN = "language_unknown"
    SUBTITLE_KIND_UNKNOWN = "subtitle_kind_unknown"


def make_doc_id(url_canonical: str, content_hash: str) -> str:
    digest = hashlib.sha256(f"{url_canonical}:{content_hash}".encode()).hexdigest()
    return f"doc_{digest[:16]}"


def make_section_id(doc_id: str, order: int) -> str:
    return f"{doc_id}-s{order:03d}"


def make_chunk_id(doc_id: str, section_order: int, chunk_order: int) -> str:
    return f"{doc_id}-s{section_order:03d}-c{chunk_order:04d}"


@dataclass(slots=True)
class ExtractedBlock:
    """A paragraph or heading produced by an extractor, before offsets are assigned."""

    text: str
    level: int = 0
    page: int | None = None
    time_start: float | None = None
    time_end: float | None = None
    char_start: int = 0
    char_end: int = 0


@dataclass(slots=True)
class ExtractedDocument:
    """Normalized extractor output shared by every format."""

    title: str | None
    blocks: list[ExtractedBlock]
    metadata: dict[str, Any] = field(default_factory=dict)
    skip_reason: str | None = None
    flags: set[str] = field(default_factory=set)

    @property
    def text(self) -> str:
        return "\n\n".join(block.text for block in self.blocks if block.text.strip())


@dataclass(slots=True)
class Section:
    section_id: str
    title: str
    path: list[str]
    level: int
    order: int
    char_start: int
    char_end: int
    page_start: int | None = None
    page_end: int | None = None
    time_start: float | None = None
    time_end: float | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "section_id": self.section_id,
            "title": self.title,
            "path": list(self.path),
            "level": self.level,
            "order": self.order,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "time_start": self.time_start,
            "time_end": self.time_end,
        }


@dataclass(slots=True)
class Chunk:
    schema_version: str
    chunk_id: str
    doc_id: str
    artifact_id: int
    content_hash: str
    source_id: str
    authority: str
    url: str
    title: str
    section_id: str
    section_title: str
    section_path: list[str]
    section_level: int
    chunk_order: int
    text: str
    char_start: int
    char_end: int
    token_count: int
    page_start: int | None
    page_end: int | None
    time_start: float | None
    time_end: float | None
    language: str
    media_type: str
    quality_flags: list[str]
    duplicate_of: str | None
    retrieved_at: str
    license_note: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "chunk_id": self.chunk_id,
            "doc_id": self.doc_id,
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "source_id": self.source_id,
            "authority": self.authority,
            "url": self.url,
            "title": self.title,
            "section_id": self.section_id,
            "section_title": self.section_title,
            "section_path": list(self.section_path),
            "section_level": self.section_level,
            "chunk_order": self.chunk_order,
            "text": self.text,
            "char_start": self.char_start,
            "char_end": self.char_end,
            "token_count": self.token_count,
            "page_start": self.page_start,
            "page_end": self.page_end,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "language": self.language,
            "media_type": self.media_type,
            "quality_flags": list(self.quality_flags),
            "duplicate_of": self.duplicate_of,
            "retrieved_at": self.retrieved_at,
            "license_note": self.license_note,
        }


@dataclass(slots=True)
class SilverDocument:
    schema_version: str
    doc_id: str
    artifact_id: int
    campaign_id: str
    content_hash: str
    text_hash: str
    source_id: str
    authority: str
    url: str
    url_canonical: str
    title: str
    published_at: str | None
    retrieved_at: str
    language: str
    language_method: str
    category: str
    media_type: str
    cleaning_version: str
    config_hash: str
    status: str
    canonical_doc_id: str | None
    duplicate_of: str | None
    aliases: list[str]
    quality_flags: list[str]
    sections: list[Section]
    text: str
    char_count: int
    token_count: int
    license_note: str
    markdown_path: str | None
    version: int = 1
    blocks: list[ExtractedBlock] = field(default_factory=list, repr=False)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "doc_id": self.doc_id,
            "artifact_id": self.artifact_id,
            "campaign_id": self.campaign_id,
            "content_hash": self.content_hash,
            "text_hash": self.text_hash,
            "source_id": self.source_id,
            "authority": self.authority,
            "url": self.url,
            "url_canonical": self.url_canonical,
            "title": self.title,
            "published_at": self.published_at,
            "retrieved_at": self.retrieved_at,
            "language": self.language,
            "language_method": self.language_method,
            "category": self.category,
            "media_type": self.media_type,
            "cleaning_version": self.cleaning_version,
            "config_hash": self.config_hash,
            "status": self.status,
            "canonical_doc_id": self.canonical_doc_id,
            "duplicate_of": self.duplicate_of,
            "aliases": list(self.aliases),
            "quality_flags": list(self.quality_flags),
            "sections": [section.to_dict() for section in self.sections],
            "text": self.text,
            "char_count": self.char_count,
            "token_count": self.token_count,
            "license_note": self.license_note,
            "markdown_path": self.markdown_path,
        }


@dataclass(slots=True)
class ProcessingRecord:
    artifact_id: int
    content_hash: str
    config_hash: str
    status: str
    reason: str | None
    doc_id: str | None
    documents: int
    chunks: int
    quality_flags: list[str]
    processed_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "artifact_id": self.artifact_id,
            "content_hash": self.content_hash,
            "config_hash": self.config_hash,
            "status": self.status,
            "reason": self.reason,
            "doc_id": self.doc_id,
            "documents": self.documents,
            "chunks": self.chunks,
            "quality_flags": list(self.quality_flags),
            "processed_at": self.processed_at,
        }


@dataclass(slots=True)
class DuplicateGroup:
    group_id: str
    kind: str
    canonical_doc_id: str
    members: list[str]
    similarity: float | None
    reason: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "kind": self.kind,
            "canonical_doc_id": self.canonical_doc_id,
            "members": list(self.members),
            "similarity": self.similarity,
            "reason": self.reason,
        }


@dataclass(slots=True)
class RunReport:
    schema_version: str
    run_id: str
    started_at: str
    finished_at: str
    status: str
    config_hash: str
    cleaning_version: str
    tool_version: str
    git_commit: str | None
    input_artifacts: int
    processed: int
    skipped: int
    failed: int
    documents: int
    canonical_documents: int
    alias_documents: int
    chunks: int
    duplicates_exact: int
    duplicates_near: int
    tokens_in: int
    tokens_out: int
    bytes_out: int
    duration_seconds: float
    by_source: dict[str, int]
    by_media_type: dict[str, int]
    by_status: dict[str, int]
    skip_reasons: dict[str, int]
    failure_reasons: dict[str, int]
    quality_flags: dict[str, int]
    section_coverage: dict[str, int]
    report_paths: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "run_id": self.run_id,
            "started_at": self.started_at,
            "finished_at": self.finished_at,
            "status": self.status,
            "config_hash": self.config_hash,
            "cleaning_version": self.cleaning_version,
            "tool_version": self.tool_version,
            "git_commit": self.git_commit,
            "input_artifacts": self.input_artifacts,
            "processed": self.processed,
            "skipped": self.skipped,
            "failed": self.failed,
            "documents": self.documents,
            "canonical_documents": self.canonical_documents,
            "alias_documents": self.alias_documents,
            "chunks": self.chunks,
            "duplicates_exact": self.duplicates_exact,
            "duplicates_near": self.duplicates_near,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "bytes_out": self.bytes_out,
            "duration_seconds": self.duration_seconds,
            "by_source": dict(self.by_source),
            "by_media_type": dict(self.by_media_type),
            "by_status": dict(self.by_status),
            "skip_reasons": dict(self.skip_reasons),
            "failure_reasons": dict(self.failure_reasons),
            "quality_flags": dict(self.quality_flags),
            "section_coverage": dict(self.section_coverage),
            "report_paths": list(self.report_paths),
        }


def validate_document(document: SilverDocument) -> None:
    """Validate the invariants that the JSON Schema cannot express."""
    if not document.doc_id.startswith("doc_") or len(document.doc_id) != 20:
        raise ValueError(f"invalid doc_id: {document.doc_id}")
    if not document.title.strip():
        raise ValueError(f"{document.doc_id}: title must not be empty")
    if not document.sections:
        raise ValueError(f"{document.doc_id}: at least one section is required")
    if not document.text.strip():
        raise ValueError(f"{document.doc_id}: text must not be empty")
    if document.char_count != len(document.text):
        raise ValueError(f"{document.doc_id}: char_count does not match text length")
    for section in document.sections:
        if not section.section_id.startswith(document.doc_id):
            raise ValueError(f"{section.section_id}: section does not belong to document")
        if not section.title.strip():
            raise ValueError(f"{section.section_id}: section title must not be empty")
        if not section.path:
            raise ValueError(f"{section.section_id}: section path must not be empty")
        if section.char_end <= section.char_start:
            raise ValueError(f"{section.section_id}: empty section range")
        if section.char_end > len(document.text):
            raise ValueError(f"{section.section_id}: section range exceeds document text")


def validate_chunk(chunk: Chunk, document: SilverDocument, *, max_tokens: int) -> None:
    if chunk.token_count > max_tokens:
        raise ValueError(f"{chunk.chunk_id}: token_count exceeds max_tokens")
    if not 0 <= chunk.char_start < chunk.char_end <= len(document.text):
        raise ValueError(f"{chunk.chunk_id}: invalid character range")
    if document.text[chunk.char_start : chunk.char_end] != chunk.text:
        raise ValueError(f"{chunk.chunk_id}: text does not match document range")
