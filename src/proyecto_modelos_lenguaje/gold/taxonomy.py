"""Controlled taxonomy and entity vocabulary for the gold layer."""

from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import ConfigError, load_coverage_items
from .models import Entity, Topic, make_entity_id
from .text import normalize_for_match


@dataclass(frozen=True, slots=True)
class EntitySpec:
    key: str
    entity_id: str
    canonical_name: str
    entity_type: str
    aliases: tuple[str, ...]
    coverage_item_ids: tuple[str, ...]

    @property
    def all_names(self) -> tuple[str, ...]:
        return (self.canonical_name, *self.aliases)


@dataclass(frozen=True, slots=True)
class TopicMatch:
    topic: Topic
    score: int
    uncertain: bool


class Taxonomy:
    def __init__(
        self,
        *,
        topics: dict[str, Topic],
        keywords: dict[str, tuple[str, ...]],
        entities: tuple[EntitySpec, ...],
        coverage_items: dict[str, Any],
        min_score: int,
    ) -> None:
        self.topics = topics
        self.keywords = keywords
        self.entities = entities
        self.coverage_items = coverage_items
        self.min_score = min_score
        self._alias_index = {
            normalize_for_match(alias): spec for spec in entities for alias in spec.all_names
        }
        self._ordered_topics = sorted(topics.values(), key=lambda item: item.order)

    @property
    def ordered_topics(self) -> list[Topic]:
        return list(self._ordered_topics)

    def classify(self, text: str) -> TopicMatch:
        haystack = normalize_for_match(text)
        best: Topic | None = None
        best_score = 0
        for topic in self._ordered_topics:
            score = sum(
                haystack.count(normalize_for_match(keyword))
                for keyword in self.keywords.get(topic.topic_id, ())
                if keyword
            )
            if score > best_score:
                best, best_score = topic, score
        if best is None or best_score < self.min_score:
            general = self.topics["general"]
            return TopicMatch(topic=general, score=best_score, uncertain=True)
        return TopicMatch(topic=best, score=best_score, uncertain=False)

    def assign_items(self, topic: Topic, text: str) -> list[str]:
        """Assign the most specific coverage items of a topic to a unit."""
        haystack = normalize_for_match(text)
        scores: list[tuple[int, str]] = []
        for item_id in topic.coverage_item_ids:
            item = self.coverage_items.get(item_id)
            if item is None:
                continue
            score = sum(
                haystack.count(normalize_for_match(keyword)) for keyword in item.keywords if keyword
            )
            if score:
                scores.append((score, item_id))
        if not scores:
            return []
        best = max(score for score, _ in scores)
        return sorted(item_id for score, item_id in scores if score == best)

    def find_entities(self, text: str) -> list[EntitySpec]:
        haystack = normalize_for_match(text)
        found: dict[str, EntitySpec] = {}
        for alias, spec in self._alias_index.items():
            if not alias:
                continue
            start = 0
            while True:
                index = haystack.find(alias, start)
                if index < 0:
                    break
                before = haystack[index - 1] if index > 0 else " "
                after_index = index + len(alias)
                after = haystack[after_index] if after_index < len(haystack) else " "
                if not before.isalnum() and not after.isalnum():
                    found[spec.entity_id] = spec
                    break
                start = index + 1
        return sorted(found.values(), key=lambda item: item.canonical_name)

    def entity_payloads(
        self, unit_ids: dict[str, list[str]], descriptions: dict[str, str]
    ) -> list[Entity]:
        payloads: list[Entity] = []
        for spec in self.entities:
            ids = unit_ids.get(spec.entity_id, [])
            if not ids:
                continue
            payloads.append(
                Entity(
                    schema_version="1.0",
                    entity_id=spec.entity_id,
                    canonical_name=spec.canonical_name,
                    aliases=list(spec.aliases),
                    entity_type=spec.entity_type,
                    description=descriptions.get(spec.entity_id),
                    unit_ids=sorted(set(ids)),
                    coverage_item_ids=list(spec.coverage_item_ids),
                )
            )
        return sorted(payloads, key=lambda item: item.canonical_name)


def load_taxonomy(
    path: str | Path,
    *,
    coverage_path: str | Path = "config/coverage-items.toml",
    min_score: int = 2,
) -> Taxonomy:
    taxonomy_path = Path(path)
    if not taxonomy_path.is_file():
        raise ConfigError(f"taxonomy file not found: {taxonomy_path}")
    try:
        with taxonomy_path.open("rb") as handle:
            table = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {taxonomy_path}: {exc}") from exc
    coverage_items = {item.item_id: item for item in load_coverage_items(coverage_path)}
    topics: dict[str, Topic] = {}
    keywords: dict[str, tuple[str, ...]] = {}
    for index, raw in enumerate(table.get("topics", [])):
        topic_id = str(raw.get("id", "")).strip()
        if not topic_id or topic_id in topics:
            raise ConfigError(f"topics[{index}] has an empty or duplicate id")
        item_ids = tuple(str(item) for item in raw.get("coverage_item_ids", []))
        for item_id in item_ids:
            if item_id not in coverage_items:
                raise ConfigError(f"topics[{index}] references unknown coverage item {item_id}")
        topics[topic_id] = Topic(
            topic_id=topic_id,
            title=str(raw.get("title", topic_id)),
            description=str(raw.get("description", "")),
            coverage_item_ids=list(item_ids),
            order=index,
        )
        keywords[topic_id] = tuple(str(item) for item in raw.get("keywords", []))
    if "general" not in topics:
        raise ConfigError("taxonomy must define a 'general' topic")
    entities: list[EntitySpec] = []
    for index, raw in enumerate(table.get("entities", [])):
        canonical = str(raw.get("canonical_name", "")).strip()
        if not canonical:
            raise ConfigError(f"entities[{index}] has no canonical_name")
        entities.append(
            EntitySpec(
                key=str(raw.get("id", canonical)),
                entity_id=make_entity_id(canonical),
                canonical_name=canonical,
                entity_type=str(raw.get("entity_type", "other")),
                aliases=tuple(str(item) for item in raw.get("aliases", [])),
                coverage_item_ids=tuple(str(item) for item in raw.get("coverage_item_ids", [])),
            )
        )
    return Taxonomy(
        topics=topics,
        keywords=keywords,
        entities=tuple(entities),
        coverage_items=coverage_items,
        min_score=min_score,
    )
