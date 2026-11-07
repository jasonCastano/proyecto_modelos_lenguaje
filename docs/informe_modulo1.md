# Informe del Módulo 1 — RAG Ingenio Manuelita

**Equipo**: Jason Alejandro Castaño · Roberto José Guerrero

**Curso**: Técnicas Avanzadas de IA aplicadas en Modelos de Lenguaje — Maestría en IA y Ciencia de Datos,
Universidad Autónoma de Occidente, 2026-2S

**Docente**: Jan Polanco Velasco

**Fecha**: 2026-11-07

**Estado**: Borrador redactado con asistencia de Claude Code; pendiente de revisión por ambos integrantes
y de los resultados de M1-08.

> **Regla de este informe** (Principio I de la [constitución](../CONSTITUTION.md)): cada cifra indica el
> archivo o el comando del que proviene. Lo que aún no se ha medido se marca como **PENDIENTE** y no se
> estima.

---

## 1. Descripción del problema

Ingenio Manuelita S.A. es una agroindustria del Valle del Cauca (Colombia) cuya información pública está
dispersa entre su sitio oficial, su fundación, su canal de YouTube, medios de prensa, gremios y portales de
datos abiertos ([README](../README.md#problema)). Un cliente que se acerca por primera vez necesita
respuestas rápidas y confiables sobre identidad, historia, sedes, productos, certificaciones, sostenibilidad,
noticias, empleo y datos corporativos. Un asistente genérico puede responder con datos desactualizados o
inventados, y no permite verificar de dónde sale cada afirmación.

**Necesidad**: un canal de consulta automatizado, preciso y trazable que responda **solo** con información
pública verificable y cite la fuente de cada afirmación; cuando no hay evidencia, debe decirlo.

El alcance quedó fijado como contrato en [`docs/alcance.md`](alcance.md) (v1.1, aprobado el 2026-10-30) con
cuatro fronteras:

| Frontera | Definición (fuente: `docs/alcance.md` §1) |
|----------|-------------------------------------------|
| Temática | 40 preguntas en 8 categorías, mapeadas a 24 ítems de cobertura |
| Documental | Corpus activo de bronce, plata y oro (cifras en la sección 3) |
| Conductual | Siempre con cita; si no hay evidencia lo declara; no inventa |
| Negativa | Instagram, Linktree, PDF escaneados o cifrados, datos privados, asesoría financiera o legal |

Las 8 categorías y su número de preguntas (fuente: `docs/alcance.md` §4) son: identidad, historia y valores
(7); sedes, contacto y proveedores (2); productos, aplicaciones y compras (9); certificaciones y calidad (3);
sostenibilidad, ambiente y economía circular (6); noticias y presencia digital (4); empleo y comunidad (3);
datos duros, ética y transparencia (6). Total: 40. Cada pregunta declara tipo (factual, comparativa,
aplicada, meta-evidencia o síntesis), ítems, fuente esperada y resultado esperado (directa, parcial,
comparativa, meta, síntesis o *fallback*).

Los 24 ítems de cobertura están definidos en [`config/coverage-items.toml`](../config/coverage-items.toml) y
se agrupan en identidad (I-01 a I-06), oferta (O-01 a O-06), presencia digital (D-01 a D-06) y datos duros
(H-01 a H-06).

## 2. Planteamiento de la solución

La solución construye una **base de conocimiento trazable** con arquitectura *medallion* y, sobre ella, tres
tareas de LLM con LangChain (Resumen, FAQ y Q&A) expuestas en una aplicación web. El flujo completo está en
[`CLAUDE.md`](../CLAUDE.md), el [README](../README.md#arquitectura) y el diagrama interactivo
[`docs/arquitectura.html`](arquitectura.html).

```text
Fuentes públicas
  → Bronce  (scraping con Scrapling; bytes originales inmutables + hash; catálogo SQLite)
  → Plata   (limpieza, secciones, dedupe y chunking deterministas, sin LLM ni OCR)
  → Oro     (consolidación extractiva: unidades citables, hechos, entidades, conflictos, cobertura)
  → Tareas  (LangChain: recuperación léxica + prompt versionado + DeepSeek; citas [U#] validadas)
  → API + Web (FastAPI + React/Vite; modo demostración sin red ni clave)
```

Decisiones de diseño que sostienen la solución:

1. **Bronce inmutable y catálogo como fuente de verdad** de procedencia, deduplicación por hash, cobertura y
   auditoría; lo irrelevante se mueve a cuarentena con auditoría ([README](../README.md#arquitectura)).
2. **Entrada canónica de scraping** `scripts/scrape_empresa.py`, fachada fina sobre el pipeline existente,
   con *dry-run* aislado y códigos de salida definidos
   ([ADR 0005](decisions/0005-scrape-entrypoint.md), [spec 005](../specs/005-scrape-empresa-entrypoint/)).
3. **Plata determinista y offline** ([ADR 0003](decisions/0003-silver-layer.md),
   [spec 003](../specs/003-silver-medallion-layer/)).
4. **Oro extractivo**: el oro no resume ni responde; cada unidad es texto literal con su cita
   ([ADR 0004](decisions/0004-gold-layer.md), [spec 004](../specs/004-gold-medallion-layer/)).
5. **Generación anclada al contexto**: el modelo recibe solo unidades seleccionadas, cita etiquetas `[U#]`
   que el sistema valida y, sin evidencia, devuelve `status=fallback` con `citations=[]` sin llamar al modelo
   ([ADR 0007](decisions/0007-langchain-tasks.md), [spec 007](../specs/007-langchain-qa-tasks/spec.md)).
6. **Proveedor por API con modo demostración**: DeepSeek por API; la clave solo vive en el servidor y el modo
   demo usa un modelo guionizado sin red ([ADR 0012](decisions/0012-deepseek-api.md),
   [spec 011](../specs/011-deepseek-api-model/)). Reemplaza a la decisión inicial de Ollama local
   ([ADR 0006](decisions/0006-ollama-llm.md)).
7. **Aplicación web propia**: React 19 + Vite + TypeScript servida por FastAPI, con `/api/health`,
   `/api/ask`, `/api/summary`, `/api/faq` y `/api/showcase` ([ADR 0013](decisions/0013-web-frontend.md),
   [spec 012](../specs/012-manuelita-rag-showcase/)). Sustituye a la app Streamlit inicial
   ([ADR 0009](decisions/0009-streamlit-app.md), [spec 008](../specs/008-streamlit-qa-app/)); la identidad
   visual se documenta en [ADR 0010](decisions/0010-brand-identity.md).
8. **Datos versionados en Git LFS** (bronce, plata y oro; cuarentena y cachés fuera)
   ([ADR 0008](decisions/0008-data-lfs.md)), y estandarización del repositorio con Makefile, pre-commit, CI y
   gobernanza ([ADR 0011](decisions/0011-project-standard.md)).

**Fuera del Módulo 1** (por decisión de la constitución, §5 Fase 2): embeddings, base vectorial, memoria
multi-turno y enrutador. Se describen como *previstos* en la sección 4.

## 3. Preparación de los datos

### 3.1 Adquisición (bronce)

El pipeline sigue las etapas **descubrir → extraer → limpiar → deduplicar → enriquecer** y respeta
`robots.txt`, `sitemap.xml`, `User-Agent`, timeout, reintentos y límite de tasa por host (constitución §3.4).
Las fuentes y políticas se configuran en [`config/sources.toml`](../config/sources.toml),
[`config/official_channels.toml`](../config/official_channels.toml),
[`config/exclusions.toml`](../config/exclusions.toml) y [`config/relevance.toml`](../config/relevance.toml).

| Métrica | Valor | Fuente |
|---------|------:|--------|
| Artefactos catalogados en bronce | 26.905 | `docs/data_card.md` §2 |
| Artefactos en cuarentena (irrelevantes) | 26.347 | `docs/data_card.md` §2 |
| Artefactos activos tras curaduría | 557 | `docs/data_card.md` §2 (vista `v_active_artifacts`) |
| Campañas de bronce | 9 | `docs/data_card.md` §2 |
| Páginas del sitemap oficial capturadas | 249/250 (99,6 %) | `README.md`, «Estado del proyecto» |
| Ventana de captura (UTC) | 2026-10-27 a 2026-10-30 | `docs/data_card.md` §3.4 |

Composición del corpus activo por fuente (fuente: `docs/data_card.md` §3.1): sitio oficial 397, YouTube 111,
Fundación Manuelita 41, El País 4, datos.gov.co 2, Asocaña 1 y Cámara de Comercio 1 (total 557). Por tipo de
medio (§4.1): 322 HTML, 113 PDF, 76 JSON, 35 VTT, 10 XML y 1 XLSX.

Canales oficiales ([`docs/fuentes_oficiales.md`](fuentes_oficiales.md), `docs/data_card.md` §3.3):
YouTube con 69 videos y shorts auditados, 33 con transcripción (28 por subtítulos y 5 por ASR local);
Fundación Manuelita con 57 objetivos descubiertos y 41 artefactos almacenados. Instagram y Linktree quedan
con 0 artefactos porque su `robots.txt` declara `Disallow: /`; es una decisión de cumplimiento, no una falla.

### 3.2 Limpieza, deduplicación y fragmentación (plata)

Decisiones en [ADR 0003](decisions/0003-silver-layer.md): `trafilatura` + `lxml` para HTML, `pypdf` para
PDF, proxy de tokens `ceil(caracteres / 3.5)` (offline), SHA-256 sobre texto normalizado para duplicados
exactos y MinHash/LSH propio (128 permutaciones, shingles de 5 palabras, 16 bandas) para cercanos.
Parámetros de fragmentación en [`config/silver.toml`](../config/silver.toml): objetivo 800 tokens, máximo
1.000, mínimo 200, solapamiento 120 tokens, corte por oración.

| Métrica | Valor | Fuente |
|---------|------:|--------|
| Documentos de plata (canónicos + alias) | 496 | `uv run pml silver status --json` (2026-11-07) |
| Documentos canónicos | 404 | `docs/data_card.md` §2 |
| Alias (duplicados o versiones, no indexados) | 92 | `docs/data_card.md` §2 |
| Fragmentos (*chunks*) | 3.810 | `uv run pml silver status --json` |
| Omitidos | 61 | `uv run pml silver status --json` (`skipped`) |
| Fallidos | 0 | `uv run pml silver status --json` (`failed`) |
| Tokens de plata (proxy) | 1.447.841 | `docs/data_card.md` §2 |
| Tamaño de plata | 23,5 MB | `docs/data_card.md` §2 |
| Duplicados exactos / cercanos | 15 / 37 | `docs/data_card.md` §4.4 |

Los 61 omitidos se desglosan en 35 sin texto, 10 PDF escaneados, 6 PDF cifrados y 10 artefactos de
navegación (`docs/data_card.md` §4.3); no se reemplazan con contenido inventado. Idioma de los canónicos:
388 español, 11 inglés, 5 indeterminado (§4.2).

### 3.3 Consolidación (oro)

Decisiones en [ADR 0004](decisions/0004-gold-layer.md) y parámetros en
[`config/gold.toml`](../config/gold.toml) y [`config/gold_taxonomy.toml`](../config/gold_taxonomy.toml):
unidades extractivas (oración o pasaje literal, 40–700 caracteres), taxonomía controlada sin
embeddings, hechos solo con sujeto, atributo, valor y unidad explícitos, conflictos resueltos por
autoridad y fecha (los empates quedan `disputed`, nunca se promedian), y paquetes de
contexto de 8.000 y 32.000 tokens.

| Métrica | Valor | Fuente |
|---------|------:|--------|
| Unidades de conocimiento | 15.211 | `uv run pml gold status --json` (run `2026-10-gold-01`) |
| Hechos | 381 | `uv run pml gold status --json` |
| Conflictos | 38 | `uv run pml gold status --json` |
| Entidades canónicas | 15 | `docs/data_card.md` §4.5 |
| Preguntas semilla para FAQ | 53 | `docs/data_card.md` §4.5 |
| Paquetes de contexto | 2 (8.000 y 32.000) | `uv run pml gold status --json`; `config/gold.toml` |
| Tokens de oro (proxy) | 1.000.109 | `uv run pml gold status --json` |
| Ítems cubiertos / parciales / faltantes | 24 / 0 / 0 | `uv run pml gold status --json` |

Verificación muestral registrada en `docs/data_card.md` §6.4: `pml silver verify --sample 100` y
`pml gold verify --sample 100` con 100/100 unidades y 0 fallos. Cadena de linaje: URL → artefacto de bronce
(`content_hash`) → documento de plata (`doc_id`) → fragmento (`chunk_id`) → unidad de oro (`unit_id`) →
respuesta con cita (`docs/data_card.md` §5.1).

### 3.4 Ética y licencias

Los datos pertenecen a sus fuentes; se usan con fines académicos, sin redistribución, conservando URL y fecha
de captura. No se usan cookies, credenciales ni técnicas para evadir controles de acceso
(`docs/data_card.md` §7, `docs/fuentes_oficiales.md` §1).

## 4. Modelado

### 4.1 LLM

| Parámetro | Valor | Fuente |
|-----------|-------|--------|
| Framework | LangChain (`langchain-openai`, cliente compatible con OpenAI) | ADR 0012 |
| Proveedor | DeepSeek por API (DeepSeek V4.1 Flash 1017 según ADR 0012) | `config/llm.toml`, ADR 0012 |
| Identificador | `deepseek-flash` (sobreescribible con `DEEPSEEK_MODEL`) | `config/llm.toml` |
| Temperatura / `top_p` | 0,1 / 0,9 | `config/llm.toml` |
| Tokens de salida | 1.024 | `config/llm.toml` |
| Ventana de contexto configurada | 65.536 | `config/llm.toml` |
| Paquete de contexto por defecto | 8.000 | `config/llm.toml` |
| Timeout / reintentos | 60 s / 1 (backoff 2,0 s) | `config/llm.toml` |
| Clave | `DEEPSEEK_API_KEY` desde `.env`; nunca llega al navegador | `config/llm.toml`, ADR 0012/0013 |
| Modo sin red | `build_scripted_model` (demo) y `build_fake_model` (pruebas) | `CLAUDE.md`, ADR 0012 |

**Justificación** (constitución §3.5, ADR 0012): elimina la descarga de ~5 GB por equipo que exigía Ollama,
mantiene la interfaz `BaseChatModel`, soporta español y compensa la dependencia de red con el modo demo.
**Riesgo aceptado**: el identificador `deepseek-flash` y las tarifas deben confirmarse con la cuenta del
proveedor; las tarifas están en 0,0 en `config/llm.toml` («costo no configurado», no se inventa).

Historial: la primera línea base se ejecutó con `llama3.1:8b` vía Ollama
([ADR 0006](decisions/0006-ollama-llm.md)) y `qwen3.5:4b` como respaldo; ADR 0012 declara que esa línea
base deja de ser comparable directamente.

### 4.2 Recuperación del Módulo 1

[`retrieval.py`](../src/proyecto_modelos_lenguaje/retrieval.py) implementa un **BM25 simplificado léxico**
sobre tokens normalizados (minúsculas, sin acentos ni puntuación) más señales de tema, entidades y calidad,
con diversidad por tema y presupuesto de tokens ([ADR 0007](decisions/0007-langchain-tasks.md)). Parámetros
en [`config/tasks.toml`](../config/tasks.toml): Q&A con `top_k = 8`, `token_budget = 6000` y
`min_score = 0.0`; Resumen con paquete `8000` y `min_citations = 8`; FAQ con `limit = 12`, `top_k = 5`,
`min_citations = 1` y `question_max_chars = 500`.

### 4.3 Modelo de embedding previsto (Fase 2 — previsto/en revisión en PR #34)

No se usa en el Módulo 1. Según la constitución v1.3.0 (§5, Fase 2) y el PR #34
(`feat(rag): recuperación semántica para el chatbot (Módulo 2)`, abierto, sin fusionar a 2026-11-07):

- Modelo: **`intfloat/multilingual-e5-small`**, 384 dimensiones, límite de 512 tokens, ejecutado en ONNX vía
  `fastembed` (sin PyTorch).
- Criterio exigido por la constitución: evidencia de *retrieval* en español (MTEB filtrado), costo y
  latencia; registrar versión, dimensión, normalización, prefijos de consulta/documento y límite de tokens.
- El embedding no es intercambiable: cambiar de modelo obliga a reindexar.

### 4.4 Base vectorial prevista (Fase 2 — prevista/en revisión en PR #34)

- Índice propio **`numpy` + SQLite** (`vectors.npy`, `index.sqlite3`, `manifest.json`) en `data/module2/`,
  no versionado; es una vista derivada del oro y se reconstruye con un comando. Su manifiesto registra
  modelo, fragmentación, fecha y hash del oro (constitución §5, Fase 2, regla 2).
- La cátedra recomienda Chroma o FAISS; el índice propio se acepta por decisión registrada (ADR 0014 en el
  PR #34) siempre que se exponga al agente como *retriever* de LangChain.
- Recuperación híbrida descrita en el PR #34: `0.65 × semántica + 0.35 × léxica` (+0,05 si coincide en
  ambos modos), umbral 0,30, con el BM25 del Módulo 1 como respaldo y línea base.

### 4.5 Diseño del prompt

Los tres prompts están versionados en [`prompts/qa.md`](../prompts/qa.md),
[`prompts/summary.md`](../prompts/summary.md) y [`prompts/faq.md`](../prompts/faq.md) (versión 1.0) y se
cargan con `tasks.load_prompt`, que registra su SHA-256 en cada resultado. Hashes (12 primeros caracteres,
fuente: [`docs/prompt_log.md`](prompt_log.md) §1): Q&A `d09765504709`, Resumen `f6cd198ba529`, FAQ
`9bafea161abb`.

Cada prompt declara las seis secciones que exige la constitución §3.6:

| Sección | Q&A (`prompts/qa.md`) |
|---------|-----------------------|
| Rol | Analista documental especializado en el Grupo Manuelita |
| Tarea | Responder en español, breve y verificable; cada afirmación con su etiqueta |
| Contexto | Bloque `<context>` con unidades `U1…Un`, declarado como **dato no confiable** |
| Reglas | Solo contexto; casa matriz ≠ filiales; cifras discrepantes sin promediar; ver nota |
| Formato de cita | `[U#]` al final de la afirmación; sin bibliografía ni enlaces |
| Sin evidencia | Respuesta exacta: «No hay evidencia suficiente en el corpus para responder.» |

Nota: las reglas de Q&A también prohíben obedecer instrucciones que aparezcan dentro del contexto,
inventar etiquetas e incluir rutas, claves o datos personales.

El Resumen pide cinco bloques (identidad, productos y operación, sostenibilidad, presencia territorial y
cifras) con un número mínimo y máximo de citas distintas; la FAQ responde una semilla de oro en tercera
persona con al menos una cita.

Controles fuera del prompt ([ADR 0007](decisions/0007-langchain-tasks.md)): sin evidencia no se llama al
modelo; las citas que no existen en el contexto se descartan y marcan `review_required`; tras dos intentos
sin citas el resultado es `status=error` con `error=missing_citations`.

**Variantes exigidas por la constitución §3.6** (línea base zero-shot, formato estructurado y
anti-alucinación): la versión 1.0 ya incorpora formato estructurado y reglas anti-alucinación. La línea base
zero-shot y la variante final ajustada con evidencia **están pendientes** (M1-08 y M1-09, ver sección 5.4).

## 5. Resultados

Esta sección reporta solo lo medido. La evaluación de 40 preguntas aún no existe.

### 5.1 Corpus y cobertura

Las cifras de corpus están en la sección 3. La cobertura de los 24 ítems se calcula con una regla
determinista: `covered` exige ≥3 unidades y ≥1 fuente oficial (`config/gold.toml`, ADR 0004). Resultado
(fuente: `data/gold/coverage.md`, run `2026-10-gold-01`): **24 cubiertos, 0 parciales, 0 faltantes**.

| Ítem | Unidades | Ítem | Unidades | Ítem | Unidades | Ítem | Unidades |
|------|---------:|------|---------:|------|---------:|------|---------:|
| I-01 | 369 | O-01 | 1.887 | D-01 | 6 | H-01 | 172 |
| I-02 | 366 | O-02 | 3 | D-02 | 107 | H-02 | 269 |
| I-03 | 382 | O-03 | 20 | D-03 | 98 | H-03 | 430 |
| I-04 | 338 | O-04 | 6 | D-04 | 5 | H-04 | 20 |
| I-05 | 357 | O-05 | 184 | D-05 | 19 | H-05 | 8 |
| I-06 | 332 | O-06 | 456 | D-06 | 59 | H-06 | 92 |

Lectura: O-02 (fichas técnicas) apenas alcanza el umbral con 3 unidades; D-04, D-01, O-04 y H-05 tienen
menos de 10. El [README](../README.md#limitaciones-conocidas) advierte que SECOP, NIT, precios, fichas
técnicas y catálogos aún no tienen evidencia verificable, por lo que 24/24 **no** equivale a validación
humana.

### 5.2 Ejecuciones observadas de las tareas

Fuente: [`docs/prompt_log.md`](prompt_log.md) §3. Son ejecuciones puntuales, no una evaluación.

| Modelo | Tarea | Estado | Citas | Latencia | Observación registrada |
|--------|-------|--------|------:|---------:|------------------------|
| `scripted-fake` | Q&A | ok | 2 | — | 8 unidades; 894 tokens de entrada, 24 de salida |
| `scripted-fake` | Resumen 8k | ok | 10 | — | 12 unidades; 872 / 163 tokens |
| `scripted-fake` | FAQ (12) | 12 × ready | ≥1 c/u | — | — |
| `llama3.1:8b` | Q&A productos (a) | ok | 3 | 26,84 s | 1.177 / 192 tokens; tres fuentes |
| `llama3.1:8b` | Q&A casa matriz (b) | ok | 1 | 4,46 s | Declara que el contexto no lo dice; no inventa |
| `llama3.1:8b` | Resumen 8k | ok | 8 | 27,45 s | 9.050 / 701 tokens; 84 unidades en el paquete |
| `llama3.1:8b` | FAQ (10) | 7 ready, 3 review | 1–2 | — | 70 % con citas; los 3 `review` no citaron |
| `qwen3.5:4b` | Q&A productos (a) | ok | 2 | 2,91 s | Respuesta citada `[U5]`, `[U1]` |
| `qwen3.5:4b` | Resumen 8k | ok | 12 | 4,01 s | Bloques con citas |
| DeepSeek (simulado) | Q&A / Resumen | ok | ≥1 / 8–12 | — | Transporte HTTP simulado |
| DeepSeek (simulado) | Errores | controlado | — | — | 401, 404, 429, 500, timeout y vacío |

(a) «¿Qué productos ofrece Manuelita?»; (b) «¿Dónde está la casa matriz?».

**Línea base real con DeepSeek: PENDIENTE** (`docs/prompt_log.md` §3.3 y §4, tareas T045/T046): no había clave
del proveedor en el equipo cuando se registró el log.

Hallazgos registrados en el prompt log:

- Con un modelo de razonamiento y `max_output_tokens = 1024`, la salida llegó vacía (`done_reason=length`);
  el sistema lo reporta como `model_error` con instrucción accionable.
- Un acento combinado (`U+0301`) rompió la impresión en la consola `cp1252` de Windows; el CLI ahora fuerza
  UTF-8 con reemplazo.
- Recuperación (§5 del log): para «¿Qué productos ofrece Manuelita?» la primera unidad era una plantilla de
  formulario; para «¿Qué certificaciones tiene Manuelita?» la primera unidad acertó el tema. Conclusión: el
  BM25 ordena por tema, pero las páginas de plantilla y navegación compiten con el contenido sustantivo.

### 5.3 Calidad del software

| Evidencia | Valor | Fuente |
|-----------|------:|--------|
| Pruebas Python (suite offline) | 323 pasan, 12 omitidas | `uv run pytest` ejecutado el 2026-11-07 |
| Pruebas offline declaradas (Python + web) | 336 (323 + 13) | `README.md`, «Estado del proyecto» |
| Ruff | limpio | `README.md`; `bitacora/2026-11-06.md` §6 |
| Pull Requests fusionados | 32 de 33 | `bitacora/2026-11-06.md` §3 |
| Avance de la lista de verificación | 78 % (17 de 23) | `bitacora/2026-11-06.md` §1 |

### 5.4 Evaluación de 40 preguntas

> **PENDIENTE — se completa con `docs/evaluacion_modulo1.md` (M1-08).**
>
> Las 40 preguntas de [`docs/alcance.md`](alcance.md) se ejecutarán con la línea base zero-shot y con el
> prompt final. Ninguna celda de esta tabla debe llenarse a mano ni con estimaciones.

Tabla por pregunta (una fila por cada P01–P40 y por variante):

| ID | Pregunta | Variante | Respuesta | Fuente | Corrección | Coherencia | Alucinación |
|----|----------|----------|-----------|--------|------------|------------|-------------|
| P01 | Misión y visión | Zero-shot | PENDIENTE | PEND. | PENDIENTE | PENDIENTE | PENDIENTE |
| P01 | Misión y visión | Final | PENDIENTE | PEND. | PENDIENTE | PENDIENTE | PENDIENTE |
| … | … | … | … | … | … | … | … |
| P40 | (ver alcance) | Zero-shot | PENDIENTE | PEND. | PENDIENTE | PENDIENTE | PENDIENTE |
| P40 | (ver alcance) | Final | PENDIENTE | PEND. | PENDIENTE | PENDIENTE | PENDIENTE |

Tabla agregada esperada:

| Métrica | Zero-shot | Prompt final | Diferencia |
|---------|----------:|-------------:|-----------:|
| Respuestas correctas (de 40) | PENDIENTE | PENDIENTE | PENDIENTE |
| Respuestas parciales (de 40) | PENDIENTE | PENDIENTE | PENDIENTE |
| Coherencia media | PENDIENTE | PENDIENTE | PENDIENTE |
| Respuestas con alucinación | PENDIENTE | PENDIENTE | PENDIENTE |
| Respuestas con cita válida | PENDIENTE | PENDIENTE | PENDIENTE |
| *Fallback* correctos (preguntas tipo `X`) | PENDIENTE | PENDIENTE | PENDIENTE |
| Latencia media (s) | PENDIENTE | PENDIENTE | PENDIENTE |

Análisis de errores y ajuste de prompts: **PENDIENTE (M1-09)**. Los candidatos de ajuste ya identificados en
`docs/prompt_log.md` §5 son penalizar unidades de baja densidad y textos de formulario, exigir cobertura de
varios términos de la pregunta y revisar el peso del tema frente a la coincidencia léxica.

## 6. Limitaciones

1. **Sin evaluación sistemática todavía**: la calidad de las respuestas no está medida (M1-08/M1-09).
2. **Línea base de DeepSeek sin ejecutar** con la clave real; las ejecuciones reales registradas usaron
   Ollama, que ADR 0012 declara no comparable directamente.
3. **Cobertura por reglas**: 24/24 es una medida determinista, no una validación humana; varios ítems tienen
   evidencia escasa o dudosa (sección 5.1).
4. **Recuperación léxica**: puede perder paráfrasis y confunde plantillas de navegación con contenido.
5. **Tokens estimados** con `caracteres / 3.5`, no con el tokenizador del modelo (`docs/data_card.md` §8).
6. **Corpus incompleto por diseño**: Instagram y Linktree excluidos; 61 documentos omitidos sin OCR ni
   descifrado; 30 videos de YouTube no disponibles y 3 con inicio de sesión (`docs/data_card.md` §8).
7. **Inconsistencias documentales por revisar**: `docs/prompt_log.md` §2 aún lista `llm.model = llama3.1:8b`
   mientras `config/llm.toml` usa `deepseek-flash`; `docs/data_card.md` cita el run de plata
   `2026-10-silver-01`, mientras `pml silver status` reporta `2026-10-silver-02` con los mismos 496
   documentos y 3.810 fragmentos.
8. **Embeddings y base vectorial** solo previstos; dependen de la revisión y fusión del PR #34.

## 7. Referencias a archivos

- Norma y contexto: [`CONSTITUTION.md`](../CONSTITUTION.md), [`CLAUDE.md`](../CLAUDE.md),
  [`README.md`](../README.md), [`bitacora/2026-11-06.md`](../bitacora/2026-11-06.md).
- Alcance y datos: [`docs/alcance.md`](alcance.md), [`docs/data_card.md`](data_card.md),
  [`docs/fuentes_oficiales.md`](fuentes_oficiales.md), `data/gold/coverage.md`.
- Prompts: [`prompts/qa.md`](../prompts/qa.md), [`prompts/summary.md`](../prompts/summary.md),
  [`prompts/faq.md`](../prompts/faq.md), [`docs/prompt_log.md`](prompt_log.md).
- Configuración: [`config/llm.toml`](../config/llm.toml), [`config/tasks.toml`](../config/tasks.toml),
  [`config/silver.toml`](../config/silver.toml), [`config/gold.toml`](../config/gold.toml),
  [`config/gold_taxonomy.toml`](../config/gold_taxonomy.toml),
  [`config/coverage-items.toml`](../config/coverage-items.toml),
  [`config/sources.toml`](../config/sources.toml).
- Decisiones: [0003](decisions/0003-silver-layer.md), [0004](decisions/0004-gold-layer.md),
  [0005](decisions/0005-scrape-entrypoint.md), [0006](decisions/0006-ollama-llm.md),
  [0007](decisions/0007-langchain-tasks.md), [0008](decisions/0008-data-lfs.md),
  [0009](decisions/0009-streamlit-app.md), [0010](decisions/0010-brand-identity.md),
  [0011](decisions/0011-project-standard.md), [0012](decisions/0012-deepseek-api.md),
  [0013](decisions/0013-web-frontend.md).
- Especificaciones: [003](../specs/003-silver-medallion-layer/), [004](../specs/004-gold-medallion-layer/),
  [005](../specs/005-scrape-empresa-entrypoint/), [006](../specs/006-llm-ollama-config/),
  [007](../specs/007-langchain-qa-tasks/), [008](../specs/008-streamlit-qa-app/),
  [009](../specs/009-manuelita-visual-identity/), [010](../specs/010-metrics-panel-layout/),
  [011](../specs/011-deepseek-api-model/), [012](../specs/012-manuelita-rag-showcase/).
- Módulo 2 (previsto): PR #34 en `jasonCastano/proyecto_modelos_lenguaje`;
  [ADR 0015](decisions/0015-module2-scope.md).
- Comandos de lectura usados: `uv run pml gold status --json`, `uv run pml silver status --json`,
  `uv run pytest -q`.
