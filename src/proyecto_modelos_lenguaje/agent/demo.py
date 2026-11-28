"""Modo demostración determinista del agente: sin red ni clave (FR-021)."""

from __future__ import annotations

import html
import json
import re
import zlib
from collections.abc import Iterator, Mapping, Sequence
from typing import Any

from langchain_core.language_models import BaseChatModel
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import (
    AIMessage,
    AIMessageChunk,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatGenerationChunk, ChatResult

from ..config import PROJECT_ROOT
from ..tasks import FALLBACK_ANSWER
from .actions import detect_write_intent
from .router import contextual_query, heuristic_decision
from .series import series_intent

DEMO_INDEX = PROJECT_ROOT / "tests" / "fixtures" / "rag" / "index"
DEMO_EMBEDDER_KIND = "hash"

DEFAULT_SCRIPT: tuple[str, ...] = ("Respuesta de demostración basada en el corpus [U1].",)
DOCUMENT_PATTERN = re.compile(r'<documento id="([UF]\d+)"[^>]*>(.*?)</documento>', re.DOTALL)
SENTENCE_END = re.compile(r"(?<=[.!?])\s")
QUESTION_PATTERN = re.compile(r"<pregunta>(.*?)</pregunta>", re.DOTALL)
SNIPPET_CHARS = 220
STREAM_PIECE = re.compile(r"\S+\s*|\s+")
BULLETS_HINT = "formato de respuesta: viñetas"
# Spec 019: brief de atención («Atención:») con las solicitudes numeradas del turno.
ATTENTION_REQUEST = re.compile(r"^\s*(\d+)\) (.+)$", re.MULTILINE)
REPHRASE_HINT = "Retoma en una frase lo que entendiste"
MAX_DEMO_SEARCHES = 3


def build_demo_model(
    script: Sequence[str | BaseMessage] | None = None,
) -> FakeMessagesListChatModel:
    """Modelo guionado: devuelve las respuestas en orden y vuelve a empezar al agotarlas."""
    responses = [
        item if isinstance(item, BaseMessage) else AIMessage(content=item)
        for item in (script or DEFAULT_SCRIPT)
    ]
    return FakeMessagesListChatModel(responses=responses)


def _first_sentence(text: str) -> str:
    clean = " ".join(html.unescape(text).split())
    sentence = SENTENCE_END.split(clean, maxsplit=1)[0]
    if len(sentence) > SNIPPET_CHARS:
        sentence = sentence[:SNIPPET_CHARS].rsplit(" ", 1)[0] + "…"
    return sentence.rstrip(".")


def _question(text: str) -> str:
    asked = QUESTION_PATTERN.search(text)
    return (asked.group(1) if asked else text).strip()


def attention_requests(text: str) -> list[str]:
    """Solicitudes del bloque «Atención:» (vacío si el turno tiene una sola)."""
    if "Atención:" not in text:
        return []
    block = text[text.index("Atención:") :]
    return [match.group(2).strip() for match in ATTENTION_REQUEST.finditer(block)]


def demo_answer(
    evidence_text: str,
    *,
    bullets: bool = False,
    requests: Sequence[str] = (),
    rephrase: bool = False,
) -> str:
    """Respuesta extractiva: la primera oración de los dos primeros documentos, con su cita.

    Con varias solicitudes (spec 019) responde una línea numerada por solicitud, cada una con un
    documento distinto; si se pide retomar, antepone lo que entendió.
    """
    documents = DOCUMENT_PATTERN.findall(evidence_text)
    if not documents:
        return FALLBACK_ANSWER
    if len(requests) >= 2:
        lines = []
        for index, request in enumerate(requests):
            label, text = documents[
                min(len(documents) - 1, index * len(documents) // len(requests))
            ]
            lines.append(f"{index + 1}. Sobre «{request}»: {_first_sentence(text)} [{label}].")
        return "Según los documentos públicos de Manuelita:\n" + "\n".join(lines)
    parts = [f"{_first_sentence(text)} [{label}]." for label, text in documents[:2] if text.strip()]
    if not parts:
        return FALLBACK_ANSWER
    lead = "Entiendo que buscas información sobre Manuelita. " if rephrase else ""
    if bullets:
        return (
            lead
            + "Según los documentos públicos de Manuelita:\n"
            + "\n".join(f"- {p}" for p in parts)
        )
    return lead + "Según los documentos públicos de Manuelita: " + " ".join(parts)


EXTERNAL_LINE = re.compile(r"- Externo: declina con naturalidad «([^»]+)»")


def guided_answer(answer: str, guide: str) -> str:
    """Spec 020: el modo demo sigue el brief guiado como lo haría el modelo real.

    Abre reconociendo la emoción (``Sentimiento:``), anuncia el inglés (``Idioma: en``) y declina
    en una frase las partes externas (``Externo:``), todo en la misma respuesta.
    """
    if answer == FALLBACK_ANSWER or "Atención:" not in guide:
        return answer
    english = "- Idioma: en" in guide
    lead = ""
    if "- Sentimiento:" in guide:
        lead = (
            "I understand how you feel and I want to help. "
            if english
            else "Entiendo cómo te sientes y quiero ayudarte. "
        )
    if english:
        # Spec 029: en inglés no queda ninguna frase fija en español (la evidencia es del corpus).
        lead += "Here is what the public documents of Manuelita say about it. "
        answer = answer.replace("Según los documentos públicos de Manuelita:", "").strip()
    tail = [
        f"I don't have information about {label}; my focus is Manuelita."
        if english
        else f"Sobre {label} no tengo información, porque lo mío es Manuelita."
        for label in EXTERNAL_LINE.findall(guide)
    ]
    return " ".join([f"{lead}{answer}", *tail]).strip()


class DemoChatModel(BaseChatModel):
    """Modelo determinista para el modo demo: busca una vez y responde de forma extractiva.

    - Con herramientas enlazadas y sin resultados de herramienta en el turno, pide
      ``search_documents`` con la pregunta del usuario.
    - En cualquier otro caso responde con la primera oración de la evidencia y su etiqueta.
    """

    tools_bound: bool = False
    tool_names: tuple[str, ...] = ()

    @property
    def _llm_type(self) -> str:
        return "manuelita-demo"

    def bind_tools(self, tools: Sequence[Any], **_kwargs: Any) -> DemoChatModel:  # type: ignore[override]
        names = tuple(str(getattr(tool, "name", "")) for tool in tools)
        return self.model_copy(update={"tools_bound": bool(tools), "tool_names": names})

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> ChatResult:
        last_human = max(
            (i for i, message in enumerate(messages) if isinstance(message, HumanMessage)),
            default=-1,
        )
        tool_results = [m for m in messages[last_human + 1 :] if isinstance(m, ToolMessage)]
        if self.tools_bound and not tool_results:
            humans = [str(m.content) for m in messages if isinstance(m, HumanMessage)]
            current = _question(humans[-1]) if humans else ""
            previous = _question(humans[-2]) if len(humans) > 1 else None
            intent = detect_write_intent(current)
            if intent is not None:
                calls = [{"name": intent.tool, "args": dict(intent.args), "id": "demo_write_1"}]
            else:
                system = " ".join(str(m.content) for m in messages if isinstance(m, SystemMessage))
                requests = attention_requests(system)
                calls = (
                    self._part_calls(requests)
                    if len(requests) >= 2
                    else self._read_calls(current, previous)
                )
            message = AIMessage(content="", tool_calls=calls)
        else:
            evidence = "\n".join(str(m.content) for m in (tool_results or messages[-1:]))
            if tool_results and not DOCUMENT_PATTERN.search(evidence):
                # Resultado de una acción de escritura (o su rechazo): se informa tal cual.
                message = AIMessage(content=evidence.strip())
            else:
                system = " ".join(str(m.content) for m in messages if isinstance(m, SystemMessage))
                human = str(messages[last_human].content) if last_human >= 0 else ""
                guide = f"{system}\n{human}"
                answer = demo_answer(
                    evidence,
                    bullets=BULLETS_HINT in system,
                    requests=attention_requests(guide),
                    rephrase=REPHRASE_HINT in guide,
                )
                answer = guided_answer(answer, guide)
                if answer != FALLBACK_ANSWER:
                    answer = styled_answer(answer, system)  # spec 036
                message = AIMessage(content=answer)
        return ChatResult(generations=[ChatGeneration(message=message)])

    def _part_calls(self, requests: Sequence[str]) -> list[dict[str, Any]]:
        """Una búsqueda por solicitud (como máximo tres, el límite de herramientas por turno)."""
        return [
            {
                "name": "search_documents",
                "args": {"query": f"Manuelita {request}"[:300]},
                "id": f"demo_part_{index}",
            }
            for index, request in enumerate(requests[:MAX_DEMO_SEARCHES], start=1)
        ]

    def _read_calls(self, current: str, previous: str | None) -> list[dict[str, Any]]:
        """Herramientas de lectura según la ruta heurística: cifra anual, conteo o documentos."""
        from .tools import count_intent

        route = heuristic_decision(current).route
        query = contextual_query(current, previous)[:300]
        calls: list[dict[str, Any]] = []
        if route in {"structured", "mixed"}:
            asked = series_intent(current)
            entity_type = count_intent(current)
            if asked is not None and "aggregate_series" in self.tool_names:
                args = asked.model_dump(exclude_none=True)
                calls.append({"name": "aggregate_series", "args": args, "id": "demo_series_1"})
            elif "query_structured" in self.tool_names:
                args = {"entity_type": entity_type} if entity_type else {"query": query}
                calls.append({"name": "query_structured", "args": args, "id": "demo_struct_1"})
        if route != "structured" or not calls:
            calls.append(
                {"name": "search_documents", "args": {"query": query}, "id": "demo_call_1"}
            )
        return calls

    def _stream(
        self,
        messages: list[BaseMessage],
        stop: list[str] | None = None,
        run_manager: Any = None,
        **kwargs: Any,
    ) -> Iterator[ChatGenerationChunk]:
        """Streaming palabra por palabra para que el modo demo muestre la respuesta en vivo."""
        message = self._generate(messages, stop, run_manager, **kwargs).generations[0].message
        assert isinstance(message, AIMessage)
        if message.tool_calls:
            yield ChatGenerationChunk(
                message=AIMessageChunk(
                    content="",
                    tool_call_chunks=[
                        {
                            "name": call["name"],
                            "args": json.dumps(call["args"], ensure_ascii=False),
                            "id": call["id"],
                            "index": index,
                        }
                        for index, call in enumerate(message.tool_calls)
                    ],
                )
            )
            return
        for piece in STREAM_PIECE.findall(str(message.content)):
            chunk = ChatGenerationChunk(message=AIMessageChunk(content=piece))
            if run_manager is not None:
                run_manager.on_llm_new_token(piece, chunk=chunk)
            yield chunk


# ---------------------------------------------------------------- spec 020: conversación guiada

DEMO_POOLS: dict[str, dict[str, tuple[str, ...]]] = {
    "es": {
        "greeting_first": (
            "¡Hola! Soy Valer-IA Caña, la asistente virtual de Manuelita. ¿Qué te gustaría saber?",
            "¡Qué gusto saludarte! Soy Valer-IA Caña y te acompaño con la información pública "
            "de Manuelita.",
            "¡Hola, bienvenido! Te habla Valer-IA Caña; cuéntame qué quieres conocer de Manuelita.",
        ),
        "greeting": (
            "¡Hola de nuevo! ¿En qué te ayudo?",
            "¡Qué bueno leerte otra vez! Cuéntame.",
            "¡Hola! Aquí sigo para lo que necesites.",
        ),
        "smalltalk": (
            "¡Qué bien que me lo cuentes!",
            "Te entiendo perfectamente.",
            "¡Uy, sí, a veces pasa!",
            "Gracias por compartirlo conmigo.",
            "Gracias por contarme.",
        ),
        "smalltalk_follow": (
            "Si en algún momento quieres saber algo de Manuelita, aquí estoy.",
            "Cuando quieras, te cuento sobre la historia o los negocios de Manuelita.",
            "Y si te da curiosidad algo de Manuelita, me avisas.",
            "",
        ),
        "minimal": (
            "¡Listo!",
            "¡Jaja, qué bien!",
            "Perfecto.",
            "¡Dale!",
            "Entendido.",
        ),
        "minimal_follow": ("Aquí estoy si necesitas algo.", "Cuando quieras seguimos.", "", ""),
        "about_assistant": (
            "Soy Valer-IA Caña, una asistente virtual con inteligencia artificial. Te ayudo con la "
            "información pública de Manuelita.",
            "Te cuento: soy Valer-IA Caña, una asistente de inteligencia artificial y no un canal "
            "oficial, pero conozco la información pública de Manuelita.",
            "Soy Valer-IA Caña, una asistente virtual con inteligencia artificial que responde "
            "sobre Manuelita con fuentes públicas.",
        ),
        "thanks": (
            "¡Con mucho gusto!",
            "¡A ti por escribir!",
            "Para eso estoy, con gusto.",
        ),
        "closing_open": (
            "¡Fue un gusto conversar contigo{name}!",
            "¡Gracias por la charla{name}!",
            "¡Qué bueno haber conversado{name}!",
        ),
        "closing_summary": ("Hoy hablamos de {topics}.", "Repasamos {topics}."),
        "closing_end": ("Que tengas un excelente día.", "Aquí estaré cuando quieras volver."),
        "decline_open": (
            "Ahí sí no te puedo ayudar, porque no tengo esa información.",
            "Ese dato no lo tengo, así que prefiero no inventarlo.",
            "Me encantaría ayudarte con eso, pero no tengo esa información.",
            "No tengo datos confiables para darte.",
        ),
        "decline_scope": (
            "Lo mío es la información pública de Manuelita.",
            "Yo te acompaño con lo que tiene que ver con Manuelita.",
            "Mi especialidad es Manuelita y su información pública.",
        ),
        "bridge_lead": ("Por cierto,", "Si te sirve,", "Y ya que estamos,"),
        # Spec 035: cortesía sin preguntas y regreso a Manuelita con el puente.
        "greeting_redirect": ("¡Hola de nuevo!", "¡Qué bueno leerte otra vez!", "¡Hola otra vez!"),
        "redirect_lead": (
            "Lo mío es Manuelita y, por cierto,",
            "Te cuento algo de Manuelita:",
            "De Manuelita,",
        ),
        "complaint": (
            "Qué pena que te haya pasado eso.",
            "Lamento la molestia, de verdad.",
            "Entiendo que es frustrante.",
        ),
    },
    "en": {
        "greeting_first": ("Hi! I am Valer-IA Caña, an AI assistant about Manuelita.",),
        "greeting": ("Hi again! How can I help?",),
        "smalltalk": ("Thanks for sharing that!", "I hear you."),
        "smalltalk_follow": ("If you want to know about Manuelita, just ask.", ""),
        "minimal": ("Sure!", "Got it."),
        "minimal_follow": ("", "I am here if you need anything."),
        "about_assistant": (
            "I am Valer-IA Caña, an AI assistant. I can tell you about Manuelita using its public "
            "information.",
        ),
        "thanks": ("You are welcome!",),
        "closing_open": ("It was a pleasure talking with you{name}!",),
        "closing_summary": ("We talked about {topics}.",),
        "closing_end": ("Have a great day.",),
        "decline_open": ("I do not have that information.", "That is outside what I know."),
        "decline_scope": ("I can help you with public information about Manuelita.",),
        "bridge_lead": ("By the way,",),
        "greeting_redirect": ("Hi again!", "Nice to hear from you again!"),
        "redirect_lead": ("About Manuelita,", "Here is something about Manuelita:"),
        "complaint": ("I am sorry about that.",),
    },
}


UNATTAINABLE_BY_LABEL = {
    "precios y descuentos": "pricing",
    "compromisos en nombre de la empresa": "commitment",
    "hablar con una persona": "human",
}


def _choose(rng: Any, options: Sequence[str]) -> str:
    return options[rng.randrange(len(options))] if options else ""


def _demo_redirect(
    plan: Any, *, playbook: Any, rng: Any, pool: Mapping[str, Sequence[str]], lang: str, seed: int
) -> str:
    """Spec 035: cortesía en una frase y regreso a Manuelita (puente o temas sugeridos)."""
    from .care import topics_offer

    act = plan.act
    if act == "greeting":
        courtesy = _choose(rng, pool["greeting_redirect"])
    elif act == "minimal":
        courtesy = _choose(rng, pool["minimal"])
    elif act == "off_topic":
        courtesy = _choose(rng, pool["decline_open"])
        if plan.topic and lang == "es" and getattr(plan, "streak", 0) <= 1:
            # Solo en el primer turno ajeno: repetir «Sobre …» en la racha suena a guion.
            courtesy = f"Sobre {plan.topic}, {courtesy[:1].lower()}{courtesy[1:]}"
    else:
        courtesy = _choose(rng, pool["smalltalk"])
    if plan.bridge is not None:
        bridge = plan.bridge
        lead = _choose(rng, pool["redirect_lead"])
        if bridge.source == "curated":
            text = bridge.text.rstrip(".")
            redirect = f"{lead} {text[:1].lower()}{text[1:]} [U1]."
        else:
            redirect = f"{lead} puedo contarte sobre «{bridge.title}» [U1]."
    else:
        redirect = topics_offer(playbook, plan.topics, seed=rng.randrange(1000), language=lang)
    return f"{courtesy} {redirect}".strip()


# ---------------------------------------------------------------- spec 036: estilo caleño

# El bloque real abre con «<estilo>» y un salto de línea (el prompt solo lo nombra entre comillas).
STYLE_BLOCK = re.compile(r"<estilo>\n(.*?)</estilo>", re.DOTALL)
STYLE_HINTS = re.compile(r"expresiones sugeridas[^:]*:\s*(.+)")
QUOTED = re.compile(r"«([^»]+)»")
MEANING = re.compile(r"\b(significa|significado|que quiere decir|que es eso de)\b")


def with_expression(text: str, expression: str) -> str:
    """Integra la expresión al inicio de la primera frase: «Listo pues, gracias por contarme.»."""
    text = text.strip()
    if not text or not expression:
        return text
    head = expression[:1].upper() + expression[1:]
    opener = text.startswith("¡")
    body = text[1:] if opener else text
    body = body[:1].lower() + body[1:]
    return f"¡{head}, {body}" if opener else f"{head}, {body}"


def _use_expression(key: str) -> bool:
    """Unas tres de cada cuatro respuestas llevan expresión (no todas: no es muletilla)."""
    return zlib.crc32(key.encode()) % 4 != 0


def styled_answer(answer: str, system: str) -> str:
    """Respuesta con búsqueda del modo demo con el bloque ``<estilo>`` (spec 036)."""
    block = STYLE_BLOCK.search(system)
    if block is None:
        return answer
    if "pidió hablar sin modismos" in block.group(1):
        return f"Claro, te hablo sin modismos. {answer}"
    hints = STYLE_HINTS.search(block.group(1))
    names = QUOTED.findall(hints.group(1)) if hints else []
    if not names or not _use_expression(answer):
        return answer
    return with_expression(answer, names[zlib.crc32(answer.encode()) % len(names)])


def demo_converse(
    plan: Any,
    *,
    playbook: Any,
    seed: int,
    name: str | None = None,
    question: str = "",
) -> str:
    """Respuesta guiada del modo demo con el estilo caleño del plan (specs 020 y 036)."""
    from . import style as caleno
    from .structured import normalize

    memory_plain = getattr(plan, "style", "off") == "off"
    if question and caleno.wants_plain(question) and lang_es(plan):
        return "Claro, te hablo sin modismos. Si quieres, te cuento algo de Manuelita."
    named = caleno.named_expressions(question) if question else []
    if named and MEANING.search(normalize(question)) and lang_es(plan):
        meaning = caleno.glossary(named[:1])[0].split(" = ", 1)[1]
        return (
            f"Es una expresión caleña: {meaning}. Si quieres, te cuento de la historia de "
            "Manuelita."
        )
    text = _demo_converse_text(plan, playbook=playbook, seed=seed, name=name)
    hints = tuple(getattr(plan, "style_hints", ()) or ())
    if memory_plain or not hints or not _use_expression(f"{seed}:{text}"):
        return text
    return with_expression(text, hints[seed % len(hints)])


def lang_es(plan: Any) -> bool:
    return getattr(plan, "language", "es") == "es"


def _demo_converse_text(plan: Any, *, playbook: Any, seed: int, name: str | None = None) -> str:
    """Respuesta guiada determinista para el modo demo (spec 020, R14).

    Compone frases variadas según el plan con una semilla del hilo y del turno, sin afirmar hechos
    externos: los datos de Manuelita solo aparecen en el puente, con su etiqueta ``[U1]``.
    """
    import random

    rng = random.Random(seed)
    lang = "en" if plan.language == "en" else "es"
    pool = DEMO_POOLS[lang]
    act = plan.act
    if getattr(plan, "redirect", False) and plan.reason not in {"unattainable", "advice"}:
        # Spec 035 (los límites y consejos conservan su guion: canal oficial o profesional).
        return _demo_redirect(plan, playbook=playbook, rng=rng, pool=pool, lang=lang, seed=seed)
    sentences: list[str] = []
    if plan.sentiment in {"frustrated", "angry", "distressed"} and act != "complaint":
        sentences.append(_choose(rng, pool["complaint"]))
    if act == "greeting":
        sentences.append(_choose(rng, pool["greeting_first" if plan.turn == 1 else "greeting"]))
    elif act == "about_assistant":
        sentences.append(_choose(rng, pool["about_assistant"]))
    elif act == "minimal":
        sentences.append(_choose(rng, pool["minimal"]))
        sentences.append(_choose(rng, pool["minimal_follow"]))
    elif act == "thanks":
        sentences.append(_choose(rng, pool["thanks"]))
    elif act == "closing":
        suffix = f", {name}" if name else ""
        sentences.append(_choose(rng, pool["closing_open"]).format(name=suffix))
        if plan.summary_topics:
            topics = " y ".join(t.replace("_", " ") for t in plan.summary_topics[-2:])
            sentences.append(_choose(rng, pool["closing_summary"]).format(topics=topics))
        sentences.append(_choose(rng, pool["closing_end"]))
    elif act == "complaint":
        sentences.append(_choose(rng, pool["complaint"]))
        sentences.append(_choose(rng, playbook.variants["complaint.help"]))
    elif act == "clarify":
        options = _choose(rng, playbook.variants["clarify.options.default"])
        intro = _choose(rng, playbook.variants["clarify.intro"])
        sentences.append(intro.replace("{options}", options))
    elif plan.reason == "unattainable":
        kind = UNATTAINABLE_BY_LABEL.get(plan.topic or "", "commitment")
        sentences.append(_choose(rng, playbook.variants[f"boundary.{kind}"]))
        sentences.append("Para eso, el canal es el sitio oficial www.manuelita.com.")
    elif plan.reason == "advice":
        advice = _choose(rng, playbook.variants["boundary.advice"])
        if plan.topic and lang == "es":
            advice = f"Sobre {plan.topic}: {advice[:1].lower()}{advice[1:]}"
        sentences.append(advice)
    elif act == "off_topic":
        opening = _choose(rng, pool["decline_open"])
        if plan.topic and lang == "es":
            opening = f"Sobre {plan.topic}, {opening[:1].lower()}{opening[1:]}"
        sentences.append(opening)
        sentences.append(_choose(rng, pool["decline_scope"]))
    else:  # smalltalk
        sentences.append(_choose(rng, pool["smalltalk"]))
        if plan.bridge is None:
            sentences.append(_choose(rng, pool["smalltalk_follow"]))
    if plan.bridge is not None:
        bridge = plan.bridge
        lead = _choose(rng, pool["bridge_lead"])
        if bridge.source == "curated":
            text = bridge.text.rstrip(".")
            text = text[:1].lower() + text[1:]
            sentences.append(f"{lead} {text} [U1].")
        else:
            sentences.append(f"{lead} puedo contarte sobre «{bridge.title}» [U1].")
    if plan.length == "short":
        sentences = [s for s in sentences if s][:2]
    return " ".join(sentence for sentence in sentences if sentence).strip()
