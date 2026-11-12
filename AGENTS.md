# AGENTS — RAG Ingenio Manuelita

> Contexto para asistentes LLM (OpenCode, Claude Code, Cursor, Copilot CLI).
> La verdad técnica central vive en [`CONSTITUTION.md`](./CONSTITUTION.md): léela antes de operar.

## Proyecto

Sistema Q&A y RAG sobre información pública de Ingenio Manuelita. Combina un pipeline medallion
(bronce → plata → oro), tareas LangChain con DeepSeek y una experiencia web React + FastAPI de solo lectura.

- **Repositorio**: https://github.com/jasonCastano/proyecto_modelos_lenguaje
- **Mantenedor**: Jason Alejandro Castaño (`@jasonCastano`)
- **Paquete**: `src/proyecto_modelos_lenguaje/`
- **Datos**: `data/bronze`, `data/silver` y `data/gold` versionados por Git LFS; la cuarentena no.
- **Arquitectura interactiva**: `docs/arquitectura.html` (fuente `docs/arquitectura.json`).

## Flujo diario

```bash
git status
make check
git add -A
git commit -m "tipo: mensaje descriptivo"
git push
```

Usa [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`,
`refactor:`, `style:`, `test:`, `chore:`. No hagas push directo a `main`: abre un PR.

## Comandos

```bash
make help      # objetivos disponibles
make dev       # uv sync + npm ci + hooks
make check     # Python + pruebas/build web
make lint      # Ruff
make format    # Ruff format
make test      # pytest
make app       # build web + API local
make e2e       # Playwright
make build     # web + sdist + wheel
```

Comandos directos:

```bash
uv run uvicorn proyecto_modelos_lenguaje.api:app --reload --port 8000
cd web && npm run dev
uv run python -m proyecto_modelos_lenguaje.llm --check
make app
make e2e
```

Agente conversacional (Módulo 2, spec 014; estado en `MANUELITA_STATE_DIR`, fuera del repo):

```bash
uv run python -m proyecto_modelos_lenguaje.agent build-structured            # tabla SQLite desde el oro
uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo "¿Qué produce Manuelita?"
uv run python -m proyecto_modelos_lenguaje.agent chat --mode real --variant agent --thread <UUID> "¿Y dónde?"
uv run python -m proyecto_modelos_lenguaje.agent evaluate --mode real                    # enrutador
uv run python -m proyecto_modelos_lenguaje.agent evaluate --mode real --compare --judge --skip-router
```

Regla del agente: lectura automática, escritura con aprobación (`save_preference`, `forget_memory`,
`export_conversation` esperan `POST /api/threads/{id}/resume`).

## Reglas duras

- Toda gestión de entornos y dependencias pasa por `uv`. Prohibido `pip` y `requirements.txt`.
- `uv.lock` se versiona; no se edita a mano.
- No se versionan claves, `.env`, cuarentena, capturas temporales ni artefactos de build.
- La app no escribe en `data/` ni en el repositorio.
- Toda respuesta factual cita fuente o declara fallo de evidencia.
- Actualiza `CONSTITUTION.md` en el mismo commit ante cambios arquitectónicos, tecnológicos o de proceso.
- Ejecuta `make check` antes de commitear; CI corre lo mismo.
- **Autoría**: los commits son de `jasonCastano` (Jason Alejandro Castaño) o `Robertto48` (Roberto José
  Guerrero Criollo), o de un bot autorizado (`dependabot[bot]`). Nunca añadas `Co-authored-by` de un
  asistente de IA ni firmas «Generated with …» en commits, PRs, tags o releases (`CONSTITUTION.md` §4.3).

## Estructura

- `src/proyecto_modelos_lenguaje/` — API FastAPI, pipeline, retrieval, tareas LangChain y branding.
- `web/` — frontend React + Vite + TypeScript.
- `scripts/` — entradas operativas.
- `config/` — fuentes, capas, LLM, prompts y parámetros.
- `specs/` — especificaciones, planes y tareas por feature.
- `docs/` — alcance, ficha de datos, ADRs, arquitectura y bitácoras.
- `tests/` — unitarias, integración, contrato y visuales opcionales.

## Búsqueda de código: `tgrep`

Si `tgrep` está instalado, úsalo antes que `grep`/`find`:

```bash
tgrep -- "patrón" .
tgrep -F -- "símbolo" .
tgrep -t py -- "def " .
tgrep -g "src/**" -- "kw" .
tgrep index .
```

Regla de OpenCode: [`.opencode/rules/tgrep.md`](./.opencode/rules/tgrep.md).

## Estilo

- Ruff, `line-length = 100`, comillas dobles.
- Anotaciones de tipo en funciones y métodos públicos.
- UI, comentarios y commits en español; identificadores en inglés.
- Pruebas con `pytest` y patrón AAA.
