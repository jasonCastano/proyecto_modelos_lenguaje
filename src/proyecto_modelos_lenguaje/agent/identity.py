"""Reconocimiento conversacional de clientes por correo (spec 018, contracts/identity-flow.md).

Regla de privacidad: el correo en claro solo vive en memoria mientras se procesa el turno. Lo que se
guarda o se pasa al grafo es su huella ``HMAC-SHA256(clave, correo normalizado)``; el modelo de
lenguaje nunca ve el correo (el mensaje del hilo se redacta como antes).
"""

from __future__ import annotations

import contextlib
import hashlib
import hmac
import os
import re
import secrets
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal

from langgraph.store.base import BaseStore

from .privacy import detect_email

KEY_ENV = "MANUELITA_IDENTITY_KEY"
KEY_FILE = "identity.key"
MIN_KEY_LENGTH = 32
IDENTITIES_NAMESPACE: tuple[str, ...] = ("identities",)
MAX_THREAD_ATTEMPTS = 3
LOCK_FAILURES = 5
LOCK_WINDOW = timedelta(hours=1)

EMAIL_SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]{2,}$")
# «el correo de mi jefe es…»: un correo ajeno nunca identifica.
THIRD_PARTY_EMAIL = re.compile(
    r"\b(de mi|de su|del|de la|de los|de las)\s+\w+[^.@]{0,30}\b(correo|email|mail)\b|"
    r"\b(correo|email|mail)\s+(de|del)\s+(mi|su|tu|la|el)\s+\w+"
)
# Reinicio explícito (siempre) y «no soy Ana» (solo si el hilo reconoció a alguien).
RESET = re.compile(
    r"\b(soy otra persona|empecemos de nuevo|empezar de nuevo|comenzar de nuevo|"
    r"empezar desde cero|nuevo cliente|cambiar de usuario)\b"
)
NOT_ME = re.compile(r"\b[Nn]o soy ([A-ZÁÉÍÓÚÑ][a-záéíóúñ]+)")
NOT_A_NAME = re.compile(r"[?¿!¡@\d]")


class IdentityKeyError(ValueError):
    """La clave de identidad configurada es inválida."""


def _plain(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text or "")
    stripped = "".join(char for char in decomposed if not unicodedata.combining(char))
    return re.sub(r"\s+", " ", stripped).strip().casefold()


def normalize_email(email: str) -> str:
    return (email or "").strip().casefold()


def valid_email(email: str) -> bool:
    return bool(EMAIL_SHAPE.match(normalize_email(email)))


def fingerprint(key: str, email: str) -> str:
    """Huella HMAC-SHA256 (64 caracteres hex) del correo normalizado."""
    return hmac.new(
        key.encode("utf-8"), normalize_email(email).encode("utf-8"), hashlib.sha256
    ).hexdigest()


def mask_email(email: str) -> str:
    local, _, domain = normalize_email(email).partition("@")
    return f"{local[:1]}***@{domain}" if local and domain else "***"


def load_key(state_dir: Path | None) -> str:
    """Clave HMAC: ``MANUELITA_IDENTITY_KEY`` o, si falta, ``identity.key`` en el estado."""
    configured = os.environ.get(KEY_ENV, "").strip()
    if configured:
        if len(configured) < MIN_KEY_LENGTH:
            raise IdentityKeyError(f"{KEY_ENV} debe tener al menos {MIN_KEY_LENGTH} caracteres.")
        return configured
    if state_dir is None:
        raise IdentityKeyError(f"Define {KEY_ENV} o un directorio de estado.")
    path = Path(state_dir) / KEY_FILE
    if path.is_file():
        stored = path.read_text(encoding="utf-8").strip()
        if len(stored) >= MIN_KEY_LENGTH:
            return stored
    path.parent.mkdir(parents=True, exist_ok=True)
    generated = secrets.token_hex(32)
    path.write_text(generated, encoding="utf-8")
    with contextlib.suppress(OSError):
        path.chmod(0o600)
    return generated


def names_match(registered: str, given: str) -> bool:
    """Coinciden sin tildes ni mayúsculas, completos o por el primer nombre."""
    left, right = _plain(registered), _plain(given)
    if not left or not right:
        return False
    if left == right:
        return True
    return left.split()[0] == right.split()[0]


def looks_like_name(text: str) -> bool:
    """Respuesta breve que parece un nombre (para la confirmación)."""
    clean = (text or "").strip().strip(".")
    words = clean.split()
    return 0 < len(words) <= 5 and not NOT_A_NAME.search(clean)


def extract_name(text: str) -> str:
    """«Me llamo Ana», «soy Ana María», «Ana» → «Ana» / «Ana María»."""
    clean = (text or "").strip().strip(".")
    match = re.search(r"(?i)\b(?:me llamo|mi nombre es|soy)\s+(.+)$", clean)
    name = match.group(1) if match else clean
    name = re.split(r"[,.;]| y mi | y el | correo", name, maxsplit=1)[0].strip()
    return " ".join(word.capitalize() if word.islower() else word for word in name.split()[:4])


IdentityKind = Literal["email", "reset"]


@dataclass(frozen=True, slots=True)
class IdentityEvent:
    kind: IdentityKind
    fingerprint: str | None = None
    masked: str | None = None
    valid: bool = True
    explicit: bool = True  # reinicio: False para «no soy Ana» (solo aplica a un cliente reconocido)

    def to_dict(self) -> dict[str, Any]:
        return {
            "kind": self.kind,
            "fingerprint": self.fingerprint,
            "masked": self.masked,
            "valid": self.valid,
            "explicit": self.explicit,
        }


def detect_identity_event(message: str, key: str | None) -> IdentityEvent | None:
    """Evento de identidad del mensaje original (antes de redactar). El correo no sale de aquí."""
    plain = _plain(message)
    emails = detect_email(message or "")
    if len(emails) == 1 and not THIRD_PARTY_EMAIL.search(plain) and key:
        raw = emails[0]["value"]
        if not valid_email(raw):
            return IdentityEvent(kind="email", valid=False)
        return IdentityEvent(
            kind="email", fingerprint=fingerprint(key, raw), masked=mask_email(raw)
        )
    if not emails and RESET.search(plain):
        return IdentityEvent(kind="reset")
    if not emails and NOT_ME.search(message or "") and len((message or "").split()) <= 6:
        return IdentityEvent(kind="reset", explicit=False)
    return None


class IdentityRegistry:
    """Vínculos huella → cliente y fallos de confirmación en el Store de LangGraph."""

    def __init__(self, store: BaseStore) -> None:
        self.store = store

    def lookup(self, fp: str) -> str | None:
        item = self.store.get(IDENTITIES_NAMESPACE, fp)
        return str(item.value.get("user_id")) if item and item.value.get("user_id") else None

    def link(self, fp: str, user_id: str) -> None:
        self.store.put(
            IDENTITIES_NAMESPACE,
            fp,
            {"user_id": user_id, "created_at": datetime.now(UTC).isoformat()},
        )

    def unlink_user(self, user_id: str) -> int:
        removed = 0
        for item in self.store.search(IDENTITIES_NAMESPACE, limit=10_000):
            if item.value.get("user_id") == user_id:
                self.store.delete(IDENTITIES_NAMESPACE, item.key)
                removed += 1
        return removed

    def _failures_ns(self, fp: str) -> tuple[str, ...]:
        return ("identity_failures", fp)

    def record_failure(self, fp: str, *, now: datetime | None = None) -> None:
        moment = now or datetime.now(UTC)
        self.store.put(self._failures_ns(fp), secrets.token_hex(8), {"at": moment.isoformat()})

    def is_locked(self, fp: str, *, now: datetime | None = None) -> bool:
        moment = now or datetime.now(UTC)
        recent = 0
        for item in self.store.search(self._failures_ns(fp), limit=1_000):
            at = datetime.fromisoformat(str(item.value.get("at")))
            if moment - at <= LOCK_WINDOW:
                recent += 1
            else:
                self.store.delete(self._failures_ns(fp), item.key)
        return recent >= LOCK_FAILURES
