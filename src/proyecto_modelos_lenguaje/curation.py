"""Curation orchestration: analyze, review, quarantine, purge and restore."""

from __future__ import annotations

import json
import logging
import subprocess
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Any

from .catalog import Catalog
from .config import AppConfig, RelevanceConfig
from .extractors.links import decode_body, host_of, visible_text
from .relevance import RelevanceEvaluator
from .reporting import write_curation_report
from .storage import BronzeStorage, IntegrityError, StorageError
from .utils import utcnow

logger = logging.getLogger("proyecto_modelos_lenguaje.curation")

_TEXT_MEDIA = frozenset(
    {"application/xml", "text/xml", "application/json", "text/plain", "text/vtt", "text/csv"}
)


class CurationError(RuntimeError):
    exit_code = 1


class GuardError(CurationError):
    exit_code = 4


class PendingReviewsError(CurationError):
    exit_code = 5


class InvalidRunStateError(CurationError):
    exit_code = 6


class CurationIntegrityError(CurationError):
    exit_code = 7


@dataclass(slots=True)
class CurationSummary:
    run_id: str
    dry_run: bool
    status: str
    artifacts_evaluated: int
    kept: int
    removed: int
    review: int
    bytes_before: int
    bytes_quarantined: int
    bytes_freed: int
    config_hash: str
    report_paths: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dry_run": self.dry_run,
            "status": self.status,
            "artifacts_evaluated": self.artifacts_evaluated,
            "kept": self.kept,
            "removed": self.removed,
            "review": self.review,
            "bytes_before": self.bytes_before,
            "bytes_quarantined": self.bytes_quarantined,
            "bytes_freed": self.bytes_freed,
            "config_hash": self.config_hash,
            "report_paths": self.report_paths,
        }


class CurationService:
    def __init__(
        self,
        app_config: AppConfig,
        relevance_config: RelevanceConfig,
        *,
        catalog: Catalog,
        storage: BronzeStorage,
    ) -> None:
        self.app_config = app_config
        self.relevance = relevance_config
        self.catalog = catalog
        self.storage = storage
        self.evaluator = RelevanceEvaluator(relevance_config)

    # ------------------------------------------------------------------ analyze

    def analyze(
        self,
        *,
        run_id: str | None = None,
        campaign: str | None = None,
        apply: bool = False,
    ) -> CurationSummary:
        artifacts, total = self.catalog.list_artifacts(
            campaign_id=campaign, include_retracted=False, limit=1_000_000
        )
        bytes_before = sum(artifact.byte_size for artifact in artifacts)
        identifier = run_id or _new_run_id()
        if apply:
            if self.catalog.get_curation_run(identifier) is not None:
                raise InvalidRunStateError(f"curation run already exists: {identifier}")
            self.catalog.create_curation_run(
                run_id=identifier,
                config_hash=self.relevance.config_hash,
                tool_version=_tool_version(),
                scope_campaign=campaign,
                bytes_before=bytes_before,
                git_commit=_git_commit(),
            )
            self.catalog.update_curation_run(identifier, status="analyzing")

        counters = {"keep": 0, "remove": 0, "review": 0}
        for index, artifact in enumerate(artifacts, start=1):
            if index % 1000 == 0:
                logger.info(
                    "curation progress",
                    extra={"run_id": identifier, "detail": f"{index}/{len(artifacts)}"},
                )
            text, raw_text, text_available = self._read_text(artifact)
            result = self.evaluator.evaluate(
                source_id=artifact.source_id,
                url=artifact.url_canonical,
                title=artifact.title,
                text=text,
                raw_text=raw_text,
                text_available=text_available,
            )
            if not apply:
                counters[result.decision] += 1
                continue
            upserted = self.catalog.upsert_evaluation(
                artifact_id=artifact.artifact_id,
                run_id=identifier,
                decision=result.decision,
                level=result.level,
                score=result.score,
                explanation=result.explanation,
                content_hash=artifact.content_hash,
                config_hash=self.relevance.config_hash,
            )
            if not upserted:
                existing = self.catalog.get_evaluation(artifact.artifact_id)
                if existing:
                    counters[existing["decision"]] += 1
                continue
            self.catalog.replace_evidence(
                artifact.artifact_id,
                [
                    {
                        "term": hit.term,
                        "location": hit.location,
                        "snippet": hit.snippet,
                        "weight": hit.weight,
                    }
                    for hit in result.evidence
                ],
            )
            snippet = result.evidence[0].snippet if result.evidence else result.explanation
            self.catalog.sync_review_item(
                artifact_id=artifact.artifact_id,
                run_id=identifier,
                decision=result.decision,
                reason=result.explanation,
                snippet=snippet,
                score=result.score,
            )
            counters[result.decision] += 1

        report_paths: list[str] = []
        if apply:
            self.catalog.update_curation_run(
                identifier,
                status="analyzed",
                finished_at=utcnow(),
                artifacts_evaluated=total,
                kept=counters["keep"],
                removed=counters["remove"],
                review=counters["review"],
                bytes_before=bytes_before,
            )
            reports_dir = self.app_config.settings.bronze_dir / "reports" / identifier
            report_paths = write_curation_report(
                self.catalog,
                identifier,
                reports_dir,
                settings=self.relevance.settings,
            )
            self.catalog.update_curation_run(identifier, report_path=", ".join(report_paths))

        return CurationSummary(
            run_id=identifier,
            dry_run=not apply,
            status="analyzed" if apply else "dry-run",
            artifacts_evaluated=total,
            kept=counters["keep"],
            removed=counters["remove"],
            review=counters["review"],
            bytes_before=bytes_before,
            bytes_quarantined=0,
            bytes_freed=0,
            config_hash=self.relevance.config_hash,
            report_paths=report_paths,
        )

    # ------------------------------------------------------------------- review

    def list_reviews(
        self, run_id: str, *, limit: int = 50, offset: int = 0
    ) -> tuple[list[dict[str, Any]], int]:
        return self.catalog.list_review_items(run_id, limit=limit, offset=offset)

    def decide_review(
        self,
        *,
        artifact_id: int,
        decision: str,
        reviewer: str,
        note: str | None = None,
    ) -> None:
        artifact = self.catalog.get_artifact(artifact_id)
        if artifact is None:
            raise InvalidRunStateError(f"artifact not found: {artifact_id}")
        if decision == "remove":
            self._guard_protected(artifact)
        if not self.catalog.decide_review(
            artifact_id=artifact_id, decision=decision, reviewer=reviewer, note=note
        ):
            raise InvalidRunStateError(f"review item not found for artifact {artifact_id}")

    def approve(self, run_id: str, reviewer: str) -> dict[str, Any]:
        run = self._require_run(run_id)
        if run["status"] == "approved":
            return run
        if run["status"] != "analyzed":
            raise InvalidRunStateError(f"run {run_id} is not analyzed")
        pending = self.catalog.pending_review_count(run_id)
        if pending:
            raise PendingReviewsError(f"{pending} review items remain pending")
        self.catalog.approve_curation_run(run_id, reviewer)
        return self._require_run(run_id)

    # --------------------------------------------------------------- quarantine

    def quarantine(self, run_id: str) -> dict[str, Any]:
        run = self._require_run(run_id)
        if run["status"] in {"quarantined", "purged"}:
            return run
        if run["status"] not in {"approved", "quarantining"}:
            raise InvalidRunStateError(f"run {run_id} is not approved")
        self.catalog.update_curation_run(run_id, status="quarantining")
        evaluations, _ = self.catalog.evaluations(run_id, decision="remove")
        moved_bytes = 0
        moved = 0
        for evaluation in evaluations:
            artifact_id = int(evaluation["artifact_id"])
            existing = self.catalog.get_quarantine_entry(artifact_id)
            if existing and existing["status"] in {"quarantined", "purged"}:
                continue
            artifact = self.catalog.get_artifact(artifact_id)
            if artifact is None:
                continue
            self._guard_protected(artifact)
            evidence = self.catalog.evidence_for(artifact_id)
            self.catalog.add_audit_record(
                run_id=run_id,
                artifact_id=artifact_id,
                url_canonical=artifact.url_canonical,
                content_hash=artifact.content_hash,
                byte_size=artifact.byte_size,
                media_type=artifact.media_type,
                source_id=artifact.source_id,
                reason=str(evaluation["explanation"]),
                score=int(evaluation["score"]),
                evidence_json=json.dumps(evidence, ensure_ascii=False),
            )
            try:
                move = self.storage.quarantine(
                    artifact_id=artifact_id,
                    storage_path=artifact.storage_path,
                    expected_hash=artifact.content_hash,
                    run_id=run_id,
                )
            except (IntegrityError, StorageError) as exc:
                raise CurationIntegrityError(str(exc)) from exc
            self.catalog.add_quarantine_entry(
                artifact_id=artifact_id,
                run_id=run_id,
                original_path=move.original_path,
                quarantine_path=move.quarantine_path,
                byte_size=move.byte_size,
                expires_at=_expiry(self.relevance.settings.retention_days),
            )
            self.catalog.mark_audit_quarantined(artifact_id)
            moved_bytes += move.byte_size
            moved += 1
        self.catalog.refresh_manifests(active_only=True)
        total_bytes = int(run["bytes_quarantined"]) + moved_bytes
        self.catalog.update_curation_run(
            run_id,
            status="quarantined",
            finished_at=utcnow(),
            bytes_quarantined=total_bytes,
        )
        logger.info(
            "quarantine finished",
            extra={"run_id": run_id, "detail": f"{moved} artifacts moved"},
        )
        return self._require_run(run_id)

    def restore(self, artifact_id: int, *, reviewer: str = "restore") -> None:
        entry = self.catalog.get_quarantine_entry(artifact_id)
        if entry is None or entry["status"] != "quarantined":
            raise InvalidRunStateError(f"artifact {artifact_id} is not quarantined")
        artifact = self.catalog.get_artifact(artifact_id)
        if artifact is None:
            raise InvalidRunStateError(f"artifact not found: {artifact_id}")
        try:
            self.storage.restore(
                original_path=entry["original_path"],
                quarantine_path=entry["quarantine_path"],
                expected_hash=artifact.content_hash,
            )
        except (IntegrityError, StorageError) as exc:
            raise CurationIntegrityError(str(exc)) from exc
        self.catalog.update_quarantine_entry(artifact_id, status="restored", restored_at=utcnow())
        self.catalog.set_manual_decision(
            artifact_id=artifact_id,
            decision="keep",
            reviewer=reviewer,
            note="Restaurado desde cuarentena.",
        )
        self.catalog.refresh_manifests(active_only=True)

    def purge(self, run_id: str, *, now: bool = False) -> dict[str, Any]:
        run = self._require_run(run_id)
        if run["status"] == "purged":
            return run
        if run["status"] not in {"quarantined", "purging"}:
            raise InvalidRunStateError(f"run {run_id} is not quarantined")
        self.catalog.update_curation_run(run_id, status="purging")
        entries = self.catalog.list_quarantine_entries(run_id, status="quarantined")
        current = utcnow()
        eligible = [entry for entry in entries if now or str(entry["expires_at"]) <= current]
        if not eligible:
            self.catalog.update_curation_run(run_id, status="quarantined")
            return self._require_run(run_id)
        freed = 0
        purged = 0
        for entry in eligible:
            size = self.storage.purge(quarantine_path=entry["quarantine_path"])
            self.catalog.update_quarantine_entry(
                entry["artifact_id"], status="purged", purged_at=utcnow()
            )
            self.catalog.mark_audit_purged(entry["artifact_id"])
            freed += size
            purged += 1
        total_freed = int(run["bytes_freed"]) + freed
        self.catalog.update_curation_run(
            run_id,
            status="purged",
            finished_at=utcnow(),
            bytes_freed=total_freed,
        )
        logger.info(
            "purge finished",
            extra={"run_id": run_id, "detail": f"{purged} artifacts purged, {freed} bytes freed"},
        )
        return self._require_run(run_id)

    def report(self, run_id: str) -> list[str]:
        self._require_run(run_id)
        reports_dir = self.app_config.settings.bronze_dir / "reports" / run_id
        paths = write_curation_report(
            self.catalog, run_id, reports_dir, settings=self.relevance.settings
        )
        self.catalog.update_curation_run(run_id, report_path=", ".join(paths))
        return paths

    # ------------------------------------------------------------------ helpers

    def _require_run(self, run_id: str) -> dict[str, Any]:
        run = self.catalog.get_curation_run(run_id)
        if run is None:
            raise InvalidRunStateError(f"curation run not found: {run_id}")
        return run

    def _guard_protected(self, artifact: Any) -> None:
        host = host_of(artifact.url_canonical)
        protected = any(
            host == domain or host.endswith(f".{domain}")
            for domain in self.relevance.protected_domains
        )
        if protected or artifact.source_id == "official_site":
            raise GuardError(
                f"artifact {artifact.artifact_id} belongs to the protected official domain"
            )

    def _read_text(self, artifact: Any) -> tuple[str, str | None, bool]:
        path = self.storage.resolve(artifact.storage_path)
        limit = self.relevance.settings.max_scan_bytes
        size = path.stat().st_size
        if size <= limit:
            data = path.read_bytes()
        else:
            half = limit // 2
            with path.open("rb") as handle:
                head = handle.read(half)
                handle.seek(-half, 2)
                tail = handle.read(half)
            data = head + b"\n" + tail
        if artifact.media_type == "text/html":
            decoded = decode_body(data, None)
            return visible_text(decoded), decoded, True
        if artifact.media_type in _TEXT_MEDIA:
            decoded = decode_body(data, None)
            return decoded, decoded, True
        return "", None, False


def _new_run_id() -> str:
    return datetime.now(UTC).strftime("curation-%Y%m%d%H%M%S")


def _expiry(days: int) -> str:
    return (
        (datetime.now(UTC) + timedelta(days=days))
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _tool_version() -> str:
    try:
        from importlib.metadata import version

        return version("proyecto-modelos-lenguaje")
    except Exception:
        return "0.1.0"


def _git_commit() -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        return result.stdout.strip() or None
    except Exception:
        return None
