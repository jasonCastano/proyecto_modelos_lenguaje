"""Modo demostración determinista del agente: sin red ni clave (FR-021)."""

from __future__ import annotations

import html
import re
from collections.abc import Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult

from ..config import PROJECT_ROOT
from ..tasks import FALLBACK_ANSWER
from .actions import detect_write_intent
from .router import contextual_query

DEMO_INDEX = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "index"
DEMO_EMBEDDER_KIND = "hash"

DEFAULT_SCRIPT: tuple[str, ...] = ("Respuesta de demostración basada en el corpus [U1].",)
DOCUMENT_PATTERN = re.compile(r'<documento id="([UF]\d+)"[^>]*>(.*?)</documento>', re.DOTALL)
SENTENCE_END = re.compile(r"(?<=[.!?])\s")
QUESTION_PATTERN = re.compile(r"<pregunta>(.*?)</pregunta>", re.DOTALL)
SNIPPET_CHARS = 220
BULLETS_HINT = "formato de respuesta: viñetas"


def build_demo_model(
    script: Sequence[str | BaseMessage] | None = None,
) -> FakeMessagesListChatModel:
    """Modelo guionado: devuelve las respuestas en orden y vuelve a empezar al agotarlas."""
    responses = [
        item if isinstance(item, BaseMessage) else AIMessage(content=item)
        for item in (script or DEFAULT_SCRIPT)
    ]
    return FakeMessagesListChatModel(responses=responses)


def _first_sentence(text: str) -> str:
    clean = " ".join(html.unescape(text).split())
    sentence = SENTENCE_END.split(clean, maxsplit=1)[0]
    if len(sentence) > SNIPPET_CHARS:
        sentence = sentence[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"
    return sentence.rstrip(".")


def _question(text: str) -> str:
    asked = QUESTION_PATTERN.search(text)
    return (asked.group(1) if asked else text).strip()


def demo_answer(evidence_text: str, *, bullets: bool = False) -> str:
    """Respuesta extractiva: la primera oración de los dos primeros documentos, con su cita."""
    documents = DOCUMENT_PATTERN.findall(evidence_text)
    if not documents:
        return FALLBACK_ANSWER
    parts = [f"{_first_sentence(text)} [{label}]." for label, text in documents[:2] if text.strip()]
    if not parts:
        return FALLBACK_ANSWER
    if bullets:
        return "Según los documentos públicos de Manuelita:\n" + "\n".join(f"- {p}" for p in parts)
    return "Según los documentos públicos de Manuelita: " + " ".join(parts)


class DemoChatModel(BaseChatModel):
    """Modelo determinista para el modo demo: busca una vez y responde de forma extractiva.

    - Con herramientas enlazadas y sin resultados de herramienta en el turno, pide
      ``search_documents`` con la pregunta del usuario.
    - En cualquier otro caso responde con la primera oración de la evidencia y su etiqueta.
    """

    tools_bound: bool = False

    @property
    def _llm_type(self) -> str:
        return "manuelita-demo"

    def bind_tools(self, tools: Sequence[Any], **_kwargs: Any) -> DemoChatModel:  # type: ignore[override]
        return self.model_copy(update={"tools_bound": bool(tools)})

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_human = max(
            (i for i, message in enumerate(messages) if isinstance(message, HumanMessage)),
            default=-1,
        )
        tool_results = [m for m in messages[last_human + 1 :] if isinstance(m, ToolMessage)]
        if self.tools_bound and not tool_results:
            humans = [str(m.content) for m in messages if isinstance(m, HumanMessage)]
            current = _question(humans[-1]) if humans else ""
            previous = _question(humans[-2]) if len(humans) > 1 else None
            intent = detect_write_intent(current)
            if intent is not None:
                call = {"name": intent.tool, "args": dict(intent.args), "id": "demo_write_1"}
            else:
                query = contextual_query(current, previous)[:300]
                call = {"name": "search_documents", "args": {"query": query}, "id": "demo_call_1"}
            message = AIMessage(content="", tool_calls=[call])
        else:
            evidence = "\n".join(str(m.content) for m in (tool_results or messages[-1:]))
            if tool_results and not DOCUMENT_PATTERN.search(evidence):
                # Resultado de una acción de escritura (o su rechazo): se informa tal cual.
                message = AIMessage(content=evidence.strip())
            else:
                system = " ".join(str(m.content) for m in messages if isinstance(m, SystemMessage))
                message = AIMessage(content=demo_answer(evidence, bullets=BULLETS_HINT in system))
        return ChatResult(generations=[ChatGeneration(message=message)])
