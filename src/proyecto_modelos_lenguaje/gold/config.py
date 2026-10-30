"""Configuration for the gold layer."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT, ConfigError

GOLD_VERSION = "1.0.0"


@dataclass(frozen=True, slots=True)
class UnitsConfig:
    min_sentence_chars: int
    max_unit_chars: int
    dedup_threshold: float
    dedup_shingle_size: int


@dataclass(frozen=True, slots=True)
class TopicsConfig:
    min_score: int


@dataclass(frozen=True, slots=True)
class CoverageConfig:
    covered_min_units: int
    covered_min_official: int


@dataclass(frozen=True, slots=True)
class ContextConfig:
    budgets: tuple[int, ...]
    chars_per_token: float


@dataclass(frozen=True, slots=True)
class OutputConfig:
    root: Path


@dataclass(frozen=True, slots=True)
class RunConfig:
    fail_fast: bool


@dataclass(frozen=True, slots=True)
class GoldConfig:
    path: Path
    taxonomy_path: Path
    units: UnitsConfig
    topics: TopicsConfig
    coverage: CoverageConfig
    context: ContextConfig
    output: OutputConfig
    run: RunConfig
    config_hash: str
    taxonomy_hash: str


def _require(table: dict[str, Any], key: str, *, context: str) -> Any:
    if key not in table:
        raise ConfigError(f"{context}: missing required key '{key}'")
    return table[key]


def _as_int(value: Any, *, context: str, minimum: int, maximum: int) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        raise ConfigError(f"{context} must be an integer")
    if not minimum <= value <= maximum:
        raise ConfigError(f"{context} must be between {minimum} and {maximum}")
    return value


def _as_float(value: Any, *, context: str, minimum: float, maximum: float) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        raise ConfigError(f"{context} must be a number")
    number = float(value)
    if not minimum <= number <= maximum:
        raise ConfigError(f"{context} must be between {minimum} and {maximum}")
    return number


def _as_bool(value: Any, *, context: str) -> bool:
    if not isinstance(value, bool):
        raise ConfigError(f"{context} must be a boolean")
    return value


def load_gold_config(
    path: str | Path = "config/gold.toml",
    taxonomy_path: str | Path = "config/gold_taxonomy.toml",
    *,
    project_root: Path | None = None,
) -> GoldConfig:
    root = project_root or PROJECT_ROOT
    config_path = Path(path)
    if not config_path.is_absolute():
        config_path = root / config_path
    config_path = config_path.resolve()
    taxonomy = Path(taxonomy_path)
    if not taxonomy.is_absolute():
        taxonomy = root / taxonomy
    taxonomy = taxonomy.resolve()
    if not config_path.is_file():
        raise ConfigError(f"configuration file not found: {config_path}")
    if not taxonomy.is_file():
        raise ConfigError(f"taxonomy file not found: {taxonomy}")
    try:
        with config_path.open("rb") as handle:
            table = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    units_table = _require(table, "units", context="units")
    units = UnitsConfig(
        min_sentence_chars=_as_int(
            units_table.get("min_sentence_chars", 40),
            context="units.min_sentence_chars",
            minimum=1,
            maximum=2000,
        ),
        max_unit_chars=_as_int(
            units_table.get("max_unit_chars", 700),
            context="units.max_unit_chars",
            minimum=100,
            maximum=10000,
        ),
        dedup_threshold=_as_float(
            units_table.get("dedup_threshold", 0.9),
            context="units.dedup_threshold",
            minimum=0.5,
            maximum=1.0,
        ),
        dedup_shingle_size=_as_int(
            units_table.get("dedup_shingle_size", 5),
            context="units.dedup_shingle_size",
            minimum=2,
            maximum=20,
        ),
    )
    if units.max_unit_chars <= units.min_sentence_chars:
        raise ConfigError("units.max_unit_chars must be greater than min_sentence_chars")

    topics_table = table.get("topics", {})
    topics = TopicsConfig(
        min_score=_as_int(
            topics_table.get("min_score", 2),
            context="topics.min_score",
            minimum=1,
            maximum=20,
        )
    )
    coverage_table = table.get("coverage", {})
    coverage = CoverageConfig(
        covered_min_units=_as_int(
            coverage_table.get("covered_min_units", 3),
            context="coverage.covered_min_units",
            minimum=1,
            maximum=100,
        ),
        covered_min_official=_as_int(
            coverage_table.get("covered_min_official", 1),
            context="coverage.covered_min_official",
            minimum=0,
            maximum=100,
        ),
    )
    context_table = table.get("context", {})
    raw_budgets = context_table.get("budgets", [8000, 32000])
    if not isinstance(raw_budgets, list) or not raw_budgets:
        raise ConfigError("context.budgets must be a non-empty list")
    budgets = tuple(
        _as_int(item, context="context.budgets", minimum=1000, maximum=200000)
        for item in raw_budgets
    )
    if list(budgets) != sorted(set(budgets)):
        raise ConfigError("context.budgets must be strictly increasing")
    context = ContextConfig(
        budgets=budgets,
        chars_per_token=_as_float(
            context_table.get("chars_per_token", 3.5),
            context="context.chars_per_token",
            minimum=1.0,
            maximum=10.0,
        ),
    )
    output_table = table.get("output", {})
    raw_root = Path(str(output_table.get("root", "data/gold")))
    output_root = raw_root if raw_root.is_absolute() else root / raw_root
    output = OutputConfig(root=output_root.resolve())
    run_table = table.get("run", {})
    run = RunConfig(fail_fast=_as_bool(run_table.get("fail_fast", False), context="run.fail_fast"))

    canonical = json.dumps(table, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(f"{canonical}\n{GOLD_VERSION}".encode()).hexdigest()
    taxonomy_hash = hashlib.sha256(taxonomy.read_bytes()).hexdigest()
    return GoldConfig(
        path=config_path,
        taxonomy_path=taxonomy,
        units=units,
        topics=topics,
        coverage=coverage,
        context=context,
        output=output,
        run=run,
        config_hash=digest,
        taxonomy_hash=taxonomy_hash,
    )
