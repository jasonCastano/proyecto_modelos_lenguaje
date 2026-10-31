"""Parity between the Python brand palette and the web tokens."""

from __future__ import annotations

from pathlib import Path

from proyecto_modelos_lenguaje.brand import BrandPalette

ROOT = Path(__file__).resolve().parents[2]


def test_web_tokens_match_brand_palette() -> None:
    css = (ROOT / "web" / "src" / "styles" / "tokens.css").read_text(encoding="utf-8")
    palette = BrandPalette()
    for name in ("forest", "orange", "lime", "yellow", "surface", "ink"):
        value = palette.to_dict()[name].lower()
        assert value in css, f"{name} {value} no está en tokens.css"
