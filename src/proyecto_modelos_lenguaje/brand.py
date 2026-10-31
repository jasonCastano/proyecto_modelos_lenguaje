"""Identidad visual del Módulo 1 inspirada en Grupo Manuelita.

La paleta se extrae del logotipo público del sitio oficial (los `fill` del SVG) y es la fuente
verificable de los tokens CSS del frontend. El módulo no renderiza HTML ni depende de Streamlit.

Ver `specs/009-manuelita-visual-identity/` y `specs/012-manuelita-rag-showcase/`.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any

HEX_PATTERN = re.compile(r"^#[0-9A-F]{6}$")
BRAND_NAME = "Grupo Manuelita"
PROJECT_NAME = "RAG Ingenio Manuelita"
TAGLINE = "Cultivamos cosas buenas que generan progreso y bienestar"
ATTRIBUTION = (
    "Marca y contenidos de Grupo Manuelita pertenecen a sus titulares; "
    "aquí se usan con fines académicos."
)
AFFILIATION_NOTE = (
    "Proyecto académico de la Maestría en IA y Ciencia de Datos (UAO). "
    "No afiliado a Grupo Manuelita."
)


@dataclass(frozen=True, slots=True)
class BrandPalette:
    """Paleta institucional extraída del logotipo público."""

    forest: str = "#387C2B"
    orange: str = "#E86D1F"
    lime: str = "#B0BC22"
    yellow: str = "#FFD200"
    orange_light: str = "#F6A01A"
    white: str = "#FFFFFF"
    surface: str = "#F5F7F3"
    ink: str = "#14240F"
    ink_muted: str = "#3F4A3C"
    success: str = "#2F7D32"
    warning: str = "#A05F00"
    info: str = "#1D5C8A"
    danger: str = "#B3261E"

    def __post_init__(self) -> None:
        for name, value in self.to_dict().items():
            if not HEX_PATTERN.match(value):
                raise ValueError(f"{name} debe ser un hex #RRGGBB en mayúsculas: {value}")

    def to_dict(self) -> dict[str, str]:
        return {
            "forest": self.forest,
            "orange": self.orange,
            "lime": self.lime,
            "yellow": self.yellow,
            "orange_light": self.orange_light,
            "white": self.white,
            "surface": self.surface,
            "ink": self.ink,
            "ink_muted": self.ink_muted,
            "success": self.success,
            "warning": self.warning,
            "info": self.info,
            "danger": self.danger,
        }

    def get(self, name: str) -> str:
        try:
            return self.to_dict()[name]
        except KeyError as exc:
            raise KeyError(f"color desconocido: {name}") from exc


@dataclass(frozen=True, slots=True)
class ContrastPair:
    text: str
    background: str
    minimum: float

    def to_dict(self) -> dict[str, Any]:
        return {"text": self.text, "background": self.background, "minimum": self.minimum}


@dataclass(frozen=True, slots=True)
class BrandTokens:
    """Tokens de la identidad: color, tipografía, espaciado y textos institucionales."""

    palette: BrandPalette = field(default_factory=BrandPalette)
    contrast_pairs: tuple[ContrastPair, ...] = (
        ContrastPair("ink", "white", 4.5),
        ContrastPair("ink", "surface", 4.5),
        ContrastPair("ink_muted", "white", 4.5),
        ContrastPair("ink_muted", "surface", 4.5),
        ContrastPair("white", "forest", 4.5),
        ContrastPair("white", "danger", 4.5),
        ContrastPair("white", "info", 4.5),
        ContrastPair("white", "warning", 4.5),
        ContrastPair("forest", "surface", 3.0),
        ContrastPair("orange", "white", 3.0),
    )
    type_scale: dict[str, int] = field(
        default_factory=lambda: {"display": 28, "heading": 22, "body": 16, "caption": 13}
    )
    font_stack: str = 'system-ui, -apple-system, "Segoe UI", Roboto, Arial, sans-serif'
    radius: int = 12
    spacing_unit: int = 8
    brand_name: str = BRAND_NAME
    project_name: str = PROJECT_NAME
    tagline: str = TAGLINE
    attribution: str = ATTRIBUTION
    affiliation_note: str = AFFILIATION_NOTE

    def to_dict(self) -> dict[str, Any]:
        return {
            "palette": self.palette.to_dict(),
            "contrast_pairs": [pair.to_dict() for pair in self.contrast_pairs],
            "type_scale": dict(self.type_scale),
            "font_stack": self.font_stack,
            "radius": self.radius,
            "spacing_unit": self.spacing_unit,
            "brand_name": self.brand_name,
            "project_name": self.project_name,
            "tagline": self.tagline,
            "attribution": self.attribution,
            "affiliation_note": self.affiliation_note,
        }


@dataclass(frozen=True, slots=True)
class StatusVariant:
    """Representación visual de un estado funcional: color, icono y etiqueta."""

    key: str
    color: str
    icon: str
    label: str

    @property
    def text(self) -> str:
        return f"{self.icon} {self.label}"


STATUS_VARIANTS: dict[str, StatusVariant] = {
    "ok": StatusVariant("ok", "success", "✓", "Correcta"),
    "ready": StatusVariant("ready", "success", "✓", "Lista"),
    "review": StatusVariant("review", "warning", "!", "Revisar"),
    "fallback": StatusVariant("fallback", "info", "i", "Sin evidencia"),
    "missing_evidence": StatusVariant("fallback", "info", "i", "Sin evidencia"),
    "error": StatusVariant("error", "danger", "×", "Error"),
    "demo": StatusVariant("demo", "orange", "●", "Modo demo"),
}


def status_variant(key: str) -> StatusVariant:
    """Map a functional status to its visual variant (never colour-only)."""
    try:
        return STATUS_VARIANTS[key]
    except KeyError as exc:
        raise KeyError(f"estado desconocido: {key}") from exc


def _channel(value: float) -> float:
    return value / 12.92 if value <= 0.04045 else ((value + 0.055) / 1.055) ** 2.4


def relative_luminance(hex_color: str) -> float:
    """WCAG 2.1 relative luminance of an ``#RRGGBB`` colour."""
    if not HEX_PATTERN.match(hex_color):
        raise ValueError(f"color inválido: {hex_color}")
    red, green, blue = (int(hex_color[index : index + 2], 16) / 255 for index in (1, 3, 5))
    return 0.2126 * _channel(red) + 0.7152 * _channel(green) + 0.0722 * _channel(blue)


def contrast_ratio(text: str, background: str) -> float:
    """WCAG 2.1 contrast ratio between two ``#RRGGBB`` colours (1..21)."""
    first = relative_luminance(text)
    second = relative_luminance(background)
    lighter, darker = max(first, second), min(first, second)
    return round((lighter + 0.05) / (darker + 0.05), 2)


def contrast_failures(tokens: BrandTokens | None = None) -> list[str]:
    """Return the declared pairs that do not reach their minimum ratio."""
    settings = tokens or BrandTokens()
    palette = settings.palette
    failures: list[str] = []
    for pair in settings.contrast_pairs:
        ratio = contrast_ratio(palette.get(pair.text), palette.get(pair.background))
        if ratio < pair.minimum:
            failures.append(f"{pair.text}/{pair.background}: {ratio} < {pair.minimum}")
    return failures
