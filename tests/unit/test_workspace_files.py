"""Workspace versionado de OpenClaw (spec 024, T051): completo, separado y sin datos personales."""

from __future__ import annotations

import re

import pytest

from proyecto_modelos_lenguaje.ops import WORKSPACE_SOURCE

REQUIRED = ("SOUL.md", "IDENTITY.md", "AGENTS.md", "USER.md", "MEMORY.md")
SKILL = WORKSPACE_SOURCE / "skills" / "valeria-manuelita" / "SKILL.md"
E164 = re.compile(r"\+[1-9]\d{7,14}")
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
SECRET = re.compile(r"sk-[A-Za-z0-9]{8,}|lsv2_|ghp_|xox[bp]-")


@pytest.mark.parametrize("name", REQUIRED)
def test_files_exist(name: str) -> None:
    assert (WORKSPACE_SOURCE / name).is_file()


def test_user_md_limit() -> None:
    assert len((WORKSPACE_SOURCE / "USER.md").read_text(encoding="utf-8")) <= 4000


def test_identity_and_limits_are_separate() -> None:
    soul = (WORKSPACE_SOURCE / "SOUL.md").read_text(encoding="utf-8")
    agents = (WORKSPACE_SOURCE / "AGENTS.md").read_text(encoding="utf-8")
    assert "Red lines" in agents and "## Tools" in agents
    assert "Red lines" not in soul and "Valer-IA Caña" in soul


def test_skill_frontmatter() -> None:
    text = SKILL.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    front = text.split("---")[1]
    assert re.search(r"^name: valeria-manuelita$", front, re.MULTILINE)
    assert re.search(r"^description: .{20,}", front, re.MULTILINE)


def test_no_personal_data_or_secrets() -> None:
    for path in WORKSPACE_SOURCE.rglob("*.md"):
        text = path.read_text(encoding="utf-8")
        assert not E164.search(text), path
        assert not EMAIL.search(text), path
        assert not SECRET.search(text), path


def test_mcp_tools_listed_in_agents_md() -> None:
    from proyecto_modelos_lenguaje.mcp_server import exposed_specs

    agents = (WORKSPACE_SOURCE / "AGENTS.md").read_text(encoding="utf-8")
    missing = [spec.name for spec in exposed_specs() if f"`{spec.name}`" not in agents]
    assert not missing, missing
