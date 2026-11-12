"""Pruebas de la autoría permitida de commits (CONSTITUTION.md §4.3)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.authorship import (
    commit_violations,
    is_allowed,
    message_violations,
    range_violations,
)

JASON = "jasonale3007@gmail.com"
ROBERTO = "roberto.jose.7@hotmail.com"
DEPENDABOT = "49699333+dependabot[bot]@users.noreply.github.com"


@pytest.mark.parametrize(
    "email",
    [
        JASON,
        ROBERTO,
        DEPENDABOT,
        "77637361+jasonCastano@users.noreply.github.com",
        "64019968+Robertto48@users.noreply.github.com",
    ],
)
def test_allowed_identities(email: str) -> None:
    # Arrange / Act / Assert
    assert is_allowed(email)


def test_github_noreply_only_valid_as_committer() -> None:
    # Arrange
    email = "noreply@github.com"
    # Act / Assert
    assert not is_allowed(email)
    assert is_allowed(email, committer=True)


def test_message_rejects_bot_coauthor_and_signature() -> None:
    # Arrange
    message = (
        "feat: algo\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\n"
        "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n"
    )
    # Act
    found = message_violations(message)
    # Assert
    assert {v.role for v in found} == {"coautor", "firma"}


def test_message_accepts_team_coauthor() -> None:
    # Arrange
    message = f"docs: algo\n\nCo-authored-by: Jason Alejandro Castaño <{JASON}>\n"
    # Act / Assert
    assert message_violations(message) == []


def test_commit_rejects_unknown_author() -> None:
    # Arrange / Act
    found = commit_violations("abc", "Bot", "bot@example.com", "GitHub", "noreply@github.com", "x")
    # Assert
    assert [v.role for v in found] == ["autor"]


def _git(repo: Path, *args: str, email: str) -> None:
    env_args = ["-c", "user.name=Prueba", "-c", f"user.email={email}", "-c", "commit.gpgsign=false"]
    subprocess.run(["git", *env_args, *args], cwd=repo, check=True, capture_output=True)


def test_range_reports_only_offending_commits(tmp_path: Path) -> None:
    # Arrange
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "chore: base", email=ROBERTO)
    _git(tmp_path, "commit", "-q", "--allow-empty", "-m", "feat: ok", email=JASON)
    _git(
        tmp_path,
        "commit",
        "-q",
        "--allow-empty",
        "-m",
        "feat: mal\n\nCo-authored-by: Claude <noreply@anthropic.com>",
        email=ROBERTO,
    )
    # Act
    found = range_violations("HEAD~2..HEAD", cwd=str(tmp_path))
    # Assert
    assert [v.role for v in found] == ["coautor"]
