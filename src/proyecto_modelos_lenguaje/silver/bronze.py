"""Read-only access to the bronze catalog for the silver layer."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ..storage import sha256_bytes


@dataclass(frozen=True, slots=True)
class BronzeArtifact:
    artifact_id: int
    content_hash: str
    text_hash: str | None
    media_type: str
    byte_size: int
    storage_path: str
    retrieved_at: str
    source_id: str
    campaign_id: str
    authority: str
    language: str
    language_method: str
    title: str | None
    published_at: str | None
    version: int
    url_original: str
    url_canonical: str
    category: str

    @property
    def is_pdf(self) -> bool:
        return self.media_type == "application/pdf"


def _connect_read_only(db_path: Path) -> sqlite3.Connection:
    uri = f"file:{db_path.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def load_artifacts(
    db_path: Path,
    *,
    source_id: str | None = None,
    limit: int | None = None,
) -> list[BronzeArtifact]:
    """Return active bronze artifacts, including all active versions."""
    if not db_path.is_file():
        raise FileNotFoundError(f"bronze catalog not found: {db_path}")
    clauses = []
    params: list[object] = []
    if source_id:
        clauses.append("source_id = ?")
        params.append(source_id)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    limit_sql = "LIMIT ?" if limit else ""
    if limit:
        params.append(limit)
    query = f"""
        SELECT artifact_id, content_hash, text_hash, media_type, byte_size, storage_path,
               retrieved_at, source_id, campaign_id, authority, language, language_method,
               title, published_at, version, url_original, url_canonical, category
        FROM v_active_artifacts
        {where}
        ORDER BY artifact_id
        {limit_sql}
    """
    with _connect_read_only(db_path) as connection:
        rows = connection.execute(query, params).fetchall()
    return [
        BronzeArtifact(
            artifact_id=int(row["artifact_id"]),
            content_hash=str(row["content_hash"]),
            text_hash=row["text_hash"],
            media_type=str(row["media_type"]),
            byte_size=int(row["byte_size"]),
            storage_path=str(row["storage_path"]),
            retrieved_at=str(row["retrieved_at"]),
            source_id=str(row["source_id"]),
            campaign_id=str(row["campaign_id"]),
            authority=str(row["authority"]),
            language=str(row["language"]),
            language_method=str(row["language_method"]),
            title=row["title"],
            published_at=row["published_at"],
            version=int(row["version"]),
            url_original=str(row["url_original"]),
            url_canonical=str(row["url_canonical"]),
            category=str(row["category"]),
        )
        for row in rows
    ]


def latest_by_url(artifacts: list[BronzeArtifact]) -> dict[str, BronzeArtifact]:
    latest: dict[str, BronzeArtifact] = {}
    for artifact in artifacts:
        current = latest.get(artifact.url_canonical)
        if current is None or artifact.version > current.version:
            latest[artifact.url_canonical] = artifact
    return latest


def read_artifact_bytes(artifact: BronzeArtifact, bronze_dir: Path) -> bytes:
    root = bronze_dir.resolve()
    path = (root / artifact.storage_path).resolve()
    try:
        path.relative_to(root)
    except ValueError as exc:
        raise ValueError(
            f"artifact path escapes bronze directory: {artifact.storage_path}"
        ) from exc
    if not path.is_file():
        raise FileNotFoundError(f"artifact file not found: {artifact.storage_path}")
    return path.read_bytes()


def verify_artifact(artifact: BronzeArtifact, bronze_dir: Path) -> bool:
    data = read_artifact_bytes(artifact, bronze_dir)
    return sha256_bytes(data) == artifact.content_hash
