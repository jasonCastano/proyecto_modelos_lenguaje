# Data Model: Valer-IA natural y con voz por WhatsApp (spec 028)

## InboundMessage (ampliado, `channels/bridge.py`)

| Campo | Tipo | Regla |
|---|---|---|
| `channel` | `whatsapp` \| `telegram` | Sin cambio |
| `message_id` | str 1–128 | Sin cambio (dedupe) |
| `sender` | E.164 o JID | Se convierte en seudónimo; nunca se guarda |
| `kind` | `text` \| `audio` \| … | `audio` cuando llega una transcripción |
| `text` | str ≤ 4.000 | Texto escrito o **transcripción** (requerido si `kind ∈ {text, audio}`) |
| `input_mode` | `text` \| `voice` | NUEVO. `voice` si `kind = audio` |
| `language_hint` | `es` \| `en` \| null | NUEVO. Idioma detectado por el dictado, si llega |

Validación: `kind = audio` sin transcripción (vacía o solo marcas) → respuesta natural pidiendo repetir
(FR-007), estado `answered`, sin turno del agente.

## ChannelThread (tabla `channel_threads`, ampliada)

| Campo | Tipo | Regla |
|---|---|---|
| `reply_format` | `auto` \| `text` \| `voice` | NUEVO, por defecto `auto`. Cambia solo por intención natural (FR-006) |
| `last_route` | str \| null | NUEVO. Ruta del último turno; habilita la continuidad del planificador |

Transiciones de `reply_format`: `auto` → `text` («respóndeme por escrito») → `voice` («mándame audio») → …;
«empecemos de nuevo» abre un hilo con `auto`.

## PendingAction (tabla `channel_pending`, sin cambios de esquema)

Estados: `pending` → `approved` | `rejected` | `expired` | `superseded` (NUEVO: la persona cambió de tema y la
acción se canceló con aviso). Vence a los 10 minutos. Nunca pasa a `approved` sin una afirmación clara.

## Intent (`channels/intents.py`)

| Intención | Ejemplos (es / en) | Efecto |
|---|---|---|
| `restart` | «empecemos de nuevo», «nueva conversación» / «start over» | Hilo nuevo, `reply_format = auto` |
| `format_text` | «respóndeme por escrito», «sin audios» / «text me» | `reply_format = text` |
| `format_voice` | «mándame audio», «respóndeme con voz» / «send me a voice note» | `reply_format = voice` |
| `approve` / `reject` | «dale», «sí, guárdalo» / «go ahead»; «mejor no» / «no thanks» | Resuelve la acción pendiente |
| `ambiguous` | «mmm», «no sé», «sí pero no» | Re-pregunta (acción pendiente) |
| `none` | Cualquier otra cosa | Turno normal del agente |

Una intención de formato o de reinicio puede venir junto a una pregunta: se aplica y luego se atiende la
pregunta en el mismo turno.

## VoiceReply (`channels/voice.py`)

| Campo | Tipo | Regla |
|---|---|---|
| `language` | `es` \| `en` | Idioma de la pregunta |
| `script` | str 40–110 palabras | Sin citas, URLs ni bloque de fuentes; toda cifra aparece en la respuesta |
| `audio_path` | ruta absoluta | `$MANUELITA_STATE_DIR/channels/voice/<uuid>.ogg`; se borra a los 10 min |
| `duration_ms` | int ≤ 60.000 | — |
| `voice` | nombre de voz | `Rebeca` (es) o la elegida en S3 (en) |
| `script_source` | `model` \| `fallback` | Para la traza y la evaluación |

Se genera solo si `reply_format = voice`, o si `reply_format = auto` e `input_mode = voice`.

## PlanningActivation (router)

| Campo | Tipo | Regla |
|---|---|---|
| `active` | bool | Verdadero si la consulta es de planificación o es repregunta de un turno `planning` |
| `reason` | `cue` \| `follow_up` \| none | Se muestra en la traza |
| `profile_unchanged` | bool | Siempre verdadero: el perfil del hilo no cambia |

## ChannelLogRecord (ampliado)

Campos nuevos: `input_mode`, `language`, `reply_format`, `voice_ms` (síntesis), `script_ms`, `voice_sent`
(bool). Sin texto de mensajes, transcripciones, guiones ni audio.
