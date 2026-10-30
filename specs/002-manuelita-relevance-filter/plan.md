# Implementation Plan: Filtro de Relevancia del Corpus de Manuelita

**Branch**: `002-manuelita-relevance-filter` | **Date**: 2026-10-28 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/002-manuelita-relevance-filter/spec.md`

## Summary

Depurar el corpus bronce de Manuelita: evaluar los 26.752 artefactos (9,86 GB), clasificarlos como
`keep` / `remove` / `review` con evidencia verificable, retirar del corpus activo lo irrelevante, liberar
espacio mediante cuarentena y purga aprobada, conservar auditoría permanente y recalcular la cobertura de
los 24 ítems solo con contenido relevante. La solución es determinista y sin nuevos servicios: reglas de
términos y contexto sobre el catálogo SQLite existente, reutilizando la extracción de texto y el
almacenamiento actuales, con comandos nuevos en la CLI `pml` y envoltorios en `scripts/`.

## Technical Context

**Language/Version**: Python 3.14 (CPython 3.14.7), managed with `uv`; `requires-python = ">=3.14"`

**Primary Dependencies**: Existing runtime only — `scrapling[fetchers]`, `yt-dlp`, and standard library
`sqlite3`, `hashlib`, `re`, `pathlib`, `json`, `shutil`; no new runtime dependency. Third-party PDFs without
extractable text are routed to review instead of adding a PDF parser.

**Storage**: Existing SQLite catalog (`data/bronze/_meta/bronze.sqlite3`, WAL) for evaluations, runs, review
and audit; raw files in `data/bronze/raw/`; quarantine in `data/quarantine/<run_id>/<artifact_id>/`; active
manifest `data/bronze/manifests/<campaign>.jsonl` regenerated from the active view

**Testing**: `pytest` with unit tests for scoring/namesakes, integration tests over a synthetic corpus and a
fixture SQLite catalog, and JSON-schema contract tests; fully offline

**Target Platform**: Windows 11 (development) and Linux (CI/execution); `pathlib` everywhere

**Project Type**: Single Python project — CLI data-curation pipeline with `src/` layout and `scripts/` wrappers

**Performance Goals**: Evaluate 26.752 artifacts / 9,86 GB in under 30 minutes (hard ceiling 2 hours); quarantine
under 10 minutes; purge under 5 minutes; memory under 1 GB by streaming files; report generated in under 1 minute

**Constraints**: Official-domain artifacts are never removed; raw bytes of kept artifacts are never modified;
explicit approval required before quarantine and purge; 30-day reversible quarantine by default; audit survives
purge; idempotent and resumable; 10 GB cap enforced during operations

**Scale/Scope**: 26.752 artifacts, 7 sources, 9,86 GB raw; projected active corpus ≈410 artifacts (<0,3 GB);
one curation run at a time

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Gate | Status | Evidence / Plan |
|-----------|------|--------|-----------------|
| I. Reproducibilidad | Deterministic rules, versioned config, recorded commit/config hash, reproducible audit | PASS | `config/relevance.toml` hashed per run; rules have no randomness; `curation_runs` stores commit, config hash, counts and bytes |
| II. Evaluación con Métricas y Línea Base | Precision/recall measured against a labeled baseline before tuning | PASS | Stratified manual sample (100 likely relevant + 100 random) used as validation baseline; separate 100-item test sample; SC-003/SC-004 thresholds |
| III. Procedencia y Ética de Datos | Provenance documented; raw data immutable; transformations versioned and reversible | **PASS WITH JUSTIFIED EXCEPTION** | Kept bytes untouched; quarantine is reversible for 30 days; audit keeps URL/hash/reason permanently. Definitive purge of irrelevant bytes is an explicit, approved exception documented in Complexity Tracking |
| IV. Experimentos como Código | Pipeline in `src/`, CLI-invokable, config externalized, no manual steps | PASS | New `relevance.py` / `curation.py`, `pml curate` commands, `scripts/` wrappers, TOML config, tests |
| V. Simplicidad y Alcance | Minimal complexity and dependencies | PASS | Reuses catalog, storage and HTML extraction; no LLM, vector DB, queue or new package; rule-based and auditable |
| Workflow gates | Offline tests, Ruff, Conventional Commits, constitution check | PASS | Unit + integration + contract tests; atomic commits per task |

**Result**: No unjustified violations. One documented exception (definitive purge) with explicit approval,
30-day quarantine and permanent audit metadata.

**Post-design re-evaluation (after Phase 1)**: The data model isolates curation metadata from acquisition
history, the contracts require `--apply` and `--confirm` for destructive steps, and the quickstart proves the
official-domain guard and restore path. All gates remain PASS; Principle III keeps its documented exception.

## Project Structure

### Documentation (this feature)

```text
specs/002-manuelita-relevance-filter/
├── plan.md              # This file
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/           # Phase 1 output (CLI + JSON schemas)
└── tasks.md             # Phase 2 output (/speckit.tasks — NOT created here)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── relevance.py           # Terms, aliases, namesake guards, scoring and evidence
├── curation.py            # Run orchestration: analyze, review, quarantine, purge, restore
├── catalog.py             # Extended schema and queries for evaluations, runs, audit, quarantine
├── storage.py             # Quarantine moves, integrity checks, byte accounting
├── coverage.py            # Active-corpus coverage matrix
├── reporting.py           # Curation report (JSON + Markdown)
├── cli.py                 # New `pml curate ...` command group; curated coverage flag
└── config.py              # Loader/validator for config/relevance.toml

scripts/
├── analyze_relevance.py   # Thin wrapper: pml curate analyze
├── review_relevance.py    # Thin wrapper: pml curate review list/decide
└── apply_curation.py      # Thin wrapper: pml curate apply/quarantine/purge

config/
└── relevance.toml         # Terms, aliases, negative patterns, thresholds, protected domains, retention

data/
├── bronze/                # Existing corpus (raw + catalog + manifests + reports)
└── quarantine/<run_id>/<artifact_id>/<hash>.<ext>   # Not versioned

tests/
├── unit/test_relevance.py         # Scoring, namesakes, incidental tokens, thresholds
├── unit/test_curation_catalog.py  # Schema, idempotency, active view
├── integration/test_curation_flow.py  # Synthetic corpus: analyze → review → quarantine → purge/restore
└── contract/test_curation_contracts.py # JSON schemas and CLI payloads
```

**Structure Decision**: Extend the existing single project. Relevance logic and orchestration are separate
modules; the catalog and reporting modules gain curation tables/queries. Destructive behavior lives behind an
explicit command group, never in the scraping pipeline. Operational entry points remain thin wrappers in
`scripts/`. Data stays outside Git.

## Complexity Tracking

> One constitution exception is consciously accepted: definitive purge of irrelevant raw bytes.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Permanent deletion of raw bytes for irrelevant artifacts (Principle III: raw data immutable/reversible) | 99,98% of 9,86 GB is generic portal content; retaining it blocks new campaigns under the 10 GB cap and adds no value to the RAG. The spec requires reducing the corpus to ≤1,5 GB (SC-005) | Keeping all bytes in indefinite quarantine preserves immutability but never frees space and permanently closes the bronze layer. Deleting without audit would violate provenance. The chosen middle path keeps a 30-day reversible quarantine and permanent URL/hash/reason audit, requires explicit approval, and never touches official-domain artifacts |
