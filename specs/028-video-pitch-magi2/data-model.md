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
| `seed` | entero | Fijo para regenerar |
| `model` | string | `sand-ai/MAGI-2-preview` |
| `model_revision` | string | Commit del repo o tag de la imagen Docker usada |
| `resolution` | `"1080x1920"` | Fijo |
| `generated_at` | ISO 8601 o `null` | Se llena al traer el clip |
| `clip` | ruta o `null` | `video/pitch/escenas/escena-0N.mp4` |
| `duration_s` | número o `null` | Medida con ffprobe; MAGI-2 entrega 10 s |
| `trim_s` | número | Duración usada en el montaje, ≤ 9,5 |
| `status` | `pendiente` \| `aprobada` \| `descartada` | Ver transiciones |
| `review` | objeto o `null` | `{by, at, likeness, no_text, no_brand, matches_script, notes}`; los cuatro chequeos en `true` para aprobar |

**Transiciones**:

```text
pendiente --(clip traído)--> pendiente(con clip)
pendiente(con clip) --(revisión: 4 chequeos true)--> aprobada
pendiente(con clip) --(algún chequeo false)--> descartada --(regenerar con nueva seed o prompt)--> pendiente
aprobada --(cambia el bloque del guion)--> pendiente
```

El montaje exige las 6 escenas en estado `aprobada` (FR-013).

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
| `pitch-valeria.mp4` | H.264 + AAC, 1080×1920, `faststart`, ≤ 60 s, ≤ 25 MB. Rótulo de IA grabado en 0–3 s y en los últimos 4 s (FR-009) |
| `pitch-valeria.es.vtt` | WebVTT en español, una entrada por bloque, sincronizado con el montaje (FR-014) |
| `pitch-valeria.webp` | Portada, cuadro de la escena 1 con el rótulo |
| `video/pitch/transcripcion.md` | Texto completo de los 6 bloques más la declaración; la web lo muestra desde `web/src/data/pitch.ts` |

## Estado en la web (por sesión)

| Clave en `sessionStorage` | Valores | Efecto |
|---|---|---|
| `valeria.pitch` | ausente \| `visto` \| `saltado` | Ausente: el video ocupa la primera posición e intenta arrancar sin sonido. Con `visto` o `saltado`: se muestra compacto, con la acción «Ver el video» (FR-018) |
