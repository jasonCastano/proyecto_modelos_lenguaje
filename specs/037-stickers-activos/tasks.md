# Tasks: Stickers que sí llegan y se usan de forma activa

**Input**: Design documents from `specs/037-stickers-activos/`
**Prerequisites**: plan.md, spec.md, research.md (R1–R6), data-model.md, contracts/sticker-delivery.md, quickstart.md

**Tests**: incluidas. La spec exige un conjunto de verificación y una prueba real (FR-015), y la DoD exige
`make check` en verde.

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–036).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivo distinto, sin dependencias pendientes).
- **[Story]**: historia de usuario de la spec (US1–US3).

## Path Conventions

Proyecto único: `src/proyecto_modelos_lenguaje/`, `openclaw/`, `config/`, `tests/` y `docs/` en la raíz del
repositorio.

**Reglas transversales**:

- el texto de la respuesta llega siempre, aunque el sticker falle;
- sin números de teléfono ni contenido en registros o fixtures;
- los nueve stickers aprobados no cambian;
- los pasos que reinician el gateway o usan el teléfono llevan instrucciones previas paso a paso para el usuario.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: confirmar en vivo la vía de entrega antes de escribir código (Constitución V; la spec 034 no lo hizo).

- [X] T001 Prueba en vivo de la vía sin parche (manual; antes de ejecutar, dar al usuario instrucciones paso a paso):
  - **sonda temporal**: agregar en `openclaw/plugins/valeria-bridge/index.ts` una sonda que, 30 s después de
    `register(api)`, escriba en el log del gateway estos tres datos:
    - si existe `api.runtime?.channel?.runtimeContexts`;
    - si `runtimeContexts.get({channelId: "whatsapp", accountId, capability: "connection-controller"})` devuelve
      algo para `accountId` ∈ {`"default"`, `undefined`};
    - si ese controlador expone `getActiveListener()?.sendSticker`;
  - **prueba**: el usuario reinicia `ValerIA-Gateway`, espera unos 2 minutos y se leen las líneas `valeria-bridge:
    sonda` del log `~/.openclaw-valeria/tmp/openclaw/openclaw-YYYY-MM-DD.log`;
  - **registro**: el resultado (vía compartida disponible o no) va en las notas de este archivo y decide si T011–T013
    (parche) se ejecutan;
  - la sonda se reemplaza por el log de arranque de T009.
- [X] T002 [P] Ampliar `tests/fixtures/channels/stickers.jsonl` con conversaciones de uso activo, en el formato existente de la spec 034:
  - **a01**, seis mensajes: «Hola», «¿Qué produce Manuelita?», «¿Y en qué países opera?», «ok», «gracias», «chao»;
  - **a02**, tres preguntas seguidas con citas;
  - **a03**, presentación de primer contacto con una pregunta concreta (un solo sticker);
  - **a04**, queja;
  - **a05**, angustia («me siento muy mal»);
  - **a06**, número de tarjeta (aviso de datos sensibles);
  - **a07**, crisis;
  - **a08**, inglés (solo el pulgar);
  - **a09**, «sin stickers» y luego dos preguntas;
  - **a10**, conversación de 12 turnos (máximo 8);
  - **a11**, respuesta con evidencia insuficiente;
  - **a12**, saludo a mitad de conversación (`valeria-consulta`).

  Cada turno lleva el sticker esperado o `null`, y cada conversación el rango esperado de stickers.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el modelo de uso por hilo y la preferencia. US2 y US3 dependen de esta fase; US1 (entrega) puede
avanzar en paralelo.

- [X] T003 [P] Pruebas en `tests/unit/channels/test_store.py`:
  - `record_sticker(thread, name, turn, situation)` guarda la situación;
  - `sticker_usage(...)` devuelve `last_sticker`, `last_situation` y `off`;
  - `set_stickers_off(thread)` persiste y sobrevive a `rebind` del hilo;
  - una base existente sin la columna `situation` se migra sin perder filas (`situation` nula).
- [X] T004 Implementar en `src/proyecto_modelos_lenguaje/channels/store.py` y en `ThreadUsage` (`src/proyecto_modelos_lenguaje/channels/stickers.py`) según data-model §4:
  - `channel_stickers` gana la columna `situation TEXT` con migración `ALTER TABLE … ADD COLUMN`;
  - la preferencia `stickers_off` por hilo se guarda donde está `reply_format` y se conserva en `rebind`;
  - `ThreadUsage` gana `last_sticker: str | None`, `last_situation: str | None` y `off: bool`.

**Checkpoint**: el puente sabe qué sticker y qué situación fueron los últimos y si el hilo los apagó.

---

## Phase 3: User Story 1 - El sticker elegido llega al teléfono (Priority: P1) 🎯 MVP

**Goal**: todo sticker elegido llega como sticker nativo, en orden, con registro de entrega y estado en `ops
check`.

**Independent Test**: «Hola» desde un número nuevo. Llega el sticker de bienvenida y el log del gateway dice
`sticker enviado (valeria-bienvenido.webp) vía <vía>`.

### Tests for User Story 1

- [X] T005 [P] [US1] Pruebas en `openclaw/plugins/valeria-bridge/test/bridge.test.ts`:
  - **orden de vías de `findWhatsAppListener`**:
    - un doble de `runtimeContexts` con controlador → `route = "compartido"`;
    - sin él, un objeto en `globalThis[Symbol.for("valeria.whatsapp.channelRuntime")]` → `route = "parche"`;
    - sin ninguno, un import simulado → `route = "import"`;
    - sin listener → `{listener: null, reason: "sin-listener"}`;
  - **`deliverSticker`**:
    - registra `sticker enviado (<archivo>) vía <vía>`;
    - registra `sticker no enviado (<archivo>): sin-listener|sin-archivo|error`, sin dígitos;
    - nunca lanza;
    - el texto se entrega igual («antes» y «después»).
- [X] T006 [P] [US1] Pruebas en `tests/unit/test_ops.py`: `stickers_today` con un registro del canal y un log del gateway de ejemplo (en `tmp_path`) cuenta elegidos, entregados y fallidos, y da rojo (N > 0, M = 0), amarillo (0 < M < N) o verde (M = N o N = 0).

### Implementation for User Story 1

- [X] T007 [US1] En `openclaw/plugins/valeria-bridge/index.ts`:
  - **`register(api)`**: guarda `api.runtime?.channel`;
  - **`findWhatsAppListener(channelRuntime, accountId)`** (contracts §1), con este orden:
    1. `runtimeContexts.get({channelId: "whatsapp", accountId, capability: "connection-controller"})` →
       `getActiveListener()`, con `accountId` ∈ {el del evento, `"default"`, `undefined`};
    2. el símbolo global `Symbol.for("valeria.whatsapp.channelRuntime")` con la misma consulta;
    3. `loadWhatsAppListener()` (vía actual);
  - **caché**: guarda la vía que funcionó mientras el listener siga respondiendo;
  - **`stickerSender`**: devuelve `{ok, route, reason}`.
- [X] T008 [US1] En `openclaw/plugins/valeria-bridge/src/bridge.ts`:
  - `deliverSticker` registra «enviado» o «no enviado: motivo» con el nombre del archivo (data-model §6) y nunca
    bloquea el texto;
  - el sticker «Pensando» usa el mismo emisor.
- [X] T009 [US1] En `openclaw/plugins/valeria-bridge/index.ts`, log de arranque:
  - 30 s después de `register` escribe `valeria-bridge: stickers listos vía <vía>` o `valeria-bridge: sin vía de
    stickers (<motivo>)`;
  - lo repite en el primer intento fallido si antes no había vía;
  - quitar la sonda de T001.
- [X] T010 [US1] En `src/proyecto_modelos_lenguaje/ops.py`:
  - `stickers_today(...)` (contracts §4) lee los nombres elegidos del día en `logs/channels.jsonl` (campo `sticker`)
    y las líneas «enviado» y «no enviado» del log del gateway del día;
  - el log del gateway está en `OPENCLAW_STATE_DIR` o `~/.openclaw-valeria`, en `tmp/openclaw/openclaw-<día>.log`;
  - `ops check` lo muestra junto a `stickers`;
  - la línea de arranque del plugin aparece como detalle;
  - JSON: `stickers_today`.
- [X] T011 [US1] **Solo si T001 muestra que la vía compartida no expone el controlador**: crear el parche `openclaw/patches/whatsapp-sticker.mjs` (contracts §2):
  - **ancla exacta**: `const setWhatsAppRuntime = runtimeStore.setRuntime;` en `.setup/runtime-*.mjs` del
    componente instalado;
  - **qué hace**: publica `runtime.channel` en `globalThis[Symbol.for("valeria.whatsapp.channelRuntime")]` y deja
    el marcador `/* valeria-sticker v1 */`;
  - **comportamiento**: idempotente, con `--check`;
  - **códigos de salida**: 0, 2 o 3.
- [X] T012 [US1] **Solo con T011**:
  - pruebas en `openclaw/patches/test/whatsapp-sticker.test.mjs`: aplica, es idempotente, no toca nada si el ancla
    no coincide, y `--check`;
  - agregarlas a `make openclaw-test` en `Makefile`;
  - en `src/proyecto_modelos_lenguaje/ops.py`, verificación `soporte-sticker`, como `soporte-lid`;
  - en `scripts/openclaw_env.ps1`, aplicar el parche al instalar o actualizar, junto a `whatsapp-lid`.
- [X] T013 [US1] **Solo con T011**:
  - documentar el parche en `docs/decisions/0038-whatsapp-remitentes-lid.md` (anexo) o en un ADR nuevo
    `docs/decisions/0039-whatsapp-stickers-runtime.md`;
  - agregar la línea en `CONSTITUTION.md` (sección del canal, junto a `whatsapp-lid`) con la versión siguiente de
    la constitución.

**Checkpoint**: los stickers que el backend elige llegan, y `ops check` lo demuestra.

---

## Phase 4: User Story 2 - Uso activo y natural en toda la conversación (Priority: P1)

**Goal**:
- respuestas informativas con «¡Listo!» o el pulgar, en una de cada dos;
- respuestas seguidas con sticker si cambia la situación;
- máximo 8 por conversación;
- sin repetir el mismo sticker seguido, salvo el pulgar y la despedida.

**Independent Test**: en `tests/api/test_channels_stickers.py`, la conversación a01 da entre dos y cuatro stickers y
a02 lleva sticker en al menos una de cada tres respuestas.

### Tests for User Story 2

- [X] T014 [P] [US2] Pruebas en `tests/unit/channels/test_stickers.py`:
  - **`situations_of`**: con una respuesta `answered` con citas y sin respaldo devuelve `useful_answer`; la
    prioridad sigue data-model §2;
  - **cadencia**: con `useful_answer` y el sticker en el turno anterior, no hay sticker; sin sticker en el turno
    anterior, sí lo hay, alternando `valeria-listo` y `valeria-pulgar` según `last_sticker`;
  - **moderación**:
    - el tope de 8;
    - dos respuestas seguidas con situación distinta llevan sticker;
    - el mismo sticker seguido se bloquea, salvo `valeria-pulgar` y `valeria-lindo-dia`;
    - una presentación con pregunta da un solo sticker, el de presentación.
- [X] T015 [P] [US2] Prueba en `tests/api/test_channels_stickers.py` que corre el conjunto ampliado de T002 con el servicio demo y mide:
  - SC-002: a01 entre 2 y 4, y al menos el 80 % de las conversaciones con saludo y despedida con 2 o más;
  - SC-003: al menos una de cada tres respuestas informativas con sticker y nunca dos en una respuesta;
  - SC-005: máximo 8 y sin repeticiones seguidas no permitidas.

### Implementation for User Story 2

- [X] T016 [US2] Actualizar `config/stickers.toml` según data-model §1:
  - `useful_answer` en `valeria-listo` y `valeria-pulgar`, posición `after`;
  - el comentario de prioridad con `useful_answer` al final.

  En `config/agent.toml`: `stickers_per_conversation = 8`, con un comentario de la spec 037.
- [X] T017 [US2] En `src/proyecto_modelos_lenguaje/channels/stickers.py`:
  - **prioridad**: `useful_answer` en `PRIORITY` (al final);
  - **catálogo**: `StickerCatalog` admite varios stickers por situación (`candidates(situation)`);
  - **señales**: `TurnSignals.cited`;
  - **`situations_of`**: agrega `useful_answer`;
  - **`choose`**: aplica la cadencia y la moderación de data-model §5 y elimina la regla «nunca dos respuestas
    seguidas»;
  - **`StickerChoice`**: gana `situation`;
  - **`REPEATABLE`**: `{"valeria-pulgar", "valeria-lindo-dia"}`.
- [X] T018 [US2] En `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - `_choose_sticker` llena `cited` desde `reply.citations`;
  - pasa `last_sticker`, `last_situation` y `off` desde `store.sticker_usage`;
  - guarda la situación con `record_sticker`.

**Checkpoint**: la conversación típica tiene entre dos y cuatro stickers.

---

## Phase 5: User Story 3 - Los stickers nunca restan profesionalismo ni cuidado (Priority: P1)

**Goal**:
- sin stickers en queja, molestia, angustia, crisis, malestar, errores, evidencia insuficiente, datos sensibles o
  acciones rechazadas;
- en inglés, solo stickers sin texto;
- «sin stickers» los apaga en el hilo.

**Independent Test**: a04 a a09 y a11 del conjunto dan 0 stickers, salvo el pulgar en a08.

### Tests for User Story 3

- [X] T019 [P] [US3] Pruebas en `tests/unit/channels/test_stickers.py`:
  - `_excluded` es verdadero con `fallback`, `crisis` y `low_mood` (además de las exclusiones de la spec 034);
  - `OPT_OUT` reconoce «sin stickers», «no me mandes stickers», «no quiero stickers» y «no more stickers», y no
    reconoce «¿qué stickers tienes?»;
  - con `usage.off`, `choose` devuelve `None`;
  - en inglés solo se elige `valeria-pulgar`.
- [X] T020 [P] [US3] Prueba en `tests/api/test_channels_stickers.py`, con el conjunto de T002 (SC-004):
  - a04, a05, a06, a07 y a11 dan 0 stickers;
  - a08 solo el pulgar;
  - a09 no da stickers después de «sin stickers», y la respuesta escrita de ese turno confirma la preferencia en
    una frase.

### Implementation for User Story 3

- [X] T021 [US3] En `src/proyecto_modelos_lenguaje/channels/stickers.py`:
  - `TurnSignals` gana `fallback`, `crisis` y `low_mood`, y `_excluded` los aplica (data-model §5);
  - `OPT_OUT` es la expresión de «sin stickers» (contracts §3);
  - `choose` devuelve `None` con `usage.off`.
- [X] T022 [US3] En `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - **señales**: llena `fallback` (respuesta de evidencia insuficiente o texto fijo), `crisis` (`route ==
    "out_of_scope"` con `scope_reason == "crisis"`, desde la información de ruta del turno) y `low_mood`
    (`agent.style.LOW_MOOD` sobre el mensaje normalizado);
  - **«sin stickers»**: con `OPT_OUT`, llama a `store.set_stickers_off(thread)` y agrega a la respuesta una frase
    breve de confirmación en el idioma del turno («Listo, no te enviaré más stickers.» o «Got it, no more
    stickers.»), definida en los textos del canal.

**Checkpoint**: las tres historias pasan las pruebas.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T023 [P] Actualizar `docs/manual_whatsapp.md` (sección Stickers):
  - cuándo llegan: saludo, respuestas útiles, «ok», gracias, despedida y «Pensando»;
  - cuándo no: quejas, malos momentos, datos sensibles e inglés con texto;
  - cómo apagarlos: «sin stickers».

  En `docs/whatsapp/README.md`: la vía de entrega, la línea del log y `ops check` (`stickers hoy`).
- [X] T024 [P] Actualizar `specs/034-stickers-whatsapp/tasks.md` (notas):
  - T001 se resolvió en la spec 037, con la causa raíz (runtime aislado por plugin) y la vía elegida;
  - el resultado de T001 de esta spec.
- [X] T025 Ejecutar `make check` y `make openclaw-test`; corregir hasta verde.
- [X] T026 Prueba en el teléfono (quickstart §2), con instrucciones previas paso a paso:
  - reiniciar el gateway y el backend;
  - conversación de seis mensajes;
  - revisar `ops check` (`stickers hoy` en verde).

  Registrar SC-001, SC-006 y SC-007 en las notas. Si algún sticker no llega, diagnosticar con el log del gateway
  antes de cerrar.
- [X] T027 Marcar las tareas completadas con [X] y agregar notas de implementación al final de este archivo.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: T001 va primero (decide T011–T013); T002 es libre.
- **Foundational**: T003 → T004. Bloquea US2 y US3, no US1.
- **US1**:
  - T005 y T006 primero, luego T007 → T008 → T009 → T010;
  - T011–T013 solo si T001 lo exige.
- **US2**: depende de la fase 2; T014 y T015, luego T016 → T017 → T018.
- **US3**: depende de US2 (`stickers.py` y `bridge.py` compartidos); T019 y T020, luego T021 → T022.
- **Polish**: T025 y T026 al final; T026 requiere US1.

### User Story Dependencies

- US1 es el MVP: sin entrega no hay stickers.
- US2 los hace activos.
- US3 protege los momentos sensibles. Va después de US2 porque modifica los mismos archivos, pero sus pruebas
  pueden escribirse antes.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- La prueba en el teléfono (T026) cierra la spec; la spec 034 no la hizo.

### Parallel Opportunities

- T001 ∥ T002.
- T003 ∥ T005 ∥ T006.
- T014 ∥ T015.
- T019 ∥ T020.
- T023 ∥ T024.

---

## Parallel Example: User Story 1

```text
# Pruebas primero (fallan):
T005 openclaw/plugins/valeria-bridge/test/bridge.test.ts (vías de entrega y log)
T006 tests/unit/test_ops.py (stickers_today)

# Luego, en orden:
T007 index.ts (findWhatsAppListener) → T008 bridge.ts (log) → T009 log de arranque → T010 ops.py
# Solo si T001 lo exige: T011 parche → T012 pruebas y ops → T013 ADR y constitución
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. T001: prueba en vivo de la vía compartida.
2. US1: entrega con registro y `ops check`.
3. Validar en el teléfono que llega el sticker de bienvenida (los 4 stickers que hoy elige la política vieja ya
   bastan para probar).

### Incremental Delivery

1. US1: llegan.
2. US2: son activos.
3. US3: nunca inoportunos.
4. Documentación, `make check` y prueba completa en el teléfono.

### Parallel Team Strategy

Trabajo secuencial en un solo portátil (restricción del proyecto). [P] solo indica que el orden entre esas tareas es
libre.

---

## Notes

- Sin números de teléfono ni contenido en registros, fixtures ni notas.
- Comentarios y docstrings en español; identificadores en inglés; Ruff con `line-length = 100`.
- Commits, push y PR solo con autorización explícita de jasonCastano o Robertto48, sin `Co-authored-by`.
- El cambio es solo de WhatsApp; no afecta la web. No hace falta avisar a Roberto, salvo por el parche (T013), si
  se instala.

## Notas de implementación (2026-11-28)

- **T001 unido a T007 y T009**: para pedir un solo reinicio del gateway, la sonda es la búsqueda definitiva.
  `src/listener.ts` (`findWhatsAppListener`) prueba la vía compartida, la del parche y la directa, y
  `announceStickerRoute` escribe 30 s después del arranque «stickers listos vía …» o «sin vía de stickers (detalle
  por vía)». **Pendiente**: leer esa línea tras el reinicio; decide si se ejecutan T011–T013 (parche).
- **Cadencias de uso activo**: la medición en demo pedía ajustes respecto a data-model §5.
  - **Respuesta útil**: se salta solo si la anterior también fue una respuesta útil con sticker. Si se salta tras
    cualquier sticker, los «ok» y «gracias» intercalados la dejan sin sticker.
  - **«ok»**: se salta si hubo sticker en las dos respuestas anteriores (`ASSENT_GAP = 2`); si no, la conversación
    de seis mensajes llega a 5 stickers.
  - **Preferencia**: «¡Listo!» antes que el pulgar (`PREFERRED`).
- **Exclusiones**: `style.LOW_MOOD` (spec 036) ahora también reconoce la molestia («estoy muy molesto», «esto no me
  sirve», «pésimo servicio»). Así la queja no recibe el sticker de bienvenida cuando el sentimiento llega vacío, y
  el estilo caleño también se apaga.
- **Presentación**: la primera respuesta lleva «¡Bienvenido!» (o «Hola» si la conversación se retoma) aunque el
  mensaje sea una pregunta (`TurnSignals.introduced`, desde `reply.introduced == "bridge"`).
- **Pruebas de la spec 034 actualizadas** a la política nueva: respuestas seguidas con otra situación, tope 8,
  «¡Listo!» en respuestas con fuentes y la cadencia del «ok». El conjunto `stickers.jsonl` cambió en k01b, k02a,
  k04b, k04d, k05b, k06b, k06c, k08b, k08c, k08d, k09b y k10a. El conjunto nuevo `stickers_active.jsonl` tiene 12
  conversaciones y 44 mensajes.
- **Medición en demo** (`test_spec037_active_use_meets_sc002_to_sc005`):
  - SC-002: la conversación de seis mensajes da 4 stickers;
  - SC-003: la mayoría de las respuestas informativas lleva sticker;
  - SC-004 y SC-005: 0 hallazgos.
- **`ops check`**: `stickers-hoy` leyó el log real del 2026-11-28: «elegidos 4 · entregados 0 · fallidos 10
  (sin-listener) — no llega ninguno». Confirma el diagnóstico y servirá para verificar la corrección.
- **Verificación**: `make check` verde (2593 pytest, 216 vitest y build); `make openclaw-test` verde (8 del parche
  LID y 42 del plugin).
- **T001, resultado en vivo (2026-11-28 06:24 UTC)**: «sin vía de stickers (compartido: sin controlador (cuenta
  default); compartido: sin controlador (cuenta sin cuenta); parche: no instalado; import: sin listener)».
  - El componente registra el controlador (cuenta `default`) en **su** runtime de canales (`connection-controller-
    *.mjs`, `registerChannelRuntimeContext({channelRuntime: getWhatsAppChannelRuntime(), …})`).
  - El `api.runtime.channel` del plugin es otro registro: OpenClaw no comparte el runtime entre plugins.
  - Por eso se ejecutaron T011–T013.
- **T011–T013**:
  - `openclaw/patches/whatsapp-sticker.mjs`: un ancla, la marca `valeria-sticker v1` y salidas 0, 2 y 3;
  - 5 pruebas en `openclaw/patches/test/whatsapp-sticker.test.mjs`;
  - `make openclaw-test` lo incluye;
  - `ops check` muestra `soporte-sticker`;
  - `scripts/openclaw_env.ps1 -Install` lo aplica después de `whatsapp-lid`;
  - ADR 0039 y constitución 2.10.1 (PATCH: segundo parche bajo la regla 8).

  Verificado sin escribir: el anclaje aparece exactamente una vez en el componente instalado (2026.11.10).
- **Verificación final**: `make check` verde (2594 pytest, 216 vitest y build); `make openclaw-test` verde (8 + 5 +
  42).
- **Parche v1 descartado y v2 (2026-11-28, tras dos pruebas en vivo)**:
  - **El v1 no basta**: con el parche v1 aplicado, el aviso seguía en «parche: no instalado», porque los plugins
    no comparten `globalThis` (cargan aislados).
  - **El listener tampoco serviría**: el que arma `monitor-*.mjs` no expone `sendSticker`; solo `sendComposingTo`,
    `sendMessage`, `sendPoll` y `sendReaction`.
  - **El parche v2** (`valeria-sticker v2`):
    - (A) el listener expone `sendSticker` de la API de envío;
    - (B) en `send-*.mjs`, un medio `…/valeria-<nombre>.webp` se envía con `sendSticker`;
    - retira el cambio v1;
    - 6 pruebas, una de ellas ejecuta la función parcheada.
  - **Plugin**: con la marca v2 en disco, envía por el adaptador de salida (la vía de las notas de voz, que sí
    funciona desde el plugin).
  - **`ops check`**: `soporte-sticker` exige las dos partes.
  - **ADR y constitución**: actualizados.
- **Aviso de arranque**: reintenta cada 30 s durante 5 minutos. WhatsApp tardó 85 s en registrarse y conectar
  después del plugin, y el primer aviso salió antes de tiempo.
- **Efecto colateral**: el plugin se carga enlazado desde el repo, así que editar `index.ts` reinicia el gateway.
  El 2026-11-28 a las 06:48 UTC el reinicio dejó el gateway apagado (tarea en «Ready») hasta que se ejecutó
  `-Restart`. Regla operativa: no editar el plugin con el gateway en uso sin avisar.
- **T026, prueba en el teléfono (2026-11-28)**:
  - `-Install` aplicó el parche v2;
  - `ops check`: `whatsapp` vinculado, `soporte-sticker: parche valeria-sticker v2` y log «stickers listos vía
    adaptador»;
  - en la conversación de prueba los stickers llegaron como stickers nativos de WhatsApp y el usuario confirmó que
    todo funcionó (SC-001, SC-006 y SC-007).
- **Spec cerrada**: 27/27 tareas.
