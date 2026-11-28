"""Verificación del estilo caleño (spec 036, ``contracts/style-rules.md`` §5)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from proyecto_modelos_lenguaje.agent.plan import TurnPlan
from proyecto_modelos_lenguaje.agent.prompts import load_care, load_conduct
from proyecto_modelos_lenguaje.agent.review import (
    NOTES,
    RETRIEVAL_CHECKS,
    STYLE_CHECKS,
    drop_flagged_sentences,
    review,
    review_sentence,
    style_issues,
)
from proyecto_modelos_lenguaje.agent.style import find_banned, find_expressions

BASE = TurnPlan(
    act="smalltalk",
    tiers=(),
    sentiment="neutral",
    strategy=("acknowledge",),
    length="short",
    language="es",
    register="formal",
    turn=2,
)
NEUTRAL = replace(BASE, style="neutral", style_hints=("listo pues", "ve"))


def issues(text: str, plan: TurnPlan | None = NEUTRAL, recent: tuple[str, ...] = ()) -> set[str]:
    return {check for check, _span in style_issues(text, plan, recent)}


# ---------------------------------------------------------------- US1


@pytest.mark.parametrize("text", ["Listo, parce, te cuento.", "Mirá, te cuento."])
def test_banned_is_flagged(text: str) -> None:
    assert "style_banned" in issues(text)
    assert "style_banned" in issues(text, plan=None)  # también sin plan


def test_more_than_one_expression_is_excess() -> None:
    assert "style_excess" in issues("¡Ve, qué bueno! Listo pues, te cuento.")
    assert "style_excess" not in issues("Listo pues, te cuento de Manuelita.")


def test_repeating_the_last_expression_is_flagged() -> None:
    assert "style_repeat" in issues("Listo pues, te cuento.", recent=("listo pues",))
    assert "style_repeat" not in issues("A la orden, te cuento.", recent=("listo pues",))


def test_expression_with_style_off_is_flagged_but_courtesy_is_fine() -> None:
    off = replace(BASE, style="off")
    assert "style_off" in issues("Listo pues, te cuento.", plan=off)
    assert issues("Con mucho gusto te ayudo.", plan=off) == set()


def test_formal_level_only_allows_formal_expressions() -> None:
    formal = replace(BASE, style="formal")
    assert "style_off" in issues("¡Uy, qué nota! Te cuento.", plan=formal)
    assert issues("Con mucho gusto le cuento.", plan=formal) == set()


def test_a_clean_answer_with_citation_passes() -> None:
    text = "Con mucho gusto te cuento: Manuelita produce azúcar [U1]."
    assert issues(text) == set()
    assert review(text, NEUTRAL, labels={"U1"}, evidence="Manuelita produce azúcar").ok


def test_review_integrates_the_style_checks() -> None:
    verdict = review("¡Ve, qué bueno! Listo pues, te cuento de Manuelita.", NEUTRAL)
    assert "style_excess" in verdict.issues
    text = "Listo pues, te cuento de Manuelita."
    again = review(text, NEUTRAL, recent_expressions=["listo pues"])
    assert "style_repeat" in again.issues


def test_retrieval_drops_the_sentence_with_a_banned_word_and_keeps_citations() -> None:
    answer = "Listo, parce, ahí va. Manuelita produce azúcar [U1]."
    verdict = review(answer, NEUTRAL, evidence="Manuelita produce azúcar", checks=RETRIEVAL_CHECKS)
    assert "style_banned" in verdict.issues
    trimmed = drop_flagged_sentences(answer, verdict.spans)
    assert trimmed == "Manuelita produce azúcar [U1]."


def test_sentence_review_checks_banned_and_off_but_not_excess() -> None:
    assert "style_banned" in review_sentence("Mirá, te cuento.", NEUTRAL, is_first=True).issues
    off = replace(BASE, style="off")
    assert "style_off" in review_sentence("De una, te cuento.", off, is_first=True).issues
    two = review_sentence("¡Ve, qué bueno, listo pues!", NEUTRAL, is_first=True)
    assert "style_excess" not in two.issues


def test_every_style_check_has_a_note() -> None:
    assert set(STYLE_CHECKS) <= set(NOTES)


# ---------------------------------------------------------------- US3: textos fijos


def test_fixed_texts_and_fallbacks_have_no_caleno_style() -> None:
    texts = list(load_conduct().values())
    playbook = load_care()
    for key, variants in playbook.variants.items():
        texts += list(variants) if "fallback" in key else []
    texts += list(playbook.variants["crisis"])
    for text in texts:
        assert not find_banned(text), text
        courtesy = {"con mucho gusto", "a la orden"}
        non_courtesy = [e for e in find_expressions(text) if e not in courtesy]
        assert not non_courtesy, text
