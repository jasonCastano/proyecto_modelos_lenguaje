"""Segmentador y filtro de frases (spec 021, ``contracts/streaming.md`` §3)."""

from __future__ import annotations

import random

import pytest

from proyecto_modelos_lenguaje.agent.sentences import (
    SentenceGate,
    SentenceSplitter,
    split_all,
)


def stream(splitter: SentenceSplitter, text: str, size: int = 3) -> list[str]:
    out: list[str] = []
    for start in range(0, len(text), size):
        out += splitter.push(text[start : start + size])
    return out + splitter.close()


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Hola. ¿Cómo estás? ¡Qué bien!", ["Hola.", " ¿Cómo estás?", " ¡Qué bien!"]),
        ("El Sr. Pérez llegó. Fin.", ["El Sr. Pérez llegó.", " Fin."]),
        ("Resolución No. 19 del 2018. Fin.", ["Resolución No. 19 del 2018.", " Fin."]),
        ("Vendió 4.416.312 pesos en 2023. Fin.", ["Vendió 4.416.312 pesos en 2023.", " Fin."]),
        ("Produce azúcar [U1]. Y energía [U2].", ["Produce azúcar [U1].", " Y energía [U2]."]),
        ("Produce azúcar. [U1] Y energía.", ["Produce azúcar. [U1]", " Y energía."]),
    ],
)
def test_sentences_follow_the_voice_rule(text: str, expected: list[str]) -> None:
    assert split_all(text) == expected
    assert stream(SentenceSplitter(), text) == expected


def test_numbered_lists_keep_their_line_breaks() -> None:
    text = "Según los documentos:\n1. Azúcar [U1].\n2. Energía [U2]."
    pieces = split_all(text)
    assert pieces[0].endswith("Azúcar [U1].") and pieces[1] == "\n2. Energía [U2]."
    assert "".join(pieces) == text


def test_long_text_without_punctuation_is_cut_at_a_space() -> None:
    text = " ".join(["palabra"] * 80)
    pieces = split_all(text, max_chars=100, first_chars=50)
    assert len(pieces[0]) <= 50 and pieces[0].endswith("palabra")
    assert all(len(piece.strip()) <= 100 for piece in pieces[1:])
    assert "".join(pieces) == text


def test_a_trailing_period_waits_for_more_text() -> None:
    splitter = SentenceSplitter()
    assert splitter.push("Habló el Sr.") == []
    assert splitter.push(" Pérez. Y") == ["Habló el Sr. Pérez."]


def test_prefix_invariant_on_random_chunks() -> None:
    rng = random.Random(7)
    text = (
        "¡Hola! Te cuento que Manuelita produce azúcar [U1]. El Dr. Gómez visitó Palmira. "
        "¿Te interesa saber más?\n\n1. Uno.\n2. Dos. Fin"
    )
    for _ in range(30):
        splitter = SentenceSplitter(max_chars=60, first_chars=40)
        out: list[str] = []
        position = 0
        while position < len(text):
            size = rng.randint(1, 9)
            out += splitter.push(text[position : position + size])
            position += size
            assert text.startswith("".join(out))
        out += splitter.close()
        assert "".join(out) == text


def gate(mode: str, bad: tuple[str, ...] = (), **kwargs: object) -> SentenceGate:
    def check(sentence: str, _first: bool) -> list[str]:
        return ["external_fact"] if any(word in sentence for word in bad) else []

    return SentenceGate(mode, check, SentenceSplitter(), **kwargs)  # type: ignore[arg-type]


def run(target: SentenceGate, text: str) -> list[tuple[str, str]]:
    decisions = []
    for start in range(0, len(text), 4):
        decisions += target.push(text[start : start + 4])
        if target.stopped or target.first_check_failed:
            break
    else:
        decisions += target.close()
    return [(d.kind, d.text) for d in decisions]


def test_conversation_delivers_until_a_rejected_sentence() -> None:
    target = gate("conversation", bad=("32 grados",))
    decisions = run(target, "¡Qué calor! Mañana hará 32 grados. Cuídate mucho.")
    assert decisions == [("deliver", "¡Qué calor!"), ("stop", "")]
    assert target.delivered == ["¡Qué calor!"] and target.discarded == ["external_fact"]


def test_conversation_retries_when_the_first_sentence_fails() -> None:
    target = gate("conversation", bad=("32 grados",))
    assert run(target, "Hará 32 grados. ¡Uf!") == [("retry", "")]
    assert target.first_check_failed and not target.delivered


def test_short_answers_stop_after_two_sentences() -> None:
    target = gate("conversation", max_sentences=2)
    run(target, "Uno. Dos. Tres. Cuatro.")
    assert target.delivered == ["Uno.", " Dos."] and target.stopped


def test_retrieval_holds_uncited_sentences_and_skips_bad_ones() -> None:
    target = gate("retrieval", bad=("2099",))
    decisions = run(
        target,
        "Según los documentos de Manuelita: produce azúcar [U1]. En 2099 vendió todo [U2]. "
        "Opera en Colombia [U3]. Es todo.",
    )
    delivered = [text for kind, text in decisions if kind == "deliver"]
    assert delivered[0].startswith("Según los documentos")
    assert all("2099" not in text for text in delivered)
    assert delivered[-1] == " Es todo."
    assert target.discarded == ["external_fact"] and not target.no_evidence


def test_retrieval_without_citations_delivers_nothing() -> None:
    target = gate("retrieval")
    assert run(target, "Lo siento. No tengo datos.") == []
    assert target.no_evidence and not target.delivered
