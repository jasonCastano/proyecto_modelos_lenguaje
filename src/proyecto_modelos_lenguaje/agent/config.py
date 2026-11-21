"""Configuración tipada del agente RAG (``config/agent.toml``) y directorio de estado."""

from __future__ import annotations

import os
import sys
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT

DEFAULT_CONFIG_PATH = Path("config") / "agent.toml"
STATE_DIR_NAME = "manuelita-rag"


class AgentConfigError(ValueError):
    """La configuración del agente falta, es inválida o apunta a un lugar prohibido."""


@dataclass(frozen=True, slots=True)
class RouterConfig:
    min_confidence: float
    llm_temperature: float


@dataclass(frozen=True, slots=True)
class AgentLimits:
    tool_call_limit: int
    model_call_limit: int
    chain_top_k: int


@dataclass(frozen=True, slots=True)
class MemoryConfig:
    summarize_after_tokens: int
    keep_last_messages: int
    preference_ttl_days: int


@dataclass(frozen=True, slots=True)
class CareConfig:
    """Habilidades de atención de Valer-IA (spec 019)."""

    enabled: bool = True
    max_requests: int = 5
    hostility_levels: int = 3
    complaint_escalation: int = 3


@dataclass(frozen=True, slots=True)
class ConversationConfig:
    """Conversación natural guiada (spec 020, ``data-model.md`` §5)."""

    mode: str = "guided"
    temperature_social: float = 0.8
    temperature_facts: float = 0.3
    presence_penalty: float = 0.3
    frequency_penalty: float = 0.3
    bridge_every: int = 2
    bridge_min_score: float = 0.2
    repetition_threshold: float = 0.5
    recent_window: int = 10
    max_regenerations: int = 1
    converse_max_tokens: int = 220
    converse_timeout_seconds: float = 8.0
    review_llm: bool = False
    # Spec 021: entrega por frases revisadas.
    delivery: str = "sentences"
    sentence_max_chars: int = 220
    first_fragment_chars: int = 160
    stream_first_timeout_seconds: float = 8.0
    stream_idle_timeout_seconds: float = 6.0

    @property
    def guided(self) -> bool:
        return self.mode == "guided"

    @property
    def sentences(self) -> bool:
        """Entrega por frases: solo en la conversación guiada (en ``scripted`` vale la spec 019)."""
        return self.delivery == "sentences" and self.guided


CONVERSATION_MODES = ("guided", "scripted")
DELIVERY_MODES = ("sentences", "complete")

JEV_SIGNALS = ("route", "scope", "annoyance", "crisis")
JEV_ENABLED_ENV = "MANUELITA_JEV_ENABLED"


@dataclass(frozen=True, slots=True)
class JevConfig:
    """Gatekeeper System One de TypeSafe (spec 022, ``data-model.md``).

    La clave (``TYPESAFE_API_KEY``) no forma parte de la configuración: se lee del entorno al
    construir el cliente y nunca se serializa (FR-019).
    """

    enabled: bool = False
    base_url: str = "https://api.typesafe.ai"
    model: str = "jev-1.14.0"
    route_threshold: float = 0.75
    crisis_threshold: float = 0.5
    timeout_seconds: float = 2.0
    max_input_chars: int = 4000
    signals: tuple[str, ...] = JEV_SIGNALS

    def uses(self, signal: str) -> bool:
        return signal in self.signals


@dataclass(frozen=True, slots=True)
class AgentConfig:
    router: RouterConfig
    agent: AgentLimits
    memory: MemoryConfig
    structured_path: Path
    state_env_var: str
    source: Path
    care: CareConfig = CareConfig()
    conversation: ConversationConfig = ConversationConfig()
    jev: JevConfig = JevConfig()


def _section(document: dict[str, Any], key: str, source: Path) -> dict[str, Any]:
    section = document.get(key)
    if not isinstance(section, dict):
        raise AgentConfigError(f"Falta la sección [{key}] en {source}.")
    return section


def _number(
    section: dict[str, Any],
    key: str,
    *,
    table: str,
    minimum: float,
    maximum: float | None = None,
) -> float:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentConfigError(f"{table}.{key} debe ser un número.")
    if value < minimum or (maximum is not None and value > maximum):
        upper = "" if maximum is None else f" y {maximum}"
        raise AgentConfigError(f"{table}.{key} debe estar entre {minimum}{upper}.")
    return float(value)


def _integer(section: dict[str, Any], key: str, *, table: str, minimum: int = 1) -> int:
    value = section.get(key)
    if isinstance(value, bool) or not isinstance(value, int):
        raise AgentConfigError(f"{table}.{key} debe ser un entero.")
    if value < minimum:
        raise AgentConfigError(f"{table}.{key} debe ser >= {minimum}.")
    return value


def _string(section: dict[str, Any], key: str, *, table: str) -> str:
    value = section.get(key)
    if not isinstance(value, str) or not value.strip():
        raise AgentConfigError(f"{table}.{key} debe ser un texto no vacío.")
    return value.strip()


def load_agent_config(
    path: str | Path | None = None, *, project_root: Path | None = None
) -> AgentConfig:
    """Lee y valida ``config/agent.toml``."""
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    source = Path(path) if path is not None else root / DEFAULT_CONFIG_PATH
    if not source.is_file():
        raise AgentConfigError(f"No existe la configuración del agente: {source}")
    try:
        document = tomllib.loads(source.read_text(encoding="utf-8"))
    except tomllib.TOMLDecodeError as exc:
        raise AgentConfigError(f"TOML inválido en {source}: {exc}") from exc

    router = _section(document, "router", source)
    agent = _section(document, "agent", source)
    memory = _section(document, "memory", source)
    structured = _section(document, "structured", source)
    state = _section(document, "state", source)

    structured_path = Path(_string(structured, "path", table="structured"))
    if not structured_path.is_absolute():
        structured_path = root / structured_path

    return AgentConfig(
        router=RouterConfig(
            min_confidence=_number(
                router, "min_confidence", table="router", minimum=0.0, maximum=1.0
            ),
            llm_temperature=_number(
                router, "llm_temperature", table="router", minimum=0.0, maximum=2.0
            ),
        ),
        agent=AgentLimits(
            tool_call_limit=_integer(agent, "tool_call_limit", table="agent"),
            model_call_limit=_integer(agent, "model_call_limit", table="agent"),
            chain_top_k=_integer(agent, "chain_top_k", table="agent"),
        ),
        memory=MemoryConfig(
            summarize_after_tokens=_integer(memory, "summarize_after_tokens", table="memory"),
            keep_last_messages=_integer(memory, "keep_last_messages", table="memory"),
            preference_ttl_days=_integer(memory, "preference_ttl_days", table="memory"),
        ),
        structured_path=structured_path,
        state_env_var=_string(state, "env_var", table="state"),
        source=source,
        care=_care_config(document.get("care")),
        conversation=_conversation_config(document.get("conversation")),
        jev=jev_config(document.get("jev")),
    )


def _bounded(
    section: dict[str, Any],
    key: str,
    default: float,
    low: float,
    high: float,
    *,
    integer: bool = False,
    open_interval: bool = False,
) -> Any:
    """Valor numérico opcional de ``[conversation]`` dentro de su rango."""
    value = section.get(key, default)
    kind = "un entero" if integer else "un número"
    if isinstance(value, bool) or not isinstance(value, int if integer else (int, float)):
        raise AgentConfigError(f"conversation.{key} debe ser {kind}.")
    inside = low < value < high if open_interval else low <= value <= high
    if not inside:
        bounds = f"({low}, {high})" if open_interval else f"[{low}, {high}]"
        raise AgentConfigError(f"conversation.{key} debe estar en {bounds}.")
    return int(value) if integer else float(value)


def _conversation_config(section: object) -> ConversationConfig:
    """Sección ``[conversation]`` opcional (spec 020); sin ella valen los defectos."""
    if section is None:
        return ConversationConfig()
    if not isinstance(section, dict):
        raise AgentConfigError("[conversation] debe ser una tabla.")
    mode = section.get("mode", "guided")
    if mode not in CONVERSATION_MODES:
        raise AgentConfigError("conversation.mode debe ser «guided» o «scripted».")
    delivery = section.get("delivery", "sentences")
    if delivery not in DELIVERY_MODES:
        raise AgentConfigError("conversation.delivery debe ser «sentences» o «complete».")
    sentence_max_chars = _bounded(section, "sentence_max_chars", 220, 80, 600, integer=True)
    first_fragment_chars = _bounded(section, "first_fragment_chars", 160, 40, 400, integer=True)
    if first_fragment_chars > sentence_max_chars:
        raise AgentConfigError(
            "conversation.first_fragment_chars debe ser <= conversation.sentence_max_chars."
        )
    review_llm = section.get("review_llm", False)
    if not isinstance(review_llm, bool):
        raise AgentConfigError("conversation.review_llm debe ser booleano.")
    bridge_every = _bounded(section, "bridge_every", 2, 1, 1_000, integer=True)
    return ConversationConfig(
        mode=str(mode),
        temperature_social=_bounded(section, "temperature_social", 0.8, 0.0, 1.0),
        temperature_facts=_bounded(section, "temperature_facts", 0.3, 0.0, 1.0),
        presence_penalty=_bounded(section, "presence_penalty", 0.3, 0.0, 1.0),
        frequency_penalty=_bounded(section, "frequency_penalty", 0.3, 0.0, 1.0),
        bridge_every=bridge_every,
        bridge_min_score=_bounded(section, "bridge_min_score", 0.2, 0.0, 1.0),
        repetition_threshold=_bounded(
            section, "repetition_threshold", 0.5, 0.0, 1.0, open_interval=True
        ),
        recent_window=_bounded(section, "recent_window", 10, 1, 10, integer=True),
        max_regenerations=_bounded(section, "max_regenerations", 1, 0, 2, integer=True),
        converse_max_tokens=_bounded(section, "converse_max_tokens", 220, 50, 600, integer=True),
        converse_timeout_seconds=_bounded(section, "converse_timeout_seconds", 8.0, 1.0, 30.0),
        review_llm=review_llm,
        delivery=str(delivery),
        sentence_max_chars=sentence_max_chars,
        first_fragment_chars=first_fragment_chars,
        stream_first_timeout_seconds=_bounded(
            section, "stream_first_timeout_seconds", 8.0, 1.0, 30.0
        ),
        stream_idle_timeout_seconds=_bounded(
            section, "stream_idle_timeout_seconds", 6.0, 1.0, 30.0
        ),
    )


def _jev_number(
    section: dict[str, Any], key: str, default: float, low: float, high: float
) -> float:
    value = section.get(key, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise AgentConfigError(f"jev.{key} debe ser un número.")
    if not low <= value <= high:
        raise AgentConfigError(f"jev.{key} debe estar en [{low}, {high}].")
    return float(value)


def jev_config(section: object, *, environ: dict[str, str] | None = None) -> JevConfig:
    """Sección ``[jev]`` opcional (spec 022); ``MANUELITA_JEV_ENABLED`` sobrescribe ``enabled``."""
    env = os.environ if environ is None else environ
    defaults = JevConfig()
    if section is None:
        section = {}
    if not isinstance(section, dict):
        raise AgentConfigError("[jev] debe ser una tabla.")
    enabled = section.get("enabled", False)
    if not isinstance(enabled, bool):
        raise AgentConfigError("jev.enabled debe ser booleano.")
    override = env.get(JEV_ENABLED_ENV, "").strip().lower()
    if override in {"1", "true", "si", "sí", "yes", "on"}:
        enabled = True
    elif override in {"0", "false", "no", "off"}:
        enabled = False
    base_url = str(section.get("base_url", defaults.base_url)).strip()
    if not base_url.startswith("https://") or base_url.endswith("/"):
        raise AgentConfigError("jev.base_url debe empezar por https:// y no terminar en «/».")
    model = section.get("model", defaults.model)
    if not isinstance(model, str) or not model.strip():
        raise AgentConfigError("jev.model debe ser un texto no vacío.")
    if model.strip().lower().endswith("latest"):
        raise AgentConfigError("jev.model debe ser una versión fija, no un alias «latest».")
    max_chars = section.get("max_input_chars", defaults.max_input_chars)
    if isinstance(max_chars, bool) or not isinstance(max_chars, int):
        raise AgentConfigError("jev.max_input_chars debe ser un entero.")
    if not 500 <= max_chars <= 30_000:
        raise AgentConfigError("jev.max_input_chars debe estar en [500, 30000].")
    signals = section.get("signals", list(JEV_SIGNALS))
    if not isinstance(signals, list) or not all(isinstance(s, str) for s in signals):
        raise AgentConfigError("jev.signals debe ser una lista de textos.")
    unknown = sorted(set(signals) - set(JEV_SIGNALS))
    if unknown:
        raise AgentConfigError(f"jev.signals tiene señales desconocidas: {', '.join(unknown)}.")
    if "route" not in signals:
        raise AgentConfigError("jev.signals debe incluir «route».")
    return JevConfig(
        enabled=enabled,
        base_url=base_url,
        model=model.strip(),
        route_threshold=_jev_number(section, "route_threshold", 0.75, 0.5, 1.0),
        crisis_threshold=_jev_number(section, "crisis_threshold", 0.5, 0.1, 0.9),
        timeout_seconds=_jev_number(section, "timeout_seconds", 2.0, 0.2, 10.0),
        max_input_chars=max_chars,
        signals=tuple(s for s in JEV_SIGNALS if s in signals),
    )


def _care_config(section: object) -> CareConfig:
    """Sección ``[care]`` opcional; sin ella valen los valores por defecto."""
    if section is None:
        return CareConfig()
    if not isinstance(section, dict):
        raise AgentConfigError("[care] debe ser una tabla.")
    enabled = section.get("enabled", True)
    if not isinstance(enabled, bool):
        raise AgentConfigError("care.enabled debe ser booleano.")
    max_requests = _integer(section, "max_requests", table="care")
    if max_requests > 10:
        raise AgentConfigError("care.max_requests debe estar entre 1 y 10.")
    return CareConfig(
        enabled=enabled,
        max_requests=max_requests,
        hostility_levels=_integer(section, "hostility_levels", table="care"),
        complaint_escalation=_integer(section, "complaint_escalation", table="care"),
    )


def _default_state_dir() -> Path:
    if sys.platform.startswith("win"):
        base = os.environ.get("LOCALAPPDATA")
        if base:
            return Path(base) / STATE_DIR_NAME
        return Path.home() / "AppData" / "Local" / STATE_DIR_NAME
    base = os.environ.get("XDG_STATE_HOME")
    if base:
        return Path(base) / STATE_DIR_NAME
    return Path.home() / ".local" / "state" / STATE_DIR_NAME


def resolve_state_dir(
    env_var: str = "MANUELITA_STATE_DIR", *, project_root: Path | None = None
) -> Path:
    """Directorio del checkpointer y del Store, siempre fuera del repositorio.

    Regla dura de ``AGENTS.md``: la app no escribe en ``data/`` ni en el repositorio.
    """
    root = (Path(project_root) if project_root is not None else PROJECT_ROOT).resolve()
    configured = os.environ.get(env_var, "").strip()
    target = (Path(configured).expanduser() if configured else _default_state_dir()).resolve()
    if target == root or root in target.parents:
        raise AgentConfigError(
            f"El directorio de estado {target} queda dentro del repositorio; "
            f"define {env_var} con una ruta externa."
        )
    return target
