"""Acciones de escritura del agente con aprobación humana (spec 014, US4, FR-017, SC-009).

Regla de oro de la constitución: **lectura automática, escritura con aprobación**. Las tres acciones
(``forget_memory``, ``save_preference`` y ``export_conversation``) solo se ejecutan después de una
decisión humana registrada: en la variante agente las detiene ``HumanInTheLoopMiddleware``; en la
cadena, un ``interrupt()`` explícito.

La memoria larga vive en el Store de LangGraph, namespace ``("users", user_id, "preferences")``.
"""

from __future__ import annotations

import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any, Literal

from langchain_core.tools import BaseTool, StructuredTool
from langgraph.store.base import BaseStore
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from .structured import normalize

WRITE_TOOLS: tuple[str, ...] = ("forget_memory", "save_preference", "export_conversation")
PreferenceKey = Literal["response_format", "topics_of_interest", "language"]
EXPORT_PREVIEW_TURNS = 20

TOOL_DESCRIPTIONS = {
    "forget_memory": "Olvidar las preferencias guardadas del usuario",
    "save_preference": "Guardar una preferencia del usuario para próximas conversaciones",
    "export_conversation": "Exportar la conversación actual en Markdown",
}


class ForgetMemoryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SavePreferenceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: PreferenceKey = Field(description="response_format, topics_of_interest o language.")
    value: str = Field(min_length=1, max_length=200, description="Valor de la preferencia.")


class ExportConversationArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["markdown"] = "markdown"


ARG_SCHEMAS: dict[str, type[BaseModel]] = {
    "forget_memory": ForgetMemoryArgs,
    "save_preference": SavePreferenceArgs,
    "export_conversation": ExportConversationArgs,
}


class ActionArgsError(ValueError):
    """Los argumentos editados no cumplen el esquema de la herramienta."""


def validate_args(tool: str, args: dict[str, Any]) -> dict[str, Any]:
    schema = ARG_SCHEMAS.get(tool)
    if schema is None:
        raise ActionArgsError(f"Herramienta de escritura desconocida: {tool}.")
    try:
        return schema.model_validate(args).model_dump()
    except ValidationError as exc:
        raise ActionArgsError(
            f"Argumentos inválidos para {tool}: {exc.errors()[0]['msg']}"
        ) from exc


# ---------------------------------------------------------------- intención de escritura

FORGET = re.compile(
    r"\b(olvida|borra|elimina|limpia)\b.{0,40}\b(preferencias|memoria|lo que sabes|mis datos)\b"
)
EXPORT = re.compile(r"\b(exporta|descarga|guarda)\b.{0,30}\b(conversacion|chat|hilo)\b")
PREFERENCE_TRIGGER = re.compile(r"\b(prefiero|preferiria|quiero|responde|respondeme|contestame)\b")
FORMAT_VALUES = (
    ("vinetas", "viñetas"),
    ("lista", "viñetas"),
    ("breve", "breve"),
    ("corto", "breve"),
    ("detallad", "detallada"),
)
LANGUAGE_VALUES = (("ingles", "inglés"), ("espanol", "español"))
TOPICS = re.compile(r"\bme interesa(?:n)?\s+(?:mucho\s+)?(?:el|la|los|las)?\s*(.{3,80}?)[.?!]*$")


@dataclass(frozen=True, slots=True)
class WriteIntent:
    tool: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "args": dict(self.args)}


def detect_write_intent(message: str) -> WriteIntent | None:
    """Reglas deterministas para pedidos de escritura (0 llamadas al modelo)."""
    text = normalize(message).strip(" ¿?¡!.")
    if FORGET.search(text):
        return WriteIntent("forget_memory", {})
    if EXPORT.search(text):
        return WriteIntent("export_conversation", {"format": "markdown"})
    topics = TOPICS.search(text)
    if topics:
        value = message.strip(" ¿?¡!.")[-len(topics.group(1)) :].strip()
        return WriteIntent("save_preference", {"key": "topics_of_interest", "value": value})
    if PREFERENCE_TRIGGER.search(text):
        for needle, value in LANGUAGE_VALUES:
            if f"en {needle}" in text:
                return WriteIntent("save_preference", {"key": "language", "value": value})
        for needle, value in FORMAT_VALUES:
            if needle in text:
                return WriteIntent("save_preference", {"key": "response_format", "value": value})
    return None


# ---------------------------------------------------------------- efectos


def preferences_namespace(user_id: str) -> tuple[str, ...]:
    return ("users", user_id, "preferences")


def export_markdown(turns: Sequence[dict[str, Any]]) -> str:
    lines = ["# Conversación con el asistente de Manuelita", ""]
    for turn in list(turns)[-EXPORT_PREVIEW_TURNS:]:
        lines += [f"**Pregunta {turn.get('turn_id', '')}.** {turn.get('question', '')}", ""]
        lines += [str(turn.get("answer", "")), ""]
        for url in turn.get("sources", []):
            lines.append(f"- Fuente: {url}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def execute_action(
    tool: str,
    args: dict[str, Any],
    *,
    store: BaseStore | None,
    user_id: str,
    turns: Sequence[dict[str, Any]],
    ttl_days: int,
) -> str:
    """Ejecuta una acción ya aprobada y devuelve el mensaje para el usuario."""
    clean = validate_args(tool, args)
    if tool == "export_conversation":
        if not turns:
            return "La conversación todavía no tiene turnos para exportar."
        return f"Exporté la conversación ({len(turns)} turnos):\n\n{export_markdown(turns)}"
    if store is None:
        return "La memoria de preferencias no está disponible en este servidor."
    namespace = preferences_namespace(user_id)
    if tool == "forget_memory":
        items = store.search(namespace, limit=100)
        for item in items:
            store.delete(namespace, item.key)
        return f"Olvidé {len(items)} preferencias guardadas."
    now = datetime.now(UTC)
    store.put(
        namespace,
        clean["key"],
        {
            "value": clean["value"],
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(days=ttl_days)).isoformat(),
        },
    )
    return f"Guardé tu preferencia: {clean['key']} = {clean['value']}."


def build_write_tools(
    run: Callable[[str, dict[str, Any]], str],
) -> Sequence[BaseTool]:
    """Herramientas de escritura para el agente; ``run`` ejecuta la acción ya aprobada."""

    def make(name: str) -> BaseTool:
        def call(**kwargs: Any) -> str:
            return run(name, kwargs)

        return StructuredTool.from_function(
            func=call,
            name=name,
            description=f"{TOOL_DESCRIPTIONS[name]}. Requiere aprobación humana.",
            args_schema=ARG_SCHEMAS[name],
        )

    return tuple(make(name) for name in WRITE_TOOLS)
