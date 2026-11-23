# Contrato: API de dictado (spec 023)

Todas las respuestas de error usan el formato de error existente de la API (`{"error": {"code", "message",
"retryable", "action"}}`), con mensajes en español y sin detalles técnicos (FR-021).

## 1. `GET /api/stt`

Estado del reconocimiento. No dispara la carga del modelo si `warmup = false`.

```json
{
  "available": true,
  "state": "ready",
  "engine": "whisper",
  "model": "base-int8",
  "language": "es",
  "detail": null,
  "max_seconds": 60,
  "silence_ms": 1500,
  "min_speech_ms": 300,
  "handsfree_idle_seconds": 60,
  "privacy": "Tu voz se convierte en texto en el servidor del proyecto y el audio no se guarda."
}
```

| `state` | `available` | Significado |
|---|---|---|
| `disabled` | false | `enabled = false` |
| `loading` | false | modelo cargando o descargando la primera vez (la interfaz muestra «Preparando el micrófono…») |
| `ready` | true | listo |
| `unavailable` | false | error de configuración, de descarga o de carga; `detail` explica el motivo |

## 2. `POST /api/stt`

- **Petición**: cuerpo binario WAV RIFF, PCM 16 bits, mono, 16 000 Hz. `Content-Type: audio/wav`. Cabecera opcional
  `X-Thread-Id` (solo para el registro de tiempos).
- **Límites**: `max_bytes` (2 MiB) y `max_seconds` (60 s).

**200**:

```json
{"text": "¿Qué produce Manuelita?", "empty": false, "truncated": false, "language": "es",
 "audio_ms": 2040, "stt_ms": 451, "model": "base-int8"}
```

Sin voz reconocible: `{"text": "", "empty": true, …}` (FR-009). No es un error.

| Código | `error.code` | Cuándo | `retryable` |
|---|---|---|---|
| 400 | `stt_empty_audio` | cuerpo vacío o sin muestras | false |
| 413 | `stt_too_large` | supera `max_bytes` o `max_seconds` | false |
| 415 | `stt_unsupported_format` | no es WAV PCM16 mono a 16 kHz | false |
| 503 | `stt_unavailable` | servicio deshabilitado, cargando o con error (`action: "escribir"`) | true |
| 503 | `stt_busy` | se agotó `queue_timeout_seconds` esperando turno | true |
| 500 | `stt_error` | fallo inesperado del motor | true |

**Reglas**:
1. El audio se procesa en memoria; ninguna ruta escribe en disco (FR-018). El registro `stt` guarda solo
   `thread_id`, `audio_ms`, `stt_ms`, `bytes`, `model`, `status`, `chars` y `error` (nunca el texto).
2. El texto pasa por la corrección del vocabulario (R4) y se recorta a 2000 caracteres (`truncated = true`).
3. Segmentos con `no_speech_prob > no_speech_threshold` o con texto de ruido conocido se descartan.
4. Como máximo `max_concurrent` transcripciones a la vez; las demás esperan.

## 3. `GET /api/health`

El objeto existente agrega `"stt_available": bool`. Los campos actuales no cambian.

## 4. `ChatRequest` y `TurnModel`

Campo opcional nuevo, idéntico en ambos:

```json
"input": {"source": "voice", "audio_ms": 2040, "stt_ms": 451, "edited": false, "handsfree": false}
```

- Sin `input`, el comportamiento es el actual (mensaje escrito). Con `extra="forbid"`, un `source` distinto de
  `"voice"` responde 422.
- `/api/chat`, `/api/chat/stream` (evento `done`) y la reanudación de hilos devuelven `turn.input` tal como se
  recibió.
- El grafo no lee `input` (FR-012). Se registra en la entrada del turno para la vista técnica (FR-022).

## 5. CLI

```text
python -m proyecto_modelos_lenguaje.stt --check
    estado, modelo, carga y transcripción de un clip sintético
python -m proyecto_modelos_lenguaje.stt eval [--models base small] [--voices Rebeca …]
                                             [--audio-dir DIR] [--json-out PATH]
    batería R11 → docs/evaluacion_stt.{md,json}; exit 1 si no cumple SC-001 a SC-004
python -m proyecto_modelos_lenguaje.stt transcribe ARCHIVO.wav
    texto por la salida estándar (depuración local)
```
