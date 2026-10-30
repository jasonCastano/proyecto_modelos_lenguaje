"""Unit tests for Linktree parsing and official-channel config."""

from __future__ import annotations

from proyecto_modelos_lenguaje.config import load_config
from proyecto_modelos_lenguaje.extractors.linktree import parse_linktree


def test_parse_linktree_extracts_links() -> None:
    html = """
    <html><body>
    <script id="__NEXT_DATA__" type="application/json">
    {"props":{"pageProps":{"account":{"username":"manuelitaagroindustria",
    "pageTitle":"@manuelitaagroindustria","description":null,
    "profilePictureUrl":"https://example.com/pic.png","socialLinks":[]},
    "links":[{"title":"Portal Manuelita","url":"https://www.manuelita.com/","position":1},
    {"title":"Sostenibilidad","url":"https://www.manuelita.com/sostenibilidad/","position":2}]}}}
    </script>
    </body></html>
    """
    payload = parse_linktree(html)
    assert payload is not None
    assert payload["username"] == "manuelitaagroindustria"
    assert len(payload["links"]) == 2
    assert payload["links"][0]["url"] == "https://www.manuelita.com/"


def test_parse_linktree_without_data_returns_none() -> None:
    assert parse_linktree("<html><body>no data</body></html>") is None


def test_official_channels_config_has_four_sources() -> None:
    config = load_config("config/official_channels.toml")
    assert {source.source_id for source in config.sources} == {
        "youtube",
        "linktree",
        "instagram",
        "fundacion_manuelita",
    }
    assert all(source.enabled for source in config.sources)
