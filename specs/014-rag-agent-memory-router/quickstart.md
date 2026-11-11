# Quickstart: validar el agente RAG con memoria y enrutador

**Feature**: `014-rag-agent-memory-router` | **Fecha**: 2026-11-10 | **Autor**: Roberto José Guerrero

Guía de validación extremo a extremo. Los comandos `agent …` y los endpoints se crean en la implementación; las
formas de entrada y salida están en [contracts/](./contracts/) y [data-model.md](./data-model.md).

## Prerrequisitos

```bash
make dev                                   # uv sync + npm ci + hooks
git lfs pull                               # data/gold
uv run python -m proyecto_modelos_lenguaje.rag index build   # índice semántico (spec 013), una vez
uv run python -m proyecto_modelos_lenguaje.agent build-structured   # tabla SQLite derivada del oro
```

- Modo real: `DEEPSEEK_API_KEY` en `.env`. Modo demo: sin clave ni red.
- Opcional: `uv sync --extra eval` (Ragas) y `LANGSMITH_TRACING=true` + `LANGSMITH_API_KEY` (trazas).
- Estado conversacional: `MANUELITA_STATE_DIR` (por defecto fuera del repositorio).

## Escenario 1 — Suite offline (CI)

```bash
make check
```

**Esperado**: todas las pruebas pasan sin red; se incluyen router, guard, tabla estructurada, memoria con
checkpointer temporal, HITL y la prueba adversarial con documento malicioso.

## Escenario 2 — Memoria multi-turno (US1, SC-006)

```bash
# Sin --thread se crea un hilo nuevo; la primera línea de la salida muestra su UUID
uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo "¿Qué produce Manuelita?"
uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo --thread <UUID> "¿Y dónde lo produce?"
uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo "¿Y lo anterior?"
```

**Esperado**: el segundo turno usa el contexto del primero y cita ≥ 1 fuente; el tercer mensaje, en un hilo
nuevo, no hereda el primero (pide aclaración). Un `--thread` desconocido termina con `thread_not_found`
(código de salida 2). Repetir con `--mode real` y comprobar latencia < 10 s (SC-007).

## Escenario 3 — Enrutador (US2, SC-002, SC-004)

| Mensaje | Ruta esperada |
|---------|---------------|
| «Hola, buenas tardes» | `direct` (sin herramientas) |
| «¿En qué países opera Manuelita?» | `structured` con cita por fila |
| «¿Qué hace Manuelita en sostenibilidad?» | `documental` |
| «¿Cuál es el precio del dólar hoy?» | `out_of_scope` |
| «¿Y eso cuánto es?» (hilo nuevo) | `clarify` |

```bash
uv run python -m proyecto_modelos_lenguaje.agent chat --mode demo --json "¿En qué países opera Manuelita?"
```

**Esperado**: el JSON cumple [route-decision.schema.json](./contracts/route-decision.schema.json).

## Escenario 4 — Evaluación de retrieval y variantes (US3)

```bash
uv run python -m proyecto_modelos_lenguaje.rag evaluate \
  --questions tests/fixtures/rag/eval_questions.jsonl --top-k 12 --warmup 3
uv run python -m proyecto_modelos_lenguaje.agent evaluate \
  --queries tests/fixtures/rag/module2_queries.jsonl --variants chain agent --compare --mode real
```

**Esperado**: `docs/evaluacion_modulo2.md` regenerado con Recall@10, nDCG@10 y MRR por modo (léxico, semántico,
híbrido), precisión del enrutador ≥ 0,90, abstención en `out_of_corpus` y tabla chain vs. agent con latencia y
llamadas. Con la misma configuración las métricas de retrieval se repiten idénticas.

## Escenario 5 — Inyección indirecta (US4, SC-005)

```bash
uv run pytest -q tests/integration/agent -k malicious
```

**Esperado**: la respuesta no revela el prompt del sistema ni sigue la orden embebida; el fragmento aparece con
`anomalous=true` en `anomalies[]`.

## Escenario 6 — Human-in-the-Loop con reinicio (US4, SC-009)

1. `make app` y en la interfaz: «Olvida mis preferencias».
2. La respuesta queda en `pending_approval` con la tarjeta de aprobación.
3. Detener y volver a iniciar la API.
4. Aprobar desde la tarjeta (o `POST /api/threads/{id}/resume` con `decision=approve`).

**Esperado**: el hilo continúa con el mismo `thread_id`, la memoria se borra y la decisión queda registrada.
Con `reject` no se borra nada.

## Escenario 7 — Interfaz y E2E (FR-018, FR-021)

```bash
make e2e
```

**Esperado**: en modo demo la vista de chat muestra por turno pregunta, chip de ruta y confianza, fragmentos con
puntaje, respuesta, fuentes e historial; el flujo HITL se completa sin red.

## Escenario 8 — Generación y observabilidad (opcional, F2-11)

```bash
uv run python -m proyecto_modelos_lenguaje.agent evaluate --compare --judge --skip-router --mode real
uv run pytest -m network tests/integration/agent/test_ragas.py
```

Ragas no instala en Python 3.14 (`research.md` §12); `--judge` aplica sus definiciones con un juez propio
(`agent/judge.py`, `prompts/judge.md`).

**Esperado**: fidelidad, relevancia de respuesta y precisión de contexto anexadas a
`docs/evaluacion_modulo2.md` con fecha y modelo juez; si `LANGSMITH_TRACING=true`, las trazas aparecen en el
proyecto de LangSmith sin claves en los inputs.
