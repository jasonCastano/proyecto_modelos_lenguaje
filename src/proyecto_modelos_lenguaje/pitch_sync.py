"""Sincronía del pitch v2: tiempos de palabras, línea de tiempo y reajuste de planos (spec 029).

- ``align``: transcribe la narración sintetizada de cada bloque con faster-whisper (el modelo
  local del dictado, spec 023) con tiempos por palabra, ubica cada momento sincronizado y guarda
  ``video/pitch/sincronia.json`` (research R3). Sin red.
- ``build_timeline``: duración de cada escena (narración + pausa, R4), tramos de cada plano y los
  instantes de los gráficos del montaje (R6).
- ``retime``: reparte un tramo de plano entre sus anclas con factores de velocidad acotados
  (0,8×–1,25×) para que cada evento del plano caiga sobre su palabra (R5).
"""

from __future__ import annotations

import hashlib
import itertools
import json
import re
import unicodedata
import wave
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

SYNC_NAME = "sincronia.json"
MOVE_S = 0.8  # trayecto de un gráfico de `from` a `to`
FADE_S = 0.25


class SyncError(RuntimeError):
    """Error de sincronía con un mensaje accionable."""


@dataclass(frozen=True, slots=True)
class Word:
    w: str
    start: float
    end: float


Transcriber = Callable[[Path], Sequence[Word]]


# --------------------------------------------------------------------------- palabras


def normalize(text: str) -> str:
    """Minúsculas, sin tildes y sin puntuación (para comparar palabras)."""
    decomposed = unicodedata.normalize("NFKD", text.lower())
    plain = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.sub(r"[^a-z0-9ñ\s-]", " ", plain).replace("-", " ").strip()


def tokens(text: str) -> list[str]:
    return normalize(text).split()


def _same(word: str, token: str) -> bool:
    """Coincidencia por prefijo para variantes (visitante/visitantes); exacta si es corta."""
    if len(token) <= 3 or len(word) <= 3:
        return word == token
    return word.startswith(token) or token.startswith(word)


def find_phrase(words: Sequence[Word], phrase: str, after: float = 0.0) -> float | None:
    """Inicio de la primera aparición de ``phrase`` que empieza en ``after`` o después."""
    wanted = tokens(phrase)
    if not wanted:
        return None
    # Cada palabra del reconocedor puede traer varias fichas («equipo-de»); se aplanan.
    flat: list[tuple[str, float]] = []
    for item in words:
        for token in tokens(item.w):
            flat.append((token, item.start))
    for i in range(len(flat) - len(wanted) + 1):
        if flat[i][1] + 1e-6 < after:
            continue
        if all(_same(flat[i + j][0], wanted[j]) for j in range(len(wanted))):
            return flat[i][1]
    return None


def phrase_in_text(text: str, phrase: str) -> bool:
    words = [Word(token, float(i), float(i)) for i, token in enumerate(tokens(text))]
    return find_phrase(words, phrase) is not None


# --------------------------------------------------------------------------- audio


def wav_seconds(path: Path) -> float:
    with wave.open(str(path), "rb") as handle:
        return handle.getnframes() / float(handle.getframerate())


def read_wav_16k(path: Path) -> Any:
    """WAV PCM de 16 bits a ``float32`` mono de 16 kHz (lo que espera faster-whisper)."""
    import numpy as np

    from .stt.audio import resample

    with wave.open(str(path), "rb") as handle:
        rate, channels = handle.getframerate(), handle.getnchannels()
        if handle.getsampwidth() != 2:
            raise SyncError(f"{path.name}: se espera PCM de 16 bits.")
        data = np.frombuffer(handle.readframes(handle.getnframes()), dtype="<i2")
    samples = data.reshape(-1, channels).mean(axis=1).astype(np.float32) / 32768.0
    return resample(samples, rate) if rate != 16_000 else samples


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:16]


def whisper_transcriber() -> Transcriber:  # pragma: no cover - modelo real (marcador voice)
    """faster-whisper con tiempos por palabra, con el modelo configurado para el dictado."""
    from faster_whisper import WhisperModel

    from .stt.config import load_stt_config

    config = load_stt_config()
    model = WhisperModel(config.model, device="cpu", compute_type=config.compute_type)

    def transcribe(path: Path) -> list[Word]:
        # Como el dictado, se pasa el audio en memoria (16 kHz mono): la decodificación de archivos
        # de faster-whisper depende de una versión de PyAV que no es la del proyecto.
        segments, _info = model.transcribe(
            read_wav_16k(path), language="es", word_timestamps=True, beam_size=5, vad_filter=False
        )
        return [
            Word(w.word.strip(), float(w.start), float(w.end))
            for segment in segments
            for w in segment.words or ()
        ]

    return transcribe


# --------------------------------------------------------------------------- alineación


def align(
    root: Path,
    script: Any,
    narration_paths: Sequence[Path],
    *,
    pause_s: float,
    transcriber: Transcriber | None = None,
) -> dict[str, Any]:
    """Ubica cada momento en su narración y escribe ``sincronia.json`` (data-model.md)."""
    missing_files = [str(p) for p in narration_paths if not p.is_file()]
    if missing_files:
        raise SyncError("Falta la narración (pml pitch narrate): " + ", ".join(missing_files))
    transcribe = transcriber or whisper_transcriber()
    blocks: dict[str, Any] = {}
    missing: list[str] = []
    start = 0.0
    for block, path in zip(script.blocks, narration_paths, strict=True):
        narration_s = round(wav_seconds(path), 3)
        words = list(transcribe(path))
        cues: dict[str, float] = {}
        after = 0.0
        for cue in block.cues:
            at = find_phrase(words, cue.word, after)
            if at is None and cue.at_s is not None:
                at = float(cue.at_s)
            if at is None:
                missing.append(cue.id)
                continue
            after = at
            cues[cue.id] = round(min(at + cue.offset_s, narration_s), 3)
        scene_s = round(narration_s + pause_s, 3)
        blocks[block.id] = {
            "narration_s": narration_s,
            "scene_s": scene_s,
            "start_s": round(start, 3),
            "narration_hash": file_hash(path),
            "words": [
                {"w": w.w, "start": round(w.start, 3), "end": round(w.end, 3)} for w in words
            ],
            "cues": cues,
        }
        start += scene_s
    data = {
        "script_version": script.version,
        "pause_s": pause_s,
        "seconds": round(start, 3),
        "blocks": blocks,
    }
    if missing:
        raise SyncError(
            "Estas palabras de los momentos no aparecen en la narración y no tienen at_s: "
            + ", ".join(missing)
            + "."
        )
    (root / SYNC_NAME).write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "blocks": len(blocks),
        "seconds": data["seconds"],
        "cues": sum(len(b["cues"]) for b in blocks.values()),
        "missing": missing,
    }


def load_sync(root: Path) -> dict[str, Any]:
    path = root / SYNC_NAME
    if not path.is_file():
        raise SyncError("Falta video/pitch/sincronia.json: corre pml pitch align.")
    return json.loads(path.read_text(encoding="utf-8"))


def stale_reasons(
    sync: Mapping[str, Any], script: Any, narration_paths: Sequence[Path]
) -> list[str]:
    """Por qué ``sincronia.json`` ya no corresponde al guion o a la narración."""
    reasons = []
    if sync.get("script_version") != script.version:
        reasons.append(
            f"el guion es {script.version} y la sincronía es de {sync.get('script_version')}"
        )
    for block, path in zip(script.blocks, narration_paths, strict=True):
        entry = sync.get("blocks", {}).get(block.id)
        if entry is None:
            reasons.append(f"falta el bloque {block.id}")
        elif not path.is_file() or entry.get("narration_hash") != file_hash(path):
            reasons.append(f"la narración del bloque {block.id} cambió")
        else:
            known = set(entry.get("cues", {}))
            absent = [c.id for c in block.cues if c.id not in known]
            if absent:
                reasons.append("faltan los momentos " + ", ".join(absent))
    return reasons


# --------------------------------------------------------------------------- reajuste


@dataclass(slots=True)
class Piece:
    clip_start: float
    clip_end: float
    length: float  # segundos en la línea de tiempo

    @property
    def factor(self) -> float:
        """Segundos de clip por segundo de video: >1 acelera, <1 ralentiza."""
        return (self.clip_end - self.clip_start) / self.length if self.length else 1.0


def retime(
    length: float,
    anchors: Sequence[tuple[float, float]],
    clip_duration: float,
    *,
    limits: tuple[float, float],
    label: str = "",
) -> list[Piece]:
    """Tramos de clip que llenan ``length`` segundos con cada ancla sobre su instante.

    ``anchors`` son pares (segundo en el tramo, segundo en el clip). Antes de la primera y después
    de la última ancla el clip corre a 1× (o lo necesario para no pasarse del clip).
    """
    low, high = limits
    points = sorted((max(0.0, float(t)), float(c)) for t, c in anchors)
    for (t0, c0), (t1, c1) in itertools.pairwise(points):
        if t1 <= t0 or c1 <= c0:
            raise SyncError(f"{label}: las anclas deben avanzar en el clip y en la narración.")
    if not points:
        start, end = 0.0, length
    else:
        first_t, first_c = points[0]
        last_t, last_c = points[-1]
        start = max(0.0, first_c - first_t)
        end = last_c + (length - last_t)
    if end > clip_duration:
        end = clip_duration
    full = [(0.0, start), *points, (length, end)]
    pieces: list[Piece] = []
    for (t0, c0), (t1, c1) in itertools.pairwise(full):
        if t1 - t0 < 1e-3:
            continue
        piece = Piece(c0, c1, t1 - t0)
        if not low - 1e-6 <= piece.factor <= high + 1e-6:
            raise SyncError(
                f"{label}: el tramo {t0:.2f}–{t1:.2f} s necesita {piece.factor:.2f}× "
                f"(límite {low}–{high}×). Regenera el plano o mueve su ancla."
            )
        pieces.append(piece)
    return pieces


# --------------------------------------------------------------------------- línea de tiempo


@dataclass(slots=True)
class Segment:
    shot: str
    clip: Path
    start: float  # en el video
    length: float
    pieces: list[Piece]


def clip_to_video(segment: Segment, clip_t: float) -> float:
    """Segundo del video en que se ve el instante ``clip_t`` del clip de un tramo."""
    elapsed = segment.start
    for piece in segment.pieces:
        if clip_t <= piece.clip_end or piece is segment.pieces[-1]:
            offset = max(0.0, clip_t - piece.clip_start)
            return elapsed + offset / piece.factor
        elapsed += piece.length
    return elapsed


@dataclass(slots=True)
class GraphicEvent:
    cue: str
    graphic: str
    t_in: float
    t_out: float
    from_xy: tuple[float, float]
    to_xy: tuple[float, float]


@dataclass(slots=True)
class SceneSpan:
    id: str
    block: str
    start: float
    length: float
    narration_s: float
    segments: list[Segment] = field(default_factory=list)


@dataclass(slots=True)
class Timeline:
    scenes: list[SceneSpan]
    graphics: list[GraphicEvent]
    cues: list[dict[str, Any]]

    @property
    def seconds(self) -> float:
        return round(sum(s.length for s in self.scenes), 3)


def build_timeline(
    script: Any,
    scenes: Sequence[Mapping[str, Any]],
    sync: Mapping[str, Any],
    *,
    clip_path: Callable[[Mapping[str, Any]], Path],
    clip_duration: Callable[[Path], float],
    limits: tuple[float, float],
) -> Timeline:
    """Escenas, tramos de plano reajustados, gráficos y reporte de momentos."""
    spans: list[SceneSpan] = []
    graphics: list[GraphicEvent] = []
    report: list[dict[str, Any]] = []
    start = 0.0
    for block, scene in zip(script.blocks, scenes, strict=True):
        entry = sync["blocks"][block.id]
        length = float(entry["scene_s"])
        cue_at = {cid: float(t) for cid, t in entry["cues"].items()}
        span = SceneSpan(scene["id"], block.id, start, length, float(entry["narration_s"]))
        shots = list(scene["shots"])
        opens = [0.0] + [cue_at[s["starts_at"]] for s in shots[1:]]
        for index, shot in enumerate(shots):
            seg_start = opens[index]
            seg_end = opens[index + 1] if index + 1 < len(shots) else length
            if seg_end - seg_start <= 0:
                raise SyncError(f"{shot['id']}: su tramo no tiene duración; revisa starts_at.")
            review = shot.get("review") or {}
            anchors = review.get("anchors") or {}
            points = [
                (cue_at[c.id] - seg_start, float(anchors[c.id]))
                for c in block.cues
                if c.kind == "plano" and c.shot == shot["id"] and c.id in anchors
            ]
            if review.get("start_s") is not None:
                # Inicio del clip en el tramo (p. ej., saltar los paneles de la imagen de origen).
                points.append((0.0, float(review["start_s"])))
            clip = clip_path(shot)
            pieces = retime(
                seg_end - seg_start,
                points,
                clip_duration(clip),
                limits=limits,
                label=shot["id"],
            )
            span.segments.append(
                Segment(shot["id"], clip, start + seg_start, seg_end - seg_start, pieces)
            )
        for cue in block.cues:
            word_s = start + cue_at[cue.id]
            shown_s = word_s
            accepted = False
            if cue.kind == "plano":
                shot = next(s for s in shots if s["id"] == cue.shot)
                review = shot.get("review") or {}
                events = review.get("events") or {}
                if cue.id not in (review.get("anchors") or {}) and cue.id in events:
                    segment = next(g for g in span.segments if g.shot == cue.shot)
                    shown_s = clip_to_video(segment, float(events[cue.id]))
                    accepted = cue.id in (review.get("accepted") or [])
            if cue.kind == "grafico":
                t_out = start + length if cue.hold_s is None else word_s + cue.hold_s
                graphics.append(
                    GraphicEvent(
                        cue.id,
                        str(cue.graphic),
                        round(word_s, 3),
                        round(min(t_out, start + length), 3),
                        cue.from_xy,
                        cue.to_xy or cue.from_xy,
                    )
                )
            report.append(
                {
                    "id": cue.id,
                    "kind": cue.kind,
                    "word_s": round(word_s, 3),
                    "shown_s": round(shown_s, 3),
                    "delta_s": round(shown_s - word_s, 3),
                    "accepted": accepted,
                }
            )
        spans.append(span)
        start += length
    return Timeline(spans, graphics, report)
