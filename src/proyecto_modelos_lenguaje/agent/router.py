"""Puerta de decisión del agente (spec 014, FR-011 y FR-015).

Dos etapas (``research.md`` §6):

1. **Reglas deterministas** (0 llamadas al modelo): charla trivial ⇒ ``direct``; temas claramente
   ajenos a Manuelita ⇒ ``out_of_scope``.
2. **Clasificador LLM** con salida JSON validada contra ``RouteDecision`` (``prompts/router.md``).
   Sin modelo (modo demo o pruebas) se usa una heurística determinista con ``decided_by="demo"``.

Con ``confidence < min_confidence`` la ruta efectiva es ``clarify``.

Desviación documentada: en lugar de ``with_structured_output`` se pide JSON y se valida con
Pydantic. Funciona igual con DeepSeek y con los modelos guionados de las pruebas, que no soportan
*tool calling*.
"""

from __future__ import annotations

import json
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from pydantic import ValidationError

from .models import RouteDecision
from .prompts import load_agent_prompt
from .series import series_intent
from .structured import normalize

SMALLTALK = frozenset(
    {
        *("hola", "buenas", "buenos", "buen", "dia", "dias", "tardes", "noches", "que", "tal"),
        *("saludos", "hey", "gracias", "muchas", "mil", "por", "la", "informacion", "eso"),
        *("es", "todo", "hasta", "luego", "pronto", "adios", "chao", "ok", "vale", "perfecto"),
        *("listo", "genial", "excelente", "muy", "amable", "bien", "entendido", "y", "usted"),
        *("como", "esta", "estas", "un", "saludo", "nos", "vemos"),
    }
)
# Spec 018: motivos de conducta de Valer-IA (texto normalizado: minúsculas, sin tildes).
# Se evalúan antes que los temas ajenos; las palabras de la industria («quema de caña», «demanda de
# azúcar», «política antifraude») no los activan porque los patrones exigen verbos o personas.
CONDUCT_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "prompt_extraction",
        re.compile(
            r"\b((tu|tus|el|del|su) (system )?prompt|prompt del sistema|"
            r"(tus|las) instrucciones (internas|iniciales|del sistema|secretas|ocultas)|"
            r"instrucciones del sistema|ignora (tus|las|todas)( \w+){0,3} instrucciones|"
            r"olvida (tus|las) (instrucciones|reglas)|(actua|finge|comportate) como|"
            r"modo desarrollador|jailbreak|dan mode|repite (todo )?lo (anterior|de arriba))\b"
        ),
    ),
    (
        "third_party",
        re.compile(
            r"\b((correo|email|telefono|celular|direccion|cedula|salario|sueldo|"
            r"datos( personales)?)"
            r" (de|del|de los|de las) (otros? |otras? |los |las |un |una |el |la |algun )?"
            r"(cliente|clientes|usuario|usuarios|empleado|empleados|trabajador|trabajadores|"
            r"persona|personas|gerente|presidente|directivos?)|"
            r"cuanto (gana|ganan|cobra)|"
            r"quien(es)? (mas )?(se )?(ha |han )?(registrado|registro|registraron)|"
            r"(lista|base de datos) de (clientes|usuarios|empleados))\b"
        ),
    ),
    (
        "harmful",
        re.compile(
            r"\b(hackear|hackeo|hackeas|piratear|estafar|robar|envenenar|sabotear|secuestrar|"
            r"matar|(hacer|fabricar|construir|armar) (una |un )?(bomba|explosivo|arma)|"
            r"como (hago|hacer|fabrico|fabricar) (una |un )?(bomba|explosivo|arma))\b"
        ),
    ),
    (
        "abuse",
        re.compile(
            r"\b(idiota|estupida|estupido|imbecil|inutil|maldita|maldito|basura|pendeja|pendejo|"
            r"hijueputa|gonorrea|malparida|malparido|perra|zorra|callate|mierda)\b"
        ),
    ),
    (
        "advice",
        re.compile(
            r"\b((asesoria|consejo|consulta) "
            r"(legal|medica|medico|financiera|juridica|de inversion)|"
            r"(deberia|debo|me conviene|vale la pena) invertir|"
            r"que (medicamento|medicina|remedio) (tomo|debo|me))\b"
        ),
    ),
)
# «¿Eres una persona?», «¿quién eres?»: se responde como IA, sin buscar.
AI_QUESTION = re.compile(
    r"\b(eres (una |un )?(humana|humano|persona|real|robot|bot|ia|inteligencia artificial|maquina)|"
    r"hablo con (una |un )?(persona|humano|humana|bot|maquina)|quien eres|que eres)\b"
)
STRUCTURED_CUES = re.compile(
    r"(en que ano|cuant[oa]s?\b|que porcentaje|porcentaje|que puesto|capacidad|cifra|"
    r"cuantas toneladas|lista de (filiales|marcas|certificaciones)|que filiales|que marcas)"
)
# Pedido de combinar fuentes: comparar, contrastar o relacionar un dato con lo que dicen los textos.
MIXED_CUES = re.compile(
    r"\b(compara\w*|contrasta\w*|frente a|versus|vs|relacion\w* entre|coincide\w*|"
    r"cumpl\w* (la|su|el) (meta|objetivo|compromiso)|meta|objetivo|segun el documento|"
    r"(que|lo que) (dice|explica|describe|cuenta|senala) (el|la|los|las) "
    r"(informe|informes|documento|documentos|fundacion))\b"
)
# Cifra anual con año, cálculo o comparación: «ventas de 2021», «promedio de producción de azúcar».
SERIES_CUES = re.compile(
    r"\b(20[12]\d|promedio|total|suma|maximo|minimo|variacion|crecimiento|evolucion|por ano|"
    r"cuanto|cuanta|cifras?|mayor|menor|mas alto|mas bajo|ano de|en que ano)\b"
)
DEICTIC = re.compile(r"\b(eso|esa|ese|esto|aquello|lo anterior|mejor|alla|ahi)\b")
COMPANY = re.compile(r"\b(manuelita|fundacion|palmar|altamira|laredo|oceanos|mejillones|ingenio)\b")


OUT_OF_SCOPE_REASONS = frozenset(
    {
        "off_topic",
        "abuse",
        "harmful",
        "third_party",
        "prompt_extraction",
        "advice",
        "crisis",
        "unattainable",
    }
)
SENTIMENTS = frozenset({"neutral", "satisfied", "confused", "frustrated", "angry", "distressed"})
UNATTAINABLE_KINDS = frozenset({"pricing", "commitment", "human"})


@dataclass(frozen=True, slots=True)
class RouterResult:
    decision: RouteDecision
    model_calls: int = 0


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(text))


def rule_decision(message: str, signals: Mapping[str, Any] | None = None) -> RouteDecision | None:
    """Etapa 1: decide sin modelo cuando el caso es inequívoco; si no, ``None``.

    Con ``signals`` (spec 019, ``care.analyze``) la crisis va primero, el insulto solo decide si
    no hay consulta y los mensajes sin partes de Manuelita se atienden sin buscar.
    """
    from . import care

    words = _words(message)
    if not words:
        return RouteDecision(
            route="clarify", confidence=0.3, reason="mensaje vacío", decided_by="rules"
        )
    text = " ".join(words)
    if signals and signals.get("crisis"):
        return RouteDecision(
            route="out_of_scope",
            confidence=1.0,
            reason="atención: mensaje de angustia o crisis",
            decided_by="rules",
            scope_reason="crisis",
        )
    for reason, pattern in CONDUCT_PATTERNS:
        if reason == "abuse" and signals is not None and not signals.get("hostile_only"):
            continue
        if pattern.search(text):
            spec = care.match_topic(text) if reason == "advice" else None
            return RouteDecision(
                route="out_of_scope",
                confidence=0.95,
                reason=f"conducta: {reason.replace('_', ' ')}",
                decided_by="rules",
                scope_reason=reason,
                topic=spec.key if spec and spec.kind == "advice" else None,
            )
    if AI_QUESTION.search(text):
        return RouteDecision(
            route="direct",
            confidence=0.95,
            reason="pregunta por la naturaleza de la asistente",
            decided_by="rules",
        )
    if len(words) <= 8 and all(word in SMALLTALK for word in words):
        return RouteDecision(
            route="direct",
            confidence=0.95,
            reason="saludo, agradecimiento o despedida",
            decided_by="rules",
        )
    if signals is not None:
        if signals.get("guided"):
            guided = _guided_decision(signals)
            if guided is not None:
                return guided
        return _care_decision(signals)
    spec = care.match_topic(text)
    if spec is not None and not COMPANY.search(text):
        return RouteDecision(
            route="out_of_scope",
            confidence=0.9,
            reason=f"tema ajeno a Manuelita ({spec.key.replace('_', ' ')})",
            decided_by="rules",
            scope_reason=spec.kind,
            topic=spec.key,
        )
    return None


CONVERSATIONAL_ACTS = frozenset({"about_assistant", "closing", "thanks", "greeting", "minimal"})


def _guided_decision(signals: Mapping[str, Any]) -> RouteDecision | None:
    """Spec 020: charla social y actos conversacionales van a ``converse`` sin buscar."""
    act = str(signals.get("act") or "")
    parts = list(signals.get("requests") or [])
    if act in CONVERSATIONAL_ACTS and signals.get("act_ruled"):
        return RouteDecision(
            route="direct",
            confidence=0.9,
            reason=f"conversación: {act.replace('_', ' ')}",
            decided_by="rules",
            act=act,
        )
    if act != "correction" and parts and all(p.get("tier") == "social" for p in parts):
        return RouteDecision(
            route="direct",
            confidence=0.85,
            reason="conversación social sin pedido de datos",
            decided_by="rules",
            act="smalltalk",
        )
    return None


def _care_decision(signals: Mapping[str, Any]) -> RouteDecision | None:
    """Spec 019: quejas sin consulta, satisfacción y mensajes sin partes de Manuelita."""
    parts = list(signals.get("requests") or [])
    if signals.get("complaint_only") or signals.get("satisfied_only"):
        what = "queja o rechazo" if signals.get("complaint_only") else "agradecimiento"
        return RouteDecision(
            route="direct",
            confidence=0.9,
            reason=f"atención: {what} sin consulta",
            decided_by="rules",
        )
    if parts and all(part.get("kind") != "manuelita" for part in parts):
        first = parts[0]
        if first.get("kind") == "unattainable":
            return RouteDecision(
                route="out_of_scope",
                confidence=0.9,
                reason=f"pedido no atendible ({first.get('unattainable_kind')})",
                decided_by="rules",
                scope_reason="unattainable",
                kind=first.get("unattainable_kind"),
            )
        return RouteDecision(
            route="out_of_scope",
            confidence=0.9,
            reason=f"tema ajeno a Manuelita ({str(first.get('topic_key')).replace('_', ' ')})",
            decided_by="rules",
            scope_reason=first.get("kind"),
            topic=first.get("topic_key"),
        )
    return None


def heuristic_decision(message: str, history: Sequence[str] = ()) -> RouteDecision:
    """Clasificador determinista para el modo demo o si el modelo falla."""
    text = " ".join(_words(message))
    content = [word for word in text.split() if word not in SMALLTALK]
    if not history and DEICTIC.search(text) and not COMPANY.search(text) and len(content) <= 4:
        return RouteDecision(
            route="clarify",
            confidence=0.4,
            reason="referencia sin antecedente en la conversación",
            decided_by="demo",
        )
    asks_series = series_intent(message) is not None and bool(
        STRUCTURED_CUES.search(text) or SERIES_CUES.search(text)
    )
    # Comparar o relacionar explícitamente una cifra anual con un texto ⇒ ruta mixta.
    names_series = series_intent(message) is not None
    if MIXED_CUES.search(text) and (names_series or STRUCTURED_CUES.search(text) or "dato" in text):
        return RouteDecision(
            route="mixed",
            confidence=0.75,
            reason="combina un dato puntual con lo que dicen los documentos",
            decided_by="demo",
            alternative="documental",
        )
    if asks_series or STRUCTURED_CUES.search(text):
        return RouteDecision(
            route="structured",
            confidence=0.75,
            reason="pide un dato puntual (año, cifra, porcentaje o lista)",
            decided_by="demo",
            alternative="documental",
        )
    return RouteDecision(
        route="documental",
        confidence=0.7,
        reason="pregunta narrativa sobre la empresa",
        decided_by="demo",
        alternative="structured",
    )


def _extract_json(text: str) -> dict[str, object]:
    match = re.search(r"\{.*\}", text, flags=re.DOTALL)
    if match is None:
        raise ValueError("la respuesta del enrutador no contiene JSON")
    payload = json.loads(match.group(0))
    if not isinstance(payload, dict):
        raise ValueError("el JSON del enrutador no es un objeto")
    return payload


def llm_decision(
    message: str, history: Sequence[str], model: BaseChatModel, *, temperature: float = 0.0
) -> RouteDecision:
    """Etapa 2: clasificador LLM con salida JSON validada."""
    template = load_agent_prompt("router")
    system = template.render(question=message, history="\n".join(history) or "(vacío)")
    bound = model.bind(temperature=temperature) if hasattr(model, "temperature") else model
    response = bound.invoke([SystemMessage(content=system), HumanMessage(content=message)])
    payload = _extract_json(str(response.content))
    reason = str(payload.get("reason") or "sin motivo")[:200]
    route = payload.get("route")
    scope = payload.get("scope_reason") if route == "out_of_scope" else None
    if route == "out_of_scope" and scope not in OUT_OF_SCOPE_REASONS:
        scope = "off_topic"
    if scope == "crisis":
        scope = "off_topic"  # la crisis solo la decide la regla determinista (spec 019, R5)
    from .care import sanitize_topic

    sentiment = payload.get("sentiment")
    kind = payload.get("kind")
    return RouteDecision.model_validate(
        {
            "route": route,
            "confidence": payload.get("confidence"),
            "reason": reason,
            "decided_by": "llm",
            "alternative": payload.get("alternative"),
            "scope_reason": scope,
            "topic": sanitize_topic(str(payload.get("topic") or "")),
            "sentiment": sentiment if sentiment in SENTIMENTS else None,
            "kind": kind if kind in UNATTAINABLE_KINDS else None,
            "act": payload.get("act"),
        }
    )


def route_message(
    message: str,
    *,
    history: Sequence[str] = (),
    model: BaseChatModel | None = None,
    min_confidence: float = 0.6,
    temperature: float = 0.0,
    signals: Mapping[str, Any] | None = None,
) -> RouterResult:
    """Decide la ruta efectiva de un mensaje (reglas → LLM o heurística → umbral)."""
    ruled = rule_decision(message, signals)
    if ruled is not None:
        return RouterResult(ruled.effective(min_confidence), model_calls=0)
    if model is None:
        return RouterResult(heuristic_decision(message, history).effective(min_confidence))
    try:
        decision = llm_decision(message, history, model, temperature=temperature)
    except ValueError, ValidationError, json.JSONDecodeError:
        fallback = heuristic_decision(message, history)
        decision = fallback.model_copy(
            update={"reason": f"salida del enrutador inválida; {fallback.reason}"[:200]}
        )
    return RouterResult(decision.effective(min_confidence), model_calls=1)


FOLLOW_UP_MAX_WORDS = 8
FOLLOW_UP_START = re.compile(r"^(y|e|pero|entonces|tambien|ademas)\b")


def contextual_query(question: str, previous_question: str | None) -> str:
    """Consulta de búsqueda para una repregunta elíptica: antepone la pregunta previa.

    «¿Y dónde lo produce?» tras «¿Qué produce Manuelita?» se busca como ambas juntas; una
    pregunta larga o autosuficiente se busca tal cual.
    """
    if not previous_question:
        return question
    normalized = normalize(question).lstrip("¿¡ ")
    words = re.findall(r"\w+", normalized)
    elliptic = FOLLOW_UP_START.match(normalized) is not None or bool(DEICTIC.search(normalized))
    if elliptic or (len(words) <= FOLLOW_UP_MAX_WORDS and COMPANY.search(normalized) is None):
        return f"{previous_question} {question}"
    return question


def apply_structured_fallback(decision: RouteDecision, rows_found: int) -> RouteDecision:
    """Si la ruta estructurada no encontró filas, cae a documental y lo registra."""
    if decision.route == "structured" and rows_found == 0:
        return decision.model_copy(update={"route": "documental", "fallback_route": "documental"})
    return decision
