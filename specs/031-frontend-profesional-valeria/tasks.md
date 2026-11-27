---

description: "Tareas de la spec 031: frontend profesional de Valer-IA"
---

# Tasks: Frontend profesional de Valer-IA, plataforma de agentes de Manuelita

**Input**: `specs/031-frontend-profesional-valeria/` (spec, plan, research R1–R10, data-model, contracts/ui-contract,
quickstart)

**Tests**: el plan exige que Vitest y e2e sigan en verde (FR-011, SC-005). Se añade una prueba de créditos de fotos
(data-model) y se ajustan las existentes cuando cambian textos o estructura, en la misma tarea.

**Reglas para todas las tareas**:
- seguir la skill `design-taste-frontend` (`S=~/.claude/skills/design-taste-frontend`): leer `copy.md`,
  `copy-voice.md`, `system.md`, `layout-v4.md` y `sections.md` antes de la primera sección;
- NO copiar archivos del kit al repositorio (research R2): las reglas se reimplementan en `web/src/styles/`;
- Archivo como única familia (R4); paleta de R3; sin violeta; sin el logotipo de Manuelita;
- cifras solo del optimizador;
- declaración de IA y proyecto académico junto al video y en el pie;
- AA, foco visible, 320–1920 px sin scroll horizontal, «reducir movimiento».

## Format: `[ID] [P?] [Story] Description`

---

## Phase 1: Setup

- [X] T001 Leer las referencias de la skill (`$S/references/copy.md`, `copy-voice.md`, `system.md`,
  `layout-v4.md`, `sections.md`, `photos.md`, `motion.md`, `moments.md`, `cards.md`, `diagrams.md`) y escribir en
  `specs/031-frontend-profesional-valeria/copy.md` la ficha de hechos, la tarjeta de voz y **todo el texto** de la
  entrada por sección (R6). Reglas de copy:
  - el h1 nombra la categoría y el público;
  - un dato duro en la primera pantalla («26 herramientas, 5 perfiles, cada dato con su fuente»);
  - un sustantivo en cada h2;
  - botones con verbo y objeto;
  - tono cálido en primera persona del plural inspirado en manuelita.com, sin copiar sus frases.
  Pasar `node $S/scripts/copy-lint.mjs specs/031-frontend-profesional-valeria/copy.md --kind software` sin FAIL.
- [X] T002 Armar el gate: `node $S/scripts/gate.mjs --start http://127.0.0.1:8000/ --kind software --category
  "plataforma de agentes de IA" --primary "Habla con Valer-IA"` (estado en `.taste-skill/`, ya ignorado por Git).
- [X] T003 [P] Buscar y elegir 6 a 10 fotos sustitutas con `node $S/scripts/photos.mjs search` para: campo de caña,
  cosecha de caña, cristales de azúcar, uva de mesa en la vid, mejillones y plantación de palma (más bioetanol o
  energía si aparece una buena). Para cada candidata:
  - verla al 100 % y descartar marcas, letreros legibles y personas reconocibles;
  - preferir CC0 o dominio público.
  Descargar con `photos.mjs fetch`, reducir a WebP de 1600 y 800 px (≤ 200 KB) en `web/public/media/fotos/`, y
  escribir `web/public/media/fotos/CREDITOS.md` con autor, archivo, licencia y URL.
- [X] T004 [P] Añadir `web/public/media/fotos/** filter=lfs diff=lfs merge=lfs -text` a `.gitattributes`.

---

## Phase 2: Foundational (bloquea todas las historias)

- [X] T005 Reescribir `web/src/styles/tokens.css` con la paleta de R3 (`--p-bg #f5f7f3`, `--p-surface #ffffff`,
  `--p-ink #14240f`, `--p-muted #4b5747`, `--p-accent`/`--p-action #497536` con tinta `#f5f7f3`, inversos
  `#14240f`/`#21301c`, `--leaf-red #d64729`, `--leaf-orange #f39200`, `--leaf-yellow #ffd100`). Reglas:
  - conservar los colores de producto de la spec 026 con su significado;
  - escala tipográfica de `layout-v4.md` (h1 del hero 72/40);
  - rejilla de 12 columnas con `.wrap` de bordes iguales y radios `soft`;
  - alturas por pantalla (`--h: 1|2`).
- [X] T006 Reescribir `web/src/styles/global.css`:
  - tipografía Archivo (titulares `wdth` 112–125 y peso 500, texto 100, cifras condensadas con `tabular-nums`);
  - un estilo de botón `solid` (verde con tinta clara) y su secundario;
  - una tarjeta;
  - capa de movimiento de `motion.md`: tarjeta enlazada sube 2 px, foto con zoom 1,02 dentro de su marco, botón
    que responde al hover y al clic, subrayado que se dibuja;
  - foco visible y enlace de salto;
  - `prefers-reduced-motion: reduce`, que deja todo quieto y visible.
  Retirar de `web/package.json` las fuentes Bricolage y Public Sans si ya no se importan.
- [X] T007 Actualizar `web/index.html`:
  - `<html lang="es" data-type="software" data-radius="soft" data-buttons="solid" data-motion="on">`;
  - metas `page-type` y `site-kind` (`software`), `description`, `og:*` y `theme-color #14240f`.
- [X] T008 [P] Crear `web/src/data/products.ts` (data-model: `key` ∈ cane, sugar, ethanol, power, molasses, palm,
  grape, mussel; `name` como lo nombra el sitio oficial; `platform`; `color` token; `glyph`; `photo`) y
  `web/src/data/photos.ts` (`id`, `src`, `alt`, `author`, `license` ∈ {CC0, dominio público, CC BY, CC BY-SA},
  `sourceUrl`, `subject`, `standIn: true`) desde `CREDITOS.md`.
- [X] T009 [P] Escribir `web/src/test/photos.test.ts`: falla si una foto no tiene autor, licencia permitida o URL, o
  si su archivo no está en `web/public/media/fotos/`.
- [X] T010 Reescribir la carcasa en `web/src/components/shell/`:
  - `AppShell.tsx` con `NavCentre` (marca «Valer-IA» como wordmark, enlaces a las cuatro áreas, menú a pantalla
    completa en teléfono con estado anunciado);
  - `FooterStatement` (frase de cierre, enlaces, declaración de proyecto académico con IA y no canal oficial de
    Manuelita, y una línea de créditos de fotos generada desde `photos.ts`).
  Retirar `CaneRail.tsx` si deja de usarse. Ajustar `web/src/test/App.test.tsx`.

**Checkpoint**: la web compila con el sistema nuevo; `npx vitest run` en verde.

---

## Phase 3: User Story 1 - Entrada que presenta la plataforma como producto (P1) 🎯 MVP

**Goal**: la entrada de R6, una sección por pantalla, con el video pitch como visual del hero.

**Independent Test**: quickstart §B (`GATE: PASS`) y §E (4 de 5 personas explican qué es, para quién y cómo empezar).

- [X] T011 [US1] `web/src/components/home/Hero.tsx` (hero `split` de `layout-v4.md`, `data-enter`):
  - línea de aviso (proyecto académico con IA, no canal oficial);
  - h1, lead y botones «Habla con Valer-IA» → `/agente` y «Ver la planificación» → `/planificacion`;
  - el visual de 628×716 es `PitchVideo` (sin cambiar su comportamiento: saltable, sin repetirse en la sesión,
    sin reproducción automática con movimiento reducido);
  - una tarjeta flotante con un dato vivo de `/api/health` (unidades con cita del corpus o herramientas
    disponibles).
  Retirar `PlatformHero.tsx`.
- [X] T012 [US1] `web/src/components/home/AppFrame.tsx`: una ventana de la app en grande, con la lista de
  conversaciones a la izquierda y una respuesta abierta a la derecha, con citas `[U#]` y su fuente desplegada.
  HTML vivo con los componentes del chat y datos de ejemplo reales del corpus; sin capturas de pantalla.
- [X] T013 [P] [US1] `web/src/components/home/ProfilesBento.tsx`: los cinco perfiles de
  `profileSuggestions.ts` en una rejilla bento, cada uno con su glifo, su color, qué puede preguntar y un enlace
  que abre el agente con ese perfil. Retirar `ProfileLedger.tsx`.
- [X] T014 [P] [US1] `web/src/components/home/Businesses.tsx`: rejilla (sin carrusel) de las cuatro plataformas:
  caña (azúcar, bioetanol, energía), palma, frutas y hortalizas (uva) y acuicultura (mejillones).
  - foto sustituta de `photos.ts` con `alt`, `data-source="stand-in"` y sin pie de foto;
  - glifo y color de `products.ts`.
- [X] T015 [P] [US1] `web/src/components/home/Statement.tsx`: el momento `letters-assemble` de `moments.md`
  («Cada dato, con su fuente.»), reimplementado:
  - CSS y un `IntersectionObserver` dentro de su sección;
  - con movimiento reducido, la frase queda quieta y visible.
- [X] T016 [P] [US1] `web/src/components/home/PlanningBand.tsx` (`dark-band`):
  - diagrama de `diagrams.md` (un insumo «caña», un proceso «optimizador» y tres carriles: azúcar, etanol,
    energía), con pulsos que recorren las líneas en 2,5–4 s y un botón de pausa;
  - sin cifras inventadas;
  - botón «Abre la planificación».
- [X] T017 [P] [US1] `web/src/components/home/Guarantees.tsx` (reescrito): cuatro tarjetas (cita cada dato, cifras
  calculadas en código, pide permiso antes de guardar, dice cuando no sabe), al modo de las cuatro tarjetas de
  sostenibilidad del sitio oficial.
- [X] T018 [P] [US1] `web/src/components/home/EvidenceTools.tsx`:
  - íconos reales a color de las herramientas que usa el proyecto (Qdrant, DeepSeek, LangGraph, FastAPI,
    WhatsApp, OpenClaw) con `node $S/scripts/icons.mjs`, guardados en `web/public/media/iconos/` con su licencia;
  - enlace a `/evidencia`.
- [X] T019 [P] [US1] `web/src/components/home/Faq.tsx` (5 preguntas del copy) y `CloseType.tsx` (cierre tipográfico
  con la acción principal).
- [X] T020 [US1] Recomponer `web/src/pages/Home.tsx` en el orden de R6 (`main > section` con `id` y h2 primero).
  Mover `RagConsole` y `LimitsNote` a `/evidencia` (T028) y enlazarlos desde la sección de evidencia.
  Ajustar `web/src/test/HomePage.test.tsx` y `PitchVideo.test.tsx`.
- [X] T021 [US1] Ajustar `tests/e2e/test_platform.py`, `test_pitch.py`, `test_ask.py` y `test_demo.py` a la
  estructura nueva (mismos comportamientos, selectores o textos nuevos).
- [X] T022 [US1] Pasar el gate sobre la entrada con `make app` corriendo: `node $S/scripts/gate.mjs
  http://127.0.0.1:8000/`, hasta tres rondas. Corregir cada FAIL o registrar su exención con el motivo en
  `.taste-skill/waivers.json`. Exenciones previstas (plan, Complexity Tracking): Archivo en lugar de la pareja
  repartida y kit no copiado.

**Checkpoint**: la entrada sola ya presenta el producto (MVP).

---

## Phase 4: User Story 2 - Conversar con el agente en una interfaz clara (P1)

**Goal**: la vista del agente con el sistema nuevo y la misma funcionalidad.

**Independent Test**: quickstart §E (perfil Cliente B2B, pregunta y fuente abierta en < 2 min) y e2e de chat,
dictado y voz en verde.

- [X] T023 [US2] Reestilizar `web/src/pages/Agent.tsx`, `components/ChatView.tsx`, `components/agent/*` y
  `AgentAvatar.tsx`:
  - conversación a ancho de lectura (≤ 72 ch);
  - perfil activo con su color y glifo (`ProfilePicker`, `ProfileNotice`);
  - citas como enlaces;
  - `SourcesPanel` lateral en escritorio y hoja inferior en teléfono.
- [X] T024 [US2] Reestilizar `components/ApprovalCard.tsx`: se distingue de la conversación (borde rojo
  anaranjado, título «Necesito tu permiso») y explica qué pasará con «SÍ» y con «NO». Ajustar
  `ApprovalCard.test.tsx`.
- [X] T025 [P] [US2] Reestilizar `MicButton.tsx`, `VoiceControls.tsx`, `QuickReplies.tsx`, `WelcomeMessage.tsx` y
  `DemoBanner.tsx` con los botones y tarjetas del sistema (objetivos ≥ 44 px).
- [X] T026 [US2] Ajustar `web/src/test/{AgentPage,ChatView,ChatViewDictation,ChatViewVoice,Valeria}.test.tsx`,
  `tests/e2e/test_chat.py` y `test_dictation.py` si cambian textos o roles.

---

## Phase 5: User Story 3 - Planificación y evidencia al mismo nivel (P2)

**Goal**: consola de planificación y evidencia con el sistema nuevo.

**Independent Test**: escenario «caña −15 %» y traza del turno legibles a 360 px sin scroll horizontal (quickstart §C).

- [X] T027 [P] [US3] Reestilizar `web/src/pages/Planning.tsx` y `components/planning/*`:
  - `CaneFlow` con los colores de producto fijos;
  - `CommitmentLedger` y `ComparisonView` con cifras condensadas tabulares;
  - `ScenarioForm` con campos del sistema;
  - `ProposalDialog` con la confirmación en dos pasos intacta.
  Ajustar `CaneFlow.test.tsx`, `PlanningPage.test.tsx`, `ScenarioForm.test.tsx` y `ProposalDialog.test.tsx`.
- [X] T028 [P] [US3] Reestilizar `web/src/pages/Evidence.tsx` y `components/evidence/*` (catálogo, traza,
  servicios, evaluaciones), y recibir `RagConsole` y `LimitsNote` desde la entrada (T020). Ajustar
  `EvidencePage.test.tsx` y `RagConsole.test.tsx`.
- [X] T029 [US3] Capturas con `node $S/scripts/shoot.mjs` de `/agente`, `/planificacion` y `/evidencia` a 1440, 1024,
  768 y 390. Revisarlas contra el checklist de la skill: bordes iguales, nada cortado, colores fijos.

---

## Phase 6: User Story 4 - Identidad coherente con los productos (P2)

**Goal**: cada producto con su color y glifo en todas las áreas; sin el logotipo; declaración visible.

**Independent Test**: revisión de las cuatro áreas (SC-006): 0 logotipos de Manuelita y la declaración visible en
la entrada y el pie.

- [X] T030 [US4] Usar `products.ts` como única fuente de color y glifo en entrada, agente, planificación y
  evidencia. Añadir a `web/src/test/ProductGlyphs.test.tsx` una prueba de que cada producto tiene color y glifo.
- [X] T031 [US4] Revisar las cuatro áreas: sin el logotipo de Manuelita ni frases que la presenten como canal
  oficial; declaración junto al video y en el pie. Agregar la comprobación a `tests/e2e/test_platform.py`.

---

## Phase 7: Polish & Cross-Cutting

- [X] T032 [P] Enmendar `CONSTITUTION.md` a 2.6.0, §3.7:
  - colores del logotipo;
  - fotos de stock con licencia libre citadas (sustitutas, nunca presentadas como de Manuelita);
  - un momento animado;
  - la skill `design-taste-frontend` con su kit no copiado.
  Agregar su fila en el historial («Requiere la aprobación de ambos integrantes»).
- [X] T033 [P] Escribir `docs/decisions/0035-frontend-profesional.md` (contexto, decisiones R1–R9, alternativas,
  consecuencias) y actualizar `README.md` (sección de la plataforma web y una captura nueva de la entrada en
  `docs/capturas/`).
- [X] T034 Correr `make e2e` (incluye `test_accessibility.py` y `test_responsive.py` de 360 a 1920) y
  `LANGSMITH_TRACING=false make check`, ambos en verde.
- [X] T035 Medir SC-004 con `node $S/scripts/perf.mjs http://127.0.0.1:8000/`: contenido principal < 2,5 s, sin
  filas FAIL. Registrar el resultado en `quickstart.md`.
- [X] T036 Marcar las tareas y dejar SC-001 y SC-002 (validación con personas) como pendientes del integrante.
- [X] T037 Hacer el commit solo con autorización explícita, como Robertto48, sin coautores:
  `feat(web): frontend profesional de Valer-IA, plataforma de agentes de Manuelita (spec 031)`.

---

## Dependencies & Execution Order

- Setup (T001–T004) → Foundational (T005–T010) → US1 (T011–T022) → US2 (T023–T026) y US3 (T027–T029) → US4
  (T030–T031) → Polish (T032–T037).
- T001 (copy) antes de cualquier componente con texto. T003 (fotos) antes de T008 y T014.
- US2 y US3 pueden ir en paralelo después de Foundational; US4 revisa todo al final.
- T020 mueve `RagConsole` a evidencia: coordinar con T028.

## Parallel Example

```text
Setup:        T003 (fotos) ‖ T004 (LFS)
Foundational: T008 (datos) ‖ T009 (prueba de créditos)
US1:          T013 ‖ T014 ‖ T015 ‖ T016 ‖ T017 ‖ T018 ‖ T019 → T020 → T021 → T022
US2 ‖ US3:    T023–T026 ‖ T027–T029
Polish:       T032 ‖ T033
```

## Implementation Strategy

1. **MVP**: Setup + Foundational + US1. La entrada nueva cambia la primera impresión de la sustentación.
2. **Incremento 2**: US2 (agente), el centro de la demostración.
3. **Incremento 3**: US3 (planificación y evidencia) y US4 (coherencia).
4. **Cierre**: constitución 2.6.0, ADR 0035, README, `make e2e`, `make check`, rendimiento y commit autorizado.
