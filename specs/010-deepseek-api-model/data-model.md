# Fase 1 — Modelo de datos: proveedor DeepSeek por API

**Feature**: `010-deepseek-api-model`
**Fecha**: 2026-10-31

## 1. Configuración del proveedor

### 1.1 ProviderConfig

Vista validada de `config/llm.toml` (sección `[llm]`).

| Campo | Tipo | Validación | Origen |
|-------|------|------------|--------|
| `provider` | texto | `deepseek` (enum extensible) | TOML |
| `model` | texto | no vacío, sin espacios | TOML o `DEEPSEEK_MODEL` |
| `base_url` | texto | `https://` obligatorio en producción | TOML o `DEEPSEEK_BASE_URL` |
| `api_key_env` | texto | nombre de variable, `^[A-Z][A-Z0-9_]*$` | TOML |
| `temperature` | número | `0.0 ≤ x ≤ 1.0` | TOML |
| `top_p` | número | `0.01 ≤ x ≤ 1.0` | TOML |
| `max_output_tokens` | entero | `128 ≤ x ≤ 8192` | TOML |
| `context_window` | entero | `2048 ≤ x ≤ 131072` | TOML |
| `default_context_pack` | texto | `"8000"` o `"32000"`, nunca mayor que `context_window` | TOML |
| `timeout_seconds` | entero | `5 ≤ x ≤ 300` | TOML |
| `max_retries` | entero | `0 ≤ x ≤ 3` | TOML |
| `retry_backoff_seconds` | número | `0 ≤ x ≤ 30` | TOML |
| `cost_per_1k_input` | número | `≥ 0` (USD) | TOML |
| `cost_per_1k_output` | número | `≥ 0` (USD) | TOML |
| `language` | texto | `es` por defecto | TOML |

**Invariantes**:

- `api_key_present` se calcula en tiempo de ejecución; el valor de la clave **nunca** forma parte del modelo.
- `to_dict()` expone `api_key_env` y `api_key_present`, jamás la clave.
- No se aceptan claves llamadas `api_key`, `token` o `secret` en el TOML: error de configuración.

## 2. Llamada remota

### 2.1 RemoteCall

| Campo | Tipo | Notas |
|-------|------|-------|
| `task` | texto | `summary`, `faq`, `qa` |
| `model` | texto | identificador exacto enviado al proveedor |
| `prompt_version` | texto | versión del prompt usado |
| `input_tokens` | entero | reportados por el proveedor o estimados |
| `output_tokens` | entero | idem |
| `latency_seconds` | número | medido en el cliente |
| `status` | texto | `ok`, `error` |
| `error_code` | texto o nulo | uno de los códigos de §3 |
| `estimated_cost_usd` | número | calculado con las tarifas |

**Invariantes**: `input_tokens` y `output_tokens` nunca son negativos; `estimated_cost_usd ≥ 0`; una
llamada con error conserva modelo, latencia y código, pero no costo de salida inventado.

## 3. Errores del proveedor

### 3.1 ProviderError

| Código | Condición | Reintentable | Mensaje al usuario |
|--------|-----------|--------------|--------------------|
| `config_missing_key` | variable de entorno ausente o vacía | no | «Define `DEEPSEEK_API_KEY` en `.env` y recarga.» |
| `auth_failed` | 401 / 403 | no | «La clave no es válida o fue revocada. Genera una nueva.» |
| `model_unavailable` | 404 o modelo ausente del catálogo | no | «El modelo configurado no está disponible en la cuenta.» |
| `rate_limited` | 429 | sí | «Cuota agotada. Espera unos minutos o activa el modo demostración.» |
| `timeout` | sin respuesta en `timeout_seconds` | sí | «El proveedor no respondió en N s. Reintenta.» |
| `provider_unavailable` | 5xx, DNS o red caída | sí | «Proveedor no disponible. Reintenta o usa el modo demostración.» |
| `empty_response` | respuesta sin contenido | sí | «Respuesta vacía del proveedor. Reintenta.» |
| `invalid_response` | JSON no parseable | sí | «Respuesta inesperada del proveedor. Reintenta.» |

**Mapeo a las tareas**: `timeout` → `model_timeout`; el resto → `model_error`, conservando `status=error` y
`review_required=True` cuando no haya citas.

## 4. Resumen de uso

### 4.1 UsageSummary

| Campo | Tipo | Notas |
|-------|------|-------|
| `calls` | entero | llamadas realizadas en la sesión |
| `input_tokens` | entero | acumulado |
| `output_tokens` | entero | acumulado |
| `estimated_cost_usd` | número | acumulado |
| `provider` | texto | `deepseek` |
| `model` | texto | identificador exacto |
| `failed_calls` | entero | llamadas con error |

**Regla**: el resumen de sesión que se descarga no incluye claves ni encabezados de autorización.

## 5. Salud del proveedor

### 5.1 HealthStatus

| Estado | Significado | Acción sugerida |
|--------|-------------|-----------------|
| `ready` | clave válida y modelo disponible | ninguna |
| `missing_key` | falta la variable de entorno | definir la clave |
| `auth_failed` | clave inválida o revocada | generar una nueva |
| `model_unavailable` | el id no existe en la cuenta | ajustar `model` |
| `rate_limited` | cuota agotada | esperar o usar demo |
| `unavailable` | sin red o 5xx | reintentar más tarde |

**Transiciones**: cualquier estado → `ready` tras una verificación exitosa; `ready` → `rate_limited` si una
llamada recibe 429; `ready` → `auth_failed` si una llamada recibe 401/403. El estado se muestra en la app y
en `--check`, nunca con la clave.

## 6. Relaciones

```text
config/llm.toml ──► ProviderConfig ──► modelo LangChain
ProviderConfig ──► HealthStatus
ProviderConfig ──► RemoteCall (por invocación) ──► TaskResult
RemoteCall ──► UsageSummary (acumulado de sesión)
ProviderError ──► TaskResult.error
```

## 7. Validaciones transversales

1. Ninguna salida contiene la clave, encabezados de autorización ni rutas absolutas.
2. La configuración no admite campos de secreto.
3. El costo se calcula solo con tarifas configuradas; si son cero, se informa «no configurado».
4. `default_context_pack` nunca supera `context_window`.
5. El modo demostración no construye cliente remoto ni requiere clave.
6. El modelo enviado al proveedor es el mismo que se registra en el resultado.
