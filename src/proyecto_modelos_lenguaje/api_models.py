"""Pydantic models for the public web API."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

Mode = Literal["real", "demo"]
TaskKind = Literal["qa", "summary", "faq"]
AnswerStatus = Literal["ok", "fallback", "error"]
Authority = Literal["first_party", "third_party", "unknown"]
SectionStatus = Literal["done", "partial", "pending"]
DataStatus = Literal["complete", "incomplete", "unknown"]


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

    id: Literal["problem", "data", "medallion", "prompts", "tasks", "app", "metrics", "limits"]
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
