"""Analyze corpus relevance against the Manuelita rules."""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["curate", "analyze", *sys.argv[1:]]))
