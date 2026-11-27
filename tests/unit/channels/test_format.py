"""Formato de WhatsApp (spec 024, T014, channel-api §5; spec 029, T010, T017, T019)."""

from __future__ import annotations

from proyecto_modelos_lenguaje.channels.format import (
    ABBREVIATED,
    TEXTS,
    clean_title,
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
    long = [{"label": "U1", "url": "u", "title": "T" * 60 + " " + "T" * 60}]
    message = to_whatsapp("Hola [U1].", long)[0]
    line = message.splitlines()[-1]
    title = line[len("[1] ") : line.index(" — ")]
    assert len(title) == 80 and title.endswith("…")


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


# --- spec 029: idioma del turno (T010) y fuentes ordenadas (T017, T019) ---------------------------

# Título real de la fuente [5] de la prueba de las 10.00.56 (regression_2026-11-27.jsonl, r2).
REAL_INDEX_TITLE = "Índice\n1.\n2.\n3.\n\n4. \n5. \n6. \n7. \n\nCarta del presid"
REPORT_2013 = (
    "https://www.manuelita.com/wp-content/uploads/2017/05/"
    "Informe-de-Sostenibilidad-Manuelita-2013-2014_digitalA.pdf"
)
REPORT_2021 = (
    "https://www.manuelita.com/wp-content/uploads/2023/06/"
    "Informe_Sostenibilidad_Manuelita-2021-2022.pdf"
)


def test_sources_and_abbreviation_follow_the_turn_language() -> None:
    answer = "Manuelita makes sugar [U3]. It sells energy [F1]."
    english = to_whatsapp(answer, CITATIONS, language="en")[0]
    assert "Sources:\n[1] Informe de Sostenibilidad 2023" in english
    assert "Fuentes" not in english
    synthetic = [{"label": "S1", "title": "Procedimiento de cosecha", "kind": "synthetic"}]
    assert "Synthetic sources (demo):" in to_whatsapp("Step [S1].", synthetic, language="en")[0]
    sentence = "This is a sentence about sugar and ethanol in the valley [U3]. "
    long = "\n".join(to_whatsapp(sentence * 60, CITATIONS, max_chars=300, language="en"))
    assert TEXTS["en"]["abbreviated"] in long and ABBREVIATED not in long
    assert to_whatsapp("Azúcar [U3].", CITATIONS)[0].count("Fuentes:") == 1


def test_clean_title_with_the_real_index_title() -> None:
    expected = "Informe de Sostenibilidad Manuelita 2013-2014"
    assert clean_title(REAL_INDEX_TITLE, REPORT_2013) == expected
    slug = "Informe_Sostenibilidad_Manuelita-2021-2022"
    assert clean_title(slug, REPORT_2021) == "Informe Sostenibilidad Manuelita 2021-2022"
    one_line = clean_title("Manuelita:\nmás que azúcar " + "x " * 60, "https://manuelita.com/n")
    assert "\n" not in one_line and len(one_line) <= 80 and one_line.endswith("…")
    assert clean_title("", "https://www.manuelita.com/noticias") == "manuelita.com"
    assert clean_title("Conoce Manuelita", "https://manuelita.com/x") == "Conoce Manuelita"


def test_same_url_and_page_share_one_number() -> None:
    citations = [
        {"label": "F1", "url": REPORT_2021, "title": "Informe anual", "page": 31},
        {"label": "F2", "url": REPORT_2021, "title": "Informe anual", "page": 31},
        {"label": "F3", "url": REPORT_2021, "title": "Informe anual", "page": 40},
    ]
    text, used = number_citations("Ventas [F1][F2]. Agua [F2] y caña [F3].", citations)
    assert text == "Ventas [1]. Agua [1] y caña [2]."
    assert [number for number, _ in used] == [1, 2]
    message = to_whatsapp("Ventas [F1, F2]. Caña [F3].", citations)[0]
    assert message.count(REPORT_2021) == 2  # páginas 31 y 40: dos fuentes, sin repetir
    assert "[1] Informe anual, p. 31 — " in message
    assert "[2] Informe anual, p. 40 — " in message


def test_paragraphs_are_kept_and_the_sources_block_is_never_split() -> None:
    citations = [
        {"label": f"U{i}", "url": f"https://www.manuelita.com/doc-{i}", "title": f"Documento {i}"}
        for i in range(1, 6)
    ]
    paragraphs = [f"Párrafo {i} sobre Manuelita y su historia [U{i}]. " * 4 for i in range(1, 6)]
    messages = to_whatsapp("\n\n".join(paragraphs), citations, max_chars=700, max_messages=4)
    assert "\n\n" in messages[0]
    last = messages[-1]
    block = last[last.index("Fuentes:") :].splitlines()
    expected = [f"[{i}] Documento {i} — https://www.manuelita.com/doc-{i}" for i in range(1, 6)]
    assert block == ["Fuentes:", *expected]
    assert all("Fuentes:" not in message for message in messages[:-1])


def test_file_metadata_titles_use_the_document_name() -> None:
    report = (
        "https://www.manuelita.com/wp-content/uploads/2019/07/"
        "Informe-de-Sostenibilidad-2017-2018_VF_BAJA.pdf"
    )
    citations = [
        {
            "label": "F1",
            "url": report,
            "title": "Informe-de-Sostenibilidad-2017-2018_VF_BAJA, p. 27",
        },
        {"label": "U1", "url": report, "title": "Portada-acercade-cartapresidente VFBAJA"},
    ]
    message = to_whatsapp("Caña [F1]. Carta [U1].", citations)[0]
    assert "[1] Informe de Sostenibilidad 2017-2018, p. 27 — " in message
    assert "[2] Informe de Sostenibilidad 2017-2018 — " in message
    assert "_" not in message.split("Fuentes:")[1].replace(report, "")


def test_a_generic_title_shared_by_two_links_uses_each_link_name() -> None:
    generic = "Conoce las últimas noticias de Manuelita Agroindustria"
    citations = [
        {
            "label": "U1",
            "url": "https://www.manuelita.com/noticias/manuelita-mas-azucar",
            "title": generic,
        },
        {
            "label": "U2",
            "url": "https://www.manuelita.com/noticias/conciencia-verde",
            "title": generic,
        },
    ]
    message = to_whatsapp("Azúcar [U1]. Ambiente [U2].", citations)[0]
    assert "[1] Manuelita mas azucar — " in message and "[2] Conciencia verde — " in message


# --- spec 030: solo el bloque de fuentes para acompañar una nota de voz (T004) ---


def test_sources_only_keeps_the_numbers_of_the_full_text() -> None:
    from proyecto_modelos_lenguaje.channels.format import sources_only

    answer = "Manuelita produce azúcar [U3]. Vende energía [F1]."
    full = to_whatsapp(answer, CITATIONS)[0]
    only = sources_only(answer, CITATIONS)
    assert only == [full[full.index("Fuentes:") :]]
    assert only[0].splitlines()[1].startswith("[1] Informe de Sostenibilidad 2023")
    assert sources_only("Hola, ¿en qué te ayudo?", CITATIONS) == []  # sin citas en la respuesta
    assert sources_only(answer, CITATIONS, language="en")[0].startswith("Sources:\n[1] ")


def test_sources_only_keeps_synthetic_sources_apart() -> None:
    from proyecto_modelos_lenguaje.channels.format import sources_only

    citations = [
        *CITATIONS,
        {"label": "S1", "title": "Procedimiento de cosecha", "kind": "synthetic"},
    ]
    (block,) = sources_only("Dato [U3]. Paso [S1].", citations)
    assert block.startswith("Fuentes:\n[1] ")
    assert "\n\nFuentes sintéticas (demostración):\n[2] Procedimiento de cosecha" in block


def test_sources_only_splits_by_whole_lines() -> None:
    from proyecto_modelos_lenguaje.channels.format import sources_only

    citations = [
        {
            "label": f"U{i}",
            "url": f"https://www.manuelita.com/documento-{i}",
            "title": f"Documento {i}",
        }
        for i in range(1, 31)
    ]
    answer = " ".join(f"Dato {i} [U{i}]." for i in range(1, 31))
    messages = sources_only(answer, citations, max_chars=300)
    assert len(messages) > 1 and all(len(message) <= 300 for message in messages)
    lines = [line for message in messages for line in message.splitlines()]
    assert lines.count("Fuentes:") == 1 and lines[0] == "Fuentes:"
    expected = [
        f"[{i}] Documento {i} — https://www.manuelita.com/documento-{i}" for i in range(1, 31)
    ]
    assert lines[1:] == expected
