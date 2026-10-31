"""Recuperación léxica determinista sobre la capa de oro del Módulo 1.

No usa embeddings, base vectorial ni red: puntúa unidades con una variante simplificada de BM25 y
señales de calidad, y selecciona la evidencia con diversidad por tema y presupuesto de tokens.
"""

from __future__ import annotations

import json
import math
import re
import unicodedata
from collections import Counter
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .silver.cleaning import estimate_tokens

UNIT_ID_PATTERN = re.compile(r"^unit_[a-f0-9]{16}$")
TOKEN_PATTERN = re.compile(r"[a-z0-9]+")
NON_TOKEN_PATTERN = re.compile(r"[^a-z0-9]+")
CONTROL_PATTERN = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")

BM25_K1 = 1.2
BM25_B = 0.75

STOPWORDS = frozenset(
    {
        "a",
        "al",
        "algo",
        "ante",
        "como",
        "con",
        "cual",
        "cuales",
        "cuando",
        "de",
        "del",
        "donde",
        "el",
        "ella",
        "en",
        "entre",
        "es",
        "esa",
        "ese",
        "eso",
        "esta",
        "este",
        "esto",
        "fue",
        "ha",
        "han",
        "hay",
        "la",
        "las",
        "lo",
        "los",
        "mas",
        "me",
        "muy",
        "no",
        "o",
        "para",
        "pero",
        "por",
        "que",
        "se",
        "según",
        "ser",
        "si",
        "sin",
        "sobre",
        "son",
        "su",
        "sus",
        "tiene",
        "tienen",
        "un",
        "una",
        "uno",
        "y",
        "ya",
    }
)

AUTHORITY_BONUS = {"first_party": 0.5, "open_data": 0.2, "third_party": 0.0}
STATUS_BONUS = {"current": 0.3, "historical": 0.0, "disputed": -0.5, "ambiguous": -0.5}
FLAG_PENALTY = {
    "conflicting": 0.6,
    "ambiguous_value": 0.4,
    "topic_uncertain": 0.3,
    "english_content": 1.5,
    "short_unit": 0.2,
    "low_authority": 0.2,
}


class RetrievalError(ValueError):
    """Raised when the gold layer is missing or malformed."""


def normalize_text(text: str) -> str:
    """Return lowercase, accent-free text without punctuation or extra spaces."""
    if not text:
        return ""
    decomposed = unicodedata.normalize("NFKD", text)
    without_accents = "".join(char for char in decomposed if not unicodedata.combining(char))
    cleaned = NON_TOKEN_PATTERN.sub(" ", without_accents.lower())
    return " ".join(cleaned.split())


def tokenize(text: str, *, keep_stopwords: bool = False) -> tuple[str, ...]:
    """Tokenize text deterministically, dropping one-character tokens and stopwords."""
    tokens = TOKEN_PATTERN.findall(normalize_text(text))
    if keep_stopwords:
        return tuple(token for token in tokens if len(token) > 1)
    return tuple(token for token in tokens if len(token) > 1 and token not in STOPWORDS)


def normalize_question(question: str) -> str:
    """Normalize a question without dropping stopwords, for display and deduplication."""
    return normalize_text(question)


@dataclass(frozen=True, slots=True)
class GoldUnit:
    """Read-only view of one unit in ``knowledge_units.jsonl``."""

    unit_id: str
    topic_id: str
    topic_title: str
    text: str
    unit_type: str = "passage"
    language: str = "es"
    authority: str = "first_party"
    status: str = "current"
    quality_flags: tuple[str, ...] = ()
    entity_ids: tuple[str, ...] = ()
    coverage_item_ids: tuple[str, ...] = ()
    url: str = ""
    title: str = ""
    section_path: tuple[str, ...] = ()
    page_start: int | None = None
    page_end: int | None = None
    time_start: float | None = None
    time_end: float | None = None
    published_at: str | None = None
    retrieved_at: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> GoldUnit:
        return cls(
            unit_id=str(payload.get("unit_id", "")),
            topic_id=str(payload.get("topic_id", "")),
            topic_title=str(payload.get("topic_title", "")),
            text=str(payload.get("text", "")),
            unit_type=str(payload.get("unit_type", "passage")),
            language=str(payload.get("language", "es")),
            authority=str(payload.get("authority", "first_party")),
            status=str(payload.get("status", "current")),
            quality_flags=tuple(str(item) for item in payload.get("quality_flags") or ()),
            entity_ids=tuple(str(item) for item in payload.get("entity_ids") or ()),
            coverage_item_ids=tuple(str(item) for item in payload.get("coverage_item_ids") or ()),
            url=str(payload.get("url", "")),
            title=str(payload.get("title", "")),
            section_path=tuple(str(item) for item in payload.get("section_path") or ()),
            page_start=payload.get("page_start"),
            page_end=payload.get("page_end"),
            time_start=payload.get("time_start"),
            time_end=payload.get("time_end"),
            published_at=payload.get("published_at"),
            retrieved_at=str(payload.get("retrieved_at", "")),
        )

    @property
    def is_citable(self) -> bool:
        return bool(self.text.strip() and self.url and self.section_path)


@dataclass(frozen=True, slots=True)
class ContextBlock:
    unit_id: str
    text: str
    citation: str
    tokens: int
    topic_id: str
    authority: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ContextBlock:
        return cls(
            unit_id=str(payload.get("unit_id", "")),
            text=str(payload.get("text", "")),
            citation=str(payload.get("citation", "")),
            tokens=int(payload.get("tokens", 0)),
            topic_id=str(payload.get("topic_id", "")),
            authority=str(payload.get("authority", "")),
        )


@dataclass(frozen=True, slots=True)
class ContextPack:
    pack_id: str
    budget_tokens: int
    tokens: int
    blocks: tuple[ContextBlock, ...]
    unit_ids: tuple[str, ...]
    omitted_units: int

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> ContextPack:
        return cls(
            pack_id=str(payload.get("pack_id", "")),
            budget_tokens=int(payload.get("budget_tokens", 0)),
            tokens=int(payload.get("tokens", 0)),
            blocks=tuple(ContextBlock.from_dict(item) for item in payload.get("blocks") or ()),
            unit_ids=tuple(str(item) for item in payload.get("unit_ids") or ()),
            omitted_units=int(payload.get("omitted_units", 0)),
        )

    @property
    def is_empty(self) -> bool:
        return not self.blocks


@dataclass(frozen=True, slots=True)
class FAQSeed:
    seed_id: str
    question: str
    topic_id: str
    coverage_item_id: str | None
    evidence_unit_ids: tuple[str, ...]
    status: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> FAQSeed:
        coverage_item_id = payload.get("coverage_item_id")
        return cls(
            seed_id=str(payload.get("seed_id", "")),
            question=str(payload.get("question", "")),
            topic_id=str(payload.get("topic_id", "")),
            coverage_item_id=str(coverage_item_id) if coverage_item_id else None,
            evidence_unit_ids=tuple(
                str(item) for item in payload.get("evidence_unit_ids") or ()
            ),
            status=str(payload.get("status", "review")),
        )


@dataclass(frozen=True, slots=True)
class EntityIndex:
    """Maps canonical names and aliases to gold entity identifiers."""

    entries: tuple[tuple[tuple[str, ...], str], ...] = ()

    @classmethod
    def from_entities(cls, entities: Iterable[dict[str, Any]]) -> EntityIndex:
        entries: list[tuple[tuple[str, ...], str]] = []
        for entity in entities:
            entity_id = str(entity.get("entity_id", ""))
            if not entity_id:
                continue
            names = [str(entity.get("canonical_name", "")), *(entity.get("aliases") or ())]
            for name in names:
                tokens = tokenize(name, keep_stopwords=True)
                if tokens:
                    entries.append((tokens, entity_id))
        return cls(entries=tuple(entries))

    def match(self, tokens: Sequence[str]) -> frozenset[str]:
        token_set = set(tokens)
        matched: set[str] = set()
        for name_tokens, entity_id in self.entries:
            if set(name_tokens).issubset(token_set):
                matched.add(entity_id)
        return frozenset(matched)


@dataclass(frozen=True, slots=True)
class SelectedUnit:
    label: str
    unit: GoldUnit
    score: float
    reason: str


@dataclass(frozen=True, slots=True)
class EvidenceSelection:
    query: str
    topic_id: str
    entities: tuple[str, ...]
    selected: tuple[SelectedUnit, ...]
    omitted_unit_ids: tuple[str, ...]
    tokens: int
    budget_tokens: int

    @property
    def used_unit_ids(self) -> tuple[str, ...]:
        return tuple(item.unit.unit_id for item in self.selected)

    def label_map(self) -> dict[str, GoldUnit]:
        return {item.label: item.unit for item in self.selected}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise RetrievalError(f"No existe el archivo de oro: {path.name} en {path.parent.name}/.")
    records: list[dict[str, Any]] = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        stripped = line.strip()
        if not stripped:
            continue
        try:
            payload = json.loads(stripped)
        except json.JSONDecodeError as exc:
            raise RetrievalError(f"JSON inválido en {path.name}, línea {number}: {exc}") from exc
        if not isinstance(payload, dict):
            raise RetrievalError(f"Registro no válido en {path.name}, línea {number}.")
        records.append(payload)
    return records


def _read_json(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise RetrievalError(f"No existe el archivo de oro: {path.name} en {path.parent.name}/.")
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise RetrievalError(f"JSON inválido en {path.name}: {exc}") from exc
    if not isinstance(payload, dict):
        raise RetrievalError(f"El archivo {path.name} debe contener un objeto JSON.")
    return payload


def load_gold_units(gold_dir: str | Path) -> tuple[GoldUnit, ...]:
    """Load citable units; units without text, URL or section are dropped."""
    path = Path(gold_dir) / "knowledge_units.jsonl"
    units = tuple(GoldUnit.from_dict(item) for item in _read_jsonl(path))
    for unit in units:
        if unit.unit_id and not UNIT_ID_PATTERN.match(unit.unit_id):
            raise RetrievalError(f"unit_id inválido en {path.name}: {unit.unit_id}")
    return tuple(unit for unit in units if unit.is_citable)


def load_context_pack(gold_dir: str | Path, pack: str = "8000") -> ContextPack:
    """Load ``context_<pack>.json`` as a read-only context pack."""
    if pack not in {"8000", "32000"}:
        raise RetrievalError("El paquete de contexto debe ser '8000' o '32000'.")
    payload = _read_json(Path(gold_dir) / f"context_{pack}.json")
    return ContextPack.from_dict(payload)


def load_faq_seeds(gold_dir: str | Path) -> tuple[FAQSeed, ...]:
    path = Path(gold_dir) / "faq_seeds.jsonl"
    return tuple(FAQSeed.from_dict(item) for item in _read_jsonl(path))


def load_coverage(gold_dir: str | Path) -> dict[str, Any]:
    return _read_json(Path(gold_dir) / "coverage.json")


def load_entity_index(gold_dir: str | Path) -> EntityIndex:
    """Load ``entities.jsonl`` when present; an empty index is a valid fallback."""
    path = Path(gold_dir) / "entities.jsonl"
    if not path.is_file():
        return EntityIndex()
    return EntityIndex.from_entities(_read_jsonl(path))


def _bm25(
    query_tokens: Sequence[str],
    documents: Sequence[Counter[str]],
    document_frequencies: Counter[str],
    average_length: float,
) -> list[float]:
    total = len(documents)
    scores: list[float] = []
    for document in documents:
        length = sum(document.values())
        score = 0.0
        for token in query_tokens:
            frequency = document.get(token, 0)
            if not frequency:
                continue
            idf = math.log(1 + (total - document_frequencies[token] + 0.5) / (
                document_frequencies[token] + 0.5
            ))
            denominator = frequency + BM25_K1 * (1 - BM25_B + BM25_B * length / average_length)
            score += idf * (frequency * (BM25_K1 + 1)) / denominator
        scores.append(score)
    return scores


def _quality_adjustment(unit: GoldUnit) -> float:
    adjustment = AUTHORITY_BONUS.get(unit.authority, 0.0)
    adjustment += STATUS_BONUS.get(unit.status, 0.0)
    for flag in unit.quality_flags:
        adjustment -= FLAG_PENALTY.get(flag, 0.0)
    return adjustment


def _diversify(ranked: Sequence[SelectedUnit], top_k: int) -> list[SelectedUnit]:
    """Pick one unit per topic first, then a second per topic, and so on."""
    by_topic: dict[str, list[SelectedUnit]] = {}
    for item in ranked:
        by_topic.setdefault(item.unit.topic_id, []).append(item)
    topics = sorted(by_topic, key=lambda topic: (-by_topic[topic][0].score, topic))
    picked: list[SelectedUnit] = []
    index = 0
    while len(picked) < top_k:
        added = False
        for topic in topics:
            bucket = by_topic[topic]
            if index >= len(bucket):
                continue
            picked.append(bucket[index])
            added = True
            if len(picked) >= top_k:
                break
        if not added:
            break
        index += 1
    return picked


def select_evidence(
    question: str,
    units: Sequence[GoldUnit],
    *,
    entity_index: EntityIndex | None = None,
    top_k: int = 8,
    token_budget: int = 6000,
    min_score: float = 0.0,
) -> EvidenceSelection:
    """Select evidence deterministically for a question.

    Ranking = BM25 simplificado + tema + entidades + señales de calidad. La selección aplica
    diversidad por tema, un presupuesto de tokens y etiquetas ``U1..Un`` consecutivas.
    """
    if top_k < 1:
        raise RetrievalError("top_k debe ser >= 1.")
    if token_budget < 1:
        raise RetrievalError("token_budget debe ser >= 1.")

    query_tokens = tokenize(question)
    normalized_query = normalize_question(question)
    entity_index = entity_index or EntityIndex()
    query_entities = entity_index.match(tokenize(question, keep_stopwords=True))

    documents = [Counter(tokenize(f"{unit.topic_title} {unit.text}")) for unit in units]
    document_frequencies: Counter[str] = Counter()
    for document in documents:
        document_frequencies.update(set(document))
    average_length = (
        sum(sum(document.values()) for document in documents) / len(documents) if documents else 1.0
    )
    average_length = average_length or 1.0
    lexical_scores = _bm25(query_tokens, documents, document_frequencies, average_length)

    ranked: list[SelectedUnit] = []
    for unit, lexical in zip(units, lexical_scores, strict=True):
        entity_hit = bool(query_entities.intersection(unit.entity_ids))
        if lexical <= 0 and not entity_hit:
            continue
        topic_tokens = set(tokenize(f"{unit.topic_id} {unit.topic_title}"))
        topic_matches = topic_tokens.intersection(query_tokens)
        score = lexical + _quality_adjustment(unit)
        if entity_hit:
            score += 2.0
        if topic_matches:
            score += min(1.5 * len(topic_matches), 3.0)
        score = round(score, 6)
        if score <= 0 or score < min_score:
            continue
        reason_parts = []
        if lexical > 0:
            reason_parts.append("coincidencia léxica")
        if topic_matches:
            reason_parts.append("tema")
        if entity_hit:
            reason_parts.append("entidad")
        ranked.append(
            SelectedUnit(
                label="",
                unit=unit,
                score=score,
                reason=" + ".join(reason_parts) or "señal de calidad",
            )
        )

    ranked.sort(key=lambda item: (-item.score, item.unit.unit_id))
    picked = _diversify(ranked, top_k)

    selected: list[SelectedUnit] = []
    omitted: list[str] = []
    total_tokens = 0
    for item in picked:
        tokens = estimate_tokens(item.unit.text)
        if total_tokens + tokens > token_budget:
            omitted.append(item.unit.unit_id)
            continue
        total_tokens += tokens
        selected.append(
            SelectedUnit(
                label=f"U{len(selected) + 1}",
                unit=item.unit,
                score=item.score,
                reason=item.reason,
            )
        )
    picked_ids = {item.unit.unit_id for item in picked}
    omitted.extend(item.unit.unit_id for item in ranked if item.unit.unit_id not in picked_ids)

    inferred_topic = ""
    if selected:
        topic_scores: Counter[str] = Counter()
        for item in selected:
            topic_scores[item.unit.topic_id] += 1
        inferred_topic = sorted(topic_scores, key=lambda topic: (-topic_scores[topic], topic))[0]

    return EvidenceSelection(
        query=normalized_query,
        topic_id=inferred_topic,
        entities=tuple(sorted(query_entities)),
        selected=tuple(selected),
        omitted_unit_ids=tuple(dict.fromkeys(omitted)),
        tokens=total_tokens,
        budget_tokens=token_budget,
    )


def build_context(selected: Iterable[SelectedUnit]) -> str:
    """Render selected units as a delimited, non-executable context block."""
    lines = ["<context>"]
    for item in selected:
        text = CONTROL_PATTERN.sub(" ", item.unit.text).strip()
        lines.append(f'<unit id="{item.label}">{text}</unit>')
    lines.append("</context>")
    return "\n".join(lines)
