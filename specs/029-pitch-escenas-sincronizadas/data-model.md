# Data Model: Pitch v2

## Guion (`video/pitch/guion.toml`, versión 1.2.0)

| Campo | Tipo | Regla |
|---|---|---|
| `version` | string | `"1.2.0"` |
| `max_seconds` | número | 60 |
| `pause_s` | número | De 0,3 a 0,8; por defecto 0,5 (FR-009) |
| `block[].id` / `narration` / `claims` | como en la 028 | La narración de `solucion` es la de FR-001; las demás no cambian (FR-002) |
| `block[].on_screen` | string | Vacío en todos los bloques; se elimina «1 Perfil · …» (FR-004) |
| `block[].cue[]` | lista de **momentos sincronizados** | Ver abajo |

### Momento sincronizado (`[[block.cue]]`)

| Campo | Tipo | Regla |
|---|---|---|
| `id` | string | Único en el guion; por ejemplo `problema.informes` |
| `word` | string | Palabra o frase que debe aparecer en la narración del bloque; se compara sin tildes y por prefijo |
| `kind` | `"plano"` \| `"grafico"` | `plano`: el evento ocurre en un plano generado. `grafico`: lo agrega el montaje |
| `shot` | string | Obligatorio si `kind = "plano"`: el plano que lo muestra |
| `graphic` | string | Obligatorio si `kind = "grafico"`: nombre en `video/pitch/graficos/` |
| `from` / `to` | `[x, y]` en 0–1 | Trayectoria del gráfico; `to` omitido significa que queda fijo |
| `hold_s` | número | Cuánto permanece el gráfico; por defecto, hasta el fin de la escena |
| `at_s` | número opcional | Respaldo manual si la palabra no se alinea |

Momentos de la v2:

| Escena | Momentos | Tipo |
|---|---|---|
| gancho | `trapiche` (01a); `Valer-IA` (01b: entra la presentadora) | plano |
| problema | `informes`, `noticias`, `caña`, `palma`, `acuicultura`, `frutas` | gráfico (hacia la tablet) |
| solucion | `visitantes`, `clientes`, `proveedores` (por la izquierda); `colaboradores`, `equipo de planta` (por la derecha) | plano (03a) |
| diferencia | `fuente`, `cifras`, `sí` | gráfico |
| uso | `perfil` → cinco tarjetas escalonadas | gráfico |
| accion | `Entra` → despedida de los aliados | plano (06) |

## Registro de planos (`video/pitch/escenas.json`, esquema 2)

```json
{"schema": 2, "model": "magi2",
 "scenes": [{"id": "escena-01", "block": "gancho", "shots": [ { "id": "plano-01a", … } ]}]}
```

### Plano

| Campo | Tipo | Regla |
|---|---|---|
| `id` | string | `plano-0N[a-z]` |
| `mode` | `"image"` \| `"reference"` \| `"text"` | R2 |
| `source` | `"reference"` \| `"frame:<plano>"` \| `null` | `null` solo con `mode = "text"`. `frame:` exige que ese plano esté `aprobada` |
| `prompt_file` | ruta | `video/pitch/prompts/plano-*.json` (subject, setting, action, camera, style, audio, constraints) |
| `seed` | entero | Único por plano |
| `request_seconds` | entero | 4–30 (MAGI-2) o lo que admita el modelo elegido |
| `model` | string | El modelo de `escenas.json.model`; todos los planos usan el mismo |
| `job`, `history`, `generated_at`, `clip`, `duration_s` | como en la 028 | `clip` en `video/pitch/planos/` |
| `status` | `pendiente` → `generando` → `generada` → `aprobada` \| `descartada` \| `error` | Igual que la 028 |
| `review` | objeto | `{by, at, likeness, no_text, no_brand, matches_script, cue_shown, anchors, block_hash, notes}` |
| `review.anchors` | `{cue_id: segundo_en_clip}` | Obligatorio para los momentos `plano` de ese plano (R5) |

El estado de la **escena** se deriva: es `aprobada` si todos sus planos lo están.

**Migración**: un `escenas.json` sin `schema` es la v1. La v2 lo reemplaza; la v1 queda en el historial de Git.

## Sincronía (`video/pitch/sincronia.json`), generada por `pml pitch align`

| Campo | Tipo | Regla |
|---|---|---|
| `script_version` | string | Igual a la del guion; si difiere, el montaje pide realinear |
| `blocks.<id>.narration_s` | número | Duración del WAV |
| `blocks.<id>.scene_s` | número | `narration_s + pause_s` |
| `blocks.<id>.start_s` | número | Inicio de la escena en el video |
| `blocks.<id>.words[]` | `{w, start, end}` | Del reconocedor |
| `blocks.<id>.cues.<cue_id>` | número | Segundo de la palabra dentro de la escena |
| `blocks.<id>.narration_hash` | string | Huella del WAV; si cambia, se realinea |

## Gráfico (`video/pitch/graficos/<nombre>.svg` → `png/<nombre>.png`)

| Campo | Regla |
|---|---|
| Lienzo | Cuadrado de 240 px para los iconos; tarjeta de 520×140 px para los perfiles |
| Texto | Solo en las tarjetas de perfil: los nombres exactos de `web/src/lib/platform.ts` (FR-004) |
| Marca | Sin logotipo ni elementos de Manuelita (FR-014, FR-016) |
| PNG | Transparente, por LFS; se regenera con `pml pitch graphics` |

## Línea de tiempo del montaje (derivada, no se guarda)

| Elemento | Origen |
|---|---|
| Escena N | `[start_s, start_s + scene_s)` |
| Plano | Tramo de su escena: desde el inicio de la escena, o desde el momento que lo abre, hasta el siguiente plano. Se recorta o reajusta (0,8×–1,25×) para que sus `anchors` caigan sobre los `cues` |
| Gráfico | Entra en `start_s + cue` con aparición de 0,25 s, viaja `from`→`to` en 0,8 s y sale en `hold_s` o al fin de la escena |
| Narración | WAV del bloque en `start_s`, sin cambiar su velocidad |
| Subtítulos | Un tramo por escena, con sus tiempos reales |
