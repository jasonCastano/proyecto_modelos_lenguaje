"""Puente del canal: un mensaje de WhatsApp → un turno de Valer-IA (spec 024 y spec 028).

El grafo no sabe de WhatsApp: recibe ``user_id`` (seudónimo), ``thread_id`` y texto como cualquier
cliente. Aquí viven la deduplicación, la cola por usuario, las intenciones naturales del canal
(empezar de nuevo, responder por escrito o con voz), la confirmación de escrituras en lenguaje
natural (spec 028, research R6) y el formato de la respuesta, con nota de voz cuando corresponde.

Ningún texto dirigido a las personas menciona comandos (contrato ``conversation.md``). Los comandos
de la spec 024 siguen funcionando como atajos ocultos del operador.
"""

from __future__ import annotations

import threading
import time
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol

from ..agent.config import ChannelsConfig
from ..agent.structured import normalize
from ..agent.style import LOW_MOOD
from .format import sources_only, to_whatsapp
from .greeting import already_introduced, identity_line, introduction, merge
from .identity import SenderError, mask, pseudonym, sender_kind
from .intents import (
    Language,
    decision_of,
    detect_intent,
    language_of,
    looks_like_new_question,
    plain,
    remainder,
)
from .journal import ChannelLogRecord, append_daily, log_channel
from .limits import limit_decision, operators
from .stickers import (
    OPT_OUT,
    StickerCatalog,
    StickerChoice,
    TurnSignals,
    choose,
    load_catalog,
)
from .stickers import _plain as plain_text
from .store import ChannelStore

Channel = Literal["whatsapp", "telegram"]
MessageKind = Literal["text", "audio", "image", "video", "document", "sticker", "location", "other"]
InputMode = Literal["text", "voice"]
ReplyStatus = Literal[
    "answered", "pending_approval", "approval_resolved", "unsupported", "busy", "error", "ignored"
]
AGENT_MAX_CHARS = 2000
FORGET_PROMPT = "Olvida todos mis datos guardados: perfil y preferencias."
OPERATOR_SHORTCUTS = ("/ayuda", "/traza", "/nuevo", "/olvidar", "/perfil", "/cancelar")

# Textos del canal (contracts/conversation.md). Ninguno menciona comandos (prueba T027).
TEXTS: dict[str, dict[str, str]] = {
    "es": {
        "intro": (
            "¡Hola! Soy Valer-IA, la asistente virtual de Manuelita 🌱. Puedo contarte de sus "
            "productos, negocios, sostenibilidad, cifras y canales oficiales, siempre con fuentes. "
            "Escríbeme o mándame una nota de voz."
        ),
        "unsupported": (
            "Por ahora puedo leer mensajes y escuchar notas de voz, pero no ver imágenes ni "
            "archivos. ¿Me cuentas qué necesitas?"
        ),
        "unheard": "No te escuché bien. ¿Me lo repites o me lo escribes?",
        "error": (
            "Tuve un problema para responder en este momento. ¿Me lo intentas de nuevo en un "
            "minuto?"
        ),
        "queue_timeout": (
            "Sigo con tu mensaje anterior. Cuando te responda, cuéntame de nuevo esto último, "
            "por favor."
        ),
        # Spec 031: límites del canal abierto (sin comandos ni cifras del límite).
        "rate_limited": (
            "Recibí varios mensajes seguidos; dame unos minutos y seguimos conversando."
        ),
        "daily_capped": "Por hoy llegamos al máximo de mensajes; mañana con gusto seguimos.",
        "restart": "Listo, empezamos de cero. ¿Sobre qué quieres conversar?",
        "restart_notice": "Listo, empezamos de cero.",
        "format_text": "Claro, de ahora en adelante te respondo por escrito.",
        "format_voice": "¡Con gusto! Te respondo con notas de voz.",
        "confirm": "Antes de hacerlo, confírmame: {action} ¿Lo hago?",
        "reask": "Solo para estar segura: {action} ¿Lo hago o lo dejamos así?",
        "done": "Hecho.",
        "cancelled": "Perfecto, no hice ningún cambio.",
        "superseded": "Dejé sin hacer lo anterior y no hice cambios.",
        "expired": (
            "Esa confirmación ya venció y no hice cambios. Si quieres, lo intentamos de nuevo."
        ),
        "expired_notice": "La confirmación anterior venció y no hice cambios.",
        "voice_failed": (
            "Esta vez no pude enviarte el audio, pero aquí tienes la respuesta por escrito."
        ),
        "trace_empty": "Todavía no he respondido ninguna pregunta en esta conversación.",
        "stickers_off": "Listo, no te enviaré más stickers en esta conversación.",  # spec 037
    },
    "en": {
        "intro": (
            "Hi! I'm Valer-IA, Manuelita's virtual assistant 🌱. I can tell you about its "
            "products, businesses, sustainability, figures and official channels, always with "
            "sources. "
            "Write to me or send me a voice note."
        ),
        "unsupported": (
            "For now I can read messages and listen to voice notes, but I can't see images or "
            "files. What do you need?"
        ),
        "unheard": "I couldn't hear you well. Could you say it again or write it?",
        "error": "I had a problem answering right now. Could you try again in a minute?",
        "queue_timeout": (
            "I'm still working on your previous message. Once I answer, please tell me this "
            "last one again."
        ),
        "restart": "Done, we're starting fresh. What would you like to talk about?",
        "restart_notice": "Done, we're starting fresh.",
        "format_text": "Sure, from now on I'll reply in writing.",
        "format_voice": "Happy to! I'll reply with voice notes.",
        "confirm": "Before I do it, please confirm: {action} Shall I go ahead?",
        "reask": "Just to be sure: {action} Shall I go ahead or leave it?",
        "done": "Done.",
        "cancelled": "Alright, I didn't change anything.",
        "superseded": "I left the previous request undone and changed nothing.",
        "expired": "That confirmation expired and I changed nothing. We can try again if you like.",
        "expired_notice": "The previous confirmation expired and I changed nothing.",
        "voice_failed": "I couldn't send the audio this time, but here is the written answer.",
        "trace_empty": "I haven't answered any question in this conversation yet.",
        "stickers_off": "Got it, no more stickers in this conversation.",  # spec 037
        "rate_limited": (
            "I got several messages in a row; give me a few minutes and we'll keep talking."
        ),
        "daily_capped": "We've reached today's message limit; I'll be happy to continue tomorrow.",
    },
}

# Acción pendiente en lenguaje natural (contracts/conversation.md § Acción pendiente).
ACTIONS: dict[str, dict[str, str]] = {
    "forget_memory": {
        "es": "voy a borrar lo que me contaste de ti (tu perfil y tus preferencias).",
        "en": "I'll delete what you told me about yourself (your profile and preferences).",
    },
    "save_preference": {
        "es": "voy a recordar esta preferencia para próximas conversaciones: «{value}».",
        "en": "I'll remember this preference for future conversations: “{value}”.",
    },
    "save_profile": {
        "es": "voy a recordar estos datos tuyos: {fields}.",
        "en": "I'll remember these details about you: {fields}.",
    },
    "remember_client": {
        "es": "voy a recordar tu nombre: {name}.",
        "en": "I'll remember your name: {name}.",
    },
    "export_conversation": {
        "es": "voy a exportar esta conversación en un documento.",
        "en": "I'll export this conversation as a document.",
    },
    "request_human_contact": {
        "es": "voy a registrar tu solicitud para que una persona de Manuelita te contacte sobre "
        "«{topic}».",
        "en": "I'll register your request for someone from Manuelita to contact you about "
        "“{topic}”.",
    },
    "save_production_proposal": {
        "es": "voy a guardar esta propuesta de producción para que la revise el equipo de planta.",
        "en": "I'll save this production proposal for the plant team to review.",
    },
}
GENERIC_ACTION = {
    "es": "voy a guardar ese cambio.",
    "en": "I'll save that change.",
}


class ChatServiceLike(Protocol):
    def send(self, message: str, **kwargs: Any) -> Any: ...

    def resume(self, thread_id: str, **kwargs: Any) -> Any: ...


class VoicePort(Protocol):
    """Nota de voz de respuesta (spec 028); la implementa ``channels.voice.ChannelVoice``."""

    def for_answer(
        self, question: str, answer: str, language: str, *, with_sources: bool = False
    ) -> Any: ...

    def for_text(self, text: str, language: str) -> Any: ...


@dataclass(slots=True)
class InboundMessage:
    channel: Channel
    message_id: str
    sender: str
    kind: MessageKind = "text"
    text: str | None = None
    # Spec 028: nota de voz transcrita por el gateway y pista de idioma del dictado.
    input_mode: InputMode = "text"
    language_hint: str | None = None
    # Spec 033: marca del mensaje original (ISO 8601); con ella se descartan entregas tardías.
    received_at: str | None = None


def _norm(text: str) -> str:
    """Texto comparable: sin tildes, mayúsculas, signos ni espacios repetidos."""
    plain_text = unicodedata.normalize("NFKD", text or "")
    plain_text = "".join(ch for ch in plain_text if not unicodedata.combining(ch)).lower()
    return " ".join("".join(ch if ch.isalnum() else " " for ch in plain_text).split())


class RecentTranscriptions:
    """Spec 029: transcripciones recientes de notas de voz hechas por el backend.

    En OpenClaw 2026.11.10 el plugin no sabe si un mensaje fue una nota de voz: ``before_dispatch``
    solo trae el texto ya transcrito y ``message_received`` llega sin adjuntos en WhatsApp. Pero
    cada nota de voz pasa por ``POST /api/channels/transcriptions`` (el CLI de
    ``tools.media.audio``): si el mensaje coincide con una transcripción de los últimos minutos, es
    una nota de voz. Solo se guarda una huella normalizada en memoria, nunca en disco ni en logs.
    """

    def __init__(self, ttl_seconds: float = 600.0, max_items: int = 200, clock=time.monotonic):
        self._items: dict[str, tuple[float, str | None]] = {}
        self._lock = threading.Lock()
        self._ttl = ttl_seconds
        self._max = max_items
        self._clock = clock

    def note(self, text: str, language: str | None) -> None:
        key = _norm(text)
        if len(key) < 3:
            return
        now = self._clock()
        with self._lock:
            for old, (at, _lang) in list(self._items.items()):
                if now - at > self._ttl or len(self._items) >= self._max:
                    del self._items[old]
            self._items[key] = (now, language if language in ("es", "en") else None)

    def take(self, text: str | None) -> tuple[bool, str | None]:
        """``(True, idioma)`` si el texto es una transcripción reciente (se consume una vez)."""
        value = _norm(text or "")
        if not value:
            return False, None
        now = self._clock()
        with self._lock:
            for key, (at, language) in list(self._items.items()):
                if now - at > self._ttl:
                    del self._items[key]
                    continue
                if key == value or key in value:
                    del self._items[key]
                    return True, language
        return False, None


@dataclass(slots=True)
class ChannelReply:
    status: ReplyStatus
    messages: list[str] = field(default_factory=list)
    thread_id: str | None = None
    route: str | None = None
    tools: list[str] = field(default_factory=list)
    latency_ms: int = 0
    event: str | None = None  # evento auditable sin datos personales
    voice: dict[str, Any] | None = None  # spec 028: nota de voz (channel-api-v2 §1)
    language: str | None = None
    reply_format: str | None = None
    script_ms: int | None = None
    voice_ms: int | None = None
    spoken: str | None = None  # texto que se convertirá en voz (no sale del backend)
    question: str | None = None  # pregunta del turno, para el guion hablado (no sale)
    # Spec 030: con nota de voz, el texto que la acompaña es solo el bloque de fuentes.
    sources_messages: list[str] = field(default_factory=list)
    citations: list[dict[str, Any]] = field(default_factory=list)  # citas del turno (no salen)
    # Spec 032: inicio de conversación y presentación (no salen del backend, salvo en el texto).
    conversation_start: str | None = None  # first_contact | inactivity | restart
    introduced: str | None = None  # bridge | agent: quién puso la presentación
    opening: str | None = None  # presentación hablada que abre la nota de voz
    spoken_body: str | None = None  # respuesta hablada sin la presentación (guion de voz)
    client_name: str | None = None  # nombre reconocido por el servicio, si lo hay
    # Spec 034: señales del turno para el sticker y el sticker elegido (lo entrega el plugin).
    act: str | None = None
    sentiment: str | None = None
    style: str | None = None  # spec 036: nivel del estilo caleño del turno (para la nota de voz)
    scope_reason: str | None = None  # spec 037: motivo de fuera de alcance (crisis sin sticker)
    fallback: bool = False  # spec 037: respuesta de evidencia insuficiente (sin sticker)
    notices: list[str] = field(default_factory=list)
    approved_action: str | None = None
    sticker: StickerChoice | None = None

    @property
    def written(self) -> str:
        """Qué va por escrito si la voz se entrega: ``full``, ``sources`` o ``none`` (spec 030)."""
        if self.voice is None:
            return "full"
        return "sources" if self.sources_messages else "none"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "messages": self.messages,
            "sources_messages": self.sources_messages,
            "thread_id": self.thread_id,
            "route": self.route,
            "tools": self.tools,
            "latency_ms": self.latency_ms,
            "voice": self.voice,
            "sticker": self.sticker.to_dict() if self.sticker else None,  # spec 034
        }


def _kind_of(message: InboundMessage) -> str | None:
    """Spec 033: ``phone``, ``lid`` o ``telegram`` para el registro (nunca el valor)."""
    try:
        return sender_kind(message.sender, message.channel)
    except SenderError:
        return None


def action_phrase(tool: str, args: Mapping[str, Any], language: str) -> str:
    """Resumen natural de la escritura propuesta, en el idioma de la persona."""
    template = ACTIONS.get(tool, {}).get(language) or GENERIC_ACTION[language]
    fields = ", ".join(
        str(value)
        for key in ("name", "workplace", "role", "city")
        if (value := args.get(key)) not in (None, "")
    )
    values = {
        "value": args.get("value") or "",
        "fields": fields or "—",
        "name": args.get("name") or "—",
        "topic": args.get("topic") or "—",
    }
    return template.format(**values)


def _turn_dict(outcome: Any) -> dict[str, Any]:
    turn = getattr(outcome, "turn", None)
    if turn is None:
        return {}
    return turn.model_dump(mode="json") if hasattr(turn, "model_dump") else dict(turn)


def _tools_of(turn: Mapping[str, Any]) -> list[str]:
    names = [str(item.get("name")) for item in turn.get("tools") or [] if item.get("name")]
    return list(dict.fromkeys(names))


@dataclass
class LastTrace:
    route: str | None
    plan_steps: list[str]
    tools: list[dict[str, Any]]
    profile: str = "visitante"  # spec 025


class ChannelBridge:
    """Atiende mensajes del canal sobre ``ChatService`` (variante agente)."""

    def __init__(
        self,
        service: ChatServiceLike,
        store: ChannelStore,
        config: ChannelsConfig,
        *,
        salt: str,
        mode: str = "real",
        log_dir: Path | None = None,
        workspace: Path | None = None,
        clock: Callable[[], float] = time.monotonic,
        voice: VoicePort | None = None,
    ) -> None:
        self.service = service
        self.store = store
        self.config = config
        self.salt = salt
        self.mode = mode
        self.log_dir = log_dir
        self.workspace = workspace
        self.voice = voice
        self._clock = clock
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._last: dict[str, LastTrace] = {}
        # Spec 025: perfil elegido que se aplica en el siguiente turno del hilo.
        self._pending_profile: dict[str, str] = {}
        # Spec 029: huellas de las notas de voz transcritas (ver RecentTranscriptions).
        self.transcriptions = RecentTranscriptions()
        # Spec 029: idioma del último turno de cada persona (respaldo para mensajes muy cortos).
        self._languages: dict[str, Language] = {}
        self._stickers: StickerCatalog | None = None  # spec 034: catálogo perezoso

    # -- utilidades -----------------------------------------------------------------------
    def _lock_for(self, user_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(user_id, threading.Lock())

    def _format(
        self, answer: str, citations: list[dict[str, Any]], language: str = "es"
    ) -> list[str]:
        return to_whatsapp(
            answer,
            citations,
            max_chars=self.config.reply_max_chars,
            max_messages=self.config.max_messages,
            language=language,
        )

    def _short(self, text: str, language: str = "es") -> list[str]:
        return self._format(text, [], language)

    def _turn_language(self, message: InboundMessage, user_id: str) -> Language:
        """Spec 029 (FR-004): idioma del turno; con ≤ 3 palabras y sin pista, el del previo."""
        text = message.text or ""
        previous = self._languages.get(user_id)
        if message.language_hint not in ("es", "en") and previous and len(text.split()) <= 3:
            return previous
        return language_of(text, message.language_hint)

    def _say(
        self,
        status: ReplyStatus,
        key: str,
        language: str,
        thread_id: str | None,
        **values: Any,
    ) -> ChannelReply:
        text = TEXTS[language][key].format(**values) if values else TEXTS[language][key]
        return ChannelReply(status, self._short(text, language), thread_id, spoken=text)

    def _record(
        self, message: InboundMessage, user_id: str, reply: ChannelReply, **extra: Any
    ) -> None:
        record = ChannelLogRecord.for_message(
            message.message_id,
            channel=message.channel,
            user_id=user_id,
            status=reply.status,
            kind=message.kind,
            thread_id=reply.thread_id,
            route=reply.route,
            tools=reply.tools,
            latency_ms=reply.latency_ms,
            event=reply.event,
            input_mode=message.input_mode,
            language=reply.language,
            reply_format=reply.reply_format,
            script_ms=reply.script_ms,
            voice_ms=reply.voice_ms,
            voice_sent=reply.voice is not None,
            written=reply.written if reply.status != "ignored" else None,
            conversation_start=reply.conversation_start,
            introduced=reply.introduced,
            sender_kind=_kind_of(message),
            sticker=reply.sticker.name if reply.sticker else None,
            **extra,
        )
        log_channel(self.log_dir, record)
        if reply.status != "ignored":
            append_daily(record, self.workspace)

    # -- entrada ---------------------------------------------------------------------------
    def handle(self, message: InboundMessage) -> ChannelReply:
        started = self._clock()
        if message.kind == "text" and message.input_mode != "voice":
            voice, spoken_language = self.transcriptions.take(message.text)
            if voice:  # spec 029: el texto es la transcripción de una nota de voz
                message = replace(
                    message,
                    kind="audio",
                    input_mode="voice",
                    language_hint=message.language_hint or spoken_language,
                )
        user_id = pseudonym(message.sender, self.salt, message.channel)
        language = self._turn_language(message, user_id)
        if self.store.seen(message.message_id, retention_hours=self.config.dedupe_hours):
            reply = ChannelReply("ignored")
            self._record(message, user_id, reply)
            return reply
        if self._is_stale(message):
            # Spec 033 (FR-010): un mensaje retenido demasiado tiempo no recibe respuesta tardía.
            reply = ChannelReply("ignored", event="stale")
            reply.language = language
            self._record(message, user_id, reply)
            return reply
        gated = self._gate(user_id, language)
        if (
            gated is not None
        ):  # spec 031: bloqueado o sobre el límite; no ocupa la cola ni el modelo
            gated.language = language
            self._record(message, user_id, gated)
            return gated
        lock = self._lock_for(user_id)
        # Spec 028 (FR-018): los mensajes de una persona esperan su turno, en orden.
        if not lock.acquire(timeout=self.config.queue_wait_seconds):
            reply = self._say("busy", "queue_timeout", language, None)
            reply.event = "queue_timeout"
            reply.language = language
            self._record(message, user_id, reply)
            return reply
        error_code: str | None = None
        try:
            thread_id, start = self.store.open_conversation(
                user_id,
                message.channel,
                mask(message.sender, message.channel),
                idle_hours=self.config.conversation_idle_hours,
            )
            try:
                reply = self._dispatch(message, user_id, thread_id, language)
            except Exception as exc:  # el canal nunca recibe trazas internas
                error_code = getattr(exc, "code", None) or type(exc).__name__
                reply = self._say("error", "error", language, thread_id)
            reply.conversation_start = reply.conversation_start or start
            self._choose_sticker(message, reply, language)  # spec 034
            if reply.status == "error":
                self._identify(reply, reply.thread_id or thread_id, language)
            reply.language = reply.language or language
            self._languages[user_id] = language
            if reply.status != "error":
                self._attach_voice(message, reply)
        finally:
            lock.release()
        reply.latency_ms = int((self._clock() - started) * 1000)
        self._record(message, user_id, reply, error_code=error_code)
        return reply

    def _is_stale(self, message: InboundMessage) -> bool:
        """Spec 033: ``True`` si el mensaje original es más viejo que ``stale_minutes``."""
        if not message.received_at:
            return False
        try:
            sent = datetime.fromisoformat(message.received_at.replace("Z", "+00:00"))
        except ValueError:
            return False  # marca inválida: se atiende
        if sent.tzinfo is None:
            sent = sent.replace(tzinfo=UTC)
        now = self.store.now()
        if now.tzinfo is None:
            now = now.replace(tzinfo=UTC)
        # Más de un día (o en el futuro) indica una marca inconsistente (p. ej. otra unidad):
        # se atiende, para que un error de marca nunca deje el canal en silencio.
        age = now - sent
        return timedelta(minutes=self.config.stale_minutes) < age <= timedelta(days=1)

    def _gate(self, user_id: str, language: Language) -> ChannelReply | None:
        """Spec 031: bloqueo y límites por seudónimo antes de la cola (operadores sin límites)."""
        if self.store.is_blocked(user_id):
            return ChannelReply("ignored", event="blocked")
        decision, usage = limit_decision(
            self.store.get_usage(user_id),
            self.store.now(),
            self.config,
            operator=user_id in operators(),
        )
        self.store.save_usage(user_id, usage)
        if decision == "allow":
            return None
        daily = usage.day_count >= self.config.daily_max_messages
        event = "daily_capped" if daily else "rate_limited"
        if decision == "silent":
            return ChannelReply("ignored", event=event)
        reply = self._say("busy", event, language, None)
        reply.event = event
        return reply

    def _dispatch(
        self, message: InboundMessage, user_id: str, thread_id: str, language: Language
    ) -> ChannelReply:
        text = (message.text or "").strip()[:AGENT_MAX_CHARS]
        if message.kind == "audio" or message.input_mode == "voice":
            if not plain(text):
                reply = self._say("answered", "unheard", language, thread_id)
                return self._introduce(reply, language)
        elif message.kind != "text" or not text:
            reply = self._say("unsupported", "unsupported", language, thread_id)
            return self._introduce(reply, language)
        command = plain(text).split()[0] if text.startswith("/") else ""
        command = f"/{command}" if command and not command.startswith("/") else command
        team = operators()
        # Spec 031: con operadores definidos, los atajos ocultos son solo para ellos; para el resto
        # el texto sigue como conversación (salvo /olvidar y /cancelar, que son de la persona).
        if (
            command in OPERATOR_SHORTCUTS
            and command not in {"/olvidar", "/cancelar"}
            and team
            and user_id not in team
        ):
            command = ""
        shortcut = self._shortcut(command, text, user_id, thread_id, message.channel, language)
        if shortcut is not None:
            return shortcut

        notices: list[str] = []
        pending = self.store.get_pending(thread_id)
        intent = "none" if command else detect_intent(text)
        if pending is not None:
            if pending.expired(self.store.now()):
                self._resume(thread_id, pending.action_id, "reject")
                self.store.resolve_pending(thread_id, "expired")
                if decision_of(text) in {"approve", "reject"}:
                    return self._say("answered", "expired", language, thread_id)
                notices.append(TEXTS[language]["expired_notice"])
            else:
                decision = "reject" if command == "/cancelar" else decision_of(text)
                if decision in {"approve", "reject"}:
                    return self._resolve(
                        thread_id, pending.action_id, decision, language, tool=pending.tool
                    )
                new_topic = looks_like_new_question(text)
                if intent == "none" and (decision == "ambiguous" or not new_topic):
                    return self._say(
                        "pending_approval", "reask", language, thread_id, action=pending.summary
                    )
                # Cambió de tema (o pidió empezar de nuevo): la acción no se ejecuta.
                self._resume(thread_id, pending.action_id, "reject")
                self.store.resolve_pending(thread_id, "superseded")
                notices.append(TEXTS[language]["superseded"])

        start: str | None = None
        if intent == "restart":
            thread_id = self.store.new_thread(user_id)
            start = "restart"  # spec 032: la presentación va con la siguiente solicitud
            rest = remainder(text, intent)
            if not rest:
                reply = self._say("answered", "restart", language, thread_id)
                reply.conversation_start = start
                return self._with_notices(reply, notices, language)
            notices.append(TEXTS[language]["restart_notice"])
            text = rest
        elif intent in {"format_text", "format_voice"}:
            self.store.set_reply_format(thread_id, "text" if intent == "format_text" else "voice")
            rest = remainder(text, intent)
            if not rest:
                reply = self._say("answered", intent, language, thread_id)
                return self._with_notices(reply, notices, language)
            notices.append(TEXTS[language][intent])
            text = rest

        prompt = FORGET_PROMPT if command == "/olvidar" else text
        outcome = self._send(prompt, user_id, thread_id, message.channel, language)
        thread_id = str(getattr(outcome, "thread_id", None) or thread_id)
        reply = self._from_outcome(outcome, user_id, thread_id, language)
        reply.question = text
        reply.conversation_start = start
        if reply.status == "answered":
            # Spec 032: la presentación va antes de la respuesta y después de los avisos.
            self._introduce(reply, language)
        return self._with_notices(reply, notices, language)

    def _with_notices(
        self, reply: ChannelReply, notices: list[str], language: str = "es"
    ) -> ChannelReply:
        if notices:
            reply.messages = [*self._short(" ".join(notices), language), *reply.messages]
            if reply.spoken:
                reply.spoken = " ".join([*notices, reply.spoken])
            if reply.opening:
                reply.opening = " ".join([*notices, reply.opening])
        return reply

    # -- stickers (spec 034) -----------------------------------------------------------------
    @property
    def stickers(self) -> StickerCatalog:
        """Catálogo de stickers, cargado una vez (un archivo faltante solo apaga ese sticker)."""
        if self._stickers is None:
            self._stickers = load_catalog()
        return self._stickers

    def _choose_sticker(
        self, message: InboundMessage, reply: ChannelReply, language: Language
    ) -> None:
        """Decide el sticker de la respuesta; un fallo nunca afecta la respuesta (FR-009)."""
        thread_id = reply.thread_id
        if reply.status not in ("answered", "approval_resolved") or not thread_id:
            return
        if OPT_OUT.search(plain_text(message.text or "")):
            # Spec 037 (FR-012): no más stickers en esta conversación, con una confirmación breve.
            try:
                self.store.set_stickers_off(thread_id)
            except Exception:
                return
            confirm = TEXTS[reply.language or language].get("stickers_off")
            if confirm and reply.messages:
                reply.messages = [*reply.messages[:-1], f"{reply.messages[-1]}\n\n{confirm}"]
            return
        try:
            turn_no = self.store.count_answered(thread_id)
            signals = TurnSignals(
                status=reply.status,
                event=reply.event,
                route=reply.route,
                act=reply.act,
                sentiment=reply.sentiment,
                notices=tuple(reply.notices),
                language=reply.language or language,
                conversation_start=reply.conversation_start,
                approved_action=reply.approved_action,
                factual=bool(reply.citations or reply.tools),
                text=message.text or "",
                cited=bool(reply.citations),  # spec 037
                fallback=reply.fallback,
                crisis=reply.route == "out_of_scope" and reply.scope_reason == "crisis",
                low_mood=bool(LOW_MOOD.search(normalize(message.text or ""))),
                introduced=reply.introduced == "bridge",
            )
            usage = self.store.sticker_usage(thread_id, turn_no)
            choice = choose(signals, usage, self.stickers, self.config)
        except Exception:  # el sticker es un adorno: nunca tumba la respuesta
            return
        if choice is not None:
            self.store.record_sticker(thread_id, choice.name, turn_no, choice.situation)
            reply.sticker = choice

    # -- presentación (spec 032) -----------------------------------------------------------
    def _introduce(self, reply: ChannelReply, language: Language) -> ChannelReply:
        """Antepone la presentación en la primera respuesta atendida del hilo (contrato §3)."""
        thread_id = reply.thread_id
        if not thread_id or self.store.is_introduced(thread_id):
            return reply
        text = reply.spoken or (reply.messages[0] if reply.messages else "")
        if already_introduced(text):
            reply.introduced = "agent"  # el modelo ya se presentó (p. ej. ante «Hola»)
        else:
            intro = introduction(language, thread_id, reply.client_name)
            reply.messages = self._with_intro(intro, reply.messages, language)
            if reply.spoken:
                reply.spoken_body = merge("", reply.spoken)
            reply.spoken = merge(intro, reply.spoken or "")
            reply.opening = intro
            reply.introduced = "bridge"
        self.store.mark_introduced(thread_id)
        return reply

    def _with_intro(self, intro: str, messages: list[str], language: Language) -> list[str]:
        """La presentación en el primer mensaje; si no cabe, como mensaje propio (T013)."""
        if not messages:
            return self._short(intro, language)
        first = merge(intro, messages[0])
        if len(first) <= self.config.reply_max_chars:
            return [first, *messages[1:]]
        body = merge("", messages[0])
        return [intro, *([body] if body else []), *messages[1:]]

    def _identify(self, reply: ChannelReply, thread_id: str | None, language: Language) -> None:
        """Errores en un hilo sin presentar: una frase de identidad, sin marcar el hilo (R7)."""
        if not thread_id or self.store.is_introduced(thread_id) or not reply.messages:
            return
        line = identity_line(language)
        reply.messages = [f"{line} {reply.messages[0]}", *reply.messages[1:]]
        if reply.spoken:
            reply.spoken = f"{line} {reply.spoken}"

    def _shortcut(
        self,
        command: str,
        text: str,
        user_id: str,
        thread_id: str,
        channel: str,
        language: Language,
    ) -> ChannelReply | None:
        """Atajos ocultos del operador (spec 024); nunca se anuncian a las personas."""
        if command not in OPERATOR_SHORTCUTS:
            return None
        if command == "/ayuda":
            return self._say("answered", "intro", language, thread_id)
        if command == "/traza":
            trace = self._trace_text(user_id, language)
            reply = ChannelReply("answered", self._short(trace, language))
            reply.thread_id = thread_id
            return reply
        if command == "/nuevo":
            new_thread = self.store.new_thread(user_id)
            return self._say("answered", "restart", language, new_thread)
        if command == "/perfil":
            return self._profile_command(text, user_id, thread_id, channel, language)
        return None  # /olvidar y /cancelar siguen el flujo normal

    def _profile_command(
        self, text: str, user_id: str, thread_id: str, channel: str, language: Language
    ) -> ChannelReply:
        """Spec 025: lista los perfiles o activa uno en el hilo (atajo del operador)."""
        from ..agent import profiles

        argument = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else ""
        current = self._pending_profile.get(user_id) or self._current_profile(user_id)
        if not argument.strip():
            lines = ["*Perfiles de atención*:"]
            for item in profiles.describe(user_id, channel):
                mark = " ✅" if item["key"] == current else ""
                lines.append(f"• {item['key']} — {item['label']}{mark}")
            return ChannelReply("answered", self._short("\n".join(lines)), thread_id)
        key = profiles.resolve_alias(argument)
        if key is None or key not in profiles.load_profiles():
            reply = "No conozco ese perfil." if language == "es" else "I don't know that profile."
            return ChannelReply("answered", self._short(reply), thread_id)
        chosen = profiles.get_profile(key)
        if chosen.requires_authorization and not profiles.is_authorized(user_id, channel):
            self._pending_profile[user_id] = profiles.DEFAULT_PROFILE
            return ChannelReply(
                "answered",
                self._short("Ese perfil no está disponible en este canal."),
                thread_id,
                event="planner_denied",
            )
        self._pending_profile[user_id] = chosen.key
        reply = f"Listo: ahora te atiendo como {chosen.label}."
        return ChannelReply("answered", self._short(reply), thread_id)

    def _current_profile(self, user_id: str) -> str:
        last = self._last.get(user_id)
        return last.profile if last is not None else "visitante"

    def _send(
        self,
        prompt: str,
        user_id: str,
        thread_id: str,
        channel: str = "whatsapp",
        language: str | None = None,
    ) -> Any:
        """Turno del agente; el primer turno de un hilo nuevo lo crea el propio servicio."""
        fresh = not self.store.is_started(thread_id)
        extra: dict[str, Any] = {}
        profile = self._pending_profile.pop(user_id, None)
        if profile is not None:
            extra["profile"] = profile
        outcome = self.service.send(
            prompt,
            thread_id=None if fresh else thread_id,
            user_id=user_id,
            variant="agent",
            mode=self.mode,
            channel=channel,
            language=language,  # spec 029: el agente responde en el idioma del turno
            **extra,
        )
        created = str(getattr(outcome, "thread_id", None) or thread_id)
        if fresh:
            self.store.adopt_thread(user_id, thread_id, created)
        return outcome

    # -- salida ----------------------------------------------------------------------------
    def _remember_trace(self, user_id: str, turn: Mapping[str, Any]) -> None:
        route = (turn.get("route") or {}).get("route")
        self._last[user_id] = LastTrace(
            route,
            list(turn.get("plan_steps") or []),
            list(turn.get("tools") or []),
            str(turn.get("profile") or "visitante"),
        )

    def _from_outcome(
        self, outcome: Any, user_id: str, thread_id: str, language: Language
    ) -> ChannelReply:
        turn = _turn_dict(outcome)
        route = (turn.get("route") or {}).get("route")
        status = getattr(outcome, "status", "answered")
        if status == "pending_approval" and getattr(outcome, "pending_action", None):
            action = outcome.pending_action
            tool = str(action.get("tool"))
            summary = action_phrase(tool, action.get("args") or {}, language)
            self.store.set_pending(
                thread_id,
                str(action.get("action_id")),
                tool,
                summary,
                ttl_minutes=self.config.approval_ttl_minutes,
            )
            reply = self._say("pending_approval", "confirm", language, thread_id, action=summary)
            reply.route, reply.tools = route, [tool]
            return reply
        self._remember_trace(user_id, turn)
        if route:
            self.store.set_last_route(thread_id, route)
        answer = str(turn.get("answer") or "")
        messages = self._format(answer, list(turn.get("citations") or []), language)
        if not messages:
            return self._say("error", "error", language, thread_id)
        reply = ChannelReply("answered", messages, thread_id, route, _tools_of(turn))
        reply.spoken = answer
        route_info = turn.get("route") or {}
        reply.act = route_info.get("act")  # spec 034: acto y sentimiento del enrutador
        reply.sentiment = route_info.get("sentiment")
        reply.style = route_info.get("style")
        reply.scope_reason = route_info.get("scope_reason")  # spec 037
        reply.fallback = bool(turn.get("fallback"))
        reply.notices = [str(n) for n in (getattr(outcome, "notices", None) or [])]
        client = getattr(outcome, "client", None)
        if isinstance(client, Mapping) and client.get("name"):
            reply.client_name = str(client["name"])  # spec 032: saludo con el nombre
        reply.citations = list(turn.get("citations") or [])
        return reply

    def _resume(self, thread_id: str, action_id: str, decision: str) -> Any:
        return self.service.resume(thread_id, action_id=action_id, decision=decision)

    def _resolve(
        self,
        thread_id: str,
        action_id: str,
        decision: str,
        language: Language,
        *,
        tool: str | None = None,
    ) -> ChannelReply:
        outcome = self._resume(thread_id, action_id, decision)
        self.store.resolve_pending(thread_id, "approved" if decision == "approve" else "rejected")
        turn = _turn_dict(outcome)
        answer = str(turn.get("answer") or "")
        if not answer:
            answer = TEXTS[language]["done" if decision == "approve" else "cancelled"]
        route = (turn.get("route") or {}).get("route")
        reply = ChannelReply(
            "approval_resolved", self._short(answer, language), thread_id, route, _tools_of(turn),
            spoken=answer,
        )  # fmt: skip
        if decision == "approve":
            reply.approved_action = tool or "action"  # spec 034: «¡Listo!» o «Gracias por confiar»
        return reply

    # -- voz (spec 028) ----------------------------------------------------------------------
    def _wants_voice(self, message: InboundMessage, thread_id: str | None) -> tuple[bool, str]:
        reply_format = self.store.get_reply_format(thread_id) if thread_id else "auto"
        if reply_format == "voice":
            return True, reply_format
        voice_input = message.input_mode == "voice" or message.kind == "audio"
        return reply_format == "auto" and voice_input, reply_format

    def _attach_voice(self, message: InboundMessage, reply: ChannelReply) -> None:
        """Nota de voz de respuesta (spec 028) y el texto que la acompaña (spec 030).

        Con voz, ``sources_messages`` lleva solo el bloque de fuentes (o nada) y ``messages`` queda
        con la respuesta completa como respaldo: el plugin la entrega si la nota de voz no llega. Si
        la voz no se puede generar, no hay ``sources_messages`` y va el texto completo con el aviso
        ``voice_failed``.
        """
        wants, reply.reply_format = self._wants_voice(message, reply.thread_id)
        if not (wants and self.config.voice_notes and self.voice is not None and reply.spoken):
            return
        language = reply.language or "es"
        sources = (
            sources_only(
                reply.spoken,
                reply.citations,
                language=language,
                max_chars=self.config.reply_max_chars,
            )
            if reply.citations
            else []
        )
        try:
            if reply.status == "answered" and reply.question and reply.route:
                extra: dict[str, Any] = {}
                body = reply.spoken
                if reply.opening:  # spec 032: el guion se arma sin la presentación y luego la lleva
                    extra["opening"] = reply.opening
                    body = reply.spoken_body or ""
                if reply.style:
                    extra["style"] = reply.style  # spec 036: estilo caleño del guion
                result = self.voice.for_answer(
                    reply.question, body, language, with_sources=bool(sources), **extra
                )
            else:
                result = self.voice.for_text(reply.spoken, language)
        except Exception:  # la voz nunca tumba la respuesta escrita
            result = None
        if result is None:
            reply.event = reply.event or "voice_error"
            failed = self._short(TEXTS[language]["voice_failed"], language)
            reply.messages = [*reply.messages, *failed]
            return
        reply.sources_messages = sources
        reply.voice = result.to_dict()
        reply.script_ms = getattr(result, "script_ms", None)
        reply.voice_ms = getattr(result, "voice_ms", None)

    # -- traza del operador ----------------------------------------------------------------
    def _trace_text(self, user_id: str, language: Language = "es") -> str:
        last = self._last.get(user_id)
        if last is None:
            return TEXTS[language]["trace_empty"]
        from ..agent.profiles import get_profile

        lines = [f"*Perfil:* {get_profile(last.profile).label}", f"*Ruta:* {last.route or '—'}"]
        if last.plan_steps:
            steps = "\n".join(f"{i}. {step}" for i, step in enumerate(last.plan_steps, 1))
            lines.append(f"*Plan:*\n{steps}")
        if last.tools:
            rendered = []
            for item in last.tools:
                state = "ok" if item.get("ok", True) else f"error: {item.get('error')}"
                rendered.append(
                    f"• {item.get('name')} ({item.get('duration_ms', 0)} ms, {state})"
                    + (f" — {item.get('summary')}" if item.get("summary") else "")
                )
            lines.append("*Herramientas:*\n" + "\n".join(rendered))
        else:
            lines.append("*Herramientas:* ninguna (respuesta directa)")
        return "\n".join(lines)
