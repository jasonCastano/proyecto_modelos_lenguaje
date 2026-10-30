# Research: Capa Plata (Silver)

**Feature**: `003-silver-medallion-layer` | **Date**: 2026-10-29

Este documento resuelve las decisiones técnicas de la especificación. No quedan incógnitas pendientes.

---

## 1. Extracción de contenido principal en HTML

- **Decision**: usar `trafilatura` como extractor principal, con `favor_precision=True`,
  `include_tables=True`, `include_formatting=True`, `output_format="xml"` y `with_metadata=True`. Si no devuelve
  texto útil, aplicar un respaldo con `lxml` que elimina `script/style/nav/header/footer/aside/form` y elige el
  contenedor con mayor densidad de texto.
- **Rationale**: en una página real de noticias de Manuelita, `trafilatura` extrajo el artículo correcto
  (4.024 caracteres) y conservó los encabezados como `<head rend="h1">` y `<head rend="h5">`, lo que permite
  construir secciones. También devolvió título, fecha, URL y sitio. `readability-lxml` eligió un artículo
  relacionado en la misma página y perdió el contenido principal; un extractor propio con `lxml` requeriría
  reglas específicas del sitio y sería frágil. El `title` del documento se toma del bronce; si falta, del primer
  `h1`; el `<title>` genérico del sitio solo se usa como último recurso.
- **Alternatives considered**:
  - `readability-lxml` (Apache-2.0): descartado por la selección incorrecta observada.
  - Extractores propios por selectores CSS: descartados por acoplarse a la plantilla de un sitio y no
    generalizar a la Fundación, El País u otras fuentes.
  - `unstructured`/`docling`: descartados por peso, modelos y dependencias innecesarias para esta etapa.

## 2. Extracción de PDF

- **Decision**: `pypdf` para texto por página y para leer el índice/outline del documento.
- **Rationale**: `pypdf` es BSD-3-Clause, puro Python y funcionó sobre el corpus real. En un PDF de 28 MB y 106
  páginas extrajo texto y 19 entradas de outline; en un PDF de una página extrajo la tabla completa. La licencia
  es compatible con MIT y no requiere binarios externos.
- **Alternatives considered**:
  - `PyMuPDF`/`fitz`: mejor calidad y velocidad, pero **AGPL-3.0**, incompatible con la distribución MIT del
    proyecto.
  - `pdfplumber` (MIT): mejor para tablas y coordenadas, pero más lento; se reserva para una mejora futura si la
    muestra de calidad lo exige.
  - `pdfminer.six` directo: más control de layout, pero más código y menor velocidad.
  - OCR (Tesseract/`ocrmypdf`): fuera de alcance por la especificación; los PDF sin capa de texto se omiten con
    razón.

## 3. Eliminación de boilerplate en PDF

- **Decision**: eliminar líneas repetidas en al menos 30% de las páginas (normalizadas) y líneas que coincidan con
  patrones de paginación (`Página X de Y`, `Page X of Y`), códigos de formulario y avisos legales repetidos.
  Conservar la primera aparición si la línea aporta contenido y marcar la eliminación en el reporte.
- **Rationale**: el PDF de prueba repite `Código`, `Versión`, `Página 1 de 1` en cada página. Esas líneas no
  aportan conocimiento y contaminan los fragmentos. El umbral del 30% evita borrar frases legítimas que aparecen
  una o dos veces.
- **Alternatives considered**:
  - Eliminar solo por expresiones regulares: no cubre encabezados variables de cada informe.
  - No eliminar: conserva ruido y sesga la recuperación.

## 4. Detección de secciones

- **Decision**:
  - HTML: usar los encabezados `h1`–`h6` preservados por `trafilatura`, construyendo una pila jerárquica.
  - PDF: usar el outline de `pypdf` cuando existe; si no, detectar encabezados numerados
    (`^\d+(\.\d+)*\s+\S`) y líneas en mayúsculas cortas; si no hay evidencia, asignar `"sin sección"` y marcar
    `no_section`.
  - VTT/JSON: una sola sección titulada con el título del video o del registro.
- **Rationale**: el outline del informe de 106 páginas trae títulos útiles aunque con sufijos internos
  (`01-NuestraOrg-cifras-hitos-presencia_VFBAJA`); se normalizan para la ruta de sección. En PDF, el corte de
  sección se alinea al inicio de la página indicada por el outline; no se intenta precisión intra-página. El
  fallback por regex es honesto y no inventa jerarquías.
- **Alternatives considered**:
  - Inferir jerarquía por tamaño de fuente: `pypdf` no expone tamaños de fuente de forma simple; requeriría
    `pdfminer`/`pdfplumber` y más complejidad.
  - Un solo bloque sin secciones: incumple FR-009/FR-010 y empeora las citas.

## 5. Conteo de tokens

- **Decision**: proxy determinista `tokens = ceil(caracteres / 3.5)`, configurable
  (`chunking.chars_per_token`), aplicado sobre el texto normalizado.
- **Rationale**: la ejecución debe ser offline desde un clon limpio (SC-014). `tiktoken` descarga el vocabulario
  `cl100k_base` desde un blob de OpenAI en la primera ejecución, por lo que no cumple ese requisito. Un tokenizador
  de modelo (por ejemplo, el de un modelo multilingüe) también exigiría descargar archivos. El proxy es
  conservador para español (3,5 caracteres por token), no requiere red y es estable entre ejecuciones.
- **Alternatives considered**:
  - `tiktoken` (MIT): descartado por la descarga de vocabulario y la dependencia de OpenAI.
  - Tokenizador de `transformers`: descartado por el peso y la descarga de vocabulario/modelo.
  - Conteo de palabras: subestima tokens en español y puede exceder el contexto del modelo.
- **Follow-up**: recalibrar el proxy con el tokenizador del modelo elegido en el Módulo 1 y registrar el cambio de
  configuración.

## 6. Deduplicación exacta y cercana

- **Decision**:
  - Exacta: SHA-256 sobre el texto normalizado (minúsculas, espacios colapsados, sin puntuación de borde).
  - Cercana: MinHash con 128 permutaciones sobre shingles de 5 palabras y LSH de 16 bandas × 8 filas; umbral de
    Jaccard 0,90. Implementación propia con `hashlib` y semilla fija.
  - Canónico: mayor autoridad (`first_party` > `third_party`), luego versión más reciente, luego mayor
    completitud (más caracteres).
- **Rationale**: 557 documentos permiten un enfoque determinista y acotado sin añadir `datasketch`, que arrastra
  `scipy` (35,6 MB) y `numpy`, y sin depender de un servicio externo. La semilla fija y los shingles hacen que los
  grupos sean reproducibles.
- **Alternatives considered**:
  - `datasketch` (MIT): buena API, pero añade `scipy` y complejidad de instalación.
  - SimHash: más rápido, pero menos preciso para near-duplicates con reordenamientos.
  - Comparación pairwise con `rapidfuzz`: precisa, pero O(n²) sobre textos largos y con umbral difícil de calibrar.

## 7. Detección de idioma

- **Decision**: reutilizar `detect_language` del paquete (`extractors/language.py`) sobre el texto limpio y
  ampliar su muestra a los primeros 4.000 tokens. Si el resultado es `und`, conservar `und` y marcar
  `language_unknown`.
- **Rationale**: ya existe un detector determinista de español/inglés basado en stopwords, probado en el bronce.
  No requiere red ni modelos y cubre los dos idiomas del corpus.
- **Alternatives considered**:
  - `langdetect` (Apache-2.0): no determinista sin semilla y otra dependencia.
  - `lingua-language-detector`: precisa pero pesada y con modelos grandes.

## 8. Transcripciones VTT

- **Decision**: parser propio con la biblioteca estándar. Se leen cues, se eliminan etiquetas `<c>`, se
  normalizan espacios, se descartan cues vacíos o de boilerplate (`Amara.org`, “gracias por ver”), se fusionan
  cues solapados y se conserva `start`/`end` por bloque. La sección es el título del video. Cuando el bronce
  declare `subtitle_kinds`, se prefiere la variante manual; si no, se agrupan por similitud y se marca
  `subtitle_kind_unknown`.
- **Rationale**: el bronce ya contiene VTT de YouTube, incluidos automáticos y manuales; el formato es simple y no
  justifica una dependencia. Los rangos de tiempo permiten citar el minuto del video.
- **Alternatives considered**:
  - `webvtt-py`: correcto, pero añade dependencia para un formato que se resuelve en ~80 líneas.
  - Convertir a texto plano sin tiempos: pierde la citación temporal que exige FR-014.

## 9. JSON de metadatos y XML

- **Decision**: los JSON de YouTube se convierten en un registro estructurado legible (`clave: valor`, listas
  indexadas), con el título del video como sección. Los XML de sitemap/robots se omiten con razón
  `navigation_artifact`; un XML de contenido se procesaría con `ElementTree` y texto por elemento.
- **Rationale**: los 44 JSON son metadatos de video, no narrativa; aplanarlos permite recuperar canal, fecha,
  duración y descripción sin crear documentos vacíos. Los 10 XML activos son sitemaps y no aportan conocimiento.
- **Alternatives considered**:
  - Ignorar todos los JSON: pierde metadatos útiles para citas y contexto.
  - Indexar el JSON crudo: ruido de llaves y comillas, difícil de citar.

## 10. Hojas de cálculo

- **Decision**: `openpyxl` en modo `read_only`, valores calculados (nunca fórmulas), una sección por hoja y
  filas convertidas a texto tabulado con encabezados. Si la hoja está vacía, se omite.
- **Rationale**: solo hay una hoja activa; `openpyxl` es MIT, pure Python y suficiente. No se ejecutan fórmulas
  por seguridad.
- **Alternatives considered**:
  - `pandas`: pesado para una sola hoja y añade `numpy`/`pyarrow`.
  - `csv` manual: no aplica a XLSX.

## 11. Estado incremental y escritura

- **Decision**: `data/silver/_meta/state.jsonl` con una línea por artefacto:
  `artifact_id`, `content_hash`, `config_hash`, `status`, `doc_id`, `documents`, `chunks`, `processed_at`.
  Se procesan todas las versiones activas; al deduplicar, la versión más reciente por URL canónica es la
  canónica y las anteriores quedan como alias con `reason = same_url_newer`.
  Las salidas `documents.jsonl` y `chunks.jsonl` se reescriben de forma atómica (temporal + rename) al final de
  cada ejecución, en orden determinista por `artifact_id` y orden de fragmento. Caché de extracción por
  `content_hash + config_hash` en `data/silver/_meta/cache/`.
- **Rationale**: con 557 artefactos, reescribir JSONL es barato y evita una base de datos nueva. El estado permite
  saltar artefactos sin cambios y el cache evita repetir la extracción. La escritura atómica evita corpus
  parciales.
- **Alternatives considered**:
  - SQLite: útil para consultas, pero añade esquema y migraciones sin necesidad para este volumen.
  - Append-only: complica la sustitución de documentos cuando cambia un artefacto.

## 12. Formato de salida y frontmatter

- **Decision**:
  - `documents.jsonl`: un registro por documento (canónico o alias), con texto completo, secciones y linaje.
  - `chunks.jsonl`: un registro por fragmento canónico (texto, offsets, tokens, páginas/tiempos, linaje).
  - `markdown/<doc_id>.md`: representación legible con frontmatter YAML (`doc_id`, `title`, `url`, `source_id`,
    `published_at`, `retrieved_at`, `language`, `license`).
  - `reports/<run_id>/quality.{json,md}`.
- **Rationale**: cumple FR-022/FR-023 y la constitución (§3.3). JSONL es fácil de consumir por la app y Markdown
  facilita la revisión humana.
- **Alternatives considered**:
  - Un archivo por documento en JSON: más archivos y peor para carga masiva.
  - Solo Markdown: difícil de validar y consumir por la app.

## 13. Identificadores y citas

- **Decision**:
  - `doc_id = "doc_" + sha256(url_canonical + ":" + content_hash)[:16]`, para que dos artefactos con el mismo
    contenido pero distinta URL tengan documentos distintos, y para que el ID no dependa de los IDs internos
    del catálogo.
  - `section_id = doc_id + "-s" + orden(3)`.
  - `chunk_id = doc_id + "-s" + orden(3) + "-c" + orden(4)`.
  - Cada chunk incluye `url`, `title`, `section_path`, `page_start/page_end` o `time_start/time_end` y
    `retrieved_at` para citar.
- **Rationale**: los IDs dependen de la URL canónica y del contenido de entrada, no de rutas absolutas, de la
  campaña ni de los IDs autoincrementales del catálogo; son estables entre ejecuciones y reconstrucciones,
  permiten distinguir duplicados y reconstruir la cita.
- **Alternatives considered**:
  - UUID aleatorio: rompe la idempotencia y la reproducibilidad.
  - Hash del texto del chunk: dos chunks idénticos en documentos distintos colisionarían y perderían linaje.

## 14. Flags de calidad y umbrales

- **Decision**: flags versionados:
  `no_text`, `scanned_pdf`, `encrypted_pdf`, `low_text_density`, `table_heavy`, `multi_column_suspect`,
  `encoding_repaired`, `no_section`, `short_section`, `near_duplicate`, `exact_duplicate`, `language_unknown`,
  `subtitle_kind_unknown`.
  Umbrales iniciales: texto útil <100 caracteres → `no_text`; densidad <50% de caracteres alfabéticos →
  `low_text_density`; más de 30% de líneas con dos o más columnas de espacios → `table_heavy`.
- **Rationale**: los flags son observables y testeables; permiten excluir o revisar sin borrar información. Los
  umbrales quedan en `config/silver.toml`.
- **Alternatives considered**:
  - Descartar automáticamente todo lo dudoso: perdería contenido válido.
  - No marcar: el reporte no permitiría priorizar revisión.

## 15. Dependencias y licencias

| Dependencia | Versión probada | Licencia | Uso |
|-------------|-----------------|----------|-----|
| `trafilatura` | 2.3.1 | Apache-2.0 | Contenido principal HTML y metadatos |
| `pypdf` | 6.21.4 | BSD-3-Clause | Texto y outline de PDF |
| `cryptography` | 50.0.2 | Apache-2.0 / BSD-3-Clause | PDF cifrados |
| `openpyxl` | 3.1.5 | MIT | Hojas de cálculo |
| `lxml` | 6.1.3 | BSD-3-Clause | Respaldo HTML |
| `PyYAML` | 6.0.3 | MIT | Frontmatter |
| `jsonschema` | ya instalada (dev) | MIT | Contratos |
| `pytest` / `ruff` | ya instaladas (dev) | MIT | Pruebas y lint |

Todas son compatibles con la licencia MIT del proyecto. `PyMuPDF` se descartó por AGPL y `datasketch` por
arrastrar `scipy`.

## 16. Rendimiento y validación

- **Decision**: medir con un subconjunto representativo (página HTML, PDF de 1 página, PDF de 106 páginas, VTT y
  JSON) y luego con el corpus completo. Guardar `duration_seconds` y bytes por etapa en el reporte.
- **Rationale**: el PDF más grande es el caso limitante; medir primero evita descubrir el problema al final.
- **Criterio**: ≤30 minutos y ≤4 GB de memoria para 557 artefactos; si se excede, procesar PDF por página y
  reducir concurrencia.

## 17. Riesgos residuales

- La extracción de tablas complejas en PDF puede intercalar columnas; se marca y se revisa, no se corrige con
  IA.
- El proxy de tokens no coincide exactamente con el modelo final; se recalibrará.
- Los PDF escaneados quedan fuera hasta que exista una etapa OCR aprobada.
- Los títulos nulos del bronce (114) se resolverán por la estructura detectada o quedarán como
  `"sin sección"` con flag, nunca nulos.
