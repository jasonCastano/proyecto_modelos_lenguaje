"""Campaign orchestration: discovery, fetching, storage and reporting."""

from __future__ import annotations

import asyncio
import json
import logging
import random
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

from .catalog import Catalog, artifact_payload
from .config import PROJECT_ROOT, AppConfig, SourceConfig
from .coverage import build_matrix, gaps, infer_evidence, normalize_text, summarize
from .extractors.language import detect_language
from .extractors.links import (
    canonicalize_url,
    decode_body,
    extract_links,
    extract_meta,
    host_of,
    same_site,
    visible_text,
)
from .extractors.linktree import parse_linktree
from .extractors.metadata import (
    detect_media_type,
    is_allowed_media_type,
    parse_published_at,
)
from .fetchers.base import Fetcher, FetchResponse
from .fetchers.youtube import YoutubeAdapter, YoutubePart
from .models import (
    CampaignStatus,
    CoverageItem,
    Language,
    OutcomeType,
    ReasonCode,
    Target,
    TargetState,
)
from .policies import PolicyEngine, RateLimiter, RobotsCache
from .reporting import write_all_reports
from .sources import build_source
from .sources.base import DiscoveryContext
from .storage import (
    BronzeStorage,
    StorageLimitExceeded,
    StoredArtifact,
    sha256_bytes,
    sha256_text,
)
from .utils import utcnow

logger = logging.getLogger("proyecto_modelos_lenguaje.pipeline")

_TEXT_MEDIA = frozenset(
    {
        "text/html",
        "application/xml",
        "text/xml",
        "application/json",
        "text/plain",
        "text/vtt",
        "text/csv",
    }
)


@dataclass(slots=True)
class CampaignSummary:
    campaign_id: str
    status: str
    targets_discovered: int
    artifacts_stored: int
    deduplicated: int
    excluded: int
    failed: int
    deferred: int
    bytes_stored: int
    storage_limit_bytes: int
    coverage: dict[str, int]
    report_paths: list[str]

    def as_dict(self) -> dict[str, Any]:
        return {
            "campaign_id": self.campaign_id,
            "status": self.status,
            "targets_discovered": self.targets_discovered,
            "artifacts_stored": self.artifacts_stored,
            "deduplicated": self.deduplicated,
            "excluded": self.excluded,
            "failed": self.failed,
            "deferred": self.deferred,
            "bytes_stored": self.bytes_stored,
            "storage_limit_bytes": self.storage_limit_bytes,
            "coverage": self.coverage,
            "report_paths": self.report_paths,
        }

    @property
    def exit_code(self) -> int:
        return 4 if self.status == CampaignStatus.PAUSED.value else 0


class CampaignRunner:
    """Runs one campaign. Instances are single-use."""

    def __init__(
        self,
        config: AppConfig,
        coverage_items: tuple[CoverageItem, ...],
        *,
        catalog: Catalog,
        storage: BronzeStorage,
        fetcher: Fetcher,
        allow_private: bool = False,
        dry_run: bool = False,
        stop_after: int | None = None,
        max_targets: int | None = None,
        youtube_adapter: YoutubeAdapter | None = None,
    ) -> None:
        self.config = config
        self.coverage_items = coverage_items
        self.catalog = catalog
        self.storage = storage
        self.fetcher = fetcher
        self.dry_run = dry_run
        self.stop_after = stop_after
        self.max_targets = max_targets
        self._youtube = youtube_adapter or YoutubeAdapter(
            timeout=config.settings.request_timeout_seconds
        )
        self._sources: dict[str, SourceConfig] = {
            source.source_id: source for source in config.sources
        }
        self._robots = RobotsCache(
            fetcher,
            user_agent=config.settings.user_agent,
            timeout=config.settings.request_timeout_seconds,
            allow_private=allow_private,
        )
        self._policy = PolicyEngine(config, self._robots, allow_private=allow_private)
        self._limiter = RateLimiter(default_delay=config.settings.default_delay_seconds)
        self._queue: asyncio.Queue[Target | None] = asyncio.Queue()
        self._paused = False
        self._scheduling_stopped = False
        self._stored_count = 0
        self._scheduled = 0
        self._campaign_id = ""
        self._workers: list[asyncio.Task[None]] = []

    # ------------------------------------------------------------------ public

    async def run(self, campaign_id: str, *, resume: bool = False) -> CampaignSummary:
        self._campaign_id = campaign_id
        existing = self.catalog.get_campaign(campaign_id)
        if existing is None:
            self.catalog.create_campaign(
                campaign_id=campaign_id,
                config_hash=self.config.config_hash,
                tool_version=_tool_version(),
                git_commit=_git_commit(),
            )
            existing = self.catalog.get_campaign(campaign_id)
        assert existing is not None
        if existing.status in {
            CampaignStatus.COMPLETED.value,
            CampaignStatus.ABORTED.value,
            CampaignStatus.FAILED.value,
        }:
            logger.info("campaign already finished", extra={"campaign_id": campaign_id})
            return self._summary(existing.status, [])
        if existing.status in {CampaignStatus.PAUSED.value, CampaignStatus.RUNNING.value}:
            resume = True
        try:
            self.catalog.set_campaign_status(campaign_id, CampaignStatus.RUNNING.value)
        except Exception as exc:  # another campaign is running
            raise RuntimeError(f"cannot start campaign: {exc}") from exc

        try:
            if resume:
                await self._resume()
            else:
                await self._discover()
            await self._drain()
        except KeyboardInterrupt, asyncio.CancelledError:
            self._paused = True
            for worker in self._workers:
                worker.cancel()
            await asyncio.gather(*self._workers, return_exceptions=True)
            logger.warning("campaign interrupted", extra={"campaign_id": campaign_id})
        except Exception:
            self.catalog.set_campaign_status(campaign_id, CampaignStatus.FAILED.value)
            self.catalog.refresh_campaign_counters(campaign_id)
            raise

        self.catalog.refresh_campaign_counters(campaign_id)
        manifest = self._manifest_path()
        if not self.dry_run:
            self.catalog.export_jsonl(campaign_id, manifest)
        status = CampaignStatus.PAUSED.value if self._paused else CampaignStatus.COMPLETED.value
        self.catalog.set_campaign_status(campaign_id, status)
        self.catalog.refresh_campaign_counters(campaign_id)

        report_paths: list[str] = []
        if not self.dry_run:
            reports_dir = self.config.settings.bronze_dir / "reports" / campaign_id
            report_paths = [
                _display_path(path)
                for path in write_all_reports(
                    self.catalog,
                    campaign_id,
                    reports_dir,
                    storage_limit_bytes=self.config.settings.storage_limit_bytes,
                )
            ]
        return self._summary(status, report_paths)

    # --------------------------------------------------------------- discovery

    async def _discover(self) -> None:
        context = DiscoveryContext(
            fetcher=self.fetcher,
            policy=self._policy,
            limiter=self._limiter,
            timeout=self.config.settings.request_timeout_seconds,
        )
        for source in self.config.sources:
            if not source.enabled:
                continue
            adapter = build_source(source)
            if source.platform == "youtube":
                adapter.adapter = self._youtube  # type: ignore[attr-defined]
            try:
                candidates = await adapter.discover(context)
            except Exception as exc:
                logger.warning(
                    "source discovery failed",
                    extra={"source_id": source.source_id, "detail": str(exc)},
                )
                continue
            for candidate in candidates:
                await self._enqueue_candidate(source, adapter.default_category, candidate)
        logger.info("discovery finished", extra={"campaign_id": self._campaign_id})

    async def _enqueue_candidate(self, source, default_category, candidate) -> None:
        if self._paused or self._scheduling_stopped:
            return
        try:
            canonical = canonicalize_url(candidate.url)
        except ValueError:
            return
        target, created = self.catalog.add_target(
            campaign_id=self._campaign_id,
            source_id=source.source_id,
            url_original=candidate.url,
            url_canonical=canonical,
            category=candidate.category or default_category,
            depth=candidate.depth,
            priority=source.priority,
        )
        if created:
            self._scheduled += 1
            self._queue.put_nowait(target)
            if self.max_targets and self._scheduled >= self.max_targets:
                self._scheduling_stopped = True

    async def _resume(self) -> None:
        pending = self.catalog.pending_targets(self._campaign_id)
        for target in pending:
            self._queue.put_nowait(target)
            self._scheduled += 1
        logger.info(
            "campaign resumed",
            extra={"campaign_id": self._campaign_id, "pending": len(pending)},
        )

    # ----------------------------------------------------------------- workers

    async def _drain(self) -> None:
        self._workers = [
            asyncio.create_task(self._worker())
            for _ in range(min(self.config.settings.max_concurrency, 8))
        ]
        await self._queue.join()
        for _ in self._workers:
            self._queue.put_nowait(None)
        await asyncio.gather(*self._workers)
        await self.fetcher.aclose()

    async def _worker(self) -> None:
        while True:
            target = await self._queue.get()
            try:
                if target is None:
                    return
                if self._paused:
                    self.catalog.update_target_state(target.target_id, TargetState.DEFERRED)
                    continue
                await self._process(target)
            except Exception as exc:  # never let one URL abort the campaign
                logger.exception(
                    "target failed unexpectedly",
                    extra={
                        "campaign_id": self._campaign_id,
                        "url": getattr(target, "url_canonical", ""),
                    },
                )
                if target is not None:
                    self.catalog.update_target_state(target.target_id, TargetState.FAILED)
                    self.catalog.add_outcome(
                        campaign_id=self._campaign_id,
                        source_id=target.source_id,
                        url_canonical=target.url_canonical,
                        outcome_type=OutcomeType.FAILED.value,
                        reason_code=ReasonCode.PARSE_ERROR.value,
                        detail=str(exc)[:500],
                        attempts=target.attempts,
                    )
            finally:
                self._queue.task_done()

    # ---------------------------------------------------------------- processing

    async def _process(self, target: Target) -> None:
        source = self._sources[target.source_id]
        if target.attempts > self.config.settings.max_retries:
            self.catalog.add_outcome(
                campaign_id=self._campaign_id,
                source_id=target.source_id,
                url_canonical=target.url_canonical,
                outcome_type=OutcomeType.FAILED.value,
                reason_code=ReasonCode.HTTP_ERROR.value,
                detail="retry budget exhausted",
                attempts=target.attempts,
            )
            self.catalog.update_target_state(target.target_id, TargetState.FAILED)
            return

        self.catalog.update_target_state(
            target.target_id, TargetState.FETCHING, increment_attempts=True
        )
        decision = await self._policy.evaluate(target.url_canonical, source)
        self.catalog.add_policy_check(
            campaign_id=self._campaign_id,
            source_id=source.source_id,
            decision="allowed" if decision.allowed else "disallowed",
            reason=decision.detail,
        )
        if not decision.allowed:
            self.catalog.update_target_state(target.target_id, TargetState.EXCLUDED)
            self.catalog.add_outcome(
                campaign_id=self._campaign_id,
                source_id=source.source_id,
                url_canonical=target.url_canonical,
                outcome_type=OutcomeType.EXCLUDED.value,
                reason_code=decision.reason_code,
                detail=decision.detail,
                attempts=target.attempts + 1,
            )
            return
        if self.dry_run:
            self.catalog.update_target_state(target.target_id, TargetState.ALLOWED)
            return

        if source.platform == "youtube":
            await self._process_youtube(target, source)
        else:
            await self._process_http(target, source, decision.crawl_delay)

    async def _process_http(
        self, target: Target, source: SourceConfig, crawl_delay: float | None
    ) -> None:
        response = await self._fetch_with_retries(target.url_canonical, source, crawl_delay)
        if response is None or response.error:
            reason = _failure_reason(response.error if response else "no response")
            self._fail(target, reason, (response.error if response else "no response") or "")
            return
        if response.status in {401, 403}:
            self._fail(target, ReasonCode.BLOCKED, f"http_{response.status}")
            return
        if response.status == 429:
            self._fail(target, ReasonCode.RATE_LIMITED, "http_429")
            return
        if response.status >= 400 or response.status < 200:
            self._fail(target, ReasonCode.HTTP_ERROR, f"http_{response.status}")
            return
        if not response.body:
            self._fail(target, ReasonCode.EMPTY_CONTENT, "empty body")
            return
        media_type = detect_media_type(response.headers.get("content-type"), response.body)
        if not is_allowed_media_type(media_type, self.config.settings.allowed_media_types):
            self.catalog.update_target_state(target.target_id, TargetState.EXCLUDED)
            self.catalog.add_outcome(
                campaign_id=self._campaign_id,
                source_id=source.source_id,
                url_canonical=target.url_canonical,
                outcome_type=OutcomeType.EXCLUDED.value,
                reason_code=ReasonCode.OUT_OF_SCOPE.value,
                detail=f"unsupported media type: {media_type}",
                attempts=target.attempts + 1,
            )
            return

        body = response.body
        content_type = response.headers.get("content-type")
        html: str | None = None
        text = ""
        lang = Language.UND.value
        lang_method = "unknown"
        title: str | None = None
        published_at: str | None = None
        if media_type == "text/html":
            html = decode_body(body, content_type)
            meta = extract_meta(html)
            text = visible_text(html)
            title = meta.title
            published_at = parse_published_at(meta.published_at)
            lang, lang_method = detect_language(meta.lang, text)
        elif media_type in _TEXT_MEDIA:
            text = decode_body(body, content_type)
            title = _first_line(text)
            lang, lang_method = detect_language(None, text)

        text_hash = sha256_text(normalize_text(text)) if text else sha256_bytes(body)
        outcome = self._store(
            target=target,
            source=source,
            data=body,
            media_type=media_type,
            text_hash=text_hash,
            text=text,
            title=title,
            published_at=published_at,
            language=lang,
            language_method=lang_method,
            url_original=target.url_original,
            url_canonical=target.url_canonical,
            http_status=response.status,
        )
        if outcome == "deferred":
            return
        if html is not None and source.platform == "linktree":
            linktree = parse_linktree(html)
            if linktree:
                serialized = json.dumps(linktree, ensure_ascii=False, indent=2)
                linktree_outcome = self._store(
                    target=target,
                    source=source,
                    data=serialized.encode("utf-8"),
                    media_type="application/json",
                    text_hash=sha256_text(normalize_text(serialized)),
                    text=serialized,
                    title="Linktree oficial",
                    published_at=None,
                    language="es",
                    language_method="heuristic",
                    url_original=target.url_original,
                    url_canonical=f"{target.url_canonical}?view=linktree",
                    http_status=200,
                )
                if linktree_outcome == "deferred":
                    return
        if html is not None and source.follow_links:
            await self._follow_links(
                target, source, html, response.final_url or target.url_canonical
            )

    async def _process_youtube(self, target: Target, source: SourceConfig) -> None:
        await asyncio.sleep(max(source.delay_seconds, 1.0))
        path = urlsplit(target.url_canonical).path
        is_channel = path.startswith(("/@", "/channel/", "/c/", "/user/")) and not path.startswith(
            ("/watch", "/shorts", "/embed")
        )
        if is_channel:
            result = await asyncio.to_thread(self._youtube.fetch_channel, target.url_canonical)
        else:
            result = await asyncio.to_thread(self._youtube.fetch_video, target.url_canonical)
        if result.error:
            self._fail(target, ReasonCode.PARSE_ERROR, result.error[:500])
            return
        stored_any = False
        for part in result.parts:
            outcome = self._store(
                target=target,
                source=source,
                data=part.data,
                media_type=part.media_type,
                text_hash=_text_hash_for(part),
                text=part.data.decode("utf-8", errors="replace")
                if part.media_type in _TEXT_MEDIA
                else "",
                title=part.title,
                published_at=part.published_at,
                language=part.language,
                language_method="heuristic" if part.language in {"es", "en"} else "unknown",
                url_original=part.url,
                url_canonical=part.url,
                http_status=200,
            )
            stored_any = stored_any or outcome == "stored"
        if stored_any:
            self.catalog.update_target_state(target.target_id, TargetState.STORED)
        elif not self._paused:
            self.catalog.update_target_state(target.target_id, TargetState.DEDUPED)

    async def _follow_links(
        self, target: Target, source: SourceConfig, html: str, base_url: str
    ) -> None:
        max_depth = min(source.max_depth, self.config.settings.max_depth)
        if target.depth >= max_depth:
            return
        for link in extract_links(html, base_url):
            if not same_site(link, source.domain):
                continue
            await self._enqueue_candidate(
                source,
                target.category,
                _Candidate(link, depth=target.depth + 1),
            )

    # ------------------------------------------------------------------ storage

    def _store(
        self,
        *,
        target: Target,
        source: SourceConfig,
        data: bytes,
        media_type: str,
        text_hash: str,
        text: str,
        title: str | None,
        published_at: str | None,
        language: str,
        language_method: str,
        url_original: str,
        url_canonical: str,
        http_status: int,
    ) -> str:
        content_hash = sha256_bytes(data)
        existing_artifact = self.catalog.find_artifact_by_hash(content_hash)
        if existing_artifact is not None:
            stored = StoredArtifact(
                content_hash=content_hash,
                byte_size=existing_artifact.byte_size,
                storage_path=existing_artifact.storage_path,
            )
        else:
            if not self.storage.can_store(len(data)):
                self._paused = True
                self.catalog.update_target_state(target.target_id, TargetState.DEFERRED)
                self.catalog.add_outcome(
                    campaign_id=self._campaign_id,
                    source_id=source.source_id,
                    url_canonical=target.url_canonical,
                    outcome_type=OutcomeType.DEFERRED.value,
                    reason_code=ReasonCode.STORAGE_CAP.value,
                    detail=f"artifact of {len(data)} bytes exceeds remaining capacity",
                    attempts=target.attempts + 1,
                )
                return "deferred"
            try:
                stored = self.storage.store(
                    data,
                    media_type=media_type,
                    source_id=source.source_id,
                    campaign_id=self._campaign_id,
                )
            except StorageLimitExceeded as exc:
                self._paused = True
                self.catalog.update_target_state(target.target_id, TargetState.DEFERRED)
                self.catalog.add_outcome(
                    campaign_id=self._campaign_id,
                    source_id=source.source_id,
                    url_canonical=target.url_canonical,
                    outcome_type=OutcomeType.DEFERRED.value,
                    reason_code=ReasonCode.STORAGE_CAP.value,
                    detail=str(exc)[:500],
                    attempts=target.attempts + 1,
                )
                return "deferred"

        latest = self.catalog.latest_version(url_canonical)
        if latest is None:
            version, change_reason = 1, "first_capture"
        elif latest[1] != text_hash:
            version, change_reason = latest[0] + 1, "text_changed"
        else:
            version, change_reason = latest[0], None

        artifact, created = self.catalog.add_artifact(
            content_hash=stored.content_hash,
            text_hash=text_hash,
            media_type=media_type,
            byte_size=stored.byte_size,
            storage_path=stored.storage_path,
            retrieved_at=utcnow(),
            http_status=http_status,
            source_id=source.source_id,
            campaign_id=self._campaign_id,
            authority=source.authority,
            language=language
            if language in {item.value for item in Language}
            else Language.UND.value,
            language_method=language_method,
            title=title,
            published_at=published_at,
            version=version,
            url_original=url_original,
            url_canonical=url_canonical,
            category=target.category,
        )
        if change_reason:
            self.catalog.add_url_version(
                url_canonical=url_canonical,
                artifact_id=artifact.artifact_id,
                version=version,
                change_reason=change_reason,
            )
        self.catalog.link_artifact(
            campaign_id=self._campaign_id,
            artifact_id=artifact.artifact_id,
            target_id=target.target_id,
            captured_as="stored" if created else "deduped",
        )
        for evidence in infer_evidence(
            text, title=title, url=url_canonical, items=self.coverage_items
        ):
            self.catalog.add_coverage_evidence(
                item_id=evidence.item_id,
                artifact_id=artifact.artifact_id,
                confidence=evidence.confidence,
                note=evidence.note,
            )
        if created:
            self._stored_count += 1
        self.catalog.update_target_state(
            target.target_id, TargetState.STORED if created else TargetState.DEDUPED
        )
        if self.stop_after and self._stored_count >= self.stop_after:
            self._paused = True
        return "stored" if created else "deduped"

    async def _fetch_with_retries(
        self, url: str, source: SourceConfig, crawl_delay: float | None
    ) -> FetchResponse | None:
        settings = self.config.settings
        last: FetchResponse | None = None
        for attempt in range(settings.max_retries + 1):
            if attempt:
                backoff = settings.retry_backoff_seconds * (2 ** (attempt - 1))
                await asyncio.sleep(backoff + random.uniform(0, 0.25))
            await self._limiter.wait(host_of(url), crawl_delay or source.delay_seconds)
            response = await self.fetcher.fetch(url, timeout=settings.request_timeout_seconds)
            if response.error or response.status in {429, 500, 502, 503, 504}:
                last = response
                continue
            return response
        return last

    def _fail(self, target: Target, reason: str, detail: str) -> None:
        self.catalog.update_target_state(target.target_id, TargetState.FAILED)
        self.catalog.add_outcome(
            campaign_id=self._campaign_id,
            source_id=target.source_id,
            url_canonical=target.url_canonical,
            outcome_type=OutcomeType.FAILED.value,
            reason_code=reason,
            detail=detail[:500],
            attempts=target.attempts + 1,
        )

    # ------------------------------------------------------------------ summary

    def _manifest_path(self) -> Path:
        return self.config.settings.bronze_dir / "manifests" / f"{self._campaign_id}.jsonl"

    def _summary(self, status: str, report_paths: list[str]) -> CampaignSummary:
        campaign = self.catalog.get_campaign(self._campaign_id)
        counts = self.catalog.target_counts(self._campaign_id)
        rows = build_matrix(self.catalog, self._campaign_id)
        return CampaignSummary(
            campaign_id=self._campaign_id,
            status=status,
            targets_discovered=sum(counts.values()),
            artifacts_stored=counts.get("stored", 0),
            deduplicated=counts.get("deduped", 0),
            excluded=counts.get("excluded", 0),
            failed=counts.get("failed", 0),
            deferred=counts.get("deferred", 0),
            bytes_stored=campaign.bytes_stored if campaign else 0,
            storage_limit_bytes=self.config.settings.storage_limit_bytes,
            coverage=summarize(rows),
            report_paths=report_paths,
        )


@dataclass(frozen=True, slots=True)
class _Candidate:
    url: str
    depth: int = 0
    title: str | None = None
    category: str | None = None


def _failure_reason(error: str | None) -> str:
    if error and "timeout" in error.lower():
        return ReasonCode.TIMEOUT.value
    return ReasonCode.HTTP_ERROR.value


def _text_hash_for(part: YoutubePart) -> str:
    if part.media_type in _TEXT_MEDIA:
        return sha256_text(normalize_text(part.data.decode("utf-8", errors="replace")))
    return sha256_bytes(part.data)


def _first_line(text: str) -> str | None:
    for line in text.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:300]
    return None


def _display_path(path: str) -> str:
    try:
        return Path(path).resolve().relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return path


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


def summarize_campaign(catalog: Catalog, campaign_id: str) -> dict[str, Any]:
    rows = build_matrix(catalog, campaign_id)
    return {
        "summary": summarize(rows),
        "gaps": gaps(rows),
        "artifacts": [
            artifact_payload(artifact)
            for artifact in catalog.list_artifacts(campaign_id=campaign_id, limit=1000)[0]
        ],
    }
