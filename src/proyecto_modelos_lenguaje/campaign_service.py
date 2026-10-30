"""Shared campaign orchestration for the CLI and the canonical scrape entry point."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .catalog import Catalog
from .config import STORAGE_HARD_LIMIT, AppConfig, load_coverage_items
from .fetchers.base import Fetcher
from .fetchers.http import build_http_fetcher
from .pipeline import CampaignRunner, CampaignSummary
from .storage import BronzeStorage


@dataclass(frozen=True, slots=True)
class CampaignRun:
    """Result of one campaign execution."""

    summary: CampaignSummary
    policy: tuple[dict[str, Any], ...]
    duration_seconds: float
    resumed: bool
    dry_run: bool


def start_campaign(
    config: AppConfig,
    *,
    campaign_id: str,
    resume: bool = False,
    dry_run: bool = False,
    max_targets: int | None = None,
    max_bytes: int | None = None,
    coverage_path: str | Path | None = None,
    allow_private: bool = False,
    fetcher: Fetcher | None = None,
) -> CampaignRun:
    """Run or resume one bronze campaign and return its summary and policy checks.

    This is the single orchestration path used by ``pml campaign start`` and by
    ``scripts/scrape_empresa.py``. It builds the catalog, storage, fetcher and runner,
    executes the campaign, captures the policy decisions, and closes the catalog.
    """
    limit = config.settings.storage_limit_bytes
    if max_bytes is not None:
        if max_bytes < 1 or max_bytes > STORAGE_HARD_LIMIT:
            raise ValueError("max_bytes must be between 1 and 10000000000")
        limit = min(limit, max_bytes)

    coverage = (
        Path(coverage_path)
        if coverage_path is not None
        else config.path.parent / "coverage-items.toml"
    )
    items = load_coverage_items(coverage)
    database = config.settings.bronze_dir / "_meta" / "bronze.sqlite3"
    catalog = Catalog(database)
    try:
        catalog.init_schema()
        catalog.seed_sources(config.sources)
        catalog.seed_coverage(items)
        storage = BronzeStorage(config.settings.bronze_dir, limit_bytes=limit)
        http = fetcher or build_http_fetcher(
            user_agent=config.settings.user_agent,
            timeout=config.settings.request_timeout_seconds,
        )
        runner = CampaignRunner(
            config,
            items,
            catalog=catalog,
            storage=storage,
            fetcher=http,
            allow_private=allow_private,
            dry_run=dry_run,
            max_targets=max_targets,
        )
        started = time.perf_counter()
        summary = asyncio.run(runner.run(campaign_id, resume=resume))
        duration = time.perf_counter() - started
        policy = catalog.policy_checks(campaign_id)
    finally:
        catalog.close()

    return CampaignRun(
        summary=summary,
        policy=policy,
        duration_seconds=round(duration, 3),
        resumed=resume,
        dry_run=dry_run,
    )
