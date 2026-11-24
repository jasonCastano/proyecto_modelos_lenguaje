"""Formato de WhatsApp (spec 024, T014, channel-api §5)."""

from __future__ import annotations

from proyecto_modelos_lenguaje.channels.format import (
    ABBREVIATED,
    markdown_to_whatsapp,
    number_citations,
    to_whatsapp,
)

CITATIONS = [
    {"label": "U3", "url": "https://manuelita.com/a", "title": "Informe de Sostenibilidad 2023"},
    {"label": "F1", "url": "https://manuelita.com/b", "title": "Series anuales", "page": 6},
]


def test_markdown_to_whatsapp() -> None:
    text = "## Productos\n\n**Azúcar** y etanol\n- uno\n* dos"
    assert markdown_to_whatsapp(text) == "*Productos*\n\n*Azúcar* y etanol\n• uno\n• dos"


def test_tables_become_bullets() -> None:
    table = "| Año | Valor |\n|---|---|\n| 2023 | 10 |"
    assert markdown_to_whatsapp(table) == "• Año · Valor\n• 2023 · 10"


def test_citations_are_renumbered_by_appearance() -> None:
    text, used = number_citations("Azúcar [F1] y etanol [U3]; de nuevo [F1].", CITATIONS)
    assert text == "Azúcar [1] y etanol [2]; de nuevo [1]."
    assert [number for number, _ in used] == [1, 2]
    assert used[0][1]["label"] == "F1"


def test_grouped_labels() -> None:
    text, _ = number_citations("Dato [U3, F1].", CITATIONS)
    assert text == "Dato [1][2]."


def test_sources_block_at_the_end() -> None:
    messages = to_whatsapp("Manuelita produce azúcar [U3]. Vende energía [F1].", CITATIONS)
    assert len(messages) == 1
    assert messages[0].endswith(
        "Fuentes:\n[1] Informe de Sostenibilidad 2023 — https://manuelita.com/a\n"
        "[2] Series anuales, p. 6 — https://manuelita.com/b"
    )


def test_long_titles_are_shortened() -> None:
    long = [{"label": "U1", "url": "u", "title": "T" * 120}]
    message = to_whatsapp("Hola [U1].", long)[0]
    assert "T" * 79 + "…" in message and "T" * 80 not in message


def test_split_by_sentences_without_breaking_citations() -> None:
    sentence = "Manuelita produce azúcar en el Valle del Cauca desde hace muchos años [U3]. "
    messages = to_whatsapp(sentence * 40, CITATIONS, max_chars=300, max_messages=4)
    assert len(messages) == 4
    assert all(len(message) <= 300 for message in messages)
    assert ABBREVIATED in messages[-2] and messages[-1].startswith("Fuentes:")
    for message in messages:
        assert message.count("[") == message.count("]")


def test_empty_answer() -> None:
    assert to_whatsapp("", []) == []
