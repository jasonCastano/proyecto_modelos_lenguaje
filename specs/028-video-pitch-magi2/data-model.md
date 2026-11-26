# Data Model: video pitch con MAGI-2

## Guion del pitch (`video/pitch/guion.toml`)

| Campo | Tipo | Regla |
|---|---|---|
| `version` | string | Versión semántica del guion; cambia al editar texto o claims |
| `language` | `"es"` | Fijo (FR-006) |
| `max_seconds` | número | ≤ 60 (FR-001); por defecto 57 |
| `[[block]]` | lista de 6 | Exactamente 6, en el orden `gancho`, `problema`, `solucion`, `diferencia`, `uso`, `accion` (FR-002) |
| `block.id` | enum anterior | Único |
| `block.narration` | string | Español, ≤ 22 palabras, sin siglas sin explicar |
| `block.claims` | lista de `unit_id` | Requerida si `narration` afirma algo de Manuelita. Cada id existe en `data/gold/knowledge_units.jsonl` (FR-004) |
| `block.synthetic` | bool | `true` si menciona la planificación. Entonces `narration` contiene «datos sintéticos» (FR-005) |
| `block.on_screen` | string opcional | Texto que el montaje superpone (p. ej., los pasos de uso). Sin cifras sin `claims` |

**Validaciones**:

- Cada número de `narration` o `on_screen` aparece en el texto de alguna unidad de sus `claims`.
- El bloque `uso` nombra los cuatro pasos de FR-003: perfil, pregunta, fuentes y planificación.

## Escena (`video/pitch/escenas.json`, lista)

| Campo | Tipo | Regla |
|---|---|---|
| `id` | `escena-01`…`escena-06` | Una por bloque, mismo orden |
| `block` | id de bloque | Debe existir en el guion |
| `prompt_file` | ruta | `video/pitch/prompts/escena-0N.json` (caption estructurado de MAGI-2). Incluye «sin texto en pantalla» y no menciona la marca |
| `image` | ruta | `docs/referencias/avatar_ingenio_manuelita.png` (FR-007) |
| `seed` | entero | Fijo para regenerar; se envía como `seed` a la API |
| `provider` | `higgsfield` \| `local` | `higgsfield` por defecto; `local` = pesos abiertos en 8× H100 |
| `model` | string | `sand/magi-2/image-to-video` (Higgsfield) o `sand-ai/MAGI-2-preview` (local) |
| `model_revision` | string o `null` | Solo `local`: digest de la imagen Docker |
| `request_seconds` | entero | Segundos pedidos a la API: 10 (rango 4–30) |
| `resolution` | `"1080x1920"` | Fijo; se pide `"1080p"` y la imagen 9:16 fija el encuadre |
| `job` | objeto o `null` | Último trabajo de generación (ver abajo) |
| `generated_at` | ISO 8601 o `null` | Se llena al descargar el clip |
| `clip` | ruta o `null` | `video/pitch/escenas/escena-0N.mp4` |
| `duration_s` | número o `null` | Medida con ffprobe |
| `trim_s` | número | Duración usada en el montaje, ≤ 9,5 |
| `status` | `pendiente` \| `generando` \| `generada` \| `error` \| `aprobada` \| `descartada` | Ver transiciones |
| `review` | objeto o `null` | `{by, at, likeness, no_text, no_brand, matches_script, block_hash, notes}`; los cuatro chequeos en `true` para aprobar |

### Trabajo de generación (`job`, dentro de cada escena)

| Campo | Tipo | Regla |
|---|---|---|
| `request_id` | string | El que devuelve Higgsfield; permite consultar o cancelar |
| `status` | `queued` \| `in_progress` \| `completed` \| `failed` \| `nsfw` \| `canceled` | Último estado visto |
| `submitted_at`, `finished_at` | ISO 8601 | |
| `seconds` | entero | Segundos cobrables pedidos |
| `cost_usd` | número | `seconds × usd_per_second`; 0 si `failed` o `nsfw` (no se cobran) |
| `idempotency_key` | string | `escena-0N:<block_hash>:<seed>` |
| `error` | string o `null` | Mensaje de la API, sin la clave |

Los trabajos anteriores de la misma escena se guardan en `history` (lista de `job`), para sumar el gasto total.
**Nunca** se guarda la clave, la URL firmada de subida ni cabeceras.

**Transiciones**:

```text
pendiente --(generate)--> generando --(completed + descarga)--> generada
generando --(failed | nsfw | canceled | timeout | 4xx)--> error --(generate)--> generando
generada --(revisión: 4 chequeos true)--> aprobada
generada --(algún chequeo false)--> descartada --(generate con otra seed o prompt)--> generando
aprobada --(cambia el bloque del guion)--> pendiente
aprobada --(generate sin --force)--> aprobada (se omite)
```

Con `provider = "local"`, el clip se trae a mano y la escena pasa de `pendiente` a `generada`.

## Configuración de generación (`config/pitch.toml`)

| Clave | Valor inicial | Regla |
|---|---|---|
| `higgsfield.base_url` | `https://api.higgsfield.ai` | |
| `higgsfield.model` | `sand/magi-2/image-to-video` | Debe existir en `GET /models` antes de enviar |
| `higgsfield.api_key_env` | `HIGGSFIELD_API_KEY` | Nombre de la variable, nunca su valor |
| `higgsfield.fields` | `{duration = "duration", audio = "generate_audio", aspect_ratio = "aspect_ratio"}` | Confirmados con la calibración (research R11) |
| `higgsfield.resolution` | `"1080p"` | Único valor aceptado |
| `higgsfield.aspect_ratio` | `"9:16"` | Obligatorio para vertical: sin él sale 16:9 (calibración) |
| `higgsfield.seconds` | `10` | 4–30 |
| `higgsfield.audio` | `true` | Ambiente de MAGI-2 bajo la narración |
| `higgsfield.poll_s` / `timeout_s` | `10` / `3600` | La cola tardó unos 15 min por trabajo |
| `budget.usd_per_second` | `0.08` | Precio publicado el 2026-11-25 |
| `budget.max_usd` | `20` | SC-008 |

El montaje exige las 6 escenas en estado `aprobada` (FR-013). `generate` también exige la ficha de la imagen
confirmada.

## Imagen de referencia (`docs/referencias/avatar_ingenio_manuelita.md`)

Frontmatter obligatorio:

| Campo | Regla |
|---|---|
| `file` | `avatar_ingenio_manuelita.png` |
| `sha256` | Hash del PNG; el montaje lo compara |
| `origin` | Cómo se obtuvo (herramienta de IA y fecha) |
| `rights` | Derechos de uso del equipo |
| `real_person` | `false` (requisito para producir) |
| `brand_elements` | `false` (sin logo ni piezas de Manuelita) |
| `confirmed_by` | Integrante que lo declara |

## Video del pitch (`web/public/media/`)

| Archivo | Regla |
|---|---|
| `pitch-valeria.mp4` | H.264 + AAC, 1080×1920, `faststart`, ≤ 60 s, ≤ 25 MB. Sin rótulo grabado; la declaración va en la web (FR-009) |
| `pitch-valeria.es.vtt` | WebVTT en español, una entrada por bloque, sincronizado con el montaje (FR-014) |
| `pitch-valeria.webp` | Portada, cuadro de la escena 1 |
| `video/pitch/transcripcion.md` | Texto completo de los 6 bloques más la declaración; la web lo muestra desde `web/src/data/pitch.ts` |

## Estado en la web (por sesión)

| Clave en `sessionStorage` | Valores | Efecto |
|---|---|---|
| `valeria.pitch` | ausente \| `visto` \| `saltado` | Ausente: el video ocupa la primera posición e intenta arrancar sin sonido. Con `visto` o `saltado`: se muestra compacto, con la acción «Ver el video» (FR-018) |
