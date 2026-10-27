"""Unit tests for language and MIME detection."""

from __future__ import annotations

from proyecto_modelos_lenguaje.extractors.language import detect_language
from proyecto_modelos_lenguaje.extractors.metadata import (
    detect_media_type,
    extension_for,
    parse_published_at,
)


def test_declared_html_language_wins() -> None:
    assert detect_language("es-CO", "texto irrelevante") == ("es", "html_lang")
    assert detect_language("en", "texto irrelevante") == ("en", "html_lang")


def test_spanish_heuristic() -> None:
    text = (
        "La empresa colombiana trabaja por el desarrollo sostenible de la comunidad "
        "y la caña de azúcar en Colombia desde el año 1901."
    )
    assert detect_language(None, text) == ("es", "heuristic")


def test_english_heuristic() -> None:
    text = (
        "The company works for the sustainable development of the community and "
        "the sugar cane industry in Colombia from the year 1901."
    )
    assert detect_language(None, text) == ("en", "heuristic")


def test_short_text_is_undetermined() -> None:
    assert detect_language(None, "Hola") == ("und", "unknown")


def test_media_type_detection() -> None:
    assert detect_media_type("application/pdf", b"%PDF-1.7 data") == "application/pdf"
    assert detect_media_type(None, b"%PDF-1.7 data") == "application/pdf"
    assert detect_media_type("text/html; charset=utf-8", b"<!doctype html>") == "text/html"
    assert detect_media_type(None, b'{"a": 1}') == "application/json"
    assert detect_media_type(None, b"WEBVTT\n\n00:00.000 --> 00:01.000\nHola") == "text/vtt"
    assert extension_for("application/pdf") == ".pdf"
    assert extension_for("text/html") == ".html"


def test_parse_published_at() -> None:
    assert parse_published_at("2026-10-01T12:00:00Z") == "2026-10-01T12:00:00Z"
    assert parse_published_at("Thu, 01 Oct 2026 12:00:00 GMT") == "2026-10-01T12:00:00Z"
    assert parse_published_at("not-a-date") is None
