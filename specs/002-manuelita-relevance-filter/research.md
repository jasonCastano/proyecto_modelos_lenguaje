# Phase 0 Research: Filtro de Relevancia del Corpus de Manuelita

**Feature**: `002-manuelita-relevance-filter` | **Date**: 2026-10-28 | **Plan**: [plan.md](./plan.md)

All unknowns from the Technical Context are resolved below. No unresolved clarification remains.

## Corpus Facts Used for Design

| Fact | Value |
|------|-------|
| Artifacts in catalog | 26.752 (26.746 baseline + 6 smoke), all unique content hashes |
| Raw bytes | 9.860.149.523 (9,86 GB); total with metadata 9.952.882.261 |
| Official-domain artifacts | 397 (284 HTML, 112 PDF, 1 XLSX) |
| Third-party artifacts | 26.355 |
| Third-party artifacts with a verifiable mention | 13 (1 Asocaña, 1 Cámara, 5 contextual in datos.gov.co, 4 El País), plus incidental tokens |
| Official PDFs | 112 (annual/sustainability reports, catalogs, speeches) |
| Third-party PDFs | 7 (1 Cámara, 2 SECOP, 4 Supersociedades) |
| Current coverage | 24/24, inflated by keyword matches on generic portals |
| Largest sources | datos.gov.co 10.003; Cámara de Comercio 10.486; SECOP 5.316 |

## R1. Estrategia de clasificación: reglas deterministas, sin LLM

- **Decision**: Clasificación por reglas ponderadas sobre texto normalizado, título, URL y fuente. Puntuación
  0–100 con tres umbrales: `keep ≥ 60`, `review 25–59`, `remove < 25`. El dominio oficial siempre obtiene 100.
- **Rationale**: 26.752 artefactos exigen velocidad, reproducibilidad y auditabilidad; un LLM añadiría costo,
  no determinismo, dependencia de red y dificultad para explicar cada decisión ante la evaluación académica.
- **Alternatives considered**: LLM local (costo y variabilidad); embeddings + similitud (requiere índice
  vectorial, fuera de alcance); clasificador supervisado (no hay etiquetas suficientes).

## R2. Señales y puntuación

- **Decision**:
  - `official_domain` (familia `manuelita.com`) → 100, decisión `keep` obligatoria.
  - Alias fuertes (`ingenio manuelita`, `manuelita agroindustria`, `manuelita s.a.`, `manuelita sas`,
    `grupo manuelita`) → +60.
  - Término base `manuelita` → +20.
  - Mención en título o en el primer 20% del texto → +10.
  - Términos de contexto (`valle del cauca`, `azúcar`, `caña`, `etanol`, `bioenergía`, `ingenio`, `palmira`,
    `candelaria`, `miranda`, `sector agroindustrial`, cargos directivos) → +10 cada uno, tope +30.
  - Peso de fuente (`asocana`, prensa económica) → +5.
  - Patrones negativos (homónimos, nombres de persona, canción, tortuga, finca/vereda, cooperativa) → −30 cada
    uno, tope −60.
  - Mención solo incidental (correo, URL, listado de contactos, etiqueta de dataset) → puntuación limitada a 40.
- **Rationale**: Separa mención directa, contextual y nula (FR-006), y evita que un token aislado conserve una
  página genérica de 6 MB.
- **Alternatives considered**: presencia binaria de la palabra (produce los falsos positivos actuales); solo
  dominio oficial (perdería 13 menciones externas válidas).

## R3. Homónimos y menciones incidentales

- **Decision**: Detectar patrones negativos y de contexto; si el token aparece únicamente dentro de un correo,
  una URL o una lista de contactos, la decisión máxima es `review`. Si hay dos o más señales de homónimo
  (por ejemplo “tortuga”, “canción”, nombre de persona), la decisión es `remove`.
- **Rationale**: “Manuelita” es un nombre común; el análisis encontró correos de cooperativas, “finca la
  manuelita” y “antiguo ingenio manuelita”. Estos casos no deben entrar al RAG sin revisión.
- **Alternatives considered**: eliminar todo lo que no sea dominio oficial (perdería noticias y rankings
  válidos); conservar toda coincidencia (mantendría ruido).

## R4. Extracción de texto para clasificar

- **Decision**: HTML: reutilizar `visible_text` (prefiere `<main>`/`<article>` y cae al texto completo). XML,
  JSON, CSV y texto plano: decodificar UTF-8 con reemplazo. PDF: los del dominio oficial se conservan por regla
  de dominio; los 7 PDF de terceros se envían a `review` si no se puede verificar su texto. Archivos mayores a
  8 MB se escanean en los primeros y últimos 4 MB.
- **Rationale**: Cubre el 99,9% del corpus sin añadir un parser de PDF ni procesar 244 MB de reportes oficiales
  que ya se conservan por dominio.
- **Alternatives considered**: añadir `pypdf` (dependencia nueva para 7 archivos); OCR (costo alto, innecesario).

## R5. Definición del corpus activo

- **Decision**: Vista `v_active_artifacts`: artefactos no retirados, sin cuarentena activa y con evaluación
  `keep`; los artefactos sin evaluación previa cuentan como activos para no romper el comportamiento anterior.
  Los `review` quedan fuera del corpus activo hasta que el revisor decida.
- **Rationale**: Una sola definición evita que manifiestos, exportaciones, reportes y cobertura se contradigan.
- **Alternatives considered**: borrar filas del catálogo (pierde historial); bandera en `artifacts` (mezcla
  adquisición con curaduría).

## R6. Cuarentena, purga y auditoría

- **Decision**: Mover los artefactos `remove` a `data/quarantine/<run_id>/<artifact_id>/<hash>.<ext>` con
  `os.replace`; registrar `quarantine_entries` y `curation_audit` antes de mover. Retención por defecto: 30 días.
  La purga definitiva requiere run aprobado, `--confirm` y retención vencida o `--now`. El audit conserva URL,
  hash, tamaño, motivo, puntuación y fechas aunque el archivo desaparezca.
- **Rationale**: Libera espacio (SC-005) manteniendo una ventana de reversibilidad y trazabilidad (Principio III).
- **Alternatives considered**: cuarentena permanente (no libera 9,5 GB); borrado directo (irreversible y sin
  auditoría); borrado sin mover (riesgo de inconsistencia si falla a mitad).

## R7. Idempotencia y decisiones manuales

- **Decision**: Una evaluación vigente por artefacto (`artifact_id` único) con `manual_override`. Re-ejecutar el
  análisis actualiza solo evaluaciones automáticas cuyo `content_hash` no cambió; las manuales nunca se
  sobrescriben. Las acciones de cuarentena/purga son idempotentes por `artifact_id` y estado.
- **Rationale**: Cumple FR-016/FR-017 y evita que una segunda pasada revierta decisiones humanas.
- **Alternatives considered**: historial completo de evaluaciones (más complejo); sobrescribir todo (pierde
  revisión).

## R8. Revisión humana por CLI

- **Decision**: `pml curate review list` y `pml curate review decide` con revisor, nota y fecha; los casos
  `review` se listan con URL, título, fragmento, puntuación y motivo. La decisión manual actualiza la evaluación
  y el ítem de revisión.
- **Rationale**: Satisface P4 sin interfaz web ni herramienta adicional; el revisor es el responsable del
  proyecto.
- **Alternatives considered**: hoja de cálculo externa (no auditable); UI web (fuera de alcance).

## R9. Recalculo de cobertura

- **Decision**: La matriz de 24 ítems usa `v_active_artifacts`; la evidencia de artefactos eliminados se ignora.
  Para los conservados se reutiliza la evidencia existente y se recalcula el estado. Los vacíos reciben una
  razón y una recomendación de fuente.
- **Rationale**: Corrige el 24/24 inflado sin reescribir la evidencia histórica de adquisición.
- **Alternatives considered**: borrar toda la evidencia y recalcular desde cero (pierde trazabilidad de la
  campaña); confiar en el reporte actual (falso positivo).

## R10. Validación contra línea base

- **Decision**: Muestra estratificada de 200 artefactos: 100 preseleccionados como relevantes (397 oficiales +
  13 menciones) y 100 aleatorios del resto. Se etiqueta manualmente; 100 se usan para ajustar umbrales y 100
  como test. Métricas: precisión de `keep` (SC-003 ≥95%), falsos negativos de `remove` (SC-004 <1%) y tasa de
  `review`.
- **Rationale**: Cumple el Principio II con una línea base definida antes de ajustar y evita evaluar sobre los
  mismos casos usados para calibrar.
- **Alternatives considered**: confiar en el análisis preliminar (sesgo); etiquetar los 26.752 (inviable).

## R11. Rendimiento y memoria

- **Decision**: Procesamiento secuencial en streaming, lectura con tope de 8 MB por archivo, escrituras SQLite
  por lotes (`executemany`, transacciones de 500), sin cargar el corpus en memoria. Objetivo: <30 minutos;
  techo del spec: 2 horas.
- **Rationale**: El análisis preliminar de 9,86 GB ya se ejecutó en minutos con lectura secuencial; la
  simplicidad supera a un pool de procesos.
- **Alternatives considered**: multiprocessing (más memoria y complejidad); base vectorial (innecesaria).

## R12. Configuración y seguridad

- **Decision**: `config/relevance.toml` versionado con términos, alias, patrones negativos, umbrales, dominios
  protegidos y retención; hash por ejecución. `analyze` es dry-run por defecto; `apply`, `approve`, `quarantine`
  y `purge` exigen confirmación explícita. Guardas: dominio oficial, decisión manual `keep`, rutas dentro de
  `data/`, verificación de hash antes de mover/restaurar.
- **Rationale**: Cumple FR-014/FR-019 y evita eliminar por error.
- **Alternatives considered**: configuración por variables de entorno (no reproducible); flags sin confirmación
  (riesgo destructivo).

## R13. Reporte de depuración

- **Decision**: `reports/<run_id>/curation.json` y `summary.md` con conteos por fuente, decisiones, niveles,
  bytes antes/después/liberados, muestra de conservados y eliminados, y advertencias.
- **Rationale**: Satisface FR-018/SC-012 y permite revisar sin consultar SQL.
- **Alternatives considered**: solo salida de consola (no auditable).

## R14. Sin nuevas dependencias

- **Decision**: Reutilizar `sqlite3`, `hashlib`, `re`, `json`, `shutil` y la extracción existente; no se añaden
  paquetes de runtime ni servicios.
- **Rationale**: Principio V; el problema se resuelve con reglas y datos ya presentes.
- **Alternatives considered**: `pypdf` (7 archivos), LLM (costo), motor de búsqueda (índice adicional).

## Resolved Unknowns Summary

| Topic | Resolution |
|-------|------------|
| Classification method | Deterministic weighted rules, 0–100 |
| Thresholds | keep ≥60, review 25–59, remove <25 |
| Official domain | Always keep, score 100 |
| Namesakes | Negative patterns; incidental tokens capped at review |
| PDFs | Official kept by domain; third-party → review |
| Active corpus | `v_active_artifacts` (keep only, no active quarantine) |
| Deletion | 30-day quarantine then approved purge, permanent audit |
| Idempotency | One evaluation per artifact; manual overrides preserved |
| Coverage | Recalculated over active corpus |
| Validation | Stratified 200-item manual sample, 100/100 split |
| Performance | Streaming, 8 MB scan cap, <30 min target |
| Dependencies | None new |
