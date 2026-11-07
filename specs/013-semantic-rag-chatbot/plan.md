# Implementation Plan: Chatbot con recuperación semántica (RAG)

**Branch**: `013-semantic-rag-chatbot` | **Date**: 2026-11-06 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-semantic-rag-chatbot/spec.md`

**Note**: Este plan **no toca `main`**: todo se implementa en la rama `013-semantic-rag-chatbot` y se publica por PR para revisión.

## Summary

Añadir recuperación semántica al chatbot del Módulo 2: embeber las unidades de oro con un modelo multilingüe
local, persistir el índice como artefacto reproducible y combinar esa búsqueda con la léxica existente. La
respuesta sigue generándose con el proveedor actual (DeepSeek) pero recibe **solo los fragmentos
recuperados**, y la interfaz muestra qué fragmento sustenta cada cita. La decisión se valida con Recall@k y
MRR contra la línea base del Módulo 1.

## Technical Context

**Language/Version**: Python 3.14 (gestionado con `uv`).

**Primary Dependencies**: se añade `fastembed` (ONNX Runtime, sin PyTorch) y `numpy`; se reutiliza
`langchain`/`langchain-openai`, `retrieval.py` y las tareas existentes. No se añade base vectorial como
servicio: el índice se guarda en `numpy` + `sqlite3`.

**Storage**: índice en `data/module2/index/` (ignorado por Git): matriz de vectores `.npy`, metadatos
`index.sqlite3` y `manifest.json`. Los datos de origen (`data/gold/`) se leen en solo lectura.

**Testing**: `pytest` con un **embedder falso determinista** (vectores derivados de hash, sin descarga ni
red) y un índice de prueba pequeño en `tests/fixtures/`. La evaluación real se ejecuta a mano con el modelo
verdadero.

**Target Platform**: API FastAPI local + frontend React; CLI de indexación y evaluación.

**Project Type**: proyecto único: biblioteca + API + CLI + frontend.

**Performance Goals**: búsqueda semántica sobre 15.211 unidades en < 100 ms; construcción del índice una vez
(< 5 min en CPU); respuesta extremo a extremo sin superar en 20% el Módulo 1.

**Constraints**: sin escrituras en las capas medallion; índice no versionado; modo demostración sin red; la
suite no descarga modelos; el corpus no se envía a terceros para embeber.

**Scale/Scope**: 15.211 unidades, 384 dimensiones (modelo pequeño), ~23 MB de matriz, 3 modos de
recuperación (semántica, léxica, híbrida) y 5 vistas afectadas de la API.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla de la Fase 2 | Cumplimiento | Evidencia en el plan |
|--------------------|--------------|----------------------|
| Embeddings multilingües justificados | PASS | Modelo pequeño multilingüe local; justificación por calidad, costo (cero por consulta) y latencia (§research). |
| Dimensión, normalización y límite de tokens registrados | PASS | `manifest.json` y `config/retrieval.toml` guardan modelo, dimensión, `normalize`, límite y fecha. |
| Base vectorial con persistencia reproducible | PASS | Matriz `.npy` + SQLite con manifiesto y comando de reconstrucción idempotente. |
| Chunking definido y documentado | PASS | Se reutilizan las unidades de oro como fragmentos (ya citables); solo se trocean las que exceden el límite. |
| Recall@k, MRR y calidad de citas | PASS | `evaluate` calcula Recall@k y MRR por modo y compara con la línea base léxica. |
| RAG solo con fragmentos recuperados | PASS | El contexto se construye únicamente con la selección híbrida; fallback si no hay evidencia. |
| Memoria conversacional definida | PASS (fuera de alcance) | Declarada fuera de alcance en la especificación. |
| App muestra pregunta, fragmentos, respuesta y fuentes | PASS | Nuevo bloque de trazabilidad en `/api/ask` y en la vista de respuesta. |
| Evaluación ampliada e informe | PASS | Conjunto de evaluación del Módulo 2 y `docs/evaluacion_modulo2.md`. |
| Métricas de recuperación y fidelidad | PASS | Recall@k y MRR por modo; fidelidad medida como cobertura y validez de citas más revisión manual de una muestra. |
| Informe, demo y tag `v0.2.0-modulo2` | PASS | Informe actualizado, guion de demo ampliado y tag creado por el propietario tras el merge del PR. |
| Integridad medallion y secretos | PASS | Solo lectura de oro; sin claves nuevas; índice fuera de Git. |

**Resultado**: sin violaciones. No se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/013-semantic-rag-chatbot/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades y validaciones
├── quickstart.md        # Fase 1: validación end-to-end
├── contracts/
│   ├── index-manifest.schema.json
│   └── retrieval-trace.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
config/
└── retrieval.toml           # modelo, dimensión, top-k, umbral, pesos y ruta del índice

src/proyecto_modelos_lenguaje/rag/
├── __init__.py
├── embeddings.py            # embedder real (fastembed) y embedder falso determinista
├── index.py                 # build/load/verify del índice + manifiesto
├── hybrid.py                # fusión semántica + léxica, umbral, deduplicación
└── evaluate.py              # Recall@k, MRR y comparación con la línea base

src/proyecto_modelos_lenguaje/
├── retrieval.py             # sin cambios de contrato; se reutiliza para el modo léxico
├── tasks.py                 # acepta la selección híbrida como evidencia
├── api.py                   # /api/ask devuelve la traza de recuperación
└── api_models.py            # modelos de la traza

web/src/                     # bloque "fragmentos recuperados" en la respuesta

tests/
├── unit/                    # test_rag_embeddings.py, test_rag_index.py, test_rag_hybrid.py, test_rag_evaluate.py
├── contract/                # test_rag_contract.py
├── integration/             # test_rag_api.py
└── fixtures/rag/            # índice de prueba (50 unidades) y embedder falso
```

**Structure Decision**: se crea un paquete `rag/` separado para no engordar `retrieval.py`, que queda como
la recuperación léxica que ya funciona. `tasks.py` no cambia su contrato: recibe una selección de evidencia
igual que hoy.

## Complexity Tracking

Sin violaciones de la constitución. No se requiere justificación adicional.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. `fastembed` (ONNX) con un modelo multilingüe pequeño, sin PyTorch, para no repetir el problema de espacio.
2. Índice en `numpy` + SQLite en lugar de Chroma o FAISS: 15k vectores caben en memoria y el artefacto es
   inspeccionable.
3. Se reutilizan las unidades de oro como fragmentos; solo se trocean las que exceden el límite del modelo.
4. Fusión híbrida con umbral de similitud y respaldo léxico.
5. Embedder falso determinista para la suite; el modelo real solo se usa al construir el índice y evaluar.
6. Métricas Recall@k y MRR por modo, con informe en `docs/evaluacion_modulo2.md`.

## Phase 1 — Design & Contracts

### Data model

Ver [data-model.md](./data-model.md). Entidades: `EmbeddingProfile`, `VectorIndex`, `IndexManifest`,
`RetrievedFragment`, `RetrievalTrace`, `EvaluationRun`.

### Contracts

- [contracts/index-manifest.schema.json](./contracts/index-manifest.schema.json): manifiesto del índice.
- [contracts/retrieval-trace.md](./contracts/retrieval-trace.md): forma de la traza que expone `/api/ask` y
  comandos de índice/evaluación.

### Quickstart

Ver [quickstart.md](./quickstart.md). Escenarios: construir el índice, verificar, preguntar, comparar
modos, revisar fragmentos en la interfaz y operar en modo demostración.

### Re-evaluación post-diseño

| Regla de la Fase 2 | Resultado | Evidencia |
|--------------------|-----------|-----------|
| Embeddings justificados | PASS | Modelo, dimensión y costo en `config/retrieval.toml` y ADR 0014. |
| Persistencia reproducible | PASS | Comando `index build` idempotente + manifiesto con hash de la capa de oro. |
| Chunking documentado | PASS | Unidades de oro como fragmentos; troceo solo por límite del modelo. |
| Recuperación medida | PASS | `evaluate` con Recall@k y MRR por modo. |
| Fidelidad medida | PASS | Cobertura y validez de citas en el 100% de las respuestas más revisión manual de una muestra. |
| Informe, demo y tag | PASS | `docs/evaluacion_modulo2.md`, guion de demo y tag `v0.2.0-modulo2` tras el merge. |
| RAG con citas y fallback | PASS | Contrato de tareas intacto. |
| App con fragmentos | PASS | Traza en la respuesta y bloque en la UI. |

## Implementation Phases

### Fase A — Configuración y embeddings

1. Crear `config/retrieval.toml` con modelo, dimensión, `normalize`, límite de tokens, top-k, umbral, pesos y
   ruta del índice.
2. Implementar `embeddings.py` con el embedder real y el falso determinista.
3. Registrar el perfil de embedding (modelo, dimensión, normalización, fecha).

### Fase B — Índice

1. Implementar `index build` desde `data/gold/knowledge_units.jsonl`.
2. Persistir matriz `.npy`, metadatos SQLite y `manifest.json` con hash de la capa de oro.
3. Implementar `index verify` (modelo, dimensión, recuento, hash) e `index rebuild` idempotente.

### Fase C — Recuperación híbrida

1. Implementar búsqueda por similitud con normalización L2 y umbral.
2. Fusionar con `select_evidence` (léxica), deduplicar por `unit_id` y ordenar por score combinado.
3. Aplicar presupuesto de contexto y declarar los descartados con su motivo.

### Fase D — Integración con tareas y API

1. Permitir que las tareas reciban la selección híbrida sin cambiar su contrato.
2. Añadir la traza de recuperación a `/api/ask` y los modelos de la API.
3. Mostrar en la UI los fragmentos, su puntuación, su origen y los descartados.

### Fase E — Evaluación

1. Definir el conjunto de evaluación del Módulo 2 (preguntas + unidad esperada).
2. Implementar `evaluate` con Recall@k y MRR por modo.
3. Generar `docs/evaluacion_modulo2.md` con la comparación contra la línea base y el análisis de errores.

### Fase F — Pruebas y documentación

1. Unitarias con embedder falso: fusión, umbral, deduplicación, manifiesto.
2. Contrato: manifiesto y traza.
3. Integración: `/api/ask` con índice de prueba, sin red.
4. ADR 0014, README y prompt log.

## Testing Strategy

| Nivel | Qué cubre | Fixtures |
|-------|-----------|----------|
| Unitario | Embedder falso, similitud, umbral, fusión, deduplicación, manifiesto, métricas | `tests/unit/test_rag_*.py` |
| Contrato | `manifest.json` y traza de recuperación | `jsonschema` |
| Integración | `/api/ask` con índice de prueba y modo demo | `tests/fixtures/rag/` |
| Manual | Índice real con el modelo multilingüe y evaluación | quickstart |

**Regla**: la suite no descarga modelos ni usa red.

## Risks & Mitigations

| Riesgo | Mitigación |
|--------|------------|
| Descarga del modelo pesada | Modelo pequeño ONNX (sin PyTorch); descarga única y cacheada. |
| Índice desactualizado | Manifiesto con hash de la capa de oro; `index verify` lo detecta. |
| Peor precisión en cifras y nombres | Fusión híbrida con respaldo léxico y pruebas dedicadas. |
| Latencia de la búsqueda | Matriz en memoria y producto punto vectorizado; medición en la evaluación. |
| Costo de reindexar | Índice incremental por `unit_id` y hashes; reconstrucción completa solo si cambia el modelo. |
| Deriva de la calidad | Evaluación reproducible y comparación con la línea base en cada cambio de modelo. |
| Índice versionado por error | Ruta en `data/module2/` ignorada por Git y prueba que lo verifica. |

## Acceptance Mapping

| Requisito | Prueba / evidencia |
|-----------|--------------------|
| FR-001, FR-002 | `index build` + manifiesto |
| FR-003 | `index verify` con modelo/dimensión distintos |
| FR-004, FR-005 | Pruebas de fusión y deduplicación |
| FR-006 | Suite de contrato de tareas en verde |
| FR-007 | Contexto construido solo con la selección |
| FR-008 | Traza en `/api/ask` y bloque en la UI |
| FR-009 | `index build/verify/rebuild` sin tocar el origen |
| FR-010 | Prueba de modo demo con índice de prueba |
| FR-011 | Campo de origen (semántica, léxica, híbrida) |
| FR-012, FR-013 | Presupuesto, descartes y deduplicación |
| FR-014 | Pregunta en inglés recupera y responde en español |
| FR-015, FR-020 | `evaluate` y `docs/evaluacion_modulo2.md` |
| FR-016 | Embedder falso en la suite |
| FR-017 | ADR 0014 con la justificación |
| FR-018 | Índice fuera de Git; fixture pequeño versionado |
| FR-019 | Medición de latencia antes/después |
| SC-001…SC-010 | quickstart + evaluación |

## Next Steps

1. Ejecutar `/speckit.tasks` para generar el backlog.
2. Implementar Fase A y B y validar `index verify`.
3. Implementar Fase C y comparar con la línea base antes de tocar la UI.
