# Interface Contract: Curation CLI

**Feature**: `002-manuelita-relevance-filter` | **Version**: 1.0.0

New commands under `pml curate`. Existing commands remain backward compatible; `catalog list/export` and
`coverage` gain an optional `--active-only` flag.

## Global Conventions

- **Stdout**: machine-readable result (`--json`) or a human summary.
- **Stderr**: structured JSONL logs.
- **Dry-run by default**: `analyze` writes nothing unless `--apply` is present.
- **Destructive commands** (`quarantine`, `purge`) require `--confirm`; `purge` also requires run approval and
  retention expiry or `--now`.
- **Exit codes**:

  | Code | Meaning |
  |------|---------|
  | `0` | Success |
  | `2` | Invalid usage or unknown run/artifact |
  | `3` | Invalid configuration |
  | `4` | Guard blocked (official-domain artifact or manual keep) |
  | `5` | Pending review items prevent approval |
  | `6` | Run not approved / not in required state |
  | `7` | Integrity failure (hash mismatch or missing file) |
  | `1` | Unexpected error |

## Commands

### `pml curate analyze`

Evaluates relevance for the corpus (or one campaign) and optionally persists decisions.

```text
pml curate analyze --config config/relevance.toml [--campaign <id>] [--run <id>]
                   [--apply] [--json]
```

- Without `--apply`: read-only analysis; prints counts and a sample; no evaluations are written.
- With `--apply`: creates a `curation_runs` row in `analyzed`, writes evaluations and review items, and generates
  the report.
- Re-running with the same `--run` is idempotent; without `--run`, a new run id is generated.
- Output:

  ```json
  {
    "run_id": "2026-10-curation-01",
    "dry_run": false,
    "status": "analyzed",
    "artifacts_evaluated": 26752,
    "kept": 410,
    "removed": 26300,
    "review": 42,
    "bytes_before": 9860149523,
    "config_hash": "…64 hex…",
    "report_paths": ["data/bronze/reports/2026-10-curation-01/curation.json"]
  }
  ```

### `pml curate runs`

```text
pml curate runs [--json]
```

Lists runs with status, counts and bytes.

### `pml curate status`

```text
pml curate status --run <id> [--json]
```

Returns the run row plus `pending_reviews`, `quarantined`, `purged` and `bytes_freed`.

### `pml curate report`

```text
pml curate report --run <id> [--format json|md]
```

Writes and prints `reports/<run_id>/curation.json` and `summary.md`.

### `pml curate review list`

```text
pml curate review list --run <id> [--limit 50] [--offset 0] [--json]
```

- Returns pending items with `artifact_id`, URL, title, snippet, score and reason.
- Output: `{"total": 42, "count": 42, "items": [...]}`.

### `pml curate review decide`

```text
pml curate review decide --artifact <id> --decision keep|remove
                         --reviewer <name> [--note <text>] [--json]
```

- Updates `relevance_evaluations` (`method=manual`, `manual_override=1`) and `review_items`.
- Exit `4` if a `remove` decision targets an official-domain artifact.

### `pml curate approve`

```text
pml curate approve --run <id> --reviewer <name> [--json]
```

- Exit `5` if any `review_items` remains `pending`.
- Sets status `approved`, `approved_by` and `approved_at`.

### `pml curate quarantine`

```text
pml curate quarantine --run <id> --confirm [--json]
```

- Requires status `approved`.
- Writes audit rows, moves files to `data/quarantine/<run_id>/<artifact_id>/`, records entries and regenerates
  active manifests.
- Exit `4` if an official-domain artifact or a manual `keep` appears in the removal set.
- Idempotent: already quarantined artifacts are skipped.

### `pml curate restore`

```text
pml curate restore --artifact <id> [--json]
```

- Only for `quarantined` entries; verifies hash before restoring to the original path.
- Returns the artifact to the active corpus (evaluation becomes manual `keep`).

### `pml curate purge`

```text
pml curate purge --run <id> (--expired | --now) --confirm [--json]
```

- Requires `quarantined` entries and an approved run.
- `--expired`: only entries whose `expires_at` has passed.
- `--now`: explicit early purge; requires `--confirm`.
- Deletes files, marks entries `purged`, sets `purged_at`, updates `bytes_freed`; audit rows remain.
- Idempotent: purged entries are not counted twice.

### `pml coverage --active-only`

```text
pml coverage --campaign <id> [--status covered|partial|missing] --active-only [--json]
```

- Recomputes the 24-item matrix over `v_active_artifacts`.
- Without `--active-only`, existing behavior is unchanged.

### `pml catalog list/export --active-only`

- Adds an optional filter over `v_active_artifacts`; default behavior remains the full catalog.

## Script Wrappers

| Script | Equivalent |
|--------|------------|
| `scripts/analyze_relevance.py` | `pml curate analyze` |
| `scripts/review_relevance.py` | `pml curate review list` / `decide` |
| `scripts/apply_curation.py` | `pml curate approve` / `quarantine` / `purge` |

Wrappers forward exit codes unchanged and contain no domain logic.

## Compatibility

- New commands are additive; existing command signatures remain valid.
- JSON output is additive; existing fields keep type and meaning.
- The `--active-only` flag is opt-in, so pre-curation reports do not change silently.
