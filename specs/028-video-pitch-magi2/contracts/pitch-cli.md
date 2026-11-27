# Contrato: `pml pitch`

Todos los comandos aceptan `--root video/pitch` y `--json` y devuelven 0 si todo cumple y 1 si hay fallas. Solo
`generate` usa la red, y nunca con `--dry-run`.

## `pml pitch generate [--scene escena-03] [--calibrate] [--dry-run] [--yes] [--force]`

Genera escenas con MAGI-2 por la API de Higgsfield (research R11–R14), en serie.

**Antes de enviar**, se detiene sin gastar si:

- `validate` falla, o la ficha de la imagen no está confirmada;
- falta `HIGGSFIELD_API_KEY` en `.env`, o no tiene la forma `id:secreto`. El mensaje dice cómo configurarla;
- `GET /models` no lista el modelo configurado;
- el costo estimado, sumado a lo ya gastado en `escenas.json`, pasa `budget.max_usd`.

Después imprime el plan (escenas, segundos y costo) y pide confirmación, salvo con `--yes`.

**Por escena**:

1. Omite las escenas `aprobada`, salvo con `--force`.
2. Normaliza la imagen a 1080×1920 y la sube una vez por corrida (`/files/generate-upload-url`).
3. Envía `{image_url, prompt, resolution, seed, duration, generate_audio, aspect_ratio: "9:16"}` con
   `Idempotency-Key`.
4. Consulta el estado cada `poll_s` hasta `timeout_s`.
5. Descarga `video.url` a `escenas/escena-0N.mp4` y mide con ffprobe.
6. Guarda `job` y pasa a `generada`. Si falla, pasa a `error` con el mensaje.

`prompt` es el texto que se arma del caption de `prompts/escena-0N.json` (`scene`, `camera`, `audio`,
`constraints`).

**Modos**:

- `--calibrate`: un trabajo de 4 s con la escena 1, guardado en `video/pitch/calibracion/` (no toca
  `escenas.json`). Informa ancho, alto, duración y audio, y falla si no coinciden con lo pedido.
- `--dry-run`: muestra el plan y los cuerpos JSON (sin URL de subida ni clave), sin llamar a la API.

**Errores**: los códigos de research R12. 403 y 401 detienen toda la corrida. Ninguna salida, error o archivo
contiene la clave (SC-009).

Salida `--json`:

```json
{"ok": true, "dry_run": false, "scenes": [{"id": "escena-01", "status": "generada", "request_id": "…",
 "seconds": 10, "cost_usd": 0.8, "clip": "video/pitch/escenas/escena-01.mp4", "duration_s": 10.0,
 "size": "1080x1920", "audio": true}], "spent_usd": 0.8, "total_spent_usd": 1.12, "max_usd": 20}
```

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

Alternativa con los pesos abiertos (`provider = "local"`). Exporta las escenas (todas, o la indicada) al formato
`SAMPLES` de `scripts/run_demo.sh` de MAGI-2 Preview:
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
