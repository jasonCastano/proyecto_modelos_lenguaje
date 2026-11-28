# Tasks: Stickers de Valer-IA en las conversaciones de WhatsApp

**Input**: Design documents from `specs/034-stickers-whatsapp/`
**Prerequisites**: plan.md, spec.md, research.md (R1–R9), data-model.md, contracts/stickers.md, quickstart.md

**Tests**: incluidas. El plan pide pytest, `npm test` del plugin y un guion `simulate --check`, y la DoD exige
`make check` en verde.

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–033).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: historia de usuario de la spec (US1–US4)

## Path Conventions

Proyecto único: `src/proyecto_modelos_lenguaje/`, `tests/`, `config/`, `docs/` y `openclaw/` en la raíz del
repositorio. Los stickers ya existen en `docs/whatsapp/stickers/` (spec 030) y **no se modifican**.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: verificación temprana del envío real y configuración.

- [ ] T001 Verificación temprana (research R1, quickstart §0). En `openclaw/plugins/valeria-bridge/index.ts`, agregar una función `loadWhatsAppListener()`:
  - ubica `light-runtime-api.js` de `@openclaw/whatsapp` bajo `OPENCLAW_STATE_DIR` (o `%USERPROFILE%\.openclaw-valeria`) en `npm/projects/openclaw-whatsapp-*/node_modules/@openclaw/whatsapp/dist/`;
  - lo importa con `pathToFileURL`;
  - devuelve `getActiveWebListener()` o `null`, sin lanzar.

  Comprobación en el gateway real, **con instrucciones previas al usuario** (reinicio, espera de 2 min y número de
  un operador): con `VALERIA_BRIDGE_DEBUG=1` se registra si el listener existe y tiene `sendSticker`, y se envía
  un sticker de prueba.
  - Si llega **como sticker**: se sigue con el plan.
  - Si no: se documenta en las notas y se pasa al plan B (ampliar `openclaw/patches/whatsapp-lid.mjs` para que
    `sendMedia` produzca stickers) antes de US1.
- [X] T002 [P] Agregar a `ChannelsConfig` en `src/proyecto_modelos_lenguaje/agent/config.py` los campos `stickers: bool = True` (flag) y `stickers_per_conversation: int = 4` (validación «0 ≤ valor ≤ 20»), y las claves con comentarios en español en `[channels]` de `config/agent.toml`; pruebas en `tests/unit/agent/test_config.py` (defaults, -1 y 21 rechazados, `stickers` no booleano rechazado)
- [X] T003 [P] Crear `config/stickers.toml` con los nueve stickers (data-model):
  - para cada uno: `file`, `text` (exacto de su ficha `.md`), `language` (`es` o `none` para el pulgar),
    `situations` y `position`;
  - el mapeo de research R3;
  - la tabla de prioridades en un comentario.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: catálogo, estado por hilo y campo de respuesta. Todas las historias dependen de esta fase.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T004 [P] Pruebas en `tests/unit/channels/test_stickers.py` (catálogo):
  - `load_catalog()` lee los nueve;
  - cada `file` existe, pesa ≤ 500 KB y empieza con `RIFF` y `WEBP` en los bytes 8–12;
  - situaciones del vocabulario cerrado;
  - un archivo faltante o inválido desactiva solo ese sticker y lo reporta;
  - `language` en `{es, none}`;
  - `position` en `{before, after}`.
- [X] T005 Crear `src/proyecto_modelos_lenguaje/channels/stickers.py` con:
  - `StickerChoice` (frozen: `name`, `path`, `position`);
  - `Sticker`, `StickerCatalog` y `load_catalog(path=CONFIG_DIR / "stickers.toml", root=PROJECT_ROOT)`, con
    validación y la lista de `unavailable`;
  - las constantes `SITUATIONS` y `PRIORITY` del data-model.

  Docstrings en español.
- [X] T006 [P] En `src/proyecto_modelos_lenguaje/channels/store.py`:
  - tabla aditiva `channel_stickers(thread_id TEXT NOT NULL, sticker TEXT NOT NULL, turn_no INTEGER NOT NULL, sent_at TEXT NOT NULL)`;
  - columna `answered_turns INTEGER NOT NULL DEFAULT 0` en `channel_threads` (vía `MIGRATIONS`);
  - métodos `count_answered(thread_id) -> int` (incrementa y devuelve el número de respuesta),
    `sticker_usage(thread_id) -> ThreadUsage` (`answered_turns`, `last_sticker_turn`, `sent`) y
    `record_sticker(thread_id, name, turn_no)`;
  - `adopt_thread` conserva o migra estas filas al id definitivo.

  Pruebas en `tests/unit/channels/test_store.py`: migración de una base sin la tabla, uso y adopción.
- [X] T007 [P] Agregar `sticker: str | None = None` a `ChannelLogRecord` en `src/proyecto_modelos_lenguaje/channels/journal.py` (comentario «Spec 034: nombre del sticker, nunca contenido») con prueba en `tests/unit/channels/test_journal.py`; y en `ChannelReply` (`channels/bridge.py`) el campo `sticker: StickerChoice | None = None`, serializado en `to_dict()` como `{"name", "path", "position"}` o `None`

**Checkpoint**: el catálogo carga y el hilo sabe qué stickers ya recibió.

---

## Phase 3: User Story 1 - Stickers en los momentos sociales (Priority: P1) 🎯 MVP

**Goal**: saludo, agradecimiento, despedida e invitación a preguntar llevan su sticker; las preguntas factuales
no.

**Independent Test**: en una conversación nueva con `FakeService` que devuelve `route.act`: «Hola» (`greeting`,
`first_contact`) da `valeria-bienvenido` antes; una pregunta factual no lleva sticker; «gracias» (`thanks`) da
`valeria-gracias` después; «chao» (`closing`) da `valeria-lindo-dia` después.

### Tests for User Story 1

- [X] T008 [P] [US1] Pruebas puras de `situation_of` y `choose` en `tests/unit/channels/test_stickers.py` para los casos de research R3:
  - `greeting` con `first_contact` → `bienvenido` (before); con `inactivity` o `restart` → `hola` (before); a
    mitad de conversación → `consulta` (after);
  - `thanks` → `gracias` (after); `closing` → `lindo-dia` (after);
  - pregunta factual (ruta documental con citas) → `None`;
  - presentación de una pregunta directa (spec 032), con `introduced` y acto distinto de `greeting` → `None`.
- [X] T009 [P] [US1] Pruebas en `tests/unit/channels/test_bridge.py`:
  - `FakeService` puede devolver `route: {"route": "direct", "act": "greeting"}` y otros actos;
  - la secuencia hola → pregunta → gracias → chao produce los stickers esperados en `reply.sticker` y en el
    registro (`sticker`);
  - `to_dict()` incluye `sticker` con `path` absoluto existente.
- [X] T010 [P] [US1] Prueba de contrato en `tests/api/test_channels_api.py`: la respuesta de `POST /api/channels/messages` incluye la clave `sticker` (objeto o `null`) y el resto del contrato no cambia (actualizar el conjunto de claves esperado)

### Implementation for User Story 1

- [X] T011 [US1] Implementar en `src/proyecto_modelos_lenguaje/channels/stickers.py`:
  - `TurnSignals` (dataclass), `ThreadUsage` y `situation_of(signals)` para las situaciones sociales;
  - `choose(signals, usage, catalog, config)` con el orden de reglas de research R4 (las exclusiones y la
    moderación se completan en US2).
- [X] T012 [US1] En `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - cargar el catálogo una vez (atributo perezoso);
  - después de `_introduce` y antes de `_with_notices`, construir `TurnSignals` desde la respuesta
    (`reply.route`, el acto y el sentimiento del `turn["route"]`, avisos, idioma, `conversation_start`,
    `introduced`, estado y evento);
  - llamar a `store.count_answered`, `sticker_usage` y `choose`; si hay elección, `record_sticker` y
    `reply.sticker`;
  - `_record` escribe `sticker=reply.sticker.name`;
  - guardar `act`, `sentiment` y `notices` del turno en la respuesta, en `_from_outcome`.
- [X] T013 [US1] Plugin, en `openclaw/plugins/valeria-bridge/src/bridge.ts`:
  - tipos `StickerReply` y `StickerSender`;
  - `dispatch` recibe `sendSticker` opcional;
  - con `position: "before"` envía el sticker antes de la voz y del texto;
  - con `"after"` lo programa con `setTimeout(1500)` sin esperar;
  - errores atrapados y log con `maskDigits`.

  En `index.ts`: `stickerSender` con `loadWhatsAppListener()` (T001) y `listener.sendSticker(target, await readFile(path))`, que devuelve `false` si no hay listener. Pruebas en `openclaw/plugins/valeria-bridge/test/bridge.test.ts` para el orden antes/después (temporizadores falsos de `node:test`), un fallo del sticker que no afecta el texto y logs sin dígitos.

**Checkpoint**: US1 funciona en pruebas; la prueba en el teléfono va en T026.

---

## Phase 4: User Story 2 - Uso moderado (Priority: P1)

**Goal**: máximo uno por respuesta, ninguno en dos respuestas seguidas (salvo la despedida), máximo 4 por
conversación sin repetir (salvo el pulgar) y ninguno en momentos delicados ni en inglés con texto.

**Independent Test**: conversación de 10 turnos con varios saludos, agradecimientos y una queja. En
`reply.sticker`: nunca dos seguidos, total ≤ 4, sin repetidos, ninguno en la queja ni en el aviso de datos
sensibles, y en inglés solo el pulgar.

### Tests for User Story 2

- [X] T014 [P] [US2] Pruebas de moderación en `tests/unit/channels/test_stickers.py`:
  - **dos seguidos**: un `thanks` justo después de un turno con sticker da `None`, pero un `closing` sí;
  - **máximo**: con 4 ya enviados, `None`;
  - **repetidos**: `gracias` repetido da `None`; `pulgar` repetido sí;
  - **momentos delicados**: `sentiment` en `frustrated`, `angry` o `distressed` da `None`; `act=complaint` da
    `None`; `notices` con `sensitive_data` da `None`;
  - **respuestas que no llevan sticker**: `status` distinto de `answered`, o `event` en `rate_limited`,
    `daily_capped`, `stale`, `blocked`, `error` o `voice_error` → `None`;
  - **idioma**: con `language="en"`, `gracias` da `None` y `pulgar` sí;
  - **interruptor**: `config.stickers=False` o `stickers_per_conversation=0` da `None`.
- [X] T015 [P] [US2] Prueba en `tests/unit/channels/test_bridge.py`: guion de 10 turnos con actos simulados; se verifican las reglas sobre los registros (`sticker` por turno)

### Implementation for User Story 2

- [X] T016 [US2] Completar `choose` en `src/proyecto_modelos_lenguaje/channels/stickers.py` con:
  - las exclusiones, el idioma y la moderación del hilo (research R4, en ese orden);
  - la resolución por prioridad cuando concurren situaciones.

  Cada regla es una función pequeña con docstring.

**Checkpoint**: US1 y US2 completas.

---

## Phase 5: User Story 3 - Acciones completadas y asentimientos (Priority: P2)

**Goal**: «¡Gracias por confiar en nosotros!» al guardar el perfil, «¡Listo!» al olvidar datos, completar otra
acción o entregar un plan, y «Pulgar» ante un asentimiento.

**Independent Test**:
- aprobar `save_preference` da `valeria-gracias-confianza`;
- aprobar olvidar da `valeria-listo`;
- una respuesta de ruta `planning` da `valeria-listo`;
- «ok» (`act=minimal`) da `valeria-pulgar`.

### Tests for User Story 3

- [X] T017 [P] [US3] Pruebas en `tests/unit/channels/test_stickers.py`:
  - `approved_action="save_preference"` → `gracias-confianza`; `forget` u otra → `listo`;
  - `route="planning"` → `listo`;
  - `act="minimal"` con un texto de asentimiento («ok», «dale», «perfecto», «entendido», «listo», «👍») →
    `pulgar`; `minimal` con otro texto → `None`.
- [X] T018 [P] [US3] Prueba en `tests/unit/channels/test_bridge.py`: con `FakeService.propose="save_preference"`, la confirmación «dale» resuelve la aprobación y la respuesta lleva `valeria-gracias-confianza`; con `/olvidar` aprobado, `valeria-listo`

### Implementation for User Story 3

- [X] T019 [US3] En `src/proyecto_modelos_lenguaje/channels/bridge.py`, `_resolve` marca `reply.approved_action` (nombre de la herramienta aprobada; `forget` para el borrado) y aplica la decisión del sticker igual que en la respuesta normal. En `stickers.py`: situaciones `profile_saved`, `action_done` y `assent` con el léxico de asentimiento en español e inglés.

**Checkpoint**: US1–US3 completas.

---

## Phase 6: User Story 4 - «Pensando» cuando la respuesta tarda (Priority: P3)

**Goal**: si el backend tarda más de `stickerThinkingMs`, el plugin envía `valeria-pensando` antes de la
respuesta, como máximo una vez cada 10 minutos por remitente.

**Independent Test**: con temporizadores falsos, un backend que responde a los 9 s da «Pensando» y luego la
respuesta; uno a los 2 s, solo la respuesta. Un segundo mensaje lento dentro de los 10 minutos no repite
«Pensando».

### Tests for User Story 4

- [X] T020 [P] [US4] Pruebas en `openclaw/plugins/valeria-bridge/test/bridge.test.ts` con `mock.timers` de `node:test` para los tres casos anteriores, más:
  - `stickerThinkingMs: 0` desactiva el envío;
  - un fallo del sticker no afecta la respuesta.

### Implementation for User Story 4

- [X] T021 [US4] En `openclaw/plugins/valeria-bridge/src/bridge.ts`:
  - `resolveConfig` lee `stickersDir` (ruta) y `stickerThinkingMs` (entero ≥ 0; 8000 por defecto);
  - `dispatch` arma el temporizador antes del `fetch` y lo cancela al recibir respuesta;
  - un mapa en memoria `senderId → último envío` limita a uno cada 10 minutos.

  En `openclaw/openclaw.json5`, agregar en `plugins.entries.valeria-bridge.config`:
  `stickersDir: "${VALERIA_REPO}/docs/whatsapp/stickers"` y `stickerThinkingMs: 8000`, con un comentario en
  español. Verificar `tests/unit/test_openclaw_config.py`.

**Checkpoint**: las cuatro historias funcionan.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T022 [P] En `src/proyecto_modelos_lenguaje/ops.py`, la comprobación `stickers` (contrato §5):
  - con el interruptor activo, «N/9 disponibles», más los nombres faltantes;
  - con el interruptor apagado, «apagados»;
  - falla solo si el interruptor está activo y hay 0.

  Se incluye en `ops_check` después de `soporte-lid`. Pruebas en `tests/unit/test_ops.py`, con `test_all_green`
  ajustado.
- [X] T023 [P] Crear `tests/fixtures/channels/stickers.jsonl` (≥ 10 conversaciones con números ficticios `+5700000004NN`):
  - saludo inicial, pregunta, gracias, despedida, queja, asentimiento, aprobación de perfil y conversación en
    inglés;
  - cada mensaje con `expected_sticker` (nombre o `null`).

  Extender `simulate --check` en `src/proyecto_modelos_lenguaje/channels/__main__.py` para reportar
  `sticker_mismatch` cuando `payload.sticker.name` difiera de `expected_sticker`, y `sticker_overuse` si hay más
  de un sticker por respuesta o más del máximo por conversación. Agregar una prueba de API en modo demo, como
  `test_channels_conversation_start.py`.
- [X] T024 [P] Documentar en `docs/manual_whatsapp.md` (Valer-IA usa stickers con moderación), en `docs/despliegue.md` (interruptor, máximo, `stickersDir`, `stickerThinkingMs`, `ops check`, qué hacer si el sticker no llega) y en `docs/whatsapp/README.md` (sección «Uso por el bot» con el mapeo de `config/stickers.toml`; los archivos no cambian)
- [X] T025 Ejecutar `make check`, `make openclaw-test` y `simulate --check` con `stickers.jsonl` (modo demo); corregir hasta tener todo en verde
- [ ] T026 Prueba en el teléfono (manual, quickstart §2). Antes de ejecutar, dar al usuario instrucciones paso a paso:
  1. reiniciar el backend y luego `.\scripts\openclaw_env.ps1 -Install` (sincroniza la configuración del plugin) y
     esperar ~2 min;
  2. `ops check` con `stickers` ✅;
  3. hola, pregunta, gracias, chao, una queja y una consulta de planificación lenta;
  4. revisar `channels.jsonl`.

  Registrar SC-001 a SC-006 (incluida la percepción de naturalidad) en las notas.
- [X] T027 Marcar las tareas completadas con [X] y agregar notas de implementación al final de este archivo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: T001 primero, porque decide el mecanismo de envío (plan A o B). T002 y T003 son libres.
- **Foundational (fase 2)**: depende de T002 y T003. Bloquea las historias.
- **US1**: depende de la fase 2; T013 depende de T001.
- **US2**: depende de T011.
- **US3**: depende de T011 y T012.
- **US4**: depende de T013 (tipos del plugin).
- **Polish**: T025 y T026 van al final.

### User Story Dependencies

- US1 es el MVP y la base de la decisión.
- US2 completa la moderación sobre la misma función.
- US3 agrega situaciones.
- US4 es independiente del backend: solo el plugin.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- `stickers.py` va antes que `bridge.py`, y este antes que el plugin.

### Parallel Opportunities

- T002 ∥ T003.
- T004 ∥ T006 ∥ T007.
- En US1: T008 ∥ T009 ∥ T010.
- T014 ∥ T015.
- T017 ∥ T018.
- En Polish: T022 ∥ T023 ∥ T024.

---

## Parallel Example: User Story 1

```text
# Pruebas primero (fallan):
T008 tests/unit/channels/test_stickers.py (situaciones)
T009 tests/unit/channels/test_bridge.py (secuencia hola → gracias → chao)
T010 tests/api/test_channels_api.py (clave sticker)

# Luego, en orden:
T011 channels/stickers.py → T012 channels/bridge.py → T013 plugin (bridge.ts + index.ts)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001: confirmar que el sticker llega como sticker.
2. Fases 1 y 2, y US1: saludo, gracias y despedida con sticker.
3. Validar con pruebas y una conversación real corta.

### Incremental Delivery

1. US1 y US2 (P1): stickers sociales con moderación. Es lo mínimo para que el uso sea natural.
2. US3: acciones y asentimientos.
3. US4: «Pensando».
4. Polish: `ops check`, guion, documentación y prueba en el teléfono.

### Parallel Team Strategy

Trabajo secuencial en un solo portátil (restricción del proyecto). [P] solo indica que el orden entre esas tareas es
libre.

---

## Notes

- Los stickers aprobados no se tocan; la fuente única es `docs/whatsapp/stickers/`.
- Nunca números reales en pruebas: `+5700000004NN`.
- El registro guarda solo nombres de stickers.
- UI, comentarios y docstrings en español; identificadores en inglés; Ruff con `line-length = 100`.
- Commits, push y PR solo con autorización explícita de jasonCastano o Robertto48, sin `Co-authored-by`.

---

## Notas de implementación (2026-11-27)

- **Hecho**: T002–T025 y T027.
- **Pendiente** (manual, con instrucciones previas al usuario):
  - **T001**: la verificación en el gateway real. El código `loadWhatsAppListener()` ya está en `index.ts`;
    falta confirmar en el gateway que el sticker llega como sticker;
  - **T026**: la prueba en el teléfono.
- **Verificación automática**:
  - **pytest**: 2452 pruebas, 47 omitidas;
  - **web**: 216 pruebas y build;
  - **`make openclaw-test`**: 8 pruebas del parche y 38 del plugin;
  - **pre-commit** en verde sobre los archivos nuevos;
  - **guion `stickers.jsonl`** (10 conversaciones, 28 mensajes) en modo demo por la API: 0 hallazgos.
- **Una corrida de `make check` se congeló** al ~3 % de pytest. Al repetirla, la suite completa pasó en 2,5 min;
  es el problema intermitente ya conocido del entorno (HiGHS/scipy).
- **Hallazgos**:
  - el manifiesto del plugin (`openclaw.plugin.json`) tiene `additionalProperties: false`, así que se declararon
    `stickersDir` y `stickerThinkingMs`; sin eso el gateway no habría arrancado. `openclaw config validate` del
    template: válido;
  - en CI los stickers son punteros de Git LFS: las pruebas usan un catálogo temporal con WebP mínimos, y
    `test_all_green` no depende de los archivos reales;
  - en modo demo, la queja «estoy muy molesto» llega con acto `smalltalk`, así que no lleva sticker de todos
    modos. En modo real, el enrutador puede marcarla `complaint`, y la exclusión aplica.
- **Plan B** (si T001 falla): ampliar `openclaw/patches/whatsapp-lid.mjs` para que `sendMedia` envíe stickers
  (research R1), sin otra enmienda constitucional.

## Seguimiento (2026-11-28, spec 037)

- **T001 falló en producción**: en 79 respuestas el backend eligió 4 stickers y el gateway no entregó
  ninguno («sticker no enviado (listener no disponible)»).
- **Causa raíz**: OpenClaw guarda el runtime de cada plugin por instancia (`AsyncLocalStorage`), así que
  `getActiveWebListener()` llamada desde `valeria-bridge` lee el slot vacío de este plugin.
- **Corrección y uso activo**: los implementa la spec 037 (`specs/037-stickers-activos/`). El plugin busca la
  conexión en el runtime de canales compartido, con el parche de símbolo global como respaldo. La vía que
  funcionó queda en las notas de la spec 037.
- **2026-11-28**: con el parche `valeria-sticker v2` (spec 037, ADR 0039), los stickers llegan como stickers nativos en
  el teléfono. T001 y T026 de esta spec quedan verificados por la spec 037.
