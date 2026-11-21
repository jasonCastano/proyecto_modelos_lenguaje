"""Guiones de atención (``prompts/care.md``) y sus citas al oro (spec 019, T012, FR-019/FR-020)."""

from __future__ import annotations

import json
import re

import pytest

from proyecto_modelos_lenguaje.agent import care
from proyecto_modelos_lenguaje.agent.prompts import CARE_REQUIRED, load_care
from proyecto_modelos_lenguaje.agent.welcome import gold_units_path


def test_playbook_structure() -> None:
    playbook = load_care()
    assert playbook.version == "1.1"
    for key in CARE_REQUIRED:
        assert playbook.variants[key], key
    for spec in care.TOPICS:
        assert spec.bridge in playbook.variants, spec.key
        assert spec.bridge in playbook.citations, spec.key
    for key in ("channel.website", "channel.ethics_line", "channel.data_protection"):
        assert key in playbook.citations


def test_angles_cover_every_catalog_topic() -> None:
    """Spec 020 (T010): mapa de ángulos de los puentes, con palabras clave y ángulo válido."""
    from proyecto_modelos_lenguaje.agent.prompts import ANGLES, _parse_angle

    playbook = load_care()
    for spec in care.TOPICS:
        assert spec.key in playbook.angles, spec.key
    assert "default" in playbook.angles
    assert all(angle.angle in ANGLES and angle.keywords for angle in playbook.angles.values())
    with pytest.raises(ValueError, match="ángulo desconocido"):
        _parse_angle("angles.x", "keywords: a, b\nangle: deportes")


def test_crisis_has_help_lines_and_no_commercial_content() -> None:
    crisis = " ".join(load_care().variants["crisis"])
    assert "106" in crisis and "123" in crisis
    assert "Manuelita" not in crisis


def _gold_available() -> bool:
    path = gold_units_path()
    if not path.is_file():
        return False
    with path.open(encoding="utf-8") as handle:
        return not handle.readline().startswith("version https://git-lfs")


CONTACT = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|www\.[\w.-]+")


@pytest.mark.skipif(not _gold_available(), reason="corpus oro no descargado (Git LFS)")
def test_citations_exist_in_gold_and_back_every_contact() -> None:
    playbook = load_care()
    wanted = {citation.unit_id for citation in playbook.citations.values()}
    units: dict[str, dict[str, str]] = {}
    with gold_units_path().open(encoding="utf-8") as handle:
        for line in handle:
            unit = json.loads(line)
            if unit["unit_id"] in wanted:
                units[unit["unit_id"]] = unit
    for key, citation in playbook.citations.items():
        unit = units.get(citation.unit_id)
        assert unit is not None, f"{key}: {citation.unit_id} no está en el oro"
        assert unit["url"] == citation.url, key
        source = f"{unit['text']} {unit['url']}".lower()
        for variant in playbook.variants[key]:
            for contact in CONTACT.findall(variant):
                assert contact.lower().rstrip(".") in source, f"{key}: {contact}"
