"""Gráficos del montaje del pitch v2: iconos y tarjetas de perfil (spec 029, research R6).

Los gráficos son SVG propios en ``video/pitch/graficos/``. ``render_svgs`` los pasa a PNG
transparentes con Playwright (Chromium) solo cuando cambian; los PNG se versionan por LFS, así que
montar el video no necesita un navegador. ``overlay_graph`` arma la cadena de ``overlay`` de
ffmpeg: cada gráfico entra con un fundido de 0,25 s en el instante de su palabra, viaja de
``from`` a ``to`` en 0,8 s y sale al terminar su tiempo.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from pathlib import Path

from .pitch_sync import FADE_S, MOVE_S, GraphicEvent

GRAPHICS_DIR = "graficos"
PNG_DIR = "png"
MANIFEST = "manifest.json"

Rasterizer = Callable[[str, Path], None]


def svg_paths(root: Path) -> list[Path]:
    return sorted((root / GRAPHICS_DIR).glob("*.svg"))


def png_path(root: Path, name: str) -> Path:
    return root / GRAPHICS_DIR / PNG_DIR / f"{name}.png"


def _digest(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def playwright_rasterizer() -> tuple[Rasterizer, Callable[[], None]]:  # pragma: no cover
    """Chromium sin fondo: un PNG transparente del tamaño del SVG."""
    import asyncio
    import sys

    from playwright.sync_api import sync_playwright

    if sys.platform == "win32":
        # La CLI fija el bucle selector (scraping); Playwright necesita subprocesos (Proactor).
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
    manager = sync_playwright().start()
    browser = manager.chromium.launch()
    page = browser.new_page(device_scale_factor=1)

    def rasterize(svg: str, target: Path) -> None:
        page.set_content(
            "<!doctype html><html><body style='margin:0;background:transparent'>"
            f"{svg}</body></html>"
        )
        page.locator("svg").first.screenshot(path=str(target), omit_background=True)

    def close() -> None:
        browser.close()
        manager.stop()

    return rasterize, close


def render_svgs(root: Path, *, rasterizer: Rasterizer | None = None) -> dict[str, list[str]]:
    """Rasteriza los SVG nuevos o cambiados; omite los que siguen al día por su huella."""
    out_dir = root / GRAPHICS_DIR / PNG_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = out_dir / MANIFEST
    manifest = json.loads(manifest_path.read_text()) if manifest_path.is_file() else {}
    pending = []
    for svg in svg_paths(root):
        text = svg.read_text(encoding="utf-8")
        target = png_path(root, svg.stem)
        if manifest.get(svg.stem) == _digest(text) and target.is_file():
            continue
        pending.append((svg.stem, text, target))
    close: Callable[[], None] | None = None
    if pending and rasterizer is None:
        rasterizer, close = playwright_rasterizer()
    try:
        for name, text, target in pending:
            assert rasterizer is not None
            rasterizer(text, target)
            manifest[name] = _digest(text)
    finally:
        if close is not None:
            close()
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    rendered = [name for name, _, _ in pending]
    return {
        "rendered": rendered,
        "up_to_date": [p.stem for p in svg_paths(root) if p.stem not in rendered],
    }


def _lerp(a: float, b: float, t_in: float) -> str:
    """Expresión de ffmpeg: de ``a`` a ``b`` en ``MOVE_S`` segundos desde ``t_in``."""
    if abs(a - b) < 1e-9:
        return f"{a:.4f}"
    return f"({a:.4f}+({b - a:.4f})*clip((t-{t_in:.3f})/{MOVE_S},0,1))"


def overlay_graph(
    events: Sequence[GraphicEvent],
    root: Path,
    *,
    base: str,
    first_input: int,
    total_s: float,
    fps: int,
) -> tuple[list[str], list[str], str]:
    """Entradas de ffmpeg, filtros y etiqueta de salida para superponer los gráficos."""
    inputs: list[str] = []
    filters: list[str] = []
    label = base
    for offset, event in enumerate(events):
        path = png_path(root, event.graphic)
        if not path.is_file():
            raise FileNotFoundError(f"Falta {path}: corre pml pitch graphics.")
        index = first_input + offset
        inputs += ["-loop", "1", "-framerate", str(fps), "-t", f"{total_s:.3f}", "-i", str(path)]
        fade_out = max(event.t_in, event.t_out - FADE_S)
        filters.append(
            f"[{index}:v]format=rgba,"
            f"fade=t=in:st={event.t_in:.3f}:d={FADE_S}:alpha=1,"
            f"fade=t=out:st={fade_out:.3f}:d={FADE_S}:alpha=1[g{offset}]"
        )
        (fx, fy), (tx, ty) = event.from_xy, event.to_xy
        x = f"W*{_lerp(fx, tx, event.t_in)}-w/2"
        y = f"H*{_lerp(fy, ty, event.t_in)}-h/2"
        out = f"ov{offset}"
        filters.append(
            f"[{label}][g{offset}]overlay=x='{x}':y='{y}':eval=frame:"
            f"enable='between(t,{event.t_in:.3f},{event.t_out:.3f})'[{out}]"
        )
        label = out
    return inputs, filters, label
