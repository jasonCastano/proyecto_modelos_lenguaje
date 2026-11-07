# Guion de demostración — 12 + 3 minutos

**Formato** (constitución §5 Fase 1, §8.2): 12 minutos de demostración en vivo + 3 de preguntas, **sin
diapositivas**, con la app, el repositorio y el IDE abiertos y el pipeline ejecutándose en vivo. Sirve para
la sustentación del Módulo 2 y reutiliza el recorrido del Módulo 1.

**Estado**: borrador redactado con asistencia de Claude Code (2026-11-07); pendiente de ensayo
cronometrado por ambos integrantes. Ajustar cuando se publique la rúbrica de la Entrega 2.

## 0. Preparación (antes de entrar a la sesión)

| Paso | Comando o acción | Comprobación |
|------|------------------|--------------|
| Entorno | `uv sync --frozen` y `cd web && npm ci` | Sin errores |
| Calidad | `make check` | Ruff, pytest, Vitest y build en verde |
| Clave | `uv run python -m proyecto_modelos_lenguaje.llm --check` | Modelo DeepSeek alcanzable |
| Índice semántico | `uv run python -m proyecto_modelos_lenguaje.rag index verify` | Manifiesto válido (si falla: `rag index build`) |
| App | `make app` → <http://127.0.0.1:8000> | Página carga y `/api/health` responde |
| Ventanas | Navegador (app), IDE (VS Code/Cursor/Antigravity) con el repo, terminal, GitHub (PRs y CI) | Fuente grande, notificaciones apagadas |

## 1. Recorrido cronometrado

| Tiempo | Bloque | Quién | Qué se muestra | Criterio que cubre |
|--------|--------|-------|----------------|--------------------|
| 0:00–1:00 | Problema y alcance | Jason | Hero de la app; `docs/alcance.md` (8 categorías, 40 preguntas) | Análisis de la empresa |
| 1:00–3:30 | Pipeline en vivo | Jason | `uv run python scripts/scrape_empresa.py --campaign <id> --limit 3 --dry-run --json`; robots/sitemap, métricas de URLs, páginas, tokens y descartes; `uv run pml silver status --json` y `uv run pml gold status --json` | Pipeline de scraping, UI y scraping visible |
| 3:30–6:30 | Consulta con citas | Roberto | Pregunta del alcance → respuesta con citas `[U#]`, fuentes abiertas, fragmentos recuperados con puntaje y modo (híbrido/semántico/léxico); pregunta sin evidencia → *fallback* | Q&A con cita, RAG del Módulo 2 |
| 6:30–8:00 | Resumen y FAQ | Roberto | Pestañas Resumen y FAQ; prompts versionados en `prompts/` y `docs/prompt_log.md` | Tareas LLM y prompt engineering |
| 8:00–9:30 | Evaluación | Ambos | `docs/evaluacion_modulo2.md` (léxica vs. semántica vs. híbrida); `docs/evaluacion_modulo1.md` (zero-shot vs. final) | Evaluación empírica |
| 9:30–11:00 | Repositorio e IDE | Jason | Estructura `src/`, `specs/`, `docs/decisions/`; un diff de un PR fusionado y la decisión que explica; CI verde; `CONSTITUTION.md` | Repositorio, PRs, commits, revisión en el IDE |
| 11:00–12:00 | Límites y siguiente fase | Roberto | Limitaciones honestas; ruta de la spec 014 (memoria, enrutador, HITL) | Documentación y honestidad |
| 12:00–15:00 | Preguntas | Ambos | Responder desde el código o la app, no de memoria | Sustentación |

## 2. Preguntas de demostración

Usar preguntas del banco aprobado (`docs/alcance.md`) para que la respuesta sea verificable:

- **Directa**: P07 «¿Qué productos y servicios ofrece Manuelita?».
- **Paráfrasis (gana la semántica)**: una del conjunto `tests/fixtures/rag/eval_questions.jsonl` de tipo
  `paraphrase` que el reporte del Módulo 2 marque como recuperada.
- **Sin evidencia**: P14 «¿Qué entrevistas del gerente están disponibles?» (esperado `X`).
- **Fuera de alcance**: «¿Cuál es la capital de Mongolia?» — mostrar qué hace el sistema hoy y declarar el
  límite si devuelve evidencia (hallazgo de la auditoría del 2026-11-07, Anexo F de la constitución).

## 3. Plan B

| Falla | Respuesta en vivo |
|-------|-------------------|
| Sin red o sin clave DeepSeek | Cambiar el selector a **modo demostración** (modelo guionado e índice de prueba); decirlo en voz alta |
| Índice semántico ausente | La app degrada a recuperación léxica y lo declara en la traza; mostrarlo como diseño, no como error |
| El scraping en vivo se bloquea | Usar `--dry-run` sobre una campaña ya registrada y mostrar el catálogo con `uv run pml ... status` |
| La app no levanta | `uv run uvicorn proyecto_modelos_lenguaje.api:app --port 8000` y revisar el log en la terminal |
| Pregunta inesperada sobre código | Abrir el archivo en el IDE y buscar con el buscador del editor; no improvisar cifras |

## 4. Lista de verificación del ensayo

- [ ] Ensayo cronometrado completo ≤ 12:00 (registrar fecha y tiempo real aquí).
- [ ] Ambos integrantes pueden ejecutar cada bloque sin leer el README.
- [ ] Las cifras que se dicen coinciden con `README.md`, `docs/data_card.md` y los reportes de evaluación.
- [ ] Ninguna clave, ruta absoluta ni `.env` aparece en pantalla.
- [ ] Tag de la entrega creado sobre un commit con CI verde.
