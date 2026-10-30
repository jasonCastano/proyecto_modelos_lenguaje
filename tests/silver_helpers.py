"""Shared helpers for silver tests."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from proyecto_modelos_lenguaje.catalog import Catalog
from proyecto_modelos_lenguaje.config import PROJECT_ROOT, load_config, load_coverage_items
from proyecto_modelos_lenguaje.silver.config import load_silver_config
from proyecto_modelos_lenguaje.silver.pipeline import SilverPipeline
from proyecto_modelos_lenguaje.storage import BronzeStorage
from proyecto_modelos_lenguaje.utils import utcnow

CAMPAIGN = "silver-test"


@dataclass(slots=True)
class SilverEnv:
    root: Path
    bronze_dir: Path
    database: Path
    catalog: Catalog
    storage: BronzeStorage
    pipeline: SilverPipeline

    def add(
        self,
        data: bytes,
        *,
        media_type: str,
        url: str,
        title: str | None,
        source_id: str = "official_site",
        authority: str = "first_party",
        language: str = "es",
        version: int = 1,
    ) -> int:
        stored = self.storage.store(
            data,
            media_type=media_type,
            source_id=source_id,
            campaign_id=CAMPAIGN,
        )
        artifact, _ = self.catalog.add_artifact(
            content_hash=stored.content_hash,
            text_hash=None,
            media_type=media_type,
            byte_size=stored.byte_size,
            storage_path=stored.storage_path,
            retrieved_at=utcnow(),
            http_status=200,
            source_id=source_id,
            campaign_id=CAMPAIGN,
            authority=authority,
            language=language,
            language_method="heuristic",
            title=title,
            published_at=None,
            version=version,
            url_original=url,
            url_canonical=url,
            category="identity",
        )
        self.catalog.add_url_version(
            url_canonical=url,
            artifact_id=artifact.artifact_id,
            version=version,
            change_reason="first_capture",
        )
        return artifact.artifact_id


def build_silver_env(tmp_path: Path) -> SilverEnv:
    bronze_dir = tmp_path / "data" / "bronze"
    database = bronze_dir / "_meta" / "bronze.sqlite3"
    catalog = Catalog(database)
    catalog.init_schema()
    app = load_config("config/sources.toml", project_root=PROJECT_ROOT)
    catalog.seed_sources(app.sources)
    catalog.seed_coverage(load_coverage_items("config/coverage-items.toml"))
    catalog.create_campaign(
        campaign_id=CAMPAIGN,
        config_hash="a" * 64,
        tool_version="test",
    )
    storage = BronzeStorage(bronze_dir, limit_bytes=10_000_000_000)
    silver_config = load_silver_config(
        PROJECT_ROOT / "config" / "silver.toml", project_root=tmp_path
    )
    pipeline = SilverPipeline(
        bronze_db=database,
        bronze_dir=bronze_dir,
        config=silver_config,
        project_root=tmp_path,
        tool_version="test",
    )
    return SilverEnv(
        root=tmp_path,
        bronze_dir=bronze_dir,
        database=database,
        catalog=catalog,
        storage=storage,
        pipeline=pipeline,
    )
