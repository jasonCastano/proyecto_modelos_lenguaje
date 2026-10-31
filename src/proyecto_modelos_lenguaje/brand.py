"""Identidad visual del Módulo 1 inspirada en Grupo Manuelita.

La paleta se extrae del logotipo público del sitio oficial (los `fill` del SVG) y se aplica con el
tema nativo de Streamlit más una hoja de estilos propia. El módulo no contiene HTML no confiable:
todos los fragmentos se generan a partir de tokens y de datos ya validados por las tareas.

Ver `specs/009-manuelita-visual-identity/` (spec, plan, contrato y modelo de datos).
"""

from __future__ import annotations

import html
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


def brand_css(tokens: BrandTokens | None = None) -> str:
    """Static stylesheet for the identity. Contains no remote resources."""
    settings = tokens or BrandTokens()
    palette = settings.palette
    scale = settings.type_scale
    return f"""
:root {{
  --pml-forest: {palette.forest};
  --pml-orange: {palette.orange};
  --pml-lime: {palette.lime};
  --pml-surface: {palette.surface};
  --pml-ink: {palette.ink};
  --pml-muted: {palette.ink_muted};
  --pml-radius: {settings.radius}px;
}}
html, body, [class*="st-"] {{
  font-family: {settings.font_stack};
}}
h1 {{
  color: var(--pml-forest);
  font-size: {scale["display"]}px;
  line-height: 1.15;
  letter-spacing: -0.01em;
  margin-bottom: {settings.spacing_unit // 2}px;
}}
h2 {{
  color: var(--pml-forest);
  font-size: {scale["heading"]}px;
  margin-top: {settings.spacing_unit * 2}px;
}}
h3 {{
  color: var(--pml-ink);
  font-size: {scale["body"] + 2}px;
}}
a, a:visited {{
  color: var(--pml-orange);
  text-decoration: underline;
  text-decoration-color: var(--pml-lime);
  text-underline-offset: 3px;
}}
a:hover {{
  color: var(--pml-forest);
}}
a:focus-visible, button:focus-visible {{
  outline: 3px solid var(--pml-lime);
  outline-offset: 2px;
}}
[data-testid="stSidebar"] {{
  background: var(--pml-surface);
  border-right: 3px solid var(--pml-forest);
}}
[data-testid="stMetricValue"] {{
  color: var(--pml-forest);
}}
[data-testid="stMarkdownContainer"] p {{
  font-size: {scale["body"]}px;
  line-height: 1.6;
  color: var(--pml-ink);
}}
blockquote {{
  border-left: 4px solid var(--pml-lime);
  background: var(--pml-surface);
  padding: {settings.spacing_unit}px {settings.spacing_unit * 2}px;
  margin: 0;
}}
.pml-header {{
  border-bottom: 4px solid var(--pml-forest);
  padding-bottom: {settings.spacing_unit * 2}px;
  margin-bottom: {settings.spacing_unit * 2}px;
}}
.pml-brand {{
  color: var(--pml-forest);
  font-size: {scale["heading"]}px;
  font-weight: 700;
  letter-spacing: 0.02em;
  margin: 0;
}}
.pml-brand span {{
  color: var(--pml-orange);
}}
.pml-project {{
  color: var(--pml-ink);
  font-size: {scale["display"]}px;
  font-weight: 700;
  margin: {settings.spacing_unit}px 0 {settings.spacing_unit // 2}px;
}}
.pml-tagline {{
  color: var(--pml-muted);
  font-size: {scale["caption"]}px;
  margin: 0;
}}
.pml-note {{
  color: var(--pml-muted);
  font-size: {scale["caption"]}px;
  margin: {settings.spacing_unit // 2}px 0 0;
  border-left: 3px solid var(--pml-lime);
  padding-left: {settings.spacing_unit}px;
}}
.pml-status {{
  display: flex;
  flex-wrap: wrap;
  gap: {settings.spacing_unit}px;
  margin-top: {settings.spacing_unit * 1.5}px;
}}
.pml-chip {{
  border: 1px solid var(--pml-forest);
  border-radius: 999px;
  padding: 2px {settings.spacing_unit}px;
  font-size: {scale["caption"]}px;
  color: var(--pml-forest);
  background: var(--pml-surface);
}}
.pml-chip.is-demo {{
  border-color: var(--pml-orange);
  color: var(--pml-orange);
}}
.pml-source {{
  border-left: 4px solid var(--pml-orange);
  background: var(--pml-surface);
  border-radius: 0 var(--pml-radius) var(--pml-radius) 0;
  padding: {settings.spacing_unit}px {settings.spacing_unit * 2}px;
  margin: 0 0 {settings.spacing_unit}px;
}}
.pml-source .pml-label {{
  color: var(--pml-orange);
  font-weight: 700;
}}
.pml-source .pml-title {{
  color: var(--pml-ink);
  font-weight: 600;
}}
.pml-source .pml-location {{
  color: var(--pml-muted);
  font-size: {scale["caption"]}px;
  display: block;
}}
.pml-source a {{
  font-size: {scale["caption"]}px;
}}
.pml-footer {{
  border-top: 3px solid var(--pml-lime);
  margin-top: {settings.spacing_unit * 4}px;
  padding-top: {settings.spacing_unit * 2}px;
  color: var(--pml-muted);
  font-size: {scale["caption"]}px;
}}
.pml-footer p {{
  margin: 0 0 {settings.spacing_unit // 2}px;
}}
""".strip()


def inject_brand_styles(tokens: BrandTokens | None = None) -> None:
    """Inject the stylesheet once per session using ``st.html`` (no unsafe HTML)."""
    import streamlit as st

    if st.session_state.get("_pml_brand_styles"):
        return
    st.html(f"<style>{brand_css(tokens)}</style>")
    st.session_state["_pml_brand_styles"] = True


def _escape(value: str) -> str:
    return html.escape(value, quote=True)


def header_html(tokens: BrandTokens | None = None) -> str:
    """Brand header: institutional signature, project name, tagline and academic note."""
    settings = tokens or BrandTokens()
    return (
        '<div class="pml-header">'
        '<p class="pml-brand">Grupo Manuelita <span>· Ingenio Manuelita</span></p>'
        f'<p class="pml-project">{_escape(settings.project_name)}</p>'
        f'<p class="pml-tagline">{_escape(settings.tagline)}</p>'
        f'<p class="pml-note">{_escape(settings.affiliation_note)}</p>'
        "</div>"
    )


def status_bar_html(items: list[tuple[str, str, str]]) -> str:
    """Persistent status chips. ``items`` are ``(key, icon, label)`` tuples."""
    chips: list[str] = []
    for key, icon, label in items:
        demo_class = " is-demo" if key == "demo" else ""
        chips.append(f'<span class="pml-chip{demo_class}">{_escape(icon)} {_escape(label)}</span>')
    return f'<div class="pml-status">{"".join(chips)}</div>'


def source_card_html(citation: Any) -> str:
    """One source card: label, document title, location and verifiable link."""
    label = _escape(str(getattr(citation, "label", "")))
    title = _escape(str(getattr(citation, "title", "")))
    url = str(getattr(citation, "url", ""))
    location = _escape(citation_location(citation))
    return (
        '<div class="pml-source">'
        f'<span class="pml-label">[{label}]</span> '
        f'<span class="pml-title">{title}</span>'
        f'<span class="pml-location">{location}</span>'
        f'<a href="{_escape(url)}" target="_blank" rel="noopener noreferrer">{_escape(url)}</a>'
        "</div>"
    )


def source_cards_html(citations: Any) -> str:
    """Render every citation as a card; empty input yields a neutral note."""
    cards = [source_card_html(citation) for citation in citations]
    if not cards:
        return f'<p class="pml-tagline">{_escape("Sin fuentes citadas.")}</p>'
    return "".join(cards)


def citation_location(citation: Any) -> str:
    """Human location of a citation; never empty."""
    section = " > ".join(getattr(citation, "section_path", ()) or ())
    location = f"sección: {section}" if section else "sin sección declarada"
    page_start = getattr(citation, "page_start", None)
    time_start = getattr(citation, "time_start", None)
    if page_start is not None:
        location += f", p. {page_start}"
    if time_start is not None:
        location += f", {int(time_start)} s"
    return location


def footer_html(tokens: BrandTokens | None = None) -> str:
    """Academic notice plus trademark attribution."""
    settings = tokens or BrandTokens()
    return (
        '<div class="pml-footer">'
        f"<p>{_escape(settings.affiliation_note)}</p>"
        f"<p>{_escape(settings.attribution)}</p>"
        "</div>"
    )
