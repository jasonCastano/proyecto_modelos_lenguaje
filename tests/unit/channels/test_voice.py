"""Guion hablado y nota de voz del canal (spec 028, T017, FR-003, SC-002)."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.channels.transcription import decode_audio
from proyecto_modelos_lenguaje.channels.voice import (
    ChannelVoice,
    build_script,
    fallback_script,
    purge_old,
    valid_script,
)
from proyecto_modelos_lenguaje.voice.engine import get_voice_service, reset_voice_service

ANSWER = (
    "Manuelita produce **azúcar**, bioetanol y energía en el Valle del Cauca [U1]. En 2022 sus "
    "ventas crecieron 41,0 % frente a 2021 [F2]. Más detalle en https://www.manuelita.com.\n\n"
    "Fuentes:\n[1] Informe de Sostenibilidad — https://www.manuelita.com/informe"
)
FORBIDDEN = ("[", "]", "http", "Fuentes", "Sources", "*", "•")


@dataclass
class ScriptModel:
    """Modelo guionado: devuelve un texto fijo (o falla)."""

    content: str
    fail: bool = False

    def invoke(self, _prompt: str) -> object:
        if self.fail:
            raise RuntimeError("sin red")
        return type("Message", (), {"content": self.content})()


@pytest.fixture(autouse=True)
def fake_voice(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("MANUELITA_VOICE_ENGINE", "fake")
    reset_voice_service()
    yield
    reset_voice_service()


def _assert_speakable(script: str) -> None:
    for token in FORBIDDEN:
        assert token not in script, (token, script)


def test_fallback_is_clean_and_short() -> None:
    script = fallback_script(ANSWER, "es")
    _assert_speakable(script)
    assert script.startswith("Manuelita produce azúcar") and len(script) <= 600
    assert "41,0 por ciento" in script


def test_model_script_is_used_when_valid() -> None:
    model = ScriptModel(
        "Manuelita produce azúcar, bioetanol y energía en el Valle del Cauca, y en 2022 sus "
        "ventas crecieron un 41,0 por ciento frente a 2021. Si quieres, te cuento más."
    )
    script, source = build_script("¿Qué produce Manuelita?", ANSWER, "es", model)
    assert source == "model" and 20 <= len(script.split()) <= 110
    _assert_speakable(script)


def test_model_citations_and_urls_are_removed() -> None:
    model = ScriptModel(
        "Manuelita produce azúcar y bioetanol en el Valle del Cauca [1] [U1], como cuenta "
        "https://www.manuelita.com en su informe. Fuentes: [1] Informe."
    )
    script, source = build_script("¿Qué produce Manuelita?", ANSWER, "es", model)
    assert source == "model"
    _assert_speakable(script)


def test_invented_numbers_fall_back() -> None:
    model = ScriptModel("Manuelita vendió 999 millones de toneladas de azúcar en 2022, una cifra.")
    script, source = build_script("¿Cuánto vendió?", ANSWER, "es", model)
    assert source == "fallback" and "999" not in script


def test_model_failure_and_demo_mode_fall_back() -> None:
    assert build_script("q", ANSWER, "es", ScriptModel("", fail=True))[1] == "fallback"
    assert build_script("q", ANSWER, "es", None)[1] == "fallback"


def test_valid_script_rules() -> None:
    assert not valid_script("Hola.", ANSWER)  # demasiado corto
    assert not valid_script(" ".join(["palabra"] * 200), ANSWER)  # demasiado largo
    assert valid_script(
        "En 2022 las ventas crecieron cuarenta y uno por ciento frente a 2021.", ANSWER
    )


def test_english_percent_is_spoken_in_english() -> None:
    script = fallback_script("Sales grew 41 % in 2022 [F1].", "en")
    assert "41 percent" in script and "por ciento" not in script


def test_renders_a_temporary_ogg_voice_note(tmp_path: Path) -> None:
    voice = ChannelVoice(tmp_path / "voice", model_factory=None)
    reply = voice.for_answer("¿Qué produce Manuelita?", ANSWER, "es")
    path = Path(reply.audio_path)
    assert path.suffix == ".ogg" and path.read_bytes()[:4] == b"OggS"
    assert tmp_path in path.parents  # nunca dentro del repositorio
    samples, audio_ms = decode_audio(path.read_bytes())
    assert samples.size > 0 and abs(audio_ms - reply.duration_ms) < 200
    assert reply.voice == "Rebeca" and reply.script_source == "fallback"
    assert reply.to_dict() == {
        "audio_path": str(path),
        "language": "es",
        "duration_ms": reply.duration_ms,
        "mime": "audio/ogg; codecs=opus",
    }


def test_english_note_uses_the_english_voice(tmp_path: Path) -> None:
    voice = ChannelVoice(tmp_path / "voice", service_for=get_voice_service)
    reply = voice.for_text("Hi! I can tell you about Manuelita.", "en")
    assert reply.language == "en" and reply.voice == "Harper"


def test_duration_is_capped(tmp_path: Path) -> None:
    voice = ChannelVoice(tmp_path / "voice", max_seconds=10)
    long_text = " ".join(
        f"Esta es la oración número {i} de una respuesta larga." for i in range(40)
    )
    reply = voice.for_text(long_text, "es")
    assert reply.duration_ms <= 10_000


def test_old_voice_notes_are_purged(tmp_path: Path) -> None:
    directory = tmp_path / "voice"
    directory.mkdir()
    old, new = directory / "old.ogg", directory / "new.ogg"
    old.write_bytes(b"OggS")
    new.write_bytes(b"OggS")
    past = time.time() - 11 * 60
    os.utime(old, (past, past))
    assert purge_old(directory, 10) == 1
    assert not old.exists() and new.exists()


def test_nothing_to_say_is_an_error(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        ChannelVoice(tmp_path / "voice").for_text("[U1] https://x.co", "es")


# --- spec 030: con fuentes, la voz anuncia que van por escrito (T018) -----------------------------


def _script_of(voice: ChannelVoice, monkeypatch: pytest.MonkeyPatch, **kwargs: object) -> str:
    captured: list[str] = []
    monkeypatch.setattr(
        voice, "_render", lambda script, *_args: captured.append(script) or script, raising=True
    )
    voice.for_answer(**kwargs)  # type: ignore[arg-type]
    return captured[0]


def test_the_voice_closes_with_the_sources_phrase(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from proyecto_modelos_lenguaje.channels.voice import SOURCES_CLOSING

    voice = ChannelVoice(tmp_path / "voice", model_factory=None)
    question = "¿Qué produce Manuelita?"
    es = _script_of(
        voice, monkeypatch, question=question, answer=ANSWER, language="es", with_sources=True
    )
    assert es.endswith("Te dejo las fuentes por escrito.") and es.count("fuentes por escrito") == 1
    assert valid_script(es, ANSWER)  # la frase no trae cifras nuevas
    plain = _script_of(voice, monkeypatch, question=question, answer=ANSWER, language="es")
    assert SOURCES_CLOSING["es"] not in plain
    english = "Manuelita produces sugar and bioethanol in the Cauca Valley [U1]."
    en = _script_of(
        voice, monkeypatch, question="What?", answer=english, language="en", with_sources=True
    )
    assert en.endswith("I've left the sources for you in writing.")


def test_the_closing_phrase_is_not_duplicated() -> None:
    from proyecto_modelos_lenguaje.channels.voice import with_sources_closing

    once = with_sources_closing("Manuelita produce azúcar. Te dejo las fuentes por escrito.", "es")
    assert once.count("Te dejo las fuentes por escrito") == 1
    assert with_sources_closing("Manuelita produce azúcar", "es") == (
        "Manuelita produce azúcar. Te dejo las fuentes por escrito."
    )


# --- spec 038: la presentación abre la nota de voz (T014) --------------------------------------

OPENING = "¡Hola! Soy Valer-IA, la asistente virtual de Manuelita."


def test_the_opening_goes_first_with_the_fallback_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    voice = ChannelVoice(tmp_path / "voice", model_factory=None)
    script = _script_of(
        voice,
        monkeypatch,
        question="¿Qué produce Manuelita?",
        answer=ANSWER,
        language="es",
        with_sources=True,
        opening=OPENING,
    )
    assert script.startswith(OPENING) and script.count("Valer-IA") == 1
    assert script.endswith("Te dejo las fuentes por escrito.")  # cierre de la spec 030
    _assert_speakable(script)


def test_the_opening_goes_first_with_the_model_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    model = ScriptModel("Manuelita produce azúcar, bioetanol y energía en el Valle del Cauca.")
    voice = ChannelVoice(tmp_path / "voice", model_factory=lambda: model)
    script = _script_of(
        voice,
        monkeypatch,
        question="¿Qué produce Manuelita?",
        answer=ANSWER,
        language="es",
        opening=OPENING,
    )
    assert script == f"{OPENING} {model.content}"  # el modelo nunca ve ni reescribe la apertura


def test_without_opening_the_script_is_unchanged(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    voice = ChannelVoice(tmp_path / "voice", model_factory=None)
    kwargs = {"question": "¿Qué produce Manuelita?", "answer": ANSWER, "language": "es"}
    assert _script_of(voice, monkeypatch, **kwargs) == fallback_script(ANSWER, "es")


# ---------------------------------------------------------------- spec 036: estilo caleño hablado

BODY = (
    "Manuelita produce azúcar, bioetanol y energía en el Valle del Cauca, y en 2022 sus ventas "
    "crecieron un 41,0 por ciento frente a 2021."
)


@dataclass
class RecordingModel:
    """Modelo que devuelve guiones en orden y guarda los prompts recibidos."""

    replies: list[str]
    prompts: list[str]

    def invoke(self, prompt: str) -> object:
        self.prompts.append(prompt)
        content = self.replies[min(len(self.prompts) - 1, len(self.replies) - 1)]
        return type("Message", (), {"content": content})()


def test_spec036_the_prompt_gets_the_spoken_style_block() -> None:
    from proyecto_modelos_lenguaje.channels.voice import spoken_style_block

    model = RecordingModel([f"¡Ve, qué bueno! {BODY} Listo pues, te cuento más."], [])
    script, source = build_script("¿Qué produce Manuelita?", ANSWER, "es", model, style="neutral")
    assert source == "model" and "Listo pues" in script
    assert "<estilo>\nnivel: neutral" in model.prompts[0]
    assert "expresiones sugeridas (como máximo dos" in model.prompts[0]
    assert spoken_style_block("hi", "en", "neutral") == ""
    assert spoken_style_block("¿Qué produce?", "es", "off") == ""
    assert spoken_style_block("habla normal", "es", "neutral") == ""


def test_spec036_too_many_expressions_retry_then_drop_sentences() -> None:
    from proyecto_modelos_lenguaje.agent.style import find_expressions

    crowded = f"¡Ve, qué nota! {BODY} Listo pues, de una. A la orden, te cuento más de Manuelita."
    model = RecordingModel([crowded, crowded], [])
    script, source = build_script("¿Qué produce Manuelita?", ANSWER, "es", model, style="neutral")
    assert len(model.prompts) == 2  # una regeneración
    assert source == "model" and len(find_expressions(script)) <= 2


def test_spec036_banned_words_are_never_spoken() -> None:
    from proyecto_modelos_lenguaje.agent.style import find_banned

    model = RecordingModel([f"Mirá, parce: {BODY} Si quieres, te cuento más de Manuelita."], [])
    script, _source = build_script("¿Qué produce Manuelita?", ANSWER, "es", model, style="neutral")
    assert not find_banned(script)


def test_spec036_without_style_no_caleno_expressions_are_spoken() -> None:
    from proyecto_modelos_lenguaje.agent.style import find_expressions

    model = RecordingModel([f"¡Uy, qué nota! {BODY} Si quieres, te cuento más de Manuelita."], [])
    script, _source = build_script("¿Qué produce Manuelita?", ANSWER, "es", model, style="off")
    assert "<estilo>\nnivel" not in model.prompts[0]
    assert not find_expressions(script)
