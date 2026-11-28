# Data Model: stickers activos (spec 037)

## 1. Catálogo (`config/stickers.toml`)

Sin cambios en los archivos ni en los textos. Cambian las situaciones:

| Sticker | Situaciones | Posición |
|---|---|---|
| `valeria-bienvenido` | `greeting_first_contact` | antes |
| `valeria-hola` | `greeting_new_conversation` | antes |
| `valeria-consulta` | `greeting_mid` | después |
| `valeria-gracias` | `thanks` | después |
| `valeria-lindo-dia` | `closing` | después |
| `valeria-pulgar` | `assent`, **`useful_answer`** | después |
| `valeria-gracias-confianza` | `profile_saved` | después |
| `valeria-listo` | `action_done`, **`useful_answer`** | después |
| `valeria-pensando` | `thinking` (lo envía el plugin) | antes |

`StickerCatalog.for_situation(situation)` devuelve, para `useful_answer`, la lista de candidatos en orden. La
elección alterna según `ThreadUsage.last_sticker`.

## 2. Prioridad de situaciones

`profile_saved > action_done > closing > thanks > greeting_first_contact > greeting_new_conversation > greeting_mid
> assent > useful_answer`.

## 3. `TurnSignals` (entrada de `choose`)

Campos nuevos:

| Campo | Tipo | Origen |
|---|---|---|
| `cited` | `bool` | la respuesta trae citas (`reply.citations`) |
| `fallback` | `bool` | respaldo por evidencia insuficiente o mensaje fijo |
| `crisis` | `bool` | `route == "out_of_scope"` y `scope_reason == "crisis"` |
| `low_mood` | `bool` | `style.LOW_MOOD` sobre el mensaje (spec 036) |

`useful_answer` exige `status == "answered"`, `cited`, que no haya `fallback` y que el sentimiento no sea negativo.

## 4. `ThreadUsage` (lo lee `choose`)

| Campo | Tipo | Nota |
|---|---|---|
| `turn_no` | `int` | existente |
| `last_sticker_turn` | `int \| None` | existente |
| `sent` | `list[str]` | existente (nombres, en orden) |
| `last_sticker` | `str \| None` | **nuevo**: nombre del último sticker enviado |
| `last_situation` | `str \| None` | **nuevo**: situación del último sticker |
| `off` | `bool` | **nuevo**: la persona pidió no recibir stickers |

`channel_stickers` gana la columna `situation TEXT` (migración `ALTER TABLE … ADD COLUMN`, con valor nulo en las
filas existentes). `stickers_off` se guarda como las demás preferencias por hilo (como `reply_format`). Cambiar de
hilo (`rebind`) conserva ambas.

## 5. Reglas de moderación (`choose`)

1. Se excluye el turno si cumple alguna de estas condiciones (sin sticker):
   - `off`;
   - estado distinto de `answered`, salvo una acción aprobada;
   - evento de error;
   - aviso `sensitive_data`;
   - sentimiento negativo;
   - acto `complaint`;
   - `crisis`, `low_mood` o `fallback`.
2. Se toma la situación de mayor prioridad.
3. Con `len(sent) >= stickers_per_conversation` (8): sin sticker.
4. Para `useful_answer`: sin sticker si `last_sticker_turn == turn_no - 1`. Si no, el candidato distinto de
   `last_sticker`.
5. Para las demás situaciones: sin sticker si `last_sticker == candidato` y fue en el turno anterior, salvo el pulgar
   y `valeria-lindo-dia`. La regla «nunca dos respuestas seguidas» se elimina.
6. El idioma `en` solo admite stickers sin texto (`language = "none"`).

## 6. Registro de entrega (log del gateway)

| Línea | Cuándo |
|---|---|
| `valeria-bridge: stickers listos vía <compartido\|parche\|import>` | al arrancar, si hay vía |
| `valeria-bridge: sin vía de stickers (<motivo>)` | al arrancar, si no hay vía |
| `valeria-bridge: sticker enviado (<nombre>) vía <vía>` | por cada entrega |
| `valeria-bridge: sticker no enviado (<nombre>): <sin-listener\|sin-archivo\|error>` | por cada fallo |

Sin números (`maskDigits`) ni contenido.

## 7. Resumen de `ops check`

`stickers hoy: elegidos N · entregados M · fallidos K (motivo)`, con N del registro del canal y M y K del log del
gateway del día. Estados:

| Estado | Condición |
|---|---|
| rojo | N > 0 y M = 0 |
| amarillo | 0 < M < N |
| verde | M = N, o N = 0 |
