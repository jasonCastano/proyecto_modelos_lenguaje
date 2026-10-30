"""Conservative deterministic fact extraction."""

from __future__ import annotations

import re

from .models import Fact, KnowledgeUnit, make_fact_id
from .taxonomy import Taxonomy
from .text import fold_accents
from .units import attach_fact

_NUMBER = r"\d[\d.,]*"
_UNITS = (
    "toneladas",
    "tonelada",
    "hectareas",
    "hectarea",
    "empleos",
    "empleo",
    "litros",
    "litro",
    "kilogramos",
    "kilogramo",
    "millones",
    "millon",
    "pesos",
    "dolares",
    "por ciento",
    "%",
)
_UNIT_PATTERN = "|".join(re.escape(item) for item in sorted(_UNITS, key=len, reverse=True))
_NUMBER_UNIT = re.compile(rf"(?P<num>{_NUMBER})\s*(?P<unit>{_UNIT_PATTERN})\b", re.IGNORECASE)
_YEAR = re.compile(r"(?:\b(?:en|desde|fundad[ao]\s+en|año)\s+)(?P<year>18\d{2}|19\d{2}|20\d{2})\b")
_STOPWORDS = {
    "de",
    "del",
    "la",
    "el",
    "los",
    "las",
    "un",
    "una",
    "unos",
    "unas",
    "en",
    "con",
    "y",
    "o",
    "que",
    "al",
    "por",
    "para",
    "su",
    "sus",
    "se",
    "es",
    "son",
    "fue",
    "han",
    "ha",
    "como",
    "mas",
    "más",
}


def normalize_value(value: str) -> str:
    text = value.strip().replace(" ", "")
    if "," in text and "." in text:
        if text.rfind(",") > text.rfind("."):
            text = text.replace(".", "").replace(",", ".")
        else:
            text = text.replace(",", "")
    elif "," in text:
        text = text.replace(",", ".")
    elif text.count(".") > 1 or (text.count(".") == 1 and len(text.split(".")[-1]) == 3):
        text = text.replace(".", "")
    return text


def _attribute(text: str, start: int) -> str:
    words = re.findall(r"[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]+", text[:start])
    tail = []
    for word in reversed(words[-6:]):
        if fold_accents(word.lower()) in _STOPWORDS:
            if tail:
                break
            continue
        tail.append(word)
    attribute = " ".join(reversed(tail)).strip()
    return fold_accents(attribute.lower())


def extract_facts(unit: KnowledgeUnit, taxonomy: Taxonomy) -> list[Fact]:
    specs = taxonomy.find_entities(unit.text)
    if not specs:
        return []
    subject = specs[0]
    facts: list[Fact] = []
    seen: set[tuple[str, str]] = set()

    def add(attribute: str, value: str, unit_label: str | None, year: int | None) -> None:
        if not attribute or not value:
            return
        normalized = normalize_value(value)
        key = (attribute, normalized)
        if key in seen:
            return
        seen.add(key)
        fact_id = make_fact_id(subject.entity_id, attribute, normalized, unit.unit_id)
        facts.append(
            Fact(
                schema_version="1.0",
                fact_id=fact_id,
                subject_id=subject.entity_id,
                subject_label=subject.canonical_name,
                attribute=attribute,
                value=value,
                value_normalized=normalized,
                unit=unit_label,
                year=year,
                unit_id=unit.unit_id,
                evidence=list(unit.evidence),
                status="current",
            )
        )

    for match in _NUMBER_UNIT.finditer(unit.text):
        attribute = _attribute(unit.text, match.start())
        if len(attribute) < 3:
            continue
        value = match.group("num")
        unit_label = fold_accents(match.group("unit").lower())
        add(attribute, value, unit_label, None)

    for match in _YEAR.finditer(unit.text):
        attribute = _attribute(unit.text, match.start())
        if len(attribute) < 3:
            attribute = "año"
        add(attribute, match.group("year"), None, int(match.group("year")))

    if facts:
        attach_fact(unit, facts[0].fact_id)
    return facts
