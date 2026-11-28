"""Plan del turno de la conversación guiada (spec 020, ``contracts/conversation.md`` §2).

Decide *qué hacer* con cada mensaje sin modelo de lenguaje: el acto de diálogo, el nivel de cada
parte (social, externo o Manuelita), la estrategia, la longitud, el idioma y el registro. El *cómo
decirlo* queda a cargo del nodo ``converse`` y el *si se puede mostrar*, de ``review.py``.

El plan solo contiene etiquetas: nunca guarda texto del visitante.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass, field, replace
from typing import Any, Literal

from .config import ConversationConfig
from .models import DIALOGUE_ACTS
from .structured import normalize

Length = Literal["short", "medium", "long"]
Language = Literal["es", "en", "other"]
Register = Literal["formal", "informal"]

# ---------------------------------------------------------------- léxicos (texto normalizado)

CLOSING = re.compile(
    r"\b(eso (era|es|seria|fue) todo|chao|chau|adios|hasta (luego|pronto|manana|la proxima)|"
    r"nos vemos|me despido|ya me voy|bye|goodbye|that'?s all|ya no necesito (nada|mas)|"
    r"(listo|bueno|perfecto|ok),? (muchas )?gracias,? (eso|ya) (era|es) todo)\b"
)
CORRECTION = re.compile(
    r"\b(me referia (a|al|es)|quise decir|lo que quise decir|no era eso|me refiero (a|al)|"
    r"no hablaba de|no te pregunte (por|eso)|i meant)\b"
)
ABOUT_ASSISTANT = re.compile(
    r"\b(eres (una |un )?(humana|humano|persona|real|robot|bot|ia|inteligencia artificial|maquina)|"
    r"hablo con (una |un )?(persona|humano|humana|bot|maquina)|quien eres|que eres|"
    r"que (puedes|sabes) hacer|en que (me )?puedes ayudar|por que no sabes|como funcionas|"
    r"quien te (creo|hizo|programo)|como te llamas|what can you do|are you (a )?(human|bot|real)|"
    r"who are you)\b"
)
THANKS = re.compile(r"\b(gracias|te agradezco|muy amable|thanks|thank you)\b")
GREETING = re.compile(
    r"\b(hola|holi|buen(os|as)? (dia|dias|tardes|noches)|buenas|saludos|hey|que mas|que tal|"
    r"hello|hi|good (morning|afternoon|evening))\b"
)
MINIMAL_WORDS = frozenset(
    {
        *("ok", "okay", "oki", "okey", "vale", "ja", "je", "ji", "mmm", "hmm", "aja", "ah"),
        *("oh", "uh", "eh", "ya", "bueno", "listo", "si", "sip", "no", "nop", "ajam", "uy"),
        *("wow", "xd", "lol", "k", "dale", "va", "vaya", "uff", "ufff", "pues", "entiendo"),
        *("claro", "genial", "bien", "nice", "cool", "sure", "yes", "yeah"),
    }
)
LAUGH = re.compile(r"^(j[aeiou])+j?$|^(h[ae])+h?$|^m+$|^x+d+$")
# Marcas de registro informal del visitante (incluye modismos de otras regiones: aquí solo detectan
# el tono; Valer-IA nunca los usa). Spec 036: marcas caleñas («oís», «ve pues», «listo pues»,
# «qué nota»); «ve» suelto no cuenta porque también es verbo («ve a la página»).
INFORMAL = re.compile(
    r"\b(parce|parcero|parcera|jaj[a-z]*|jej[a-z]*|uy|que mas|bacano|chevere|mano|hermano|"
    r"pana|wey|xd|lol|ome|nojoda|q hubo|quiubo|vea pues|pues si|bro|ois|ve pues|que mas pues|"
    r"listo pues|que nota|de una)\b"
)
SPANISH_FUNCTION = re.compile(
    r"\b(que|el|la|de|es|y|en|los|las|un|una|por|con|para|me|mi|tu|no|se|lo|como|del|eso|esa|"
    r"ese|esto|era|todo|toda|gracias|hola|listo|si|muy|bien|pero|mas|ya|esta|estoy|hay|son|fue|"
    r"yo|te|al|sus|su|nada|algo|cuando|donde|quien|cual|porque|tambien|aqui|ahi|hoy|ayer|"
    r"manana|buen|buenas|bueno|dia|claro|vale|parce|chao|adios|quiero|tengo|puedes|sabes)\b"
)
ENGLISH_FUNCTION = re.compile(
    r"\b(the|what|where|when|how|does|do|is|are|please|company|who|you|your|and|of|to|in|"
    r"can|about|tell|me|it|was|were|which|why|did|has|have|had|this|that|there|for|with|from|"
    r"by|an|much|many|any|know|we|our|they|their|its|my|could|would|should|will|been)\b"
)
EMOJI_ONLY = re.compile(r"^[^\w]+$")

NEGATIVE = frozenset({"frustrated", "angry", "distressed", "confused"})
UPSET = frozenset({"frustrated", "angry", "distressed"})
RULED_ACTS = frozenset(
    {"closing", "correction", "complaint", "about_assistant", "minimal", "thanks", "greeting"}
)


def _words(normalized: str) -> list[str]:
    return re.findall(r"[a-z0-9']+", normalized)


def is_minimal(message: str) -> bool:
    """«ok», «jaja», «👍», «mmm»: asentimientos, risas, emojis y muletillas sueltas."""
    text = normalize(message).strip(" .,!¡?¿…")
    if not text:
        return False
    if EMOJI_ONLY.match(text):
        return True
    words = _words(text)
    return 0 < len(words) <= 3 and all(w in MINIMAL_WORDS or LAUGH.match(w) for w in words)


def detect_act(message: str, signals: Mapping[str, Any] | None = None) -> tuple[str, bool]:
    """Acto de diálogo dominante y si lo determinó un léxico (prioridad de ``tasks.md`` T007).

    Prioridad: ``closing`` > ``correction`` > ``complaint`` > ``about_assistant`` > ``minimal`` >
    ``thanks`` > ``greeting`` > ``manuelita`` > ``off_topic`` > ``smalltalk``.
    """
    text = normalize(message)
    signals = signals or {}
    parts = list(signals.get("requests") or [])
    tiers = [str(part.get("tier") or "") for part in parts]
    asks = "manuelita" in tiers or "external" in tiers
    if CLOSING.search(text) and not (asks and "?" in message):
        return "closing", True
    if CORRECTION.search(text):
        return "correction", True
    if signals.get("complaint_only") or (signals.get("rejection") and not asks):
        return "complaint", True
    if ABOUT_ASSISTANT.search(text):
        return "about_assistant", True
    if is_minimal(message):
        return "minimal", True
    if THANKS.search(text) and not asks:
        return "thanks", True
    if GREETING.search(text) and not asks:
        return "greeting", True
    if "manuelita" in tiers:
        return "manuelita", False
    if "external" in tiers:
        return "off_topic", False
    return "smalltalk", False


def detect_language(message: str) -> Language | None:
    """Idioma del mensaje; con 3 palabras o menos devuelve ``None`` (se hereda de la memoria)."""
    text = normalize(message)
    words = _words(text)
    if len(words) <= 3:
        return None
    english = len(ENGLISH_FUNCTION.findall(text))
    spanish = len(SPANISH_FUNCTION.findall(text))
    if english >= 2 and english > spanish:
        return "en"
    if spanish == 0 and english == 0 and len(words) >= 4:
        return "other"
    return "es"


def detect_register(message: str) -> Register:
    """``informal`` con marcas coloquiales («parce», «jaja», «qué más»); si no, ``formal``."""
    return "informal" if INFORMAL.search(normalize(message)) else "formal"


# ---------------------------------------------------------------- plan del turno


@dataclass(frozen=True, slots=True)
class BridgeChoice:
    """Puente elegido para el turno (``data-model.md`` §3)."""

    unit_id: str
    angle: str
    title: str
    url: str
    text: str
    source: Literal["retrieval", "curated"]
    score: float = 0.0
    key: str | None = None  # sección curada de care.md, si viene de ahí

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class TurnPlan:
    """Plan determinista del turno (``data-model.md`` §1). Solo etiquetas."""

    act: str
    tiers: tuple[str, ...]
    sentiment: str
    strategy: tuple[str, ...]
    length: Length
    language: Language
    register: Register
    bridge: BridgeChoice | None = None
    bridge_allowed: bool = False
    best_guess: bool = False
    reason: str | None = None  # scope_reason de la decisión
    topic: str | None = None  # etiqueta controlada del tema ajeno
    turn: int = 1
    summary_topics: tuple[str, ...] = field(default_factory=tuple)
    introduced: bool = False  # ya se presentó como Valer-IA Caña en este hilo
    # Spec 035: regreso obligatorio a Manuelita en turnos ajenos, racha y temas sugeridos.
    redirect: bool = False
    streak: int = 0
    topics: tuple[str, ...] = field(default_factory=tuple)
    # Spec 036: nivel del estilo caleño (off, formal, neutral, informal) y expresiones sugeridas.
    style: str = "off"
    style_hints: tuple[str, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if self.act not in DIALOGUE_ACTS:
            raise ValueError(f"acto desconocido: {self.act}")
        if not self.strategy:
            raise ValueError("la estrategia nunca puede quedar vacía")

    def with_bridge(self, bridge: BridgeChoice | None, allowed: bool) -> TurnPlan:
        return replace(self, bridge=bridge if allowed else None, bridge_allowed=allowed)

    def to_state(self) -> dict[str, Any]:
        """Versión serializable para el estado del hilo (sin texto del visitante)."""
        data = {
            "act": self.act,
            "tiers": list(self.tiers),
            "sentiment": self.sentiment,
            "strategy": list(self.strategy),
            "length": self.length,
            "language": self.language,
            "register": self.register,
            "bridge_allowed": self.bridge_allowed,
            "best_guess": self.best_guess,
            "reason": self.reason,
            "topic": self.topic,
            "turn": self.turn,
            "summary_topics": list(self.summary_topics),
            "introduced": self.introduced,
            "redirect": self.redirect,
            "streak": self.streak,
            "topics": list(self.topics),
            "style": self.style,
            "style_hints": list(self.style_hints),
            "bridge": self.bridge.to_dict() if self.bridge else None,
        }
        return data

    @classmethod
    def from_state(cls, data: Mapping[str, Any] | None) -> TurnPlan | None:
        if not data:
            return None
        bridge = data.get("bridge")
        return cls(
            act=str(data["act"]),
            tiers=tuple(data.get("tiers") or ()),
            sentiment=str(data.get("sentiment") or "neutral"),
            strategy=tuple(data.get("strategy") or ("accompany",)),
            length=data.get("length") or "medium",
            language=data.get("language") or "es",
            register=data.get("register") or "formal",
            bridge=BridgeChoice(**bridge) if bridge else None,
            bridge_allowed=bool(data.get("bridge_allowed")),
            best_guess=bool(data.get("best_guess")),
            reason=data.get("reason"),
            topic=data.get("topic"),
            turn=int(data.get("turn") or 1),
            summary_topics=tuple(data.get("summary_topics") or ()),
            introduced=bool(data.get("introduced")),
            redirect=bool(data.get("redirect")),
            streak=int(data.get("streak") or 0),
            topics=tuple(data.get("topics") or ()),
            style=str(data.get("style") or "off"),
            style_hints=tuple(data.get("style_hints") or ()),
        )

    def render(self, topic_texts: Mapping[str, str] | None = None) -> str:
        """Bloque ``<plan>`` para el prompt de ``converse``.

        ``topic_texts`` traduce las claves de los temas sugeridos (``offer.topics``) a su texto.
        """
        lengths = {
            "short": "breve: una o dos frases",
            "medium": "media: dos a cuatro frases",
            "long": "completa: hasta seis frases",
        }
        lines = [
            f"acto: {self.act}",
            f"niveles: {', '.join(self.tiers) or 'social'}",
            f"emoción del visitante: {self.sentiment}",
            f"estrategia: {', '.join(self.strategy)}",
            f"longitud: {lengths[self.length]}",
            f"idioma: {self.language}",
            f"registro: {self.register}",
            f"puente: {'permitido (opcional)' if self.bridge else 'no'}",
        ]
        if self.reason:
            lines.append(f"motivo: {self.reason}")
        if self.topic:
            lines.append(f"tema ajeno: {self.topic}")
        if self.act == "closing" and self.summary_topics:
            lines.append(f"temas para el resumen: {', '.join(self.summary_topics)}")
        if self.introduced and self.act == "about_assistant":
            lines.append("ya te presentaste: no repitas la presentación completa, varía la forma")
        if self.best_guess:
            lines.append("aclaración repetida: responde con la interpretación más probable")
        if self.redirect:
            # Spec 035: empatía breve y siempre de vuelta a Manuelita (sin abrir charla ajena).
            lines.append(
                "regreso a Manuelita: obligatorio (termina con el puente, un tema concreto o las "
                "opciones)"
            )
            lines.append(
                "preguntas: solo sobre Manuelita; nada sobre el tema ajeno ni la vida personal"
            )
            lines.append(f"turnos ajenos seguidos: {self.streak}")
            if self.streak >= FOCUS_SHORT_STREAK:
                lines.append("máximo dos frases: cortesía breve y opciones de Manuelita")
            if self.topics and self.bridge is None:
                texts = [(topic_texts or {}).get(key, key) for key in self.topics]
                lines.append(f"temas sugeridos: {'; '.join(texts)}")
        return "<plan>\n" + "\n".join(lines) + "\n</plan>"


# Spec 035: actos en los que la respuesta debe volver a Manuelita y no abrir charla ajena.
FOCUS_ACTS = frozenset({"smalltalk", "off_topic", "minimal", "greeting"})
FOCUS_SHORT_STREAK = 3  # desde este turno ajeno seguido, máximo dos frases
FOCUS_EXEMPT_SENTIMENTS = frozenset({"distressed"})  # la angustia sigue el cuidado de la spec 019


def needs_redirect(act: str, turn: int, assent_to_offer: bool = False) -> bool:
    """¿Este turno debe terminar llevando la conversación a Manuelita? (spec 035, R3)."""
    if act not in FOCUS_ACTS:
        return False
    if act == "greeting":
        return turn > 1  # el primer saludo lo resuelve la presentación (spec 032)
    if act == "minimal":
        return not assent_to_offer
    return True


STRATEGIES: dict[str, tuple[str, ...]] = {
    "greeting": ("accompany",),
    "smalltalk": ("accompany",),
    "off_topic": ("decline", "accompany"),
    "manuelita": ("answer",),
    "complaint": ("empathize", "limit"),
    "correction": ("answer",),
    "minimal": ("accompany",),
    "about_assistant": ("answer",),
    "closing": ("farewell",),
    "thanks": ("accompany",),
    "clarify": ("clarify",),
}


def _act_for(signals: Mapping[str, Any] | None, decision: Mapping[str, Any]) -> tuple[str, bool]:
    act = str((signals or {}).get("act") or "")
    ruled = bool((signals or {}).get("act_ruled"))
    if act and ruled:
        return act, True
    proposed = decision.get("act")
    if proposed in DIALOGUE_ACTS:
        return str(proposed), False
    route = decision.get("route")
    reason = decision.get("scope_reason")
    if route == "clarify":
        return "clarify", False
    if route == "out_of_scope" and reason in {"off_topic", "advice", "unattainable"}:
        return "off_topic", False
    if route in {"documental", "structured", "mixed"}:
        return "manuelita", False
    return act or "smalltalk", False


def build_plan(
    signals: Mapping[str, Any] | None,
    decision: Mapping[str, Any],
    memory: Mapping[str, Any] | None,
    config: ConversationConfig,
    *,
    turn: int = 1,
    has_evidence: bool = False,
    topic: str | None = None,
    focus_topics: tuple[str, ...] = (),
    style: str = "off",
    style_hints: tuple[str, ...] = (),
) -> TurnPlan:
    """Plan determinista: mismas señales, decisión y memoria ⇒ mismo plan (C §2)."""
    del config  # los parámetros de generación no cambian el plan; se reserva para extensiones
    signals = signals or {}
    memory = memory or {}
    act, _ruled = _act_for(signals, decision)
    sentiment = str(signals.get("sentiment") or decision.get("sentiment") or "neutral")
    reason = decision.get("scope_reason")
    strategy = list(STRATEGIES[act])
    if reason == "unattainable":
        strategy = ["limit", "decline"]
    elif reason == "advice":
        strategy = ["decline"]
    if sentiment in NEGATIVE and "empathize" not in strategy:
        strategy.insert(0, "empathize")
    topics = tuple(memory.get("topics") or ())
    if act in {"minimal", "thanks", "greeting", "smalltalk", "about_assistant"}:
        length: Length = "short"
    elif act == "closing":
        length = "medium" if topics else "short"
    elif act in {"manuelita", "correction"} and has_evidence:
        length = "long"
    else:
        length = "medium"
    language = signals.get("language") or memory.get("language") or "es"
    register = (
        signals.get("register")
        if signals.get("register") == "informal"
        else memory.get("register") or signals.get("register") or "formal"
    )
    tiers = tuple(str(part.get("tier") or "social") for part in signals.get("requests") or [])
    # Spec 035: regreso a Manuelita, racha de turnos ajenos y temas sugeridos. Un «ok» o un
    # «jaja» después de un puente también vuelve a Manuelita (el plan no ve el texto, así que no
    # distingue el asentimiento de la risa; aceptar el puente con contenido lo resuelve el router).
    redirect = needs_redirect(act, turn) and sentiment not in FOCUS_EXEMPT_SENTIMENTS
    streak = int(memory.get("offtopic_streak") or 0) + 1 if redirect else 0
    if redirect and streak >= FOCUS_SHORT_STREAK:
        length = "short"
    return TurnPlan(
        act=act,
        tiers=tiers or ("social",),
        sentiment=sentiment,
        strategy=tuple(strategy),
        length=length,
        language=language,  # type: ignore[arg-type]
        register=register,  # type: ignore[arg-type]
        best_guess=bool(signals.get("best_guess")),
        reason=str(reason) if reason else None,
        topic=topic,
        turn=turn,
        summary_topics=topics[-4:] if act == "closing" else (),
        introduced=bool(memory.get("introduced")),
        redirect=redirect,
        streak=streak,
        topics=tuple(focus_topics) if redirect else (),
        style=style,
        style_hints=tuple(style_hints) if style != "off" else (),
    )
