---

description: "Task list for spec 028: video elevator pitch de Valer-IA generado con MAGI-2"
---

# Tasks: Video elevator pitch de Valer-IA generado con MAGI-2

**Input**: Design documents from `/specs/028-video-pitch-magi2/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: se incluyen. La constitución exige `make check` en verde, y la spec mide SC-001, SC-003 a SC-007 con
pruebas. Las pruebas de cada historia se escriben primero y deben fallar.

**Organization**: tareas agrupadas por historia. Backend y CLI en `src/proyecto_modelos_lenguaje/`, producción en
`video/pitch/`, web en `web/src/` y `web/public/media/`.

**⚠️ Tareas con recurso externo**: están marcadas con **[EXTERNO]**. Todo lo demás corre en el equipo local y en CI
sin GPU ni red.

- **Gasto en Higgsfield** (revisión 2026-11-26, research R11–R14). T051, la calibración, y T024, las escenas,
  llaman a la API de Higgsfield con `HIGGSFIELD_API_KEY` y gastan saldo. Solo se corren con la autorización
  explícita del integrante.
- **Imagen de referencia**: T008 ya está hecha; la ficha se confirmó el 2026-11-26.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia de la spec (US1, US2, US3).

---

## Phase 1: Setup

**Purpose**: estructura, Git LFS y la imagen de referencia versionada.

- [X] T001 Crear `video/pitch/` con las subcarpetas `prompts/`, `escenas/` y `narracion/` (con `.gitkeep`), y
  `web/public/media/` (plan.md, Source Code).
- [X] T002 Añadir a `.gitattributes` las reglas LFS:
  - `video/pitch/escenas/*.mp4`;
  - `video/pitch/narracion/*.wav`;
  - `web/public/media/*.mp4`;
  - `web/public/media/*.webp`;
  - `docs/referencias/*.png`.

  Todas con `filter=lfs diff=lfs merge=lfs -text` (research R6). Verificar con `git check-attr`.
- [X] T003 Versionar `docs/referencias/avatar_ingenio_manuelita.png` por LFS. Crear la ficha
  `docs/referencias/avatar_ingenio_manuelita.md` con el frontmatter de data-model.md: `file`, `sha256` (calculado),
  `origin`, `rights`, `real_person`, `brand_elements` y `confirmed_by`. `real_person` y `confirmed_by` quedan
  vacíos hasta T008.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el módulo `pitch.py` con la carga y validación de los archivos de producción. Todas las historias
dependen de él.

**⚠️ CRITICAL**: ninguna historia empieza antes de esta fase.

- [X] T004 [P] Escribir las pruebas de carga y validación en `tests/unit/test_pitch.py`, con unidades de oro falsas
  en `tmp_path`. Validación del guion:
  - el guion exige «Exactamente 6, en el orden `gancho`, `problema`, `solucion`, `diferencia`, `uso`, `accion`»;
  - `language == "es"`;
  - `max_seconds ≤ 60`;
  - `narration` con «≤ 22 palabras»;
  - `claims` con ids que «existe[n] en `data/gold/knowledge_units.jsonl`»;
  - cada número de `narration`/`on_screen` presente en el texto de alguna unidad de sus `claims`;
  - si `synthetic = true`, `narration` contiene «datos sintéticos»;
  - el bloque `uso` nombra perfil, pregunta, fuentes y planificación.

  Validación del manifiesto:
  - 6 escenas `escena-01…06`, una por bloque y en el mismo orden;
  - `status` ∈ {`pendiente`, `aprobada`, `descartada`};
  - `trim_s ≤ 9,5`;
  - `resolution == "1080x1920"`;
  - `model == "sand-ai/MAGI-2-preview"`;
  - `aprobada` exige `review` con `likeness`, `no_text`, `no_brand` y `matches_script` en `true`.

  Validación de la ficha: `real_person: false`, `brand_elements: false` y `sha256` igual al PNG.
- [X] T005 Crear `src/proyecto_modelos_lenguaje/pitch.py`:
  - modelos inmutables `PitchBlock`, `PitchScript`, `Scene` y `ReferenceSheet`;
  - `load_script(root)`, `load_scenes(root)` y `load_reference(path)`;
  - `validate(root, gold_dir) -> ValidationReport`, con `ok`, `blocks`, `max_seconds`, `claims`,
    `unsupported_numbers`, `missing_units`, `reference{confirmed, sha256_matches}` y `errors`
    (contracts/pitch-cli.md).

  Sin red ni MAGI-2. T004 debe quedar en verde.
- [X] T006 Añadir el subcomando `pml pitch validate [--root video/pitch] [--json]` en
  `src/proyecto_modelos_lenguaje/cli.py` (junto a `sub.add_parser`, cerca de la línea 681). Devuelve 0 si `ok` y 1 si
  no. Probar la salida JSON en `tests/unit/test_pitch.py`.
- [X] T007 Crear `video/pitch/escenas.json` con las 6 escenas en `pendiente`:
  - `seed` 2026–2031;
  - `image: docs/referencias/avatar_ingenio_manuelita.png`;
  - `trim_s: 9.5`;
  - `clip`, `generated_at`, `duration_s` y `review` en `null` (contracts/production-files.md).
- [X] T008 **[EXTERNO]** El integrante confirma en `docs/referencias/avatar_ingenio_manuelita.md` el origen de la
  imagen (herramienta de IA y fecha), los derechos de uso, `real_person: false`, `brand_elements: false` y
  `confirmed_by`. Sin esto, `pml pitch validate` falla y no se genera (research R10, FR-008).

**Checkpoint**: `uv run pml pitch validate --json` corre y reporta las fallas pendientes (guion vacío o ficha sin
confirmar).

---

## Phase 3: User Story 1 - Entender Valer-IA en menos de un minuto al entrar (Priority: P1) 🎯 MVP

**Goal**: un video de 60 s o menos, con guion verificable, generado con MAGI-2, narrado en español y montado. Es el
primer elemento de la entrada y termina con «Empezar con Valer-IA».

**Independent Test**: `make app` → en `/` el video es lo primero visible, dura 60 s o menos y al terminar ofrece
«Empezar con Valer-IA» hacia `/agente`. `pml pitch validate` y `pml pitch check` en verde.

### Tests for User Story 1 ⚠️

- [X] T009 [P] [US1] En `tests/unit/test_pitch.py`, probar `export_samples(root, scene=None)`:
  - genera `[{"prompt_file": …, "image": …}]` en el orden de las escenas;
  - con `scene` exporta solo esa;
  - falla si `validate` falla.
- [X] T010 [P] [US1] En `tests/unit/test_pitch.py`, probar `narrate(root, engine)` con un motor de voz falso:
  - escribe `narracion/bloque-0N.wav`;
  - mide su duración;
  - falla si un bloque supera el `trim_s` de su escena.
- [X] T011 [P] [US1] Crear `tests/integration/test_pitch_assemble.py` (marca `skipif` sin ffmpeg):
  1. Generar 6 clips sintéticos 1080×1920 de 10 s con audio, usando ffmpeg `testsrc`/`sine`.
  2. Generar 6 WAV de 6 s y marcar las escenas `aprobada`.
  3. Correr `assemble`.

  Comprobar con ffprobe:
  - duración ≤ 57 s;
  - 1080×1920;
  - pista de audio;
  - `faststart`;
  - que existen `.vtt`, `.webp` y `transcripcion.md`;
  - que el VTT cubre toda la duración.

  Comprobar también que `assemble` se niega si alguna escena no está `aprobada`.
- [X] T012 [P] [US1] En `tests/unit/test_pitch.py`, probar `check(video)`. Debe fallar con más de 60 s, con otra
  resolución, sin audio o con más de 25 MB (contracts/pitch-cli.md, SC-001).
- [X] T013 [P] [US1] Crear `web/src/test/PitchVideo.test.tsx`:
  - `section[data-testid=pitch]` es el primer hijo de `.home`;
  - el `<video>` tiene `muted`, `playsInline`, `preload="metadata"`, `poster` y un `track` de subtítulos en español
    `default`;
  - al disparar `ended` aparece el enlace «Empezar con Valer-IA» a `/agente`;
  - la declaración «Video generado con IA» es visible como texto (contracts/web-ui.md).

### Implementation for User Story 1

- [X] T014 [US1] Escribir `video/pitch/guion.toml` (versión 1.0.0, 6 bloques, `max_seconds = 57`):
  - texto narrado en español de 22 palabras o menos por bloque, con la estructura gancho → problema → solución →
    diferencia → uso → acción;
  - `claims` con `unit_id` reales del oro para cada dato de Manuelita;
  - el bloque `uso` con los 4 pasos y `on_screen` «1 Perfil · 2 Pregunta · 3 Fuentes · 4 Planificación»;
  - el bloque que mencione la planificación con `synthetic = true` y «datos sintéticos».

  Buscar las unidades con `uv run python -m proyecto_modelos_lenguaje.tasks qa` o leyendo
  `data/gold/knowledge_units.jsonl`. Debe pasar `pml pitch validate`.
- [X] T015 [P] [US1] Escribir `video/pitch/prompts/escena-01.json`…`escena-06.json`. Cada uno es un caption
  estructurado con:
  - `scene`: la presentadora de la referencia, chaqueta verde y tableta, en el cañaduzal con el ingenio al fondo;
    la acción coherente con su bloque;
  - `camera`: plano y movimiento;
  - `audio`: ambiente de campo, sin voz;
  - `constraints`: «sin texto en pantalla, sin logotipos, la presentadora no habla a cámara».

  No incluir el nombre de la marca (contracts/production-files.md).
- [X] T016 [US1] Implementar en `src/proyecto_modelos_lenguaje/pitch.py` la función
  `export_samples(root, scene=None) -> list[dict]`. Añadir el comando `pml pitch samples [--scene] -o samples.json`
  en `cli.py`, que imprime las semillas para `SEED`. T009 en verde.
- [X] T017 [US1] Implementar `narrate(root, engine=None)` en `pitch.py`:
  - por defecto usa `voice.engine` (Phonon, spec 016) y escribe WAV con `voice.audio.to_wav_bytes`;
  - mide la duración y falla si supera `trim_s`;
  - CLI `pml pitch narrate [--block]`.

  La voz real se prueba aparte con la marca `voice`. T010 en verde.
- [X] T018 [US1] Implementar `assemble(root, output)` en `pitch.py` con ffmpeg (`subprocess` y una lista de
  argumentos):
  1. Verificar `validate` en verde, las 6 escenas `aprobada` con clip y las 6 narraciones.
  2. Recortar cada clip a `trim_s` y concatenar.
  3. Mezclar la narración con el audio de MAGI-2 a −18 dB.
  4. Grabar con `drawtext` «Video generado con IA · Valer-IA es un proyecto académico, no un canal oficial de
     Manuelita» en 0–3 s y en los últimos 4 s (research R7).
  5. Superponer `on_screen`.
  6. Codificar con `libx264 -movflags +faststart` y AAC.
  7. Escribir `pitch-valeria.es.vtt` (una entrada por bloque con sus tiempos), `pitch-valeria.webp` (cuadro de la
     escena 1 con el rótulo) y `video/pitch/transcripcion.md`.

  CLI `pml pitch assemble -o …`. T011 en verde.
- [X] T019 [US1] Implementar `check(video, vtt)` en `pitch.py` con ffprobe: duración ≤ `max_seconds`, 1080×1920,
  audio presente, ≤ 25 MB y cobertura del VTT. CLI `pml pitch check … --json`. T012 en verde.
- [X] T020 [P] [US1] Crear `web/src/data/pitch.ts` con las rutas (`/media/pitch-valeria.mp4`, `.webp`, `.es.vtt`),
  la transcripción (los 6 bloques de `guion.toml`) y la declaración de IA. `pml pitch assemble` lo regenera desde el
  guion para que no diverjan; añadir esa escritura en T018.
- [X] T021 [US1] Crear `web/src/components/home/PitchVideo.tsx` (contracts/web-ui.md, posición y estructura):
  - `<section data-testid="pitch">` con el encabezado «Conoce Valer-IA en un minuto» y la declaración de IA visible;
  - `<video>` con `muted`, `playsInline`, `preload="metadata"`, `controls`, `poster` y `track` de subtítulos
    `default`;
  - al terminar (`ended`), el enlace «Empezar con Valer-IA» a `/agente` (FR-021).
- [X] T022 [US1] En `web/src/pages/Home.tsx`, renderizar `<PitchVideo />` como **primer** hijo de `.home`, antes de
  `<PlatformHero />` (FR-015).
- [X] T023 [US1] En `web/src/styles/platform.css`, estilos de `.pitch` con los tokens de la spec 026:
  - en ≥ 900 px, video vertical a la izquierda (ancho máximo 360 px) con título, declaración y transcripción a la
    derecha;
  - en teléfono, video arriba a todo el ancho con altura máxima de 70 vh;
  - sin desplazamiento horizontal de 360 a 1920 px.
- [X] T024 [US1] **[EXTERNO, gasta unos 4,80 USD]** Generar las 6 escenas con MAGI-2 por la API de Higgsfield
  (revisado el 2026-11-26; requiere T040–T051):
  1. `uv run pml pitch generate --dry-run`: 6 escenas, 60 s y unos 4,80 USD.
  2. Con la autorización del integrante, `uv run pml pitch generate`. Cada clip queda en
     `video/pitch/escenas/escena-0N.mp4`, y `escenas.json` registra `job`, `generated_at` y `duration_s` con
     estado `generada`.
  3. Confirmar en la salida `--json` que cada clip mide 1080×1920 (o 1088×1920), unos 10 s y tiene audio.

  *Alternativa*: si Higgsfield no está disponible, seguir la sección de pesos abiertos del RUNBOOK
  (`pml pitch samples` en 8× H100).
- [X] T025 [US1] Revisar cada escena con los cuatro chequeos de `review`: `likeness`, `no_text`, `no_brand` y
  `matches_script`. Marcar `aprobada` o `descartada` en `escenas.json`. Las descartadas se regeneran con
  `pml pitch generate --scene escena-0N`, con otra semilla o indicación (FR-013).
- [X] T026 [US1] Producir el video final:
  1. `uv run pml pitch narrate`;
  2. `uv run pml pitch assemble -o web/public/media/pitch-valeria.mp4`;
  3. `uv run pml pitch check web/public/media/pitch-valeria.mp4 --json`.

  Registrar duración, tamaño y resolución en `specs/028-video-pitch-magi2/quickstart.md` §D (SC-001).

**Checkpoint**: con el video en `web/public/media/`, `make app` muestra el pitch primero. La US1 se demuestra sola.

---

## Phase 4: User Story 2 - Ver o saltar el video sin estorbar la entrada (Priority: P2)

**Goal**: el cliente controla el video. Puede saltarlo en un paso, el video no se repite en la sesión, respeta el
movimiento reducido y, si falla, la entrada sigue igual.

**Independent Test**: en `/`, «Saltar el video» lleva el foco al héroe. Al recargar en la misma sesión el bloque
aparece compacto. Con `prefers-reduced-motion` no arranca solo. Sin el archivo, se ven la portada y la
transcripción.

### Tests for User Story 2 ⚠️

- [X] T027 [P] [US2] Ampliar `web/src/test/PitchVideo.test.tsx`:
  - «Saltar el video» pausa, guarda `sessionStorage['valeria.pitch'] = 'saltado'` y lleva el foco a `#hero-title`;
  - con `valeria.pitch` en `visto` o `saltado`, el bloque es compacto con «Ver el video» y no llama a `play()`;
  - con `matchMedia('(prefers-reduced-motion: reduce)')`, no llama a `play()` y la transcripción queda abierta;
  - un evento `error` del `<video>` muestra «El video no está disponible; aquí tienes la transcripción.» y la
    transcripción;
  - «Activar sonido» y «Silenciar» alternan `muted`;
  - si `sessionStorage` lanza un error, el componente funciona igual.
- [X] T028 [P] [US2] Crear `tests/e2e/test_pitch.py`:
  - el pitch es el primer elemento de `main` en `/`;
  - «Saltar el video» deja visible el héroe en un paso;
  - al recargar en la sesión aparece compacto;
  - con `reduced_motion="reduce"` el video está pausado;
  - al bloquear `/media/pitch-valeria.mp4` con `page.route` se ven la portada y la transcripción, y el resto de la
    entrada funciona;
  - sin desplazamiento horizontal a 360, 768, 1440 y 1920 px;
  - axe-core sin violaciones serias en `/`.

### Implementation for User Story 2

- [X] T029 [US2] Completar `web/src/components/home/PitchVideo.tsx` (contracts/web-ui.md, Comportamiento):
  - `play()` sin sonido solo en la primera visita de la sesión y sin movimiento reducido;
  - el botón «Saltar el video» (`data-testid=pitch-skip`) pausa, guarda `saltado` y enfoca `#hero-title`;
  - `ended` guarda `visto`;
  - modo compacto con portada pequeña y «Ver el video»;
  - «Activar sonido» y «Silenciar»;
  - un `<details>` con «Ver la transcripción»;
  - estado de error con el mensaje y la transcripción abierta;
  - todo acceso a `sessionStorage` dentro de `try/catch`;
  - pausar al desmontar (cambio de área).

  Estilos del modo compacto en `web/src/styles/platform.css`. T027 en verde.

**Checkpoint**: las US1 y US2 funcionan juntas. `npx vitest run` y `make e2e` en verde.

---

## Phase 5: User Story 3 - Producir el video de forma reproducible y honesta (Priority: P3)

**Goal**: cualquiera del equipo entiende y repite la producción, puede regenerar una escena sola, y la declaración
de IA y de proyecto académico está en el video, la portada y la transcripción.

**Independent Test**: con `RUNBOOK.md` y `escenas.json`, `pml pitch samples --scene escena-03` reproduce la entrada
exacta de esa escena. La declaración de IA está junto al video en la web y en la transcripción, no grabada.

- [X] T030 [P] [US3] Escribir `video/pitch/RUNBOOK.md`:
  - requisitos: 8× Hopper de clase 80 GB, unos 307 GB de checkpoints, Docker y ffmpeg;
  - comandos exactos: `docker pull sandai/magi-2-preview`, `hf download sand-ai/MAGI-2-preview --local-dir ckpt`,
    `docker run --gpus all …` y `SAMPLES=… OUTPUT_DIR=… SEED=… bash scripts/run_demo.sh`;
  - cómo traer los clips y registrar `model_revision` y `generated_at`;
  - cómo revisar con los 4 chequeos;
  - cómo regenerar una escena con `pml pitch samples --scene`;
  - costo y tiempo estimados (research R1, R2, R9).
- [X] T031 [P] [US3] En `tests/unit/test_pitch.py`, probar la regeneración y la invalidación:
  - `export_samples(scene="escena-03")` reproduce exactamente su `prompt_file`, `image` y `seed`;
  - al cambiar el texto de un bloque del guion, la escena `aprobada` de ese bloque se reporta como desactualizada
    (transición «aprobada --(cambia el bloque)--> pendiente» de data-model.md), con un hash del bloque guardado en
    `review`.

  Implementar esa comprobación en `pitch.py` (SC-007).
- [X] T032 [P] [US3] (Revisada el 2026-11-26: ahora prueba que **no** hay rótulo grabado,
  `test_no_disclaimer_is_burned_in`.) En `tests/integration/test_pitch_assemble.py`, comprobar que el rótulo de IA
  está grabado:
  - extraer con ffmpeg un cuadro en t=1 s y otro en t=duración−2 s;
  - verificar que difieren del clip de origen en la franja del rótulo (o, si hay OCR disponible, que contienen «IA»);
  - comprobar que `transcripcion.md` y la portada incluyen la declaración (FR-009, SC-006).
- [X] T033 [US3] Añadir `docs/prompt_log.md` §3.24 con las 6 indicaciones de escena, sus semillas y la versión de
  MAGI-2, y el guion versionado. Añadir `docs/decisions/0032-video-pitch-magi2.md` con:
  - contexto y decisión (MAGI-2 fuera de línea, I2V con la referencia, voz Phonon, montaje ffmpeg, LFS, primer
    elemento de la entrada);
  - alternativas (servicio externo, horizontal, YouTube);
  - consecuencias (GPU alquilada, revisión humana).

---

## Phase 5b: User Story 3 - Generación por la API de Higgsfield y calibración (revisión 2026-11-26)

**Goal**: `pml pitch generate` produce las escenas con MAGI-2 en Higgsfield, en serie, con:

- tope de gasto;
- confirmación previa;
- `--dry-run`;
- calibración previa de 4 s;
- registro de cada trabajo en `escenas.json`;
- la clave sin aparecer nunca (FR-025 a FR-028, SC-008, SC-009).

**Independent Test**:

- **Sin red**: `uv run pytest tests/unit/test_pitch_generate.py` en verde, con `httpx.MockTransport`.
- **Con el repositorio**: `uv run pml pitch generate --dry-run --json` muestra 6 escenas, 60 s y 4,80 USD, sin
  llamar a la API.

### Tests for Higgsfield ⚠️

- [X] T040 [P] [US3] Crear `config/pitch.toml` (contracts/production-files.md):
  - `[higgsfield]`: `base_url = "https://api.higgsfield.ai"`, `model = "sand/magi-2/image-to-video"`,
    `api_key_env = "HIGGSFIELD_API_KEY"`, `resolution = "1080p"`, `seconds = 10`, `audio = true`, `poll_s = 10` y
    `timeout_s = 900`;
  - `[higgsfield.fields]`: `duration = "duration"` y `audio = "generate_audio"`;
  - `[budget]`: `usd_per_second = 0.08` y `max_usd = 20`.

  Además:
  - añadir `HIGGSFIELD_API_KEY=` a `.env.example`, sin valor, con el comentario «formato id:secreto, consola de
    Higgsfield»;
  - añadir `video/pitch/calibracion/` a `.gitignore`.
- [X] T041 [P] [US3] Crear `tests/unit/test_pitch_generate.py`, sin red: `httpx.MockTransport`, clips sintéticos
  de ffmpeg como respuesta de descarga y `tmp_path` como raíz. Casos:
  1. **Clave**:
     - sin `HIGGSFIELD_API_KEY`, falla antes de cualquier solicitud con un mensaje que nombra la variable y
       `.env`;
     - si no contiene `:`, falla igual.
  2. **Cabecera**: es `Authorization: Key <id>:<secreto>`.
  3. **Modelo**: si `GET /models` no lista `sand/magi-2/image-to-video`, falla sin enviar trabajos.
  4. **Flujo feliz** de una escena:
     - `POST /files/generate-upload-url` → `PUT upload_url` sin `Authorization` → `POST
       /sand/magi-2/image-to-video`;
     - el cuerpo es `{image_url, prompt, resolution: "1080p", seed, duration: 10, generate_audio: true}`, con la
       cabecera `Idempotency-Key` = `escena-01:<block_hash>:2026`;
     - estados `queued` → `in_progress` → `completed`;
     - descarga `video.url` a `escenas/escena-01.mp4`;
     - `escenas.json` queda con `status: "generada"`, `job.request_id`, `job.cost_usd == 0.8`, `generated_at` y
       `duration_s`.
  5. **Subida**: la imagen se sube una sola vez para varias escenas.
  6. **En serie**: no se envía la escena 2 antes de que termine la 1.
  7. **Aprobadas**: se omiten sin `--force` y se regeneran con `force=True`; el trabajo anterior pasa a
     `history`.
  8. **Tope**: con `max_usd` bajo, o con `history` que ya suma cerca del tope, se niega sin enviar.
  9. **`dry_run=True`**: no hace solicitudes (MockTransport falla si recibe alguna) y devuelve el plan con
     `seconds` y `cost_usd`.
  10. **Errores**:
      - 401 y 403 detienen la corrida sin tocar las escenas `aprobada`;
      - 429 con `Retry-After: 1` reintenta y sigue;
      - `failed` y `nsfw` dejan la escena en `error` con `cost_usd == 0` y el mensaje;
      - si pasa `timeout_s`, la escena queda en `error`.
  11. **Calibración**:
      - `calibrate()` envía 4 s a la escena 1 y guarda en `calibracion/`, sin modificar `escenas.json`;
      - informa ancho, alto, duración y audio;
      - falla si la duración medida difiere de 4 s en más de 1 s o si falta el audio.
  12. **SC-009**: en ningún caso la clave aparece en `str()` de excepciones, en la salida JSON, en `escenas.json`
      ni en los registros (`caplog`).
  13. **`prompt_text(scene)`**: arma el texto desde `prompts/escena-0N.json` (`scene`, `camera`, `audio`,
      `constraints`) e incluye «sin texto en pantalla» y «sin logotipos».

  Añadir una prueba con el marcador `network`, excluida por defecto: con la clave real, `GET /models` lista el
  modelo. No genera nada.
- [X] T042 [P] [US3] En `tests/unit/test_pitch.py`, actualizar la validación del manifiesto (data-model.md,
  Escena):
  - `status` ∈ {`pendiente`, `generando`, `generada`, `error`, `aprobada`, `descartada`};
  - `provider` ∈ {`higgsfield`, `local`};
  - `model == "sand/magi-2/image-to-video"` si `provider == "higgsfield"`, y `"sand-ai/MAGI-2-preview"` si
    `local`;
  - `request_seconds` entre 4 y 30;
  - las entradas antiguas sin `provider`, `job` ni `history` se cargan con los valores por defecto.

### Implementation for Higgsfield

- [X] T043 [US3] Crear `src/proyecto_modelos_lenguaje/pitch_higgsfield.py` (research R12–R14):
  - **Configuración y credenciales**:
    - `HiggsfieldConfig.load(path="config/pitch.toml")`;
    - `load_credentials(env)` lee `HIGGSFIELD_API_KEY` con `python-dotenv` y exige `id:secreto`.
  - **Cliente** `HiggsfieldClient(config, credentials, transport=None)` sobre `httpx.Client`, con métodos:
    - `list_models()`;
    - `upload_image(path) -> public_url`: `POST /files/generate-upload-url` y luego `PUT` con `upload_headers`,
      **sin** `Authorization`;
    - `submit(body, idempotency_key) -> request_id, status_url`;
    - `wait(status_url)`: consulta cada `poll_s` hasta `timeout_s` y devuelve el estado final;
    - `download(url, dest)`.
  - **Errores** tipados: `CredentialsError` (401 y clave ausente), `BalanceError` (403), `ModelUnavailable` (404,
    423 y 503 tras reintentos), `ValidationFailed` (400 y 422) y `JobFailed` (`failed`, `nsfw` y `canceled`).
    429 respeta `Retry-After`.
  - **Clave**: un `redact()` la quita de todo mensaje de error y de los registros. Nunca se registra la URL de
    subida.

  T041 (casos 1–3, 10 y 12) en verde.
- [X] T044 [US3] En `src/proyecto_modelos_lenguaje/pitch.py`, ampliar el modelo de escena (data-model.md):
  - nuevos campos `provider`, `request_seconds`, `job` y `history`;
  - estados `generando`, `generada` y `error`;
  - la validación por `provider`;
  - la carga compatible con el formato anterior.

  `assemble` sigue exigiendo `aprobada`.

  Actualizar `video/pitch/escenas.json`: las 6 escenas con `provider: "higgsfield"`, `model:
  "sand/magi-2/image-to-video"`, `request_seconds: 10`, `job: null` e `history: []`.

  Actualizar `docs/prompt_log.md` §3.24 con el modelo nuevo. T042 en verde.
- [X] T045 [US3] Implementar en `src/proyecto_modelos_lenguaje/pitch.py` la función
  `generate(root, *, scene=None, dry_run=False, force=False, client=None, confirm=None) -> GenerateReport`
  (contracts/pitch-cli.md). Precondiciones:
  - `validate` en verde;
  - la ficha confirmada;
  - el modelo en `list_models()`;
  - el costo estimado más lo gastado (suma de `cost_usd` en `job` e `history`) ≤ `max_usd`.

  Pasos:
  1. `prompt_text(scene)` desde el caption.
  2. Normalizar la referencia a 1080×1920 con ffmpeg (lanczos y relleno) en un archivo temporal.
  3. Subirla una vez.
  4. Por cada escena, en serie: escena a `generando`, `submit` con `Idempotency-Key` `escena-0N:<block_hash>:<seed>`,
     `wait` y `download`.
  5. Medir con `ffprobe`.
  6. Guardar `job` y `generated_at` con estado `generada`; si falla, `error` con el mensaje redactado.

  Guardar `escenas.json` después de cada escena, para no perder lo hecho si se interrumpe. T041 (casos 4–9 y 13) en
  verde.
- [X] T046 [US3] Implementar `calibrate(root, *, client=None, seconds=4) -> CalibrationReport` en `pitch.py`:
  - escena 1 con `seconds=4`, guardada en `video/pitch/calibracion/calibracion.mp4`;
  - informa `width`, `height`, `duration_s`, `audio` y `cost_usd`;
  - `ok` exige duración 4 ± 1 s, audio y alto 1920 o 1920 ± 16;
  - si falla, el mensaje sugiere revisar `[higgsfield.fields]` en `config/pitch.toml` (research R11).

  No modifica `escenas.json`, pero suma su costo al gasto total en `video/pitch/calibracion/gasto.json`. T041
  (caso 11) en verde.
- [X] T047 [US3] Añadir a `src/proyecto_modelos_lenguaje/cli.py` el comando
  `pml pitch generate [--scene escena-0N] [--calibrate] [--dry-run] [--yes] [--force] [--json]`:
  - imprime el plan (escenas, segundos y costo) y pide confirmación por consola salvo `--yes` o `--dry-run`;
  - devuelve 0 si todo quedó `generada` (o si la calibración pasa) y 1 si no.

  Probar en `tests/unit/test_pitch_generate.py` que `--dry-run --json` no usa red y que sin `--yes` respeta la
  respuesta «n».
- [X] T048 [P] [US3] Reescribir `video/pitch/RUNBOOK.md`:
  - **Higgsfield primero**:
    - clave `id:secreto` en `.env`;
    - saldo;
    - `generate --dry-run`, `--calibrate` y `generate`;
    - revisión;
    - regenerar con `--scene`;
    - costo esperado de 5 a 20 USD.
  - **Pesos abiertos en 8× H100** como alternativa: se conservan los pasos actuales.
  - **Datos**: qué se sube a Higgsfield (solo la imagen normalizada y los prompts) y por cuánto tiempo se conserva
    (7 días).
- [X] T049 [P] [US3] Actualizar la documentación de gobierno:
  - **`docs/decisions/0032-video-pitch-magi2.md`**: la decisión 1 pasa a Higgsfield. En alternativas, la API
    directa de Sand.ai, SandBase y las 8× H100. En consecuencias, el costo real, que se anota tras T024. También
    los datos enviados a un tercero y la clave en `.env`.
  - **`CONSTITUTION.md`** 2.3.0 (sin fusionar), §10 y fila del historial: «se genera con MAGI-2 por la API de
    Higgsfield, una vez y fuera de la app; la clave vive solo en `.env`; a Higgsfield solo se suben la imagen
    sintética y los prompts».
  - **`README.md`**: sección «Video pitch» con `generate`.
- [X] T050 [US3] Verificar sin gastar:
  - `uv run pml pitch generate --dry-run --json` sobre el repositorio da 6 escenas, 60 s y 4,80 USD;
  - una búsqueda de la clave en el repositorio da 0 resultados (SC-009).

  Registrar ambos resultados en `specs/028-video-pitch-magi2/quickstart.md` §D.
- [X] T051 [US3] **[EXTERNO, gasta unos 0,32 USD]** Con la autorización del integrante, correr
  `uv run pml pitch generate --calibrate --json`. Si no pasa, corregir `[higgsfield.fields]` en `config/pitch.toml`
  y repetir. Registrar en quickstart.md §D, «Calibración de 4 s»: tamaño, duración, audio, costo y nombres de
  campo confirmados. También actualizar research R11, cambiando «sin confirmar» por los nombres que funcionaron.

**Checkpoint**: con T040–T050, todo se prueba sin red. Con T051 aprobada, T024 genera las escenas reales.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T034 En `CONSTITUTION.md`, versión 2.3.0 (MINOR) en la cabecera y el pie:
  - en §3.7, «La entrada abre con el video pitch (spec 028): primer elemento, sin sonido, con subtítulos, saltable y
    sin repetirse en la sesión; la web funciona sin el video»;
  - en §10, «El video del pitch se genera fuera de línea con MAGI-2 a partir de un guion con fuentes del oro; declara
    en pantalla que es IA y proyecto académico; la imagen de referencia tiene ficha de origen y no representa a
    personas reales; solo se montan escenas revisadas»;
  - fila 2.3.0 en el historial;
  - nota de que requiere la aprobación de jasonCastano.
- [X] T035 [P] En `README.md`:
  - capturas de la entrada con el pitch;
  - sección «Video pitch (spec 028)» con cómo validar (`pml pitch validate`) y producir (enlace a `RUNBOOK.md`);
  - fila de estado de la spec 028;
  - enlace al ADR 0032.

  Mencionar que el video llega con `git lfs pull`.
- [X] T036 [P] Actualizar `docs/rubrica_modulo3.md` con una fila de la spec 028 que cite el video, el guion con
  fuentes y la declaración de IA.
- [X] T037 Correr `make check` y `make e2e`. Medir el JS (≤ 120 kB gzip) y la carga de la portada (< 1 s en local).
  Registrar los resultados en `specs/028-video-pitch-magi2/quickstart.md` §D.
- [ ] T038 **[EXTERNO]** Validación con personas (SC-002): 5 personas que no conocen el proyecto ven solo el video y
  luego describen Valer-IA y hacen su primera pregunta en `/agente`. Registrar el resultado en quickstart.md §D. La
  meta es al menos 4 de 5.
- [X] T039 Hacer commit a nombre de Robertto48, sin firmas de bot, con la constitución, el ADR y el código en el mismo
  commit. Los archivos de video van por LFS. No hacer push ni abrir el PR sin una petición explícita del integrante.
- [X] T052 Tras T040–T050, correr `make check` y `make e2e` con `LANGSMITH_TRACING=false`. Registrar las cifras en
  quickstart.md §D. Hacer commit a nombre de Robertto48, sin firmas de bot, con la spec, el plan, la ficha y el
  código de Higgsfield. Sin push ni PR hasta que el integrante lo pida.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 → T002 → T003.
- **Foundational (Phase 2)**: T004 → T005 → T006. T007 en paralelo. T008 hecha (2026-11-26).
- **US1 (Phase 3)**:
  - Pruebas T009–T013 primero.
  - Código: T014, T015 → T016–T019.
  - Web: T020–T023, independiente de la generación.
  - Producción: T024 (externo, requiere T051) → T025 → T026.
- **Higgsfield (Phase 5b)**:
  - pruebas T040, T041 y T042 en paralelo;
  - T043 → T044 → T045 → T046 → T047;
  - T048 y T049 en paralelo con el código;
  - T050 después de T047;
  - T051 (gasto, con autorización) después de T050;
  - luego T024.
- **US2 (Phase 4)**: depende de T021 (mismo componente). No necesita el video real: las pruebas simulan el
  `<video>`.
- **US3 (Phase 5)**: T030 antes de T024. T031 y T032 dependen de T016 y T018.
- **Polish (Phase 6)**: al final. T038 requiere T026. T052 cierra la Phase 5b.

### User Story Dependencies

- **US1**: Phase 2. Su entregable final (el video) depende de los recursos externos T008 y T024.
- **US2**: T021. Se puede terminar y probar sin el video real (la web cae a portada y transcripción).
- **US3**: Phase 2 y T016/T018. El `RUNBOOK` (T030) es prerrequisito de la generación.

### Parallel Opportunities

- Phase 2: T004 y T007.
- US1: las pruebas T009–T013; T015 junto con T014; T020 junto con T016–T019.
- US2: T027 junto con T028.
- US3: T030, T031 y T032.
- Higgsfield: T040, T041 y T042, y después T048 y T049 junto con T043–T047.
- Polish: T035 junto con T036.

---

## Parallel Example: User Story 1

```text
Task: "T009 export_samples en tests/unit/test_pitch.py"
Task: "T011 montaje con clips sintéticos en tests/integration/test_pitch_assemble.py"
Task: "T013 PitchVideo en web/src/test/PitchVideo.test.tsx"
Task: "T015 captions de MAGI-2 en video/pitch/prompts/escena-0N.json"
Task: "T020 transcripción y rutas en web/src/data/pitch.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Phases 1–2: estructura, LFS y validación.
2. US1 sin GPU: guion con fuentes, captions, CLI (`samples`, `narrate`, `assemble`, `check`) y `PitchVideo` en
   primera posición. Con clips sintéticos se prueba toda la cadena.
3. Con la ficha confirmada (T008, hecha): comando de Higgsfield probado sin red (T040–T050), calibración de 4 s
   (T051), y luego generar (T024), revisar, montar y publicar el video real.

### Incremental Delivery

1. Cadena completa probada con clips sintéticos: puede integrarse a `main` sin el video. La web muestra la portada
   y la transcripción.
2. US2: controles, sesión, movimiento reducido y fallas.
3. US3: runbook, regeneración, rótulo verificado y ADR.
4. Video real generado con MAGI-2, montado y validado con personas.

---

## Notes

- No se añade ninguna dependencia de Python ni de npm. ffmpeg, `httpx`, `python-dotenv` y la voz Phonon ya están en
  el proyecto.
- MAGI-2 y Higgsfield nunca corren en CI ni en la aplicación. Las pruebas usan clips sintéticos de ffmpeg, una voz
  falsa y `httpx.MockTransport`.
- La portada (`pitch-valeria.webp`) y el VTT pueden existir antes del video real. El componente cae a ellos si el
  `.mp4` falta.

### Implementación (2026-11-26)

- **Pendientes externos, a propósito**:
  - T008: el integrante confirma la ficha de la imagen de referencia.
  - T024: generar las 6 escenas en 8× H100/H200.
  - T025: revisar las escenas.
  - T026: montar el video real.
  - T038: validación con 5 personas.

  Sin el `.mp4`, la entrada muestra la portada y la transcripción, como exige FR-020.
- **Fuera de las tareas**:
  - `pml pitch poster` genera la portada desde la imagen de referencia, con la declaración de IA, para que la
    entrada tenga portada antes del video real (`web/public/media/pitch-valeria.webp`).
  - `pml pitch webdata` regenera `web/src/data/pitch.ts` desde el guion. Una prueba comprueba que no divergen.
  - `pml pitch samples --prefix` antepone la ruta del repositorio dentro del contenedor de MAGI-2.
  - El montaje limita la tasa de video a 3 Mbps: con contenido muy cambiante el archivo pasaba de 25 MB.
  - Los textos del rótulo se escriben en bytes con LF: en Windows `write_text` ponía CRLF y drawtext dibujaba
    líneas vacías.
  - `web/src/test/setup.ts` define `play`/`pause` vacíos (jsdom no los implementa).
  - El título del héroe recibe `tabIndex={-1}` para poder recibir el foco al saltar el video.
- **Orden TDD**: las pruebas de `PitchVideo` se escribieron junto al componente, no antes. Cubren todo el contrato
  web-ui.
- **Capturas del README**: se agregan cuando exista el video real. Hoy la entrada mostraría el aviso de video no
  disponible.
