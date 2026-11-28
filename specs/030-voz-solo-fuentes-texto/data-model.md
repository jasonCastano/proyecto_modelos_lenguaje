# Data Model: Respuesta por voz sin texto duplicado (spec 030)

Sin persistencia nueva. Cambian la respuesta del canal (contrato) y un campo del registro del canal.

## 1. Respuesta del canal (`ChannelReply` / `ChannelReplyModel`)

| Campo | Tipo | Regla |
|---|---|---|
| `messages` | `list[str]` | Respuesta completa con fuentes (sin cambios). Respaldo cuando la voz no se entrega. |
| `sources_messages` | `list[str]` (nuevo, opcional, por defecto `[]`) | Solo el bloque de fuentes en el idioma del turno. Vacío si no hay fuentes o si no hay voz. |
| `voice` | objeto \| `null` | Sin cambios (`audio_path`, `language`, `duration_ms`, `mime`). |

Validaciones:

- Si `voice` es `null`, `sources_messages` es `[]`.
- Cada elemento de `sources_messages` es ≤ `reply_max_chars` (1.500) y está formado solo por:
  - el encabezado («Fuentes:» / «Sources:» / «Fuentes sintéticas (demostración):» / «Synthetic sources (demo):»);
  - líneas `[n] Título[, p. X] — URL`.
- Los números `[n]` y el orden coinciden con los de `messages`.

## 2. Entrega del turno (decisión del plugin)

| Estado de la voz | Texto entregado | `written` efectivo |
|---|---|---|
| `voice` presente y entregada | `sources_messages` (o nada si está vacío) | `sources` / `none` |
| `voice` presente y no entregada | `messages` | `full` |
| `voice` = `null` (texto o falla al generar) | `messages` | `full` |

## 3. Registro del canal (`channels.jsonl`)

- Campo nuevo `written`: `"full" | "sources" | "none"`.
  - Con voz: lo previsto si la voz se entrega (`"sources"` o `"none"`).
  - Sin voz: `"full"`.
- Sin texto ni números, como el resto del registro (regla 10).

## 4. Guion hablado

- Si el turno tiene fuentes, el guion termina con la frase de cierre del idioma del turno (research R3).
- Sin fuentes, no hay frase de cierre.
