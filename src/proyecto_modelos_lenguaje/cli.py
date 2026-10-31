"""Command-line interface for the bronze layer."""

from __future__ import annotations

import argparse
import asyncio
import csv
import json
import logging
import random
import sys
from pathlib import Path
from typing import Any

from .campaign_service import start_campaign
from .catalog import Catalog, artifact_payload
from .config import (
    STORAGE_HARD_LIMIT,
    ConfigError,
    load_config,
    load_coverage_items,
    load_relevance_config,
)
from .coverage import build_matrix
from .curation import CurationError, CurationService
from .gold.pipeline import GoldPipeline
from .gold.store import GoldStateError
from .reporting import write_campaign_report, write_coverage_report
from .silver.pipeline import SilverPipeline
from .silver.state import SilverStateError
from .storage import BronzeStorage
from .utils import utcnow

DEFAULT_CONFIG = "config/sources.toml"
DEFAULT_RELEVANCE_CONFIG = "config/relevance.toml"


class _JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "level": record.levelname.lower(),
            "event": record.getMessage(),
        }
        for key in ("campaign_id", "url", "source_id", "detail"):
            value = getattr(record, key, None)
            if value:
                payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def _configure_logging() -> None:
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(_JsonFormatter())
    root = logging.getLogger("proyecto_modelos_lenguaje")
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(logging.INFO)
    # scrapling's own logger would break the structured stderr contract.
    logging.getLogger("scrapling").setLevel(logging.WARNING)


def _configure_event_loop() -> None:
    if sys.platform == "win32":
        try:
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        except AttributeError:
            return


def _emit(payload: dict[str, Any], as_json: bool) -> None:
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    for key, value in payload.items():
        if isinstance(value, (dict, list)):
            print(f"{key}: {json.dumps(value, ensure_ascii=False)}")
        else:
            print(f"{key}: {value}")


def _error(message: str, code: int) -> int:
    print(json.dumps({"status": "error", "detail": message}, ensure_ascii=False), file=sys.stderr)
    return code


def _open_catalog(config_path: Path) -> tuple[Any, Catalog]:
    config = load_config(config_path)
    catalog = Catalog(config.settings.bronze_dir / "_meta" / "bronze.sqlite3")
    catalog.init_schema()
    return config, catalog


def _coverage_path(args: argparse.Namespace, config) -> Path:
    if getattr(args, "coverage", None):
        return Path(args.coverage)
    return config.path.parent / "coverage-items.toml"


def _init_project(config, coverage_path: Path) -> tuple[int, int]:
    catalog = Catalog(config.settings.bronze_dir / "_meta" / "bronze.sqlite3")
    try:
        catalog.init_schema()
        sources = catalog.seed_sources(config.sources)
        items = catalog.seed_coverage(load_coverage_items(coverage_path))
        return sources, items
    finally:
        catalog.close()


def cmd_init(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    sources, items = _init_project(config, _coverage_path(args, config))
    _emit(
        {
            "status": "initialized",
            "schema_version": "1.0",
            "coverage_items": items,
            "sources": sources,
            "database": str(config.settings.bronze_dir / "_meta" / "bronze.sqlite3"),
        },
        args.json,
    )
    return 0


def cmd_campaign_start(args: argparse.Namespace) -> int:
    config = load_config(args.config)
    if args.max_bytes is not None and (args.max_bytes < 1 or args.max_bytes > STORAGE_HARD_LIMIT):
        return _error("--max-bytes must be between 1 and 10000000000", 3)
    run = start_campaign(
        config,
        campaign_id=args.campaign,
        resume=args.resume,
        dry_run=args.dry_run,
        max_targets=args.max_targets,
        max_bytes=args.max_bytes,
        coverage_path=_coverage_path(args, config),
    )
    _emit(run.summary.as_dict(), args.json)
    return run.summary.exit_code


def cmd_campaign_status(args: argparse.Namespace) -> int:
    config, catalog = _open_catalog(args.config)
    try:
        campaign = catalog.get_campaign(args.campaign)
        if campaign is None:
            return _error(f"campaign not found: {args.campaign}", 2)
        payload = {
            "campaign_id": campaign.campaign_id,
            "status": campaign.status,
            "started_at": campaign.started_at,
            "finished_at": campaign.finished_at,
            "config_hash": campaign.config_hash,
            "git_commit": campaign.git_commit,
            "tool_version": campaign.tool_version,
            "bytes_stored": campaign.bytes_stored,
            "artifact_count": campaign.artifact_count,
            "storage_limit_bytes": config.settings.storage_limit_bytes,
            "targets": catalog.target_counts(campaign.campaign_id),
            "outcomes": catalog.outcomes_by_reason(campaign.campaign_id),
        }
    finally:
        catalog.close()
    _emit(payload, args.json)
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    config, catalog = _open_catalog(args.config)
    storage = BronzeStorage(
        config.settings.bronze_dir, limit_bytes=config.settings.storage_limit_bytes
    )
    failures: list[dict[str, str]] = []
    try:
        artifacts, total = catalog.list_artifacts(
            campaign_id=args.campaign,
            include_retracted=True,
            active_only=True,
            limit=1_000_000,
        )
        sample_size = min(args.sample, total)
        sampled = random.Random(args.seed).sample(list(artifacts), sample_size)
        for artifact in sampled:
            try:
                valid = storage.verify(artifact.storage_path, artifact.content_hash)
            except Exception as exc:
                valid = False
                failures.append({"artifact_id": str(artifact.artifact_id), "reason": str(exc)})
                continue
            if not valid:
                failures.append(
                    {"artifact_id": str(artifact.artifact_id), "reason": "hash_mismatch"}
                )
                continue
            if not artifact.url_canonical or not artifact.retrieved_at or not artifact.category:
                failures.append(
                    {"artifact_id": str(artifact.artifact_id), "reason": "missing_metadata"}
                )
    finally:
        catalog.close()
    payload = {
        "campaign_id": args.campaign,
        "sampled": len(sampled),
        "passed": len(sampled) - len(failures),
        "failed": len(failures),
        "failures": failures,
    }
    _emit(payload, args.json)
    return 5 if failures else 0


def cmd_report(args: argparse.Namespace) -> int:
    config, catalog = _open_catalog(args.config)
    reports_dir = config.settings.bronze_dir / "reports" / args.campaign
    try:
        if catalog.get_campaign(args.campaign) is None:
            return _error(f"campaign not found: {args.campaign}", 2)
        if args.report_kind == "campaign":
            payload = write_campaign_report(
                catalog,
                args.campaign,
                reports_dir,
                storage_limit_bytes=config.settings.storage_limit_bytes,
            )
            if args.format == "md":
                print((reports_dir / "summary.md").read_text(encoding="utf-8"))
            else:
                print(reports_dir / "campaign.json")
        else:
            payload = write_coverage_report(catalog, args.campaign, reports_dir)
            if args.format == "md":
                print((reports_dir / "coverage.md").read_text(encoding="utf-8"))
            else:
                print(reports_dir / "coverage.json")
    finally:
        catalog.close()
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


def cmd_coverage(args: argparse.Namespace) -> int:
    _, catalog = _open_catalog(args.config)
    try:
        rows = build_matrix(catalog, args.campaign, active_only=args.active_only)
    finally:
        catalog.close()
    if args.status:
        rows = tuple(row for row in rows if row.status == args.status)
    payload = {
        "campaign_id": args.campaign,
        "generated_at": utcnow(),
        "items": [
            {
                "item_id": row.item_id,
                "category": row.category,
                "name": row.name,
                "status": row.status,
                "evidence_count": row.evidence_count,
                "artifact_refs": list(row.artifact_refs),
                "gap_reason": row.gap_reason,
            }
            for row in rows
        ],
    }
    _emit(payload, args.json)
    return 0


def cmd_catalog_list(args: argparse.Namespace) -> int:
    _, catalog = _open_catalog(args.config)
    try:
        artifacts, total = catalog.list_artifacts(
            campaign_id=args.campaign,
            category=args.category,
            source_id=args.source,
            language=args.language,
            coverage_item_id=args.coverage_item,
            include_retracted=args.include_retracted,
            active_only=args.active_only,
            limit=args.limit,
            offset=args.offset,
        )
    finally:
        catalog.close()
    payload = {
        "total": total,
        "count": len(artifacts),
        "offset": args.offset,
        "items": [artifact_payload(artifact) for artifact in artifacts],
    }
    _emit(payload, args.json)
    return 0


def cmd_catalog_show(args: argparse.Namespace) -> int:
    _, catalog = _open_catalog(args.config)
    try:
        artifact = catalog.get_artifact(args.artifact_id)
    finally:
        catalog.close()
    if artifact is None:
        return _error(f"artifact not found: {args.artifact_id}", 2)
    _emit(artifact_payload(artifact), args.json)
    return 0


def cmd_catalog_export(args: argparse.Namespace) -> int:
    config, catalog = _open_catalog(args.config)
    destination = Path(args.output)
    if not destination.is_absolute():
        destination = config.settings.bronze_dir / destination
    destination = destination.resolve()
    try:
        destination.relative_to(config.settings.bronze_dir.resolve())
    except ValueError:
        catalog.close()
        return _error("export destination must live under data/bronze/", 3)
    if destination.exists() and not args.force:
        catalog.close()
        return _error("destination exists; use --force to overwrite", 2)
    destination.parent.mkdir(parents=True, exist_ok=True)
    try:
        if args.format == "jsonl":
            count = catalog.export_jsonl(args.campaign, destination, active_only=args.active_only)
        else:
            artifacts, _ = catalog.list_artifacts(
                campaign_id=args.campaign,
                include_retracted=True,
                active_only=args.active_only,
                limit=1_000_000,
            )
            with destination.open("w", encoding="utf-8", newline="") as handle:
                writer = csv.writer(handle)
                writer.writerow(
                    [
                        "artifact_id",
                        "campaign_id",
                        "source_id",
                        "url_original",
                        "url_canonical",
                        "content_hash",
                        "media_type",
                        "byte_size",
                        "storage_path",
                        "retrieved_at",
                        "http_status",
                        "language",
                        "category",
                    ]
                )
                for artifact in artifacts:
                    writer.writerow(
                        [
                            artifact.artifact_id,
                            artifact.campaign_id,
                            artifact.source_id,
                            artifact.url_original,
                            artifact.url_canonical,
                            artifact.content_hash,
                            artifact.media_type,
                            artifact.byte_size,
                            artifact.storage_path,
                            artifact.retrieved_at,
                            artifact.http_status,
                            artifact.language,
                            artifact.category,
                        ]
                    )
            count = len(artifacts)
    finally:
        catalog.close()
    _emit({"status": "exported", "count": count, "path": str(destination)}, args.json)
    return 0


def _open_curation(args: argparse.Namespace) -> tuple[CurationService, Catalog]:
    app = load_config(args.config)
    relevance = load_relevance_config(getattr(args, "relevance_config", DEFAULT_RELEVANCE_CONFIG))
    catalog = Catalog(app.settings.bronze_dir / "_meta" / "bronze.sqlite3")
    catalog.init_schema()
    storage = BronzeStorage(app.settings.bronze_dir, limit_bytes=app.settings.storage_limit_bytes)
    service = CurationService(app, relevance, catalog=catalog, storage=storage)
    return service, catalog


def cmd_curate_analyze(args: argparse.Namespace) -> int:
    service, catalog = _open_curation(args)
    try:
        summary = service.analyze(run_id=args.run, campaign=args.campaign, apply=args.apply)
    finally:
        catalog.close()
    _emit(summary.as_dict(), args.json)
    return 0


def cmd_curate_runs(args: argparse.Namespace) -> int:
    _, catalog = _open_catalog(args.config)
    try:
        rows = catalog.connection.execute(
            "SELECT * FROM curation_runs ORDER BY started_at DESC"
        ).fetchall()
        runs = [dict(row) for row in rows]
    finally:
        catalog.close()
    _emit({"runs": runs, "total": len(runs)}, args.json)
    return 0


def cmd_curate_status(args: argparse.Namespace) -> int:
    _, catalog = _open_catalog(args.config)
    try:
        run = catalog.get_curation_run(args.run)
        if run is None:
            return _error(f"curation run not found: {args.run}", 2)
        entries = catalog.list_quarantine_entries(args.run)
        pending = catalog.pending_review_count(args.run)
    finally:
        catalog.close()
    payload = {
        **run,
        "pending_reviews": pending,
        "quarantined": sum(1 for entry in entries if entry["status"] == "quarantined"),
        "restored": sum(1 for entry in entries if entry["status"] == "restored"),
        "purged": sum(1 for entry in entries if entry["status"] == "purged"),
    }
    _emit(payload, args.json)
    return 0


def cmd_curate_report(args: argparse.Namespace) -> int:
    service, catalog = _open_curation(args)
    try:
        paths = service.report(args.run)
    finally:
        catalog.close()
    if args.format == "md":
        print(Path(paths[-1]).read_text(encoding="utf-8"))
    else:
        print(paths[0])
    return 0


def cmd_curate_review_list(args: argparse.Namespace) -> int:
    service, catalog = _open_curation(args)
    try:
        items, total = service.list_reviews(args.run, limit=args.limit, offset=args.offset)
    finally:
        catalog.close()
    _emit(
        {"total": total, "count": len(items), "offset": args.offset, "items": items},
        args.json,
    )
    return 0


def cmd_curate_review_decide(args: argparse.Namespace) -> int:
    service, catalog = _open_curation(args)
    try:
        service.decide_review(
            artifact_id=args.artifact,
            decision=args.decision,
            reviewer=args.reviewer,
            note=args.note,
        )
    finally:
        catalog.close()
    _emit(
        {
            "artifact_id": args.artifact,
            "decision": args.decision,
            "reviewer": args.reviewer,
            "status": "decided",
        },
        args.json,
    )
    return 0


def cmd_curate_approve(args: argparse.Namespace) -> int:
    service, catalog = _open_curation(args)
    try:
        run = service.approve(args.run, args.reviewer)
    finally:
        catalog.close()
    _emit(run, args.json)
    return 0


def cmd_curate_quarantine(args: argparse.Namespace) -> int:
    if not args.confirm:
        return _error("quarantine requires --confirm", 2)
    service, catalog = _open_curation(args)
    try:
        run = service.quarantine(args.run)
    finally:
        catalog.close()
    _emit(run, args.json)
    return 0


def cmd_curate_restore(args: argparse.Namespace) -> int:
    service, catalog = _open_curation(args)
    try:
        service.restore(args.artifact, reviewer=args.reviewer)
    finally:
        catalog.close()
    _emit({"artifact_id": args.artifact, "status": "restored"}, args.json)
    return 0


def cmd_curate_purge(args: argparse.Namespace) -> int:
    if not args.confirm:
        return _error("purge requires --confirm", 2)
    if not (args.now or args.expired):
        return _error("purge requires --now or --expired", 2)
    service, catalog = _open_curation(args)
    try:
        run = service.purge(args.run, now=args.now)
    finally:
        catalog.close()
    _emit(run, args.json)
    return 0


def cmd_silver_build(args: argparse.Namespace) -> int:
    pipeline = SilverPipeline.from_paths(
        sources_config=args.sources_config,
        silver_config=args.config,
    )
    payload = pipeline.build(
        args.run,
        limit=args.limit,
        source=args.source,
        force=args.force,
    )
    _emit(payload, args.json)
    return 0 if payload.get("status") == "completed" else 1


def cmd_silver_verify(args: argparse.Namespace) -> int:
    pipeline = SilverPipeline.from_paths(
        sources_config=args.sources_config,
        silver_config=args.config,
    )
    payload = pipeline.verify_run(args.run, sample=args.sample, seed=args.seed)
    _emit(payload, args.json)
    return 0 if payload.get("passed") else 1


def cmd_silver_report(args: argparse.Namespace) -> int:
    pipeline = SilverPipeline.from_paths(
        sources_config=args.sources_config,
        silver_config=args.config,
    )
    payload = pipeline.report(args.run)
    if args.format == "md":
        path = pipeline.config.output.root / "reports" / args.run / "quality.md"
        print(path.read_text(encoding="utf-8"))
        return 0
    _emit(payload, True)
    return 0


def cmd_silver_status(args: argparse.Namespace) -> int:
    pipeline = SilverPipeline.from_paths(
        sources_config=args.sources_config,
        silver_config=args.config,
    )
    payload = pipeline.status(args.run)
    _emit(payload, args.json)
    return 0


def cmd_gold_build(args: argparse.Namespace) -> int:
    pipeline = GoldPipeline.from_paths(
        silver_dir=args.silver_dir,
        config_path=args.config,
        taxonomy_path=args.taxonomy,
    )
    payload = pipeline.build(
        args.run,
        limit=args.limit,
        topic=args.topic,
        force=args.force,
    )
    _emit(payload, args.json)
    return 0 if payload.get("status") == "completed" else 1


def cmd_gold_verify(args: argparse.Namespace) -> int:
    pipeline = GoldPipeline.from_paths(
        silver_dir=args.silver_dir,
        config_path=args.config,
        taxonomy_path=args.taxonomy,
    )
    payload = pipeline.verify_run(args.run, sample=args.sample, seed=args.seed)
    _emit(payload, args.json)
    return 0 if payload.get("passed") else 1


def cmd_gold_report(args: argparse.Namespace) -> int:
    pipeline = GoldPipeline.from_paths(
        silver_dir=args.silver_dir,
        config_path=args.config,
        taxonomy_path=args.taxonomy,
    )
    payload = pipeline.report(args.run)
    if args.format == "md":
        path = pipeline.config.output.root / "reports" / args.run / "quality.md"
        print(path.read_text(encoding="utf-8"))
        return 0
    _emit(payload, True)
    return 0


def cmd_gold_status(args: argparse.Namespace) -> int:
    pipeline = GoldPipeline.from_paths(
        silver_dir=args.silver_dir,
        config_path=args.config,
        taxonomy_path=args.taxonomy,
    )
    payload = pipeline.status(args.run)
    _emit(payload, args.json)
    return 0


def build_parser() -> argparse.ArgumentParser:
    common = argparse.ArgumentParser(add_help=False)
    common.add_argument("--config", default=argparse.SUPPRESS, help="path to sources.toml")

    parser = argparse.ArgumentParser(
        prog="pml", description="Bronze layer for the Manuelita RAG", parents=[common]
    )
    sub = parser.add_subparsers(dest="command", required=True)

    init = sub.add_parser(
        "init", help="create the catalog and seed sources/coverage", parents=[common]
    )
    init.add_argument("--coverage", default=None)
    init.add_argument("--json", action="store_true")
    init.set_defaults(func=cmd_init)

    campaign = sub.add_parser("campaign", help="campaign operations", parents=[common])
    campaign_sub = campaign.add_subparsers(dest="campaign_command", required=True)

    start = campaign_sub.add_parser("start", help="start or resume a campaign", parents=[common])
    start.add_argument("--campaign", required=True)
    start.add_argument("--resume", action="store_true")
    start.add_argument("--dry-run", action="store_true")
    start.add_argument("--max-bytes", type=int, default=None)
    start.add_argument("--max-targets", type=int, default=None)
    start.add_argument("--json", action="store_true")
    start.set_defaults(func=cmd_campaign_start)

    status = campaign_sub.add_parser("status", help="show campaign state", parents=[common])
    status.add_argument("--campaign", required=True)
    status.add_argument("--json", action="store_true")
    status.set_defaults(func=cmd_campaign_status)

    verify = sub.add_parser("verify", help="verify artifact hashes and metadata", parents=[common])
    verify.add_argument("--campaign", required=True)
    verify.add_argument("--sample", type=int, default=20)
    verify.add_argument("--seed", type=int, default=0)
    verify.add_argument("--json", action="store_true")
    verify.set_defaults(func=cmd_verify)

    report = sub.add_parser("report", help="write campaign or coverage reports", parents=[common])
    report_sub = report.add_subparsers(dest="report_kind", required=True)
    for kind in ("campaign", "coverage"):
        node = report_sub.add_parser(kind, parents=[common])
        node.add_argument("--campaign", required=True)
        node.add_argument("--format", choices=["json", "md"], default="json")
        node.add_argument("--json", action="store_true")
        node.set_defaults(func=cmd_report)

    coverage = sub.add_parser(
        "coverage", help="print the 24-item coverage matrix", parents=[common]
    )
    coverage.add_argument("--campaign", required=True)
    coverage.add_argument("--status", choices=["covered", "partial", "missing"])
    coverage.add_argument("--active-only", action="store_true")
    coverage.add_argument("--json", action="store_true")
    coverage.set_defaults(func=cmd_coverage)

    catalog = sub.add_parser("catalog", help="catalog queries", parents=[common])
    catalog_sub = catalog.add_subparsers(dest="catalog_command", required=True)

    list_node = catalog_sub.add_parser("list", parents=[common])
    list_node.add_argument("--campaign")
    list_node.add_argument(
        "--category", choices=["identity", "offer", "digital_presence", "hard_data"]
    )
    list_node.add_argument("--source")
    list_node.add_argument("--language", choices=["es", "en", "und"])
    list_node.add_argument("--coverage-item")
    list_node.add_argument("--limit", type=int, default=100)
    list_node.add_argument("--offset", type=int, default=0)
    list_node.add_argument("--include-retracted", action="store_true")
    list_node.add_argument("--active-only", action="store_true")
    list_node.add_argument("--json", action="store_true")
    list_node.set_defaults(func=cmd_catalog_list)

    show = catalog_sub.add_parser("show", parents=[common])
    show.add_argument("--artifact-id", type=int, required=True)
    show.add_argument("--json", action="store_true")
    show.set_defaults(func=cmd_catalog_show)

    export = catalog_sub.add_parser("export", parents=[common])
    export.add_argument("--campaign", required=True)
    export.add_argument("--format", choices=["jsonl", "csv"], default="jsonl")
    export.add_argument("--output", required=True)
    export.add_argument("--force", action="store_true")
    export.add_argument("--active-only", action="store_true")
    export.add_argument("--json", action="store_true")
    export.set_defaults(func=cmd_catalog_export)

    curate = sub.add_parser("curate", help="relevance curation and cleanup", parents=[common])
    curate_sub = curate.add_subparsers(dest="curate_command", required=True)

    analyze = curate_sub.add_parser("analyze", parents=[common])
    analyze.add_argument("--relevance-config", default=DEFAULT_RELEVANCE_CONFIG)
    analyze.add_argument("--campaign")
    analyze.add_argument("--run")
    analyze.add_argument("--apply", action="store_true")
    analyze.add_argument("--json", action="store_true")
    analyze.set_defaults(func=cmd_curate_analyze)

    runs = curate_sub.add_parser("runs", parents=[common])
    runs.add_argument("--json", action="store_true")
    runs.set_defaults(func=cmd_curate_runs)

    curate_status = curate_sub.add_parser("status", parents=[common])
    curate_status.add_argument("--run", required=True)
    curate_status.add_argument("--json", action="store_true")
    curate_status.set_defaults(func=cmd_curate_status)

    curate_report = curate_sub.add_parser("report", parents=[common])
    curate_report.add_argument("--run", required=True)
    curate_report.add_argument("--format", choices=["json", "md"], default="json")
    curate_report.add_argument("--json", action="store_true")
    curate_report.set_defaults(func=cmd_curate_report)

    review = curate_sub.add_parser("review", parents=[common])
    review_sub = review.add_subparsers(dest="review_command", required=True)
    review_list = review_sub.add_parser("list", parents=[common])
    review_list.add_argument("--run", required=True)
    review_list.add_argument("--limit", type=int, default=50)
    review_list.add_argument("--offset", type=int, default=0)
    review_list.add_argument("--json", action="store_true")
    review_list.set_defaults(func=cmd_curate_review_list)
    review_decide = review_sub.add_parser("decide", parents=[common])
    review_decide.add_argument("--artifact", type=int, required=True)
    review_decide.add_argument("--decision", choices=["keep", "remove"], required=True)
    review_decide.add_argument("--reviewer", required=True)
    review_decide.add_argument("--note")
    review_decide.add_argument("--json", action="store_true")
    review_decide.set_defaults(func=cmd_curate_review_decide)

    approve = curate_sub.add_parser("approve", parents=[common])
    approve.add_argument("--run", required=True)
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--json", action="store_true")
    approve.set_defaults(func=cmd_curate_approve)

    quarantine = curate_sub.add_parser("quarantine", parents=[common])
    quarantine.add_argument("--run", required=True)
    quarantine.add_argument("--confirm", action="store_true")
    quarantine.add_argument("--json", action="store_true")
    quarantine.set_defaults(func=cmd_curate_quarantine)

    restore = curate_sub.add_parser("restore", parents=[common])
    restore.add_argument("--artifact", type=int, required=True)
    restore.add_argument("--reviewer", default="restore")
    restore.add_argument("--json", action="store_true")
    restore.set_defaults(func=cmd_curate_restore)

    purge = curate_sub.add_parser("purge", parents=[common])
    purge.add_argument("--run", required=True)
    purge.add_argument("--now", action="store_true")
    purge.add_argument("--expired", action="store_true")
    purge.add_argument("--confirm", action="store_true")
    purge.add_argument("--json", action="store_true")
    purge.set_defaults(func=cmd_curate_purge)

    silver = sub.add_parser("silver", help="silver layer operations")
    silver_sub = silver.add_subparsers(dest="silver_command", required=True)

    silver_build = silver_sub.add_parser("build", help="build or update the silver layer")
    silver_build.add_argument("--config", default="config/silver.toml")
    silver_build.add_argument("--sources-config", default=DEFAULT_CONFIG)
    silver_build.add_argument("--run", required=True)
    silver_build.add_argument("--limit", type=int, default=None)
    silver_build.add_argument("--source")
    silver_build.add_argument("--force", action="store_true")
    silver_build.add_argument("--json", action="store_true")
    silver_build.set_defaults(func=cmd_silver_build)

    silver_verify = silver_sub.add_parser("verify", help="audit a silver run")
    silver_verify.add_argument("--config", default="config/silver.toml")
    silver_verify.add_argument("--sources-config", default=DEFAULT_CONFIG)
    silver_verify.add_argument("--run", required=True)
    silver_verify.add_argument("--sample", type=int, default=50)
    silver_verify.add_argument("--seed", type=int, default=1)
    silver_verify.add_argument("--json", action="store_true")
    silver_verify.set_defaults(func=cmd_silver_verify)

    silver_report = silver_sub.add_parser("report", help="show a silver quality report")
    silver_report.add_argument("--config", default="config/silver.toml")
    silver_report.add_argument("--sources-config", default=DEFAULT_CONFIG)
    silver_report.add_argument("--run", required=True)
    silver_report.add_argument("--format", choices=["json", "md"], default="json")
    silver_report.set_defaults(func=cmd_silver_report)

    silver_status = silver_sub.add_parser("status", help="show the latest silver run")
    silver_status.add_argument("--config", default="config/silver.toml")
    silver_status.add_argument("--sources-config", default=DEFAULT_CONFIG)
    silver_status.add_argument("--run")
    silver_status.add_argument("--json", action="store_true")
    silver_status.set_defaults(func=cmd_silver_status)

    gold = sub.add_parser("gold", help="gold layer operations")
    gold_sub = gold.add_subparsers(dest="gold_command", required=True)

    gold_build = gold_sub.add_parser("build", help="build or update the gold layer")
    gold_build.add_argument("--config", default="config/gold.toml")
    gold_build.add_argument("--taxonomy", default="config/gold_taxonomy.toml")
    gold_build.add_argument("--silver-dir", default="data/silver")
    gold_build.add_argument("--run", required=True)
    gold_build.add_argument("--limit", type=int, default=None)
    gold_build.add_argument("--topic")
    gold_build.add_argument("--force", action="store_true")
    gold_build.add_argument("--json", action="store_true")
    gold_build.set_defaults(func=cmd_gold_build)

    gold_verify = gold_sub.add_parser("verify", help="audit a gold run")
    gold_verify.add_argument("--config", default="config/gold.toml")
    gold_verify.add_argument("--taxonomy", default="config/gold_taxonomy.toml")
    gold_verify.add_argument("--silver-dir", default="data/silver")
    gold_verify.add_argument("--run", required=True)
    gold_verify.add_argument("--sample", type=int, default=50)
    gold_verify.add_argument("--seed", type=int, default=1)
    gold_verify.add_argument("--json", action="store_true")
    gold_verify.set_defaults(func=cmd_gold_verify)

    gold_report = gold_sub.add_parser("report", help="show a gold quality report")
    gold_report.add_argument("--config", default="config/gold.toml")
    gold_report.add_argument("--taxonomy", default="config/gold_taxonomy.toml")
    gold_report.add_argument("--silver-dir", default="data/silver")
    gold_report.add_argument("--run", required=True)
    gold_report.add_argument("--format", choices=["json", "md"], default="json")
    gold_report.set_defaults(func=cmd_gold_report)

    gold_status = gold_sub.add_parser("status", help="show the latest gold run")
    gold_status.add_argument("--config", default="config/gold.toml")
    gold_status.add_argument("--taxonomy", default="config/gold_taxonomy.toml")
    gold_status.add_argument("--silver-dir", default="data/silver")
    gold_status.add_argument("--run")
    gold_status.add_argument("--json", action="store_true")
    gold_status.set_defaults(func=cmd_gold_status)

    return parser


def main(argv: list[str] | None = None) -> int:
    _configure_logging()
    _configure_event_loop()
    parser = build_parser()
    args = parser.parse_args(argv)
    if not hasattr(args, "config"):
        args.config = DEFAULT_CONFIG
    try:
        return int(args.func(args))
    except SilverStateError as exc:
        return _error(str(exc), 2)
    except GoldStateError as exc:
        return _error(str(exc), 2)
    except ConfigError as exc:
        return _error(str(exc), 3)
    except CurationError as exc:
        return _error(str(exc), exc.exit_code)
    except FileNotFoundError as exc:
        return _error(str(exc), 3)
    except KeyboardInterrupt:
        return _error("interrupted", 1)
