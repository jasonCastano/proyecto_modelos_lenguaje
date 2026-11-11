"""Origen estructurado de solo lectura derivado del oro (spec 014, FR-012 y FR-013).

``build_structured_store`` lee ``data/gold/entities.jsonl`` y ``data/gold/facts.jsonl`` y publica,
con renombrado atómico, ``data/module2/structured/structured.sqlite3`` + ``manifest.json``. Es una
**vista derivada**: se reconstruye con ``agent build-structured`` y no se versiona.

La app solo abre la base en modo lectura (``mode=ro`` + ``PRAGMA query_only=ON``) y la consulta con
funciones parametrizadas; no hay SQL libre. Cada hecho conserva su ``unit_id`` y sus citas.

Desviación documentada respecto a ``data-model.md``: ``facts`` guarda además ``snippet`` (la frase
de la unidad de oro que contiene el valor). Los atributos extraídos automáticamente son ruidosos
(p. ej. «colombia» = 1864) y sin la frase el agente no puede interpretar el dato ni citarlo con
sentido.
"""

from __future__ import annotations

import hashlib
import json
import re
import shutil
import sqlite3
import time
import unicodedata
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

SCHEMA_VERSION = "1.0"
BUILDER_VERSION = "014.1"
DATABASE_NAME = "structured.sqlite3"
MANIFEST_NAME = "manifest.json"
ACCEPTED_STATUSES = frozenset({"current", "accepted"})
SNIPPET_RADIUS = 160
STOPWORDS = frozenset(
    {
        *("a", "al", "como", "con", "cual", "cuales", "cuando", "cuanto", "cuantos", "cuantas"),
        *("de", "del", "donde", "el", "en", "es", "esa", "ese", "eso", "esta", "este", "la"),
        *("las", "lo", "los", "mas", "me", "para", "por", "que", "quien", "se", "su", "sus"),
        *("tiene", "un", "una", "y", "ya", "hay", "fue", "son", "ha"),
    }
)


class StructuredError(RuntimeError):
    """Error base del origen estructurado."""


class StructuredGoldError(StructuredError):
    """El oro falta, está vacío o es inválido."""


class StructuredExistsError(StructuredError):
    """Ya existe una tabla y no se pidió ``force``."""


class StructuredInvalidError(StructuredError):
    """El manifiesto o la base no son válidos o están desactualizados."""


def normalize(text: str) -> str:
    """Minúsculas sin tildes, para comparar nombres y atributos."""
    decomposed = unicodedata.normalize("NFKD", text or "")
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower().strip()


def _tokens(text: str) -> set[str]:
    tokens = (token.strip(".,") for token in re.findall(r"[a-z0-9][a-z0-9.,%]*", normalize(text)))
    return {token for token in tokens if token not in STOPWORDS and len(token) > 1}


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


@dataclass(frozen=True, slots=True)
class StructuredManifest:
    built_at: str
    gold_manifest_sha256: str
    entity_count: int
    fact_count: int
    citation_count: int
    builder_version: str = BUILDER_VERSION
    schema_version: str = SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "built_at": self.built_at,
            "gold_manifest_sha256": self.gold_manifest_sha256,
            "entity_count": self.entity_count,
            "fact_count": self.fact_count,
            "citation_count": self.citation_count,
            "builder_version": self.builder_version,
        }

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> StructuredManifest:
        if payload.get("schema_version") != SCHEMA_VERSION:
            raise StructuredInvalidError("schema_version del manifiesto estructurado no soportado")
        return cls(
            built_at=str(payload["built_at"]),
            gold_manifest_sha256=str(payload["gold_manifest_sha256"]),
            entity_count=int(payload["entity_count"]),
            fact_count=int(payload["fact_count"]),
            citation_count=int(payload["citation_count"]),
            builder_version=str(payload["builder_version"]),
        )


@dataclass(frozen=True, slots=True)
class Citation:
    url: str
    title: str
    content_hash: str = ""
    authority: str = ""

    def to_dict(self) -> dict[str, str]:
        return {"url": self.url, "title": self.title}


@dataclass(frozen=True, slots=True)
class StructuredFact:
    fact_id: str
    subject_id: str
    subject_label: str
    attribute: str
    value: str
    year: int | None
    unit_id: str
    snippet: str
    citations: tuple[Citation, ...] = field(default_factory=tuple)
    score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "fact_id": self.fact_id,
            "subject_label": self.subject_label,
            "attribute": self.attribute,
            "value": self.value,
            "year": self.year,
            "unit_id": self.unit_id,
            "snippet": self.snippet,
            "citations": [citation.to_dict() for citation in self.citations],
        }


@dataclass(frozen=True, slots=True)
class StructuredEntity:
    entity_id: str
    canonical_name: str
    entity_type: str
    aliases: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "entity_id": self.entity_id,
            "canonical_name": self.canonical_name,
            "entity_type": self.entity_type,
            "aliases": list(self.aliases),
        }


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise StructuredGoldError(f"No existe {path}.")
    rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
    if not rows:
        raise StructuredGoldError(f"{path} está vacío.")
    return rows


def _snippets(units_path: Path, wanted: dict[str, str]) -> dict[str, str]:
    """Frase de cada unidad que contiene el valor del hecho (``wanted``: unit_id → valor)."""
    if not wanted or not units_path.is_file():
        return {}
    found: dict[str, str] = {}
    with units_path.open(encoding="utf-8") as handle:
        for line in handle:
            if '"unit_id"' not in line:
                continue
            payload = json.loads(line)
            unit_id = payload.get("unit_id")
            if unit_id not in wanted or unit_id in found:
                continue
            text = " ".join(str(payload.get("text", "")).split())
            position = text.find(wanted[unit_id])
            if position < 0:
                found[unit_id] = text[: SNIPPET_RADIUS * 2]
            else:
                start = max(0, position - SNIPPET_RADIUS)
                found[unit_id] = text[start : position + SNIPPET_RADIUS].strip()
    return found


SCHEMA_SQL = """
CREATE TABLE entities (
    entity_id TEXT PRIMARY KEY,
    canonical_name TEXT NOT NULL,
    name_norm TEXT NOT NULL,
    aliases TEXT NOT NULL,
    aliases_norm TEXT NOT NULL,
    entity_type TEXT NOT NULL
);
CREATE TABLE facts (
    fact_id TEXT PRIMARY KEY,
    subject_id TEXT NOT NULL REFERENCES entities(entity_id),
    subject_label TEXT NOT NULL,
    subject_norm TEXT NOT NULL,
    attribute TEXT NOT NULL,
    value TEXT NOT NULL,
    value_normalized TEXT,
    unit TEXT,
    year INTEGER,
    unit_id TEXT NOT NULL,
    status TEXT NOT NULL,
    snippet TEXT NOT NULL
);
CREATE TABLE citations (
    fact_id TEXT NOT NULL REFERENCES facts(fact_id),
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    content_hash TEXT,
    authority TEXT
);
CREATE INDEX facts_subject ON facts(subject_norm);
CREATE INDEX citations_fact ON citations(fact_id);
"""


def _rename_with_retry(source: Path, target: Path, *, attempts: int = 5) -> None:
    for attempt in range(attempts):
        try:
            source.rename(target)
            return
        except PermissionError:
            if attempt == attempts - 1:
                raise
            time.sleep(0.2 * (attempt + 1))


def build_structured_store(
    gold_dir: str | Path, target_dir: str | Path, *, force: bool = False
) -> StructuredManifest:
    """Construye la tabla estructurada desde el oro (solo lectura sobre ``gold_dir``)."""
    gold = Path(gold_dir)
    target = Path(target_dir)
    if (target / DATABASE_NAME).exists() and not force:
        raise StructuredExistsError(
            f"Ya existe {target / DATABASE_NAME}; usa --force para reconstruir."
        )
    gold_manifest = gold / "manifest.json"
    if not gold_manifest.is_file():
        raise StructuredGoldError(f"No existe {gold_manifest}.")
    entities = _read_jsonl(gold / "entities.jsonl")
    facts = [
        fact
        for fact in _read_jsonl(gold / "facts.jsonl")
        if fact.get("status") in ACCEPTED_STATUSES and fact.get("evidence")
    ]
    if not facts:
        raise StructuredGoldError("No hay hechos aceptados con evidencia en el oro.")
    known = {entity["entity_id"] for entity in entities}
    facts = [fact for fact in facts if fact.get("subject_id") in known]
    snippets = _snippets(
        gold / "knowledge_units.jsonl", {fact["unit_id"]: str(fact["value"]) for fact in facts}
    )

    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.parent / f".structured-tmp-{uuid.uuid4().hex}"
    temporary.mkdir()
    backup: Path | None = None
    citation_count = 0
    try:
        connection = sqlite3.connect(temporary / DATABASE_NAME)
        try:
            connection.executescript(SCHEMA_SQL)
            for entity in entities:
                aliases = [str(alias) for alias in entity.get("aliases") or []]
                connection.execute(
                    "INSERT INTO entities VALUES (?, ?, ?, ?, ?, ?)",
                    (
                        entity["entity_id"],
                        entity["canonical_name"],
                        normalize(entity["canonical_name"]),
                        json.dumps(aliases, ensure_ascii=False),
                        "|".join(normalize(alias) for alias in aliases),
                        entity.get("entity_type", "other"),
                    ),
                )
            for fact in facts:
                value = str(fact["value"])
                connection.execute(
                    "INSERT INTO facts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                    (
                        fact["fact_id"],
                        fact["subject_id"],
                        fact["subject_label"],
                        normalize(fact["subject_label"]),
                        normalize(str(fact.get("attribute", ""))),
                        value,
                        fact.get("value_normalized"),
                        fact.get("unit"),
                        fact.get("year"),
                        fact["unit_id"],
                        fact["status"],
                        snippets.get(fact["unit_id"], ""),
                    ),
                )
                for evidence in fact["evidence"]:
                    connection.execute(
                        "INSERT INTO citations VALUES (?, ?, ?, ?, ?)",
                        (
                            fact["fact_id"],
                            evidence.get("url", ""),
                            evidence.get("title", ""),
                            evidence.get("content_hash"),
                            evidence.get("authority"),
                        ),
                    )
                    citation_count += 1
            connection.commit()
        finally:
            connection.close()
        manifest = StructuredManifest(
            built_at=datetime.now(UTC).replace(microsecond=0).isoformat(),
            gold_manifest_sha256=sha256_file(gold_manifest),
            entity_count=len(entities),
            fact_count=len(facts),
            citation_count=citation_count,
        )
        (temporary / MANIFEST_NAME).write_text(
            json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        if target.exists():
            backup = target.parent / f".structured-old-{uuid.uuid4().hex}"
            _rename_with_retry(target, backup)
        _rename_with_retry(temporary, target)
    except Exception:
        if backup is not None and backup.exists() and not target.exists():
            backup.rename(target)
        shutil.rmtree(temporary, ignore_errors=True)
        raise
    finally:
        if backup is not None:
            shutil.rmtree(backup, ignore_errors=True)
    return manifest


class StructuredStore:
    """Acceso de solo lectura a la tabla estructurada."""

    def __init__(self, directory: str | Path, *, gold_dir: str | Path | None = None) -> None:
        self.directory = Path(directory)
        database = self.directory / DATABASE_NAME
        manifest_path = self.directory / MANIFEST_NAME
        if not (database.is_file() and manifest_path.is_file()):
            raise StructuredInvalidError(
                f"No hay tabla estructurada en {self.directory}; ejecuta `agent build-structured`."
            )
        try:
            self.manifest = StructuredManifest.from_dict(
                json.loads(manifest_path.read_text(encoding="utf-8"))
            )
        except (KeyError, ValueError, json.JSONDecodeError) as exc:
            raise StructuredInvalidError(f"Manifiesto estructurado inválido: {exc}") from exc
        if gold_dir is not None:
            gold_manifest = Path(gold_dir) / "manifest.json"
            if (
                gold_manifest.is_file()
                and sha256_file(gold_manifest) != self.manifest.gold_manifest_sha256
            ):
                raise StructuredInvalidError(
                    "La tabla estructurada no corresponde al oro actual; reconstruye con "
                    "`agent build-structured --force`."
                )
        uri = f"{database.resolve().as_uri()}?mode=ro"
        self._connection = sqlite3.connect(uri, uri=True, check_same_thread=False)
        self._connection.execute("PRAGMA query_only = ON")
        self._connection.row_factory = sqlite3.Row

    def close(self) -> None:
        self._connection.close()

    def __enter__(self) -> StructuredStore:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _citations(self, fact_ids: Sequence[str]) -> dict[str, tuple[Citation, ...]]:
        if not fact_ids:
            return {}
        placeholders = ",".join("?" for _ in fact_ids)
        rows = self._connection.execute(
            f"SELECT fact_id, url, title, content_hash, authority FROM citations "
            f"WHERE fact_id IN ({placeholders})",
            tuple(fact_ids),
        ).fetchall()
        grouped: dict[str, list[Citation]] = {}
        for row in rows:
            grouped.setdefault(row["fact_id"], []).append(
                Citation(
                    row["url"], row["title"], row["content_hash"] or "", row["authority"] or ""
                )
            )
        return {key: tuple(value) for key, value in grouped.items()}

    def _facts(self, rows: Iterable[sqlite3.Row], scores: dict[str, float] | None = None):
        rows = list(rows)
        citations = self._citations([row["fact_id"] for row in rows])
        return [
            StructuredFact(
                fact_id=row["fact_id"],
                subject_id=row["subject_id"],
                subject_label=row["subject_label"],
                attribute=row["attribute"],
                value=row["value"],
                year=row["year"],
                unit_id=row["unit_id"],
                snippet=row["snippet"],
                citations=citations.get(row["fact_id"], ()),
                score=(scores or {}).get(row["fact_id"], 0.0),
            )
            for row in rows
        ]

    def list_entities(self, entity_type: str | None = None) -> list[StructuredEntity]:
        """Entidades del oro, opcionalmente filtradas por tipo (``subsidiary``, ``brand``…)."""
        query = "SELECT * FROM entities"
        params: tuple[str, ...] = ()
        if entity_type:
            query += " WHERE entity_type = ?"
            params = (entity_type,)
        rows = self._connection.execute(query + " ORDER BY canonical_name", params).fetchall()
        return [
            StructuredEntity(
                row["entity_id"],
                row["canonical_name"],
                row["entity_type"],
                tuple(json.loads(row["aliases"])),
            )
            for row in rows
        ]

    def _subject_ids(self, subject: str) -> list[str]:
        needle = normalize(subject)
        rows = self._connection.execute("SELECT entity_id, name_norm, aliases_norm FROM entities")
        return [
            row["entity_id"]
            for row in rows
            if needle == row["name_norm"]
            or needle in row["aliases_norm"].split("|")
            or (len(needle) > 3 and needle in row["name_norm"])
        ]

    def get_facts(
        self, subject: str | None = None, attribute: str | None = None, *, limit: int = 20
    ) -> list[StructuredFact]:
        """Hechos por sujeto (nombre o alias) y fragmento de atributo, con sus citas."""
        clauses: list[str] = []
        params: list[Any] = []
        if subject:
            ids = self._subject_ids(subject)
            if not ids:
                return []
            clauses.append(f"subject_id IN ({','.join('?' for _ in ids)})")
            params.extend(ids)
        if attribute:
            clauses.append("attribute LIKE ?")
            params.append(f"%{normalize(attribute)}%")
        where = f" WHERE {' AND '.join(clauses)}" if clauses else ""
        rows = self._connection.execute(
            f"SELECT * FROM facts{where} ORDER BY fact_id LIMIT ?",
            (*params, max(1, limit)),
        ).fetchall()
        return self._facts(rows)

    def search_facts(self, text: str, *, limit: int = 8) -> list[StructuredFact]:
        """Hechos cuyo sujeto, atributo o frase comparten términos con la consulta."""
        query_tokens = _tokens(text)
        if not query_tokens:
            return []
        scores: dict[str, float] = {}
        rows_by_id: dict[str, sqlite3.Row] = {}
        for row in self._connection.execute("SELECT * FROM facts"):
            haystack = _tokens(f"{row['subject_label']} {row['attribute']} {row['snippet']}")
            overlap = query_tokens & haystack
            if not overlap:
                continue
            scores[row["fact_id"]] = len(overlap) / len(query_tokens)
            rows_by_id[row["fact_id"]] = row
        best = sorted(scores, key=lambda key: (-scores[key], key))[: max(1, limit)]
        return self._facts([rows_by_id[key] for key in best], scores)
