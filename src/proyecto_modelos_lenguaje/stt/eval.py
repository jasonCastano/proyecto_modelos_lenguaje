"""Evaluación del dictado (spec 023, FR-023, research R11).

La batería se **genera** en cada corrida: las frases de ``tests/fixtures/stt/phrases.jsonl`` se
sintetizan con Phonon (voz de Valer-IA y otra del catálogo) y se agregan clips de silencio y ruido
con semilla. No se guarda ni se versiona audio. Opcionalmente se suman grabaciones humanas locales
(``--audio-dir``, pares ``nombre.wav`` + ``nombre.txt``) cuyo texto solo se publica con
``--include-human-text``.

Métricas: WER normalizado (minúsculas, tildes, puntuación y números en palabras), acierto del
vocabulario propio, latencia p50/p90 por tramo de duración y vacío en silencio o ruido.
"""

from __future__ import annotations

import argparse
import json
import math
import re
import statistics
import sys
import unicodedata
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

import numpy as np

from ..config import PROJECT_ROOT
from .audio import SAMPLE_RATE, encode_wav16k, parse_wav16k, resample
from .config import SttConfig, load_stt_config
from .engine import SttService

PHRASES_PATH = PROJECT_ROOT / "tests" / "fixtures" / "stt" / "phrases.jsonl"
DEFAULT_VOICES = ("Rebeca", "Regina")
SPEECH_KINDS = {"speech", "human"}
SILENT_KINDS = {"silence", "noise"}
SAMPLE_PHRASE = "¿Qué produce Manuelita?"

TARGET_WER = 0.15
TARGET_VOCAB = 0.90
TARGET_LATENCY_MS = 2000

# ------------------------------------------------------------------------- números en palabras

_UNITS = [
    "cero",
    "uno",
    "dos",
    "tres",
    "cuatro",
    "cinco",
    "seis",
    "siete",
    "ocho",
    "nueve",
    "diez",
    "once",
    "doce",
    "trece",
    "catorce",
    "quince",
    "dieciseis",
    "diecisiete",
    "dieciocho",
    "diecinueve",
    "veinte",
    "veintiuno",
    "veintidos",
    "veintitres",
    "veinticuatro",
    "veinticinco",
    "veintiseis",
    "veintisiete",
    "veintiocho",
    "veintinueve",
]
_TENS = [
    "_",
    "_",
    "_",
    "treinta",
    "cuarenta",
    "cincuenta",
    "sesenta",
    "setenta",
    "ochenta",
    "noventa",
]
_HUNDREDS = [
    "_",
    "ciento",
    "doscientos",
    "trescientos",
    "cuatrocientos",
    "quinientos",
    "seiscientos",
    "setecientos",
    "ochocientos",
    "novecientos",
]


def _below_thousand(number: int) -> list[str]:
    if number < 30:
        return [_UNITS[number]]
    if number < 100:
        tens, unit = divmod(number, 10)
        return [_TENS[tens]] + (["y", _UNITS[unit]] if unit else [])
    if number == 100:
        return ["cien"]
    hundreds, rest = divmod(number, 100)
    return [_HUNDREDS[hundreds]] + (_below_thousand(rest) if rest else [])


def number_words(number: int) -> list[str]:
    """Número entero en palabras (español), hasta 999 999 999."""
    if number < 1000:
        return _below_thousand(number)
    if number < 1_000_000:
        thousands, rest = divmod(number, 1000)
        head = ["mil"] if thousands == 1 else [*_below_thousand(thousands), "mil"]
        return head + (_below_thousand(rest) if rest else [])
    millions, rest = divmod(number, 1_000_000)
    head = ["un", "millon"] if millions == 1 else [*number_words(millions), "millones"]
    return head + (number_words(rest) if rest else [])


def _fold(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text.lower())
    return "".join(char for char in decomposed if not unicodedata.combining(char))


def normalize_for_wer(text: str) -> list[str]:
    """Tokens comparables: sin tildes ni puntuación, con números y porcentajes en palabras."""
    folded = _fold(text).replace("%", " por ciento ")
    folded = re.sub(r"(?<=\d)[.,](?=\d{3}\b)", "", folded)  # 46.933 → 46933
    tokens: list[str] = []
    for token in re.findall(r"[a-z0-9]+", folded):
        if token.isdigit() and len(token) <= 9:
            tokens.extend(number_words(int(token)))
        else:
            tokens.append(token)
    return tokens


def wer(reference: str, hypothesis: str) -> float:
    """Tasa de error de palabras (distancia de edición sobre tokens normalizados)."""
    ref = normalize_for_wer(reference)
    hyp = normalize_for_wer(hypothesis)
    if not ref:
        return 0.0 if not hyp else 1.0
    row = list(range(len(hyp) + 1))
    for i, word in enumerate(ref, start=1):
        previous, row[0] = row[0], i
        for j, other in enumerate(hyp, start=1):
            current = row[j]
            row[j] = min(row[j] + 1, row[j - 1] + 1, previous + (word != other))
            previous = current
    return row[len(hyp)] / len(ref)


def _words(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", _fold(text))


def vocab_hits(hypothesis: str, terms: Sequence[str]) -> tuple[int, int]:
    """Cuántos términos del vocabulario aparecen escritos tal cual (sin distinguir tildes)."""
    heard = f" {' '.join(_words(hypothesis))} "
    hits = sum(1 for term in terms if f" {' '.join(_words(term))} " in heard)
    return hits, len(terms)


def percentile(values: Sequence[float], p: float) -> float:
    """Percentil por rango más cercano (0 si no hay valores)."""
    if not values:
        return 0
    ordered = sorted(values)
    rank = max(1, math.ceil(p / 100 * len(ordered)))
    return ordered[rank - 1]


# ------------------------------------------------------------------------------- batería


@dataclass
class EvalItem:
    id: str
    kind: str
    voice: str
    audio_ms: int
    stt_ms: int
    reference: str | None
    hypothesis: str | None
    wer: float
    vocab_hits: int
    vocab_total: int

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class Synthesizer(Protocol):
    def synthesize(self, text: str, voice: str) -> tuple[np.ndarray, int]: ...


class PhononSynthesizer:
    """Sintetiza con la voz del proyecto (spec 016); requiere el modelo Phonon."""

    def __init__(self) -> None:
        from ..voice.engine import get_voice_service

        self._service = get_voice_service()

    def synthesize(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        result = self._service.synthesize(text, voice)
        return result.samples, result.sample_rate


def load_phrases(path: Path = PHRASES_PATH) -> list[dict[str, Any]]:
    return [
        json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()
    ]


def _silent_clip(item: dict[str, Any]) -> np.ndarray:
    rng = np.random.default_rng(int(item.get("seed", 0)))
    count = int(float(item.get("seconds", 2)) * SAMPLE_RATE)
    scale = 0.05 if item["kind"] == "noise" else 0.001
    return np.clip(rng.normal(0, scale, count), -1, 1).astype(np.float32)


def _human_clips(audio_dir: Path) -> Iterable[tuple[str, np.ndarray, int, str]]:
    for wav in sorted(Path(audio_dir).glob("*.wav")):
        reference = wav.with_suffix(".txt")
        if not reference.exists():
            continue
        data = wav.read_bytes()
        try:
            samples, audio_ms = parse_wav16k(data, max_bytes=len(data) + 1, max_seconds=120)
        except ValueError:
            from faster_whisper.audio import decode_audio  # otros formatos (lectura local)

            samples = decode_audio(str(wav), sampling_rate=SAMPLE_RATE)
            audio_ms = round(samples.size * 1000 / SAMPLE_RATE)
        yield wav.stem, samples, audio_ms, reference.read_text(encoding="utf-8").strip()


def _score(
    service: SttService,
    *,
    item_id: str,
    kind: str,
    voice: str,
    samples: np.ndarray,
    audio_ms: int,
    reference: str,
    vocab: Sequence[str],
    publish: bool = True,
) -> EvalItem:
    result = service.transcribe(samples, audio_ms)
    hits, total = vocab_hits(result.text, vocab) if kind in SPEECH_KINDS else (0, 0)
    return EvalItem(
        id=item_id,
        kind=kind,
        voice=voice,
        audio_ms=int(audio_ms),
        stt_ms=int(result.stt_ms),
        reference=reference if publish else None,
        hypothesis=result.text if publish else None,
        wer=round(wer(reference, result.text), 4) if kind in SPEECH_KINDS else 0.0,
        vocab_hits=hits,
        vocab_total=total,
    )


def summarize(items: Sequence[EvalItem]) -> dict[str, Any]:
    speech = [item for item in items if item.kind in SPEECH_KINDS]
    silent = [item for item in items if item.kind in SILENT_KINDS]
    hits = sum(item.vocab_hits for item in speech)
    total = sum(item.vocab_total for item in speech)

    def bucket(selected: list[EvalItem]) -> dict[str, float]:
        latencies = [item.stt_ms for item in selected]
        return {
            "n": len(latencies),
            "p50": percentile(latencies, 50),
            "p90": percentile(latencies, 90),
        }

    return {
        "items": len(items),
        "speech_items": len(speech),
        "wer": round(statistics.mean(item.wer for item in speech), 4) if speech else 0.0,
        "vocab_accuracy": round(hits / total, 4) if total else 1.0,
        "vocab_hits": hits,
        "vocab_total": total,
        "latency_ms": {
            "<=5s": bucket([i for i in speech if i.audio_ms <= 5000]),
            "5-10s": bucket([i for i in speech if 5000 < i.audio_ms <= 10_000]),
            ">10s": bucket([i for i in speech if i.audio_ms > 10_000]),
            "<=10s": bucket([i for i in speech if i.audio_ms <= 10_000]),
        },
        "empty_rate_on_silence": (
            round(sum(1 for i in silent if not i.hypothesis) / len(silent), 4) if silent else 1.0
        ),
    }


def targets(summary: dict[str, Any]) -> dict[str, bool]:
    """Metas SC-001 a SC-004 de la spec 023."""
    return {
        "SC-001": summary["wer"] <= TARGET_WER,
        "SC-002": summary["vocab_accuracy"] >= TARGET_VOCAB,
        "SC-003": summary["latency_ms"]["<=10s"]["p90"] < TARGET_LATENCY_MS,
        "SC-004": summary["empty_rate_on_silence"] == 1.0,
    }


def _config_dict(config: SttConfig) -> dict[str, Any]:
    data = asdict(config)
    data["vocabulary"] = list(config.vocabulary)
    data["corrections"] = {key: value for key, value in config.corrections}
    return data


def run_eval(
    phrases: Sequence[dict[str, Any]],
    *,
    models: Sequence[str],
    voices: Sequence[str],
    synthesizer: Synthesizer,
    service_for: Callable[[str], SttService],
    before_item: Callable[[dict[str, Any]], None] | None = None,
    audio_dir: Path | None = None,
    include_human_text: bool = False,
    progress: Callable[[str], None] | None = None,
) -> dict[str, Any]:
    """Corre la batería para cada modelo y devuelve el informe (data-model §8)."""
    clips: list[tuple[dict[str, Any], str, np.ndarray, int]] = []
    for item in phrases:
        if item["kind"] == "speech":
            for voice in voices:
                samples, rate = synthesizer.synthesize(item["text"], voice)
                audio = resample(samples, rate)
                clips.append((item, voice, audio, round(audio.size * 1000 / SAMPLE_RATE)))
        elif item["kind"] in SILENT_KINDS:
            audio = _silent_clip(item)
            clips.append((item, "-", audio, round(audio.size * 1000 / SAMPLE_RATE)))
    humans = list(_human_clips(audio_dir)) if audio_dir else []
    report: dict[str, Any] = {
        "generated_at": datetime.now(UTC).isoformat(timespec="seconds"),
        "voices": list(voices),
        "phrases": sum(1 for item in phrases if item["kind"] == "speech"),
        "human_recordings": len(humans),
        "models": {},
    }
    for model in models:
        service = service_for(model)
        report.setdefault("config", _config_dict(service.config))
        items: list[EvalItem] = []
        for item, voice, audio, audio_ms in clips:
            if before_item is not None:
                before_item(item)
            suffix = f"-{voice}" if voice != "-" else ""
            items.append(
                _score(
                    service,
                    item_id=f"{item['id']}{suffix}",
                    kind=item["kind"],
                    voice=voice,
                    samples=audio,
                    audio_ms=audio_ms,
                    reference=item.get("text", ""),
                    vocab=item.get("vocab", []),
                )
            )
        for name, audio, audio_ms, reference in humans:
            items.append(
                _score(
                    service,
                    item_id=name,
                    kind="human",
                    voice="humano",
                    samples=audio,
                    audio_ms=audio_ms,
                    reference=reference,
                    vocab=[],
                    publish=include_human_text,
                )
            )
        summary = summarize(items)
        report["models"][model] = {
            "model_label": service.config.model_label,
            "summary": summary,
            "targets": targets(summary),
            "items": [item.to_dict() for item in items],
        }
        if progress is not None:
            progress(
                f"{model}: WER {summary['wer']:.3f} · vocabulario {summary['vocab_accuracy']:.2f}"
            )
    return report


# ------------------------------------------------------------------------------- informe


def _mark(ok: bool) -> str:
    return "✅" if ok else "❌"


def render_markdown(report: dict[str, Any]) -> str:
    config = report.get("config", {})
    lines = [
        "# Evaluación del dictado (spec 023)",
        "",
        f"Generado: {report['generated_at']} · frases: {report['phrases']} · voces de Phonon: "
        f"{', '.join(report['voices']) or '—'} · "
        f"grabaciones humanas: {report['human_recordings']}.",
        "",
        f"Motor `{config.get('engine')}`, `compute_type` {config.get('compute_type')}, "
        f"`beam_size` {config.get('beam_size')}, idioma `{config.get('language')}`, "
        f"`no_speech_threshold` {config.get('no_speech_threshold')}. El vocabulario propio "
        f"({len(config.get('vocabulary', []))} términos) va como prompt inicial.",
        "",
        "Metas: SC-001 WER ≤ 0.15 · SC-002 vocabulario ≥ 90 % · SC-003 p90 < 2 s para clips de "
        "hasta 10 s · SC-004 vacío en el 100 % de los silencios y ruidos.",
        "",
        "| Modelo | WER | Vocabulario | p50 / p90 ≤ 5 s (ms) | p50 / p90 5–10 s (ms) | "
        "p90 ≤ 10 s (ms) | Vacío en silencio | SC-001 | SC-002 | SC-003 | SC-004 |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for row in report["models"].values():
        summary = row["summary"]
        latency = summary["latency_ms"]
        verdict = row["targets"]
        lines.append(
            f"| `{row['model_label']}` | {summary['wer']:.3f} | "
            f"{summary['vocab_hits']}/{summary['vocab_total']} "
            f"({summary['vocab_accuracy'] * 100:.0f} %) | "
            f"{latency['<=5s']['p50']:.0f} / {latency['<=5s']['p90']:.0f} | "
            f"{latency['5-10s']['p50']:.0f} / {latency['5-10s']['p90']:.0f} | "
            f"{latency['<=10s']['p90']:.0f} | {summary['empty_rate_on_silence'] * 100:.0f} % | "
            + " | ".join(_mark(verdict[key]) for key in ("SC-001", "SC-002", "SC-003", "SC-004"))
            + " |"
        )
    for row in report["models"].values():
        worst = sorted(
            (item for item in row["items"] if item["kind"] == "speech"),
            key=lambda item: item["wer"],
            reverse=True,
        )[:8]
        if not worst:
            continue
        lines += [
            "",
            f"## Frases con más error · `{row['model_label']}`",
            "",
            "| Frase | Voz | Audio (ms) | Reconocimiento (ms) | WER | Referencia | Transcripción |",
            "|---|---|---|---|---|---|---|",
        ]
        for item in worst:
            lines.append(
                f"| {item['id']} | {item['voice']} | {item['audio_ms']} | {item['stt_ms']} | "
                f"{item['wer']:.2f} | {item['reference']} | {item['hypothesis'] or '(vacío)'} |"
            )
    lines += [
        "",
        "El audio se genera en memoria en cada corrida y no se guarda. Las grabaciones humanas, si "
        "las hay, son locales y su texto solo se publica con `--include-human-text`.",
        "",
    ]
    return "\n".join(line.rstrip() for line in lines)


# ------------------------------------------------------------------------------- CLI


def _service_factory(config: SttConfig) -> Callable[[str], SttService]:
    def build(model: str) -> SttService:
        service = SttService(replace(config, model=model, warmup=False))
        service.ensure_loaded()
        service.transcribe(np.zeros(SAMPLE_RATE, dtype=np.float32), 1000)  # primera llamada lenta
        return service

    return build


def main_eval(args: argparse.Namespace) -> int:
    config = load_stt_config()
    if args.export_sample:
        target = Path(args.export_sample).expanduser().resolve()
        data_dir = (PROJECT_ROOT / "data").resolve()
        if target == data_dir or data_dir in target.parents:
            print("No se escribe audio dentro de data/.", file=sys.stderr)
            return 1
        samples, rate = PhononSynthesizer().synthesize(SAMPLE_PHRASE, DEFAULT_VOICES[0])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encode_wav16k(resample(samples, rate)))
        print(target)
        return 0
    models = list(args.models or [config.model])
    voices = list(args.voices or DEFAULT_VOICES)
    phrases = load_phrases()
    if args.limit:
        speech = [p for p in phrases if p["kind"] == "speech"][: args.limit]
        phrases = [*speech, *(p for p in phrases if p["kind"] != "speech")]
    report = run_eval(
        phrases,
        models=models,
        voices=voices,
        synthesizer=PhononSynthesizer(),
        service_for=_service_factory(config),
        audio_dir=args.audio_dir,
        include_human_text=args.include_human_text,
        progress=print,
    )
    json_out = Path(args.json_out)
    json_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    json_out.with_suffix(".md").write_text(render_markdown(report), encoding="utf-8")
    print(f"informe: {json_out} y su Markdown")
    configured = config.model if config.model in report["models"] else models[0]
    verdict = report["models"][configured]["targets"]
    print(f"{configured}: " + " · ".join(f"{k} {_mark(v)}" for k, v in verdict.items()))
    return 0 if all(verdict.values()) else 1
