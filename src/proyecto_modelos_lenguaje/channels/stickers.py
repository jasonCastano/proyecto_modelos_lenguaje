"""Stickers de Valer-IA en WhatsApp: catálogo, situaciones y moderación (spec 034).

El backend decide de forma determinista si una respuesta lleva sticker, con señales que el canal
ya tiene: acto y sentimiento del turno (enrutador), avisos, inicio de conversación y presentación
(spec 032), aprobaciones resueltas, ruta e idioma. El plugin ``valeria-bridge`` solo lo entrega. Las
reglas, en orden (research R4): interruptor, exclusiones, situación, idioma y moderación del hilo.
Un sticker por respuesta como máximo y nunca en lugar de la respuesta.
"""

from __future__ import annotations

import re
import tomllib
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal

from ..config import PROJECT_ROOT

CATALOG_PATH = PROJECT_ROOT / "config" / "stickers.toml"
MAX_BYTES = 500 * 1024  # límite de WhatsApp para stickers animados
Position = Literal["before", "after"]

SITUATIONS = (
    "greeting_first_contact",
    "greeting_new_conversation",
    "greeting_mid",
    "thanks",
    "closing",
    "assent",
    "profile_saved",
    "action_done",
    "thinking",
    "useful_answer",  # spec 037
)
# Cuando concurren varias situaciones en un turno gana la primera (data-model).
PRIORITY = (
    "profile_saved",
    "action_done",
    "closing",
    "thanks",
    "greeting_first_contact",
    "greeting_new_conversation",
    "greeting_mid",
    "assent",
    "useful_answer",  # spec 037: respuesta útil con citas
)
NEGATIVE_SENTIMENTS = frozenset({"frustrated", "angry", "distressed"})
# Spec 037: el pulgar y la despedida pueden repetirse en respuestas seguidas.
REPEATABLE = frozenset({"valeria-pulgar", "valeria-lindo-dia"})
# Spec 037 (FR-012): la persona pide no recibir stickers en la conversación.
OPT_OUT = re.compile(
    r"\b(sin stickers?|no (me )?(mandes|envies|mandas|envias|pongas) (mas )?stickers?|"
    r"no quiero (mas )?stickers?|ya no (mas )?stickers?|deja de (mandar|enviar) stickers?|"
    r"no more stickers?|stop (sending )?stickers?|no stickers?)\b"
)
# Spec 037: el «ok» no lleva sticker si hubo uno en las dos respuestas anteriores.
ASSENT_GAP = 2
# Spec 037: preferencia cuando una situación admite varios stickers (respuesta útil).
PREFERRED = ("valeria-listo", "valeria-pulgar")
# Situaciones que siguen permitidas en una respuesta con información (spec 037).
FACTUAL_OK = frozenset(
    {
        "profile_saved",
        "action_done",
        "greeting_first_contact",
        "greeting_new_conversation",
        "useful_answer",
    }
)
ASSENT = frozenset(
    {
        "ok", "okay", "oki", "okis", "dale", "perfecto", "entendido", "listo", "vale", "genial",
        "de acuerdo", "claro", "bien", "excelente", "super", "sure", "got it", "great", "fine",
        "sounds good", "alright", "cool", "👍", "👌",
    }
)  # fmt: skip


@dataclass(frozen=True, slots=True)
class Sticker:
    """Una pieza aprobada de la spec 030 con su uso en la conversación."""

    name: str
    path: Path
    text: str
    language: str  # "es" o "none"
    situations: tuple[str, ...]
    position: Position


@dataclass(frozen=True, slots=True)
class StickerChoice:
    """Sticker elegido para una respuesta (lo entrega el plugin)."""

    name: str
    path: Path
    position: Position
    situation: str = ""  # spec 037: situación que lo justificó (se registra en el hilo)

    def to_dict(self) -> dict[str, str]:
        return {"name": self.name, "path": str(self.path), "position": self.position}


@dataclass(slots=True)
class StickerCatalog:
    """Stickers disponibles y los que no se pueden usar (con el motivo, sin detener el canal)."""

    stickers: dict[str, Sticker] = field(default_factory=dict)
    unavailable: dict[str, str] = field(default_factory=dict)

    def for_situation(self, situation: str) -> Sticker | None:
        return next((s for s in self.stickers.values() if situation in s.situations), None)

    def candidates(self, situation: str) -> list[Sticker]:
        """Spec 037: todos los stickers de la situación, en el orden del catálogo."""
        return [s for s in self.stickers.values() if situation in s.situations]


@dataclass(frozen=True, slots=True)
class TurnSignals:
    """Lo que el canal sabe del turno; ``text`` solo se usa para el léxico de asentimiento."""

    status: str
    event: str | None = None
    route: str | None = None
    act: str | None = None
    sentiment: str | None = None
    notices: tuple[str, ...] = ()
    language: str = "es"
    conversation_start: str | None = None
    approved_action: str | None = None
    factual: bool = False  # la respuesta trae citas o usó herramientas de consulta
    text: str = ""
    # Spec 037: respuesta útil con citas, respaldo, crisis, malestar y presentación del turno.
    cited: bool = False
    fallback: bool = False
    crisis: bool = False
    low_mood: bool = False
    introduced: bool = False


@dataclass(frozen=True, slots=True)
class ThreadUsage:
    """Stickers ya enviados en el hilo y número de la respuesta actual."""

    turn_no: int
    last_sticker_turn: int | None = None
    sent: tuple[str, ...] = ()
    last_sticker: str | None = None  # spec 037
    last_situation: str | None = None  # spec 037
    off: bool = False  # spec 037: la persona pidió no recibir stickers


def _is_webp(path: Path) -> str | None:
    """Motivo por el que el archivo no sirve, o ``None`` si es un WebP válido (≤ 500 KB)."""
    if not path.is_file():
        return "archivo no encontrado"
    size = path.stat().st_size
    if size > MAX_BYTES:
        return "pesa más de 500 KB"
    with path.open("rb") as handle:
        head = handle.read(12)
    if head[:4] != b"RIFF" or head[8:12] != b"WEBP":
        return "no es un WebP (¿puntero de Git LFS sin descargar?)"
    return None


def load_catalog(path: Path = CATALOG_PATH, root: Path = PROJECT_ROOT) -> StickerCatalog:
    """Lee ``config/stickers.toml``; una pieza inválida queda en ``unavailable`` con su motivo."""
    catalog = StickerCatalog()
    try:
        data = tomllib.loads(path.read_text(encoding="utf-8"))
    except (OSError, tomllib.TOMLDecodeError) as exc:
        catalog.unavailable["catálogo"] = f"no se pudo leer: {type(exc).__name__}"
        return catalog
    for name, raw in (data.get("stickers") or {}).items():
        try:
            situations = tuple(str(s) for s in raw.get("situations") or ())
            position = str(raw.get("position") or "")
            language = str(raw.get("language") or "")
            if not situations or any(s not in SITUATIONS for s in situations):
                raise ValueError("situaciones inválidas")
            if position not in ("before", "after") or language not in ("es", "none"):
                raise ValueError("posición o idioma inválidos")
            file = root / str(raw["file"])
        except (KeyError, TypeError, ValueError, AttributeError) as exc:
            catalog.unavailable[name] = f"configuración inválida: {exc}"
            continue
        problem = _is_webp(file)
        if problem:
            catalog.unavailable[name] = problem
            continue
        catalog.stickers[name] = Sticker(
            name,
            file,
            str(raw.get("text") or ""),
            language,
            situations,
            position,  # type: ignore[arg-type]
        )
    return catalog


def _plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", (text or "").lower())
    cleaned = "".join(c for c in folded if not unicodedata.combining(c))
    return " ".join(cleaned.replace("!", " ").replace(".", " ").replace(",", " ").split())


def is_assent(text: str) -> bool:
    """Asentimiento corto sin pedir nada nuevo («ok», «dale», «perfecto», «👍»)."""
    value = _plain(text)
    return value in ASSENT or (text or "").strip() in ASSENT


def situations_of(signals: TurnSignals) -> list[str]:
    """Situaciones del turno, en orden de prioridad (puede haber varias o ninguna)."""
    found: set[str] = set()
    if signals.approved_action == "save_preference":
        found.add("profile_saved")
    elif signals.approved_action:
        found.add("action_done")
    if signals.route == "planning" and signals.status == "answered":
        found.add("action_done")  # plan de producción entregado
    if signals.act == "closing":
        found.add("closing")
    elif signals.act == "thanks":
        found.add("thanks")
    elif signals.act == "greeting":
        if signals.conversation_start == "first_contact":
            found.add("greeting_first_contact")
        elif signals.conversation_start in ("inactivity", "restart"):
            found.add("greeting_new_conversation")
        else:
            found.add("greeting_mid")
    elif signals.act == "minimal" and is_assent(signals.text):
        found.add("assent")
    if signals.introduced and signals.conversation_start == "first_contact":
        found.add("greeting_first_contact")  # spec 037: la presentación lleva su sticker
    elif signals.introduced and signals.conversation_start in ("inactivity", "restart"):
        found.add("greeting_new_conversation")
    if signals.status == "answered" and signals.cited and not signals.fallback:
        found.add("useful_answer")  # spec 037: respuesta útil con fuentes
    return [situation for situation in PRIORITY if situation in found]


def _excluded(signals: TurnSignals) -> bool:
    """Momentos sin sticker: errores, avisos, quejas, molestia y datos sensibles (FR-007)."""
    if signals.status == "approval_resolved":
        if not signals.approved_action:
            return True  # una acción rechazada no se celebra
    elif signals.status != "answered":
        return True
    if signals.event:
        return True
    if "sensitive_data" in signals.notices:
        return True
    if signals.fallback or signals.crisis or signals.low_mood:
        return True  # spec 037: sin evidencia, crisis o malestar, nunca un sticker
    return signals.sentiment in NEGATIVE_SENTIMENTS or signals.act == "complaint"


def _language_ok(sticker: Sticker, language: str) -> bool:
    """En inglés solo stickers sin texto (FR-008)."""
    return language == "es" or sticker.language == "none"


def _moderation_ok(sticker: Sticker, situation: str, usage: ThreadUsage, limit: int) -> bool:
    """Spec 037 (data-model §5): máximo por conversación y sin repetir el mismo sticker seguido.

    Dos respuestas seguidas pueden llevar sticker si cambia la situación. Cadencias (sin saturar):

    - la respuesta útil se salta si la anterior también fue una respuesta útil con sticker (una de
      cada dos respuestas informativas seguidas);
    - el «ok» se salta si hubo sticker en cualquiera de las dos respuestas anteriores (es el más
      prescindible).
    """
    if len(usage.sent) >= limit:
        return False
    last = usage.last_sticker_turn
    consecutive = last is not None and usage.turn_no - last <= 1
    if situation == "useful_answer" and consecutive and usage.last_situation == "useful_answer":
        return False
    if situation == "assent" and last is not None and usage.turn_no - last <= ASSENT_GAP:
        return False
    repeated = usage.last_sticker == sticker.name and sticker.name not in REPEATABLE
    return not (consecutive and repeated)


def _pick(options: list[Sticker], usage: ThreadUsage) -> Sticker:
    """Con varios candidatos, el que no fue el último; «¡Listo!» antes que el pulgar (alternan)."""
    ordered = sorted(options, key=lambda s: PREFERRED.index(s.name) if s.name in PREFERRED else 99)
    fresh = [s for s in ordered if s.name != usage.last_sticker]
    return (fresh or ordered)[0]


def choose(
    signals: TurnSignals, usage: ThreadUsage, catalog: StickerCatalog, config: Any
) -> StickerChoice | None:
    """Sticker para esta respuesta, o ``None`` (research R4, en orden)."""
    limit = int(getattr(config, "stickers_per_conversation", 0))
    if not getattr(config, "stickers", False) or limit <= 0 or usage.off or _excluded(signals):
        return None
    candidates = situations_of(signals)
    if signals.factual:
        # Una respuesta con información no lleva saludos sociales a mitad de conversación, pero sí
        # la presentación, la respuesta útil (spec 037) o una acción completada.
        candidates = [s for s in candidates if s in FACTUAL_OK]
    for situation in candidates:
        options = [s for s in catalog.candidates(situation) if _language_ok(s, signals.language)]
        if not options:
            continue
        sticker = _pick(options, usage)
        if _moderation_ok(sticker, situation, usage, limit):
            return StickerChoice(sticker.name, sticker.path, sticker.position, situation)
        return None  # la situación principal no admite sticker: no se busca otra de menor rango
    return None
