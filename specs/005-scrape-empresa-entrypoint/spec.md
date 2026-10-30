# Feature Specification: Canonical Company Scraping Entry Point

**Feature Branch**: `005-scrape-empresa-entrypoint`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "despliega las especificaciones para la creación de scrape_empresa.py para el cumplimiento de la tarea M1-02"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the canonical scraping command (Priority: P1)

An operator or evaluator needs one documented command to start a company scraping campaign without
knowing the internal pipeline commands, configuration layout, or campaign conventions.

**Why this priority**: The constitution and the M1-02 acceptance criterion require a canonical entry
point. Without it, the project can scrape, but a third party cannot reproduce the run from the
documentation alone.

**Independent Test**: Run the canonical command against a small, disposable campaign and confirm that
it starts the existing bronze pipeline, reports the campaign status and metrics, and leaves the
bronze corpus in a valid state.

**Acceptance Scenarios**:

1. **Given** a valid configuration and a new campaign identifier, **When** the operator runs the
   canonical command, **Then** the campaign starts, the existing pipeline performs discovery and
   extraction, and the command reports the final status and metrics.
2. **Given** a valid configuration and an existing campaign, **When** the operator runs the command,
   **Then** it reports the existing state and resumes only when the campaign is resumable.
3. **Given** no arguments, **When** the operator runs the command, **Then** it displays usage and
   examples, exits successfully, and performs no network access.

---

### User Story 2 - Resume an interrupted campaign (Priority: P2)

An operator needs to continue a campaign that was paused, interrupted, or failed without creating
duplicates or losing progress.

**Why this priority**: Scraping takes time and can fail mid-run. Reproducibility and idempotency are
non-negotiable project principles.

**Independent Test**: Interrupt a limited campaign, run the command again with the same campaign
identifier, and verify that it resumes, does not duplicate artifacts, and reports the accumulated
metrics.

**Acceptance Scenarios**:

1. **Given** a campaign in a resumable state, **When** the operator runs the command with the same
   campaign identifier, **Then** it resumes from the recorded state and reports what was resumed.
2. **Given** a completed campaign, **When** the operator runs the command with the same identifier
   without an explicit resume or new campaign, **Then** it reports that the campaign is complete and
   does not silently overwrite it.
3. **Given** a campaign identifier that does not exist, **When** the operator requests a resume,
   **Then** the command fails with an actionable message and does not create a campaign.

---

### User Story 3 - Run a safe trial before a full campaign (Priority: P3)

An operator needs to validate configuration, connectivity, and policy compliance with a small run
before committing to a full campaign.

**Why this priority**: A full run is expensive and could hit rate limits or storage limits. A safe
trial reduces risk and supports the demo.

**Independent Test**: Run the command in dry-run mode with a target limit and confirm that no bronze
artifacts or catalog records are created, while the discovery summary is still reported.

**Acceptance Scenarios**:

1. **Given** a valid configuration and a target limit, **When** the operator runs a dry-run, **Then**
   the command discovers targets, reports the summary, and writes no bronze artifacts or catalog
   records.
2. **Given** a positive target limit, **When** the operator runs a real limited campaign, **Then** the
   command processes no more than the requested number of targets.
3. **Given** an invalid limit, **When** the operator runs the command, **Then** it rejects the value
   before any network access.

---

### User Story 4 - Audit policy compliance and delegation (Priority: P4)

An auditor needs to confirm that the canonical command delegates to the existing pipeline and does not
bypass access controls, duplicate scraping logic, or modify downstream layers.

**Why this priority**: The project's data ethics and reproducibility principles require that the
canonical entry point be transparent and auditable.

**Independent Test**: Compare a limited run through the canonical command with the same run through
the underlying pipeline and verify equivalent artifacts, policy decisions, and metrics.

**Acceptance Scenarios**:

1. **Given** a source disallowed by `robots.txt`, **When** the campaign runs, **Then** the source is
   recorded as blocked with its reason and the campaign continues with the remaining sources.
2. **Given** a completed run, **When** the auditor inspects the bronze catalog and reports, **Then**
   the artifacts, hashes, policy decisions, and metrics match a direct pipeline run with the same
   inputs.
3. **Given** any invocation, **When** the command finishes, **Then** it has not modified silver, gold,
   or any downstream layer.

---

### Edge Cases

- The configuration file is missing, unreadable, or invalid: fail before any network access with an
  actionable message and a usage exit code.
- The campaign identifier is empty, malformed, or contains unsafe characters: reject it before any
  network access.
- The campaign is already running in another process: refuse to start a second concurrent run and
  report the active state.
- The campaign is completed: report completion and do not silently overwrite it; require a new
  identifier or an explicit resume policy.
- `robots.txt` cannot be retrieved: follow the pipeline's documented policy, record the decision, and
  never silently ignore the result.
- A source is disallowed: record the decision, skip the source, and continue the campaign.
- The network fails mid-run: preserve partial state, exit non-zero, and allow a later resume.
- The storage limit is reached: stop gracefully, report the limit, and exit non-zero.
- The output is requested as JSON and an error occurs: emit a machine-readable error object and a
  non-zero exit code.
- The command is invoked from a directory other than the repository root: resolve documented paths
  consistently and fail with a clear message if the project root cannot be determined.
- The platform uses different path separators or console encodings: behave consistently on Windows and
  Linux.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The project MUST provide the canonical command `scripts/scrape_empresa.py`, executable
  with `uv run python scripts/scrape_empresa.py`.
- **FR-002**: The command MUST accept `--config` and default to the versioned source configuration
  when the option is omitted.
- **FR-003**: The command MUST require an explicit `--campaign` identifier for any run. Invoking it
  without a campaign MUST display usage and examples, exit successfully, and perform no network access.
- **FR-004**: The command MUST accept `--help` and document every supported option, its default, and at
  least one complete example.
- **FR-005**: The command MUST accept `--resume` to continue an existing resumable campaign and MUST
  report that the run is a resume.
- **FR-006**: The command MUST automatically resume a campaign that the pipeline reports as resumable,
  even when `--resume` is omitted, and MUST state that decision in the output.
- **FR-007**: The command MUST accept `--limit N` to cap the number of processed targets, where `N` is a
  positive integer, and MUST reject zero, negative, or non-integer values before network access.
- **FR-008**: The command MUST accept `--dry-run` to discover targets and report the summary without
  creating or modifying bronze artifacts, catalog records, or campaign state.
- **FR-009**: The command MUST accept `--json` to emit a machine-readable summary and MUST keep human
  output readable when the option is absent.
- **FR-010**: The command MUST delegate discovery, extraction, storage, policy checks, and metrics to
  the existing bronze pipeline. It MUST NOT implement a second crawler or duplicate pipeline logic.
- **FR-011**: The command MUST respect `robots.txt`, the source terms of use, rate limits, timeouts,
  retries, and the declared user agent. It MUST NOT bypass access controls, use session cookies, or
  use credentials.
- **FR-012**: The command MUST be idempotent and resumable: re-running the same campaign MUST NOT create
  duplicate artifacts or lose previously stored progress.
- **FR-013**: The command MUST report the campaign identifier, status, discovered targets, extracted
  pages, stored artifacts, skipped sources, failed sources, bytes stored, and duration.
- **FR-014**: The command MUST use exit code 0 for success, 2 for usage or configuration errors, and a
  non-zero code for pipeline failures.
- **FR-015**: The command MUST fail before any network access when the configuration is missing,
  unreadable, or invalid, and MUST explain how to correct the problem.
- **FR-016**: The command MUST validate the campaign identifier and reject empty, malformed, or unsafe
  values before creating any state.
- **FR-017**: The command MUST create a new campaign only with the exact identifier provided by the
  operator. It MUST NOT invent, rename, or reuse a campaign identifier.
- **FR-018**: The command MUST detect an already running campaign and refuse to start a concurrent run,
  reporting the active state.
- **FR-019**: The command MUST record blocked sources with their policy reason and continue the
  campaign instead of aborting the entire corpus.
- **FR-020**: The command MUST NOT modify silver, gold, or any downstream layer. Its writes are limited
  to the bronze layer and its campaign reports.
- **FR-021**: The command MUST NOT emit secrets, credentials, or session data. When it reports paths, it
  MUST prefer repository-relative paths over absolute filesystem paths.
- **FR-022**: The command MUST state the effective configuration, campaign, resume decision, limit, and
  dry-run mode before starting work.
- **FR-023**: The command MUST behave consistently on Windows and Linux, including path handling and
  console encoding.
- **FR-024**: When the campaign is already complete, the command MUST report completion and MUST NOT
  overwrite it; it MUST require a new campaign identifier or an explicit resume policy.
- **FR-025**: The command MUST report the policy outcome for every source it attempts, including
  allowed, blocked, and unreachable decisions, without exposing credentials or session data.

### Key Entities *(include if feature involves data)*

- **Scrape Request**: the operator's intent, composed of the configuration path, campaign identifier,
  resume flag, target limit, dry-run flag, and output format.
- **Campaign**: a named bronze collection run with a status, start and finish times, configuration
  reference, and accumulated metrics.
- **Run Summary**: the outcome of a request, including status, target and artifact counts, skipped and
  failed sources, bytes stored, duration, and exit code.
- **Policy Decision**: the recorded allow or block decision for a source or URL, with its reason and
  timestamp.
- **Effective Parameters**: the resolved configuration, campaign, resume decision, limit, and dry-run
  mode that the command reports before execution.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A new operator can display complete usage with `--help` or with no arguments in under 5
  seconds, with exit code 0 and no network activity.
- **SC-002**: A dry-run with a limit of 5 creates zero bronze artifacts and zero catalog records, while
  reporting the discovery summary and exiting successfully.
- **SC-003**: A limited real run through the canonical command produces the same artifacts, hashes,
  policy decisions, and metrics as a direct run of the underlying pipeline with the same inputs.
- **SC-004**: After an interruption and resume, 100% of stored artifacts have unique content hashes and
  no previously stored artifact is lost.
- **SC-005**: 100% of sources blocked by `robots.txt` are recorded with a reason, and zero blocked
  sources are fetched.
- **SC-006**: Every successful run reports at least the campaign, status, discovered targets, stored
  artifacts, skipped sources, failed sources, bytes stored, and duration.
- **SC-007**: 100% of invalid configurations, campaign identifiers, and limits are rejected before
  network access with an actionable message and exit code 2.
- **SC-008**: The canonical command adds no more than 2 seconds of overhead compared with a direct
  invocation of the underlying pipeline for the same inputs.
- **SC-009**: Human and JSON outputs contain zero secrets, credentials, or session data in 100% of
  tested runs, and reported paths are repository-relative whenever a relative path is sufficient.
- **SC-010**: A reviewer can reproduce a limited campaign using only the command's help text and the
  repository documentation, without reading the pipeline source code.

## Assumptions

- The existing bronze pipeline is the source of truth for discovery, extraction, storage, policy
  checks, and metrics; the new command is a thin facade over it.
- An explicit campaign identifier is required for a real run; no default campaign is executed to avoid
  accidental long or destructive runs. Invoking the command without a campaign shows usage.
- The default configuration is the versioned source configuration already used by the project.
- Operators have network access to public sources and a working project environment.
- The bronze layer remains the only layer written by this command; silver and gold are built by their
  own commands.
- No new dependencies are required; the command reuses the existing runtime and configuration.
- Campaign identifiers follow the project's existing naming convention and are provided by the
  operator.
- The command is intended for operators, evaluators, and the demo, not for end users of the Q&A app.

## Out of Scope

- Cleaning, normalization, chunking, deduplication, or any silver-layer transformation.
- Gold-layer units, facts, conflicts, coverage, context packs, or FAQ seeds.
- LLM prompts, LangChain tasks, Streamlit UI, or the 40-question evaluation.
- New data sources, new scraping techniques, or changes to the source catalog.
- Bypassing `robots.txt`, terms of service, authentication, or rate limits.
- Scheduling, orchestration, dashboards, or long-running service operation.
- Changes to the bronze storage schema or to downstream layer contracts.
