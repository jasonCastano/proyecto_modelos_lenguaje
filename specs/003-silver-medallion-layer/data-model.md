# Data Model: Capa Plata (Silver)

**Feature**: `003-silver-medallion-layer` | **Date**: 2026-10-29

El modelo es lógico y agnóstico de la base de datos. Las salidas se materializan en JSONL y Markdown; el estado
incremental se guarda en JSONL. Los contratos formales están en `contracts/`.

## 1. Entidades

### 1.1 SilverRun (ejecución)

Representa una corrida completa del pipeline.

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `run_id` | string | sí | Único, formato `YYYY-MM-silver-NN` |
| `started_at` / `finished_at` | string (UTC) | sí | ISO 8601; `finished_at >= started_at` |
| `status` | enum | sí | `planned`, `running`, `completed`, `completed_with_failures`, `failed` |
| `config_hash` | string | sí | SHA-256 de `config/silver.toml` + versión de reglas |
| `cleaning_version` | string | sí | Semver de las reglas de limpieza |
| `tool_version` | string | sí | Versión del paquete |
| `git_commit` | string | no | Commit de la ejecución |
| `input_artifacts` | integer | sí | Artefactos activos leídos |
| `processed` / `skipped` / `failed` | integer | sí | Suma igual a `input_artifacts` |
| `documents` / `chunks` | integer | sí | Documentos publicados (canónicos + alias) y fragmentos canónicos |
| `canonical_documents` / `alias_documents` | integer | sí | Desglose de `documents` |
| `duplicates_exact` / `duplicates_near` | integer | sí | Grupos detectados |
| `tokens_in` / `tokens_out` | integer | sí | Proxy de tokens de entrada y salida |
| `bytes_out` | integer | sí | Tamaño de las salidas |
| `duration_seconds` | number | sí | Duración total |
| `by_source` / `by_media_type` / `by_status` | object | sí | Conteos |
| `skip_reasons` / `failure_reasons` | object | sí | Conteos por motivo |
| `quality_flags` | object | sí | Conteos por flag |
| `section_coverage` | object | sí | `with_title`, `without_title` |
| `report_paths` | array[string] | sí | Rutas relativas de los reportes |

**Invariante**: `processed + skipped + failed = input_artifacts` y
`canonical_documents + alias_documents = documents`.

### 1.2 ProcessingRecord (estado por artefacto)

Una línea por artefacto de entrada en `data/silver/_meta/state.jsonl`.

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `artifact_id` | integer | sí | Clave del catálogo bronce |
| `content_hash` | string | sí | Hash del artefacto bronce |
| `config_hash` | string | sí | Configuración con la que se procesó |
| `status` | enum | sí | `processed`, `skipped`, `failed` |
| `reason` | string | condicional | Obligatorio si `status != processed` |
| `doc_id` | string | condicional | Obligatorio si `status = processed` |
| `documents` | integer | sí | 0 o 1 |
| `chunks` | integer | sí | ≥0 |
| `quality_flags` | array[string] | sí | Puede ser vacío |
| `processed_at` | string (UTC) | sí | ISO 8601 |

**Invariante**: si `status = processed`, `doc_id` existe y `documents = 1`; si `status != processed`,
`documents = 0` y `chunks = 0`.

### 1.3 SilverDocument (documento plata)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `schema_version` | string | sí | `1.0` |
| `doc_id` | string | sí | `doc_` + 16 caracteres de `sha256(url_canonical:content_hash)`; estable ante reconstrucciones del catálogo |
| `artifact_id` | integer | sí | Referencia al bronce |
| `campaign_id` | string | sí | Campaña de origen |
| `content_hash` / `text_hash` | string | sí | Hashes de contenido y texto |
| `source_id` | string | sí | Fuente del bronce |
| `authority` | enum | sí | `first_party`, `third_party`, `open_data` |
| `url` / `url_canonical` | string | sí | URL pública y canónica |
| `title` | string | sí | Si el bronce no tiene, se usa el H1 o el nombre del archivo; nunca nulo |
| `published_at` / `retrieved_at` | string (UTC) | no / sí | Fechas de publicación y captura |
| `language` | enum | sí | `es`, `en`, `und` |
| `language_method` | enum | sí | `html_lang`, `heuristic`, `unknown` |
| `category` | enum | sí | `identity`, `offer`, `digital_presence`, `hard_data` |
| `media_type` | string | sí | Tipo del bronce |
| `cleaning_version` | string | sí | Versión de reglas aplicadas |
| `config_hash` | string | sí | Configuración de la ejecución |
| `status` | enum | sí | `canonical`, `alias` |
| `canonical_doc_id` | string | condicional | Obligatorio si `status = alias`; nulo si es canónico |
| `duplicate_of` | string | condicional | Igual a `canonical_doc_id` para alias |
| `aliases` | array[string] | sí | `doc_id` de los alias del grupo |
| `quality_flags` | array[string] | sí | Flags del documento |
| `sections` | array[Section] | sí | ≥1; ordenadas por `order` |
| `text` | string | sí | Texto limpio completo, UTF-8 |
| `char_count` | integer | sí | `len(text)` |
| `token_count` | integer | sí | Proxy de tokens |
| `license_note` | string | sí | Nota de uso académico y atribución |
| `markdown_path` | string | no | Ruta relativa del Markdown |

**Invariantes**:
- `doc_id` es determinista a partir de `url_canonical` y `content_hash`.
- Si `status = alias`, `canonical_doc_id` apunta a un documento canónico del mismo grupo.
- Un grupo de duplicados tiene exactamente un canónico.
- `text` no está vacío y `char_count > 0`.

### 1.4 Section (sección)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `section_id` | string | sí | `doc_id` + `-s` + orden de 3 dígitos |
| `title` | string | sí | Título detectado o `"sin sección"` |
| `path` | array[string] | sí | Ruta jerárquica; último elemento = `title` |
| `level` | integer | sí | 1–6; 0 para `"sin sección"` |
| `order` | integer | sí | 0..N-1, estrictamente creciente |
| `char_start` / `char_end` | integer | sí | Rango no vacío dentro de `document.text` |
| `page_start` / `page_end` | integer | no | Solo PDF; `page_start <= page_end` |
| `time_start` / `time_end` | number | no | Solo VTT; segundos, `time_start <= time_end` |

**Invariantes**: las secciones no se solapan y cubren el texto en orden; `char_end > char_start`; si no hay
título, `title = "sin sección"`, `level = 0` y el documento lleva `no_section`.

### 1.5 Chunk (fragmento)

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `schema_version` | string | sí | `1.0` |
| `chunk_id` | string | sí | `doc_id-sNNN-cNNNN`; único |
| `doc_id` | string | sí | Documento padre |
| `artifact_id` | integer | sí | Linaje al bronce |
| `content_hash` | string | sí | Linaje al bronce |
| `source_id` / `authority` | string / enum | sí | Fuente y autoridad |
| `url` / `title` | string | sí | Para citar |
| `section_id` | string | sí | Sección padre |
| `section_title` | string | sí | Copia del título de la sección |
| `section_path` | array[string] | sí | Ruta completa |
| `section_level` | integer | sí | Nivel de la sección |
| `chunk_order` | integer | sí | Orden dentro de la sección, desde 0 |
| `text` | string | sí | Texto literal del fragmento |
| `char_start` / `char_end` | integer | sí | Offsets dentro de `document.text` |
| `token_count` | integer | sí | >0 y ≤ `chunking.max_tokens` |
| `page_start` / `page_end` | integer | no | PDF |
| `time_start` / `time_end` | number | no | VTT |
| `language` | enum | sí | `es`, `en`, `und` |
| `media_type` | string | sí | Tipo de origen |
| `quality_flags` | array[string] | sí | Flags del fragmento |
| `duplicate_of` | string | no | `chunk_id` canónico si es duplicado |
| `retrieved_at` | string (UTC) | sí | Fecha de captura del bronce |
| `license_note` | string | sí | Nota de uso |

**Invariantes**:
- `document.text[char_start:char_end]` contiene exactamente `chunk.text` (salvo normalización de espacios
  declarada y registrada).
- Solo los documentos canónicos generan chunks recuperables; los alias conservan su texto y secciones para
  auditoría, pero no se exportan a `chunks.jsonl`.
- Los chunks de una sección son contiguos y no se solapan más allá del solapamiento configurado.
- Un chunk nunca cruza el límite de una sección.
- `token_count <= max_tokens`; si la sección completa es menor que `min_tokens`, se permite un único chunk corto.
- `chunk_id` es estable para el mismo contenido y configuración.

### 1.6 DuplicateGroup

| Campo | Tipo | Obligatorio | Regla |
|-------|------|-------------|-------|
| `group_id` | string | sí | `dup_` + hash del representante |
| `kind` | enum | sí | `exact`, `near` |
| `canonical_doc_id` | string | sí | Documento elegido |
| `members` | array[string] | sí | ≥2 `doc_id` |
| `similarity` | number | no | 0..1; obligatorio en `near` |
| `reason` | string | sí | `same_text`, `same_url_newer`, `official_preferred`, `longer_text` |

**Invariante**: `canonical_doc_id` pertenece a `members` y es el de mayor prioridad según autoridad, fecha y
completitud. El grupo no se materializa en un archivo separado: se reconstruye desde `documents.jsonl`
(`aliases` del canónico y `canonical_doc_id` de cada alias).

### 1.7 QualityFlag

| Flag | Significado | Umbral / condición |
|------|-------------|--------------------|
| `no_text` | No se extrajo texto útil | <100 caracteres tras limpiar |
| `scanned_pdf` | PDF sin capa de texto | 0 caracteres en todas las páginas |
| `encrypted_pdf` | PDF protegido con contraseña | No se puede descifrar sin credenciales |
| `low_text_density` | Texto con muchos caracteres no alfabéticos | <50% alfabéticos |
| `table_heavy` | Predominan filas tabulares | >30% de líneas con 2+ columnas |
| `multi_column_suspect` | Posible intercalado de columnas | Heurística de líneas cortas alternadas |
| `encoding_repaired` | Se reparó mojibake | Cambio reversible aplicado |
| `no_section` | Sin encabezados detectables | `title = "sin sección"` |
| `short_section` | Sección menor al mínimo | `tokens < min_tokens` |
| `exact_duplicate` | Texto normalizado idéntico | Hash igual |
| `near_duplicate` | Similitud ≥ umbral | Jaccard ≥0,90 |
| `language_unknown` | Idioma no determinable | `language = und` |
| `subtitle_kind_unknown` | No se sabe si el subtítulo es manual o automático | Metadato de YouTube ausente |

### 1.8 Lineage

No es una entidad separada: se materializa en los campos de `SilverDocument` y `Chunk`
(`artifact_id`, `content_hash`, `url`, `retrieved_at`, `campaign_id`, `source_id`). La auditoría debe poder
reconstruir:

```text
chunk_id → doc_id → artifact_id → content_hash → storage_path en bronce → URL pública
```

## 2. Relaciones

```text
SilverRun 1 ─── N ProcessingRecord
ProcessingRecord 1 ─── 0..1 SilverDocument
SilverDocument 1 ─── 1..N Section
SilverDocument 1 ─── 1..N Chunk
Section 1 ─── 1..N Chunk
DuplicateGroup N ─── N SilverDocument
SilverDocument (canónico) 1 ─── N SilverDocument (alias)
```

## 3. Transiciones de estado

### 3.1 Artefacto

```text
pending → processing → processed
                    ├── skipped (sin texto, navegación, sitemap, vacío)
                    └── failed (error de lectura o escritura)
failed → processing (reintento) → processed | skipped | failed
```

Un artefacto no puede quedar en `processing` al finalizar la ejecución.

### 3.2 Documento

```text
extracted → cleaned → sectioned → deduped → canonical → chunked → published
                                          └── alias
```

Un documento `alias` conserva su texto y secciones para auditoría, pero no se fragmenta ni se publica en
`chunks.jsonl`; el canónico del grupo es el único que genera fragmentos recuperables.

### 3.3 Ejecución

```text
planned → running → completed
                  └── completed_with_failures (si failed > 0)
                  └── failed (error global)
```

## 4. Reglas de validación

1. **Conteo**: `processed + skipped + failed = input_artifacts`.
2. **Cobertura**: todo `ProcessingRecord` con `status = processed` tiene exactamente un `SilverDocument`.
3. **Sección**: todo `chunk.section_id` existe en `document.sections`; todo `section_id` es único en el documento.
4. **Offsets**: `0 <= char_start < char_end <= len(document.text)`; los chunks de una sección son crecientes.
5. **Tokens**: `0 < chunk.token_count <= chunking.max_tokens`, salvo sección corta única.
6. **Linaje**: `artifact_id` y `content_hash` existen en el catálogo bronce y el hash coincide.
7. **Canónico**: cada `DuplicateGroup` tiene exactamente un `canonical_doc_id`; los alias apuntan a él.
8. **Idempotencia**: con el mismo `config_hash` y los mismos `content_hash`, los `doc_id`, `chunk_id`, textos y
   hashes de salida son idénticos.
9. **No nulos**: `title`, `section_title`, `section_path`, `url`, `language` y `license_note` nunca son nulos.
10. **Bronce inmutable**: ningún registro escribe en `data/bronze/`; los hashes de entrada se verifican antes y
    después.

## 5. Configuración (`config/silver.toml`)

| Sección | Clave | Valor inicial | Uso |
|---------|-------|---------------|-----|
| `[chunking]` | `target_tokens` | 800 | Objetivo por fragmento |
| | `max_tokens` | 1000 | Máximo duro |
| | `min_tokens` | 200 | Mínimo salvo sección corta |
| | `overlap_tokens` | 120 | Solapamiento |
| | `chars_per_token` | 3.5 | Proxy de conteo |
| | `boundary` | `sentence` | Preferencia de corte |
| `[dedup]` | `near_threshold` | 0.90 | Jaccard mínimo |
| | `shingle_size` | 5 | Palabras por shingle |
| | `num_perm` | 128 | Permutaciones MinHash |
| | `bands` | 16 | Bandas LSH |
| `[quality]` | `min_text_chars` | 100 | Umbral de `no_text` |
| | `min_alpha_ratio` | 0.50 | Umbral de densidad |
| | `table_line_ratio` | 0.30 | Umbral de tablas |
| | `repeated_line_ratio` | 0.30 | Boilerplate PDF |
| `[output]` | `root` | `data/silver` | Directorio de salida |
| | `markdown` | `true` | Generar Markdown |
| `[language]` | `min_tokens` | 10 | Mínimo para detectar |
| `[run]` | `max_workers` | 4 | Concurrencia acotada |
| | `fail_fast` | `false` | Continuar ante fallos |

El archivo se versiona; su hash y el de las reglas se registran en cada ejecución.
