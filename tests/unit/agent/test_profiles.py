"""Perfiles de la plataforma de agentes (spec 025, T006, contracts/profiles.md)."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.agent import profiles
from proyecto_modelos_lenguaje.agent.catalog import catalog
from proyecto_modelos_lenguaje.agent.profiles import (
    PROFILE_KEYS,
    ProfileError,
    is_authorized,
    load_profiles,
    match_trigger,
    profile_focus,
    resolve_alias,
)

SPEC_024_READ = {
    "search_documents",
    "query_structured",
    "aggregate_series",
    "list_indicators",
    "compare_indicator",
    "sustainability_lookup",
    "list_business_units",
    "list_company_entities",
    "get_official_channels",
    "faq_lookup",
    "summarize_topic",
    "latest_news",
    "get_fragment",
    "calculate",
    "get_my_profile",
}


def test_five_profiles_loaded() -> None:
    loaded = load_profiles()
    assert tuple(loaded) == PROFILE_KEYS
    assert [p.key for p in loaded.values() if p.requires_authorization] == ["planificador"]
    for profile in loaded.values():
        assert 3 <= len(profile.label) <= 40


def test_visitante_offers_exactly_spec_024_reads() -> None:
    assert set(load_profiles()["visitante"].tools) == SPEC_024_READ


def test_tools_exist_in_catalog() -> None:
    names = {spec.name for spec in catalog()}
    for profile in load_profiles().values():
        assert set(profile.tools) <= names


def test_public_profiles_have_no_planning_tools() -> None:
    planning = {spec.name for spec in catalog() if "planning" in spec.routes}
    for key in ("visitante", "cliente", "proveedor", "colaborador"):
        assert not set(load_profiles()[key].tools) & planning


def test_every_profile_has_focus() -> None:
    for key in PROFILE_KEYS:
        assert len(profile_focus(key)) > 40


def test_unknown_tool_fails(tmp_path: Path) -> None:
    config = tmp_path / "profiles.toml"
    config.write_text(
        '[profiles]\nenabled = true\ndefault = "visitante"\n'
        '[[profile]]\nkey = "visitante"\nlabel = "Visitante"\nrequires_authorization = false\n'
        'triggers = []\ntools = ["no_existe"]\n',
        encoding="utf-8",
    )
    with pytest.raises(ProfileError, match="no_existe"):
        load_profiles(config_path=config)


def test_missing_focus_section_fails(tmp_path: Path) -> None:
    prompt = tmp_path / "profiles.md"
    prompt.write_text(
        "<!-- prompt_version: 1.0 -->\n\n# T\n\n## visitante\n\nfoco\n", encoding="utf-8"
    )
    with pytest.raises(ProfileError, match="cliente"):
        load_profiles(prompt_path=prompt)


def test_disabled_keeps_only_visitante(tmp_path: Path) -> None:
    original = Path(profiles.PROFILES_CONFIG).read_text(encoding="utf-8")
    config = tmp_path / "profiles.toml"
    config.write_text(original.replace("enabled = true", "enabled = false", 1), encoding="utf-8")
    assert tuple(load_profiles(config_path=config)) == ("visitante",)


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("Proveedor", "proveedor"),
        ("b2b", "cliente"),
        ("CLIENTE", "cliente"),
        ("planificador", "planificador"),
        ("visitante", "visitante"),
        ("colaborador", "colaborador"),
        ("gerente", None),
    ],
)
def test_resolve_alias(text: str, expected: str | None) -> None:
    assert resolve_alias(text) == expected


def test_triggers() -> None:
    assert match_trigger("Soy proveedor de caña, ¿qué apoyo dan?") == "proveedor"
    assert match_trigger("Compro azúcar para mi empresa") == "cliente"
    assert match_trigger("Trabajo en Manuelita hace dos años") == "colaborador"
    assert match_trigger("¿Qué produce Manuelita?") is None


def test_authorization(monkeypatch: pytest.MonkeyPatch) -> None:
    for var in ("VALERIA_PLANNERS", "MANUELITA_PLANNER_OPEN", "MANUELITA_PLANNER_WEB"):
        monkeypatch.delenv(var, raising=False)
    assert not is_authorized("wa-0123456789abcdef", "whatsapp")
    monkeypatch.setenv("VALERIA_PLANNERS", "wa-aaaa, wa-0123456789abcdef")
    assert is_authorized("wa-0123456789abcdef", "whatsapp")
    assert not is_authorized("wa-ffff", "whatsapp")
    monkeypatch.setenv("MANUELITA_PLANNER_WEB", "1")
    assert is_authorized("anon", "web")
    assert not is_authorized("wa-ffff", "whatsapp")
    monkeypatch.setenv("MANUELITA_PLANNER_OPEN", "1")
    assert is_authorized("wa-ffff", "whatsapp")
