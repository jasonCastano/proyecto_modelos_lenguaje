---

description: "Tareas de la spec 030: imágenes de perfil y banner de Valer-IA"
---

# Tasks: Imágenes de perfil y banner de Valer-IA

**Input**: Design documents from `specs/030-imagenes-perfil-valeria/`

**Prerequisites**: plan.md, spec.md, research.md (R1–R9), data-model.md, contracts/whatsapp-images-cli.md, quickstart.md

**Tests**: el plan pide `tests/unit/test_whatsapp_images.py` (sin navegador ni red) para `check` y las fichas. Se
escriben antes de implementar esas funciones.

**Organization**: por historia de usuario. Reglas que aplican a todas las tareas:
- sin costo, sin red, sin claves y sin modelos de generación de imágenes (FR-010, FR-012);
- solo las skills `design` y `frontend-design` para el diseño; NO usar `ai-image-generation` ni las funciones de
  `design` que llaman a Gemini;
- sin logotipo ni marca de Manuelita (FR-006); la presentadora nunca como vocera de Manuelita (FR-007).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede correr en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 foto de perfil, US2 portadas, US3 recomendaciones

---

## Phase 1: Setup

**Purpose**: carpetas, versionado y recursos compartidos de diseño.

- [X] T001 Crear `docs/whatsapp/`, `docs/whatsapp/fuente/glifos/` y `docs/whatsapp/borrador/`; añadir
  `docs/whatsapp/borrador/` a `.gitignore` y `docs/whatsapp/*.png filter=lfs diff=lfs merge=lfs -text` a
  `.gitattributes` bajo un comentario «Spec 030: imágenes de perfil de Valer-IA» (R8).
- [X] T002 [P] Exportar como SVG independientes los glifos de caña, azúcar, etanol, energía y melaza de
  `web/src/components/brand/ProductGlyphs.tsx` a `docs/whatsapp/fuente/glifos/{cana,azucar,etanol,energia,melaza}.svg`,
  con el mismo `viewBox` y trazos, y el color fijo de su producto (R6).
- [X] T003 [P] Crear `docs/whatsapp/fuente/base.css`:
  - tokens de la paleta de R6 (`--cane #387c2b`, `--cane-deep #173512`, `--sugar #ffd200`, `--molasses #f6a01a`,
    `--ethanol #e86d1f`, `--power #b0bc22`, `--ink #14240f`, `--field #f5f7f3`);
  - `@font-face` de Archivo variable desde `../../../web/node_modules/@fontsource-variable/archivo/files/` (sin red);
  - reglas comunes: `html, body` sin márgenes, tamaño fijo por pieza, `data-safe` para los bloques de texto.

---

## Phase 2: Foundational (bloquea US1 y US2)

**Purpose**: el script `scripts/whatsapp_images.py` con catálogo, fichas, `check`, `approve` y `render`, según
`contracts/whatsapp-images-cli.md` y `data-model.md`.

### Pruebas primero

- [X] T004 Escribir `tests/unit/test_whatsapp_images.py` con raíz temporal (`tmp_path`, el script acepta la raíz por
  parámetro) e imágenes sintéticas creadas con Pillow. Casos:
  - `check` aprueba una pieza coherente;
  - `check` falla si el PNG no mide lo del catálogo, si el `sha256` de la ficha no coincide, si
    `reference_sha256` difiere, si `generative_model` no es `none`, si `cost_usd` no es 0, si una fuente no tiene
    licencia libre, si faltan `approved_by` o `approved_at`, y si una portada no registra `disclosure_in`;
  - `check` reporta las piezas sin aprobar sin fallar;
  - un PNG que es puntero LFS (`version https://git-lfs…`) se reporta como no descargado;
  - `approve` no copia nada si falta el borrador o no pasa las comprobaciones, y escribe PNG + ficha si pasa;
  - la ficha escrita se vuelve a leer igual (ida y vuelta);
  - la referencia con `real_person` o `brand_elements` distinto de `false` bloquea `render` y `approve`;
  - `contrast_ratio` da 21 para negro/blanco y 1 para colores iguales (WCAG 2.x).

### Implementación

- [X] T005 Crear `scripts/whatsapp_images.py` con:
  - el catálogo de `data-model.md` (`perfil` 640×640 → `valeria-perfil.png`; `linkedin` 1584×396 →
    `valeria-linkedin.png`; `facebook` 1640×624 → `valeria-facebook.png`; `whatsapp` 1920×1080 →
    `valeria-whatsapp-portada.png`), cada pieza con fuente HTML, zona segura de R2, escala máxima 1,15 y si es
    portada (`disclosure_in` obligatorio);
  - la validación de la referencia: existe, no es puntero LFS, `sha256` igual al de
    `docs/referencias/avatar_ingenio_manuelita.md` y ficha con `real_person: false` y `brand_elements: false`;
  - lectura y escritura de fichas con encabezado YAML (campos de `data-model.md`), usando PyYAML si ya está en el
    entorno y, si no, un lector mínimo de claves planas y listas, sin añadir dependencias.
- [X] T006 Implementar en `scripts/whatsapp_images.py` `contrast_ratio`, `check` y `approve` según el contrato
  (salida 0/1, `--json` con `ok` y `pieces[]`), hasta que T004 pase.
- [X] T007 Implementar `render` en `scripts/whatsapp_images.py`:
  - Playwright/Chromium (política Proactor en Windows, como `pitch_graphics.render_svgs`), viewport con la medida
    exacta de la pieza, `device_scale_factor` 1, espera a que carguen fuentes e imágenes;
  - mide en la página: escala de la referencia (caja renderizada de `img[data-ref]` frente a su tamaño natural, en
    ambos ejes y debe ser igual en los dos), cajas de `[data-safe]` dentro de la zona segura y contraste de cada
    `[data-text]` contra el color de `data-bg`;
  - guarda el PNG en `docs/whatsapp/borrador/` y, con Pillow, las vistas previas en
    `docs/whatsapp/borrador/revision/`: la foto en círculo a 48, 96 y 640 px; cada portada con un círculo gris donde
    la plataforma pone la foto de perfil, en escritorio y, para Facebook, el recorte central de teléfono (16:9).
  - errores claros si falta Chromium o `web/node_modules` (indicar `make dev`).
- [X] T008 `uv run ruff check scripts/whatsapp_images.py tests/unit/test_whatsapp_images.py`, `ruff format` y
  `LANGSMITH_TRACING=false uv run pytest tests/unit/test_whatsapp_images.py` en verde.

**Checkpoint**: el script funciona con piezas de prueba; ya se pueden diseñar las piezas reales.

---

## Phase 3: User Story 1 - Foto de perfil de Valer-IA (Priority: P1) 🎯 MVP

**Goal**: foto de perfil 640×640 aprobada en `docs/whatsapp/valeria-perfil.png` con su ficha.

**Independent Test**: la vista previa en círculo a 48 px deja ver el rostro; a 640 px es la misma presentadora del
video; sin texto ni logotipos (quickstart §A.1).

- [X] T009 [US1] Cargar la skill `design` (flujo «social photos») y `frontend-design`, y diseñar
  `docs/whatsapp/fuente/perfil.html` a 640×640:
  - `img[data-ref]` con `../../referencias/avatar_ingenio_manuelita.png`, recortada en cabeza y hombros, rostro en el
    80 % central del círculo inscrito, escala ≤ 1,15 e igual en ambos ejes (R3);
  - fondo de la referencia armonizado con la paleta: degradado suave de `--cane`/`--cane-deep` en los bordes y un
    anillo de color dentro del círculo (R4);
  - sin texto, logotipos ni marca de Manuelita (FR-002).
- [X] T010 [US1] `uv run python scripts/whatsapp_images.py render --piece perfil --json`; revisar las vistas previas
  de `docs/whatsapp/borrador/revision/` (círculo a 48/96/640) y ajustar `perfil.html` hasta cumplir SC-004.
- [X] T011 [US1] Mostrar al integrante la foto y las vistas previas y pedir su aprobación (FR-009). Solo con su
  aprobación: `uv run python scripts/whatsapp_images.py approve perfil --by "Roberto José Guerrero"`.

**Checkpoint**: la foto de perfil está lista para subirse a WhatsApp, LinkedIn y Facebook.

---

## Phase 4: User Story 2 - Portadas de LinkedIn, Facebook y WhatsApp (Priority: P2)

**Goal**: tres portadas aprobadas en `docs/whatsapp/` con su ficha y texto exacto; la declaración de IA va en el
texto del perfil (decisión del integrante, 2026-11-27).

**Independent Test**: en las vistas previas con la foto superpuesta (escritorio y teléfono), nombre y lema se ven
completos, sin errores y con contraste ≥ 4,5 (quickstart §A.2).

Texto común (R5), aprobado por el integrante en T015:
- «Valer-IA»;
- «Agentes de IA para la agroindustria de la caña: respuestas con fuente y planificación industrial»;
- (la frase de declaración se retiró de las imágenes por pedido del integrante; va en el texto del perfil)

- [X] T012 [P] [US2] Diseñar `docs/whatsapp/fuente/linkedin.html` a 1584×396 con `design` (flujo «banner design») y
  `frontend-design`: presentadora en un panel a la derecha (escala ≤ 1,15), texto en el tercio central-derecho
  dentro de la zona segura de R2, fuera del área de la foto de perfil abajo a la izquierda (≈ 0–568 × 200–396),
  glifos de producto como ritmo visual; cada bloque de texto con `data-safe`, `data-text` y `data-bg`.
- [X] T013 [P] [US2] Diseñar `docs/whatsapp/fuente/facebook.html` a 1640×624: texto en el centro de 1280×560 para
  sobrevivir al recorte de teléfono, presentadora a un lado, mismas reglas de T012.
- [X] T014 [P] [US2] Diseñar `docs/whatsapp/fuente/whatsapp.html` a 1920×1080: la foto de perfil de WhatsApp Business
  queda centrada abajo, así que el texto va en la mitad superior del centro de 1600×760; mismas reglas de T012.
- [X] T015 [US2] `uv run python scripts/whatsapp_images.py render --piece linkedin facebook whatsapp --json`;
  revisar las vistas previas, ajustar hasta que todo el texto quede en su zona segura con contraste ≥ 4,5 y sin
  errores; mostrar al integrante las portadas y el texto, y pedir su aprobación.
- [X] T016 [US2] Solo con la aprobación del integrante: `approve linkedin`, `approve facebook` y `approve whatsapp`
  con `--by "Roberto José Guerrero"`.

**Checkpoint**: las cuatro piezas están aprobadas.

---

## Phase 5: User Story 3 - Recomendaciones para el bot de WhatsApp (Priority: P3)

**Goal**: el integrante sabe qué imágenes producir después y cómo subir las actuales.

**Independent Test**: `docs/whatsapp/README.md` lista cada pieza con su destino y la tabla de recomendaciones con
uso, contenido y prioridad.

- [X] T017 [P] [US3] Escribir `docs/whatsapp/README.md`:
  - tabla de piezas (archivo, medidas, dónde subirla, qué la tapa en cada plataforma);
  - textos sugeridos para «Info» de WhatsApp y para la descripción de LinkedIn y Facebook, con la declaración de IA;
  - nota de que la portada solo existe en WhatsApp Business;
  - las nueve recomendaciones de la spec (sección «Recomendaciones») con su prioridad, más las reglas comunes;
  - cómo reexportar una pieza (`render` → revisión → `approve`).

---

## Phase 6: Polish & Cross-Cutting

- [X] T018 [P] Enmendar `CONSTITUTION.md` a 2.5.0: en §10 una regla «Imágenes de perfil de Valer-IA (spec 030)»
  (solo composiciones de la imagen de referencia con ficha, sin modelos generativos, sin marca de Manuelita,
  declaración de IA en el texto del perfil, ficha y aprobación humana por pieza, costo 0) y su fila en el historial
  («Requiere la aprobación de ambos integrantes»).
- [X] T019 [P] Escribir `docs/decisions/0034-imagenes-perfil-valeria.md` (contexto, decisión de R1/R4, alternativas
  descartadas de R1 y consecuencias), en el formato de `docs/decisions/0033-pitch-v2-sincronia.md`.
- [X] T020 [P] Enlazar `docs/whatsapp/` desde `README.md`, en la sección del canal de WhatsApp.
- [X] T021 `uv run python scripts/whatsapp_images.py check --json` con `ok: true` y cuatro piezas aprobadas (SC-001,
  SC-005); `LANGSMITH_TRACING=false make check` en verde.
- [X] T022 Revisar `specs/030-imagenes-perfil-valeria/quickstart.md` contra lo implementado, marcar las tareas en
  este archivo y dejar SC-002 (5 personas) como validación pendiente del integrante.
- [X] T023 Commit solo con autorización explícita del integrante, como Robertto48, sin `Co-authored-by` ni
  «Generated with»: `feat(docs): imágenes de perfil y portadas de Valer-IA (spec 030)`.

---

## Phase 7: Ampliación del 2026-11-27 — tarjetas del bot (US4) y stickers (US5)

- [X] T024 [US5] Dibujar a Valer-IA en caricatura en `docs/whatsapp/fuente/personaje.js` (insignia, poses,
  ojos, extras, borde troquelado redondeado) y la página `fuente/sticker.html?id=…` con animaciones de 2 s.
- [X] T025 Ampliar `scripts/whatsapp_images.py`: catálogo con tarjetas, stickers e ícono; captura cuadro a cuadro
  y WebP animado ≤ 500 KB; ícono 96×96 ≤ 50 KB; contraste solo en portadas y tarjetas; escala solo donde se usa
  la referencia; vistas previas de cuadros sobre los fondos del chat.
- [X] T026 Ampliar `tests/unit/test_whatsapp_images.py` (catálogo, sticker animado, peso máximo, tarjetas sin
  referencia).
- [X] T027 [P] [US4] Diseñar `fuente/tarjeta.css` y las tarjetas `bienvenida`, `perfiles`, `guia`,
  `sin-evidencia`, `fuera-de-servicio`, `plantilla-planificacion`, `estado-consejo` y `estado-novedad`.
- [X] T028 [US4] Generar `fuente/qr-repositorio.svg` en local (pendiente de autorizar `uvx segno`) y exportar
  `qr-repositorio`.
- [X] T029 Exportar tarjetas y stickers, revisar vistas previas, pedir la aprobación del integrante y publicar con
  `approve`.
- [X] T030 Actualizar `docs/whatsapp/README.md` (tarjetas, stickers, cómo cargarlos), ADR 0034 y la regla de §10
  (ilustración propia en código para los stickers); `check` y `make check` en verde.

## Phase 8: Ampliación US6 — audios de los stickers con la voz de Valer-IA (Priority: P3)

**Goal**: ocho audios aprobados, uno por sticker con frase, con la voz oficial del agente (Phonon, «Rebeca»), en
`docs/whatsapp/stickers/audios/`.

**Independent Test**: `check --json` lista los 8 audios aprobados, cada uno en OGG/Opus mono de 48 kHz, de 5 s o
menos y con su ficha. Al escucharlos en un teléfono se oye la frase completa, con la voz del chat de la web y un
volumen parejo.

### Preparación

- [X] T031 Crear la rama `030-audios-stickers` con `git switch -c`, llevando los cambios de spec y plan sin
  commitear. La rama parte de `031-frontend-profesional-valeria` (PR #87 abierto), no de `main`: la 031 sube la
  constitución a 2.6.0 y esta ampliación la lleva a 2.7.0. Es el mismo criterio con el que la 030 partió de la
  029. El PR de esta rama depende del #87.
- [X] T032 [P] Añadir `docs/whatsapp/**/*.ogg filter=lfs diff=lfs merge=lfs -text` a `.gitattributes`, junto a
  las reglas de `docs/whatsapp/**/*.png` y `*.webp`. `docs/whatsapp/borrador/` ya está en `.gitignore`.

### Pruebas primero (sin modelo ni red: `FakeSynthesizer` + PyAV)

- [X] T033 [P] [US6] En `tests/unit/test_whatsapp_images.py`, probar el catálogo de audios:
  - exactamente 8 piezas `audio-<nombre>`;
  - ninguna para `pulgar`;
  - el `text` de cada una es la frase exacta de la tabla de `data-model.md`;
  - cada `sticker` asociado existe en el catálogo de stickers.
- [X] T034 [P] [US6] En `tests/unit/test_whatsapp_images.py`, probar el acabado con una señal sintética de numpy
  (silencio + tono + silencio):
  - el silencio de los extremos se recorta, con un umbral de −45 dBFS en ventanas de 10 ms y 30 ms de margen;
  - quedan 150 ms de silencio a cada lado;
  - el RMS queda en −20 dBFS ± 1 y el pico ≤ −1 dBFS.
- [X] T035 [P] [US6] En `tests/unit/test_whatsapp_images.py`, probar la codificación: el archivo resultante es
  OGG/Opus, «1 canal, 48 kHz», con la duración esperada (±50 ms), leído de vuelta con PyAV.
- [X] T036 [P] [US6] En `tests/unit/test_whatsapp_images.py`, probar que `render` rechaza un audio de más de
  5,0 s (salida 1, sin escribir el borrador) y que, si la voz no está disponible (`VoiceUnavailableError`), sale
  con 1 sin escribir nada.
- [X] T037 [P] [US6] En `tests/unit/test_whatsapp_images.py`, probar `approve` y `check` de un audio en un
  `tmp_path`:
  - `approve` copia el `.ogg` a `docs/whatsapp/stickers/audios/` (crea la carpeta) y escribe la ficha con todos
    los campos de `data-model.md`;
  - `check` falla si cambia el `sha256`, si `duration_s > 5.0`, si `codec ≠ opus`, si falta `approved_by` o si
    falta `attribution`;
  - un audio sin aprobar aparece como pendiente sin que `check` falle.

### Implementación

- [X] T038 [US6] En `scripts/whatsapp_images.py`:
  - añadir el tipo de pieza `audio` y las ocho entradas `audio-<nombre>` con `text`, `speech_text` opcional,
    archivo `valeria-<nombre>.ogg` y sticker asociado (`data-model.md`);
  - añadir el alias `audios` para `--piece`;
  - definir las constantes `AUDIO_DIR = OUT_DIR / "stickers" / "audios"`, `AUDIO_DRAFT_DIR = DRAFT_DIR / "audios"`
    y `AUDIO_MAX_SECONDS = 5.0`.
- [X] T039 [US6] En `scripts/whatsapp_images.py`, implementar el acabado (R12): recorte de silencio, relleno de
  150 ms, normalización a −20 dBFS RMS con el pico limitado a −1 dBFS, y la medición de duración, RMS y pico. Solo
  numpy.
- [X] T040 [US6] En `scripts/whatsapp_images.py`, implementar la codificación a OGG/Opus con PyAV: remuestreo de
  la tasa de la voz (24 kHz) a 48 kHz, mono, `libopus` a 32 kbit/s. No llamar a `ffmpeg` por `subprocess`.
- [X] T041 [US6] En `scripts/whatsapp_images.py`, conectar `render` para las piezas de audio:
  - no abrir Chromium;
  - usar `VoiceService` (`proyecto_modelos_lenguaje.voice.engine`) con `config/voice.toml` y `load_dotenv()`;
  - poner `HF_HUB_OFFLINE=1` si el modelo ya está en la caché;
  - sintetizar `speech_text`, aplicar el acabado y escribir `docs/whatsapp/borrador/audios/<archivo>.ogg`;
  - reportar `duration_s`, `rms_dbfs` y `peak_dbfs`;
  - salir con 1 si la voz no está (con el detalle de `--check`) o si un audio pasa de 5 s.

  Permitir inyectar el sintetizador para las pruebas.
- [X] T042 [US6] En `scripts/whatsapp_images.py`, conectar `approve` y `check` para los audios: la ficha y sus
  reglas de `data-model.md`, con estos valores:
  - `voice: Rebeca`, `voice_id: Sx8m6WdXBG06zwZT`;
  - `tts_model: gradium/phonon-40m-es`, `tts_quant: q8_0`, `engine: ptts <versión instalada>`;
  - `license: CC BY-NC 4.0 (modelo y voces); MIT/Apache-2.0 (motor)` y la `attribution` a Phonon (Gradium);
  - `cost_usd: 0`.

  La regla `generative_model: none` sigue solo para las imágenes. Actualizar el docstring del módulo.
- [X] T043 [US6] Correr `LANGSMITH_TRACING=false uv run pytest tests/unit/test_whatsapp_images.py` y
  `uv run ruff check` / `ruff format --check`, todo en verde.

### Producción y aprobación (requiere el modelo de voz en el equipo del integrante)

- [X] T044 [US6] Con `HF_HUB_OFFLINE=1 uv run python scripts/whatsapp_images.py render --piece audios --json`,
  generar los 8 borradores y confirmar que todos duran ≤ 5 s. Si alguno pronuncia o entona mal, ajustar solo su
  `speech_text` en el catálogo y volver a generarlo.
- [X] T045 [US6] Pedir al integrante que escuche los 8 borradores (quickstart E: frase reconocible sin ver el texto,
  voz del chat web, sin cortes, volumen parejo) y que envíe uno a un chat de prueba de WhatsApp (SC-008,
  SC-009). No aprobar nada sin su respuesta.
- [X] T046 [US6] Publicar cada audio aprobado con `approve audio-<nombre> --by "<integrante>"` y comprobar con
  `check --json` que los 8 aparecen aprobados (SC-007).

### Documentación y gobierno

- [X] T047 [P] [US6] Actualizar `docs/whatsapp/README.md`:
  - tabla de audios (archivo, frase, sticker, duración);
  - cómo enviarlos como nota de voz o unirlos al sticker en un video (fuera del alcance);
  - la atribución: «Voz sintetizada con Phonon (Gradium), modelo y voces CC BY-NC 4.0, uso académico no
    comercial».
- [X] T048 [P] Enmendar `CONSTITUTION.md` a 2.7.0. En la regla de §10 «Imágenes de perfil de Valer-IA», añadir los
  audios de los stickers (`docs/whatsapp/stickers/audios/`):
  - solo la voz oficial del agente (spec 016), sintetizada en local y sin costo;
  - sin clonar ni imitar voces reales;
  - licencia CC BY-NC 4.0 con atribución en la ficha y el README, y uso académico no comercial;
  - ficha y aprobación de un integrante por audio, verificadas por `check`.

  Agregar la fila 2.7.0 en el historial («Requiere la aprobación de ambos integrantes») y actualizar la versión y
  la fecha en el encabezado y al pie.
- [X] T049 [P] Escribir `docs/decisions/0036-audios-stickers-valeria.md` (contexto, decisión de R12/R13,
  alternativas descartadas: MP3/M4A, WAV, `ffmpeg` por `subprocess`, otra voz; consecuencias), en el formato de
  `docs/decisions/0034-imagenes-perfil-valeria.md`.
- [X] T050 `uv run python scripts/whatsapp_images.py check --json` con `ok: true` y `LANGSMITH_TRACING=false make
  check` en verde. Revisar `quickstart.md` (sección E) contra lo implementado y marcar T031–T050 en este archivo.
- [X] T051 Commit solo con autorización explícita del integrante, como Robertto48, sin `Co-authored-by` ni
  «Generated with»: `feat(docs): audios de los stickers con la voz de Valer-IA (spec 030)`. El PR también solo
  con su autorización.

---

## Dependencies & Execution Order

- **Setup (T001–T003)** → **Foundational (T004–T008)** → **US1 (T009–T011)** → **US2 (T012–T016)**.
- US2 necesita el script (Phase 2) y conviene tener la foto aprobada (US1), porque las vistas previas superponen la
  foto de perfil.
- **US3 (T017)** no depende del script; puede escribirse en cualquier momento después de T001.
- **Polish**: T018–T020 en paralelo cuando haya piezas aprobadas; T021 → T022 → T023 al final.
- Dentro de Phase 2: T004 antes de T006; T005 antes de T006 y T007.
- **US6 (Phase 8)**:
  - no depende de US1–US5, salvo que los stickers asociados ya existen;
  - orden: T031 → T032 → pruebas T033–T037 (en paralelo, deben fallar antes de implementar) →
    T038 → T039 ‖ T040 → T041 → T042 → T043 → T044 → T045 (integrante) → T046 → T047 ‖ T048 ‖ T049 → T050 → T051;
  - T044–T046 necesitan el modelo de voz en la caché del integrante. El resto corre sin modelo ni red.

## Parallel Example

```text
Setup:   T002 (glifos) ‖ T003 (base.css)
US2:     T012 (LinkedIn) ‖ T013 (Facebook) ‖ T014 (WhatsApp) → T015 → T016
Polish:  T017 ‖ T018 ‖ T019 ‖ T020
US6:     T033 ‖ T034 ‖ T035 ‖ T036 ‖ T037 → T038 → T039 ‖ T040 → T041 → T042
         T047 ‖ T048 ‖ T049 (después de la aprobación T046)
```

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1. La foto de perfil aprobada ya le da identidad al bot de WhatsApp.
2. **Incremento 2**: US2, las tres portadas.
3. **Incremento 3**: US3 y Polish (constitución 2.5.0, ADR, README, verificación y commit autorizado).

4. **Incremento US6**: primero un solo audio (`audio-hola`, T044 con `--piece audio-hola`) para validar la voz y
   WhatsApp; luego los ocho, la documentación y la constitución 2.7.0.

Las aprobaciones (T011, T015, T016, T045) son del integrante: no se marca una pieza como aprobada sin su respuesta.
