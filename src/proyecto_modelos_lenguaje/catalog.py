"""SQLite catalog for the bronze layer."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from .config import SourceConfig
from .models import (
    Artifact,
    Campaign,
    CoverageItem,
    CoverageRow,
    CoverageStatus,
    Language,
    Target,
    TargetState,
)
from .utils import utcnow

SCHEMA_VERSION = "1.0"

SCHEMA = """
CREATE TABLE IF NOT EXISTS schema_meta (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    campaign_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN
        ('planned','running','paused','completed','aborted','failed')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    config_hash TEXT NOT NULL,
    git_commit TEXT,
    tool_version TEXT NOT NULL,
    bytes_stored INTEGER NOT NULL DEFAULT 0 CHECK (bytes_stored >= 0),
    artifact_count INTEGER NOT NULL DEFAULT 0 CHECK (artifact_count >= 0),
    notes TEXT
);

CREATE UNIQUE INDEX IF NOT EXISTS ux_campaign_running
    ON campaigns(status) WHERE status = 'running';

CREATE TABLE IF NOT EXISTS sources (
    source_id TEXT PRIMARY KEY,
    domain TEXT NOT NULL,
    platform TEXT NOT NULL,
    authority TEXT NOT NULL CHECK (authority IN ('first_party','third_party','open_data')),
    policy_status TEXT NOT NULL CHECK (
        policy_status IN ('allowed','restricted','excluded','unknown')
    ),
    policy_notes TEXT,
    crawl_delay_seconds REAL NOT NULL DEFAULT 1.0 CHECK (crawl_delay_seconds >= 0),
    priority INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 0 AND 3),
    enabled INTEGER NOT NULL DEFAULT 1 CHECK (enabled IN (0,1))
);

CREATE TABLE IF NOT EXISTS acquisition_targets (
    target_id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    url_original TEXT NOT NULL,
    url_canonical TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN
        ('identity','offer','digital_presence','hard_data')),
    coverage_item_id TEXT,
    depth INTEGER NOT NULL DEFAULT 0 CHECK (depth BETWEEN 0 AND 3),
    priority INTEGER NOT NULL DEFAULT 2 CHECK (priority BETWEEN 0 AND 3),
    state TEXT NOT NULL CHECK (state IN
        ('discovered','allowed','excluded','fetching','stored','deduped','failed','deferred')),
    discovered_from TEXT,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    first_seen_at TEXT NOT NULL,
    last_attempt_at TEXT,
    UNIQUE (campaign_id, url_canonical)
);

CREATE INDEX IF NOT EXISTS ix_targets_campaign_state
    ON acquisition_targets(campaign_id, state);

CREATE TABLE IF NOT EXISTS artifacts (
    artifact_id INTEGER PRIMARY KEY AUTOINCREMENT,
    content_hash TEXT NOT NULL UNIQUE,
    text_hash TEXT,
    media_type TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size > 0),
    storage_path TEXT NOT NULL UNIQUE,
    retrieved_at TEXT NOT NULL,
    http_status INTEGER NOT NULL CHECK (http_status BETWEEN 100 AND 599),
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id),
    authority TEXT NOT NULL CHECK (authority IN ('first_party','third_party','open_data')),
    language TEXT NOT NULL CHECK (language IN ('es','en','und')),
    language_method TEXT NOT NULL CHECK (language_method IN ('html_lang','heuristic','unknown')),
    title TEXT,
    published_at TEXT,
    version INTEGER NOT NULL DEFAULT 1 CHECK (version >= 1),
    url_original TEXT NOT NULL,
    url_canonical TEXT NOT NULL,
    category TEXT NOT NULL CHECK (category IN
        ('identity','offer','digital_presence','hard_data')),
    retracted_at TEXT,
    retraction_reason TEXT
);

CREATE INDEX IF NOT EXISTS ix_artifacts_campaign ON artifacts(campaign_id);
CREATE INDEX IF NOT EXISTS ix_artifacts_source ON artifacts(source_id);
CREATE INDEX IF NOT EXISTS ix_artifacts_category ON artifacts(category);
CREATE INDEX IF NOT EXISTS ix_artifacts_url ON artifacts(url_canonical);

CREATE TABLE IF NOT EXISTS url_versions (
    url_version_id INTEGER PRIMARY KEY AUTOINCREMENT,
    url_canonical TEXT NOT NULL,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(artifact_id),
    version INTEGER NOT NULL CHECK (version >= 1),
    observed_at TEXT NOT NULL,
    change_reason TEXT NOT NULL CHECK (change_reason IN
        ('first_capture','text_changed','retracted')),
    UNIQUE (url_canonical, version)
);

CREATE INDEX IF NOT EXISTS ix_url_versions_artifact ON url_versions(artifact_id);

CREATE TABLE IF NOT EXISTS campaign_artifacts (
    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(artifact_id),
    target_id INTEGER,
    captured_as TEXT NOT NULL CHECK (captured_as IN ('stored','deduped')),
    observed_at TEXT NOT NULL,
    PRIMARY KEY (campaign_id, artifact_id)
);

CREATE TABLE IF NOT EXISTS coverage_items (
    item_id TEXT PRIMARY KEY,
    category TEXT NOT NULL CHECK (category IN
        ('identity','offer','digital_presence','hard_data')),
    name TEXT NOT NULL,
    keywords TEXT NOT NULL,
    required INTEGER NOT NULL DEFAULT 1 CHECK (required IN (0,1))
);

CREATE TABLE IF NOT EXISTS coverage_evidence (
    coverage_evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    item_id TEXT NOT NULL REFERENCES coverage_items(item_id),
    artifact_id INTEGER NOT NULL REFERENCES artifacts(artifact_id),
    confidence TEXT NOT NULL CHECK (confidence IN ('direct','supporting')),
    note TEXT,
    UNIQUE (item_id, artifact_id)
);

CREATE TABLE IF NOT EXISTS outcomes (
    outcome_id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    url_canonical TEXT NOT NULL,
    outcome_type TEXT NOT NULL CHECK (outcome_type IN ('excluded','failed','deferred')),
    reason_code TEXT NOT NULL CHECK (reason_code IN
        ('robots_disallowed','tos_restricted','requires_auth','out_of_scope',
         'manual_exclusion','blocked','rate_limited','timeout','http_error',
         'parse_error','storage_cap','empty_content')),
    detail TEXT,
    attempts INTEGER NOT NULL DEFAULT 0 CHECK (attempts >= 0),
    occurred_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_outcomes_campaign ON outcomes(campaign_id);

CREATE TABLE IF NOT EXISTS policy_checks (
    policy_check_id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL REFERENCES campaigns(campaign_id) ON DELETE CASCADE,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    decision TEXT NOT NULL CHECK (decision IN ('allowed','disallowed','unknown')),
    reason TEXT NOT NULL,
    checked_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS curation_runs (
    run_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK (status IN
        ('planned','analyzing','analyzed','approved','quarantining','quarantined',
         'purging','purged','aborted')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    config_hash TEXT NOT NULL,
    git_commit TEXT,
    tool_version TEXT NOT NULL,
    scope_campaign TEXT,
    artifacts_evaluated INTEGER NOT NULL DEFAULT 0 CHECK (artifacts_evaluated >= 0),
    kept INTEGER NOT NULL DEFAULT 0 CHECK (kept >= 0),
    removed INTEGER NOT NULL DEFAULT 0 CHECK (removed >= 0),
    review INTEGER NOT NULL DEFAULT 0 CHECK (review >= 0),
    bytes_before INTEGER NOT NULL DEFAULT 0 CHECK (bytes_before >= 0),
    bytes_quarantined INTEGER NOT NULL DEFAULT 0 CHECK (bytes_quarantined >= 0),
    bytes_freed INTEGER NOT NULL DEFAULT 0 CHECK (bytes_freed >= 0),
    approved_by TEXT,
    approved_at TEXT,
    report_path TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS relevance_evaluations (
    artifact_id INTEGER PRIMARY KEY REFERENCES artifacts(artifact_id),
    run_id TEXT NOT NULL REFERENCES curation_runs(run_id),
    decision TEXT NOT NULL CHECK (decision IN ('keep','remove','review')),
    level TEXT NOT NULL CHECK (level IN ('direct','contextual','none')),
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    method TEXT NOT NULL CHECK (method IN ('rule_based','manual')),
    explanation TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    config_hash TEXT NOT NULL,
    manual_override INTEGER NOT NULL DEFAULT 0 CHECK (manual_override IN (0,1)),
    reviewer TEXT,
    reviewed_at TEXT,
    evaluated_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS ix_evaluations_run ON relevance_evaluations(run_id, decision);

CREATE TABLE IF NOT EXISTS relevance_evidence (
    evidence_id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER NOT NULL REFERENCES artifacts(artifact_id),
    term TEXT NOT NULL,
    location TEXT NOT NULL CHECK (location IN ('title','body','url','metadata')),
    snippet TEXT NOT NULL,
    weight INTEGER NOT NULL CHECK (weight BETWEEN -100 AND 100),
    created_at TEXT NOT NULL,
    UNIQUE (artifact_id, term, location)
);

CREATE TABLE IF NOT EXISTS review_items (
    artifact_id INTEGER PRIMARY KEY REFERENCES artifacts(artifact_id),
    run_id TEXT NOT NULL REFERENCES curation_runs(run_id),
    reason TEXT NOT NULL,
    snippet TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    status TEXT NOT NULL CHECK (status IN ('pending','decided')),
    decision TEXT CHECK (decision IN ('keep','remove')),
    reviewer TEXT,
    decided_at TEXT,
    note TEXT
);

CREATE TABLE IF NOT EXISTS curation_audit (
    audit_id INTEGER PRIMARY KEY AUTOINCREMENT,
    run_id TEXT NOT NULL REFERENCES curation_runs(run_id),
    artifact_id INTEGER UNIQUE NOT NULL REFERENCES artifacts(artifact_id),
    url_canonical TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size > 0),
    media_type TEXT NOT NULL,
    source_id TEXT NOT NULL REFERENCES sources(source_id),
    decision TEXT NOT NULL CHECK (decision = 'remove'),
    reason TEXT NOT NULL,
    score INTEGER NOT NULL CHECK (score BETWEEN 0 AND 100),
    evidence_json TEXT NOT NULL,
    decided_at TEXT NOT NULL,
    quarantined_at TEXT,
    purged_at TEXT
);

CREATE TABLE IF NOT EXISTS quarantine_entries (
    quarantine_id INTEGER PRIMARY KEY AUTOINCREMENT,
    artifact_id INTEGER UNIQUE NOT NULL REFERENCES artifacts(artifact_id),
    run_id TEXT NOT NULL REFERENCES curation_runs(run_id),
    original_path TEXT NOT NULL,
    quarantine_path TEXT NOT NULL,
    byte_size INTEGER NOT NULL CHECK (byte_size > 0),
    moved_at TEXT NOT NULL,
    expires_at TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('quarantined','restored','purged')),
    restored_at TEXT,
    purged_at TEXT
);

CREATE INDEX IF NOT EXISTS ix_quarantine_run ON quarantine_entries(run_id, status);

CREATE VIEW IF NOT EXISTS v_active_artifacts AS
SELECT a.*
FROM artifacts a
LEFT JOIN relevance_evaluations e ON e.artifact_id = a.artifact_id
LEFT JOIN curation_runs r ON r.run_id = e.run_id
LEFT JOIN quarantine_entries q
       ON q.artifact_id = a.artifact_id AND q.status = 'quarantined'
WHERE a.retracted_at IS NULL
  AND q.quarantine_id IS NULL
  AND (
        e.artifact_id IS NULL
        OR e.decision = 'keep'
        OR r.status NOT IN ('approved','quarantining','quarantined','purging','purged')
      );
"""


def _iso(value: Any) -> str | None:
    return str(value) if value is not None else None


class Catalog:
    """Transactional catalog backed by SQLite."""

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(self.path, timeout=30)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA foreign_keys=ON")
        self._conn.execute("PRAGMA busy_timeout=5000")

    def __enter__(self) -> Catalog:
        return self

    def __exit__(self, *_: object) -> None:
        self.close()

    def close(self) -> None:
        self._conn.close()

    @property
    def connection(self) -> sqlite3.Connection:
        return self._conn

    def init_schema(self) -> None:
        self._conn.executescript(SCHEMA)
        self._conn.execute(
            "INSERT OR REPLACE INTO schema_meta(key, value) VALUES ('schema_version', ?)",
            (SCHEMA_VERSION,),
        )
        self._conn.commit()

    def seed_sources(self, sources: Iterable[SourceConfig]) -> int:
        count = 0
        for source in sources:
            policy_status = "excluded" if source.policy.requires_auth else "allowed"
            notes = "requires authentication" if source.policy.requires_auth else None
            self._conn.execute(
                """
                INSERT INTO sources (source_id, domain, platform, authority, policy_status,
                                     policy_notes, crawl_delay_seconds, priority, enabled)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(source_id) DO UPDATE SET
                    domain = excluded.domain,
                    platform = excluded.platform,
                    authority = excluded.authority,
                    policy_status = excluded.policy_status,
                    policy_notes = excluded.policy_notes,
                    crawl_delay_seconds = excluded.crawl_delay_seconds,
                    priority = excluded.priority,
                    enabled = excluded.enabled
                """,
                (
                    source.source_id,
                    source.domain,
                    source.platform,
                    source.authority,
                    policy_status,
                    notes,
                    source.delay_seconds,
                    source.priority,
                    int(source.enabled),
                ),
            )
            count += 1
        self._conn.commit()
        return count

    def seed_coverage(self, items: Sequence[CoverageItem]) -> int:
        if len(items) != 24:
            raise ValueError("exactly 24 coverage items are required")
        for item in items:
            self._conn.execute(
                """
                INSERT INTO coverage_items (item_id, category, name, keywords, required)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(item_id) DO UPDATE SET
                    category = excluded.category,
                    name = excluded.name,
                    keywords = excluded.keywords,
                    required = excluded.required
                """,
                (
                    item.item_id,
                    item.category,
                    item.name,
                    ";".join(item.keywords),
                    int(item.required),
                ),
            )
        self._conn.commit()
        return len(items)

    def coverage_items(self) -> tuple[CoverageItem, ...]:
        rows = self._conn.execute(
            "SELECT item_id, category, name, keywords, required "
            "FROM coverage_items ORDER BY item_id"
        ).fetchall()
        return tuple(
            CoverageItem(
                item_id=row["item_id"],
                category=row["category"],
                name=row["name"],
                keywords=tuple(str(row["keywords"]).split(";")) if row["keywords"] else (),
                required=bool(row["required"]),
            )
            for row in rows
        )

    # ---------------------------------------------------------------- campaigns

    def create_campaign(
        self,
        *,
        campaign_id: str,
        config_hash: str,
        tool_version: str,
        git_commit: str | None = None,
    ) -> bool:
        try:
            self._conn.execute(
                """
                INSERT INTO campaigns (campaign_id, status, started_at, config_hash, git_commit,
                                       tool_version)
                VALUES (?, 'planned', ?, ?, ?, ?)
                """,
                (campaign_id, utcnow(), config_hash, git_commit, tool_version),
            )
            self._conn.commit()
            return True
        except sqlite3.IntegrityError:
            return False

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        row = self._conn.execute(
            "SELECT * FROM campaigns WHERE campaign_id = ?", (campaign_id,)
        ).fetchone()
        if row is None:
            return None
        return Campaign(
            campaign_id=row["campaign_id"],
            status=row["status"],
            started_at=row["started_at"],
            finished_at=row["finished_at"],
            config_hash=row["config_hash"],
            git_commit=row["git_commit"],
            tool_version=row["tool_version"],
            bytes_stored=row["bytes_stored"],
            artifact_count=row["artifact_count"],
            notes=row["notes"],
        )

    def set_campaign_status(self, campaign_id: str, status: str) -> None:
        terminal = status in {"completed", "aborted", "failed"}
        self._conn.execute(
            "UPDATE campaigns SET status = ?, finished_at = ? WHERE campaign_id = ?",
            (status, utcnow() if terminal else None, campaign_id),
        )
        self._conn.commit()

    def refresh_campaign_counters(self, campaign_id: str) -> None:
        linked = self._conn.execute(
            "SELECT COUNT(*) AS item_count FROM campaign_artifacts WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()["item_count"]
        stored = self._conn.execute(
            "SELECT COALESCE(SUM(byte_size), 0) AS total_bytes FROM artifacts "
            "WHERE campaign_id = ?",
            (campaign_id,),
        ).fetchone()["total_bytes"]
        self._conn.execute(
            "UPDATE campaigns SET artifact_count = ?, bytes_stored = ? WHERE campaign_id = ?",
            (linked, stored, campaign_id),
        )
        self._conn.commit()

    # ------------------------------------------------------------------ targets

    def add_target(
        self,
        *,
        campaign_id: str,
        source_id: str,
        url_original: str,
        url_canonical: str,
        category: str,
        coverage_item_id: str | None = None,
        depth: int = 0,
        priority: int = 2,
        discovered_from: str | None = None,
        state: str = TargetState.DISCOVERED,
    ) -> tuple[Target, bool]:
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO acquisition_targets
                (campaign_id, source_id, url_original, url_canonical, category,
                 coverage_item_id, depth, priority, state, discovered_from, first_seen_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                source_id,
                url_original,
                url_canonical,
                category,
                coverage_item_id,
                depth,
                priority,
                state,
                discovered_from,
                utcnow(),
            ),
        )
        created = cursor.rowcount == 1
        self._conn.commit()
        row = self._conn.execute(
            "SELECT * FROM acquisition_targets WHERE campaign_id = ? AND url_canonical = ?",
            (campaign_id, url_canonical),
        ).fetchone()
        return self._target_from_row(row), created

    @staticmethod
    def _target_from_row(row: sqlite3.Row) -> Target:
        return Target(
            target_id=row["target_id"],
            campaign_id=row["campaign_id"],
            source_id=row["source_id"],
            url_original=row["url_original"],
            url_canonical=row["url_canonical"],
            category=row["category"],
            coverage_item_id=row["coverage_item_id"],
            depth=row["depth"],
            priority=row["priority"],
            state=row["state"],
            discovered_from=row["discovered_from"],
            attempts=row["attempts"],
            first_seen_at=row["first_seen_at"],
            last_attempt_at=row["last_attempt_at"],
        )

    def update_target_state(
        self,
        target_id: int,
        state: str,
        *,
        increment_attempts: bool = False,
    ) -> None:
        if increment_attempts:
            self._conn.execute(
                """
                UPDATE acquisition_targets
                SET state = ?, attempts = attempts + 1, last_attempt_at = ?
                WHERE target_id = ?
                """,
                (state, utcnow(), target_id),
            )
        else:
            self._conn.execute(
                "UPDATE acquisition_targets SET state = ? WHERE target_id = ?",
                (state, target_id),
            )
        self._conn.commit()

    def targets(
        self,
        campaign_id: str,
        *,
        states: Sequence[str] | None = None,
    ) -> tuple[Target, ...]:
        query = "SELECT * FROM acquisition_targets WHERE campaign_id = ?"
        params: list[Any] = [campaign_id]
        if states:
            placeholders = ",".join("?" for _ in states)
            query += f" AND state IN ({placeholders})"
            params.extend(states)
        query += " ORDER BY priority ASC, target_id ASC"
        rows = self._conn.execute(query, params).fetchall()
        return tuple(self._target_from_row(row) for row in rows)

    def pending_targets(self, campaign_id: str) -> tuple[Target, ...]:
        return self.targets(
            campaign_id,
            states=[
                TargetState.DISCOVERED,
                TargetState.ALLOWED,
                TargetState.FAILED,
                TargetState.DEFERRED,
            ],
        )

    # ---------------------------------------------------------------- artifacts

    def find_artifact_by_hash(self, content_hash: str) -> Artifact | None:
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE content_hash = ?", (content_hash,)
        ).fetchone()
        return self._artifact_from_row(row) if row else None

    def get_artifact(self, artifact_id: int) -> Artifact | None:
        row = self._conn.execute(
            "SELECT * FROM artifacts WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        return self._artifact_from_row(row) if row else None

    def add_artifact(
        self,
        *,
        content_hash: str,
        text_hash: str | None,
        media_type: str,
        byte_size: int,
        storage_path: str,
        retrieved_at: str,
        http_status: int,
        source_id: str,
        campaign_id: str,
        authority: str,
        language: str,
        language_method: str,
        title: str | None,
        published_at: str | None,
        version: int,
        url_original: str,
        url_canonical: str,
        category: str,
    ) -> tuple[Artifact, bool]:
        cursor = self._conn.execute(
            """
            INSERT OR IGNORE INTO artifacts
                (content_hash, text_hash, media_type, byte_size, storage_path, retrieved_at,
                 http_status, source_id, campaign_id, authority, language, language_method,
                 title, published_at, version, url_original, url_canonical, category)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                content_hash,
                text_hash,
                media_type,
                byte_size,
                storage_path,
                retrieved_at,
                http_status,
                source_id,
                campaign_id,
                authority,
                language,
                language_method,
                title,
                published_at,
                version,
                url_original,
                url_canonical,
                category,
            ),
        )
        self._conn.commit()
        if cursor.rowcount == 1:
            artifact = self.get_artifact(int(cursor.lastrowid))
            assert artifact is not None
            return artifact, True
        existing = self.find_artifact_by_hash(content_hash)
        assert existing is not None
        return existing, False

    def _artifact_from_row(self, row: sqlite3.Row) -> Artifact:
        evidence = self._conn.execute(
            "SELECT item_id FROM coverage_evidence WHERE artifact_id = ? ORDER BY item_id",
            (row["artifact_id"],),
        ).fetchall()
        return Artifact(
            artifact_id=row["artifact_id"],
            content_hash=row["content_hash"],
            text_hash=row["text_hash"],
            media_type=row["media_type"],
            byte_size=row["byte_size"],
            storage_path=row["storage_path"],
            retrieved_at=row["retrieved_at"],
            http_status=row["http_status"],
            source_id=row["source_id"],
            campaign_id=row["campaign_id"],
            authority=row["authority"],
            language=row["language"],
            language_method=row["language_method"],
            title=row["title"],
            published_at=row["published_at"],
            version=row["version"],
            url_original=row["url_original"],
            url_canonical=row["url_canonical"],
            category=row["category"],
            coverage_item_ids=tuple(item["item_id"] for item in evidence),
            retracted_at=row["retracted_at"],
            retraction_reason=row["retraction_reason"],
        )

    def list_artifacts(
        self,
        *,
        campaign_id: str | None = None,
        category: str | None = None,
        source_id: str | None = None,
        language: str | None = None,
        coverage_item_id: str | None = None,
        include_retracted: bool = False,
        active_only: bool = False,
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[tuple[Artifact, ...], int]:
        clauses: list[str] = []
        params: list[Any] = []
        joins: list[str] = []
        if campaign_id:
            joins.append(
                "JOIN campaign_artifacts ca ON ca.artifact_id = a.artifact_id "
                "AND ca.campaign_id = ?"
            )
            params.append(campaign_id)
        if active_only:
            joins.append("JOIN v_active_artifacts va ON va.artifact_id = a.artifact_id")
        if category:
            clauses.append("a.category = ?")
            params.append(category)
        if source_id:
            clauses.append("a.source_id = ?")
            params.append(source_id)
        if language:
            clauses.append("a.language = ?")
            params.append(language)
        if coverage_item_id:
            clauses.append(
                "EXISTS (SELECT 1 FROM coverage_evidence e WHERE e.artifact_id = a.artifact_id "
                "AND e.item_id = ?)"
            )
            params.append(coverage_item_id)
        if not include_retracted:
            clauses.append("a.retracted_at IS NULL")
        join = " ".join(joins)
        where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
        total = self._conn.execute(
            f"SELECT COUNT(DISTINCT a.artifact_id) AS n FROM artifacts a {join} {where}",
            params,
        ).fetchone()["n"]
        rows = self._conn.execute(
            f"SELECT DISTINCT a.* FROM artifacts a {join} {where} "
            "ORDER BY a.artifact_id LIMIT ? OFFSET ?",
            [*params, limit, offset],
        ).fetchall()
        return tuple(self._artifact_from_row(row) for row in rows), int(total)

    def link_artifact(
        self,
        *,
        campaign_id: str,
        artifact_id: int,
        target_id: int,
        captured_as: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO campaign_artifacts
                (campaign_id, artifact_id, target_id, captured_as, observed_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (campaign_id, artifact_id, target_id, captured_as, utcnow()),
        )
        self._conn.commit()

    def used_bytes(self) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(SUM(byte_size), 0) AS total FROM artifacts"
        ).fetchone()
        return int(row["total"])

    # -------------------------------------------------------------- url versions

    def next_version(self, url_canonical: str) -> int:
        row = self._conn.execute(
            "SELECT COALESCE(MAX(version), 0) + 1 AS next FROM url_versions "
            "WHERE url_canonical = ?",
            (url_canonical,),
        ).fetchone()
        return int(row["next"])

    def latest_version(self, url_canonical: str) -> tuple[int, str | None] | None:
        row = self._conn.execute(
            """
            SELECT v.version, a.text_hash FROM url_versions v
            JOIN artifacts a ON a.artifact_id = v.artifact_id
            WHERE v.url_canonical = ?
            ORDER BY v.version DESC LIMIT 1
            """,
            (url_canonical,),
        ).fetchone()
        return (int(row["version"]), row["text_hash"]) if row else None

    def latest_version_hash(self, url_canonical: str) -> str | None:
        latest = self.latest_version(url_canonical)
        return latest[1] if latest else None

    def add_url_version(
        self,
        *,
        url_canonical: str,
        artifact_id: int,
        version: int,
        change_reason: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO url_versions
                (url_canonical, artifact_id, version, observed_at, change_reason)
            VALUES (?, ?, ?, ?, ?)
            """,
            (url_canonical, artifact_id, version, utcnow(), change_reason),
        )
        self._conn.commit()

    # ----------------------------------------------------------------- coverage

    def add_coverage_evidence(
        self,
        *,
        item_id: str,
        artifact_id: int,
        confidence: str,
        note: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO coverage_evidence (item_id, artifact_id, confidence, note)
            VALUES (?, ?, ?, ?)
            """,
            (item_id, artifact_id, confidence, note),
        )
        self._conn.commit()

    def coverage_matrix(
        self, campaign_id: str, *, active_only: bool = False
    ) -> tuple[CoverageRow, ...]:
        items = self.coverage_items()
        rows: list[CoverageRow] = []
        active_join = (
            "JOIN v_active_artifacts va ON va.artifact_id = e.artifact_id" if active_only else ""
        )
        for item in items:
            evidence = self._conn.execute(
                f"""
                SELECT e.artifact_id, e.confidence
                FROM coverage_evidence e
                JOIN artifacts a ON a.artifact_id = e.artifact_id
                JOIN campaign_artifacts ca
                    ON ca.artifact_id = e.artifact_id AND ca.campaign_id = ?
                {active_join}
                WHERE e.item_id = ? AND a.retracted_at IS NULL
                ORDER BY e.artifact_id
                """,
                (campaign_id, item.item_id),
            ).fetchall()
            direct = [row["artifact_id"] for row in evidence if row["confidence"] == "direct"]
            supporting = [
                row["artifact_id"] for row in evidence if row["confidence"] == "supporting"
            ]
            refs = tuple(sorted(set(direct + supporting)))
            if direct:
                status = CoverageStatus.COVERED
            elif supporting:
                status = CoverageStatus.PARTIAL
            else:
                status = CoverageStatus.MISSING
            rows.append(
                CoverageRow(
                    item_id=item.item_id,
                    category=item.category,
                    name=item.name,
                    status=status.value,
                    evidence_count=len(refs),
                    artifact_refs=refs,
                    gap_reason=None
                    if status is not CoverageStatus.MISSING
                    else self._gap_reason(campaign_id),
                )
            )
        return tuple(rows)

    def _gap_reason(self, campaign_id: str) -> str:
        row = self._conn.execute(
            """
            SELECT reason_code, COUNT(*) AS n FROM outcomes
            WHERE campaign_id = ? GROUP BY reason_code ORDER BY n DESC, reason_code LIMIT 1
            """,
            (campaign_id,),
        ).fetchone()
        if row is None:
            return "No se encontró contenido público que cubra este elemento en la campaña."
        return (
            f"Sin evidencia directa; la causa más frecuente registrada fue '{row['reason_code']}'."
        )

    # ------------------------------------------------------------------ outcomes

    def add_outcome(
        self,
        *,
        campaign_id: str,
        source_id: str,
        url_canonical: str,
        outcome_type: str,
        reason_code: str,
        detail: str | None = None,
        attempts: int = 0,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO outcomes
                (campaign_id, source_id, url_canonical, outcome_type, reason_code,
                 detail, attempts, occurred_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                campaign_id,
                source_id,
                url_canonical,
                outcome_type,
                reason_code,
                detail,
                attempts,
                utcnow(),
            ),
        )
        self._conn.commit()

    def outcomes_by_reason(self, campaign_id: str) -> dict[str, int]:
        rows = self._conn.execute(
            """
            SELECT reason_code, COUNT(*) AS n FROM outcomes
            WHERE campaign_id = ? GROUP BY reason_code
            """,
            (campaign_id,),
        ).fetchall()
        return {row["reason_code"]: int(row["n"]) for row in rows}

    def add_policy_check(
        self,
        *,
        campaign_id: str,
        source_id: str,
        decision: str,
        reason: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO policy_checks (campaign_id, source_id, decision, reason, checked_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (campaign_id, source_id, decision, reason, utcnow()),
        )
        self._conn.commit()

    # ------------------------------------------------------------------ summary

    def target_counts(self, campaign_id: str) -> dict[str, int]:
        rows = self._conn.execute(
            """
            SELECT state, COUNT(*) AS n FROM acquisition_targets
            WHERE campaign_id = ? GROUP BY state
            """,
            (campaign_id,),
        ).fetchall()
        return {row["state"]: int(row["n"]) for row in rows}

    def policy_checks(self, campaign_id: str) -> tuple[dict[str, Any], ...]:
        rows = self._conn.execute(
            "SELECT * FROM policy_checks WHERE campaign_id = ? ORDER BY policy_check_id",
            (campaign_id,),
        ).fetchall()
        return tuple(dict(row) for row in rows)

    def export_jsonl(
        self, campaign_id: str, destination: Path, *, active_only: bool = False
    ) -> int:
        artifacts, _ = self.list_artifacts(
            campaign_id=campaign_id,
            include_retracted=True,
            active_only=active_only,
            limit=1_000_000,
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="\n") as handle:
            for artifact in artifacts:
                handle.write(json.dumps(_artifact_payload(artifact), ensure_ascii=False) + "\n")
        return len(artifacts)

    # ------------------------------------------------------------------ curation

    def create_curation_run(
        self,
        *,
        run_id: str,
        config_hash: str,
        tool_version: str,
        scope_campaign: str | None = None,
        bytes_before: int = 0,
        git_commit: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            INSERT INTO curation_runs
                (run_id, status, started_at, config_hash, git_commit, tool_version,
                 scope_campaign, bytes_before)
            VALUES (?, 'planned', ?, ?, ?, ?, ?, ?)
            """,
            (run_id, utcnow(), config_hash, git_commit, tool_version, scope_campaign, bytes_before),
        )
        self._conn.commit()

    def get_curation_run(self, run_id: str) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM curation_runs WHERE run_id = ?", (run_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_curation_run(self, run_id: str, **fields: Any) -> None:
        allowed = {
            "status",
            "finished_at",
            "artifacts_evaluated",
            "kept",
            "removed",
            "review",
            "bytes_before",
            "bytes_quarantined",
            "bytes_freed",
            "approved_by",
            "approved_at",
            "report_path",
            "notes",
        }
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        self._conn.execute(
            f"UPDATE curation_runs SET {assignments} WHERE run_id = ?",
            [*updates.values(), run_id],
        )
        self._conn.commit()

    def approve_curation_run(self, run_id: str, reviewer: str) -> None:
        self._conn.execute(
            "UPDATE curation_runs SET status = 'approved', approved_by = ?, approved_at = ? "
            "WHERE run_id = ?",
            (reviewer, utcnow(), run_id),
        )
        self._conn.commit()

    def pending_review_count(self, run_id: str) -> int:
        row = self._conn.execute(
            "SELECT COUNT(*) AS n FROM review_items WHERE run_id = ? AND status = 'pending'",
            (run_id,),
        ).fetchone()
        return int(row["n"])

    def upsert_evaluation(
        self,
        *,
        artifact_id: int,
        run_id: str,
        decision: str,
        level: str,
        score: int,
        explanation: str,
        content_hash: str,
        config_hash: str,
        method: str = "rule_based",
    ) -> bool:
        existing = self._conn.execute(
            "SELECT manual_override FROM relevance_evaluations WHERE artifact_id = ?",
            (artifact_id,),
        ).fetchone()
        if existing and existing["manual_override"]:
            return False
        self._conn.execute(
            """
            INSERT INTO relevance_evaluations
                (artifact_id, run_id, decision, level, score, method, explanation,
                 content_hash, config_hash, manual_override, evaluated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?)
            ON CONFLICT(artifact_id) DO UPDATE SET
                run_id = excluded.run_id,
                decision = excluded.decision,
                level = excluded.level,
                score = excluded.score,
                method = excluded.method,
                explanation = excluded.explanation,
                content_hash = excluded.content_hash,
                config_hash = excluded.config_hash,
                evaluated_at = excluded.evaluated_at
            """,
            (
                artifact_id,
                run_id,
                decision,
                level,
                score,
                method,
                explanation,
                content_hash,
                config_hash,
                utcnow(),
            ),
        )
        self._conn.commit()
        return True

    def replace_evidence(self, artifact_id: int, evidence: list[dict[str, Any]]) -> None:
        self._conn.execute("DELETE FROM relevance_evidence WHERE artifact_id = ?", (artifact_id,))
        if evidence:
            self._conn.executemany(
                """
                INSERT OR IGNORE INTO relevance_evidence
                    (artifact_id, term, location, snippet, weight, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                [
                    (
                        artifact_id,
                        str(item["term"])[:200],
                        str(item["location"]),
                        str(item["snippet"])[:500],
                        int(item["weight"]),
                        utcnow(),
                    )
                    for item in evidence
                ],
            )
        self._conn.commit()

    def sync_review_item(
        self,
        *,
        artifact_id: int,
        run_id: str,
        decision: str,
        reason: str,
        snippet: str,
        score: int,
    ) -> None:
        if decision == "review":
            self._conn.execute(
                """
                INSERT INTO review_items
                    (artifact_id, run_id, reason, snippet, score, status)
                VALUES (?, ?, ?, ?, ?, 'pending')
                ON CONFLICT(artifact_id) DO UPDATE SET
                    run_id = excluded.run_id,
                    reason = excluded.reason,
                    snippet = excluded.snippet,
                    score = excluded.score
                WHERE review_items.status = 'pending'
                """,
                (artifact_id, run_id, reason[:500], snippet[:500], score),
            )
        else:
            self._conn.execute(
                "DELETE FROM review_items WHERE artifact_id = ? AND status = 'pending'",
                (artifact_id,),
            )
        self._conn.commit()

    def list_review_items(
        self,
        run_id: str,
        *,
        limit: int = 50,
        offset: int = 0,
        status: str = "pending",
    ) -> tuple[list[dict[str, Any]], int]:
        total = self._conn.execute(
            "SELECT COUNT(*) AS n FROM review_items WHERE run_id = ? AND status = ?",
            (run_id, status),
        ).fetchone()["n"]
        rows = self._conn.execute(
            """
            SELECT r.*, a.url_canonical, a.title, a.source_id
            FROM review_items r JOIN artifacts a ON a.artifact_id = r.artifact_id
            WHERE r.run_id = ? AND r.status = ?
            ORDER BY r.artifact_id LIMIT ? OFFSET ?
            """,
            (run_id, status, limit, offset),
        ).fetchall()
        return [dict(row) for row in rows], int(total)

    def decide_review(
        self,
        *,
        artifact_id: int,
        decision: str,
        reviewer: str,
        note: str | None,
    ) -> bool:
        row = self._conn.execute(
            "SELECT run_id FROM review_items WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        if row is None:
            return False
        self._conn.execute(
            """
            UPDATE review_items SET status = 'decided', decision = ?, reviewer = ?,
                   decided_at = ?, note = ?
            WHERE artifact_id = ?
            """,
            (decision, reviewer, utcnow(), note, artifact_id),
        )
        self._conn.execute(
            """
            UPDATE relevance_evaluations
            SET decision = ?, method = 'manual', manual_override = 1, reviewer = ?,
                reviewed_at = ?, explanation = ?
            WHERE artifact_id = ?
            """,
            (
                decision,
                reviewer,
                utcnow(),
                note or f"Revisión manual: {decision}",
                artifact_id,
            ),
        )
        self._conn.commit()
        return True

    def curation_counts(self, run_id: str) -> dict[str, int]:
        rows = self._conn.execute(
            "SELECT decision, COUNT(*) AS n FROM relevance_evaluations "
            "WHERE run_id = ? GROUP BY decision",
            (run_id,),
        ).fetchall()
        return {row["decision"]: int(row["n"]) for row in rows}

    def get_evaluation(self, artifact_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM relevance_evaluations WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        return dict(row) if row else None

    def evidence_for(self, artifact_id: int) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            "SELECT term, location, snippet, weight FROM relevance_evidence "
            "WHERE artifact_id = ? ORDER BY evidence_id",
            (artifact_id,),
        ).fetchall()
        return [dict(row) for row in rows]

    def set_manual_decision(
        self,
        *,
        artifact_id: int,
        decision: str,
        reviewer: str,
        note: str | None = None,
    ) -> None:
        self._conn.execute(
            """
            UPDATE relevance_evaluations
            SET decision = ?, method = 'manual', manual_override = 1, reviewer = ?,
                reviewed_at = ?, explanation = ?
            WHERE artifact_id = ?
            """,
            (
                decision,
                reviewer,
                utcnow(),
                note or f"Decisión manual: {decision}",
                artifact_id,
            ),
        )
        self._conn.commit()

    def curation_by_source(self, run_id: str) -> list[dict[str, Any]]:
        rows = self._conn.execute(
            """
            SELECT a.source_id, e.decision, COUNT(*) AS n
            FROM relevance_evaluations e JOIN artifacts a ON a.artifact_id = e.artifact_id
            WHERE e.run_id = ? GROUP BY a.source_id, e.decision
            """,
            (run_id,),
        ).fetchall()
        aggregate: dict[str, dict[str, Any]] = {}
        for row in rows:
            entry = aggregate.setdefault(
                row["source_id"],
                {"source_id": row["source_id"], "total": 0, "kept": 0, "removed": 0, "review": 0},
            )
            count = int(row["n"])
            entry["total"] += count
            key = {"keep": "kept", "remove": "removed", "review": "review"}[row["decision"]]
            entry[key] += count
        return sorted(aggregate.values(), key=lambda item: item["source_id"])

    def evaluations(
        self, run_id: str, *, decision: str | None = None, limit: int = 1_000_000
    ) -> tuple[list[dict[str, Any]], int]:
        query = "SELECT * FROM relevance_evaluations WHERE run_id = ?"
        params: list[Any] = [run_id]
        if decision:
            query += " AND decision = ?"
            params.append(decision)
        total = self._conn.execute(f"SELECT COUNT(*) AS n FROM ({query})", params).fetchone()["n"]
        query += " ORDER BY artifact_id LIMIT ?"
        params.append(limit)
        rows = self._conn.execute(query, params).fetchall()
        return [dict(row) for row in rows], int(total)

    def add_audit_record(
        self,
        *,
        run_id: str,
        artifact_id: int,
        url_canonical: str,
        content_hash: str,
        byte_size: int,
        media_type: str,
        source_id: str,
        reason: str,
        score: int,
        evidence_json: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO curation_audit
                (run_id, artifact_id, url_canonical, content_hash, byte_size, media_type,
                 source_id, decision, reason, score, evidence_json, decided_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'remove', ?, ?, ?, ?)
            """,
            (
                run_id,
                artifact_id,
                url_canonical,
                content_hash,
                byte_size,
                media_type,
                source_id,
                reason,
                score,
                evidence_json,
                utcnow(),
            ),
        )
        self._conn.commit()

    def get_audit_record(self, artifact_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM curation_audit WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        return dict(row) if row else None

    def mark_audit_quarantined(self, artifact_id: int) -> None:
        self._conn.execute(
            "UPDATE curation_audit SET quarantined_at = ? WHERE artifact_id = ?",
            (utcnow(), artifact_id),
        )
        self._conn.commit()

    def mark_audit_purged(self, artifact_id: int) -> None:
        self._conn.execute(
            "UPDATE curation_audit SET purged_at = ? WHERE artifact_id = ?",
            (utcnow(), artifact_id),
        )
        self._conn.commit()

    def add_quarantine_entry(
        self,
        *,
        artifact_id: int,
        run_id: str,
        original_path: str,
        quarantine_path: str,
        byte_size: int,
        expires_at: str,
    ) -> None:
        self._conn.execute(
            """
            INSERT OR IGNORE INTO quarantine_entries
                (artifact_id, run_id, original_path, quarantine_path, byte_size,
                 moved_at, expires_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, 'quarantined')
            """,
            (
                artifact_id,
                run_id,
                original_path,
                quarantine_path,
                byte_size,
                utcnow(),
                expires_at,
            ),
        )
        self._conn.commit()

    def get_quarantine_entry(self, artifact_id: int) -> dict[str, Any] | None:
        row = self._conn.execute(
            "SELECT * FROM quarantine_entries WHERE artifact_id = ?", (artifact_id,)
        ).fetchone()
        return dict(row) if row else None

    def update_quarantine_entry(self, artifact_id: int, **fields: Any) -> None:
        allowed = {"status", "restored_at", "purged_at"}
        updates = {key: value for key, value in fields.items() if key in allowed}
        if not updates:
            return
        assignments = ", ".join(f"{key} = ?" for key in updates)
        self._conn.execute(
            f"UPDATE quarantine_entries SET {assignments} WHERE artifact_id = ?",
            [*updates.values(), artifact_id],
        )
        self._conn.commit()

    def list_quarantine_entries(
        self, run_id: str, *, status: str | None = None
    ) -> list[dict[str, Any]]:
        query = "SELECT * FROM quarantine_entries WHERE run_id = ?"
        params: list[Any] = [run_id]
        if status:
            query += " AND status = ?"
            params.append(status)
        query += " ORDER BY artifact_id"
        return [dict(row) for row in self._conn.execute(query, params).fetchall()]

    def refresh_manifests(
        self,
        *,
        active_only: bool = True,
    ) -> list[Path]:
        """Regenerate manifests for every campaign using the current corpus state."""
        rows = self._conn.execute(
            "SELECT campaign_id FROM campaigns ORDER BY campaign_id"
        ).fetchall()
        written: list[Path] = []
        for row in rows:
            campaign_id = row["campaign_id"]
            destination = self.path.parent.parent / "manifests" / f"{campaign_id}.jsonl"
            self.export_jsonl(campaign_id, destination, active_only=active_only)
            written.append(destination)
        return written


def _artifact_payload(artifact: Artifact) -> dict[str, Any]:
    return {
        "schema_version": "1.0",
        "artifact_id": artifact.artifact_id,
        "campaign_id": artifact.campaign_id,
        "source_id": artifact.source_id,
        "authority": artifact.authority,
        "url_original": artifact.url_original,
        "url_canonical": artifact.url_canonical,
        "content_hash": artifact.content_hash,
        "text_hash": artifact.text_hash,
        "media_type": artifact.media_type,
        "byte_size": artifact.byte_size,
        "storage_path": artifact.storage_path,
        "retrieved_at": artifact.retrieved_at,
        "http_status": artifact.http_status,
        "language": artifact.language,
        "language_method": artifact.language_method,
        "title": artifact.title,
        "published_at": artifact.published_at,
        "version": artifact.version,
        "coverage_item_ids": list(artifact.coverage_item_ids),
        "retracted_at": artifact.retracted_at,
        "retraction_reason": artifact.retraction_reason,
    }


def artifact_payload(artifact: Artifact) -> dict[str, Any]:
    """Public serializer used by CLI and manifests."""
    return _artifact_payload(artifact)


def is_terminal(state: str) -> bool:
    return state in {
        item.value for item in (TargetState.STORED, TargetState.DEDUPED, TargetState.EXCLUDED)
    }


def valid_language(value: str) -> bool:
    return value in {item.value for item in Language}
