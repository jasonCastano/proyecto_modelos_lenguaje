"""Presentación al iniciar una conversación (spec 038, T007)."""

from __future__ import annotations

import re

import pytest

from proyecto_modelos_lenguaje.channels.greeting import (
    INTRODUCTIONS,
    already_introduced,
    identity_line,
    introduction,
    merge,
)

TERMINAL = re.compile(r"[.!?…](?=\s|$)")


def sentences(text: str) -> int:
    return len(TERMINAL.findall(text))


@pytest.mark.parametrize("language", ["es", "en"])
def test_three_distinct_short_variants_that_say_who_she_is(language: str) -> None:
    variants = INTRODUCTIONS[language]
    assert len(variants) == 3 and len(set(variants)) == 3
    for template in variants:
        text = template.format(name="")
        assert sentences(text) <= 2  # FR-013
        assert "Valer-IA" in text and "Manuelita" in text
        assert ("voz" in text) if language == "es" else ("voice" in text)
        assert ("fuentes" in text) if language == "es" else ("sources" in text)
        assert "/" not in text and not re.search(r"(^|\s)\d+\.", text)  # sin comandos ni menús


def test_the_variant_is_stable_per_thread_and_varies_across_threads() -> None:
    assert introduction("es", "hilo-1") == introduction("es", "hilo-1")
    seen = {introduction("es", f"hilo-{n}") for n in range(40)}
    assert len(seen) == 3


def test_language_of_the_turn() -> None:
    assert introduction("en", "hilo-1").startswith(("Hi", "Hello"))
    assert introduction("es", "hilo-1").startswith("¡Hola")


def test_the_name_goes_in_the_greeting_and_numbers_never_do() -> None:
    assert introduction("es", "hilo-1", "Ana").startswith("¡Hola, Ana")
    assert introduction("en", "hilo-1", "Ana").split("!")[0].endswith("Ana") or ", Ana" in (
        introduction("en", "hilo-1", "Ana")
    )
    assert "3001" not in introduction("es", "hilo-1", "+573001234567")
    assert sentences(introduction("es", "hilo-1", "Ana")) <= 2


def test_identity_line_is_one_sentence() -> None:
    assert sentences(identity_line("es")) == 1 and "Valer-IA" in identity_line("es")
    assert "Valer-IA" in identity_line("en")


@pytest.mark.parametrize(
    ("answer", "expected"),
    [
        ("¡Hola! Soy Valer-IA, la asistente de Manuelita. ¿En qué te ayudo?", True),
        ("Hola, soy Valeria y te cuento de Manuelita.", True),
        ("Manuelita produce azúcar, etanol y energía [1].", False),
        ("Manuelita produce azúcar. También uvas. Valer-IA te lo cuenta.", False),
    ],
)
def test_already_introduced(answer: str, expected: bool) -> None:
    assert already_introduced(answer) is expected


@pytest.mark.parametrize(
    ("answer", "body"),
    [
        ("¡Hola! ¿En qué te puedo ayudar?", "¿En qué te puedo ayudar?"),
        ("Hola, cuéntame qué quieres saber.", "Cuéntame qué quieres saber."),
        ("Hi! What would you like to know?", "What would you like to know?"),
        ("¡Hola, Ana! 👋 Te cuento.", "Te cuento."),
    ],
)
def test_merge_replaces_a_loose_greeting(answer: str, body: str) -> None:
    intro = introduction("es", "hilo-1")
    assert merge(intro, answer) == f"{intro} {body}"


def test_merge_keeps_a_hola_in_the_middle_and_handles_empty_answers() -> None:
    intro = introduction("es", "hilo-1")
    answer = "Manuelita dice hola a sus clientes en cada empaque."
    assert merge(intro, answer) == f"{intro} {answer}"
    assert merge(intro, "¡Hola!") == intro
    assert merge(intro, "") == intro


def test_spec036_introductions_keep_the_caleno_style_professional() -> None:
    from proyecto_modelos_lenguaje.agent.style import find_banned, find_expressions

    spanish = [template.format(name=", Ana") for template in INTRODUCTIONS["es"]]
    assert any(find_expressions(text) == ["ve"] for text in spanish)
    for text in [*spanish, *(t.format(name="") for t in INTRODUCTIONS["en"])]:
        assert not find_banned(text) and len(find_expressions(text)) <= 1
