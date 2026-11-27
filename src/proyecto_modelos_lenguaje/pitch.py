"""Producción del video pitch de Valer-IA con MAGI-2 (spec 028, ADR 0032).

El video no se genera en la aplicación: las escenas se generan una vez con MAGI-2 por la API de
Higgsfield (``pml pitch generate``) o, como alternativa, con los pesos abiertos en 8 GPU Hopper
(``video/pitch/RUNBOOK.md``). Este módulo cubre:

- ``generate`` y ``calibrate``: las escenas por la API de Higgsfield, en serie y con tope de
  gasto (FR-025 a FR-028); es lo único que usa la red;

- ``validate``: el guion tiene 6 bloques con fuentes del oro, las escenas cumplen el manifiesto y
  la ficha de la imagen de referencia está confirmada (FR-004, FR-008, FR-012, FR-013);
- ``export_samples``: las entradas ``SAMPLES`` de ``scripts/run_demo.sh`` de MAGI-2, por escena;
- ``narrate``: la voz en español con Phonon (spec 016), un WAV por bloque;
- ``assemble``: el montaje con ffmpeg (recorte, narración, subtítulos, portada);
- ``check``: duración, resolución, audio, tamaño y subtítulos del video final.
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
from collections.abc import Callable, Iterable, Sequence
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol

from .config import PROJECT_ROOT

PITCH_ROOT = PROJECT_ROOT / "video" / "pitch"
DEFAULT_REFERENCE = PROJECT_ROOT / "docs" / "referencias" / "avatar_ingenio_manuelita.md"
MEDIA_DIR = PROJECT_ROOT / "web" / "public" / "media"
WEB_DATA = PROJECT_ROOT / "web" / "src" / "data" / "pitch.ts"
VIDEO_NAME = "pitch-valeria.mp4"
CAPTIONS_NAME = "pitch-valeria.es.vtt"
POSTER_NAME = "pitch-valeria.webp"

BLOCK_ORDER = ("gancho", "problema", "solucion", "diferencia", "uso", "accion")
USE_STEPS = {
    "perfil": "perfil",
    "pregunt": "pregunta",
    "fuente": "fuentes",
    "planific": "planificación",
}
MAX_WORDS = 22
MAX_TRIM = 9.5
MAX_SECONDS = 60
MAX_MEGABYTES = 25
MODEL = "sand/magi-2/image-to-video"
LOCAL_MODEL = "sand-ai/MAGI-2-preview"
MODELS = {"higgsfield": MODEL, "local": LOCAL_MODEL}
RESOLUTION = "1080x1920"
WIDTH, HEIGHT = 1080, 1920
FPS = 24
STATUSES = ("pendiente", "generando", "generada", "error", "aprobada", "descartada")
SKIP_UNLESS_FORCED = ("aprobada", "generada")
REQUEST_SECONDS = 10
MIN_SECONDS, MAX_REQUEST_SECONDS = 4, 30
CALIBRATION_SECONDS = 4
REVIEW_CHECKS = ("likeness", "no_text", "no_brand", "matches_script")
BED_GAIN_DB = -18
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
FONTS = (
    "C:/Windows/Fonts/arialbd.ttf",
    "C:/Windows/Fonts/arial.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
)


class PitchError(RuntimeError):
    """Error de producción del pitch con un mensaje accionable."""


# --------------------------------------------------------------------------- modelos


@dataclass(frozen=True, slots=True)
class PitchBlock:
    id: str
    narration: str
    claims: tuple[str, ...] = ()
    synthetic: bool = False
    on_screen: str = ""


@dataclass(frozen=True, slots=True)
class PitchScript:
    version: str
    language: str
    max_seconds: float
    blocks: tuple[PitchBlock, ...]

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
    unsupported_numbers: list[dict[str, str]] = field(default_factory=list)
    missing_units: list[str] = field(default_factory=list)
    reference: dict[str, bool] = field(default_factory=dict)
    stale_scenes: list[str] = field(default_factory=list)
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


def load_script(root: Path = PITCH_ROOT) -> PitchScript:
    data = tomllib.loads((root / "guion.toml").read_text(encoding="utf-8"))
    blocks = tuple(
        PitchBlock(
            id=str(item.get("id", "")),
            narration=str(item.get("narration", "")).strip(),
            claims=tuple(str(c) for c in item.get("claims") or ()),
            synthetic=bool(item.get("synthetic", False)),
            on_screen=str(item.get("on_screen", "")).strip(),
        )
        for item in data.get("block") or ()
    )
    return PitchScript(
        version=str(data.get("version", "")),
        language=str(data.get("language", "")),
        max_seconds=float(data.get("max_seconds", 0)),
        blocks=blocks,
    )


def normalize_scene(scene: dict[str, Any]) -> dict[str, Any]:
    """Completa una escena del formato anterior (sin ``provider``, ``job`` ni ``history``)."""
    if "provider" not in scene:
        scene["provider"] = "local" if scene.get("model") == LOCAL_MODEL else "higgsfield"
    scene.setdefault("request_seconds", REQUEST_SECONDS)
    scene.setdefault("job", None)
    scene.setdefault("history", [])
    return scene


def load_scenes(root: Path = PITCH_ROOT) -> list[dict[str, Any]]:
    scenes = json.loads((root / "escenas.json").read_text(encoding="utf-8"))
    if not isinstance(scenes, list):
        raise PitchError("escenas.json debe ser una lista de escenas.")
    return [normalize_scene(scene) for scene in scenes]


def save_scenes(root: Path, scenes: Sequence[dict[str, Any]]) -> None:
    text = json.dumps(list(scenes), ensure_ascii=False, indent=2) + "\n"
    (root / "escenas.json").write_text(text, encoding="utf-8")


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
    """Huella del texto de un bloque: si cambia, la escena aprobada queda desactualizada."""
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


def _validate_script(script: PitchScript, gold_dir: Path, report: ValidationReport) -> None:
    report.blocks = len(script.blocks)
    report.max_seconds = script.max_seconds
    ids = tuple(block.id for block in script.blocks)
    if ids != BLOCK_ORDER:
        report.errors.append(f"El guion debe tener 6 bloques en el orden {', '.join(BLOCK_ORDER)}.")
    if script.language != "es":
        report.errors.append('El guion debe estar en español (language = "es").')
    if not 0 < script.max_seconds <= MAX_SECONDS:
        report.errors.append(f"max_seconds debe ser mayor que 0 y como máximo {MAX_SECONDS}.")
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
                f"El bloque {block.id} tiene {words} palabras (máximo 22 palabras)."
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


def _validate_scenes(
    root: Path, script: PitchScript, scenes: list[dict[str, Any]], report: ValidationReport
) -> None:
    expected = [f"escena-{index:02d}" for index in range(1, len(BLOCK_ORDER) + 1)]
    if [scene.get("id") for scene in scenes] != expected:
        report.errors.append("escenas.json debe tener escena-01 a escena-06 en orden.")
    blocks = {block.id: block for block in script.blocks}
    for index, scene in enumerate(scenes):
        sid = scene.get("id", f"#{index}")
        if index < len(BLOCK_ORDER) and scene.get("block") != BLOCK_ORDER[index]:
            report.errors.append(f"{sid} debe corresponder al bloque {BLOCK_ORDER[index]}.")
        prompt = _resolve(root, scene.get("prompt_file"))
        if prompt is None or not prompt.is_file():
            report.errors.append(f"{sid}: falta su prompt_file.")
        if not 0 < float(scene.get("trim_s") or 0) <= MAX_TRIM:
            report.errors.append(f"{sid}: trim_s debe estar entre 0 y {MAX_TRIM} s.")
        if scene.get("resolution") != RESOLUTION:
            report.errors.append(f"{sid}: la resolución debe ser {RESOLUTION}.")
        provider = scene.get("provider")
        if provider not in MODELS:
            report.errors.append(f"{sid}: provider debe ser higgsfield o local.")
        elif scene.get("model") != MODELS[provider]:
            report.errors.append(f"{sid}: con {provider} el modelo debe ser {MODELS[provider]}.")
        seconds = scene.get("request_seconds")
        if not isinstance(seconds, int) or not MIN_SECONDS <= seconds <= MAX_REQUEST_SECONDS:
            report.errors.append(
                f"{sid}: request_seconds debe ser un entero entre {MIN_SECONDS} y "
                f"{MAX_REQUEST_SECONDS}."
            )
        status = scene.get("status")
        if status not in STATUSES:
            report.errors.append(f"{sid}: estado {status!r} inválido ({', '.join(STATUSES)}).")
        if status == "aprobada":
            review = scene.get("review") or {}
            if not all(review.get(check) is True for check in REVIEW_CHECKS) or not review.get(
                "block_hash"
            ):
                report.errors.append(
                    f"{sid}: una escena aprobada necesita la revisión completa "
                    f"({', '.join(REVIEW_CHECKS)} y block_hash)."
                )
            block = blocks.get(str(scene.get("block")))
            if block and review.get("block_hash") and review["block_hash"] != block_hash(block):
                report.stale_scenes.append(str(sid))
                report.errors.append(f"{sid}: el texto de su bloque cambió; hay que revisarla.")


def validate(
    root: Path = PITCH_ROOT,
    *,
    gold_dir: Path | None = None,
    reference: Path | None = None,
) -> ValidationReport:
    """Valida guion, escenas y ficha de la imagen (contracts/pitch-cli.md)."""
    report = ValidationReport()
    script = load_script(root)
    _validate_script(script, gold_dir or default_gold_dir(), report)
    _validate_scenes(root, script, load_scenes(root), report)
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


# --------------------------------------------------------------------------- MAGI-2


def export_samples(
    root: Path = PITCH_ROOT,
    scene: str | None = None,
    *,
    gold_dir: Path | None = None,
    reference: Path | None = None,
    prefix: str = "",
) -> list[dict[str, str]]:
    """Entradas ``SAMPLES`` de ``scripts/run_demo.sh`` (I2V: prompt_file + image).

    ``prefix`` antepone la ruta donde el repositorio está montado en la máquina de MAGI-2.
    """
    _require_valid(root, gold_dir, reference)
    scenes = load_scenes(root)
    chosen = [s for s in scenes if scene is None or s["id"] == scene]
    if scene and not chosen:
        raise PitchError(f"No existe la escena {scene}.")
    return [
        {"prompt_file": prefix + s["prompt_file"], "image": prefix + s["image"]} for s in chosen
    ]


def scene_seed(root: Path, scene: str) -> int:
    for item in load_scenes(root):
        if item["id"] == scene:
            return int(item["seed"])
    raise PitchError(f"No existe la escena {scene}.")


# --------------------------------------------------------------------------- Higgsfield


def prompt_text(root: Path, scene: dict[str, Any]) -> str:
    """Texto que recibe MAGI-2, armado desde el caption de ``prompts/escena-0N.json``."""
    path = _resolve(root, scene.get("prompt_file"))
    if path is None or not path.is_file():
        raise PitchError(f"{scene.get('id')}: falta su prompt_file.")
    caption = json.loads(path.read_text(encoding="utf-8"))
    parts = [caption.get(key, "") for key in ("subject", "setting", "action")]
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


def _spent(root: Path, scenes: Sequence[dict[str, Any]]) -> float:
    total = 0.0
    for scene in scenes:
        for job in [*(scene.get("history") or []), scene.get("job")]:
            if job:
                total += float(job.get("cost_usd") or 0)
    ledger = root / "calibracion" / "gasto.json"
    if ledger.is_file():
        total += sum(float(item.get("cost_usd") or 0) for item in json.loads(ledger.read_text()))
    return round(total, 2)


def _normalized_reference(image: Path, work: Path) -> Path:
    """La referencia a 1080×1920 (9:16) para que MAGI-2 genere vertical (research R13)."""
    target = work / "referencia-1080x1920.png"
    vf = (
        f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase:flags=lanczos,"
        f"crop={WIDTH}:{HEIGHT}"
    )
    _run([_tool("ffmpeg"), "-y", "-i", str(image), "-vf", vf, "-frames:v", "1", str(target)])
    return target


def _clip_facts(path: Path) -> dict[str, Any]:
    info = ffprobe(path)
    video = next((s for s in info.get("streams", []) if s.get("codec_type") == "video"), {})
    return {
        "duration_s": round(float(info.get("format", {}).get("duration") or 0), 2),
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "audio": any(s.get("codec_type") == "audio" for s in info.get("streams", [])),
    }


def _hf():  # import diferido: solo generate/calibrate usan la red
    from . import pitch_higgsfield

    return pitch_higgsfield


def generate(
    root: Path = PITCH_ROOT,
    *,
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
    """Genera escenas con MAGI-2 por la API de Higgsfield, en serie (contracts/pitch-cli.md)."""
    hf = _hf()
    cfg = config or hf.HiggsfieldConfig.load()
    _require_valid(root, gold_dir, reference)
    script = load_script(root)
    scenes = load_scenes(root)
    if scene and scene not in {s["id"] for s in scenes}:
        raise PitchError(f"No existe la escena {scene}.")
    chosen = [
        s
        for s in scenes
        if (scene is None or s["id"] == scene)
        and s.get("provider") == "higgsfield"
        and (force or s.get("status") not in SKIP_UNLESS_FORCED)
    ]
    skipped = [s["id"] for s in scenes if (scene is None or s["id"] == scene) and s not in chosen]
    seconds = sum(int(s.get("request_seconds") or cfg.seconds) for s in chosen)
    cost = cfg.cost(seconds)
    spent = _spent(root, scenes)
    plan = {
        "ok": True,
        "dry_run": dry_run,
        "model": cfg.model,
        "scenes": [
            {
                "id": s["id"],
                "block": s["block"],
                "seed": int(s["seed"]),
                "seconds": int(s.get("request_seconds") or cfg.seconds),
                "cost_usd": cfg.cost(int(s.get("request_seconds") or cfg.seconds)),
            }
            for s in chosen
        ],
        "skipped": skipped,
        "seconds": seconds,
        "cost_usd": cost,
        "spent_before_usd": spent,
        "max_usd": cfg.max_usd,
    }
    if spent + cost > cfg.max_usd:
        raise PitchError(
            f"El costo estimado ({cost:.2f} USD) más lo gastado ({spent:.2f} USD) pasa el tope de "
            f"{cfg.max_usd:.2f} USD (config/pitch.toml)."
        )
    if dry_run:
        for item, s in zip(plan["scenes"], chosen, strict=True):
            item["body"] = cfg.body(
                image_url="<imagen subida>",
                prompt=prompt_text(root, s),
                seed=int(s["seed"]),
                seconds=item["seconds"],
            )
        return plan
    if not chosen:
        return {**plan, "spent_usd": 0.0, "total_spent_usd": spent}
    if confirm is not None and not confirm(plan):
        return {**plan, "ok": False, "cancelled": True}

    own = client is None
    client = client or hf.HiggsfieldClient.from_env(cfg, env)
    blocks = {block.id: block for block in script.blocks}
    results: list[dict[str, Any]] = []
    spent_now = 0.0
    try:
        if cfg.model not in client.list_models():
            raise PitchError(f"Higgsfield no lista el modelo {cfg.model} para esta cuenta.")
        with tempfile.TemporaryDirectory(prefix="pitch-ref-") as tmp:
            image = _resolve(root, chosen[0]["image"])
            if image is None or not image.is_file():
                raise PitchError("Falta la imagen de referencia (git lfs pull).")
            image_url = client.upload_image(_normalized_reference(image, Path(tmp)))
        for s in chosen:
            secs = int(s.get("request_seconds") or cfg.seconds)
            key = f"{s['id']}:{block_hash(blocks[s['block']])}:{int(s['seed'])}"
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
                "error": None,
            }
            s.update(job=job, status="generando", model=cfg.model)
            save_scenes(root, scenes)
            body = cfg.body(
                image_url=image_url, prompt=prompt_text(root, s), seed=int(s["seed"]), seconds=secs
            )
            try:
                sent = client.submit(body, key)
                job["request_id"] = sent["request_id"]
                save_scenes(root, scenes)
                done = client.wait(sent["request_id"], sent["status_url"])
                dest = root / "escenas" / f"{s['id']}.mp4"
                client.download(hf.video_url(done), dest)
            except hf.JobFailed as exc:
                job.update(status=exc.status, finished_at=_now(), error=str(exc))
                s["status"] = "error"
                save_scenes(root, scenes)
                results.append({"id": s["id"], "status": "error", "error": str(exc)})
                continue
            except hf.HiggsfieldError as exc:
                job.update(status="error", finished_at=_now(), error=str(exc))
                s["status"] = "error"
                save_scenes(root, scenes)
                raise PitchError(str(exc)) from None
            facts = _clip_facts(dest)
            job.update(status="completed", finished_at=_now(), cost_usd=cfg.cost(secs))
            spent_now += job["cost_usd"]
            s.update(
                status="generada",
                clip=_relative(root, dest),
                generated_at=job["finished_at"],
                duration_s=facts["duration_s"],
                review=None,
            )
            save_scenes(root, scenes)
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
        "scenes": results,
        "spent_usd": round(spent_now, 2),
        "total_spent_usd": round(spent + spent_now, 2),
    }


def calibrate(
    root: Path = PITCH_ROOT,
    *,
    client: Any = None,
    config: Any = None,
    seconds: int = CALIBRATION_SECONDS,
    gold_dir: Path | None = None,
    reference: Path | None = None,
    env: dict[str, str] | None = None,
) -> dict[str, Any]:
    """Un trabajo corto con la escena 1 para confirmar campos, tamaño y audio (research R11)."""
    hf = _hf()
    cfg = config or hf.HiggsfieldConfig.load()
    _require_valid(root, gold_dir, reference)
    scenes = load_scenes(root)
    first = scenes[0]
    cost = cfg.cost(seconds)
    spent = _spent(root, scenes)
    if spent + cost > cfg.max_usd:
        raise PitchError(f"La calibración pasaría el tope de {cfg.max_usd:.2f} USD.")
    own = client is None
    client = client or hf.HiggsfieldClient.from_env(cfg, env)
    out_dir = root / "calibracion"
    dest = out_dir / "calibracion.mp4"
    try:
        if cfg.model not in client.list_models():
            raise PitchError(f"Higgsfield no lista el modelo {cfg.model} para esta cuenta.")
        with tempfile.TemporaryDirectory(prefix="pitch-ref-") as tmp:
            image = _resolve(root, first["image"])
            if image is None or not image.is_file():
                raise PitchError("Falta la imagen de referencia (git lfs pull).")
            image_url = client.upload_image(_normalized_reference(image, Path(tmp)))
        body = cfg.body(
            image_url=image_url,
            prompt=prompt_text(root, first),
            seed=int(first["seed"]),
            seconds=seconds,
        )
        try:
            sent = client.submit(body, f"calibracion:{first['seed']}:{seconds}:{_now()}")
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
        {"request_id": sent["request_id"], "seconds": seconds, "cost_usd": cost, "at": _now()}
    )
    ledger.write_text(json.dumps(entries, indent=2) + "\n", encoding="utf-8")
    facts = _clip_facts(dest)
    problems = []
    if abs(facts["duration_s"] - seconds) > 1:
        problems.append(
            f"la duración medida es {facts['duration_s']} s y se pidieron {seconds} s: revisa "
            f"[higgsfield.fields] duration en config/pitch.toml"
        )
    if not facts["audio"]:
        problems.append(
            "el clip no trae audio: revisa [higgsfield.fields] audio en config/pitch.toml"
        )
    if abs(facts["height"] - HEIGHT) > 16 or facts["width"] >= facts["height"]:
        problems.append(
            f"el clip mide {facts['width']}x{facts['height']}, no es vertical 1080x1920"
        )
    return {
        "ok": not problems,
        "request_id": sent["request_id"],
        "clip": _relative(root, dest),
        "requested_seconds": seconds,
        **facts,
        "cost_usd": cost,
        "fields": dict(cfg.fields),
        "problems": problems,
    }


# --------------------------------------------------------------------------- narración


def _narration_path(root: Path, index: int) -> Path:
    return root / "narracion" / f"bloque-{index:02d}.wav"


def narrate(
    root: Path = PITCH_ROOT,
    *,
    engine: VoiceEngine | None = None,
    block: str | None = None,
    voice: str | None = None,
) -> list[dict[str, Any]]:
    """Narración en español por bloque (voz Phonon, spec 016). Falla si no cabe en su escena."""
    from .voice.audio import to_wav_bytes
    from .voice.text import clean_for_speech

    if engine is None:
        from .voice.engine import VoiceService

        engine = VoiceService()
    script = load_script(root)
    scenes = {s["block"]: s for s in load_scenes(root)}
    results = []
    for index, item in enumerate(script.blocks, start=1):
        if block and item.id != block:
            continue
        result = engine.synthesize(clean_for_speech(item.narration), voice)
        seconds = len(result.samples) / float(result.sample_rate)
        limit = float(scenes[item.id]["trim_s"])
        if seconds > limit:
            raise PitchError(
                f"La narración del bloque {item.id} dura {seconds:.2f} s y su escena admite "
                f"{limit} s: recorta el texto, no aceleres la voz."
            )
        target = _narration_path(root, index)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(to_wav_bytes(result.samples, result.sample_rate))
        results.append({"block": item.id, "file": str(target), "seconds": round(seconds, 3)})
    return results


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


def _font() -> Path:
    for candidate in FONTS:
        if Path(candidate).is_file():
            return Path(candidate)
    raise PitchError("No se encontró una fuente TTF para el rótulo (Arial o DejaVu).")


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
        " * Video pitch de Valer-IA (spec 028). Generado por `pml pitch webdata` desde\n"
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


def assemble(
    root: Path = PITCH_ROOT,
    output: Path = MEDIA_DIR / VIDEO_NAME,
    *,
    gold_dir: Path | None = None,
    reference: Path | None = None,
    web_data: Path | None = None,
    preset: str = "medium",
) -> dict[str, Any]:
    """Monta el video final con ffmpeg a partir de escenas aprobadas y su narración."""
    _require_valid(root, gold_dir, reference)
    script = load_script(root)
    scenes = load_scenes(root)
    pending = [s["id"] for s in scenes if s.get("status") != "aprobada"]
    if pending:
        raise PitchError("Solo se montan escenas aprobadas; faltan: " + ", ".join(pending) + ".")
    clips: list[Path] = []
    voices: list[Path] = []
    for index, scene in enumerate(scenes, start=1):
        clip = _resolve(root, scene.get("clip"))
        if clip is None or not clip.is_file():
            raise PitchError(f"{scene['id']}: falta su clip generado con MAGI-2.")
        voice = _narration_path(root, index)
        if not voice.is_file():
            raise PitchError(f"Falta la narración del bloque {scene['block']}: pml pitch narrate.")
        clips.append(clip.resolve())
        voices.append(voice.resolve())
    durations = [float(scene["trim_s"]) for scene in scenes]
    total = sum(durations)
    if total > script.max_seconds:
        raise PitchError(f"El montaje dura {total} s y el guion admite {script.max_seconds} s.")

    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    count = len(scenes)
    with tempfile.TemporaryDirectory(prefix="pitch-assemble-") as tmp:
        work = Path(tmp)
        shutil.copyfile(_font(), work / "font.ttf")
        parts: list[str] = []
        overlays: list[str] = []
        start = 0.0
        for i, (clip, length, block) in enumerate(
            zip(clips, durations, script.blocks, strict=True)
        ):
            parts.append(
                f"[{i}:v]trim=duration={length},setpts=PTS-STARTPTS,"
                f"scale={WIDTH}:{HEIGHT}:force_original_aspect_ratio=increase,"
                f"crop={WIDTH}:{HEIGHT},fps={FPS},setsar=1[v{i}]"
            )
            bed = (
                f"[{i}:a]atrim=duration={length},asetpts=PTS-STARTPTS,"
                if _has_audio(clip)
                else f"anullsrc=r=48000:cl=stereo,atrim=duration={length},"
            )
            parts.append(
                bed + f"volume={BED_GAIN_DB}dB,aresample=48000,aformat=channel_layouts=stereo[b{i}]"
            )
            parts.append(
                f"[{count + i}:a]aresample=48000,aformat=channel_layouts=stereo,"
                f"apad=whole_dur={length},atrim=duration={length}[n{i}]"
            )
            parts.append(f"[b{i}][n{i}]amix=inputs=2:duration=first:normalize=0[a{i}]")
            if block.on_screen:
                name = f"on_screen_{i}.txt"
                (work / name).write_bytes(block.on_screen.encode("utf-8"))
                overlays.append(
                    f"drawtext=fontfile=font.ttf:textfile={name}:fontcolor=white:fontsize=44:"
                    "box=1:boxcolor=black@0.55:boxborderw=20:x=(w-text_w)/2:y=h*0.12:"
                    f"enable='between(t,{start:.2f},{start + length:.2f})'"
                )
            start += length
        joined = "".join(f"[v{i}][a{i}]" for i in range(count))
        parts.append(f"{joined}concat=n={count}:v=1:a=1[vc][ac]")
        parts.append("[vc]" + (",".join(overlays) or "null") + "[vout]")
        command = [_tool("ffmpeg"), "-y"]
        for path in [*clips, *voices]:
            command += ["-i", str(path)]
        command += [
            "-filter_complex",
            ";".join(parts),
            "-map",
            "[vout]",
            "-map",
            "[ac]",
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
        _run(command, cwd=work)
    captions = output.with_name(CAPTIONS_NAME)
    captions.write_text(render_captions(script, durations), encoding="utf-8", newline="\n")
    poster = output.with_name(POSTER_NAME)
    _run(
        [_tool("ffmpeg"), "-y", "-ss", "1", "-i", str(output), "-frames:v", "1", str(poster)],
    )
    transcript = root / "transcripcion.md"
    transcript.write_text(render_transcript(script), encoding="utf-8", newline="\n")
    if web_data is not None:
        write_web_data(root, web_data)
    return {
        "video": str(output),
        "captions": str(captions),
        "poster": str(poster),
        "transcript": str(transcript),
        "seconds": total,
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
    max_seconds: float = MAX_SECONDS,
    max_megabytes: float = MAX_MEGABYTES,
) -> dict[str, Any]:
    """Comprueba el video final (SC-001): duración, 1080×1920, audio, tamaño y subtítulos."""
    info = ffprobe(video)
    duration = float(info.get("format", {}).get("duration") or 0)
    streams = info.get("streams", [])
    video_stream = next((s for s in streams if s.get("codec_type") == "video"), {})
    size_mb = video.stat().st_size / (1024 * 1024)
    captions = vtt if vtt is not None else video.with_name(CAPTIONS_NAME)
    caption_end = _vtt_end(captions) if captions.is_file() else 0.0
    size = (video_stream.get("width"), video_stream.get("height"))
    checks = {
        "duration": {"ok": 0 < duration <= max_seconds, "value": round(duration, 2)},
        "resolution": {"ok": size == (WIDTH, HEIGHT), "value": f"{size[0]}x{size[1]}"},
        "audio": {"ok": any(s.get("codec_type") == "audio" for s in streams), "value": None},
        "size": {"ok": size_mb <= max_megabytes, "value": round(size_mb, 2)},
        "captions": {"ok": caption_end >= duration - 0.5, "value": round(caption_end, 2)},
    }
    return {
        "ok": all(item["ok"] for item in checks.values()),
        "duration_s": round(duration, 2),
        "checks": checks,
    }
