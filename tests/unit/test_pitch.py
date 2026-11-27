"""Producción del video pitch (specs 028 y 029): guion, momentos, planos, narración y chequeos.

Sin red, sin modelo de video y sin voz real: unidades de oro, imagen y motor de voz falsos en
``tmp_path``.
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
    "accion": "Conocer Manuelita ya no es buscar: es preguntar. Entra y haz tu primera pregunta.",
}
UNITS = {
    "unit_1864": "Lo que inició como un trapiche para producir azúcar en 1864 es hoy el ingenio.",
    "unit_plataformas": "Cuatro plataformas: caña de azúcar, palma, acuicultura y frutas.",
}
REVIEW = {
    "by": "Roberto",
    "at": "2026-11-26",
    "likeness": True,
    "no_text": True,
    "no_brand": True,
    "matches_script": True,
    "cue_shown": True,
}


def _toml_table(header: str, values: dict) -> str:
    lines = [header]
    for key, value in values.items():
        if isinstance(value, bool):
            lines.append(f"{key} = {'true' if value else 'false'}")
        else:
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    return "\n".join(lines) + "\n"


def write_script(
    root: Path,
    overrides: dict[str, dict] | None = None,
    cues: dict[str, list[dict]] | None = None,
    **head: object,
) -> None:
    overrides = overrides or {}
    cues = cues or {}
    header = {"version": "1.2.0", "language": "es", "max_seconds": 57, "pause_s": 0.5, **head}
    text = "".join(f"{k} = {json.dumps(v, ensure_ascii=False)}\n" for k, v in header.items())
    defaults = {
        "gancho": {"claims": ["unit_1864"]},
        "problema": {"claims": ["unit_plataformas"]},
        "uso": {"synthetic": True},
    }
    for block_id, narration in BLOCKS.items():
        extra = {**defaults.get(block_id, {}), **overrides.get(block_id, {})}
        narration = extra.pop("narration", narration)
        if extra.pop("drop", False):
            continue
        text += "\n" + _toml_table("[[block]]", {"id": block_id, "narration": narration, **extra})
        for cue in cues.get(block_id, []):
            text += _toml_table("[[block.cue]]", cue)
    (root / "guion.toml").write_text(text, encoding="utf-8")


def default_shots() -> dict[str, list[dict]]:
    return {f"escena-{i:02d}": [{"id": f"plano-{i:02d}"}] for i in range(1, 7)}


def write_register(
    root: Path,
    shots: dict[str, list[dict]] | None = None,
    raw: object | None = None,
    **head: object,
) -> dict:
    """``escenas.json`` esquema 2; ``shots`` da por escena la lista de planos (con cambios)."""
    if raw is not None:
        (root / "escenas.json").write_text(json.dumps(raw), encoding="utf-8")
        return {}
    shots = shots or default_shots()
    scenes = []
    seed = 3000
    for index, block_id in enumerate(BLOCKS, start=1):
        scene_id = f"escena-{index:02d}"
        items = []
        for change in shots.get(scene_id, []):
            seed += 1
            shot_id = change["id"]
            prompt = root / "prompts" / f"{shot_id}.json"
            prompt.parent.mkdir(parents=True, exist_ok=True)
            prompt.write_text('{"subject": "campo de caña"}', encoding="utf-8")
            items.append(
                {
                    "mode": "image",
                    "source": "reference",
                    "prompt_file": f"prompts/{shot_id}.json",
                    "seed": seed,
                    "request_seconds": 10,
                    "model": None,
                    "job": None,
                    "history": [],
                    "generated_at": None,
                    "clip": None,
                    "duration_s": None,
                    "status": "pendiente",
                    "review": None,
                    **change,
                }
            )
        scenes.append({"id": scene_id, "block": block_id, "shots": items})
    register = {
        "schema": 2,
        "model": None,
        "image": "referencia.png",
        "prior_spent_usd": 0.0,
        "scenes": scenes,
        **head,
    }
    (root / "escenas.json").write_text(json.dumps(register, ensure_ascii=False), encoding="utf-8")
    return register


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


def write_svg(root: Path, name: str) -> None:
    folder = root / "graficos"
    folder.mkdir(exist_ok=True)
    (folder / f"{name}.svg").write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', encoding="utf-8"
    )


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
    write_register(root)
    reference = write_reference(root)
    return {"root": root, "gold": gold, "reference": reference}


def run_validate(project: dict[str, Path]) -> pitch.ValidationReport:
    return pitch.validate(project["root"], gold_dir=project["gold"], reference=project["reference"])


def errors_of(project: dict[str, Path]) -> str:
    return " ".join(run_validate(project).errors)


# --------------------------------------------------------------------------- guion


def test_valid_project_passes(project: dict[str, Path]) -> None:
    report = run_validate(project)
    assert report.ok, report.errors
    assert report.blocks == 6 and report.max_seconds == 57 and report.claims == 2
    assert report.shots == 6 and report.cues == 0
    assert report.reference == {"confirmed": True, "sha256_matches": True}


def test_blocks_must_be_six_in_order(project: dict[str, Path]) -> None:
    write_script(project["root"], {"accion": {"drop": True}})
    assert "6 bloques" in errors_of(project)


def test_language_and_duration_limits(project: dict[str, Path]) -> None:
    write_script(project["root"], language="en", max_seconds=75)
    errors = errors_of(project)
    assert "español" in errors and "60" in errors


def test_narration_word_limit(project: dict[str, Path]) -> None:
    long_text = " ".join(["palabra"] * 41)
    write_script(project["root"], {"solucion": {"narration": long_text}})
    assert "40 palabras" in errors_of(project)


@pytest.mark.parametrize("pause", [0.2, 0.9])
def test_pause_must_be_between_limits(project: dict[str, Path], pause: float) -> None:
    """FR-009: la pausa tras cada narración va de 0,3 a 0,8 s."""
    write_script(project["root"], pause_s=pause)
    assert "pause_s" in errors_of(project)


def test_numbered_steps_on_screen_are_rejected(project: dict[str, Path]) -> None:
    """FR-004: los pasos «1 Perfil · 2 Pregunta…» se reemplazan por la vista de perfiles."""
    on_screen = "1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación"
    write_script(project["root"], {"uso": {"on_screen": on_screen}})
    assert "FR-004" in errors_of(project)


def test_missing_unit_is_reported(project: dict[str, Path]) -> None:
    write_script(project["root"], {"gancho": {"claims": ["unit_inventada"]}})
    report = run_validate(project)
    assert not report.ok and report.missing_units == ["unit_inventada"]


def test_number_without_source_is_rejected(project: dict[str, Path]) -> None:
    """FR-004 de la 028, SC-003: una cifra solo entra si está en el texto de sus unidades."""
    narration = "Manuelita vende 600 millones al año y nació en 1864."
    write_script(project["root"], {"gancho": {"narration": narration}})
    report = run_validate(project)
    assert report.unsupported_numbers == [{"block": "gancho", "number": "600"}]


def test_planning_requires_synthetic_label(project: dict[str, Path]) -> None:
    narration = "Elige tu perfil, haz tu pregunta, revisa las fuentes y abre la planificación."
    write_script(project["root"], {"uso": {"narration": narration}})
    assert "datos sintéticos" in errors_of(project)


def test_use_block_names_the_four_steps(project: dict[str, Path]) -> None:
    write_script(project["root"], {"uso": {"narration": "Entra y pregunta."}})
    errors = errors_of(project)
    assert "perfil" in errors and "fuentes" in errors


# --------------------------------------------------------------------------- momentos (T005)


def test_valid_cues_pass(project: dict[str, Path]) -> None:
    write_svg(project["root"], "icono-informes")
    cues = {
        "problema": [
            {
                "id": "problema.informes",
                "word": "informes",
                "kind": "grafico",
                "graphic": "icono-informes",
                "from": [0.1, 0.2],
                "to": [0.5, 0.6],
                "hold_s": 1.3,
            }
        ],
        "gancho": [{"id": "gancho.valeria", "word": "Valer", "kind": "plano", "shot": "plano-01"}],
    }
    write_script(project["root"], cues=cues)
    report = run_validate(project)
    assert report.ok, report.errors
    assert report.cues == 2
    script = pitch.load_script(project["root"])
    cue = script.block("problema").cues[0]
    assert cue.from_xy == (0.1, 0.2) and cue.to_xy == (0.5, 0.6) and cue.hold_s == 1.3


@pytest.mark.parametrize(
    ("cue", "message"),
    [
        ({"id": "a", "word": "inexistente", "kind": "grafico", "graphic": "x"}, "no está en"),
        ({"id": "a", "word": "informes", "kind": "otro"}, "kind"),
        ({"id": "a", "word": "informes", "kind": "plano"}, "necesita shot"),
        ({"id": "a", "word": "informes", "kind": "grafico"}, "necesita graphic"),
        ({"id": "a", "word": "informes", "kind": "grafico", "graphic": "falta"}, "falta.svg"),
        (
            {"id": "a", "word": "informes", "kind": "grafico", "graphic": "ok", "from": [1.2, 0]},
            "entre 0 y 1",
        ),
        ({"id": "a", "word": "informes", "kind": "plano", "shot": "plano-05"}, "no es de"),
    ],
)
def test_cue_rules(project: dict[str, Path], cue: dict, message: str) -> None:
    write_svg(project["root"], "ok")
    write_script(project["root"], cues={"problema": [cue]})
    assert message in errors_of(project)


def test_cue_ids_are_unique(project: dict[str, Path]) -> None:
    write_svg(project["root"], "ok")
    cue = {"id": "dup", "word": "informes", "kind": "grafico", "graphic": "ok"}
    write_script(project["root"], cues={"problema": [cue, cue]})
    assert "id único" in errors_of(project)


def test_cue_with_manual_time_skips_the_word_check(project: dict[str, Path]) -> None:
    write_svg(project["root"], "ok")
    cue = {"id": "a", "word": "nada", "kind": "grafico", "graphic": "ok", "at_s": 2.0}
    write_script(project["root"], cues={"problema": [cue]})
    assert run_validate(project).ok


# --------------------------------------------------------------------------- registro (T006)


def test_v1_register_is_rejected(project: dict[str, Path]) -> None:
    write_register(project["root"], raw=[{"id": "escena-01"}])
    assert "v1" in errors_of(project)


@pytest.mark.parametrize(
    ("change", "message"),
    [
        ({"id": "plano-07"}, "el id debe ser"),
        ({"mode": "video"}, "mode debe ser"),
        ({"mode": "text", "source": "reference"}, "no lleva source"),
        ({"mode": "reference", "source": None}, 'source = "reference"'),
        ({"mode": "image", "source": "frame:plano-06"}, "plano anterior"),
        ({"request_seconds": 2}, "request_seconds"),
        ({"request_seconds": 31}, "request_seconds"),
        ({"status": "rara"}, "estado"),
        ({"seed": "x"}, "seed"),
        ({"status": "aprobada", "review": {"likeness": True}}, "revisión completa"),
        ({"model": "kling4"}, "modelo magi2"),
    ],
)
def test_shot_rules(project: dict[str, Path], change: dict, message: str) -> None:
    shots = default_shots()
    shots["escena-02"] = [{"id": "plano-02", **change}]
    write_register(project["root"], shots, model="magi2")
    assert message in errors_of(project)


def test_frame_source_and_starts_at(project: dict[str, Path]) -> None:
    write_script(
        project["root"],
        cues={
            "solucion": [{"id": "s.cinco", "word": "cinco", "kind": "plano", "shot": "plano-03b"}]
        },
    )
    shots = default_shots()
    shots["escena-03"] = [
        {"id": "plano-03a", "mode": "reference"},
        {"id": "plano-03b", "source": "frame:plano-03a", "starts_at": "s.cinco"},
    ]
    shots["escena-06"] = [{"id": "plano-06", "source": "frame:plano-03a"}]
    write_register(project["root"], shots)
    assert run_validate(project).ok, run_validate(project).errors
    shots["escena-03"][1].pop("starts_at")
    write_register(project["root"], shots)
    assert "starts_at" in errors_of(project)
    shots["escena-03"][1]["starts_at"] = "s.cinco"
    shots["escena-03"][0]["starts_at"] = "s.cinco"
    write_register(project["root"], shots)
    assert "primer plano" in errors_of(project)


def test_seeds_are_unique(project: dict[str, Path]) -> None:
    shots = default_shots()
    shots["escena-01"] = [{"id": "plano-01", "seed": 7}]
    shots["escena-02"] = [{"id": "plano-02", "seed": 7}]
    write_register(project["root"], shots)
    assert "semilla 7" in errors_of(project)


def test_every_scene_needs_a_shot(project: dict[str, Path]) -> None:
    shots = default_shots()
    shots["escena-04"] = []
    write_register(project["root"], shots)
    assert "al menos un plano" in errors_of(project)


def test_approved_shot_needs_anchors_for_its_plano_cues(project: dict[str, Path]) -> None:
    cue = {"id": "g.valer", "word": "Valer", "kind": "plano", "shot": "plano-01"}
    write_script(project["root"], cues={"gancho": [cue]})
    script = pitch.load_script(project["root"])
    review = {**REVIEW, "block_hash": pitch.block_hash(script.block("gancho"))}
    shots = default_shots()
    shots["escena-01"] = [{"id": "plano-01", "status": "aprobada", "review": review}]
    write_register(project["root"], shots)
    assert "anclas" in errors_of(project)
    shots["escena-01"][0]["review"] = {**review, "anchors": {"g.valer": 0.4}}
    write_register(project["root"], shots)
    assert run_validate(project).ok


def test_changed_block_marks_approved_shot_stale(project: dict[str, Path]) -> None:
    """SC-007 de la 028: si cambia el texto de su bloque, el plano aprobado queda desactualizado."""
    script = pitch.load_script(project["root"])
    review = {**REVIEW, "block_hash": pitch.block_hash(script.block("solucion"))}
    shots = default_shots()
    shots["escena-03"] = [{"id": "plano-03", "status": "aprobada", "review": review}]
    write_register(project["root"], shots)
    assert run_validate(project).ok
    write_script(project["root"], {"solucion": {"narration": "Un texto distinto para la escena."}})
    report = run_validate(project)
    assert report.stale_shots == ["plano-03"] and not report.ok


@pytest.mark.parametrize("status", ["generando", "generada", "error", "descartada"])
def test_generation_statuses_are_valid(project: dict[str, Path], status: str) -> None:
    shots = default_shots()
    shots["escena-02"] = [{"id": "plano-02", "status": status}]
    write_register(project["root"], shots)
    assert run_validate(project).ok


def test_scene_status_is_derived_from_its_shots() -> None:
    approved = {"status": "aprobada"}
    assert pitch.scene_status({"shots": [approved, approved]}) == "aprobada"
    assert pitch.scene_status({"shots": [approved, {"status": "generada"}]}) == "generada"
    assert pitch.scene_status({"shots": [approved, {"status": "error"}]}) == "error"


def test_reference_sheet_must_be_confirmed(project: dict[str, Path]) -> None:
    write_reference(project["root"], real_person='""', confirmed_by='""')
    report = run_validate(project)
    assert not report.ok and report.reference["confirmed"] is False


def test_reference_hash_must_match(project: dict[str, Path]) -> None:
    (project["root"] / "referencia.png").write_bytes(b"otra imagen")
    assert run_validate(project).reference["sha256_matches"] is False


# --------------------------------------------------------------------------- CLI


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


# --------------------------------------------------------------------------- pesos abiertos


def test_export_samples_uses_image_shots_from_the_reference(project: dict[str, Path]) -> None:
    shots = default_shots()
    shots["escena-01"] = [{"id": "plano-01", "mode": "text", "source": None}]
    write_register(project["root"], shots)
    kw = {"gold_dir": project["gold"], "reference": project["reference"]}
    samples = pitch.export_samples(project["root"], **kw)
    assert len(samples) == 5 and set(samples[0]) == {"prompt_file", "image"}
    assert samples[0]["image"] == "referencia.png"
    one = pitch.export_samples(project["root"], "plano-03", **kw)
    assert len(one) == 1 and one[0]["prompt_file"].endswith("plano-03.json")


def test_export_samples_fails_when_invalid(project: dict[str, Path]) -> None:
    write_reference(project["root"], real_person="true")
    with pytest.raises(pitch.PitchError, match="validación"):
        pitch.export_samples(
            project["root"], gold_dir=project["gold"], reference=project["reference"]
        )


def test_seed_of_a_shot_is_reproducible(project: dict[str, Path]) -> None:
    assert pitch.shot_seed(project["root"], "plano-03") == 3003


# --------------------------------------------------------------------------- narración (T026)


@dataclass
class FakeSynth:
    samples: np.ndarray
    sample_rate: int


class FakeVoice:
    def __init__(self, seconds: float | dict[str, float] = 6.0) -> None:
        self.seconds = seconds
        self.texts: list[str] = []

    def synthesize(self, text: str, voice: str | None = None) -> FakeSynth:
        self.texts.append(text)
        rate = 16_000
        seconds = self.seconds
        if isinstance(seconds, dict):
            seconds = next((v for k, v in seconds.items() if text.startswith(k)), 6.0)
        return FakeSynth(np.zeros(int(rate * seconds), dtype=np.float32), rate)


def test_narrate_writes_one_wav_per_block(project: dict[str, Path]) -> None:
    voice = FakeVoice(6.0)
    result = pitch.narrate(project["root"], engine=voice)
    files = sorted((project["root"] / "narracion").glob("bloque-*.wav"))
    assert [f.name for f in files] == [f"bloque-0{i}.wav" for i in range(1, 7)]
    assert all(abs(item["seconds"] - 6.0) < 0.01 for item in result)
    assert voice.texts[0].startswith("Manuelita nació en 1864")


def test_a_long_block_is_fine_if_the_total_fits(project: dict[str, Path]) -> None:
    """R4: ya no hay tope de 9,5 s por escena; manda el total."""
    result = pitch.narrate(project["root"], engine=FakeVoice({"Valer-IA reúne": 12.6}))
    assert max(item["seconds"] for item in result) > 12


def test_narrate_fails_when_the_total_is_too_long(project: dict[str, Path]) -> None:
    with pytest.raises(pitch.PitchError, match="recorta el bloque solucion"):
        pitch.narrate(project["root"], engine=FakeVoice({"Valer-IA reúne": 30.0, "": 6.0}))
    assert not (project["root"] / "narracion").exists()


def test_narrate_one_block(project: dict[str, Path]) -> None:
    voice = FakeVoice(5.0)
    pitch.narrate(project["root"], engine=voice, block="uso")
    assert len(voice.texts) == 1 and (project["root"] / "narracion" / "bloque-05.wav").is_file()


# --------------------------------------------------------------------------- comprobación (T027)


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


def _montage(gaps: list[float], deltas: list[float]) -> dict:
    return {
        "scenes": [{"scene_s": 6 + gap, "narration_s": 6} for gap in gaps],
        "cues": [{"id": f"c{i}", "delta_s": d} for i, d in enumerate(deltas)],
    }


@pytest.mark.parametrize(
    ("gaps", "deltas", "failing"),
    [
        ([0.5] * 6, [0.0] * 10, set()),
        ([0.5, 1.0, 0.5, 0.5, 0.5, 0.5], [0.0] * 10, {"pauses"}),
        ([0.5] * 6, [0.0] * 8 + [0.7, 0.9], {"cues"}),
        ([0.5] * 6, [0.0] * 9 + [0.7], set()),
        ([0.5] * 6, [0.0] * 9 + [-0.1], {"cues"}),
    ],
)
def test_check_pauses_and_cues(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    gaps: list[float],
    deltas: list[float],
    failing: set[str],
) -> None:
    """SC-002 (≥ 90 % a ±0,5 s y ninguno antes de su palabra) y SC-003 (pausas ≤ 0,8 s)."""
    video = tmp_path / "pitch.mp4"
    video.write_bytes(b"0")
    vtt = tmp_path / "pitch.es.vtt"
    vtt.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:57.000\nhola\n", encoding="utf-8")
    monkeypatch.setattr(pitch, "ffprobe", lambda path: _probe(57.0))
    report = pitch.check(video, vtt, montage=_montage(gaps, deltas))
    assert {name for name, item in report["checks"].items() if not item["ok"]} == failing


def test_check_flags_numbered_steps(project: dict[str, Path], tmp_path: Path, monkeypatch) -> None:
    write_script(project["root"], {"uso": {"on_screen": "1 Perfil · 2 Pregunta"}})
    video = tmp_path / "pitch.mp4"
    video.write_bytes(b"0")
    monkeypatch.setattr(pitch, "ffprobe", lambda path: _probe(57.0))
    report = pitch.check(video, script=pitch.load_script(project["root"]))
    assert report["checks"]["no_steps_text"] == {"ok": False, "value": ["uso"]}


# --------------------------------------------------------------------------- datos del repositorio


def test_web_data_matches_the_published_script() -> None:
    """La transcripción de la web se genera desde el guion publicado y no diverge.

    Mientras la v2 no se publique (FR-022), la web conserva los datos de la v1.
    """
    actual = (pitch.PROJECT_ROOT / "web" / "src" / "data" / "pitch.ts").read_text(encoding="utf-8")
    script = pitch.load_script(pitch.PITCH_ROOT)
    if f'PITCH_SCRIPT_VERSION = "{script.version}"' in actual:
        assert actual.replace("\r\n", "\n") == pitch.render_web_data(script)
    else:
        assert 'PITCH_SCRIPT_VERSION = "1.1.0"' in actual


def test_repository_pitch_is_valid() -> None:
    """El guion 1.2.0 y el registro v2 del repositorio validan sin errores."""
    report = pitch.validate(pitch.PITCH_ROOT)
    assert report.errors == []
    assert report.shots == 8 and report.cues == 23


def test_events_can_replace_anchors(project: dict[str, Path]) -> None:
    cue = {"id": "g.valer", "word": "Valer", "kind": "plano", "shot": "plano-01"}
    write_script(project["root"], cues={"gancho": [cue]})
    script = pitch.load_script(project["root"])
    review = {**REVIEW, "block_hash": pitch.block_hash(script.block("gancho"))}
    shots = default_shots()
    shots["escena-01"] = [
        {"id": "plano-01", "status": "aprobada", "review": {**review, "events": {"g.valer": 1.0}}}
    ]
    write_register(project["root"], shots)
    assert run_validate(project).ok


def test_check_tolerates_only_accepted_early_cues(tmp_path: Path, monkeypatch) -> None:
    video = tmp_path / "pitch.mp4"
    video.write_bytes(b"0")
    vtt = tmp_path / "pitch.es.vtt"
    vtt.write_text("WEBVTT\n\n00:00:00.000 --> 00:00:57.000\nhola\n", encoding="utf-8")
    monkeypatch.setattr(pitch, "ffprobe", lambda path: _probe(57.0))
    montage = _montage([0.5] * 6, [0.0] * 19)
    montage["cues"].append({"id": "tarde", "delta_s": 1.1, "accepted": True})
    montage["cues"].append({"id": "temprano", "delta_s": -0.9, "accepted": True})
    report = pitch.check(video, vtt, montage=montage)
    assert report["checks"]["cues"]["ok"] is True
    assert report["checks"]["cues"]["outside"] == ["tarde", "temprano"]
    montage["cues"][-1]["accepted"] = False
    assert pitch.check(video, vtt, montage=montage)["checks"]["cues"]["ok"] is False
