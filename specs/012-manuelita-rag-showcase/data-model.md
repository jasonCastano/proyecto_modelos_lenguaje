# Data Model — Frontend profesional y showcase del Módulo 1

**Feature**: `012-manuelita-rag-showcase`
**Fecha**: 2026-10-31

Modelo de la interfaz y de la API. No crea almacenamiento nuevo ni modifica las entidades del corpus.

## Entidades

### `RAGQuery`

Pregunta enviada por una persona.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `id` | string | sí | Identificador de la consulta en la sesión. |
| `question` | string | sí | Texto limpio, entre 1 y 500 caracteres. |
| `mode` | enum | sí | `real` o `demo`. |
| `status` | enum | sí | `idle`, `submitting`, `success`, `fallback` o `error`. |
| `created_at` | string (date-time) | sí | Marca temporal UTC. |
| `task` | enum | sí | `qa`, `summary` o `faq`. |

**Reglas**:

- `question` no puede estar vacía ni contener caracteres de control.
- `question` no puede superar 500 caracteres.
- `mode=demo` debe rotularse como simulado.
- `status=success` exige al menos una cita.
- `status=fallback` exige `citations=[]` y mensaje explícito.
- `status=error` exige `error.code` y `error.action`.

### `CitedAnswer`

Respuesta visible y metadatos de la tarea.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `query_id` | string | sí | Consulta que originó la respuesta. |
| `status` | enum | sí | `ok`, `fallback` o `error`. |
| `answer` | string | sí | Markdown seguro o texto enriquecido controlado. |
| `citations` | array de `SourceCitation` | sí | Fuentes verificables; vacío solo en fallback/error. |
| `model` | string | sí | Modelo usado o `scripted`. |
| `provider` | string | sí | `deepseek` o `demo`. |
| `prompt_version` | string | sí | Versión del prompt. |
| `latency_ms` | number | sí | Latencia observada. |
| `input_tokens` | integer | sí | Tokens de entrada informados o estimados. |
| `output_tokens` | integer | sí | Tokens de salida informados o estimados. |
| `cost_usd` | number \| null | no | Costo estimado; `null` si no hay tarifas. |
| `error` | `ApiError` \| null | no | Error accionable. |
| `review_required` | boolean | sí | Indica revisión humana. |

**Reglas**:

- `status=ok` exige `citations.length >= 1` y `error=null`.
- `status=fallback` exige `citations=[]`, `error=null` y el mensaje de fallback.
- `status=error` exige `error` no nulo y no debe presentar una respuesta factual.
- `provider` nunca puede ser `deepseek` si `model=scripted`.
- `cost_usd=null` se muestra como “costo no configurado”; no se inventa 0.

### `SourceCitation`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `label` | string | sí | Etiqueta `[U#]`. |
| `title` | string | sí | Título de la fuente. |
| `url` | string (uri) | sí | Enlace público de origen. |
| `section_path` | array de string | sí | Sección o ruta documental. |
| `page` | integer \| null | no | Página del PDF. |
| `time_start` | number \| null | no | Segundo inicial del video. |
| `authority` | enum | sí | `first_party`, `third_party` o `unknown`. |
| `snippet` | string \| null | no | Extracto breve que sustenta la cita. |

**Reglas**: `url` debe ser HTTP(S); `label` debe existir en el contexto usado; no se muestran citas fuera del contexto.

### `ShowcaseSection`

Bloque narrativo del Módulo 1.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `id` | string | sí | `problem`, `data`, `medallion`, `prompts`, `tasks`, `app`, `metrics`, `limits`. |
| `order` | integer | sí | Orden de lectura. |
| `title` | string | sí | Titular visible. |
| `body` | string | sí | Texto narrativo breve. |
| `evidence` | array de `EvidenceLink` | sí | Enlaces a specs, reportes o código. |
| `metrics` | array de `CorpusMetric` | sí | Cifras asociadas. |
| `status` | enum | sí | `done`, `partial` o `pending`. |

**Reglas**: el orden es problema → datos → medallion → prompts → tareas → app → métricas → límites; toda cifra debe provenir de `CorpusMetric`; las secciones `pending` deben declararse como pendientes, no ocultarse.

### `CorpusMetric`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `key` | string | sí | `active_artifacts`, `canonical_documents`, `chunks`, `units`, `facts`, `entities`, `conflicts`, `coverage`, `tokens`. |
| `label` | string | sí | Etiqueta visible. |
| `value` | number | sí | Valor real. |
| `unit` | string | sí | Unidad (`documentos`, `unidades`, `tokens`, etc.). |
| `source` | string | sí | Reporte o archivo de origen. |
| `status` | enum | sí | `complete`, `incomplete` o `unknown`. |

**Reglas**: `value >= 0`; `coverage` se expresa como `covered/total`; no se mezclan tokens de plata y oro; las cifras deben coincidir con `app_metrics`.

### `EvidenceLink`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `label` | string | sí | Texto del enlace. |
| `href` | string | sí | Ruta interna o URL pública. |
| `kind` | enum | sí | `spec`, `adr`, `report`, `code` o `bitacora`. |

### `ApiError`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `code` | string | sí | `config_missing_key`, `auth_failed`, `model_unavailable`, `rate_limited`, `timeout`, `provider_unavailable`, `empty_response`, `invalid_response`, `empty_question`, `question_too_long`. |
| `message` | string | sí | Mensaje accionable en español. |
| `retryable` | boolean | sí | Indica si se puede reintentar. |
| `action` | string | sí | Acción sugerida (`reintentar`, `configurar clave`, `usar demo`). |

**Reglas**: nunca incluye la clave, el cuerpo crudo del proveedor ni una traza; `message` no culpa a la persona.

### `HealthStatus`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `ok` | boolean | sí | Proveedor disponible. |
| `provider` | string | sí | `deepseek` o `demo`. |
| `model` | string | sí | Modelo configurado. |
| `configured` | boolean | sí | Credencial presente; nunca su valor. |
| `demo_available` | boolean | sí | Modo demo disponible. |
| `latency_ms` | number \| null | no | Latencia del chequeo. |
| `detail` | string \| null | no | Mensaje seguro. |

### `DemoState`

| Estado | Significado | UI |
|--------|-------------|----|
| `real` | Proveedor real configurado | Sin banner; metadatos reales |
| `demo` | Modelo falso solicitado | Banner visible “Modo demostración” |
| `missing_key` | Sin credencial | Aviso accionable + oferta de demo |
| `degraded` | Proveedor no disponible | Aviso, reintento y demo |

## Transiciones de estado

### Consulta

```text
idle ──(enviar)──> submitting
submitting ──(ok)────> success
submitting ──(sin evidencia)──> fallback
submitting ──(error)──> error
success/fallback/error ──(reintentar)──> submitting
success/fallback/error ──(nueva pregunta)──> idle
```

### Modo

```text
real ──(sin clave / proveedor caído)──> missing_key/degraded
missing_key/degraded ──(activar demo)──> demo
demo ──(configurar clave)──> real
```

## Invariantes

1. La clave nunca sale del servidor.
2. La página no escribe en `data/`.
3. Toda respuesta `ok` tiene al menos una cita.
4. Todo fallback declara la falta de evidencia.
5. Las cifras del showcase provienen de reportes reales.
6. El modo demo siempre es visible.
7. La sesión conserva la última pregunta y respuesta, sin persistencia en disco.
