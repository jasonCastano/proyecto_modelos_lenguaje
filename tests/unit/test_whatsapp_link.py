"""Enlace de la pestaña WhatsApp (spec 032): número E.164, enlaces, QR, modo y privacidad.

Solo se usan números ficticios armados en la prueba; ningún número real entra al repositorio.
"""

from __future__ import annotations

import logging
import re
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.channels import whatsapp_link as wl

# Número ficticio: indicativo de Colombia y un celular inventado de 10 dígitos.
FAKE_DIGITS = "57" + "3" + "1" * 9
FAKE_NUMBER = "+" + FAKE_DIGITS
MESSAGE_QUERY = "Hola%2C%20Valer-IA"


def _env(tmp_path: Path, number: str | None = None, policy: str | None = None) -> dict[str, str]:
    state = tmp_path / "openclaw"
    env = {"OPENCLAW_STATE_DIR": str(state)}
    if number is not None:
        env[wl.ENV_VAR] = number
    if policy is not None:
        state.mkdir(parents=True, exist_ok=True)
        (state / ".env").write_text(f"WA_DM_POLICY={policy}\nWA_ALLOW_1=*\n", encoding="utf-8")
    return env


# --------------------------------------------------------------------------- normalize_number


def test_normalize_accepts_colombian_e164() -> None:
    assert wl.normalize_number(FAKE_NUMBER) == FAKE_DIGITS


def test_normalize_strips_spaces() -> None:
    spaced = f"+57 {FAKE_DIGITS[2:5]} {FAKE_DIGITS[5:8]} {FAKE_DIGITS[8:]}"
    assert wl.normalize_number(spaced) == FAKE_DIGITS


@pytest.mark.parametrize(
    "raw",
    [
        FAKE_DIGITS,  # sin «+»
        "+57abc1111111",  # letras
        f"+57-{FAKE_DIGITS[2:]}",  # guiones
        "+5731",  # menos de 8 dígitos
        "+0" + "1" * 10,  # no empieza por 1-9
        "",
        "   ",
    ],
)
def test_normalize_rejects_invalid(raw: str) -> None:
    assert wl.normalize_number(raw) is None


# --------------------------------------------------------------------------- build_link


def test_build_link_with_valid_number(tmp_path: Path) -> None:
    link = wl.build_link(_env(tmp_path, FAKE_NUMBER))
    assert link.available is True
    assert link.message == "Hola, Valer-IA"
    assert link.web_url == f"https://web.whatsapp.com/send?phone={FAKE_DIGITS}&text={MESSAGE_QUERY}"
    assert link.app_url == f"https://wa.me/{FAKE_DIGITS}?text={MESSAGE_QUERY}"
    assert "+" not in link.web_url and "+" not in link.app_url
    assert link.qr_svg is not None and link.qr_svg.startswith("<svg")


@pytest.mark.parametrize("number", [None, "", "+57abc", FAKE_DIGITS])
def test_unavailable_has_no_links(tmp_path: Path, number: str | None) -> None:
    link = wl.build_link(_env(tmp_path, number))
    assert link.available is False
    assert link.web_url is None and link.app_url is None and link.qr_svg is None


def test_invalid_number_is_logged_without_value(
    tmp_path: Path, caplog: pytest.LogCaptureFixture
) -> None:
    bad = FAKE_NUMBER.replace("+", "")
    with caplog.at_level(logging.WARNING):
        wl.build_link(_env(tmp_path, bad))
    assert "whatsapp_link: formato inválido" in caplog.text
    assert bad not in caplog.text and FAKE_DIGITS[2:] not in caplog.text


def test_missing_number_is_not_an_error(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING):
        wl.build_link(_env(tmp_path, None))
    assert "formato inválido" not in caplog.text


# --------------------------------------------------------------------------- modo del canal


@pytest.mark.parametrize(
    ("policy", "expected"), [("open", "open"), ("allowlist", "closed"), (None, "unknown")]
)
def test_mode_from_gateway_env(tmp_path: Path, policy: str | None, expected: str) -> None:
    assert wl.build_link(_env(tmp_path, FAKE_NUMBER, policy)).mode == expected


# --------------------------------------------------------------------------- QR (US2)


def test_qr_encodes_exactly_the_app_url(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    encoded: list[str] = []
    real_make = wl.segno.make

    def spy(content: str, **kwargs: object) -> object:
        encoded.append(content)
        return real_make(content, **kwargs)

    monkeypatch.setattr(wl.segno, "make", spy)
    link = wl.build_link(_env(tmp_path, FAKE_NUMBER))
    assert encoded == [link.app_url]
    assert link.qr_svg is not None
    assert not link.qr_svg.lstrip().startswith("<?xml")
    assert "#14240f" in link.qr_svg
    # Escalable: viewBox y sin ancho fijo, para que la web no lo recorte.
    assert "viewBox=" in link.qr_svg and "width=" not in link.qr_svg.split(">", 1)[0]


# --------------------------------------------------------------------------- SC-003


MOBILE_CO = re.compile(r"\+?57 ?3\d{2} ?\d{3} ?\d{4}")
SCANNED = ("web/src", "config", "openclaw")
SUFFIXES = {".ts", ".tsx", ".css", ".json", ".json5", ".toml", ".md", ".js", ".mjs", ".html"}


def test_no_colombian_mobile_number_in_versioned_sources() -> None:
    root = Path(__file__).resolve().parents[2]
    hits = []
    for folder in SCANNED:
        for path in (root / folder).rglob("*"):
            # Las pruebas usan el número ficticio del proyecto; se revisan código y configuración.
            skip = {"node_modules", "test", "tests"} & set(path.parts)
            if skip or not path.is_file() or path.suffix not in SUFFIXES:
                continue
            if MOBILE_CO.search(path.read_text(encoding="utf-8", errors="ignore")):
                hits.append(str(path.relative_to(root)))
    assert hits == []
