"""Resumen, FAQ y Q&A del Módulo 1 sobre la capa de oro.

Expone una interfaz de biblioteca (``answer_question``, ``summarize_corpus``, ``generate_faq``) y un
CLI de validación. No usa embeddings ni servicios externos: la recuperación es léxica y el modelo se
inyecta, de modo que las pruebas pueden ejecutarse con un modelo falso.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import time
import tomllib
from collections.abc import Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage, HumanMessage, SystemMessage
from langchain_core.outputs import ChatGeneration, ChatResult

from .config import PROJECT_ROOT
from .llm import LLMConfigError, load_llm_config
from .retrieval import (
    CONTROL_PATTERN,
    ContextPack,
    EntityIndex,
    EvidenceSelection,
    FAQSeed,
    GoldUnit,
    RetrievalError,
    SelectedUnit,
    build_context,
    load_context_pack,
    load_entity_index,
    load_faq_seeds,
    load_gold_units,
    normalize_question,
    select_evidence,
)
from .silver.cleaning import estimate_tokens

ChatModel = BaseChatModel

SCHEMA_VERSION = "1.0"
DEFAULT_CONFIG = "config/tasks.toml"
DEFAULT_GOLD_DIR = "data/gold"
PROMPT_DIR = "prompts"
GOLD_DIR_ENV = "PML_GOLD_DIR"
FAKE_MODEL_NAME = "scripted-fake"
FALLBACK_ANSWER = "No hay evidencia suficiente en el corpus para responder."
SIGNS_ERROR_ANSWER = "No se pudo generar una respuesta con citas válidas."
STRICT_REMINDER = (
    "Recuerda: cada afirmación debe terminar con la etiqueta de la unidad que la sostiene, por "
    "ejemplo [U1]. No respondas sin citas y no inventes etiquetas fuera del contexto."
)

PROMPT_VERSION_PATTERN = re.compile(r"<!--\s*prompt_version:\s*([0-9][\w.\-]*)\s*-->")
PLACEHOLDER_PATTERN = re.compile(r"\{\{([a-z_]+)\}\}")
SECTION_PATTERN = re.compile(r"^##\s+(.+)$", re.MULTILINE)
CITATION_PATTERN = re.compile(r"\[(U\d+)\]")
UNIT_TAG_PATTERN = re.compile(r'<unit id="(U\d+)">')
HEADING_PATTERN = re.compile(r"^#\s+(.+)$", re.MULTILINE)

SECTION_ALIASES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("fallback", ("sin evidencia", "fallback", "sin contexto")),
    ("rol", ("rol", "papel", "perfil")),
    ("tarea", ("tarea", "objetivo", "encargo")),
    ("contexto", ("contexto",)),
    ("reglas", ("regla",)),
    ("formato", ("formato", "cita")),
)
REQUIRED_SECTIONS = ("rol", "tarea", "contexto", "reglas", "formato", "fallback")

USAGE_ERROR_CODES = frozenset({"invalid_config", "empty_question", "question_too_long"})
VALID_TASKS = ("summary", "faq", "qa")
VALID_PACKS = ("8000", "32000")


class TaskError(Exception):
    """Controlled task error with an actionable code (see ``data-model.md``)."""

    def __init__(
        self,
        code: str,
        message: str,
        *,
        task: str,
        review_required: bool = False,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.task = task
        self.review_required = review_required

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "task": self.task,
            "review_required": self.review_required,
        }


@dataclass(frozen=True, slots=True)
class TaskConfig:
    """Validated configuration from ``config/tasks.toml``."""

    qa_top_k: int = 8
    qa_token_budget: int = 6000
    qa_min_score: float = 0.0
    summary_pack: str = "8000"
    summary_min_citations: int = 8
    faq_limit: int = 12
    faq_top_k: int = 5
    faq_min_citations: int = 1
    question_max_chars: int = 500

    def to_dict(self) -> dict[str, Any]:
        return {
            "qa_top_k": self.qa_top_k,
            "qa_token_budget": self.qa_token_budget,
            "qa_min_score": self.qa_min_score,
            "summary_pack": self.summary_pack,
            "summary_min_citations": self.summary_min_citations,
            "faq_limit": self.faq_limit,
            "faq_top_k": self.faq_top_k,
            "faq_min_citations": self.faq_min_citations,
            "question_max_chars": self.question_max_chars,
        }


@dataclass(frozen=True, slots=True)
class PromptTemplate:
    """Versioned Markdown prompt with its six mandatory sections and SHA-256 hash."""

    task: str
    version: str
    path: str
    text: str
    sha256: str
    sections: dict[str, str] = field(default_factory=dict)

    def render(self, **values: object) -> str:
        missing = sorted(set(PLACEHOLDER_PATTERN.findall(self.text)) - set(values))
        if missing:
            raise TaskError(
                "invalid_config",
                f"El prompt {self.task} requiere valores para {missing}.",
                task=self.task,
            )
        rendered = self.text
        for key, value in values.items():
            rendered = rendered.replace("{{" + key + "}}", str(value))
        leftover = PLACEHOLDER_PATTERN.findall(rendered)
        if leftover:
            raise TaskError(
                "invalid_config",
                f"El prompt {self.task} conserva marcadores sin resolver: {sorted(set(leftover))}.",
                task=self.task,
            )
        return rendered

    def to_dict(self) -> dict[str, Any]:
        return {
            "task": self.task,
            "version": self.version,
            "path": self.path,
            "sha256": self.sha256,
            "sections": dict(self.sections),
        }


@dataclass(frozen=True, slots=True)
class Citation:
    """Resolved citation for a gold unit."""

    label: str
    unit_id: str
    title: str
    url: str
    section_path: tuple[str, ...]
    page_start: int | None
    page_end: int | None
    time_start: float | None
    time_end: float | None
    authority: str
    citation: str

    @classmethod
    def from_unit(cls, label: str, unit: GoldUnit) -> Citation:
        location = f"sección: {' > '.join(unit.section_path)}"
        if unit.page_start is not None:
            location += f", p. {unit.page_start}"
        if unit.time_start is not None:
            location += f", {int(unit.time_start)} s"
        return cls(
            label=label,
            unit_id=unit.unit_id,
            title=unit.title,
            url=unit.url,
            section_path=unit.section_path,
            page_start=unit.page_start,
            page_end=unit.page_end,
            time_start=unit.time_start,
            time_end=unit.time_end,
            authority=unit.authority,
            citation=f"{unit.title} — {unit.url} ({location})",
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "unit_id": self.unit_id,
            "title": self.title,
            "url": self.url,
            "section_path": list(self.section_path),
            "page_start": self.page_start,
            "page_end": self.page_end,
            "time_start": self.time_start,
            "time_end": self.time_end,
            "authority": self.authority,
            "citation": self.citation,
        }


@dataclass(frozen=True, slots=True)
class TaskResult:
    """Result of the summary, FAQ or Q&A task."""

    task: str
    status: str
    answer: str
    citations: tuple[Citation, ...] = ()
    used_unit_ids: tuple[str, ...] = ()
    omitted_unit_ids: tuple[str, ...] = ()
    prompt_version: str = "1.0"
    prompt_sha256: str = "0" * 64
    model: str = "unknown"
    latency_seconds: float = 0.0
    input_tokens: int = 0
    output_tokens: int = 0
    fallback: bool = False
    review_required: bool = False
    error: str | None = None
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.task not in VALID_TASKS:
            raise ValueError(f"tarea inválida: {self.task}")
        if self.status == "fallback" and (not self.fallback or self.citations):
            raise ValueError("status=fallback exige fallback=True y citations vacío")
        if self.status == "ok" and (self.fallback or not self.citations):
            raise ValueError("status=ok exige fallback=False y al menos una cita")
        if self.status == "error" and not self.error:
            raise ValueError("status=error exige un código de error")
        used = set(self.used_unit_ids)
        for citation in self.citations:
            if citation.unit_id not in used:
                raise ValueError(f"cita fuera del contexto: {citation.unit_id}")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "task": self.task,
            "status": self.status,
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "used_unit_ids": list(self.used_unit_ids),
            "omitted_unit_ids": list(self.omitted_unit_ids),
            "prompt_version": self.prompt_version,
            "prompt_sha256": self.prompt_sha256,
            "model": self.model,
            "latency_seconds": self.latency_seconds,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "fallback": self.fallback,
            "review_required": self.review_required,
            "error": self.error,
        }


@dataclass(frozen=True, slots=True)
class FAQItem:
    """One entry of the generated FAQ."""

    question: str
    answer: str
    citations: tuple[Citation, ...] = ()
    topic_id: str = ""
    seed_id: str | None = None
    coverage_item_id: str | None = None
    status: str = "ready"
    prompt_version: str = "1.0"
    model: str = "unknown"
    schema_version: str = SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.status == "ready" and not self.citations:
            raise ValueError("status=ready exige al menos una cita")
        if self.status == "missing_evidence" and self.citations:
            raise ValueError("status=missing_evidence exige citations vacío")
        if len(self.question.strip()) < 3:
            raise ValueError("la pregunta debe tener al menos 3 caracteres")

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "seed_id": self.seed_id,
            "question": self.question,
            "answer": self.answer,
            "citations": [citation.to_dict() for citation in self.citations],
            "topic_id": self.topic_id,
            "coverage_item_id": self.coverage_item_id,
            "status": self.status,
            "prompt_version": self.prompt_version,
            "model": self.model,
        }


def _as_int(value: Any, *, field_name: str, minimum: int, maximum: int, task: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise TaskError("invalid_config", f"{field_name} debe ser un entero.", task=task)
    if not minimum <= value <= maximum:
        raise TaskError(
            "invalid_config",
            f"{field_name} debe estar entre {minimum} y {maximum}.",
            task=task,
        )
    return value


def _as_float(value: Any, *, field_name: str, minimum: float, task: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise TaskError("invalid_config", f"{field_name} debe ser un número.", task=task)
    number = float(value)
    if number < minimum:
        raise TaskError(
            "invalid_config", f"{field_name} debe ser mayor o igual a {minimum}.", task=task
        )
    return number


def _as_str(value: Any, *, field_name: str, task: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise TaskError("invalid_config", f"{field_name} debe ser un texto no vacío.", task=task)
    return value.strip()


def _table(document: dict[str, Any], key: str, *, task: str) -> dict[str, Any]:
    value = document.get(key)
    if not isinstance(value, dict):
        raise TaskError("invalid_config", f"Falta la tabla [{key}] en la configuración.", task=task)
    return value


def load_task_config(
    path: str | Path = DEFAULT_CONFIG,
    *,
    project_root: Path | None = None,
) -> TaskConfig:
    """Load and validate ``config/tasks.toml``."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = root / config_path
    if not config_path.is_file():
        raise TaskError(
            "invalid_config",
            f"No existe la configuración de tareas: {_display_path(config_path, root)}.",
            task="config",
        )
    try:
        with config_path.open("rb") as handle:
            document = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise TaskError("invalid_config", f"TOML inválido: {exc}", task="config") from exc

    qa = _table(document, "qa", task="config")
    summary = _table(document, "summary", task="config")
    faq = _table(document, "faq", task="config")

    pack = _as_str(summary.get("pack"), field_name="summary.pack", task="config")
    if pack not in VALID_PACKS:
        raise TaskError("invalid_config", "summary.pack debe ser '8000' o '32000'.", task="config")

    return TaskConfig(
        qa_top_k=_as_int(
            qa.get("top_k"), field_name="qa.top_k", minimum=1, maximum=20, task="config"
        ),
        qa_token_budget=_as_int(
            qa.get("token_budget"),
            field_name="qa.token_budget",
            minimum=1000,
            maximum=30000,
            task="config",
        ),
        qa_min_score=_as_float(
            qa.get("min_score"), field_name="qa.min_score", minimum=0.0, task="config"
        ),
        summary_pack=pack,
        summary_min_citations=_as_int(
            summary.get("min_citations"),
            field_name="summary.min_citations",
            minimum=1,
            maximum=30,
            task="config",
        ),
        faq_limit=_as_int(
            faq.get("limit"), field_name="faq.limit", minimum=10, maximum=20, task="config"
        ),
        faq_top_k=_as_int(
            faq.get("top_k"), field_name="faq.top_k", minimum=1, maximum=10, task="config"
        ),
        faq_min_citations=_as_int(
            faq.get("min_citations"),
            field_name="faq.min_citations",
            minimum=1,
            maximum=10,
            task="config",
        ),
        question_max_chars=_as_int(
            faq.get("question_max_chars"),
            field_name="faq.question_max_chars",
            minimum=20,
            maximum=2000,
            task="config",
        ),
    )


def _section_key(heading: str) -> str | None:
    normalized = heading.strip().lower()
    for key, aliases in SECTION_ALIASES:
        if any(alias in normalized for alias in aliases):
            return key
    return None


def _parse_sections(text: str, *, task: str) -> dict[str, str]:
    matches = list(SECTION_PATTERN.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        start = match.end()
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        key = _section_key(match.group(1))
        if key is None:
            continue
        sections[key] = text[start:end].strip()
    missing = [section for section in REQUIRED_SECTIONS if not sections.get(section)]
    if missing:
        raise TaskError(
            "invalid_config",
            f"El prompt {task} no define las secciones obligatorias: {missing}.",
            task=task,
        )
    return sections


def load_prompt(
    task: str,
    *,
    path: str | Path | None = None,
    project_root: Path | None = None,
) -> PromptTemplate:
    """Load and validate one of the three versioned prompts."""
    if task not in VALID_TASKS:
        raise TaskError("invalid_config", f"Tarea desconocida: {task}.", task="config")
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    prompt_path = Path(path) if path is not None else Path(PROMPT_DIR) / f"{task}.md"
    if not prompt_path.is_absolute():
        prompt_path = root / prompt_path
    if not prompt_path.is_file():
        raise TaskError(
            "invalid_config",
            f"No existe el prompt {_display_path(prompt_path, root)}.",
            task=task,
        )
    text = prompt_path.read_text(encoding="utf-8")
    version_match = PROMPT_VERSION_PATTERN.search(text)
    if version_match is None:
        raise TaskError(
            "invalid_config",
            f"El prompt {task} no declara prompt_version.",
            task=task,
        )
    heading = HEADING_PATTERN.search(text)
    if heading is None:
        raise TaskError("invalid_config", f"El prompt {task} no tiene título.", task=task)
    return PromptTemplate(
        task=task,
        version=version_match.group(1),
        path=_display_path(prompt_path, root),
        text=text,
        sha256=hashlib.sha256(text.encode("utf-8")).hexdigest(),
        sections=_parse_sections(text, task=task),
    )


def _display_path(path: Path, root: Path) -> str:
    try:
        return path.resolve().relative_to(root.resolve()).as_posix()
    except ValueError:
        return path.name


def _resolve_gold_dir(gold_dir: str | Path | None, root: Path) -> Path:
    raw = gold_dir if gold_dir is not None else os.getenv(GOLD_DIR_ENV, DEFAULT_GOLD_DIR)
    path = Path(raw)
    if not path.is_absolute():
        path = root / path
    return path


def _model_name(model: BaseChatModel, default: str = "") -> str:
    for attribute in ("model", "model_name"):
        value = getattr(model, attribute, None)
        if isinstance(value, str) and value.strip():
            return value.strip()
    identifier = getattr(model, "_llm_type", None)
    if isinstance(identifier, str) and identifier and identifier != "base_chat_model":
        return identifier
    return default or type(model).__name__


class ScriptedTaskModel(BaseChatModel):
    """Deterministic offline model that cites the units it receives in the context."""

    task: str = "qa"
    citation_limit: int = 2

    @property
    def _llm_type(self) -> str:
        return FAKE_MODEL_NAME

    @property
    def _identifying_params(self) -> dict[str, Any]:
        return {"task": self.task, "citation_limit": self.citation_limit}

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        text = "\n".join(str(message.content) for message in messages)
        labels = list(dict.fromkeys(UNIT_TAG_PATTERN.findall(text)))
        answer = _scripted_answer(self.task, labels, self.citation_limit)
        return ChatResult(generations=[ChatGeneration(message=AIMessage(content=answer))])


def _scripted_answer(task: str, labels: Sequence[str], limit: int) -> str:
    if not labels:
        return FALLBACK_ANSWER
    if task == "summary":
        chosen = list(labels[:10])
        blocks = [
            f"**Bloque {index}**\n\nSíntesis de la evidencia disponible [{label}]."
            for index, label in enumerate(chosen, start=1)
        ]
        return "\n\n".join(blocks)
    chosen = " ".join(f"[{label}]" for label in labels[: max(1, limit)])
    return f"Según el corpus de oro, la respuesta se sostiene en las fuentes citadas {chosen}."


def build_scripted_model(task: str) -> ChatModel:
    """Return the deterministic fake model used by ``--fake`` and offline tests."""
    limits = {"qa": 2, "summary": 10, "faq": 1}
    return ScriptedTaskModel(task=task, citation_limit=limits.get(task, 2))


def _invoke(model: ChatModel, system_text: str, user_text: str, *, task: str) -> str:
    messages = [SystemMessage(content=system_text), HumanMessage(content=user_text)]
    try:
        response = model.invoke(messages)
    except Exception as exc:
        name = type(exc).__name__.lower()
        code = "model_timeout" if "timeout" in name else "model_error"
        raise TaskError(code, f"El modelo no respondió: {exc}", task=task) from exc
    content = getattr(response, "content", "")
    if isinstance(content, list):
        content = "".join(
            str(part.get("text", "")) if isinstance(part, dict) else str(part) for part in content
        )
    answer = str(content).strip()
    if not answer:
        metadata = getattr(response, "response_metadata", {}) or {}
        if metadata.get("done_reason") == "length":
            raise TaskError(
                "model_error",
                "El modelo agotó max_output_tokens antes de responder; usa un modelo sin "
                "razonamiento o aumenta llm.max_output_tokens en config/llm.toml.",
                task=task,
            )
        raise TaskError("model_error", "El modelo devolvió una respuesta vacía.", task=task)
    return answer


def _parse_citations(answer: str, selection: EvidenceSelection) -> tuple[list[Citation], list[str]]:
    label_map = selection.label_map()
    citations: list[Citation] = []
    invalid: list[str] = []
    seen: set[str] = set()
    for label in CITATION_PATTERN.findall(answer):
        if label in seen:
            continue
        unit = label_map.get(label)
        if unit is None:
            invalid.append(label)
            continue
        seen.add(label)
        citations.append(Citation.from_unit(label, unit))
    return citations, invalid


def _generate_with_citations(
    model: ChatModel,
    system_text: str,
    user_text: str,
    selection: EvidenceSelection,
    *,
    task: str,
    min_citations: int,
) -> tuple[str, list[Citation], list[str]]:
    answer = ""
    citations: list[Citation] = []
    invalid: list[str] = []
    for attempt in range(2):
        instruction = system_text if attempt == 0 else f"{system_text}\n\n{STRICT_REMINDER}"
        answer = _invoke(model, instruction, user_text, task=task)
        citations, invalid = _parse_citations(answer, selection)
        if len(citations) >= max(1, min_citations):
            break
    return answer, citations, invalid


def _validate_question(question: str, config: TaskConfig) -> str:
    text = question.strip()
    if not text or CONTROL_PATTERN.search(question):
        raise TaskError(
            "empty_question",
            "La pregunta no puede estar vacía ni contener caracteres de control.",
            task="qa",
        )
    if len(text) > config.question_max_chars:
        raise TaskError(
            "question_too_long",
            f"La pregunta supera {config.question_max_chars} caracteres.",
            task="qa",
        )
    return text


def _load_units(gold_dir: Path, task: str) -> tuple[GoldUnit, ...]:
    try:
        return load_gold_units(gold_dir)
    except RetrievalError as exc:
        raise TaskError("invalid_config", str(exc), task=task) from exc


def _fallback_result(
    task: str,
    prompt: PromptTemplate,
    model: ChatModel,
    *,
    omitted: Sequence[str] = (),
    started: float | None = None,
) -> TaskResult:
    return TaskResult(
        task=task,
        status="fallback",
        answer=FALLBACK_ANSWER,
        citations=(),
        used_unit_ids=(),
        omitted_unit_ids=tuple(omitted),
        prompt_version=prompt.version,
        prompt_sha256=prompt.sha256,
        model=_model_name(model),
        latency_seconds=0.0 if started is None else round(time.perf_counter() - started, 3),
        input_tokens=0,
        output_tokens=0,
        fallback=True,
        review_required=False,
        error=None,
    )


def answer_question(
    question: str,
    *,
    model: ChatModel,
    config: TaskConfig | None = None,
    prompt: PromptTemplate | None = None,
    units: Sequence[GoldUnit] | None = None,
    entity_index: EntityIndex | None = None,
    gold_dir: str | Path | None = None,
    project_root: Path | None = None,
) -> TaskResult:
    """Answer one question with gold evidence, verifiable citations and explicit fallback."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    settings = config or load_task_config(project_root=root)
    template = prompt or load_prompt("qa", project_root=root)
    text = _validate_question(question, settings)
    directory = _resolve_gold_dir(gold_dir, root)
    corpus = tuple(units) if units is not None else _load_units(directory, "qa")
    if entity_index is None:
        try:
            entity_index = load_entity_index(directory)
        except RetrievalError:
            entity_index = EntityIndex()
    selection = select_evidence(
        text,
        corpus,
        entity_index=entity_index,
        top_k=settings.qa_top_k,
        token_budget=settings.qa_token_budget,
        min_score=settings.qa_min_score,
    )
    started = time.perf_counter()
    if not selection.selected:
        return _fallback_result("qa", template, model, omitted=(), started=started)

    context = build_context(selection.selected)
    system_text = template.render(
        context=context,
        question=text,
        language="español",
        min_citations=1,
    )
    answer, citations, invalid = _generate_with_citations(
        model, system_text, text, selection, task="qa", min_citations=1
    )
    latency = round(time.perf_counter() - started, 3)
    input_tokens = estimate_tokens(system_text) + estimate_tokens(text)
    output_tokens = estimate_tokens(answer)

    if not citations:
        return TaskResult(
            task="qa",
            status="error",
            answer=SIGNS_ERROR_ANSWER,
            citations=(),
            used_unit_ids=selection.used_unit_ids,
            omitted_unit_ids=selection.omitted_unit_ids,
            prompt_version=template.version,
            prompt_sha256=template.sha256,
            model=_model_name(model),
            latency_seconds=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            fallback=False,
            review_required=True,
            error="missing_citations",
        )

    return TaskResult(
        task="qa",
        status="review" if invalid else "ok",
        answer=answer,
        citations=tuple(citations),
        used_unit_ids=selection.used_unit_ids,
        omitted_unit_ids=selection.omitted_unit_ids,
        prompt_version=template.version,
        prompt_sha256=template.sha256,
        model=_model_name(model),
        latency_seconds=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        fallback=False,
        review_required=bool(invalid),
        error=None,
    )


def _pack_blocks(pack: ContextPack, units_by_id: dict[str, GoldUnit]) -> list[SelectedUnit]:
    selected: list[SelectedUnit] = []
    for block in pack.blocks:
        unit = units_by_id.get(block.unit_id)
        if unit is None:
            continue
        selected.append(
            SelectedUnit(
                label=f"U{len(selected) + 1}",
                unit=unit,
                score=0.0,
                reason=f"paquete {pack.pack_id}",
            )
        )
    return selected


def summarize_corpus(
    *,
    pack: str | None = None,
    model: ChatModel,
    config: TaskConfig | None = None,
    prompt: PromptTemplate | None = None,
    units: Sequence[GoldUnit] | None = None,
    gold_dir: str | Path | None = None,
    context_window: int | None = None,
    project_root: Path | None = None,
) -> TaskResult:
    """Summarize the gold corpus with 8–12 citations, declaring the pack actually used."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    settings = config or load_task_config(project_root=root)
    template = prompt or load_prompt("summary", project_root=root)
    resolved_pack = pack or settings.summary_pack
    if resolved_pack not in VALID_PACKS:
        raise TaskError("invalid_config", "El paquete debe ser '8000' o '32000'.", task="summary")
    declarations: list[str] = []
    if resolved_pack == "32000" and (context_window is None or context_window < 32000):
        resolved_pack = "8000"
        declarations.append(
            "El modelo no declara una ventana de 32.000 tokens; se usó el paquete de 8.000."
        )

    directory = _resolve_gold_dir(gold_dir, root)
    try:
        loaded_pack = load_context_pack(directory, resolved_pack)
    except RetrievalError as exc:
        raise TaskError("invalid_config", str(exc), task="summary") from exc
    corpus = tuple(units) if units is not None else _load_units(directory, "summary")
    started = time.perf_counter()
    if loaded_pack.is_empty:
        return _fallback_result("summary", template, model, started=started)

    units_by_id = {unit.unit_id: unit for unit in corpus}
    selected = _pack_blocks(loaded_pack, units_by_id)
    if not selected:
        return _fallback_result("summary", template, model, started=started)

    min_citations = settings.summary_min_citations
    max_citations = min(min_citations + 4, 12)
    selection = EvidenceSelection(
        query="",
        topic_id="",
        entities=(),
        selected=tuple(selected),
        omitted_unit_ids=(),
        tokens=loaded_pack.tokens,
        budget_tokens=loaded_pack.budget_tokens,
    )
    context = build_context(selected)
    system_text = template.render(
        context=context,
        pack_id=loaded_pack.pack_id,
        min_citations=min_citations,
        max_citations=max_citations,
    )
    answer, citations, invalid = _generate_with_citations(
        model,
        system_text,
        f"Genera el resumen del paquete {loaded_pack.pack_id}.",
        selection,
        task="summary",
        min_citations=min_citations,
    )
    latency = round(time.perf_counter() - started, 3)
    input_tokens = estimate_tokens(system_text)
    output_tokens = estimate_tokens(answer)
    header = "\n".join([f"**Paquete de contexto:** {resolved_pack} tokens", *declarations])
    answer = f"{header}\n\n{answer}"

    if len(citations) < min_citations:
        return TaskResult(
            task="summary",
            status="error",
            answer=SIGNS_ERROR_ANSWER,
            citations=(),
            used_unit_ids=selection.used_unit_ids,
            omitted_unit_ids=(),
            prompt_version=template.version,
            prompt_sha256=template.sha256,
            model=_model_name(model),
            latency_seconds=latency,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            fallback=False,
            review_required=True,
            error="missing_citations",
        )

    trimmed = tuple(citations[:max_citations])
    return TaskResult(
        task="summary",
        status="review" if invalid else "ok",
        answer=answer,
        citations=trimmed,
        used_unit_ids=selection.used_unit_ids,
        omitted_unit_ids=(),
        prompt_version=template.version,
        prompt_sha256=template.sha256,
        model=_model_name(model),
        latency_seconds=latency,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        fallback=False,
        review_required=bool(invalid),
        error=None,
    )


def _seed_selection(
    seed: FAQSeed,
    units_by_id: dict[str, GoldUnit],
    *,
    top_k: int,
    token_budget: int,
) -> list[SelectedUnit]:
    selected: list[SelectedUnit] = []
    total = 0
    for unit_id in seed.evidence_unit_ids:
        if len(selected) >= top_k:
            break
        unit = units_by_id.get(unit_id)
        if unit is None or not unit.is_citable:
            continue
        tokens = estimate_tokens(unit.text)
        if total + tokens > token_budget:
            continue
        total += tokens
        selected.append(
            SelectedUnit(
                label=f"U{len(selected) + 1}",
                unit=unit,
                score=0.0,
                reason=f"semilla {seed.seed_id}",
            )
        )
    return selected


def generate_faq(
    *,
    limit: int | None = None,
    model: ChatModel,
    config: TaskConfig | None = None,
    prompt: PromptTemplate | None = None,
    units: Sequence[GoldUnit] | None = None,
    seeds: Sequence[FAQSeed] | None = None,
    gold_dir: str | Path | None = None,
    project_root: Path | None = None,
) -> tuple[FAQItem, ...]:
    """Generate 10–20 FAQ entries from the gold seeds, one model call per seed."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    settings = config or load_task_config(project_root=root)
    template = prompt or load_prompt("faq", project_root=root)
    requested = settings.faq_limit if limit is None else limit
    if not 10 <= requested <= 20:
        raise TaskError("invalid_config", "El límite de FAQ debe estar entre 10 y 20.", task="faq")

    directory = _resolve_gold_dir(gold_dir, root)
    if seeds is None:
        try:
            loaded_seeds = load_faq_seeds(directory)
        except RetrievalError as exc:
            raise TaskError("invalid_config", str(exc), task="faq") from exc
    else:
        loaded_seeds = tuple(seeds)
    corpus = tuple(units) if units is not None else _load_units(directory, "faq")

    units_by_id = {unit.unit_id: unit for unit in corpus}
    deduplicated: list[FAQSeed] = []
    seen_questions: set[str] = set()
    for seed in loaded_seeds:
        key = normalize_question(seed.question)
        if not key or key in seen_questions:
            continue
        seen_questions.add(key)
        deduplicated.append(seed)
    chosen = deduplicated[:requested]
    if not chosen:
        raise TaskError(
            "invalid_config", "No hay semillas de FAQ utilizables en el corpus.", task="faq"
        )

    items: list[FAQItem] = []
    for seed in chosen:
        question = seed.question.strip()[: settings.question_max_chars]
        selected = _seed_selection(
            seed,
            units_by_id,
            top_k=settings.faq_top_k,
            token_budget=settings.qa_token_budget,
        )
        if not selected:
            items.append(
                FAQItem(
                    question=question,
                    answer=FALLBACK_ANSWER,
                    citations=(),
                    topic_id=seed.topic_id,
                    seed_id=seed.seed_id,
                    coverage_item_id=seed.coverage_item_id,
                    status="missing_evidence",
                    prompt_version=template.version,
                    model=_model_name(model),
                )
            )
            continue
        selection = EvidenceSelection(
            query=normalize_question(question),
            topic_id=seed.topic_id,
            entities=(),
            selected=tuple(selected),
            omitted_unit_ids=(),
            tokens=0,
            budget_tokens=settings.qa_token_budget,
        )
        system_text = template.render(
            question=question,
            context=build_context(selected),
            min_citations=settings.faq_min_citations,
        )
        answer, citations, invalid = _generate_with_citations(
            model,
            system_text,
            question,
            selection,
            task="faq",
            min_citations=settings.faq_min_citations,
        )
        ready = len(citations) >= settings.faq_min_citations
        items.append(
            FAQItem(
                question=question,
                answer=answer,
                citations=tuple(citations),
                topic_id=seed.topic_id,
                seed_id=seed.seed_id,
                coverage_item_id=seed.coverage_item_id,
                status="ready" if ready and not invalid else "review",
                prompt_version=template.version,
                model=_model_name(model),
            )
        )
    return tuple(items)


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for the three tasks."""
    parser = argparse.ArgumentParser(
        prog="proyecto_modelos_lenguaje.tasks",
        description="Resumen, FAQ y Q&A del Módulo 1 sobre la capa de oro.",
    )
    subparsers = parser.add_subparsers(dest="task", required=True)

    def add_common(target: argparse.ArgumentParser) -> None:
        target.add_argument("--config", default=DEFAULT_CONFIG, help="Ruta de config/tasks.toml.")
        target.add_argument("--fake", action="store_true", help="Usa el modelo falso, sin red.")
        target.add_argument("--json", action="store_true", help="Emite un único objeto JSON.")

    qa_parser = subparsers.add_parser("qa", help="Responde una pregunta con citas.")
    qa_parser.add_argument("--question", default="", help="Pregunta del usuario; obligatoria.")
    add_common(qa_parser)

    summary_parser = subparsers.add_parser("summary", help="Resume el corpus con citas.")
    summary_parser.add_argument("--pack", choices=VALID_PACKS, default=None)
    add_common(summary_parser)

    faq_parser = subparsers.add_parser("faq", help="Genera la FAQ con evidencia.")
    faq_parser.add_argument("--limit", type=int, default=None, help="Número de preguntas (10-20).")
    add_common(faq_parser)
    return parser


def _emit_result(result: TaskResult) -> None:
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))


def _emit_faq(items: Sequence[FAQItem]) -> None:
    print(json.dumps([item.to_dict() for item in items], ensure_ascii=False, indent=2))


def _print_result(result: TaskResult) -> None:
    print(f"Tarea: {result.task}")
    print(f"Estado: {result.status}")
    print(f"Respuesta: {result.answer}")
    if result.citations:
        print("Fuentes:")
        for citation in result.citations:
            print(f"  [{citation.label}] {citation.citation}")
    else:
        print("Fuentes: —")
    print(f"Modelo: {result.model}")
    print(f"Prompt: {result.task} v{result.prompt_version}")
    print(f"Latencia: {result.latency_seconds:.1f} s")
    print(f"Tokens: entrada={result.input_tokens} salida={result.output_tokens}")


def _print_faq(items: Sequence[FAQItem]) -> None:
    print(f"FAQ: {len(items)} pregunta(s)")
    for index, item in enumerate(items, start=1):
        print(f"\n{index}. {item.question}")
        print(f"   Estado: {item.status}")
        print(f"   Respuesta: {item.answer}")
        if item.citations:
            labels = " ".join(f"[{citation.label}]" for citation in item.citations)
            print(f"   Fuentes: {labels}")
        else:
            print("   Fuentes: —")


def _fail(exc: TaskError, *, as_json: bool) -> int:
    payload = exc.to_dict()
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"Error: {exc.code} — {exc.message}")
    return 2 if exc.code in USAGE_ERROR_CODES else 1


def _build_model(fake: bool, task: str, root: Path) -> BaseChatModel:
    if fake:
        return build_scripted_model(task)
    from .llm import build_chat_model

    return build_chat_model(load_llm_config(project_root=root))


def _configure_output() -> None:
    """Make console output UTF-8 safe so non-Latin characters never crash the CLI."""
    for stream in (sys.stdout, sys.stderr):
        reconfigure = getattr(stream, "reconfigure", None)
        if reconfigure is None:
            continue
        try:
            reconfigure(encoding="utf-8", errors="replace")
        except ValueError, OSError:  # pragma: no cover - depende de la consola
            continue


def main(argv: Sequence[str] | None = None, *, project_root: Path | None = None) -> int:
    """CLI entry point for ``summary``, ``faq`` and ``qa``."""
    _configure_output()
    parser = build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    try:
        config = load_task_config(args.config, project_root=root)
        if args.task == "qa":
            template = load_prompt("qa", project_root=root)
            model = _build_model(args.fake, "qa", root)
            result = answer_question(
                args.question,
                model=model,
                config=config,
                prompt=template,
                gold_dir=_resolve_gold_dir(None, root),
                project_root=root,
            )
            if args.json:
                _emit_result(result)
            else:
                _print_result(result)
            return 0
        if args.task == "summary":
            template = load_prompt("summary", project_root=root)
            model = _build_model(args.fake, "summary", root)
            context_window = None
            if not args.fake:
                try:
                    context_window = load_llm_config(project_root=root).context_window
                except LLMConfigError:
                    context_window = None
            result = summarize_corpus(
                pack=args.pack,
                model=model,
                config=config,
                prompt=template,
                context_window=context_window,
                project_root=root,
            )
            if args.json:
                _emit_result(result)
            else:
                _print_result(result)
            return 0
        template = load_prompt("faq", project_root=root)
        model = _build_model(args.fake, "faq", root)
        items = generate_faq(
            limit=args.limit,
            model=model,
            config=config,
            prompt=template,
            project_root=root,
        )
        if args.json:
            _emit_faq(items)
        else:
            _print_faq(items)
        return 0
    except TaskError as exc:
        return _fail(exc, as_json=getattr(args, "json", False))


if __name__ == "__main__":
    sys.exit(main())
