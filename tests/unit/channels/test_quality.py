"""Revisión automática del formato del canal (spec 029, T004, FR-015)."""

from __future__ import annotations

import json

import pytest

from proyecto_modelos_lenguaje.channels.quality import codes, review_reply
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

REGRESSION = PROJECT_ROOT / "tests" / "fixtures" / "channels" / "regression_2026-11-27.jsonl"


def _cases() -> dict[str, dict]:
    lines = REGRESSION.read_text(encoding="utf-8").splitlines()
    return {case["id"]: case for case in map(json.loads, lines) if case}


def test_the_three_real_replies_fail_the_review() -> None:
    cases = _cases()
    found = {
        cid: codes(review_reply([case["reply"]], case["lang"], sensitive_input=False))
        for cid, case in cases.items()
    }
    assert all("unexpected_notice" in issues for issues in found.values())  # aviso sin motivo
    assert {"dirty_title", "sources_line_format"} <= found["r2"]  # «Índice 1. 2. 3. …»
    assert {"mixed_language", "wrong_sources_header", "duplicate_source"} <= found["r3"]


ES_OK = (
    "Manuelita nació en 1864 en el Valle del Cauca [1]. "
    "Hoy tiene negocios en varios países [2].\n\n"
    "Fuentes:\n"
    "[1] Manuelita: más que azúcar — https://www.manuelita.com/noticias/mas-azucar\n"
    "[2] Informe de Sostenibilidad Manuelita 2021-2022, p. 31 — https://www.manuelita.com/x.pdf"
)
EN_OK = (
    "Manuelita was founded in 1864 in the Cauca Valley [1]. If you like, I can tell you more.\n\n"
    "Sources:\n"
    "[1] Manuelita: more than sugar — https://www.manuelita.com/noticias/mas-azucar"
)


@pytest.mark.parametrize(("reply", "language"), [(ES_OK, "es"), (EN_OK, "en")])
def test_well_formed_replies_pass(reply: str, language: str) -> None:
    assert review_reply([reply], language) == []


def test_each_code_has_a_case() -> None:
    assert "wrong_sources_header" in codes(review_reply([ES_OK], "en"))
    numbering = ES_OK.replace("[2] Informe", "[3] Informe")
    assert "sources_numbering" in codes(review_reply([numbering], "es"))
    long_title = ES_OK.replace("Manuelita: más que azúcar", "x" * 90)
    assert "dirty_title" in codes(review_reply([long_title], "es"))
    notice = "Ojo: por aquí no hace falta que compartas datos como tarjetas. " + ES_OK
    assert "unexpected_notice" in codes(review_reply([notice], "es"))
    assert review_reply([notice], "es", sensitive_input=True) == []
    assert "missing_notice" in codes(review_reply([ES_OK], "es", sensitive_input=True))
    mixed = "Manuelita was founded in 1864 and the company is in the Cauca Valley. " + ES_OK
    assert "mixed_language" in codes(review_reply([mixed], "es"))


def test_sources_split_across_messages_count_together() -> None:
    first = "Manuelita produce azúcar y etanol en el Valle del Cauca [1]."
    last = "Fuentes:\n[1] Informe — https://www.manuelita.com/a.pdf"
    assert review_reply([first, last], "es") == []


# --- spec 030: el texto que acompaña a la nota de voz (T005) -------------------------------------

REGRESSION_B = PROJECT_ROOT / "tests" / "fixtures" / "channels" / "regression_2026-11-27b.jsonl"


def _cases_b() -> list[dict]:
    lines = REGRESSION_B.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line]


def test_real_voice_turns_repeat_the_answer_in_text() -> None:
    for case in _cases_b():
        found = codes(review_reply([case["reply"]], case["lang"], voice=True))
        assert "voice_text_duplicate" in found, case["id"]


def test_the_sources_block_alone_passes_with_voice() -> None:
    for case in _cases_b():
        block = case["reply"][case["reply"].index("Fuentes:") :]
        assert len(block.splitlines()) == case["sources_lines"] + 1  # SC-005: encabezado + fuentes
        assert review_reply([block], case["lang"], voice=True) == [], case["id"]


def test_voice_turns_without_text_and_text_turns_still_pass() -> None:
    assert review_reply([], "es", voice=True) == []
    assert review_reply([ES_OK], "es") == []
    # El aviso de datos sensibles va en la voz: no se exige por escrito.
    assert review_reply([], "es", voice=True, sensitive_input=True) == []
    continuation = [
        "Fuentes:\n[1] Informe — https://manuelita.com/a",
        "[2] Otro — https://manuelita.com/b",
    ]
    assert review_reply(continuation, "es", voice=True) == []
