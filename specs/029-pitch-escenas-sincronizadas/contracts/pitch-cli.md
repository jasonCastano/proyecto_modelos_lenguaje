# Contrato: comandos `pml pitch` (v2)

Todos aceptan `--root video/pitch` y `--json`. Los que no se nombran aquí siguen como en la 028.

## `pml pitch probe` (nuevo, sin costo)

Comprueba si el modelo configurado está disponible. Consulta el catálogo de Higgsfield y envía a cada modo un cuerpo
inválido, por lo que no hay cobro.

```json
{"model": "magi2", "available": false,
 "modes": {"image": "403 model_unavailable", "reference": "403 model_unavailable", "text": "403 model_unavailable"},
 "alternatives": ["kling4"]}
```

- Sale con 0 si todos los modos que usan los planos responden con validación (400/422).
- Sale con 3 si alguno responde `model_unavailable`.

## `pml pitch narrate` (cambia)

Sintetiza cada bloque sin el tope de 9,5 s. Falla si `Σ(narration_s + pause_s) > max_seconds`, con el nombre del
bloque más largo. No acelera la voz.

## `pml pitch align` (nuevo, sin red)

1. Transcribe cada WAV con faster-whisper y tiempos por palabra.
2. Escribe `sincronia.json`.
3. Falla con código 2 si una palabra de un momento no aparece y ese momento no tiene `at_s`.

```json
{"blocks": 6, "seconds": 50.3, "cues": 17, "missing": []}
```

## `pml pitch graphics` (nuevo, sin red)

Rasteriza `graficos/*.svg` a `graficos/png/*.png` transparentes con Playwright (Chromium). Solo se necesita cuando
cambia un SVG.

## `pml pitch generate` (cambia)

| Opción | Efecto |
|---|---|
| `--shot plano-0Nx` | Un plano; puede repetirse |
| `--scene escena-0N` | Todos los planos de la escena |
| `--dry-run` | Desglose por plano: segundos, USD, gastado y restante; no llama a la API |
| `--calibrate --mode reference\|text` | Clip de 4 s para confirmar los campos del modo |
| `--yes`, `--force` | Como en la 028 |

Antes de generar:

1. Ejecuta el sondeo de `probe` y se niega a seguir si el modelo no está disponible.
2. Resuelve `source = frame:<plano>`: extrae el último cuadro del plano aprobado y lo sube como imagen.
3. Respeta el tope de `budget.max_usd`.

## `pml pitch assemble` (cambia)

- Por defecto escribe en `video/pitch/borrador/pitch-valeria.mp4`, junto con `.vtt` y `.webp`.
- Exige:
  - todos los planos `aprobada`;
  - `sincronia.json` vigente (misma versión de guion y mismas huellas de WAV);
  - `anchors` completos.
- Falla si un tramo necesita un reajuste fuera de 0,8×–1,25×.

```json
{"video": "video/pitch/borrador/pitch-valeria.mp4", "seconds": 50.3,
 "scenes": [{"id": "escena-01", "start_s": 0.0, "scene_s": 8.34}],
 "retime": [{"shot": "plano-03a", "factors": [1.08, 0.94, 1.12]}],
 "cues": [{"id": "problema.informes", "word_s": 10.92, "shown_s": 10.92, "delta_s": 0.0}]}
```

## `pml pitch check VIDEO` (cambia)

A los chequeos de la 028 (duración, resolución, audio, tamaño, subtítulos) suma:

- `pauses`: ningún silencio entre escenas pasa de 0,8 s;
- `cues`: al menos el 90 % de los momentos tienen `|delta_s| ≤ 0.5`, y ninguno es negativo;
- `no_steps_text`: el guion no tiene `on_screen` con pasos numerados.

## `pml pitch publish` (nuevo)

1. Exige `check` en `ok`.
2. Copia el borrador a `web/public/media/`.
3. Regenera `web/src/data/pitch.ts` y `transcripcion.md`.
4. Imprime qué archivos de la v1 quedan para borrar en el commit.

No hace commit.
