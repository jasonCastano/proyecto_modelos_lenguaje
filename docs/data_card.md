# Ficha de datos — RAG Ingenio Manuelita

**Versión**: 1.1
**Fecha de corte**: 2026-10-30
**Commit de referencia del corpus**: `d40e8ef`
**Autores**: Jason Alejandro Castaño, Roberto José Guerrero
**Licencia del código**: MIT
**Uso de los datos**: académico, con cita de la fuente original; sin redistribución

---

## 1. Identificación

| Campo | Valor |
|-------|-------|
| Nombre | RAG Ingenio Manuelita — corpus público |
| Tipo | Corpus textual multiformato para Q&A y RAG |
| Idioma principal | Español |
| Cobertura | Información pública de Ingenio Manuelita, sus filiales, marcas y Fundación |
| Runs de referencia | Bronce: campañas 2026-10; plata: `2026-10-silver-01`; oro: `2026-10-gold-01` |
| Formatos de salida | JSONL, Markdown con frontmatter, JSON, SQLite (catálogo de bronce) |
| Versionado | Código y documentos en Git; bronce, plata y oro en Git LFS; cuarentena y cachés fuera de Git |
| Contacto | Repositorio `jasonCastano/proyecto_modelos_lenguaje` |

**Propósito**: servir de base verificable para Resumen, FAQ y Q&A del Módulo 1, con citas y linaje hasta
una URL pública.

**No incluye**: datos privados, contenido autenticado, Instagram, Linktree, PDF escaneados o cifrados,
OCR, traducción, embeddings ni respuestas generadas por un LLM.

---

## 2. Resumen ejecutivo

| Métrica | Valor |
|---------|------:|
| Artefactos catalogados en bronce | 26.905 |
| Artefactos en cuarentena | 26.347 |
| Artefactos activos tras curaduría | **557** |
| Campañas de bronce | 9 |
| Documentos de plata | 496 |
| Documentos canónicos | **404** |
| Alias de plata | 92 |
| Fragmentos de plata | 3.810 |
| Tamaño de plata | 23,5 MB |
| Tokens de plata | 1.447.841 |
| Unidades de oro | 15.211 |
| Hechos de oro | 381 |
| Entidades de oro | 15 |
| Conflictos de oro | 38 |
| Cobertura de los 24 ítems | 24/24 |
| Paquetes de contexto | 2 (8.000 y 32.000 tokens) |
| Tokens de oro | 1.000.109 |
| Pruebas offline | 165 |

> **Nota sobre “activos”**: la tabla `artifacts` conserva 26.905 filas y 26.904 sin retirar. La vista
> `v_active_artifacts` devuelve **557** porque excluye la cuarentena y las evaluaciones de relevancia. La
> cifra oficial del corpus activo es **557**.

---

## 3. Fuentes y gobernanza

### 3.1 Fuentes activas

| Fuente | Autoridad | Artefactos de entrada | Acceso | Condición registrada |
|--------|-----------|----------------------:|--------|----------------------|
| `official_site` (`manuelita.com`) | first-party | 397 | Permitido | Términos del sitio; uso académico |
| `youtube` (`@ManuelitaAgroindustria`) | first-party | 111 | Permitido | Términos de YouTube; metadatos y subtítulos |
| `fundacion_manuelita` (`fundacionmanuelita.org`) | first-party | 41 | Permitido | Términos del sitio; uso académico |
| `elpais` (`elpais.com.co`) | third-party | 4 | Permitido | Términos del medio; cita obligatoria |
| `datos_gov` (`datos.gov.co`) | open data | 2 | Permitido | Licencia del portal de datos abiertos |
| `asocana` | third-party | 1 | Permitido | Términos del gremio; cita obligatoria |
| `camara_comercio` | third-party | 1 | Permitido | Términos del registro; cita obligatoria |
| **Total** | | **557** | | |

### 3.2 Fuentes excluidas

| Fuente | Artefactos | Motivo |
|--------|-----------:|--------|
| Instagram (`@manuelitaagroindustria`) | 0 | `robots.txt` con `Disallow: /` y términos de Meta que prohíben la recolección automatizada sin permiso |
| Linktree (`linktr.ee/manuelitaagroindustria`) | 0 | `robots.txt` con `Disallow: /`; sin contenido propio distinto de sus cuatro enlaces |

### 3.3 Cobertura de canales

- **YouTube**: 69 videos y shorts auditados; 33 con transcripción (28 por subtítulos y 5 por ASR local);
  2 sin habla; 1 duplicado exacto; 3 requieren inicio de sesión; 30 no disponibles.
- **Fundación Manuelita**: 57 objetivos descubiertos; 41 artefactos almacenados; 16 fallos por enlaces
  históricos rotos o `http://` que responden 522.
- **Instagram y Linktree**: 0 artefactos; se conservan como fuentes deshabilitadas y auditadas.

### 3.4 Fechas

- Captura del corpus: **2026-10-27 a 2026-10-30** (UTC).
- Fecha de corte de esta ficha: **2026-10-30**.
- Fechas de publicación: variables; cada documento conserva `published_at` cuando la fuente lo expone.
- Fecha de captura por artefacto: `retrieved_at` en el catálogo y en los JSONL.

---

## 4. Composición

### 4.1 Artefactos de entrada por tipo de medio

| Tipo | Artefactos |
|------|-----------:|
| `text/html` | 322 |
| `application/pdf` | 113 |
| `application/json` | 76 |
| `text/vtt` | 35 |
| `application/xml` | 10 |
| `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet` | 1 |
| **Total** | **557** |

### 4.2 Documentos canónicos de plata

| Dimensión | Distribución |
|-----------|--------------|
| Estado | 404 canónicos + 92 alias = 496 |
| Idioma | Español 388, inglés 11, indeterminado 5 |
| Autoridad | first-party 398, third-party 6 |
| Secciones | 893 con título; 0 sin título |
| Fragmentos | 3.810 |
| Tamaño | 23,5 MB |
| Tokens | 1.447.841 |

### 4.3 Omisiones de plata

| Motivo | Documentos |
|--------|-----------:|
| `no_text` | 35 |
| `scanned_pdf` | 10 |
| `encrypted_pdf` | 6 |
| `navigation_artifact` | 10 |
| **Total** | **61** |

Los 61 omitidos no se reemplazan con contenido inventado; quedan declarados en la ficha y en los
reportes.

### 4.4 Duplicación

- **15 duplicados exactos** por `content_hash`.
- **37 duplicados cercanos** detectados con MinHash/LSH.
- **92 alias** conservados para auditoría; no se indexan en la plata.
- La plata indexa solo documentos canónicos: 404 documentos y 3.810 fragmentos.

### 4.5 Capa oro

| Elemento | Cantidad |
|----------|---------:|
| Unidades de conocimiento | 15.211 |
| Hechos | 381 |
| Entidades canónicas | 15 |
| Conflictos | 38 |
| Ítems de cobertura | 24 |
| Paquetes de contexto | 2 |
| Preguntas semilla | 53 |

---

## 5. Proceso y reproducibilidad

### 5.1 Cadena de linaje

```text
URL pública
  → artefacto de bronce (content_hash, retrieved_at)
  → documento canónico de plata (doc_id, text_hash)
  → fragmento (chunk_id, section_path, offsets)
  → unidad de oro (unit_id, evidence)
  → contexto / FAQ / respuesta con cita
```

Cada unidad de oro conserva `chunk_id`, `doc_id`, URL, título, sección y página o marca temporal.

### 5.2 Comandos

```bash
# Bronce: estado y verificación
uv run pml campaign status --campaign 2026-10-baseline --json
uv run python scripts/verify_official_channels.py

# Plata: construcción y reporte
uv run pml silver build --run 2026-10-silver-01 --json
uv run pml silver report --run 2026-10-silver-01 --format json
uv run pml silver verify --run 2026-10-silver-01 --sample 100 --json

# Oro: construcción y reporte
uv run pml gold build --run 2026-10-gold-01 --json
uv run pml gold report --run 2026-10-gold-01 --format json
uv run pml gold verify --run 2026-10-gold-01 --sample 100 --json

# Pruebas
uv run pytest -q
uv run pytest --collect-only -q
```

### 5.3 Configuraciones y hashes

| Archivo | Uso |
|---------|-----|
| `config/sources.toml` | Fuentes, políticas y límites de bronce |
| `config/official_channels.toml` | Canales oficiales |
| `config/silver.toml` | Limpieza, secciones, chunks y deduplicación |
| `config/gold.toml` | Unidades, temas, cobertura y contexto |
| `config/gold_taxonomy.toml` | Temas, palabras clave, entidades y mapeo a 24 ítems |
| `data/gold/manifest.json` | Hashes SHA-256 de las salidas de oro |

Los hashes de configuración quedan en los reportes de cada ejecución.

### 5.4 Herramientas

- Python 3.14 y `uv` con versiones fijadas en `uv.lock`.
- `scrapling` y `yt-dlp` para bronce.
- `trafilatura`, `lxml`, `pypdf`, `cryptography`, `openpyxl` y `PyYAML` para plata.
- `faster-whisper` y `av` (extra `asr`) para transcripción local opcional.
- Biblioteca estándar para oro; sin LLM, embeddings, OCR ni traducción.
- `pytest`, `ruff` y `jsonschema` para calidad.

### 5.5 Duraciones observadas

| Etapa | Duración |
|-------|---------:|
| Plata (`2026-10-silver-01`) | 120,7 s |
| Oro (`2026-10-gold-01`) | 54,5 s |

---

## 6. Calidad y linaje

### 6.1 Señales de calidad de plata

| Flag | Documentos |
|------|-----------:|
| `no_section` | 158 |
| `multi_column_suspect` | 55 |
| `exact_duplicate` | 53 |
| `near_duplicate` | 39 |
| `table_heavy` | 22 |
| `language_unknown` | 10 |

### 6.2 Señales de calidad de oro

| Flag | Unidades |
|------|---------:|
| `topic_uncertain` | 5.799 |
| `english_content` | 1.745 |
| `low_authority` | 215 |
| `short_unit` | 235 |
| `conflicting` | 89 |

### 6.3 Conflictos y cobertura

- **38 conflictos** entre hechos con el mismo sujeto y atributo.
- Resolución por autoridad (`first_party` > `open_data` > `third_party`), fecha y evidencia.
- Los empates quedan `disputed`; no se promedian cifras.
- **24/24 ítems** evaluados con al menos una unidad y una fuente.
- La cobertura es una regla determinista: `covered` exige ≥3 unidades y ≥1 fuente oficial. No sustituye
  una revisión humana.

### 6.4 Verificación

- `pml silver verify --run 2026-10-silver-01 --sample 100`: 100/100 unidades, 0 fallos.
- `pml gold verify --run 2026-10-gold-01 --sample 100`: 100/100 unidades, 24/24 ítems, 0 fallos.
- Pruebas offline: **165**.
- CI verde y Ruff limpio.

---

## 7. Licencias y uso

### 7.1 Código

El código del proyecto se distribuye bajo **MIT** (`LICENSE`, 2026).

### 7.2 Datos

- Los datos pertenecen a sus fuentes originales.
- El proyecto los usa con fines **académicos** y **no los redistribuye**.
- Cada documento conserva su URL y fecha de captura.
- La nota de licencia registrada en plata es: *“Uso académico. Contenido público de su fuente original;
  se cita la URL y la fecha de captura.”*
- Los documentos de terceros conservan sus propios términos; la cita es obligatoria.

### 7.3 Condiciones por fuente

| Fuente | Condición | Verificación |
|--------|-----------|--------------|
| `official_site` | Términos del sitio; uso académico | `robots.txt` respetado; sin credenciales |
| `youtube` | Términos de YouTube; metadatos y subtítulos | `robots.txt` permitió rutas públicas; sin cookies |
| `fundacion_manuelita` | Términos del sitio; uso académico | `robots.txt` sin restricciones |
| `elpais` | Términos del medio; cita obligatoria | 4 artefactos; sin redistribución |
| `datos_gov` | Licencia de datos abiertos del portal | Verificar la licencia del conjunto específico |
| `asocana` | Términos del gremio; cita obligatoria | 1 artefacto |
| `camara_comercio` | Términos del registro; cita obligatoria | 1 artefacto |
| Instagram | Prohibida la recolección automatizada sin permiso | Excluido |
| Linktree | `robots.txt` con `Disallow: /` | Excluido |

> **Limitación de licencias**: el proyecto no declara una licencia explícita por fuente cuando el sitio no
> la publica. En esos casos se registra la condición de uso académico y se remite a los términos del sitio.
> Antes de reutilizar el corpus fuera del ámbito académico, verifica la licencia de cada fuente.

---

## 8. Limitaciones y sesgos

1. **Instagram y Linktree fuera del corpus** por `robots.txt` y términos de Meta. Las preguntas sobre
   contenido exclusivo de esas redes deben responderse como “sin evidencia”.
2. **61 artefactos omitidos**: 35 sin texto, 10 PDF escaneados, 6 PDF cifrados y 10 artefactos de
   navegación. No se aplica OCR ni descifrado.
3. **YouTube incompleto**: 30 videos no disponibles, 3 con login y 2 sin habla. No se usaron cookies.
4. **Dependencia de fuentes públicas**: el corpus refleja lo publicado y accesible al 2026-10-30; no
   representa necesariamente la operación interna ni información privada.
5. **Idioma**: 388 documentos en español, 11 en inglés y 5 indeterminados. El corpus no es bilingüe
   equilibrado.
6. **Terceros**: solo 6 documentos canónicos de terceros; no representan al sector.
7. **Taxonomía por reglas**: 5.799 unidades con `topic_uncertain`; la asignación de temas no usa
   embeddings ni un modelo semántico.
8. **Conflictos**: 38; algunos atributos son genéricos y requieren revisión muestral antes de la
   evaluación final.
9. **Cobertura**: 24/24 es una medida determinista por reglas; no equivale a validación humana.
10. **Tokens**: estimados con `caracteres / 3.5`; se recalibrarán con el modelo del Módulo 1.
11. **Sin OCR, LLM, embeddings ni traducción** en la construcción del corpus.
12. **Fechas**: la captura es del 27 al 30 de octubre de 2026; las fechas de publicación son variables y
    no siempre están disponibles.

---

## 9. Mantenimiento

### 9.1 Actualización

1. Ejecutar una nueva campaña de bronce con un identificador nuevo.
2. Reconstruir plata con `uv run pml silver build --run YYYY-MM-silver-NN`.
3. Reconstruir oro con `uv run pml gold build --run YYYY-MM-gold-NN`.
4. Ejecutar `verify` en plata y oro.
5. Actualizar esta ficha con las nuevas cifras, run IDs y limitaciones.
6. Registrar el cambio en el changelog.

### 9.2 Reglas

- Bronce, plata y oro se versionan en **Git LFS**; la cuarentena, los cachés, los smoke runs y `data/module1/`
  no se versionan.
- Los datos se regeneran desde las capas y se referencian por manifiesto y hash.
- No se borran campañas ni registros del catálogo sin justificación.
- Las fuentes bloqueadas se mantienen declaradas; no se intenta evadir `robots.txt`.

### 9.3 Clonación con LFS

```bash
git lfs install
git clone https://github.com/jasonCastano/proyecto_modelos_lenguaje.git
cd proyecto_modelos_lenguaje
git lfs pull
uv sync
```

`git lfs pull` descarga bronce, plata y oro (~489 MB). La cuarentena no se descarga.

---

## 10. Changelog

| Versión | Fecha | Cambio |
|---------|-------|--------|
| 1.0 | 2026-10-30 | Ficha inicial con el corpus de referencia: 557 activos, 404 canónicos, 3.810 fragmentos, 15.211 unidades y 24/24 ítems |
| 1.1 | 2026-10-30 | Bronce, plata y oro versionados en Git LFS; cuarentena y cachés excluidos |

---

## 11. Evidencia de verificación

```text
Commit de referencia        -> d40e8ef
Artefactos catalogados      -> 26905
Artefactos en cuarentena    -> 26347
Artefactos activos          -> 557 (v_active_artifacts)
Plata                       -> data/silver/reports/2026-10-silver-01/quality.json
Oro                         -> data/gold/reports/2026-10-gold-01/quality.json
Manifiesto de oro           -> data/gold/manifest.json
Canales oficiales           -> docs/fuentes_oficiales.md
Pruebas                     -> 165 passed
Ruff                        -> All checks passed!
```
