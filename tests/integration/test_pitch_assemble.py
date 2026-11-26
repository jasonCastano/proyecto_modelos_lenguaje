"""Montaje del video pitch con ffmpeg y clips sintéticos (spec 028, T011 y T032).

No usa MAGI-2 ni la voz real: genera clips de 10 s con ``testsrc2`` y narraciones de tono puro, y
comprueba el video, los subtítulos, la portada, la transcripción y el rótulo de IA grabado.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageStat

from proyecto_modelos_lenguaje import pitch

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe",
)

NARRATIONS = [
    ("gancho", "Manuelita nació en 1864 como un trapiche. Valer-IA te ayuda a conocerla."),
    ("problema", "Su información está repartida en informes y páginas."),
    ("solucion", "Valer-IA reúne esa información en un solo agente."),
    ("diferencia", "Cita cada fuente y calcula las cifras en código."),
    ("uso", "Elige tu perfil, pregunta y revisa las fuentes. Si planificas, usa datos sintéticos."),
    ("accion", "Proyecto académico, no canal oficial de Manuelita. Empieza a preguntar."),
]
ON_SCREEN = "1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación"


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def _write_project(root: Path, clip: Path) -> Path:
    lines = ['version = "1.0.0"', 'language = "es"', "max_seconds = 57", ""]
    for block_id, text in NARRATIONS:
        lines += ["[[block]]", f'id = "{block_id}"', f'narration = "{text}"']
        if block_id == "gancho":
            lines.append('claims = ["unit_1864"]')
        if block_id == "uso":
            lines += [f'on_screen = "{ON_SCREEN}"', "synthetic = true"]
        lines.append("")
    (root / "guion.toml").write_text("\n".join(lines), encoding="utf-8")
    script = pitch.load_script(root)
    scenes = []
    for index, (block_id, _) in enumerate(NARRATIONS, start=1):
        prompt = root / "prompts" / f"escena-{index:02d}.json"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text("{}", encoding="utf-8")
        target = root / "escenas" / f"escena-{index:02d}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(clip, target)
        review = {
            "by": "prueba",
            "at": "2026-11-26",
            "likeness": True,
            "no_text": True,
            "no_brand": True,
            "matches_script": True,
            "block_hash": pitch.block_hash(script.block(block_id)),
        }
        scenes.append(
            {
                "id": f"escena-{index:02d}",
                "block": block_id,
                "prompt_file": f"prompts/escena-{index:02d}.json",
                "image": "referencia.png",
                "seed": 2025 + index,
                "model": pitch.MODEL,
                "model_revision": "prueba",
                "resolution": pitch.RESOLUTION,
                "generated_at": "2026-11-26T00:00:00Z",
                "clip": f"escenas/escena-{index:02d}.mp4",
                "duration_s": 10.0,
                "trim_s": 9.5,
                "status": "aprobada",
                "review": review,
            }
        )
    (root / "escenas.json").write_text(json.dumps(scenes), encoding="utf-8")
    image = root / "referencia.png"
    _ffmpeg("-f", "lavfi", "-i", "color=c=green:s=941x1672", "-frames:v", "1", str(image))
    digest = hashlib.sha256(image.read_bytes()).hexdigest()
    sheet = root / "referencia.md"
    sheet.write_text(
        "---\nfile: referencia.png\n"
        f"sha256: {digest}\norigin: prueba\nrights: prueba\nreal_person: false\n"
        "brand_elements: false\nconfirmed_by: prueba\n---\n",
        encoding="utf-8",
    )
    return sheet


@pytest.fixture(scope="module")
def produced(tmp_path_factory: pytest.TempPathFactory) -> dict:
    base = tmp_path_factory.mktemp("pitch")
    clip = base / "clip.mp4"
    _ffmpeg(
        "-f", "lavfi", "-i", "testsrc2=size=1080x1920:rate=24:duration=10",
        "-f", "lavfi", "-i", "sine=frequency=330:duration=10",
        "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
        "-c:a", "aac", "-shortest", str(clip),
    )  # fmt: skip
    root = base / "pitch"
    root.mkdir()
    reference = _write_project(root, clip)
    gold = base / "gold"
    gold.mkdir()
    unit = {"unit_id": "unit_1864", "text": "Un trapiche para producir azúcar en 1864."}
    (gold / "knowledge_units.jsonl").write_text(json.dumps(unit) + "\n", encoding="utf-8")
    narration = root / "narracion"
    narration.mkdir()
    for index in range(1, 7):
        _ffmpeg(
            "-f", "lavfi", "-i", "sine=frequency=220:duration=6",
            str(narration / f"bloque-{index:02d}.wav"),
        )  # fmt: skip
    output = base / "media" / pitch.VIDEO_NAME
    web_data = base / "pitch.ts"
    result = pitch.assemble(
        root, output, gold_dir=gold, reference=reference, web_data=web_data, preset="ultrafast"
    )
    return {"root": root, "gold": gold, "reference": reference, "clip": clip, **result}


def test_video_meets_the_pitch_limits(produced: dict) -> None:
    report = pitch.check(Path(produced["video"]), Path(produced["captions"]))
    assert report["ok"], report
    assert report["duration_s"] <= 57.1
    assert report["checks"]["resolution"]["value"] == "1080x1920"


def test_faststart_puts_metadata_first(produced: dict) -> None:
    head = Path(produced["video"]).read_bytes()[:4096]
    assert head.find(b"moov") != -1 and head.find(b"moov") < max(head.find(b"mdat"), 4096)


def test_side_files_are_written(produced: dict) -> None:
    vtt = Path(produced["captions"]).read_text(encoding="utf-8")
    assert vtt.startswith("WEBVTT") and vtt.count("-->") == 6
    assert "00:00:57.000" in vtt
    assert Path(produced["poster"]).stat().st_size > 0
    transcript = Path(produced["transcript"]).read_text(encoding="utf-8")
    assert pitch.DISCLAIMER in transcript and "1864" in transcript
    assert "PITCH_TRANSCRIPT" in (Path(produced["video"]).parents[1] / "pitch.ts").read_text(
        encoding="utf-8"
    )


def _band(image: Path) -> float:
    with Image.open(image) as frame:
        gray = frame.convert("L")
        width, height = gray.size
        box = (int(width * 0.3), height - 300, int(width * 0.7), height - 160)
        return ImageStat.Stat(gray.crop(box)).mean[0]


def _frame(video: Path, at: float, target: Path) -> Path:
    _ffmpeg("-ss", f"{at}", "-i", str(video), "-frames:v", "1", str(target))
    return target


def test_ai_disclaimer_is_burned_in(produced: dict, tmp_path: Path) -> None:
    """FR-009, SC-006: el rótulo oscurece su franja al inicio y al final, y no a mitad del video."""
    video, clip = Path(produced["video"]), produced["clip"]
    start = _band(_frame(video, 1.0, tmp_path / "out1.png")) - _band(
        _frame(clip, 1.0, tmp_path / "src1.png")
    )
    end = _band(_frame(video, 55.0, tmp_path / "out2.png")) - _band(
        _frame(clip, 55.0 - 47.5, tmp_path / "src2.png")
    )
    middle = _band(_frame(video, 25.0, tmp_path / "out3.png")) - _band(
        _frame(clip, 25.0 - 19.0, tmp_path / "src3.png")
    )
    assert start < -20 and end < -20
    assert abs(middle) < 12


def test_assemble_refuses_unapproved_scenes(produced: dict, tmp_path: Path) -> None:
    root = produced["root"]
    scenes = pitch.load_scenes(root)
    scenes[2]["status"] = "pendiente"
    pitch.save_scenes(root, scenes)
    try:
        with pytest.raises(pitch.PitchError, match="escena-03"):
            pitch.assemble(
                root,
                tmp_path / "otro.mp4",
                gold_dir=produced["gold"],
                reference=produced["reference"],
            )
    finally:
        scenes[2]["status"] = "aprobada"
        pitch.save_scenes(root, scenes)
