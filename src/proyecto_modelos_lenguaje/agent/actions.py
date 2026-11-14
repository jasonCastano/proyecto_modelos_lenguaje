"""Acciones de escritura del agente con aprobación humana (spec 014, US4, FR-017, SC-009).

Regla de oro de la constitución: **lectura automática, escritura con aprobación**. Las cuatro
acciones (``forget_memory``, ``save_preference``, ``save_profile`` y ``export_conversation``)
solo se ejecutan después de una decisión humana registrada: en la variante agente las detiene
``HumanInTheLoopMiddleware``; en la cadena, un ``interrupt()`` explícito.

La memoria larga vive en el Store de LangGraph: preferencias en
``("users", user_id, "preferences")`` y perfil en ``("users", user_id, "profile")``.
"""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from typing import Any, Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langchain_core.tools import BaseTool, StructuredTool
from langgraph.store.base import BaseStore
from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator

from .memory import PROFILE_KEYS, PreferenceError, UserMemory, UserProfile
from .prompts import load_agent_prompt
from .structured import normalize

WRITE_TOOLS: tuple[str, ...] = (
    "forget_memory",
    "save_preference",
    "save_profile",
    "export_conversation",
)
PreferenceKey = Literal["response_format", "topics_of_interest", "language"]
EXPORT_PREVIEW_TURNS = 20

TOOL_DESCRIPTIONS = {
    "forget_memory": "Olvidar las preferencias y el perfil guardados del usuario",
    "save_preference": "Guardar una preferencia del usuario para próximas conversaciones",
    "save_profile": "Guardar datos del perfil del usuario (nombre, trabajo, cargo o ciudad)",
    "export_conversation": "Exportar la conversación actual en Markdown",
}


class ForgetMemoryArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SavePreferenceArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: PreferenceKey = Field(description="response_format, topics_of_interest o language.")
    value: str = Field(min_length=1, max_length=200, description="Valor de la preferencia.")


class SaveProfileArgs(BaseModel):
    """Datos que el usuario cuenta de sí mismo; al menos uno es obligatorio."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=80, description="Nombre del usuario.")
    workplace: str | None = Field(default=None, max_length=80, description="Dónde trabaja.")
    role: str | None = Field(default=None, max_length=80, description="Cargo u ocupación.")
    city: str | None = Field(default=None, max_length=80, description="Ciudad donde vive.")

    @model_validator(mode="after")
    def at_least_one(self) -> SaveProfileArgs:
        if not any((self.name, self.workplace, self.role, self.city)):
            raise ValueError("indica al menos un dato del perfil")
        return self


class ExportConversationArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")

    format: Literal["markdown"] = "markdown"


ARG_SCHEMAS: dict[str, type[BaseModel]] = {
    "forget_memory": ForgetMemoryArgs,
    "save_preference": SavePreferenceArgs,
    "save_profile": SaveProfileArgs,
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
# Perfil: se busca sobre el texto original para conservar mayúsculas y tildes.
_NAME_WORD = r"[A-ZÁÉÍÓÚÑ][a-záéíóúñü]+"
PROFILE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "name",
        # Solo la frase disparadora ignora mayúsculas; el nombre debe ir capitalizado
        # («soy Ana» sí; «soy ingeniera» o «soy de Cali» no).
        re.compile(
            rf"\b(?i:me llamo|mi nombre es|me dicen|soy)\s+({_NAME_WORD}(?:\s+{_NAME_WORD})?)"
            r"(?=\s*(?:[,.;!?]|$|\s+(?i:y|de|trabajo|laboro|vivo|soy)\b))"
        ),
    ),
    (
        "workplace",
        re.compile(
            r"\b(?:trabajo|laboro|estoy trabajando) (?:actualmente )?(?:en|para|con)\s+"
            r"(.{2,60}?)(?=\s+(?:y|como|desde)\b|[,.;!?]|$)"
            r"|\bmi empresa es\s+(.{2,60}?)(?=\s+(?:y|como|desde)\b|[,.;!?]|$)",
            re.I,
        ),
    ),
    (
        "role",
        re.compile(
            r"\b(?:trabajo como|laboro como|me desempeño como|mi cargo es|soy (?:el|la) )"
            r"\s*(.{3,60}?)(?=\s+(?:y|en)\b|[,.;!?]|$)",
            re.I,
        ),
    ),
    (
        "city",
        re.compile(
            r"\b(?:vivo en|resido en|soy de)\s+(.{2,60}?)(?=\s+(?:y|desde)\b|[,.;!?]|$)", re.I
        ),
    ),
)
# Mensaje que probablemente declara datos personales: si la regex no los extrae, se pide al LLM.
PROFILE_CUE = re.compile(
    r"\b(me llamo|mi nombre|me dicen|soy|trabajo|laboro|mi empresa|vivo|resido|mi cargo|"
    r"me desempeno|me presento|les escribe|te escribe|estoy vinculad[oa]|mi profesion)\b"
)
PROFILE_QUESTION = re.compile(
    r"\b(donde trabajo|como me llamo|cual es mi nombre|quien soy|que sabes de mi|donde vivo|"
    r"cual es mi cargo|en que trabajo|recuerdas mi nombre|sabes como me llamo|mi perfil|"
    r"donde laboro|cual es mi empresa|para quien trabajo|de donde soy|a que me dedico)\b"
)


class ProfileFacts(BaseModel):
    """Salida estructurada del extractor LLM del perfil (``prompts/profile_extract.md``)."""

    model_config = ConfigDict(extra="ignore")

    name: str | None = Field(default=None, max_length=80)
    workplace: str | None = Field(default=None, max_length=80)
    role: str | None = Field(default=None, max_length=80)
    city: str | None = Field(default=None, max_length=80)

    def as_profile(self) -> dict[str, str]:
        values = self.model_dump()
        return {
            key: str(value).strip(" .,;!?¿¡\"'")
            for key, value in values.items()
            if value and str(value).strip(" .,;!?¿¡\"'")
        }


def extract_profile_llm(model: BaseChatModel, message: str) -> dict[str, str]:
    """Extrae el perfil con el LLM y salida JSON validada con Pydantic; ``{}`` si algo falla."""
    prompt = load_agent_prompt("profile_extract").render(message=message)
    try:
        response = model.invoke([HumanMessage(content=prompt)])
        match = re.search(r"\{.*\}", str(response.content), flags=re.DOTALL)
        if match is None:
            return {}
        return ProfileFacts.model_validate(json.loads(match.group(0))).as_profile()
    except Exception:
        return {}


def extract_profile(message: str) -> dict[str, str]:
    """Datos de perfil declarados en un mensaje («Me llamo Ana y trabajo en Carvajal»)."""
    found: dict[str, str] = {}
    for key, pattern in PROFILE_PATTERNS:
        match = pattern.search(message)
        if match:
            group = next((g for g in match.groups() if g), "")
            value = group.strip(" .,;!?¿¡")
            if value:
                found[key] = value
    return found


def is_profile_question(message: str) -> bool:
    """Pregunta del usuario sobre sí mismo («¿Dónde trabajo?»): se responde desde la memoria."""
    return PROFILE_QUESTION.search(normalize(message)) is not None


TOPICS = re.compile(r"\bme interesa(?:n)?\s+(?:mucho\s+)?(?:el|la|los|las)?\s*(.{3,80}?)[.?!]*$")


@dataclass(frozen=True, slots=True)
class WriteIntent:
    tool: str
    args: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"tool": self.tool, "args": dict(self.args)}


def detect_write_intent(message: str, model: BaseChatModel | None = None) -> WriteIntent | None:
    """Pedidos de escritura: reglas deterministas y, para el perfil, el LLM como refuerzo.

    Las reglas no llaman al modelo. Solo si el mensaje parece declarar datos personales («laboro
    en…», «mi empresa es…») y la regex no extrae nada, se pide al LLM una salida JSON validada.
    """
    text = normalize(message).strip(" ¿?¡!.")
    if FORGET.search(text):
        return WriteIntent("forget_memory", {})
    if EXPORT.search(text):
        return WriteIntent("export_conversation", {"format": "markdown"})
    profile = extract_profile(message)
    declares = "?" not in message and PROFILE_CUE.search(text) is not None
    if not profile and model is not None and declares:
        extracted = extract_profile_llm(model, message)
        profile = {key: value for key, value in extracted.items() if key in PROFILE_KEYS}
    if profile:
        return WriteIntent("save_profile", profile)
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
        return "La memoria de largo plazo no está disponible en este servidor."
    memory = UserMemory(store, ttl_days)
    profile = UserProfile(store)
    if tool == "forget_memory":
        preferences = memory.forget(user_id)
        facts = profile.forget(user_id)
        return f"Olvidé {preferences} preferencias y {facts} datos de tu perfil."
    if tool == "save_profile":
        facts = {key: value for key, value in clean.items() if value}
        try:
            saved = profile.save(user_id, facts)
        except PreferenceError as exc:
            raise ActionArgsError(str(exc)) from exc
        listed = "; ".join(f"{item.key} = {item.value}" for item in saved)
        return f"Guardé en tu perfil: {listed}. Lo recordaré también en conversaciones nuevas."
    try:
        item = memory.save(user_id, clean["key"], clean["value"])
    except PreferenceError as exc:
        raise ActionArgsError(str(exc)) from exc
    return f"Guardé tu preferencia: {item.key} = {item.value}."


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
