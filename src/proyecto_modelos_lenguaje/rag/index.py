"""Índice vectorial reproducible: fragmentos, matriz normalizada y manifiesto."""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import numpy as np

from ..retrieval import GoldUnit
from ..silver.cleaning import estimate_tokens
from .embeddings import Embedder, EmbeddingProfile
from .errors import GoldError, IndexExistsError, IndexInvalidError, IndexUnavailableError

CHARS_PER_TOKEN = 3.5
CHUNK_TARGET_TOKENS = 480
CHUNK_OVERLAP_TOKENS = 32
SCHEMA_VERSION = 1
SHA256_PATTERN = re.compile(r"^[a-f0-9]{64}$")
MANIFEST_NAME = "manifest.json"
VECTORS_NAME = "vectors.npy"
DATABASE_NAME = "index.sqlite3"


def sha256_file(path: Path) -> str:
    """Return the SHA-256 hex digest of a file."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class Fragment:
    """Unidad mínima recuperable del índice."""

    fragment_id: str
    unit_id: str
    doc_id: str
    title: str
    url: str
    published_at: str | None
    topic: str | None
    text: str
    tokens: int
    chunk_index: int
    chunk_total: int

    def __post_init__(self) -> None:
        if not self.fragment_id.strip():
            raise ValueError("fragment_id no puede estar vacío")
        if not self.unit_id.strip():
            raise ValueError("unit_id no puede estar vacío")
        if not self.text.strip():
            raise ValueError("text no puede estar vacío")
        if self.tokens < 1:
            raise ValueError("tokens debe ser >= 1")
        if self.chunk_index < 1 or self.chunk_total < self.chunk_index:
            raise ValueError("chunk_index debe estar entre 1 y chunk_total")

    def to_row(self, position: int) -> tuple[Any, ...]:
        return (
            position,
            self.fragment_id,
            self.unit_id,
            self.doc_id,
            self.title,
            self.url,
            self.published_at,
            self.topic,
            self.text,
            self.tokens,
            self.chunk_index,
            self.chunk_total,
        )

    @classmethod
    def from_row(cls, row: Sequence[Any]) -> Fragment:
        return cls(
            fragment_id=str(row[1]),
            unit_id=str(row[2]),
            doc_id=str(row[3]),
            title=str(row[4]),
            url=str(row[5]),
            published_at=str(row[6]) if row[6] is not None else None,
            topic=str(row[7]) if row[7] is not None else None,
            text=str(row[8]),
            tokens=int(row[9]),
            chunk_index=int(row[10]),
            chunk_total=int(row[11]),
        )


@dataclass(frozen=True, slots=True)
class IndexManifest:
    """Manifiesto versionado que describe cómo se construyó el índice."""

    model: str
    dimension: int
    normalize: bool
    max_tokens: int
    count: int
    gold_sha256: str
    created_at: str
    schema_version: int = SCHEMA_VERSION
    library: str = ""
    gold_path: str = ""
    command: str = ""

    def __post_init__(self) -> None:
        if self.schema_version != SCHEMA_VERSION:
            raise ValueError(f"schema_version debe ser {SCHEMA_VERSION}")
        if not self.model.strip():
            raise ValueError("model no puede estar vacío")
        if self.dimension < 1:
            raise ValueError("dimension debe ser >= 1")
        if self.count < 0:
            raise ValueError("count debe ser >= 0")
        if not SHA256_PATTERN.match(self.gold_sha256):
            raise ValueError("gold_sha256 debe ser un SHA-256 hexadecimal de 64 caracteres")

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema_version": self.schema_version,
            "model": self.model,
            "dimension": self.dimension,
            "normalize": self.normalize,
            "max_tokens": self.max_tokens,
            "count": self.count,
            "gold_sha256": self.gold_sha256,
            "created_at": self.created_at,
        }
        if self.library:
            payload["library"] = self.library
        if self.gold_path:
            payload["gold_path"] = self.gold_path
        if self.command:
            payload["command"] = self.command
        return payload

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> IndexManifest:
        return cls(
            model=str(payload["model"]),
            dimension=int(payload["dimension"]),
            normalize=bool(payload["normalize"]),
            max_tokens=int(payload["max_tokens"]),
            count=int(payload["count"]),
            gold_sha256=str(payload["gold_sha256"]),
            created_at=str(payload["created_at"]),
            schema_version=int(payload.get("schema_version", SCHEMA_VERSION)),
            library=str(payload.get("library", "")),
            gold_path=str(payload.get("gold_path", "")),
            command=str(payload.get("command", "")),
        )

    def matches(self, profile: EmbeddingProfile) -> bool:
        return (
            self.model == profile.model
            and self.dimension == profile.dimension
            and self.normalize == profile.normalize
            and self.max_tokens == profile.max_tokens
        )


def chunk_text(
    text: str, *, max_tokens: int, overlap_tokens: int = CHUNK_OVERLAP_TOKENS
) -> list[str]:
    """Split text only when it exceeds the model token limit.

    Las unidades que caben se devuelven intactas. Las que exceden se parten en ventanas de
    ``CHUNK_TARGET_TOKENS`` con ``overlap_tokens`` de solape, respetando límites de palabra.
    """
    if max_tokens < 1:
        raise ValueError("max_tokens debe ser >= 1")
    if estimate_tokens(text) <= max_tokens:
        return [text]
    target_chars = max(200, int(CHUNK_TARGET_TOKENS * CHARS_PER_TOKEN))
    overlap_chars = max(0, int(overlap_tokens * CHARS_PER_TOKEN))
    chunks: list[str] = []
    start = 0
    length = len(text)
    while start < length:
        end = min(start + target_chars, length)
        if end < length:
            boundary = text.rfind(" ", start, end)
            if boundary > start + target_chars // 2:
                end = boundary
        piece = text[start:end].strip()
        if piece:
            chunks.append(piece)
        if end >= length:
            break
        next_start = max(end - overlap_chars, start + 1)
        space = text.find(" ", next_start, min(next_start + 40, length))
        start = space + 1 if space != -1 else next_start
    return chunks or [text]


def build_fragments(units: Iterable[GoldUnit], profile: EmbeddingProfile) -> list[Fragment]:
    """Map gold units to indexable fragments, chunking only oversized units."""
    fragments: list[Fragment] = []
    for unit in units:
        if not unit.text.strip():
            continue
        pieces = chunk_text(unit.text, max_tokens=profile.max_tokens)
        total = len(pieces)
        for index, piece in enumerate(pieces, start=1):
            fragment_id = unit.unit_id if total == 1 else f"{unit.unit_id}#{index}"
            fragments.append(
                Fragment(
                    fragment_id=fragment_id,
                    unit_id=unit.unit_id,
                    doc_id=unit.topic_id,
                    title=unit.title or unit.topic_title,
                    url=unit.url,
                    published_at=unit.published_at,
                    topic=unit.topic_title or unit.topic_id,
                    text=piece,
                    tokens=estimate_tokens(piece),
                    chunk_index=index,
                    chunk_total=total,
                )
            )
    return fragments


def _library_version() -> str:
    try:
        from importlib.metadata import version

        return f"fastembed {version('fastembed')}"
    except Exception:
        return ""


def _relative_display(path: Path) -> str:
    try:
        return path.resolve().relative_to(Path.cwd().resolve()).as_posix()
    except ValueError:
        return path.name


def _write_database(path: Path, fragments: Sequence[Fragment]) -> None:
    connection = sqlite3.connect(path)
    try:
        connection.execute(
            """
            CREATE TABLE fragments (
                position INTEGER PRIMARY KEY,
                fragment_id TEXT UNIQUE NOT NULL,
                unit_id TEXT NOT NULL,
                doc_id TEXT NOT NULL,
                title TEXT NOT NULL,
                url TEXT NOT NULL,
                published_at TEXT,
                topic TEXT,
                text TEXT NOT NULL,
                tokens INTEGER NOT NULL,
                chunk_index INTEGER NOT NULL,
                chunk_total INTEGER NOT NULL
            )
            """
        )
        connection.executemany(
            "INSERT INTO fragments VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [fragment.to_row(position) for position, fragment in enumerate(fragments)],
        )
        connection.execute("CREATE INDEX fragments_unit ON fragments(unit_id)")
        connection.commit()
    finally:
        connection.close()


def _read_database(path: Path) -> tuple[Fragment, ...]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            "SELECT position, fragment_id, unit_id, doc_id, title, url, published_at, topic, "
            "text, tokens, chunk_index, chunk_total FROM fragments ORDER BY position"
        ).fetchall()
    finally:
        connection.close()
    return tuple(Fragment.from_row(row) for row in rows)


def _load_units_from_file(path: Path) -> tuple[GoldUnit, ...]:
    """Read gold units directly from a JSONL file (real corpus or fixture)."""
    units: list[GoldUnit] = []
    try:
        content = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise GoldError(f"No se pudo leer la capa de oro {path}: {exc}") from exc
    for number, line in enumerate(content.splitlines(), start=1):
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as exc:
            raise GoldError(f"JSON inválido en {path.name}, línea {number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise GoldError(f"Registro no válido en {path.name}, línea {number}.")
        units.append(GoldUnit.from_dict(payload))
    return tuple(units)


def build_index(
    gold_path: str | Path,
    index_dir: str | Path,
    embedder: Embedder,
    profile: EmbeddingProfile,
    *,
    force: bool = False,
    command: str = "",
) -> IndexManifest:
    """Build the index from the gold layer and publish it atomically."""
    gold_file = Path(gold_path)
    if not gold_file.is_file():
        raise GoldError(f"No existe la capa de oro: {gold_file}.")
    gold_sha256 = sha256_file(gold_file)
    target = Path(index_dir)

    if not force and (target / MANIFEST_NAME).is_file():
        try:
            existing = IndexManifest.from_dict(
                json.loads((target / MANIFEST_NAME).read_text(encoding="utf-8"))
            )
        except OSError, ValueError, KeyError, json.JSONDecodeError:
            existing = None
        if (
            existing is not None
            and existing.gold_sha256 == gold_sha256
            and existing.matches(profile)
        ):
            raise IndexExistsError(
                "Ya existe un índice equivalente; usa --force para reconstruirlo."
            )

    try:
        units = _load_units_from_file(gold_file)
    except GoldError:
        raise
    except Exception as exc:
        raise GoldError(f"No se pudo leer la capa de oro: {exc}") from exc
    if not units:
        raise GoldError("La capa de oro está vacía; no hay nada que indexar.")

    fragments = build_fragments(units, profile)
    if not fragments:
        raise GoldError("Ninguna unidad de oro produjo fragmentos indexables.")

    vectors = np.asarray(
        embedder.embed_passages([fragment.text for fragment in fragments]), dtype=np.float32
    )
    if vectors.ndim != 2 or vectors.shape != (len(fragments), profile.dimension):
        raise IndexInvalidError(
            "La matriz de vectores no coincide con los fragmentos o la dimensión configurada."
        )

    manifest = IndexManifest(
        model=profile.model,
        dimension=profile.dimension,
        normalize=profile.normalize,
        max_tokens=profile.max_tokens,
        count=len(fragments),
        gold_sha256=gold_sha256,
        created_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
        library=_library_version(),
        gold_path=_relative_display(gold_file),
        command=command,
    )

    parent = target.parent
    parent.mkdir(parents=True, exist_ok=True)
    temporary = parent / f".index-tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    backup: Path | None = None
    try:
        np.save(temporary / VECTORS_NAME, vectors)
        _write_database(temporary / DATABASE_NAME, fragments)
        (temporary / MANIFEST_NAME).write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        if target.exists():
            backup = parent / f".index-old-{uuid.uuid4().hex}"
            target.rename(backup)
        temporary.rename(target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            backup.rename(target)
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    else:
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
    return manifest


@dataclass(frozen=True, slots=True)
class LoadedIndex:
    """Índice cargado en memoria: matriz normalizada y metadatos."""

    directory: Path
    manifest: IndexManifest
    vectors: np.ndarray
    fragments: tuple[Fragment, ...]

    @property
    def unit_ids(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(fragment.unit_id for fragment in self.fragments))

    def vector_for_unit(self, unit_id: str) -> np.ndarray | None:
        for position, fragment in enumerate(self.fragments):
            if fragment.unit_id == unit_id:
                return self.vectors[position]
        return None


def load_index(index_dir: str | Path, profile: EmbeddingProfile | None = None) -> LoadedIndex:
    """Load and validate an index; raise a controlled error when unusable."""
    directory = Path(index_dir)
    manifest_path = directory / MANIFEST_NAME
    vectors_path = directory / VECTORS_NAME
    database_path = directory / DATABASE_NAME
    if not (manifest_path.is_file() and vectors_path.is_file() and database_path.is_file()):
        raise IndexUnavailableError(
            f"No hay índice completo en {directory}. Construye uno con `rag index build`."
        )
    try:
        manifest = IndexManifest.from_dict(json.loads(manifest_path.read_text(encoding="utf-8")))
    except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
        raise IndexInvalidError(f"Manifiesto inválido en {manifest_path}: {exc}") from exc
    try:
        vectors = np.load(vectors_path, allow_pickle=False)
    except (OSError, ValueError) as exc:
        raise IndexInvalidError(f"No se pudo leer {vectors_path}: {exc}") from exc
    if vectors.ndim != 2 or vectors.shape[1] != manifest.dimension:
        raise IndexInvalidError(
            f"La matriz tiene forma {vectors.shape}; el manifiesto declara dimensión "
            f"{manifest.dimension}."
        )
    if vectors.shape[0] != manifest.count:
        raise IndexInvalidError(
            f"La matriz tiene {vectors.shape[0]} filas y el manifiesto declara {manifest.count}."
        )
    fragments = _read_database(database_path)
    if len(fragments) != manifest.count:
        raise IndexInvalidError(
            f"La base tiene {len(fragments)} fragmentos y el manifiesto declara {manifest.count}."
        )
    if profile is not None and not manifest.matches(profile):
        raise IndexInvalidError(
            "El índice se construyó con otro perfil de embeddings "
            f"({manifest.model}, {manifest.dimension}d) y la configuración usa "
            f"({profile.model}, {profile.dimension}d). Reconstruye con `rag index rebuild`."
        )
    return LoadedIndex(
        directory=directory,
        manifest=manifest,
        vectors=np.asarray(vectors, dtype=np.float32),
        fragments=fragments,
    )


@dataclass(frozen=True, slots=True)
class VerificationResult:
    ok: bool
    code: int
    messages: tuple[str, ...]
    manifest: IndexManifest | None = None


def verify_index(
    index_dir: str | Path,
    profile: EmbeddingProfile | None = None,
    *,
    gold_path: str | Path | None = None,
) -> VerificationResult:
    """Check manifest, matrix, database and gold freshness.

    Códigos: ``0`` correcto, ``5`` inválido, ``6`` desactualizado respecto de la capa de oro.
    """
    directory = Path(index_dir)
    try:
        loaded = load_index(directory, profile)
    except IndexUnavailableError as exc:
        return VerificationResult(ok=False, code=5, messages=(str(exc),))
    except IndexInvalidError as exc:
        return VerificationResult(ok=False, code=5, messages=(str(exc),))

    messages = [
        f"Índice válido: {loaded.manifest.count} fragmentos de "
        f"{loaded.manifest.dimension} dimensiones."
    ]
    code = 0
    ok = True
    if gold_path is not None and Path(gold_path).is_file():
        current = sha256_file(Path(gold_path))
        if current != loaded.manifest.gold_sha256:
            ok = False
            code = 6
            messages.append(
                "El índice está desactualizado respecto de la capa de oro; ejecuta "
                "`rag index rebuild`."
            )
    return VerificationResult(ok=ok, code=code, messages=tuple(messages), manifest=loaded.manifest)
