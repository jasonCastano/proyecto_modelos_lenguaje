"""Notas de voz de respuesta para WhatsApp (spec 028, research R2–R4, data-model «VoiceReply»).

1. **Guion**: el modelo convierte la respuesta escrita y citada en lo que una persona diría en una
   nota de voz (``prompts/voice_script.md``). Se limpia y se valida: sin citas, URLs ni fuentes, y
   toda cifra del guion debe estar en la respuesta. Si algo falla, se usa un respaldo determinista
   (las primeras oraciones limpias de la respuesta).
2. **Voz**: Phonon en el idioma de la pregunta (spec 016; ``es`` Rebeca, ``en`` phonon-31m-en),
   oración por oración, recortada a ``voice_max_seconds``.
3. **Audio**: Ogg/Opus mono (el formato de las notas de voz de WhatsApp) en un archivo temporal
   fuera del repositorio que se borra a los ``voice_retention_minutes``.
"""

from __future__ import annotations

import io
import re
import time
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from ..voice.text import clean_for_speech, split_sentences

OPUS_RATES = (8_000, 12_000, 16_000, 24_000, 48_000)
MIME = "audio/ogg; codecs=opus"
SENTENCE_GAP_SECONDS = 0.18
MIN_SCRIPT_WORDS = 6
MAX_SCRIPT_WORDS = 140
FALLBACK_CHARS = 600
ANY_CITATION = re.compile(r"\[\s*(?:[UFS]?\d+)(?:\s*[,;]\s*[UFS]?\d+)*\s*\]", re.IGNORECASE)
# «Fuentes:» (o «Sources:») y todo lo que sigue: en un bloque aparte o pegado al final del guion.
SOURCES_BLOCK = re.compile(r"\*?\b(?:fuentes(?: sintéticas[^:\n]*)?|sources)\*?\s*:.*", re.I | re.S)
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")

ModelFactory = Callable[[], Any]
ServiceFor = Callable[[str], Any]


@dataclass(frozen=True, slots=True)
class VoiceReply:
    language: str
    script: str
    audio_path: str
    duration_ms: int
    voice: str
    script_source: str  # "model" | "fallback" | "text"
    script_ms: int
    voice_ms: int

    def to_dict(self) -> dict[str, Any]:
        """Contrato channel-api-v2 §1 (el guion no sale del backend)."""
        return {
            "audio_path": self.audio_path,
            "language": self.language,
            "duration_ms": self.duration_ms,
            "mime": MIME,
        }


def _unspoken(text: str, language: str) -> str:
    """Quita lo que nunca se dice: bloque de fuentes y citas de cualquier tipo."""
    value = SOURCES_BLOCK.sub("", text or "")
    value = ANY_CITATION.sub(" ", value)
    if language == "en":
        value = value.replace("%", " percent ")
    return clean_for_speech(value)


def _numbers(text: str) -> set[str]:
    return {re.sub(r"[.,]", "", match) for match in NUMBER.findall(text)}


def fallback_script(answer: str, language: str) -> str:
    """Respaldo determinista: las primeras oraciones limpias de la respuesta (≤ 600 caracteres)."""
    clean = _unspoken(answer, language)
    chosen: list[str] = []
    size = 0
    for sentence in split_sentences(clean, max_chars=FALLBACK_CHARS):
        if chosen and size + len(sentence) > FALLBACK_CHARS:
            break
        chosen.append(sentence)
        size += len(sentence) + 1
    return " ".join(chosen)


def valid_script(script: str, answer: str) -> bool:
    """Largo razonable y sin cifras que no estén en la respuesta escrita (nada inventado)."""
    words = script.split()
    if not MIN_SCRIPT_WORDS <= len(words) <= MAX_SCRIPT_WORDS:
        return False
    return _numbers(script) <= _numbers(answer)


def build_script(question: str, answer: str, language: str, model: Any | None) -> tuple[str, str]:
    """Guion hablado y su origen (``model`` o ``fallback``)."""
    if model is not None and answer.strip():
        from ..agent.prompts import load_agent_prompt

        prompt = load_agent_prompt("voice_script").render(
            language=language, question=question.strip(), answer=answer.strip()
        )
        try:
            raw = model.invoke(prompt)
            content = getattr(raw, "content", raw)
            script = _unspoken(str(content), language)
            if valid_script(script, answer):
                return script, "model"
        except Exception:  # el guion nunca tumba la respuesta: se usa el respaldo
            pass
    return fallback_script(answer, language), "fallback"


# Spec 030: con fuentes, por escrito va solo el bloque de fuentes y la voz lo dice al final.
SOURCES_CLOSING = {
    "es": "Te dejo las fuentes por escrito.",
    "en": "I've left the sources for you in writing.",
}


def with_sources_closing(script: str, language: str) -> str:
    """Añade la frase de cierre del idioma del turno (sin duplicarla si el guion ya la trae)."""
    closing = SOURCES_CLOSING.get(language, SOURCES_CLOSING["es"])
    body = script.strip()
    if closing.lower().rstrip(".") in body.lower():
        return body
    if body and body[-1] not in ".!?…":
        body += "."
    return f"{body} {closing}".strip()


def encode_ogg_opus(samples: np.ndarray, sample_rate: int) -> bytes:
    """Ogg/Opus mono con PyAV (verificado en el portátil servidor, prueba S4)."""
    import av

    pcm = np.clip(np.asarray(samples, dtype=np.float32).reshape(-1), -1.0, 1.0)
    rate = sample_rate if sample_rate in OPUS_RATES else 48_000
    buffer = io.BytesIO()
    container = av.open(buffer, mode="w", format="ogg")
    stream = container.add_stream("libopus", rate=rate)
    stream.layout = "mono"
    frame = av.AudioFrame.from_ndarray(pcm.reshape(1, -1), format="flt", layout="mono")
    frame.sample_rate = sample_rate
    if rate != sample_rate:
        resampler = av.AudioResampler(format="flt", layout="mono", rate=rate)
        frames = [*resampler.resample(frame), *resampler.resample(None)]
    else:
        frames = [frame]
    for item in frames:
        for packet in stream.encode(item):
            container.mux(packet)
    for packet in stream.encode(None):
        container.mux(packet)
    container.close()
    return buffer.getvalue()


def purge_old(directory: Path, minutes: int, *, now: float | None = None) -> int:
    """Borra las notas de voz generadas hace más de ``minutes`` (FR-008)."""
    if not directory.is_dir():
        return 0
    limit = (now if now is not None else time.time()) - minutes * 60
    removed = 0
    for path in directory.glob("*.ogg"):
        try:
            if path.stat().st_mtime < limit:
                path.unlink()
                removed += 1
        except OSError:
            continue
    return removed


class ChannelVoice:
    """Implementa ``bridge.VoicePort``: guion + voz + archivo temporal."""

    def __init__(
        self,
        voice_dir: Path,
        *,
        model_factory: ModelFactory | None = None,
        service_for: ServiceFor | None = None,
        max_seconds: int = 60,
        retention_minutes: int = 10,
    ) -> None:
        if service_for is None:
            from ..voice.engine import get_voice_service

            service_for = get_voice_service
        self.voice_dir = Path(voice_dir)
        self.model_factory = model_factory
        self.service_for = service_for
        self.max_seconds = max_seconds
        self.retention_minutes = retention_minutes
        purge_old(self.voice_dir, 0)  # al arrancar no quedan audios de una sesión anterior

    def for_answer(
        self, question: str, answer: str, language: str, *, with_sources: bool = False
    ) -> VoiceReply:
        started = time.perf_counter()
        model = self.model_factory() if self.model_factory is not None else None
        script, source = build_script(question, answer, language, model)
        if with_sources:
            script = with_sources_closing(script, language)
        script_ms = round((time.perf_counter() - started) * 1000)
        return self._render(script, language, source, script_ms)

    def for_text(self, text: str, language: str) -> VoiceReply:
        return self._render(_unspoken(text, language), language, "text", 0)

    def _render(self, script: str, language: str, source: str, script_ms: int) -> VoiceReply:
        if not script:
            raise ValueError("No hay nada que decir en voz alta.")
        purge_old(self.voice_dir, self.retention_minutes)
        service = self.service_for(language)
        started = time.perf_counter()
        chunks: list[np.ndarray] = []
        rate = 0
        voice = ""
        for sentence in split_sentences(script, max_chars=service.config.max_chars):
            result = service.synthesize(sentence)
            rate, voice = result.sample_rate, result.voice
            chunks.append(np.asarray(result.samples, dtype=np.float32).reshape(-1))
            chunks.append(np.zeros(int(rate * SENTENCE_GAP_SECONDS), dtype=np.float32))
            if sum(chunk.size for chunk in chunks) >= rate * self.max_seconds:
                break
        samples = np.concatenate(chunks)[: rate * self.max_seconds]
        voice_ms = round((time.perf_counter() - started) * 1000)
        self.voice_dir.mkdir(parents=True, exist_ok=True)
        path = self.voice_dir / f"{uuid.uuid4().hex}.ogg"
        path.write_bytes(encode_ogg_opus(samples, rate))
        return VoiceReply(
            language=language,
            script=script,
            audio_path=str(path.resolve()),
            duration_ms=round(samples.size * 1000 / rate),
            voice=voice,
            script_source=source,
            script_ms=script_ms,
            voice_ms=voice_ms,
        )
