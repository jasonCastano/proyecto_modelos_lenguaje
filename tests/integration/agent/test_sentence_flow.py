"""Entrega por frases revisadas en los dos grafos, sin red (spec 021).

Las pruebas se agrupan por historia: ``-k us1`` (conversación) y ``-k us2`` (búsqueda). Verifican
las garantías G1–G4 de ``contracts/streaming.md`` §1.
"""

from __future__ import annotations

import re
from dataclasses import replace
from typing import Any

import pytest
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, AIMessageChunk, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult
from pydantic import Field

from proyecto_modelos_lenguaje.agent.config import ConversationConfig
from proyecto_modelos_lenguaje.agent.prompts import load_care
from proyecto_modelos_lenguaje.agent.service import ChatService
from proyecto_modelos_lenguaje.tasks import FALLBACK_ANSWER
from tests.agent_helpers import agent_config, make_service

VARIANTS = ["chain", "agent"]


class StreamingScriptModel(BaseChatModel):
    """Transmite cada respuesta palabra por palabra; ``RAISE`` falla y ``|ERR`` corta a mitad."""

    replies: list[str] = Field(default_factory=list)
    calls: int = 0

    @property
    def _llm_type(self) -> str:
        return "streaming-script"

    def _next(self) -> str:
        reply = self.replies[min(self.calls, len(self.replies) - 1)]
        self.calls += 1
        return reply

    def _generate(self, messages: list[BaseMessage], stop: Any = None, **_: Any) -> ChatResult:
        reply = self._next()
        if reply == "RAISE":
            raise RuntimeError("proveedor caído")
        text = reply.split("|ERR")[0]
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=text))])

    def _stream(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **_: Any
    ):
        reply = self._next()
        if reply == "RAISE":
            raise RuntimeError("proveedor caído")
        text, cut, _rest = reply.partition("|ERR")
        for word in re.findall(r"\S+\s*", text):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=word))
            if run_manager is not None:
                run_manager.on_llm_new_token(word, chunk=chunk)
            yield chunk
        if cut:
            raise RuntimeError("se cortó la conexión")


def service(model: BaseChatModel | None = None, **conversation: Any) -> ChatService:
    conversation.setdefault("mode", "guided")
    conversation.setdefault("delivery", "sentences")
    config = replace(agent_config(), conversation=replace(ConversationConfig(), **conversation))
    return make_service(model=model, config=config)


def turn(
    svc: ChatService, message: str, variant: str = "chain", thread_id: str | None = None
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    _thread, events = svc.open_stream(message, thread_id=thread_id, variant=variant)
    collected = list(events)
    errors = [e for e in collected if e["event"] == "error"]
    assert not errors, errors
    done = next(e for e in collected if e["event"] == "done")["response"]
    return collected, done


def sentences(events: list[dict[str, Any]]) -> list[str]:
    return [e["text"] for e in events if e["event"] == "sentence"]


def assert_guarantees(events: list[dict[str, Any]], done: dict[str, Any]) -> None:
    """G1: sin tokens; G2: la unión de las frases es la respuesta final."""
    assert not [e for e in events if e["event"] == "token"]
    shown = " ".join("".join(sentences(events)).split())
    assert shown == " ".join(done["turn"]["answer"].split())
    assert [e["index"] for e in events if e["event"] == "sentence"] == list(
        range(len(sentences(events)))
    )


# ---------------------------------------------------------------- US1: conversación


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_smalltalk_arrives_sentence_by_sentence(variant: str) -> None:
    events, done = turn(service(), "¡qué calor hace hoy en Cali!", variant)
    assert len(sentences(events)) >= 1
    assert_guarantees(events, done)
    assert done["contact"]["acts"][-1]["discarded"] == 0


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_a_later_external_fact_is_never_shown(variant: str) -> None:
    model = StreamingScriptModel(
        replies=["¡Uf, qué calor! Mañana hará 32 grados en Cali. Cuídate."]
    )
    events, done = turn(service(model), "¡qué calor hace hoy!", variant)
    assert_guarantees(events, done)
    assert "32" not in done["turn"]["answer"]
    assert done["turn"]["answer"].startswith("¡Uf, qué calor!")
    assert "sentence_discarded" in done["notices"]
    assert done["contact"]["acts"][-1]["discarded"] == 1


def test_us1_a_rejected_first_sentence_is_regenerated_without_showing_it() -> None:
    model = StreamingScriptModel(
        replies=[
            "Mañana hará 32 grados en Cali. Lleva agua.",
            "No tengo pronósticos del tiempo. Lo mío es contarte sobre Manuelita.",
        ]
    )
    events, done = turn(service(model), "¿cómo va a estar el clima mañana?")
    assert_guarantees(events, done)
    assert all("32" not in text for text in sentences(events))
    assert "review_retry" in done["notices"]
    assert done["contact"]["acts"][-1]["reviewed"] == "retry"


def test_us1_model_failure_before_any_sentence_uses_the_fallback() -> None:
    events, done = turn(service(StreamingScriptModel(replies=["RAISE"])), "¿quién ganó el partido?")
    assert_guarantees(events, done)
    assert "review_fallback" in done["notices"]
    assert "proveedor" not in done["turn"]["answer"]


def test_us1_model_failure_mid_answer_keeps_what_was_shown() -> None:
    model = StreamingScriptModel(replies=["¡Hola! Qué gusto leerte. |ERR"])
    events, done = turn(service(model), "¡qué rico este día!")
    assert_guarantees(events, done)
    answer = done["turn"]["answer"]
    assert answer.startswith("¡Hola! Qué gusto leerte.")
    closings = load_care().variants["close.short"]
    assert any(answer.endswith(closing) for closing in closings)


def test_us1_required_phrase_is_added_at_the_end() -> None:
    model = StreamingScriptModel(replies=["¡Hola! ¿Cómo va todo por allá?"])
    events, done = turn(service(model), "hola, buen día")
    assert_guarantees(events, done)
    answer = done["turn"]["answer"]
    assert answer.startswith("¡Hola!") and "Valer-IA Caña" in answer


@pytest.mark.parametrize("variant", VARIANTS)
def test_us1_crisis_keeps_its_fixed_text(variant: str) -> None:
    events, done = turn(service(), "ya no quiero vivir", variant)
    assert_guarantees(events, done)
    assert done["turn"]["answer"] == load_care().variants["crisis"][0]


def test_us1_complete_delivery_restores_spec_020() -> None:
    events, done = turn(service(delivery="complete"), "¡qué calor hace hoy!")
    assert not sentences(events)
    assert done["turn"]["answer"]


def test_us1_minimal_messages_keep_at_most_two_sentences() -> None:
    model = StreamingScriptModel(replies=["¡Listo! Aquí sigo. Cuéntame lo que quieras. Dale."])
    events, done = turn(service(model), "jaja")
    assert_guarantees(events, done)
    assert len(sentences(events)) == 2


# ---------------------------------------------------------------- US2: respuestas con búsqueda


@pytest.mark.parametrize("variant", VARIANTS)
def test_us2_retrieval_answers_arrive_with_valid_citations(variant: str) -> None:
    events, done = turn(service(), "¿Qué produce Manuelita?", variant)
    assert_guarantees(events, done)
    turn_data = done["turn"]
    assert turn_data["citations"]
    labels = {c["label"] for c in turn_data["citations"]}
    assert set(re.findall(r"\[([UF]\d+)\]", turn_data["answer"])) <= labels | {
        label
        for label in re.findall(r"\[([UF]\d+)\]", turn_data["answer"])
        if label in {f["label"] for f in turn_data["fragments"]}
    }


def test_us2_an_unsupported_figure_is_never_shown() -> None:
    model = StreamingScriptModel(
        replies=[
            "Según los documentos públicos de Manuelita, produce azúcar [U1]. "
            "En 2099 vendió 77 millones de toneladas [U1]. También genera energía [U1]."
        ]
    )
    events, done = turn(service(model), "¿Qué produce Manuelita?")
    assert_guarantees(events, done)
    answer = done["turn"]["answer"]
    assert "2099" not in answer and "genera energía" in answer
    assert "sentence_discarded" in done["notices"]


def test_us2_without_citations_the_visitor_sees_the_evidence_message() -> None:
    model = StreamingScriptModel(replies=["Manuelita es una gran empresa. Tiene muchos productos."])
    events, done = turn(service(model), "¿Qué produce Manuelita?")
    assert_guarantees(events, done)
    assert done["turn"]["answer"] == FALLBACK_ANSWER
    assert done["turn"]["citations"] == []


def test_us2_uncited_lead_in_is_held_until_a_cited_sentence() -> None:
    model = StreamingScriptModel(
        replies=["Te cuento lo que dicen los documentos. Manuelita produce azúcar [U1]."]
    )
    events, done = turn(service(model), "¿Qué produce Manuelita?")
    assert_guarantees(events, done)
    shown = sentences(events)
    assert shown[0].startswith("Te cuento") and "[U1]" in shown[1]
