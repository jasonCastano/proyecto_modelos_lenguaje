"""Puente del canal con un ChatService falso (spec 024 y spec 028: T018, T028, T030, T033)."""

from __future__ import annotations

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


@dataclass
class FakeService:
    calls: list[dict[str, Any]] = field(default_factory=list)
    resumes: list[dict[str, Any]] = field(default_factory=list)
    propose: str | None = None
    propose_args: dict[str, Any] = field(default_factory=lambda: {"name": "Ana"})
    fail: bool = False
    gate: threading.Event | None = None
    cite: bool = True

    def send(self, message: str, **kwargs: Any) -> Outcome:
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
        if not self.cite:  # spec 030: respuesta conversacional, sin fuentes
            return Outcome(thread, {"route": {"route": "direct"}, "answer": f"Hola: {message}."})
        turn = {
            "route": {"route": "documental"},
            "answer": f"Respuesta a «{message}» [U1].",
            "citations": [{"label": "U1", "url": "https://manuelita.com", "title": "Informe"}],
            "tools": [{"name": "search_documents", "ok": True, "duration_ms": 12}],
            "plan_steps": ["buscar en documentos", "responder con cita"],
        }
        return Outcome(thread, turn)

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
    fail: bool = False

    def for_answer(
        self, question: str, answer: str, language: str, *, with_sources: bool = False
    ) -> VoiceResult:
        if self.fail:
            raise RuntimeError("motor de voz caído")
        self.answers.append((question, answer, language))
        self.with_sources.append(with_sources)
        return VoiceResult(language, "guion")

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
    assert reply.status == "error" and reply.messages[0] == TEXTS["es"]["error"]
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
    assert reply.messages[0] == TEXTS["es"]["unheard"] and service.calls == []
    assert reply.voice is not None and voice.texts == [(TEXTS["es"]["unheard"], "es")]


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
