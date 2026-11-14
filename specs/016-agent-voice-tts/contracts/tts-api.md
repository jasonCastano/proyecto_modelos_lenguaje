# Contrato HTTP: voz del agente (spec 016)

Los dos endpoints son nuevos. Los existentes no cambian, salvo el campo opcional `voice_available` en
`/api/health`.

## `GET /api/voice` → `200 VoiceStatus`

Estado del motor de voz. Responde siempre `200`; la indisponibilidad se expresa en el cuerpo.

```json
{
  "available": true,
  "state": "ready",
  "engine": "phonon",
  "model": "hf://gradium/phonon-40m-es",
  "voice": "Rebeca",
  "language": "es",
  "sample_rate": 24000,
  "license": "CC BY-NC 4.0 (modelo y voces); MIT/Apache-2.0 (motor)",
  "detail": null
}
```

Ejemplos de motor no disponible:
- `{"available": false, "state": "unavailable", "detail": "No se pudo descargar el modelo de voz: falta HF_TOKEN o no se aceptaron las condiciones del modelo.", ...}`
- `{"available": false, "state": "disabled", "detail": "Voz desactivada por configuración.", ...}`

Reglas:
- Ningún campo incluye el token, rutas absolutas ni trazas.
- `state = "loading"` implica `available = true`: la siguiente petición espera a que termine la carga.

## `POST /api/tts` → audio de una oración

**Request** (`application/json`, `extra="forbid"`):

```json
{ "text": "Manuelita produce azúcar, etanol y energía [U2].", "voice": null, "thread_id": "t-123", "segment": 0 }
```

**Respuestas**:

| Código | Cuerpo | Cuándo |
|--------|--------|--------|
| `200` | `audio/wav` (PCM 16 bits mono, `sample_rate` del modelo), con cabeceras `X-Voice`, `X-Synth-Ms`, `X-Audio-Ms` y `Cache-Control: no-store` | Síntesis correcta del texto limpio. |
| `204` | vacío | Después de limpiar no queda texto pronunciable (por ejemplo, solo `[U2]`). |
| `422` | `{"error": {"code": "text_too_long" \| "unknown_voice" \| "invalid_request", ...}}` | `text` vacío o con más de `max_chars`, o voz fuera del catálogo. |
| `503` | `{"error": {"code": "voice_unavailable", "message": "...", "retryable": false, "action": "continuar sin voz"}}` | Motor deshabilitado o no disponible. |
| `500` | `{"error": {"code": "voice_error", "message": "...", "retryable": true, "action": "reintentar"}}` | Falla de síntesis puntual. El motor sigue `ready`. |

Las respuestas de error usan el mismo formato `{"error": {...}}` que el resto de la API.

Invariantes:
- El texto se limpia en el servidor con `clean_for_speech`; el audio nunca pronuncia `[U#]`, URLs ni la marca de
  oración neutralizada.
- La petición no depende de `DEEPSEEK_API_KEY` ni del `mode` del chat (FR-008, FR-011).
- Cada petición agrega una línea a `voice.jsonl` (ver data-model). Si el registro falla, la respuesta no cambia.
- La síntesis no escribe archivos en `data/` ni en el repositorio.

## `GET /api/health` (cambio compatible)

`HealthStatus` agrega `voice_available: bool = False`. Refleja `VoiceStatus.available` sin forzar la carga del
modelo; durante el warmup vale `true` si el estado es `loading`.
