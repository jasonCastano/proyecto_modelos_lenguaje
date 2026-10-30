"""Review ambiguous relevance cases."""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.cli import main

if __name__ == "__main__":
    arguments = sys.argv[1:]
    if not arguments or arguments[0] not in {"list", "decide"}:
        arguments = ["list", *arguments]
    raise SystemExit(main(["curate", "review", *arguments]))
