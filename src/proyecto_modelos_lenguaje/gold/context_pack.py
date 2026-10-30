"""Token-bounded context packs."""

from __future__ import annotations

from ..silver.cleaning import estimate_tokens
from .config import ContextConfig
from .models import ContextBlock, ContextPack, CoverageEntry, KnowledgeUnit
from .topics import citation

_AUTHORITY_SCORE = {"first_party": 3, "open_data": 1, "third_party": 0}


def _score(unit: KnowledgeUnit, coverage: dict[str, CoverageEntry]) -> float:
    score = _AUTHORITY_SCORE.get(unit.authority, 0)
    for item_id in unit.coverage_item_ids:
        entry = coverage.get(item_id)
        if entry is not None:
            score += 2 if entry.status == "covered" else 1 if entry.status == "partial" else 0
    if unit.status == "current":
        score += 1
    elif unit.status in {"disputed", "ambiguous"}:
        score -= 1
    if unit.published_at and unit.published_at[:4].isdigit() and int(unit.published_at[:4]) >= 2020:
        score += 1
    return score


def _order(units: list[KnowledgeUnit], coverage: dict[str, CoverageEntry]) -> list[KnowledgeUnit]:
    ranked = sorted(
        units,
        key=lambda unit: (-_score(unit, coverage), unit.unit_id),
    )
    by_topic: dict[str, KnowledgeUnit] = {}
    for unit in ranked:
        by_topic.setdefault(unit.topic_id, unit)
    first = sorted(by_topic.values(), key=lambda unit: (-_score(unit, coverage), unit.unit_id))
    seen = {unit.unit_id for unit in first}
    rest = [unit for unit in ranked if unit.unit_id not in seen]
    return [*first, *rest]


def build_context_packs(
    units: list[KnowledgeUnit],
    coverage_entries: list[CoverageEntry],
    config: ContextConfig,
) -> list[ContextPack]:
    coverage = {entry.item_id: entry for entry in coverage_entries}
    ordered = _order(units, coverage)
    packs: list[ContextPack] = []
    for budget in config.budgets:
        selected: list[KnowledgeUnit] = []
        blocks: list[ContextBlock] = []
        total = 0
        for unit in ordered:
            tokens = estimate_tokens(unit.text, config.chars_per_token)
            if total + tokens > budget:
                continue
            total += tokens
            selected.append(unit)
            blocks.append(
                ContextBlock(
                    unit_id=unit.unit_id,
                    text=unit.text,
                    citation=citation(unit),
                    tokens=tokens,
                    topic_id=unit.topic_id,
                    authority=unit.authority,
                )
            )
        coverage_ids = sorted({item_id for unit in selected for item_id in unit.coverage_item_ids})
        packs.append(
            ContextPack(
                schema_version="1.0",
                pack_id=f"pack_summary_{budget}",
                task="summary",
                budget_tokens=budget,
                tokens=total,
                unit_ids=[unit.unit_id for unit in selected],
                blocks=blocks,
                coverage_item_ids=coverage_ids,
                omitted_units=len(units) - len(selected),
            )
        )
    return packs


def render_context_markdown(pack: ContextPack) -> str:
    lines = [
        f"# Paquete de contexto — {pack.pack_id}",
        "",
        f"- Presupuesto: {pack.budget_tokens} tokens",
        f"- Tokens usados: {pack.tokens}",
        f"- Unidades incluidas: {len(pack.unit_ids)}",
        f"- Unidades omitidas: {pack.omitted_units}",
        f"- Ítems cubiertos: {', '.join(pack.coverage_item_ids) or '—'}",
        "",
    ]
    for block in pack.blocks:
        lines.extend(
            [
                f"## {block.topic_id}",
                "",
                block.text,
                "",
                f"> {block.citation}",
                "",
            ]
        )
    return "\n".join(lines).strip() + "\n"
