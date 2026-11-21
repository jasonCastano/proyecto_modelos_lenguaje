"""Revisión antes de mostrar (spec 020, R8 y ``contracts/conversation.md`` §4)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent import care
from proyecto_modelos_lenguaje.agent.config import CareConfig
from proyecto_modelos_lenguaje.agent.plan import TurnPlan
from proyecto_modelos_lenguaje.agent.prompts import load_care, load_conduct
from proyecto_modelos_lenguaje.agent.review import (
    correction_note,
    drop_flagged_sentences,
    review,
    similarity,
    trim_sentences,
)


def plan(act: str = "smalltalk", **kwargs: object) -> TurnPlan:
    values = {
        "act": act,
        "tiers": ("social",),
        "sentiment": "neutral",
        "strategy": ("accompany",),
        "length": "medium",
        "language": "es",
        "register": "formal",
        "turn": 2,
    }
    values.update(kwargs)
    return TurnPlan(**values)  # type: ignore[arg-type]


@pytest.mark.parametrize(
    "text",
    [
        "Mañana hará 32 grados en Cali.",
        "Ganó 2 a 1 el equipo local.",
        "El dólar está a 4.000 pesos.",
        "Según Juan Pérez, va a llover.",
        "Hace mucho calor, unos grados más que ayer.",
    ],
)
def test_external_facts_are_flagged(text: str) -> None:
    verdict = review(text, plan())
    assert not verdict.ok
    assert "external_fact" in verdict.issues


@pytest.mark.parametrize(
    "text",
    [
        "¡Uf, en Cali el calor no perdona! ¿Te ayudo con algo de Manuelita?",
        "Hola Ana, qué gusto leerte de nuevo.",
        "Soy Valer-IA Caña y te cuento sobre la Fundación Manuelita.",
        "Hi! I'm Valer-IA Caña, an AI assistant.",
    ],
)
def test_social_text_passes(text: str) -> None:
    verdict = review(text, plan(), names=["Ana"])
    assert verdict.ok, verdict.spans


def test_numbers_from_the_bridge_are_allowed() -> None:
    bridge = "Manuelita empezó en 1864 como un trapiche."
    text = "Por cierto, Manuelita empezó en 1864 como un trapiche [U1]."
    assert review(text, plan(), evidence=bridge, labels={"U1"}).ok
    assert "citation" in review(text, plan(), evidence=bridge, labels=()).issues


def test_invented_contacts_promises_and_opinions() -> None:
    playbook = load_care()
    contact = review("Escríbeme a ventas@manuelita.co para eso.", plan(), playbook=playbook)
    assert "contact" in contact.issues
    assert "promise" in review("Te garantizo que te van a contratar.", plan()).issues
    assert "promise" in review("Te hago un descuento especial.", plan()).issues
    assert "opinion" in review("Yo creo que el gobierno lo hace mal.", plan()).issues


def test_repetition_against_recent_answers() -> None:
    previous = "No tengo esa información, pero con gusto te cuento sobre Manuelita."
    same = "No tengo esa información, pero con gusto te cuento sobre Manuelita hoy."
    different = "¡Uy, qué calor! Ojalá tengas un ventilador cerca."
    assert similarity(previous, same) > 0.5
    assert "repetition" in review(same, plan(), recent_answers=[previous]).issues
    assert review(different, plan(), recent_answers=[previous]).ok


def test_required_phrases_follow_the_plan() -> None:
    greeting = plan("greeting", turn=1)
    assert "required" in review("¡Hola! ¿En qué te ayudo?", greeting).issues
    assert review("¡Hola! Soy Valer-IA Caña, ¿en qué te ayudo?", greeting).ok
    about = plan("about_assistant")
    assert not review("Soy una asistente.", about).ok
    assert review("Soy Valer-IA Caña, una asistente con inteligencia artificial.", about).ok
    advice = plan("off_topic", reason="advice")
    assert not review("Eso no lo puedo responder.", advice).ok
    assert review("Para eso consulta a un profesional.", advice).ok
    english = plan("about_assistant", language="en")
    assert review("I'm an AI assistant.", english).ok


def test_correction_note_names_each_issue() -> None:
    verdict = review("Mañana hará 32 grados.", plan())
    note = correction_note(verdict, plan())
    assert note.startswith("Corrige") and "cifras" in note


def test_scripted_fallback_texts_pass_the_review() -> None:
    """Los guiones de respaldo (spec 019) pasan la revisión con su propia cita como evidencia."""
    playbook = load_care()
    state = care.empty_care_state()
    for message in ["¿Cómo va a estar el clima mañana?", "¿Quién ganó el partido?"]:
        signals = care.analyze(message, state, CareConfig())
        decision = {"route": "out_of_scope", "scope_reason": "off_topic"}
        text, citations = care.compose_out_of_scope(signals, decision, playbook, state)
        evidence = " ".join(
            variant for key in playbook.citations for variant in playbook.variants[key]
        )
        labels = {c["label"] for c in citations}
        verdict = review(text, plan("off_topic"), evidence=evidence, labels=labels)
        assert verdict.ok, verdict.spans
    for key in ("greeting", "ai_disclosure", "farewell", "clarify"):
        assert review(load_conduct()[key], plan()).ok, key


def test_trim_and_drop_helpers() -> None:
    assert trim_sentences("Uno. Dos. Tres.", 2) == "Uno. Dos."
    text = "Manuelita produce azúcar [U1]. En 2099 vendió 5 millones… [U2]. Opera en Colombia [U3]."
    assert drop_flagged_sentences(text, ["2099"]) == (
        "Manuelita produce azúcar [U1]. Opera en Colombia [U3]."
    )
