"""Verify hashes and metadata for a sample of bronze artifacts."""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.cli import main

if __name__ == "__main__":
    raise SystemExit(main(["verify", *sys.argv[1:]]))
