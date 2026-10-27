"""Domain types shared by the bronze pipeline."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum


class CampaignStatus(StrEnum):
    PLANNED = "planned"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    ABORTED = "aborted"
    FAILED = "failed"


class TargetState(StrEnum):
    DISCOVERED = "discovered"
    ALLOWED = "allowed"
    EXCLUDED = "excluded"
    FETCHING = "fetching"
    STORED = "stored"
    DEDUPED = "deduped"
    FAILED = "failed"
    DEFERRED = "deferred"


TERMINAL_TARGET_STATES = frozenset({TargetState.STORED, TargetState.DEDUPED, TargetState.EXCLUDED})


class OutcomeType(StrEnum):
    EXCLUDED = "excluded"
    FAILED = "failed"
    DEFERRED = "deferred"


class ReasonCode(StrEnum):
    ROBOTS_DISALLOWED = "robots_disallowed"
    TOS_RESTRICTED = "tos_restricted"
    REQUIRES_AUTH = "requires_auth"
    OUT_OF_SCOPE = "out_of_scope"
    MANUAL_EXCLUSION = "manual_exclusion"
    BLOCKED = "blocked"
    RATE_LIMITED = "rate_limited"
    TIMEOUT = "timeout"
    HTTP_ERROR = "http_error"
    PARSE_ERROR = "parse_error"
    STORAGE_CAP = "storage_cap"
    EMPTY_CONTENT = "empty_content"


class Category(StrEnum):
    IDENTITY = "identity"
    OFFER = "offer"
    DIGITAL_PRESENCE = "digital_presence"
    HARD_DATA = "hard_data"


class Authority(StrEnum):
    FIRST_PARTY = "first_party"
    THIRD_PARTY = "third_party"
    OPEN_DATA = "open_data"


class Language(StrEnum):
    ES = "es"
    EN = "en"
    UND = "und"


class LanguageMethod(StrEnum):
    HTML_LANG = "html_lang"
    HEURISTIC = "heuristic"
    UNKNOWN = "unknown"


class CoverageStatus(StrEnum):
    COVERED = "covered"
    PARTIAL = "partial"
    MISSING = "missing"


class Confidence(StrEnum):
    DIRECT = "direct"
    SUPPORTING = "supporting"


@dataclass(frozen=True, slots=True)
class Campaign:
    campaign_id: str
    status: str
    started_at: str
    finished_at: str | None
    config_hash: str
    git_commit: str | None
    tool_version: str
    bytes_stored: int
    artifact_count: int
    notes: str | None


@dataclass(frozen=True, slots=True)
class Source:
    source_id: str
    domain: str
    platform: str
    authority: str
    policy_status: str
    policy_notes: str | None
    crawl_delay_seconds: float
    priority: int
    enabled: bool


@dataclass(frozen=True, slots=True)
class Target:
    target_id: int
    campaign_id: str
    source_id: str
    url_original: str
    url_canonical: str
    category: str
    coverage_item_id: str | None
    depth: int
    priority: int
    state: str
    discovered_from: str | None
    attempts: int
    first_seen_at: str
    last_attempt_at: str | None


@dataclass(frozen=True, slots=True)
class Artifact:
    artifact_id: int
    content_hash: str
    text_hash: str | None
    media_type: str
    byte_size: int
    storage_path: str
    retrieved_at: str
    http_status: int
    source_id: str
    campaign_id: str
    authority: str
    language: str
    language_method: str
    title: str | None
    published_at: str | None
    version: int
    url_original: str
    url_canonical: str
    category: str
    coverage_item_ids: tuple[str, ...]
    retracted_at: str | None
    retraction_reason: str | None


@dataclass(frozen=True, slots=True)
class CoverageItem:
    item_id: str
    category: str
    name: str
    keywords: tuple[str, ...]
    required: bool


@dataclass(frozen=True, slots=True)
class Outcome:
    outcome_id: int
    campaign_id: str
    source_id: str
    url_canonical: str
    outcome_type: str
    reason_code: str
    detail: str | None
    attempts: int
    occurred_at: str


@dataclass(frozen=True, slots=True)
class CoverageRow:
    item_id: str
    category: str
    name: str
    status: str
    evidence_count: int
    artifact_refs: tuple[int, ...]
    gap_reason: str | None
