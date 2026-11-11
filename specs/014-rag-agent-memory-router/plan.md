# Implementation Plan: Agente RAG con memoria y enrutador (Módulo 2)

**Branch**: `014-rag-agent-memory-router` | **Date**: 2026-11-10 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/014-rag-agent-memory-router/spec.md`

**Autor del plan**: Roberto José Guerrero

**Note**: Este plan **no toca `main`**: todo se implementa en ramas derivadas de `014-rag-agent-memory-router` y
se publica por PR con aprobación cruzada (§4.2 de la constitución).

## Summary

Convertir el Q&A de una sola pregunta en una **conversación con memoria** que decide, turno a turno, de dónde
sacar la evidencia. Una **puerta de decisión** clasifica cada mensaje (directo, documental, estructurado, fuera
de alcance o aclaración); la ruta documental reutiliza el `HybridRetriever` de la spec 013 como herramienta, y la
ruta estructurada consulta en solo lectura una **tabla SQLite derivada del oro** (`entities.jsonl` +
`facts.jsonl`) con cita por fila. Se implementan dos variantes comparables, **cadena fija** (recupera siempre) y
**agente** (`langchain.agents.create_agent` con las fuentes como `@tool`), sobre un grafo LangGraph con
**checkpointer SQLite por `thread_id`**, recorte/resumen de hilos largos, **aislamiento XML** del contexto con
detector de instrucciones embebidas y **Human-in-the-Loop** (`HumanInTheLoopMiddleware` / `interrupt()` +
`Command(resume=...)`) para las acciones de escritura. La evaluación de la spec 013 se amplía con Recall@10,
nDCG@10, precisión del enrutador, abstención fuera de corpus, latencia con calentamiento y llamadas al modelo;
la fidelidad de la generación se mide con Ragas y las trazas con LangSmith, ambos opcionales y apagados en CI.

## Technical Context

**Language/Version**: Python 3.14 (gestionado con `uv`); TypeScript 5 + React 19 en `web/`.

**Primary Dependencies**: se reutilizan `langchain` 1.4, `langchain-core`, `langchain-openai` (DeepSeek),
`fastembed`, `numpy` y FastAPI. `langgraph` 1.2 ya llega como dependencia transitiva de `langchain`; se declara
explícita junto con **`langgraph-checkpoint-sqlite`** (checkpointer persistente). Grupo opcional
`[project.optional-dependencies].eval` con **`ragas`**; **LangSmith** se activa solo con variables de entorno
(`LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY`). Ver [research.md](./research.md) §1–§3.

**Storage**:

- Índice semántico (spec 013): `data/module2/index/` — vista derivada, sin cambios de formato salvo el manifiesto
  (FR-003).
- Tabla estructurada: `data/module2/structured/structured.sqlite3` + `manifest.json` — **vista derivada** del oro,
  construida por CLI, no versionada; la app la abre con `mode=ro` y `PRAGMA query_only=ON`.
- Estado conversacional: checkpointer y Store en `MANUELITA_STATE_DIR` (por defecto
  `%LOCALAPPDATA%/manuelita-rag/` o `~/.local/state/manuelita-rag/`), **fuera del repositorio y de `data/`**
  (regla dura de AGENTS.md: la app no escribe en el repo).
- Conjunto de evaluación etiquetado: `tests/fixtures/rag/module2_queries.jsonl` (versionado, FR-019).

**Testing**: `pytest` (AAA) con `HashEmbedder` y modelo guionado (`FakeMessagesListChatModel`) para todo lo
nuevo; checkpointer `InMemorySaver` en unitarias y SQLite temporal (`tmp_path`) en integración; prueba
adversarial con documento malicioso en `tests/fixtures/rag/malicious/`; Vitest para la vista de chat y
Playwright E2E en modo demo. Ragas y LangSmith se marcan `@pytest.mark.network` y se omiten en CI.

**Target Platform**: API FastAPI local + frontend React (Vite); CLI para construir la tabla estructurada y
ejecutar la evaluación. Windows 11 y Linux (CI de GitHub).

**Project Type**: proyecto único — biblioteca `src/proyecto_modelos_lenguaje/` + API + CLI + frontend `web/`.

**Performance Goals**: respuesta conversacional típica < 10 s con DeepSeek (SC-007); enrutador ≤ 1 llamada al
modelo (0 en saludos y fuera de alcance detectados por reglas); búsqueda híbrida sin regresión frente a la spec
013 (p95 medido con calentamiento); agente con `recursion_limit` que acota a ≤ 3 búsquedas por turno.

**Constraints**: modo demostración completo sin red ni clave (FR-021); la suite no descarga modelos ni llama a
APIs; solo lectura sobre el oro y la tabla estructurada; ningún dato personal sensible en memoria (FR-010); el
contexto recuperado nunca se concatena como instrucción (Principio IV).

**Scale/Scope**: 15.211 unidades indexadas; 15 entidades y 381 hechos del oro para la tabla estructurada; 5
rutas del enrutador; 2 variantes (cadena y agente); 30 consultas etiquetadas con ruta esperada (más las 40 de la
spec 013 para retrieval); 4 endpoints nuevos y 1 vista de chat.

Sin `NEEDS CLARIFICATION` pendientes: las decisiones abiertas se resolvieron en [research.md](./research.md).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Fuente: `CONSTITUTION.md` v1.3.0, §5 Fase 2 (reglas 1–14), principios I–IX y reglas duras de `AGENTS.md`.

| Regla | Cumplimiento | Evidencia en el plan |
|-------|--------------|----------------------|
| F2-1 Embeddings con evidencia MTEB-es | PASS (acción) | Se reutiliza e5-small; la ADR 0014 se amplía con la evidencia MTEB Retrieval/español (research §4, FR-004). |
| F2-2 Base vectorial embebida, persistente, vista derivada, expuesta como retriever | PASS | `HybridRetriever` envuelto en `@tool search_documents`; índice reconstruible y no versionado. |
| F2-3 Chunking medido y documentado | PASS (acción) | El manifiesto registra tamaño y solapamiento (FR-003); búsqueda exacta (sin ANN) justificada en research §5. |
| F2-4 Denso vs. léxico vs. híbrido | PASS | Evaluación por modo heredada de 013, ampliada a @10 (FR-006). |
| F2-5 Memoria corta con checkpointer persistente y recorte | PASS | `SqliteSaver` por `thread_id` + `SummarizationMiddleware`/recorte (research §2). |
| F2-6 Memoria larga opcional con retención y borrado | PASS (P3) | Store SQLite por namespace de usuario, TTL 30 días, borrado vía HITL; `docs/memoria.md`. |
| F2-7 Enrutador con confianza y origen estructurado de solo lectura | PASS | `RouteDecision` tipada; tabla SQLite `mode=ro`; aclaración con confianza < 0,6. |
| F2-8 RAG Chain vs. RAG Agent | PASS | Dos variantes sobre las mismas herramientas; comparación de calidad, latencia y llamadas. |
| F2-9 Blindaje XML + prueba maliciosa + HITL | PASS | `<documento>` con escape, detector de instrucciones, fixture maliciosa que DEBE pasar, HITL en escrituras. |
| F2-10 20–30 consultas, Recall@10, nDCG@10, MRR, router, citas, latencia, llamadas | PASS | `module2_queries.jsonl` (30) + extensión de `rag/evaluate.py`. |
| F2-11 Ragas + LangSmith sin romper offline | PASS | Grupo opcional `eval`; LangSmith por variables de entorno; pruebas de red omitidas en CI. |
| F2-12 App muestra ruta, fragmentos, respuesta, fuentes e historial; demo sin red | PASS | Contrato `chat-api.md`; vista de chat; modo demo guionado. |
| F2-13 Prompts nuevos versionados | PASS | `prompts/router.md`, `prompts/agent.md`, `prompts/memory_summary.md` + `docs/prompt_log.md`. |
| F2-14 Informe, demo y tag `v0.2.0-modulo2` | PASS (cierre) | Tareas de cierre en `tasks.md`; tag tras el merge. |
| I Integridad y autoría / IX Transparencia | PASS | Autoría y decisiones registradas en ADR 0016 (agente) y prompt log. |
| II Reproducibilidad (`uv`, sin `pip`) | PASS | Dependencias vía `uv add`; `uv.lock` versionado. |
| III Procedencia | PASS | Cada fila estructurada conserva `unit_id` y `evidence[].url`. |
| IV Generación anclada y citas | PASS | Solo se responde con fragmentos o filas recuperadas; fallback declarado. |
| V Evaluación antes de afirmar | PASS | SC-001…SC-009 medidos por el evaluador antes de documentar resultados. |
| VII Simplicidad | PASS | SQLite embebido, sin servicios nuevos; herramientas tipadas en vez de SQL libre. |
| AGENTS.md: la app no escribe en `data/` ni en el repo | PASS | Estado en `MANUELITA_STATE_DIR`; vistas derivadas solo por CLI. |
| Puerta de la Fase 1 cerrada antes de implementar | PENDIENTE (bloquea `/speckit-implement`, no el plan) | M1-08 en curso en `feat/m1-08-evaluacion-modulo1`; tag `v0.1.0-modulo1` tras su merge. |

**Resultado**: sin violaciones. La única puerta pendiente (Fase 1) no afecta al diseño; se verifica antes de
implementar.

**Re-evaluación post-diseño (Fase 1)**: el modelo de datos y los contratos mantienen todas las filas en PASS. El
diseño añade una ADR (0016) y un documento (`docs/memoria.md`) ya exigidos por §9; no introduce servicios
externos ni escrituras en el repositorio.

## Project Structure

### Documentation (this feature)

```text
specs/014-rag-agent-memory-router/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, validaciones y estados
├── quickstart.md        # Fase 1: validación extremo a extremo
├── contracts/
│   ├── chat-api.md                      # Endpoints de conversación, reanudación y memoria
│   ├── route-decision.schema.json       # Salida tipada del enrutador
│   ├── structured-manifest.schema.json  # Manifiesto de la tabla estructurada
│   └── eval-query.schema.json           # Línea del conjunto etiquetado
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit-tasks; no lo crea este comando)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── rag/                         # spec 013 (se amplía, no se reescribe)
│   ├── index.py                 # + chunk_size/overlap en el manifiesto (FR-003)
│   ├── hybrid.py                # + filtro por metadatos (FR-005)
│   └── evaluate.py              # + Recall@10, nDCG@10, router, abstención, warm-up, llamadas (FR-020)
├── agent/                       # NUEVO
│   ├── __init__.py
│   ├── __main__.py              # CLI: chat, build-structured, evaluate-agent
│   ├── config.py                # config/agent.toml tipado
│   ├── router.py                # reglas + clasificador LLM → RouteDecision
│   ├── structured.py            # construcción y consulta solo-lectura de la tabla SQLite
│   ├── tools.py                 # @tool search_documents, query_structured, forget_memory
│   ├── guard.py                 # aislamiento XML y detector de instrucciones embebidas
│   ├── memory.py                # checkpointer, Store, recorte/resumen, filtro de datos sensibles
│   ├── graph.py                 # variantes chain y agent (create_agent + middleware HITL)
│   └── demo.py                  # modelo y embeddings guionados para modo demo
├── api.py                       # + /api/chat, /api/threads/{id}, /api/threads/{id}/resume, /api/memory
└── api_models.py                # + modelos Pydantic del contrato chat-api

config/agent.toml                # umbrales, límites, rutas, TTL de memoria
prompts/router.md | agent.md | memory_summary.md

web/src/
├── components/ChatView.tsx      # conversación, ruta, fragmentos, fuentes, historial
├── components/ApprovalCard.tsx  # aprobar / editar / rechazar acciones pendientes
└── api/chat.ts

tests/
├── unit/agent/                  # router, guard, structured, memory, tools
├── integration/agent/           # grafo chain/agent con checkpointer SQLite temporal
├── contract/test_chat_api.py
└── fixtures/rag/{module2_queries.jsonl, malicious/}

docs/decisions/0016-rag-agent-langgraph.md
docs/memoria.md
docs/evaluacion_modulo2.md       # regenerado con las nuevas métricas
```

**Structure Decision**: se mantiene el proyecto único existente. La lógica nueva vive en un subpaquete
`agent/` que **depende** de `rag/` (spec 013) y de `tasks.py`, sin modificarlos más allá de los puntos
señalados. La API y la web solo consumen `agent.graph`.

## Fases de implementación (orientativas para `/speckit-tasks`)

1. **Fundaciones**: dependencias, `config/agent.toml`, `MANUELITA_STATE_DIR`, modo demo.
2. **US3 primero (medir)**: conjunto de 30 consultas con ruta esperada, Recall@10/nDCG@10, abstención y
   warm-up; reporte base antes de tocar el agente.
3. **US2**: tabla estructurada + enrutador + herramienta `query_structured`.
4. **US1**: grafo con memoria por `thread_id`, variante chain y agent, endpoint `/api/chat` y vista de chat.
5. **US4**: guard XML, fixture maliciosa, HITL con reanudación tras reinicio.
6. **US5 (P3)**: Store de preferencias, TTL y borrado.
7. **Cierre**: Ragas + LangSmith, ADR 0016, `docs/memoria.md`, prompt log, informe, demo y tag.

## Complexity Tracking

Sin violaciones de la constitución; no aplica.
