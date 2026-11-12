"""Verifica que los commits solo tengan autores y coautores permitidos (CONSTITUTION.md §4.3).

Uso:
    # Hook commit-msg (pre-commit): revisa el autor actual y el mensaje
    uv run python scripts/check_commit_authors.py --message-file .git/COMMIT_EDITMSG
    # CI: revisa todos los commits de un rango
    uv run python scripts/check_commit_authors.py --range origin/main..HEAD
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from proyecto_modelos_lenguaje.authorship import (
    ALLOWED_IDENTITIES,
    Violation,
    current_author_email,
    is_allowed,
    message_violations,
    range_violations,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--message-file", type=Path, help="Mensaje de commit (hook commit-msg)")
    group.add_argument("--range", dest="rev_range", help="Rango de Git, p. ej. origin/main..HEAD")
    args = parser.parse_args(argv)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    if args.message_file is not None:
        violations: list[Violation] = message_violations(
            args.message_file.read_text(encoding="utf-8")
        )
        email = current_author_email()
        if not is_allowed(email):
            violations.insert(0, Violation("commit nuevo", "autor", email or "(sin correo)"))
    else:
        violations = range_violations(args.rev_range)

    if not violations:
        return 0
    print("Autoría no permitida (CONSTITUTION.md §4.3):", file=sys.stderr)
    for violation in violations:
        print(f"  - {violation}", file=sys.stderr)
    print("Identidades permitidas: " + ", ".join(ALLOWED_IDENTITIES), file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
