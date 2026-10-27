"""Start or resume a bronze campaign."""

from __future__ import annotations

import sys

from proyecto_modelos_lenguaje.catalog import Catalog
from proyecto_modelos_lenguaje.cli import main
from proyecto_modelos_lenguaje.config import load_config


def _option(arguments: list[str], name: str) -> str | None:
    try:
        return arguments[arguments.index(name) + 1]
    except ValueError, IndexError:
        return None


def _with_resume(arguments: list[str]) -> list[str]:
    campaign = _option(arguments, "--campaign")
    if not campaign or "--resume" in arguments:
        return arguments
    config_path = _option(arguments, "--config") or "config/sources.toml"
    try:
        config = load_config(config_path)
        database = config.settings.bronze_dir / "_meta" / "bronze.sqlite3"
        if not database.is_file():
            return arguments
        with Catalog(database) as catalog:
            existing = catalog.get_campaign(campaign)
            if existing and existing.status in {"planned", "paused", "running", "failed"}:
                return [*arguments, "--resume"]
    except Exception:
        return arguments
    return arguments


if __name__ == "__main__":
    raise SystemExit(main(["campaign", "start", *_with_resume(sys.argv[1:])]))
