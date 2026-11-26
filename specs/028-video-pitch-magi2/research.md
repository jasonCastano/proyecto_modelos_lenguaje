# Research: video elevator pitch con MAGI-2

Fuentes:

- Ficha del modelo: <https://huggingface.co/sand-ai/MAGI-2-preview>.
- README: <https://github.com/SandAI-org/MAGI-2-preview>.
- Ambas consultadas el 2026-11-25.
- Lo que esas páginas no dicen se marca como *no indicado*.
- Revisión 2026-11-26: documentación de la API de Higgsfield (<https://docs.higgsfield.ai>: autenticación,
  solicitudes, archivos, errores, límites y webhooks), su blog «Best Ways to Access MAGI-2» (2026-11-25) y un
  sondeo de la API con la clave del integrante (R11). R1 describe los pesos abiertos, que quedan como alternativa.

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

- **Decision** (revisada el 2026-11-26): las escenas se generan con **MAGI-2 alojado en Higgsfield**, por su API,
  desde el equipo del integrante con `pml pitch generate`. Es un trabajo **único**, fuera de la app y de la CI. El
  repositorio guarda las entradas (guion, manifiesto, prompts, imagen y su ficha) y las salidas aprobadas (clips y
  video final).
- **Rationale**:
  - el integrante ya tiene la clave y saldo;
  - cuesta unos 5 USD por las 6 escenas, frente a 40–80 USD de alquilar 8 GPU;
  - no exige descargar 307 GB ni preparar Docker;
  - el modelo alojado es el MAGI-2 completo, a 1080p.
- **Alternatives considered**:
  - **Pesos abiertos en 8× H100 alquiladas** (decisión anterior): queda documentada en `RUNBOOK.md` como
    alternativa; `pml pitch samples` se mantiene.
  - **API directa de Sand.ai**: sin recargas de autoservicio a noviembre de 2026.
  - **SandBase u otros agregadores**: documentan el esquema, pero exigen otra cuenta y otra clave.
  - **Editor web de Higgsfield a mano**: posible, pero sin registro reproducible de cada escena (FR-012).

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

## R7. Declaración de IA (FR-009, revisada el 2026-11-26)

- **Decision**: el video **no** lleva rótulo grabado, por decisión del integrante, para que funcione como un
  elevator pitch limpio. La declaración «Video generado con IA · Valer-IA es un proyecto académico, no un canal
  oficial de Manuelita» va:
  - como texto visible junto al video en la entrada (`.pitch__disclaimer`);
  - en la transcripción.

  El cierre narrado es un llamado a la acción.
- **Rationale**: la web es el único lugar donde se publica el video. Allí la declaración siempre está a la vista, así
  que se cumple §10 sin cargar el pitch con un aviso.
- **Alternatives considered**:
  - rótulo grabado en 0–3 s y en los últimos 4 s (decisión anterior), descartado por el integrante;
  - declaración narrada en el cierre, cambiada por un llamado a la acción.
- **Consecuencia**: si el archivo se comparte fuera de la web, no lleva la declaración. Por eso el video no se
  publica en otros canales.

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

## R11. MAGI-2 en la API de Higgsfield: modelo y campos

Sondeo del 2026-11-26 con la clave del integrante. Solo se enviaron cuerpos inválidos, que la API rechaza con 400
sin crear trabajos ni cobrar.

- **Catálogo** (`GET https://api.higgsfield.ai/models`, 108 modelos). Hay tres entradas de MAGI-2:
  - `sand/magi-2/image-to-video`: «Animate a still image into a 1080p video, with an optional final frame to guide
    the ending. […] choose a duration from 4 to 30 seconds, with optional generated audio»;
  - `sand/magi-2/text-to-video`: menciona «one of six aspect ratios»;
  - `sand/magi-2/reference-to-video`.

  El catálogo no publica su `input_schema` (viene `null`), y la documentación de Higgsfield todavía no tiene página
  de MAGI-2.
- **Campos confirmados** en `sand/magi-2/image-to-video` por los mensajes del validador:

  | Campo | Regla confirmada |
  |---|---|
  | `image_url` | Obligatorio, cadena |
  | `prompt` | Cadena |
  | `resolution` | Enum `["1080p"]` |
  | `seed` | Entero |

- **Confirmado por la calibración (2026-11-26)**:
  - `duration` y `generate_audio` funcionan: se pidieron 4 s y salieron 4,24 s, con audio;
  - **`aspect_ratio: "9:16"` es necesario**. Sin él, la primera calibración salió **1920×1080**: MAGI-2 extendió
    la imagen vertical a 16:9 con más paisaje a los lados. Con `"9:16"`, la segunda salió **1080×1920**;
  - cada trabajo de 4 s tardó unos 15 min en la cola de Higgsfield, así que `timeout_s` sube a 3600;
  - las dos calibraciones costaron 0,64 USD.
- **Antes de calibrar** estaban sin confirmar los nombres de los campos de duración, audio y cuadro final. El validador informa un error a
  la vez y acepta campos desconocidos, así que un nombre mal escrito se ignoraría sin aviso. Los nombres probables
  son `duration` y `generate_audio`, que usan los demás modelos del catálogo y SandBase.
- **Decision**:
  - **Calibración**: antes de las 6 escenas se corre una generación pagada de 4 s, que cuesta unos 0,32 USD
    (`pml pitch generate --calibrate`). ffprobe confirma la duración, el tamaño y la pista de audio del resultado.
  - **Nombres configurables**: los nombres de campo viven en `config/pitch.toml`, así que si la calibración muestra
    otro nombre se corrige sin tocar código.
- **Alternatives considered**:
  - Asumir los nombres: un nombre mal escrito haría salir 6 clips de duración por defecto, con dinero gastado.
  - Pedir el esquema a soporte: lento, y la calibración lo resuelve por 0,32 USD.

## R12. Autenticación con Higgsfield

- **Decision**:
  - **Cabecera**: `Authorization: Key <id>:<secreto>`, contra `https://api.higgsfield.ai` (docs:
    *Authentication*).
  - **Clave**: `HIGGSFIELD_API_KEY` en `.env` ya trae el par `id:secreto`. Se verificó su forma sin imprimirla.
    Con ella, `GET /models` responde 200 y el modelo responde 400 de validación, no 401.
  - **Lectura**: el CLI la lee con `python-dotenv`, igual que `DEEPSEEK_API_KEY`.
  - **Cliente**: se usa `httpx`, que ya es dependencia, y no el SDK `higgsfield-client`, que lee `HF_KEY`.
- **Rationale**:
  - sin dependencias nuevas;
  - `HF_*` choca con `HF_TOKEN` de Hugging Face, que ya usa la voz Phonon;
  - con un cliente propio, la clave no aparece en registros ni excepciones: se redacta en todo mensaje de error
    (FR-026).
- **Errores esperados** (docs: *Errors*):

  | Código | Significado | Qué hace el comando |
  |---|---|---|
  | 401 | Credenciales inválidas | Pide revisar `.env` |
  | 403 | Saldo insuficiente | Pide recargar; no reintenta |
  | 404 | Modelo no disponible para la cuenta | Se detiene |
  | 400, 422 | Validación | Se detiene y muestra el detalle |
  | 429 | Cola llena | Espera `Retry-After` y reintenta |
  | 503 | Admisión no disponible | Reintenta con espera |

  Los trabajos `failed` y `nsfw` no se cobran.
- **Alternatives considered**: el SDK oficial (dependencia nueva y variable `HF_KEY`), o cabeceras heredadas
  `hf-api-key`/`hf-secret` (en retiro).

## R13. Formato vertical e imagen como primer cuadro

- **Primer cuadro**: sí. El modo `image-to-video` «anima una imagen fija», con cuadro final opcional; la imagen
  es el inicio del clip. Es lo que pide FR-007 para la coherencia entre escenas.
- **Vertical**:
  - El catálogo solo menciona relaciones de aspecto para `text-to-video`, pero `image-to-video` también acepta
    `aspect_ratio`. **Sin él, sale 16:9 aunque la imagen sea vertical**; esto lo mostró la calibración.
  - La referencia mide 941×1672, una proporción de 0,5628, frente a 0,5625 de 9:16. Se envía
    `aspect_ratio: "9:16"`.
  - **Decision**: antes de subirla, `generate` normaliza la referencia a 1080×1920 con ffmpeg (lanczos y relleno
    de 1 px) en un archivo temporal, para que el clip salga 9:16 a 1080p. La calibración lo confirma. El montaje
    ya escala y recorta a 1080×1920 si el clip trae otra medida, por ejemplo 1088×1920.
- **Cuadro final**: no se usa. Su nombre de campo no está confirmado y la continuidad entre escenas ya la da la
  misma imagen inicial.
- **Subida**: `image_url` exige una URL. El flujo de archivos de Higgsfield es:
  1. `POST /files/generate-upload-url` con `{"content_type": "image/png"}`;
  2. `PUT` del archivo a `upload_url` con `upload_headers` y sin credenciales;
  3. usar `public_url`, de retención temporal.

  Se sube una vez por corrida y se reutiliza en todas las escenas.

## R14. Flujo, costo y control del gasto

- **Envío**:
  - `POST https://api.higgsfield.ai/sand/magi-2/image-to-video`;
  - con cabecera `Idempotency-Key` = `escena-0N:<block_hash>:<seed>`, para que un reintento no cobre dos veces;
  - responde `request_id` y `status_url`.
- **Espera**:
  - consulta `status_url` cada 10 s, con un tope de 15 min;
  - estados: `queued`, `in_progress`, `completed`, `failed`, `nsfw` y `canceled`;
  - al completar, `video.url` se descarga a `video/pitch/escenas/escena-0N.mp4`, porque los resultados se
    conservan 7 días;
  - sin webhooks, porque el equipo local no expone una URL pública.
- **En serie**: el blog de MAGI-2 indica una generación concurrente por cuenta por defecto. Más trabajos quedarían
  en cola; en serie, el costo y los errores son más claros.
- **Costo**:
  - 0,08 USD por segundo (blog de Higgsfield, 2026-11-25): 6 × 10 s = 4,80 USD, más 0,32 USD de calibración;
  - `config/pitch.toml` fija `usd_per_second` y `max_usd = 20` (SC-008);
  - antes de enviar, el comando muestra segundos y costo, suma lo ya gastado según `escenas.json` y se niega a
    pasar el tope;
  - pide confirmación (`--yes` la omite) y `--dry-run` no llama a la API (FR-027).
- **Qué se sube**: solo la imagen de referencia normalizada y el texto del prompt de cada escena. Nunca el guion
  narrado, datos del corpus, claves ni datos personales.
- **Pruebas**: `httpx.MockTransport` simula catálogo, subida, envío, estados y errores (401, 403, 429, `failed`,
  `nsfw`) sin red (FR-028).
