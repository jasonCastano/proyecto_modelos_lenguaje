# Phase 1 — Data Model: Chatbot con recuperación semántica (RAG)

**Feature**: `013-semantic-rag-chatbot` | **Date**: 2026-11-06

El modelo es **derivado y de solo lectura** sobre el corpus: no se crea ni se modifica ninguna entidad
de `data/bronze`, `data/silver` ni `data/gold`. Todo lo nuevo vive en `data/module2/index/` (ignorado
por Git) y en `tests/fixtures/rag/` (versionado, reducido).

---

## Entidades

### `EmbeddingProfile`

Perfil del modelo con el que se generan los vectores. Se compara en cada carga del índice.

| Campo | Tipo | Reglas | Origen |
|-------|------|--------|--------|
| `model` | string | obligatorio, no vacío | `config/retrieval.toml` |
| `dimension` | int | > 0; debe coincidir con la matriz | configuración |
| `normalize` | bool | `true` fija norma L2 = 1 | configuración |
| `max_tokens` | int | > 0, por defecto 512 | configuración |
| `query_prefix` | string | prefijo de consulta (`"query: "`) | configuración |
| `passage_prefix` | string | prefijo de documento (`"passage: "`) | configuración |
| `created_at` | datetime ISO-8601 UTC | obligatorio | construcción |

**Invariante**: `dimension` del perfil == ancho de la matriz `.npy`; si no, el índice se rechaza
(FR-003).

---

### `Fragment` (fragmento indexable)

Unidad mínima recuperable. Normalmente una unidad de oro; si excede `max_tokens`, una ventana de ella.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `fragment_id` | string | `<unit_id>` o `<unit_id>#<chunk_index>`; único |
| `unit_id` | string | obligatorio; es el que se cita |
| `doc_id` | string | obligatorio |
| `title` | string | puede ser vacío |
| `url` | string | puede ser vacío |
| `published_at` | string \| null | ISO-8601 |
| `topic` | string \| null | taxonomía de oro |
| `text` | string | no vacío; recortado a `max_tokens` |
| `tokens` | int | > 0 |
| `chunk_index` | int | ≥ 1 |
| `chunk_total` | int | ≥ `chunk_index` |

**Invariante**: `chunk_total == 1` para unidades que caben en el límite; la concatenación de las
ventanas de una unidad reproduce su texto (salvo el solape declarado).

---

### `VectorIndex`

Artefacto persistido en `data/module2/index/`.

| Componente | Archivo | Contenido |
|------------|---------|-----------|
| Matriz | `vectors.npy` | float32, forma `(n, 384)`, filas normalizadas L2 |
| Metadatos | `index.sqlite3` | tabla `fragments` con las columnas de `Fragment` y su posición |
| Manifiesto | `manifest.json` | esquema de [contracts/index-manifest.schema.json](./contracts/index-manifest.schema.json) |

**Reglas**:

- `manifest.count` == número de filas de `vectors.npy` == filas de `fragments`.
- `manifest.gold_sha256` es el hash del conjunto `knowledge_units.jsonl` usado; si cambia, el índice
  está desactualizado (se avisa, no se rompe).
- El índice es **reemplazable de forma atómica**: se construye en un directorio temporal y se renombra
  al final; nunca se escribe en el directorio activo a medias.
- El índice **no se versiona**; solo el manifiesto de ejemplo y el índice de prueba.

---

### `RetrievedFragment` (candidato de una consulta)

| Campo | Tipo | Reglas |
|-------|------|--------|
| `unit_id` | string | obligatorio |
| `title` | string | — |
| `url` | string | — |
| `score` | float | [0, 1] combinado |
| `semantic_score` | float \| null | [0, 1] o `null` si no vino de semántica |
| `lexical_score` | float \| null | [0, 1] o `null` si no vino de léxica |
| `origin` | enum | `semantic` \| `lexical` \| `both` |
| `status` | enum | `used` \| `omitted_threshold` \| `omitted_budget` \| `omitted_duplicate` |
| `reason` | string \| null | obligatorio si `status != used` |

**Transiciones de estado** (por consulta):

```text
candidato
  ├─ score < min_similarity (sin respaldo léxico) → omitted_threshold
  ├─ duplicado de uno ya usado (sim > 0.98)      → omitted_duplicate
  ├─ cabe en el presupuesto                      → used
  └─ no cabe                                     → omitted_budget
```

---

### `RetrievalTrace`

Resumen auditable de una consulta. Es el contrato que consume la API y la UI
(ver [contracts/retrieval-trace.md](./contracts/retrieval-trace.md)).

| Campo | Tipo | Reglas |
|-------|------|--------|
| `mode` | enum | `semantic` \| `lexical` \| `hybrid` \| `none` |
| `semantic_available` | bool | `false` si no hay índice válido |
| `candidates` | int | ≥ 0 |
| `threshold` | float | umbral aplicado |
| `fragments` | `RetrievedFragment[]` | ordenados por `score` desc |
| `used_unit_ids` | string[] | coherente con `status == used` |
| `notes` | string[] | avisos legibles (índice desactualizado, modelo distinto, etc.) |
| `elapsed_ms` | float | ≥ 0, solo recuperación |

**Invariante**: `used_unit_ids` == `[f.unit_id for f in fragments if f.status == "used"]`, sin
repetidos (FR-005).

---

### `EvaluationRun`

Resultado de comparar modos sobre el conjunto de preguntas.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `run_id` | string | fecha + hash corto del conjunto |
| `mode` | enum | `semantic` \| `lexical` \| `hybrid` |
| `k_values` | int[] | `[1, 3, 5, 8]` |
| `recall_at_k` | map[int, float] | [0, 1] |
| `mrr` | float | [0, 1] |
| `citation_coverage` | float | [0, 1] |
| `fidelity` | float | [0, 1]; respuestas `ok` sustentadas en los fragmentos citados |
| `latency_ms` | `{mean, p95}` | > 0 |
| `errors` | objeto[] | `{question_id, tipo, causa}` |

**Reglas**: cada `EvaluationRun` se compara solo con otros del mismo conjunto de preguntas; el informe
declara el ganador por métrica y los empates.

---

## Relaciones

```text
GoldUnit (existente, solo lectura)
   └─1..n─ Fragment ──1─ VectorIndex ──1─ IndexManifest
                          │
consulta ──► RetrievalTrace ──1..n─ RetrievedFragment ──► EvidenceSelection (existente)
                                                              │
                                                              └─► TaskResult (existente)
EvaluationRun ──n─► Question (conjunto de evaluación)
```

Nada nuevo apunta hacia las capas medallion en escritura: `GoldUnit` se lee y se copia a `Fragment`
como artefacto derivado.

---

## Validaciones derivadas de los requisitos

| Requisito | Validación |
|-----------|------------|
| FR-002 | `manifest.gold_sha256` presente y calculado sobre el archivo de oro real |
| FR-003 | `index verify` falla con código ≠ 0 y mensaje accionable si modelo o dimensión no coinciden |
| FR-004 | `RetrievalTrace.mode == "lexical"` cuando no hay candidato semántico sobre el umbral |
| FR-005 | `used_unit_ids` sin duplicados (prueba unitaria) |
| FR-006 | `TaskResult` conserva estados, citas y metadatos (pruebas de contrato existentes) |
| FR-008 | Cada `RetrievedFragment` aparece en la UI con `status` y `reason` |
| FR-011 | `origin` presente en cada fragmento y `mode` en la traza |
| FR-012 | `omitted_budget` con `reason` y respeto del `token_budget` |
| FR-013 | `omitted_duplicate` para pares con similitud > `dedup_similarity` |
| FR-018 | Prueba de que `data/module2/` está en `.gitignore` |
| SC-010 | Prueba de que construir el índice no modifica mtimes ni hashes de `data/gold` |
