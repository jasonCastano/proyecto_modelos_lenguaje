"""Sincronía del pitch v2 (spec 029, T015-T016): palabras, momentos, línea de tiempo y reajuste.

Sin reconocedor real: un transcriptor falso devuelve palabras con tiempos.
"""

from __future__ import annotations

import json
import wave
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje import pitch, pitch_sync
from proyecto_modelos_lenguaje.pitch_sync import Word, find_phrase, retime
from tests.unit.test_pitch import write_register, write_script

# --------------------------------------------------------------------------- palabras


def words(text: str, step: float = 0.5) -> list[Word]:
    return [Word(w, i * step, i * step + 0.4) for i, w in enumerate(text.split())]


def test_find_phrase_by_prefix_and_without_accents() -> None:
    said = words("Para visitante, clientes y la acuicultúra del equipo de planta")
    assert find_phrase(said, "visitantes") == 0.5
    assert find_phrase(said, "acuicultura") == 2.5
    assert find_phrase(said, "equipo de planta") == 3.5
    assert find_phrase(said, "palma") is None


def test_short_words_match_exactly() -> None:
    said = words("si planificas sin dudas pide un sí")
    assert find_phrase(said, "sí") == 0.0
    assert find_phrase(said, "sí", after=0.1) == 3.0


def test_find_phrase_honors_after_and_repeated_words() -> None:
    said = words("perfil uno perfil dos")
    assert find_phrase(said, "perfil") == 0.0
    assert find_phrase(said, "perfil", after=0.0) == 0.0
    assert find_phrase(said, "perfil", after=0.1) == 1.0


def test_valer_ia_matches_how_whisper_may_write_it() -> None:
    for heard in ("Valeria te ayuda", "Valer IA te ayuda", "Valer-IA te ayuda"):
        assert find_phrase(words(heard), "Valer") == 0.0


# --------------------------------------------------------------------------- reajuste (T016)


def test_retime_without_anchors_plays_at_normal_speed() -> None:
    pieces = retime(5.0, [], 10.0, limits=(0.8, 1.25))
    assert len(pieces) == 1
    assert pieces[0].clip_start == 0 and pieces[0].clip_end == 5.0 and pieces[0].factor == 1.0


def test_retime_puts_each_anchor_on_its_word() -> None:
    """El evento a 4,2 s del clip cae a 4,0 s del tramo; el de 6,4 s cae a 6,5 s."""
    pieces = retime(8.0, [(4.0, 4.2), (6.5, 6.4)], 10.0, limits=(0.8, 1.25))
    assert [round(p.clip_start, 3) for p in pieces] == [0.2, 4.2, 6.4]
    assert [round(p.factor, 3) for p in pieces] == [1.0, 0.88, 1.0]
    assert abs(sum(p.length for p in pieces) - 8.0) < 1e-6


def test_retime_rejects_factors_out_of_range() -> None:
    with pytest.raises(pitch_sync.SyncError, match=r"plano-03a.*1\.\d+×"):
        retime(8.0, [(2.0, 2.0), (3.0, 4.0)], 10.0, limits=(0.8, 1.25), label="plano-03a")


def test_retime_slows_a_short_clip_within_limits() -> None:
    pieces = retime(6.0, [], 5.0, limits=(0.8, 1.25))
    assert round(pieces[0].factor, 3) == round(5 / 6, 3)
    with pytest.raises(pitch_sync.SyncError):
        retime(8.0, [], 5.0, limits=(0.8, 1.25))


def test_retime_requires_anchors_to_advance() -> None:
    with pytest.raises(pitch_sync.SyncError, match="avanzar"):
        retime(8.0, [(2.0, 3.0), (4.0, 2.5)], 10.0, limits=(0.5, 2.0))


# --------------------------------------------------------------------------- alineación (T015)


def write_wav(path: Path, seconds: float, rate: int = 16_000) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(path), "wb") as handle:
        handle.setnchannels(1)
        handle.setsampwidth(2)
        handle.setframerate(rate)
        handle.writeframes(b"\x00\x00" * int(rate * seconds))


CUES = {
    "problema": [
        {"id": "p.informes", "word": "informes", "kind": "grafico", "graphic": "i"},
        {"id": "p.plataformas", "word": "plataformas", "kind": "grafico", "graphic": "i"},
    ],
    "uso": [
        {"id": "u.a", "word": "perfil", "kind": "grafico", "graphic": "i"},
        {"id": "u.b", "word": "perfil", "kind": "grafico", "graphic": "i", "offset_s": 0.35},
    ],
}


@pytest.fixture
def aligned_root(tmp_path: Path) -> Path:
    root = tmp_path / "pitch"
    root.mkdir()
    write_script(root, cues=CUES)
    write_register(root)
    for i in range(1, 7):
        write_wav(root / "narracion" / f"bloque-{i:02d}.wav", 6.0)
    return root


def fake_transcriber(path: Path) -> list[Word]:
    script = pitch.load_script(path.parent.parent)
    index = int(path.stem[-2:]) - 1
    return words(script.blocks[index].narration)


def test_align_writes_the_sync_file(aligned_root: Path) -> None:
    result = pitch.align(aligned_root, transcriber=fake_transcriber)
    assert result == {"blocks": 6, "seconds": 39.0, "cues": 4, "missing": []}
    data = json.loads((aligned_root / "sincronia.json").read_text(encoding="utf-8"))
    problema = data["blocks"]["problema"]
    assert data["script_version"] == "1.2.0" and data["pause_s"] == 0.5
    assert problema["narration_s"] == 6.0 and problema["scene_s"] == 6.5
    assert problema["start_s"] == 6.5
    assert problema["cues"] == {"p.informes": 2.5, "p.plataformas": 5.0}
    assert data["blocks"]["uso"]["cues"] == {"u.a": 1.0, "u.b": 1.35}
    assert problema["words"][0] == {"w": "Su", "start": 0.0, "end": 0.4}


def test_align_fails_with_the_missing_cue(aligned_root: Path) -> None:
    def deaf(path: Path) -> list[Word]:
        return words("nada que ver")

    with pytest.raises(pitch.PitchError, match=r"p\.informes"):
        pitch.align(aligned_root, transcriber=deaf)


def test_align_uses_manual_time_when_the_word_is_missing(aligned_root: Path) -> None:
    cue = {"id": "p.x", "word": "informes", "kind": "grafico", "graphic": "i", "at_s": 3.3}
    cues = {"problema": [cue]}
    write_script(aligned_root, cues=cues)

    def deaf(path: Path) -> list[Word]:
        return words("nada que ver")

    pitch.align(aligned_root, transcriber=deaf)
    data = json.loads((aligned_root / "sincronia.json").read_text(encoding="utf-8"))
    assert data["blocks"]["problema"]["cues"] == {"p.x": 3.3}


def test_stale_sync_is_detected(aligned_root: Path) -> None:
    pitch.align(aligned_root, transcriber=fake_transcriber)
    script = pitch.load_script(aligned_root)
    paths = pitch.narration_paths(aligned_root, script)
    sync = pitch_sync.load_sync(aligned_root)
    assert pitch_sync.stale_reasons(sync, script, paths) == []
    write_wav(paths[2], 7.0)
    expected = ["la narración del bloque solucion cambió"]
    assert pitch_sync.stale_reasons(sync, script, paths) == expected


# --------------------------------------------------------------------------- línea de tiempo


def test_timeline_scenes_segments_and_graphics(aligned_root: Path) -> None:
    pitch.align(aligned_root, transcriber=fake_transcriber)
    script = pitch.load_script(aligned_root)
    register = pitch.load_register(aligned_root)
    timeline = pitch_sync.build_timeline(
        script,
        register["scenes"],
        pitch_sync.load_sync(aligned_root),
        clip_path=lambda shot: Path(f"{shot['id']}.mp4"),
        clip_duration=lambda path: 10.0,
        limits=(0.8, 1.25),
    )
    assert timeline.seconds == 39.0
    assert [s.start for s in timeline.scenes] == [0.0, 6.5, 13.0, 19.5, 26.0, 32.5]
    informes = next(g for g in timeline.graphics if g.cue == "p.informes")
    assert informes.t_in == 9.0 and informes.t_out == 13.0
    assert {c["id"]: c["word_s"] for c in timeline.cues}["u.b"] == 27.35


def test_timeline_splits_a_scene_at_starts_at(tmp_path: Path) -> None:
    root = tmp_path / "pitch"
    root.mkdir()
    cues = {
        "solucion": [
            {"id": "s.agente", "word": "agente", "kind": "plano", "shot": "plano-03a"},
            {"id": "s.cinco", "word": "cinco", "kind": "plano", "shot": "plano-03b"},
        ]
    }
    write_script(root, cues=cues)
    shots = {f"escena-{i:02d}": [{"id": f"plano-{i:02d}"}] for i in (1, 2, 4, 5, 6)}
    review = {"anchors": {"s.agente": 3.2, "s.cinco": 0.3}}
    shots["escena-03"] = [
        {"id": "plano-03a", "mode": "reference", "review": review},
        {"id": "plano-03b", "starts_at": "s.cinco", "review": review},
    ]
    write_register(root, shots)
    for i in range(1, 7):
        write_wav(root / "narracion" / f"bloque-{i:02d}.wav", 6.0)
    pitch.align(root, transcriber=fake_transcriber)
    script = pitch.load_script(root)
    timeline = pitch_sync.build_timeline(
        script,
        pitch.load_register(root)["scenes"],
        pitch_sync.load_sync(root),
        clip_path=lambda shot: Path(f"{shot['id']}.mp4"),
        clip_duration=lambda path: 10.0,
        limits=(0.8, 1.25),
    )
    first, second = timeline.scenes[2].segments
    # «agente» se dice a 4,0 s y «cinco» a 5,0 s; la narración dura 6 s más 0,5 de pausa.
    assert (first.start, first.length) == (13.0, 5.0)
    assert (second.start, second.length) == (18.0, 1.5)
    # El evento de 03a (3,2 s del clip) cae sobre «agente» (4,0 s): el primer tramo va a 0,8×.
    assert [round(p.clip_start, 3) for p in first.pieces] == [0.0, 3.2]
    assert [round(p.factor, 3) for p in first.pieces] == [0.8, 1.0]
    # 03b abre en «cinco» con su ancla (0,3 s): empieza en ese cuadro del clip.
    assert round(second.pieces[0].clip_start, 3) == 0.3


# ------------------------------------------------------------------ inicio y eventos (2026-11-26)


def _timeline_for(root: Path, shots: dict) -> pitch_sync.Timeline:
    write_register(root, shots)
    for i in range(1, 7):
        write_wav(root / "narracion" / f"bloque-{i:02d}.wav", 6.0)
    pitch.align(root, transcriber=fake_transcriber)
    return pitch_sync.build_timeline(
        pitch.load_script(root),
        pitch.load_register(root)["scenes"],
        pitch_sync.load_sync(root),
        clip_path=lambda shot: Path(f"{shot['id']}.mp4"),
        clip_duration=lambda path: 7.0,
        limits=(0.7, 1.25),
    )


def test_review_start_skips_the_beginning_of_a_clip(tmp_path: Path) -> None:
    """Saltar 1,0 s del clip (paneles de la imagen de origen) y llenar 6,5 s con 6,0 s: 0,92×."""
    root = tmp_path / "pitch"
    root.mkdir()
    write_script(root)
    shots = {f"escena-{i:02d}": [{"id": f"plano-{i:02d}"}] for i in range(1, 7)}
    shots["escena-02"] = [{"id": "plano-02", "review": {"start_s": 1.0}}]
    timeline = _timeline_for(root, shots)
    piece = timeline.scenes[1].segments[0].pieces[0]
    assert (piece.clip_start, piece.clip_end) == (1.0, 7.0)
    assert round(piece.factor, 3) == round(6.0 / 6.5, 3)


def test_events_without_anchor_report_their_real_offset(tmp_path: Path) -> None:
    """Un momento sin ancla se mide con su instante real del clip (``events``)."""
    root = tmp_path / "pitch"
    root.mkdir()
    cues = {
        "solucion": [
            {"id": "s.reune", "word": "reúne", "kind": "plano", "shot": "plano-03"},
            {"id": "s.agente", "word": "agente", "kind": "plano", "shot": "plano-03"},
            {"id": "s.cinco", "word": "cinco", "kind": "plano", "shot": "plano-03"},
        ]
    }
    write_script(root, cues=cues)
    review = {
        "anchors": {"s.reune": 0.5, "s.cinco": 4.5},
        "events": {"s.agente": 2.0},
        "accepted": ["s.agente"],
    }
    shots = {f"escena-{i:02d}": [{"id": f"plano-{i:02d}"}] for i in range(1, 7)}
    shots["escena-03"] = [{"id": "plano-03", "review": review}]
    timeline = _timeline_for(root, shots)
    report = {c["id"]: c for c in timeline.cues}
    assert report["s.reune"]["delta_s"] == 0.0 and report["s.cinco"]["delta_s"] == 0.0
    # «reúne» (0,5 s) y «cinco» (5,0 s) anclados: el tramo entre ellos va a 4,0/4,5 = 0,889×.
    # «agente» se dice a 4,0 s (17,0 s del video); su evento (2,0 s del clip) se ve a 15,19 s.
    agente = report["s.agente"]
    assert agente["word_s"] == 17.0 and agente["accepted"] is True
    assert agente["delta_s"] == round(13 + 0.5 + 1.5 / (4.0 / 4.5) - 17.0, 3)
