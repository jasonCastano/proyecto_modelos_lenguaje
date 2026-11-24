"""Identidad del remitente del canal (spec 024, research R7, data-model §1).

El número de teléfono nunca se guarda ni se registra: se normaliza a E.164, se convierte en un
seudónimo ``wa-<16 hex>`` con HMAC-SHA256 y una sal secreta (``VALERIA_CHANNEL_SALT``) y se
descarta. Para mostrar al equipo solo existe la máscara con los últimos cuatro dígitos.
"""

from __future__ import annotations

import hashlib
import hmac
import os
import re

SALT_ENV = "VALERIA_CHANNEL_SALT"
E164 = re.compile(r"^\+[1-9]\d{7,14}$")
WHATSAPP_JID = re.compile(
    r"^(?:whatsapp:)?\+?([1-9]\d{7,14})(?::\d+)?(?:@(?:s\.whatsapp\.net|c\.us))?$"
)
TELEGRAM = re.compile(r"^(?:tg:|telegram:)?(\d{1,20})$")
PREFIXES = {"whatsapp": "wa", "telegram": "tg"}


class SenderError(ValueError):
    """Remitente con formato inválido o canal no soportado."""


def normalize_sender(raw: str, channel: str = "whatsapp") -> str:
    """E.164 para WhatsApp (acepta JID ``573…@s.whatsapp.net``) y ``tg:<id>`` para Telegram."""
    value = (raw or "").strip().replace(" ", "")
    if channel == "whatsapp":
        match = WHATSAPP_JID.match(value)
        if match is None:
            raise SenderError("El remitente de WhatsApp debe ser un número E.164.")
        number = f"+{match.group(1)}"
        if not E164.match(number):
            raise SenderError("El remitente de WhatsApp debe ser un número E.164.")
        return number
    if channel == "telegram":
        match = TELEGRAM.match(value)
        if match is None:
            raise SenderError("El remitente de Telegram debe ser un id numérico.")
        return f"tg:{match.group(1)}"
    raise SenderError(f"Canal no soportado: {channel}.")


def channel_salt() -> str:
    salt = os.environ.get(SALT_ENV, "").strip()
    if len(salt) < 16:
        raise SenderError(f"Falta {SALT_ENV} (mínimo 16 caracteres) para seudonimizar remitentes.")
    return salt


def pseudonym(sender: str, salt: str, channel: str = "whatsapp") -> str:
    """``wa-``/``tg-`` + 16 hex de HMAC-SHA256: estable, irreversible sin la sal."""
    normalized = normalize_sender(sender, channel)
    digest = hmac.new(salt.encode("utf-8"), normalized.encode("utf-8"), hashlib.sha256)
    return f"{PREFIXES[channel]}-{digest.hexdigest()[:16]}"


def mask(sender: str, channel: str = "whatsapp") -> str:
    """``+57 ••• ••• 4567``: solo para mostrar al equipo, nunca en archivos versionados."""
    normalized = normalize_sender(sender, channel)
    if channel == "telegram":
        return f"tg:•••{normalized[-3:]}"
    digits = normalized[1:]
    return f"+{digits[:2]} ••• ••• {digits[-4:]}"
