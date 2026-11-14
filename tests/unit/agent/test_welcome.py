"""Bienvenida y personaje de Valer-IA Caña (spec 018, US1)."""

from __future__ import annotations

import json
import re

import pytest

from proyecto_modelos_lenguaje.agent.prompts import CONDUCT_SECTIONS, load_conduct, load_sections
from proyecto_modelos_lenguaje.agent.welcome import gold_units_path, load_welcome, parse_citations


def test_welcome_text_and_citations() -> None:
    welcome = load_welcome()
    text = welcome["text"]
    assert welcome["assistant"] == "Valer-IA Caña"
    assert welcome["version"] == "1.0"
    assert len(text) < 700
    for phrase in ("Valer-IA Caña", "asistente virtual de Manuelita", "inteligencia artificial"):
        assert phrase in text
    assert "no reemplazo sus canales oficiales" in text
    labels = set(re.findall(r"\[(U\d+)\]", text))
    assert labels == {citation["label"] for citation in welcome["citations"]}
    assert all(
        citation["url"].startswith("https://www.manuelita.com") for citation in welcome["citations"]
    )


def _gold_available() -> bool:
    path = gold_units_path()
    if not path.is_file():
        return False
    with path.open(encoding="utf-8") as handle:
        return not handle.readline().startswith("version https://git-lfs")


@pytest.mark.skipif(not _gold_available(), reason="corpus oro no descargado (Git LFS)")
def test_cited_units_contain_the_attributed_facts() -> None:
    _version, sections = load_sections("welcome")
    declared = parse_citations(sections["citations"])
    wanted = {row["unit_id"] for row in declared}
    units = {}
    with gold_units_path().open(encoding="utf-8") as handle:
        for line in handle:
            unit = json.loads(line)
            if unit["unit_id"] in wanted:
                units[unit["unit_id"]] = unit
    for row in declared:
        unit = units[row["unit_id"]]
        assert unit["url"] == row["url"], row["unit_id"]
        for fact in row["facts"]:
            assert fact in unit["text"], (row["unit_id"], fact)


def test_conduct_sections_are_complete_and_in_persona() -> None:
    conduct = load_conduct()
    assert set(CONDUCT_SECTIONS) <= set(conduct)
    for key in CONDUCT_SECTIONS:
        text = conduct[key]
        assert text
        for jargon in ("RAG", "LangGraph", "agente", "enrutador"):
            assert jargon not in text, (key, jargon)
    assert "Valer-IA Caña" in conduct["greeting"]
    assert "inteligencia artificial" in conduct["ai_disclosure"]
    assert "{name}" in conduct["identity_recognized"]
