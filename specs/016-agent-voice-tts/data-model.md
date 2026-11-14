# Data Model: Voz del agente (spec 016)

## VoiceConfig (servidor, `voice/config.py`)

Se lee de `config/voice.toml` y las variables `MANUELITA_VOICE_*` la sobrescriben (ver
[contracts/voice-config.md](./contracts/voice-config.md)).

| Campo | Tipo | Regla |
|-------|------|-------|
| `enabled` | bool | Por defecto `true`. Con `false`, el estado es no disponible y el motivo es «Voz desactivada por configuración». |
| `engine` | `"phonon" \| "fake"` | Por defecto `"phonon"`. `"fake"` solo se usa en pruebas y demos sin modelo. |
| `model` | str | Por defecto `"hf://gradium/phonon-40m-es"`. |
| `language` | str | `"es"`. |
| `quant` | uno de `ptts.available_quants()` (`f32`, `q8_0`, `q8_1`, `q8k`, `q6k`, `q5_0`, `q5_1`, `q5k`, `q4_0`, `q4_1`, `q4k`) | Por defecto `"q8_0"`. |
| `voice` | str | Nombre o identificador del catálogo. Por defecto `"Rebeca"`, la voz oficial elegida por el equipo (R4, T037). No puede ser vacío. |
| `voice_gender` | `"female" \| "male"` | Metadato informativo, `"female"`. |
| `max_chars` | int | Entre 1 y 1000; por defecto 600. Es el límite por petición a `/api/tts`. |
| `warmup` | bool | Por defecto `true`: carga el modelo en un hilo al arrancar la app. |

## VoiceStatus (API, `GET /api/voice`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `available` | bool | `true` solo si el motor está cargado o cargable y la configuración lo permite. |
| `state` | `"disabled" \| "loading" \| "ready" \| "unavailable"` | Ver las transiciones más abajo. |
| `engine` | str | `"phonon"` o `"fake"`. |
| `model` | str | Sin token ni rutas absolutas. |
| `voice` | str | Nombre configurado. |
| `language` | str | `"es"`. |
| `sample_rate` | int \| null | `24000` cuando está listo. |
| `license` | str | `"CC BY-NC 4.0 (modelo y voces); MIT/Apache-2.0 (motor)"`. |
| `detail` | str \| null | Motivo legible si no está disponible; sin trazas ni rutas. |

**Transiciones de estado del motor (`VoiceService`)**:

```text
disabled                       (enabled=false; terminal)
loading ──ok──▶ ready ──error de síntesis──▶ ready  (el error se registra, el motor sigue)
   │
   └──error de import/descarga/CPU──▶ unavailable   (se reintenta solo al reiniciar la app)
```

`loading` es el estado inicial. Si llega una petición antes del warmup, esa petición dispara la carga y espera a
que termine.

## SpeechSegment (petición `POST /api/tts`)

| Campo | Tipo | Regla |
|-------|------|-------|
| `text` | str | De 1 a `max_chars` caracteres antes de limpiar; si se excede, responde `422 text_too_long`. |
| `voice` | str \| null | Opcional; debe existir en el catálogo y si no, responde `422 unknown_voice`. Por defecto, la voz configurada. |
| `thread_id` | str \| null | Opcional, solo para el registro. |
| `segment` | int \| null | Índice ≥ 0 de la oración dentro de la respuesta, solo para el registro. |

**Limpieza (`clean_for_speech`)**, aplicada en este orden:

1. Quitar la marca `[instrucción embebida omitida]`.
2. Quitar citas `[U\d+]` y listas `[U1, U2]`.
3. Convertir enlaces Markdown `[texto](url)` en `texto` y quitar las URLs sueltas.
4. Quitar el énfasis y los encabezados Markdown (`*`, `_`, `#`, `` ` ``, `>`) y las viñetas al inicio de línea.
5. Convertir `%` en « por ciento » y `&` en « y ».
6. Colapsar los espacios.

Si el resultado queda vacío o sin letras ni dígitos, se responde `204` sin audio.

## SpeechAudio (respuesta `200`)

- `audio/wav`, PCM 16 bits, mono, a la frecuencia `sample_rate` del modelo.
- Cabeceras: `X-Voice` (nombre), `X-Synth-Ms` (milisegundos de síntesis) y `X-Audio-Ms` (duración del audio).

## VoiceLogRecord (`MANUELITA_STATE_DIR/logs/voice.jsonl`)

| Campo | Tipo |
|-------|------|
| `ts` | ISO-8601 UTC |
| `thread_id` | str \| null |
| `segment` | int \| null |
| `voice` | str |
| `chars` | int (texto limpio) |
| `synth_ms` | float |
| `audio_ms` | float |
| `status` | `"ok" \| "empty" \| "error" \| "unavailable"` |
| `error` | str \| null (código, sin traza) |

No se guarda el texto ni el audio (FR-014). Si no se puede escribir el registro, la respuesta no falla.

## Entidades del navegador (`web/src/lib/voice.ts`)

### SentenceSegmenter

- `push(chunk: string): string[]`: acumula el texto y devuelve las oraciones completas nuevas. Una oración se cierra
  con `.`, `!`, `?`, `…` o `;` seguidos de espacio o salto de línea, o con un salto de línea doble. No corta en
  abreviaturas comunes (`Sr.`, `Dra.`, `etc.`, `p. ej.`, `No.`) ni en números decimales (`3.5`).
- `flush(): string[]`: devuelve el resto pendiente al terminar el turno.
- Una oración de más de `max_chars` (600) se parte por comas o espacios.
- El **primer** segmento de cada respuesta se limita a `FIRST_SEGMENT_CHARS` = 120, cortando en una coma o un
  espacio, para que el primer audio llegue en < 1,5 s (SC-001, research R10).

### ReadingSession (una por respuesta)

| Campo | Tipo |
|-------|------|
| `id` | str (turno o `live`) |
| `threadId` | str \| null |
| `state` | `"idle" \| "playing" \| "stopped" \| "done" \| "failed"` |
| `queued` | lista ordenada de oraciones con índice |
| `spokenText` | texto ya encolado (para compararlo con la respuesta final) |
| `firstAudioMs` | número \| null: tiempo desde que se cierra la primera oración hasta que empieza a sonar (SC-001) |

**Transiciones**:

```text
idle ──primera oración──▶ playing ──cola vacía y flush──▶ done
playing ──stop / silenciar / nueva pregunta / unmount──▶ stopped   (aborta fetch y para el audio)
playing ──503 o error de red──▶ failed   (aviso «voz no disponible»; el texto sigue)
done|stopped ──«Escuchar»──▶ playing    (una sesión nueva con la respuesta guardada)
```

Solo puede haber **una sesión sonando** a la vez en la página.

### VoicePreference (`localStorage["manuelita.voice.muted"]`)

- `"1"` significa silenciado; si la clave no existe, la voz está activada.
- La lectura y la escritura van en `try/catch`. Si el almacenamiento falla, se asume activada solo durante la
  sesión.
