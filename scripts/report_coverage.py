"""Generate the 24-item coverage report for a campaign."""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["report", "coverage", *sys.argv[1:]]))
