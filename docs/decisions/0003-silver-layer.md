# ADR 0003 — Capa plata (silver) del medallion

- **Estado**: aceptada
- **Fecha**: 2026-10-29
- **Autores**: Jason Alejandro Castaño, Roberto José Guerrero
- **Contexto**: Módulo 1 del curso, base de conocimiento de Manuelita

## Contexto

El bronce contiene 557 artefactos activos (290 MB): 322 HTML, 113 PDF, 76 JSON, 35 VTT, 10 XML y 1 XLSX.
Para alimentar las tareas de LangChain se necesita texto limpio, secciones, fragmentos recuperables y
trazabilidad, sin usar LLM, embeddings ni OCR en esta etapa.

## Decisiones

1. **HTML**: `trafilatura` 2.3.1 (Apache-2.0) como extractor principal, con respaldo `lxml`. Conserva el
   artículo principal y los encabezados; `readability-lxml` eligió un artículo relacionado en una prueba real.
2. **PDF**: `pypdf` 6.21 (BSD-3-Clause), texto por página y outline. `PyMuPDF` se descartó por AGPL.
   `cryptography` se añadió para PDF cifrados; si no se pueden descifrar sin credenciales, se omiten.
3. **Tokens**: proxy offline `ceil(caracteres / 3.5)`. `tiktoken` descarga su vocabulario y rompe SC-014.
4. **Duplicados**: SHA-256 sobre texto normalizado para exactos; MinHash/LSH propio (128 permutaciones,
   shingles de 5 palabras, 16 bandas × 8 filas, semilla fija) para cercanos. `datasketch` se descartó porque
   arrastra `scipy` (35,6 MB).
5. **Estado**: JSONL incremental (`_meta/state.jsonl`) con escritura atómica y caché por
   `content_hash + config_hash`; no se añadió base de datos.
6. **Identificadores**: `doc_id = sha256(url_canonical:content_hash)[:16]`; `section_id` y `chunk_id`
   derivados del documento y del orden estructural.
7. **Secciones**: encabezados HTML y outline PDF; para PDF el corte se alinea al inicio de página. Sin
   encabezados se usa el título del documento o `"sin sección"`; nunca queda nulo.
8. **Deduplicación**: se conserva un canónico por grupo y los alias mantienen texto/secciones para auditoría,
   pero no generan fragmentos recuperables. La autoridad, la versión y la longitud definen el canónico.
9. **Salidas**: `documents.jsonl`, `chunks.jsonl`, Markdown con frontmatter YAML y reportes `quality.{json,md}`
   bajo `data/silver/`.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| `PyMuPDF` | Licencia AGPL incompatible con MIT |
| `pdfplumber` | MIT, pero más lento para 113 PDF; se reserva para una mejora de tablas |
| `tiktoken` | Descarga de vocabulario; no es offline |
| `datasketch` | Dependencia de `scipy` (35,6 MB) |
| `readability-lxml` | Selección incorrecta del artículo principal en prueba real |
| SQLite para plata | Innecesario para 557 artefactos; JSONL + estado es suficiente |
| OCR en esta etapa | Fuera de alcance y costoso; se declara como vacío |

## Consecuencias

- La capa plata es reproducible desde bronce sin red y sin modificar el bronce.
- Los PDF escaneados/cifrados y los sitemaps quedan fuera con razón explícita.
- El proxy de tokens debe recalibrarse cuando se elija el modelo del Módulo 1.
- Los alias no se indexan; si el Módulo 2 necesita auditar duplicados, puede leer `documents.jsonl`.

## Validación observada

Campaña de backfill de metadatos: `2026-10-youtube-metadata-kinds` (creó versiones nuevas de metadatos con
`subtitle_kinds` sin modificar los artefactos existentes).

Ejecución `2026-10-silver-01` (2026-10-30 UTC):

- 557 artefactos de entrada, 496 procesados, 61 omitidos, 0 fallidos.
- 404 documentos canónicos, 92 alias, 3.810 fragmentos.
- 15 grupos de duplicados exactos y 37 cercanos.
- 1.278.431 tokens de entrada, 1.447.841 de salida, 23,5 MB de salida.
- 120,7 s de duración; muy por debajo del objetivo de 30 minutos.
- `pml silver verify --sample 50`: 50/50 fragmentos rastreados, 0 fallos.
- Omisiones: 35 `no_text`, 10 `scanned_pdf`, 6 `encrypted_pdf`, 10 `navigation_artifact`.

## Licencias de dependencias

| Dependencia | Licencia |
|-------------|----------|
| trafilatura | Apache-2.0 |
| pypdf | BSD-3-Clause |
| openpyxl | MIT |
| lxml | BSD-3-Clause |
| PyYAML | MIT |
| cryptography | Apache-2.0 / BSD-3-Clause |
| fpdf2 (dev) | MIT |
