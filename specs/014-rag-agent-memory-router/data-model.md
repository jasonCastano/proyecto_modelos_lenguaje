# Data Model: Agente RAG con memoria y enrutador

**Feature**: `014-rag-agent-memory-router` | **Fecha**: 2026-11-10 | **Autor**: Roberto José Guerrero

Entidades nuevas o ampliadas respecto a la spec 013. `RetrievedFragment`, `RetrievalTrace` e `IndexManifest`
se reutilizan de `src/proyecto_modelos_lenguaje/rag/` y solo se listan sus cambios.

## 1. IndexManifest (ampliado, FR-003)

| Campo nuevo | Tipo | Regla |
|-------------|------|-------|
| `chunk_strategy` | `"unit" \| "unit+window"` | Obligatorio. |
| `chunk_size_tokens` | int | > 0 y ≤ límite del modelo (512). |
| `chunk_overlap_tokens` | int | 10–20 % de `chunk_size_tokens`. |

Un índice con manifiesto antiguo (sin estos campos) se reporta como `IndexInvalidError` con la acción
«reconstruir».

## 2. RetrievedFragment (ampliado)

| Campo nuevo | Tipo | Regla |
|-------------|------|-------|
| `anomalous` | bool | `true` si `guard.detect_instructions` encontró patrones imperativos (FR-016). |
| `anomaly_reasons` | list[str] | Vacía si `anomalous=false`. |

## 3. RouteDecision ([schema](./contracts/route-decision.schema.json))

| Campo | Tipo | Regla |
|-------|------|-------|
| `route` | enum `direct`, `documental`, `structured`, `out_of_scope`, `clarify` | Obligatorio. |
| `confidence` | float [0, 1] | Si < `router.min_confidence` (0,6) la ruta efectiva es `clarify`. |
| `reason` | str | ≤ 200 caracteres, en español. |
| `decided_by` | enum `rules`, `llm`, `demo` | Trazabilidad de la decisión. |
| `fallback_route` | enum o null | `documental` cuando `structured` no devolvió filas. |
| `alternative` | enum o null | Segunda ruta más probable. |

## 4. StructuredEntity y StructuredFact (tabla SQLite)

Base: `data/module2/structured/structured.sqlite3`, solo lectura en la app.

**`entities`**

| Columna | Tipo | Origen |
|---------|------|--------|
| `entity_id` (PK) | TEXT | `entities.jsonl.entity_id` |
| `canonical_name` | TEXT | idem |
| `aliases` | TEXT (JSON) | idem |
| `entity_type` | TEXT | `company`, `subsidiary`, `brand`, `certification`, `other` |

**`facts`**

| Columna | Tipo | Origen |
|---------|------|--------|
| `fact_id` (PK) | TEXT | `facts.jsonl.fact_id` |
| `subject_id` (FK → entities) | TEXT | idem |
| `subject_label` | TEXT | idem |
| `attribute` | TEXT | idem, normalizado a minúsculas |
| `value` / `value_normalized` | TEXT | idem |
| `unit` | TEXT null | idem |
| `year` | INT null | idem |
| `unit_id` | TEXT | unidad oro citable |
| `status` | TEXT | solo se cargan hechos con estado aceptado |

**`citations`**: `fact_id` (FK), `url`, `title`, `content_hash`, `authority` — una fila por evidencia.

**Validaciones**: toda fila de `facts` tiene ≥ 1 cita (FR-012); el constructor falla si el hash del oro no
coincide con el manifiesto; la conexión de la app usa `mode=ro` y `PRAGMA query_only=ON` (FR-013).

**StructuredManifest** ([schema](./contracts/structured-manifest.schema.json)): `schema_version`, `built_at`,
`gold_manifest_sha256`, `entity_count`, `fact_count`, `citation_count`, `builder_version`.

## 5. Conversation / Thread (estado del grafo)

| Campo | Tipo | Regla |
|-------|------|-------|
| `thread_id` | UUID4 str | Generado por la API; clave del checkpointer (FR-007). |
| `user_id` | str | Identificador anónimo; namespace de la memoria larga. |
| `variant` | enum `chain`, `agent` | Fijo durante el hilo. |
| `messages` | list[BaseMessage] | Recortado/resumido por `SummarizationMiddleware` (FR-008). |
| `summary` | str null | Resumen acumulado; conserva citas `[U#]` vigentes. |
| `turns` | list[Turn] | Historial visible en la UI. |
| `pending_action` | PendingAction null | No nulo ⇔ estado `pending_approval`. |

**Estados del hilo**

```text
idle ──mensaje──▶ routing ──▶ retrieving ──▶ answering ──▶ idle
                     │              │
                     │              └─acción sensible─▶ pending_approval ──approve/edit──▶ answering
                     │                                        └──reject──▶ idle (registrado)
                     └─direct / out_of_scope / clarify──▶ answering
```

`pending_approval` persiste en el checkpointer y sobrevive a reinicios (US4-3).

## 6. Turn

| Campo | Tipo |
|-------|------|
| `turn_id` | int creciente por hilo |
| `question` | str |
| `route` | RouteDecision |
| `fragments` | list[RetrievedFragment] (vacía en `direct`/`out_of_scope`) |
| `structured_rows` | list[StructuredFact + citas] |
| `answer` | str |
| `citations` / `sources` | list (IDs `[U#]` y URLs) |
| `fallback` | bool (sin evidencia) |
| `metrics` | `latency_ms`, `model_calls`, `tool_calls`, `input_tokens`, `output_tokens` |

## 7. PendingAction

| Campo | Tipo | Regla |
|-------|------|-------|
| `action_id` | str | Único por hilo. |
| `tool` | enum `forget_memory`, `save_preference`, `export_conversation` | Solo herramientas de escritura. |
| `args` | dict | Editable por la persona revisora. |
| `proposed_at` | datetime UTC | — |
| `decision` | enum `approve`, `edit`, `reject` o null | Registrada en el estado (SC-009). |

## 8. UserMemory (P3)

| Campo | Tipo | Regla |
|-------|------|-------|
| namespace | `("users", user_id, "preferences")` | — |
| `key` | enum `response_format`, `topics_of_interest`, `language` | Lista cerrada. |
| `value` | str ≤ 200 | Pasado por `PIIMiddleware` (redact) — FR-010. |
| `created_at` / `expires_at` | datetime | TTL 30 días (`config/agent.toml`). |

## 9. EvalQuery ([schema](./contracts/eval-query.schema.json))

| Campo | Tipo | Regla |
|-------|------|-------|
| `query_id` | str | Único (`r01`…). |
| `question` | str | Pregunta real en español (o inglés si `type=english`). |
| `expected_route` | enum de RouteDecision | Obligatorio. |
| `expected_unit_ids` | list[str] | Obligatorio y no vacío si la ruta es `documental`. |
| `expected_fact_ids` | list[str] | Obligatorio si la ruta es `structured`. |
| `type` | enum `greeting`, `documental`, `structured`, `out_of_corpus`, `ambiguous`, `follow_up` | — |
| `follow_up_of` | str null | `query_id` del turno previo en repreguntas elípticas. |

## 10. EvaluationReport (ampliado)

Por configuración (`lexical`, `semantic`, `hybrid`) y por variante (`chain`, `agent`): Recall@{1,5,10},
nDCG@10, MRR, `router_accuracy`, `abstention_rate`, `citation_validity`, `latency_mean_ms`, `latency_p95_ms`
(tras calentamiento), `model_calls_mean`, `tool_calls_mean`; metadatos `run_id`, `created_at`, `model`,
`embedding_model`, `index_manifest_sha256`.
