"""Léxico, nivel y sugerencias del estilo caleño (spec 036, ``contracts/style-rules.md`` §1)."""

from __future__ import annotations

from dataclasses import dataclass

import pytest

from proyecto_modelos_lenguaje.agent import style
from proyecto_modelos_lenguaje.agent.style import (
    find_banned,
    find_expressions,
    glossary,
    level_for,
    load_lexicon,
    named_expressions,
    parse_lexicon,
    render_block,
    suggest,
    wants_plain,
)


@dataclass
class Plan:
    language: str = "es"
    sentiment: str = "neutral"
    act: str = "smalltalk"
    reason: str | None = None
    register: str = "formal"


# ---------------------------------------------------------------- léxico


def test_lexicon_loads_and_is_valid() -> None:
    lexicon = load_lexicon()
    assert lexicon.enabled and len(lexicon.approved) >= 8
    assert sum("formal" in e.levels for e in lexicon.approved) >= 3
    assert lexicon.max_written == 1 and lexicon.max_spoken == 2
    banned = {normalized for normalized, _reason, _kind in lexicon.banned}
    assert {"parce", "vos", "mirá"} <= banned
    assert len(lexicon.sha256) == 64


@pytest.mark.parametrize(
    "raw",
    [
        b"[style]\nenabled = true\n",  # sin aprobadas
        b'[[approved]]\ntext = "ve"\nlevels = ["callejero"]\n' * 8,  # nivel desconocido
        b"esto no es toml = = =",
    ],
)
def test_invalid_lexicon_turns_style_off_without_raising(raw: bytes) -> None:
    assert parse_lexicon(raw).enabled is False


def test_duplicated_text_turns_style_off() -> None:
    rows = (
        "".join(f'[[approved]]\ntext = "e{i}"\nlevels = ["formal"]\n' for i in range(8))
        + '[[banned]]\ntext = "e1"\n'
    )
    assert parse_lexicon(rows.encode()).enabled is False


# ---------------------------------------------------------------- coincidencias


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("LISTO PUES, aquí está.", ["listo pues"]),
        ("A la orden para lo que necesites.", ["a la orden"]),
        ("¡Ve, qué buena pregunta!", ["ve"]),
        ("Qué bueno, ve, te cuento.", ["qué bueno, ve"]),
        ("Ve a la página oficial www.manuelita.com.", []),
        ("Ahí te cuento, pues.", ["pues"]),
        ("Pues sí, te cuento.", []),
        ("Qué chévere, y de ñapa te cuento algo.", ["chévere", "de ñapa"]),
    ],
)
def test_find_expressions(text: str, expected: list[str]) -> None:
    assert find_expressions(text) == expected


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Listo, parce, te cuento", ["parce"]),
        ("Mirá, te cuento", ["mirá"]),
        ("¿Vos sabés qué hace Manuelita?", ["vos", "sabés"]),
        ("Mira, te cuento", []),  # tuteo válido
        ("¿Sabes qué hace Manuelita?", []),
    ],
)
def test_find_banned(text: str, expected: list[str]) -> None:
    assert find_banned(text) == expected


@pytest.mark.parametrize(
    "message", ["Habla normal, por favor", "háblame normal", "sin modismos", "speak normally"]
)
def test_wants_plain(message: str) -> None:
    assert wants_plain(message)


def test_regular_messages_do_not_ask_for_plain_speech() -> None:
    assert not wants_plain("¿Qué produce Manuelita?")


def test_named_expressions_finds_the_asked_word() -> None:
    assert "ve" in named_expressions('¿qué significa "ve"?')


# ---------------------------------------------------------------- sugerencias y bloque


def test_suggest_respects_level_recent_and_spoken() -> None:
    lexicon = load_lexicon()
    by_key = lexicon.by_key()
    formal = suggest("formal", seed=0)
    assert formal and all("formal" in by_key[style.normalize(t)].levels for t in formal)
    recent = ["listo pues", "ve"]
    picked = suggest("neutral", recent, seed=3)
    assert picked and not {"listo pues", "ve"} & set(picked)
    spoken = suggest("informal", seed=7, spoken=True)
    assert "de ñapa" not in spoken
    assert all(by_key[style.normalize(t)].suggested for t in suggest("informal", seed=2))
    assert suggest("off") == ()


def test_suggest_rotates_with_the_seed() -> None:
    assert suggest("neutral", seed=0) != suggest("neutral", seed=1)


def test_render_block() -> None:
    assert render_block("off", ("ve",)) == ""
    written = render_block("neutral", ("listo pues",))
    assert written.startswith("<estilo>") and "como máximo una" in written
    assert "tuteo, nunca voseo" in written
    spoken = render_block("informal", ("ve",), spoken=True)
    assert "como máximo dos" in spoken and "ritmo" in spoken
    assert "cortesías suaves" in render_block("formal", ("a la orden",))
    plain = render_block("neutral", ("ve",), plain_request=True)
    assert "sin modismos" in plain and "«ve»" not in plain


def test_glossary_explains_the_expression() -> None:
    lines = glossary(["ve"])
    assert lines and lines[0].startswith("«ve» = ")
    block = render_block("neutral", (), glossary_lines=lines)
    assert "glosario: «ve» = " in block


# ---------------------------------------------------------------- nivel (US3, data-model §2)


@pytest.mark.parametrize(
    ("plan", "memory", "message"),
    [
        (Plan(language="en"), {}, "hi there"),
        (Plan(sentiment="frustrated"), {}, "esto no sirve"),
        (Plan(sentiment="angry"), {}, "qué rabia"),
        (Plan(sentiment="distressed"), {}, "me siento muy mal"),
        (Plan(act="complaint"), {}, "llevo una hora buscando"),
        (Plan(reason="crisis"), {}, "ya no quiero vivir"),
        (Plan(), {"style_opt_out": True}, "¿qué produce Manuelita?"),
        (Plan(), {}, "habla normal, por favor"),
    ],
)
def test_level_is_off(plan: Plan, memory: dict, message: str) -> None:
    assert level_for(plan, memory, message) == "off"


def test_level_formal_informal_and_neutral() -> None:
    assert level_for(Plan(), {}, "Buenos días, quisiera información") == "formal"
    assert level_for(Plan(register="informal"), {}, "qué más, ve") == "informal"
    assert level_for(Plan(), {}, "¿Qué produce Manuelita?") == "neutral"
    assert level_for(None, {}, "hola") == "off"
