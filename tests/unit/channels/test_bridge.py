"""Puente del canal con un ChatService falso (spec 024 y spec 028: T018, T028, T030, T033)."""

from __future__ import annotations

import itertools
import json
import threading
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from proyecto_modelos_lenguaje.agent.config import ChannelsConfig
from proyecto_modelos_lenguaje.channels.bridge import TEXTS, ChannelBridge, InboundMessage
from proyecto_modelos_lenguaje.channels.store import ChannelStore

SALT = "sal-de-prueba-0123456789"
PHONE = "+573001234567"


@dataclass
class Outcome:
    thread_id: str
    turn: dict[str, Any]
    status: str = "answered"
    pending_action: dict[str, Any] | None = None
    client: dict[str, Any] | None = None  # spec 032: nombre reconocido


@dataclass
class FakeService:
    calls: list[dict[str, Any]] = field(default_factory=list)
    resumes: list[dict[str, Any]] = field(default_factory=list)
    propose: str | None = None
    propose_args: dict[str, Any] = field(default_factory=lambda: {"name": "Ana"})
    fail: bool = False
    gate: threading.Event | None = None
    cite: bool = True
    answer: str | None = None  # spec 032: respuesta fija del modelo (p. ej. un saludo)
    client: dict[str, Any] | None = None
    route_extra: dict[str, Any] = field(default_factory=dict)  # spec 034: act, sentiment…

    def send(self, message: str, **kwargs: Any) -> Outcome:
        outcome = self._answer(message, **kwargs)
        if self.route_extra:
            outcome.turn["route"] = {**(outcome.turn.get("route") or {}), **self.route_extra}
        return outcome

    def _answer(self, message: str, **kwargs: Any) -> Outcome:
        self.calls.append({"message": message, **kwargs})
        if self.gate is not None:
            self.gate.wait(2)
        if self.fail:
            raise RuntimeError("Traceback interno")
        thread = kwargs["thread_id"]
        if self.propose:
            return Outcome(
                thread,
                {"route": {"route": "direct"}},
                "pending_approval",
                {"action_id": "act-1", "tool": self.propose, "args": self.propose_args},
            )
        if self.answer is not None:  # spec 032: respuesta conversacional fija
            return Outcome(
                thread, {"route": {"route": "direct"}, "answer": self.answer}, client=self.client
            )
        if not self.cite:  # spec 030: respuesta conversacional, sin fuentes
            return Outcome(thread, {"route": {"route": "direct"}, "answer": f"Hola: {message}."})
        turn = {
            "route": {"route": "documental"},
            "answer": f"Respuesta a «{message}» [U1].",
            "citations": [{"label": "U1", "url": "https://manuelita.com", "title": "Informe"}],
            "tools": [{"name": "search_documents", "ok": True, "duration_ms": 12}],
            "plan_steps": ["buscar en documentos", "responder con cita"],
        }
        return Outcome(thread, turn, client=self.client)

    def resume(self, thread_id: str, **kwargs: Any) -> Outcome:
        self.resumes.append({"thread_id": thread_id, **kwargs})
        answer = "Guardé tu perfil." if kwargs["decision"] == "approve" else ""
        return Outcome(thread_id, {"route": {"route": "direct"}, "answer": answer})


@dataclass
class VoiceResult:
    language: str
    script: str
    script_ms: int = 5
    voice_ms: int = 7

    def to_dict(self) -> dict[str, Any]:
        return {
            "audio_path": "C:/estado/channels/voice/x.ogg",
            "language": self.language,
            "duration_ms": 1200,
            "mime": "audio/ogg; codecs=opus",
        }


@dataclass
class FakeVoice:
    answers: list[tuple[str, str, str]] = field(default_factory=list)
    texts: list[tuple[str, str]] = field(default_factory=list)
    with_sources: list[bool] = field(default_factory=list)
    openings: list[str | None] = field(default_factory=list)  # spec 032
    fail: bool = False

    def for_answer(
        self,
        question: str,
        answer: str,
        language: str,
        *,
        with_sources: bool = False,
        opening: str | None = None,
    ) -> VoiceResult:
        if self.fail:
            raise RuntimeError("motor de voz caído")
        self.answers.append((question, answer, language))
        self.with_sources.append(with_sources)
        self.openings.append(opening)
        return VoiceResult(language, f"{opening} guion" if opening else "guion")

    def for_text(self, text: str, language: str) -> VoiceResult:
        if self.fail:
            raise RuntimeError("motor de voz caído")
        self.texts.append((text, language))
        return VoiceResult(language, text)


class Clock:
    def __init__(self) -> None:
        self.now = datetime(2026, 11, 28, 13, 0, tzinfo=UTC)

    def __call__(self) -> datetime:
        return self.now


@pytest.fixture()
def clock() -> Clock:
    return Clock()


@pytest.fixture()
def service() -> FakeService:
    return FakeService()


@pytest.fixture()
def voice() -> FakeVoice:
    return FakeVoice()


def make_bridge(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice | None, **config: Any
) -> ChannelBridge:
    store = ChannelStore(tmp_path / "channels.sqlite3", clock=clock)
    return ChannelBridge(
        service,
        store,
        ChannelsConfig(voice_notes=True, **config),
        salt=SALT,
        mode="demo",
        log_dir=tmp_path / "logs",
        workspace=tmp_path / "workspace",
        voice=voice,
    )


@pytest.fixture()
def bridge(tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice) -> ChannelBridge:
    return make_bridge(tmp_path, service, clock, voice)


def msg(text: str | None, message_id: str, kind: str = "text", **extra: Any) -> InboundMessage:
    return InboundMessage("whatsapp", message_id, PHONE, kind, text, **extra)  # type: ignore[arg-type]


def audio(text: str, message_id: str, language: str | None = None) -> InboundMessage:
    return msg(text, message_id, "audio", input_mode="voice", language_hint=language)


# --- comportamiento base (spec 024) ----------------------------------------------------------


def test_answers_in_a_stable_thread(bridge: ChannelBridge, service: FakeService) -> None:
    first = bridge.handle(msg("¿Qué produce Manuelita?", "m1"))
    second = bridge.handle(msg("¿y en Perú?", "m2"))
    assert first.status == second.status == "answered"
    assert first.thread_id == second.thread_id
    assert first.route == "documental" and first.tools == ["search_documents"]
    assert "[1]" in first.messages[0] and "Fuentes:" in first.messages[-1]
    assert service.calls[0]["variant"] == "agent" and service.calls[0]["mode"] == "demo"
    assert service.calls[0]["user_id"].startswith("wa-")


def test_duplicate_is_ignored(bridge: ChannelBridge, service: FakeService) -> None:
    bridge.handle(msg("hola", "m1"))
    again = bridge.handle(msg("hola", "m1"))
    assert again.status == "ignored" and again.messages == []
    assert len(service.calls) == 1


def test_errors_are_short_and_clean(bridge: ChannelBridge, service: FakeService) -> None:
    service.fail = True
    reply = bridge.handle(msg("hola", "m1"))
    # Spec 032 (R7): en un hilo sin presentar, el error dice en una frase quién es Valer-IA.
    assert reply.status == "error" and reply.messages[0].endswith(TEXTS["es"]["error"])
    assert reply.messages[0].startswith("Soy Valer-IA")
    assert "Traceback" not in " ".join(reply.messages)


def test_logs_have_no_text_nor_number(bridge: ChannelBridge, tmp_path: Path) -> None:
    bridge.handle(audio("¿Qué produce Manuelita?", "3EB0C4", "es"))
    log = (tmp_path / "logs" / "channels.jsonl").read_text(encoding="utf-8")
    record = json.loads(log.splitlines()[-1])
    assert record["user_id"].startswith("wa-") and record["status"] == "answered"
    assert record["input_mode"] == "voice" and record["voice_sent"] is True
    assert record["language"] == "es" and record["reply_format"] == "auto"
    assert "Manuelita" not in log and "3001234567" not in log and "3EB0C4" not in log
    assert "guion" not in log  # ni el guion hablado
    daily = next((tmp_path / "workspace" / "memory").glob("*.md")).read_text(encoding="utf-8")
    assert "search_documents" in daily and "3001234567" not in daily


# --- medios y audio sin habla (spec 028) ----------------------------------------------------


def test_images_get_a_natural_answer(bridge: ChannelBridge, service: FakeService) -> None:
    reply = bridge.handle(msg(None, "m1", "image"))
    assert reply.status == "unsupported" and "notas de voz" in reply.messages[0]
    assert service.calls == []


def test_voice_note_without_speech_asks_to_repeat(
    bridge: ChannelBridge, service: FakeService, voice: FakeVoice
) -> None:
    reply = bridge.handle(audio("", "m1"))
    # Spec 032: primer mensaje de un número nuevo, así que va con la presentación.
    assert TEXTS["es"]["unheard"] in " ".join(reply.messages) and service.calls == []
    spoken, language = voice.texts[0]
    assert reply.voice is not None and language == "es"
    assert spoken.startswith("¡Hola") and spoken.endswith(TEXTS["es"]["unheard"])


# --- cola por usuario (T033) ----------------------------------------------------------------


def test_second_message_waits_and_is_answered_in_order(
    bridge: ChannelBridge, service: FakeService
) -> None:
    service.gate = threading.Event()
    results: dict[str, Any] = {}
    first = threading.Thread(target=lambda: results.setdefault("a", bridge.handle(msg("a", "m1"))))
    first.start()
    while not service.calls:
        pass
    second = threading.Thread(target=lambda: results.setdefault("b", bridge.handle(msg("b", "m2"))))
    second.start()
    service.gate.set()
    first.join()
    second.join()
    assert results["a"].status == results["b"].status == "answered"
    assert [call["message"] for call in service.calls] == ["a", "b"]


def test_queue_timeout_is_natural(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice
) -> None:
    bridge = make_bridge(tmp_path, service, clock, voice, queue_wait_seconds=1)
    service.gate = threading.Event()
    worker = threading.Thread(target=lambda: bridge.handle(msg("a", "m1")))
    worker.start()
    while not service.calls:
        pass
    late = bridge.handle(msg("b", "m2"))
    service.gate.set()
    worker.join()
    assert late.status == "busy" and late.event == "queue_timeout"
    assert late.messages[0] == TEXTS["es"]["queue_timeout"]


# --- confirmación natural (T028) --------------------------------------------------------------


@pytest.mark.parametrize("answer", ["dale", "Sí, guárdalo", "go ahead", "claro que sí"])
def test_natural_yes_approves(bridge: ChannelBridge, service: FakeService, answer: str) -> None:
    service.propose = "save_profile"
    pending = bridge.handle(msg("Me llamo Ana", "m1"))
    assert pending.status == "pending_approval"
    assert "Ana" in pending.messages[0] and "¿Lo hago?" in pending.messages[0]
    assert "SÍ" not in pending.messages[0] and "min" not in pending.messages[0]
    done = bridge.handle(msg(answer, "m2"))
    assert done.status == "approval_resolved" and "Guardé" in done.messages[0]
    assert service.resumes[-1]["decision"] == "approve"


@pytest.mark.parametrize("answer", ["mejor no", "déjalo así", "no thanks", "no"])
def test_natural_no_rejects(bridge: ChannelBridge, service: FakeService, answer: str) -> None:
    service.propose = "save_profile"
    bridge.handle(msg("Me llamo Ana", "m1"))
    done = bridge.handle(msg(answer, "m2"))
    assert done.status == "approval_resolved" and service.resumes[-1]["decision"] == "reject"


@pytest.mark.parametrize("answer", ["mmm", "no sé", "sí pero no", "gracias"])
def test_ambiguous_answer_asks_again_and_never_executes(
    bridge: ChannelBridge, service: FakeService, answer: str
) -> None:
    service.propose = "save_profile"
    bridge.handle(msg("Me llamo Ana", "m1"))
    again = bridge.handle(msg(answer, "m2"))
    assert again.status == "pending_approval" and "Solo para estar segura" in again.messages[0]
    assert service.resumes == []


def test_new_question_supersedes_the_pending_action(
    bridge: ChannelBridge, service: FakeService
) -> None:
    service.propose = "save_preference"
    service.propose_args = {"key": "estilo", "value": "respuestas cortas"}
    bridge.handle(msg("guarda que prefiero respuestas cortas", "m1"))
    service.propose = None
    reply = bridge.handle(msg("¿cuáles son los canales oficiales de Manuelita?", "m2"))
    assert service.resumes[-1]["decision"] == "reject"
    assert reply.status == "answered" and reply.messages[0] == TEXTS["es"]["superseded"]
    assert bridge.store.get_pending(reply.thread_id) is None  # type: ignore[arg-type]


def test_expired_confirmation_is_explained(
    bridge: ChannelBridge, service: FakeService, clock: Clock
) -> None:
    service.propose = "save_profile"
    bridge.handle(msg("Me llamo Ana", "m1"))
    service.propose = None
    clock.now += timedelta(minutes=11)
    reply = bridge.handle(msg("sí", "m2"))
    assert service.resumes[-1]["decision"] == "reject"
    assert reply.messages[0] == TEXTS["es"]["expired"]
    assert len(service.calls) == 1  # no se envió «sí» al agente


def test_expired_then_new_question_gets_notice_and_answer(
    bridge: ChannelBridge, service: FakeService, clock: Clock
) -> None:
    service.propose = "save_profile"
    bridge.handle(msg("Me llamo Ana", "m1"))
    service.propose = None
    clock.now += timedelta(minutes=11)
    reply = bridge.handle(msg("¿Qué produce Manuelita?", "m2"))
    assert reply.status == "answered" and "venció" in reply.messages[0]


def test_english_confirmation_texts(bridge: ChannelBridge, service: FakeService) -> None:
    service.propose = "save_profile"
    pending = bridge.handle(msg("My name is Ana and I work at a sugar mill", "m1"))
    assert "Shall I go ahead?" in pending.messages[0]


# --- intenciones naturales (T030) ---------------------------------------------------------------


def test_start_over_opens_a_new_thread(bridge: ChannelBridge, service: FakeService) -> None:
    first = bridge.handle(msg("hola", "m1"))
    new = bridge.handle(msg("empecemos de nuevo", "m2"))
    after = bridge.handle(msg("¿Qué produce Manuelita?", "m3"))
    assert new.messages[0] == TEXTS["es"]["restart"] and new.thread_id != first.thread_id
    assert after.thread_id == new.thread_id
    assert service.calls[-1]["user_id"] == service.calls[0]["user_id"]  # el perfil se conserva


def test_start_over_with_a_question_answers_it(bridge: ChannelBridge, service: FakeService) -> None:
    bridge.handle(msg("hola", "m1"))
    reply = bridge.handle(msg("Empecemos de nuevo. ¿Qué certificaciones tiene Manuelita?", "m2"))
    assert reply.messages[0] == TEXTS["es"]["restart_notice"]
    assert service.calls[-1]["message"] == "¿Qué certificaciones tiene Manuelita?"


def test_forget_in_natural_language_goes_to_the_agent(
    bridge: ChannelBridge, service: FakeService
) -> None:
    service.propose = "forget_memory"
    reply = bridge.handle(msg("olvida lo que sabes de mí", "m1"))
    assert reply.status == "pending_approval" and "borrar" in reply.messages[0]
    assert service.calls[-1]["message"] == "olvida lo que sabes de mí"


# --- voz (T018) ---------------------------------------------------------------------------------


def test_voice_question_gets_voice_and_text(
    bridge: ChannelBridge, service: FakeService, voice: FakeVoice
) -> None:
    reply = bridge.handle(audio("¿Qué produce Manuelita?", "m1", "es"))
    assert reply.voice is not None and reply.voice["language"] == "es"
    assert "Fuentes:" in reply.messages[-1]  # las fuentes van en el texto
    question, answer, language = voice.answers[0]
    assert question == "¿Qué produce Manuelita?" and "[U1]" in answer and language == "es"
    assert reply.to_dict()["voice"]["mime"].startswith("audio/ogg")


def test_english_voice_question_gets_english_voice(bridge: ChannelBridge, voice: FakeVoice) -> None:
    reply = bridge.handle(audio("What does Manuelita produce?", "m1", "en"))
    assert reply.voice is not None and voice.answers[0][2] == "en"


def test_text_question_gets_only_text(bridge: ChannelBridge, voice: FakeVoice) -> None:
    reply = bridge.handle(msg("¿Qué produce Manuelita?", "m1"))
    assert reply.voice is None and voice.answers == []


def test_written_preference_overrides_voice_input(bridge: ChannelBridge, voice: FakeVoice) -> None:
    confirm = bridge.handle(audio("respóndeme por escrito", "m1", "es"))
    assert confirm.messages[0] == TEXTS["es"]["format_text"] and confirm.voice is None
    reply = bridge.handle(audio("¿Qué produce Manuelita?", "m2", "es"))
    assert reply.voice is None


def test_voice_preference_applies_to_text_questions(
    bridge: ChannelBridge, voice: FakeVoice
) -> None:
    confirm = bridge.handle(msg("mándame audio", "m1"))
    assert confirm.messages[0] == TEXTS["es"]["format_voice"] and confirm.voice is not None
    reply = bridge.handle(msg("¿Qué produce Manuelita?", "m2"))
    assert reply.voice is not None


def test_pending_action_from_voice_is_spoken_briefly(
    bridge: ChannelBridge, service: FakeService, voice: FakeVoice
) -> None:
    service.propose = "save_profile"
    reply = bridge.handle(audio("Me llamo Ana", "m1", "es"))
    assert reply.status == "pending_approval" and reply.voice is not None
    assert voice.answers == [] and "¿Lo hago?" in voice.texts[0][0]


def test_voice_failure_keeps_the_written_answer(
    bridge: ChannelBridge, voice: FakeVoice, tmp_path: Path
) -> None:
    voice.fail = True
    reply = bridge.handle(audio("¿Qué produce Manuelita?", "m1", "es"))
    assert reply.status == "answered" and reply.voice is None
    assert reply.messages[-1] == TEXTS["es"]["voice_failed"] and reply.event == "voice_error"


def test_voice_notes_can_be_disabled(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice
) -> None:
    store = ChannelStore(tmp_path / "c.sqlite3", clock=clock)
    bridge = ChannelBridge(
        service, store, ChannelsConfig(voice_notes=False), salt=SALT, mode="demo", voice=voice
    )
    assert bridge.handle(audio("¿Qué produce Manuelita?", "m1", "es")).voice is None


# --- atajos ocultos del operador ------------------------------------------------------------------


def test_operator_shortcuts_still_work(bridge: ChannelBridge, service: FakeService) -> None:
    assert bridge.handle(msg("/ayuda", "m1")).messages[0] == TEXTS["es"]["intro"]
    assert bridge.handle(msg("/traza", "m2")).messages[0] == TEXTS["es"]["trace_empty"]
    bridge.handle(msg("¿Qué produce Manuelita?", "m3"))
    trace = bridge.handle(msg("/traza", "m4")).messages[0]
    assert "documental" in trace and "search_documents" in trace and "1. buscar" in trace
    first = bridge.handle(msg("/nuevo", "m5"))
    assert first.messages[0] == TEXTS["es"]["restart"]


# --- spec 029: idioma del turno (T010) ---------------------------------------------------------


def test_the_turn_language_reaches_the_agent_and_the_formatter(
    bridge: ChannelBridge, service: FakeService
) -> None:
    reply = bridge.handle(msg("When was Ingenio Manuelita founded?", "l1"))
    assert service.calls[-1]["language"] == "en"
    assert "Sources:" in reply.messages[-1] and "Fuentes:" not in "\n".join(reply.messages)
    spanish = bridge.handle(msg("¿Cuándo inició Ingenio Manuelita?", "l2"))
    assert service.calls[-1]["language"] == "es" and "Fuentes:" in spanish.messages[-1]


def test_short_messages_keep_the_previous_language(
    bridge: ChannelBridge, service: FakeService
) -> None:
    bridge.handle(msg("What products does Manuelita make?", "l3"))
    bridge.handle(msg("ok", "l4"))
    assert service.calls[-1]["language"] == "en"
    bridge.handle(audio("¿y el agua?", "l5", language="es"))
    assert service.calls[-1]["language"] == "es"  # la pista del dictado manda


# --- spec 029: transcripciones recientes (OpenClaw no marca la nota de voz) ---


def test_recent_transcriptions_match_once_and_expire() -> None:
    from proyecto_modelos_lenguaje.channels.bridge import RecentTranscriptions

    now = [0.0]
    recent = RecentTranscriptions(ttl_seconds=600, clock=lambda: now[0])
    recent.note("When was Ingenio Manuelita founded?", "en")
    assert recent.take("when was ingenio manuelita founded") == (True, "en")
    assert recent.take("When was Ingenio Manuelita founded?") == (False, None)  # consumida
    recent.note("¿Cuándo inició Ingenio Manuelita?", "es")
    now[0] = 700.0
    assert recent.take("¿Cuándo inició Ingenio Manuelita?") == (False, None)  # vencida
    recent.note("ok", "es")  # muy corta: no se guarda
    assert recent.take("ok") == (False, None)


def test_a_transcribed_text_is_handled_as_a_voice_note(
    bridge: ChannelBridge, service: FakeService, voice: FakeVoice
) -> None:
    bridge.transcriptions.note("What products does Manuelita make?", "en")
    reply = bridge.handle(msg("What products does Manuelita make?", "t-voz"))
    assert reply.voice is not None and reply.voice["language"] == "en"
    assert service.calls[-1]["language"] == "en"
    written = bridge.handle(msg("¿Qué produce Manuelita?", "t-texto"))
    assert written.voice is None


# --- spec 030: con voz, por escrito solo las fuentes (T006, T013, T014) ---


def _written(tmp_path: Path) -> list[str | None]:
    lines = (tmp_path / "logs" / "channels.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line).get("written") for line in lines]


def test_a_voice_answer_carries_only_the_sources_in_writing(
    bridge: ChannelBridge, voice: FakeVoice, tmp_path: Path
) -> None:
    reply = bridge.handle(audio("¿Qué produce Manuelita?", "s-voz", language="es"))
    assert reply.voice is not None
    assert reply.sources_messages == ["Fuentes:\n[1] Informe — https://manuelita.com"]
    assert "Respuesta a" in reply.messages[0]  # la respuesta completa queda como respaldo
    assert voice.with_sources[-1] is True
    english = bridge.handle(audio("What does Manuelita produce?", "s-en", language="en"))
    assert english.sources_messages[0].startswith("Sources:\n[1] ")
    written = bridge.handle(msg("¿Qué produce Manuelita?", "s-texto"))
    assert written.voice is None and written.sources_messages == []
    assert _written(tmp_path)[-3:] == ["sources", "sources", "full"]


def test_a_voice_answer_without_sources_has_no_text(
    bridge: ChannelBridge, service: FakeService, tmp_path: Path
) -> None:
    service.cite = False
    reply = bridge.handle(audio("Hola Valeria", "s-hola", language="es"))
    assert reply.voice is not None and reply.sources_messages == []
    assert reply.written == "none" and _written(tmp_path)[-1] == "none"


def test_voice_preference_with_a_written_question_also_sends_only_sources(
    bridge: ChannelBridge,
) -> None:
    bridge.handle(msg("mándame audio", "s-pref"))
    reply = bridge.handle(msg("¿Qué produce Manuelita?", "s-pref-2"))
    assert reply.voice is not None and reply.sources_messages[0].startswith("Fuentes:")


def test_if_the_voice_fails_the_full_answer_goes_in_writing(
    tmp_path: Path, service: FakeService, clock: Clock
) -> None:
    bridge = make_bridge(tmp_path, service, clock, FakeVoice(fail=True))
    reply = bridge.handle(audio("¿Qué produce Manuelita?", "s-falla", language="es"))
    assert reply.voice is None and reply.sources_messages == []
    text = "\n".join(reply.messages)
    assert "Respuesta a" in text and "Fuentes:" in text
    assert _written(tmp_path)[-1] == "full"


# --- spec 031: cualquier número (T007) ---


def test_two_new_numbers_get_their_own_conversations(
    bridge: ChannelBridge, service: FakeService
) -> None:
    first = bridge.handle(InboundMessage("whatsapp", "n1", "+570000000101", "text", "Hola"))
    second = bridge.handle(InboundMessage("whatsapp", "n2", "+570000000102", "text", "Hola"))
    assert first.status == second.status == "answered"
    assert first.thread_id != second.thread_id
    users = [call["user_id"] for call in service.calls[-2:]]
    assert users[0] != users[1] and all(user.startswith("wa-") for user in users)
    voice = bridge.handle(
        InboundMessage(
            "whatsapp", "n3", "+570000000101", "audio", "¿Qué produce Manuelita?",
            input_mode="voice", language_hint="es",
        )
    )  # fmt: skip
    assert voice.voice is not None and voice.sources_messages


# --- spec 031: protecciones del canal abierto (T014, T015) ---


def _events(tmp_path: Path) -> list[str | None]:
    lines = (tmp_path / "logs" / "channels.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line).get("event") for line in lines]


def _me() -> str:
    from proyecto_modelos_lenguaje.channels.identity import pseudonym

    return pseudonym(PHONE, SALT, "whatsapp")


def test_the_short_window_limit_sends_one_notice_then_silence(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice
) -> None:
    bridge = make_bridge(
        tmp_path, service, clock, voice, rate_max_messages=3, daily_max_messages=50
    )
    replies = [bridge.handle(msg(f"¿Qué produce Manuelita? {i}", f"r{i}")) for i in range(5)]
    assert [r.status for r in replies] == ["answered"] * 3 + ["busy", "ignored"]
    assert replies[3].messages == [TEXTS["es"]["rate_limited"]] and replies[4].messages == []
    assert len(service.calls) == 3  # el modelo solo atendió lo permitido
    assert _events(tmp_path)[-2:] == ["rate_limited", "rate_limited"]
    english = bridge.handle(msg("What does Manuelita produce for export markets?", "r-en"))
    assert english.status == "ignored"  # ya avisado en esta ventana
    clock.now += timedelta(minutes=10)
    assert bridge.handle(msg("¿Y en Perú?", "r-later")).status == "answered"


def test_the_notice_follows_the_message_language(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice
) -> None:
    bridge = make_bridge(
        tmp_path, service, clock, voice, rate_max_messages=1, daily_max_messages=50
    )
    bridge.handle(msg("What does Manuelita produce?", "e1"))
    notice = bridge.handle(msg("What does Manuelita export to other countries?", "e2"))
    assert notice.status == "busy" and notice.messages == [TEXTS["en"]["rate_limited"]]


def test_the_daily_cap_notifies_once(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice
) -> None:
    bridge = make_bridge(
        tmp_path, service, clock, voice, rate_max_messages=50, daily_max_messages=2
    )
    statuses = [
        bridge.handle(msg(f"Pregunta {i} sobre Manuelita", f"d{i}")).status for i in range(4)
    ]
    assert statuses == ["answered", "answered", "busy", "ignored"]
    assert _events(tmp_path)[-2:] == ["daily_capped", "daily_capped"]


def test_operators_have_no_limits(
    tmp_path: Path,
    service: FakeService,
    clock: Clock,
    voice: FakeVoice,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("VALERIA_OPERATORS", _me())
    bridge = make_bridge(tmp_path, service, clock, voice, rate_max_messages=1, daily_max_messages=1)
    statuses = {bridge.handle(msg(f"Pregunta {i}", f"o{i}")).status for i in range(4)}
    assert statuses == {"answered"}


def test_a_blocked_number_is_ignored_without_calling_the_agent(
    bridge: ChannelBridge, service: FakeService, tmp_path: Path
) -> None:
    bridge.store.block(_me())
    reply = bridge.handle(msg("Hola", "b1"))
    assert reply.status == "ignored" and reply.messages == [] and service.calls == []
    assert _events(tmp_path)[-1] == "blocked"


def test_operator_shortcuts_only_for_operators(
    bridge: ChannelBridge, service: FakeService, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("VALERIA_OPERATORS", "wa-ffffffffffffffff")  # otra persona
    reply = bridge.handle(msg("/traza", "t1"))
    assert service.calls and service.calls[-1]["message"] == "/traza"  # va como conversación
    assert reply.messages[0] != TEXTS["es"]["trace_empty"]
    monkeypatch.setenv("VALERIA_OPERATORS", _me())
    assert bridge.handle(msg("/traza", "t2")).messages[0] != ""
    calls = len(service.calls)
    bridge.handle(msg("/traza", "t3"))
    assert len(service.calls) == calls  # el operador recibe la traza sin pasar por el agente


# --- spec 032: saludo y presentación al iniciar una conversación (T009, T010, T013, T015, T018,
# T020) ---------------------------------------------------------------------------------------


def _log(tmp_path: Path) -> list[dict[str, Any]]:
    lines = (tmp_path / "logs" / "channels.jsonl").read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines]


def _text(reply: Any) -> str:
    return " ".join(reply.messages)


def test_a_direct_first_question_gets_the_introduction_and_the_answer(
    bridge: ChannelBridge, tmp_path: Path
) -> None:
    first = bridge.handle(msg("¿Qué produce Manuelita?", "g1"))
    assert first.messages[0].startswith("¡Hola") and "Valer-IA" in first.messages[0]
    assert "Respuesta a «¿Qué produce Manuelita?»" in _text(first)  # sin pedir que la repita
    assert first.introduced == "bridge"
    second = bridge.handle(msg("¿y en Perú?", "g2"))
    assert "Valer-IA" not in _text(second) and second.introduced is None
    rows = _log(tmp_path)
    assert [row["conversation_start"] for row in rows] == ["first_contact", None]
    assert [row["introduced"] for row in rows] == ["bridge", None]


def test_a_greeting_already_introduced_by_the_model_is_not_repeated(
    bridge: ChannelBridge, service: FakeService
) -> None:
    service.answer = "¡Hola! Soy Valer-IA, la asistente de Manuelita. ¿En qué te ayudo?"
    reply = bridge.handle(msg("Hola", "g1"))
    assert _text(reply).count("Valer-IA") == 1 and reply.introduced == "agent"


def test_a_loose_hola_from_the_model_is_not_doubled(
    bridge: ChannelBridge, service: FakeService
) -> None:
    service.answer = "¡Hola! ¿En qué te puedo ayudar hoy?"
    reply = bridge.handle(msg("Hola", "g1"))
    assert _text(reply).count("¡Hola") == 1
    assert "¿En qué te puedo ayudar hoy?" in _text(reply) and reply.introduced == "bridge"


def test_the_introduction_follows_the_language_and_the_name(
    bridge: ChannelBridge, service: FakeService
) -> None:
    english = bridge.handle(msg("What does Manuelita produce for export markets?", "g1"))
    assert english.messages[0].startswith(("Hi", "Hello")) and "Valer-IA" in english.messages[0]

    service.client = {"name": "Ana"}  # otro número nuevo, con nombre reconocido
    named = bridge.handle(
        InboundMessage("whatsapp", "g2", "+570000000202", "text", "¿Qué produce Manuelita?")
    )
    assert named.messages[0].startswith("¡Hola, Ana")


def test_notices_shortcuts_and_blocked_numbers_get_no_introduction(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice, monkeypatch: Any
) -> None:
    bridge = make_bridge(tmp_path, service, clock, voice, rate_max_messages=1)
    bridge.store.block(_me())
    assert bridge.handle(msg("¿Qué produce Manuelita?", "b1")).messages == []
    bridge.store.unblock(_me())
    monkeypatch.setenv("VALERIA_OPERATORS", "")
    shortcut = bridge.handle(msg("/traza", "b2"))
    assert "Valer-IA" not in _text(shortcut) and shortcut.introduced is None
    clock.now += timedelta(minutes=11)
    first = bridge.handle(msg("¿Qué produce Manuelita?", "b3"))
    assert first.introduced == "bridge"  # el atajo no marcó el hilo
    notice = bridge.handle(msg("¿Y en Perú?", "b4"))
    assert notice.messages == [TEXTS["es"]["rate_limited"]] and notice.introduced is None


def test_an_image_as_first_message_introduces_and_explains(bridge: ChannelBridge) -> None:
    reply = bridge.handle(msg(None, "g1", "image"))
    assert reply.status == "unsupported" and _text(reply).startswith("¡Hola")
    assert "notas de voz" in _text(reply) and reply.introduced == "bridge"


def test_an_error_on_the_first_turn_keeps_the_introduction_for_later(
    bridge: ChannelBridge, service: FakeService
) -> None:
    service.fail = True
    error = bridge.handle(msg("¿Qué produce Manuelita?", "g1"))
    assert error.messages[0].startswith("Soy Valer-IA") and error.introduced is None
    service.fail = False
    later = bridge.handle(msg("¿Qué produce Manuelita?", "g2"))
    assert later.introduced == "bridge" and later.messages[0].startswith("¡Hola")


def test_the_sensitive_notice_stays_at_the_end(bridge: ChannelBridge, service: FakeService) -> None:
    notice = "Ojo: por aquí no hace falta que compartas datos como tarjetas o contraseñas."
    service.answer = f"Te cuento lo que sé de Manuelita.\n\n{notice}"
    reply = bridge.handle(msg("Mi tarjeta es 4111 1111 1111 1111, ¿qué produce Manuelita?", "g1"))
    text = _text(reply)
    assert text.startswith("¡Hola") and text.rstrip().endswith(notice)


def test_a_long_first_answer_gets_the_introduction_as_its_own_message(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice
) -> None:
    bridge = make_bridge(tmp_path, service, clock, voice, reply_max_chars=200)
    service.answer = (
        "Manuelita produce azúcar. " * 7
    )  # ~180 caracteres: no cabe con la presentación
    reply = bridge.handle(msg("¿Qué produce Manuelita?", "g1"))
    assert reply.messages[0].startswith("¡Hola") and reply.messages[1].startswith("Manuelita")
    assert all(len(part) <= 200 for part in reply.messages)


# --- US2: voz ---------------------------------------------------------------------------------


def test_the_first_voice_answer_opens_with_the_introduction(
    bridge: ChannelBridge, voice: FakeVoice
) -> None:
    first = bridge.handle(audio("¿Qué produce Manuelita?", "v1", "es"))
    assert first.voice is not None and voice.openings[0] is not None
    assert voice.openings[0].startswith("¡Hola") and "Valer-IA" in voice.openings[0]
    assert "Valer-IA" not in voice.answers[0][1]  # el guion se arma sin la presentación
    assert first.sources_messages and first.sources_messages[0].startswith("Fuentes:")
    second = bridge.handle(audio("¿Y en Perú?", "v2", "es"))
    assert second.voice is not None and voice.openings[1] is None


def test_a_first_spoken_greeting_is_introduced_once(
    bridge: ChannelBridge, service: FakeService, voice: FakeVoice
) -> None:
    service.answer = "¡Hola! ¿En qué te puedo ayudar?"
    reply = bridge.handle(audio("Hola", "v1", "es"))
    assert reply.voice is not None
    spoken = voice.openings[0] if voice.openings else voice.texts[0][0]
    assert spoken is not None and spoken.count("¡Hola") == 1


def test_an_english_first_voice_note_is_introduced_in_english(
    bridge: ChannelBridge, voice: FakeVoice
) -> None:
    reply = bridge.handle(audio("What does Manuelita produce?", "v1", "en"))
    assert reply.voice is not None and voice.openings[0] is not None
    assert voice.openings[0].startswith(("Hi", "Hello"))


# --- US3: regreso después de la inactividad ----------------------------------------------------


def test_coming_back_after_the_idle_period_starts_a_new_conversation(
    bridge: ChannelBridge, service: FakeService, clock: Clock, tmp_path: Path
) -> None:
    first = bridge.handle(msg("¿Qué produce Manuelita?", "i1"))
    clock.now += timedelta(hours=11)
    same = bridge.handle(msg("¿y en Perú?", "i2"))
    assert same.thread_id == first.thread_id and same.introduced is None
    clock.now += timedelta(hours=13)
    service.client = {"name": "Ana"}
    back = bridge.handle(msg("¿Qué certificaciones tiene?", "i3"))
    assert back.thread_id != first.thread_id and back.messages[0].startswith("¡Hola, Ana")
    assert service.calls[-1]["thread_id"] is None  # hilo nuevo: sin el contexto anterior
    assert service.calls[-1]["user_id"] == service.calls[0]["user_id"]  # el perfil se conserva
    assert [row["conversation_start"] for row in _log(tmp_path)] == [
        "first_contact",
        None,
        "inactivity",
    ]


# --- US4: empezar de nuevo ---------------------------------------------------------------------


def test_starting_over_with_a_question_confirms_introduces_and_answers(
    bridge: ChannelBridge, tmp_path: Path
) -> None:
    bridge.handle(msg("¿Qué produce Manuelita?", "s1"))
    reply = bridge.handle(msg("Empecemos de nuevo. ¿Qué certificaciones tiene Manuelita?", "s2"))
    text = _text(reply)
    assert reply.messages[0] == TEXTS["es"]["restart_notice"]
    assert text.count("Valer-IA") == 1 and text.index("Valer-IA") < text.index("Respuesta a")
    assert reply.conversation_start == "restart" and reply.introduced == "bridge"


def test_starting_over_alone_leaves_the_introduction_for_the_next_request(
    bridge: ChannelBridge,
) -> None:
    bridge.handle(msg("¿Qué produce Manuelita?", "s1"))
    only = bridge.handle(msg("empecemos de nuevo", "s2"))
    assert only.messages == [TEXTS["es"]["restart"]] and only.introduced is None
    assert only.conversation_start == "restart"
    nxt = bridge.handle(msg("¿Qué certificaciones tiene Manuelita?", "s3"))
    assert nxt.introduced == "bridge" and nxt.messages[0].startswith("¡Hola")


# --- spec 033: cuentas identificadas solo por ID (T007, T016) ---------------------------------

LID = "10000000000001@lid"  # ficticio


def test_an_id_only_account_is_answered_in_one_thread(
    bridge: ChannelBridge, service: FakeService, tmp_path: Path
) -> None:
    first = bridge.handle(InboundMessage("whatsapp", "l1", LID, "text", "¿Qué produce Manuelita?"))
    assert first.status == "answered" and first.messages[0].startswith("¡Hola")
    assert service.calls[0]["user_id"].startswith("wa-")
    second = bridge.handle(InboundMessage("whatsapp", "l2", LID, "text", "¿y en Perú?"))
    assert second.thread_id == first.thread_id and second.introduced is None
    rows = _log(tmp_path)
    assert [row["sender_kind"] for row in rows] == ["lid", "lid"]
    raw = (tmp_path / "logs" / "channels.jsonl").read_text(encoding="utf-8")
    assert "10000000000001" not in raw  # nunca el ID
    assert bridge.handle(msg("hola", "p1")).status == "answered"
    assert _log(tmp_path)[-1]["sender_kind"] == "phone"


def test_late_messages_are_dropped_and_recent_ones_answered_once(
    bridge: ChannelBridge, service: FakeService, clock: Clock, tmp_path: Path
) -> None:
    old = (clock.now - timedelta(minutes=20)).isoformat()
    late = bridge.handle(msg("¿Qué produce Manuelita?", "s1", received_at=old))
    assert late.status == "ignored" and late.event == "stale" and service.calls == []
    assert _log(tmp_path)[-1]["event"] == "stale"
    recent = (clock.now - timedelta(minutes=5)).isoformat()
    assert (
        bridge.handle(msg("¿Qué produce Manuelita?", "s2", received_at=recent)).status == "answered"
    )
    assert (
        bridge.handle(msg("¿Qué produce Manuelita?", "s2", received_at=recent)).status == "ignored"
    )
    assert len(service.calls) == 1  # el duplicado no se responde dos veces
    inconsistent = "1970-01-21T09:00:00+00:00"  # p. ej. segundos leídos como milisegundos
    for value in (None, "no-es-fecha", "2026-11-28T12:58:00", inconsistent):
        reply = bridge.handle(msg("¿y en Perú?", f"s-{value}", received_at=value))
        assert reply.status == "answered", value


# --- spec 034: stickers (T009, T015, T018) ------------------------------------------------------


def _with_catalog(bridge: ChannelBridge, tmp_path: Path) -> ChannelBridge:
    from tests.unit.channels.test_stickers import make_catalog

    bridge._stickers = make_catalog(tmp_path / "catalogo")
    return bridge


def _say(bridge: ChannelBridge, service: FakeService, text: str, mid: str, **route: Any):
    service.route_extra = route
    return bridge.handle(msg(text, mid))


def test_social_moments_get_their_sticker(
    bridge: ChannelBridge, service: FakeService, tmp_path: Path
) -> None:
    _with_catalog(bridge, tmp_path)
    service.answer = "¡Hola! Soy Valer-IA, la asistente de Manuelita. ¿En qué te ayudo?"
    hola = _say(bridge, service, "Hola", "k1", act="greeting")
    assert hola.sticker and hola.sticker.name == "valeria-bienvenido"
    assert hola.sticker.position == "before" and Path(hola.to_dict()["sticker"]["path"]).is_file()
    service.answer = None
    factual = _say(bridge, service, "¿Qué produce Manuelita?", "k2", act="manuelita")
    # Spec 037: una respuesta útil con fuentes lleva «¡Listo!» (antes no llevaba sticker).
    assert factual.sticker and factual.sticker.name == "valeria-listo"
    service.answer = "¡Con gusto!"
    gracias = _say(bridge, service, "Muchas gracias", "k3", act="thanks")
    assert gracias.sticker and gracias.sticker.name == "valeria-gracias"
    service.answer = "¡Hasta pronto!"
    chao = _say(bridge, service, "Chao", "k4", act="closing")
    assert chao.sticker and chao.sticker.name == "valeria-lindo-dia"  # despedida: aunque siga
    assert [row["sticker"] for row in _log(tmp_path)] == [
        "valeria-bienvenido",
        "valeria-listo",
        "valeria-gracias",
        "valeria-lindo-dia",
    ]


def test_moderation_over_a_ten_turn_conversation(
    bridge: ChannelBridge, service: FakeService, tmp_path: Path
) -> None:
    _with_catalog(bridge, tmp_path)
    service.answer = "Te cuento."
    turns = [
        ("Hola", "greeting", None),
        ("Gracias", "thanks", None),  # spec 037: seguida, pero con otra situación
        ("¿Qué produce Manuelita?", "manuelita", None),
        ("Gracias", "thanks", None),
        ("Esto no me sirve, estoy molesto", "complaint", "angry"),
        ("ok", "minimal", None),
        ("Gracias", "thanks", None),
        ("Hola", "greeting", None),
        ("ok", "minimal", None),
        ("Chao", "closing", None),
    ]
    for index, (text, act, sentiment) in enumerate(turns):
        route = {"act": act, **({"sentiment": sentiment} if sentiment else {})}
        _say(bridge, service, text, f"m{index}", **route)
    stickers = [row["sticker"] for row in _log(tmp_path)]
    sent = [name for name in stickers if name]
    assert 4 <= len(sent) <= 8  # spec 037: uso activo, con el tope de la configuración
    assert stickers[1] == "valeria-gracias" and stickers[4] is None  # la queja nunca lleva sticker
    for before, after in itertools.pairwise(stickers):
        if before and after and before == after:
            assert after in {"valeria-pulgar", "valeria-lindo-dia"}  # nunca el mismo seguido


def test_approved_actions_get_their_sticker(
    bridge: ChannelBridge, service: FakeService, tmp_path: Path
) -> None:
    _with_catalog(bridge, tmp_path)
    service.propose = "save_preference"
    bridge.handle(msg("Recuerda que me llamo Ana", "a1"))
    service.propose = None
    saved = bridge.handle(msg("dale", "a2"))
    assert saved.status == "approval_resolved"
    assert saved.sticker and saved.sticker.name == "valeria-gracias-confianza"
    useful = bridge.handle(msg("¿Qué produce Manuelita?", "a3")).sticker
    assert useful and useful.name == "valeria-listo"  # spec 037: respuesta útil
    service.propose = "forget_memory"
    bridge.handle(msg("Olvida lo que sabes de mí", "a4"))
    service.propose = None
    forgotten = bridge.handle(msg("sí, dale", "a5"))
    assert forgotten.sticker is None  # spec 037: «¡Listo!» no va dos respuestas seguidas
    service.propose = "forget_memory"
    bridge.handle(msg("Olvida lo que sabes de mí", "a6"))
    service.propose = None
    again = bridge.handle(msg("sí, dale", "a7"))
    assert again.sticker and again.sticker.name == "valeria-listo"  # la acción conserva el suyo


def test_rejected_actions_and_disabled_switch_get_no_sticker(
    tmp_path: Path, service: FakeService, clock: Clock, voice: FakeVoice
) -> None:
    bridge = _with_catalog(make_bridge(tmp_path, service, clock, voice, stickers=False), tmp_path)
    service.answer = "¡Con gusto!"
    assert _say(bridge, service, "Gracias", "d1", act="thanks").sticker is None
