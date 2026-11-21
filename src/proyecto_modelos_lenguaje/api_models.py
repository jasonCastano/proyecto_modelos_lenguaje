"""Pydantic models for the public web API."""

from __future__ import annotations

from typing import Any, Literal

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
    neutralized_sentences: int = Field(default=0, ge=0)


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
    adversarial_corpus: bool = False  # spec 015: el servidor usa el corpus de prueba del blindaje
    voice_available: bool = False  # spec 016: el motor de voz (Phonon) está listo o cargando


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

Route = Literal["direct", "documental", "structured", "mixed", "out_of_scope", "clarify"]
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
# Spec 019: emoción del visitante, pedidos no atendibles y registro del contacto (CRM).
Sentiment = Literal["neutral", "satisfied", "confused", "frustrated", "angry", "distressed"]
UnattainableKind = Literal["pricing", "commitment", "human"]
# Spec 020: acto de diálogo del turno (etiqueta controlada).
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
ContactCategory = Literal[
    "manuelita", "off_topic", "advice", "complaint", "unattainable", "crisis", "conduct", "other"
]
ContactStatus = Literal[
    "resolved", "out_of_scope", "not_attainable", "needs_clarification", "referred", "no_evidence"
]
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
    scope_reason: ScopeReason | None = None
    topic: str | None = Field(default=None, max_length=40)
    sentiment: Sentiment | None = None
    kind: UnattainableKind | None = None
    act: DialogueAct | None = None  # spec 020


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
    neutralized_sentences: int = Field(default=0, ge=0)


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


class ClientInfo(BaseModel):
    """Cliente del hilo tras el turno (spec 018). Nunca incluye el correo en claro."""

    model_config = ConfigDict(extra="forbid")

    user_id: str
    recognized: bool = False
    name: str | None = None
    reset: bool = False
    masked_email: str | None = None


class WelcomeCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: str
    unit_id: str
    url: str
    title: str


class WelcomeResponse(BaseModel):
    """``GET /api/welcome``: presentación de Valer-IA Caña (sin modelo de lenguaje)."""

    model_config = ConfigDict(extra="forbid")

    assistant: str
    version: str
    text: str
    citations: list[WelcomeCitation] = Field(default_factory=list)


class ContactRequestModel(BaseModel):
    """Una solicitud del contacto: categoría, tema controlado y estado (spec 019)."""

    model_config = ConfigDict(extra="forbid")

    turn: int = Field(ge=1)
    category: ContactCategory
    topic: str = Field(max_length=40)
    status: ContactStatus


class ContactTurnModel(BaseModel):
    """Etiquetas de un turno (spec 020): acto, si hubo puente y qué hizo la revisión."""

    model_config = ConfigDict(extra="forbid")

    act: DialogueAct
    bridged: bool = False
    reviewed: Literal["show", "retry", "fallback"] = "show"


class ContactRecordModel(BaseModel):
    """Registro del contacto (CRM) sin datos personales; solo lo muestra la vista técnica."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    opened_at: str
    updated_at: str
    turns: int = Field(ge=0)
    requests: list[ContactRequestModel] = Field(default_factory=list)
    sentiments: list[Sentiment] = Field(default_factory=list)
    motive: list[str] = Field(default_factory=list, max_length=5)
    resolved: bool = True
    hostile_turns: int = Field(default=0, ge=0)
    crisis: bool = False
    # Spec 020: secuencia de actos del hilo (como máximo 50; ``turns`` ya es el contador).
    acts: list[ContactTurnModel] = Field(default_factory=list, max_length=50)


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    turn: TurnModel
    status: ChatStatus
    pending_action: dict[str, object] | None = None
    anomalies: list[AnomalyModel] = Field(default_factory=list)
    # spec 018: cliente activo (reconocimiento o reinicio) y avisos del turno
    client: ClientInfo | None = None
    notices: list[str] = Field(default_factory=list)
    contact: ContactRecordModel | None = None  # spec 019


class ThreadView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str
    variant: Literal["chain", "agent"]
    turns: list[TurnModel] = Field(default_factory=list)
    summary: str = ""
    status: Literal["idle", "pending_approval"] = "idle"
    pending_action: dict[str, object] | None = None
    actions: list[dict[str, object]] = Field(default_factory=list)
    contact: ContactRecordModel | None = None  # spec 019


class MemoryItemModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: Literal["response_format", "topics_of_interest", "language"]
    value: str = Field(max_length=200)
    created_at: str
    expires_at: str


class ProfileItemModel(BaseModel):
    """Dato del perfil del usuario en el Store (memoria de largo plazo)."""

    model_config = ConfigDict(extra="forbid")

    key: Literal["name", "workplace", "role", "city"]
    value: str = Field(max_length=80)
    created_at: str


class MemoryView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    user_id: str
    items: list[MemoryItemModel] = Field(default_factory=list)
    profile: list[ProfileItemModel] = Field(default_factory=list)


class ResumeRequest(RequestModel):
    """``POST /api/threads/{thread_id}/resume``: decisión humana sobre la acción pendiente."""

    action_id: str = Field(min_length=1, max_length=128)
    decision: Literal["approve", "edit", "reject"]
    args: dict[str, object] | None = None


class ObservabilityStatus(BaseModel):
    """Estado de las trazas, del log estructurado y de la búsqueda vectorial (sin secretos)."""

    langsmith: bool
    project: str | None = None
    structured_log: str | None = None
    vector_store: dict[str, str] = Field(default_factory=dict)
    adversarial_corpus: bool = False
    # spec 016: estado resumido de la voz del agente
    voice: dict[str, Any] = Field(default_factory=dict)


class PendingForget(BaseModel):
    """Respuesta 202 de ``DELETE /api/memory/{user_id}``: el olvido espera aprobación."""

    status: str
    thread_id: str
    pending_action: dict[str, Any] | None = None


class TtsRequest(BaseModel):
    """Una oración de la respuesta del agente para leer en voz alta (spec 016)."""

    model_config = ConfigDict(extra="forbid")

    text: str = Field(min_length=1)
    voice: str | None = None
    thread_id: str | None = None
    segment: int | None = Field(default=None, ge=0)


class VoiceStatus(BaseModel):
    """Estado del motor de voz, sin token ni rutas (spec 016, contracts/tts-api.md)."""

    model_config = ConfigDict(extra="forbid")

    available: bool
    state: Literal["disabled", "loading", "ready", "unavailable"]
    engine: str
    model: str
    voice: str
    language: str
    sample_rate: int | None = None
    license: str
    detail: str | None = None
