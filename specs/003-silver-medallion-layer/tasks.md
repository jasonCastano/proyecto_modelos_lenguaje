# Tareas: Capa Plata (Silver) de la Arquitectura Medallion

**Entrada**: documentos de diseño de `/specs/003-silver-medallion-layer/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: incluidas porque la constitución exige pruebas para cada módulo crítico (§3.8) y la especificación
define criterios verificables. No se exige TDD estricto, pero cada tarea de prueba debe fallar antes de la
implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: código en `src/proyecto_modelos_lenguaje/`, pruebas en `tests/`, configuración en `config/`,
documentación en `specs/003-silver-medallion-layer/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: dependencias, configuración y esqueleto del paquete.

- [X] T001 Añadir las dependencias de ejecución `trafilatura>=2.3`, `pypdf>=6.21`, `openpyxl>=3.1`, `lxml>=6.1` y `PyYAML>=6.0`, más la dependencia de desarrollo `fpdf2` para generar PDF de prueba, en `pyproject.toml`; ejecutar `uv lock`.
- [X] T002 Crear `config/silver.toml` con las secciones `[chunking]`, `[dedup]`, `[quality]`, `[output]`, `[language]` y `[run]`, con los valores iniciales de `data-model.md`.
- [X] T003 Crear el esqueleto del paquete `src/proyecto_modelos_lenguaje/silver/__init__.py` y `src/proyecto_modelos_lenguaje/silver/extractors/__init__.py`; crear los directorios `tests/unit/silver/`, `tests/contract/silver/` y `tests/integration/silver/`.
- [X] T004 [P] Añadir los fixtures de texto `tests/fixtures/silver/sample.html`, `tests/fixtures/silver/sample.vtt` y `tests/fixtures/silver/sample.json`, más `tests/fixtures/silver/generate.py` para construir un PDF con texto usando `fpdf2` y un XLSX con `openpyxl` en un directorio temporal.
- [X] T005 [P] Añadir `tests/integration/silver/conftest.py` con un fixture que cree un catálogo bronce temporal (fuentes, 24 ítems de cobertura, campaña y artefactos con `Catalog` y `Storage`) y devuelva la ruta de configuración y la ruta de la base de datos.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: modelos, configuración, estado y lectura de bronce que bloquean todas las historias.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [X] T006 Crear `src/proyecto_modelos_lenguaje/silver/models.py` con los dataclasses `SilverDocument`, `Section`, `Chunk`, `ProcessingRecord`, `DuplicateGroup` y `RunReport`, y los enums `DocumentStatus`, `ProcessStatus` y `QualityFlag`; validar `doc_id` `doc_[a-f0-9]{16}`, `section_id` `doc_[a-f0-9]{16}-s\d{3}`, `chunk_id` `doc_[a-f0-9]{16}-s\d{3}-c\d{4}`, `title`/`section_title`/`section_path` no nulos y `chunk.token_count <= config.chunking.max_tokens`.
- [X] T007 Crear `src/proyecto_modelos_lenguaje/silver/config.py` para cargar `config/silver.toml` con `tomllib`, validar rangos (`0 < min_tokens <= target_tokens <= max_tokens`, `0 <= overlap_tokens < target_tokens`, `0 < near_threshold <= 1`), exponer un `SilverConfig` tipado y calcular un `config_hash` SHA-256 sobre JSON canónico más `CLEANING_VERSION`.
- [X] T008 Crear `src/proyecto_modelos_lenguaje/silver/cleaning.py` con las funciones puras `estimate_tokens(text, chars_per_token)`, `normalize_whitespace(text)`, `repair_mojibake(text)`, `sha256_text(text)` y `CLEANING_VERSION = "1.0.0"`; `estimate_tokens` DEBE usar `ceil(len(text) / chars_per_token)`.
- [X] T009 Crear `src/proyecto_modelos_lenguaje/silver/state.py` con escritura atómica de JSONL (archivo temporal + `os.replace`), `read_state(path)`, `merge_state(records)`, caché por `content_hash + config_hash` y validación estricta de `run_id` (`YYYY-MM-silver-NN`).
- [X] T010 Crear `src/proyecto_modelos_lenguaje/silver/bronze.py` para leer `v_active_artifacts` y `url_versions` en modo solo lectura, devolver todas las versiones activas con `artifact_id`, `content_hash`, `url_canonical`, `version`, fuente, autoridad, idioma, fechas y categoría, y exponer la versión más reciente por URL sin escribir en la base de datos bronce.
- [X] T011 Crear `tests/contract/silver/conftest.py` con helpers para cargar `contracts/document.schema.json`, `contracts/chunk.schema.json` y `contracts/run-report.schema.json` y validar registros con `jsonschema.Draft202012Validator`.

**Punto de control**: modelos, configuración, estado y lectura de bronce listos; las historias pueden comenzar.

---

## Fase 3: Historia de Usuario 1 — Texto limpio y citable (Prioridad: P1) 🎯 MVP

**Objetivo**: convertir cada artefacto activo en un documento con texto limpio, metadatos y linaje, omitiendo con razón lo que no tenga texto.

**Prueba independiente**: procesar una muestra con HTML, PDF, VTT, JSON y XLSX y verificar que cada uno produce texto legible, conserva cifras/fechas/nombres, tiene linaje completo y que un PDF escaneado se omite con `scanned_pdf`.

### Pruebas de la Historia 1

- [X] T012 [P] [US1] Pruebas unitarias de extracción HTML en `tests/unit/silver/test_html.py`: se conserva el artículo principal, se eliminan navegación/cookies/enlaces relacionados, se preservan `h1`–`h6`, hay respaldo de título y una página vacía produce `no_text`.
- [X] T013 [P] [US1] Pruebas unitarias de extracción PDF en `tests/unit/silver/test_pdf.py`: texto por página, números de página, títulos del outline, eliminación de encabezados/pies repetidos, PDF escaneado produce `scanned_pdf`, un fixture de 100+ páginas termina sin error.
- [X] T014 [P] [US1] Pruebas unitarias del parser VTT en `tests/unit/silver/test_vtt.py`: se eliminan etiquetas `<c>`, se fusionan cues duplicados/solapados, se elimina el boilerplate `Amara.org` y `time_start`/`time_end` son monótonos.
- [X] T015 [P] [US1] Pruebas unitarias de formatos estructurados en `tests/unit/silver/test_structured.py`: JSON de YouTube aplanado a texto estable `clave: valor`, XML de sitemap omitido con `navigation_artifact`, XLSX leído sin fórmulas y una sección por hoja.
- [X] T016 [P] [US1] Pruebas unitarias de limpieza en `tests/unit/silver/test_cleaning.py`: normalización de espacios, reparación reversible de mojibake, proxy de tokens `ceil(chars/3.5)` y detección de idioma `es`/`en`/`und`.
- [X] T017 [US1] Prueba de integración en `tests/integration/silver/test_build_us1.py`: construir un catálogo bronce temporal con un artefacto por formato; verificar campos de linaje, títulos no nulos, razones de omisión y hashes del bronce sin cambios.

### Implementación de la Historia 1

- [X] T018 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/silver/extractors/html.py` con `trafilatura.extract(..., output_format="xml", include_formatting=True, favor_precision=True, with_metadata=True)` y un respaldo `lxml` que elimine `script/style/nav/header/footer/aside/form`; devolver texto, eventos de encabezado, título y metadatos.
- [X] T019 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/silver/extractors/pdf.py` con `pypdf.PdfReader`, texto por página, outline, eliminación de líneas repetidas en `>= 0.30` de las páginas y flags `scanned_pdf`, `low_text_density`, `table_heavy`, `multi_column_suspect`.
- [X] T020 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/silver/extractors/vtt.py` con un parser de la biblioteca estándar que fusione cues, elimine etiquetas y boilerplate, conserve rangos de tiempo y emita una sección titulada con el título del video.
- [X] T021 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/silver/extractors/structured.py` para aplanar el JSON de YouTube de forma determinista (`sort_keys=True`) y procesar XML de contenido con `ElementTree`; devolver una razón de omisión para XML de sitemap/robots.
- [X] T022 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/silver/extractors/spreadsheet.py` con `openpyxl.load_workbook(read_only=True, data_only=True)`, una sección por hoja, encabezados como contexto y sin evaluar fórmulas.
- [X] T023 [US1] Implementar `src/proyecto_modelos_lenguaje/silver/extractors/registry.py` para despachar por `media_type`, mapear tipos no soportados a una razón de omisión explícita y normalizar la salida de los extractores en un `ExtractedDocument` común.
- [X] T024 [US1] Extender `src/proyecto_modelos_lenguaje/silver/cleaning.py` con el pipeline de limpieza: eliminar boilerplate HTML/PDF, colapsar espacios, reparar encoding de forma reversible, llamar a `detect_language` y adjuntar flags de calidad.
- [X] T025 [US1] Implementar las etapas extraer→limpiar→documento en `src/proyecto_modelos_lenguaje/silver/pipeline.py`, incluyendo campos de linaje, estado de omisión/fallo, manejo de `no_text` y aislamiento de errores por artefacto.
- [X] T026 [US1] Implementar la salida Markdown con frontmatter YAML (`doc_id`, `title`, `url`, `source_id`, `published_at`, `retrieved_at`, `language`, `license`) en `src/proyecto_modelos_lenguaje/silver/reporting.py`, escribiendo en `data/silver/markdown/<doc_id>.md`.
- [X] T027 [US1] Añadir el subcomando `pml silver build` en `src/proyecto_modelos_lenguaje/cli.py` con `--config`, `--run`, `--limit`, `--source`, `--force` y `--json`; escribir `data/silver/documents.jsonl` y `data/silver/_meta/state.jsonl` de forma atómica.
- [X] T028 [US1] Añadir validación de invariantes del documento en `src/proyecto_modelos_lenguaje/silver/models.py`: `title`/`section_title`/`section_path` no nulos, `char_end > char_start`, IDs únicos y campos de linaje presentes en cada documento.

**Punto de control**: `pml silver build --limit 10` produce documentos y Markdown con linaje completo; la US1 es verificable de forma independiente.

---

## Fase 4: Historia de Usuario 2 — Secciones y fragmentos recuperables (Prioridad: P2)

**Objetivo**: estructurar documentos en secciones jerárquicas y fragmentos con contexto, offsets, páginas/tiempos y tokens.

**Prueba independiente**: procesar un informe extenso y una página con encabezados; verificar que cada fragmento pertenece a una sola sección, respeta `max_tokens`, incluye `section_path` y puede reconstruirse en orden.

### Pruebas de la Historia 2

- [X] T029 [P] [US2] Pruebas unitarias de secciones en `tests/unit/silver/test_sections.py`: jerarquía `h1`–`h6`, mapeo del outline PDF alineado al inicio de página, respaldo por encabezados numerados y `"sin sección"` para documentos sin título.
- [X] T030 [P] [US2] Pruebas unitarias de fragmentación en `tests/unit/silver/test_chunking.py`: objetivo/máximo/solapamiento, cortes en oraciones, sección corta como un solo fragmento, cero cruces de sección, `chunk_id` determinista y offsets que coinciden con el texto del documento.
- [X] T031 [US2] Prueba de integración en `tests/integration/silver/test_build_us2.py`: construir un catálogo temporal con una página HTML larga y un PDF multipágina; verificar secciones, `chunks.jsonl`, límites de tokens, rangos de página y `section_path` completo.

### Implementación de la Historia 2

- [X] T032 [P] [US2] Implementar `src/proyecto_modelos_lenguaje/silver/sections.py` para construir un árbol jerárquico desde encabezados HTML y outline PDF, normalizar sufijos del outline, usar encabezados numerados como respaldo y asignar `"sin sección"` con `level=0` y flag `no_section`.
- [X] T033 [P] [US2] Implementar `src/proyecto_modelos_lenguaje/silver/chunking.py` con el proxy `ceil(chars/3.5)`, cortes en límites de párrafo/oración, solapamiento configurado, sin mezclar secciones, rangos de página/tiempo y `chunk_id` determinista.
- [X] T034 [US2] Integrar las etapas de sección y fragmentación en `src/proyecto_modelos_lenguaje/silver/pipeline.py`, produciendo chunks para todos los documentos procesados; la US3 añadirá el filtro de canónicos.
- [X] T035 [US2] Escribir `data/silver/chunks.jsonl` con campos de cita (`url`, `title`, `section_path`, `page_start/page_end`, `time_start/time_end`, `retrieved_at`, `license_note`) y escritura atómica en `src/proyecto_modelos_lenguaje/silver/state.py`.
- [X] T036 [US2] Extender el resumen `--json` de `pml silver build` en `src/proyecto_modelos_lenguaje/cli.py` con `documents`, `chunks`, `section_coverage` y `quality_flags`.

**Punto de control**: documentos y chunks producidos con contexto completo; la US2 es verificable de forma independiente.

---

## Fase 5: Historia de Usuario 3 — Deduplicación y versión canónica (Prioridad: P3)

**Objetivo**: detectar duplicados exactos y cercanos, elegir un canónico por grupo y conservar alias, versiones e idiomas.

**Prueba independiente**: introducir copias exactas, versiones casi idénticas, una fuente oficial y un tercero, y dos idiomas; verificar un canónico por grupo, alias con URL y ninguna mezcla entre idiomas.

### Pruebas de la Historia 3

- [X] T037 [P] [US3] Pruebas unitarias de deduplicación en `tests/unit/silver/test_dedup.py`: coincidencia exacta SHA-256, umbral MinHash/LSH `0.90`, grupos deterministas, selección por autoridad/vigencia/completitud, separación por idioma y `subtitle_kind_unknown`.
- [X] T038 [US3] Prueba de integración en `tests/integration/silver/test_build_us3.py`: construir un catálogo temporal con duplicados y versiones; verificar `canonical_documents`, `alias_documents`, `duplicates_exact`, `duplicates_near` y que solo los canónicos aparezcan en `chunks.jsonl`.

### Implementación de la Historia 3

- [X] T039 [US3] Implementar deduplicación exacta y MinHash/LSH (128 permutaciones, shingles de 5 palabras, 16 bandas × 8 filas, semilla fija) en `src/proyecto_modelos_lenguaje/silver/dedup.py`.
- [X] T040 [US3] Implementar la selección canónica en `src/proyecto_modelos_lenguaje/silver/dedup.py`: `first_party` sobre `third_party`, versión más reciente para la misma URL y luego texto más largo; registrar alias con `reason` en `{same_text, same_url_newer, official_preferred, longer_text}`.
- [X] T041 [US3] Integrar la etapa de deduplicación antes de la publicación de chunks en `src/proyecto_modelos_lenguaje/silver/pipeline.py`: solo los documentos canónicos generan chunks; los alias conservan texto/secciones y los canónicos llevan la lista de alias.
- [X] T042 [US3] Extender los metadatos de YouTube en `src/proyecto_modelos_lenguaje/fetchers/youtube.py` con `subtitle_kinds` (manual/automático por idioma) y añadir cobertura en `tests/unit/test_youtube.py`; si falta, asignar `subtitle_kind_unknown`.
- [X] T043 [US3] Añadir `config/youtube_metadata_backfill.toml` y ejecutar una campaña de backfill solo de metadatos que cree nuevas versiones sin modificar los artefactos existentes; registrar el ID de campaña resultante en las notas de `data/silver/reports/`.

**Punto de control**: duplicados y versiones resueltos; la US3 es verificable de forma independiente.

---

## Fase 6: Historia de Usuario 4 — Calidad, reproceso e idempotencia (Prioridad: P4)

**Objetivo**: reporte de calidad verificable, estado incremental, auditoría de trazabilidad y CLI completa.

**Prueba independiente**: ejecutar dos veces sin cambios y verificar cero documentos/fragmentos nuevos; modificar un artefacto y verificar que solo ese documento se actualiza; auditar 50 fragmentos hasta la URL pública.

### Pruebas de la Historia 4

- [X] T044 [P] [US4] Pruebas de contrato en `tests/contract/silver/test_contracts.py`: validar documentos, chunks y reporte contra los tres JSON Schema, incluyendo el condicional de alias y el enum de `quality_flags`.
- [X] T045 [P] [US4] Pruebas unitarias del reporte en `tests/unit/silver/test_reporting.py`: conteos por fuente/formato/estado, totales de tokens, duplicados, cobertura de secciones, razones de omisión/fallo y renderizado Markdown.
- [X] T046 [P] [US4] Prueba de integración de idempotencia en `tests/integration/silver/test_idempotency.py`: dos ejecuciones sin cambios producen IDs/hashes idénticos; un artefacto modificado solo reprocesa ese documento; `--force` regenera.
- [X] T047 [P] [US4] Prueba de integración de auditoría en `tests/integration/silver/test_audit.py`: muestrear 50 chunks, resolver cada uno a `artifact_id`/`content_hash`/`url`, verificar `document.text[char_start:char_end]` y confirmar que los hashes del bronce no cambian.

### Implementación de la Historia 4

- [X] T048 [US4] Implementar el merge de estado incremental y caché en `src/proyecto_modelos_lenguaje/silver/state.py`: omitir `content_hash + config_hash` sin cambios, reutilizar extracción cacheada, reemplazar registros cambiados y mantener orden determinista de salida.
- [X] T049 [US4] Implementar `data/silver/reports/<run_id>/quality.json` y `quality.md` en `src/proyecto_modelos_lenguaje/silver/reporting.py` con todos los campos requeridos por `contracts/run-report.schema.json`.
- [X] T050 [US4] Implementar la orquestación de la ejecución, el aislamiento de fallos por artefacto, los filtros `--limit`/`--source` y la muestra de auditoría en `src/proyecto_modelos_lenguaje/silver/pipeline.py`.
- [X] T051 [US4] Completar los subcomandos `pml silver build|verify|report|status` en `src/proyecto_modelos_lenguaje/cli.py`, incluyendo sobres JSON y códigos de salida 0/1/2/3 de `contracts/cli.md`.
- [X] T052 [US4] Crear `scripts/build_silver.py` como envoltorio canónico que delegue en `pml silver build` y acepte `--run`, `--config`, `--limit`, `--force` y `--json`.
- [X] T053 [US4] Añadir la verificación de offline y de inmutabilidad del bronce en `src/proyecto_modelos_lenguaje/silver/pipeline.py`: sin llamadas de red, verificación de hashes antes/después y ninguna escritura bajo `data/bronze/`.
- [X] T054 [US4] Implementar la protección contra reutilización de `run_id`, la confirmación de `--force` y la preverificación de espacio de salida en `src/proyecto_modelos_lenguaje/silver/state.py` y `src/proyecto_modelos_lenguaje/cli.py`.

**Punto de control**: CLI completa, estado incremental y reporte de calidad funcionando; la US4 es verificable de forma independiente.

---

## Fase 7: Pulido y preocupaciones transversales

**Propósito**: documentación, CI, rendimiento y validación final.

- [X] T055 [P] Documentar la capa plata en `README.md`: propósito, estructura de `data/silver/`, comandos, métricas y limitaciones.
- [X] T056 [P] Crear `docs/decisions/0003-silver-layer.md` con las decisiones de dependencias (trafilatura, pypdf, proxy de tokens, MinHash propio), alternativas rechazadas y justificación de licencias.
- [X] T057 [P] Añadir o actualizar `.github/workflows/ci.yml` para ejecutar `uv sync --frozen`, `uv run ruff check .`, `uv run pytest` y las pruebas de contrato de plata en push y pull request.
- [X] T058 Ejecutar la construcción del corpus completo con `uv run python scripts/build_silver.py --run 2026-10-silver-01 --json`, confirmar `processed + skipped + failed = 557` y guardar el reporte en `data/silver/reports/2026-10-silver-01/`.
- [X] T059 Medir el PDF de 106 páginas/28 MB y la ejecución completa contra el objetivo de 30 minutos/4 GB; registrar resultados en `docs/decisions/0003-silver-layer.md` y ajustar `config/silver.toml` si es necesario.
- [X] T060 Ejecutar todos los escenarios de `specs/003-silver-medallion-layer/quickstart.md` y registrar el resultado de SC-001 a SC-014 en `specs/003-silver-medallion-layer/checklists/requirements.md`.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; comienza de inmediato.
- **Fundamentos (Fase 2)**: depende de la preparación; bloquea todas las historias.
- **US1 (Fase 3)**: depende de los fundamentos; entrega el MVP.
- **US2 (Fase 4)**: depende de los documentos de US1.
- **US3 (Fase 5)**: depende de las secciones de US2; puede comenzar después del estructurado aunque la publicación de chunks esté pendiente.
- **US4 (Fase 6)**: depende de las salidas de US1–US3.
- **Pulido (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1 (P1)**: independiente tras los fundamentos; produce documentos limpios.
- **US2 (P2)**: requiere US1; añade secciones y chunks.
- **US3 (P3)**: requiere US2; deduplica y selecciona canónicos antes de publicar chunks.
- **US4 (P4)**: requiere US3; añade reporte, estado, auditoría y CLI completa.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar antes de la implementación.
- Extractores/modelos antes de registry/pipeline.
- Etapas del pipeline antes del cableado de la CLI.
- La historia se completa y valida antes de pasar a la siguiente prioridad.

### Oportunidades de paralelización

- T004 y T005 pueden ejecutarse en paralelo tras T001–T003.
- T012–T016 pueden ejecutarse en paralelo; T018–T022 también.
- T029–T030 pueden ejecutarse en paralelo; T032–T033 también.
- T037 y T042 pueden ejecutarse en paralelo con T039.
- T044–T047 pueden ejecutarse en paralelo; T055–T057 también.
- Historias distintas pueden trabajarse en paralelo solo cuando su dependencia esté satisfecha.

---

## Ejemplo paralelo: Historia 1

```text
# Pruebas (paralelo)
Tarea: T012 Pruebas de extracción HTML en tests/unit/silver/test_html.py
Tarea: T013 Pruebas de extracción PDF en tests/unit/silver/test_pdf.py
Tarea: T014 Pruebas del parser VTT en tests/unit/silver/test_vtt.py
Tarea: T015 Pruebas de formatos estructurados en tests/unit/silver/test_structured.py
Tarea: T016 Pruebas de limpieza en tests/unit/silver/test_cleaning.py

# Extractores (paralelo, después de que las pruebas fallen)
Tarea: T018 Extractor HTML en src/proyecto_modelos_lenguaje/silver/extractors/html.py
Tarea: T019 Extractor PDF en src/proyecto_modelos_lenguaje/silver/extractors/pdf.py
Tarea: T020 Extractor VTT en src/proyecto_modelos_lenguaje/silver/extractors/vtt.py
Tarea: T021 Extractor estructurado en src/proyecto_modelos_lenguaje/silver/extractors/structured.py
Tarea: T022 Extractor de hojas de cálculo en src/proyecto_modelos_lenguaje/silver/extractors/spreadsheet.py
```

## Ejemplo paralelo: Historia 2

```text
Tarea: T029 Pruebas de secciones en tests/unit/silver/test_sections.py
Tarea: T030 Pruebas de fragmentación en tests/unit/silver/test_chunking.py

Tarea: T032 Constructor de secciones en src/proyecto_modelos_lenguaje/silver/sections.py
Tarea: T033 Fragmentación en src/proyecto_modelos_lenguaje/silver/chunking.py
```

## Ejemplo paralelo: Historia 3

```text
Tarea: T037 Pruebas de deduplicación en tests/unit/silver/test_dedup.py
Tarea: T042 Subtitle_kinds de YouTube en src/proyecto_modelos_lenguaje/fetchers/youtube.py y tests/unit/test_youtube.py
```

## Ejemplo paralelo: Historia 4

```text
Tarea: T044 Pruebas de contrato en tests/contract/silver/test_contracts.py
Tarea: T045 Pruebas del reporte en tests/unit/silver/test_reporting.py
Tarea: T046 Pruebas de idempotencia en tests/integration/silver/test_idempotency.py
Tarea: T047 Pruebas de auditoría en tests/integration/silver/test_audit.py
```

---

## Estrategia de implementación

### MVP primero (solo Historia 1)

1. Completar la Fase 1: Preparación.
2. Completar la Fase 2: Fundamentos.
3. Completar la Fase 3: US1.
4. Ejecutar `uv run pml silver build --run 2026-10-silver-00 --limit 10 --json`.
5. Validar documentos, Markdown y linaje; detenerse si el MVP es el objetivo.

### Entrega incremental

1. Preparación + Fundamentos → base lista.
2. US1 → documentos citables (MVP).
3. US2 → secciones y chunks recuperables.
4. US3 → deduplicación y canónicos.
5. US4 → estado, reporte, auditoría y CLI completa.
6. Pulido → documentación, CI, rendimiento y validación SC-001…SC-014.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 extractores + US2 secciones/chunks.
3. Roberto: US1 limpieza/Markdown + US3 dedup + US4 CLI/reporte.
4. Integrar en el orden US1 → US2 → US3 → US4 y validar cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- No se versionan datos ni PDFs de prueba; los fixtures binarios se generan en tiempo de ejecución.
- La capa bronce es de solo lectura; cualquier tarea que la modifique es un defecto.
- Los reportes y el estado viven en `data/silver/` y no se versionan.
- Las tareas T058–T060 requieren el corpus bronce activo y no deben ejecutarse en CI.
