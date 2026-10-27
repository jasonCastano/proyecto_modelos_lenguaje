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
        limit: int = 100,
        offset: int = 0,
    ) -> tuple[tuple[Artifact, ...], int]:
        clauses: list[str] = []
        params: list[Any] = []
        join = ""
        if campaign_id:
            join = (
                "JOIN campaign_artifacts ca ON ca.artifact_id = a.artifact_id "
                "AND ca.campaign_id = ?"
            )
            params.append(campaign_id)
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

    def coverage_matrix(self, campaign_id: str) -> tuple[CoverageRow, ...]:
        items = self.coverage_items()
        rows: list[CoverageRow] = []
        for item in items:
            evidence = self._conn.execute(
                """
                SELECT e.artifact_id, e.confidence
                FROM coverage_evidence e
                JOIN artifacts a ON a.artifact_id = e.artifact_id
                JOIN campaign_artifacts ca
                    ON ca.artifact_id = e.artifact_id AND ca.campaign_id = ?
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

    def export_jsonl(self, campaign_id: str, destination: Path) -> int:
        artifacts, _ = self.list_artifacts(
            campaign_id=campaign_id, include_retracted=True, limit=1_000_000
        )
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="\n") as handle:
            for artifact in artifacts:
                handle.write(json.dumps(_artifact_payload(artifact), ensure_ascii=False) + "\n")
        return len(artifacts)


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
