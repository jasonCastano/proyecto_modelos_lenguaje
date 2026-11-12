"""Pydantic models for the public web API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

Mode = Literal["real", "demo"]
TaskKind = Literal["qa", "summary", "faq"]
AnswerStatus = Literal["ok", "fallback", "error"]
Authority = Literal["first_party", "third_party", "unknown"]
SectionStatus = Literal["done", "partial", "pending"]
DataStatus = Literal["complete", "incomplete", "unknown"]
RetrievalMode = Literal["semantic", "lexical", "hybrid", "none"]
FragmentOrigin = Literal["semantic", "lexical", "both"]
FragmentStatus = Literal["used", "omitted_threshold", "omitted_budget", "omitted_duplicate"]


class RequestModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class AskRequest(RequestModel):
    question: str = Field(min_length=1, max_length=500)
    mode: Mode = "real"

    @field_validator("question")
    @classmethod
    def _not_blank(cls, value: str) -> str:
        clean = value.strip()
        if not clean:
            raise ValueError("La pregunta no puede estar vacía.")
        return clean


class SummaryRequest(RequestModel):
    pack: Literal["8000", "32000"] = "8000"
    mode: Mode = "real"


class FaqRequest(RequestModel):
    limit: int = Field(default=12, ge=10, le=20)
    mode: Mode = "real"


class Citation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    title: str
    url: str
    section_path: list[str] = Field(default_factory=list)
    page: int | None = None
    time_start: float | None = None
    authority: Authority = "unknown"
    snippet: str | None = None


class ApiError(BaseModel):
    model_config = ConfigDict(extra="forbid")

    code: str
    message: str
    retryable: bool
    action: str


class RetrievalFragmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    unit_id: str
    title: str = ""
    url: str = ""
    score: float = Field(ge=0.0, le=1.0)
    semantic_score: float | None = Field(default=None, ge=0.0, le=1.0)
    lexical_score: float | None = Field(default=None, ge=0.0, le=1.0)
    origin: FragmentOrigin
    status: FragmentStatus
    reason: str | None = None
    anomalous: bool = False
    anomaly_reasons: list[str] = Field(default_factory=list)


class RetrievalTraceModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: RetrievalMode
    semantic_available: bool
    candidates: int = Field(ge=0)
    threshold: float = Field(ge=0.0, le=1.0)
    fragments: list[RetrievalFragmentModel] = Field(default_factory=list)
    used_unit_ids: list[str] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)
    elapsed_ms: float = Field(ge=0.0)

    @model_validator(mode="after")
    def _used_ids_match_fragments(self) -> RetrievalTraceModel:
        used = [fragment.unit_id for fragment in self.fragments if fragment.status == "used"]
        if used != list(self.used_unit_ids):
            raise ValueError("used_unit_ids debe coincidir con los fragmentos usados")
        if len(used) != len(set(used)):
            raise ValueError("used_unit_ids no puede contener duplicados")
        return self


class CitedAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query_id: str
    status: AnswerStatus
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    model: str
    provider: str
    prompt_version: str
    latency_ms: float
    input_tokens: int
    output_tokens: int
    cost_usd: float | None = None
    review_required: bool = False
    error: ApiError | None = None
    retrieval: RetrievalTraceModel | None = None


class FaqItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
    status: Literal["ready", "review", "missing_evidence"]
    model: str
    prompt_version: str


class FaqResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[FaqItem]


class HealthStatus(BaseModel):
    model_config = ConfigDict(extra="forbid")

    ok: bool
    provider: str
    model: str
    configured: bool
    demo_available: bool = True
    latency_ms: float | None = None
    detail: str | None = None


class CorpusMetric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    label: str
    value: float
    unit: str
    source: str
    status: DataStatus


class EvidenceLink(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    href: str
    kind: Literal["spec", "adr", "report", "code", "bitacora"]


class ShowcaseSection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: Literal[
        "problem",
        "data",
        "medallion",
        "prompts",
        "tasks",
        "retrieval",
        "agent",
        "safety",
        "app",
        "metrics",
        "limits",
    ]
    order: int
    title: str
    body: str
    status: SectionStatus
    metrics: list[CorpusMetric] = Field(default_factory=list)
    evidence: list[EvidenceLink] = Field(default_factory=list)


class ShowcaseResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    generated_at: str
    data_status: DataStatus
    sections: list[ShowcaseSection]
    metrics: list[CorpusMetric]


# ---------------------------------------------------------------- conversación (spec 014, US1)

Route = Literal["direct", "documental", "structured", "out_of_scope", "clarify"]
ChatStatus = Literal["answered", "fallback", "clarify", "pending_approval"]


class ChatRequest(RequestModel):
    """``POST /api/chat``. El mensaje se valida en el servicio para responder 400 con su código."""

    thread_id: str | None = Field(
        default=None,
        pattern=r"^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$",
    )
    user_id: str = Field(default="anon", pattern=r"^[A-Za-z0-9-]{1,64}$")
    message: str = Field(max_length=2000)
    variant: Literal["chain", "agent"] = "chain"
    mode: Mode = "real"


class RouteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    route: Route
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str
    decided_by: Literal["rules", "llm", "demo"]
    alternative: Route | None = None
    fallback_route: Literal["documental"] | None = None


class TurnMetricsModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    latency_ms: int = 0
    model_calls: int = 0
    tool_calls: int = 0
    input_tokens: int = 0
    output_tokens: int = 0


class ChatFragmentModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    unit_id: str
    title: str
    url: str
    score: float
    semantic_score: float | None = None
    lexical_score: float | None = None
    origin: FragmentOrigin
    status: FragmentStatus = "used"
    reason: str | None = None
    anomalous: bool = False
    anomaly_reasons: list[str] = Field(default_factory=list)


class StructuredRowModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    fact_id: str
    subject_label: str
    attribute: str
    value: str
    year: int | None = None
    unit_id: str
    citations: list[dict[str, str]] = Field(default_factory=list)


class ChatCitationModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    unit_id: str
    url: str
    title: str = ""
    fact_id: str | None = None


class TurnModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    turn_id: int = Field(ge=1)
    question: str
    route: RouteModel
    fragments: list[ChatFragmentModel] = Field(default_factory=list)
    structured_rows: list[StructuredRowModel] = Field(default_factory=list)
    answer: str = ""
    citations: list[ChatCitationModel] = Field(default_factory=list)
    sources: list[str] = Field(default_factory=list)
    fallback: bool = False
    metrics: TurnMetricsModel = Field(default_factory=TurnMetricsModel)


class AnomalyModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str | None = None
    unit_id: str | None = None
    reasons: list[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    turn: TurnModel
    status: ChatStatus
    pending_action: dict[str, object] | None = None
    anomalies: list[AnomalyModel] = Field(default_factory=list)


class ThreadView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    variant: Literal["chain", "agent"]
    turns: list[TurnModel] = Field(default_factory=list)
    summary: str = ""
    status: Literal["idle", "pending_approval"] = "idle"
    pending_action: dict[str, object] | None = None
    actions: list[dict[str, object]] = Field(default_factory=list)


class MemoryItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Literal["response_format", "topics_of_interest", "language"]
    value: str = Field(max_length=200)
    created_at: str
    expires_at: str


class MemoryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    items: list[MemoryItemModel] = Field(default_factory=list)


class ResumeRequest(RequestModel):
    """``POST /api/threads/{thread_id}/resume``: decisión humana sobre la acción pendiente."""

    action_id: str = Field(min_length=1, max_length=128)
    decision: Literal["approve", "edit", "reject"]
    args: dict[str, object] | None = None
