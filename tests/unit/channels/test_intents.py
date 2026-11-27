"""Intenciones naturales del canal (spec 028, T015, research R6)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.channels.intents import (
    decision_of,
    detect_intent,
    language_of,
    looks_like_new_question,
    remainder,
)


@pytest.mark.parametrize(
    "text",
    [
        "empecemos de nuevo",
        "Empecemos de cero, por favor",
        "quiero una nueva conversación",
        "borrón y cuenta nueva",
        "reiniciemos la conversación",
        "volvamos a empezar",
        "let's start over",
        "new conversation please",
    ],
)
def test_restart(text: str) -> None:
    assert detect_intent(text) == "restart"


@pytest.mark.parametrize(
    "text",
    [
        "respóndeme por escrito",
        "mejor por escrito",
        "sin audios por favor",
        "no me mandes notas de voz",
        "contéstame en texto",
        "text me instead",
        "reply in text",
    ],
)
def test_format_text(text: str) -> None:
    assert detect_intent(text) == "format_text"


@pytest.mark.parametrize(
    "text",
    [
        "mándame audio",
        "respóndeme con voz",
        "prefiero notas de voz",
        "envíame un audio",
        "send me a voice note",
        "reply with voice",
    ],
)
def test_format_voice(text: str) -> None:
    assert detect_intent(text) == "format_voice"


@pytest.mark.parametrize(
    "text",
    [
        "¿Qué produce Manuelita?",
        "¿Cómo empezó Manuelita?",  # «empezó» no es reiniciar
        "¿Puedo empezar a trabajar en Manuelita?",
        "la empresa produce azúcar",
        "",
    ],
)
def test_ordinary_messages_have_no_intent(text: str) -> None:
    assert detect_intent(text) == "none"


def test_remainder_keeps_the_question_that_comes_with_an_intent() -> None:
    text = "Empecemos de nuevo. ¿Qué certificaciones tiene Manuelita?"
    assert detect_intent(text) == "restart"
    assert remainder(text, "restart") == "¿Qué certificaciones tiene Manuelita?"
    assert remainder("respóndeme por escrito", "format_text") == ""


@pytest.mark.parametrize(
    "text",
    [
        "sí",
        "Sí, guárdalo",
        "dale",
        "hágale",
        "de una",
        "claro",
        "ok",
        "adelante",
        "go ahead",
        "yes please",
        "sure",
        "claro que sí",
        "confirmo",
    ],
)
def test_approve(text: str) -> None:
    assert decision_of(text) == "approve"


@pytest.mark.parametrize(
    "text",
    [
        "no",
        "mejor no",
        "déjalo así",
        "olvídalo",
        "cancela",
        "no gracias",
        "no thanks",
        "claro que no",
        "nope",
    ],
)
def test_reject(text: str) -> None:
    assert decision_of(text) == "reject"


@pytest.mark.parametrize(
    "text", ["mmm", "no sé", "sí pero no", "tal vez", "maybe", "hmm", "¿?", "eh"]
)
def test_ambiguous(text: str) -> None:
    assert decision_of(text) == "ambiguous"


def test_long_messages_are_not_decisions() -> None:
    question = "¿cuáles son los canales oficiales de Manuelita para trabajar con ellos?"
    assert decision_of(question) is None
    assert looks_like_new_question(question)
    assert not looks_like_new_question("mmm")


@pytest.mark.parametrize(
    ("text", "hint", "expected"),
    [
        ("What does Manuelita produce?", None, "en"),
        ("hi, what can you do?", None, "en"),
        ("let's start over", None, "en"),
        ("hola", None, "es"),
        ("¿Qué produce Manuelita?", None, "es"),
        ("¿Qué produce Manuelita?", "en", "en"),
    ],
)
def test_language_of(text: str, hint: str | None, expected: str) -> None:
    assert language_of(text, hint) == expected
