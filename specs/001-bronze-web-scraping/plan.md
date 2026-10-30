# Implementation Plan: Capa Bronce de Recolección Web para el RAG de Manuelita

**Branch**: `001-bronze-web-scraping` | **Date**: 2026-10-27 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-bronze-web-scraping/spec.md`

## Summary

Construir la capa bronce del RAG de Manuelita: un pipeline de adquisición web que descubre y captura
contenido público (sitio oficial, noticias, blogs, YouTube, redes sociales, portales de empleo y datos
abiertos), lo almacena en crudo e inmutable con procedencia completa, lo cataloga de forma consultable,
garantiza idempotencia y reanudación, y nunca supera los 10 GB. La implementación es un paquete Python
3.14 con CLI, `scrapling` como motor de extracción, catálogo SQLite, almacenamiento en sistema de archivos
bajo `data/bronze/` y scripts operativos en `scripts/`.

## Technical Context

**Language/Version**: Python 3.14 (CPython 3.14.7 installed), managed with `uv`; `requires-python = ">=3.14"`

**Primary Dependencies**: `scrapling[fetchers]` 0.5 (AsyncFetcher, StealthyFetcher, curl_cffi,
playwright/patchright, protego), `yt-dlp` (YouTube metadata and subtitles only); standard library
`sqlite3`, `tomllib`, `hashlib`, `urllib.robotparser`, `logging`, `pathlib`

**Storage**: Local filesystem for raw artifacts + SQLite (WAL) catalog and JSONL manifests/reports under
`data/bronze/`; no external database or object storage; hard cap of 10 GB

**Testing**: `pytest` (unit, integration with a local fixture HTTP server, contract tests for CLI JSON);
`ruff` for lint/format; no network access in tests

**Target Platform**: Windows 11 (development) and Linux (execution/CI); cross-platform paths via `pathlib`

**Project Type**: Single project — Python CLI data pipeline with `src/` layout and operational scripts

**Performance Goals**: ≤5 requests/second per host; full campaign for ~50,000 artifacts in under 24 hours;
catalog queries under 1 second at 50,000 records; coverage/run report generated within 15 minutes of
campaign end

**Constraints**: 10 GB hard storage ceiling; no authentication bypass, paywall circumvention or PII
collection; offline-testable; deterministic manifests; no video/audio binaries; Windows and Linux support

**Scale/Scope**: One company (Ingenio Manuelita), 15–25 allowed sources, 24 required information items,
~50,000 artifacts, one active campaign at a time, append-only bronze

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Evidence / Plan |
|-----------|------|--------|-----------------|
| I. Reproducibilidad Experimental | Environment rebuildable with `uv sync --frozen`; seeds recorded; data and config versioned; each run records commit, config hash and metrics | PASS | `uv.lock` committed; campaigns reference config hash + git commit; manifests store SHA-256 per artifact |
| II. Evaluación con Métricas y Línea Base | Measurable evaluation against a baseline defined before execution | PASS (adapted) | Baseline = curated seed list of known URLs and 24 required items; coverage/precision metrics (SC-001…SC-010) measured per campaign |
| III. Procedencia y Ética de Datos | Provenance per artifact; robots/ToS/rate limits; no PII; raw data immutable | PASS | `sources.toml` policies, `sources.policy_status` + `policy_checks`, exclusion log, immutable raw store, no auth bypass |
| IV. Experimentos como Código Versionado | Pipelines in `src/`, CLI-invokable, config externalized, no absolute paths or secrets | PASS | Package modules + `scripts/` entry points; TOML config; all paths derived from a configurable data root |
| V. Simplicidad y Alcance Académico | Minimal complexity and dependencies; YAGNI | PASS | Stdlib SQLite/TOML/hashlib; only two runtime dependencies; no vector DB, queue or service |
| Workflow gates (tests, review, commits) | Offline tests, Ruff, Conventional Commits, constitution check in plan | PASS | Test pyramid in `tests/`; CI-ready commands; atomic commits per task |

**Result**: No violations. `Complexity Tracking` remains empty.

**Post-design re-evaluation (after Phase 1)**: The data model, CLI contracts and quickstart were reviewed
against all five principles. The design keeps raw content immutable, records provenance and policy decisions,
stores configuration as code, and adds no service or dependency beyond `scrapling[fetchers]` and `yt-dlp`.
All gates remain **PASS**; no new complexity needs justification.

## Project Structure

### Documentation (this feature)

```text
specs/001-bronze-web-scraping/
├── plan.md              # This file (/speckit.plan command output)
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI and data contracts)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── __init__.py
├── cli.py                 # Typer-free argparse CLI: campaign, verify, report, catalog
├── config.py              # TOML loading/validation, path resolution, config hashing
├── models.py              # Dataclasses/enums for targets, artifacts, campaigns, outcomes
├── pipeline.py            # Campaign orchestrator: discovery, fetch, store, resume, reports
├── utils.py               # UTC timestamps, slugs and human-readable sizes
├── catalog.py             # SQLite schema, migrations, queries, WAL, transactions
├── storage.py             # Raw artifact writer, atomic writes, 10 GB guard, hashing
├── policies.py            # robots.txt, ToS/allowlist checks, per-host rate limiting
├── coverage.py            # 24-item coverage matrix and gap justification
├── reporting.py           # Campaign report and coverage report (JSON + Markdown)
├── fetchers/
│   ├── base.py            # Fetcher protocol (HTTP/browser/API adapters)
│   ├── http.py            # scrapling AsyncFetcher adapter
│   ├── browser.py         # Optional StealthyFetcher adapter (JS-heavy sources)
│   ├── youtube.py         # yt-dlp metadata/subtitles adapter (no media download)
│   └── social.py          # Public social page adapter (Open Graph + HTML)
├── extractors/
│   ├── links.py           # Link discovery, canonicalization, scope filters
│   ├── metadata.py        # MIME sniffing, title/date/language extraction
│   └── language.py        # Spanish/English heuristic (HTML lang + stopwords)
└── sources/
    ├── official_site.py   # Sitemap-first crawl of manuelita.com
    ├── news.py            # Press room, news, blogs
    ├── youtube.py         # Channel/video search and captions
    ├── social.py          # Public Facebook/Instagram/X best effort
    └── open_data.py       # Superintendencia, SECOP, rankings, job boards

scripts/
├── run_campaign.py        # Thin wrapper: start/resume a campaign
├── verify_bronze.py       # Sample verification of hashes and metadata
├── report_coverage.py     # Export coverage matrix and gaps
└── query_catalog.py       # Ad-hoc catalog queries for review

config/
├── sources.toml           # Allowed sources, seeds, policies, rate limits, priorities
├── coverage-items.toml    # 24 required items with keywords and evidence rules
└── exclusions.toml        # Manual URL/domain exclusions

data/                      # Not versioned (.gitignore)
├── bronze/
│   ├── raw/<source>/<campaign>/<sha256>.<ext>
│   ├── manifests/<campaign>.jsonl
│   ├── reports/<campaign>/
│   └── _meta/bronze.sqlite3
├── silver/                # Reserved for Phase 2
└── gold/                  # Reserved for Phase 3

tests/
├── unit/                  # Canonicalization, hashing, cap guard, coverage math
├── integration/           # End-to-end campaign against local fixture server
└── contract/              # CLI JSON outputs against schemas in contracts/
```

**Structure Decision**: Single Python project using the existing `src/proyecto_modelos_lenguaje/` layout.
Domain logic lives in the package; `scripts/` holds the thin operational entry points requested by the user.
Configuration is declarative TOML; all persistent data lives under `data/` and is excluded from Git. Tests
mirror the package layers.

## Complexity Tracking

> No constitution violations. No additional projects, services or abstraction layers are introduced.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
