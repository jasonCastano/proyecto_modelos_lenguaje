# Runbook: producir el video pitch con MAGI-2 (spec 028)

El video de unos 57 s que abre la entrada se arma con 6 escenas generadas con **MAGI-2** de Sand.ai. Este runbook
se sigue **una vez**, o cuando cambia una escena. La web y las pruebas no dependen de MAGI-2.

**Vía principal (revisión 2026-11-26)**: la API de Higgsfield, desde el equipo del integrante, con
`pml pitch generate` (sección A). La vía con los pesos abiertos en 8× H100 queda como alternativa (secciones 1 a 4).

## A. Generar con la API de Higgsfield (vía principal)

1. **Clave**: en `.env`, `HIGGSFIELD_API_KEY=<id>:<secreto>` (consola de Higgsfield). Nunca en otro archivo.
2. **Saldo**: entre 5 y 20 USD. MAGI-2 cuesta unos 0,08 USD por segundo, así que 6 escenas de 10 s son 4,80 USD.
   El tope total está en `config/pitch.toml` (`max_usd = 20`) y el comando se niega a pasarlo.
3. **Plan sin gastar**: `uv run pml pitch generate --dry-run --json`. Muestra 6 escenas, 60 s, el costo y el
   cuerpo de cada solicitud.
4. **Calibración**: `uv run pml pitch generate --calibrate --yes --json`. Genera un clip de 4 s (unos 0,32 USD) en
   `video/pitch/calibracion/` y comprueba:
   - la duración pedida;
   - el audio;
   - que el clip salga vertical 1080×1920.

   Si algo no coincide, se corrige `[higgsfield.fields]` o `aspect_ratio` en `config/pitch.toml` y se repite.
5. **Escenas**: `uv run pml pitch generate --yes --json`. Se generan en serie; cada una tarda unos minutos.
   - Cada clip queda en `video/pitch/escenas/escena-0N.mp4`.
   - `escenas.json` registra su `job` (solicitud, estado, costo) y queda `generada`.
   - Las escenas `generada` o `aprobada` no se regeneran sin `--force`.
6. **Revisar**: paso 5 de este runbook. Una escena descartada se regenera con
   `pml pitch generate --scene escena-0N`, con otra semilla o con el prompt ajustado.

**Qué se sube a Higgsfield**: solo la imagen de referencia normalizada a 1080×1920 y el texto del prompt de cada
escena. Nunca el guion narrado, datos del corpus, la clave ni datos personales. Higgsfield conserva las solicitudes
y sus resultados 7 días.

Fuentes del modelo abierto (alternativa):

- <https://huggingface.co/sand-ai/MAGI-2-preview>
- <https://github.com/SandAI-org/MAGI-2-preview>

Se consultaron el 2026-11-25. Si cambian, se actualiza este archivo y el ADR 0032.

## 0. Antes de generar (equipo local)

1. **Ficha de la imagen**. Completa `docs/referencias/avatar_ingenio_manuelita.md` con:
   - `origin`, `rights` y `confirmed_by`;
   - `real_person: false` y `brand_elements: false`.

   Si la imagen representa a una persona real o tiene la marca de Manuelita, **no se genera**.
2. **Guion**. `uv run pml pitch validate --json` debe responder `ok: true`. Ese comando comprueba:
   - 6 bloques en orden;
   - cada cifra con su fuente del oro;
   - «datos sintéticos» donde se menciona la planificación;
   - los cuatro pasos en el bloque `uso`;
   - el manifiesto y la ficha.
3. **Narración**. `uv run pml pitch narrate` genera la voz Phonon (spec 016) en `video/pitch/narracion/` y falla
   si un bloque no cabe en 9,5 s. Si falla, se recorta el texto del bloque en `guion.toml`; no se acelera la voz.

## 1. Alternativa: máquina de generación con los pesos abiertos

| Requisito | Valor (README oficial) |
|---|---|
| GPU | 8× NVIDIA Hopper de clase 80 GB (H100 o H200) |
| Disco | Unos 307 GB de checkpoints, más espacio de salida |
| Software | Docker con NVIDIA Container Toolkit, `hf` CLI y ffmpeg |
| Salida | Clips de **10 s** (única duración), 1088×1920 reescalados a 1080×1920, con audio |

El equipo local (RTX 3080 Ti, 16 GB) **no** alcanza. Hay que alquilar una instancia de 8× H100 por unas 2 horas:
descarga de pesos, 6 escenas y algunas regeneraciones. El costo depende del proveedor; se registra en el ADR 0032
al hacerlo.

## 2. Preparar la máquina

```bash
git clone https://github.com/jasonCastano/proyecto_modelos_lenguaje.git repo   # con git lfs pull
cd repo && git lfs pull --include "docs/referencias/*" && cd ..
docker pull sandai/magi-2-preview:latest
hf download sand-ai/MAGI-2-preview --local-dir ckpt
docker inspect --format '{{index .RepoDigests 0}}' sandai/magi-2-preview:latest   # anotar como model_revision
```

## 3. Generar escena por escena

Cada escena tiene su propia semilla en `escenas.json`, así que se genera una a la vez. En el equipo local, exporta
las entradas con la ruta del repositorio dentro del contenedor:

```bash
for n in 01 02 03 04 05 06; do
  uv run pml pitch samples --scene escena-$n --prefix /workspace/repo/ -o samples-$n.json
done
```

Copia los `samples-NN.json` a la máquina. Allí, con el repositorio montado en `/workspace/repo`:

```bash
docker run --gpus all -it \
  -v $PWD/ckpt:/workspace/ckpt -v $PWD/repo:/workspace/repo -v $PWD/out:/workspace/out \
  sandai/magi-2-preview:latest bash

# dentro del contenedor, por cada escena (SEED = la que imprimió pml pitch samples):
SAMPLES=/workspace/repo/samples-01.json OUTPUT_DIR=/workspace/out/escena-01 SEED=2026 bash scripts/run_demo.sh
```

`run_demo.sh` escribe `OUTPUT_DIR/sample_000.mp4`.

## 4. Traer y registrar los clips

1. Copia cada `out/escena-NN/sample_000.mp4` a `video/pitch/escenas/escena-NN.mp4` (va por Git LFS).
2. En `video/pitch/escenas.json`, completa por escena:
   - `clip`: `video/pitch/escenas/escena-NN.mp4`;
   - `model_revision`: el digest de la imagen Docker;
   - `generated_at`: ISO 8601;
   - `duration_s`: `ffprobe -v error -show_entries format=duration -of csv=p=0 <clip>`.

## 5. Revisar (obligatorio, FR-013)

Mira cada clip completo y llena `review`:

```json
"review": {"by": "<integrante>", "at": "<fecha>", "likeness": true, "no_text": true,
           "no_brand": true, "matches_script": true, "block_hash": "<hash>", "notes": "…"}
```

| Chequeo | Qué mirar |
|---|---|
| `likeness` | La presentadora se parece a la imagen de referencia: cara, cabello, chaqueta verde, tableta |
| `no_text` | No aparecen letras, números ni texto inventado en pantalla |
| `no_brand` | No aparecen logotipos ni la marca de Manuelita |
| `matches_script` | La acción acompaña el bloque del guion y la presentadora no «habla» a cámara |

Obtén `block_hash` con:

```bash
uv run python -c "from proyecto_modelos_lenguaje import pitch; s = pitch.load_script(); print(pitch.block_hash(s.block('<bloque>')))"
```

Con los cuatro chequeos en `true`, marca `"status": "aprobada"`. Si alguno falla, usa `"descartada"` y regenera la
escena del paso 3, con otra semilla o con el prompt ajustado en `video/pitch/prompts/escena-NN.json`. Registra el
cambio en `docs/prompt_log.md` §3.24.

Si después cambias el texto de un bloque, `pml pitch validate` marca su escena como desactualizada y hay que
revisarla de nuevo.

## 6. Montar y comprobar

```bash
uv run pml pitch assemble        # web/public/media/pitch-valeria.mp4 + .es.vtt + .webp, transcripción y web/src/data/pitch.ts
uv run pml pitch check web/public/media/pitch-valeria.mp4 --json
```

`check` exige:

- 60 s o menos;
- 1080×1920;
- audio;
- 25 MB o menos;
- subtítulos que cubran todo el video.

El video no lleva rótulo grabado. La declaración «Video generado con IA · Valer-IA es un proyecto académico, no un
canal oficial de Manuelita» la muestra la web junto al video y está en la transcripción. Por eso el video se publica
solo en la web.

## 7. Publicar

```bash
make app     # la entrada abre con el pitch en http://127.0.0.1:8000/
git add video/pitch web/public/media web/src/data/pitch.ts docs/prompt_log.md
```

Commit a nombre del integrante, sin firmas de bot. Los `.mp4`, `.wav` y `.webp` van por LFS (`.gitattributes`).
