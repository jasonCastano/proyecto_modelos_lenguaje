"""Deterministic relevance scoring for the Manuelita corpus."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .config import RelevanceConfig, RelevanceSettings
from .coverage import normalize_text
from .extractors.links import host_of


@dataclass(frozen=True, slots=True)
class EvidenceHit:
    term: str
    location: str
    snippet: str
    weight: int


@dataclass(frozen=True, slots=True)
class RelevanceResult:
    decision: str
    level: str
    score: int
    explanation: str
    evidence: tuple[EvidenceHit, ...]


def _is_official(url: str, config: RelevanceConfig) -> bool:
    host = host_of(url)
    return any(host == domain or host.endswith(f".{domain}") for domain in config.protected_domains)


def _snippet(text: str, term: str, *, radius: int = 90) -> str:
    lowered = text.lower()
    needle = term.lower()
    index = lowered.find(needle)
    if index < 0:
        return term
    start = max(0, index - radius)
    end = min(len(text), index + len(needle) + radius)
    return re.sub(r"\s+", " ", text[start:end]).strip()[:500]


def _term_hits(text: str, terms: tuple[str, ...]) -> list[str]:
    hits: list[str] = []
    for term in terms:
        normalized = normalize_text(term)
        if not normalized:
            continue
        if re.search(rf"(?<!\w){re.escape(normalized)}(?!\w)", text):
            hits.append(term)
    return hits


def _occurrences(text: str, term: str) -> list[int]:
    return [match.start() for match in re.finditer(re.escape(term), text)]


def _all_incidental(text: str, positions: list[int], patterns: tuple[str, ...]) -> bool:
    if not positions:
        return False
    spans: list[tuple[int, int]] = []
    for pattern in patterns:
        for match in re.finditer(re.escape(normalize_text(pattern)), text):
            spans.append((match.start(), match.end()))
    if not spans:
        return False
    return all(any(start <= position < end for start, end in spans) for position in positions)


class RelevanceEvaluator:
    """Rule-based evaluator; no randomness, network or model calls."""

    def __init__(self, config: RelevanceConfig) -> None:
        self.config = config
        self.settings: RelevanceSettings = config.settings

    def evaluate(
        self,
        *,
        source_id: str,
        url: str,
        title: str | None,
        text: str,
        raw_text: str | None = None,
        text_available: bool = True,
    ) -> RelevanceResult:
        if _is_official(url, self.config):
            domain = host_of(url)
            return RelevanceResult(
                decision="keep",
                level="direct",
                score=100,
                explanation=f"Dominio oficial protegido ({domain}).",
                evidence=(EvidenceHit(domain, "url", url, 100),),
            )

        if not text_available:
            return RelevanceResult(
                decision="review",
                level="none",
                score=50,
                explanation="Contenido no textual o sin texto verificable; requiere revisión.",
                evidence=(EvidenceHit("sin_texto", "metadata", url, 0),),
            )

        normalized = normalize_text(text)
        title_normalized = normalize_text(title or "")
        evidence: list[EvidenceHit] = []
        score = 0

        strong_hits = _term_hits(normalized, self.config.strong_aliases)
        if strong_hits:
            score += 60
            for term in strong_hits[:3]:
                evidence.append(EvidenceHit(term, "body", _snippet(text, term), 60))

        company_positions = _occurrences(normalized, "manuelita")
        if company_positions:
            score += 20
            if not strong_hits:
                evidence.append(EvidenceHit("manuelita", "body", _snippet(text, "manuelita"), 20))
            score += min(20, max(0, len(company_positions) - 1) * 2)

        title_hits = _term_hits(title_normalized, ("manuelita", *self.config.strong_aliases))
        if title_hits:
            score += self.settings.title_weight
            evidence.append(
                EvidenceHit(title_hits[0], "title", (title or "")[:500], self.settings.title_weight)
            )

        context_hits = _term_hits(normalized, self.config.context_terms)
        if context_hits:
            context_score = min(30, 10 * len(context_hits))
            score += context_score
            for term in context_hits[:3]:
                evidence.append(
                    EvidenceHit(term, "body", _snippet(text, term), min(10, context_score))
                )

        source_weight = self.config.source_weights.get(source_id, 0)
        if source_weight:
            score += source_weight
            evidence.append(
                EvidenceHit(f"source:{source_id}", "metadata", source_id, source_weight)
            )

        negative_hits = _term_hits(normalized, self.config.negative_patterns)
        if negative_hits:
            penalty = min(60, 30 * len(negative_hits))
            score -= penalty
            for term in negative_hits[:2]:
                evidence.append(EvidenceHit(term, "body", _snippet(text, term), -30))

        incidental = bool(company_positions) and _all_incidental(
            normalized, company_positions, self.config.incidental_patterns
        )
        if incidental:
            score = max(
                self.settings.review_threshold, min(score, self.settings.review_threshold + 15)
            )
            evidence.append(
                EvidenceHit(
                    "mencion_incidental",
                    "metadata",
                    "La palabra aparece solo en correos o dominios, sin contexto de la empresa.",
                    -20,
                )
            )

        if not company_positions and not strong_hits:
            if raw_text and "manuelita" in normalize_text(raw_text):
                return RelevanceResult(
                    decision="review",
                    level="none",
                    score=max(self.settings.review_threshold, 30),
                    explanation=(
                        "Mención encontrada solo en contenido embebido no visible; "
                        "requiere revisión."
                    ),
                    evidence=(
                        EvidenceHit(
                            "manuelita",
                            "metadata",
                            _snippet(raw_text, "manuelita"),
                            self.settings.review_threshold,
                        ),
                    ),
                )
            return RelevanceResult(
                decision="remove",
                level="none",
                score=0,
                explanation="Sin mención ni relación verificable con Ingenio Manuelita.",
                evidence=(),
            )

        if (
            company_positions
            and not negative_hits
            and not strong_hits
            and score < self.settings.review_threshold
        ):
            score = self.settings.review_threshold

        score = max(0, min(100, score))
        level = "direct" if (strong_hits or title_hits) else "contextual"
        if not company_positions and not strong_hits:
            level = "none"

        if score >= self.settings.keep_threshold:
            decision = "keep"
            explanation = "Mención o relación verificable con Ingenio Manuelita."
        elif score >= self.settings.review_threshold:
            decision = "review"
            explanation = (
                "Posible relación con Manuelita; la evidencia es ambigua y requiere revisión."
            )
        else:
            decision = "remove"
            explanation = "La mención no se relaciona con Ingenio Manuelita o es un homónimo."

        return RelevanceResult(
            decision=decision,
            level=level,
            score=score,
            explanation=explanation,
            evidence=tuple(evidence),
        )
