# Quickstart: Validación de la Capa Bronce

**Feature**: `001-bronze-web-scraping` | **Date**: 2026-10-27

Guía para verificar de extremo a extremo que la capa bronce cumple la especificación. No contiene código de
implementación; los detalles técnicos están en [plan.md](./plan.md), [data-model.md](./data-model.md) y
[contracts/](./contracts/).

## Prerequisites

- Python 3.14 and `uv` installed.
- Internet access for real campaigns; **not** required for the test suite.
- Repository cloned with the feature branch checked out.
- `config/sources.toml`, `config/coverage-items.toml` and `config/exclusions.toml` present.
- No credentials are needed; unauthenticated public content only.

## Setup

```bash
uv sync --frozen
uv run ruff check .
uv run pytest
```

Expected: environment builds from `uv.lock`, lint passes, all tests pass without network access.

## Scenario 1 — Initialize the catalog (SC-001 baseline)

```bash
uv run pml init --config config/sources.toml --json
```

Expected:

```json
{"status":"initialized","schema_version":"1.0","coverage_items":24,"sources":15}
```

Failure signal: exit code `3` if the coverage seed does not contain exactly the 24 required item IDs.

## Scenario 2 — Dry run of discovery and policy (SC-007)

```bash
uv run pml campaign start --config config/sources.toml --campaign smoke-001 --dry-run --json
```

Expected: `status` is `completed` or `paused`, `artifacts_stored` is `0`, and every discovered host has a
`policy_checks` decision. No HTTP request is issued to a disallowed path.

## Scenario 3 — Offline end-to-end test (SC-002, SC-004, SC-005)

```bash
uv run pytest tests/integration -q
```

Expected: a campaign runs against the local fixture server (HTML, PDF, sitemap, robots), artifacts are
stored, a second run stores zero duplicates, and an interrupted run resumes without corruption.

## Scenario 4 — First real campaign (SC-008, SC-010)

```bash
uv run python scripts/run_campaign.py --config config/sources.toml --campaign 2026-10-baseline
```

Expected:

- Exit code `0` (or `4` if the cap was reached, with the campaign paused).
- `data/bronze/reports/2026-10-baseline/campaign.json` exists.
- `bytes_stored` ≤ `10000000000`.
- Coverage summary totals 24 items.
- At least 95% of allowed reachable official-site pages captured.

## Scenario 5 — Verify provenance and integrity (SC-002, SC-006)

```bash
uv run python scripts/verify_bronze.py --campaign 2026-10-baseline --sample 20 --seed 42 --json
```

Expected:

```json
{"campaign_id":"2026-10-baseline","sampled":20,"passed":20,"failed":0,"failures":[]}
```

Manual check: open any `storage_path`, recompute its SHA-256 and compare with `content_hash` from
`data/bronze/manifests/2026-10-baseline.jsonl`.

## Scenario 6 — Idempotency and resume (SC-004, SC-005)

```bash
# Interrupt during scenario 4 with Ctrl+C, then:
uv run python scripts/run_campaign.py --config config/sources.toml --campaign 2026-10-baseline --resume
```

Expected: the campaign continues from the last state; no artifact is re-downloaded, no partial file remains,
and artifact counts do not duplicate.

## Scenario 7 — Coverage matrix (SC-001, SC-010)

```bash
uv run python scripts/report_coverage.py --campaign 2026-10-baseline
```

Expected: a 24-row matrix in `data/bronze/reports/2026-10-baseline/coverage.json` where every item has
`covered`, `partial` or `missing`; each `missing` item has a non-empty `gap_reason`.

## Scenario 8 — Catalog queries (FR-006)

```bash
uv run python scripts/query_catalog.py list --campaign 2026-10-baseline --category identity --limit 5 --json
uv run python scripts/query_catalog.py show --artifact-id 1 --json
```

Expected: JSON validates against `contracts/artifact.schema.json`; results exclude retracted artifacts by
default.

## Scenario 9 — Storage ceiling (SC-003)

```bash
uv run pml campaign start --config config/sources.toml --campaign cap-test --max-bytes 5000000 --json
```

Expected: exit code `4`; `bytes_stored` ≤ 5,000,000; deferred targets recorded with reason
`storage_cap`; no write exceeds the limit.

## Scenario 10 — Ethics and policy audit (SC-007)

```bash
uv run python scripts/query_catalog.py list --campaign 2026-10-baseline --json
```

Inspect `data/bronze/_meta/bronze.sqlite3` table `policy_checks` and the campaign log. Expected: zero
requests to paths disallowed by robots, zero auth-protected sources, and every exclusion has a reason code.

## Acceptance Map

| Scenario | Requirements | Success criteria |
|----------|--------------|------------------|
| 1 | FR-007, FR-018 | SC-001 |
| 2 | FR-008, FR-009, FR-018 | SC-007 |
| 3 | FR-011, FR-012, FR-013 | SC-002, SC-004, SC-005 |
| 4 | FR-001, FR-002, FR-010, FR-017 | SC-008, SC-010 |
| 5 | FR-003, FR-011 | SC-002, SC-006 |
| 6 | FR-012, FR-020 | SC-004, SC-005 |
| 7 | FR-007, FR-017 | SC-001, SC-009, SC-010 |
| 8 | FR-006 | SC-002 |
| 9 | FR-010 | SC-003 |
| 10 | FR-008, FR-009, FR-016 | SC-007 |

## Troubleshooting

- **Exit `3`**: configuration invalid; read the stderr JSONL `event=config_invalid`.
- **Exit `4`**: storage ceiling reached; inspect `outcomes` with `reason_code=storage_cap`, then raise the cap
  or defer large sources to another campaign.
- **Exit `5`**: integrity failure; do not delete evidence — record the failing artifact ID and re-fetch it in a
  new campaign so the previous version remains auditable.
- **No coverage for a social source**: expected when the platform requires authentication; confirm the
  documented gap in the coverage report.
