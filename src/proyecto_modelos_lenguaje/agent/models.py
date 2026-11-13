"""Modelos de dominio del agente RAG (``specs/014-rag-agent-memory-router/data-model.md``)."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

Route = Literal["direct", "documental", "structured", "mixed", "out_of_scope", "clarify"]
DecidedBy = Literal["rules", "llm", "demo"]
WriteTool = Literal["forget_memory", "save_preference", "save_profile", "export_conversation"]
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
