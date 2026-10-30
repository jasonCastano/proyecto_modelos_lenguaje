"""Canonical entry point for the gold layer."""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.cli import main


def run() -> int:
    return main(["gold", "build", *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(run())
