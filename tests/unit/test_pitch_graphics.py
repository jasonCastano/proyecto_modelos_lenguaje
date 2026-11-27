"""Gráficos del montaje del pitch v2 (spec 029, T017): rasterizado y cadena de overlay.

Sin navegador: un rasterizador falso escribe PNG de prueba.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje import pitch_graphics
from proyecto_modelos_lenguaje.pitch_sync import GraphicEvent


def svg(root: Path, name: str, color: str = "#387c2b") -> Path:
    folder = root / "graficos"
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.svg"
    path.write_text(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="20" height="20">'
        f'<rect width="20" height="20" fill="{color}"/></svg>',
        encoding="utf-8",
    )
    return path


class FakeRasterizer:
    def __init__(self) -> None:
        self.calls: list[str] = []

    def __call__(self, text: str, target: Path) -> None:
        self.calls.append(target.stem)
        target.write_bytes(b"\x89PNG fake")


def test_render_svgs_writes_one_png_each_and_skips_up_to_date(tmp_path: Path) -> None:
    svg(tmp_path, "icono-a")
    svg(tmp_path, "icono-b")
    fake = FakeRasterizer()
    first = pitch_graphics.render_svgs(tmp_path, rasterizer=fake)
    assert first == {"rendered": ["icono-a", "icono-b"], "up_to_date": []}
    assert pitch_graphics.png_path(tmp_path, "icono-a").is_file()
    second = pitch_graphics.render_svgs(tmp_path, rasterizer=fake)
    assert second == {"rendered": [], "up_to_date": ["icono-a", "icono-b"]}
    svg(tmp_path, "icono-b", color="#ffd200")
    third = pitch_graphics.render_svgs(tmp_path, rasterizer=fake)
    assert third["rendered"] == ["icono-b"]
    assert fake.calls == ["icono-a", "icono-b", "icono-b"]


def test_missing_png_is_rendered_again(tmp_path: Path) -> None:
    svg(tmp_path, "icono-a")
    fake = FakeRasterizer()
    pitch_graphics.render_svgs(tmp_path, rasterizer=fake)
    pitch_graphics.png_path(tmp_path, "icono-a").unlink()
    assert pitch_graphics.render_svgs(tmp_path, rasterizer=fake)["rendered"] == ["icono-a"]


def event(cue: str, graphic: str, t_in: float, t_out: float, **kw) -> GraphicEvent:
    return GraphicEvent(
        cue, graphic, t_in, t_out, kw.get("from_xy", (0.2, 0.3)), kw.get("to_xy", (0.5, 0.6))
    )


def test_overlay_graph_enters_on_the_word_and_moves(tmp_path: Path) -> None:
    png = pitch_graphics.png_path(tmp_path, "icono-a")
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    inputs, filters, label = pitch_graphics.overlay_graph(
        [event("p.informes", "icono-a", 10.92, 12.22)],
        tmp_path,
        base="vbase",
        first_input=14,
        total_s=50.3,
        fps=24,
    )
    assert inputs == ["-loop", "1", "-framerate", "24", "-t", "50.300", "-i", str(png)]
    fade, over = filters
    assert fade.startswith("[14:v]format=rgba,fade=t=in:st=10.920:d=0.25:alpha=1")
    assert "fade=t=out:st=11.970" in fade
    assert over.startswith("[vbase][g0]overlay=")
    assert "enable='between(t,10.920,12.220)'" in over
    assert "clip((t-10.920)/0.8,0,1)" in over  # trayecto de 0,8 s desde la palabra
    assert "W*(0.2000+(0.3000)*" in over and "H*(0.3000+(0.3000)*" in over
    assert label == "ov0"


def test_fixed_graphic_has_no_motion(tmp_path: Path) -> None:
    png = pitch_graphics.png_path(tmp_path, "perfil")
    png.parent.mkdir(parents=True)
    png.write_bytes(b"x")
    _, filters, _ = pitch_graphics.overlay_graph(
        [event("u.a", "perfil", 3.0, 8.0, from_xy=(0.7, 0.3), to_xy=(0.7, 0.3))],
        tmp_path,
        base="vbase",
        first_input=0,
        total_s=10,
        fps=24,
    )
    assert "x='W*0.7000-w/2'" in filters[1] and "clip(" not in filters[1]


def test_profile_cards_chain_in_order(tmp_path: Path) -> None:
    names = ["perfil-visitante", "perfil-cliente", "perfil-proveedor"]
    for name in names:
        png = pitch_graphics.png_path(tmp_path, name)
        png.parent.mkdir(parents=True, exist_ok=True)
        png.write_bytes(b"x")
    events = [event(f"u.{i}", name, 40 + 0.35 * i, 47) for i, name in enumerate(names)]
    inputs, filters, label = pitch_graphics.overlay_graph(
        events, tmp_path, base="vbase", first_input=20, total_s=50, fps=24
    )
    assert inputs.count("-i") == 3 and label == "ov2"
    assert filters[3].startswith("[ov0][g1]overlay") and filters[5].startswith("[ov1][g2]overlay")
    assert "between(t,40.350,47.000)" in filters[3]


def test_missing_png_is_reported(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="pml pitch graphics"):
        pitch_graphics.overlay_graph(
            [event("x", "nada", 1, 2)], tmp_path, base="v", first_input=0, total_s=5, fps=24
        )


def test_repository_graphics_cover_every_cue() -> None:
    """Cada momento gráfico del guion tiene su SVG y su PNG versionados."""
    from proyecto_modelos_lenguaje import pitch

    script = pitch.load_script(pitch.PITCH_ROOT)
    names = {c.graphic for b in script.blocks for c in b.cues if c.kind == "grafico"}
    assert len(names) == 14
    for name in names:
        assert (pitch.PITCH_ROOT / "graficos" / f"{name}.svg").is_file()
        assert pitch_graphics.png_path(pitch.PITCH_ROOT, name).is_file()
