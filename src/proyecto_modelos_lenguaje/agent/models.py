"""Modelos de dominio del agente RAG (``specs/014-rag-agent-memory-router/data-model.md``)."""

from __future__ import annotations

import re
from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Route = Literal["direct", "documental", "structured", "mixed", "out_of_scope", "clarify"]
# Spec 022: "jev" = gatekeeper System One de TypeSafe.
DecidedBy = Literal["rules", "llm", "demo", "jev"]
WriteTool = Literal[
    "forget_memory", "save_preference", "save_profile", "export_conversation", "remember_client"
]
# Spec 018: motivo de una respuesta sin búsqueda (conducta de Valer-IA).
# Spec 019: «crisis» (angustia grave) y «unattainable» (precios, compromisos, pedir una persona).
ScopeReason = Literal[
    "off_topic",
    "abuse",
    "harmful",
    "third_party",
    "prompt_extraction",
    "advice",
    "identity",
    "crisis",
    "unattainable",
]
# Spec 019: estado emocional del visitante y tipo de pedido no atendible.
Sentiment = Literal["neutral", "satisfied", "confused", "frustrated", "angry", "distressed"]
UnattainableKind = Literal["pricing", "commitment", "human"]
# Spec 020: acto de diálogo del turno, nivel de contenido de cada parte y estrategia de respuesta.
DialogueAct = Literal[
    "greeting",
    "smalltalk",
    "off_topic",
    "manuelita",
    "complaint",
    "correction",
    "minimal",
    "about_assistant",
    "closing",
    "thanks",
    "clarify",
]
DIALOGUE_ACTS: frozenset[str] = frozenset(DialogueAct.__args__)  # type: ignore[attr-defined]
Tier = Literal["social", "external", "manuelita"]
Strategy = Literal["accompany", "empathize", "decline", "answer", "clarify", "limit", "farewell"]
TOPIC_PATTERN = re.compile(r"^[a-záéíóúñü]+( [a-záéíóúñü]+){0,3}$")
TOPIC_MAX_CHARS = 40
Decision = Literal["approve", "edit", "reject"]


class RouteDecision(BaseModel):
    """Salida tipada de la puerta de decisión (FR-011, FR-015)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    route: Route
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str = Field(max_length=200, description="Motivo breve, en español.")
    decided_by: DecidedBy
    alternative: Route | None = None
    fallback_route: Literal["documental"] | None = None
    scope_reason: ScopeReason | None = None
    # Spec 019: tema ajeno saneado, emoción propuesta por el LLM y tipo de pedido no atendible.
    topic: str | None = None
    sentiment: Sentiment | None = None
    kind: UnattainableKind | None = None
    # Spec 020: acto de diálogo (lo proponen las reglas o el LLM del enrutador).
    act: DialogueAct | None = None

    @field_validator("act", mode="before")
    @classmethod
    def _known_act(cls, value: object) -> str | None:
        """Un acto fuera del vocabulario controlado se descarta sin error."""
        return value if isinstance(value, str) and value in DIALOGUE_ACTS else None

    @field_validator("topic", mode="before")
    @classmethod
    def _sanitize_topic(cls, value: object) -> str | None:
        """Saneado: ``[a-záéíóúñ ]``, como máximo 4 palabras y 40 caracteres; si no, ``None``."""
        if not isinstance(value, str):
            return None
        topic = " ".join(value.lower().split())
        if len(topic) > TOPIC_MAX_CHARS or TOPIC_PATTERN.fullmatch(topic) is None:
            return None
        return topic

    @model_validator(mode="after")
    def _scope_fields(self) -> RouteDecision:
        # ``topic`` solo acompaña a un tema ajeno; ``kind``, a un pedido no atendible.
        if self.topic is not None and self.scope_reason not in {"off_topic", "advice"}:
            object.__setattr__(self, "topic", None)
        if self.kind is not None and self.scope_reason != "unattainable":
            object.__setattr__(self, "kind", None)
        return self

    def effective(self, min_confidence: float) -> RouteDecision:
        """Ruta efectiva: con confianza baja se pide aclaración en vez de adivinar."""
        if self.route != "clarify" and self.confidence < min_confidence:
            return self.model_copy(update={"route": "clarify", "alternative": self.route})
        return self


class TurnMetrics(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latency_ms: int = Field(default=0, ge=0)
    model_calls: int = Field(default=0, ge=0)
    tool_calls: int = Field(default=0, ge=0)
    input_tokens: int = Field(default=0, ge=0)
    output_tokens: int = Field(default=0, ge=0)
    # Spec 022: consultas al gatekeeper Jev (no cuentan como model_calls, que mide el LLM).
    gate_calls: int = Field(default=0, ge=0)


class PendingAction(BaseModel):
    """Acción de escritura que espera una decisión humana (FR-017, SC-009)."""

    model_config = ConfigDict(extra="forbid")

    action_id: str = Field(min_length=1)
    tool: WriteTool
    args: dict[str, Any] = Field(default_factory=dict)
    proposed_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decision: Decision | None = None


class Turn(BaseModel):
    """Un turno visible de la conversación."""

    model_config = ConfigDict(extra="forbid")

    turn_id: int = Field(ge=1)
    question: str
    route: RouteDecision
    fragments: list[dict[str, Any]] = Field(default_factory=list)
    structured_rows: list[dict[str, Any]] = Field(default_factory=list)
    answer: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    fallback: bool = False
    metrics: TurnMetrics = Field(default_factory=TurnMetrics)
    # Spec 022: traza del gatekeeper Jev (estado, ruta, confianza, latencia, costo); sin texto.
    jev: dict[str, Any] | None = None
    # Spec 023: el mensaje llegó por dictado (origen, duración y tiempo de reconocimiento).
    input: dict[str, Any] | None = None
