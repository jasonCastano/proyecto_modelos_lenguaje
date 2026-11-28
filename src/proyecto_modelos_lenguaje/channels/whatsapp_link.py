"""Enlace de la pestaña WhatsApp de la web (spec 032).

El número de la SIM vive solo en ``VALERIA_WHATSAPP_NUMBER`` (el ``.env`` del proyecto, fuera de
Git; constitución §9). Este módulo lo valida en formato E.164 y arma lo que la web necesita: el
enlace a WhatsApp Web (computador), el enlace ``wa.me`` (teléfono y QR) y el QR en SVG generado aquí
con ``segno``, sin servicios externos. El número nunca se escribe en registros (§10).
"""

from __future__ import annotations

import logging
import os
import re
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Literal
from urllib.parse import quote

import segno

from ..ops import OPENCLAW_DIR, channel_mode

log = logging.getLogger(__name__)

ENV_VAR = "VALERIA_WHATSAPP_NUMBER"
MESSAGE = "Hola, Valer-IA"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")
QR_DARK = "#14240f"
QR_LIGHT = "#ffffff"

ChannelMode = Literal["open", "closed", "unknown"]


@dataclass(frozen=True)
class WhatsAppLinkData:
    available: bool
    mode: ChannelMode
    message: str
    web_url: str | None
    app_url: str | None
    qr_svg: str | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def normalize_number(raw: str | None) -> str | None:
    """Dígitos del número si ``raw`` es E.164 (se toleran espacios); ``None`` si no."""
    if raw is None:
        return None
    compact = raw.replace(" ", "").strip()
    return compact[1:] if E164.match(compact) else None


def qr_svg(content: str) -> str:
    """QR en SVG (corrección M, borde de 4 módulos), sin declaración XML, listo para insertar.

    Con ``viewBox`` y sin ancho ni alto fijos (``omitsize``): la web lo escala sin recortarlo.
    """
    code = segno.make(content, error="m")
    return code.svg_inline(scale=8, border=4, dark=QR_DARK, light=QR_LIGHT, omitsize=True)


def _mode(env: Mapping[str, str]) -> ChannelMode:
    configured = env.get("OPENCLAW_STATE_DIR", "").strip()
    base = Path(configured) if configured else Path.home() / OPENCLAW_DIR
    result = channel_mode(base)
    if not result.ok:
        return "unknown"
    return "open" if result.detail.startswith("ABIERTO") else "closed"


def build_link(env: Mapping[str, str] | None = None) -> WhatsAppLinkData:
    """Lo que la pestaña necesita; sin número válido, ``available=False`` y sin enlaces (SC-004)."""
    env = os.environ if env is None else env
    raw = env.get(ENV_VAR, "")
    digits = normalize_number(raw)
    mode = _mode(env)
    if digits is None:
        if raw.strip():
            log.warning(
                "whatsapp_link: formato inválido en %s (se esperaba +57 y 10 dígitos)", ENV_VAR
            )
        return WhatsAppLinkData(False, mode, MESSAGE, None, None, None)
    text = quote(MESSAGE, safe="")
    app_url = f"https://wa.me/{digits}?text={text}"
    web_url = f"https://web.whatsapp.com/send?phone={digits}&text={text}"
    return WhatsAppLinkData(True, mode, MESSAGE, web_url, app_url, qr_svg(app_url))
