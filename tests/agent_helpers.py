"""Utilidades compartidas por las pruebas del agente conversacional (spec 014, US1)."""

from __future__ import annotations

import json
from collections.abc import Sequence
from dataclasses import replace
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.outputs import ChatGeneration, ChatResult
from pydantic import Field

from proyecto_modelos_lenguaje.agent.config import AgentConfig, load_agent_config
from proyecto_modelos_lenguaje.agent.demo import DemoChatModel
from proyecto_modelos_lenguaje.agent.graph import GraphDeps
from proyecto_modelos_lenguaje.agent.memory import memory_checkpointer
from proyecto_modelos_lenguaje.agent.service import ChatService
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.rag.config import load_retrieval_config
from proyecto_modelos_lenguaje.rag.embeddings import EmbeddingProfile, HashEmbedder
from proyecto_modelos_lenguaje.rag.hybrid import HybridRetriever
from proyecto_modelos_lenguaje.rag.index import load_index
from proyecto_modelos_lenguaje.retrieval import EntityIndex, GoldUnit

FIXTURE_DIR = PROJECT_ROOT / "tests" / "fixtures" / "rag"


def demo_retriever() -> HybridRetriever:
    """Recuperador híbrido sobre el índice de prueba, con embeddings hash (sin red)."""
    config = load_retrieval_config(project_root=PROJECT_ROOT)
    profile = EmbeddingProfile.from_config(config.embedding)
    units = [
        GoldUnit.from_dict(json.loads(line))
        for line in (FIXTURE_DIR / "gold_sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    return HybridRetriever(
        units,
        index=load_index(FIXTURE_DIR / "index", profile),
        embedder=HashEmbedder(profile),
        entity_index=EntityIndex(),
        config=config,
    )


def agent_config(**memory: Any) -> AgentConfig:
    config = load_agent_config()
    if memory:
        config = replace(config, memory=replace(config.memory, **memory))
    return config


def make_service(
    checkpointer: Any = None,
    *,
    model: BaseChatModel | None = None,
    config: AgentConfig | None = None,
    summary_model: BaseChatModel | None = None,
) -> ChatService:
    config = config or agent_config()
    retriever = demo_retriever()
    return ChatService(
        config,
        checkpointer if checkpointer is not None else memory_checkpointer(),
        lambda _mode: GraphDeps(
            config, retriever, None, model or DemoChatModel(), summary_model=summary_model
        ),
    )


class ScriptedModel(BaseChatModel):
    """Modelo que devuelve siempre el mismo texto y registra lo que recibió."""

    reply: str = ""
    seen: list[list[BaseMessage]] = Field(default_factory=list)

    @property
    def _llm_type(self) -> str:
        return "scripted-test"

    def _generate(
        self, messages: list[BaseMessage], stop: Any = None, run_manager: Any = None, **_: Any
    ) -> ChatResult:
        self.seen.append(list(messages))
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=self.reply))])


class AlwaysSearchModel(DemoChatModel):
    """Agente que pide buscar en cada llamada: sirve para probar los límites del middleware."""

    def _generate(
        self, messages: Sequence[BaseMessage], stop: Any = None, run_manager: Any = None, **_: Any
    ) -> ChatResult:
        calls = sum(isinstance(m, AIMessage) for m in messages)
        message = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "search_documents",
                    "args": {"query": f"Manuelita búsqueda {calls}"},
                    "id": f"call_{calls}",
                }
            ],
        )
        return ChatResult(generations=[ChatGeneration(message=message)])
