# Quickstart: video pitch con MAGI-2

## A. Validación sin GPU (cualquier equipo)

```bash
uv run pml pitch validate --json              # guion con fuentes, manifiesto y ficha de la imagen
uv run pytest tests/unit/test_pitch.py tests/integration/test_pitch_assemble.py -q
cd web && npx vitest run src/test/PitchVideo.test.tsx && cd ..
make e2e                                       # incluye tests/e2e/test_pitch.py
```

**Resultado esperado**:

- `validate` responde `ok: true`, con 6 bloques, `unsupported_numbers: []` y la referencia confirmada.
- El montaje con clips sintéticos produce un `.mp4` de 57 s o menos, con el VTT y sin rótulo grabado.
- La entrada muestra el pitch primero, se puede saltar y cae a la transcripción si falta el video.

## B. Producción (una vez, por la API de Higgsfield)

Detalle en `video/pitch/RUNBOOK.md`. Requiere `HIGGSFIELD_API_KEY=<id>:<secreto>` en `.env` y saldo en la cuenta.

1. **Antes de generar**: la ficha de la imagen está confirmada (2026-11-26) y `pml pitch validate` sale en verde.
2. Ver el plan sin gastar: `uv run pml pitch generate --dry-run`. Debe mostrar 6 escenas, 60 s y unos 4,80 USD.
3. **Calibrar**: `uv run pml pitch generate --calibrate` (4 s, unos 0,32 USD). Resultado esperado:
   - 1080×1920 (o 1088×1920);
   - unos 4 s;
   - pista de audio.

   Si la duración o el audio no coinciden, corregir los nombres en `config/pitch.toml` `[higgsfield.fields]` y
   repetir.
4. Generar: `uv run pml pitch generate`. Son 6 escenas en serie, de 3 a 5 minutos cada una. Cada clip queda en
   `video/pitch/escenas/` y `escenas.json` registra `job` y su costo.
5. Revisar cada escena con los cuatro chequeos de `review`. Las descartadas se regeneran con
   `pml pitch generate --scene escena-0N`, con otra semilla o indicación.

   *Alternativa sin Higgsfield*: pesos abiertos en 8× H100 con `pml pitch samples`, según el RUNBOOK.
6. Generar la narración con `uv run pml pitch narrate` (voz Phonon) y montar con
   `uv run pml pitch assemble -o web/public/media/pitch-valeria.mp4`.
7. Comprobar con `uv run pml pitch check web/public/media/pitch-valeria.mp4 --json`: duración ≤ 60 s, 1080×1920,
   audio y ≤ 25 MB.
8. Abrir la app con `make app`: el pitch aparece primero en `http://127.0.0.1:8000/`.

## C. Validación con personas (SC-002)

Cinco personas que no conocen el proyecto ven solo el video y luego, sin ayuda, describen Valer-IA y hacen su
primera pregunta en `/agente`. Se anotan los resultados en §D. La meta es al menos 4 de 5.

## D. Mediciones

### Sin GPU (2026-11-26)

| Medición | Resultado |
|---|---|
| `pml pitch validate` (repo) | `ok: true`: 6 bloques, 2 unidades del oro, 0 cifras sin fuente, ficha de la imagen confirmada (T008, 2026-11-26) |
| Montaje con 6 clips sintéticos 1080×1920 + narración | 57,0 s; 1080×1920; audio AAC; `faststart`; ≤ 25 MB (tasa limitada a 3 Mbps); VTT de 6 entradas hasta 00:00:57.000 |
| Sin rótulo grabado (revisión 2026-11-26) | La franja inferior no cambia en t=1, 25 y 55 s (`test_no_disclaimer_is_burned_in`); la declaración está en la web y en la transcripción |
| `make check` (con el video real, 2026-11-26) | 1.934 pruebas de Python (43 omitidas sin `PML_E2E`) y 198 web; Ruff y build en verde |
| `make e2e` | 43/43 (9 del pitch: primera posición, saltar, sesión, movimiento reducido, falla, 360–1920 px, axe-core). Con el `.mp4` real de 19 MB en reproducción automática, `networkidle` no llegaba; las demás suites lo sirven como ausente (`skip_pitch_video` en `tests/e2e/conftest.py`) |
| JS de producción | 110,37 kB gzip (≤ 120 kB) |

### Sondeo de la API de Higgsfield (2026-11-26, sin costo)

| Medición | Resultado |
|---|---|
| Autenticación con `HIGGSFIELD_API_KEY` (`Authorization: Key id:secreto`) | `GET /models` → 200; el modelo responde 400 de validación, no 401 |
| Modelo | `sand/magi-2/image-to-video` en el catálogo (y `text-to-video`, `reference-to-video`) |
| Campos confirmados | `image_url` (obligatorio), `prompt`, `resolution` ∈ {`1080p`}, `seed` entero |
| Duración y audio | Nombres sin confirmar; los confirma la calibración |
| `pml pitch generate --dry-run --json` (T050) | 6 escenas, 60 s, 4,80 USD, sin llamar a la API |
| Búsqueda de la clave en el repositorio (SC-009) | 0 apariciones en archivos versionados y no ignorados, `escenas.json` y `gasto.json` |

### Con MAGI-2 (pendiente: calibración y T024–T026)

| Medición | Resultado |
|---|---|
| Calibración 1 de 4 s, sin `aspect_ratio` | 1920×1080 (16:9: MAGI-2 extendió la imagen), 4,24 s, audio, 0,32 USD |
| Calibración 2 de 4 s, con `aspect_ratio: "9:16"` | **1080×1920**, 4,24 s, audio, 0,32 USD; unos 15 min en cola. Campos confirmados: `duration`, `generate_audio`, `aspect_ratio` |
| Generación de las 6 escenas (T024, 2026-11-26) | 6/6 `generada`: 1080×1920, 10,0 s, con audio; 0,80 USD cada una, unos 15 min en cola por escena |
| Gasto total en Higgsfield (≤ 20 USD, SC-008) | **5,44 USD**: 0,64 de calibración + 4,80 de escenas |
| Duración, tamaño y resolución del video real (`pml pitch check`) | `ok: true`: 57,0 s; 1080×1920; H.264 a 24 fps + AAC; 18,85 MB; VTT hasta 57,0 s |
| Escenas aprobadas, descartadas y regeneradas | 6 aprobadas, 0 descartadas, 0 regeneradas. La escena 03 muestra en la tablet seudotexto ilegible y las 02 y 05 paneles con iconos; ninguna tiene palabras legibles ni logotipos |
| Validación con 5 personas (SC-002) | — |
