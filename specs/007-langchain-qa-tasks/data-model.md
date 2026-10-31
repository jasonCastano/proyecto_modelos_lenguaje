# Fase 1 — Modelo de datos: tareas LangChain del Módulo 1

**Feature**: `007-langchain-qa-tasks`
**Fecha**: 2026-10-30

## 1. Configuración de tareas

### 1.1 TaskConfig

| Campo | Tipo | Validación |
|-------|------|------------|
| `qa_top_k` | entero | `1 <= x <= 20` |
| `qa_token_budget` | entero | `1000 <= x <= 30000` |
| `qa_min_score` | número | `>= 0` |
| `summary_pack` | texto | `"8000"` o `"32000"` |
| `summary_min_citations` | entero | `1 <= x <= 30` |
| `faq_limit` | entero | `10 <= x <= 20` |
| `faq_top_k` | entero | `1 <= x <= 10` |
| `faq_min_citations` | entero | `1 <= x <= 10` |
| `question_max_chars` | entero | `20 <= x <= 2000` |

La configuración vive en `config/tasks.toml` y se registra en cada resultado.

## 2. Plantillas de prompt

### 2.1 PromptTemplate

| Campo | Tipo | Notas |
|-------|------|-------|
| `task` | texto | `summary`, `faq` o `qa` |
| `version` | texto | `1.0`, `1.1`, … |
| `path` | texto | `prompts/summary.md`, `prompts/faq.md`, `prompts/qa.md` |
| `text` | texto | Contenido completo de la plantilla |
| `sha256` | texto | Hash del contenido, para auditoría |
| `sections` | mapa | Rol, tarea, contexto, reglas, formato, fallback |

**Invariante**: las seis secciones deben existir y no estar vacías.

## 3. Datos de entrada

### 3.1 GoldUnit

Vista de lectura de `data/gold/knowledge_units.jsonl`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `unit_id` | texto | `unit_[a-f0-9]{16}` |
| `topic_id` | texto | Tema de oro |
| `topic_title` | texto | Título del tema |
| `text` | texto | Afirmación extractiva |
| `unit_type` | texto | `passage` o `fact` |
| `language` | texto | `es`, `en`, `und` |
| `authority` | texto | `first_party`, `open_data`, `third_party` |
| `status` | texto | `current`, `historical`, `disputed`, `ambiguous` |
| `quality_flags` | lista | Flags de la capa oro |
| `entity_ids` | lista | Entidades detectadas |
| `coverage_item_ids` | lista | Ítems de cobertura |
| `url` | texto | URL pública |
| `title` | texto | Título del documento |
| `section_path` | lista | Ruta de sección |
| `page_start` / `page_end` | entero o nulo | Página del PDF |
| `time_start` / `time_end` | número o nulo | Marca temporal del video |
| `published_at` | texto o nulo | Fecha de publicación |
| `retrieved_at` | texto | Fecha de captura |

**Regla**: una unidad sin `text`, `url` o `section_path` no se usa.

### 3.2 ContextPack

Vista de `data/gold/context_8000.json` o `context_32000.json`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `pack_id` | texto | Identificador del paquete |
| `budget_tokens` | entero | 8000 o 32000 |
| `tokens` | entero | Tokens usados |
| `blocks` | lista | Bloques con `unit_id`, `text`, `citation`, `tokens`, `topic_id`, `authority` |
| `unit_ids` | lista | Unidades incluidas |
| `omitted_units` | entero | Unidades omitidas |
| `coverage_item_ids` | lista | Ítems cubiertos |

### 3.3 FAQSeed

Vista de `data/gold/faq_seeds.jsonl`.

| Campo | Tipo | Notas |
|-------|------|-------|
| `seed_id` | texto | `faq_[a-f0-9]{16}` |
| `question` | texto | Pregunta semilla |
| `topic_id` | texto | Tema |
| `coverage_item_id` | texto o nulo | Ítem de cobertura |
| `evidence_unit_ids` | lista | Unidades de evidencia |
| `status` | texto | `ready`, `review`, `missing_evidence` |

## 4. Selección de evidencia

### 4.1 SelectedUnit

| Campo | Tipo | Notas |
|-------|------|-------|
| `label` | texto | `U1`, `U2`, … |
| `unit` | GoldUnit | Unidad original |
| `score` | número | Puntuación determinista |
| `reason` | texto | Tema, entidad o coincidencia léxica |

### 4.2 EvidenceSelection

| Campo | Tipo | Notas |
|-------|------|-------|
| `query` | texto | Pregunta normalizada |
| `topic_id` | texto | Tema inferido |
| `entities` | lista | Entidades detectadas |
| `selected` | lista de SelectedUnit | Unidades elegidas |
| `omitted_unit_ids` | lista | Unidades relevantes no incluidas por presupuesto |
| `tokens` | entero | Tokens estimados del contexto |
| `budget_tokens` | entero | Presupuesto aplicado |

**Invariante**: `tokens <= budget_tokens`; las etiquetas son únicas y consecutivas.

## 5. Citas

### 5.1 Citation

| Campo | Tipo | Notas |
|-------|------|-------|
| `label` | texto | `U1`, `U2`, … |
| `unit_id` | texto | Unidad de oro |
| `title` | texto | Título del documento |
| `url` | texto | URL pública |
| `section_path` | lista | Sección |
| `page_start` / `page_end` | entero o nulo | Página |
| `time_start` / `time_end` | número o nulo | Tiempo |
| `authority` | texto | Autoridad de la fuente |
| `citation` | texto | Cadena legible: título — URL (sección, página/tiempo) |

**Invariante**: toda cita debe corresponder a una unidad seleccionada; no se aceptan citas externas.

## 6. Resultados

### 6.1 TaskResult

| Campo | Tipo | Notas |
|-------|------|-------|
| `schema_version` | texto | `1.0` |
| `task` | texto | `summary`, `faq`, `qa` |
| `status` | texto | `ok`, `fallback`, `review`, `error` |
| `answer` | texto | Respuesta o mensaje de fallback |
| `citations` | lista de Citation | Fuentes usadas |
| `used_unit_ids` | lista | Unidades incluidas en el contexto |
| `omitted_unit_ids` | lista | Unidades omitidas por presupuesto |
| `prompt_version` | texto | Versión del prompt |
| `prompt_sha256` | texto | Hash del prompt |
| `model` | texto | Modelo usado |
| `latency_seconds` | número | `>= 0` |
| `input_tokens` | entero | Estimación de tokens de entrada |
| `output_tokens` | entero | Estimación de tokens de salida |
| `fallback` | booleano | `True` si no hubo evidencia |
| `review_required` | booleano | `True` si hay citas inválidas o baja confianza |
| `error` | texto o nulo | Código de error controlado |

**Invariantes**:

- `status=fallback` implica `fallback=True` y `citations=[]`.
- `status=ok` implica `citations` no vacío.
- `status=error` implica `error` no nulo y `answer` con un mensaje accionable.
- Todas las `citations.unit_id` pertenecen a `used_unit_ids`.

### 6.2 FAQItem

| Campo | Tipo | Notas |
|-------|------|-------|
| `schema_version` | texto | `1.0` |
| `seed_id` | texto o nulo | Semilla de origen |
| `question` | texto | Pregunta final |
| `answer` | texto | Respuesta citada |
| `citations` | lista de Citation | Fuentes |
| `topic_id` | texto | Tema |
| `coverage_item_id` | texto o nulo | Ítem de cobertura |
| `status` | texto | `ready`, `review`, `missing_evidence` |
| `prompt_version` | texto | Versión del prompt |
| `model` | texto | Modelo usado |

**Invariantes**:

- `status=ready` implica respuesta y al menos una cita.
- `status=missing_evidence` implica `answer` con el mensaje de fallback y `citations=[]`.
- No hay dos `FAQItem` con la misma pregunta normalizada.

### 6.3 TaskError

| Campo | Tipo | Notas |
|-------|------|-------|
| `code` | texto | `empty_question`, `question_too_long`, `no_evidence`, `missing_citations`, `invalid_citation`, `model_timeout`, `model_error`, `invalid_config` |
| `message` | texto | Mensaje accionable |
| `task` | texto | Tarea que falló |
| `review_required` | booleano | Si el resultado debe revisarse |

## 7. Relaciones

```text
TaskConfig ──► RetrievalConfig
GoldUnit ──► EvidenceSelection ──► SelectedUnit ──► Citation
PromptTemplate ──► TaskResult
EvidenceSelection ──► TaskResult
FAQSeed ──► FAQItem
```

## 8. Estados

### 8.1 TaskResult

| Estado inicial | Evento | Estado final |
|----------------|--------|--------------|
| `ok` | Cita inválida | `review` |
| `ok` | Respuesta sin citas tras reintento | `error` |
| `ok` | Sin evidencia | `fallback` |
| `fallback` | N/A | `fallback` |
| `review` | Revisión humana | `ok` o `error` |

### 8.2 FAQItem

| Estado inicial | Evento | Estado final |
|----------------|--------|--------------|
| `ready` | Revisión humana | `ready` o `review` |
| `missing_evidence` | Nueva evidencia | `ready` |
| `review` | Corrección | `ready` |

## 9. Validaciones transversales

1. Pregunta no vacía y `<= question_max_chars`.
2. Contexto delimitado y sin instrucciones ejecutables.
3. Citas dentro del conjunto seleccionado.
4. Respuesta no vacía.
5. Fallback sin citas.
6. FAQ con 10–20 elementos.
7. Sin duplicados de pregunta normalizada.
8. Tokens dentro del presupuesto.
9. Sin secretos ni rutas absolutas en la salida.
10. Modelo y versión de prompt registrados.
