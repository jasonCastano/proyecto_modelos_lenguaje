"""Limpieza y segmentación del texto que se lee (spec 016, data-model.md)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.guard import OMITTED_MARKER
from proyecto_modelos_lenguaje.voice.text import clean_for_speech, split_sentences


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Manuelita produce azúcar [U2].", "Manuelita produce azúcar."),
        ("Etanol y energía [U1, U3] en el Valle.", "Etanol y energía en el Valle."),
        (f"Dato legítimo. {OMITTED_MARKER} Otro dato.", "Dato legítimo. Otro dato."),
        ("Ver [el informe](https://www.manuelita.com/informe).", "Ver el informe."),
        ("Más en https://www.manuelita.com hoy.", "Más en hoy."),
        ("**Azúcar** y _etanol_ en `kWh`", "Azúcar y etanol en kWh"),
        ("# Título\n- primero\n- segundo", "Título primero segundo"),
        ("Creció 12% en 2023", "Creció 12 por ciento en 2023"),
        ("Azúcar & energía", "Azúcar y energía"),
        ("  muchos    espacios  ", "muchos espacios"),
    ],
)
def test_clean_for_speech(raw: str, expected: str) -> None:
    assert clean_for_speech(raw) == expected


@pytest.mark.parametrize("raw", ["[U2]", "  ", "**", "[U1, U2] —", OMITTED_MARKER, ""])
def test_nothing_speakable_returns_empty(raw: str) -> None:
    assert clean_for_speech(raw) == ""


def test_split_sentences_basic_order() -> None:
    text = "Manuelita produce azúcar. ¿Y etanol? ¡Sí! También energía; y biogás.\n\nFin"
    assert split_sentences(text) == [
        "Manuelita produce azúcar.",
        "¿Y etanol?",
        "¡Sí!",
        "También energía;",
        "y biogás.",
        "Fin",
    ]


@pytest.mark.parametrize(
    "text",
    [
        "La Sra. Pérez dirige la planta.",
        "La Dra. Gómez lo confirmó.",
        "Azúcar, etanol, etc. son productos clave.",
        "Hay productos, p. ej. azúcar y etanol.",
        "El ingenio No. 3 opera en Palmira.",
        "La producción fue de 3.5 millones de toneladas.",
    ],
)
def test_split_sentences_keeps_abbreviations_and_decimals(text: str) -> None:
    assert split_sentences(text) == [text]


def test_lowercase_no_at_the_end_still_splits() -> None:
    assert split_sentences("Dijo que no. Luego aceptó.") == ["Dijo que no.", "Luego aceptó."]


def test_long_sentence_is_split_by_commas_within_limit() -> None:
    text = ", ".join(["producción de azúcar"] * 60) + "."
    parts = split_sentences(text, max_chars=100)
    assert len(parts) > 1
    assert all(len(part) <= 100 for part in parts)
    assert " ".join(parts).replace(" ,", ",") == text


def test_first_segment_is_capped_for_fast_first_audio() -> None:
    # Arrange: primera oración larga, como las respuestas reales del agente
    first = (
        "La historia de Manuelita, y la de los ingenios azucareros en Colombia, comienza en 1864, "
        * 3
    )
    text = first.strip() + ". Segunda oración corta."
    # Act
    parts = split_sentences(text, first_max_chars=120)
    # Assert
    assert len(parts[0]) <= 120
    assert parts[-1] == "Segunda oración corta."
    assert all(len(part) <= 600 for part in parts[1:])
    assert " ".join(parts).replace(" ,", ",") == " ".join(text.split())


def test_first_segment_cap_only_applies_to_the_first() -> None:
    long_second = "Manuelita produce azúcar, etanol, energía y biogás en varias plantas " * 3
    text = "Hola. " + long_second.strip() + "."
    parts = split_sentences(text, first_max_chars=120)
    assert parts[0] == "Hola."
    assert len(parts[1]) > 120
