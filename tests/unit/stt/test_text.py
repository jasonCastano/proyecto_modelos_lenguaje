"""Texto del dictado: prompt de vocabulario, correcciones, recorte y ruido (spec 023, R4 y R6)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.stt.text import (
    MAX_MESSAGE_CHARS,
    MAX_PROMPT_CHARS,
    apply_corrections,
    clip_message,
    initial_prompt,
    is_hallucination,
)

CORRECTIONS = (
    ("valeria caña", "Valer-IA Caña"),
    ("valeria", "Valer-IA"),
    ("manuelita", "Manuelita"),
    ("oceanos", "Océanos"),
)


def test_initial_prompt_joins_terms_and_ends_with_a_period() -> None:
    assert initial_prompt(("Manuelita", "Valer-IA Caña")) == "Manuelita, Valer-IA Caña."
    assert initial_prompt(()) == ""
    assert len(initial_prompt(tuple(f"Término {i}" for i in range(50)))) <= MAX_PROMPT_CHARS


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        (
            "hola valeria caña, ¿qué produce manuelita?",
            "hola Valer-IA Caña, ¿qué produce Manuelita?",
        ),
        ("Hola Valeria Cana", "Hola Valer-IA Caña"),
        ("VALERIA, cuéntame", "Valer-IA, cuéntame"),
        ("¿qué hace oceanos?", "¿qué hace Océanos?"),
        ("¿qué hace Océanos?", "¿qué hace Océanos?"),
        ("las manuelitas del barrio", "las manuelitas del barrio"),
        ("Valer-IA Caña ya está bien", "Valer-IA Caña ya está bien"),
    ],
)
def test_corrections_replace_whole_words_ignoring_case_and_accents(raw: str, expected: str) -> None:
    assert apply_corrections(raw, CORRECTIONS) == expected


def test_clip_message_cuts_at_a_word_boundary() -> None:
    short = "¿Qué produce Manuelita?"
    assert clip_message(short) == (short, False)
    long = "palabra " * 400
    clipped, truncated = clip_message(long)
    assert truncated and len(clipped) <= MAX_MESSAGE_CHARS
    assert clipped.endswith("palabra")


@pytest.mark.parametrize(
    "text",
    [
        "Subtítulos realizados por la comunidad de Amara.org",
        "¡Gracias por ver!",
        "Gracias por ver el video.",
        "Suscríbete al canal.",
        "  ",
    ],
)
def test_known_hallucinations_are_discarded(text: str) -> None:
    assert is_hallucination(text)


@pytest.mark.parametrize("text", ["gracias", "¡Muchas gracias!", "¿Qué produce Manuelita?"])
def test_real_messages_are_kept(text: str) -> None:
    assert not is_hallucination(text)
