# Tasks: Filtro de Relevancia del Corpus de Manuelita

**Input**: Design documents from `/specs/002-manuelita-relevance-filter/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Included (constitution requires offline tests).

**Organization**: Tasks follow the prioritized user stories. Foundation blocks all stories.

## Phase 1: Setup

- [x] T001 Create `config/relevance.toml` with terms, aliases, negative patterns, thresholds and retention
- [x] T002 Implement `load_relevance_config` with validation and config hashing in `src/proyecto_modelos_lenguaje/config.py`
- [x] T003 [P] Verify `.gitignore` covers `data/quarantine/` and add it if missing

---

## Phase 2: Foundational (Blocking)

- [x] T004 Extend the SQLite schema with `curation_runs`, `relevance_evaluations`, `relevance_evidence`, `review_items`, `curation_audit`, `quarantine_entries` and `v_active_artifacts` in `src/proyecto_modelos_lenguaje/catalog.py`
- [x] T005 Implement curation CRUD, review queries, active-artifact filters and report aggregates in `catalog.py`
- [x] T006 Implement deterministic scoring, namesake/incidental guards and evidence extraction in `src/proyecto_modelos_lenguaje/relevance.py`
- [x] T007 Implement quarantine move, restore and purge with integrity checks in `src/proyecto_modelos_lenguaje/storage.py`
- [x] T008 [P] Unit tests for scoring, namesakes, config and catalog invariants in `tests/unit/test_relevance.py` and `tests/unit/test_curation_catalog.py`

**Checkpoint**: Foundation ready.

---

## Phase 3: User Story 1 - Clasificar (P1) 🎯 MVP

- [x] T009 Implement `CurationService.analyze` (dry-run/apply, evidence, review items, counts) in `src/proyecto_modelos_lenguaje/curation.py`
- [x] T010 Implement `pml curate analyze|runs|status` in `src/proyecto_modelos_lenguaje/cli.py`
- [x] T011 [P] [US1] Integration test for dry-run/apply over a synthetic corpus in `tests/integration/test_curation_flow.py`
- [x] T012 [US1] Run dry-run analysis on the real corpus and validate counts against the spec baseline

---

## Phase 4: User Story 2 - Eliminar con auditoría (P2)

- [x] T013 [US2] Implement review decision and run approval with pending-review gate in `curation.py` and `catalog.py`
- [x] T014 [US2] Implement quarantine with audit records, file moves and active-manifest regeneration
- [x] T015 [US2] Implement purge (expired/now + confirm) and restore with hash verification
- [x] T016 [P] [US2] Integration test for approve → quarantine → restore → purge and idempotency

---

## Phase 5: User Story 3 - Cobertura y reportes (P3)

- [x] T017 [US3] Add `--active-only` coverage and catalog queries over `v_active_artifacts`
- [x] T018 [US3] Implement curation report (JSON + Markdown) in `src/proyecto_modelos_lenguaje/reporting.py`
- [x] T019 [P] [US3] Contract tests for evaluation, audit and curation report schemas

---

## Phase 6: User Story 4 - Revisión de ambiguos (P4)

- [x] T020 [US4] Implement `pml curate review list|decide` and `approve` CLI commands
- [x] T021 [US4] Add `scripts/analyze_relevance.py`, `review_relevance.py` and `apply_curation.py`

---

## Phase 7: Polish & Execution

- [x] T022 [P] Update `README.md` with the curation workflow
- [x] T023 Run Ruff and the full offline test suite; fix findings
- [x] T024 Execute the real curation: dry-run → apply → review → approve → quarantine (purge pending approval)
- [x] T025 Commit implementation with Conventional Commits
- [ ] T026 Purge definitively after the 30-day retention or with explicit approval (`--now --confirm`)

---

## Dependencies

- Phase 1 → Phase 2 → US1 → US2 → US3 → US4 → Polish.
- US2 depends on US1 evaluations; US3 depends on active view; US4 depends on review items.
- Tests before destructive commands; official-domain guard validated before quarantine.

## Strategy

MVP = Setup + Foundational + US1, validated with a dry-run on the real corpus. Then US2 (reversible
quarantine first, purge only with confirmation), US3 reporting and US4 review tooling. Purge remains the last,
explicitly confirmed action.
