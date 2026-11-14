# Tasks: Avatar del agente con sincronización de labios

**Input**: Design documents from `/specs/017-avatar-lipsync/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluidas. La spec las exige (FR-013, SC-006) y la constitución (§3.8) pide pruebas por módulo crítico.
Todas corren en Vitest sin red ni audio real.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1, US2, US3)

## Path Conventions

- Todo el código está en el frontend: `web/src/lib/`, `web/src/components/`, `web/src/styles/` y `web/src/test/`.
- Las pruebas se corren con `cd web && npx vitest run <archivo>`; la verificación completa, con
  `UV_PROJECT_ENVIRONMENT=.venv make check`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Tipos compartidos y punto de partida verificado.

- [X] T001 Verificar la línea base: `UV_PROJECT_ENVIRONMENT=.venv make check` en verde sobre la rama `017-avatar-lipsync` antes de cambiar código.
- [X] T002 [P] Definir los tipos del contrato en `web/src/lib/lipsync.ts`, con cuerpos `throw new Error("TODO")`: `MouthShape = "closed" | "half" | "open" | "round" | "wide"`, `AudioFeatures { rmsDb; b1; b2; b3 }`, `MouthState { shape; openness; pending }`, `MouthGeometry { width; height; roundness }`, `AnalyserLike` (`fftSize`, `frequencyBinCount`, `getFloatTimeDomainData`, `getByteFrequencyData`) y las firmas de `readFeatures`, `mouthFromFeatures`, `mouthGeometry` y `mouthPath` según `contracts/lipsync.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: El analizador en el grafo de audio y el modelo de la boca, que usan las tres historias.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Tests (escribir primero; deben fallar)

- [X] T003 [P] Pruebas de la boca en `web/src/test/lipsync.test.ts`:
  - silencio (`rmsDb = -100`) y ruido bajo la puerta (`-50`) dan `closed` con `openness = 0`;
  - en voz plena, la apertura sube a > 0,9 en ≤ 100 ms simulados (`attackMs = 30`);
  - desde `openness = 1` con silencio, `closed` en ≤ 160 ms (`releaseMs = 55`);
  - las formas siguen las reglas: `b3/(b1+b2) > 0.9` da `wide`; `b1/(b1+b2+b3) > 0.55` con `b3 < 0.25` da `round`; en otro caso, `open`; `openness < 0.08` da `closed`; `< 0.30` da `half`;
  - histéresis: una forma abierta nueva se adopta solo tras 2 cuadros iguales y `closed`/`half` se aplican sin espera;
  - `mouthFromFeatures` no muta `previous`;
  - `openness` siempre está en [0, 1];
  - `mouthGeometry` respeta la tabla de data-model (`closed` 28×0, `half` 26×6, `open` 26×16, `round` 16×14, `wide` 34×8), con alto efectivo = alto × openness;
  - `mouthPath` devuelve un `d` válido;
  - `readFeatures` con un analizador simulado calcula el RMS en dBFS y las bandas B1 300–900 Hz, B2 900–1800 Hz y B3 1800–3500 Hz según `sampleRate` y `fftSize`.
- [X] T004 [P] Pruebas del analizador en `web/src/test/voice.test.ts`:
  - el `AudioContext` simulado expone `createAnalyser` y `sampleRate`;
  - `VoicePlayer.analyser()` crea un único analizador (`fftSize = 1024`, `smoothingTimeConstant = 0.5`) conectado a `destination`;
  - cada fuente reproducida se conecta al analizador y no directamente al destino;
  - sin `createAnalyser`, o si lanza error, `analyser()` devuelve `null` y la fuente va a `destination` como antes.

### Implementation

- [X] T005 Implementar `web/src/lib/lipsync.ts` según data-model.md:
  - `LIPSYNC_TUNING = { gateDb: -45, fullDb: -15, attackMs: 30, releaseMs: 55, wideRatio: 0.9, roundRatio: 0.55, roundMaxB3: 0.25, hysteresisFrames: 2 }` (congelado) y `CLOSED_MOUTH`;
  - `readFeatures`, que reutiliza buffers por analizador para no crear arreglos en cada cuadro;
  - `mouthFromFeatures`, con suavizado exponencial `α = 1 − exp(−dt/τ)` e histéresis;
  - `mouthGeometry` y `mouthPath`, una forma de boca con dos curvas cuadráticas cuyo ancho, alto y redondez vienen de la geometría.
- [X] T006 Modificar `web/src/lib/voice.ts`:
  - `AudioContextLike` agrega `sampleRate` y `createAnalyser()`;
  - `VoicePlayer.analyser()` crea un analizador único y perezoso, conectado a `destination`;
  - `playNext` conecta la fuente al analizador, o a `destination` si no hay analizador;
  - ninguna otra API pública cambia.
- [X] T007 Exponer `analyser()` en `VoiceControl` de `web/src/lib/useVoice.ts`, delegando en el reproductor. Actualizar los mocks de `VoiceControl` en `web/src/test/VoiceControls.test.tsx`.

**Checkpoint**: T003 y T004 pasan; la voz suena igual que antes, ahora a través del analizador.

---

## Phase 3: User Story 1 - Ver al agente hablar con la boca sincronizada (Priority: P1) 🎯 MVP

**Goal**: avatar SVG junto al chat cuya boca sigue el audio de la voz: se abre con la voz, cambia entre 5 formas
suaves y se cierra en los silencios y al detener (FR-001…FR-004).

**Independent Test**: quickstart §2, filas «Boca sincronizada» y «Cierre inmediato». En Vitest, con estado
`speaking` y un analizador simulado que entrega voz, `avatar-mouth` cambia su `data-shape` a formas abiertas; al pasar
a `idle`, queda `closed` en el mismo cuadro.

### Tests for User Story 1 ⚠️

- [X] T008 [P] [US1] Pruebas del componente en `web/src/test/AgentAvatar.test.tsx`, con `requestAnimationFrame` falso y un analizador simulado:
  - en `speaking` con voz, `avatar-mouth` pasa a una forma abierta y su `d` cambia;
  - con silencio vuelve a `closed`;
  - al pasar a `idle`, `closed` inmediato y el bucle se cancela (`cancelAnimationFrame` llamado);
  - si `analyser()` devuelve `null`, la boca queda cerrada aunque el estado sea `speaking`;
  - el SVG lleva `aria-hidden="true"`;
  - `data-state` refleja el estado.
- [X] T009 [P] [US1] Integración en `web/src/test/ChatViewVoice.test.tsx`: con `FakeAudioContext` ampliado con `sampleRate` y `createAnalyser`, `agent-avatar` aparece en el chat, pasa a `data-state="speaking"` mientras suena la respuesta y vuelve a `idle` al terminar.

### Implementation for User Story 1

- [X] T010 [US1] Crear `web/src/components/AgentAvatar.tsx`:
  - SVG original de una asistente femenina, en `viewBox` 0–200, con la paleta de `tokens.css` (`--forest`, `--forest-deep`, `--orange`, `--gold`, `--paper`, `--ink`) y capas separadas: cabello, cara, ojos (`avatar-eyes`) y boca (`avatar-mouth`, un `path`);
  - no imita a una persona real ni usa el logo de Manuelita;
  - bucle `requestAnimationFrame` solo en `speaking`: `readFeatures`, luego `mouthFromFeatures` con `dt` real, luego lerp 0,35 de la geometría y `setAttribute("d")` y `data-shape` por `ref`, sin `setState` por cuadro;
  - al salir de `speaking`, cancelar el bucle y fijar `CLOSED_MOUTH`;
  - prop `debug`, que muestra `avatar-debug` con «forma · apertura».
- [X] T011 [US1] Estilos base en `web/src/styles/global.css`: `.agent-avatar` (tarjeta de 160 px, `--paper` y borde `--line`) y una rejilla `.chat-layout` de dos columnas (`160px 1fr`) desde 720 px.
- [X] T012 [US1] Integrar en `web/src/components/ChatView.tsx`:
  - envolver la conversación en `.chat-layout` con `<AgentAvatar state analyser={voice.analyser} debug={avatarDebug} />`;
  - `state = voice.speaking ? "speaking" : busy ? "thinking" : "idle"`;
  - `avatarDebug` se lee de `?avatarDebug=1` en `window.location.search`.

**Checkpoint**: el MVP funciona; el avatar habla con la boca sincronizada.

---

## Phase 4: User Story 2 - Un avatar que transmite su estado (Priority: P2)

**Goal**: reposo con respiración y parpadeo irregular, «pensando» con la mirada a un lado mientras se genera, y
hablando (FR-005).

**Independent Test**: quickstart §2, fila «Estados». En Vitest, `data-state` sigue la secuencia idle → thinking →
speaking → idle al enviar una pregunta con voz, y thinking → idle sin voz.

### Tests for User Story 2 ⚠️

- [X] T013 [P] [US2] En `web/src/test/AgentAvatar.test.tsx`:
  - el parpadeo es irregular, con un retardo entre 2,5 y 6 s (`nextBlinkDelay`) y `data-blinking` en `avatar-eyes` (implementado con un temporizador, porque CSS no permite variar `animation-delay` entre ciclos);
  - en `thinking`, `avatar-eyes` lleva la clase de mirada lateral.
- [X] T014 [P] [US2] En `web/src/test/ChatViewVoice.test.tsx`:
  - secuencia idle → thinking (tras enviar) → speaking (con audio) → idle;
  - con la voz silenciada: thinking → idle al terminar el turno, con la boca siempre `closed`.

### Implementation for User Story 2

- [X] T015 [US2] Animaciones en `web/src/styles/global.css`:
  - `@keyframes avatar-breathe` (escala de 1 % cada 4 s) en `[data-state="idle"]`;
  - parpadeo con la clase `.avatar-eyes--blink` (escala vertical 0,1), aplicada por el temporizador;
  - clase `.avatar-eyes--aside` con transición de la mirada lateral para `thinking`.
- [X] T016 [US2] En `web/src/components/AgentAvatar.tsx`:
  - programar el parpadeo con un temporizador de retardo aleatorio entre 2,5 y 6 s (`nextBlinkDelay`) y 140 ms de cierre;
  - aplicar `.avatar-eyes--aside` en `thinking`.

**Checkpoint**: US1 y US2 funcionan; el avatar comunica reposo, pensando y hablando.

---

## Phase 5: User Story 3 - Accesible, discreto y sin riesgos (Priority: P3)

**Goal**: movimiento reducido, diseño de teléfono, ocultar/mostrar con persistencia y boca cerrada sin voz, sin
cambiar el chat (FR-006, FR-007, FR-009, FR-010, FR-012; SC-005).

**Independent Test**: quickstart §2, filas «Movimiento reducido», «Teléfono», «Ocultar» y «Sin voz». En Vitest:
- `avatar-toggle` oculta el avatar y la preferencia sobrevive al remontaje;
- oculto, la voz sigue pidiendo `/api/tts`;
- con la voz silenciada no hay formas abiertas.

### Tests for User Story 3 ⚠️

- [X] T017 [P] [US3] En `web/src/test/ChatViewVoice.test.tsx`:
  - `avatar-toggle` oculta `agent-avatar` y escribe `localStorage["manuelita.avatar.hidden"] = "1"`;
  - al remontar sigue oculto y el texto del botón es «Mostrar avatar»;
  - oculto, la respuesta igual pide audio a `/api/tts`;
  - si `localStorage` lanza error, el avatar queda visible solo en la sesión.
- [X] T018 [P] [US3] En `web/src/test/AgentAvatar.test.tsx`: con `matchMedia("(prefers-reduced-motion: reduce)")` simulado como `true`, el contenedor lleva `data-reduced-motion="true"`, no parpadea (sin temporizador) y la boca sigue animándose en `speaking`.

### Implementation for User Story 3

- [X] T019 [US3] En `web/src/components/ChatView.tsx`:
  - botón `avatar-toggle` («Ocultar avatar» o «Mostrar avatar») junto a los controles de voz;
  - estado `avatarHidden` persistido en `localStorage["manuelita.avatar.hidden"]` (`"1"` = oculto), con `try/catch`;
  - sin avatar, la rejilla vuelve a una sola columna.
- [X] T020 [US3] En `web/src/components/AgentAvatar.tsx`: detectar `prefers-reduced-motion` con `matchMedia` (protegido si no existe), exponer `data-reduced-motion` y omitir el parpadeo.
- [X] T021 [US3] En `web/src/styles/global.css`:
  - `@media (prefers-reduced-motion: reduce)` desactiva respiración, parpadeo y mirada en `.agent-avatar`;
  - `@media (max-width: 719px)`: el avatar pasa a una franja de 72 px sobre la conversación, nunca sobre el formulario, y sin desplazamiento horizontal.

**Checkpoint**: las tres historias funcionan de forma independiente; el chat no cambia con el avatar oculto o la voz silenciada.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Documentación, gobernanza y verificación.

- [X] T022 [P] Escribir `docs/decisions/0021-avatar-local.md`, ADR con:
  - la elección del avatar local frente a HeyGen LiveAvatar LITE (costo de 1 crédito por minuto, nube, red) y `heygen-com/skills` (asíncrono);
  - la técnica de lip-sync por volumen y formantes, con sus límites (sin fonemas exactos);
  - Rhubarb Lip Sync como mejora futura.
- [X] T023 [P] Actualizar `CONSTITUTION.md` (versión menor y fecha, avatar local en §3.7 y regla de ilustración original sin imitar personas reales), `README.md` (avatar en la solución y su uso) y `docs/demo.md` (mostrar el avatar en el bloque de conversación y el plan B: ocultarlo).
- [X] T024 Ejecutar `UV_PROJECT_ENVIRONMENT=.venv make check` (Ruff, pytest, Vitest y build) y corregir hasta verde.
- [X] T025 Validación manual con `quickstart.md` §2 y §3:
  - los 8 escenarios con `make app` y la voz Rebeca;
  - medición de SC-001 con `?avatarDebug=1` sobre 10 preguntas;
  - ajustar `LIPSYNC_TUNING` si hace falta;
  - anotar los resultados en `specs/017-avatar-lipsync/quickstart.md` (sección de resultados).
  Requiere a una persona que mire y escuche; dejar constancia de lo que no se pudo verificar.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias. T005 depende de T002; T007, de T006.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US2 (Phase 4)**: depende de T010 y T012 de US1, porque usa el mismo componente y la misma integración.
- **US3 (Phase 5)**: depende de T010 y T012 de US1; puede ir en paralelo con US2 salvo en los archivos que comparten (`AgentAvatar.tsx`, `global.css`), que se editan en secuencia.
- **Polish (Phase 6)**: T022 y T023 pueden empezar después de US1; T024 y T025 van al final.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- `lipsync.ts` va antes que `voice.ts`, este antes que `useVoice.ts`, este antes que `AgentAvatar.tsx` y este antes que `ChatView.tsx`.

### Parallel Opportunities

- Fase 2: T003 y T004 en paralelo.
- US1: T008 y T009 en paralelo.
- US2 y US3: sus pruebas (T013, T014, T017, T018) en paralelo.
- Polish: T022 y T023 en paralelo.

## Parallel Example: User Story 1

```bash
# Pruebas de US1 en paralelo (archivos distintos):
Task: "T008 Pruebas de AgentAvatar en web/src/test/AgentAvatar.test.tsx"
Task: "T009 Integración del avatar en web/src/test/ChatViewVoice.test.tsx"
```

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1 y Fase 2: el analizador en el grafo y el modelo de la boca, probados.
2. Fase 3: el avatar con la boca sincronizada en el chat.
3. **Parar y validar**: quickstart §2, «Boca sincronizada» y «Cierre inmediato».

### Incremental Delivery

1. Base, luego US1 (MVP: el avatar habla).
2. US2: estados de reposo y pensando.
3. US3: accesibilidad, teléfono y ocultar.
4. Polish: ADR, constitución, documentación y validación con personas.

## Notes

- No hay cambios en el servidor ni dependencias nuevas.
- Los commits, push y PR los hace el equipo (CONSTITUTION §4.3), salvo autorización explícita.
