"""Aviso de datos sensibles natural y oportuno (spec 029, US3, T014)."""

from __future__ import annotations

import pytest

from proyecto_modelos_lenguaje.agent.privacy import find_pii, redact_pii
from proyecto_modelos_lenguaje.agent.prompts import load_conduct
from tests.agent_helpers import make_service

VARIANTS = ["chain", "agent"]
HEADER = "[WhatsApp +57 300 123 4567] "


def _kinds(text: str) -> set[str]:
    return {match["type"] for match in find_pii(text)}


def test_password_phrases_are_detected_and_redacted() -> None:
    assert "password" in _kinds("My password is Caña2026!, what does Manuelita produce?")
    assert "password" in _kinds("mi contraseña es hola1234")
    assert "password" in _kinds("clave: 998877")
    assert "Caña2026" not in redact_pii("My password is Caña2026!")
    assert "password" not in _kinds("¿Cuál es la clave del éxito de Manuelita?")


@pytest.mark.parametrize("variant", VARIANTS)
def test_a_phone_number_never_triggers_the_notice(variant: str) -> None:
    outcome = make_service().send(
        HEADER + "¿Qué produce Manuelita?", user_id="anon-s1", variant=variant
    )
    assert "sensitive_data" not in outcome.notices
    conduct = load_conduct()
    assert conduct["sensitive_notice"] not in outcome.turn.answer


@pytest.mark.parametrize(
    "message",
    [
        "Mi tarjeta es 4111 1111 1111 1111, ¿qué productos tiene Manuelita?",
        "Mi cédula es 1234567890, ¿dónde queda Manuelita?",
        "Mi contraseña es Caña2026!, ¿qué produce Manuelita?",
    ],
)
def test_card_document_and_password_trigger_it_at_the_end(message: str) -> None:
    outcome = make_service().send(message, user_id="anon-s2", variant="agent")
    notice = load_conduct()["sensitive_notice"]
    assert "sensitive_data" in outcome.notices
    assert outcome.turn.answer.endswith(notice)
    assert not outcome.turn.answer.startswith(notice)
    assert "4111" not in outcome.turn.answer and "1234567890" not in outcome.turn.answer


@pytest.mark.parametrize("variant", VARIANTS)
def test_once_per_thread_unless_a_new_kind_appears(variant: str) -> None:
    service = make_service()
    notice = load_conduct()["sensitive_notice"]
    card = "Mi tarjeta es 4111 1111 1111 1111, ¿qué produce Manuelita?"
    first = service.send(card, user_id="anon-s3", variant=variant)
    again = service.send(card, thread_id=first.thread_id, user_id="anon-s3", variant=variant)
    other = service.send(
        "Mi cédula es 1234567890, ¿dónde queda Manuelita?",
        thread_id=first.thread_id,
        user_id="anon-s3",
        variant=variant,
    )
    assert first.turn.answer.endswith(notice)
    assert notice not in again.turn.answer
    assert other.turn.answer.endswith(notice)


def test_the_notice_is_natural() -> None:
    conduct = load_conduct()
    assert conduct["sensitive_notice"].startswith("Ojo:")
    assert "no compartas" not in conduct["sensitive_notice"]
    assert conduct["sensitive_notice_en"].startswith("Just so you know")
