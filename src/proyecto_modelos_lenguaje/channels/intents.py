"""Intenciones naturales del canal, sin comandos (spec 028, research R6, data-model «Intent»).

Léxico determinista en español e inglés: es rápido, gratis y comprobable, justo donde importa la
seguridad (confirmar escrituras). Las intenciones abiertas (olvidar datos, cambiar de perfil,
presentarse) las resuelve el agente por contexto.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Literal

Intent = Literal["restart", "format_text", "format_voice", "none"]
Decision = Literal["approve", "reject", "ambiguous"]
Language = Literal["es", "en"]

MAX_DECISION_WORDS = 8
NEW_QUESTION_WORDS = 6


def plain(text: str) -> str:
    """Minúsculas, sin tildes ni signos (conserva letras, números y espacios)."""
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    folded = folded.replace("'", "").replace("’", "")
    return re.sub(r"\s+", " ", re.sub(r"[^\w ]+", " ", folded)).strip()


def _pattern(*alternatives: str) -> re.Pattern[str]:
    return re.compile(r"(?:^| )(?:" + "|".join(alternatives) + r")(?: |$)")


RESTART = _pattern(
    r"(?:empecemos|empezemos|comencemos|empezar|comenzar|volvamos a empezar)"
    r"(?: (?:de nuevo|de cero|otra vez|desde cero))?(?: la conversacion)?",
    r"(?:una |otra )?(?:nueva|otra) conversacion",
    r"borron y cuenta nueva",
    r"(?:reinicia|reiniciar|reiniciemos) (?:la )?(?:conversacion|charla|chat)",
    r"(?:lets |let us )?start (?:over|again|fresh|a new conversation)",
    r"new conversation",
    r"reset (?:the )?(?:conversation|chat)",
)
# «empezar» solo no basta: exige «de nuevo/de cero/otra vez» o «conversación».
RESTART_GUARD = re.compile(
    r"de nuevo|de cero|desde cero|otra vez|conversacion|conversation|charla|chat|borron|"
    r"volvamos a empezar|start|reset"
)

FORMAT_TEXT = _pattern(
    r"(?:respondeme|contestame|escribeme|responde|contesta|responder) "
    r"(?:solo )?(?:por|en|con) (?:escrito|texto|mensajes?)",
    r"(?:mejor |prefiero )?(?:por escrito|solo texto|en texto)",
    r"(?:sin|no me (?:mandes|envies)) (?:mas )?(?:audios?|notas de voz|voz)",
    r"prefiero (?:que me escribas|leer)",
    r"text me",
    r"(?:reply|answer|respond) (?:in|by|with) (?:text|writing)",
    r"in writing",
    r"no (?:more )?(?:voice notes?|audios?)",
)
FORMAT_VOICE = _pattern(
    r"(?:mandame|enviame|respondeme|contestame|hablame|responde|contesta) "
    r"(?:un |una |con |por |en )?(?:audios?|voz|nota de voz|notas de voz)",
    r"(?:prefiero|quiero) (?:un |una |que me respondas con |que me hables por )?"
    r"(?:audios?|voz|notas? de voz)",
    r"(?:send|reply|answer) (?:me )?(?:with |by |in )?(?:an? )?(?:voice notes?|audio|voice)",
    r"(?:talk|speak) to me",
)

NEGATIVE_PHRASES = _pattern(
    r"claro que no",
    r"por supuesto que no",
    r"mejor no",
    r"no gracias",
    r"no thanks?",
    r"no lo hagas",
    r"no lo guardes",
    r"no quiero",
    r"dejalo (?:asi|como esta|para despues)",
    r"dejalo",
    r"olvidalo",
    r"ni loco",
    r"(?:dont|do not) (?:do it|save it)",
    r"never mind",
)
AFFIRMATIVE_PHRASES = _pattern(
    r"claro que si",
    r"por supuesto",
    r"de una",
    r"de acuerdo",
    r"hagale",
    r"hazlo",
    r"guardalo",
    r"borralo",
    r"adelante",
    r"go ahead",
    r"do it",
    r"please do",
    r"sounds good",
)
AMBIGUOUS_PHRASES = _pattern(
    r"no se",
    r"no estoy segur[oa]",
    r"tal vez",
    r"quizas?",
    r"a lo mejor",
    r"depende",
    r"maybe",
    r"not sure",
    r"m+",
    r"e+h+",
    r"h+m+",
)
AFFIRMATIVE_WORDS = {
    "si",
    "s",
    "claro",
    "dale",
    "ok",
    "okay",
    "vale",
    "listo",
    "confirmo",
    "confirmar",
    "procede",
    "perfecto",
    "seguro",
    "yes",
    "yep",
    "yeah",
    "sure",
    "confirm",
}
NEGATIVE_WORDS = {"no", "n", "nop", "nope", "cancela", "cancelar", "cancelo", "cancel", "stop"}

ENGLISH_HINTS = re.compile(
    r"\b(?:hi|hello|hey|thanks|thank you|yes|yeah|sure|please|what|how|who|where|when|why|"
    r"can you|could you|start over|text me|voice note|go ahead|no thanks|the|does|is|are)\b"
)
SPANISH_HINTS = re.compile(
    r"\b(?:hola|gracias|que|como|quien|donde|cuando|por que|puedes|dale|si|claro|mejor|"
    r"empecemos|mandame|respondeme|de|la|el|los|las|es|son)\b"
)


def detect_intent(text: str) -> Intent:
    """Intención del canal en el mensaje (antes de pasarlo al agente)."""
    value = plain(text)
    if not value:
        return "none"
    if RESTART.search(value) and RESTART_GUARD.search(value):
        return "restart"
    if FORMAT_TEXT.search(value):
        return "format_text"
    if FORMAT_VOICE.search(value):
        return "format_voice"
    return "none"


def remainder(text: str, intent: Intent) -> str:
    """La pregunta que acompaña a una intención («empecemos de nuevo: ¿qué produce…?»)."""
    if intent == "none":
        return text.strip()
    pattern = {"restart": RESTART, "format_text": FORMAT_TEXT, "format_voice": FORMAT_VOICE}[intent]
    parts = re.split(r"(?<=[.!?¿,;:])\s+|\n+", text.strip())
    kept = [part for part in parts if part and not pattern.search(plain(part))]
    rest = " ".join(kept).strip(" ,.;:")
    return rest if len(plain(rest).split()) >= 3 or "?" in rest else ""


def decision_of(text: str) -> Decision | None:
    """Respuesta a una confirmación pendiente.

    ``approve``/``reject`` solo con una intención clara; ``ambiguous`` si mezcla ambas o duda;
    ``None`` si el mensaje no es una respuesta corta (probablemente otra pregunta).
    """
    value = plain(text)
    words = value.split()
    if not words:
        return "ambiguous"
    if len(words) > MAX_DECISION_WORDS:
        return None
    negative = bool(NEGATIVE_PHRASES.search(value))
    affirmative = bool(AFFIRMATIVE_PHRASES.search(value))
    doubtful = bool(AMBIGUOUS_PHRASES.search(value))
    remaining = NEGATIVE_PHRASES.sub(" ", AFFIRMATIVE_PHRASES.sub(" ", value)).split()
    negative = negative or any(word in NEGATIVE_WORDS for word in remaining)
    affirmative = affirmative or any(word in AFFIRMATIVE_WORDS for word in remaining)
    if doubtful or (negative and affirmative):
        return "ambiguous"
    if affirmative:
        return "approve"
    if negative:
        return "reject"
    if "?" in text or len(words) >= 4:
        return None
    return "ambiguous"


def looks_like_new_question(text: str) -> bool:
    """¿El mensaje cambia de tema? («?» o ≥ 6 palabras sin ser una confirmación)."""
    return "?" in text or "¿" in text or len(plain(text).split()) >= NEW_QUESTION_WORDS


def language_of(text: str, hint: str | None = None) -> Language:
    """Idioma para responder: la pista del dictado, el detector del agente o el léxico corto."""
    if hint in ("es", "en"):
        return hint  # type: ignore[return-value]
    from ..agent.plan import detect_language

    detected = detect_language(text)
    if detected in ("es", "en"):
        return detected  # type: ignore[return-value]
    value = plain(text)
    english = len(ENGLISH_HINTS.findall(value))
    spanish = len(SPANISH_HINTS.findall(value))
    return "en" if english > spanish else "es"
