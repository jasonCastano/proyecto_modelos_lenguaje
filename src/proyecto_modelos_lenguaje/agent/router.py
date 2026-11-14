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
from collections.abc import Sequence
from dataclasses import dataclass

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
OUT_OF_SCOPE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "finanzas_externas",
        re.compile(r"\b(dolar|euro|bitcoin|tasa de cambio|trm|bolsa de valores)\b"),
    ),
    ("clima", re.compile(r"\b(clima|llover|lluvia|temperatura|pronostico del tiempo)\b")),
    ("deportes", re.compile(r"\b(futbol|mundial|liga|partido de|seleccion colombia)\b")),
    ("politica", re.compile(r"\b(elecciones|presidente de (colombia|estados unidos)|congreso)\b")),
    (
        "programacion",
        re.compile(r"\b(python|javascript|sql|codigo|programa en|funcion en|script)\b"),
    ),
)
STRUCTURED_CUES = re.compile(
    r"(en que ano|cuant[oa]s?\b|que porcentaje|porcentaje|que puesto|capacidad|cifra|"
    r"cuantas toneladas|lista de (filiales|marcas|certificaciones)|que filiales|que marcas)"
)
# Pedido de combinar fuentes: comparar, contrastar o relacionar un dato con lo que dicen los textos.
MIXED_CUES = re.compile(
    r"\b(compara\w*|contrasta\w*|frente a|versus|vs|relacion\w* entre|coincide\w*|"
    r"cumpl\w* (la|su|el) (meta|objetivo|compromiso)|meta|objetivo|segun el documento)\b"
)
# Cifra anual con año, cálculo o comparación: «ventas de 2021», «promedio de producción de azúcar».
SERIES_CUES = re.compile(
    r"\b(20[12]\d|promedio|total|suma|maximo|minimo|variacion|crecimiento|evolucion|por ano|"
    r"cuanto|cuanta|cifras?|mayor|menor|mas alto|mas bajo|ano de|en que ano)\b"
)
DEICTIC = re.compile(r"\b(eso|esa|ese|esto|aquello|lo anterior|mejor|alla|ahi)\b")
COMPANY = re.compile(r"\b(manuelita|fundacion|palmar|altamira|laredo|oceanos|mejillones|ingenio)\b")


@dataclass(frozen=True, slots=True)
class RouterResult:
    decision: RouteDecision
    model_calls: int = 0


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", normalize(text))


def rule_decision(message: str) -> RouteDecision | None:
    """Etapa 1: decide sin modelo cuando el caso es inequívoco; si no, ``None``."""
    words = _words(message)
    if not words:
        return RouteDecision(
            route="clarify", confidence=0.3, reason="mensaje vacío", decided_by="rules"
        )
    if len(words) <= 8 and all(word in SMALLTALK for word in words):
        return RouteDecision(
            route="direct",
            confidence=0.95,
            reason="saludo, agradecimiento o despedida",
            decided_by="rules",
        )
    text = " ".join(words)
    for name, pattern in OUT_OF_SCOPE_PATTERNS:
        if pattern.search(text) and not COMPANY.search(text):
            return RouteDecision(
                route="out_of_scope",
                confidence=0.9,
                reason=f"tema ajeno a Manuelita ({name.replace('_', ' ')})",
                decided_by="rules",
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
    if MIXED_CUES.search(text) and (asks_series or STRUCTURED_CUES.search(text) or "dato" in text):
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
    return RouteDecision.model_validate(
        {
            "route": payload.get("route"),
            "confidence": payload.get("confidence"),
            "reason": reason,
            "decided_by": "llm",
            "alternative": payload.get("alternative"),
        }
    )


def route_message(
    message: str,
    *,
    history: Sequence[str] = (),
    model: BaseChatModel | None = None,
    min_confidence: float = 0.6,
    temperature: float = 0.0,
) -> RouterResult:
    """Decide la ruta efectiva de un mensaje (reglas → LLM o heurística → umbral)."""
    ruled = rule_decision(message)
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
