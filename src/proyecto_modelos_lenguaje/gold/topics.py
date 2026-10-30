"""Topic pages and glossary rendering."""

from __future__ import annotations

from pathlib import Path

import yaml

from .models import Entity, KnowledgeUnit, Topic
from .store import write_text
from .taxonomy import Taxonomy


def build_topics(units: list[KnowledgeUnit], taxonomy: Taxonomy) -> list[Topic]:
    topics: list[Topic] = []
    for topic in taxonomy.ordered_topics:
        topic_units = [unit for unit in units if unit.topic_id == topic.topic_id]
        topic.unit_count = len(topic_units)
        if not topic_units:
            topic.status = "empty"
        elif len(topic_units) >= 3:
            topic.status = "covered"
        else:
            topic.status = "partial"
        topics.append(topic)
    return topics


def citation(unit: KnowledgeUnit) -> str:
    section = " > ".join(unit.section_path)
    location = f"sección: {section}"
    if unit.page_start is not None:
        location += f", p. {unit.page_start}"
    if unit.time_start is not None:
        location += f", {int(unit.time_start)} s"
    return f"{unit.title} — {unit.url} ({location})"


def render_topic_page(topic: Topic, units: list[KnowledgeUnit]) -> str:
    frontmatter = {
        "topic_id": topic.topic_id,
        "title": topic.title,
        "description": topic.description,
        "coverage_item_ids": list(topic.coverage_item_ids),
        "unit_count": len(units),
    }
    header = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    lines = [f"---\n{header}\n---", "", f"# {topic.title}", "", topic.description, ""]
    if not units:
        lines.append("_Sin unidades verificables en esta ejecución._")
    for unit in sorted(units, key=lambda item: (item.unit_id,)):
        lines.extend(
            [
                f"## {unit.text[:80]}",
                "",
                unit.text,
                "",
                f"> {citation(unit)}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"


def write_topic_pages(topics: list[Topic], units: list[KnowledgeUnit], directory: Path) -> int:
    by_topic: dict[str, list[KnowledgeUnit]] = {}
    for unit in units:
        by_topic.setdefault(unit.topic_id, []).append(unit)
    count = 0
    for topic in topics:
        topic_units = by_topic.get(topic.topic_id, [])
        if not topic_units:
            continue
        write_text(directory / f"{topic.topic_id}.md", render_topic_page(topic, topic_units))
        count += 1
    return count


def render_glossary(entities: list[Entity]) -> str:
    lines = [
        "---",
        "title: Glosario de entidades",
        "---",
        "",
        "# Glosario de entidades",
        "",
    ]
    for entity in sorted(entities, key=lambda item: item.canonical_name):
        aliases = ", ".join(entity.aliases) if entity.aliases else "—"
        lines.extend(
            [
                f"## {entity.canonical_name}",
                "",
                f"- **Tipo**: {entity.entity_type}",
                f"- **Alias**: {aliases}",
                f"- **Descripción**: {entity.description or 'Sin descripción extractiva.'}",
                f"- **Unidades**: {len(entity.unit_ids)}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"
