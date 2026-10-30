# Data Model: Capa Oro (Gold)

**Feature**: `004-gold-medallion-layer` | **Date**: 2026-10-30

Modelo lógico de la base consolidada. Las salidas se materializan en JSONL y Markdown; el estado incremental
en JSONL. Los contratos formales están en `contracts/`.

## 1. Entidades

### 1.1 KnowledgeUnit (unidad de conocimiento)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `schema_version` | string | sí | `1.0` |
| `unit_id` | string | sí | `unit_` + 16 hex; determinista |
| `topic_id` | string | sí | Debe existir en la taxonomía |
| `topic_title` | string | sí | Título legible del tema |
| `text` | string | sí | Texto extractivo, no generado |
| `unit_type` | enum | sí | `passage`, `fact` |
| `language` | enum | sí | `es`, `en`, `und` |
| `authority` | enum | sí | `first_party`, `third_party`, `open_data` |
| `confidence` | number | sí | 0..1; regla de clasificación |
| `status` | enum | sí | `current`, `historical`, `disputed`, `ambiguous` |
| `entity_ids` | array[string] | sí | Puede ser vacío; sin duplicados |
| `coverage_item_ids` | array[string] | sí | Puede ser vacío; IDs de los 24 ítems |
| `evidence` | array[Evidence] | sí | ≥1 |
| `fact_id` | string \| null | sí | Obligatorio si `unit_type = fact` |
| `text_hash` | string | sí | SHA-256 del texto normalizado |
| `quality_flags` | array[string] | sí | Marcas de calidad |
| `url` | string | sí | URL pública de la evidencia principal |
| `title` | string | sí | Título del documento de origen |
| `section_path` | array[string] | sí | ≥1 |
| `page_start` / `page_end` | integer \| null | sí | PDF |
| `time_start` / `time_end` | number \| null | sí | VTT |
| `published_at` / `retrieved_at` | string \| null / string | sí | Fechas |
| `license_note` | string | sí | Atribución y uso académico |

**Invariantes**:
- `evidence` no está vacío.
- `text` aparece en el texto del fragmento de la evidencia principal (tras normalización declarada).
- `unit_id` es estable para el mismo fragmento, oración y configuración.
- `status = disputed` exige al menos dos evidencias con valores distintos.
- No se publica una unidad sin `topic_id`, `url`, `title` ni `section_path`.

### 1.2 Evidence (evidencia)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `chunk_id` | string | sí | Fragmento de plata |
| `doc_id` | string | sí | Documento canónico |
| `artifact_id` | integer | sí | Artefacto bronce |
| `content_hash` | string | sí | Hash del artefacto |
| `url` | string | sí | URL pública |
| `title` | string | sí | Título |
| `section_path` | array[string] | sí | Ruta de sección |
| `page_start` / `page_end` | integer \| null | sí | Página |
| `time_start` / `time_end` | number \| null | sí | Tiempo |
| `authority` | enum | sí | Autoridad |
| `published_at` | string \| null | sí | Publicación |
| `retrieved_at` | string | sí | Captura |
| `score` | number | sí | 0..1; confianza en la evidencia |

### 1.3 Fact (hecho)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `schema_version` | string | sí | `1.0` |
| `fact_id` | string | sí | `fact_` + 16 hex |
| `subject_id` | string | sí | Entidad canónica |
| `subject_label` | string | sí | Nombre legible |
| `attribute` | string | sí | Atributo normalizado |
| `value` | string | sí | Valor literal normalizado |
| `value_normalized` | string | sí | Para comparar |
| `unit` | string \| null | sí | Unidad de medida |
| `year` | integer \| null | sí | Año del dato |
| `unit_id` | string | sí | Unidad que lo respalda |
| `evidence` | array[Evidence] | sí | ≥1 |
| `status` | enum | sí | `current`, `historical`, `disputed`, `ambiguous` |

**Invariantes**: `subject_id` y `attribute` no vacíos; `value_normalized` estable; un hecho sin unidad o sin
atributo no se publica como hecho (queda como pasaje).

### 1.4 Entity (entidad)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `entity_id` | string | sí | `ent_` + 16 hex |
| `canonical_name` | string | sí | Único |
| `aliases` | array[string] | sí | Sin duplicados |
| `entity_type` | enum | sí | `company`, `subsidiary`, `brand`, `product`, `site`, `person`, `certification`, `other` |
| `description` | string \| null | sí | Breve, extractiva |
| `unit_ids` | array[string] | sí | Unidades que la mencionan |
| `coverage_item_ids` | array[string] | sí | Ítems asociados |

**Invariante**: los alias no se repiten entre entidades; la entidad canónica agrupa todas las variantes.

### 1.5 Topic (tema)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `topic_id` | string | sí | Slug estable |
| `title` | string | sí | Legible |
| `description` | string | sí | Propósito del tema |
| `coverage_item_ids` | array[string] | sí | Mapeo a los 24 ítems |
| `order` | integer | sí | Orden de navegación |
| `unit_count` | integer | sí | Calculado |
| `status` | enum | sí | `covered`, `partial`, `empty` |

### 1.6 Conflict (conflicto)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `conflict_id` | string | sí | `conf_` + 16 hex |
| `subject_id` | string | sí | Entidad |
| `attribute` | string | sí | Atributo comparable |
| `values` | array[ConflictValue] | sí | ≥2 valores distintos |
| `preferred_unit_id` | string \| null | sí | Nulo si disputado |
| `status` | enum | sí | `resolved`, `disputed` |
| `reason` | string | sí | `official_source`, `newer_date`, `more_evidence`, `unresolved` |

`ConflictValue`: `value`, `value_normalized`, `unit`, `year`, `authority`, `unit_id`, `url`.

### 1.7 CoverageEntry (ítem de cobertura)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `item_id` | string | sí | I-01…H-06 |
| `name` | string | sí | Nombre del ítem |
| `category` | string | sí | Identidad, oferta, presencia digital, datos duros |
| `status` | enum | sí | `covered`, `partial`, `missing` |
| `unit_ids` | array[string] | sí | Evidencia |
| `authority_counts` | object | sí | Conteo por autoridad |
| `conflict_ids` | array[string] | sí | Conflictos asociados |
| `gap_reason` | string \| null | sí | Obligatorio si no cubierto |
| `recommendation` | string \| null | sí | Fuente sugerida |

**Invariante**: `covered` exige ≥3 unidades y ≥1 oficial; `partial` exige 1–2 unidades o solo terceros;
`missing` no tiene unidades y debe tener `gap_reason`.

### 1.8 ContextPack (paquete de contexto)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `pack_id` | string | sí | `pack_<task>_<budget>` |
| `task` | enum | sí | `summary`, `faq`, `qa` |
| `budget_tokens` | integer | sí | 8000 o 32000 |
| `tokens` | integer | sí | ≤ budget |
| `unit_ids` | array[string] | sí | Sin duplicados |
| `blocks` | array[ContextBlock] | sí | ≥1 |
| `coverage_item_ids` | array[string] | sí | Cobertura incluida |
| `omitted_units` | integer | sí | Unidades excluidas por presupuesto |

`ContextBlock`: `unit_id`, `text`, `citation`, `tokens`, `topic_id`, `authority`.

**Invariantes**: `tokens <= budget_tokens`; cada bloque tiene `citation`; no se repite `unit_id`; el paquete
de 32k contiene todos los temas del de 8k.

### 1.9 FAQSeed (pregunta semilla)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `seed_id` | string | sí | `faq_` + 16 hex |
| `question` | string | sí | Pregunta en español |
| `topic_id` | string | sí | Tema |
| `coverage_item_id` | string \| null | sí | Ítem asociado |
| `evidence_unit_ids` | array[string] | sí | ≥1 |
| `status` | enum | sí | `ready`, `review`, `missing_evidence` |

### 1.10 GoldManifest y QualityReport

`GoldManifest`: `run_id`, `config_hash`, `taxonomy_hash`, `created_at`, `input_documents`, `input_chunks`,
`knowledge_units`, `facts`, `entities`, `conflicts`, `faq_seeds`, `files` (ruta + hash + bytes), `report_paths`.

`QualityReport`: `run_id`, `status`, `config_hash`, `input_documents`, `processed`, `skipped`, `failed`,
`units`, `facts`, `entities`, `conflicts`, `coverage` (conteos), `context_packs`, `tokens`, `duration_seconds`,
`quality_flags`, `skip_reasons`, `failure_reasons`, `report_paths`.

## 2. Relaciones

```text
SilverDocument 1 ─── N SilverChunk 1 ─── N KnowledgeUnit
KnowledgeUnit N ─── N Entity
KnowledgeUnit N ─── N CoverageItem
KnowledgeUnit N ─── N Evidence
KnowledgeUnit 1 ─── 0..1 Fact
Fact N ─── N ConflictValue
Conflict 1 ─── N ConflictValue
Topic 1 ─── N KnowledgeUnit
ContextPack 1 ─── N ContextBlock ─── 1 KnowledgeUnit
FAQSeed 1 ─── N KnowledgeUnit
```

## 3. Estados

### 3.1 Documento de plata

```text
pending → processing → processed (≥0 unidades)
                    ├── skipped (sin chunks, sin tema, sin evidencia)
                    └── failed (error de lectura)
```

### 3.2 Unidad

```text
draft → published → current
                 ├── historical
                 ├── disputed
                 └── ambiguous
```

Una unidad `disputed` conserva al menos dos evidencias contradictorias; una `historical` tiene fecha anterior
a otra unidad vigente del mismo sujeto/atributo.

### 3.3 Conflicto

```text
open → resolved (official_source | newer_date | more_evidence)
     └── disputed (unresolved)
```

### 3.4 Ejecución

```text
planned → running → completed
                  └── completed_with_failures
```

## 4. Reglas de validación

1. Solo documentos y fragmentos canónicos de plata; ningún alias.
2. Toda unidad tiene ≥1 evidencia y linaje hasta URL.
3. El texto de la unidad aparece en el fragmento de la evidencia principal.
4. `unit_id`, `fact_id`, `entity_id` y `seed_id` son deterministas.
5. Un hecho no se publica sin sujeto, atributo y valor.
6. Un conflicto tiene ≥2 valores normalizados distintos.
7. La cobertura `covered` exige ≥3 unidades y ≥1 oficial.
8. Un paquete de contexto no excede su presupuesto y no repite unidades.
9. Las 24 entradas de cobertura existen siempre, aunque estén vacías.
10. No se modifican bronce ni plata; los hashes se verifican antes/después.

## 5. Configuración

### `config/gold.toml`

| Sección | Clave | Valor inicial |
|---------|-------|---------------|
| `[units]` | `min_sentence_chars` | 40 |
| | `max_unit_chars` | 700 |
| | `dedup_threshold` | 0.90 |
| | `dedup_shingle_size` | 5 |
| `[topics]` | `min_score` | 1 |
| `[coverage]` | `covered_min_units` | 3 |
| | `covered_min_official` | 1 |
| `[context]` | `budgets` | [8000, 32000] |
| | `chars_per_token` | 3.5 |
| `[output]` | `root` | `data/gold` |
| `[run]` | `fail_fast` | false |

### `config/gold_taxonomy.toml`

Cada `[[topics]]` declara `id`, `title`, `description`, `coverage_item_ids` y `keywords`. Cada
`[[entities]]` declara `id`, `canonical_name`, `entity_type`, `aliases` y `coverage_item_ids`.
