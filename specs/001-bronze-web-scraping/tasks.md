# Tasks: Capa Bronce de Recolección Web para el RAG de Manuelita

**Input**: Design documents from `/specs/001-bronze-web-scraping/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included. The constitution requires offline tests and the plan defines unit, integration and
contract layers.

**Organization**: Phases follow the four prioritized user stories; foundational infrastructure blocks all
stories. Tasks are marked `[P]` when they touch different files and can run in parallel.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Dependencies, configuration files and repository hygiene.

- [x] T001 Add runtime/dev dependencies and `pml` entry point in `pyproject.toml`, refresh `uv.lock`
- [x] T002 [P] Create `.gitignore` for Python, uv, data, secrets and caches
- [x] T003 [P] Create `config/coverage-items.toml` with the 24 required items
- [x] T004 [P] Create `config/sources.toml` and `config/exclusions.toml` with real seeds and policies
- [x] T005 [P] Configure Ruff, pytest and coverage settings in `pyproject.toml`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core models, persistence, storage guard, extraction and policy layer.

**⚠️ CRITICAL**: No user story can be implemented until this phase is complete.

- [x] T006 Implement enums and dataclasses in `src/proyecto_modelos_lenguaje/models.py`
- [x] T007 Implement TOML loading, validation and config hashing in `src/proyecto_modelos_lenguaje/config.py`
- [x] T008 Implement SQLite schema, migrations and CRUD in `src/proyecto_modelos_lenguaje/catalog.py`
- [x] T009 Implement atomic writes, hashing, MIME detection and the 10 GB guard in `src/proyecto_modelos_lenguaje/storage.py`
- [x] T010 [P] Implement URL canonicalization, link/sitemap parsing and metadata extraction in `src/proyecto_modelos_lenguaje/extractors/`
- [x] T011 [P] Implement language detection in `src/proyecto_modelos_lenguaje/extractors/language.py`
- [x] T012 Implement robots/ToS checks, SSRF guard and rate limiting in `src/proyecto_modelos_lenguaje/policies.py`
- [x] T013 [P] Add unit tests for extractors, storage and policies in `tests/unit/`
- [x] T014 Implement the fetcher protocol and scrapling HTTP adapter in `src/proyecto_modelos_lenguaje/fetchers/`

**Checkpoint**: Foundation ready — user stories can proceed.

---

## Phase 3: User Story 1 - Captura del sitio oficial (Priority: P1) 🎯 MVP

**Goal**: Crawl the official domain (sitemap + bounded BFS), store raw artifacts with provenance.

**Independent Test**: Run a campaign against the local fixture server and confirm pages/PDFs are stored once
with complete metadata and blocked paths are recorded.

### Tests for User Story 1

- [x] T015 [P] [US1] Integration test for the full fixture campaign in `tests/integration/test_campaign.py`

### Implementation for User Story 1

- [x] T016 [US1] Implement the campaign orchestrator in `src/proyecto_modelos_lenguaje/pipeline.py`
- [x] T017 [US1] Implement the official-site source in `src/proyecto_modelos_lenguaje/sources/official_site.py`
- [x] T018 [US1] Implement discovery and policy checks for sources in `src/proyecto_modelos_lenguaje/sources/base.py`
- [x] T019 [US1] Implement `init`, `campaign start` and `campaign status` in `src/proyecto_modelos_lenguaje/cli.py`
- [x] T020 [US1] Implement `scripts/run_campaign.py` as a thin wrapper
- [x] T021 [US1] Implement coverage seeding and evidence inference in `src/proyecto_modelos_lenguaje/coverage.py`
- [x] T022 [US1] Validate the MVP: fixture campaign stores artifacts, writes manifest and enforces policies

**Checkpoint**: Official-site capture works end to end offline.

---

## Phase 4: User Story 2 - Trazabilidad y reanudación (Priority: P2)

**Goal**: Audit provenance, verify integrity, deduplicate and resume interrupted campaigns.

**Independent Test**: Re-run a completed campaign with zero duplicates; interrupt and resume without loss;
verify sampled hashes.

### Tests for User Story 2

- [x] T023 [P] [US2] Tests for idempotency, resume, versioning and hashes in `tests/integration/test_resume.py`
- [x] T024 [P] [US2] Contract test for artifact JSON in `tests/contract/test_artifact_contract.py`

### Implementation for User Story 2

- [x] T025 [US2] Implement content dedupe and URL versioning in `catalog.py` and `pipeline.py`
- [x] T026 [US2] Implement `verify` and `catalog list/show/export` in `src/proyecto_modelos_lenguaje/cli.py`
- [x] T027 [US2] Implement `scripts/verify_bronze.py` and `scripts/query_catalog.py`

**Checkpoint**: Provenance, idempotency and resume validated.

---

## Phase 5: User Story 3 - Cobertura de las cuatro categorías (Priority: P3)

**Goal**: Produce the 24-item coverage matrix with evidence and justified gaps.

**Independent Test**: Generate a coverage report from a fixture campaign; all 24 items present with status.

### Tests for User Story 3

- [x] T028 [P] [US3] Unit and contract tests for coverage reports in `tests/unit/test_coverage.py` and `tests/contract/test_reports_contract.py`

### Implementation for User Story 3

- [x] T029 [US3] Implement campaign and coverage reporting in `src/proyecto_modelos_lenguaje/reporting.py`
- [x] T030 [US3] Wire `report` and `coverage` commands plus `scripts/report_coverage.py`

**Checkpoint**: Coverage matrix and reports validated.

---

## Phase 6: User Story 4 - Presencia digital y contenido audiovisual (Priority: P4)

**Goal**: Capture YouTube metadata/subtitles, public social posts, news and open-data sources.

**Independent Test**: Process fixture video metadata and public social pages; restricted platforms produce
documented exclusions.

### Tests for User Story 4

- [x] T031 [P] [US4] Tests for YouTube parsing and social exclusion in `tests/unit/test_youtube.py`

### Implementation for User Story 4

- [x] T032 [US4] Implement the YouTube adapter in `src/proyecto_modelos_lenguaje/fetchers/youtube.py`
- [x] T033 [US4] Implement the social adapter and platform policy matrix in `src/proyecto_modelos_lenguaje/fetchers/social.py`
- [x] T034 [US4] Implement news and open-data sources in `src/proyecto_modelos_lenguaje/sources/`

**Checkpoint**: All sources defined in configuration are supported.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [x] T035 [P] Update `README.md` with setup, campaign and verification commands
- [x] T036 Run Ruff and the full offline test suite; fix findings
- [x] T037 Execute quickstart dry-run and storage-cap scenarios against fixtures
- [x] T038 Create branch `001-bronze-web-scraping`, commit spec/plan/implementation with Conventional Commits

---

## Dependencies & Execution Order

- Setup (Phase 1) → Foundational (Phase 2) → US1 (Phase 3) → US2 (Phase 4) → US3 (Phase 5) → US4 (Phase 6) → Polish.
- US2 and US3 depend on US1's catalog and pipeline; US4 depends on the fetcher protocol only.
- Within each phase: tests before implementation, models before services, services before CLI.

## Implementation Strategy

MVP = Phase 1 + Phase 2 + Phase 3, validated with the fixture campaign. Then harden provenance/resume (US2),
coverage reporting (US3) and additional sources (US4) before the final quality gates.
