# AGENTS — RAG Ingenio Manuelita

> Contexto para asistentes LLM (OpenCode, Claude Code, Cursor, Copilot CLI).
> La verdad técnica central vive en [`CONSTITUTION.md`](./CONSTITUTION.md): léela antes de operar.

## Proyecto

Sistema Q&A y RAG sobre información pública de Ingenio Manuelita. Combina un pipeline medallion
(bronce → plata → oro), tareas LangChain con Ollama local y una app Streamlit de solo lectura.

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
make dev       # uv sync + hooks de pre-commit
make check     # lint + formato + pruebas
make lint      # Ruff
make format    # Ruff format
make test      # pytest
make app       # Streamlit local
make audit     # auditoría visual de Métricas (requiere app en :8501)
make build     # sdist + wheel
```

Comandos directos:

```bash
uv run streamlit run app.py
PML_DEMO=1 uv run streamlit run app.py
uv run python -m proyecto_modelos_lenguaje.llm --check
uv run python scripts/audit_metrics_layout.py --url http://localhost:8501 --output artifacts/metrics-layout/final
```

## Reglas duras

- Toda gestión de entornos y dependencias pasa por `uv`. Prohibido `pip` y `requirements.txt`.
- `uv.lock` se versiona; no se edita a mano.
- No se versionan claves, `.env`, cuarentena, capturas temporales ni artefactos de build.
- La app no escribe en `data/` ni en el repositorio.
- Toda respuesta factual cita fuente o declara fallo de evidencia.
- Actualiza `CONSTITUTION.md` en el mismo commit ante cambios arquitectónicos, tecnológicos o de proceso.
- Ejecuta `make check` antes de commitear; CI corre lo mismo.

## Estructura

- `src/proyecto_modelos_lenguaje/` — pipeline, retrieval, tareas LangChain y branding.
- `app.py` — app Streamlit (Consulta, Resumen, FAQ, Métricas).
- `scripts/` — entradas operativas y auditoría visual.
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
