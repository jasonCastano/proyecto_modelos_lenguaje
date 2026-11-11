"""Redacción de datos personales antes de persistir (spec 014, FR-010).

Usa los detectores de LangChain para correo y tarjeta, y patrones propios para teléfono y documento
de identidad colombianos. La misma política se aplica en tres puntos:

1. al mensaje del usuario antes de guardarlo en el hilo (checkpointer);
2. al valor de una preferencia antes de escribirla en el Store;
3. a la entrada del modelo en la variante agente, con ``PIIMiddleware`` en modo ``redact``.
"""

from __future__ import annotations

import re
from collections.abc import Callable

from langchain.agents.middleware import PIIMiddleware
from langchain.agents.middleware.pii import (
    PIIMatch,
    apply_strategy,
    detect_credit_card,
    detect_email,
)

PHONE_PATTERN = re.compile(
    r"(?<![\w.])(?:\+?57[\s.-]?)?(?:3\d{2}[\s.-]?\d{3}[\s.-]?\d{4}|60\d[\s.-]?\d{3}[\s.-]?\d{4})(?![\w.])"
)
DOCUMENT_PATTERN = re.compile(
    r"(?i)\b(?:c\.?\s?c\.?|cedula|cédula|documento|nit|pasaporte|t\.?\s?i\.?)"
    r"(?:\s+(?:es|de\s+ciudadan[ií]a|de\s+identidad|n(?:o|ú|u)?\.?|n[uú]mero))*"
    r"[\s:#.-]*\d[\d.\s-]{4,14}\d"
)


def _regex_detector(kind: str, pattern: re.Pattern[str]) -> Callable[[str], list[PIIMatch]]:
    def detect(text: str) -> list[PIIMatch]:
        return [
            PIIMatch(type=kind, value=match.group(0), start=match.start(), end=match.end())
            for match in pattern.finditer(text)
        ]

    return detect


detect_phone = _regex_detector("phone", PHONE_PATTERN)
detect_document = _regex_detector("document", DOCUMENT_PATTERN)

DETECTORS: dict[str, Callable[[str], list[PIIMatch]]] = {
    "email": detect_email,
    "credit_card": detect_credit_card,
    "document": detect_document,
    "phone": detect_phone,
}


def find_pii(text: str) -> list[PIIMatch]:
    """Coincidencias de datos personales sin solaparse (gana la primera detectada)."""
    matches: list[PIIMatch] = []
    for detector in DETECTORS.values():
        for match in detector(text or ""):
            overlaps = any(
                match["start"] < other["end"] and other["start"] < match["end"] for other in matches
            )
            if not overlaps:
                matches.append(match)
    return matches


def redact_pii(text: str) -> str:
    """Reemplaza cada dato personal por ``[REDACTED_<TIPO>]``, como ``PIIMiddleware``."""
    matches = find_pii(text)
    return apply_strategy(text, matches, "redact") if matches else text


def build_pii_middleware() -> list[PIIMiddleware]:
    """``PIIMiddleware`` en modo ``redact`` para la entrada del agente (correo, tarjeta, documento,
    teléfono)."""
    return [
        PIIMiddleware(kind, strategy="redact", detector=detector, apply_to_input=True)
        for kind, detector in DETECTORS.items()
    ]
