# Quickstart: Pitch v2

## A. Validación sin red (cualquier equipo)

```bash
LANGSMITH_TRACING=false uv run pytest tests/unit/test_pitch_sync.py tests/unit/test_pitch_graphics.py \
  tests/unit/test_pitch.py tests/unit/test_pitch_generate.py tests/integration/test_pitch_assemble.py
uv run pml pitch validate --json        # guion 1.2.0, momentos, escenas.json v2
uv run pml pitch generate --dry-run --json
```

Esperado:

- **Pruebas**: en verde.
- **`validate`**: `ok: true`.
- **Pruebas de sincronía**: con un alineador falso, un icono aparece en su palabra ±0,04 s (un cuadro), y un plano
  con anclas se reajusta dentro de 0,8×–1,25×.
- **Pruebas de montaje**: ninguna pausa pasa de 0,8 s.
- **`--dry-run`**: 8 planos, 57 s y el costo del modelo configurado, sin llamar a la API.

## B. Producción

1. `uv run pml pitch probe --json`.
   - Si `available: false`, parar y decidir el modelo (research R1). No se genera nada.
2. `uv run pml pitch narrate`, luego `uv run pml pitch align --json`.
   - Revisar `missing: []` y la duración total (≈ 50 s).
3. `uv run pml pitch graphics`, si hay SVG nuevos o cambiados.
4. Calibrar los modos nuevos: `uv run pml pitch generate --calibrate --mode reference` y `--mode text`.
5. Generar los planos en orden. 03a va antes que 03b y que 06, porque esos usan su último cuadro:
   ```bash
   uv run pml pitch generate --dry-run
   uv run pml pitch generate --shot plano-01a --shot plano-01b --shot plano-02 --shot plano-03a \
     --shot plano-04 --shot plano-05
   # revisar y aprobar plano-03a, luego:
   uv run pml pitch generate --shot plano-03b --shot plano-06
   ```
6. Revisar cada plano:
   - los cuatro chequeos de la 028, más `cue_shown`;
   - las `anchors` en segundos del clip.
7. Montar y validar el borrador:
   ```bash
   uv run pml pitch assemble --json
   uv run pml pitch check video/pitch/borrador/pitch-valeria.mp4 --json
   ```
8. Ver el borrador sin sonido y comprobar que los perfiles se reconocen (SC-005).
9. `uv run pml pitch publish`, y luego `make check` y `make e2e`.

## C. Mediciones (se llenan al implementar)

| Medición | Resultado |
|---|---|
| `probe` (2026-11-26, 22:38 UTC) | MAGI-2: los 3 modos en `403 model_unavailable`. Kling 4.0: los 3 modos responden con validación. Modelo a usar: `kling4` |
| Calibración `reference` y `text` | Sin calibración aparte: la ronda 1 (`plano-01a` text y `plano-01b` reference, 2,09 USD) hizo de calibración. Ambos salieron 1080×1920 y con audio; Kling 4.0 sí genera audio |
| Narración (Phonon) y alineación (faster-whisper `base`, en memoria) | 7,84 · 7,92 · 14,32 · 5,12 · 7,12 · 6,80 s → escenas de 8,34 · 8,42 · 14,82 · 5,62 · 7,62 · 7,30 s; **total 52,12 s**; 23 de 23 momentos ubicados. El reconocedor oyó «un siente» por «un sí antes», así que `diferencia.confirmar` se ancla en «pide» + 0,36 s |
| Momentos con `|delta| ≤ 0,5 s` (SC-002) | 21 de 23 (91,3 %). Fuera: `solucion.colaboradores` (−0,92 s) y `solucion.proveedores` (+1,11 s), porque Kling las hizo llegar en otro orden; desfase aceptado por el integrante y marcado `accepted`. `solucion.clientes` queda a +0,26 s |
| Pausa máxima entre escenas (SC-003) | 0,5 s en las seis escenas. Borrador: 52,12 s, 1080×1920, 18,98 MB, subtítulos hasta 52,12 s; `pml pitch check` en `ok` |
| Planos aprobados, descartados y regenerados | 8 aprobados, 0 descartados, 0 regenerados. `plano-02` empieza en 1,75 s del clip y `plano-05` en 0,6 s, para saltar los paneles de la imagen de origen. Factores de reajuste: 03a 0,735/0,823/1,0; 06 0,709/1,0; 02 0,866; 05 0,977. `plano-06` se recuperó de su trabajo ya enviado tras la pausa, sin reenviarlo |
| Gasto de la v2 y gasto total (≤ 20 USD) | v2: **11,02 USD** con Kling 4.0 (58 s). Total del pitch: **16,46 USD** (v1 4,80 + calibraciones 0,64 + v2 11,02) |
| Prueba sin sonido: perfiles reconocidos (SC-005) | — |
| Pruebas sin red (antes de producir) | 2.000 de Python en verde (120 del pitch unitario + 11 de montaje); Ruff en verde |
| `make check` / `make e2e` (con la v2 publicada, 2026-11-27) | 2.004 de Python y 198 web; Ruff y build en verde; JS 110,44 kB gzip. E2E 43/43 |
