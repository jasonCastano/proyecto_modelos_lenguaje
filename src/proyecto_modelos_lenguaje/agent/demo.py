"""Modo demostración determinista del agente: sin red ni clave (FR-021)."""

from __future__ import annotations

from collections.abc import Sequence

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, BaseMessage

from ..config import PROJECT_ROOT

DEMO_INDEX = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "index"
DEMO_EMBEDDER_KIND = "hash"

DEFAULT_SCRIPT: tuple[str, ...] = ("Respuesta de demostración basada en el corpus [U1].",)


def build_demo_model(
    script: Sequence[str | BaseMessage] | None = None,
) -> FakeMessagesListChatModel:
    """Modelo guionado: devuelve las respuestas en orden y vuelve a empezar al agotarlas."""
    responses = [
        item if isinstance(item, BaseMessage) else AIMessage(content=item)
        for item in (script or DEFAULT_SCRIPT)
    ]
    return FakeMessagesListChatModel(responses=responses)
