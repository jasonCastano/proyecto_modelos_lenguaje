"""Integration tests for the canonical scrape entry point."""

from __future__ import annotations

import hashlib
import json
import shutil
import sqlite3
from pathlib import Path

from proyecto_modelos_lenguaje.campaign_service import start_campaign
from proyecto_modelos_lenguaje.catalog import Catalog
from proyecto_modelos_lenguaje.config import load_config
from proyecto_modelos_lenguaje.entrypoint import main


def _database(root: Path) -> Path:
    return root / "data" / "bronze" / "_meta" / "bronze.sqlite3"


def _campaign_count(database: Path) -> int:
    if not database.is_file():
        return 0
    connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
    try:
        return int(connection.execute("SELECT COUNT(*) FROM campaigns").fetchone()[0])
    finally:
        connection.close()


def _artifact_hashes(root: Path, campaign_id: str) -> list[str]:
    catalog = Catalog(_database(root))
    try:
        artifacts, _ = catalog.list_artifacts(campaign_id=campaign_id, limit=1000)
    finally:
        catalog.close()
    return sorted(artifact.content_hash for artifact in artifacts)


def _copy_config(source: Path, project_root: Path) -> Path:
    target_dir = project_root / "config"
    target_dir.mkdir(parents=True, exist_ok=True)
    for name in ("sources.toml", "exclusions.toml", "coverage-items.toml"):
        shutil.copyfile(source.parent / name, target_dir / name)
    return target_dir / "sources.toml"


def _hash_tree(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(root.rglob("*")):
        if path.is_file():
            digest.update(path.relative_to(root).as_posix().encode())
            digest.update(path.read_bytes())
    return digest.hexdigest()


def test_new_campaign_stores_artifacts(tmp_path: Path, write_config, server, capsys) -> None:
    config_path = write_config(server)
    code = main(
        ["--config", str(config_path), "--campaign", "c001", "--limit", "3", "--json"],
        project_root=tmp_path,
        allow_private=True,
    )
    payload = json.loads(capsys.readouterr().out)
    assert code == 0
    assert payload["campaign_id"] == "c001"
    assert payload["mode"] == "new"
    assert payload["summary"]["artifacts_stored"] >= 1
    assert payload["summary"]["targets_discovered"] >= 1
    assert (tmp_path / "data" / "bronze" / "reports" / "c001").is_dir()


def test_resume_after_pause_does_not_duplicate(
    tmp_path: Path, write_config, server, site, capsys
) -> None:
    index = site / "index.html"
    index.write_text(
        index.read_text(encoding="utf-8") + '<a href="/big.html">Grande</a>',
        encoding="utf-8",
    )
    (site / "big.html").write_text(
        "<!doctype html><html><body><p>" + ("x" * 1_500_000) + "</p></body></html>",
        encoding="utf-8",
    )
    config_path = write_config(server, limit=1_048_576)
    first = main(
        ["--config", str(config_path), "--campaign", "resume1", "--limit", "5", "--json"],
        project_root=tmp_path,
        allow_private=True,
    )
    first_payload = json.loads(capsys.readouterr().out)
    assert first == 4
    assert first_payload["status"] == "paused"

    write_config(server, limit=10_000_000)
    second = main(
        ["--config", str(config_path), "--campaign", "resume1", "--resume", "--json"],
        project_root=tmp_path,
        allow_private=True,
    )
    second_payload = json.loads(capsys.readouterr().out)
    assert second == 0
    assert second_payload["status"] == "completed"
    assert second_payload["mode"] == "resume"
    hashes = _artifact_hashes(tmp_path, "resume1")
    assert len(hashes) == len(set(hashes))


def test_dry_run_does_not_touch_real_bronze(tmp_path: Path, write_config, server, capsys) -> None:
    config_path = write_config(server)
    database = _database(tmp_path)
    before = _campaign_count(database)
    code = main(
        [
            "--config",
            str(config_path),
            "--campaign",
            "c-dry",
            "--limit",
            "3",
            "--dry-run",
            "--json",
        ],
        project_root=tmp_path,
        allow_private=True,
    )
    payload = json.loads(capsys.readouterr().out)
    assert code in {0, 4}
    assert payload["effective"]["dry_run"] is True
    assert payload["summary"]["artifacts_stored"] == 0
    assert _campaign_count(database) == before


def test_blocked_source_is_recorded(tmp_path: Path, write_config, server, capsys) -> None:
    config_path = write_config(server)
    code = main(
        ["--config", str(config_path), "--campaign", "c-policy", "--limit", "10", "--json"],
        project_root=tmp_path,
        allow_private=True,
    )
    assert code == 0
    capsys.readouterr()
    catalog = Catalog(_database(tmp_path))
    try:
        checks = catalog.policy_checks("c-policy")
        artifacts, _ = catalog.list_artifacts(campaign_id="c-policy", limit=1000)
    finally:
        catalog.close()
    disallowed = [check for check in checks if check["decision"] == "disallowed"]
    assert disallowed
    assert all(check["reason"] for check in disallowed)
    assert all(not artifact.url_canonical.endswith("/blocked.html") for artifact in artifacts)


def test_wrapper_matches_direct_campaign_metrics(
    tmp_path: Path, write_config, server, capsys
) -> None:
    source = write_config(server)
    wrapper_root = tmp_path / "wrapper"
    direct_root = tmp_path / "direct"
    wrapper_config = _copy_config(source, wrapper_root)
    direct_config_path = _copy_config(source, direct_root)

    wrapper_code = main(
        [
            "--config",
            str(wrapper_config),
            "--campaign",
            "c-wrapper",
            "--limit",
            "3",
            "--json",
        ],
        project_root=wrapper_root,
        allow_private=True,
    )
    wrapper_payload = json.loads(capsys.readouterr().out)
    assert wrapper_code == 0

    direct_config = load_config(direct_config_path, project_root=direct_root)
    direct = start_campaign(
        direct_config,
        campaign_id="c-direct",
        max_targets=3,
        coverage_path=direct_root / "config" / "coverage-items.toml",
        allow_private=True,
    )
    direct_payload = direct.summary.as_dict()
    for key in (
        "targets_discovered",
        "artifacts_stored",
        "excluded",
        "failed",
        "bytes_stored",
    ):
        assert wrapper_payload["summary"][key] == direct_payload[key]


def test_wrapper_does_not_modify_silver_or_gold(
    tmp_path: Path, write_config, server, capsys
) -> None:
    config_path = write_config(server)
    silver = tmp_path / "data" / "silver"
    gold = tmp_path / "data" / "gold"
    silver.mkdir(parents=True)
    gold.mkdir(parents=True)
    (silver / "marker.txt").write_text("silver", encoding="utf-8")
    (gold / "marker.txt").write_text("gold", encoding="utf-8")
    before = (_hash_tree(silver), _hash_tree(gold))
    code = main(
        ["--config", str(config_path), "--campaign", "c-layers", "--limit", "2", "--json"],
        project_root=tmp_path,
        allow_private=True,
    )
    assert code == 0
    capsys.readouterr()
    after = (_hash_tree(silver), _hash_tree(gold))
    assert after == before
