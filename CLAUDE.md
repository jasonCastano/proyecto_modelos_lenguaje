# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

Las reglas del equipo para asistentes están en [`AGENTS.md`](./AGENTS.md) y la norma técnica completa en
[`CONSTITUTION.md`](./CONSTITUTION.md) (capas, scraping, prompts, app, DoD). Este archivo resume lo
necesario para operar sin repetirlos.

## Comandos

Todo pasa por `uv` (nunca `pip`). Python ≥ 3.14; frontend en `web/` con npm.

```bash
make dev            # uv sync + npm ci + pre-commit install
make check          # ruff check + ruff format --check + pytest + vitest + build web (igual que CI)
make app            # build web + uvicorn en http://127.0.0.1:8000
make e2e            # Playwright (requiere PML_E2E=1, lo pone el Makefile; navegador vía PML_E2E_BROWSER)
```

Pruebas puntuales:

```bash
uv run pytest tests/unit/test_x.py::test_nombre
uv run pytest tests/api -k ask
cd web && npx vitest run src/test/DemoBanner.test.tsx
```

Desarrollo con recarga: `uv run uvicorn proyecto_modelos_lenguaje.api:app --reload --port 8000` y
`cd web && npm run dev`.

Tareas LangChain desde CLI (sin clave con `--fake`):

```bash
uv run python -m proyecto_modelos_lenguaje.tasks qa --question "¿Qué produce Manuelita?" --fake --json
uv run python -m proyecto_modelos_lenguaje.tasks summary --pack 8000 --json
uv run python -m proyecto_modelos_lenguaje.tasks faq --limit 12 --json
uv run python -m proyecto_modelos_lenguaje.llm --check   # valida DEEPSEEK_API_KEY / modelo
```

Pipeline de datos (CLI `pml` = `proyecto_modelos_lenguaje.cli:main`; cada capa tiene también un wrapper en
`scripts/`):

```bash
uv run python scripts/scrape_empresa.py --campaign <id> --limit 3 --dry-run --json   # bronce, sin escribir
uv run pml silver build --run <run_id> [--limit 10] --json
uv run pml gold build --run <run_id> [--limit 10] --json
uv run pml {silver,gold} {verify,report,status} ...
```

## Arquitectura

Flujo medallion → tareas → web:

1. **Bronce** (`sources/`, `fetchers/`, `extractors/`, `pipeline.py`, `campaign_service.py`): scraping con
   Scrapling por campañas, respetando robots/sitemap/rate limit. Guarda bytes originales **inmutables** con
   hash en `data/bronze/`. Un catálogo SQLite (`catalog.py`, `storage.py`) es la fuente de verdad de
   procedencia, dedupe por hash, cobertura de los 24 ítems (`coverage.py`) y auditoría. `relevance.py` /
   `curation.py` mueven lo irrelevante a `data/quarantine/` (no versionada); `manuelita.com` nunca se retira.
   Fuentes y políticas en `config/sources.toml`, `config/exclusions.toml`, `config/relevance.toml`.
2. **Plata** (`silver/`): limpieza, secciones, dedupe y chunking deterministas y offline (sin LLM ni OCR) →
   `data/silver/documents.jsonl`, `chunks.jsonl`, `markdown/`. Incremental vía `_meta/state.jsonl`.
3. **Oro** (`gold/`): consolidación **extractiva** (no resume ni responde) → `knowledge_units.jsonl`, facts,
   entities, conflicts, `faq_seeds.jsonl`, `context_8000/32000.*`, topics. Cada unidad conserva su cita.
4. **Tareas** (`tasks.py` + `retrieval.py` + `llm.py`): Q&A, Resumen y FAQ con LangChain sobre el oro.
   `retrieval.py` es BM25 simplificado léxico (sin embeddings todavía; embeddings/RAG con memoria son Fase 2).
   Prompts versionados en `prompts/{qa,summary,faq}.md` (secciones parseadas por `tasks.load_prompt`),
   parámetros en `config/tasks.toml`, modelo DeepSeek (cliente OpenAI-compatible) en `config/llm.toml`.
   Las citas son etiquetas `[U#]` que se validan contra la evidencia seleccionada; sin evidencia el resultado
   es `status=fallback` con `citations=[]` — nunca se inventa contenido. `PML_GOLD_DIR` cambia el directorio oro.
5. **API + Web** (`api.py`, `api_models.py`, `showcase.py`, `app_metrics.py`; `web/`): FastAPI expone
   `/api/health`, `/api/ask`, `/api/summary`, `/api/faq`, `/api/showcase` y sirve `web/dist` (SPA React 19 +
   Vite + TS). Cada request elige `mode`: `demo` usa `build_scripted_model` (sin red ni clave) y si no,
   DeepSeek. La clave nunca sale del servidor y la app **no escribe** en `data/` ni en el repo.

Modelos falsos para pruebas: `build_scripted_model` (tasks) y `build_fake_model` (llm); las pruebas unitarias y de
contrato deben pasar sin red. Helpers compartidos en `tests/{silver,gold,tasks}_helpers.py`.

## Convenciones

- Proceso por feature con Spec Kit: `specs/NNN-nombre/` (spec, plan, tasks, quickstart); ADRs en
  `docs/decisions/`. Cambios de prompts se registran en `docs/prompt_log.md`.
- Cambios arquitectónicos, tecnológicos o de proceso actualizan `CONSTITUTION.md` en el mismo commit.
- Ramas + PR (no push a `main`), Conventional Commits; UI, comentarios y commits en español, identificadores
  en inglés. Ruff con `line-length = 100`.
- **Autoría** (`CONSTITUTION.md` §4.3, ADR 0017): solo `jasonCastano` y `Robertto48` hacen commits, PRs, tags
  y releases. Claude Code prepara los cambios y no hace `git commit`, `git push` ni `gh pr create` salvo
  autorización explícita del integrante; nunca añade `Co-authored-by`, `Signed-off-by` ni firmas
  «Generated with …» (el hook `commit-msg` y el job `autoria` del CI lo rechazan).
- `data/bronze|silver|gold` van por Git LFS; no regeneres ni reescribas capas salvo que se pida.
- Arquitectura interactiva: `docs/arquitectura.html` generada desde `docs/arquitectura.json`.
