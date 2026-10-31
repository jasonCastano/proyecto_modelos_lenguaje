# Contrato de errores y diagnóstico del proveedor

**Feature**: `011-deepseek-api-model`
**Versión**: 1.0
**Fecha**: 2026-10-31

## 1. Mapeo de errores

| Situación | Código interno | Tipo de error | Reintento | Mensaje accionable |
|-----------|----------------|---------------|-----------|--------------------|
| Variable de entorno ausente o vacía | `config_missing_key` | `LLMConfigError` | no | «Define `DEEPSEEK_API_KEY` en `.env` y recarga la app.» |
| 401 / 403 | `auth_failed` | `LLMAuthError` | no | «La clave no es válida o fue revocada. Genera una nueva.» |
| 404 o modelo fuera del catálogo | `model_unavailable` | `LLMModelMissingError` | no | «El modelo configurado no está disponible en la cuenta.» |
| 429 | `rate_limited` | `LLMRateLimitError` | sí | «Cuota agotada. Espera unos minutos o activa el modo demostración.» |
| Sin respuesta en `timeout_seconds` | `timeout` | `LLMTimeoutError` | sí | «El proveedor no respondió en {N} s. Reintenta.» |
| 5xx, DNS o red caída | `provider_unavailable` | `LLMUnavailableError` | sí | «Proveedor no disponible. Reintenta o usa el modo demostración.» |
| Respuesta sin contenido | `empty_response` | `LLMResponseError` | sí | «Respuesta vacía del proveedor. Reintenta.» |
| JSON no parseable | `invalid_response` | `LLMResponseError` | sí | «Respuesta inesperada del proveedor. Reintenta.» |

**Regla**: el mensaje visible nunca reproduce el cuerpo crudo del proveedor ni encabezados de autorización.

## 2. Correspondencia con el contrato de tareas

| Código del proveedor | `TaskResult.error` | `status` |
|----------------------|--------------------|----------|
| `timeout` | `model_timeout` | `error` |
| `auth_failed`, `rate_limited`, `provider_unavailable`, `empty_response`, `invalid_response` | `model_error` | `error` |
| `config_missing_key`, `model_unavailable` | `invalid_config` | `error` |

El resto de invariantes de `TaskResult` no cambia: `status=fallback` implica `citations=[]`; `status=ok`
implica al menos una cita.

## 3. Comando `--check`

```bash
uv run python -m proyecto_modelos_lenguaje.llm --check
```

Salida de éxito (código `0`):

```json
{
  "ok": true,
  "provider": "deepseek",
  "model": "deepseek-flash",
  "base_url": "https://api.deepseek.com/v1",
  "api_key_present": true,
  "latency_ms": 412.5,
  "detail": "modelo disponible"
}
```

Salida de fallo (código `2`):

```json
{
  "ok": false,
  "error": "LLMAuthError",
  "code": "auth_failed",
  "detail": "La clave no es válida o fue revocada."
}
```

**Garantía**: en ningún caso se imprime el valor de la clave ni el encabezado `Authorization`.

## 4. Comando `--print-config`

```bash
uv run python -m proyecto_modelos_lenguaje.llm --print-config
```

Salida (código `0`), validable contra `provider-config.schema.json`:

```json
{
  "provider": "deepseek",
  "model": "deepseek-flash",
  "base_url": "https://api.deepseek.com/v1",
  "api_key_env": "DEEPSEEK_API_KEY",
  "api_key_present": true,
  "temperature": 0.1,
  "top_p": 0.9,
  "max_output_tokens": 1024,
  "context_window": 16384,
  "default_context_pack": "8000",
  "timeout_seconds": 60,
  "max_retries": 1,
  "retry_backoff_seconds": 2.0,
  "cost_per_1k_input": 0.0,
  "cost_per_1k_output": 0.0,
  "language": "es"
}
```

## 5. Modo demostración

- Se activa con `PML_DEMO=1` o con el interruptor de la app.
- No construye cliente remoto, no lee la clave y no hace peticiones de red.
- La interfaz muestra un distintivo persistente y el panel indica «modelo de demostración».
- Los resultados declaran `model = "scripted-fake"`.

## 6. Garantías de seguridad

1. La clave solo se lee de `os.environ[api_key_env]`.
2. `to_dict()` y cualquier serialización usan `api_key_present`, nunca el valor.
3. Los registros no incluyen prompts completos ni encabezados.
4. La descarga de sesión no contiene credenciales.
5. Un test busca la clave en los artefactos generados y falla si aparece.
