"""Integration tests for the three medallion pages (bronze, silver, gold)."""

from __future__ import annotations

from pathlib import Path

import pytest
from streamlit.testing.v1 import AppTest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT


def _script() -> None:
    """Rendered inside AppTest; the page is chosen through environment variables."""

    from tests.app_page_helpers import render_page_from_env

    render_page_from_env()


def _run(monkeypatch: pytest.MonkeyPatch, page: str, *, incomplete: bool = False) -> AppTest:
    monkeypatch.setenv("PML_TEST_PAGE", page)
    monkeypatch.setenv("PML_TEST_INCOMPLETE", "1" if incomplete else "0")
    app = AppTest.from_function(_script).run()
    assert not app.exception
    return app


def _texts(app: AppTest, element: str) -> list[str]:
    values: list[str] = []
    for item in app.get(element):
        for attribute in ("value", "body", "label"):
            if hasattr(item, attribute):
                values.append(str(getattr(item, attribute)))
    return values


def test_bronze_page_explains_the_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run(monkeypatch, "bronze")
    assert any("Capa bronce" in text for text in _texts(app, "subheader"))
    joined = " ".join(_texts(app, "markdown"))
    assert "bytes originales" in joined
    assert "SHA-256" in joined
    assert "cuarentena" in joined.lower()
    labels = [str(item.label) for item in app.get("metric")]
    assert "Artefactos activos" in labels
    assert any("data/bronze" in text for text in _texts(app, "code"))


def test_silver_page_explains_the_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run(monkeypatch, "silver")
    assert any("Capa plata" in text for text in _texts(app, "subheader"))
    joined = " ".join(_texts(app, "markdown"))
    assert "texto legible y citable" in joined
    assert "chunks" in joined
    labels = [str(item.label) for item in app.get("metric")]
    assert "Documentos canónicos" in labels
    values = [str(item.value) for item in app.get("metric")]
    assert "226" in values
    assert any("data/silver" in text for text in _texts(app, "code"))


def test_gold_page_explains_the_layer(monkeypatch: pytest.MonkeyPatch) -> None:
    app = _run(monkeypatch, "gold")
    assert any("Capa oro" in text for text in _texts(app, "subheader"))
    joined = " ".join(_texts(app, "markdown"))
    assert "base de conocimiento" in joined
    assert "Conflictos" in joined
    values = [str(item.value) for item in app.get("metric")]
    assert "15.211" in values
    assert "24/24" in values
    assert any("data/gold" in text for text in _texts(app, "code"))


@pytest.mark.parametrize("page", ["bronze", "silver", "gold"])
def test_pages_warn_when_data_is_incomplete(monkeypatch: pytest.MonkeyPatch, page: str) -> None:
    app = _run(monkeypatch, page, incomplete=True)
    assert app.warning
    assert any("git lfs pull" in str(item.value) for item in app.warning)


def test_navigation_declares_the_three_medallion_pages() -> None:
    source = Path(PROJECT_ROOT / "app.py").read_text(encoding="utf-8")
    for title, path in (("Bronce", "bronce"), ("Plata", "plata"), ("Oro", "oro")):
        assert f'title="{title}"' in source
        assert f'url_path="{path}"' in source
    assert "st.navigation(pages).run()" in source
    assert 'title="Consulta"' in source
