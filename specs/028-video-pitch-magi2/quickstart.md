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
- El montaje con clips sintéticos produce un `.mp4` de 57 s o menos, con el rótulo y el VTT.
- La entrada muestra el pitch primero, se puede saltar y cae a la transcripción si falta el video.

## B. Producción (una vez)

Detalle en `video/pitch/RUNBOOK.md`.

1. **Antes de generar**: confirmar la ficha `docs/referencias/avatar_ingenio_manuelita.md` (`real_person: false`)
   y que `pml pitch validate` está en verde.
2. Exportar las escenas: `uv run pml pitch samples -o samples.json`.
3. En una máquina con 8× H100 o H200:
   ```bash
   docker pull sandai/magi-2-preview:latest
   hf download sand-ai/MAGI-2-preview --local-dir ckpt
   docker run --gpus all -it -v $PWD/ckpt:/workspace/ckpt -v $PWD/pitch:/workspace/pitch sandai/magi-2-preview:latest
   SAMPLES=/workspace/pitch/samples.json OUTPUT_DIR=/workspace/pitch/out SEED=2026 bash scripts/run_demo.sh
   ```
4. Traer `out/sample_00N.mp4` a `video/pitch/escenas/escena-0N.mp4` y registrar `model_revision` y `generated_at`.
5. Revisar cada escena con los cuatro chequeos de `review`. Las descartadas se regeneran con
   `pml pitch samples --scene escena-0N` y otra semilla o indicación.
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
| `pml pitch validate` (repo) | Guion válido: 6 bloques, 2 unidades del oro, 0 cifras sin fuente. Falla solo por la ficha de la imagen sin confirmar (T008) |
| Montaje con 6 clips sintéticos 1080×1920 + narración | 57,0 s; 1080×1920; audio AAC; `faststart`; ≤ 25 MB (tasa limitada a 3 Mbps); VTT de 6 entradas hasta 00:00:57.000 |
| Rótulo de IA grabado | Oscurece su franja en t=1 s y t=55 s, no en t=25 s (`test_ai_disclaimer_is_burned_in`) |
| `make check` | 1.901 pruebas de Python y 198 web; Ruff y build en verde |
| `make e2e` | 43/43 (9 del pitch: primera posición, saltar, sesión, movimiento reducido, falla, 360–1920 px, axe-core) |
| JS de producción | 110,34 kB gzip (≤ 120 kB) |

### Con MAGI-2 (pendiente: T008, T024–T026)

| Medición | Resultado |
|---|---|
| Duración, tamaño y resolución del video real (`pml pitch check`) | — |
| Escenas aprobadas, descartadas y regeneradas | — |
| Validación con 5 personas (SC-002) | — |
