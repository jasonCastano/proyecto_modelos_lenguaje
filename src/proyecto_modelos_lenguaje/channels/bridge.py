"""Puente del canal: un mensaje de WhatsApp → un turno de Valer-IA (spec 024, channel-api §1).

El grafo no sabe de WhatsApp: recibe ``user_id`` (seudónimo), ``thread_id`` y texto como cualquier
cliente. Aquí viven la deduplicación, el candado por usuario, los comandos del canal, la
confirmación de escrituras por «SÍ/NO» (research R8) y el formato de la respuesta.
"""

from __future__ import annotations

import re
import threading
import time
import unicodedata
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Literal, Protocol

from ..agent.actions import TOOL_DESCRIPTIONS
from ..agent.config import ChannelsConfig
from .format import to_whatsapp
from .identity import mask, pseudonym
from .journal import ChannelLogRecord, append_daily, log_channel
from .store import ChannelStore

Channel = Literal["whatsapp", "telegram"]
MessageKind = Literal["text", "audio", "image", "video", "document", "sticker", "location", "other"]
ReplyStatus = Literal[
    "answered", "pending_approval", "approval_resolved", "unsupported", "busy", "error", "ignored"
]
AGENT_MAX_CHARS = 2000
YES = {"si", "sí", "s", "confirmo", "confirmar", "dale", "ok", "okay", "vale", "listo", "yes"}
NO = {"no", "n", "cancela", "cancelar", "cancelo", "rechazo", "nop", "/cancelar"}
FORGET_PROMPT = "Olvida todos mis datos guardados: perfil y preferencias."

HELP_TEXT = (
    "Soy *Valer-IA Caña* 🌱, la asistente de Manuelita. Pregúntame por sus productos, "
    "negocios, sostenibilidad, cifras anuales, certificaciones o canales oficiales; cito "
    "siempre mis fuentes.\n\n"
    "Comandos:\n"
    "• /nuevo — empezar otra conversación (recuerdo tu perfil si lo guardaste)\n"
    "• /olvidar — borrar los datos que guardé sobre ti\n"
    "• /traza — ver cómo resolví tu última pregunta (ruta, plan y herramientas)\n"
    "• /perfil — ver o cambiar cómo te atiendo (cliente, proveedor, colaborador…)\n"
    "• /ayuda — este mensaje\n\n"
    "Antes de guardar o enviar algo te pido confirmación: responde *SÍ* o *NO*."
)
UNSUPPORTED_TEXT = (
    "Por ahora solo leo mensajes de texto 🙂. Escríbeme tu pregunta y con gusto te ayudo."
)
BUSY_TEXT = "Sigo con tu mensaje anterior; enseguida te respondo."
ERROR_TEXT = (
    "Tuve un problema para responder en este momento. Inténtalo de nuevo en un minuto, por favor."
)
NEW_THREAD_TEXT = (
    "Listo, empezamos una conversación nueva. Si me habías dado tu nombre, lo sigo recordando."
)
EXPIRED_TEXT = "La confirmación anterior venció y no se ejecutó nada."
PLANNER_DENIED_TEXT = (
    "La planificación industrial es solo para planificadores autorizados. Sigo como visitante."
)


class ChatServiceLike(Protocol):
    def send(self, message: str, **kwargs: Any) -> Any: ...

    def resume(self, thread_id: str, **kwargs: Any) -> Any: ...


@dataclass(slots=True)
class InboundMessage:
    channel: Channel
    message_id: str
    sender: str
    kind: MessageKind = "text"
    text: str | None = None


@dataclass(slots=True)
class ChannelReply:
    status: ReplyStatus
    messages: list[str] = field(default_factory=list)
    thread_id: str | None = None
    route: str | None = None
    tools: list[str] = field(default_factory=list)
    latency_ms: int = 0
    event: str | None = None  # spec 025: evento auditable (p. ej. planner_denied)

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "messages": self.messages,
            "thread_id": self.thread_id,
            "route": self.route,
            "tools": self.tools,
            "latency_ms": self.latency_ms,
        }


def plain(text: str) -> str:
    folded = unicodedata.normalize("NFKD", text.lower())
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch))
    return re.sub(r"[^\w/ ]+", " ", folded).strip()


def decision_of(text: str) -> Literal["approve", "reject"] | None:
    words = plain(text).split()
    if not words or len(words) > 4:
        return None
    if words[0] in {plain(w) for w in YES}:
        return "approve"
    if words[0] in {plain(w) for w in NO}:
        return "reject"
    return None


def describe_action(tool: str, args: Mapping[str, Any]) -> str:
    title = TOOL_DESCRIPTIONS.get(tool, tool)
    details = [f"• {key}: {value}" for key, value in args.items() if value not in (None, "", [])]
    return title + ("\n" + "\n".join(details) if details else "")


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
    ) -> None:
        self.service = service
        self.store = store
        self.config = config
        self.salt = salt
        self.mode = mode
        self.log_dir = log_dir
        self.workspace = workspace
        self._clock = clock
        self._locks: dict[str, threading.Lock] = {}
        self._locks_guard = threading.Lock()
        self._last: dict[str, LastTrace] = {}
        # Spec 025: perfil elegido con /perfil que se aplica en el siguiente turno del hilo.
        self._pending_profile: dict[str, str] = {}

    # -- utilidades -----------------------------------------------------------------------
    def _lock_for(self, user_id: str) -> threading.Lock:
        with self._locks_guard:
            return self._locks.setdefault(user_id, threading.Lock())

    def _format(self, answer: str, citations: list[dict[str, Any]]) -> list[str]:
        return to_whatsapp(
            answer,
            citations,
            max_chars=self.config.reply_max_chars,
            max_messages=self.config.max_messages,
        )

    def _short(self, text: str) -> list[str]:
        return self._format(text, [])

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
            **extra,
        )
        log_channel(self.log_dir, record)
        if reply.status != "ignored":
            append_daily(record, self.workspace)

    # -- entrada ---------------------------------------------------------------------------
    def handle(self, message: InboundMessage) -> ChannelReply:
        started = self._clock()
        user_id = pseudonym(message.sender, self.salt, message.channel)
        if self.store.seen(message.message_id, retention_hours=self.config.dedupe_hours):
            reply = ChannelReply("ignored")
            self._record(message, user_id, reply)
            return reply
        lock = self._lock_for(user_id)
        if not lock.acquire(blocking=False):
            reply = ChannelReply("busy", self._short(BUSY_TEXT))
            self._record(message, user_id, reply)
            return reply
        error_code: str | None = None
        try:
            thread_id = self.store.ensure_user(
                user_id, message.channel, mask(message.sender, message.channel)
            )
            try:
                reply = self._dispatch(message, user_id, thread_id)
            except Exception as exc:  # el canal nunca recibe trazas internas
                error_code = getattr(exc, "code", None) or type(exc).__name__
                reply = ChannelReply("error", self._short(ERROR_TEXT), thread_id)
        finally:
            lock.release()
        reply.latency_ms = int((self._clock() - started) * 1000)
        self._record(message, user_id, reply, error_code=error_code)
        return reply

    def _dispatch(self, message: InboundMessage, user_id: str, thread_id: str) -> ChannelReply:
        if message.kind != "text" or not (message.text or "").strip():
            return ChannelReply("unsupported", self._short(UNSUPPORTED_TEXT), thread_id)
        text = (message.text or "").strip()[:AGENT_MAX_CHARS]
        command = plain(text).split()[0] if text.startswith("/") else ""
        if command == "/ayuda":
            return ChannelReply("answered", self._short(HELP_TEXT), thread_id)
        if command == "/traza":
            return ChannelReply("answered", self._short(self._trace_text(user_id)), thread_id)
        if command == "/nuevo":
            new_thread = self.store.new_thread(user_id)
            return ChannelReply("answered", self._short(NEW_THREAD_TEXT), new_thread)
        if command == "/perfil":
            return self._profile_command(text, user_id, thread_id, message.channel)

        notices: list[str] = []
        pending = self.store.get_pending(thread_id)
        if pending is not None:
            if pending.expired(self.store.now()):
                self._resume(thread_id, pending.action_id, "reject")
                self.store.resolve_pending(thread_id, "expired")
                notices.append(EXPIRED_TEXT)
            else:
                decision = decision_of(text)
                if decision is None and command == "/cancelar":
                    decision = "reject"
                if decision is not None:
                    return self._resolve(thread_id, pending.action_id, decision)
                reminder = (
                    f"Tengo una confirmación pendiente:\n{pending.summary}\n\n"
                    "Responde *SÍ* para confirmar o *NO* para cancelar."
                )
                return ChannelReply("pending_approval", self._short(reminder), thread_id)

        prompt = FORGET_PROMPT if command == "/olvidar" else text
        outcome = self._send(prompt, user_id, thread_id, message.channel)
        thread_id = str(getattr(outcome, "thread_id", None) or thread_id)
        reply = self._from_outcome(outcome, user_id, thread_id)
        if notices:
            reply.messages = [*self._short("\n".join(notices)), *reply.messages]
        return reply

    def _profile_command(
        self, text: str, user_id: str, thread_id: str, channel: str
    ) -> ChannelReply:
        """Spec 025: ``/perfil`` lista los perfiles; ``/perfil <clave>`` activa uno en el hilo."""
        from ..agent import profiles

        argument = text.split(maxsplit=1)[1] if len(text.split(maxsplit=1)) > 1 else ""
        current = self._pending_profile.get(user_id) or self._current_profile(user_id)
        if not argument.strip():
            lines = ["*Perfiles de atención* (escribe /perfil <nombre>):"]
            for item in profiles.describe(user_id, channel):
                mark = " ✅" if item["key"] == current else ""
                lock = " (solo autorizados)" if item["requires_authorization"] else ""
                lines.append(f"• {item['key']} — {item['label']}{lock}{mark}")
            return ChannelReply("answered", self._short("\n".join(lines)), thread_id)
        key = profiles.resolve_alias(argument)
        if key is None or key not in profiles.load_profiles():
            reply = "No conozco ese perfil. Escribe /perfil para ver la lista."
            return ChannelReply("answered", self._short(reply), thread_id)
        chosen = profiles.get_profile(key)
        if chosen.requires_authorization and not profiles.is_authorized(user_id, channel):
            self._pending_profile[user_id] = profiles.DEFAULT_PROFILE
            return ChannelReply(
                "answered",
                self._short(PLANNER_DENIED_TEXT),
                thread_id,
                event="planner_denied",
            )
        self._pending_profile[user_id] = chosen.key
        reply = (
            f"Listo: ahora te atiendo como {chosen.label}. ¿Quieres que lo recuerde para "
            "próximas conversaciones? Escribe «recuerda mi perfil»."
        )
        return ChannelReply("answered", self._short(reply), thread_id)

    def _current_profile(self, user_id: str) -> str:
        last = self._last.get(user_id)
        return last.profile if last is not None else "visitante"

    def _send(self, prompt: str, user_id: str, thread_id: str, channel: str = "whatsapp") -> Any:
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

    def _from_outcome(self, outcome: Any, user_id: str, thread_id: str) -> ChannelReply:
        turn = _turn_dict(outcome)
        route = (turn.get("route") or {}).get("route")
        status = getattr(outcome, "status", "answered")
        if status == "pending_approval" and getattr(outcome, "pending_action", None):
            action = outcome.pending_action
            summary = describe_action(str(action.get("tool")), action.get("args") or {})
            self.store.set_pending(
                thread_id,
                str(action.get("action_id")),
                str(action.get("tool")),
                summary,
                ttl_minutes=self.config.approval_ttl_minutes,
            )
            text = (
                f"Antes de hacerlo necesito tu confirmación:\n{summary}\n\n"
                f"Responde *SÍ* para confirmar o *NO* para cancelar "
                f"(vence en {self.config.approval_ttl_minutes} min)."
            )
            return ChannelReply(
                "pending_approval", self._short(text), thread_id, route, [str(action.get("tool"))]
            )
        self._remember_trace(user_id, turn)
        messages = self._format(str(turn.get("answer") or ""), list(turn.get("citations") or []))
        return ChannelReply(
            "answered", messages or self._short(ERROR_TEXT), thread_id, route, _tools_of(turn)
        )

    def _resume(self, thread_id: str, action_id: str, decision: str) -> Any:
        return self.service.resume(thread_id, action_id=action_id, decision=decision)

    def _resolve(self, thread_id: str, action_id: str, decision: str) -> ChannelReply:
        outcome = self._resume(thread_id, action_id, decision)
        self.store.resolve_pending(thread_id, "approved" if decision == "approve" else "rejected")
        turn = _turn_dict(outcome)
        answer = str(turn.get("answer") or "")
        if not answer:
            answer = "Hecho." if decision == "approve" else "Cancelado: no hice ningún cambio."
        route = (turn.get("route") or {}).get("route")
        return ChannelReply(
            "approval_resolved", self._short(answer), thread_id, route, _tools_of(turn)
        )

    def _trace_text(self, user_id: str) -> str:
        last = self._last.get(user_id)
        if last is None:
            return "Todavía no he respondido ninguna pregunta en esta conversación."
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
