# Research: video elevator pitch con MAGI-2

Fuentes:

- Ficha del modelo: <https://huggingface.co/sand-ai/MAGI-2-preview>.
- README: <https://github.com/SandAI-org/MAGI-2-preview>.
- Ambas consultadas el 2026-11-25.
- Lo que esas páginas no dicen se marca como *no indicado*.

## R1. Capacidades y límites de MAGI-2 Preview

- **Modelo**: «Magi-2 Preview», 114B parámetros (MoE, unos 6B activos por token), licencia **Apache 2.0**.
  - Hugging Face: `sand-ai/MAGI-2-preview`.
  - GitHub: `SandAI-org/MAGI-2-preview`.
  - Docker: `sandai/magi-2-preview`.
- **Modos**: texto a video (T2V) e imagen + texto a video (I2V). La imagen se usa como **primer cuadro**.
- **Duración**: clips de **10 s fijos**, «la única duración que el modelo admite hoy». No hay continuación ni
  encadenamiento de clips.
- **Resolución**: la etapa *preview* genera 512×896 y el *refiner* genera 1088×1920 (vertical). Con
  `--output-width/--output-height` se reescala a medidas múltiplos de 16. Los FPS no están indicados.
- **Audio**: genera sonido junto al video (VAE de audio *stable-audio-open-1.0*). Voz hablada en español y sincronía
  de labios: **no indicado**.
- **Hardware**: 8 GPU NVIDIA Hopper (clase 80 GB), Python 3.12, CUDA y ffmpeg. Los checkpoints pesan unos 307 GB.
  La variante destilada figura como «Coming soon».
- **Ejecución**:
  - Por lotes: `bash scripts/run_demo.sh` con `SAMPLES` (JSON con `prompt` o `prompt_file` e `image`), `OUTPUT_DIR`
    y `SEED`.
  - Un clip: `torchrun --nproc_per_node=8 inference/pipeline/entry.py --prompt … --image … --seed …
    --output-width … --output-height … --output …`.
- **Servicio alojado o precio**: no indicado. La ficha dice que ningún proveedor de inferencia lo despliega.

## R2. Dónde se genera

- **Decision**: la generación es un trabajo **fuera de línea y único**. Corre en una máquina alquilada con 8× H100 o
  H200 usando la imagen Docker oficial. El repositorio guarda solo las entradas (guion, manifiesto de escenas,
  imagen) y las salidas aprobadas (clips y video final).
- **Rationale**: el equipo local (RTX 3080 Ti, 16 GB) no puede correr el modelo. La web no debe depender de una
  GPU ni de un servicio externo para mostrar el video (spec, *Dónde se genera*).
- **Alternatives considered**:
  - **Space o API de terceros**: no hay proveedor oficial, y subir la imagen y el guion a un tercero sin acuerdo
    es otro riesgo.
  - **Esperar la variante destilada**: sin fecha.
  - **Otro modelo**: la spec exige MAGI-2.

## R3. Voz del pitch

- **Decision**: la narración en español se genera con la voz **Phonon** del proyecto (spec 016:
  `python -m proyecto_modelos_lenguaje.voice --say … -o bloque.wav`). Se mezcla en el montaje sobre el sonido
  ambiente de MAGI-2, bajado de volumen.
- **Rationale**: MAGI-2 no documenta voz en español ni sincronía de labios. Una voz en off con la presentadora sin
  hablar a cámara (gestos, tableta, mirada) evita labios desincronizados. Phonon ya está aprobada y es la voz que
  la web usa para Valer-IA.
- **Alternatives considered**:
  - Pedirle a MAGI-2 que la presentadora hable: resultado no garantizado.
  - Grabar a una persona: introduce a una persona real, que la spec evita.

## R4. Estructura del pitch y duración

- **Decision**: 6 escenas I2V de 10 s, recortadas a **9,5 s cada una**, para un total de **57 s**. Cada escena
  corresponde a un bloque del pitch:
  1. gancho;
  2. problema;
  3. solución;
  4. diferencia;
  5. cómo usarla;
  6. llamado a la acción.

  El texto narrado de cada bloque tiene un tope de palabras (alrededor de 22, unas 2,3 palabras por segundo).
- **Rationale**: los clips de 10 s fijos marcan el ritmo. Un bloque por escena simplifica regenerar solo una
  (SC-007). El margen de 3 s absorbe las transiciones.
- **Alternatives considered**: 5 escenas de 10 s más tarjetas de texto. Se descarta porque deja menos imagen
  generada y más montaje manual.
- **Video guía de YouTube**: no se pudo revisar. Se usa la estructura estándar del pitch. Si el integrante aporta
  la estructura del video guía, solo cambia el guion, no el plan.

## R5. Formato y ubicación en la web

- **Decision**: video vertical de **1080×1920**, H.264 + AAC y `faststart`, de unos 15 a 25 MB. Se sirve desde
  `web/public/media/` con:
  - subtítulos WebVTT (`pitch-valeria.es.vtt`);
  - portada (`pitch-valeria.webp`);
  - transcripción (en el código de la web).

  En la entrada, el video ocupa la **primera posición del héroe**: a la izquierda en escritorio, arriba y a todo lo
  ancho en teléfono.
- **Rationale**:
  - La imagen de referencia y la salida nativa de MAGI-2 son verticales; reencuadrar a horizontal recortaría a la
    presentadora.
  - Vite copia `web/public` a `web/dist`, y el servidor ya sirve esos archivos con soporte de rangos (Starlette
    1.10), así que se puede adelantar el video.
  - `webbuild` ya incluye `public/` en su huella, así que un video nuevo recompila la web.
- **Alternatives considered**:
  - Horizontal 1920×1088: recorta a la presentadora y no coincide con el modo nativo.
  - Servicio de video externo (YouTube): depende de un tercero y de la red, y no funciona sin conexión en la
    sustentación.

## R6. Versionado del video para quien clona (FR-023)

- **Decision**: los `.mp4` y `.webp` del pitch van por **Git LFS** (`web/public/media/*.mp4`,
  `video/pitch/escenas/*.mp4`), como las capas de datos. Los `.vtt`, el guion y el manifiesto van como texto.
- **Rationale**: el clon ya hace `git lfs pull` para los datos (README). Así el video llega con los pasos
  habituales.
- **Alternatives considered**: descargarlo de una URL externa al compilar. Se descarta porque rompe el clon sin red
  y crea otra fuente que mantener.

## R7. Declaración de IA en pantalla (FR-009)

- **Decision**: el montaje **graba en el video** un rótulo en los primeros 3 s y en los últimos 4 s: «Video generado
  con IA · Valer-IA es un proyecto académico, no un canal oficial de Manuelita». También va en la portada y en la
  transcripción.
- **Rationale**: grabado en el archivo, el rótulo acompaña al video aunque se descargue o comparta fuera de la web.
- **Alternatives considered**: superponerlo solo en la web. Se pierde al compartir el archivo.

## R8. Afirmaciones con fuente (FR-004)

- **Decision**: el guion (`video/pitch/guion.toml`) declara en cada bloque `claims` con su `unit_id` del oro. Un
  validador comprueba tres cosas:
  - que cada `unit_id` existe en `data/gold/knowledge_units.jsonl`;
  - que cada número del texto narrado aparece en alguna de sus unidades;
  - que los bloques que mencionan la planificación incluyen «datos sintéticos».
- **Rationale**: aplica al guion la misma regla del agente: sin fuente no hay cifra (constitución §10).
- **Alternatives considered**: revisión manual sola. No deja evidencia verificable para SC-003.

## R9. Revisión humana y registro (FR-012, FR-013)

- **Decision**: `video/pitch/escenas.json` guarda por escena:
  - `prompt`, `image`, `seed`, `model` y `revision` del repositorio de MAGI-2;
  - `generated_at`, `duration_s` y `status` (`pendiente`, `aprobada`, `descartada`);
  - `review` (quién revisó y las notas de los cuatro chequeos).

  El montaje **solo** acepta escenas `aprobada`. Regenerar una escena es exportar su entrada a `SAMPLES` y volver a
  correr `run_demo.sh` con la misma semilla.
- **Rationale**: es reproducible y auditable, y en el montaje no hay escena sin revisión.
- **Alternatives considered**: guardar solo los clips. Sin indicación ni semilla no se puede regenerar.

## R10. Imagen de referencia (FR-008)

- **Decision**: `docs/referencias/avatar_ingenio_manuelita.png` (941×1672, PNG, sin metadatos) se versiona con una
  ficha `docs/referencias/avatar_ingenio_manuelita.md`, firmada por el integrante, que declara:
  - origen (herramienta de IA con la que se generó);
  - derechos de uso;
  - que no representa a una persona real;
  - que no contiene la marca de Manuelita.

  El montaje se niega a correr si la ficha no está confirmada. Para I2V se escala a 1088×1920 sin deformar (se
  rellena el borde).
- **Rationale**: la constitución exige que el avatar no imite a personas reales. La imagen no trae metadatos de
  origen, así que la confirmación debe ser explícita.
- **Alternatives considered**: asumirlo sin registro. No es verificable.
