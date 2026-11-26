# Contrato: `pml pitch`

Todos los comandos aceptan `--root video/pitch` y `--json`, devuelven 0 si todo cumple y 1 si hay fallas, y nunca
llaman a MAGI-2 ni a la red.

## `pml pitch validate`

Valida `guion.toml`, `escenas.json` y la ficha de la imagen ([data-model.md](../data-model.md)).

Salida `--json`:

```json
{"ok": true, "blocks": 6, "max_seconds": 57, "claims": 9, "unsupported_numbers": [],
 "missing_units": [], "reference": {"confirmed": true, "sha256_matches": true}, "errors": []}
```

Fallas típicas:

- `missing_units`: un `unit_id` no existe en el oro.
- `unsupported_numbers`: hay una cifra sin respaldo.
- Falta «datos sintéticos» en un bloque que menciona la planificación.
- `reference.confirmed=false`.

## `pml pitch samples [--scene escena-03] -o samples.json`

Exporta las escenas (todas, o la indicada) al formato `SAMPLES` de `scripts/run_demo.sh` de MAGI-2:
`[{"prompt_file": "...", "image": "..."}]`. También imprime la semilla, para correrla con la misma. Falla si
`validate` falla.

## `pml pitch narrate [--block uso]`

Genera `narracion/bloque-0N.wav` con la voz Phonon (spec 016) y mide su duración. Falla si un bloque supera
`trim_s` de su escena. Las pruebas usan un motor de voz falso; la voz real lleva el marcador `voice`.

## `pml pitch assemble -o web/public/media/pitch-valeria.mp4`

Requisitos: `validate` en verde, las 6 escenas en estado `aprobada` con su clip y las 6 narraciones.

Pasos con ffmpeg:

1. Recorta cada clip a `trim_s` y concatena.
2. Mezcla la narración sobre el audio de MAGI-2 atenuado a −18 dB.
3. Graba el rótulo de IA en 0–3 s y en los últimos 4 s.
4. Superpone `on_screen` donde el bloque lo pide.
5. Codifica H.264 + AAC con `faststart`.

Escribe también `pitch-valeria.es.vtt`, `pitch-valeria.webp` y `transcripcion.md`.

## `pml pitch check web/public/media/pitch-valeria.mp4`

Con ffprobe comprueba:

- duración ≤ `max_seconds`;
- 1080×1920;
- pista de audio presente;
- tamaño ≤ 25 MB;
- que el VTT cubre toda la duración.

Salida `--json` con cada chequeo.
