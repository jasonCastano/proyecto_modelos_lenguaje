"""Query the bronze catalog."""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.cli import main

_COMMANDS = {"list", "show", "export"}

if __name__ == "__main__":
    arguments = sys.argv[1:]
    if not arguments or arguments[0] not in _COMMANDS:
        arguments = ["list", *arguments]
    raise SystemExit(main(["catalog", *arguments]))
