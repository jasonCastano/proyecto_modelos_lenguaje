"""Perfiles de la plataforma de agentes de Manuelita (spec 025, idea 7; research R1, R14, R15).

Un solo agente atiende a cinco públicos. Cada perfil declara en ``config/profiles.toml`` su lista
blanca de herramientas de **lectura** del catálogo y, en ``prompts/profiles.md``, el foco que se
añade al system prompt. El perfil no cambia el enrutador: solo restringe qué herramientas se
ofrecen (``catalog.specs_for_route(..., profile=...)``).

La autorización depende del canal (spec 027, constitución regla 20): en la **web** los cinco
perfiles, incluido el ``planificador``, son de libre elección; en **WhatsApp** el planificador
exige un seudónimo en ``VALERIA_PLANNERS`` o ``MANUELITA_PLANNER_OPEN=1`` durante la jornada.
Ninguna lista de personas vive en el repositorio. ``MANUELITA_PLANNER_WEB`` ya no se lee.
"""

from __future__ import annotations

import os
import re
import tomllib
import unicodedata
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT

PROFILES_CONFIG = PROJECT_ROOT / "config" / "profiles.toml"
PROFILES_PROMPT = PROJECT_ROOT / "prompts" / "profiles.md"
PROFILE_KEYS: tuple[str, ...] = ("visitante", "cliente", "proveedor", "colaborador", "planificador")
DEFAULT_PROFILE = "visitante"
PLANNER = "planificador"
WEB = "web"
ALIASES = {
    "b2b": "cliente",
    "cliente b2b": "cliente",
    "comprador": "cliente",
    "planeador": "planificador",
    "planificacion": "planificador",
    "planificador industrial": "planificador",
    "empleado": "colaborador",
    "general": "visitante",
}
SECTION = re.compile(r"^##\s+(\S+)\s*$", re.MULTILINE)
TRUTHY = {"1", "true", "yes", "si", "sí", "on"}


class ProfileError(ValueError):
    """Configuración de perfiles inválida (falla al cargar, no en un turno)."""


@dataclass(frozen=True, slots=True)
class Profile:
    key: str
    label: str
    tools: tuple[str, ...]
    requires_authorization: bool
    triggers: tuple[re.Pattern[str], ...]
    focus: str

    def requires_authorization_in(self, channel: str) -> bool:
        """¿Exige autorización en ``channel``? En la web, nunca (spec 027)."""
        return self.requires_authorization and channel != WEB

    def to_dict(self, *, channel: str = WEB, authorized: bool = True) -> dict[str, Any]:
        return {
            "key": self.key,
            "label": self.label,
            "requires_authorization": self.requires_authorization_in(channel),
            "authorized": authorized,
        }


def plain(text: str) -> str:
    """Texto sin tildes, en minúsculas y con espacios simples (para alias y disparadores)."""
    decomposed = unicodedata.normalize("NFKD", text)
    stripped = "".join(ch for ch in decomposed if not unicodedata.combining(ch))
    return " ".join(stripped.lower().split())


def _focus_sections(prompt_path: Path) -> dict[str, str]:
    if not prompt_path.is_file():
        raise ProfileError(f"No existe {prompt_path.name}.")
    text = prompt_path.read_text(encoding="utf-8")
    matches = list(SECTION.finditer(text))
    sections: dict[str, str] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        sections[match.group(1)] = " ".join(text[match.end() : end].split())
    return sections


def _read_tools() -> set[str]:
    from .catalog import catalog

    return {spec.name for spec in catalog() if spec.kind == "read"}


def load_profiles(
    *, config_path: Path | None = None, prompt_path: Path | None = None
) -> dict[str, Profile]:
    """Carga y valida los perfiles; con ``enabled = false`` solo queda ``visitante``."""
    if config_path is None and prompt_path is None:
        return dict(_default_profiles())
    return _load(config_path or PROFILES_CONFIG, prompt_path or PROFILES_PROMPT)


@lru_cache(maxsize=1)
def _default_profiles() -> tuple[tuple[str, Profile], ...]:
    return tuple(_load(PROFILES_CONFIG, PROFILES_PROMPT).items())


def _load(config_path: Path, prompt_path: Path) -> dict[str, Profile]:
    try:
        document = tomllib.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        raise ProfileError(f"No pude leer {config_path.name}: {exc}") from exc
    settings = document.get("profiles") or {}
    enabled = bool(settings.get("enabled", True))
    entries = document.get("profile") or []
    focus = _focus_sections(prompt_path)
    available = _read_tools()
    loaded: dict[str, Profile] = {}
    for entry in entries:
        key = str(entry.get("key", ""))
        if key not in PROFILE_KEYS:
            raise ProfileError(f"Perfil desconocido: {key!r}.")
        if key in loaded:
            raise ProfileError(f"Perfil repetido: {key}.")
        if not enabled and key != DEFAULT_PROFILE:
            continue
        label = str(entry.get("label", ""))
        if not 3 <= len(label) <= 40:
            raise ProfileError(f"{key}: la etiqueta debe tener 3–40 caracteres.")
        tools = tuple(str(name) for name in entry.get("tools") or ())
        unknown = sorted(set(tools) - available)
        if unknown:
            raise ProfileError(f"{key}: herramientas inexistentes o de escritura: {unknown}.")
        if key not in focus:
            raise ProfileError(f"Falta la sección «## {key}» en {prompt_path.name}.")
        try:
            triggers = tuple(re.compile(str(p)) for p in entry.get("triggers") or ())
        except re.error as exc:
            raise ProfileError(f"{key}: disparador inválido: {exc}") from exc
        loaded[key] = Profile(
            key=key,
            label=label,
            tools=tools,
            requires_authorization=bool(entry.get("requires_authorization", False)),
            triggers=triggers,
            focus=focus[key],
        )
    if DEFAULT_PROFILE not in loaded:
        raise ProfileError("El perfil «visitante» es obligatorio.")
    missing = [key for key in PROFILE_KEYS if key not in loaded] if enabled else []
    if missing:
        raise ProfileError(f"Faltan perfiles en {config_path.name}: {missing}.")
    return {key: loaded[key] for key in PROFILE_KEYS if key in loaded}


def profiles_enabled() -> bool:
    return len(load_profiles()) > 1


def get_profile(key: str | None) -> Profile:
    """El perfil pedido o ``visitante`` si no existe (o si los perfiles están desactivados)."""
    loaded = load_profiles()
    return loaded.get(str(key or DEFAULT_PROFILE), loaded[DEFAULT_PROFILE])


def profile_focus(key: str) -> str:
    return get_profile(key).focus


def resolve_alias(text: str) -> str | None:
    """Clave de perfil a partir de lo que escribe la persona (``/perfil b2b`` → ``cliente``)."""
    value = plain(text)
    if not value:
        return None
    if value in PROFILE_KEYS:
        return value
    if value in ALIASES:
        return ALIASES[value]
    for profile in load_profiles().values():
        if plain(profile.label) == value:
            return profile.key
    return None


def match_trigger(message: str) -> str | None:
    """Perfil cuya autopresentación coincide con el mensaje («soy proveedor…»), si hay uno."""
    text = plain(message)
    for profile in load_profiles().values():
        if any(pattern.search(text) for pattern in profile.triggers):
            return profile.key
    return None


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in TRUTHY


def planners() -> frozenset[str]:
    raw = os.environ.get("VALERIA_PLANNERS", "")
    return frozenset(item.strip() for item in raw.split(",") if item.strip())


def is_authorized(user_id: str, channel: str = "web") -> bool:
    """¿Puede ``user_id`` usar el perfil planificador en ``channel``? (spec 027, R1).

    En la web, siempre. Fuera de la web, ``MANUELITA_PLANNER_OPEN=1`` o la lista
    ``VALERIA_PLANNERS``.
    """
    if channel == WEB or _flag("MANUELITA_PLANNER_OPEN"):
        return True
    return user_id in planners()


def effective_profile(key: str | None, user_id: str, channel: str = "web") -> str:
    """Perfil que rige el turno: inválido o no autorizado → ``visitante``."""
    profile = get_profile(key)
    if profile.requires_authorization_in(channel) and not is_authorized(user_id, channel):
        return DEFAULT_PROFILE
    return profile.key


def describe(user_id: str, channel: str = "web") -> list[dict[str, Any]]:
    """Lista para ``GET /api/profiles`` y ``/perfil``."""
    return [
        profile.to_dict(
            channel=channel,
            authorized=not profile.requires_authorization_in(channel)
            or is_authorized(user_id, channel),
        )
        for profile in load_profiles().values()
    ]
