"""Autoría permitida de los commits (CONSTITUTION.md §4.3).

Solo pueden aparecer como autores, committers o coautores (`Co-authored-by`) los integrantes del
equipo y los bots autorizados. GitHub firma como committer los merges y squash hechos desde la web.
"""

from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass

# Correos de cada identidad permitida (los de GitHub `noreply` incluyen el id de la cuenta).
ALLOWED_IDENTITIES: dict[str, frozenset[str]] = {
    "jasonCastano (Jason Alejandro Castaño)": frozenset(
        {"jasonale3007@gmail.com", "77637361+jasoncastano@users.noreply.github.com"}
    ),
    "Robertto48 (Roberto José Guerrero Criollo)": frozenset(
        {"roberto.jose.7@hotmail.com", "64019968+robertto48@users.noreply.github.com"}
    ),
    "dependabot[bot]": frozenset({"49699333+dependabot[bot]@users.noreply.github.com"}),
}
# Committer que GitHub usa al fusionar desde la web; nunca vale como autor.
GITHUB_COMMITTER = "noreply@github.com"

ALLOWED_EMAILS: frozenset[str] = frozenset().union(*ALLOWED_IDENTITIES.values())

_TRAILER = re.compile(r"^[ \t]*co-authored-by:[ \t]*(?P<value>.+)$", re.IGNORECASE | re.MULTILINE)
_EMAIL = re.compile(r"<(?P<email>[^>]+)>")
_BOT_SIGNATURE = re.compile(r"generated with \[?claude code", re.IGNORECASE)


@dataclass(frozen=True)
class Violation:
    """Una identidad o firma no permitida en un commit."""

    commit: str
    role: str
    identity: str

    def __str__(self) -> str:
        return f"{self.commit}: {self.role} no permitido: {self.identity}"


def is_allowed(email: str, *, committer: bool = False) -> bool:
    """Indica si el correo pertenece a una identidad permitida."""
    normalized = email.strip().lower()
    return normalized in ALLOWED_EMAILS or (committer and normalized == GITHUB_COMMITTER)


def message_violations(message: str, commit: str = "mensaje") -> list[Violation]:
    """Revisa los coautores y las firmas de herramientas en un mensaje de commit."""
    found: list[Violation] = []
    for match in _TRAILER.finditer(message):
        value = match.group("value").strip()
        email = _EMAIL.search(value)
        if email is None or not is_allowed(email.group("email")):
            found.append(Violation(commit, "coautor", value))
    for line in message.splitlines():
        if _BOT_SIGNATURE.search(line):
            found.append(Violation(commit, "firma", line.strip()))
    return found


def commit_violations(
    commit: str, author: str, author_email: str, committer: str, committer_email: str, message: str
) -> list[Violation]:
    """Revisa autor, committer y mensaje de un commit."""
    found: list[Violation] = []
    if not is_allowed(author_email):
        found.append(Violation(commit, "autor", f"{author} <{author_email}>"))
    if not is_allowed(committer_email, committer=True):
        found.append(Violation(commit, "committer", f"{committer} <{committer_email}>"))
    return found + message_violations(message, commit)


_SEP = "\x1f"
_END = "\x1e"


def range_violations(rev_range: str, cwd: str | None = None) -> list[Violation]:
    """Revisa todos los commits de un rango de Git (`base..head`)."""
    fmt = _SEP.join(["%h", "%an", "%ae", "%cn", "%ce", "%B"]) + _END
    out = subprocess.run(
        ["git", "log", f"--format={fmt}", rev_range],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        cwd=cwd,
    ).stdout
    found: list[Violation] = []
    for record in out.split(_END):
        record = record.strip("\n")
        if not record:
            continue
        sha, author, author_email, committer, committer_email, message = record.split(_SEP, 5)
        found += commit_violations(sha, author, author_email, committer, committer_email, message)
    return found


def current_author_email(cwd: str | None = None) -> str:
    """Correo del autor con el que Git firmará el próximo commit."""
    ident = subprocess.run(
        ["git", "var", "GIT_AUTHOR_IDENT"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
        cwd=cwd,
    ).stdout
    match = _EMAIL.search(ident)
    return match.group("email") if match else ""
