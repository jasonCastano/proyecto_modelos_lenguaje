"""Producción del video pitch (spec 028): guion con fuentes, escenas, narración y chequeos.

Sin red, sin MAGI-2 y sin voz real: unidades de oro, imagen y motor de voz falsos en ``tmp_path``.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pytest

from proyecto_modelos_lenguaje import pitch

BLOCKS = {
    "gancho": "Manuelita nació en 1864 como un trapiche de caña. Valer-IA te ayuda a conocerla.",
    "problema": "Su información está repartida en informes y páginas de cuatro plataformas.",
    "solucion": "Valer-IA reúne esa información pública en un solo agente para cinco públicos.",
    "diferencia": "Cita cada fuente, calcula las cifras en código y pide un sí antes de guardar.",
    "uso": "Elige tu perfil, pregunta y revisa las fuentes. Si planificas, usa datos sintéticos.",
    "accion": "Proyecto académico, no canal oficial de Manuelita. Entra y empieza a preguntar.",
}
UNITS = {
    "unit_1864": "Lo que inició como un trapiche para producir azúcar en 1864 es hoy el ingenio.",
    "unit_plataformas": "Cuatro plataformas: caña de azúcar, palma, acuicultura y frutas.",
}


def _toml_block(block_id: str, narration: str, **extra: object) -> str:
    lines = ["[[block]]", f'id = "{block_id}"', f'narration = "{narration}"']
    for key, value in extra.items():
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        elif isinstance(value, list):
            lines.append(f"{key} = [{', '.join(json.dumps(v) for v in value)}]")
        else:
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def write_script(root: Path, overrides: dict[str, dict] | None = None, **head: object) -> None:
    overrides = overrides or {}
    header = {"version": "1.0.0", "language": "es", "max_seconds": 57, **head}
    text = "".join(f"{k} = {json.dumps(v, ensure_ascii=False)}\n" for k, v in header.items())
    defaults = {
        "gancho": {"claims": ["unit_1864"]},
        "problema": {"claims": ["unit_plataformas"]},
        "uso": {
            "on_screen": "1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación",
            "synthetic": True,
        },
    }
    for block_id, narration in BLOCKS.items():
        extra = {**defaults.get(block_id, {}), **overrides.get(block_id, {})}
        narration = extra.pop("narration", narration)
        if extra.pop("drop", False):
            continue
        text += "\n" + _toml_block(block_id, narration, **extra)
    (root / "guion.toml").write_text(text, encoding="utf-8")


def write_scenes(root: Path, **changes: dict) -> list[dict]:
    scenes = []
    for index, block_id in enumerate(BLOCKS, start=1):
        scene_id = f"escena-{index:02d}"
        prompt = root / "prompts" / f"{scene_id}.json"
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text('{"scene": "campo de caña"}', encoding="utf-8")
        scene = {
            "id": scene_id,
            "block": block_id,
            "prompt_file": f"prompts/{scene_id}.json",
            "image": "referencia.png",
            "seed": 2025 + index,
            "model": "sand-ai/MAGI-2-preview",
            "model_revision": None,
            "resolution": "1080x1920",
            "generated_at": None,
            "clip": None,
            "duration_s": None,
            "trim_s": 9.5,
            "status": "pendiente",
            "review": None,
        }
        scene.update(changes.get(scene_id, {}))
        scenes.append(scene)
    (root / "escenas.json").write_text(json.dumps(scenes, ensure_ascii=False), encoding="utf-8")
    return scenes


def write_reference(root: Path, **fields: str) -> Path:
    image = root / "referencia.png"
    image.write_bytes(b"\x89PNG fake")
    meta = {
        "file": "referencia.png",
        "sha256": hashlib.sha256(image.read_bytes()).hexdigest(),
        "origin": '"generada con IA, 2026-11"',
        "rights": '"uso del equipo"',
        "real_person": "false",
        "brand_elements": "false",
        "confirmed_by": '"Roberto"',
        **fields,
    }
    sheet = root / "referencia.md"
    body = "\n".join(f"{key}: {value}" for key, value in meta.items())
    sheet.write_text(f"---\n{body}\n---\n\n# Ficha\n", encoding="utf-8")
    return sheet


@pytest.fixture
def project(tmp_path: Path) -> dict[str, Path]:
    root = tmp_path / "pitch"
    root.mkdir()
    gold = tmp_path / "gold"
    gold.mkdir()
    rows = [{"unit_id": key, "text": text} for key, text in UNITS.items()]
    (gold / "knowledge_units.jsonl").write_text(
        "\n".join(json.dumps(r, ensure_ascii=False) for r in rows) + "\n", encoding="utf-8"
    )
    write_script(root)
    write_scenes(root)
    reference = write_reference(root)
    return {"root": root, "gold": gold, "reference": reference}


def run_validate(project: dict[str, Path]) -> pitch.ValidationReport:
    return pitch.validate(project["root"], gold_dir=project["gold"], reference=project["reference"])


# --------------------------------------------------------------------------- validación (T004)


def test_valid_project_passes(project: dict[str, Path]) -> None:
    report = run_validate(project)
    assert report.ok, report.errors
    assert report.blocks == 6 and report.max_seconds == 57 and report.claims == 2
    assert report.reference == {"confirmed": True, "sha256_matches": True}


def test_blocks_must_be_six_in_order(project: dict[str, Path]) -> None:
    write_script(project["root"], {"accion": {"drop": True}})
    assert any("6 bloques" in e for e in run_validate(project).errors)


def test_language_and_duration_limits(project: dict[str, Path]) -> None:
    write_script(project["root"], language="en", max_seconds=75)
    errors = " ".join(run_validate(project).errors)
    assert "español" in errors and "60" in errors


def test_narration_word_limit(project: dict[str, Path]) -> None:
    long_text = " ".join(["palabra"] * 23)
    write_script(project["root"], {"solucion": {"narration": long_text}})
    assert any("22 palabras" in e for e in run_validate(project).errors)


def test_missing_unit_is_reported(project: dict[str, Path]) -> None:
    write_script(project["root"], {"gancho": {"claims": ["unit_inventada"]}})
    report = run_validate(project)
    assert not report.ok and report.missing_units == ["unit_inventada"]


def test_number_without_source_is_rejected(project: dict[str, Path]) -> None:
    """FR-004, SC-003: una cifra solo entra si está en el texto de sus unidades."""
    narration = "Manuelita vende 600 millones al año y nació en 1864."
    write_script(project["root"], {"gancho": {"narration": narration}})
    report = run_validate(project)
    assert report.unsupported_numbers == [{"block": "gancho", "number": "600"}]


def test_planning_requires_synthetic_label(project: dict[str, Path]) -> None:
    narration = "Elige tu perfil, haz tu pregunta, revisa las fuentes y abre la planificación."
    write_script(project["root"], {"uso": {"narration": narration}})
    assert any("datos sintéticos" in e for e in run_validate(project).errors)


def test_use_block_names_the_four_steps(project: dict[str, Path]) -> None:
    write_script(project["root"], {"uso": {"narration": "Entra y pregunta.", "on_screen": ""}})
    assert any("perfil" in e and "fuentes" in e for e in run_validate(project).errors)


def test_scene_manifest_rules(project: dict[str, Path]) -> None:
    write_scenes(
        project["root"],
        **{
            "escena-02": {"trim_s": 10},
            "escena-03": {"resolution": "1920x1088"},
            "escena-04": {"model": "otro"},
            "escena-05": {"status": "lista"},
            "escena-06": {"status": "aprobada", "review": {"likeness": True}},
        },
    )
    errors = " ".join(run_validate(project).errors)
    for fragment in ("9.5", "1080x1920", "MAGI-2", "estado", "revisión"):
        assert fragment in errors


def test_reference_sheet_must_be_confirmed(project: dict[str, Path]) -> None:
    write_reference(project["root"], real_person='""', confirmed_by='""')
    report = run_validate(project)
    assert not report.ok and report.reference["confirmed"] is False


def test_reference_hash_must_match(project: dict[str, Path]) -> None:
    (project["root"] / "referencia.png").write_bytes(b"otra imagen")
    assert run_validate(project).reference["sha256_matches"] is False


# --------------------------------------------------------------------------- CLI (T006)


def test_cli_validate_json(project: dict[str, Path], capsys: pytest.CaptureFixture[str]) -> None:
    from proyecto_modelos_lenguaje.cli import main

    args = [
        "pitch",
        "validate",
        "--root",
        str(project["root"]),
        "--gold",
        str(project["gold"]),
        "--reference",
        str(project["reference"]),
        "--json",
    ]
    assert main(args) == 0
    assert json.loads(capsys.readouterr().out)["ok"] is True
    write_script(project["root"], {"gancho": {"claims": ["nada"]}})
    assert main(args) == 1


# --------------------------------------------------------------------------- muestras (T009, T031)


def test_export_samples_all_and_one(project: dict[str, Path]) -> None:
    samples = pitch.export_samples(
        project["root"], gold_dir=project["gold"], reference=project["reference"]
    )
    assert [s["prompt_file"].endswith(f"escena-0{i}.json") for i, s in enumerate(samples, 1)]
    assert len(samples) == 6 and set(samples[0]) == {"prompt_file", "image"}
    one = pitch.export_samples(
        project["root"], scene="escena-03", gold_dir=project["gold"], reference=project["reference"]
    )
    assert len(one) == 1 and one[0]["prompt_file"].endswith("escena-03.json")


def test_export_samples_fails_when_invalid(project: dict[str, Path]) -> None:
    write_reference(project["root"], real_person="true")
    with pytest.raises(pitch.PitchError, match="validación"):
        pitch.export_samples(
            project["root"], gold_dir=project["gold"], reference=project["reference"]
        )


def test_seed_of_a_scene_is_reproducible(project: dict[str, Path]) -> None:
    assert pitch.scene_seed(project["root"], "escena-03") == 2028


def test_changed_block_marks_approved_scene_stale(project: dict[str, Path]) -> None:
    """SC-007: si cambia el texto de su bloque, la escena aprobada queda desactualizada."""
    script = pitch.load_script(project["root"])
    review = {
        "by": "Roberto",
        "at": "2026-11-26",
        "likeness": True,
        "no_text": True,
        "no_brand": True,
        "matches_script": True,
        "block_hash": pitch.block_hash(script.block("solucion")),
    }
    write_scenes(project["root"], **{"escena-03": {"status": "aprobada", "review": review}})
    assert run_validate(project).ok
    write_script(project["root"], {"solucion": {"narration": "Un texto distinto para la escena."}})
    report = run_validate(project)
    assert report.stale_scenes == ["escena-03"] and not report.ok


# --------------------------------------------------------------------------- narración (T010)


@dataclass
class FakeSynth:
    samples: np.ndarray
    sample_rate: int


class FakeVoice:
    def __init__(self, seconds: float = 6.0) -> None:
        self.seconds = seconds
        self.texts: list[str] = []

    def synthesize(self, text: str, voice: str | None = None) -> FakeSynth:
        self.texts.append(text)
        rate = 16_000
        return FakeSynth(np.zeros(int(rate * self.seconds), dtype=np.float32), rate)


def test_narrate_writes_one_wav_per_block(project: dict[str, Path]) -> None:
    voice = FakeVoice(6.0)
    result = pitch.narrate(project["root"], engine=voice)
    files = sorted((project["root"] / "narracion").glob("bloque-*.wav"))
    assert [f.name for f in files] == [f"bloque-0{i}.wav" for i in range(1, 7)]
    assert all(abs(item["seconds"] - 6.0) < 0.01 for item in result)
    assert voice.texts[0].startswith("Manuelita nació en 1864")


def test_narrate_fails_when_a_block_is_too_long(project: dict[str, Path]) -> None:
    with pytest.raises(pitch.PitchError, match=r"9\.5"):
        pitch.narrate(project["root"], engine=FakeVoice(9.8))


def test_narrate_one_block(project: dict[str, Path]) -> None:
    voice = FakeVoice(5.0)
    pitch.narrate(project["root"], engine=voice, block="uso")
    assert len(voice.texts) == 1 and (project["root"] / "narracion" / "bloque-05.wav").is_file()


# --------------------------------------------------------------------------- comprobación (T012)


def _probe(duration: float, width: int = 1080, height: int = 1920, audio: bool = True) -> dict:
    streams = [{"codec_type": "video", "width": width, "height": height}]
    if audio:
        streams.append({"codec_type": "audio"})
    return {"format": {"duration": str(duration)}, "streams": streams}


@pytest.mark.parametrize(
    ("probe", "size_mb", "failing"),
    [
        (_probe(57.0), 18, set()),
        (_probe(61.0), 18, {"duration", "captions"}),
        (_probe(57.0, 1920, 1080), 18, {"resolution"}),
        (_probe(57.0, audio=False), 18, {"audio"}),
        (_probe(57.0), 26, {"size"}),
    ],
)
def test_check_video(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    probe: dict,
    size_mb: int,
    failing: set[str],
) -> None:
    video = tmp_path / "pitch.mp4"
    video.write_bytes(b"0" * (size_mb * 1024 * 1024))
    vtt = tmp_path / "pitch.es.vtt"
    vtt.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:57.000\nhola\n", encoding="utf-8")
    monkeypatch.setattr(pitch, "ffprobe", lambda path: probe)
    report = pitch.check(video, vtt, max_seconds=60)
    assert {name for name, item in report["checks"].items() if not item["ok"]} == failing
    assert report["ok"] is (not failing)


def test_check_vtt_must_cover_the_video(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    video = tmp_path / "pitch.mp4"
    video.write_bytes(b"0")
    vtt = tmp_path / "pitch.es.vtt"
    vtt.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:30.000\nhola\n", encoding="utf-8")
    monkeypatch.setattr(pitch, "ffprobe", lambda path: _probe(57.0))
    assert pitch.check(video, vtt)["checks"]["captions"]["ok"] is False


# --------------------------------------------------------------------------- datos de la web


def test_web_data_matches_the_script() -> None:
    """La transcripción de la web se genera desde el guion versionado y no diverge."""
    script = pitch.load_script(pitch.PITCH_ROOT)
    expected = pitch.render_web_data(script)
    actual = (pitch.PROJECT_ROOT / "web" / "src" / "data" / "pitch.ts").read_text(encoding="utf-8")
    assert actual.replace("\r\n", "\n") == expected


def test_repository_script_is_valid_except_external_confirmation() -> None:
    """El guion real tiene fuentes válidas; solo puede faltar la ficha de la imagen (T008)."""
    report = pitch.validate(pitch.PITCH_ROOT)
    others = [e for e in report.errors if "ficha" not in e and "imagen" not in e]
    assert others == [] and report.missing_units == [] and report.unsupported_numbers == []
