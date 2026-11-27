# Data Model: voz, idioma único y formato ordenado (spec 029)

## Entrada del puente (plugin → backend)

| Campo | Regla |
|---|---|
| `kind` | `audio` si `content` **o** `body` contienen `[Audio]`, `Transcript:` o `<media:audio>` en cualquier posición; si no, según el texto |
| `input_mode` | `voice` cuando `kind = audio` |
| `text` | Solo la transcripción (texto tras el último `Transcript:`) o el texto escrito; **nunca** el encabezado del gateway ni números de teléfono del encabezado; ≤ 4.000 caracteres |
| `language_hint` | Sin cambio (el backend decide con `language_of`) |

Validación: si `kind = audio` y la transcripción queda vacía → `text = null` (el backend pide repetir).

## Idioma del turno

| Campo | Tipo | Regla |
|---|---|---|
| `language` | `es` \| `en` | `language_of(texto, pista)`; mensajes ≤ 3 palabras heredan el idioma anterior del hilo; por defecto `es` |

Viaja: puente → `ChatService.send(..., language=)` → estado del grafo (`turn_language`) → `to_whatsapp(..., language=)`.

## Aviso de seguridad

| Campo | Tipo | Regla |
|---|---|---|
| `sensitive_kinds` | lista | Tipos detectados en el **mensaje de la persona**: `credit_card`, `document`, `password` (no `phone`, no `email`) |
| `sensitive_notice_given` | bool (estado del hilo) | Se marca al dar el aviso; con `true` no se repite salvo un dato sensible nuevo en un turno posterior |
| Texto | `conduct.md` § `sensitive_notice` / `sensitive_notice_en` | Una frase, al final de la respuesta, sin repetir el dato |

## Fuente presentada

| Campo | Regla |
|---|---|
| `number` | Consecutivo desde 1, por orden de primera aparición; único por (`url`, `page`) |
| `title` | `clean_title`: una línea, sin listas ni numeraciones de índice, ≤ 80 caracteres; respaldo: nombre del documento del enlace; último respaldo: dominio |
| `page` | Opcional; se muestra «, p. X» |
| `url` | Obligatoria si existe en la cita |
| `kind` | `public` \| `synthetic` (bloques separados, como en la spec 025) |

Línea: `[n] Título, p. X — URL` (es) / igual en inglés; encabezado `Fuentes:` / `Sources:`; sintéticas
`Fuentes sintéticas (demostración):` / `Synthetic sources (demo):`.

## Hallazgo de la revisión (`channels/quality.py`)

| Campo | Valores |
|---|---|
| `code` | `mixed_language`, `wrong_sources_header`, `sources_line_format`, `sources_numbering`, `duplicate_source`, `dirty_title`, `unexpected_notice`, `missing_notice` |
| `message_index` | Índice del mensaje afectado |
| `detail` | Texto corto sin datos personales |
