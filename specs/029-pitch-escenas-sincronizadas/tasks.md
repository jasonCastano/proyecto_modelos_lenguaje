# Tasks: Pitch v2 con escenas sincronizadas a la narración

**Input**: Design documents from `specs/029-pitch-escenas-sincronizadas/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: se incluyen. La constitución (DoD) exige pruebas sin red para todo código nuevo, como en la spec 028.
Se usan clips sintéticos de ffmpeg, `httpx.MockTransport` y un alineador falso. Correr siempre con
`LANGSMITH_TRACING=false`.

**Organization**: por historia de usuario.

- **US1 (P1)**: ver en pantalla lo que la narración nombra.
- **US2 (P2)**: ritmo que sigue a la narración.
- **US3 (P3)**: producir la v2 sin perder la v1 ni salirse del presupuesto.

**Gasto**: las tareas marcadas **[EXTERNO, gasta]** llaman a la API de Higgsfield y requieren la autorización del
integrante. Todo lo demás es sin red.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: US1, US2 o US3.

## Path Conventions

- Código: `src/proyecto_modelos_lenguaje/`.
- Pruebas: `tests/unit/` y `tests/integration/`.
- Producción: `video/pitch/`.
- Web: `web/public/media/` y `web/src/data/pitch.ts`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuración, rutas y reglas de Git para la v2.

- [X] T001 Reescribir `config/pitch.toml` al esquema de `contracts/production-files.md`:
  - `[higgsfield]`: `base_url`, `api_key_env`, `poll_s` y `timeout_s = 3600`;
  - `[pitch]`: `model = "magi2"`, `pause_s = 0.5`, `retime_min = 0.8` y `retime_max = 1.25`;
  - `[models.magi2]` y `[models.kling4]`, con `usd_per_second`, `resolution`, `aspect_ratio = "9:16"` y los slugs
    `image`, `reference` y `text`;
  - `[models.<id>.fields]` con los nombres de campo conocidos: MAGI-2 `duration`, `generate_audio` y
    `aspect_ratio`; Kling, por calibrar;
  - `[budget]`: `max_usd = 20`.
- [X] T002 [P] Agregar a `.gitattributes`: `video/pitch/planos/*.mp4` y `video/pitch/graficos/png/*.png` por LFS.
  Agregar a `.gitignore`: `video/pitch/borrador/`.
- [X] T003 [P] Crear las carpetas `video/pitch/planos/`, `video/pitch/graficos/` y `video/pitch/graficos/png/`
  (con `.gitkeep` donde haga falta), y `docs/decisions/0033-pitch-v2-sincronia.md` con la estructura de ADR del
  proyecto (contexto, decisión, alternativas, consecuencias).
- [X] T004 [P] Crear los esqueletos con docstring en español: `src/proyecto_modelos_lenguaje/pitch_sync.py`,
  `src/proyecto_modelos_lenguaje/pitch_graphics.py`, `tests/unit/test_pitch_sync.py` y
  `tests/unit/test_pitch_graphics.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: guion 1.2.0, registro de planos v2 y configuración por modelo. Todo lo demás depende de esto.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

### Pruebas (escribir primero; deben fallar)

- [X] T005 [P] En `tests/unit/test_pitch.py`, pruebas del guion 1.2.0:
  - `pause_s` fuera de 0,3–0,8 da error;
  - `on_screen` con pasos numerados da error (FR-004);
  - cada `[[block.cue]]` exige `id` único, `word` presente en la narración de su bloque (comparada sin tildes y por
    prefijo), `kind` en `{"plano", "grafico"}`, `shot` si `kind = "plano"` y `graphic` si `kind = "grafico"`;
  - `from` y `to` con valores en 0–1.
- [X] T006 [P] En `tests/unit/test_pitch.py`, pruebas de `escenas.json` esquema 2:
  - carga de `{"schema": 2, "model", "scenes": [{"id", "block", "shots": [...]}]}`;
  - `id` con patrón `plano-0N[a-z]`;
  - `mode` en `{"image", "reference", "text"}`;
  - `source` en `{"reference", "frame:<plano>", null}`, con `null` solo si `mode = "text"`;
  - semillas únicas;
  - todos los planos con el modelo de `escenas.json.model`;
  - estado de escena derivado (`aprobada` solo si todos sus planos lo están);
  - un plano `aprobada` exige `review` con `likeness`, `no_text`, `no_brand`, `matches_script`, `cue_shown`,
    `block_hash` y `anchors` completos para sus momentos `plano`.
- [X] T007 [P] En `tests/unit/test_pitch_generate.py`, pruebas de configuración multimodelo:
  - `HiggsfieldConfig.load` lee `[pitch].model` y `[models.*]`;
  - `slug(mode)` devuelve el slug del modo;
  - `cost(seconds)` usa el `usd_per_second` del modelo;
  - un modelo desconocido da un error claro.

### Implementación

- [X] T008 Extender `PitchBlock` y `load_script` en `src/proyecto_modelos_lenguaje/pitch.py`:
  - `pause_s` a nivel de guion;
  - `cues: tuple[PitchCue, ...]`, con `PitchCue(id, word, kind, shot, graphic, from_xy, to_xy, hold_s, at_s)`;
  - validación de T005 dentro de `_validate_script`.
- [X] T009 Implementar el esquema 2 de escenas en `src/proyecto_modelos_lenguaje/pitch.py`: `load_scenes`,
  `save_scenes`, `iter_shots`, `scene_status` y `_validate_scenes`, con las reglas de T006.
  - Un archivo sin `schema` se rechaza con el mensaje «registro de la v1: migrar con la v2 del plan».
  - `block_hash` sigue invalidando la revisión si cambia el texto.
- [X] T010 Pasar `HiggsfieldConfig` a configuración por modelo en
  `src/proyecto_modelos_lenguaje/pitch_higgsfield.py`:
  - `model_id`, `slugs` por modo, `fields` por modelo y `usd_per_second`;
  - `submit(body, key, mode)` usa el slug del modo;
  - `body(...)` arma los campos según el modelo y el modo: `image_url` para `image`, la referencia para
    `reference` (en Kling, `elements`) y nada para `text`.
- [X] T011 Escribir `video/pitch/guion.toml` versión `1.2.0`:
  - `pause_s = 0.5`;
  - la narración de `solucion` de FR-001, con la coma («así, los aliados…»);
  - las demás narraciones iguales a la 1.1.0;
  - sin `on_screen`;
  - los momentos de `data-model.md`: gancho (2, `plano`), problema (6, `grafico`, `to` sobre la tablet), solucion
    (5, `plano` en `plano-03a`), diferencia (3, `grafico`), uso (1 momento `perfil` con las 5 tarjetas), accion
    (1, `plano` en `plano-06`).
- [X] T012 Escribir `video/pitch/escenas.json` esquema 2 con los 8 planos del plan (`plano-01a` texto 5 s,
  `plano-01b` referencia 6 s, `plano-02` imagen 9 s, `plano-03a` referencia 10 s, `plano-03b` imagen desde
  `frame:plano-03a` 5 s, `plano-04` referencia 6 s, `plano-05` imagen 9 s, `plano-06` imagen desde
  `frame:plano-03a` 8 s), semillas 3001–3008, `status "pendiente"`, `job null`, `history []`.
- [X] T013 [P] Escribir los 8 prompts en `video/pitch/prompts/plano-*.json`:
  - campos `subject`, `setting`, `style`, `action`, `camera`, `audio`, `constraints` y `duration_s`;
  - `people` en `plano-03a.json`, con las cinco personas descritas por vestimenta (FR-013);
  - `plano-04.json`: oficina ejecutiva genérica, sin logotipos ni letreros (FR-014);
  - `plano-01a.json`: trapiche tradicional genérico funcionando en un cañaduzal;
  - `plano-02.json` y `plano-05.json` explicitan «sin paneles flotantes»;
  - todos con «sin texto, letras, números ni logotipos» (FR-016).
- [X] T014 Actualizar `prompt_text` y `validate` en `src/proyecto_modelos_lenguaje/pitch.py` para planos: el
  prompt incluye `people` si existe. Correr `uv run pml pitch validate --json` y dejarlo en `ok: true`.

**Checkpoint**: guion, registro y configuración v2 cargan y validan. T005–T007 en verde.

---

## Phase 3: User Story 1 - Ver en pantalla lo que la narración nombra (Priority: P1) 🎯 MVP

**Goal**: cada momento sincronizado aparece a ±0,5 s de su palabra. Iconos y perfiles van como gráficos del montaje,
y los eventos de los planos se ajustan con anclas.

**Independent Test**: con planos sintéticos y un alineador falso, montar y comprobar en la salida `cues` que cada
`delta_s` cumple `|delta_s| ≤ 0.5` y que ninguno es negativo. Con el video real, verlo sin sonido junto a la
lista de momentos.

### Pruebas (escribir primero; deben fallar)

- [X] T015 [P] [US1] En `tests/unit/test_pitch_sync.py`, pruebas de `align`:
  - con un transcriptor falso que devuelve palabras con tiempos, `find_cue` encuentra «visitantes» por prefijo y sin
    tildes («acuicultura»/«acuicultúra»);
  - toma la primera aparición después del momento anterior;
  - usa `at_s` si la palabra falta;
  - falla con el `cue_id` si no hay ni palabra ni `at_s`;
  - `sincronia.json` guarda `script_version`, `narration_s`, `scene_s`, `start_s`, `words`, `cues` y
    `narration_hash`.
- [X] T016 [P] [US1] En `tests/unit/test_pitch_sync.py`, pruebas de la línea de tiempo y del reajuste:
  - los tramos de plano dentro de su escena;
  - un plano con anclas `{cue: t_clip}` se reparte por tramos con factores dentro de `[retime_min, retime_max]`;
  - un tramo que exige 1,4× da `PitchError` con el plano y el momento;
  - sin anclas, el plano se recorta desde 0 sin reajuste.
- [X] T017 [P] [US1] En `tests/unit/test_pitch_graphics.py`, pruebas de gráficos:
  - el filtro `overlay` de un momento `grafico` tiene `enable='between(t,a,b)'` con `a = start_s + cue` y la
    trayectoria lineal `from`→`to` en 0,8 s;
  - la vista de perfiles escalona las 5 tarjetas;
  - `render_svgs` con un rasterizador falso escribe un PNG por SVG y omite los que están al día por hash.
- [X] T018 [US1] En `tests/integration/test_pitch_assemble.py`, montaje por planos con 8 clips sintéticos de ffmpeg,
  narraciones sintéticas, `sincronia.json` de prueba y PNG de prueba:
  - el video dura `Σ scene_s`;
  - en el cuadro de un momento `grafico`, la zona del icono cambia respecto del cuadro anterior a su palabra
    (diferencia de píxeles);
  - la salida JSON trae `cues` con `|delta_s| ≤ 0.5`;
  - un plano `frame:` usa el último cuadro del plano fuente.

### Implementación

- [X] T019 [US1] Implementar `align(root, *, transcriber=None)` en `src/proyecto_modelos_lenguaje/pitch_sync.py`:
  - usa faster-whisper (`WhisperModel` del modelo configurado en `config/stt.toml`, idioma `es`,
    `word_timestamps=True`), cargado de forma diferida;
  - normaliza con `unicodedata` y empareja por prefijo;
  - escribe `video/pitch/sincronia.json` según `data-model.md`.
- [X] T020 [US1] Implementar en `src/proyecto_modelos_lenguaje/pitch_sync.py`:
  - `timeline(script, scenes, sync, config)`: inicio y fin de cada escena, tramos de plano e instantes de gráficos;
  - `retime_segments(shot, anchors, cues, window, limits)`: factores por tramo y filtros `trim`/`setpts`;
  - errores claros cuando un factor sale de 0,8–1,25.
- [X] T021 [P] [US1] Dibujar los SVG propios en `video/pitch/graficos/`:
  - iconos `icono-informes`, `icono-noticias`, `icono-cana`, `icono-palma`, `icono-acuicultura`, `icono-frutas`,
    `icono-cita`, `icono-calculo` e `icono-confirmar`;
  - tarjetas `perfil-visitante`, `perfil-cliente`, `perfil-proveedor`, `perfil-colaborador` y
    `perfil-planificador`, con los nombres exactos de `web/src/lib/platform.ts` (Visitante, Cliente B2B, Proveedor,
    Colaborador, Planificador industrial);
  - colores de la web (`web/src/styles`) y tipografía del proyecto;
  - sin marca Manuelita.
- [X] T022 [US1] Implementar en `src/proyecto_modelos_lenguaje/pitch_graphics.py`:
  - `render_svgs(root, *, rasterizer=None)`: Playwright con Chromium, `omit_background=True`; escribe en
    `graficos/png/` y omite los PNG al día por hash;
  - `overlay_filters(timeline, graphics_dir)`: entradas de PNG y cadena de `overlay`, con aparición de 0,25 s
    (`fade` sobre alfa), trayectoria `from`→`to` en 0,8 s y salida en `hold_s` o al fin de la escena.
- [X] T023 [US1] Reescribir `assemble` en `src/proyecto_modelos_lenguaje/pitch.py`:
  - consume `timeline` y `retime_segments` y concatena los tramos de cada escena;
  - aplica `overlay_filters`;
  - mezcla la narración de cada bloque en `start_s`;
  - el fondo de cada plano va a −18 dB, o silencio si no tiene audio;
  - devuelve `scenes`, `retime` y `cues` (con `word_s`, `shown_s` y `delta_s`) según `contracts/pitch-cli.md`;
  - exige `sincronia.json` vigente (misma `script_version` y mismo `narration_hash`).
- [X] T024 [US1] Agregar a `src/proyecto_modelos_lenguaje/cli.py` los comandos `pml pitch align` y
  `pml pitch graphics`, con `--root` y `--json`. Códigos: 0 si va bien, 2 si falta un momento.
- [X] T025 [US1] Actualizar `render_captions` y `render_transcript` en `src/proyecto_modelos_lenguaje/pitch.py`:
  un tramo de subtítulo por escena, con los tiempos reales de `sincronia.json`.

**Checkpoint**: con datos sintéticos, la v2 se monta con iconos, perfiles y eventos sincronizados. T015–T018 en
verde.

---

## Phase 4: User Story 2 - Un ritmo que sigue a la narración (Priority: P2)

**Goal**: cada escena dura su narración más una pausa de 0,3–0,8 s. Ninguna narración se corta, y el total queda en
60 s o menos.

**Independent Test**: medir en el borrador el silencio entre escenas (≤ 0,8 s) y la duración total (≤ 60 s), con
`pml pitch check`.

### Pruebas (escribir primero; deben fallar)

- [X] T026 [P] [US2] En `tests/unit/test_pitch.py`, pruebas de `narrate` con un motor falso:
  - ya no falla porque un bloque dure más de 9,5 s;
  - falla si `Σ(narration_s + pause_s) > max_seconds` y nombra el bloque más largo;
  - no cambia la velocidad.
- [X] T027 [P] [US2] En `tests/integration/test_pitch_assemble.py`, pruebas de `check`:
  - `pauses` falla con una pausa de 1,0 s;
  - `cues` falla si menos del 90 % cumple ±0,5 s o si alguno es negativo;
  - la narración de un bloque se oye completa: el audio de la escena dura al menos `narration_s`.

### Implementación

- [X] T028 [US2] Cambiar `narrate` en `src/proyecto_modelos_lenguaje/pitch.py`: quitar el límite por `trim_s` y
  validar el total contra `max_seconds` con `pause_s`.
- [X] T029 [US2] Ampliar `check` en `src/proyecto_modelos_lenguaje/pitch.py` con `pauses`, `cues` y
  `no_steps_text`, según `contracts/pitch-cli.md`. Lee `sincronia.json` y la salida de `assemble` guardada en
  `video/pitch/borrador/montaje.json`.
- [X] T030 [US2] Si la suma pasa de 60 s, `validate` y `narrate` sugieren qué bloque recortar (el de mayor
  `narration_s`), en `src/proyecto_modelos_lenguaje/pitch.py`.

**Checkpoint**: con datos sintéticos, las pausas y la duración cumplen y `check` las mide. T026–T027 en verde.

---

## Phase 5: User Story 3 - Producir la v2 sin perder la v1 ni salirse del presupuesto (Priority: P3)

**Goal**: estimar, sondear, generar, revisar, montar en borrador y publicar con tope de gasto. La web muestra la v1
hasta `publish`.

**Independent Test**:

- `pml pitch generate --dry-run --json` muestra 8 planos, segundos, USD y lo que queda, sin red;
- con planos sin aprobar, `publish` se niega y `web/public/media/pitch-valeria.mp4` no cambia.

### Pruebas (escribir primero; deben fallar)

- [X] T031 [P] [US3] En `tests/unit/test_pitch_generate.py`, pruebas de `probe` con `MockTransport`:
  - si el catálogo no trae el slug y el modo responde `403 model_unavailable`, da `available: false` y código 3;
  - si los modos responden 400/422, da `available: true` y código 0;
  - nunca envía un cuerpo válido (sin cobro).
- [X] T032 [P] [US3] En `tests/unit/test_pitch_generate.py`, pruebas de `generate` por plano:
  - `--shot` y `--scene`;
  - el modo correcto por plano;
  - `source = frame:plano-03a` extrae el último cuadro del clip aprobado y lo sube una vez, y falla si 03a no está
    `aprobada`;
  - el tope suma v1, calibraciones y v2 con el precio del modelo;
  - `--dry-run` desglosa por plano;
  - se niega a generar si `probe` da `available: false`;
  - la clave no aparece en el registro ni en la salida.
- [X] T033 [P] [US3] En `tests/unit/test_pitch_generate.py`, prueba de `--calibrate --mode reference|text`:
  - escribe `calibracion/calibracion-<modo>.mp4`;
  - suma a `gasto.json`;
  - reporta `fields` y `problems` como en la 028.
- [X] T034 [P] [US3] En `tests/integration/test_pitch_assemble.py`, pruebas de publicación:
  - `assemble` escribe en `video/pitch/borrador/` por defecto;
  - `publish` falla si hay planos sin aprobar o si `check` no está `ok`, y no toca `web/public/media/`;
  - con todo aprobado, copia el `.mp4`, el `.vtt` y el `.webp`, regenera `web/src/data/pitch.ts` con
    `PITCH_SCRIPT_VERSION = "1.2.0"` y lista los archivos de la v1 por borrar.

### Implementación

- [X] T035 [US3] Implementar `probe(config, client)` en `src/proyecto_modelos_lenguaje/pitch_higgsfield.py`, según
  `contracts/pitch-cli.md`: catálogo y cuerpo inválido por modo usado, con `alternatives` de los demás `[models.*]`.
- [X] T036 [US3] Adaptar `generate` y `calibrate` en `src/proyecto_modelos_lenguaje/pitch.py`:
  - por plano, con `--shot`, `--scene` y `--mode`;
  - resolución de `frame:` (último cuadro con ffmpeg `-sseof -0.1`);
  - sondeo previo;
  - costo por modelo;
  - Idempotency-Key `plano-0Nx:<block_hash>:<seed>`;
  - clips en `video/pitch/planos/`.
- [X] T037 [US3] Implementar `publish(root, media_dir, web_data)` en `src/proyecto_modelos_lenguaje/pitch.py` y
  cambiar la salida por defecto de `assemble` a `video/pitch/borrador/`.
- [X] T038 [US3] Agregar a `src/proyecto_modelos_lenguaje/cli.py`:
  - los comandos `pml pitch probe` y `pml pitch publish`;
  - en `generate`, las opciones `--shot` (repetible) y `--mode` para `--calibrate`.
- [X] T039 [US3] Revisar `tests/e2e/test_pitch.py` y `tests/e2e/conftest.py`: la web no cambia de código. Basta
  confirmar que `skip_pitch_video` sigue aplicando y que las 9 pruebas del pitch pasan con el nuevo `pitch.ts`.

### Producción (requiere T001–T038)

- [X] T040 [US3] (Decidido el 2026-11-26: MAGI-2 si responde y, si no, Kling 4.0; ver research R1.)
  **[EXTERNO, sin costo]** Correr `uv run pml pitch probe --json` y registrar el resultado en
  `specs/029-pitch-escenas-sincronizadas/quickstart.md` §C.
  - Si `available: false`, **detenerse** y pedir al integrante que elija entre esperar a MAGI-2 y cambiar
    `[pitch].model` a `kling4` (research R1).
  - Si cambia el modelo, enmendar `CONSTITUTION.md` (§3.7 y §10, versión 2.4.0) y el ADR 0033 en el mismo commit.
- [X] T041 [US3] **[EXTERNO, voz]** Correr `uv run pml pitch narrate`, luego `uv run pml pitch align --json`.
  Revisar `missing: []` y el total (≈ 50 s).
- [X] T042 [US3] **[EXTERNO, gasta 0,64–1,50 USD]** Calibrar los modos `reference` y `text`
  (`uv run pml pitch generate --calibrate --mode reference` y `--mode text`). Confirmar los campos en
  `config/pitch.toml` `[models.<id>.fields]` y registrar en `research.md` R2.
- [X] T043 [US3] **[EXTERNO, gasta ~4,56 USD con MAGI-2 o ~10,70 con Kling 4.0]** Generar en este orden, con
  `--dry-run` previo y la autorización del integrante:
  1. `plano-01a`, `01b`, `02`, `03a`, `04` y `05`;
  2. revisar y aprobar `plano-03a`;
  3. `plano-03b` y `06`.
- [X] T044 [US1] Revisar cada plano con ffmpeg (cuadros cada 1 s):
  - los cuatro chequeos de la 028, más `cue_shown`;
  - anotar `anchors` en segundos del clip para los momentos `plano`;
  - marcar `aprobada` o `descartada` en `video/pitch/escenas.json`;
  - regenerar los descartados con `--shot` y otra semilla (dentro del tope).
- [X] T045 [US1] Montar y validar el borrador: `uv run pml pitch graphics`, `uv run pml pitch assemble --json` y
  `uv run pml pitch check video/pitch/borrador/pitch-valeria.mp4 --json`. Ver el borrador sin sonido (SC-005).
  Registrar duración, `delta_s`, pausas y gasto en `quickstart.md` §C.
- [X] T046 [US3] Con la aprobación del integrante, correr `uv run pml pitch publish`. En el mismo commit, borrar
  `video/pitch/escenas/escena-0N.mp4` de la v1 (queda en el historial).

**Checkpoint**: v2 publicada y v1 recuperable en Git. Gasto total de 20 USD o menos.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T047 [P] Completar `docs/decisions/0033-pitch-v2-sincronia.md`:
  - planos por escena, sincronía por palabra, gráficos del montaje, reajuste 0,8–1,25×, borrador y publicación;
  - el modelo usado y el motivo (MAGI-2 o alternativa);
  - costo real.
- [X] T048 [P] Actualizar `CONSTITUTION.md` §3.7 «Video pitch», solo si cambian sus reglas: duración por escena y
  gráficos del montaje como único texto legible. Agregar una fila en la tabla de versiones, PATCH o MINOR según el
  modelo.
- [X] T049 [P] Actualizar `docs/prompt_log.md` (§3.24: prompts por plano, semillas y regeneraciones),
  `video/pitch/RUNBOOK.md` (flujo v2: probe → narrate → align → graphics → generate → review → assemble → check →
  publish) y `README.md` (mención breve).
- [X] T050 [P] Marcar `video/pitch/cambios.md` como aplicado: una línea al inicio con la fecha y la versión 1.2.0.
- [X] T051 Correr `ruff check`, `ruff format`, `make check` y `make e2e` con `LANGSMITH_TRACING=false`. Registrar
  las cifras en `quickstart.md` §C.
- [ ] T052 Hacer commit a nombre de Robertto48, sin firmas de bot, con el código, la spec, el ADR, el registro y los
  clips (por LFS). Sin push ni PR hasta que el integrante lo pida.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias.
- **US1 (Phase 3)**: depende de Phase 2.
- **US2 (Phase 4)**: depende de Phase 2. Comparte `pitch.py` con US1, así que T028–T030 van después de T023.
- **US3 (Phase 5)**:
  - el código (T031–T039) depende de Phase 2 y puede avanzar en paralelo con US1 en archivos distintos
    (`pitch_higgsfield.py`, `cli.py`);
  - la producción (T040–T046) requiere US1, US2 y el código de US3.
- **Polish (Phase 6)**: al final. T052 cierra.

### Dentro de cada historia

- Pruebas primero, que deben fallar; luego la implementación.
- T019 → T020 → T023 (la línea de tiempo antes del montaje). T021 → T022.
- T040 → T041 → T042 → T043 → T044 → T045 → T046 (estrictamente en serie: gasto y revisión humana).

### Parallel Opportunities

- Setup: T002, T003 y T004.
- Foundational: T005, T006 y T007 (pruebas); T013 (prompts) en paralelo con T008–T010.
- US1: T015, T016 y T017 (pruebas); T021 (SVG) en paralelo con T019–T020.
- US2: T026 y T027.
- US3: T031–T034 (pruebas); T035 en paralelo con T019–T023, porque es otro archivo.
- Polish: T047–T050.

## Parallel Example: User Story 1

```bash
# Pruebas en paralelo (archivos distintos):
Task: "T015 pruebas de align en tests/unit/test_pitch_sync.py"
Task: "T017 pruebas de gráficos en tests/unit/test_pitch_graphics.py"
# Implementación en paralelo:
Task: "T019 align en src/proyecto_modelos_lenguaje/pitch_sync.py"
Task: "T021 SVG en video/pitch/graficos/"
```

## Implementation Strategy

### MVP First (User Story 1)

1. Phase 1 y Phase 2.
2. Phase 3 con datos sintéticos: el montaje sincronizado funciona y se prueba sin gastar.
3. **Parar y validar** con la salida `cues` de un montaje sintético.

### Incremental Delivery

1. Setup + Foundational: guion y registro v2.
2. US1: sincronía e iconos (sin red).
3. US2: ritmo y pausas (sin red).
4. Código de US3: probe, generate por plano, borrador y publish (sin red).
5. Producción, con gasto y revisión humana: probe → narración → calibración → planos → revisión → borrador →
   publish.

### Puertas de decisión del integrante

- **T040**: si MAGI-2 no está disponible, elegir modelo.
- **T043**: autorizar el gasto tras `--dry-run`.
- **T046**: aprobar la publicación que reemplaza la v1.
- **T052**: el commit. Push y PR solo a pedido.
