# Fase 1 — Modelo de datos: app Streamlit del Módulo 1

**Feature**: `008-streamlit-qa-app`
**Fecha**: 2026-10-30

## 1. AppMetrics

Métricas de solo lectura que alimentan el panel lateral.

| Campo | Tipo | Origen | Validación |
|-------|------|--------|------------|
| `active_artifacts` | entero | `v_active_artifacts` de bronce | `>= 0` |
| `canonical_documents` | entero | reporte de plata | `>= 0` |
| `aliases` | entero | reporte de plata | `>= 0` |
| `chunks` | entero | reporte de plata | `>= 0` |
| `units` | entero | reporte de oro | `>= 0` |
| `facts` | entero | reporte de oro | `>= 0` |
| `entities` | entero | reporte de oro | `>= 0` |
| `conflicts` | entero | reporte de oro | `>= 0` |
| `coverage_covered` | entero | `coverage.json` | `0..24` |
| `coverage_total` | entero | `coverage.json` | `= 24` |
| `silver_tokens` | entero | reporte de plata | `>= 0` |
| `gold_tokens` | entero | reporte de oro | `>= 0` |
| `skipped` | entero | reporte de plata | `>= 0` |
| `omissions` | entero | `skip_reasons` de plata | `>= 0` |
| `silver_run` | texto | reporte de plata | `YYYY-MM-silver-NN` |
| `gold_run` | texto | reporte de oro | `YYYY-MM-gold-NN` |
| `data_status` | texto | detección de datos | `complete`, `incomplete` o `unknown` |
| `detail` | texto o nulo | detección de datos | Motivo si está incompleto |

**Invariante**: `coverage_total = 24`; `omissions` es la suma de `skip_reasons`.

## 2. AppStatus

Estado de la app para el panel.

| Campo | Tipo | Valores |
|-------|------|---------|
| `data_status` | texto | `complete`, `incomplete`, `unknown` |
| `model_status` | texto | `ollama_ready`, `ollama_unavailable`, `model_missing`, `demo` |
| `demo_mode` | booleano | — |
| `detail` | texto o nulo | Mensaje accionable |
| `last_error` | texto o nulo | Último error controlado |

## 3. AppSessionState

Estado de la sesión de Streamlit.

| Campo | Tipo | Notas |
|-------|------|-------|
| `question` | texto | Pregunta actual |
| `qa_result` | TaskResult o nulo | Última respuesta Q&A |
| `summary_result` | TaskResult o nulo | Último resumen |
| `faq_items` | lista de FAQItem | FAQ generada |
| `demo_mode` | booleano | Modelo falso |
| `summary_pack` | texto | `8000` o `32000` |
| `faq_limit` | entero | 10–20 |
| `last_error` | texto o nulo | Error controlado |

**Invariante**: los resultados se conservan al cambiar de pestaña; una nueva generación solo ocurre por una
acción explícita del usuario.

## 4. AnswerView

Vista de una respuesta Q&A o de un resumen.

| Campo | Tipo | Notas |
|-------|------|-------|
| `task` | texto | `qa` o `summary` |
| `answer` | texto | Respuesta del modelo |
| `citations` | lista de Citation | Fuentes |
| `status` | texto | `ok`, `fallback`, `review`, `error` |
| `fallback` | booleano | Sin evidencia |
| `review_required` | booleano | Cita inválida o baja confianza |
| `model` | texto | Modelo usado |
| `prompt_version` | texto | Versión del prompt |
| `latency_seconds` | número | `>= 0` |
| `input_tokens` / `output_tokens` | entero | `>= 0` |
| `citation_count` | entero | Derivado de `citations` |

## 5. FAQView

| Campo | Tipo | Notas |
|-------|------|-------|
| `items` | lista de FAQItem | 10–20 elementos |
| `ready` | entero | `status=ready` |
| `review` | entero | `status=review` |
| `missing_evidence` | entero | `status=missing_evidence` |
| `generated_at` | texto o nulo | UTC de la sesión |

**Invariante**: `ready + review + missing_evidence = len(items)` y `10 <= len(items) <= 20`.

## 6. PanelMetric

| Campo | Tipo | Notas |
|-------|------|-------|
| `label` | texto | Etiqueta visible |
| `value` | texto o número | Valor formateado |
| `help` | texto o nulo | Explicación corta |
| `status` | texto | `ok`, `warning`, `error` |

## 7. SourceCitation

Vista de una cita para la interfaz.

| Campo | Tipo | Notas |
|-------|------|-------|
| `label` | texto | `U1`, `U2`, … |
| `title` | texto | Título del documento |
| `url` | texto | URL pública |
| `section` | texto | Sección, página o tiempo |
| `authority` | texto | Autoridad |
| `markdown` | texto | Enlace listo para mostrar |

## 8. Relaciones

```text
AppMetrics ──► PanelMetric[]
AppStatus ──► PanelMetric[]
TaskResult ──► AnswerView ──► SourceCitation[]
FAQItem[] ──► FAQView
AppSessionState ──► AnswerView + FAQView + AppStatus
```

## 9. Estados

### 9.1 DataStatus

| Estado | Condición | Comportamiento |
|--------|-----------|----------------|
| `complete` | archivos requeridos presentes, no vacíos y no punteros LFS | App operativa |
| `incomplete` | falta un archivo, está vacío o es puntero LFS | Mostrar instrucción `git lfs pull` y deshabilitar generación |
| `unknown` | error de lectura inesperado | Mostrar error controlado |

### 9.2 ModelStatus

| Estado | Condición | Comportamiento |
|--------|-----------|----------------|
| `ollama_ready` | servidor y modelo disponibles | Usar modelo real |
| `ollama_unavailable` | servidor no responde | Mostrar `ollama serve`; sugerir demo |
| `model_missing` | servidor sin el modelo | Mostrar `ollama pull`; sugerir demo |
| `demo` | modo demostración activo | Usar modelo falso |

## 10. Validaciones

1. `coverage_total = 24`.
2. Métricas no negativas.
3. Pregunta no vacía y `<= 500` caracteres.
4. FAQ entre 10 y 20.
5. Citas visibles y con URL.
6. Sin rutas absolutas ni secretos.
7. Sin escritura en `data/`.
8. Estado de datos y modelo visible.
9. Resultados conservados en sesión.
10. Errores controlados sin trazas.
