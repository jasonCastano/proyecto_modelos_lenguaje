"""Unit tests for VTT parsing."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.silver.extractors.vtt import extract_vtt

FIXTURES = Path(__file__).resolve().parents[2] / "fixtures" / "silver"


def test_merges_cues_and_removes_boilerplate() -> None:
    document = extract_vtt(
        (FIXTURES / "sample.vtt").read_bytes(), title="Manuelita, manifiesto 2026"
    )
    text = document.text
    assert document.skip_reason is None
    assert "Manuelita transforma" in text
    assert text.count("La compañía opera") == 1
    assert "Amara.org" not in text
    cues = [block for block in document.blocks if block.time_start is not None]
    assert len(cues) == 2
    assert cues[0].time_end <= cues[1].time_start
    assert document.blocks[0].level == 1
