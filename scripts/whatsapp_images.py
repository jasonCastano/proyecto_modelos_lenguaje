"""Imágenes de Valer-IA para WhatsApp, LinkedIn y Facebook (spec 030), fuera de línea y sin costo.

Cuatro familias de piezas, todas páginas HTML/CSS/SVG en ``docs/whatsapp/fuente/`` hechas con las
skills ``design`` y ``frontend-design``:

- **perfil y portadas** (``docs/whatsapp/``): composiciones de la imagen de referencia sintética;
- **tarjetas del bot** (``docs/whatsapp/tarjetas/``): bienvenida, perfiles, guía, avisos, plantilla,
  QR y Estados;
- **stickers animados** (``docs/whatsapp/stickers/``): Valer-IA en caricatura, dibujada en SVG en
  código (``personaje.js``), exportada a WebP animado de 512×512, más el ícono del paquete (96×96).

Este script las exporta con Chromium local, mide escala, zona segura, contraste y peso, y deja
vistas previas para la revisión humana. Nada sale del equipo: sin red, sin claves y sin modelos de
generación de imágenes.

Uso::

    uv run python scripts/whatsapp_images.py render [--piece ID ...] [--json]
    uv run python scripts/whatsapp_images.py approve ID [ID ...] --by "NOMBRE" [--json]
    uv run python scripts/whatsapp_images.py check [--json]
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import io
import json
import re
import shutil
import sys
import warnings
from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = Path("docs/whatsapp")
SOURCE_DIR = OUT_DIR / "fuente"
DRAFT_DIR = OUT_DIR / "borrador"
REVIEW_DIR = DRAFT_DIR / "revision"
REFERENCE_PNG = Path("docs/referencias/avatar_ingenio_manuelita.png")
REFERENCE_MD = Path("docs/referencias/avatar_ingenio_manuelita.md")
FONT_DIR = Path("web/node_modules/@fontsource-variable/archivo/files")

LFS_POINTER = b"version https://git-lfs"
FREE_LICENSES = frozenset({"OFL-1.1", "Apache-2.0", "MIT", "CC0-1.0", "CC-BY-4.0"})
MIN_CONTRAST = 4.5
TOOLS = [
    "skill design (banner design, social photos)",
    "skill frontend-design",
    "Playwright + Chromium local",
]
ARCHIVO = {"name": "Archivo", "license": "OFL-1.1"}
# La declaración de IA va en el texto del perfil de cada red, no en la imagen (decisión del
# integrante, 2026-11-27); la ficha de cada portada lo registra.
DISCLOSURE_IN = "texto del perfil de cada red (docs/whatsapp/README.md)"
ILLUSTRATION = "Valer-IA en caricatura, SVG dibujado en código (docs/whatsapp/fuente/personaje.js)"

# Requisitos de WhatsApp para stickers: 512×512, animado ≤ 500 KB, ícono del paquete 96×96 ≤ 50 KB.
STICKER_FPS = 12
STICKER_SECONDS = 2
STICKER_MAX_BYTES = 500 * 1024
ICON_MAX_BYTES = 50 * 1024

Box = tuple[int, int, int, int]
Circle = tuple[int, int, int]


class ImageError(RuntimeError):
    """La producción no puede seguir (referencia inválida, falta Chromium o las fuentes)."""


@dataclass(frozen=True)
class Piece:
    """Una pieza del catálogo (data-model.md)."""

    id: str
    file: str
    width: int
    height: int
    kind: str  # perfil | portada | tarjeta | sticker | icono
    safe: Box | None = None
    avatar: Circle | None = None
    mobile_crop: Box | None = None
    max_scale: float = 1.15
    subdir: str = ""
    page: str = ""
    query: str = ""
    uses_reference: bool = True
    text: bool = True
    max_bytes: int | None = None
    capture: int | None = None  # lado del lienzo capturado antes de reducir (ícono)

    @property
    def cover(self) -> bool:
        return self.kind == "portada"

    @property
    def animated(self) -> bool:
        return self.kind == "sticker"

    @property
    def source(self) -> Path:
        return SOURCE_DIR / (self.page or f"{self.id}.html")

    @property
    def out(self) -> Path:
        return OUT_DIR / self.subdir / self.file

    @property
    def ficha(self) -> Path:
        return OUT_DIR / self.subdir / f"{Path(self.file).stem}.md"

    @property
    def draft(self) -> Path:
        return DRAFT_DIR / self.subdir / self.file

    @property
    def report(self) -> Path:
        return DRAFT_DIR / f"{self.id}.json"


def _card(pid: str, file: str, size: tuple[int, int], *, reference: bool = False) -> Piece:
    w, h = size
    status = h == 1920
    # Estados: WhatsApp tapa arriba (nombre, barra de progreso) y abajo (responder).
    safe = (60, 240, w - 60, h - 260) if status else (56, 56, w - 56, h - 56)
    return Piece(pid, file, w, h, "tarjeta", safe=safe, subdir="tarjetas", uses_reference=reference)


def _sticker(name: str, *, text: bool = True) -> Piece:
    return Piece(
        f"sticker-{name}",
        f"valeria-{name}.webp",
        512,
        512,
        "sticker",
        subdir="stickers",
        page="sticker.html",
        query=f"id={name}",
        uses_reference=False,
        text=text,
        max_bytes=STICKER_MAX_BYTES,
    )


STICKERS = (
    "pulgar",
    "bienvenido",
    "gracias-confianza",
    "consulta",
    "hola",
    "lindo-dia",
    "gracias",
    "pensando",
    "listo",
)

# Zonas seguras y posición de la foto de perfil de cada plataforma (research R2).
PIECES: dict[str, Piece] = {
    "perfil": Piece("perfil", "valeria-perfil.png", 640, 640, "perfil", text=False),
    "linkedin": Piece(
        "linkedin",
        "valeria-linkedin.png",
        1584,
        396,
        "portada",
        safe=(600, 40, 1190, 356),
        avatar=(250, 396, 175),
    ),
    "facebook": Piece(
        "facebook",
        "valeria-facebook.png",
        1640,
        624,
        "portada",
        safe=(460, 60, 1050, 564),
        avatar=(260, 624, 175),
        mobile_crop=(265, 0, 1375, 624),
    ),
    "whatsapp": Piece(
        "whatsapp",
        "valeria-whatsapp-portada.png",
        1920,
        1080,
        "portada",
        safe=(160, 100, 1280, 800),
        avatar=(960, 1080, 230),
    ),
    # Tarjetas del bot (recomendaciones 1–6, 8 y 9 de docs/whatsapp/README.md).
    "bienvenida": _card("bienvenida", "bienvenida.png", (1080, 1080), reference=True),
    "perfiles": _card("perfiles", "perfiles.png", (1080, 1350)),
    "guia": _card("guia", "guia-rapida.png", (1080, 1350)),
    "sin-evidencia": _card("sin-evidencia", "sin-evidencia.png", (1080, 1080)),
    "fuera-de-servicio": _card("fuera-de-servicio", "fuera-de-servicio.png", (1080, 1080)),
    "plantilla-planificacion": _card(
        "plantilla-planificacion", "plantilla-planificacion.png", (1080, 1350)
    ),
    "qr-repositorio": _card("qr-repositorio", "qr-repositorio.png", (1080, 1080)),
    "estado-consejo": _card("estado-consejo", "estado-consejo.png", (1080, 1920)),
    "estado-novedad": _card("estado-novedad", "estado-novedad.png", (1080, 1920), reference=True),
    # Stickers animados (recomendación 7) y el ícono del paquete.
    **{f"sticker-{name}": _sticker(name, text=name != "pulgar") for name in STICKERS},
    "stickers-icono": Piece(
        "stickers-icono",
        "icono-paquete.png",
        96,
        96,
        "icono",
        subdir="stickers",
        page="sticker.html",
        query="id=pulgar",
        uses_reference=False,
        text=False,
        max_bytes=ICON_MAX_BYTES,
        capture=512,
    ),
}


# --------------------------------------------------------------------------- utilidades


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_lfs_pointer(path: Path) -> bool:
    with path.open("rb") as handle:
        return handle.read(len(LFS_POINTER)) == LFS_POINTER


def read_front_matter(path: Path) -> tuple[dict[str, Any], str]:
    """Encabezado YAML entre ``---`` y el cuerpo de una ficha."""
    text = path.read_text(encoding="utf-8").replace("\r\n", "\n")
    match = re.match(r"^---\n(.*?)\n---\n?(.*)$", text, re.DOTALL)
    if not match:
        return {}, text
    meta = yaml.safe_load(match.group(1)) or {}
    return dict(meta), match.group(2)


def write_front_matter(path: Path, meta: dict[str, Any], body: str) -> None:
    header = yaml.safe_dump(meta, allow_unicode=True, sort_keys=False, width=100).strip()
    path.write_text(f"---\n{header}\n---\n{body}", encoding="utf-8", newline="\n")


def _luminance(color: str) -> float:
    value = color.lstrip("#")
    channels = [int(value[i : i + 2], 16) / 255 for i in (0, 2, 4)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    """Contraste WCAG 2.x entre dos colores ``#rrggbb``."""
    high, low = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _rgb_to_hex(css: str) -> str:
    if css.startswith("#"):
        return css.lower()
    parts = [int(float(p)) for p in re.findall(r"[\d.]+", css)[:3]]
    return "#" + "".join(f"{p:02x}" for p in parts)


def _image_info(path: Path) -> tuple[tuple[int, int], int]:
    """Medidas y número de cuadros de una imagen."""
    from PIL import Image

    with Image.open(path) as image:
        return image.size, getattr(image, "n_frames", 1)


# --------------------------------------------------------------------------- referencia


def reference_errors(root: Path) -> list[str]:
    """La referencia existe, está descargada, coincide con su ficha y es sintética y sin marca."""
    png, md = root / REFERENCE_PNG, root / REFERENCE_MD
    if not png.is_file():
        return [f"Falta la imagen de referencia {REFERENCE_PNG}."]
    if is_lfs_pointer(png):
        return [f"{REFERENCE_PNG} es un puntero LFS: ejecuta `git lfs pull`."]
    if not md.is_file():
        return [f"Falta la ficha de la referencia {REFERENCE_MD}."]
    meta, _ = read_front_matter(md)
    errors = []
    if meta.get("sha256") != sha256(png):
        errors.append("El sha256 de la referencia no coincide con su ficha.")
    if meta.get("real_person") is not False:
        errors.append("La ficha de la referencia debe declarar real_person: false.")
    if meta.get("brand_elements") is not False:
        errors.append("La ficha de la referencia debe declarar brand_elements: false.")
    return errors


# --------------------------------------------------------------------------- check


def _file_errors(piece: Piece, path: Path, label: str) -> list[str]:
    """Medidas, animación y peso de un PNG o WebP de la pieza."""
    errors = []
    (width, height), frames = _image_info(path)
    if (width, height) != (piece.width, piece.height):
        expected = f"{piece.width}×{piece.height}"
        errors.append(f"{label} mide {width}×{height}; debe medir {expected}.")
    if piece.animated and frames < 2:
        errors.append(f"{label} debe ser animado (tiene {frames} cuadro).")
    size = path.stat().st_size
    if piece.max_bytes and size > piece.max_bytes:
        errors.append(f"{label} pesa {size // 1024} KB; el máximo es {piece.max_bytes // 1024} KB.")
    return errors


def ficha_errors(root: Path, piece: Piece) -> list[str]:
    png, ficha = root / piece.out, root / piece.ficha
    if not png.is_file():
        return [f"Falta {piece.out.as_posix()}."]
    if is_lfs_pointer(png):
        return [f"{piece.file} es un puntero LFS sin descargar."]
    if not ficha.is_file():
        return [f"Falta la ficha {piece.ficha.as_posix()}."]
    meta, _ = read_front_matter(ficha)
    errors = _file_errors(piece, png, piece.file)
    if meta.get("sha256") != sha256(png):
        errors.append("El sha256 de la ficha no coincide con el archivo.")
    if (meta.get("width"), meta.get("height")) != (piece.width, piece.height):
        errors.append("Las medidas de la ficha no coinciden con el catálogo.")
    ref = root / REFERENCE_PNG
    if ref.is_file() and not is_lfs_pointer(ref) and meta.get("reference_sha256") != sha256(ref):
        errors.append("reference_sha256 no coincide con la imagen de referencia.")
    if meta.get("generative_model") != "none":
        errors.append("generative_model debe ser none (FR-010).")
    if meta.get("cost_usd") != 0:
        errors.append("cost_usd debe ser 0 (SC-005).")
    fonts = meta.get("fonts") or []
    if (piece.text and not fonts) or any(f.get("license") not in FREE_LICENSES for f in fonts):
        errors.append("Cada tipografía debe tener una licencia libre (FR-011).")
    for field in ("approved_by", "approved_at"):
        if not str(meta.get(field) or "").strip():
            errors.append(f"Falta {field} (FR-009).")
    if piece.cover and not str(meta.get("disclosure_in") or "").strip():
        errors.append("Las portadas deben registrar disclosure_in: dónde va la declaración de IA.")
    return errors


def check(root: Path = ROOT) -> dict[str, Any]:
    pieces = []
    for piece in PIECES.values():
        if not (root / piece.out).exists() and not (root / piece.ficha).exists():
            pieces.append({"id": piece.id, "status": "pendiente", "errors": []})
            continue
        pieces.append({"id": piece.id, "status": "aprobada", "errors": ficha_errors(root, piece)})
    return {"ok": all(not p["errors"] for p in pieces), "pieces": pieces}


# --------------------------------------------------------------------------- approve


def draft_errors(piece: Piece, draft: Path, report: dict[str, Any]) -> list[str]:
    errors = _file_errors(piece, draft, "El borrador")
    if piece.uses_reference:
        scale = report.get("scale")
        if scale is None or scale > piece.max_scale:
            errors.append(
                f"La referencia se amplía {scale}×; el máximo es {piece.max_scale}× (R3)."
            )
        if not report.get("scale_uniform"):
            errors.append("La referencia se deforma: la escala debe ser igual en ambos ejes.")
    if not report.get("safe_ok", True):
        errors.append("Hay texto fuera de la zona segura (R2).")
    if piece.kind in {"portada", "tarjeta"}:
        contrast = report.get("min_contrast")
        if contrast is None or contrast < MIN_CONTRAST:
            errors.append(f"Contraste mínimo {contrast}; debe ser ≥ {MIN_CONTRAST} (AA).")
    fonts = report.get("fonts") or []
    if any(f.get("license") not in FREE_LICENSES for f in fonts):
        errors.append("Hay tipografías sin licencia libre (FR-011).")
    return errors


def approve(root: Path, piece_id: str, by: str, *, today: str | None = None) -> dict[str, Any]:
    piece = PIECES[piece_id]
    result: dict[str, Any] = {"id": piece_id, "ok": False, "errors": []}
    if not by.strip():
        result["errors"].append("--by es obligatorio: quién aprueba la pieza (FR-009).")
        return result
    errors = reference_errors(root)
    draft = root / piece.draft
    report_path = root / piece.report
    if not draft.is_file() or not report_path.is_file():
        errors.append(f"No hay borrador de {piece_id}: ejecuta `render --piece {piece_id}`.")
    if errors:
        result["errors"] = errors
        return result
    report = json.loads(report_path.read_text(encoding="utf-8"))
    errors = draft_errors(piece, draft, report)
    if errors:
        result["errors"] = errors
        return result

    out = root / piece.out
    out.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(draft, out)
    meta: dict[str, Any] = {
        "file": piece.file,
        "sha256": sha256(out),
        "width": piece.width,
        "height": piece.height,
        "source": (piece.source.as_posix() + (f"?{piece.query}" if piece.query else "")),
        "reference": REFERENCE_PNG.as_posix(),
        "reference_sha256": sha256(root / REFERENCE_PNG),
        "reference_use": "composición sin alterar rasgos"
        if piece.uses_reference
        else "inspiración para la ilustración",
        "reference_scale": report.get("scale"),
        "illustration": None if piece.uses_reference else ILLUSTRATION,
        "tools": TOOLS,
        "fonts": report.get("fonts") or [],
        "generative_model": "none",
        "cost_usd": 0,
        "disclosure_in": DISCLOSURE_IN if piece.cover else None,
        "min_contrast": report.get("min_contrast"),
        "frames": report.get("frames"),
        "bytes": out.stat().st_size,
        "approved_by": by.strip(),
        "approved_at": today or dt.date.today().isoformat(),
    }
    body = (
        f"\n# Ficha de origen: {piece.file} (spec 030)\n\n"
        f"Pieza `{piece_id}` ({piece.kind}) de {piece.width}×{piece.height} px, exportada con\n"
        "Chromium local desde su fuente HTML/CSS/SVG. Sin modelos de generación de imágenes, sin\n"
        "red y sin costo. Dónde se usa: `docs/whatsapp/README.md`.\n"
    )
    write_front_matter(root / piece.ficha, meta, body)
    result["errors"] = ficha_errors(root, piece)
    result["ok"] = not result["errors"]
    return result


# --------------------------------------------------------------------------- render

_MEASURE = """
() => {
  const out = {scaleX: null, scaleY: null, safe: [], texts: []};
  const ref = document.querySelector('img[data-ref]');
  if (ref) {
    const r = ref.getBoundingClientRect();
    out.scaleX = r.width / ref.naturalWidth;
    out.scaleY = r.height / ref.naturalHeight;
  }
  for (const el of document.querySelectorAll('[data-safe]')) {
    const r = el.getBoundingClientRect();
    out.safe.push({name: el.dataset.safe, box: [r.left, r.top, r.right, r.bottom]});
  }
  for (const el of document.querySelectorAll('[data-text]')) {
    const holder = el.closest('[data-bg]');
    out.texts.push({
      name: el.dataset.text,
      color: getComputedStyle(el).color,
      bg: el.dataset.bg || (holder ? holder.dataset.bg : null),
    });
  }
  out.fontsOk = document.fonts.check('800 32px Archivo');
  return out;
}
"""

_SEEK = """
(t) => {
  for (const a of document.getAnimations()) { a.pause(); a.currentTime = t; }
  return document.getAnimations().length;
}
"""


def _measure(piece: Piece, raw: dict[str, Any]) -> dict[str, Any]:
    report: dict[str, Any] = {"id": piece.id, "width": piece.width, "height": piece.height}
    sx, sy = raw.get("scaleX"), raw.get("scaleY")
    report["scale"] = round(max(sx, sy), 3) if sx and sy else None
    report["scale_uniform"] = bool(sx and sy and abs(sx - sy) < 0.005)
    outside = []
    if piece.safe:
        x0, y0, x1, y1 = piece.safe
        for item in raw.get("safe", []):
            left, top, right, bottom = item["box"]
            if left < x0 - 0.5 or top < y0 - 0.5 or right > x1 + 0.5 or bottom > y1 + 0.5:
                outside.append(item["name"])
    report["safe_ok"] = not outside
    report["outside_safe"] = outside
    contrasts = []
    for text in raw.get("texts", []):
        if text.get("bg"):
            ratio = contrast_ratio(_rgb_to_hex(text["color"]), text["bg"])
            contrasts.append({"name": text["name"], "ratio": round(ratio, 2)})
    report["contrast"] = contrasts
    report["min_contrast"] = min((c["ratio"] for c in contrasts), default=None)
    report["fonts_loaded"] = bool(raw.get("fontsOk"))
    report["fonts"] = [ARCHIVO] if piece.text else []
    return report


def _circle(image: Any, size: int) -> Any:
    from PIL import Image, ImageDraw

    small = image.convert("RGB").resize((size, size), Image.Resampling.LANCZOS)
    mask = Image.new("L", (size * 4, size * 4), 0)
    ImageDraw.Draw(mask).ellipse((0, 0, size * 4 - 1, size * 4 - 1), fill=255)
    mask = mask.resize((size, size), Image.Resampling.LANCZOS)
    out = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    out.paste(small, (0, 0), mask)
    return out


def _previews(root: Path, piece: Piece, path: Path, frames: list[Any] | None) -> list[str]:
    from PIL import Image, ImageDraw

    review = root / REVIEW_DIR
    review.mkdir(parents=True, exist_ok=True)
    written = []
    if piece.animated and frames:
        # Seis cuadros del ciclo sobre el fondo claro y el oscuro del chat de WhatsApp.
        picks = [frames[i * len(frames) // 6] for i in range(6)]
        sheet = Image.new("RGB", (6 * 256, 2 * 256), (239, 234, 226))
        sheet.paste(Image.new("RGB", (6 * 256, 256), (11, 20, 26)), (0, 256))
        for i, frame in enumerate(picks):
            small = frame.resize((256, 256), Image.Resampling.LANCZOS)
            sheet.paste(small, (i * 256, 0), small)
            sheet.paste(small, (i * 256, 256), small)
        target = review / f"{piece.id}-cuadros.png"
        sheet.save(target)
        written.append(target)
        return [p.relative_to(root).as_posix() for p in written]
    with Image.open(path) as image:
        if piece.id == "perfil":
            # Lista de chats: miniaturas sobre blanco y sobre el fondo oscuro de WhatsApp.
            sheet = Image.new("RGB", (40 + 48 + 24 + 96 + 24 + 640 + 40, 840), (255, 255, 255))
            sheet.paste(Image.new("RGB", (sheet.width, 120), (17, 27, 33)), (0, 720))
            x = 40
            for size in (48, 96, 640):
                sheet.paste(_circle(image, size), (x, 40), _circle(image, size))
                if size < 640:
                    sheet.paste(_circle(image, size), (x, 732), _circle(image, size))
                x += size + 24
            target = review / "perfil-circulo.png"
            sheet.save(target)
            written.append(target)
        elif piece.cover:
            base = image.convert("RGB")
            avatar_path = root / PIECES["perfil"].out
            draft_avatar = root / PIECES["perfil"].draft
            source = avatar_path if avatar_path.is_file() else draft_avatar
            if piece.avatar:
                cx, cy, r = piece.avatar
                overlay = base.copy()
                draw = ImageDraw.Draw(overlay)
                draw.ellipse((cx - r - 8, cy - r - 8, cx + r + 8, cy + r + 8), fill=(255, 255, 255))
                if source.is_file() and not is_lfs_pointer(source):
                    with Image.open(source) as avatar:
                        disc = _circle(avatar, 2 * r)
                        overlay.paste(disc, (cx - r, cy - r), disc)
                else:
                    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(160, 160, 160))
                if piece.safe:
                    draw.rectangle(piece.safe, outline=(255, 0, 255), width=2)
                target = review / f"{piece.id}-escritorio.png"
                overlay.save(target)
                written.append(target)
            if piece.mobile_crop:
                target = review / f"{piece.id}-telefono.png"
                base.crop(piece.mobile_crop).save(target)
                written.append(target)
        elif piece.kind == "tarjeta" and piece.safe:
            overlay = image.convert("RGB")
            ImageDraw.Draw(overlay).rectangle(piece.safe, outline=(255, 0, 255), width=3)
            target = review / f"{piece.id}-zona.png"
            overlay.save(target)
            written.append(target)
    return [p.relative_to(root).as_posix() for p in written]


def _save_webp(frames: list[Any], target: Path, max_bytes: int) -> int:
    """WebP animado en bucle; baja la calidad hasta caber en el peso de WhatsApp."""
    duration = round(1000 / STICKER_FPS)
    data = b""
    for quality in (80, 70, 60, 50, 40):
        buffer = io.BytesIO()
        frames[0].save(
            buffer,
            format="WEBP",
            save_all=True,
            append_images=frames[1:],
            duration=duration,
            loop=0,
            quality=quality,
            method=4,
        )
        data = buffer.getvalue()
        if len(data) <= max_bytes:
            break
    target.write_bytes(data)
    return len(frames)


def _capture(page: Any, piece: Piece, target: Path) -> tuple[list[Any] | None, int | None]:
    from PIL import Image

    side = piece.capture or piece.width
    clip = {"x": 0, "y": 0, "width": side, "height": piece.height if not piece.capture else side}
    if piece.animated:
        frames = []
        total = STICKER_FPS * STICKER_SECONDS
        for i in range(total):
            page.evaluate(_SEEK, i * 1000 / STICKER_FPS)
            shot = page.screenshot(clip=clip, omit_background=True)
            frames.append(Image.open(io.BytesIO(shot)).convert("RGBA"))
        count = _save_webp(frames, target, piece.max_bytes or STICKER_MAX_BYTES)
        return frames, count
    if piece.capture:
        page.evaluate(_SEEK, 0)
        shot = page.screenshot(clip=clip, omit_background=True)
        image = Image.open(io.BytesIO(shot)).convert("RGBA")
        image.resize((piece.width, piece.height), Image.Resampling.LANCZOS).save(
            target, optimize=True
        )
        return None, None
    page.screenshot(path=str(target), clip=clip)
    return None, None


def render(root: Path, ids: Sequence[str] | None = None) -> dict[str, Any]:
    errors = reference_errors(root)
    if errors:
        raise ImageError(" ".join(errors))
    if not (root / FONT_DIR).is_dir():
        raise ImageError(f"Falta {FONT_DIR}: ejecuta `make dev` (instala las fuentes de la web).")
    chosen = list(ids or PIECES)
    for piece_id in chosen:
        if not (root / PIECES[piece_id].source).is_file():
            raise ImageError(f"Falta la fuente {PIECES[piece_id].source}.")

    import asyncio

    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:  # pragma: no cover - depende del entorno
        raise ImageError("Falta Playwright: ejecuta `make dev`.") from exc
    if sys.platform == "win32":
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    reports = []
    # El perfil va primero: las vistas previas de las portadas lo superponen.
    ordered = sorted(chosen, key=lambda pid: pid != "perfil")
    with sync_playwright() as manager:
        try:
            browser = manager.chromium.launch()
        except Exception as exc:  # pragma: no cover - depende del entorno
            raise ImageError(
                "Falta Chromium: ejecuta `uv run playwright install chromium`."
            ) from exc
        try:
            for piece_id in ordered:
                piece = PIECES[piece_id]
                side = piece.capture or piece.width
                height = piece.capture or piece.height
                page = browser.new_page(
                    viewport={"width": side, "height": height}, device_scale_factor=1
                )
                url = (root / piece.source).resolve().as_uri()
                page.goto(url + (f"?{piece.query}" if piece.query else ""))
                page.wait_for_load_state("load")
                page.evaluate("document.fonts.ready.then(() => true)")
                target = root / piece.draft
                target.parent.mkdir(parents=True, exist_ok=True)
                report = _measure(piece, page.evaluate(_MEASURE))
                frames, count = _capture(page, piece, target)
                page.close()
                report["frames"] = count
                report["bytes"] = target.stat().st_size
                report["previews"] = _previews(root, piece, target, frames)
                report["errors"] = draft_errors(piece, target, report)
                if piece.text and not report["fonts_loaded"]:
                    report["errors"].append("La tipografía Archivo no cargó.")
                (root / piece.report).write_text(
                    json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8"
                )
                report["draft"] = target.relative_to(root).as_posix()
                reports.append(report)
        finally:
            browser.close()
    return {"ok": all(not r["errors"] for r in reports), "pieces": reports}


# --------------------------------------------------------------------------- CLI


def _print(result: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return
    for piece in result.get("pieces", [result]):
        status = piece.get("status") or ("ok" if not piece.get("errors") else "error")
        print(f"{piece['id']}: {status}")
        for error in piece.get("errors", []):
            print(f"  - {error}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    sub = parser.add_subparsers(dest="command", required=True)
    p_render = sub.add_parser("render", help="exporta borradores y vistas previas")
    p_render.add_argument("--piece", nargs="+", choices=list(PIECES))
    p_render.add_argument("--json", action="store_true")
    p_approve = sub.add_parser("approve", help="publica piezas aprobadas con su ficha")
    p_approve.add_argument("piece", nargs="+", choices=list(PIECES))
    p_approve.add_argument("--by", required=True)
    p_approve.add_argument("--json", action="store_true")
    p_check = sub.add_parser("check", help="verifica las piezas aprobadas")
    p_check.add_argument("--json", action="store_true")
    for p in (p_render, p_approve, p_check):
        p.add_argument("--root", type=Path, default=argparse.SUPPRESS, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    root = Path(args.root)
    try:
        if args.command == "render":
            result = render(root, args.piece)
        elif args.command == "approve":
            results = [approve(root, pid, args.by) for pid in args.piece]
            result = {"ok": all(r["ok"] for r in results), "pieces": results}
        else:
            result = check(root)
    except ImageError as exc:
        result = {"ok": False, "errors": [str(exc)], "pieces": []}
        _print(result, args.json)
        if not args.json:
            print(str(exc), file=sys.stderr)
        return 1
    _print(result, args.json)
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
