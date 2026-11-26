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

**⚠️ Tareas con recurso externo**: T024 necesita una máquina con 8× H100/H200 (MAGI-2, research R1–R2), y T008
necesita que el integrante confirme el origen de la imagen. Están marcadas con **[EXTERNO]**. Todo lo demás corre en
el equipo local y en CI sin GPU ni red.

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
- [ ] T008 **[EXTERNO]** El integrante confirma en `docs/referencias/avatar_ingenio_manuelita.md` el origen de la
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
- [ ] T024 [US1] **[EXTERNO]** Generar las 6 escenas con MAGI-2 siguiendo `video/pitch/RUNBOOK.md` (T030) en una
  máquina con 8× H100/H200:
  1. `uv run pml pitch samples -o samples.json`.
  2. Imagen Docker `sandai/magi-2-preview` y `SAMPLES=… SEED=… bash scripts/run_demo.sh`.
  3. Traer cada `sample_00N.mp4` a `video/pitch/escenas/escena-0N.mp4`.
  4. Registrar `model_revision` (tag o commit de la imagen), `generated_at` y `duration_s` en `escenas.json`.
- [ ] T025 [US1] Revisar cada escena con los cuatro chequeos de `review`: `likeness`, `no_text`, `no_brand` y
  `matches_script`. Marcar `aprobada` o `descartada` en `escenas.json`. Las descartadas vuelven a T024 con
  `--scene` y otra semilla o indicación (FR-013).
- [ ] T026 [US1] Producir el video final:
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
exacta de esa escena. El rótulo aparece en los primeros 3 s y los últimos 4 s del video.

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
- [X] T032 [P] [US3] En `tests/integration/test_pitch_assemble.py`, comprobar que el rótulo de IA está grabado:
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

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 → T002 → T003.
- **Foundational (Phase 2)**: T004 → T005 → T006. T007 en paralelo. T008 (externo) bloquea solo la generación
  (T024).
- **US1 (Phase 3)**:
  - Pruebas T009–T013 primero.
  - Código: T014, T015 → T016–T019.
  - Web: T020–T023, independiente de la generación.
  - Producción: T024 (externo, requiere T008, T015, T016 y T030) → T025 → T026.
- **US2 (Phase 4)**: depende de T021 (mismo componente). No necesita el video real: las pruebas simulan el
  `<video>`.
- **US3 (Phase 5)**: T030 antes de T024. T031 y T032 dependen de T016 y T018.
- **Polish (Phase 6)**: al final. T038 requiere T026.

### User Story Dependencies

- **US1**: Phase 2. Su entregable final (el video) depende de los recursos externos T008 y T024.
- **US2**: T021. Se puede terminar y probar sin el video real (la web cae a portada y transcripción).
- **US3**: Phase 2 y T016/T018. El `RUNBOOK` (T030) es prerrequisito de la generación.

### Parallel Opportunities

- Phase 2: T004 y T007.
- US1: las pruebas T009–T013; T015 junto con T014; T020 junto con T016–T019.
- US2: T027 junto con T028.
- US3: T030, T031 y T032.
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
3. Con la ficha confirmada (T008) y GPU (T024): generar, revisar, montar y publicar el video real.

### Incremental Delivery

1. Cadena completa probada con clips sintéticos: puede integrarse a `main` sin el video. La web muestra la portada
   y la transcripción.
2. US2: controles, sesión, movimiento reducido y fallas.
3. US3: runbook, regeneración, rótulo verificado y ADR.
4. Video real generado con MAGI-2, montado y validado con personas.

---

## Notes

- No se añade ninguna dependencia de Python ni de npm. ffmpeg y la voz Phonon ya están en el proyecto.
- MAGI-2 nunca corre en CI ni en la aplicación. Las pruebas usan clips sintéticos de ffmpeg y una voz falsa.
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
