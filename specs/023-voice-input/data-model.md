# Data Model: Dictado por voz (spec 023)

Ninguna entidad se guarda en `data/` ni en disco. El audio vive solo en memoria durante una petición (FR-018).

## 1. `SttConfig` (`config/stt.toml`, sección `[stt]`; variables `MANUELITA_STT_*`)

| Campo | Tipo | Defecto | Validación |
|---|---|---|---|
| `enabled` | bool | `true` | `MANUELITA_STT_ENABLED` tiene prioridad |
| `engine` | str | `"whisper"` | `whisper` \| `fake` (`MANUELITA_STT_ENGINE`) |
| `model` | str | `"base"` | `tiny`, `base`, `small`, `medium`, `large-v3`, `large-v3-turbo` o una ruta `hf://…` (`MANUELITA_STT_MODEL`) |
| `compute_type` | str | `"int8"` | `int8`, `int8_float32`, `float32` |
| `cpu_threads` | int | `0` (automático) | 0–32 |
| `language` | str | `"es"` | código ISO de dos letras |
| `beam_size` | int | `1` | 1–5 |
| `vocabulary` | list[str] | Manuelita, Valer-IA Caña, Palmira, Valle del Cauca, Fundación Manuelita, Océanos, Mejillones América, Laredo, Aceites Manuelita, … | 0–60 términos de 1–40 caracteres; el `initial_prompt` armado no supera 600 caracteres |
| `corrections` | dict[str, str] | `{"valeria caña" = "Valer-IA Caña", …}` | claves en minúsculas; valores no vacíos |
| `no_speech_threshold` | float | `0.6` | 0–1 |
| `max_seconds` | float | `60` | 1–120 |
| `max_bytes` | int | `2_097_152` | ≥ 44 + 16000 × 2 × `max_seconds` |
| `silence_ms` | int | `1500` | 300–5000 (el cliente lo lee de `GET /api/stt`) |
| `min_speech_ms` | int | `300` | 100–2000 |
| `handsfree_idle_seconds` | int | `60` | 10–600 |
| `max_concurrent` | int | `2` | 1–8 |
| `queue_timeout_seconds` | float | `10` | 1–60 |
| `warmup` | bool | `true` | `MANUELITA_STT_WARMUP` |

Una configuración inválida deja el servicio en `unavailable` con el motivo; no detiene la API (igual que la voz).

## 2. `Recording` (cliente, en memoria)

| Campo | Tipo | Notas |
|---|---|---|
| `samples` | `Float32Array[]` | bloques del `AudioWorklet` a la frecuencia del contexto |
| `sampleRate` | number | 44 100 o 48 000 normalmente |
| `startedAt` / `endedAt` | number | `performance.now()` |
| `speechMs` | number | tiempo marcado como habla |
| `endReason` | `"manual" \| "silence" \| "limit" \| "cancel" \| "hidden"` | `cancel` y `hidden` no se envían (FR-005) |

Se convierte a WAV PCM16 mono a 16 kHz (`encodeWav16k`) y se descarta al recibir la respuesta.

## 3. `Transcription` (respuesta de `POST /api/stt`)

| Campo | Tipo | Notas |
|---|---|---|
| `text` | str | transcripción ya corregida (R4); `""` si `empty` |
| `empty` | bool | sin voz reconocible (FR-009) |
| `truncated` | bool | el texto se recortó a 2000 caracteres (límite de `ChatRequest.message`) |
| `language` | str | idioma pedido (`es`) |
| `audio_ms` | int | duración del audio recibido |
| `stt_ms` | int | tiempo de reconocimiento en el servidor |
| `model` | str | p. ej. `base-int8` |

## 4. `InputMeta` (nuevo campo opcional en `ChatRequest` y `TurnModel`)

| Campo | Tipo | Validación |
|---|---|---|
| `source` | `"voice"` | literal; sin `input`, el mensaje se considera escrito |
| `audio_ms` | int | 0–120 000 |
| `stt_ms` | int | 0–60 000 |
| `edited` | bool | el visitante cambió el texto antes de enviarlo |
| `handsfree` | bool | enviado en modo manos libres |

- Se guarda en la entrada del turno del estado del hilo (`turn_log`) y se devuelve en `TurnModel.input`.
- No entra al registro del contacto ni a la memoria de largo plazo, y no afecta las decisiones del grafo.

## 5. `SttStatus` (`GET /api/stt`; resumen en `/api/health`)

| Campo | Tipo | Notas |
|---|---|---|
| `available` | bool | |
| `state` | `"disabled" \| "loading" \| "ready" \| "unavailable"` | |
| `engine`, `model`, `language` | str | |
| `detail` | str \| null | motivo legible, sin rutas ni claves |
| `max_seconds`, `silence_ms`, `min_speech_ms`, `handsfree_idle_seconds` | number | parámetros del cliente |
| `privacy` | str | texto mostrado junto al micrófono (FR-019) |

## 6. `DictationState` (cliente, `useDictation`)

```text
idle ──pulsar──▶ requesting ──permiso──▶ listening ──fin (manual/silencio/límite)──▶ processing
  ▲                  │ negado                │ cancelar/ocultar                         │
  │                  ▼                       ▼                                          ▼
  └──────────── error(permission) ◀──── idle (nada enviado)          ready(text) │ empty │ error
                                                                     │ normal: texto al campo → idle
                                                                     │ manos libres: enviar → waiting_reply
waiting_reply ──respuesta suena──▶ speaking ──termina──▶ listening (manos libres)
speaking ──voz del visitante (umbral ×2, 250 ms)──▶ voice.stop() → listening
listening (manos libres) ──60 s sin voz──▶ idle (manos libres apagado)
```

Errores tipificados: `permission`, `no_device`, `insecure`, `unsupported`, `unavailable`, `busy`, `too_long`,
`network` y `server`. Cada uno tiene su mensaje en español en `contracts/ui.md`.

## 7. Preferencias en el navegador

| Clave | Valor | Uso |
|---|---|---|
| `manuelita.stt.handsfree` | `"1"` \| `"0"` | modo manos libres (FR-017) |

Todo acceso a `localStorage` va en `try/catch`. Sin almacenamiento, el modo normal es el defecto.

## 8. Evaluación (`docs/evaluacion_stt.json`)

- `config`: `SttConfig` sin rutas.
- `items[]`: `id`, `kind` (`speech` \| `silence` \| `noise` \| `human`), `voice`, `audio_ms`, `stt_ms`, `reference`,
  `hypothesis`, `wer`, `vocab_hits` y `vocab_total`.
- `summary`:
  - `wer`;
  - `vocab_accuracy`;
  - `latency_ms` (p50/p90 por tramo: ≤ 5 s, 5–10 s, > 10 s);
  - `empty_rate_on_silence`;
  - `targets` (`SC-001` a `SC-004`: bool).

En el modo `human`, `reference` es la del `.txt` local, y la hipótesis no se publica en el informe versionado salvo
con `--include-human-text`.
