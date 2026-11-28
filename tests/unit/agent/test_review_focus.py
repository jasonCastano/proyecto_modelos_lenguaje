"""Verificaciones de enfoque en Manuelita (spec 035, ``contracts/focus-rules.md`` §4)."""

from __future__ import annotations

from dataclasses import replace

import pytest

from proyecto_modelos_lenguaje.agent.plan import TurnPlan
from proyecto_modelos_lenguaje.agent.review import (
    FOCUS_CHECKS,
    NOTES,
    correction_note,
    focus_issues,
    review,
    review_sentence,
)

BASE = TurnPlan(
    act="smalltalk",
    tiers=(),
    strategy=("acknowledge",),
    sentiment="neutral",
    language="es",
    register="informal",
    length="short",
    turn=3,
)
REDIRECT = replace(BASE, redirect=True, streak=1)


def issues(text: str, recent: tuple[str, ...] = ()) -> set[str]:
    return {check for check, _span in focus_issues(text, REDIRECT, recent)}


# ---------------------------------------------------------------- US1: invitación a charlar


@pytest.mark.parametrize(
    "text",
    [
        "Muy bien, gracias. ¿Seguimos con algo de Manuelita o prefieres solo charlar un rato?",
        "Claro que sí, charlar también se vale. Lo mío es Manuelita.",
        "¡Qué bien! Cuéntame qué has hecho hoy, y si quieres te hablo de Manuelita.",
        "Con gusto. ¿Qué tema te gustaría conversar? También sé de Manuelita.",
    ],
)
def test_chat_invite_is_flagged(text: str) -> None:
    assert "chat_invite" in issues(text)


def test_an_offer_about_manuelita_is_not_a_chat_invite() -> None:
    assert not issues("¡Qué bueno leerte! ¿Te cuento sobre la Fundación Manuelita?")


def test_no_redirect_is_flagged() -> None:
    assert "no_redirect" in issues("¡Qué bueno que hayas tenido plan hoy!")
    assert "no_redirect" not in issues("¡Qué buen plan! Si quieres, te cuento de Manuelita.")
    assert "no_redirect" not in issues("Por cierto, apoya programas deportivos [U1].")


def test_focus_checks_do_not_apply_without_redirect() -> None:
    text = "Claro que sí, charlar también se vale. ¿Cómo te fue en el partido?"
    assert focus_issues(text, BASE, ()) == []
    assert review(text, BASE).ok
    assert not review(text, REDIRECT).ok


# ---------------------------------------------------------------- US2: propuesta de charla


@pytest.mark.parametrize(
    "text",
    ["Claro que sí, charlemos de lo que quieras.", "Claro, cuéntame de qué quieres hablar."],
)
def test_accepting_free_chat_is_flagged(text: str) -> None:
    assert "chat_invite" in issues(text)


def test_purpose_and_topics_pass() -> None:
    text = (
        "Me encanta conversar contigo; lo mío es Manuelita: ¿te cuento de su historia o de su "
        "fundación?"
    )
    assert not issues(text)


# ---------------------------------------------------------------- US3: preguntas y rechazo


@pytest.mark.parametrize(
    "text",
    [
        "Qué bien. ¿Cómo te fue en el partido? Lo mío es Manuelita.",
        "Qué mal. ¿Y qué sigue para tu equipo? Lo mío es Manuelita.",
        "Nice! How was the game? I focus on Manuelita.",
    ],
)
def test_offtopic_questions_are_flagged(text: str) -> None:
    assert "offtopic_question" in issues(text)


def test_question_about_manuelita_passes() -> None:
    assert not issues("¡Qué plan! ¿Quieres que te cuente qué hace la Fundación Manuelita?")


@pytest.mark.parametrize(
    "text",
    ["Mejor no me cuentes cuál es; lo mío es Manuelita.", "No me interesa, pero Manuelita sí."],
)
def test_rejection_is_flagged(text: str) -> None:
    assert "rejection" in issues(text)


def test_thanking_is_not_a_rejection() -> None:
    assert "rejection" not in issues("Gracias por contármelo. Si quieres, te cuento de Manuelita.")


# ---------------------------------------------------------------- US4: cierre repetido


def test_closing_repeat_is_flagged() -> None:
    closing = "Lo mío es la información pública de Manuelita, por si algo de eso te sirve."
    before = f"Qué duro que la temporada termine así. {closing}"
    assert "closing_repeat" in issues(f"Te agradezco la confianza. {closing}", (before,))
    other = "Qué bien. Si quieres, te cuento de los países donde opera Manuelita."
    assert "closing_repeat" not in issues(other, (before,))


# ---------------------------------------------------------------- integración


def test_notes_and_correction_cover_every_focus_check() -> None:
    assert set(FOCUS_CHECKS) <= set(NOTES)
    verdict = review("Claro, charlemos de lo que quieras. ¿Cómo te fue hoy?", REDIRECT)
    note = correction_note(verdict, REDIRECT)
    assert "Manuelita" in note and "charlar" in note


def test_sentence_review_applies_local_focus_checks() -> None:
    flagged = review_sentence("¿Cómo te fue en el partido?", REDIRECT, is_first=False)
    assert "offtopic_question" in flagged.issues
    # El regreso y el cierre se miden sobre la respuesta completa, no por frase.
    calm = review_sentence("¡Qué buen plan para el día!", REDIRECT, is_first=True)
    assert calm.ok
    assert review_sentence("¿Cómo te fue en el partido?", BASE, is_first=False).ok
