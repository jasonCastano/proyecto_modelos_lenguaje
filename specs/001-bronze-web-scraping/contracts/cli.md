# Interface Contract: CLI and Operational Scripts

**Feature**: `001-bronze-web-scraping` | **Version**: 1.0.0

The package exposes a `pml` console entry point (`proyecto-modelos-lenguaje` alias). The scripts in
`scripts/` are thin wrappers over the same commands and MUST behave identically. This contract is what the
contract tests validate.

## Global Conventions

- **Stdout**: machine-readable result only (JSON when `--json`, human table otherwise).
- **Stderr**: structured JSONL logs (`{"level","event","campaign_id","url","detail"}`).
- **Exit codes**:
  | Code | Meaning |
  |------|---------|
  | `0` | Success (including a campaign that finished with recorded gaps) |
  | `2` | Invalid usage or arguments |
  | `3` | Invalid configuration or source policy |
  | `4` | Storage ceiling reached; campaign paused with partial results |
  | `5` | Verification failed (hash or metadata mismatch) |
  | `1` | Unexpected runtime error |
- **Paths**: all input paths are relative to the repository root unless absolute. Outputs outside
  `data/bronze/` are rejected.
- **Idempotency**: every write command is safe to re-run.

## Commands

### `pml init`

Validates configuration, seeds the 24 coverage items and creates the SQLite schema.

```text
pml init --config config/sources.toml [--json]
```

- Exit `3` if the TOML is invalid, the coverage seed is not exactly 24 items, or a source domain is duplicated.
- Output: `{"status":"initialized","schema_version":"1.0","coverage_items":24,"sources":N}`.

### `pml campaign start`

Starts a new campaign or resumes an existing one.

```text
pml campaign start --config config/sources.toml --campaign <id> [--resume] [--dry-run]
                   [--max-bytes <n>] [--json]
```

- `--campaign` MUST match `^[a-z0-9][a-z0-9-]{2,63}$`.
- `--max-bytes` cannot exceed `10000000000` (exit `3` otherwise).
- `--dry-run` performs discovery and policy checks without writing artifacts.
- Exit `4` when the storage guard pauses the campaign.
- Output:
  ```json
  {
    "campaign_id": "2026-10-baseline",
    "status": "completed",
    "targets_discovered": 4120,
    "artifacts_stored": 3987,
    "deduplicated": 96,
    "excluded": 21,
    "failed": 16,
    "deferred": 0,
    "bytes_stored": 184320011,
    "storage_limit_bytes": 10000000000,
    "coverage": {"covered": 24, "partial": 0, "missing": 0, "total": 24},
    "report_paths": ["data/bronze/reports/2026-10-baseline/campaign.json"]
  }
  ```

### `pml campaign status`

```text
pml campaign status --campaign <id> [--json]
```

- Output: campaign row with `status`, timestamps, counters and `bytes_stored`.
- Exit `2` if the campaign does not exist.

### `pml verify`

Recomputes hashes and validates metadata for a random sample (default 20, maximum 500).

```text
pml verify --campaign <id> [--sample 20] [--seed 0] [--json]
```

- Deterministic sample for a given `--seed` (default `0`).
- Checks: file exists, SHA-256 matches `content_hash`, size matches, required fields present, path inside
  `data/bronze/raw/`.
- Exit `5` if any check fails.
- Output: `{"campaign_id":"…","sampled":20,"passed":20,"failed":0,"failures":[]}`.

### `pml report`

```text
pml report campaign --campaign <id> [--format json|md]
pml report coverage --campaign <id> [--format json|md]
```

- Writes `reports/<campaign>/campaign.json` and `summary.md`, or `coverage.json` and `coverage.md`.
- Prints the generated path to stdout.
- Must complete within 15 minutes of campaign end (SC-009).

### `pml catalog`

```text
pml catalog list --campaign <id> [--category <c>] [--source <id>] [--language es|en|und]
                 [--coverage-item <id>] [--limit 100] [--offset 0] [--json]
pml catalog show --artifact-id <id> [--json]
pml catalog export --campaign <id> --format jsonl|csv --output <relative-path>
```

- `list` returns artifacts ordered by `artifact_id`, excluding retracted ones by default
  (`--include-retracted` to include).
- `export` refuses paths outside `data/bronze/` and refuses to overwrite an existing export unless
  `--force` is passed.
- JSON list output:
  ```json
  {"total": 3987, "count": 100, "offset": 0, "items": [{"artifact_id": 1, "...": "..."}]}
  ```

### `pml coverage`

```text
pml coverage --campaign <id> [--status covered|partial|missing] [--json]
```

- Returns the 24-item matrix even when empty (SC-001).
- `missing` items always include `gap_reason`.

## Script Wrappers

| Script | Equivalent command |
|--------|--------------------|
| `scripts/run_campaign.py` | `pml campaign start` (adds `--resume` when the campaign exists) |
| `scripts/verify_bronze.py` | `pml verify` |
| `scripts/report_coverage.py` | `pml report coverage` then `pml coverage` |
| `scripts/query_catalog.py` | `pml catalog list/show/export` |

Wrappers MUST forward exit codes unchanged and MUST NOT contain domain logic.

## Compatibility Rules

- Adding optional flags is backward compatible; renaming or removing a flag requires a MAJOR contract bump.
- JSON outputs are additive: new fields may appear, existing fields never change type or meaning.
- Every schema referenced here is versioned with `schema_version: "1.0"`.
