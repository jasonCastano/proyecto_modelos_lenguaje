"""Contrato del gatekeeper Jev (spec 021): configuración, prompts y secretos (SC-008)."""

from __future__ import annotations

import re
import subprocess
import tomllib

from proyecto_modelos_lenguaje.agent.config import jev_config
from proyecto_modelos_lenguaje.agent.jev import ROUTES, SCOPE_REASONS, load_gate_prompts
from proyecto_modelos_lenguaje.config import PROJECT_ROOT

KEY_SHAPE = re.compile(r"TYPESAFE_API_KEY\s*=\s*['\"]?sk-[A-Za-z0-9_-]{8,}")


def test_agent_toml_jev_section_loads_and_is_disabled_by_default() -> None:
    document = tomllib.loads((PROJECT_ROOT / "config" / "agent.toml").read_text(encoding="utf-8"))
    section = document["jev"]
    assert section["enabled"] is False
    assert not section["model"].endswith("latest")
    config = jev_config(section, environ={})
    assert config.enabled is False and config.signals[0] == "route"


def test_prompts_have_every_route_and_scope_reason() -> None:
    prompts = load_gate_prompts()
    assert set(prompts.questions) >= {"route", "scope", "annoyance", "crisis"}
    assert [key for key, _ in prompts.questions["route"].options] == list(ROUTES)
    assert [key for key, _ in prompts.questions["scope"].options] == list(SCOPE_REASONS)
    assert prompts.version


def test_env_example_declares_the_key_without_a_value() -> None:
    text = (PROJECT_ROOT / ".env.example").read_text(encoding="utf-8")
    assert re.search(r"^TYPESAFE_API_KEY=$", text, flags=re.MULTILINE)


def test_no_versioned_file_contains_a_typesafe_key() -> None:
    files = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True, check=True, cwd=PROJECT_ROOT
    ).stdout.splitlines()
    offenders = []
    for name in files:
        if name.startswith("data/") or not name.endswith(
            (".py", ".md", ".toml", ".json", ".ts", ".tsx", ".yml", ".yaml", ".txt", ".example")
        ):
            continue
        path = PROJECT_ROOT / name
        if path.is_file() and KEY_SHAPE.search(path.read_text(encoding="utf-8", errors="ignore")):
            offenders.append(name)
    assert offenders == []
