"""Fusión de recuperación semántica y léxica con trazabilidad auditable."""

from __future__ import annotations

import time
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np

from ..retrieval import (
    EntityIndex,
    EvidenceSelection,
    GoldUnit,
    SelectedUnit,
    normalize_question,
    select_evidence,
    tokenize,
)
from ..silver.cleaning import estimate_tokens
from .config import RetrievalConfig, load_retrieval_config
from .embeddings import Embedder
from .index import LoadedIndex
from .vectorstore import QdrantVectorStore

VALID_ORIGINS = ("semantic", "lexical", "both")
VALID_STATUSES = ("used", "omitted_threshold", "omitted_budget", "omitted_duplicate")
VALID_MODES = ("semantic", "lexical", "hybrid", "none")


@dataclass(frozen=True, slots=True)
class RetrievedFragment:
    """Candidato recuperado con su puntuación, origen y estado."""

    unit_id: str
    title: str
    url: str
    score: float
    semantic_score: float | None
    lexical_score: float | None
    origin: str
    status: str = "used"
    reason: str | None = None
    anomalous: bool = False
    anomaly_reasons: tuple[str, ...] = ()
    neutralized_sentences: int = 0  # spec 015: oraciones sustituidas antes de llegar al modelo

    def __post_init__(self) -> None:
        if self.origin not in VALID_ORIGINS:
            raise ValueError(f"origin inválido: {self.origin}")
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status inválido: {self.status}")
        if not 0.0 <= self.score <= 1.0:
            raise ValueError("score debe estar en [0, 1]")
        if self.status != "used" and not self.reason:
            raise ValueError("reason es obligatorio cuando status != used")
        if self.anomalous != bool(self.anomaly_reasons):
            raise ValueError("anomaly_reasons debe tener motivos si y solo si anomalous es True")
        if self.neutralized_sentences < 0:
            raise ValueError("neutralized_sentences no puede ser negativo")
        if self.neutralized_sentences and not self.anomalous:
            raise ValueError("solo un fragmento anómalo puede tener oraciones neutralizadas")

    def to_dict(self) -> dict[str, object]:
        return {
            "unit_id": self.unit_id,
            "title": self.title,
            "url": self.url,
            "score": round(self.score, 6),
            "semantic_score": None
            if self.semantic_score is None
            else round(self.semantic_score, 6),
            "lexical_score": None if self.lexical_score is None else round(self.lexical_score, 6),
            "origin": self.origin,
            "status": self.status,
            "reason": self.reason,
            "anomalous": self.anomalous,
            "anomaly_reasons": list(self.anomaly_reasons),
            "neutralized_sentences": self.neutralized_sentences,
        }


@dataclass(frozen=True, slots=True)
class RetrievalTrace:
    """Resumen auditable de una consulta."""

    mode: str
    semantic_available: bool
    candidates: int
    threshold: float
    fragments: tuple[RetrievedFragment, ...]
    notes: tuple[str, ...]
    elapsed_ms: float

    def __post_init__(self) -> None:
        if self.mode not in VALID_MODES:
            raise ValueError(f"mode inválido: {self.mode}")
        scores = [fragment.score for fragment in self.fragments]
        if scores != sorted(scores, reverse=True):
            raise ValueError("fragments debe estar ordenado por score descendente")

    @property
    def used_unit_ids(self) -> tuple[str, ...]:
        return tuple(fragment.unit_id for fragment in self.fragments if fragment.status == "used")

    @property
    def omitted_unit_ids(self) -> tuple[str, ...]:
        return tuple(fragment.unit_id for fragment in self.fragments if fragment.status != "used")

    def to_dict(self) -> dict[str, object]:
        return {
            "mode": self.mode,
            "semantic_available": self.semantic_available,
            "candidates": self.candidates,
            "threshold": self.threshold,
            "fragments": [fragment.to_dict() for fragment in self.fragments],
            "used_unit_ids": list(self.used_unit_ids),
            "notes": list(self.notes),
            "elapsed_ms": round(self.elapsed_ms, 3),
        }


def _clamp(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


class SemanticRetriever:
    """Búsqueda vectorial: Qdrant si hay colección; si no, coseno sobre la matriz normalizada."""

    def __init__(
        self,
        index: LoadedIndex | None,
        embedder: Embedder,
        config: RetrievalConfig,
        *,
        notes: Sequence[str] = (),
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self.index = index
        self.embedder = embedder
        self.config = config
        self.notes = tuple(notes)
        self.vector_store = vector_store

    @property
    def available(self) -> bool:
        return self.index is not None

    @property
    def filters_in_store(self) -> bool:
        """Qdrant aplica el filtro por *payload* durante la búsqueda (una sola etapa)."""
        return self.vector_store is not None

    def _ranked(
        self, query: np.ndarray, limit: int, metadata_filter: MetadataFilter | None
    ) -> list[tuple[int, float]]:
        if self.vector_store is not None:
            active = metadata_filter if metadata_filter and metadata_filter.active else None
            hits = self.vector_store.search(
                query,
                limit=limit,
                topics=sorted(active.topics) if active else (),
                authorities=sorted(active.authorities) if active else (),
                unit_types=sorted(active.unit_types) if active else (),
            )
            return [(hit.position, hit.score) for hit in hits]
        assert self.index is not None
        scores = self.index.vectors @ query
        order = np.argsort(-scores, kind="stable")[:limit]
        return [(int(position), float(scores[int(position)])) for position in order]

    def search(
        self,
        question: str,
        *,
        top_k: int | None = None,
        metadata_filter: MetadataFilter | None = None,
    ) -> list[RetrievedFragment]:
        if self.index is None or not question.strip():
            return []
        query = np.asarray(self.embedder.embed_query(question), dtype=np.float32)
        if query.ndim != 1 or query.shape[0] != self.index.manifest.dimension:
            return []
        limit = top_k or self.config.hybrid.semantic_top_k
        fragments: list[RetrievedFragment] = []
        seen: set[str] = set()
        for position, raw_score in self._ranked(query, limit, metadata_filter):
            if not 0 <= position < len(self.index.fragments):
                continue
            fragment = self.index.fragments[position]
            if fragment.unit_id in seen:
                continue
            seen.add(fragment.unit_id)
            score = _clamp(raw_score)
            fragments.append(
                RetrievedFragment(
                    unit_id=fragment.unit_id,
                    title=fragment.title,
                    url=fragment.url,
                    score=score,
                    semantic_score=score,
                    lexical_score=None,
                    origin="semantic",
                )
            )
        return fragments


@dataclass(frozen=True, slots=True)
class MetadataFilter:
    """Filtro por metadatos de la unidad de oro (spec 014, FR-005).

    ``topics`` corresponde a la sección temática (``topic_id``), ``authorities`` al tipo de fuente
    (``first_party`` / ``third_party``) y ``unit_types`` a ``passage`` / ``fact``. Un campo vacío
    no filtra.
    """

    topics: frozenset[str] = frozenset()
    authorities: frozenset[str] = frozenset()
    unit_types: frozenset[str] = frozenset()

    @classmethod
    def of(
        cls,
        *,
        topics: Sequence[str] = (),
        authorities: Sequence[str] = (),
        unit_types: Sequence[str] = (),
    ) -> MetadataFilter:
        return cls(frozenset(topics), frozenset(authorities), frozenset(unit_types))

    @property
    def active(self) -> bool:
        return bool(self.topics or self.authorities or self.unit_types)

    def accepts(self, unit: GoldUnit) -> bool:
        return (
            (not self.topics or unit.topic_id in self.topics)
            and (not self.authorities or unit.authority in self.authorities)
            and (not self.unit_types or unit.unit_type in self.unit_types)
        )

    def describe(self) -> str:
        parts = [
            f"{name}={','.join(sorted(values))}"
            for name, values in (
                ("tema", self.topics),
                ("fuente", self.authorities),
                ("tipo", self.unit_types),
            )
            if values
        ]
        return "; ".join(parts)


class HybridRetriever:
    """Combina semántica y léxica, aplica umbral, presupuesto y deduplicación."""

    def __init__(
        self,
        units: Sequence[GoldUnit],
        *,
        index: LoadedIndex | None = None,
        embedder: Embedder | None = None,
        entity_index: EntityIndex | None = None,
        config: RetrievalConfig | None = None,
        notes: Sequence[str] = (),
        vector_store: QdrantVectorStore | None = None,
    ) -> None:
        self.units = tuple(units)
        self.units_by_id = {unit.unit_id: unit for unit in self.units}
        self.config = config or load_retrieval_config()
        self.entity_index = entity_index or EntityIndex()
        self.semantic = (
            SemanticRetriever(index, embedder, self.config, notes=notes, vector_store=vector_store)
            if embedder
            else None
        )
        self.notes = tuple(notes)

    @property
    def semantic_available(self) -> bool:
        return bool(self.semantic and self.semantic.available)

    def vector_search_status(self) -> str:
        """Qué búsqueda vectorial está en juego, para la UI y los logs (nunca en silencio)."""
        semantic = self.semantic
        if semantic is not None and semantic.vector_store is not None:
            return f"Búsqueda vectorial en {semantic.vector_store.describe()}"
        if semantic is not None and semantic.index is not None:
            reason = next((n for n in self.notes if n.startswith("Respaldo numpy")), "")
            return reason or "Respaldo numpy: Qdrant desactivado en la configuración."
        return "Sin índice semántico: recuperación léxica."

    def retrieve(
        self,
        question: str,
        *,
        top_k: int = 8,
        token_budget: int = 6000,
        min_score: float = 0.0,
        metadata_filter: MetadataFilter | None = None,
    ) -> RetrievalTrace:
        started = time.perf_counter()
        active_filter = metadata_filter if metadata_filter and metadata_filter.active else None
        semantic_top_k = None
        in_store = self.semantic is not None and self.semantic.filters_in_store
        if active_filter is not None and self.semantic is not None and not in_store:
            # Sin Qdrant se sobremuestrea porque el filtro se aplica después de la búsqueda.
            semantic_top_k = self.config.hybrid.semantic_top_k * 5
        if self.semantic is None:
            semantic_fragments: list[RetrievedFragment] = []
        elif in_store and active_filter is not None:
            semantic_fragments = self.semantic.search(
                question, top_k=semantic_top_k, metadata_filter=active_filter
            )
        else:
            semantic_fragments = self.semantic.search(question, top_k=semantic_top_k)
        if active_filter is not None and not in_store:
            semantic_fragments = [
                fragment
                for fragment in semantic_fragments
                if (unit := self.units_by_id.get(fragment.unit_id)) is not None
                and active_filter.accepts(unit)
            ][: self.config.hybrid.semantic_top_k]
        lexical_units = (
            self.units
            if active_filter is None
            else tuple(unit for unit in self.units if active_filter.accepts(unit))
        )
        lexical_selection = select_evidence(
            question,
            lexical_units,
            entity_index=self.entity_index,
            top_k=min(self.config.hybrid.lexical_top_k, max(top_k, 1)),
            token_budget=10**9,
            min_score=min_score,
        )

        max_lexical = max((item.score for item in lexical_selection.selected), default=0.0)
        merged: dict[str, dict[str, object]] = {}
        for fragment in semantic_fragments:
            merged[fragment.unit_id] = {
                "semantic": fragment.semantic_score,
                "lexical": None,
            }
        for item in lexical_selection.selected:
            entry = merged.setdefault(item.unit.unit_id, {"semantic": None, "lexical": None})
            entry["lexical"] = _clamp(item.score / max_lexical) if max_lexical > 0 else 0.0

        threshold = self.config.hybrid.min_similarity
        candidates: list[RetrievedFragment] = []
        for unit_id, entry in merged.items():
            unit = self.units_by_id.get(unit_id)
            if unit is None:
                continue
            semantic = entry["semantic"]
            lexical = entry["lexical"]
            semantic_score = float(semantic) if semantic is not None else None
            lexical_score = float(lexical) if lexical is not None else None
            origin = (
                "both"
                if semantic_score is not None and lexical_score is not None
                else ("semantic" if semantic_score is not None else "lexical")
            )
            combined = 0.0
            if semantic_score is not None:
                combined += self.config.hybrid.weight_semantic * semantic_score
            if lexical_score is not None:
                combined += self.config.hybrid.weight_lexical * lexical_score
            if origin == "both":
                combined += self.config.hybrid.both_bonus
            candidates.append(
                RetrievedFragment(
                    unit_id=unit_id,
                    title=unit.title or unit.topic_title,
                    url=unit.url,
                    score=_clamp(combined),
                    semantic_score=semantic_score,
                    lexical_score=lexical_score,
                    origin=origin,
                )
            )
        candidates.sort(key=lambda fragment: (-fragment.score, fragment.unit_id))

        has_semantic = any(
            fragment.semantic_score is not None and fragment.semantic_score >= threshold
            for fragment in candidates
        )
        has_lexical = any(fragment.lexical_score is not None for fragment in candidates)
        if has_semantic and has_lexical:
            mode = "hybrid"
        elif has_semantic:
            mode = "semantic"
        elif has_lexical:
            mode = "lexical"
        else:
            mode = "none"

        resolved: list[RetrievedFragment] = []
        accepted_vectors: list[np.ndarray] = []
        total_tokens = 0
        for fragment in candidates:
            if (
                fragment.origin == "semantic"
                and fragment.semantic_score is not None
                and fragment.semantic_score < threshold
            ):
                resolved.append(
                    self._mark(
                        fragment,
                        "omitted_threshold",
                        f"Similitud por debajo de {threshold:.2f} y sin coincidencia léxica",
                    )
                )
                continue
            if self.semantic is not None and self.semantic.index is not None:
                vector = self.semantic.index.vector_for_unit(fragment.unit_id)
                if vector is not None and any(
                    float(np.dot(vector, other)) > self.config.hybrid.dedup_similarity
                    for other in accepted_vectors
                ):
                    resolved.append(
                        self._mark(
                            fragment,
                            "omitted_duplicate",
                            "Fragmento casi idéntico a otro ya seleccionado",
                        )
                    )
                    continue
                if vector is not None:
                    accepted_vectors.append(vector)
            unit = self.units_by_id[fragment.unit_id]
            tokens = estimate_tokens(unit.text)
            if total_tokens + tokens > token_budget:
                resolved.append(
                    self._mark(fragment, "omitted_budget", "Presupuesto de contexto agotado")
                )
                continue
            total_tokens += tokens
            resolved.append(fragment)

        elapsed_ms = (time.perf_counter() - started) * 1000
        notes = list(self.notes)
        if active_filter is not None:
            notes.append(f"Filtro por metadatos: {active_filter.describe()}")
        if self.semantic is None:
            notes.append("Recuperación semántica no configurada; se usó recuperación léxica")
        elif not self.semantic.available:
            notes.append("Índice no disponible; se usó recuperación léxica")
        return RetrievalTrace(
            mode=mode,
            semantic_available=self.semantic_available,
            candidates=len(resolved),
            threshold=threshold,
            fragments=tuple(resolved),
            notes=tuple(dict.fromkeys(notes)),
            elapsed_ms=elapsed_ms,
        )

    @staticmethod
    def _mark(fragment: RetrievedFragment, status: str, reason: str) -> RetrievedFragment:
        return RetrievedFragment(
            unit_id=fragment.unit_id,
            title=fragment.title,
            url=fragment.url,
            score=fragment.score,
            semantic_score=fragment.semantic_score,
            lexical_score=fragment.lexical_score,
            origin=fragment.origin,
            status=status,
            reason=reason,
        )

    def select(
        self,
        question: str,
        *,
        top_k: int = 8,
        token_budget: int = 6000,
        min_score: float = 0.0,
    ) -> tuple[EvidenceSelection, RetrievalTrace]:
        """Return the evidence selection consumed by the tasks plus its trace."""
        trace = self.retrieve(question, top_k=top_k, token_budget=token_budget, min_score=min_score)
        selected: list[SelectedUnit] = []
        for fragment in trace.fragments:
            if fragment.status != "used":
                continue
            unit = self.units_by_id[fragment.unit_id]
            selected.append(
                SelectedUnit(
                    label=f"U{len(selected) + 1}",
                    unit=unit,
                    score=fragment.score,
                    reason=f"recuperación {fragment.origin}",
                )
            )
        topic_scores: Counter[str] = Counter(item.unit.topic_id for item in selected)
        inferred_topic = (
            sorted(topic_scores, key=lambda topic: (-topic_scores[topic], topic))[0]
            if selected
            else ""
        )
        entities = self.entity_index.match(tokenize(question, keep_stopwords=True))
        selection = EvidenceSelection(
            query=normalize_question(question),
            topic_id=inferred_topic,
            entities=tuple(sorted(entities)),
            selected=tuple(selected),
            omitted_unit_ids=trace.omitted_unit_ids,
            tokens=sum(estimate_tokens(item.unit.text) for item in selected),
            budget_tokens=token_budget,
        )
        return selection, trace
