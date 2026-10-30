"""Configuration for the silver layer."""

from __future__ import annotations

import hashlib
import json
import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ..config import PROJECT_ROOT, ConfigError
from .cleaning import CLEANING_VERSION


@dataclass(frozen=True, slots=True)
class ChunkingConfig:
    target_tokens: int
    max_tokens: int
    min_tokens: int
    overlap_tokens: int
    chars_per_token: float
    boundary: str


@dataclass(frozen=True, slots=True)
class DedupConfig:
    near_threshold: float
    shingle_size: int
    num_perm: int
    bands: int


@dataclass(frozen=True, slots=True)
class QualityConfig:
    min_text_chars: int
    min_alpha_ratio: float
    table_line_ratio: float
    repeated_line_ratio: float


@dataclass(frozen=True, slots=True)
class OutputConfig:
    root: Path
    markdown: bool


@dataclass(frozen=True, slots=True)
class LanguageConfig:
    min_tokens: int


@dataclass(frozen=True, slots=True)
class RunConfig:
    max_workers: int
    fail_fast: bool


@dataclass(frozen=True, slots=True)
class SilverConfig:
    path: Path
    chunking: ChunkingConfig
    dedup: DedupConfig
    quality: QualityConfig
    output: OutputConfig
    language: LanguageConfig
    run: RunConfig
    config_hash: str


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


def _as_str(value: Any, *, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"{context} must be a non-empty string")
    return value.strip()


def load_silver_config(
    path: str | Path = "config/silver.toml",
    *,
    project_root: Path | None = None,
) -> SilverConfig:
    """Load and validate ``config/silver.toml``."""
    config_path = Path(path)
    root = project_root or PROJECT_ROOT
    if not config_path.is_absolute():
        config_path = root / config_path
    config_path = config_path.resolve()
    if not config_path.is_file():
        raise ConfigError(f"configuration file not found: {config_path}")
    try:
        with config_path.open("rb") as handle:
            table = tomllib.load(handle)
    except tomllib.TOMLDecodeError as exc:
        raise ConfigError(f"invalid TOML in {config_path}: {exc}") from exc

    chunking_table = _require(table, "chunking", context="chunking")
    chunking = ChunkingConfig(
        target_tokens=_as_int(
            _require(chunking_table, "target_tokens", context="chunking.target_tokens"),
            context="chunking.target_tokens",
            minimum=50,
            maximum=8000,
        ),
        max_tokens=_as_int(
            _require(chunking_table, "max_tokens", context="chunking.max_tokens"),
            context="chunking.max_tokens",
            minimum=100,
            maximum=16000,
        ),
        min_tokens=_as_int(
            _require(chunking_table, "min_tokens", context="chunking.min_tokens"),
            context="chunking.min_tokens",
            minimum=1,
            maximum=4000,
        ),
        overlap_tokens=_as_int(
            _require(chunking_table, "overlap_tokens", context="chunking.overlap_tokens"),
            context="chunking.overlap_tokens",
            minimum=0,
            maximum=2000,
        ),
        chars_per_token=_as_float(
            _require(chunking_table, "chars_per_token", context="chunking.chars_per_token"),
            context="chunking.chars_per_token",
            minimum=1.0,
            maximum=10.0,
        ),
        boundary=_as_str(chunking_table.get("boundary", "sentence"), context="chunking.boundary"),
    )
    if not (
        chunking.min_tokens <= chunking.target_tokens <= chunking.max_tokens
        and chunking.overlap_tokens < chunking.target_tokens
    ):
        raise ConfigError(
            "chunking must satisfy min_tokens <= target_tokens <= max_tokens and "
            "overlap_tokens < target_tokens"
        )
    if chunking.boundary not in {"sentence", "paragraph"}:
        raise ConfigError("chunking.boundary must be 'sentence' or 'paragraph'")

    dedup_table = _require(table, "dedup", context="dedup")
    dedup = DedupConfig(
        near_threshold=_as_float(
            _require(dedup_table, "near_threshold", context="dedup.near_threshold"),
            context="dedup.near_threshold",
            minimum=0.5,
            maximum=1.0,
        ),
        shingle_size=_as_int(
            _require(dedup_table, "shingle_size", context="dedup.shingle_size"),
            context="dedup.shingle_size",
            minimum=2,
            maximum=20,
        ),
        num_perm=_as_int(
            _require(dedup_table, "num_perm", context="dedup.num_perm"),
            context="dedup.num_perm",
            minimum=16,
            maximum=512,
        ),
        bands=_as_int(
            _require(dedup_table, "bands", context="dedup.bands"),
            context="dedup.bands",
            minimum=1,
            maximum=64,
        ),
    )
    if dedup.num_perm % dedup.bands != 0:
        raise ConfigError("dedup.num_perm must be divisible by dedup.bands")

    quality_table = _require(table, "quality", context="quality")
    quality = QualityConfig(
        min_text_chars=_as_int(
            quality_table.get("min_text_chars", 100),
            context="quality.min_text_chars",
            minimum=1,
            maximum=100000,
        ),
        min_alpha_ratio=_as_float(
            quality_table.get("min_alpha_ratio", 0.5),
            context="quality.min_alpha_ratio",
            minimum=0.0,
            maximum=1.0,
        ),
        table_line_ratio=_as_float(
            quality_table.get("table_line_ratio", 0.3),
            context="quality.table_line_ratio",
            minimum=0.0,
            maximum=1.0,
        ),
        repeated_line_ratio=_as_float(
            quality_table.get("repeated_line_ratio", 0.3),
            context="quality.repeated_line_ratio",
            minimum=0.0,
            maximum=1.0,
        ),
    )

    output_table = _require(table, "output", context="output")
    raw_root = Path(_as_str(output_table.get("root", "data/silver"), context="output.root"))
    output_root = raw_root if raw_root.is_absolute() else root / raw_root
    output = OutputConfig(
        root=output_root.resolve(),
        markdown=_as_bool(output_table.get("markdown", True), context="output.markdown"),
    )

    language_table = table.get("language", {})
    language = LanguageConfig(
        min_tokens=_as_int(
            language_table.get("min_tokens", 10),
            context="language.min_tokens",
            minimum=1,
            maximum=1000,
        )
    )
    run_table = table.get("run", {})
    run = RunConfig(
        max_workers=_as_int(
            run_table.get("max_workers", 4),
            context="run.max_workers",
            minimum=1,
            maximum=16,
        ),
        fail_fast=_as_bool(run_table.get("fail_fast", False), context="run.fail_fast"),
    )

    canonical = json.dumps(table, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(f"{canonical}\n{CLEANING_VERSION}".encode()).hexdigest()
    return SilverConfig(
        path=config_path,
        chunking=chunking,
        dedup=dedup,
        quality=quality,
        output=output,
        language=language,
        run=run,
        config_hash=digest,
    )
