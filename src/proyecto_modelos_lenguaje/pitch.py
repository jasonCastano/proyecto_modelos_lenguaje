"""Producción del video pitch de Valer-IA (spec 028, ADR 0032; v2 por planos: spec 029, ADR 0033).

El video no se genera en la aplicación: los planos se generan una vez por la API de Higgsfield
(``pml pitch generate``) con el modelo de ``config/pitch.toml`` (MAGI-2 si responde; si no,
Kling 4.0). Este módulo cubre:

- ``validate``: guion 1.2.0 con fuentes del oro y momentos sincronizados, registro de planos
  (``escenas.json`` esquema 2) y ficha de la imagen de referencia (FR-004 a FR-021);
- ``probe``, ``generate`` y ``calibrate``: lo único que usa la red, con tope de gasto;
- ``narrate``: la voz en español con Phonon (spec 016), un WAV por bloque;
- ``align`` (en ``pitch_sync``): tiempos de cada palabra y de cada momento;
- ``assemble``: el borrador con ffmpeg (planos reajustados, narración, gráficos, subtítulos);
- ``check`` y ``publish``: validan el borrador y lo copian a la web, sin perder la v1 (FR-022).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import tempfile
import tomllib
import unicodedata
from collections.abc import Callable, Iterable, Iterator, Mapping, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from . import pitch_sync
from .config import PROJECT_ROOT

PITCH_ROOT = PROJECT_ROOT / "video" / "pitch"
DEFAULT_REFERENCE = PROJECT_ROOT / "docs" / "referencias" / "avatar_ingenio_manuelita.md"
MEDIA_DIR = PROJECT_ROOT / "web" / "public" / "media"
WEB_DATA = PROJECT_ROOT / "web" / "src" / "data" / "pitch.ts"
VIDEO_NAME = "pitch-valeria.mp4"
CAPTIONS_NAME = "pitch-valeria.es.vtt"
POSTER_NAME = "pitch-valeria.webp"
DRAFT_DIR = "borrador"
MONTAGE_NAME = "montaje.json"

BLOCK_ORDER = ("gancho", "problema", "solucion", "diferencia", "uso", "accion")
USE_STEPS = {
    "perfil": "perfil",
    "pregunt": "pregunta",
    "fuente": "fuentes",
    "planific": "planificación",
}
# v2: manda la duración total (narración + pausas ≤ 60 s); el tope por bloque solo evita textos
# desmedidos (la escena 03 ampliada tiene 31 palabras, FR-001).
MAX_WORDS = 40
MAX_SECONDS = 60
MAX_MEGABYTES = 25
PAUSE_RANGE = (0.3, 0.8)
SCHEMA = 2
WIDTH, HEIGHT = 1080, 1920
FPS = 24
MODES = ("image", "reference", "text")
CUE_KINDS = ("plano", "grafico")
SHOT_ID = re.compile(r"^plano-0([1-6])[a-z]?$")
STATUSES = ("pendiente", "generando", "generada", "error", "aprobada", "descartada")
SKIP_UNLESS_FORCED = ("aprobada", "generada")
MIN_REQUEST, MAX_REQUEST = 3, 30
CALIBRATION_SECONDS = 4
REVIEW_CHECKS = ("likeness", "no_text", "no_brand", "matches_script", "cue_shown")
CUE_TOLERANCE_S = 0.5
CUE_SHARE = 0.9
BED_GAIN_DB = -18
# Aspecto de época por plano (cambio del 2026-11-27): sepia suave con grano, viñeta y parpadeo, y un
# barrido de luz de derecha a izquierda que devuelve el color al final del tramo.
LOOKS = ("sepia-suave",)
SWEEP_RANGE = (0.2, 2.0)
SWEEP_FEATHER_PX = 60
SWEEP_GLOW = 110
SWEEP_GLOW_PX = 28
# 3 Mbps × 60 s ≈ 22 MB con el audio: el video cabe en 25 MB sea cual sea el contenido.
VIDEO_MAXRATE = "3M"
VIDEO_BUFSIZE = "6M"
# La declaración va como texto junto al video en la web y en la transcripción; el video no la
# lleva grabada (decisión del integrante, 2026-11-26).
DISCLAIMER = (
    "Video generado con IA · Valer-IA es un proyecto académico, no un canal oficial de Manuelita"
)
NUMBER = re.compile(r"\d+(?:[.,]\d+)*")
STEP_NUMBER = re.compile(r"(?:^|·)\s*\d\s")


class PitchError(RuntimeError):
    """Error de producción del pitch con un mensaje accionable."""


# --------------------------------------------------------------------------- modelos


@dataclass(frozen=True, slots=True)
class PitchCue:
    """Momento sincronizado: cuando la narración dice ``word``, se ve algo (data-model.md)."""

    id: str
    word: str
    kind: str
    shot: str | None = None
    graphic: str | None = None
    from_xy: tuple[float, float] = (0.5, 0.5)
    to_xy: tuple[float, float] | None = None
    hold_s: float | None = None
    offset_s: float = 0.0
    at_s: float | None = None


@dataclass(frozen=True, slots=True)
class PitchBlock:
    id: str
    narration: str
    claims: tuple[str, ...] = ()
    synthetic: bool = False
    on_screen: str = ""
    cues: tuple[PitchCue, ...] = ()


@dataclass(frozen=True, slots=True)
class PitchScript:
    version: str
    language: str
    max_seconds: float
    blocks: tuple[PitchBlock, ...]
    pause_s: float = 0.5

    def block(self, block_id: str) -> PitchBlock:
        for block in self.blocks:
            if block.id == block_id:
                return block
        raise PitchError(f"El guion no tiene el bloque {block_id!r}.")


@dataclass(frozen=True, slots=True)
class ReferenceSheet:
    path: Path
    fields: dict[str, str]

    @property
    def confirmed(self) -> bool:
        f = self.fields
        filled = all(f.get(key, "").strip() for key in ("origin", "rights", "confirmed_by"))
        return filled and f.get("real_person") == "false" and f.get("brand_elements") == "false"

    @property
    def image(self) -> Path:
        return self.path.parent / self.fields.get("file", "")

    @property
    def sha256_matches(self) -> bool:
        image = self.image
        return image.is_file() and _sha256(image) == self.fields.get("sha256", "")


@dataclass(slots=True)
class ValidationReport:
    ok: bool = True
    blocks: int = 0
    max_seconds: float = 0.0
    claims: int = 0
    cues: int = 0
    shots: int = 0
    unsupported_numbers: list[dict[str, str]] = field(default_factory=list)
    missing_units: list[str] = field(default_factory=list)
    reference: dict[str, bool] = field(default_factory=dict)
    stale_shots: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class VoiceEngine(Protocol):
    def synthesize(self, text: str, voice: str | None = None) -> Any: ...


# --------------------------------------------------------------------------- carga


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower()


def _xy(value: Any) -> tuple[float, float] | None:
    if value is None:
        return None
    if not isinstance(value, list | tuple) or len(value) != 2:
        raise PitchError(f"Una posición debe ser [x, y]; se recibió {value!r}.")
    return float(value[0]), float(value[1])


def _cue(item: Mapping[str, Any]) -> PitchCue:
    return PitchCue(
        id=str(item.get("id", "")),
        word=str(item.get("word", "")),
        kind=str(item.get("kind", "")),
        shot=item.get("shot"),
        graphic=item.get("graphic"),
        from_xy=_xy(item.get("from")) or (0.5, 0.5),
        to_xy=_xy(item.get("to")),
        hold_s=float(item["hold_s"]) if item.get("hold_s") is not None else None,
        offset_s=float(item.get("offset_s", 0.0)),
        at_s=float(item["at_s"]) if item.get("at_s") is not None else None,
    )


def load_script(root: Path = PITCH_ROOT) -> PitchScript:
    data = tomllib.loads((root / "guion.toml").read_text(encoding="utf-8"))
    blocks = tuple(
        PitchBlock(
            id=str(item.get("id", "")),
            narration=str(item.get("narration", "")).strip(),
            claims=tuple(str(c) for c in item.get("claims") or ()),
            synthetic=bool(item.get("synthetic", False)),
            on_screen=str(item.get("on_screen", "")).strip(),
            cues=tuple(_cue(c) for c in item.get("cue") or ()),
        )
        for item in data.get("block") or ()
    )
    return PitchScript(
        version=str(data.get("version", "")),
        language=str(data.get("language", "")),
        max_seconds=float(data.get("max_seconds", 0)),
        blocks=blocks,
        pause_s=float(data.get("pause_s", 0.5)),
    )


def load_register(root: Path = PITCH_ROOT) -> dict[str, Any]:
    """``escenas.json`` esquema 2: escenas → planos (data-model.md)."""
    data = json.loads((root / "escenas.json").read_text(encoding="utf-8"))
    if not isinstance(data, dict) or data.get("schema") != SCHEMA:
        raise PitchError(
            "escenas.json es el registro de la v1 (una lista de escenas): migra al esquema 2 de la "
            "spec 029 (escenas → planos)."
        )
    data.setdefault("model", None)
    data.setdefault("prior_spent_usd", 0.0)
    for scene in data.get("scenes", []):
        for shot in scene.setdefault("shots", []):
            shot.setdefault("job", None)
            shot.setdefault("history", [])
            shot.setdefault("review", None)
            shot.setdefault("status", "pendiente")
    return data


def save_register(root: Path, register: Mapping[str, Any]) -> None:
    text = json.dumps(register, ensure_ascii=False, indent=2) + "\n"
    (root / "escenas.json").write_text(text, encoding="utf-8")


def iter_shots(register: Mapping[str, Any]) -> Iterator[tuple[dict[str, Any], dict[str, Any]]]:
    """Pares (escena, plano) en el orden del registro."""
    for scene in register.get("scenes", []):
        for shot in scene.get("shots", []):
            yield scene, shot


def scene_status(scene: Mapping[str, Any]) -> str:
    """La escena está ``aprobada`` solo si todos sus planos lo están."""
    statuses = {shot.get("status") for shot in scene.get("shots", [])}
    if statuses == {"aprobada"}:
        return "aprobada"
    for status in ("error", "generando", "descartada", "pendiente", "generada"):
        if status in statuses:
            return status
    return "pendiente"


def load_reference(path: Path = DEFAULT_REFERENCE) -> ReferenceSheet:
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.match(r"---\n(.*?)\n---", text, re.S)
    fields: dict[str, str] = {}
    for line in (match.group(1) if match else "").splitlines():
        key, _, value = line.partition(":")
        if key.strip():
            fields[key.strip()] = value.strip().strip('"').strip("'")
    return ReferenceSheet(path=path, fields=fields)


def block_hash(block: PitchBlock) -> str:
    """Huella del texto de un bloque: si cambia, el plano aprobado queda desactualizado."""
    return hashlib.sha256(f"{block.narration}\n{block.on_screen}".encode()).hexdigest()[:16]


def _resolve(root: Path, value: str | None) -> Path | None:
    if not value:
        return None
    candidate = Path(value)
    if candidate.is_absolute():
        return candidate
    for base in (root, PROJECT_ROOT):
        if (base / candidate).exists():
            return base / candidate
    return PROJECT_ROOT / candidate


def _gold_texts(gold_dir: Path, ids: Iterable[str]) -> dict[str, str]:
    wanted = set(ids)
    found: dict[str, str] = {}
    path = gold_dir / "knowledge_units.jsonl"
    if not wanted or not path.is_file():
        return found
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            unit = json.loads(line)
            if unit.get("unit_id") in wanted:
                found[unit["unit_id"]] = str(unit.get("text", ""))
    return found


def default_gold_dir() -> Path:
    return Path(os.environ.get("PML_GOLD_DIR") or PROJECT_ROOT / "data" / "gold")


# --------------------------------------------------------------------------- validación


def _numbers(block: PitchBlock) -> list[str]:
    numbers = NUMBER.findall(block.narration)
    on_screen = STEP_NUMBER.sub(" ", block.on_screen)
    return numbers + NUMBER.findall(on_screen)


def _validate_cues(root: Path, script: PitchScript, report: ValidationReport) -> None:
    seen: set[str] = set()
    for block in script.blocks:
        for cue in block.cues:
            report.cues += 1
            where = f"{block.id}/{cue.id or '?'}"
            if not cue.id or cue.id in seen:
                report.errors.append(f"{where}: cada momento necesita un id único.")
            seen.add(cue.id)
            if cue.at_s is None and not pitch_sync.phrase_in_text(block.narration, cue.word):
                report.errors.append(
                    f"{where}: la palabra {cue.word!r} no está en la narración del bloque."
                )
            if cue.kind not in CUE_KINDS:
                report.errors.append(f"{where}: kind debe ser plano o grafico.")
            if cue.kind == "plano" and not cue.shot:
                report.errors.append(f"{where}: un momento plano necesita shot.")
            if cue.kind == "grafico":
                if not cue.graphic:
                    report.errors.append(f"{where}: un momento grafico necesita graphic.")
                elif not (root / "graficos" / f"{cue.graphic}.svg").is_file():
                    report.errors.append(f"{where}: falta graficos/{cue.graphic}.svg.")
            for name, xy in (("from", cue.from_xy), ("to", cue.to_xy)):
                if xy is not None and not all(0 <= v <= 1 for v in xy):
                    report.errors.append(f"{where}: {name} debe tener valores entre 0 y 1.")
            if cue.offset_s < 0 or (cue.hold_s is not None and cue.hold_s <= 0):
                report.errors.append(f"{where}: offset_s ≥ 0 y hold_s > 0.")


def _validate_script(
    root: Path, script: PitchScript, gold_dir: Path, report: ValidationReport
) -> None:
    report.blocks = len(script.blocks)
    report.max_seconds = script.max_seconds
    ids = tuple(block.id for block in script.blocks)
    if ids != BLOCK_ORDER:
        report.errors.append(f"El guion debe tener 6 bloques en el orden {', '.join(BLOCK_ORDER)}.")
    if script.language != "es":
        report.errors.append('El guion debe estar en español (language = "es").')
    if not 0 < script.max_seconds <= MAX_SECONDS:
        report.errors.append(f"max_seconds debe ser mayor que 0 y como máximo {MAX_SECONDS}.")
    low, high = PAUSE_RANGE
    if not low <= script.pause_s <= high:
        report.errors.append(f"pause_s debe estar entre {low} y {high} s (FR-009).")
    claims = {claim for block in script.blocks for claim in block.claims}
    report.claims = len(claims)
    texts = _gold_texts(gold_dir, claims)
    report.missing_units = sorted(claims - set(texts))
    for unit_id in report.missing_units:
        report.errors.append(f"La unidad {unit_id} no existe en el oro.")
    for block in script.blocks:
        words = len(block.narration.split())
        if not block.narration:
            report.errors.append(f"El bloque {block.id} no tiene narración.")
        if words > MAX_WORDS:
            report.errors.append(
                f"El bloque {block.id} tiene {words} palabras (máximo {MAX_WORDS} palabras)."
            )
        if STEP_NUMBER.search(block.on_screen):
            report.errors.append(
                f"El bloque {block.id} muestra pasos numerados en pantalla; la v2 usa la vista "
                "de perfiles (FR-004)."
            )
        sources = " ".join(texts.get(claim, "") for claim in block.claims)
        for number in _numbers(block):
            if number not in sources:
                report.unsupported_numbers.append({"block": block.id, "number": number})
                report.errors.append(f"La cifra {number} del bloque {block.id} no tiene fuente.")
        mentions_planning = "planific" in plain(f"{block.narration} {block.on_screen}")
        if (block.synthetic or mentions_planning) and "datos sinteticos" not in plain(
            block.narration
        ):
            report.errors.append(
                f"El bloque {block.id} menciona la planificación: debe decir «datos sintéticos»."
            )
    if "uso" in ids:
        use = script.block("uso")
        text = plain(f"{use.narration} {use.on_screen}")
        missing = [name for stem, name in USE_STEPS.items() if stem not in text]
        if missing:
            report.errors.append(
                "El bloque uso debe nombrar perfil, pregunta, fuentes y planificación; falta: "
                + ", ".join(missing)
                + "."
            )
    _validate_cues(root, script, report)


def _validate_shot(
    root: Path,
    scene_index: int,
    shot: Mapping[str, Any],
    block: PitchBlock | None,
    earlier: set[str],
    report: ValidationReport,
) -> None:
    sid = str(shot.get("id", "?"))
    match = SHOT_ID.match(sid)
    if not match or int(match.group(1)) != scene_index:
        report.errors.append(
            f"{sid}: el id debe ser plano-0{scene_index} o plano-0{scene_index}<letra>."
        )
    mode, source = shot.get("mode"), shot.get("source")
    if mode not in MODES:
        report.errors.append(f"{sid}: mode debe ser image, reference o text.")
    if mode == "text" and source is not None:
        report.errors.append(f"{sid}: un plano text no lleva source.")
    if mode == "reference" and source != "reference":
        report.errors.append(f'{sid}: un plano reference usa source = "reference".')
    if mode == "image":
        if source == "reference":
            pass
        elif isinstance(source, str) and source.startswith("frame:"):
            if source.removeprefix("frame:") not in earlier:
                report.errors.append(f"{sid}: {source} debe nombrar un plano anterior.")
        else:
            report.errors.append(f'{sid}: un plano image usa source "reference" o "frame:<plano>".')
    prompt = _resolve(root, shot.get("prompt_file"))
    if prompt is None or not prompt.is_file():
        report.errors.append(f"{sid}: falta su prompt_file.")
    seconds = shot.get("request_seconds")
    if not isinstance(seconds, int) or not MIN_REQUEST <= seconds <= MAX_REQUEST:
        report.errors.append(
            f"{sid}: request_seconds debe ser un entero entre {MIN_REQUEST} y {MAX_REQUEST}."
        )
    if not isinstance(shot.get("seed"), int):
        report.errors.append(f"{sid}: seed debe ser un entero.")
    look = shot.get("look")
    if look is not None:
        if not isinstance(look, Mapping) or look.get("style") not in LOOKS:
            report.errors.append(f"{sid}: look.style debe ser {', '.join(LOOKS)}.")
        else:
            sweep = look.get("sweep_s")
            low, high = SWEEP_RANGE
            if sweep is not None and (
                not isinstance(sweep, int | float) or not low <= sweep <= high
            ):
                report.errors.append(f"{sid}: look.sweep_s debe estar entre {low} y {high} s.")
    status = shot.get("status")
    if status not in STATUSES:
        report.errors.append(f"{sid}: estado {status!r} inválido ({', '.join(STATUSES)}).")
    if status != "aprobada" or block is None:
        return
    review = shot.get("review") or {}
    if not all(review.get(check) is True for check in REVIEW_CHECKS) or not review.get(
        "block_hash"
    ):
        report.errors.append(
            f"{sid}: un plano aprobado necesita la revisión completa "
            f"({', '.join(REVIEW_CHECKS)} y block_hash)."
        )
    # Cada momento del plano se sincroniza con un ancla o, si el plano no lo permite, se registra
    # su instante real en ``events`` para medir el desfase (research R5; decisión del 2026-11-26).
    anchors = review.get("anchors") or {}
    events = review.get("events") or {}
    needed = [c.id for c in block.cues if c.kind == "plano" and c.shot == sid]
    absent = [cid for cid in needed if cid not in anchors and cid not in events]
    if absent:
        report.errors.append(f"{sid}: faltan anclas o eventos para {', '.join(absent)} (R5).")
    if review.get("block_hash") and review["block_hash"] != block_hash(block):
        report.stale_shots.append(sid)
        report.errors.append(f"{sid}: el texto de su bloque cambió; hay que revisarlo.")


def _validate_register(
    root: Path, script: PitchScript, register: Mapping[str, Any], report: ValidationReport
) -> None:
    scenes = register.get("scenes", [])
    expected = [f"escena-{index:02d}" for index in range(1, len(BLOCK_ORDER) + 1)]
    if [scene.get("id") for scene in scenes] != expected:
        report.errors.append("escenas.json debe tener escena-01 a escena-06 en orden.")
    blocks = {block.id: block for block in script.blocks}
    earlier: set[str] = set()
    seeds: set[int] = set()
    model = register.get("model")
    for index, scene in enumerate(scenes, start=1):
        block_id = scene.get("block")
        if index <= len(BLOCK_ORDER) and block_id != BLOCK_ORDER[index - 1]:
            report.errors.append(f"{scene.get('id')} debe corresponder a {BLOCK_ORDER[index - 1]}.")
        shots = scene.get("shots") or []
        if not shots:
            report.errors.append(f"{scene.get('id')}: necesita al menos un plano.")
        block = blocks.get(str(block_id))
        cue_ids = {c.id for c in block.cues} if block else set()
        for position, shot in enumerate(shots):
            report.shots += 1
            sid = str(shot.get("id"))
            starts_at = shot.get("starts_at")
            if position == 0 and starts_at:
                report.errors.append(f"{sid}: el primer plano de una escena no lleva starts_at.")
            if position > 0 and starts_at not in cue_ids:
                report.errors.append(f"{sid}: starts_at debe ser un momento de su bloque.")
            if shot.get("seed") in seeds:
                report.errors.append(f"{sid}: la semilla {shot.get('seed')} ya la usa otro plano.")
            seeds.add(shot.get("seed"))
            if model and shot.get("model") not in (None, model):
                report.errors.append(f"{sid}: todos los planos usan el modelo {model}.")
            _validate_shot(root, index, shot, block, earlier, report)
            earlier.add(sid)
        if block:
            shot_ids = {str(s.get("id")) for s in shots}
            for cue in block.cues:
                if cue.kind == "plano" and cue.shot not in shot_ids:
                    report.errors.append(
                        f"{block.id}/{cue.id}: el plano {cue.shot} no es de {scene.get('id')}."
                    )


def validate(
    root: Path = PITCH_ROOT,
    *,
    gold_dir: Path | None = None,
    reference: Path | None = None,
) -> ValidationReport:
    """Valida guion, registro de planos y ficha de la imagen (contracts/pitch-cli.md)."""
    report = ValidationReport()
    script = load_script(root)
    _validate_script(root, script, gold_dir or default_gold_dir(), report)
    try:
        _validate_register(root, script, load_register(root), report)
    except PitchError as exc:
        report.errors.append(str(exc))
    sheet = load_reference(reference or DEFAULT_REFERENCE)
    report.reference = {"confirmed": sheet.confirmed, "sha256_matches": sheet.sha256_matches}
    if not sheet.confirmed:
        report.errors.append(
            "La ficha de la imagen de referencia no está confirmada: faltan origen, derechos o "
            "confirmed_by, o real_person/brand_elements no son false (FR-008)."
        )
    if not sheet.sha256_matches:
        report.errors.append("El sha256 de la ficha no coincide con la imagen de referencia.")
    report.ok = not report.errors
    return report


def _require_valid(root: Path, gold_dir: Path | None, reference: Path | None) -> None:
    report = validate(root, gold_dir=gold_dir, reference=reference)
    if not report.ok:
        raise PitchError("La validación del pitch falla: " + " ".join(report.errors))


# --------------------------------------------------------------------------- pesos abiertos


def export_samples(
    root: Path = PITCH_ROOT,
    shot: str | None = None,
    *,
    gold_dir: Path | None = None,
    reference: Path | None = None,
    prefix: str = "",
) -> list[dict[str, str]]:
    """Entradas ``SAMPLES`` de ``scripts/run_demo.sh`` de MAGI-2 (planos image desde la referencia).

    ``prefix`` antepone la ruta donde el repositorio está montado en la máquina de MAGI-2.
    """
    _require_valid(root, gold_dir, reference)
    register = load_register(root)
    chosen = [
        s
        for _, s in iter_shots(register)
        if (shot is None or s["id"] == shot) and s["mode"] == "image" and s["source"] == "reference"
    ]
    if shot and not chosen:
        raise PitchError(f"No existe el plano {shot} con mode image desde la referencia.")
    return [
        {"prompt_file": prefix + s["prompt_file"], "image": prefix + register["image"]}
        for s in chosen
    ]


def shot_seed(root: Path, shot: str) -> int:
    for _, item in iter_shots(load_register(root)):
        if item["id"] == shot:
            return int(item["seed"])
    raise PitchError(f"No existe el plano {shot}.")


# --------------------------------------------------------------------------- Higgsfield


def prompt_text(root: Path, shot: Mapping[str, Any]) -> str:
    """Texto que recibe el modelo, armado desde el caption de ``prompts/plano-*.json``."""
    path = _resolve(root, shot.get("prompt_file"))
    if path is None or not path.is_file():
        raise PitchError(f"{shot.get('id')}: falta su prompt_file.")
    caption = json.loads(path.read_text(encoding="utf-8"))
    parts = [caption.get(key, "") for key in ("subject", "setting", "action")]
    if caption.get("people"):
        parts.append("People: " + caption["people"])
    if caption.get("scene"):
        parts.append(caption["scene"])
    for key, label in (("camera", "Camera"), ("style", "Style"), ("audio", "Audio")):
        if caption.get(key):
            parts.append(f"{label}: {caption[key]}")
    constraints = caption.get("constraints") or []
    if isinstance(constraints, str):
        constraints = [constraints]
    if constraints:
        parts.append("Constraints: " + " ".join(constraints))
    return " ".join(p.strip() for p in parts if p and p.strip())


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _relative(root: Path, path: Path) -> str:
    for base in (PROJECT_ROOT, root):
        try:
            return path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            continue
    return str(path)


def _spent(root: Path, register: Mapping[str, Any]) -> float:
    """Gasto acumulado: v1 (``prior_spent_usd``), planos v2 y calibraciones (SC-007)."""
    total = float(register.get("prior_spent_usd") or 0)
    for _, shot in iter_shots(register):
        for job in [*(shot.get("history") or []), shot.get("job")]:
            if job:
                total += float(job.get("cost_usd") or 0)
    ledger = root / "calibracion" / "gasto.json"
    if ledger.is_file():
        total += sum(float(item.get("cost_usd") or 0) for item in json.loads(ledger.read_text()))
    return round(total, 2)


def _normalized(image: Path, work: Path, name: str) -> Path:
    """Imagen a 1080×1920 (9:16) para que el modelo genere vertical (research R13 de la 028)."""
    target = work / f"{name}-1080x1920.png"
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={WIDTH}:{HEIGHT}"
    )
    _run([_tool("ffmpeg"), "-y", "-i", str(image), "-vf", vf, "-frames:v", "1", str(target)])
    return target


def _last_frame(clip: Path, work: Path, name: str) -> Path:
    """Último cuadro de un plano aprobado (``source = frame:<plano>``, research R2)."""
    raw = work / f"{name}-ultimo.png"
    _run(
        [
            _tool("ffmpeg"),
            "-y",
            "-sseof",
            "-0.2",
            "-i",
            str(clip),
            "-frames:v",
            "1",
            "-update",
            "1",
            str(raw),
        ]
    )
    return _normalized(raw, work, name)


def _clip_facts(path: Path) -> dict[str, Any]:
    info = ffprobe(path)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    return {
        "duration_s": round(float(info.get("format", {}).get("duration") or 0), 2),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "audio": any(s.get("codec_type") == "audio" for s in info.get("streams", [])),
    }


def _hf():  # import diferido: solo probe/generate/calibrate usan la red
    from . import pitch_higgsfield

    return pitch_higgsfield


def _modes(register: Mapping[str, Any]) -> list[str]:
    return sorted({shot["mode"] for _, shot in iter_shots(register)})


def probe_models(client: Any, cfg: Any, modes: Sequence[str], only: str | None = None) -> dict:
    """Disponibilidad de cada modelo por modo, sin cobro (contracts/pitch-cli.md)."""
    models: dict[str, Any] = {}
    chosen = None
    for model_id in [only] if only else list(cfg.preference):
        spec = cfg.spec(model_id)
        results = {}
        for mode in modes:
            code, detail = client.probe(spec.slug(mode))
            results[mode] = f"{code} {detail}"[:160]
        available = all(r.split(" ", 1)[0] in ("400", "422") for r in results.values())
        models[model_id] = {"title": spec.title, "available": available, "modes": results}
        if available and chosen is None:
            chosen = model_id
    return {"model": chosen, "available": chosen is not None, "models": models}


def probe(
    root: Path = PITCH_ROOT,
    *,
    client: Any = None,
    config: Any = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """``pml pitch probe``: qué modelo de la preferencia responde, sin crear trabajos."""
    hf = _hf()
    cfg = config or hf.HiggsfieldConfig.load()
    register = load_register(root)
    own = client is None
    client = client or hf.HiggsfieldClient.from_env(cfg, env)
    try:
        report = probe_models(client, cfg, _modes(register), register.get("model"))
    finally:
        if own:
            client.close()
    return {**report, "locked": register.get("model"), "preference": list(cfg.preference)}


def _select_shots(
    register: Mapping[str, Any], shots: Sequence[str] | None, scene: str | None, force: bool
) -> tuple[list[dict[str, Any]], list[str]]:
    known = {s["id"] for _, s in iter_shots(register)}
    for name in shots or ():
        if name not in known:
            raise PitchError(f"No existe el plano {name}.")
    if scene and scene not in {s["id"] for s in register["scenes"]}:
        raise PitchError(f"No existe la escena {scene}.")
    wanted = [
        s
        for sc, s in iter_shots(register)
        if (not shots or s["id"] in shots) and (scene is None or sc["id"] == scene)
    ]
    chosen = [s for s in wanted if force or s.get("status") not in SKIP_UNLESS_FORCED]
    return chosen, [s["id"] for s in wanted if s not in chosen]


def _shot_lookup(register: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    return {s["id"]: s for _, s in iter_shots(register)}


def generate(
    root: Path = PITCH_ROOT,
    *,
    shots: Sequence[str] | None = None,
    scene: str | None = None,
    dry_run: bool = False,
    force: bool = False,
    client: Any = None,
    config: Any = None,
    confirm: Callable[[dict[str, Any]], bool] | None = None,
    gold_dir: Path | None = None,
    reference: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Genera planos por la API de Higgsfield, en serie (contracts/pitch-cli.md)."""
    hf = _hf()
    cfg = config or hf.HiggsfieldConfig.load()
    _require_valid(root, gold_dir, reference)
    script = load_script(root)
    register = load_register(root)
    chosen, skipped = _select_shots(register, shots, scene, force)
    blocks = {sc["id"]: script.block(sc["block"]) for sc in register["scenes"]}
    scene_of = {s["id"]: sc["id"] for sc, s in iter_shots(register)}
    by_id = _shot_lookup(register)
    seconds = sum(int(s["request_seconds"]) for s in chosen)
    spent = _spent(root, register)
    estimates = {m: cfg.spec(m).cost(seconds) for m in cfg.preference}
    model_id = register.get("model") or cfg.preference[0]
    plan: dict[str, Any] = {
        "ok": True,
        "dry_run": dry_run,
        "model": model_id,
        "locked": register.get("model"),
        "estimates_usd": estimates,
        "shots": [
            {
                "id": s["id"],
                "mode": s["mode"],
                "seed": int(s["seed"]),
                "seconds": int(s["request_seconds"]),
            }
            for s in chosen
        ],
        "skipped": skipped,
        "seconds": seconds,
        "spent_before_usd": spent,
        "max_usd": cfg.max_usd,
    }

    def finish_plan(spec: Any) -> None:
        for item in plan["shots"]:
            item["cost_usd"] = spec.cost(item["seconds"])
        plan.update(model=spec.id, cost_usd=spec.cost(seconds))
        plan["remaining_usd"] = round(cfg.max_usd - spent - plan["cost_usd"], 2)
        too_short = [s["id"] for s in chosen if int(s["request_seconds"]) < spec.min_seconds]
        if too_short:
            raise PitchError(
                f"{spec.title} pide al menos {spec.min_seconds} s: " + ", ".join(too_short) + "."
            )
        if spent + plan["cost_usd"] > cfg.max_usd:
            raise PitchError(
                f"El costo estimado ({plan['cost_usd']:.2f} USD) más lo gastado ({spent:.2f} USD) "
                f"pasa el tope de {cfg.max_usd:.2f} USD (config/pitch.toml)."
            )

    if dry_run:
        spec = cfg.spec(model_id)
        finish_plan(spec)
        for item, s in zip(plan["shots"], chosen, strict=True):
            item["body"] = spec.body(
                s["mode"],
                prompt=prompt_text(root, s),
                seconds=item["seconds"],
                seed=int(s["seed"]),
                image_url=None if s["mode"] == "text" else "<imagen subida>",
            )
        return plan
    if not chosen:
        return {**plan, "cost_usd": 0.0, "spent_usd": 0.0, "total_spent_usd": spent}
    pending_sources = [
        f"{s['id']} ← {s['source']}"
        for s in chosen
        if str(s.get("source", "")).startswith("frame:")
        and by_id[s["source"].removeprefix("frame:")].get("status") != "aprobada"
    ]
    if pending_sources:
        raise PitchError(
            "Estos planos parten del último cuadro de un plano aún sin aprobar: "
            + ", ".join(pending_sources)
            + ". Aprueba primero el plano fuente."
        )

    own = client is None
    client = client or hf.HiggsfieldClient.from_env(cfg, env)
    results: list[dict[str, Any]] = []
    spent_now = 0.0
    try:
        availability = probe_models(client, cfg, _modes(register), register.get("model"))
        if not availability["available"]:
            raise PitchError(
                "Ningún modelo de la preferencia está disponible en Higgsfield: "
                + json.dumps(availability["models"], ensure_ascii=False)
            )
        spec = cfg.spec(availability["model"])
        finish_plan(spec)
        if confirm is not None and not confirm(plan):
            return {**plan, "ok": False, "cancelled": True}
        uploads: dict[str, str] = {}
        with tempfile.TemporaryDirectory(prefix="pitch-ref-") as tmp:
            work = Path(tmp)

            def image_for(shot: Mapping[str, Any]) -> str | None:
                source = shot.get("source")
                if shot["mode"] == "text" or not source:
                    return None
                if source not in uploads:
                    if source == "reference":
                        image = _resolve(root, register.get("image"))
                        if image is None or not image.is_file():
                            raise PitchError("Falta la imagen de referencia (git lfs pull).")
                        path = _normalized(image, work, "referencia")
                    else:
                        origin = by_id[source.removeprefix("frame:")]
                        clip = _resolve(root, origin.get("clip"))
                        if clip is None or not clip.is_file():
                            raise PitchError(f"Falta el clip de {origin['id']}.")
                        path = _last_frame(clip, work, origin["id"])
                    uploads[source] = client.upload_image(path)
                return uploads[source]

            for s in chosen:
                secs = int(s["request_seconds"])
                block = blocks[scene_of[s["id"]]]
                key = f"{s['id']}:{block_hash(block)}:{int(s['seed'])}:{spec.id}"
                if s.get("job"):
                    s["history"] = [*(s.get("history") or []), s["job"]]
                job: dict[str, Any] = {
                    "request_id": None,
                    "status": "queued",
                    "submitted_at": _now(),
                    "finished_at": None,
                    "seconds": secs,
                    "cost_usd": 0.0,
                    "idempotency_key": key,
                    "slug": spec.slug(s["mode"]),
                    "error": None,
                }
                register["model"] = spec.id
                s.update(job=job, status="generando", model=spec.id)
                save_register(root, register)
                try:
                    body = spec.body(
                        s["mode"],
                        prompt=prompt_text(root, s),
                        seconds=secs,
                        seed=int(s["seed"]),
                        image_url=image_for(s),
                    )
                    sent = client.submit(body, key, spec.slug(s["mode"]))
                    job["request_id"] = sent["request_id"]
                    save_register(root, register)
                    done = client.wait(sent["request_id"], sent["status_url"])
                    dest = root / "planos" / f"{s['id']}.mp4"
                    client.download(hf.video_url(done), dest)
                except hf.JobFailed as exc:
                    job.update(status=exc.status, finished_at=_now(), error=str(exc))
                    s["status"] = "error"
                    save_register(root, register)
                    results.append({"id": s["id"], "status": "error", "error": str(exc)})
                    continue
                except hf.HiggsfieldError as exc:
                    job.update(status="error", finished_at=_now(), error=str(exc))
                    s["status"] = "error"
                    save_register(root, register)
                    raise PitchError(str(exc)) from None
                facts = _clip_facts(dest)
                job.update(status="completed", finished_at=_now(), cost_usd=spec.cost(secs))
                spent_now += job["cost_usd"]
                s.update(
                    status="generada",
                    clip=_relative(root, dest),
                    generated_at=job["finished_at"],
                    duration_s=facts["duration_s"],
                    review=None,
                )
                save_register(root, register)
                results.append(
                    {
                        "id": s["id"],
                        "status": "generada",
                        "request_id": job["request_id"],
                        "seconds": secs,
                        "cost_usd": job["cost_usd"],
                        "clip": s["clip"],
                        "duration_s": facts["duration_s"],
                        "size": f"{facts['width']}x{facts['height']}",
                        "audio": facts["audio"],
                    }
                )
    finally:
        if own:
            client.close()
    return {
        **plan,
        "ok": all(r["status"] == "generada" for r in results),
        "shots": results,
        "spent_usd": round(spent_now, 2),
        "total_spent_usd": round(spent + spent_now, 2),
    }


def calibrate(
    root: Path = PITCH_ROOT,
    *,
    mode: str = "image",
    client: Any = None,
    config: Any = None,
    seconds: int = CALIBRATION_SECONDS,
    gold_dir: Path | None = None,
    reference: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Un trabajo corto del primer plano de ``mode`` para confirmar campos y formato (R2)."""
    hf = _hf()
    cfg = config or hf.HiggsfieldConfig.load()
    if mode not in MODES:
        raise PitchError(f"mode debe ser {', '.join(MODES)}.")
    _require_valid(root, gold_dir, reference)
    register = load_register(root)
    sample = next((s for _, s in iter_shots(register) if s["mode"] == mode), None)
    if sample is None:
        raise PitchError(f"Ningún plano usa mode {mode}.")
    spent = _spent(root, register)
    own = client is None
    client = client or hf.HiggsfieldClient.from_env(cfg, env)
    out_dir = root / "calibracion"
    dest = out_dir / f"calibracion-{mode}.mp4"
    try:
        availability = probe_models(client, cfg, [mode], register.get("model"))
        if not availability["available"]:
            raise PitchError(
                "Ningún modelo responde en el modo "
                + mode
                + ": "
                + json.dumps(availability["models"], ensure_ascii=False)
            )
        spec = cfg.spec(availability["model"])
        seconds = max(seconds, spec.min_seconds)
        cost = spec.cost(seconds)
        if spent + cost > cfg.max_usd:
            raise PitchError(f"La calibración pasaría el tope de {cfg.max_usd:.2f} USD.")
        image_url = None
        if mode != "text":
            with tempfile.TemporaryDirectory(prefix="pitch-ref-") as tmp:
                image = _resolve(root, register.get("image"))
                if image is None or not image.is_file():
                    raise PitchError("Falta la imagen de referencia (git lfs pull).")
                image_url = client.upload_image(_normalized(image, Path(tmp), "referencia"))
        body = spec.body(
            mode,
            prompt=prompt_text(root, sample),
            seconds=seconds,
            seed=int(sample["seed"]),
            image_url=image_url,
        )
        try:
            sent = client.submit(body, f"calibracion:{spec.id}:{mode}:{_now()}", spec.slug(mode))
            done = client.wait(sent["request_id"], sent["status_url"])
            client.download(hf.video_url(done), dest)
        except hf.HiggsfieldError as exc:
            raise PitchError(str(exc)) from None
    finally:
        if own:
            client.close()
    ledger = out_dir / "gasto.json"
    entries = json.loads(ledger.read_text()) if ledger.is_file() else []
    entries.append(
        {
            "request_id": sent["request_id"],
            "model": spec.id,
            "mode": mode,
            "seconds": seconds,
            "cost_usd": cost,
            "at": _now(),
        }
    )
    ledger.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    facts = _clip_facts(dest)
    problems = []
    if abs(facts["duration_s"] - seconds) > 1:
        problems.append(
            f"la duración medida es {facts['duration_s']} s y se pidieron {seconds} s: revisa "
            f"[models.{spec.id}.fields] duration en config/pitch.toml"
        )
    if spec.audio and not facts["audio"]:
        problems.append(
            f"el clip no trae audio: revisa [models.{spec.id}.fields] audio en config/pitch.toml"
        )
    if abs(facts["height"] - HEIGHT) > 16 or facts["width"] >= facts["height"]:
        problems.append(
            f"el clip mide {facts['width']}x{facts['height']}, no es vertical 1080x1920"
        )
    return {
        "ok": not problems,
        "model": spec.id,
        "mode": mode,
        "request_id": sent["request_id"],
        "clip": _relative(root, dest),
        "requested_seconds": seconds,
        **facts,
        "cost_usd": cost,
        "fields": sorted(body),
        "problems": problems,
    }


# --------------------------------------------------------------------------- narración


def _narration_path(root: Path, index: int) -> Path:
    return root / "narracion" / f"bloque-{index:02d}.wav"


def narration_paths(root: Path, script: PitchScript) -> list[Path]:
    return [_narration_path(root, i) for i in range(1, len(script.blocks) + 1)]


def narrate(
    root: Path = PITCH_ROOT,
    *,
    engine: VoiceEngine | None = None,
    block: str | None = None,
    voice: str | None = None,
) -> list[dict[str, Any]]:
    """Narración por bloque (Phonon, spec 016). Falla si el total pasa de ``max_seconds`` (R4)."""
    from .voice.audio import to_wav_bytes
    from .voice.text import clean_for_speech

    if engine is None:
        from .voice.engine import VoiceService

        engine = VoiceService()
    script = load_script(root)
    synthesized: dict[int, tuple[Any, float]] = {}
    lengths: dict[str, float] = {}
    for index, item in enumerate(script.blocks, start=1):
        if block and item.id != block:
            path = _narration_path(root, index)
            if path.is_file():
                lengths[item.id] = pitch_sync.wav_seconds(path)
            continue
        result = engine.synthesize(clean_for_speech(item.narration), voice)
        seconds = len(result.samples) / float(result.sample_rate)
        synthesized[index] = (result, seconds)
        lengths[item.id] = seconds
    total = sum(lengths.values()) + script.pause_s * len(script.blocks)
    if total > script.max_seconds:
        longest = max(lengths, key=lambda k: lengths[k])
        raise PitchError(
            f"La narración suma {total:.2f} s con las pausas y el guion admite "
            f"{script.max_seconds} s: recorta el bloque {longest} ({lengths[longest]:.2f} s); "
            "no aceleres la voz."
        )
    results = []
    for index, (result, seconds) in synthesized.items():
        target = _narration_path(root, index)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(to_wav_bytes(result.samples, result.sample_rate))
        item = script.blocks[index - 1]
        results.append({"block": item.id, "file": str(target), "seconds": round(seconds, 3)})
    return results


def align(
    root: Path = PITCH_ROOT, *, transcriber: pitch_sync.Transcriber | None = None
) -> dict[str, Any]:
    """``pml pitch align``: tiempos de palabras y momentos en ``sincronia.json`` (R3)."""
    script = load_script(root)
    try:
        return pitch_sync.align(
            root,
            script,
            narration_paths(root, script),
            pause_s=script.pause_s,
            transcriber=transcriber,
        )
    except pitch_sync.SyncError as exc:
        raise PitchError(str(exc)) from None


# --------------------------------------------------------------------------- ffmpeg


def _tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise PitchError(f"No se encontró {name}. Instala ffmpeg y vuelve a intentarlo.")
    return path


def _run(command: Sequence[str], cwd: Path | None = None) -> None:
    result = subprocess.run(list(command), cwd=cwd, capture_output=True, text=True, check=False)
    if result.returncode != 0:
        tail = "\n".join(result.stderr.strip().splitlines()[-8:])
        raise PitchError(f"{Path(command[0]).name} falló:\n{tail}")


def ffprobe(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [
            _tool("ffprobe"),
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise PitchError(f"ffprobe no pudo leer {path}: {result.stderr.strip()}")
    return json.loads(result.stdout)


def _has_audio(path: Path) -> bool:
    return any(s.get("codec_type") == "audio" for s in ffprobe(path).get("streams", []))


def _duration(path: Path) -> float:
    return float(ffprobe(path).get("format", {}).get("duration") or 0)


def _timestamp(seconds: float) -> str:
    millis = round(seconds * 1000)
    hours, rest = divmod(millis, 3_600_000)
    minutes, rest = divmod(rest, 60_000)
    secs, ms = divmod(rest, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d}.{ms:03d}"


def render_captions(script: PitchScript, durations: Sequence[float]) -> str:
    lines = ["WEBVTT", ""]
    start = 0.0
    for index, (block, length) in enumerate(zip(script.blocks, durations, strict=True), start=1):
        end = start + length
        lines += [str(index), f"{_timestamp(start)} --> {_timestamp(end)}", block.narration, ""]
        start = end
    return "\n".join(lines)


def render_transcript(script: PitchScript) -> str:
    body = "\n\n".join(block.narration for block in script.blocks)
    return (
        "# Transcripción del video pitch de Valer-IA\n\n"
        f"*Guion {script.version}. {DISCLAIMER}.*\n\n{body}\n"
    )


def render_web_data(script: PitchScript) -> str:
    """``web/src/data/pitch.ts``, generado desde el guion para que la web no diverja."""
    items = ",\n".join(
        f"  {{ id: {json.dumps(b.id)}, text: {json.dumps(b.narration, ensure_ascii=False)} }}"
        for b in script.blocks
    )
    return (
        "/**\n"
        " * Video pitch de Valer-IA (specs 028 y 029). Generado por `pml pitch webdata` desde\n"
        " * video/pitch/guion.toml: no editar a mano.\n"
        " */\n"
        "export const PITCH_VIDEO = {\n"
        f'  src: "/media/{VIDEO_NAME}",\n'
        f'  poster: "/media/{POSTER_NAME}",\n'
        f'  captions: "/media/{CAPTIONS_NAME}",\n'
        "};\n\n"
        f"export const PITCH_DISCLAIMER = {json.dumps(DISCLAIMER, ensure_ascii=False)};\n\n"
        f"export const PITCH_SCRIPT_VERSION = {json.dumps(script.version)};\n\n"
        "export const PITCH_TRANSCRIPT: { id: string; text: string }[] = [\n"
        f"{items},\n"
        "];\n"
    )


def write_web_data(root: Path = PITCH_ROOT, target: Path = WEB_DATA) -> Path:
    target.write_text(render_web_data(load_script(root)), encoding="utf-8", newline="\n")
    return target


def poster_from_image(image: Path, output: Path) -> Path:
    """Portada a partir de la imagen de referencia, antes del video real."""
    output.parent.mkdir(parents=True, exist_ok=True)
    vf = f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,crop={WIDTH}:{HEIGHT}"
    _run([_tool("ffmpeg"), "-y", "-i", str(image), "-vf", vf, "-frames:v", "1", str(output)])
    return output


def _retime_limits() -> tuple[float, float]:
    try:
        cfg = _hf().HiggsfieldConfig.load()
        return float(cfg.retime_min), float(cfg.retime_max)
    except FileNotFoundError, KeyError, ValueError:
        return 0.7, 1.25


def _look_filters(
    src: str, out: str, index: int, look: Mapping[str, Any], length: float
) -> list[str]:
    """Sepia suave de época y, si hay ``sweep_s``, el barrido que devuelve el color.

    El barrido es una línea de luz que cruza la pantalla de derecha a izquierda en los últimos
    ``sweep_s`` segundos del tramo; a su paso la imagen pasa de sepia al color original.
    """
    sepia = (
        "colorchannelmixer=.393:.769:.189:0:.349:.686:.168:0:.272:.534:.131,"
        "eq=contrast=0.92:saturation=0.8:brightness='0.012*sin(2*PI*6*t)':eval=frame,"
        "noise=alls=9:allf=t+u,vignette=angle=PI/5"
    )
    sweep = look.get("sweep_s")
    if not sweep:
        return [f"[{src}]{sepia},format=yuv420p[{out}]"]
    start = max(0.0, length - float(sweep))
    edge = f"(W*(1-(T-{start:.4f})/{float(sweep):.4f}))"
    alpha = f"clip((X-{edge})/{SWEEP_FEATHER_PX}+0.5,0,1)"
    glow = f"{SWEEP_GLOW}*max(0,1-abs(X-{edge})/{SWEEP_GLOW_PX})"
    expr = f"min(255,A*(1-{alpha})+B*{alpha}+{glow})"
    return [
        f"[{src}]split=2[lc{index}][ls{index}]",
        f"[ls{index}]{sepia},format=gbrp[lsp{index}]",
        f"[lc{index}]format=gbrp[lcp{index}]",
        f"[lsp{index}][lcp{index}]blend=all_expr='{expr}',format=yuv420p[{out}]",
    ]


def _segment_filters(
    index: int,
    seg: pitch_sync.Segment,
    has_audio: bool,
    look: Mapping[str, Any] | None = None,
) -> list[str]:
    """Video y fondo de un tramo de plano: recorte, reajuste por piezas, tamaño y aspecto."""
    parts: list[str] = []
    norm = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
        f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1"
    )
    pieces = seg.pieces
    sources = (
        [f"[{index}:v]"] if len(pieces) == 1 else [f"[p{index}_{k}]" for k in range(len(pieces))]
    )
    if len(pieces) > 1:
        parts.append(f"[{index}:v]split={len(pieces)}" + "".join(sources))
    chunks = []
    for k, (src, piece) in enumerate(zip(sources, pieces, strict=True)):
        label = f"q{index}_{k}"
        parts.append(
            f"{src}trim=start={piece.clip_start:.4f}:end={piece.clip_end:.4f},"
            f"setpts=(PTS-STARTPTS)/{piece.factor:.5f},{norm}[{label}]"
        )
        chunks.append(f"[{label}]")
    joined = "".join(chunks)
    concat = f"concat=n={len(chunks)}:v=1:a=0," if len(chunks) > 1 else ""
    parts.append(
        f"{joined}{concat}tpad=stop_mode=clone:stop_duration=1,"
        f"trim=duration={seg.length:.4f},setpts=PTS-STARTPTS[{'w' if look else 'v'}{index}]"
    )
    if look:
        parts += _look_filters(f"w{index}", f"v{index}", index, look, seg.length)
    start = pieces[0].clip_start if pieces else 0.0
    bed = (
        f"[{index}:a]atrim=start={start:.4f}:duration={seg.length:.4f},asetpts=PTS-STARTPTS,"
        if has_audio
        else f"anullsrc=r=48000:cl=stereo,atrim=duration={seg.length:.4f},"
    )
    parts.append(
        bed + f"volume={BED_GAIN_DB}dB,aresample=48000,aformat=channel_layouts=stereo,"
        f"apad=whole_dur={seg.length:.4f},atrim=duration={seg.length:.4f}[b{index}]"
    )
    return parts


def assemble(
    root: Path = PITCH_ROOT,
    output: Path | None = None,
    *,
    gold_dir: Path | None = None,
    reference: Path | None = None,
    preset: str = "medium",
    limits: tuple[float, float] | None = None,
) -> dict[str, Any]:
    """Monta el borrador con ffmpeg: planos reajustados, narración y gráficos (contrato v2)."""
    from .pitch_graphics import overlay_graph

    _require_valid(root, gold_dir, reference)
    script = load_script(root)
    register = load_register(root)
    pending = [s["id"] for _, s in iter_shots(register) if s.get("status") != "aprobada"]
    if pending:
        raise PitchError("Solo se montan planos aprobados; faltan: " + ", ".join(pending) + ".")
    voices = narration_paths(root, script)
    missing = [str(v) for v in voices if not v.is_file()]
    if missing:
        raise PitchError("Falta la narración (pml pitch narrate): " + ", ".join(missing))
    try:
        sync = pitch_sync.load_sync(root)
    except pitch_sync.SyncError as exc:
        raise PitchError(str(exc)) from None
    stale = pitch_sync.stale_reasons(sync, script, voices)
    if stale:
        raise PitchError(
            "sincronia.json está desactualizada (pml pitch align): " + "; ".join(stale)
        )

    def clip_path(shot: Mapping[str, Any]) -> Path:
        clip = _resolve(root, shot.get("clip"))
        if clip is None or not clip.is_file():
            raise PitchError(f"{shot['id']}: falta su clip generado.")
        return clip.resolve()

    try:
        timeline = pitch_sync.build_timeline(
            script,
            register["scenes"],
            sync,
            clip_path=clip_path,
            clip_duration=_duration,
            limits=limits or _retime_limits(),
        )
    except pitch_sync.SyncError as exc:
        raise PitchError(str(exc)) from None
    total = timeline.seconds
    if total > script.max_seconds:
        raise PitchError(f"El montaje dura {total} s y el guion admite {script.max_seconds} s.")

    output = (output or root / DRAFT_DIR / VIDEO_NAME).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    segments = [seg for span in timeline.scenes for seg in span.segments]
    parts: list[str] = []
    command = [_tool("ffmpeg"), "-y"]
    for seg in segments:
        command += ["-i", str(seg.clip)]
    for voice in voices:
        command += ["-i", str(voice.resolve())]
    shots = _shot_lookup(register)
    for index, seg in enumerate(segments):
        look = shots.get(seg.shot, {}).get("look")
        parts += _segment_filters(index, seg, _has_audio(seg.clip), look)
    joined = "".join(f"[v{i}][b{i}]" for i in range(len(segments)))
    parts.append(f"{joined}concat=n={len(segments)}:v=1:a=1[vbase][abed]")
    mix = ["[abed]"]
    for k, span in enumerate(timeline.scenes):
        delay = round(span.start * 1000)
        parts.append(
            f"[{len(segments) + k}:a]aresample=48000,aformat=channel_layouts=stereo,"
            f"adelay={delay}|{delay}[n{k}]"
        )
        mix.append(f"[n{k}]")
    parts.append(f"{''.join(mix)}amix=inputs={len(mix)}:duration=first:normalize=0[ac]")
    try:
        inputs, overlays, label = overlay_graph(
            timeline.graphics,
            root,
            base="vbase",
            first_input=len(segments) + len(voices),
            total_s=total,
            fps=FPS,
        )
    except FileNotFoundError as exc:
        raise PitchError(str(exc)) from None
    command += inputs
    parts += overlays
    parts.append(f"[{label}]null[vout]")
    command += [
        "-filter_complex",
        ";".join(parts),
        "-map",
        "[vout]",
        "-map",
        "[ac]",
        "-t",
        f"{total:.3f}",
        "-c:v",
        "libx264",
        "-preset",
        preset,
        "-crf",
        "23",
        "-maxrate",
        VIDEO_MAXRATE,
        "-bufsize",
        VIDEO_BUFSIZE,
        "-pix_fmt",
        "yuv420p",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-movflags",
        "+faststart",
        str(output),
    ]
    _run(command)
    durations = [span.length for span in timeline.scenes]
    captions = output.with_name(CAPTIONS_NAME)
    captions.write_text(render_captions(script, durations), encoding="utf-8", newline="\n")
    poster = output.with_name(POSTER_NAME)
    _run([_tool("ffmpeg"), "-y", "-ss", "1", "-i", str(output), "-frames:v", "1", str(poster)])
    montage = {
        "script_version": script.version,
        "seconds": total,
        "scenes": [
            {
                "id": span.id,
                "block": span.block,
                "start_s": round(span.start, 3),
                "scene_s": round(span.length, 3),
                "narration_s": round(span.narration_s, 3),
            }
            for span in timeline.scenes
        ],
        "retime": [
            {"shot": seg.shot, "factors": [round(p.factor, 3) for p in seg.pieces]}
            for seg in segments
        ],
        "cues": timeline.cues,
    }
    (output.parent / MONTAGE_NAME).write_text(
        json.dumps(montage, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return {
        "video": str(output),
        "captions": str(captions),
        "poster": str(poster),
        "montage": str(output.parent / MONTAGE_NAME),
        **montage,
    }


# --------------------------------------------------------------------------- comprobación


def _vtt_end(path: Path) -> float:
    ends = re.findall(r"-->\s*(\d+):(\d+):(\d+)\.(\d+)", path.read_text(encoding="utf-8"))
    if not ends:
        return 0.0
    h, m, s, ms = (int(x) for x in ends[-1])
    return h * 3600 + m * 60 + s + ms / 1000


def check(
    video: Path,
    vtt: Path | None = None,
    *,
    montage: Mapping[str, Any] | None = None,
    script: PitchScript | None = None,
    max_seconds: float = MAX_SECONDS,
    max_megabytes: float = MAX_MEGABYTES,
) -> dict[str, Any]:
    """Comprueba el video (SC-001) y, con el montaje, pausas y momentos (SC-002, SC-003)."""
    info = ffprobe(video)
    duration = float(info.get("format", {}).get("duration") or 0)
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    size_mb = video.stat().st_size / (1024 * 1024)
    captions = vtt if vtt is not None else video.with_name(CAPTIONS_NAME)
    caption_end = _vtt_end(captions) if captions.is_file() else 0.0
    size = (video_stream.get("width"), video_stream.get("height"))
    checks: dict[str, dict[str, Any]] = {
        "duration": {"ok": 0 < duration <= max_seconds, "value": round(duration, 2)},
        "resolution": {"ok": size == (WIDTH, HEIGHT), "value": f"{size[0]}x{size[1]}"},
        "audio": {"ok": any(s.get("codec_type") == "audio" for s in streams), "value": None},
        "size": {"ok": size_mb <= max_megabytes, "value": round(size_mb, 2)},
        "captions": {"ok": caption_end >= duration - 0.5, "value": round(caption_end, 2)},
    }
    if montage is not None:
        gaps = [round(float(s["scene_s"]) - float(s["narration_s"]), 3) for s in montage["scenes"]]
        checks["pauses"] = {
            "ok": bool(gaps) and max(gaps) <= PAUSE_RANGE[1] + 1e-3,
            "value": max(gaps or [0]),
        }
        cues = montage.get("cues") or []
        deltas = [float(c["delta_s"]) for c in cues]
        within = sum(1 for d in deltas if abs(d) <= CUE_TOLERANCE_S)
        share = within / len(deltas) if deltas else 1.0
        early = [c["id"] for c in cues if float(c["delta_s"]) < -1e-6 and not c.get("accepted")]
        checks["cues"] = {
            "ok": share >= CUE_SHARE and not early,
            "value": round(share, 3),
        }
        outside = [c["id"] for c in cues if abs(float(c["delta_s"])) > CUE_TOLERANCE_S]
        if outside:
            checks["cues"]["outside"] = outside
    if script is not None:
        steps = [b.id for b in script.blocks if STEP_NUMBER.search(b.on_screen)]
        checks["no_steps_text"] = {"ok": not steps, "value": steps or None}
    return {
        "ok": all(item["ok"] for item in checks.values()),
        "duration_s": round(duration, 2),
        "checks": checks,
    }


def publish(
    root: Path = PITCH_ROOT,
    *,
    media_dir: Path = MEDIA_DIR,
    web_data: Path = WEB_DATA,
    gold_dir: Path | None = None,
    reference: Path | None = None,
) -> dict[str, Any]:
    """Copia el borrador aprobado y validado a la web (FR-022). No hace commit."""
    _require_valid(root, gold_dir, reference)
    register = load_register(root)
    pending = [s["id"] for _, s in iter_shots(register) if s.get("status") != "aprobada"]
    if pending:
        raise PitchError("No se publica con planos sin aprobar: " + ", ".join(pending) + ".")
    draft = root / DRAFT_DIR
    video = draft / VIDEO_NAME
    montage_path = draft / MONTAGE_NAME
    if not video.is_file() or not montage_path.is_file():
        raise PitchError("Falta el borrador: corre pml pitch assemble.")
    script = load_script(root)
    montage = json.loads(montage_path.read_text(encoding="utf-8"))
    if montage.get("script_version") != script.version:
        raise PitchError("El borrador es de otra versión del guion: vuelve a montarlo.")
    report = check(video, montage=montage, script=script)
    if not report["ok"]:
        failed = [name for name, item in report["checks"].items() if not item["ok"]]
        raise PitchError("El borrador no pasa el chequeo: " + ", ".join(failed) + ".")
    media_dir.mkdir(parents=True, exist_ok=True)
    published = []
    for name in (VIDEO_NAME, CAPTIONS_NAME, POSTER_NAME):
        shutil.copyfile(draft / name, media_dir / name)
        published.append(str(media_dir / name))
    transcript = root / "transcripcion.md"
    transcript.write_text(render_transcript(script), encoding="utf-8", newline="\n")
    write_web_data(root, web_data)
    old = sorted(_relative(root, p) for p in (root / "escenas").glob("escena-*.mp4"))
    return {
        "published": published,
        "transcript": str(transcript),
        "web_data": str(web_data),
        "seconds": montage["seconds"],
        "remove_v1": old,
    }
