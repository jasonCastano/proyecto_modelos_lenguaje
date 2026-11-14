# Guion de demostración — 12 + 3 minutos

> **Reemplazado el 2026-11-14.** El guion vigente de la sustentación del Módulo 2 (casos, preparación con
> `make demo-prep`, plan B y reparto por integrante) está en [`rubrica_modulo2.md`](rubrica_modulo2.md) §5,
> como pidió la evaluación docente para no tener dos guiones contradictorios. Este archivo se conserva como
> referencia del recorrido del Módulo 1.

**Formato** (constitución §5 Fase 1, §8.2): 12 minutos de demostración en vivo + 3 de preguntas, **sin
diapositivas**, con la app, el repositorio y el IDE abiertos y el pipeline ejecutándose en vivo. Sirve para
la sustentación del Módulo 2 y reutiliza el recorrido del Módulo 1.

**Estado**: guion actualizado por Roberto José Guerrero el 2026-11-11 con el agente conversacional del
Módulo 2 (spec 014); pendiente de ensayo cronometrado por ambos integrantes. Ajustar cuando se publique la
rúbrica de la Entrega 2. La versión anterior (2026-11-07) fue redactada con asistencia de Claude Code.

## 0. Preparación (antes de entrar a la sesión)

| Paso | Comando o acción | Comprobación |
|------|------------------|--------------|
| Entorno | `uv sync --frozen` y `cd web && npm ci` | Sin errores |
| Calidad | `make check` | Ruff, pytest, Vitest y build en verde |
| Clave | `uv run python -m proyecto_modelos_lenguaje.llm --check` | Modelo DeepSeek alcanzable |
| Índice semántico | `uv run python -m proyecto_modelos_lenguaje.rag index verify` | Manifiesto válido (si falla: `rag index build`) |
| Tabla estructurada | `uv run python -m proyecto_modelos_lenguaje.agent build-structured` | 15 entidades, 381 hechos, 477 citas (si existe: código 2, sin cambios) |
| Estado limpio | `MANUELITA_STATE_DIR` apuntando a una carpeta vacía de demo | Sin hilos ni preferencias de ensayos anteriores |
| App | `make app` → <http://127.0.0.1:8000> | Página carga y `/api/health` responde |
| Ventanas | Navegador (app), IDE (VS Code/Cursor/Antigravity) con el repo, terminal, GitHub (PRs y CI) | Fuente grande, notificaciones apagadas |

## 1. Recorrido cronometrado

| Tiempo | Bloque | Quién | Qué se muestra | Criterio que cubre |
|--------|--------|-------|----------------|--------------------|
| 0:00–1:00 | Problema y alcance | Jason | Hero de la app; `docs/alcance.md` (8 categorías, 40 preguntas) | Análisis de la empresa |
| 1:00–3:30 | Pipeline en vivo | Jason | `uv run python scripts/scrape_empresa.py --campaign <id> --limit 3 --dry-run --json`; robots/sitemap, métricas de URLs, páginas, tokens y descartes; `uv run pml silver status --json` y `uv run pml gold status --json` | Pipeline de scraping, UI y scraping visible |
| 3:30–5:00 | Conversación con memoria | Roberto | Pestaña «Conversación», variante Cadena: «¿Qué produce Manuelita?» → «¿Y dónde lo produce?»; señalar el chip de ruta y confianza, los fragmentos con puntaje, las fuentes y las métricas del turno; «Nueva conversación» + «¿Y lo anterior?» → aclaración | Memoria multi-turno y RAG |
| 5:00–6:30 | Enrutador | Roberto | «Hola» (directa, 0 llamadas), «¿En qué países opera Manuelita?» (estructurada, filas `[F#]`), «¿Cuál es el precio del dólar hoy?» (fuera de alcance, sin buscar); abrir `prompts/router.md` | Enrutamiento documental vs. estructurado |
| 6:30–8:00 | Blindaje y aprobación humana | Roberto | Variante Agente: «Prefiero respuestas en viñetas» → tarjeta de aprobación → Aprobar; nueva conversación responde en viñetas; «Olvidar» → Rechazar; mostrar `tests/fixtures/rag/malicious/` y el aviso de fragmento anómalo | Inyección indirecta y HITL |
| 8:00–9:30 | Evaluación | Ambos | `docs/evaluacion_modulo2.md`: Recall@10/nDCG@10 por modo, enrutador 35/36, cadena vs. agente (citas, repreguntas, latencia, llamadas, juez) | Evaluación empírica |
| 9:30–11:00 | Repositorio e IDE | Jason | `src/proyecto_modelos_lenguaje/agent/graph.py` (los dos grafos), ADR 0016, PRs #44–#50 con CI verde, `CONSTITUTION.md` | Repositorio, PRs, commits, revisión en el IDE |
| 11:00–12:00 | Límites y siguiente fase | Roberto | Límites declarados en `docs/informe_modulo2.md` §5; Fase 3 (canal real y despliegue) | Documentación y honestidad |
| 12:00–15:00 | Preguntas | Ambos | Responder desde el código o la app, no de memoria | Sustentación |

## 2. Preguntas de demostración

Usar preguntas del banco aprobado (`docs/alcance.md`) para que la respuesta sea verificable:

- **Directa**: P07 «¿Qué productos y servicios ofrece Manuelita?».
- **Paráfrasis (gana la semántica)**: una del conjunto `tests/fixtures/rag/eval_questions.jsonl` de tipo
  `paraphrase` que el reporte del Módulo 2 marque como recuperada.
- **Sin evidencia**: P14 «¿Qué entrevistas del gerente están disponibles?» (esperado `X`).
- **Fuera de alcance**: «¿Cuál es el precio del dólar hoy?» — el enrutador responde sin buscar.
- **Repregunta elíptica**: «¿Cómo empezó la historia de Manuelita?» → «¿A quién le compró las haciendas?».
- **Escritura con aprobación**: «Prefiero respuestas en viñetas» y «Exporta la conversación».

## 3. Plan B

| Falla | Respuesta en vivo |
|-------|-------------------|
| Sin red o sin clave DeepSeek | Cambiar el selector a **modo demostración** (modelo guionado e índice de prueba); decirlo en voz alta |
| El agente tarda más de 10 s | Cambiar a la variante Cadena (una llamada menos por turno) y explicarlo con la tabla de la evaluación |
| Una acción queda pendiente al cambiar de pestaña | Volver a «Conversación»: el hilo se restaura desde el servidor con su tarjeta de aprobación |
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
