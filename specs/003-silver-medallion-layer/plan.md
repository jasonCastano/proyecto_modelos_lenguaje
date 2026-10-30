# Implementation Plan: Capa Plata (Silver) de la Arquitectura Medallion

**Branch**: `003-silver-medallion-layer` | **Date**: 2026-10-29 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/003-silver-medallion-layer/spec.md`

## Summary

Construir un pipeline determinista y offline que convierta los 557 artefactos activos tras el backfill de metadatos del bronce en una capa
plata lista para recuperación: texto limpio y verificable, secciones jerárquicas, fragmentos con contexto y
metadata, deduplicación exacta y cercana, y un reporte de calidad con trazabilidad completa. El proceso no usa
LLM, embeddings, OCR ni red; no modifica el bronce.

La implementación se integra al paquete existente y a la CLI `pml`, reutiliza el catálogo bronce en modo lectura
y produce JSONL, Markdown con frontmatter y reportes versionados. Se apoya en cinco etapas visibles: extraer,
limpiar, estructurar, deduplicar y fragmentar/auditar.

## Technical Context

**Language/Version**: Python 3.14 (misma versión del proyecto, gestionada con `uv`).

**Primary Dependencies**: `trafilatura>=2.3` (Apache-2.0) para contenido principal HTML y metadatos; `pypdf>=6.21`
(BSD-3-Clause) para PDF y su índice; `cryptography>=3.1` para PDF cifrados; `openpyxl>=3.1` (MIT) para hojas de
cálculo; `lxml>=6.1` (BSD-3-Clause) como respaldo de extracción HTML; `PyYAML>=6.0` (MIT) para frontmatter. Se
reutilizan `scrapling`/`yt-dlp` solo como dependencias existentes del bronce y `jsonschema` para validar
contratos.

**Storage**: sistema de archivos para las salidas (`data/silver/`), lectura de solo lectura del catálogo bronce
(`data/bronze/_meta/bronze.sqlite3`) y estado incremental en JSONL. No se crea base de datos nueva.

**Testing**: `pytest` con pruebas unitarias, de contrato (JSON Schema) e integración sobre un catálogo bronce
temporal; sin red. Ruff para lint y formato.

**Target Platform**: CLI multiplataforma; desarrollo en Windows 11 y ejecución en Linux/CI. Sin interfaz gráfica.

**Project Type**: proyecto único de librería + CLI sobre el paquete `proyecto_modelos_lenguaje`.

**Performance Goals**: procesar 557 artefactos / 290,5 MB en ≤30 minutos en 4 núcleos y 8 GB; memoria pico
≤4 GB; segunda ejecución sin cambios en ≤2 minutos gracias al estado incremental y la caché de extracción.

**Constraints**: 100% offline; sin LLM, embeddings, OCR ni traducción; bronce inmutable; se procesan todas las
versiones activas y la más reciente por URL canónica es la canónica; salidas deterministas; tope de
almacenamiento global de 10 GB (la plata solo agrega texto derivado); datos no versionados.

**Scale/Scope**: 557 artefactos activos (322 HTML, 113 PDF, 76 JSON, 35 VTT, 10 XML, 1 XLSX), 114 títulos
nulos, PDF de hasta 28 MB y 106+ páginas; se estiman entre 8.000 y 15.000 fragmentos.

**Dependencia de bronce identificada**: el JSON de metadatos de YouTube no distingue si un subtítulo es manual
o automático. Para cumplir FR-019, la implementación incluye un backfill corto de metadatos que agregue
`subtitle_kinds` a los videos con subtítulos; el backfill crea nuevas versiones de metadatos y no altera los
artefactos existentes. Si el metadato no está disponible, la capa plata agrupa las variantes por similitud y
marca `subtitle_kind_unknown` en el reporte. No se modifica el contenido de los VTT.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cumplimiento | Evidencia en el plan |
|--------------------------|--------------|----------------------|
| I. Reproducibilidad experimental | PASS | Dependencias fijadas en `uv.lock`, configuración versionada con hash, IDs deterministas, ejecución offline y regeneración desde bronce. |
| II. Evaluación con métricas y línea base | PASS | Reporte de calidad por ejecución, métricas de cobertura, omisiones, duplicados y tiempos; escenarios de quickstart verificables. |
| III. Procedencia y ética de datos | PASS | Linaje completo por fragmento, sin scraping nuevo, sin datos privados y respeto de la curaduría vigente. |
| IV. Experimentos como código versionado | PASS | Configuración `config/silver.toml`, contratos JSON Schema, pruebas y reportes versionados por ejecución. |
| V. Simplicidad y alcance académico | PASS | Sin base de datos nueva, sin LLM ni embeddings, seis dependencias justificadas y una sola etapa del medallion. |
| Datos y capas medallion (CONSTITUTION §3.3) | PASS | Salidas en `data/silver/`, JSONL y Markdown con frontmatter, metadata obligatoria y deduplicación por hash. |
| Pipeline y reproducibilidad (§3.4, §3.8) | PASS | Etapas visibles, idempotencia, pruebas offline y ejecución canónica documentada. |
| Seguridad y datos no versionados (§3.9) | PASS | Sin credenciales ni red; `data/` fuera de Git; solo se lee bronce. |

**Resultado**: sin violaciones. No se requiere justificación en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/003-silver-medallion-layer/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, campos y transiciones
├── quickstart.md        # Fase 1: guía de validación end-to-end
├── contracts/           # Fase 1: esquemas de documento, fragmento y reporte
│   ├── document.schema.json
│   ├── chunk.schema.json
│   ├── run-report.schema.json
│   └── cli.md
├── checklists/
│   └── requirements.md  # Validación de la especificación
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── cli.py                       # Nuevo subcomando `pml silver`
├── config.py                    # Configuración existente (se reutiliza)
├── models.py                    # Modelos existentes del bronce
└── silver/
    ├── __init__.py
    ├── models.py                # Documento, Sección, Fragmento, Estado, Reporte
    ├── config.py                # Carga y hash de config/silver.toml
    ├── extractors/
    │   ├── __init__.py
    │   ├── registry.py          # Despacho por media_type
    │   ├── html.py              # trafilatura + respaldo lxml
    │   ├── pdf.py               # pypdf, páginas, outline y boilerplate
    │   ├── vtt.py               # Cues, solapamientos y rangos de tiempo
    │   ├── structured.py        # JSON de YouTube y XML de contenido
    │   └── spreadsheet.py       # openpyxl, valores y hojas
    ├── cleaning.py              # Normalización, encoding y líneas repetidas
    ├── sections.py              # Jerarquía de encabezados y fallback
    ├── chunking.py              # Proxy de tokens, cortes y solapamiento
    ├── dedup.py                 # Hash exacto + MinHash/LSH propio
    ├── state.py                 # Estado incremental JSONL y escritura atómica
    ├── reporting.py             # quality.json / quality.md
    └── pipeline.py              # Orquestador de las cinco etapas

config/
└── silver.toml                  # Umbrales, reglas y rutas de la capa plata

scripts/
└── build_silver.py              # Entrada canónica, delega en `pml silver build`

tests/
├── unit/silver/                 # Limpieza, secciones, chunking, dedup, lectores
├── contract/silver/             # Validación de los JSON Schema
└── integration/silver/          # Catálogo bronce temporal, idempotencia, auditoría
```

**Structure Decision**: se elige la estructura de proyecto único existente. La lógica vive en
`src/proyecto_modelos_lenguaje/silver/` para reutilizar el paquete, los modelos y la CLI; los scripts quedan como
envoltorios operativos y las pruebas siguen la separación unit/contract/integration ya usada por el bronce.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. Extracción HTML con `trafilatura` y respaldo `lxml`, porque conserva el artículo principal y los encabezados.
2. Extracción PDF con `pypdf` (licencia BSD y buen rendimiento), usando el índice del PDF y expresiones de
   encabezado como respaldo.
3. Conteo de tokens con un proxy determinista de caracteres, porque `tiktoken` descarga vocabulario y rompe la
   reproducibilidad offline.
4. Deduplicación exacta por hash y cercana con MinHash/LSH propio, evitando `datasketch` y su dependencia de
   `scipy`.
5. Estado incremental en JSONL con escritura atómica, sin añadir una base de datos.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md): entidades, campos, invariantes y transiciones de estado.
- [contracts/document.schema.json](./contracts/document.schema.json): registro de documento plata.
- [contracts/chunk.schema.json](./contracts/chunk.schema.json): registro de fragmento recuperable.
- [contracts/run-report.schema.json](./contracts/run-report.schema.json): reporte de calidad por ejecución.
- [contracts/cli.md](./contracts/cli.md): comandos, argumentos y códigos de salida.
- [quickstart.md](./quickstart.md): validación end-to-end y escenarios de auditoría.

### Data flow

```text
bronce activo (solo lectura)
        │
        ▼
[1] extraer ──► texto + estructura + páginas/tiempos
        │
        ▼
[2] limpiar ──► normalización, encoding, boilerplate
        │
        ▼
[3] estructurar ──► secciones jerárquicas y títulos
        │
        ▼
[4] deduplicar ──► duplicados exactos/cercanos, canónicos y alias
        │
        ▼
[5] fragmentar/auditar ──► chunks solo de canónicos, flags y reporte
        │
        ▼
data/silver/{documents,chunks}.jsonl + markdown/ + reports/
```

### Delivery slices

| Slice | Alcance | Requisitos cubiertos | Validación |
|-------|---------|----------------------|------------|
| S1 | Lectores HTML/PDF/VTT/JSON/XLSX y limpieza | FR-003, FR-005–FR-008, FR-020, FR-025 | Muestra por formato; texto coincide con bronce |
| S2 | Secciones, chunks y offsets | FR-009–FR-015, FR-022–FR-024 | Informe extenso y página con encabezados |
| S3 | Deduplicación y canónicos | FR-016–FR-019 | Copias exactas, versiones y variantes de idioma |
| S4 | Estado, reporte y auditoría | FR-001, FR-002, FR-021, FR-026–FR-033 | Doble ejecución, cambio de un artefacto, muestra de 50 |

Cada slice es demostrable por separado; S1 ya entrega texto citable, S2 lo hace recuperable y S3–S4 lo hacen
confiable y reproducible. En la integración final, S3 se ejecuta antes de publicar los chunks: solo los
documentos canónicos se fragmentan.

## Phase 1 Re-check — Constitution

| Principio | Re-evaluación | Resultado |
|-----------|---------------|-----------|
| Reproducibilidad | IDs y hashes deterministas, configuración versionada, sin red | PASS |
| Métricas | Reporte por ejecución y contratos verificables | PASS |
| Procedencia | Linaje documento → artefacto → URL en cada chunk | PASS |
| Simplicidad | Seis dependencias, sin DB ni LLM | PASS |
| Datos/medallion | JSONL, Markdown, metadata y dedup por hash | PASS |

Sin violaciones después del diseño. No se requiere Complexity Tracking.

## Risks and Mitigations

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| PDF escaneados o con columnas intercaladas | Texto incompleto o desordenado | Detección de densidad y flags; omitir sin inventar; revisión muestral |
| PDF grandes (28 MB) | Tiempo o memoria excesivos | Procesamiento por página, límites de memoria y prueba de rendimiento |
| HTML con el artículo principal mal detectado | Contenido perdido o ruido | `trafilatura` con `favor_precision` + respaldo lxml + flags de calidad |
| Token proxy alejado del modelo final | Chunks mayores o menores de lo previsto | Documentar el proxy y recalibrar con el tokenizador del Módulo 1 |
| Duplicados cercanos costosos | Tiempo O(n²) | MinHash/LSH con bandas y umbral 0,90; bloqueo por similitud |
| Cambios de configuración | IDs y chunks distintos | `config_hash` en estado y reporte; regeneración explícita |
| Subtítulos manuales y automáticos sin distinguir | FR-019 no se puede cumplir con certeza | Backfill de `subtitle_kinds`; si falta, agrupar y marcar `subtitle_kind_unknown` |

## Complexity Tracking

Sin violaciones de la constitución; no hay complejidad adicional que justificar.
