# Data Model: stickers de Valer-IA en WhatsApp (spec 034)

## Catálogo (`config/stickers.toml`)

```toml
[stickers.valeria-hola]
file = "docs/whatsapp/stickers/valeria-hola.webp"
text = "Hola"            # texto visible; "" si no tiene
language = "es"          # idioma del texto; "none" si no tiene
situations = ["greeting_new_conversation"]
position = "before"      # before | after
```

| Campo | Regla |
|---|---|
| `file` | ruta relativa al repositorio; existe, ≤ 500 KB, cabecera `RIFF….WEBP` |
| `text` | el texto compuesto en el diseño (ficha de la spec 030) |
| `language` | `es` o `none`; en inglés solo se admiten `none` |
| `situations` | una o más de: `greeting_first_contact`, `greeting_new_conversation`, `greeting_mid`, `thanks`, `closing`, `assent`, `profile_saved`, `action_done`, `thinking` |
| `position` | `before` (antes del texto) o `after` (después) |

Prioridad cuando concurren situaciones: `profile_saved` > `action_done` > `closing` > `thanks` >
`greeting_first_contact` > `greeting_new_conversation` > `greeting_mid` > `assent`.

## Configuración (`[channels]` en `config/agent.toml`)

| Clave | Tipo | Defecto | Validación |
|---|---|---|---|
| `stickers` | bool | `true` | — |
| `stickers_per_conversation` | int | 4 | 0 ≤ valor ≤ 20 (0 = sin stickers) |

Configuración del plugin (`plugins.entries.valeria-bridge.config` en `openclaw/openclaw.json5`):

- `stickersDir`: `${VALERIA_REPO}/docs/whatsapp/stickers`;
- `stickerThinkingMs`: 8000 (0 = sin «Pensando»).

## Uso en la conversación (`channel_stickers`, tabla nueva aditiva)

| Columna | Tipo | Regla |
|---|---|---|
| `thread_id` | TEXT | hilo del canal |
| `sticker` | TEXT | nombre del catálogo |
| `turn_no` | INTEGER | número de respuesta atendida en el hilo (para «no en dos respuestas seguidas») |
| `sent_at` | TEXT | ISO UTC |

Más una columna `answered_turns INTEGER NOT NULL DEFAULT 0` en `channel_threads`, que se incrementa con cada
respuesta atendida. Sin texto ni números.

## Respuesta del canal (campo nuevo, opcional)

```json
"sticker": {"name": "valeria-gracias", "path": "D:/…/docs/whatsapp/stickers/valeria-gracias.webp", "position": "after"}
```

`null` cuando no hay sticker. La ruta es absoluta en la máquina del servidor; el plugin la lee del disco.

## Registro (`ChannelLogRecord`)

| Campo | Valores |
|---|---|
| `sticker` | nombre del sticker decidido o `null` |
