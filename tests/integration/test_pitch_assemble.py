"""Montaje del pitch v2 con ffmpeg y planos sintéticos (specs 028 y 029, T018, T027 y T034).

No usa modelos de video, voz real ni reconocedor: genera clips con ``testsrc2``, narraciones de
tono puro y un transcriptor falso. Comprueba el borrador, los gráficos en el instante de su
palabra, el reajuste de planos, las pausas, el chequeo y la publicación.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
from pathlib import Path

import pytest
from PIL import Image, ImageChops, ImageStat

from proyecto_modelos_lenguaje import pitch
from proyecto_modelos_lenguaje.pitch_sync import Word

pytestmark = pytest.mark.skipif(
    shutil.which("ffmpeg") is None or shutil.which("ffprobe") is None,
    reason="requiere ffmpeg y ffprobe",
)

NARRATIONS = [
    ("gancho", "Manuelita nació en 1864 como un trapiche. Valer-IA te ayuda a conocerla."),
    ("problema", "Su información está repartida en informes y páginas de plataformas."),
    ("solucion", "Valer-IA reúne esa información en un solo agente para cinco públicos."),
    ("diferencia", "Cita cada fuente y calcula las cifras en código."),
    ("uso", "Elige tu perfil, pregunta y revisa las fuentes. Si planificas, usa datos sintéticos."),
    ("accion", "Conocer Manuelita ya no es buscar: es preguntar. Empieza hoy."),
]
SHOTS = [
    ("escena-01", "gancho", "plano-01", {}),
    ("escena-02", "problema", "plano-02", {}),
    ("escena-03", "solucion", "plano-03a", {}),
    ("escena-03", "solucion", "plano-03b", {"starts_at": "s.cinco", "source": "frame:plano-03a"}),
    ("escena-04", "diferencia", "plano-04", {}),
    ("escena-05", "uso", "plano-05", {}),
    ("escena-06", "accion", "plano-06", {}),
]
NARRATION_S = 6.0
STEP = 0.5  # el transcriptor falso dice una palabra cada 0,5 s


def _ffmpeg(*args: str) -> None:
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", *args], check=True)


def words_of(text: str) -> list[Word]:
    return [Word(w, i * STEP, i * STEP + 0.4) for i, w in enumerate(text.split())]


def fake_transcriber(path: Path) -> list[Word]:
    return words_of(NARRATIONS[int(path.stem[-2:]) - 1][1])


def _write_project(root: Path, clip: Path) -> Path:
    lines = ['version = "1.2.0"', 'language = "es"', "max_seconds = 57", "pause_s = 0.5", ""]
    for block_id, text in NARRATIONS:
        lines += ["[[block]]", f'id = "{block_id}"', f'narration = "{text}"']
        if block_id == "gancho":
            lines.append('claims = ["unit_1864"]')
        if block_id == "uso":
            lines.append("synthetic = true")
        lines.append("")
        if block_id == "problema":
            lines += [
                "[[block.cue]]",
                'id = "p.informes"',
                'word = "informes"',
                'kind = "grafico"',
                'graphic = "icono-prueba"',
                "from = [0.5, 0.25]",
                "to = [0.5, 0.25]",
                "hold_s = 1.5",
                "",
            ]
        if block_id == "solucion":
            lines += [
                "[[block.cue]]",
                'id = "s.agente"',
                'word = "agente"',
                'kind = "plano"',
                'shot = "plano-03a"',
                "",
                "[[block.cue]]",
                'id = "s.cinco"',
                'word = "cinco"',
                'kind = "plano"',
                'shot = "plano-03b"',
                "",
            ]
    (root / "guion.toml").write_text("\n".join(lines), encoding="utf-8")
    graphics = root / "graficos"
    (graphics / "png").mkdir(parents=True)
    (graphics / "icono-prueba.svg").write_text("<svg/>", encoding="utf-8")
    Image.new("RGBA", (240, 240), (255, 210, 0, 255)).save(graphics / "png" / "icono-prueba.png")
    script = pitch.load_script(root)
    scenes: dict[str, dict] = {}
    for seed, (scene_id, block_id, shot_id, extra) in enumerate(SHOTS, start=3001):
        prompt = root / "prompts" / f"{shot_id}.json"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text("{}", encoding="utf-8")
        target = root / "planos" / f"{shot_id}.mp4"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(clip, target)
        anchors = {"s.agente": 3.15} if shot_id == "plano-03a" else {}
        if shot_id == "plano-03b":
            anchors = {"s.cinco": 0.2}
        scenes.setdefault(scene_id, {"id": scene_id, "block": block_id, "shots": []})
        scenes[scene_id]["shots"].append(
            {
                "id": shot_id,
                "mode": "image",
                "source": "reference",
                **extra,
                "prompt_file": f"prompts/{shot_id}.json",
                "seed": seed,
                "request_seconds": 10,
                "model": "magi2",
                "job": None,
                "history": [],
                "generated_at": "2026-11-26T00:00:00Z",
                "clip": f"planos/{shot_id}.mp4",
                "duration_s": 10.0,
                "status": "aprobada",
                "review": {
                    "by": "prueba",
                    "at": "2026-11-26",
                    "likeness": True,
                    "no_text": True,
                    "no_brand": True,
                    "matches_script": True,
                    "cue_shown": True,
                    "anchors": anchors,
                    "block_hash": pitch.block_hash(script.block(block_id)),
                },
            }
        )
    register = {
        "schema": 2,
        "model": "magi2",
        "image": "referencia.png",
        "prior_spent_usd": 0.0,
        "scenes": list(scenes.values()),
    }
    (root / "escenas.json").write_text(json.dumps(register), encoding="utf-8")
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
            "-f", "lavfi", "-i", f"sine=frequency=220:duration={NARRATION_S}",
            "-c:a", "pcm_s16le", str(narration / f"bloque-{index:02d}.wav"),
        )  # fmt: skip
    pitch.align(root, transcriber=fake_transcriber)
    result = pitch.assemble(root, gold_dir=gold, reference=reference, preset="ultrafast")
    return {"root": root, "gold": gold, "reference": reference, "clip": clip, **result}


def _frame(video: Path, at: float, target: Path) -> Path:
    _ffmpeg("-ss", f"{at}", "-i", str(video), "-frames:v", "1", str(target))
    return target


# --------------------------------------------------------------------------- borrador (T018)


def test_draft_goes_to_the_draft_folder_with_its_side_files(produced: dict) -> None:
    video = Path(produced["video"])
    assert video.parent == produced["root"] / "borrador"
    for name in (pitch.CAPTIONS_NAME, pitch.POSTER_NAME, pitch.MONTAGE_NAME):
        assert (video.parent / name).is_file()


def test_scene_lengths_follow_the_narration(produced: dict) -> None:
    """R4: cada escena dura su narración más la pausa de 0,5 s."""
    assert produced["seconds"] == pytest.approx(6 * (NARRATION_S + 0.5))
    starts = [s["start_s"] for s in produced["scenes"]]
    assert starts == pytest.approx([0, 6.5, 13, 19.5, 26, 32.5])
    report = pitch.check(Path(produced["video"]), montage=produced)
    assert report["ok"], report
    assert report["duration_s"] == pytest.approx(39.0, abs=0.1)
    assert report["checks"]["pauses"]["value"] == pytest.approx(0.5)


def test_faststart_puts_metadata_first(produced: dict) -> None:
    head = Path(produced["video"]).read_bytes()[:4096]
    assert head.find(b"moov") != -1 and head.find(b"moov") < max(head.find(b"mdat"), 4096)


def test_captions_use_real_scene_times(produced: dict) -> None:
    vtt = Path(produced["captions"]).read_text(encoding="utf-8")
    assert vtt.startswith("WEBVTT") and vtt.count("-->") == 6
    assert "00:00:06.500 --> 00:00:13.000" in vtt and "00:00:39.000" in vtt


def test_graphic_appears_on_its_word(produced: dict, tmp_path: Path) -> None:
    """«informes» es la palabra 5 del bloque 02: 6,5 + 2,5 = 9,0 s; ahí aparece el icono."""
    video = Path(produced["video"])
    before = Image.open(_frame(video, 8.7, tmp_path / "antes.png")).convert("RGB")
    during = Image.open(_frame(video, 9.6, tmp_path / "durante.png")).convert("RGB")
    box = (440, 380, 640, 580)  # alrededor de (0,5; 0,25) del cuadro
    diff = ImageStat.Stat(ImageChops.difference(before.crop(box), during.crop(box))).mean
    assert sum(diff) / 3 > 40
    red, green, blue = ImageStat.Stat(during.crop((500, 440, 580, 520))).mean
    assert red > 200 and green > 170 and blue < 80  # amarillo del icono
    cue = next(c for c in produced["cues"] if c["id"] == "p.informes")
    assert cue["word_s"] == pytest.approx(9.0) and cue["delta_s"] == 0.0


def test_shots_are_split_and_retimed(produced: dict) -> None:
    """03a cubre hasta «cinco» (4,5 s); su ancla de 3,15 s cae sobre «agente» (3,5 s): 0,9×."""
    retime = {r["shot"]: r["factors"] for r in produced["retime"]}
    assert retime["plano-03a"] == [0.9, 1.0]
    assert retime["plano-03b"] == [1.0]
    assert len(retime) == 7


# --------------------------------------------------------------------------- reglas del montaje


def test_assemble_refuses_unapproved_shots(produced: dict, tmp_path: Path) -> None:
    root = produced["root"]
    original = (root / "escenas.json").read_text(encoding="utf-8")
    register = json.loads(original)
    register["scenes"][2]["shots"][1]["status"] = "generada"
    (root / "escenas.json").write_text(json.dumps(register), encoding="utf-8")
    try:
        with pytest.raises(pitch.PitchError, match="plano-03b"):
            pitch.assemble(
                root, tmp_path / "x.mp4", gold_dir=produced["gold"], reference=produced["reference"]
            )
    finally:
        (root / "escenas.json").write_text(original, encoding="utf-8")


def test_assemble_refuses_a_stale_sync(produced: dict, tmp_path: Path) -> None:
    root = produced["root"]
    wav = root / "narracion" / "bloque-04.wav"
    original = wav.read_bytes()
    _ffmpeg("-f", "lavfi", "-i", "sine=frequency=440:duration=5", "-c:a", "pcm_s16le", str(wav))
    try:
        with pytest.raises(pitch.PitchError, match="diferencia cambió"):
            pitch.assemble(
                root, tmp_path / "x.mp4", gold_dir=produced["gold"], reference=produced["reference"]
            )
    finally:
        wav.write_bytes(original)


def test_retime_out_of_range_is_reported(produced: dict, tmp_path: Path) -> None:
    root = produced["root"]
    original = (root / "escenas.json").read_text(encoding="utf-8")
    register = json.loads(original)
    register["scenes"][2]["shots"][0]["review"]["anchors"] = {"s.agente": 1.0}
    (root / "escenas.json").write_text(json.dumps(register), encoding="utf-8")
    try:
        with pytest.raises(pitch.PitchError, match=r"plano-03a.*límite"):
            pitch.assemble(
                root, tmp_path / "x.mp4", gold_dir=produced["gold"], reference=produced["reference"]
            )
    finally:
        (root / "escenas.json").write_text(original, encoding="utf-8")


# --------------------------------------------------------------------------- publicación (T034)


def test_publish_copies_the_draft_and_regenerates_web_data(
    produced: dict, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = produced["root"]
    old = root / "escenas"
    old.mkdir(exist_ok=True)
    (old / "escena-01.mp4").write_bytes(b"v1")
    media = tmp_path / "media"
    web_data = tmp_path / "pitch.ts"
    result = pitch.publish(
        root,
        media_dir=media,
        web_data=web_data,
        gold_dir=produced["gold"],
        reference=produced["reference"],
    )
    for name in (pitch.VIDEO_NAME, pitch.CAPTIONS_NAME, pitch.POSTER_NAME):
        assert (media / name).is_file()
    assert (media / pitch.VIDEO_NAME).read_bytes() == Path(produced["video"]).read_bytes()
    assert 'PITCH_SCRIPT_VERSION = "1.2.0"' in web_data.read_text(encoding="utf-8")
    transcript = (root / "transcripcion.md").read_text(encoding="utf-8")
    assert pitch.DISCLAIMER in transcript and "1864" in transcript
    assert any(path.endswith("escena-01.mp4") for path in result["remove_v1"])


def test_publish_refuses_unapproved_shots_and_keeps_v1(produced: dict, tmp_path: Path) -> None:
    root = produced["root"]
    media = tmp_path / "media"
    media.mkdir()
    (media / pitch.VIDEO_NAME).write_bytes(b"v1")
    original = (root / "escenas.json").read_text(encoding="utf-8")
    register = json.loads(original)
    register["scenes"][0]["shots"][0]["status"] = "descartada"
    (root / "escenas.json").write_text(json.dumps(register), encoding="utf-8")
    try:
        with pytest.raises(pitch.PitchError, match="sin aprobar"):
            pitch.publish(
                root,
                media_dir=media,
                web_data=tmp_path / "pitch.ts",
                gold_dir=produced["gold"],
                reference=produced["reference"],
            )
    finally:
        (root / "escenas.json").write_text(original, encoding="utf-8")
    assert (media / pitch.VIDEO_NAME).read_bytes() == b"v1"
    assert not (tmp_path / "pitch.ts").exists()
