# Data Model: Capa Bronce de Recolección Web

**Feature**: `001-bronze-web-scraping` | **Date**: 2026-10-27

The bronze layer combines an immutable raw store on the filesystem with a transactional SQLite catalog.
The catalog is the source of truth for metadata, state and provenance; raw bytes are the source of truth for
content. Every field traces back to functional requirements in [spec.md](./spec.md).

## Storage Layout

```text
data/bronze/
├── raw/<source_id>/<campaign_id>/<content_hash><ext>   # immutable raw bytes
├── manifests/<campaign_id>.jsonl                        # one JSON object per artifact
├── reports/<campaign_id>/campaign.json
├── reports/<campaign_id>/coverage.json
├── reports/<campaign_id>/summary.md
└── _meta/
    ├── bronze.sqlite3                                   # catalog (WAL mode)
    └── logs/<campaign_id>.jsonl                         # structured run log
```

- `content_hash` is the SHA-256 of the raw bytes, encoded as 64 lowercase hex characters.
- `ext` is derived from the detected media type (`.html`, `.pdf`, `.xml`, `.json`, `.txt`, `.vtt`), never from
  the URL alone.
- Total bytes under `data/bronze/` (raw + metadata + reports) MUST stay at or below 10,000,000,000.

## Entity Relationship Overview

```text
campaigns 1──N acquisition_targets N──1 sources
campaigns 1──N artifacts          N──1 sources
campaigns 1──N campaign_artifacts N──1 artifacts
artifacts 1──N url_versions
artifacts 1──N coverage_evidence N──1 coverage_items
campaigns 1──N outcomes
campaigns 1──N policy_checks      N──1 sources
```

## Table: `campaigns`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `campaign_id` | TEXT | PRIMARY KEY | Stable slug, e.g. `2026-10-baseline` |
| `status` | TEXT | NOT NULL, CHECK in `planned,running,paused,completed,aborted,failed` | Exactly one `running` campaign at a time |
| `started_at` | TEXT | NOT NULL | ISO 8601 UTC (`YYYY-MM-DDTHH:MM:SSZ`) |
| `finished_at` | TEXT | NULL | Required when status is terminal |
| `config_hash` | TEXT | NOT NULL | SHA-256 of the effective TOML configuration |
| `git_commit` | TEXT | NULL | Commit of the code that ran the campaign |
| `tool_version` | TEXT | NOT NULL | Package version |
| `bytes_stored` | INTEGER | NOT NULL DEFAULT 0, CHECK >= 0 | Bytes attributed to the campaign |
| `artifact_count` | INTEGER | NOT NULL DEFAULT 0, CHECK >= 0 | Unique artifacts stored |
| `notes` | TEXT | NULL | Operator notes |

**State transitions**: `planned → running → completed`, `running → paused → running`, and any active state →
`aborted` or `failed`. Terminal states are immutable except for `notes`.

## Table: `sources`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `source_id` | TEXT | PRIMARY KEY | Slug: `official_site`, `youtube`, `facebook`, `secop`, … |
| `domain` | TEXT | NOT NULL | Registrable domain or platform host |
| `platform` | TEXT | NOT NULL | `website`, `youtube`, `facebook`, `instagram`, `x`, `job_board`, `open_data` |
| `authority` | TEXT | NOT NULL, CHECK in `first_party,third_party,open_data` | Drives FR-019 ranking |
| `policy_status` | TEXT | NOT NULL, CHECK in `allowed,restricted,excluded,unknown` | Last evaluated decision |
| `policy_notes` | TEXT | NULL | ToS/robots summary and justification |
| `crawl_delay_seconds` | REAL | NOT NULL DEFAULT 1.0, CHECK >= 0 | Effective delay between requests |
| `priority` | INTEGER | NOT NULL, CHECK BETWEEN 0 AND 3 | 0 = highest (official/identity) |
| `enabled` | INTEGER | NOT NULL DEFAULT 1, CHECK IN (0,1) | Manual kill switch |

## Table: `acquisition_targets`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `target_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `campaign_id` | TEXT | NOT NULL, FK → `campaigns` | |
| `source_id` | TEXT | NOT NULL, FK → `sources` | |
| `url_original` | TEXT | NOT NULL | Exactly as discovered |
| `url_canonical` | TEXT | NOT NULL | Normalized per FR-014 |
| `category` | TEXT | NOT NULL, CHECK in `identity,offer,digital_presence,hard_data` | |
| `coverage_item_id` | TEXT | NULL, FK → `coverage_items` | Optional direct mapping |
| `depth` | INTEGER | NOT NULL DEFAULT 0, CHECK BETWEEN 0 AND 3 | Discovery depth |
| `priority` | INTEGER | NOT NULL, CHECK BETWEEN 0 AND 3 | Inherited or overridden |
| `state` | TEXT | NOT NULL, CHECK in `discovered,allowed,excluded,fetching,stored,deduped,failed,deferred` | |
| `discovered_from` | TEXT | NULL | Parent URL |
| `attempts` | INTEGER | NOT NULL DEFAULT 0, CHECK >= 0 | Retry counter |
| `first_seen_at` | TEXT | NOT NULL | UTC |
| `last_attempt_at` | TEXT | NULL | UTC |

**Uniqueness**: `(campaign_id, url_canonical)`.

**State transitions**:
`discovered → allowed | excluded`; `allowed → fetching`; `fetching → stored | deduped | failed | deferred`;
`failed → fetching` (bounded retries); `deferred → fetching` (only in a later campaign with available space).
Terminal states: `stored`, `deduped`, `excluded`.

## Table: `artifacts`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `artifact_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `content_hash` | TEXT | UNIQUE NOT NULL, `^[a-f0-9]{64}$` | Dedup key (FR-011) |
| `text_hash` | TEXT | NULL, `^[a-f0-9]{64}$` | Normalized visible text; versioning key |
| `media_type` | TEXT | NOT NULL | From `Content-Type` + byte signature |
| `byte_size` | INTEGER | NOT NULL, CHECK > 0 | Raw size |
| `storage_path` | TEXT | UNIQUE NOT NULL | Relative to `data/bronze/` |
| `retrieved_at` | TEXT | NOT NULL | UTC |
| `http_status` | INTEGER | NOT NULL, CHECK BETWEEN 100 AND 599 | |
| `source_id` | TEXT | NOT NULL, FK → `sources` | |
| `campaign_id` | TEXT | NOT NULL, FK → `campaigns` | First campaign that captured it |
| `authority` | TEXT | NOT NULL, CHECK in `first_party,third_party,open_data` | |
| `language` | TEXT | NOT NULL, CHECK in `es,en,und` | FR-022 |
| `language_method` | TEXT | NOT NULL, CHECK in `html_lang,heuristic,unknown` | Reproducibility |
| `title` | TEXT | NULL | Extracted label, raw bytes untouched |
| `published_at` | TEXT | NULL | Source publication date when declared |
| `version` | INTEGER | NOT NULL DEFAULT 1, CHECK >= 1 | Version of the canonical URL |
| `url_original` | TEXT | NOT NULL | Exact URL that produced the artifact |
| `url_canonical` | TEXT | NOT NULL | Canonical form (FR-014) |
| `category` | TEXT | NOT NULL, CHECK in `identity,offer,digital_presence,hard_data` | First-capture category |
| `retracted_at` | TEXT | NULL | Takedown/retraction date |
| `retraction_reason` | TEXT | NULL | Required when `retracted_at` is set |

**Invariants**:
- `content_hash` unique: identical bytes are stored once.
- `storage_path` MUST resolve inside `data/bronze/raw/` (path traversal rejected).
- `SUM(byte_size)` across artifacts plus on-disk overhead MUST remain ≤ 10,000,000,000.

## Table: `url_versions`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `url_version_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `url_canonical` | TEXT | NOT NULL | |
| `artifact_id` | INTEGER | NOT NULL, FK → `artifacts` | |
| `version` | INTEGER | NOT NULL, CHECK >= 1 | Monotonic per URL |
| `observed_at` | TEXT | NOT NULL | UTC |
| `change_reason` | TEXT | NOT NULL, CHECK in `first_capture,text_changed,retracted` | FR-020 |

**Uniqueness**: `(url_canonical, version)`. A new row is appended only when `text_hash` changes or a retraction
is recorded; the previous version is never modified.

## Table: `campaign_artifacts`

Associates every observed artifact with each campaign that saw it, including content deduplicated from a
previous campaign. `artifacts.campaign_id` keeps the first capture; this table provides per-campaign visibility.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `campaign_id` | TEXT | NOT NULL, FK → `campaigns` | |
| `artifact_id` | INTEGER | NOT NULL, FK → `artifacts` | |
| `target_id` | INTEGER | NULL | Target that produced the capture |
| `captured_as` | TEXT | NOT NULL, CHECK in `stored,deduped` | Whether bytes were newly persisted |
| `observed_at` | TEXT | NOT NULL | UTC |

**Primary key**: `(campaign_id, artifact_id)`. It is insert-only; re-runs do not duplicate rows.

## Table: `coverage_items`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `item_id` | TEXT | PRIMARY KEY | `I-01` … `H-06` (24 rows, seeded) |
| `category` | TEXT | NOT NULL, CHECK in `identity,offer,digital_presence,hard_data` | |
| `name` | TEXT | NOT NULL | Human-readable requirement |
| `keywords` | TEXT | NOT NULL | Semicolon-separated matching hints |
| `required` | INTEGER | NOT NULL DEFAULT 1, CHECK IN (0,1) | All 24 are required |

Seeding MUST produce exactly 24 rows matching the checklist table in the specification; startup validation
fails if the count or IDs differ.

## Table: `coverage_evidence`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `coverage_evidence_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `item_id` | TEXT | NOT NULL, FK → `coverage_items` | |
| `artifact_id` | INTEGER | NOT NULL, FK → `artifacts` | |
| `confidence` | TEXT | NOT NULL, CHECK in `direct,supporting` | Evidence strength |
| `note` | TEXT | NULL | Why it supports the item |

**Uniqueness**: `(item_id, artifact_id)`.

## Table: `outcomes`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `outcome_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `campaign_id` | TEXT | NOT NULL, FK → `campaigns` | |
| `source_id` | TEXT | NOT NULL, FK → `sources` | |
| `url_canonical` | TEXT | NOT NULL | |
| `outcome_type` | TEXT | NOT NULL, CHECK in `excluded,failed,deferred` | |
| `reason_code` | TEXT | NOT NULL, CHECK in `robots_disallowed,tos_restricted,requires_auth,out_of_scope,manual_exclusion,blocked,rate_limited,timeout,http_error,parse_error,storage_cap,empty_content` | FR-008/FR-013 |
| `detail` | TEXT | NULL | Error message or policy reference (no secrets) |
| `attempts` | INTEGER | NOT NULL DEFAULT 0 | |
| `occurred_at` | TEXT | NOT NULL | UTC |

## Table: `policy_checks`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `policy_check_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `campaign_id` | TEXT | NOT NULL, FK → `campaigns` | |
| `source_id` | TEXT | NOT NULL, FK → `sources` | |
| `decision` | TEXT | NOT NULL, CHECK in `allowed,disallowed,unknown` | Audit trail for SC-007 |
| `reason` | TEXT | NOT NULL | robots rule, ToS clause or allowlist result |
| `checked_at` | TEXT | NOT NULL | UTC |

## Derived View: `v_coverage_matrix`

Computed per campaign:

| Column | Derivation |
|--------|------------|
| `item_id`, `category`, `name` | From `coverage_items` |
| `evidence_count` | Count of linked artifacts with `retracted_at IS NULL` |
| `status` | `covered` if ≥1 direct evidence; `partial` if only supporting evidence; `missing` otherwise |
| `gap_reason` | From the latest `outcomes.reason_code` or manual note when `status = missing` |
| `artifact_refs` | JSON array of `artifact_id` values |

Evidence is counted only for artifacts observed by the campaign (`campaign_artifacts`), so a campaign cannot
claim coverage from content it never fetched. The report MUST list all 24 items regardless of status (SC-001).

## Validation Rules (from requirements)

1. **Provenance completeness (FR-003, SC-002)**: every artifact row has non-null `source_id`, `retrieved_at`,
   `http_status`, `content_hash`, `media_type`, `byte_size`, `storage_path`, `authority`, `language`.
2. **Hash format (FR-003/FR-011)**: 64 lowercase hex characters; reject anything else before insert.
3. **URL canonicalization (FR-014)**: lowercase scheme and host, remove default ports, drop fragments, sort
   query parameters, strip `utm_*`, `fbclid`, `gclid`, `mc_cid`, `mc_eid`; keep original in `url_original`.
4. **Storage ceiling (FR-010, SC-003)**: pre-write projection MUST be ≤ 10,000,000,000 bytes; otherwise defer
   and record `storage_cap`.
5. **Immutability (FR-004)**: existing artifact files are never overwritten; new content gets a new
   `content_hash` and `url_versions` row.
6. **Idempotency (FR-012, SC-004)**: re-running a campaign skips terminal targets; unique `content_hash`
   prevents duplicate bytes.
7. **Policy decision (FR-008/FR-009, SC-007)**: no request is issued unless a `policy_checks` row with
   `decision = allowed` exists for the host in the campaign.
8. **Coverage completeness (FR-007, SC-001)**: exactly 24 items; each reports `covered`, `partial` or `missing`;
   `missing` requires a `gap_reason`.
9. **Language (FR-022)**: `es`, `en` or `und`; method recorded.
10. **Retraction (edge case)**: setting `retracted_at` removes the artifact from reports and RAG exports but
    preserves its row, file and hash for audit.
11. **Campaign concurrency**: at most one campaign in `running` state (enforced by a partial unique index).

## Filesystem Metadata Contract

Each line of `data/bronze/manifests/<campaign_id>.jsonl` is an artifact record with the fields of
`contracts/artifact.schema.json`. The manifest is append-only during a campaign and can be rebuilt from
SQLite with `catalog export --format jsonl`.
