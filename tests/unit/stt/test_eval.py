"""Evaluación del dictado (spec 023, FR-023, research R11): métricas e informe, sin red."""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest

from proyecto_modelos_lenguaje.stt.audio import encode_wav16k
from proyecto_modelos_lenguaje.stt.config import SttConfig
from proyecto_modelos_lenguaje.stt.engine import Segment, SttService
from proyecto_modelos_lenguaje.stt.eval import (
    EvalItem,
    load_phrases,
    normalize_for_wer,
    percentile,
    render_markdown,
    run_eval,
    summarize,
    targets,
    vocab_hits,
    wer,
)


def test_normalization_spells_numbers_and_drops_accents() -> None:
    assert normalize_for_wer("¿Cuánto invirtió Manuelita en 2024?") == [
        "cuanto",
        "invirtio",
        "manuelita",
        "en",
        "dos",
        "mil",
        "veinticuatro",
    ]
    assert normalize_for_wer("el año dos mil veinticuatro") == normalize_for_wer("el año 2024")
    assert normalize_for_wer("Educar 1-1") == ["educar", "uno", "uno"]
    assert normalize_for_wer("1864, 77% y 840") == normalize_for_wer(
        "mil ochocientos sesenta y cuatro setenta y siete por ciento y ochocientos cuarenta"
    )
    assert normalize_for_wer("Valer-IA Caña") == ["valer", "ia", "cana"]


def test_wer_is_word_edit_distance() -> None:
    assert wer("¿Qué produce Manuelita?", "que produce manuelita") == 0.0
    assert wer("hola valer ia", "hola valeria") == pytest.approx(2 / 3)
    assert wer("uno dos tres cuatro", "uno tres cuatro cinco") == pytest.approx(0.5)
    assert wer("", "algo") == 1.0


def test_vocab_hits_need_the_exact_name() -> None:
    assert vocab_hits(
        "Hola Valer-IA Caña, ¿qué produce Manuelita?", ["Valer-IA Caña", "Manuelita"]
    ) == (
        2,
        2,
    )
    assert vocab_hits("hola valeria caña", ["Valer-IA Caña"]) == (0, 1)
    assert vocab_hits("qué hace oceanos", ["Océanos"]) == (1, 1)  # sin distinguir tildes
    assert vocab_hits("algo", []) == (0, 0)


def test_percentile() -> None:
    assert percentile([], 90) == 0
    assert percentile([100, 200, 300, 400, 500, 600, 700, 800, 900, 1000], 90) == 900
    assert percentile([5], 50) == 5


def _item(**values) -> EvalItem:
    base = {
        "id": "x",
        "kind": "speech",
        "voice": "Rebeca",
        "audio_ms": 3000,
        "stt_ms": 500,
        "reference": "hola",
        "hypothesis": "hola",
        "wer": 0.0,
        "vocab_hits": 1,
        "vocab_total": 1,
    }
    base.update(values)
    return EvalItem(**base)


def test_summary_and_targets() -> None:
    items = [
        _item(id="a", audio_ms=3000, stt_ms=400, wer=0.1),
        _item(id="b", audio_ms=8000, stt_ms=1500, wer=0.2, vocab_hits=0, vocab_total=1),
        _item(id="c", audio_ms=12_000, stt_ms=3000, wer=0.0),
        _item(
            id="s",
            kind="silence",
            reference="",
            hypothesis="",
            wer=0.0,
            vocab_total=0,
            vocab_hits=0,
        ),
        _item(
            id="n",
            kind="noise",
            reference="",
            hypothesis="hmm",
            wer=0.0,
            vocab_total=0,
            vocab_hits=0,
        ),
    ]
    summary = summarize(items)
    assert summary["wer"] == pytest.approx(0.1)
    assert summary["vocab_accuracy"] == pytest.approx(2 / 3, abs=1e-3)
    assert summary["latency_ms"]["<=5s"]["p90"] == 400
    assert summary["latency_ms"]["5-10s"]["p50"] == 1500
    assert summary["latency_ms"][">10s"]["p90"] == 3000
    assert summary["latency_ms"]["<=10s"]["p90"] == 1500
    assert summary["empty_rate_on_silence"] == 0.5
    verdict = targets(summary)
    assert verdict == {"SC-001": True, "SC-002": False, "SC-003": True, "SC-004": False}


class _FakeSynth:
    def synthesize(self, text: str, voice: str) -> tuple[np.ndarray, int]:
        seconds = max(1.0, len(text) / 15)
        tone = 0.3 * np.sin(np.linspace(0, 400 * np.pi * seconds, int(24_000 * seconds)))
        return tone.astype(np.float32), 24_000


class _Echo:
    """Transcriptor que «oye» el texto de la frase que se le pide (vía un registro externo)."""

    model_label = "eco"

    def __init__(self) -> None:
        self.next_text = ""

    def transcribe(self, samples: np.ndarray) -> list[Segment]:
        if float(np.sqrt(np.mean(np.square(samples)))) < 0.01:
            return []
        return [Segment(self.next_text)]


def test_run_eval_builds_the_report(tmp_path: Path) -> None:
    echo = _Echo()
    config = replace(SttConfig(), engine="fake", warmup=False)

    def service_for(model: str) -> SttService:
        return SttService(config, transcriber=echo)

    phrases = load_phrases()
    speech = [p for p in phrases if p["kind"] == "speech"][:3]
    noise = [p for p in phrases if p["kind"] != "speech"][:2]

    def before(item: dict) -> None:
        echo.next_text = item.get("text", "")

    report = run_eval(
        [*speech, *noise],
        models=["base"],
        voices=["Rebeca"],
        synthesizer=_FakeSynth(),
        service_for=service_for,
        before_item=before,
    )
    row = report["models"]["base"]
    assert row["summary"]["wer"] == 0.0
    assert row["summary"]["empty_rate_on_silence"] == 1.0
    assert all(row["targets"].values())
    assert {item["kind"] for item in row["items"]} == {"speech", "silence"}
    assert report["config"]["engine"] == "fake" and "vocabulary" in report["config"]

    path = tmp_path / "evaluacion_stt.json"
    path.write_text(json.dumps(report, ensure_ascii=False), encoding="utf-8")
    markdown = render_markdown(report)
    assert "# Evaluación del dictado" in markdown and "SC-001" in markdown
    assert all(line == line.rstrip() for line in markdown.splitlines())


def test_human_recordings_are_private_by_default(tmp_path: Path) -> None:
    (tmp_path / "uno.wav").write_bytes(
        encode_wav16k((0.3 * np.sin(np.linspace(0, 400 * np.pi, 32_000))).astype(np.float32))
    )
    (tmp_path / "uno.txt").write_text("¿Qué produce Manuelita?", encoding="utf-8")
    echo = _Echo()
    echo.next_text = "¿Qué produce Manuelita?"
    config = replace(SttConfig(), engine="fake", warmup=False)
    report = run_eval(
        [],
        models=["base"],
        voices=[],
        synthesizer=_FakeSynth(),
        service_for=lambda _m: SttService(config, transcriber=echo),
        audio_dir=tmp_path,
    )
    item = report["models"]["base"]["items"][0]
    assert item["kind"] == "human" and item["wer"] == 0.0
    assert item["hypothesis"] is None and item["reference"] is None
    report = run_eval(
        [],
        models=["base"],
        voices=[],
        synthesizer=_FakeSynth(),
        service_for=lambda _m: SttService(config, transcriber=echo),
        audio_dir=tmp_path,
        include_human_text=True,
    )
    assert report["models"]["base"]["items"][0]["hypothesis"] == "¿Qué produce Manuelita?"


def test_fixture_has_the_planned_battery() -> None:
    phrases = load_phrases()
    speech = [p for p in phrases if p["kind"] == "speech"]
    assert len(speech) == 44 and len(phrases) - len(speech) == 6
    assert sum(1 for p in speech if p["group"] == "larga") == 4  # tramos de 5–10 s y > 10 s
    assert sum(1 for p in speech if p["vocab"]) >= 12
