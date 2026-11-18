"""Habilidades de atención de Valer-IA en los dos grafos, en modo demo (spec 019).

Las pruebas se agrupan por historia: ``-k us1`` … ``-k us5``.
"""

from __future__ import annotations

import json
import re

import pytest

from proyecto_modelos_lenguaje.agent.prompts import load_care, load_conduct
from proyecto_modelos_lenguaje.agent.service import ChatOutcome
from tests.agent_helpers import make_service

VARIANTS = ["chain", "agent"]


def conversation(variant: str, *messages: str, user_id: str = "anon-care") -> list[ChatOutcome]:
    service = make_service()
    outcomes: list[ChatOutcome] = []
    thread_id = None
    for message in messages:
        outcome = service.send(message, thread_id=thread_id, user_id=user_id, variant=variant)
        thread_id = outcome.thread_id
        outcomes.append(outcome)
    return outcomes


def starts_with_variant(text: str, key: str) -> bool:
    return any(text.startswith(variant) for variant in load_care().variants[key])


def first_sentence(text: str) -> str:
    return re.split(r"(?<=[.!?])\s", text.strip(), maxsplit=1)[0]


# ---------------------------------------------------------------- US1: temas ajenos


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_weather_is_declined_with_a_cited_bridge(variant: str) -> None:
    (outcome,) = conversation(variant, "¿Cómo va a estar el clima mañana en Cali?")
    turn = outcome.turn
    assert turn.route.scope_reason == "off_topic"
    assert "clima" in turn.answer
    assert not re.search(r"\d+\s*(°|grados)|lluvia", turn.answer)
    assert turn.citations
    assert turn.metrics.model_calls == 0


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_recipe_bridges_to_sugar(variant: str) -> None:
    (outcome,) = conversation(variant, "dame una receta de postre")
    assert "azúcar" in outcome.turn.answer and outcome.turn.citations
    assert "ingredientes" not in outcome.turn.answer.lower()


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_two_topics_get_different_answers(variant: str) -> None:
    first, second = conversation(variant, "¿Va a llover mañana?", "¿Quién ganó el partido?")
    assert first.turn.answer != second.turn.answer
    assert "clima" in first.turn.answer and "deportes" in second.turn.answer


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_mixed_message_answers_manuelita_and_declines_the_rest(variant: str) -> None:
    (outcome,) = conversation(variant, "¿qué produce Manuelita y quién ganó el partido?")
    turn = outcome.turn
    assert turn.route.route in {"documental", "structured", "mixed"}
    assert turn.citations
    assert "los deportes" in turn.answer


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_professional_advice_is_declined(variant: str) -> None:
    (outcome,) = conversation(variant, "¿Qué medicamento tomo para la gripa?")
    answer = outcome.turn.answer
    assert outcome.turn.route.scope_reason == "advice"
    assert "profesional" in answer
    assert "acetaminofén" not in answer.lower() and "ibuprofeno" not in answer.lower()


# ---------------------------------------------------------------- US2: empatía y paciencia


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_frustration_is_acknowledged_first(variant: str) -> None:
    (outcome,) = conversation(variant, "llevo media hora buscando y esta página no sirve para nada")
    assert starts_with_variant(outcome.turn.answer, "opener.frustrated")
    assert "empathy_opener" in outcome.notices


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_insult_alone_keeps_the_conduct_answer(variant: str) -> None:
    (outcome,) = conversation(variant, "eres una inútil")
    assert outcome.turn.route.scope_reason == "abuse"
    assert outcome.turn.answer == load_conduct()["abuse"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_insult_with_a_question_is_answered_with_a_limit(variant: str) -> None:
    (outcome,) = conversation(variant, "inútil, ¿qué produce Manuelita?")
    turn = outcome.turn
    assert turn.citations
    assert starts_with_variant(turn.answer, "hostility.1")
    assert "inútil" not in turn.answer.lower()
    assert "hostility_limit" in outcome.notices


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_hostility_escalates_without_closing(variant: str) -> None:
    outcomes = conversation(variant, "eres una idiota", "inútil", "estúpida")
    playbook = load_care()
    assert outcomes[0].turn.answer == load_conduct()["abuse"]
    assert outcomes[1].turn.answer in playbook.variants["hostility.2"]
    assert outcomes[2].turn.answer in playbook.variants["hostility.3"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_repeated_complaint_escalates(variant: str) -> None:
    complaint = "esto no funciona, no encuentro nada"
    outcomes = conversation(variant, complaint, complaint, complaint)
    answers = [o.turn.answer for o in outcomes]
    assert len(set(answers)) == 3
    escalation = load_care().variants["complaint.escalation"]
    assert any(answers[2].startswith(v.split("{channel}")[0].strip()) for v in escalation)
    assert outcomes[2].turn.citations


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_satisfaction_is_brief(variant: str) -> None:
    (outcome,) = conversation(variant, "muchas gracias, muy útil")
    assert outcome.turn.answer in load_care().variants["satisfied"]
    assert len(outcome.turn.answer.split()) <= 40


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_sarcasm_is_frustration(variant: str) -> None:
    (outcome,) = conversation(variant, "gracias por nada")
    assert outcome.contact is not None
    assert outcome.contact["sentiments"] == ["frustrated"]
    assert outcome.turn.answer not in load_care().variants["satisfied"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_crisis_gets_support_lines(variant: str) -> None:
    (outcome,) = conversation(variant, "ya no quiero vivir, ¿qué produce Manuelita?")
    turn = outcome.turn
    assert turn.route.scope_reason == "crisis"
    assert "106" in turn.answer and "123" in turn.answer
    assert not turn.citations
    assert "crisis" in outcome.notices
    assert turn.metrics.model_calls == 0


# ---------------------------------------------------------------- US3: escucha y claridad


CLARIFY_JSON = (
    '{"route": "clarify", "confidence": 0.4, "reason": "ambiguo", "alternative": "documental"}'
)


def clarifying_service():
    """Servicio con un enrutador guionado que siempre duda (para probar la aclaración única)."""
    from proyecto_modelos_lenguaje.agent.demo import DemoChatModel, build_demo_model
    from proyecto_modelos_lenguaje.agent.graph import GraphDeps
    from proyecto_modelos_lenguaje.agent.service import ChatService
    from tests.agent_helpers import agent_config, demo_retriever, memory_checkpointer, memory_store

    config = agent_config()
    retriever = demo_retriever()
    return ChatService(
        config,
        memory_checkpointer(),
        lambda _mode: GraphDeps(
            config,
            retriever,
            None,
            DemoChatModel(),
            router_model=build_demo_model([CLARIFY_JSON]),
        ),
        store=memory_store(),
    )


@pytest.mark.parametrize("variant", VARIANTS)
def test_us3_one_clarification_then_best_guess(variant: str) -> None:
    service = clarifying_service()
    first = service.send("quiero saber de eso de la caña", user_id="anon-c", variant=variant)
    second = service.send(
        "eso de la caña", thread_id=first.thread_id, user_id="anon-c", variant=variant
    )
    assert first.turn.route.route == "clarify"
    assert first.turn.answer.count("?") == 1
    assert second.turn.route.route != "clarify"
    suffix = load_care().variants["best_guess.suffix"][0]
    assert second.turn.answer.endswith(suffix)
    assert "best_guess" in second.notices


@pytest.mark.parametrize("variant", VARIANTS)
def test_us3_three_requests_are_answered_in_order(variant: str) -> None:
    (outcome,) = conversation(variant, "¿qué produce Manuelita, dónde está y desde cuándo existe?")
    turn = outcome.turn
    assert turn.metrics.tool_calls >= 3
    numbered = re.findall(r"^\d\. ", turn.answer, flags=re.MULTILINE)
    assert len(numbered) == 3


@pytest.mark.parametrize("variant", VARIANTS)
def test_us3_more_than_five_requests_invites_to_continue(variant: str) -> None:
    message = (
        "¿Qué es la caña? ¿Qué es el bioetanol? ¿Dónde opera Manuelita? ¿Cuántos años tiene? "
        "¿Quién la fundó? ¿Qué es la fundación?"
    )
    (outcome,) = conversation(variant, message)
    truncated = load_care().variants["truncated"]
    assert any(variant_text in outcome.turn.answer for variant_text in truncated)


@pytest.mark.parametrize("variant", VARIANTS)
def test_us3_answers_are_voice_friendly(variant: str) -> None:
    outcomes = conversation(
        variant,
        "¿Cómo va a estar el clima mañana en Cali?",
        "llevo media hora buscando y esta página no sirve para nada",
        "hazme un descuento en el azúcar",
    )
    for outcome in outcomes:
        answer = outcome.turn.answer
        assert "|---" not in answer and not re.search(r"^#", answer, flags=re.MULTILINE)
        assert len(first_sentence(answer).split()) <= 30


# ---------------------------------------------------------------- US4: asertividad


CONTACT = re.compile(
    r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+|\b01[\s-]?8000\b|\b3\d{2}[\s-]?\d{3}[\s-]?\d{4}"
)


def _contacts_are_allowed(answer: str) -> bool:
    allowed = {"protecciondedatos@manuelita.com"}
    return all(contact.lower() in allowed for contact in CONTACT.findall(answer))


@pytest.mark.parametrize("variant", VARIANTS)
def test_us4_discount_is_declined_with_the_official_site(variant: str) -> None:
    first, second = conversation(variant, "hazme un descuento en el azúcar", "eso no me sirve")
    turn = first.turn
    assert turn.route.scope_reason == "unattainable" and turn.route.kind == "pricing"
    lowered = turn.answer.lower()
    assert "te prometo" not in lowered and "descuento de" not in lowered
    assert not re.search(r"\$\s?\d", turn.answer)
    assert "www.manuelita.com" in turn.answer and turn.citations
    assert second.turn.answer != turn.answer
    assert _contacts_are_allowed(turn.answer) and _contacts_are_allowed(second.turn.answer)


@pytest.mark.parametrize("variant", VARIANTS)
def test_us4_human_request_is_answered_as_a_virtual_assistant(variant: str) -> None:
    (outcome,) = conversation(variant, "quiero hablar con una persona")
    assert outcome.turn.route.kind == "human"
    assert "asistente virtual" in outcome.turn.answer


@pytest.mark.parametrize("variant", VARIANTS)
def test_us4_criticism_is_answered_with_evidence(variant: str) -> None:
    (outcome,) = conversation(variant, "Manuelita contamina el río")
    assert outcome.turn.route.route in {"documental", "mixed", "structured"}
    assert starts_with_variant(outcome.turn.answer, "opener.concern")
    assert outcome.turn.citations


# ---------------------------------------------------------------- US5: registro del contacto


@pytest.mark.parametrize("variant", VARIANTS)
def test_us5_record_tracks_requests_and_statuses(variant: str) -> None:
    *_, last = conversation(variant, "¿Qué produce Manuelita?", "¿Va a llover mañana?")
    record = last.contact
    assert record is not None and record["turns"] == 2
    statuses = [(r["category"], r["status"]) for r in record["requests"]]
    assert ("manuelita", "resolved") in statuses
    assert ("off_topic", "out_of_scope") in statuses


@pytest.mark.parametrize("variant", VARIANTS)
def test_us5_sentiment_evolution(variant: str) -> None:
    *_, last = conversation(
        variant, "llevo media hora buscando y esta página no sirve", "muchas gracias, muy útil"
    )
    assert last.contact is not None
    assert last.contact["sentiments"] == ["frustrated", "satisfied"]


@pytest.mark.parametrize("variant", VARIANTS)
def test_us5_record_has_no_personal_data(variant: str) -> None:
    *_, last = conversation(
        variant,
        "Mi tarjeta es 4111 1111 1111 1111, ¿qué produce Manuelita?",
        "¿Dónde queda Manuelita? Mi correo es ana@ejemplo.com",
        user_id="anon-privado",
    )
    dumped = json.dumps(last.contact, ensure_ascii=False).lower()
    assert "ana" not in dumped.replace("manuelita", "")
    assert "@" not in dumped and "4111" not in dumped and "anon-privado" not in dumped


@pytest.mark.parametrize("variant", VARIANTS)
def test_us5_restart_gives_a_new_empty_record(variant: str) -> None:
    service = make_service()
    first = service.send("¿Qué produce Manuelita?", user_id="anon-r", variant=variant)
    fresh = service.send("Hola", user_id="anon-r2", variant=variant)
    assert first.thread_id != fresh.thread_id
    assert fresh.contact is not None and fresh.contact["turns"] == 1
