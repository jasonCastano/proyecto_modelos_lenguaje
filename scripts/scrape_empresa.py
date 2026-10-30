"""Canonical company scraping entry point.

Delegates to the bronze pipeline through :mod:`proyecto_modelos_lenguaje.entrypoint`.
"""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.entrypoint import main


def run() -> int:
    return main(sys.argv[1:])


if __name__ == "__main__":
    raise SystemExit(run())
