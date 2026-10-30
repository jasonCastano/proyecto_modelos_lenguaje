"""Unit tests for configuration validation."""

from __future__ import annotations

from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.config import ConfigError, load_config, load_coverage_items
from tests.conftest import COVERAGE_PATH, PROJECT_ROOT

MINIMAL = """
[settings]
data_root = "data"
storage_limit_bytes = 2000000
user_agent = "ManuelitaRAG-test/0.1"
max_depth = 1
max_retries = 0
default_delay_seconds = 0.5
retry_backoff_seconds = 0.5
request_timeout_seconds = 5

[[sources]]
id = "fixture"
domain = "example.com"
platform = "website"
authority = "first_party"
seeds = ["https://example.com/"]
follow_links = false
max_depth = 1
policy = { robots = "respect", requires_auth = false }
"""


def _write_config(root: Path, body: str) -> Path:
    directory = root / "config"
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / "sources.toml"
    path.write_text(body, encoding="utf-8")
    (directory / "exclusions.toml").write_text(
        "[exclusions]\nurls=[]\ndomains=[]\n", encoding="utf-8"
    )
    return path


def test_real_configuration_is_valid() -> None:
    config = load_config(PROJECT_ROOT / "config" / "sources.toml")
    assert len(config.sources) == 15
    assert config.settings.storage_limit_bytes == 10_000_000_000
    assert len(config.config_hash) == 64
    items = load_coverage_items(COVERAGE_PATH)
    assert len(items) == 24
    assert {item.item_id for item in items} == {
        f"{prefix}-{index:02d}" for prefix in "IODH" for index in range(1, 7)
    }


def test_config_hash_is_stable(tmp_path: Path) -> None:
    path = _write_config(tmp_path, MINIMAL)
    first = load_config(path, project_root=tmp_path).config_hash
    second = load_config(path, project_root=tmp_path).config_hash
    assert first == second


def test_duplicate_source_ids_are_rejected(tmp_path: Path) -> None:
    source_block = MINIMAL.split("[[sources]]", 1)[1].replace("example.com", "example.org")
    duplicate = MINIMAL + "\n[[sources]]" + source_block
    path = _write_config(tmp_path, duplicate)
    with pytest.raises(ConfigError, match="unique"):
        load_config(path, project_root=tmp_path)


def test_data_root_must_stay_under_data(tmp_path: Path) -> None:
    body = MINIMAL.replace('data_root = "data"', 'data_root = "elsewhere"')
    path = _write_config(tmp_path, body)
    with pytest.raises(ConfigError, match="data"):
        load_config(path, project_root=tmp_path)


def test_storage_limit_cannot_exceed_hard_cap(tmp_path: Path) -> None:
    body = MINIMAL.replace("storage_limit_bytes = 2000000", "storage_limit_bytes = 20000000000")
    path = _write_config(tmp_path, body)
    with pytest.raises(ConfigError, match="between"):
        load_config(path, project_root=tmp_path)


def test_coverage_requires_exactly_24_items(tmp_path: Path) -> None:
    path = tmp_path / "coverage.toml"
    path.write_text(
        '[[items]]\nid = "I-01"\ncategory = "identity"\nname = "Misión"\nkeywords = ["mision"]\n',
        encoding="utf-8",
    )
    with pytest.raises(ConfigError, match="24"):
        load_coverage_items(path)
