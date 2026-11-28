"""Idioma del turno en el agente (spec 029, US2, T013): nunca se mezclan idiomas."""

from __future__ import annotations

import json

import pytest

from proyecto_modelos_lenguaje.agent.graph import localized, turn_language
from proyecto_modelos_lenguaje.agent.plan import detect_language
from proyecto_modelos_lenguaje.agent.prompts import load_conduct
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from tests.agent_helpers import make_service

FIXTURE = PROJECT_ROOT / "tests" / "fixtures" / "channels" / "language_format.jsonl"
CASES = [json.loads(line) for line in FIXTURE.read_text(encoding="utf-8").splitlines() if line]


@pytest.mark.parametrize("case", CASES, ids=[case["id"] for case in CASES])
def test_the_language_of_every_fixture_question(case: dict) -> None:
    assert detect_language(case["text"]) == case["lang"]


def test_the_channel_language_wins_over_detection() -> None:
    assert turn_language({"turn_language": "en", "question": "¿Qué produce Manuelita?"}) == "en"
    assert turn_language({"question": "What does Manuelita produce for export?"}) == "en"
    assert turn_language({"question": "ok"}) == "es"


def test_fixed_texts_have_an_english_variant_or_are_skipped() -> None:
    conduct = load_conduct()
    assert localized("sensitive_notice", "en") == conduct["sensitive_notice_en"]
    assert localized("remember_offer", "en") == conduct["remember_offer_en"]
    assert localized("greeting", "en") is None  # sin variante: se omite, no se mezcla
    assert localized("greeting", "es") == conduct["greeting"]


SPANISH_ONLY = ("Por tu seguridad", "Ojo:", "Te respondo en español", "Si quieres que te reconozca")


@pytest.mark.parametrize("variant", ["chain", "agent"])
def test_an_english_turn_has_no_spanish_fixed_text(variant: str) -> None:
    outcome = make_service().send(
        "My card is 4111 1111 1111 1111, what does Manuelita produce?",
        user_id="anon-l1",
        variant=variant,
        language="en",
    )
    answer = outcome.turn.answer
    assert answer.endswith(load_conduct()["sensitive_notice_en"])
    assert not any(marker in answer for marker in SPANISH_ONLY)
