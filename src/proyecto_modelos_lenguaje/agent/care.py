"""Habilidades de atención de Valer-IA Caña (spec 019, ``contracts/care-skills.md``).

Analiza cada mensaje sin modelo de lenguaje y compone las respuestas que no necesitan buscar:

- emoción, hostilidad, rechazo, crítica, crisis y solicitudes múltiples (``analyze``);
- temas ajenos, consejos profesionales y pedidos no atendibles, desde los guiones versionados de
  ``prompts/care.md`` (``compose``), con variantes que rotan en el hilo;
- el brief de atención para el modelo en las rutas con búsqueda (``brief``);
- el registro del contacto, o CRM, con etiquetas controladas y sin texto del visitante
  (``update_contact``).

El texto del visitante solo vive en las señales del turno y nunca se guarda en el registro.
"""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from typing import Any, Literal, TypedDict

from ..config import PROJECT_ROOT
from . import plan as turn_plan
from .config import CareConfig
from .privacy import find_pii, redact_pii
from .prompts import CarePlaybook
from .router import COMPANY, CONDUCT_PATTERNS
from .structured import normalize

PartKind = Literal["manuelita", "off_topic", "advice", "unattainable"]
Category = Literal[
    "manuelita", "off_topic", "advice", "complaint", "unattainable", "crisis", "conduct", "other"
]
Status = Literal[
    "resolved", "out_of_scope", "not_attainable", "needs_clarification", "referred", "no_evidence"
]
NEGATIVE = frozenset({"frustrated", "angry", "confused"})
GENERIC_TOPIC = "ese tema"


# ---------------------------------------------------------------- catálogo de temas ajenos


@dataclass(frozen=True, slots=True)
class TopicSpec:
    key: str
    label: str
    pattern: re.Pattern[str]
    kind: Literal["off_topic", "advice"]

    @property
    def bridge(self) -> str:
        return f"bridge.{self.key}"


def _topic(key: str, label: str, words: str, kind: str = "off_topic") -> TopicSpec:
    return TopicSpec(key, label, re.compile(rf"\b({words})\b"), kind)  # type: ignore[arg-type]


# Texto normalizado (minúsculas, sin tildes). Los consejos van primero: «invertir en bitcoin» es
# una inversión, no finanzas externas. Política va antes que deportes («partido político»).
TOPICS: tuple[TopicSpec, ...] = (
    _topic(
        "salud",
        "tu salud",
        r"medicamentos?|medicinas?|remedios?|sintomas?|dolor de \w+|enfermedad(es)?|gripa|"
        r"doctor|tratamiento medico|dieta|diabetes|que tomo para",
        "advice",
    ),
    _topic(
        "legal",
        "un tema legal",
        r"abogad[oa]|demanda judicial|demandar|divorcio|herencia|asesoria (legal|juridica)|"
        r"consulta legal|tutela|derecho de peticion",
        "advice",
    ),
    _topic(
        "inversion",
        "una inversión",
        r"invertir|comprar acciones|inversion en acciones|asesoria financiera|consejo financiero",
        "advice",
    ),
    _topic(
        "politica",
        "la política",
        r"elecciones|presidente de (colombia|estados unidos)|congreso|candidat[oa]s?|votar|"
        r"partido politico",
    ),
    _topic(
        "deportes",
        "los deportes",
        r"futbol|mundial|liga|partido de \w+|partido|seleccion colombia|gol(es)?|campeonato|"
        r"tenis|baloncesto|ciclismo",
    ),
    _topic(
        "finanzas_externas",
        "el mercado financiero",
        r"dolar|euro|bitcoin|tasa de cambio|trm|bolsa de valores|criptomonedas?|cripto",
    ),
    _topic(
        "programacion",
        "la programación",
        r"python|javascript|sql|codigo|programa en|funcion en|script|programar",
    ),
    _topic(
        "cocina",
        "la cocina",
        r"recetas?|postres?|cocinar|torta|ponque|galletas|preparar un|ingredientes",
    ),
    _topic(
        "tareas",
        "las tareas escolares",
        r"tareas?|colegio|ensayo|examen|universidad|ecuacion|matematicas",
    ),
    _topic(
        "entretenimiento",
        "el entretenimiento",
        r"peliculas?|series?|musica|cancion(es)?|netflix|chistes?|poemas?|cantante|novela",
    ),
    _topic(
        "viajes",
        "los viajes",
        r"viajes?|viajar|vuelos?|hotel(es)?|turismo|vacaciones|tiquetes?",
    ),
    _topic(
        "tecnologia",
        "la tecnología",
        r"celular|computador(a)?|internet|wifi|iphone|android|portatil|chatgpt|videojuegos?",
    ),
    _topic(
        "otras_empresas",
        "otras empresas",
        r"riopaila|incauca|mayaguez|coca ?cola|postobon|ecopetrol|nestle|bavaria",
    ),
    _topic("clima", "el clima", r"clima|llover|lluvia|llueve|temperatura|pronostico del tiempo"),
)
TOPIC_BY_KEY = {spec.key: spec for spec in TOPICS}


def match_topic(text: str) -> TopicSpec | None:
    """Primer tema del catálogo presente en el texto (se normaliza aquí)."""
    normalized = normalize(text)
    return next((spec for spec in TOPICS if spec.pattern.search(normalized)), None)


# ---------------------------------------------------------------- léxicos (texto normalizado)

CRISIS = re.compile(
    r"\b(quiero morir(me)?|me quiero morir|no quiero (seguir )?vivir|suicid\w*|"
    r"quitarme la vida|hacerme dano|lastimarme|matarme|me voy a matar|"
    r"ya no puedo mas con (la|mi) vida|no le encuentro sentido a (la|mi) vida)\b"
)
DISTRESSED = re.compile(
    r"\b(desesperad[oa]|no aguanto|no puedo mas|angustiad[oa]|estoy muy mal|me siento fatal)\b"
)
ANGRY = re.compile(
    r"\b(indignad[oa]|que rabia|me da rabia|furios[oa]|exijo|pesim[oa]|una verguenza|"
    r"vergonzoso|estoy hart[oa]|me tienen hart[oa]|inaceptable)\b"
)
FRUSTRATED = re.compile(
    r"\b(no sirven?|no funciona|nada funciona|llevo (media hora|horas|rato|un rato|dias)|"
    r"otra vez|lo mismo de nuevo|no encuentro|no encontre|no he podido|ya pregunte|ya te dije|"
    r"sigo sin|no me ayudas|que fastidio|perdiendo el tiempo|perdi el tiempo)\b"
)
CONFUSED = re.compile(
    r"\b(no entiendo|no entendi|no me queda claro|no comprendo|estoy confundid[oa]|me perdi|"
    r"como asi|explicame mejor|no le entiendo)\b"
)
SATISFIED = re.compile(
    r"\b(gracias|excelente|muy util|me sirvio|perfecto|genial|que bien|super|muy amable|"
    r"te agradezco)\b"
)
PRAISE = re.compile(r"\b(excelente|muy util|me sirvio|perfecto|genial|que bien|super|muy amable)\b")
REJECTION = re.compile(
    r"\b(eso no me sirve|no me sirve|no me ayudaste|no me ayuda|no es lo que (pedi|pregunte|busco)|"
    r"no me entiendes|no entiendes|eso no es lo que)\b"
)
SARCASM = re.compile(
    r"\b(gracias por nada|que buen servicio|vaya ayuda|que gran ayuda|si claro|aja si)\b"
)
CONCERN = re.compile(
    r"\b(contamina\w*|dano ambiental|danan el (medio )?ambiente|explota\w* a|explotacion|"
    r"abuso laboral|deforestacion|trabajo infantil|destruy\w*|queman|las quemas)\b"
)
QUESTION = re.compile(
    r"\?|\b(que|quien|quienes|cual|cuales|donde|cuando|como|cuanto|cuanta|cuantos|cuantas|"
    r"por que|dime|cuentame|explicame|quiero saber)\b"
)
ENGLISH = re.compile(r"\b(the|what|where|when|how|does|is|are|please|company|who)\b")
FAREWELL_WORDS = re.compile(r"\b(adios|chao|hasta luego|hasta pronto|nos vemos|eso es todo)\b")
ABUSE = dict(CONDUCT_PATTERNS)["abuse"]
ADVICE = dict(CONDUCT_PATTERNS)["advice"]

PRICING = re.compile(
    r"\b((hazme|dame|me das|me haces) (un )?descuento|descuentos?|cotizacion|cotizar|"
    r"cuanto (cuesta|cuestan|vale|valen)|precio de(l)? (\w+ )?(bulto|kilo|libra|azucar|arroba|"
    r"tonelada|producto)|quiero comprar|donde (compro|puedo comprar)|venderme|me vendes|"
    r"al por mayor)\b"
)
COMMITMENT = re.compile(
    r"\b(garantiza\w*|me prometes|prometeme|reembolso|devuelvanme|devuelveme|"
    r"devolucion de mi dinero|(consigueme|dame) (un )?(empleo|trabajo)|contratame|"
    r"me contratan)\b"
)
HUMAN = re.compile(
    r"\b(hablar con (una |un |alguna |algun )?(persona|humano|humana|asesor[a]?|agente|"
    r"operador[a]?|alguien)|pasame con|comunicame con|(quiero|necesito) (un |una )?asesor[a]?|"
    r"atencion humana)\b"
)
ETHICS = re.compile(r"\b(irregular\w*|fraude|denuncia\w*|corrupcion|soborno)\b")
DATA_PROTECTION = re.compile(r"\b(datos personales|habeas data|mis datos|proteccion de datos)\b")

# Separadores de solicitudes: «?», «;», saltos de línea, enumeraciones y conectores. La coma y la
# «y» solo separan si después viene una palabra interrogativa («…, dónde está y desde cuándo…»).
INTERROGATIVE = (
    r"(?:qu[eé]|qui[eé]n(?:es)?|cu[aá]l(?:es)?|d[oó]nde|cu[aá]ndo|c[oó]mo|cu[aá]nt[oa]s?|"
    r"desde cu[aá]ndo|por qu[eé]|a qui[eé]n)\b"
)
SPLITTER = re.compile(
    r"[?;\n]+|(?:^|\s)\d+[.)]\s+|(?:^|\n)\s*[-•]\s+|"
    r"\b(?:y tambi[eé]n|adem[aá]s|otra pregunta|por otro lado)\b|"
    rf",\s*(?=¿?{INTERROGATIVE})|\s(?:y|e)\s+(?=¿?{INTERROGATIVE})",
    re.IGNORECASE,
)
FILLER = frozenset(
    {
        *("y", "e", "o", "de", "del", "la", "el", "los", "las", "un", "una", "a", "al", "en"),
        *("por", "para", "con", "me", "mi", "te", "tu", "se", "lo", "le", "les", "hola"),
        *("buenas", "gracias", "pues", "bueno", "ok", "eres", "sos", "usted", "es", "son"),
        *("no", "nada", "muy", "tan", "sirves", "sirve", "que", "ya", "si"),
    }
)


def _content_words(normalized: str) -> list[str]:
    return [word for word in re.findall(r"[a-z0-9]+", normalized) if word not in FILLER]


# ---------------------------------------------------------------- señales del turno


class RequestPart(TypedDict, total=False):
    index: int
    text: str
    kind: PartKind
    topic_key: str | None
    unattainable_kind: str | None
    tier: str  # spec 020: social | external | manuelita


class CareSignals(TypedDict, total=False):
    enabled: bool
    sentiment: str
    hostile: bool
    hostile_only: bool
    rejection: bool
    sarcasm: bool
    concern: bool
    crisis: bool
    complaint_only: bool
    satisfied_only: bool
    language_other: bool
    requests: list[RequestPart]
    truncated: bool
    best_guess: bool
    opener_done: bool
    channel: str | None
    hostility_level: int
    complaint_streak: int
    escalation_at: int
    # spec 020: acto de diálogo, si lo fijó un léxico, idioma y registro del turno
    act: str
    act_ruled: bool
    greets: bool
    guided: bool
    language: str | None
    register: str


class CareState(TypedDict):
    used: dict[str, int]
    last_variant: dict[str, int]
    complaint_streak: int
    clarify_streak: int
    hostile_turns: int
    alternatives_offered: list[str]


def empty_care_state() -> CareState:
    return {
        "used": {},
        "last_variant": {},
        "complaint_streak": 0,
        "clarify_streak": 0,
        "hostile_turns": 0,
        "alternatives_offered": [],
    }


def copy_care_state(state: dict[str, Any] | None) -> CareState:
    base = empty_care_state()
    if state:
        base.update(
            used=dict(state.get("used") or {}),
            last_variant=dict(state.get("last_variant") or {}),
            complaint_streak=int(state.get("complaint_streak", 0)),
            clarify_streak=int(state.get("clarify_streak", 0)),
            hostile_turns=int(state.get("hostile_turns", 0)),
            alternatives_offered=list(state.get("alternatives_offered") or []),
        )
    return base


# ---------------------------------------------------------------- memoria del hilo (spec 020)

MEMORY_TOPICS = 20
TOPIC_LABEL = re.compile(r"^[a-záéíóúñü_]+( [a-záéíóúñü_]+){0,3}$")


class BridgeRecord(TypedDict):
    unit_id: str
    angle: str
    turn: int


class ConversationMemory(TypedDict):
    """Memoria estructurada del hilo (``data-model.md`` §2).

    ``thread_name`` vive solo aquí: nunca pasa a ``contact``, al Store ni a los informes.
    """

    topics: list[str]
    bridges_offered: list[BridgeRecord]
    bridge_rejected_at: int | None
    interest_after_rejection: bool
    last_bridge_turn: int | None
    offtopic_since_bridge: int
    corrections: int
    registers: list[str]
    register: str
    language: str
    thread_name: str | None
    introduced: bool  # ya se presentó como Valer-IA Caña (saludo o pregunta sobre ella)


def empty_conversation() -> ConversationMemory:
    return {
        "topics": [],
        "bridges_offered": [],
        "bridge_rejected_at": None,
        "interest_after_rejection": False,
        "last_bridge_turn": None,
        "offtopic_since_bridge": 0,
        "corrections": 0,
        "registers": [],
        "register": "formal",
        "language": "es",
        "thread_name": None,
        "introduced": False,
    }


def copy_conversation(memory: dict[str, Any] | None) -> ConversationMemory:
    base = empty_conversation()
    if memory:
        base.update(
            topics=list(memory.get("topics") or []),
            bridges_offered=[dict(b) for b in memory.get("bridges_offered") or []],  # type: ignore[misc]
            bridge_rejected_at=memory.get("bridge_rejected_at"),
            interest_after_rejection=bool(memory.get("interest_after_rejection")),
            last_bridge_turn=memory.get("last_bridge_turn"),
            offtopic_since_bridge=int(memory.get("offtopic_since_bridge") or 0),
            corrections=int(memory.get("corrections") or 0),
            registers=list(memory.get("registers") or []),
            register=str(memory.get("register") or "formal"),
            language=str(memory.get("language") or "es"),
            thread_name=memory.get("thread_name"),
            introduced=bool(memory.get("introduced")),
        )
    return base


ACCEPTANCE = re.compile(
    r"\b(si,? (cuentame|dime|claro|por favor)|cuentame (mas|sobre)|me interesa|dale,? cuentame|"
    r"quiero saber (mas|sobre)|sure|tell me more)\b"
)
BRIDGE_REJECTION = re.compile(
    r"\b(no me interesa|no gracias|no,? gracias|no quiero saber|deja de (ofrecer|recomendar)|"
    r"no me importa|eso no me interesa|no me hables de manuelita)\b"
)


def memory_topics(signals: CareSignals | None, decision: dict[str, Any]) -> list[str]:
    """Etiquetas de tema del turno (catálogo o tema del oro), sin texto del visitante."""
    labels: list[str] = []
    for part in (signals or {}).get("requests") or []:
        if part.get("topic_key"):
            labels.append(str(part["topic_key"]))
        elif part.get("tier") == "manuelita" and part.get("text"):
            labels.append(manuelita_topic(str(part["text"])))
    if not labels and decision.get("topic"):
        spec = match_topic(str(decision["topic"]))
        if spec is not None:
            labels.append(spec.key)
    return [label for label in labels if label and label != "otro" and TOPIC_LABEL.match(label)]


def update_conversation(
    memory: ConversationMemory,
    *,
    message: str,
    signals: CareSignals | None,
    decision: dict[str, Any],
    act: str,
    turn: int,
    bridged: dict[str, Any] | None,
    name: str | None = None,
) -> ConversationMemory:
    """Transiciones de ``data-model.md`` §2 tras un turno del modo guiado."""
    text = normalize(message)
    for label in memory_topics(signals, decision):
        if label in memory["topics"]:
            memory["topics"].remove(label)
        memory["topics"].append(label)
    memory["topics"] = memory["topics"][-MEMORY_TOPICS:]
    if act == "correction":
        memory["corrections"] += 1
    previous_bridge = bool(memory["bridges_offered"]) and memory["bridges_offered"][-1]["turn"] == (
        turn - 1
    )
    rejected = BRIDGE_REJECTION.search(text) is not None
    if rejected or (previous_bridge and (signals or {}).get("rejection")):
        memory["bridge_rejected_at"] = turn
        memory["interest_after_rejection"] = False
    elif memory["bridge_rejected_at"] is not None and (
        ACCEPTANCE.search(text) or act in {"manuelita", "correction"}
    ):
        memory["interest_after_rejection"] = True
    if bridged:
        memory["bridges_offered"].append(
            {"unit_id": str(bridged["unit_id"]), "angle": str(bridged["angle"]), "turn": turn}
        )
        memory["last_bridge_turn"] = turn
        memory["offtopic_since_bridge"] = 0
    elif act in {"off_topic", "smalltalk"}:
        memory["offtopic_since_bridge"] += 1
    register = str((signals or {}).get("register") or "formal")
    memory["registers"] = [*memory["registers"], register][-3:]
    informal = sum(1 for r in memory["registers"] if r == "informal")
    memory["register"] = "informal" if informal * 2 > len(memory["registers"]) else "formal"
    language = (signals or {}).get("language")
    if language:
        memory["language"] = str(language)
    if name:
        memory["thread_name"] = name[:40]
    if act in {"greeting", "about_assistant"}:
        memory["introduced"] = True
    return memory


def render_memory(memory: ConversationMemory | None) -> str:
    """Bloque ``<memoria>`` para ``converse`` y el brief: etiquetas, sin texto del visitante."""
    if not memory:
        return ""
    lines: list[str] = []
    if memory["topics"]:
        lines.append(f"temas tratados: {', '.join(memory['topics'][-8:])}")
    if memory["bridges_offered"]:
        angles = ", ".join(dict.fromkeys(b["angle"] for b in memory["bridges_offered"]))
        lines.append(f"ya ofreciste temas de Manuelita sobre: {angles} (no los repitas)")
    if memory["bridge_rejected_at"] is not None and not memory["interest_after_rejection"]:
        lines.append("el visitante rechazó las sugerencias: no ofrezcas temas nuevos")
    if memory["corrections"]:
        lines.append(f"correcciones del visitante: {memory['corrections']}")
    if memory["thread_name"]:
        lines.append(f"nombre que dio en esta conversación: {memory['thread_name']}")
    if not lines:
        return ""
    return "<memoria>\n" + "\n".join(lines) + "\n</memoria>"


def split_requests(message: str, max_requests: int = 5) -> tuple[list[str], bool]:
    """Solicitudes de un mensaje (como máximo ``max_requests``) y si hubo más."""
    pieces = [piece.strip(" ¿¡,.:") for piece in SPLITTER.split(message or "") if piece]
    parts = [piece for piece in pieces if _content_words(normalize(piece))]
    if len(parts) > 1:
        # Con varias piezas solo cuentan los pedidos: «Me llamo Ana» no es una solicitud.
        parts = [part for part in parts if _is_request(part)]
    if not parts:
        parts = [(message or "").strip()]
    return parts[:max_requests], len(parts) > max_requests


REQUEST_CUES = re.compile(
    r"\b(quiero|quisiera|necesito|dame|dime|cuentame|explicame|hazme|pasame|me gustaria|"
    r"puedes|podrias|me ayudas|ayudame|busco)\b"
)


def _is_request(text: str) -> bool:
    normalized = normalize(text)
    return bool(
        QUESTION.search(normalized)
        or REQUEST_CUES.search(normalized)
        or match_topic(normalized)
        or PRICING.search(normalized)
        or COMMITMENT.search(normalized)
        or HUMAN.search(normalized)
    )


EXCLAMATIVE = re.compile(
    r"^[¡ ]*(que|como|cuanto) (calor|frio|pereza|sueno|hambre|rico|rica|bueno|buena|bonito|"
    r"bonita|lindo|linda|chevere|bacano|maluco|feo|fea|horrible|genial|bien|mal|dia|tarde|"
    r"noche|tan|mas|lluvia|sol|cansancio|risa|nervios|alegria|emocion|susto|miedo)\b"
)


def part_tier(text: str, kind: PartKind, *, asked: bool = False) -> str:
    """Nivel de contenido de una parte (spec 020, R3).

    - ``external``: tema ajeno, consejo profesional o pedido no atendible;
    - ``manuelita``: menciona la empresa, o es un pedido sin tema ajeno;
    - ``social``: afirmación, exclamación, saludo, risa o emoji sin pedido.

    ``asked`` indica que el mensaje original traía «?» (``split_requests`` lo quita).
    """
    if kind != "manuelita":
        return "external"
    normalized = normalize(text)
    if COMPANY.search(normalized) or asked or "?" in text:
        return "manuelita"
    # «¡Qué calor hace!»: una exclamación con «qué» o «cómo» no es una pregunta.
    exclamation = not REQUEST_CUES.search(normalized) and (
        "!" in text or EXCLAMATIVE.match(normalized) is not None
    )
    if _is_request(text) and not exclamation:
        return "manuelita"
    return "social"


def classify_part(text: str) -> tuple[PartKind, str | None, str | None]:
    """Tipo de una solicitud: Manuelita, tema ajeno, consejo o pedido no atendible."""
    normalized = normalize(text)
    for kind, pattern in (("pricing", PRICING), ("commitment", COMMITMENT), ("human", HUMAN)):
        if pattern.search(normalized):
            return "unattainable", None, kind
    spec = match_topic(normalized)
    if spec is not None and not COMPANY.search(normalized):
        return spec.kind, spec.key, None
    return "manuelita", None, None


def detect_crisis(message: str) -> bool:
    return CRISIS.search(normalize(message)) is not None


def detect_sentiment(message: str) -> tuple[str, dict[str, bool]]:
    """Emoción del visitante y banderas de rechazo, sarcasmo, crítica y hostilidad."""
    text = normalize(message)
    flags = {
        "rejection": REJECTION.search(text) is not None,
        "sarcasm": SARCASM.search(text) is not None
        or (re.search(r"\bjaja+\b", text) is not None and FRUSTRATED.search(text) is not None),
        "concern": CONCERN.search(text) is not None,
        "hostile": ABUSE.search(text) is not None,
    }
    if DISTRESSED.search(text):
        sentiment = "distressed"
    elif flags["hostile"] or ANGRY.search(text):
        sentiment = "angry"
    elif flags["sarcasm"] or flags["rejection"] or FRUSTRATED.search(text):
        sentiment = "frustrated"
    elif CONFUSED.search(text):
        sentiment = "confused"
    elif SATISFIED.search(text):
        sentiment = "satisfied"
    else:
        sentiment = "neutral"
    return sentiment, flags


def analyze(message: str, care_state: CareState, config: CareConfig) -> CareSignals:
    """Señales del turno: emoción, banderas, crisis y solicitudes clasificadas."""
    text = normalize(message)
    sentiment, flags = detect_sentiment(message)
    texts, truncated = split_requests(message, config.max_requests)
    requests: list[RequestPart] = []
    for index, part in enumerate(texts, start=1):
        kind, topic_key, unattainable = classify_part(part)
        requests.append(
            {
                "index": index,
                "text": part,
                "kind": kind,
                "topic_key": topic_key,
                "unattainable_kind": unattainable,
                "tier": part_tier(part, kind, asked="?" in message),
            }
        )
    asks = QUESTION.search(text) is not None or COMPANY.search(text) is not None
    has_topic = match_topic(text) is not None
    without_insults = ABUSE.sub(" ", text)
    hostile_only = flags["hostile"] and not (
        QUESTION.search(without_insults)
        or COMPANY.search(without_insults)
        or match_topic(without_insults)
        or len(_content_words(without_insults)) >= 5
    )
    negative = sentiment in NEGATIVE or flags["rejection"]
    complaint_only = (
        negative and not flags["hostile"] and not asks and not has_topic and not flags["concern"]
    )
    english = len(ENGLISH.findall(text)) >= 2 and not re.search(r"\b(que|el|la|de|es)\b", text)
    signals: CareSignals = {
        "enabled": config.enabled,
        "sentiment": sentiment,
        "hostile": flags["hostile"],
        "hostile_only": bool(hostile_only),
        "rejection": flags["rejection"],
        "sarcasm": flags["sarcasm"],
        "concern": flags["concern"],
        "crisis": CRISIS.search(text) is not None,
        "complaint_only": complaint_only,
        "satisfied_only": sentiment == "satisfied"
        and PRAISE.search(text) is not None
        and not asks
        and not FAREWELL_WORDS.search(text),
        "language_other": english,
        "requests": requests,
        "truncated": truncated,
        "best_guess": False,
        "opener_done": False,
        "channel": channel_key(message),
        "greets": turn_plan.GREETING.search(text) is not None,
        "language": turn_plan.detect_language(message),
        "register": turn_plan.detect_register(message),
    }
    act, ruled = turn_plan.detect_act(message, signals)
    signals["act"] = act
    signals["act_ruled"] = ruled
    return signals


def update_counters(signals: CareSignals, care_state: CareState, config: CareConfig) -> None:
    """Rachas del hilo: quejas seguidas y turnos hostiles (antes de responder)."""
    if signals.get("hostile"):
        care_state["hostile_turns"] += 1
    complaint = signals.get("complaint_only") or signals.get("rejection")
    care_state["complaint_streak"] = care_state["complaint_streak"] + 1 if complaint else 0
    signals["hostility_level"] = min(care_state["hostile_turns"], config.hostility_levels)
    signals["escalation_at"] = config.complaint_escalation
    signals["complaint_streak"] = care_state["complaint_streak"]


def strip_texts(signals: CareSignals | None) -> CareSignals | None:
    """Quita el texto de las solicitudes: solo vive mientras dura el turno."""
    if not signals:
        return signals
    cleaned: CareSignals = {**signals}  # type: ignore[typeddict-item]
    cleaned["requests"] = [{**part, "text": ""} for part in signals.get("requests") or []]
    return cleaned


# ---------------------------------------------------------------- guiones y composición


def pick(playbook: CarePlaybook, key: str, care_state: CareState, **values: str) -> str:
    """Variante de ``key`` con rotación determinista que no repite la anterior."""
    variants = playbook.variants[key]
    used = care_state["used"].get(key, 0)
    index = used % len(variants)
    if len(variants) > 1 and index == care_state["last_variant"].get(key):
        index = (index + 1) % len(variants)
    care_state["used"][key] = used + 1
    care_state["last_variant"][key] = index
    text = variants[index]
    for name, value in values.items():
        text = text.replace("{" + name + "}", value)
    return text


class Composer:
    """Arma una respuesta con citas ``[U#]`` a los puentes y canales del guion."""

    def __init__(self, playbook: CarePlaybook, care_state: CareState) -> None:
        self.playbook = playbook
        self.care_state = care_state
        self.sentences: list[str] = []
        self.citations: list[dict[str, Any]] = []

    def say(self, key: str, **values: str) -> str:
        text = pick(self.playbook, key, self.care_state, **values)
        citation = self.playbook.citations.get(key)
        if citation is not None:
            label = self._label(citation.unit_id, citation.url, citation.title)
            text = cite(text, label)
        self.sentences.append(text)
        return text

    def add(self, text: str) -> None:
        if text:
            self.sentences.append(text)

    def _label(self, unit_id: str, url: str, title: str) -> str:
        for existing in self.citations:
            if existing["unit_id"] == unit_id:
                return str(existing["label"])
        label = f"U{len(self.citations) + 1}"
        self.citations.append({"label": label, "unit_id": unit_id, "url": url, "title": title})
        return label

    def result(self) -> tuple[str, list[dict[str, Any]]]:
        return " ".join(self.sentences), self.citations


def cite(text: str, label: str) -> str:
    """Pone ``[U#]`` antes del punto final de la frase."""
    stripped = text.rstrip()
    if stripped.endswith((".", "!", "?")):
        return f"{stripped[:-1]} [{label}]{stripped[-1]}"
    return f"{stripped} [{label}]"


def topic_label(signals: CareSignals | None, decision: dict[str, Any]) -> tuple[str, str | None]:
    """Etiqueta que se dice al visitante y clave del catálogo (si la hay)."""
    parts = [p for p in (signals or {}).get("requests") or [] if p.get("topic_key")]
    keys = list(dict.fromkeys(str(p["topic_key"]) for p in parts))
    if keys:
        labels = [TOPIC_BY_KEY[key].label for key in keys[:2]]
        return " y ".join(labels), keys[0]
    raw = decision.get("topic")
    if raw:
        spec = match_topic(str(raw))
        if spec is not None:
            return spec.label, spec.key
        sanitized = sanitize_topic(str(raw))
        if sanitized:
            return sanitized, None
    return GENERIC_TOPIC, None


def sanitize_topic(raw: str | None) -> str | None:
    """Etiqueta libre del enrutador LLM: corta, sin símbolos ni datos personales."""
    if not raw:
        return None
    topic = " ".join(str(raw).lower().split())
    if len(topic) > 40 or re.fullmatch(r"[a-záéíóúñü]+( [a-záéíóúñü]+){0,3}", topic) is None:
        return None
    if redact_pii(topic) != topic or find_pii(topic):
        return None
    return topic


def channel_key(message: str) -> str:
    text = normalize(message)
    if DATA_PROTECTION.search(text):
        return "channel.data_protection"
    if ETHICS.search(text):
        return "channel.ethics_line"
    return "channel.website"


def _opener(composer: Composer, signals: CareSignals | None) -> None:
    sentiment = (signals or {}).get("sentiment")
    if sentiment in NEGATIVE:
        composer.say(f"opener.{sentiment}")
        if signals is not None:
            signals["opener_done"] = True


DEFAULT_BRIDGE = "default"


def say_bridge(composer: Composer, bridge: Any) -> None:
    """Puente elegido por ``bridges.py`` (spec 020): guion curado o unidad del oro, con cita."""
    key = getattr(bridge, "key", None)
    if key and key in composer.playbook.variants:
        composer.say(key)
        return
    label = composer._label(bridge.unit_id, bridge.url, bridge.title)
    composer.add(cite(f"Si te interesa, puedo contarte sobre «{bridge.title}».", label))


def compose_out_of_scope(
    signals: CareSignals | None,
    decision: dict[str, Any],
    playbook: CarePlaybook,
    care_state: CareState,
    bridge: Any = DEFAULT_BRIDGE,
) -> tuple[str, list[dict[str, Any]]]:
    """Tema ajeno, consejo o pedido no atendible (R1, R8).

    ``bridge`` (spec 020): ``"default"`` mantiene el puente por tema de la spec 019; un
    ``BridgeChoice`` usa ese puente y ``None`` omite el puente (cuota, molestia o rechazo).
    """
    composer = Composer(playbook, care_state)
    reason = decision.get("scope_reason") or "off_topic"
    _opener(composer, signals)
    if reason == "unattainable":
        kind = decision.get("kind") or _first_unattainable(signals) or "commitment"
        composer.say(f"boundary.{kind}")
        composer.say("offer.positive")
        composer.say((signals or {}).get("channel") or "channel.website")
        composer.say("close")
        return composer.result()
    label, key = topic_label(signals, decision)
    composer.say("ack.advice" if reason == "advice" else "ack.off_topic", topic=label)
    composer.say("boundary.advice" if reason == "advice" else "boundary.off_topic")
    if bridge is None:
        composer.say("offer.positive")
        return composer.result()
    if bridge == DEFAULT_BRIDGE:
        section = (
            f"bridge.{key}" if key and f"bridge.{key}" in playbook.variants else "bridge.default"
        )
        composer.say(section)
    else:
        say_bridge(composer, bridge)
    composer.say("close")
    return composer.result()


def _first_unattainable(signals: CareSignals | None) -> str | None:
    for part in (signals or {}).get("requests") or []:
        if part.get("unattainable_kind"):
            return str(part["unattainable_kind"])
    return None


def compose_complaint(
    signals: CareSignals, playbook: CarePlaybook, care_state: CareState
) -> tuple[str, list[dict[str, Any]]]:
    """Queja o rechazo sin consulta: empatía, alternativas que no se repiten y escalamiento."""
    composer = Composer(playbook, care_state)
    channel = signals.get("channel") or "channel.website"
    if care_state["complaint_streak"] >= int(signals.get("escalation_at") or 3):
        channel_text = Composer(playbook, care_state)
        sentence = channel_text.say(channel)
        composer.citations = channel_text.citations
        composer.add(pick(playbook, "complaint.escalation", care_state, channel=sentence))
        signals["opener_done"] = True
        return composer.result()
    if signals.get("rejection") or care_state["complaint_streak"] >= 2:
        offered = care_state["alternatives_offered"]
        options = ("rejection.rephrase", "rejection.related_topics", "rejection.official_channel")
        choice = next((key for key in options if key not in offered), options[-1])
        offered.append(choice)
        if choice == "rejection.official_channel":
            channel_text = Composer(playbook, care_state)
            sentence = channel_text.say(channel)
            composer.citations = channel_text.citations
            composer.add(pick(playbook, choice, care_state, channel=sentence))
        else:
            composer.say(choice)
        signals["opener_done"] = True
        return composer.result()
    _opener(composer, signals)
    composer.say("complaint.help")
    return composer.result()


def compose_clarify(
    signals: CareSignals | None, playbook: CarePlaybook, care_state: CareState
) -> tuple[str, list[dict[str, Any]]]:
    """Una sola pregunta de aclaración con opciones concretas (R10)."""
    composer = Composer(playbook, care_state)
    options = pick(playbook, "clarify.options.default", care_state)
    composer.add(pick(playbook, "clarify.intro", care_state, options=options))
    return composer.result()


def crisis_reply(playbook: CarePlaybook, care_state: CareState) -> str:
    return pick(playbook, "crisis", care_state)


def decline_part(part: RequestPart, playbook: CarePlaybook, care_state: CareState) -> str:
    """Declinación breve de una parte ajena dentro de un turno con búsqueda."""
    if part.get("kind") == "unattainable":
        label = UNATTAINABLE_LABELS.get(str(part.get("unattainable_kind")), GENERIC_TOPIC)
    else:
        spec = TOPIC_BY_KEY.get(str(part.get("topic_key")))
        label = spec.label if spec else GENERIC_TOPIC
    return pick(playbook, "decline.part", care_state, topic=label)


UNATTAINABLE_LABELS = {
    "pricing": "precios y descuentos",
    "commitment": "compromisos en nombre de la empresa",
    "human": "hablar con una persona",
}


# ---------------------------------------------------------------- antepuestos y brief


def prefixes(
    signals: CareSignals | None,
    decision: dict[str, Any],
    playbook: CarePlaybook,
    care_state: CareState,
    *,
    guided: bool = False,
) -> tuple[list[str], list[str]]:
    """Frases antes de la respuesta (límite por hostilidad y apertura empática) y avisos.

    En el modo guiado (spec 020, C §6) el modelo redacta la apertura empática y responde en el
    idioma del visitante: aquí solo queda el límite por hostilidad.
    """
    if not signals or not signals.get("enabled", True):
        return [], []
    reason = decision.get("scope_reason")
    if reason == "crisis":
        return [], ["crisis"]
    texts: list[str] = []
    notices: list[str] = []
    if signals.get("hostile") and reason != "abuse":
        level = max(1, int(signals.get("hostility_level") or 1))
        texts.append(pick(playbook, f"hostility.{level}", care_state))
        notices.append("hostility_limit")
    if guided:
        return texts, notices
    if not signals.get("opener_done") and reason not in CONDUCT_REASONS:
        sentiment = signals.get("sentiment")
        key = (
            f"opener.{sentiment}" if sentiment in NEGATIVE and not signals.get("hostile") else None
        )
        if key is None and signals.get("concern"):
            key = "opener.concern"
        if key is not None:
            texts.append(pick(playbook, key, care_state))
            signals["opener_done"] = True
    if signals.get("opener_done"):
        notices.append("empathy_opener")
    if signals.get("language_other"):
        texts.insert(0, pick(playbook, "language.other", care_state))
    return texts, notices


def suffixes(
    signals: CareSignals | None,
    decision: dict[str, Any],
    playbook: CarePlaybook,
    care_state: CareState,
    *,
    retrieval: bool,
    guided: bool = False,
) -> tuple[list[str], list[str]]:
    """Declinaciones de partes ajenas, aviso de solicitudes truncadas y mejor interpretación."""
    if not signals or not signals.get("enabled", True) or decision.get("scope_reason") == "crisis":
        return [], []
    texts: list[str] = []
    notices: list[str] = []
    if retrieval:
        for part in signals.get("requests") or []:
            if part.get("kind") != "manuelita" and not guided:
                texts.append(decline_part(part, playbook, care_state))
        if signals.get("truncated"):
            texts.append(pick(playbook, "truncated", care_state))
    if signals.get("best_guess"):
        texts.append(pick(playbook, "best_guess.suffix", care_state))
        notices.append("best_guess")
    return texts, notices


CONDUCT_REASONS = frozenset({"third_party", "prompt_extraction", "harmful", "abuse", "identity"})


def manuelita_parts(signals: CareSignals | None) -> list[RequestPart]:
    return [p for p in (signals or {}).get("requests") or [] if p.get("kind") == "manuelita"]


SENTIMENT_LABELS = {
    "neutral": "neutral",
    "satisfied": "satisfecho",
    "confused": "confundido",
    "frustrated": "frustrado",
    "angry": "molesto",
    "distressed": "angustiado",
}


LANGUAGE_LABELS = {"en": "inglés", "other": "el idioma del visitante"}


def brief(
    signals: CareSignals | None,
    care_state: CareState,
    previous_route: str | None,
    *,
    guided: bool = False,
    memory: ConversationMemory | None = None,
) -> str:
    """Bloque «Atención:» para el modelo en las rutas con búsqueda (contracts/care-skills.md).

    Con ``guided`` (spec 020, C §5) el modelo redacta una sola respuesta fluida: acompaña lo
    social, declina lo externo con sus palabras, responde en el idioma y el registro del visitante
    y abre reconociendo la emoción.
    """
    if not signals or not signals.get("enabled", True):
        return ""
    if guided:
        return _guided_brief(signals, care_state, previous_route, memory)
    parts = manuelita_parts(signals)
    foreign = [p for p in signals.get("requests") or [] if p.get("kind") != "manuelita"]
    sentiment = str(signals.get("sentiment") or "neutral")
    rephrase = previous_route in {"clarify", "fallback"} or care_state["complaint_streak"] >= 2
    plain = len(parts) <= 1 and not foreign and sentiment == "neutral"
    if plain and not rephrase and not signals.get("concern"):
        return ""
    lines = ["Atención:"]
    if parts:
        lines.append("- Solicitudes a responder en orden:")
        lines.extend(f"  {i}) {redact_pii(p['text'])}" for i, p in enumerate(parts, start=1))
    if foreign:
        labels = []
        for part in foreign:
            spec = TOPIC_BY_KEY.get(str(part.get("topic_key")))
            labels.append(
                spec.label
                if spec
                else UNATTAINABLE_LABELS.get(str(part.get("unattainable_kind")), GENERIC_TOPIC)
            )
        lines.append(
            "- Partes ajenas (no las respondas, el sistema las declina): " + ", ".join(labels)
        )
    if sentiment != "neutral":
        note = (
            " (el sistema ya abre con una frase empática; no la repitas)"
            if (sentiment in NEGATIVE)
            else ""
        )
        lines.append(f"- Estado del visitante: {SENTIMENT_LABELS[sentiment]}{note}")
    if rephrase:
        lines.append("- Retoma en una frase lo que entendiste antes de responder.")
    if signals.get("concern"):
        lines.append(
            "- Es una crítica: responde con equilibrio, solo con lo que documenta la evidencia."
        )
    return "\n".join(lines)


# ---------------------------------------------------------------- contactos inventados

EMAIL = re.compile(r"[\w.+-]+@[\w-]+(?:\.[\w-]+)+")
# Teléfonos: móviles y fijos de Colombia, líneas 01 8000 e indicativo entre paréntesis. Las cifras
# con puntos de miles («7.476.475») no son teléfonos.
PHONE = re.compile(
    r"(?<![\w.])(?:\+?57[\s-]?)?(?:3\d{2}[\s-]?\d{3}[\s-]?\d{4}|60\d[\s-]?\d{3}[\s-]?\d{4}|"
    r"01[\s-]?8000[\s-]?\d{2,3}[\s-]?\d{3,4}|\(\d{1,2}\)[\s-]?\d{3}[\s-]?\d{4})(?![\w.])"
)


def allowed_contacts(playbook: CarePlaybook) -> set[str]:
    """Correos y teléfonos que aparecen en los canales citados del guion."""
    allowed: set[str] = set()
    for key, variants in playbook.variants.items():
        if key.startswith("channel.") or key == "crisis":
            for variant in variants:
                allowed.update(email.lower() for email in EMAIL.findall(variant))
    return allowed


def invented_contacts(text: str, playbook: CarePlaybook, evidence: str = "") -> list[str]:
    """Correos o teléfonos de la respuesta que no salen de un canal citado ni de la evidencia."""
    allowed = allowed_contacts(playbook)
    source = evidence.lower()
    found = [
        email
        for email in EMAIL.findall(text)
        if email.lower() not in allowed and email.lower() not in source
    ]
    found += [phone for phone in PHONE.findall(text) if phone not in evidence]
    return found


def replace_contacts(text: str, contacts: list[str]) -> str:
    for contact in contacts:
        text = text.replace(contact, "los canales oficiales de www.manuelita.com")
    return text


# ---------------------------------------------------------------- registro del contacto (CRM)


class ContactRequest(TypedDict):
    turn: int
    category: str
    topic: str
    status: str


class ContactRecord(TypedDict):
    version: str
    opened_at: str
    updated_at: str
    turns: int
    requests: list[ContactRequest]
    sentiments: list[str]
    motive: list[str]
    resolved: bool
    hostile_turns: int
    crisis: bool
    acts: list[dict[str, Any]]  # spec 020: {act, bridged, reviewed} por turno, máximo 50


MAX_CONTACT_ACTS = 50


def empty_contact() -> ContactRecord:
    now = datetime.now(UTC).isoformat()
    return {
        "version": "1.0",
        "opened_at": now,
        "updated_at": now,
        "turns": 0,
        "requests": [],
        "sentiments": [],
        "motive": [],
        "resolved": True,
        "hostile_turns": 0,
        "crisis": False,
        "acts": [],
    }


@lru_cache(maxsize=1)
def _taxonomy() -> tuple[tuple[str, tuple[str, ...]], ...]:
    """Temas del oro (``config/gold_taxonomy.toml``) con sus palabras clave normalizadas."""
    path = PROJECT_ROOT / "config" / "gold_taxonomy.toml"
    try:
        document = tomllib.loads(path.read_text(encoding="utf-8"))
    except OSError, tomllib.TOMLDecodeError:
        return ()
    return tuple(
        (str(topic["id"]), tuple(normalize(str(k)) for k in topic.get("keywords") or []))
        for topic in document.get("topics") or []
        if topic.get("id")
    )


def manuelita_topic(text: str) -> str:
    """Tema del oro de una solicitud de Manuelita, por palabras clave de la taxonomía."""
    normalized = normalize(text)
    best, hits = "otro", 0
    for topic_id, keywords in _taxonomy():
        # Raíz de cada palabra clave: «producto» también reconoce «produce» y «productos».
        count = sum(
            1 for k in keywords if re.search(rf"\b{re.escape(k[: max(4, len(k) - 2)])}", normalized)
        )
        if count > hits:
            best, hits = topic_id, count
    return best


RESOLVED_STATUSES = frozenset({"resolved", "out_of_scope", "referred"})


def turn_requests(
    *,
    turn: int,
    signals: CareSignals | None,
    decision: dict[str, Any],
    citations: list[dict[str, Any]],
    fallback: bool,
    action: bool,
) -> list[ContactRequest]:
    """Solicitudes del turno con categoría, tema controlado y estado (data-model.md)."""
    route = decision.get("route")
    reason = decision.get("scope_reason")

    def request(category: str, topic: str, status: str) -> ContactRequest:
        return {"turn": turn, "category": category, "topic": topic, "status": status}

    if action:
        return [request("other", "memoria", "resolved")]
    if reason == "crisis":
        return [request("crisis", "apoyo", "referred")]
    if reason == "identity":
        return [request("other", "identidad", "resolved")]
    if reason in {"third_party", "prompt_extraction", "harmful", "abuse"}:
        return [request("conduct", str(reason), "out_of_scope")]
    parts = list((signals or {}).get("requests") or [])
    if reason == "unattainable":
        kind = decision.get("kind") or _first_unattainable(signals) or "commitment"
        status = "referred" if citations else "not_attainable"
        return [request("unattainable", str(kind), status)]
    if reason in {"off_topic", "advice"}:
        foreign = [p for p in parts if p.get("kind") in {"off_topic", "advice"}]
        if not foreign:
            spec = match_topic(str(decision.get("topic") or ""))
            return [request(str(reason), spec.key if spec else "otro", "out_of_scope")]
        return [
            request(str(p["kind"]), str(p.get("topic_key") or "otro"), "out_of_scope")
            for p in foreign
        ]
    if signals and signals.get("complaint_only"):
        escalated = bool(citations)
        return [
            request("complaint", "atencion", "referred" if escalated else "needs_clarification")
        ]
    if route == "clarify":
        return [request("manuelita", "otro", "needs_clarification")]
    if route == "direct":
        return [request("other", "conversacion", "resolved")]
    status = "resolved" if citations and not fallback else "no_evidence"
    category = "complaint" if signals and signals.get("concern") else "manuelita"
    rows = [
        request(category, manuelita_topic(str(p.get("text", ""))), status)
        for p in manuelita_parts(signals)
    ] or [request(category, "otro", status)]
    for part in parts:
        if part.get("kind") == "unattainable":
            rows.append(
                request("unattainable", str(part.get("unattainable_kind")), "not_attainable")
            )
        elif part.get("kind") in {"off_topic", "advice"}:
            rows.append(request(str(part["kind"]), str(part.get("topic_key")), "out_of_scope"))
    return rows


def update_contact(
    record: dict[str, Any] | None,
    *,
    signals: CareSignals | None,
    decision: dict[str, Any],
    citations: list[dict[str, Any]],
    fallback: bool,
    care_state: CareState,
    action: bool = False,
    act: dict[str, Any] | None = None,
) -> ContactRecord:
    """Registro del contacto tras el turno: sin ``user_id``, nombres ni texto del visitante."""
    current: ContactRecord = {**empty_contact(), **(record or {})}  # type: ignore[typeddict-item]
    turn = current["turns"] + 1
    rows = turn_requests(
        turn=turn,
        signals=signals,
        decision=decision,
        citations=citations,
        fallback=fallback,
        action=action,
    )
    motive = list(current["motive"])
    for row in rows:
        if row["topic"] not in motive and len(motive) < 5:
            motive.append(row["topic"])
    current.update(
        turns=turn,
        updated_at=datetime.now(UTC).isoformat(),
        requests=[*current["requests"], *rows],
        sentiments=[*current["sentiments"], str((signals or {}).get("sentiment") or "neutral")],
        motive=motive,
        resolved=all(row["status"] in RESOLVED_STATUSES for row in rows),
        hostile_turns=care_state["hostile_turns"],
        crisis=current["crisis"] or decision.get("scope_reason") == "crisis",
    )
    if act is not None:
        # Solo etiquetas controladas: el acto, si hubo puente y qué hizo la revisión.
        entry = {
            "act": str(act.get("act") or "smalltalk"),
            "bridged": bool(act.get("bridged")),
            "reviewed": str(act.get("reviewed") or "show"),
        }
        current["acts"] = [*(current.get("acts") or []), entry][-MAX_CONTACT_ACTS:]
    return current


def _part_label(part: RequestPart) -> str:
    spec = TOPIC_BY_KEY.get(str(part.get("topic_key")))
    if spec is not None:
        return spec.label
    return UNATTAINABLE_LABELS.get(str(part.get("unattainable_kind")), GENERIC_TOPIC)


def _guided_brief(
    signals: CareSignals,
    care_state: CareState,
    previous_route: str | None,
    memory: ConversationMemory | None,
) -> str:
    """Brief del modo guiado (spec 020, C §5): una sola respuesta fluida."""
    parts = manuelita_parts(signals)
    foreign = [p for p in signals.get("requests") or [] if p.get("kind") != "manuelita"]
    sentiment = str(signals.get("sentiment") or "neutral")
    lines: list[str] = []
    if len(parts) > 1:
        lines.append("- Solicitudes a responder en orden:")
        lines.extend(f"  {i}) {redact_pii(p['text'])}" for i, p in enumerate(parts, start=1))
    if signals.get("greets"):
        lines.append("- Social: el visitante saluda; acompáñalo en una frase breve.")
    for part in foreign:
        lines.append(
            f"- Externo: declina con naturalidad «{_part_label(part)}», en una frase y sin "
            "inventar datos (no tienes esa información)."
        )
    if sentiment in NEGATIVE or sentiment == "distressed":
        lines.append(
            f"- Sentimiento: {SENTIMENT_LABELS.get(sentiment, sentiment)} → abre reconociéndolo "
            "en una frase breve."
        )
    language = str(signals.get("language") or (memory or {}).get("language") or "es")
    if language != "es":
        lines.append(f"- Idioma: {language} → responde en {LANGUAGE_LABELS.get(language)}.")
    register = str((memory or {}).get("register") or signals.get("register") or "formal")
    if signals.get("register") == "informal" or register == "informal":
        lines.append("- Registro: informal → tono cercano y coloquial, sin groserías.")
    if previous_route in {"clarify", "fallback"} or care_state["complaint_streak"] >= 2:
        lines.append("- Retoma en una frase lo que entendiste antes de responder.")
    if signals.get("act") == "correction":
        lines.append(
            "- Corrección: el visitante aclara lo que quiso decir; responde eso sin pedir otra "
            "aclaración."
        )
    if signals.get("concern"):
        if not any(line.startswith("- Sentimiento:") for line in lines):
            lines.append("- Sentimiento: preocupación → abre reconociéndola en una frase breve.")
        lines.append(
            "- Es una crítica: responde con equilibrio, solo con lo que documenta la evidencia."
        )
    remembered = render_memory(memory)
    if remembered:
        lines.append("- Memoria del hilo:")
        lines.extend(f"  {line}" for line in remembered.splitlines()[1:-1])
    if not lines:
        return ""
    return "\n".join(["Atención:", *lines])
