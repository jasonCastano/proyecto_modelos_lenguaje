# API Contract — RAG y showcase

**Feature**: `012-manuelita-rag-showcase`
**Versión**: 1.0
**Base**: `/api`
**Formato**: JSON UTF-8

## Reglas generales

- Todas las respuestas usan `application/json`.
- La clave del proveedor vive solo en el servidor; nunca aparece en una respuesta, log o error.
- `mode` acepta `real` (por defecto) o `demo`.
- Los errores usan el formato `ApiError` de `data-model.md`.
- La API no escribe en `data/`.
- Los endpoints son idempotentes para lectura; `ask`, `summary` y `faq` pueden consumir cuota del proveedor.

## `GET /api/health`

Comprueba el proveedor y los datos sin revelar credenciales.

**Respuesta 200**:

```json
{
  "ok": true,
  "provider": "deepseek",
  "model": "deepseek-flash",
  "configured": true,
  "demo_available": true,
  "latency_ms": 572.36,
  "detail": "modelo disponible"
}
```

Si el proveedor falla, `ok=false`, `configured` refleja la presencia de la clave y `detail` es un mensaje seguro.

## `GET /api/showcase`

Devuelve la narrativa y las cifras reales para la página del Módulo 1.

**Respuesta 200**:

```json
{
  "generated_at": "2026-10-31T15:00:00Z",
  "data_status": "complete",
  "sections": [
    {
      "id": "problem",
      "order": 1,
      "title": "La información estaba dispersa",
      "body": "…",
      "status": "done",
      "metrics": [],
      "evidence": []
    }
  ],
  "metrics": [
    {
      "key": "units",
      "label": "Unidades de conocimiento",
      "value": 15211,
      "unit": "unidades",
      "source": "data/gold/reports/2026-10-gold-01/quality.json",
      "status": "complete"
    }
  ]
}
```

`data_status` puede ser `complete`, `incomplete` o `unknown`; si es distinto de `complete`, la UI muestra el aviso correspondiente.

## `POST /api/ask`

**Request**:

```json
{
  "question": "¿Qué productos ofrece Manuelita?",
  "mode": "real"
}
```

**Validación**:

- `question`: 1–500 caracteres, sin controles.
- `mode`: `real` o `demo`.

**Respuesta 200**: `CitedAnswer` (`contracts/answer.schema.json`).

- `status=ok`: al menos una cita.
- `status=fallback`: `citations=[]` y mensaje “No hay evidencia suficiente…”.
- `status=error`: `error` con código y acción.

**Errores**:

| HTTP | Código | Cuándo |
|------|--------|--------|
| 422 | `empty_question` / `question_too_long` | Pregunta inválida |
| 503 | `config_missing_key` | Sin credencial y `mode=real` |
| 502 | `auth_failed` / `provider_unavailable` | Proveedor rechaza o no responde |
| 504 | `timeout` | Se agota el tiempo |
| 429 | `rate_limited` | Cuota temporal |

## `POST /api/summary`

**Request**:

```json
{ "pack": "8000", "mode": "real" }
```

**Respuesta 200**: `CitedAnswer` con `status=ok|fallback|error`, `citations` y metadatos. El campo `answer` incluye el paquete usado.

## `POST /api/faq`

**Request**:

```json
{ "limit": 12, "mode": "real" }
```

**Respuesta 200**:

```json
{
  "items": [
    {
      "question": "¿Qué productos ofrece Manuelita?",
      "answer": "…",
      "citations": [],
      "status": "ready",
      "model": "deepseek-flash",
      "prompt_version": "1.0"
    }
  ]
}
```

`limit` está entre 10 y 20. Cada ítem con `status=ready` exige cita; `missing_evidence` no tiene citas.

## Seguridad

- No se aceptan claves en el cuerpo de la petición.
- La API no devuelve `DEEPSEEK_API_KEY`, `api_key`, tokens de entorno ni trazas.
- Los errores del proveedor se normalizan; no se reenvía el cuerpo crudo.
- En producción, el frontend y la API comparten origen; no se habilita CORS amplio.
- La API no sirve archivos fuera de `web/dist` en producción.

## Versionado

Cambios incompatibles en campos obligatorios suben la versión del contrato y requieren actualizar `answer.schema.json`, `showcase.schema.json`, las pruebas y este documento.
