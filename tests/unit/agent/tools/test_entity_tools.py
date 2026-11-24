"""Herramientas de entidades: list_business_units y list_company_entities (T030, spec 024)."""

from __future__ import annotations

import json

import pytest

from proyecto_modelos_lenguaje.agent.catalog import ToolArgsError, ToolContext, get_spec, run_read
from proyecto_modelos_lenguaje.agent.structured import normalize
from proyecto_modelos_lenguaje.agent.tools_entities import BUSINESS_LOCATIONS, load_entities
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.rag.hybrid import HybridRetriever
from proyecto_modelos_lenguaje.retrieval import GoldUnit
from tests.unit.agent.tools.gold import requires_gold

pytestmark = requires_gold
GOLD_UNITS = PROJECT_ROOT / "data" / "gold" / "knowledge_units.jsonl"
URL = "https://www.manuelita.com/informe.pdf"


@pytest.fixture(scope="module")
def retriever() -> HybridRetriever:
    """Unidades sintéticas con los unit_id que citan las herramientas (sin cargar el oro)."""
    units: dict[str, GoldUnit] = {}
    for name, location in BUSINESS_LOCATIONS.items():
        units[location.unit_id] = GoldUnit(
            unit_id=location.unit_id,
            topic_id="sedes",
            topic_title="Sedes",
            text=f"{name} en {location.place}, {location.country}.",
            url=URL,
            title="Informe de sostenibilidad",
        )
    for entity in load_entities():
        first = entity["unit_ids"][0]
        previous = units[first].text if first in units else ""
        units[first] = GoldUnit(
            unit_id=first,
            topic_id="certificaciones",
            topic_title="Certificaciones",
            text=f"{previous} Manuelita cuenta con {entity['canonical_name']}.".strip(),
            url=URL,
            title="Informe",
        )
    return HybridRetriever(list(units.values()))


def _run(name: str, args: dict, retriever) -> tuple[str, ToolContext]:
    ctx = ToolContext(retriever=retriever)
    return run_read(get_spec(name), ctx, args), ctx


def test_list_business_units_lists_subsidiaries_with_country_and_citation(retriever) -> None:
    # Arrange
    expected = {
        e["canonical_name"]
        for e in load_entities()
        if e["entity_type"] in ("subsidiary", "company")
    }

    # Act
    output, ctx = _run("list_business_units", {}, retriever)

    # Assert
    assert {fact.subject_label for fact in ctx.trace.facts} == expected
    assert all(fact.unit_id and fact.citations for fact in ctx.trace.facts)
    assert '<documento id="F1"' in output
    assert "Perú" in output and "Chile" in output


def test_list_business_units_filters_by_country_without_accents(retriever) -> None:
    # Act
    output, ctx = _run("list_business_units", {"country": "peru"}, retriever)

    # Assert
    assert [fact.subject_label for fact in ctx.trace.facts] == ["Agroindustrial Laredo"]
    assert "Caña de azúcar" in output  # plataforma según las series anuales


def test_list_business_units_unknown_country_is_sin_resultados(retriever) -> None:
    # Act
    output, ctx = _run("list_business_units", {"country": "Japón"}, retriever)

    # Assert
    assert output.startswith("Sin resultados")
    assert ctx.trace.facts == []


@pytest.mark.parametrize(("kind", "minimum"), [("certification", 4), ("brand", 3)])
def test_list_company_entities_by_kind_with_evidence(retriever, kind: str, minimum: int) -> None:
    # Arrange
    expected = sorted(e["canonical_name"] for e in load_entities() if e["entity_type"] == kind)

    # Act
    output, ctx = _run("list_company_entities", {"kind": kind}, retriever)

    # Assert
    assert len(expected) >= minimum
    assert [fact.subject_label for fact in ctx.trace.facts] == expected
    assert all(fact.citations and fact.unit_id for fact in ctx.trace.facts)
    assert all(name in output for name in expected)


@pytest.mark.parametrize("args", [{"kind": "subsidiary"}, {}, {"kind": "brand", "extra": 1}])
def test_list_company_entities_rejects_invalid_kind(retriever, args: dict) -> None:
    # Act / Assert
    with pytest.raises(ToolArgsError, match="list_company_entities"):
        _run("list_company_entities", args, retriever)


def test_curated_locations_are_stated_in_the_cited_gold_units() -> None:
    # Arrange
    wanted = {location.unit_id for location in BUSINESS_LOCATIONS.values()}
    texts: dict[str, str] = {}
    with GOLD_UNITS.open(encoding="utf-8") as handle:
        for line in handle:
            unit_id = line[line.find('"unit_id": "') + 12 :][:21]
            if unit_id in wanted:
                texts[unit_id] = normalize(json.loads(line)["text"])

    # Act / Assert
    for name, location in BUSINESS_LOCATIONS.items():
        text = texts[location.unit_id]
        assert normalize(location.country) in text, name
        assert normalize(name).split()[-1] in text, name
