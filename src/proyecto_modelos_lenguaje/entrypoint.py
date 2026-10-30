"""Canonical entry point for the bronze scraping pipeline."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tempfile
from collections import Counter
from collections.abc import Sequence
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from .campaign_service import CampaignRun, start_campaign
from .catalog import Catalog
from .config import PROJECT_ROOT, AppConfig, ConfigError, load_config
from .fetchers.base import Fetcher
from .pipeline import CampaignSummary

SCHEMA_VERSION = "1.0"
DEFAULT_CONFIG = "config/sources.toml"
CAMPAIGN_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$")

EXIT_OK = 0
EXIT_FAILURE = 1
EXIT_USAGE = 2
EXIT_PAUSED = 4

EXAMPLES = """Ejemplos:
  uv run python scripts/scrape_empresa.py --help
  uv run python scripts/scrape_empresa.py
  uv run python scripts/scrape_empresa.py --campaign 2026-10-m1-02-smoke --limit 3 --dry-run --json
  uv run python scripts/scrape_empresa.py --campaign 2026-10-m1-02-smoke --limit 3 --json
  uv run python scripts/scrape_empresa.py --campaign 2026-10-m1-02-smoke --resume
"""


@dataclass(frozen=True, slots=True)
class ScrapeRequest:
    config_path: str
    campaign_id: str | None
    resume: bool
    limit: int | None
    dry_run: bool
    json_output: bool


@dataclass(frozen=True, slots=True)
class EffectiveParameters:
    config: str
    campaign: str
    resume: bool
    limit: int | None
    dry_run: bool
    mode: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "config": self.config,
            "campaign": self.campaign,
            "resume": self.resume,
            "limit": self.limit,
            "dry_run": self.dry_run,
        }


@dataclass(frozen=True, slots=True)
class CampaignStateAssessment:
    exists: bool
    status: str | None
    action: str
    reason: str
    exit_code: int


@dataclass(frozen=True, slots=True)
class ScrapeOutcome:
    schema_version: str
    campaign_id: str
    status: str
    mode: str
    effective: EffectiveParameters
    summary: dict[str, Any]
    policy: dict[str, Any]
    duration_seconds: float
    exit_code: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "campaign_id": self.campaign_id,
            "status": self.status,
            "mode": self.mode,
            "effective": self.effective.to_dict(),
            "summary": dict(self.summary),
            "policy": dict(self.policy),
            "duration_seconds": self.duration_seconds,
            "exit_code": self.exit_code,
        }


@dataclass(frozen=True, slots=True)
class EntryError(Exception):
    code: str
    message: str
    exit_code: int = EXIT_USAGE

    def __str__(self) -> str:
        return self.message

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": SCHEMA_VERSION,
            "status": "error",
            "error": {"code": self.code, "message": self.message},
            "exit_code": self.exit_code,
        }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="scrape_empresa.py",
        description="Entrada canónica para ejecutar una campaña de scraping de bronce.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=EXAMPLES,
    )
    parser.add_argument(
        "--config",
        default=DEFAULT_CONFIG,
        help="Configuración de fuentes (por defecto: config/sources.toml).",
    )
    parser.add_argument(
        "--campaign",
        default=None,
        help="Identificador de la campaña. Obligatorio para ejecutar.",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Reanuda una campaña existente y reanudable.",
    )
    parser.add_argument(
        "--limit",
        default=None,
        help="Máximo de objetivos a procesar. Debe ser un entero positivo.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Descubre y reporta sin escribir en el bronce real.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emite un único objeto JSON validable.",
    )
    return parser


def parse_request(argv: Sequence[str]) -> ScrapeRequest:
    parser = build_parser()
    args = parser.parse_args(list(argv))
    limit: int | None = None
    if args.limit is not None:
        try:
            limit = int(args.limit)
        except (TypeError, ValueError) as exc:
            raise EntryError(
                "invalid_limit",
                f"--limit debe ser un entero positivo; se recibió {args.limit!r}.",
            ) from exc
    return ScrapeRequest(
        config_path=str(args.config),
        campaign_id=args.campaign,
        resume=bool(args.resume),
        limit=limit,
        dry_run=bool(args.dry_run),
        json_output=bool(args.json),
    )


def validate_request(request: ScrapeRequest, *, project_root: Path | None = None) -> AppConfig:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    if not request.campaign_id:
        raise EntryError(
            "invalid_campaign", "Falta --campaign: indica un identificador de campaña."
        )
    if not CAMPAIGN_PATTERN.fullmatch(request.campaign_id):
        raise EntryError(
            "invalid_campaign",
            "Identificador de campaña inválido. Usa letras, números, punto, guion o guion bajo "
            "y comienza con una letra o un número.",
        )
    if request.limit is not None and request.limit <= 0:
        raise EntryError("invalid_limit", "--limit debe ser un entero positivo.")
    config_path = Path(request.config_path)
    if not config_path.is_absolute():
        config_path = root / config_path
    if not config_path.is_file():
        raise EntryError(
            "missing_config",
            f"No existe la configuración: {request.config_path}.",
        )
    try:
        return load_config(config_path, project_root=root)
    except (ConfigError, OSError) as exc:
        raise EntryError("invalid_config", f"Configuración inválida: {exc}") from exc


def _read_campaign_status(database: Path, campaign_id: str) -> str | None:
    if not database.is_file():
        return None
    try:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            row = connection.execute(
                "SELECT status FROM campaigns WHERE campaign_id = ?", (campaign_id,)
            ).fetchone()
        finally:
            connection.close()
    except sqlite3.OperationalError:
        return None
    return str(row[0]) if row is not None else None


def assess_campaign_state(
    config: AppConfig,
    campaign_id: str,
    *,
    resume: bool,
) -> CampaignStateAssessment:
    database = config.settings.bronze_dir / "_meta" / "bronze.sqlite3"
    status = _read_campaign_status(database, campaign_id)
    if status is None:
        if resume:
            return CampaignStateAssessment(
                exists=False,
                status=None,
                action="missing_campaign_for_resume",
                reason="No existe la campaña que se intenta reanudar.",
                exit_code=EXIT_USAGE,
            )
        return CampaignStateAssessment(
            exists=False,
            status=None,
            action="create",
            reason="La campaña no existe; se creará.",
            exit_code=EXIT_OK,
        )
    if status in {"planned", "paused", "failed"}:
        return CampaignStateAssessment(
            exists=True,
            status=status,
            action="resume",
            reason=f"La campaña está en estado '{status}'; se reanudará.",
            exit_code=EXIT_OK,
        )
    if status == "running":
        return CampaignStateAssessment(
            exists=True,
            status=status,
            action="campaign_running",
            reason="Ya hay una campaña en ejecución; espera a que termine o reanúdala.",
            exit_code=EXIT_USAGE,
        )
    if status == "completed":
        return CampaignStateAssessment(
            exists=True,
            status=status,
            action="noop_completed",
            reason="La campaña ya está completada; no se reejecuta.",
            exit_code=EXIT_OK,
        )
    if status == "aborted":
        return CampaignStateAssessment(
            exists=True,
            status=status,
            action="campaign_aborted",
            reason="La campaña fue abortada; usa un identificador nuevo.",
            exit_code=EXIT_USAGE,
        )
    return CampaignStateAssessment(
        exists=True,
        status=status,
        action="invalid_config",
        reason=f"Estado de campaña no reconocido: {status}.",
        exit_code=EXIT_USAGE,
    )


def _relative_path(path: str, project_root: Path) -> str:
    candidate = Path(path)
    if not candidate.is_absolute():
        return candidate.as_posix()
    try:
        return candidate.resolve().relative_to(project_root.resolve()).as_posix()
    except ValueError:
        return candidate.as_posix()


def _summary_payload(summary: CampaignSummary | dict[str, Any]) -> dict[str, Any]:
    raw = summary.as_dict() if isinstance(summary, CampaignSummary) else dict(summary)
    return {
        "targets_discovered": int(raw.get("targets_discovered", 0)),
        "artifacts_stored": int(raw.get("artifacts_stored", 0)),
        "deduplicated": int(raw.get("deduplicated", 0)),
        "excluded": int(raw.get("excluded", 0)),
        "failed": int(raw.get("failed", 0)),
        "deferred": int(raw.get("deferred", 0)),
        "bytes_stored": int(raw.get("bytes_stored", 0)),
        "storage_limit_bytes": max(1, int(raw.get("storage_limit_bytes", 1))),
        "coverage": {str(key): int(value) for key, value in raw.get("coverage", {}).items()},
        "report_paths": [str(item) for item in raw.get("report_paths", [])],
    }


def aggregate_policy(checks: Sequence[dict[str, Any]]) -> dict[str, Any]:
    allowed = 0
    disallowed = 0
    unreachable = 0
    by_reason: Counter[str] = Counter()
    for check in checks:
        decision = str(check.get("decision", ""))
        reason = str(check.get("reason", "")) or "unknown"
        by_reason[reason] += 1
        if reason in {"robots_unreachable", "unresolvable_host"}:
            unreachable += 1
        elif decision == "allowed":
            allowed += 1
        elif decision == "disallowed":
            disallowed += 1
    return {
        "allowed": allowed,
        "disallowed": disallowed,
        "unreachable": unreachable,
        "by_reason": dict(sorted(by_reason.items())),
    }


def _build_outcome(
    run: CampaignRun,
    request: ScrapeRequest,
    config: AppConfig,
    *,
    mode: str,
    project_root: Path,
) -> ScrapeOutcome:
    summary = _summary_payload(run.summary)
    summary["report_paths"] = [
        _relative_path(path, project_root) for path in summary["report_paths"]
    ]
    status = str(run.summary.status)
    exit_code = EXIT_PAUSED if status == "paused" else EXIT_OK
    effective = EffectiveParameters(
        config=_relative_path(str(config.path), project_root),
        campaign=str(request.campaign_id),
        resume=run.resumed,
        limit=request.limit,
        dry_run=run.dry_run,
        mode=mode,
    )
    return ScrapeOutcome(
        schema_version=SCHEMA_VERSION,
        campaign_id=str(request.campaign_id),
        status=status,
        mode=mode,
        effective=effective,
        summary=summary,
        policy=aggregate_policy(run.policy),
        duration_seconds=round(float(run.duration_seconds), 3),
        exit_code=exit_code,
    )


def _completed_outcome(
    request: ScrapeRequest,
    config: AppConfig,
    *,
    project_root: Path,
) -> ScrapeOutcome:
    campaign_id = str(request.campaign_id)
    database = config.settings.bronze_dir / "_meta" / "bronze.sqlite3"
    catalog = Catalog(database)
    try:
        campaign = catalog.get_campaign(campaign_id)
        targets = catalog.target_counts(campaign_id)
        policy_checks = catalog.policy_checks(campaign_id)
    finally:
        catalog.close()
    summary = {
        "targets_discovered": sum(targets.values()),
        "artifacts_stored": campaign.artifact_count if campaign else 0,
        "deduplicated": targets.get("deduped", 0),
        "excluded": targets.get("excluded", 0),
        "failed": targets.get("failed", 0),
        "deferred": targets.get("deferred", 0),
        "bytes_stored": campaign.bytes_stored if campaign else 0,
        "storage_limit_bytes": config.settings.storage_limit_bytes,
        "coverage": {},
        "report_paths": [],
    }
    effective = EffectiveParameters(
        config=_relative_path(str(config.path), project_root),
        campaign=campaign_id,
        resume=False,
        limit=request.limit,
        dry_run=False,
        mode="already_completed",
    )
    return ScrapeOutcome(
        schema_version=SCHEMA_VERSION,
        campaign_id=campaign_id,
        status="completed",
        mode="already_completed",
        effective=effective,
        summary=_summary_payload(summary),
        policy=aggregate_policy(policy_checks),
        duration_seconds=0.0,
        exit_code=EXIT_OK,
    )


def execute(
    request: ScrapeRequest,
    config: AppConfig,
    assessment: CampaignStateAssessment,
    *,
    project_root: Path | None = None,
    allow_private: bool = False,
    fetcher: Fetcher | None = None,
) -> ScrapeOutcome:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    campaign_id = str(request.campaign_id)
    if assessment.action == "noop_completed":
        return _completed_outcome(request, config, project_root=root)

    coverage_path = config.path.parent / "coverage-items.toml"
    if request.dry_run:
        with tempfile.TemporaryDirectory(prefix="scrape-empresa-dry-") as temporary:
            temporary_config = replace(
                config,
                settings=replace(config.settings, data_root=Path(temporary)),
            )
            run = start_campaign(
                temporary_config,
                campaign_id=campaign_id,
                resume=False,
                dry_run=True,
                max_targets=request.limit,
                coverage_path=coverage_path,
                allow_private=allow_private,
                fetcher=fetcher,
            )
        return _build_outcome(run, request, config, mode="dry_run", project_root=root)

    resume = assessment.action == "resume"
    run = start_campaign(
        config,
        campaign_id=campaign_id,
        resume=resume,
        dry_run=False,
        max_targets=request.limit,
        coverage_path=coverage_path,
        allow_private=allow_private,
        fetcher=fetcher,
    )
    return _build_outcome(
        run,
        request,
        config,
        mode="resume" if resume else "new",
        project_root=root,
    )


def render_human(outcome: ScrapeOutcome) -> str:
    summary = outcome.summary
    omitted = summary["excluded"] + summary["deduplicated"] + summary["deferred"]
    limit = "sin límite" if outcome.effective.limit is None else str(outcome.effective.limit)
    reports = ", ".join(summary["report_paths"]) or "—"
    lines = [
        f"Campaña: {outcome.campaign_id}",
        f"Configuración: {outcome.effective.config}",
        f"Modo: {outcome.mode}",
        f"Límite: {limit}",
        f"Estado: {outcome.status}",
        f"Descubiertos: {summary['targets_discovered']}",
        f"Almacenados: {summary['artifacts_stored']}",
        f"Omitidos: {omitted} (excluidos {summary['excluded']}, "
        f"duplicados {summary['deduplicated']}, diferidos {summary['deferred']})",
        f"Fallidos: {summary['failed']}",
        f"Bytes: {summary['bytes_stored']}",
        f"Duración: {outcome.duration_seconds:.2f} s",
        f"Políticas: permitidas={outcome.policy['allowed']}, "
        f"bloqueadas={outcome.policy['disallowed']}, "
        f"inalcanzables={outcome.policy['unreachable']}",
        f"Reportes: {reports}",
    ]
    return "\n".join(lines)


def render_json(outcome: ScrapeOutcome) -> str:
    return json.dumps(outcome.to_dict(), ensure_ascii=False, indent=2)


def _print_error(error: EntryError, *, as_json: bool) -> None:
    if as_json:
        print(json.dumps(error.to_dict(), ensure_ascii=False, indent=2))
    else:
        print(f"Error [{error.code}]: {error.message}", file=sys.stderr)


def main(
    argv: Sequence[str] | None = None,
    *,
    project_root: Path | None = None,
    allow_private: bool = False,
    fetcher: Fetcher | None = None,
) -> int:
    arguments = list(sys.argv[1:] if argv is None else argv)
    parser = build_parser()
    as_json = "--json" in arguments
    if not arguments:
        parser.print_help()
        return EXIT_OK
    try:
        request = parse_request(arguments)
        if request.campaign_id is None:
            parser.print_help()
            return EXIT_OK
        config = validate_request(request, project_root=project_root)
        assessment = assess_campaign_state(config, request.campaign_id, resume=request.resume)
        if assessment.exit_code != EXIT_OK:
            raise EntryError(assessment.action, assessment.reason, assessment.exit_code)
        outcome = execute(
            request,
            config,
            assessment,
            project_root=project_root,
            allow_private=allow_private,
            fetcher=fetcher,
        )
    except SystemExit as exc:
        return int(exc.code or 0)
    except EntryError as exc:
        _print_error(exc, as_json=as_json)
        return exc.exit_code
    except Exception as exc:
        error = EntryError("pipeline_failure", str(exc), EXIT_FAILURE)
        _print_error(error, as_json=as_json)
        return error.exit_code

    print(render_json(outcome) if request.json_output else render_human(outcome))
    return outcome.exit_code
