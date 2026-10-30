"""Read canonical silver documents and chunks for the gold layer."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .store import read_jsonl


@dataclass(frozen=True, slots=True)
class SilverDocument:
    doc_id: str
    content_hash: str
    text_hash: str
    url: str
    url_canonical: str
    title: str
    authority: str
    language: str
    published_at: str | None
    retrieved_at: str
    source_id: str


@dataclass(frozen=True, slots=True)
class SilverChunk:
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
    section_path: tuple[str, ...]
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
    quality_flags: tuple[str, ...]
    retrieved_at: str
    license_note: str


def load_silver_input(
    silver_dir: str | Path,
) -> tuple[list[SilverDocument], dict[str, list[SilverChunk]]]:
    root = Path(silver_dir)
    documents_path = root / "documents.jsonl"
    chunks_path = root / "chunks.jsonl"
    if not documents_path.is_file() or not chunks_path.is_file():
        raise FileNotFoundError(f"silver corpus not found in {root}")
    documents: list[SilverDocument] = []
    for payload in read_jsonl(documents_path):
        if payload.get("status") != "canonical":
            continue
        documents.append(
            SilverDocument(
                doc_id=str(payload["doc_id"]),
                content_hash=str(payload["content_hash"]),
                text_hash=str(payload["text_hash"]),
                url=str(payload["url"]),
                url_canonical=str(payload["url_canonical"]),
                title=str(payload["title"]),
                authority=str(payload["authority"]),
                language=str(payload["language"]),
                published_at=payload.get("published_at"),
                retrieved_at=str(payload["retrieved_at"]),
                source_id=str(payload["source_id"]),
            )
        )
    by_doc: dict[str, list[SilverChunk]] = {document.doc_id: [] for document in documents}
    for payload in read_jsonl(chunks_path):
        doc_id = str(payload.get("doc_id", ""))
        if doc_id not in by_doc:
            continue
        chunk = SilverChunk(
            chunk_id=str(payload["chunk_id"]),
            doc_id=doc_id,
            artifact_id=int(payload["artifact_id"]),
            content_hash=str(payload["content_hash"]),
            source_id=str(payload["source_id"]),
            authority=str(payload["authority"]),
            url=str(payload["url"]),
            title=str(payload["title"]),
            section_id=str(payload["section_id"]),
            section_title=str(payload["section_title"]),
            section_path=tuple(payload.get("section_path") or [payload["section_title"]]),
            chunk_order=int(payload.get("chunk_order", 0)),
            text=str(payload["text"]),
            char_start=int(payload["char_start"]),
            char_end=int(payload["char_end"]),
            token_count=int(payload["token_count"]),
            page_start=payload.get("page_start"),
            page_end=payload.get("page_end"),
            time_start=payload.get("time_start"),
            time_end=payload.get("time_end"),
            language=str(payload["language"]),
            media_type=str(payload["media_type"]),
            quality_flags=tuple(payload.get("quality_flags") or []),
            retrieved_at=str(payload["retrieved_at"]),
            license_note=str(payload["license_note"]),
        )
        if not chunk.text.strip() or not chunk.section_path:
            continue
        by_doc[doc_id].append(chunk)
    for chunks in by_doc.values():
        chunks.sort(key=lambda item: item.chunk_id)
    return documents, by_doc
