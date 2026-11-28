# Tasks: Respuesta automática a cuentas de WhatsApp identificadas solo por ID (LID)

**Input**: Design documents from `specs/033-whatsapp-remitentes-lid/`
**Prerequisites**: plan.md, spec.md, research.md (R1–R9), data-model.md, contracts/lid-support.md, quickstart.md

**Tests**: incluidas. El plan pide pytest, `node --test` del parche y `npm test` del puente, y la DoD exige
`make check` en verde.

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–032).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: historia de usuario de la spec (US1–US4)

## Path Conventions

Proyecto único: `src/proyecto_modelos_lenguaje/`, `tests/`, `config/`, `docs/`, `scripts/` y `openclaw/` en la raíz
del repositorio.

**Regla de privacidad en todas las tareas**: nunca números ni ID reales. En pruebas se usan ID ficticios como
`10000000000001@lid` y números `+5700000003NN`; ningún registro lleva dígitos de ID.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuración de la antigüedad máxima de un mensaje.

- [X] T001 Agregar `stale_minutes: int = 15` a `ChannelsConfig` en `src/proyecto_modelos_lenguaje/agent/config.py` con validación «1 ≤ valor ≤ 1440» (en el diccionario `limits` de `channels_config`), y la clave `stale_minutes = 15` con comentario en español («minutos tras los que un mensaje recibido tarde se descarta sin responder, spec 033») en `[channels]` de `config/agent.toml`
- [X] T002 [P] Pruebas en `tests/unit/agent/test_config.py`: `channels.stale_minutes == 15`, y rechazo de 0 y 1441 en `test_channel_config_rejects_unsafe_values`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: identidad seudonimizada para remitentes `…@lid` y campo de registro. Todas las historias dependen de
esta fase.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T003 [P] Pruebas en `tests/unit/channels/test_identity.py` (research R6, data-model):
  - `normalize_sender("10000000000001@lid") == "lid:10000000000001"`, también con `@hosted.lid` y con sufijo
    `:12`;
  - rechazo de `abc@lid`, de `1234@lid` (menos de 5 dígitos) y de más de 20 dígitos;
  - `pseudonym` estable, con forma `^wa-[0-9a-f]{16}$` y distinto del seudónimo de un número con los mismos
    dígitos;
  - `mask("10000000000001@lid") == "ID ••••0001"`;
  - los números E.164 y JID `@s.whatsapp.net` siguen igual.
- [X] T004 Implementar en `src/proyecto_modelos_lenguaje/channels/identity.py`:
  - patrón `WHATSAPP_LID = ^(\d{5,20})(?::\d+)?@(?:lid|hosted\.lid)$`;
  - `normalize_sender` prueba primero el LID y devuelve `lid:<dígitos>`;
  - `pseudonym` aplica el HMAC sobre ese valor normalizado;
  - `mask` devuelve `ID ••••<4 últimos>` para `lid:`;
  - `sender_kind(raw, channel) -> Literal["phone", "lid", "telegram"]`.

  Docstrings en español, mencionando la spec 033.
- [X] T005 [P] Agregar `sender_kind: str | None = None` a `ChannelLogRecord` en `src/proyecto_modelos_lenguaje/channels/journal.py` (comentario «Spec 033: phone | lid | telegram, nunca el valor») y la prueba de serialización en `tests/unit/channels/test_journal.py`

**Checkpoint**: el backend sabe seudonimizar un ID de WhatsApp.

---

## Phase 3: User Story 1 - Una cuenta identificada solo por ID recibe respuesta por texto (Priority: P1) 🎯 MVP

**Goal**: los mensajes de cuentas solo-ID dejan de quedar en reintentos y reciben respuesta en su chat.

**Independent Test**: con el parche aplicado a copias de los archivos del componente, el normalizador devuelve el
`…@lid` como remitente. El backend responde a `sender: "10000000000001@lid"` con presentación y respuesta, y
registra `sender_kind: "lid"`.

### Tests for User Story 1

- [X] T006 [P] [US1] Crear `openclaw/patches/test/whatsapp-lid.test.mjs` (`node --test`), con fragmentos mínimos que copian textualmente los anclajes del contrato (§1):
  - un `package.json` con versión `2026.11.10`;
  - `dist/.setup/monitor-x.mjs` con la línea `const from = group ? remoteJid : await socketSession.resolveInboundJid(remoteJid);` y el `throw new Error("WhatsApp inbound LID identity unavailable")`;
  - `dist/.setup/normalize-target-x.mjs` con `const phone = extractUserJidPhone(candidate);\n\tif (phone) {`.

  Todo bajo un directorio temporal con la estructura `npm/projects/openclaw-whatsapp-test/node_modules/@openclaw/whatsapp`.
  Casos:
  - `--check` dice `ausente`;
  - aplicar produce `aplicado`, deja la marca `valeria-lid v1` en ambos archivos y crea `*.orig`;
  - una segunda ejecución dice `parcheado` y no cambia los archivos;
  - sin el `throw` dice `nativo` y no escribe;
  - con otra versión y el `throw` presente sale con código 1 sin escribir;
  - sin anclajes sale con código 1 sin escribir;
  - sin plugin dice `sin-plugin` y sale con código 1.
- [X] T007 [P] [US1] Pruebas en `tests/unit/channels/test_bridge.py`:
  - un mensaje con `sender="10000000000001@lid"` se responde (presentación de la spec 032 incluida);
  - `user_id` empieza con `wa-`;
  - el registro tiene `sender_kind == "lid"` y no contiene `10000000000001`;
  - un segundo mensaje continúa el mismo hilo;
  - con número, `sender_kind == "phone"`.
- [X] T008 [P] [US1] Prueba de contrato en `tests/api/test_channels_api.py`: `POST /api/channels/messages` con `sender: "10000000000001@lid"` responde 200 y `status: "answered"`, y `GET /api/channels/status` no contiene los dígitos del ID

### Implementation for User Story 1

- [X] T009 [US1] Crear `openclaw/patches/whatsapp-lid.mjs` (ESM, sin dependencias, comentarios en español) según el contrato §1:
  - argumentos `--state-dir` y `--check`;
  - busca el plugin con `fs.readdirSync` en `npm/projects/openclaw-whatsapp-*`;
  - **reemplazo A** (entrada) exactamente como en el contrato;
  - conteo de anclajes exactamente 1;
  - copia `*.orig` antes de escribir;
  - verificación posterior;
  - salida `soporte-lid: <estado>` y código 0 o 1.

  El reemplazo B se agrega en T014; en esta tarea el script ya debe soportar una lista de reemplazos por archivo.
- [X] T010 [US1] En `scripts/openclaw_env.ps1`, dentro de `Sync-ValeriaConfig` (después de `openclaw plugins install --link …valeria-bridge`), ejecutar `node (Join-Path $Repo "openclaw\patches\whatsapp-lid.mjs") --state-dir $State`. Si el código es distinto de 0, emitir `Write-Warning` con la salida y continuar; documentar en el comentario de cabecera que `-Install` aplica el parche de la spec 033. Verificar el análisis sintáctico del script con `[System.Management.Automation.Language.Parser]::ParseFile`.
- [X] T011 [US1] En `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - calcular `sender_kind` con `identity.sender_kind(message.sender, message.channel)`;
  - guardarlo en la respuesta y escribirlo en `_record` (`ChannelLogRecord.sender_kind`);
  - confirmar que `mask` y `pseudonym` aceptan el LID sin otros cambios (`handle` y `open_conversation`).

**Checkpoint**: US1 lista en pruebas automáticas. La prueba real va en T026.

---

## Phase 4: User Story 2 - La misma cuenta recibe notas de voz (Priority: P1)

**Goal**: la nota de voz de respuesta llega al chat `…@lid`, no a un número falso.

**Independent Test**: con el parche, `normalizeWhatsAppTarget("10000000000001@lid")` devuelve
`"10000000000001@lid"` (no `+10000000000001`), y `voiceCommandArgs` acepta ese destino.

### Tests for User Story 2

- [X] T012 [P] [US2] Extender `openclaw/patches/test/whatsapp-lid.test.mjs`: después de aplicar, importar dinámicamente una copia del `normalize-target-x.mjs` de prueba (con un `extractUserJidPhone`, `WHATSAPP_LID_RE` y un `normalizeE164` mínimos) y comprobar que `normalizeWhatsAppTarget("10000000000001@lid") === "10000000000001@lid"` y que `"+573000000301"` sigue igual
- [X] T013 [P] [US2] En `openclaw/plugins/valeria-bridge/test/bridge.test.ts`:
  - `voiceCommandArgs("whatsapp", "10000000000001@lid", "a.ogg")` incluye `--target 10000000000001@lid`;
  - se siguen rechazando `"+57; rm -rf /"` y `"abc@lid"`;
  - `dispatch` con `senderId` `…@lid` llama a `sendVoice` con ese destino;
  - los logs no contienen los dígitos (`maskDigits`).

### Implementation for User Story 2

- [X] T014 [US2] Agregar el **reemplazo B** (salida, `normalize-target-*.mjs`) a `openclaw/patches/whatsapp-lid.mjs`, exactamente como en el contrato §1: `lidTarget = candidate.match(WHATSAPP_LID_RE)` antes de `extractUserJidPhone`, con la marca `/* valeria-lid v1 */`. El estado `parcheado` exige la marca en ambos archivos.
- [X] T015 [US2] En `openclaw/plugins/valeria-bridge/src/bridge.ts`, `voiceCommandArgs` acepta destinos `^\d{5,20}@(lid|hosted\.lid)$` además de E.164; comentario «spec 033». Ejecutar `npm test` en `openclaw/plugins/valeria-bridge`.

**Checkpoint**: US1 y US2 completas en pruebas automáticas.

---

## Phase 5: User Story 3 - Los mensajes atascados no se pierden (Priority: P2)

**Goal**: un mensaje retenido de más de 15 minutos no recibe una respuesta tardía; uno reciente se responde una sola
vez.

**Independent Test**: un mensaje con `received_at` de hace 20 min devuelve `ignored` con evento `stale` y no llama
al servicio; uno de hace 5 min se responde; el mismo `message_id` dos veces se responde una vez.

### Tests for User Story 3

- [X] T016 [P] [US3] Pruebas en `tests/unit/channels/test_bridge.py` con el reloj simulado:
  - `received_at` 20 min antes: `status == "ignored"`, `event == "stale"`, `service.calls == []` y el registro
    con `event: "stale"`;
  - `received_at` 5 min antes: respondido;
  - `received_at` ausente o inválido: se responde, sin descartar;
  - duplicado: una sola respuesta.

### Implementation for User Story 3

- [X] T017 [US3] En `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - verificar que `InboundMessage` tenga `received_at` (si no, agregarlo desde la API en `src/proyecto_modelos_lenguaje/api.py`);
  - en `handle`, después de la deduplicación y antes de `_gate`, descartar con `ChannelReply("ignored", event="stale")` si `store.now() - received_at > stale_minutes`;
  - comparar en UTC y tolerar valores sin zona o inválidos (en ese caso, no descartar).

**Checkpoint**: US3 completa.

---

## Phase 6: User Story 4 - El equipo verifica y protege el canal (Priority: P2)

**Goal**: `ops check` muestra el estado del soporte; el operador puede bloquear por seudónimo.

**Independent Test**:
- `ops check` sobre un estado con el plugin parcheado da `soporte-lid` ✅; sin parche da ❌ con la instrucción
  `-Install`; con la versión nativa da ✅;
- `pml channels block --pseudonym wa-…` bloquea sin número.

### Tests for User Story 4

- [X] T018 [P] [US4] Pruebas en `tests/unit/test_ops.py`:
  - `lid_support(state_dir)` con fragmentos de prueba en `tmp_path` (los mismos de T006, generados por un
    helper);
  - el estado `parcheado` es OK;
  - `ausente` es `ok=False` y el detalle menciona `openclaw_env.ps1 -Install`;
  - `nativo` es OK;
  - sin plugin es `ok=False`;
  - `ops_check` incluye la comprobación `soporte-lid`;
  - sin `node` en el PATH, la comprobación no falla de forma brusca: diagnóstico Python equivalente o mensaje
    claro.
- [X] T019 [P] [US4] Pruebas en `tests/unit/channels/test_cli_operator.py`: `block --pseudonym wa-0123456789abcdef` y `unblock --pseudonym …` funcionan; `--pseudonym` inválido sale con error sin eco del valor; `--sender` y `--pseudonym` juntos dan error de argparse; la salida nunca contiene un número

### Implementation for User Story 4

- [X] T020 [US4] En `src/proyecto_modelos_lenguaje/ops.py`, agregar `lid_support(state_dir=None) -> CheckResult("soporte-lid", …)` e incluirla en `ops_check` después de `whatsapp`:
  - hace el diagnóstico en Python (lee `package.json` y los archivos con `glob`, igual que el script, y busca la
    marca y el `throw`), sin depender de `node`;
  - mensajes en español: «parche valeria-lid v1», «nativo del componente», «falta: ejecuta
    `.\scripts\openclaw_env.ps1 -Install`», «componente de WhatsApp no instalado».
- [X] T021 [US4] En `src/proyecto_modelos_lenguaje/channels/__main__.py`:
  - `block` y `unblock` aceptan `--pseudonym` (grupo mutuamente excluyente con `--sender`, uno requerido);
  - `--pseudonym` valida `^wa-[0-9a-f]{16}$`;
  - en `run_operator`, si llega el seudónimo se usa directo;
  - se actualiza el docstring de uso.

**Checkpoint**: las cuatro historias pasan sus pruebas automáticas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T022 [P] Escribir `docs/decisions/0038-whatsapp-remitentes-lid.md` (contexto, decisión de parche versionado con anclajes, alternativas, consecuencias, salida cuando OpenClaw lo corrija) y enmendar `CONSTITUTION.md` a **2.10.0** (MINOR):
  - regla 8: un parche versionado, anclado y verificado por `ops check` puede corregir un defecto del componente
    de WhatsApp mientras no exista la corrección oficial (ADR 0038);
  - regla 10: los ID de WhatsApp (`…@lid`) se seudonimizan igual que los números y nunca se registran;
  - fila del historial y las dos líneas de versión;
  - el README menciona la constitución 2.10.0.
- [X] T023 [P] Documentar en `docs/despliegue.md` (§3.5 o §3.7: el parche, `node openclaw\patches\whatsapp-lid.mjs --check`, `soporte-lid` en `ops check`, qué hacer si se reinstala o actualiza el componente, `--pseudonym`, `stale_minutes`), en `docs/manual_whatsapp.md` (cualquier cuenta recibe respuesta, también las que WhatsApp entrega sin número) y en la guía de respaldo de Roberto (`-Install` aplica el parche; `ops check` debe mostrar `soporte-lid` ✅)
- [X] T024 [P] Agregar al `Makefile` un objetivo `openclaw-test` (`node --test openclaw/patches/test` y `npm test` en `openclaw/plugins/valeria-bridge`) con comentario `##` en español; no se agrega a CI
- [X] T025 Ejecutar `make check`, `node --test openclaw/patches/test` y `npm test` del puente; corregir hasta tener todo en verde
- [ ] T026 Activación y prueba real (manual, quickstart §2–§3). Antes de ejecutar, dar al usuario instrucciones paso a paso:
  1. `node openclaw\patches\whatsapp-lid.mjs --check` (esperado: `ausente`);
  2. reiniciar el backend;
  3. `.\scripts\openclaw_env.ps1 -Install` y esperar unos 2 minutos;
  4. `uv run pml ops check` (`soporte-lid` ✅);
  5. desde la cuenta que falló, escribir por texto y por voz;
  6. revisar `channels.jsonl` (`sender_kind: "lid"`, y `stale` para el mensaje retenido) y el registro del gateway
     (sin `LID identity unavailable`).

  Si falla, revertir con `openclaw plugins install @openclaw/whatsapp --force` y `-Restart`, y documentar la
  limitación. Registrar SC-001 a SC-006 en las notas.
- [X] T027 Marcar las tareas completadas con [X] y agregar notas de implementación al final de este archivo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: sin dependencias de la fase 1, salvo el orden de ejecución. Bloquea las historias.
- **US1 (Phase 3)**: depende de la fase 2.
- **US2 (Phase 4)**: depende de T009 (el script del parche admite varios reemplazos).
- **US3 (Phase 5)**: depende de T001 (`stale_minutes`) y de la fase 2.
- **US4 (Phase 6)**: depende de T009 y T014 para conocer los estados del parche, y de la fase 2.
- **Polish (Phase 7)**: T025 y T026 van al final; T026 requiere T010 y T014–T015.

### User Story Dependencies

- US1 es el MVP: sin ella nada llega al backend.
- US2 completa la voz, sobre el mismo script.
- US3 y US4 son independientes entre sí.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- El script del parche (T009) va antes que su integración en `openclaw_env.ps1` (T010).

### Parallel Opportunities

- T002, T003 y T005 van en paralelo.
- En US1: T006 ∥ T007 ∥ T008.
- En US2: T012 ∥ T013.
- En US4: T018 ∥ T019.
- En Polish: T022 ∥ T023 ∥ T024.

---

## Parallel Example: User Story 1

```text
# Pruebas primero (fallan):
T006 openclaw/patches/test/whatsapp-lid.test.mjs
T007 tests/unit/channels/test_bridge.py (remitente …@lid)
T008 tests/api/test_channels_api.py (contrato …@lid)

# Luego, en orden:
T009 openclaw/patches/whatsapp-lid.mjs → T010 scripts/openclaw_env.ps1 → T011 channels/bridge.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1 y 2.
2. US1: parche de entrada, integración en `-Install` y backend con `…@lid`.
3. Validar con pruebas automáticas y la prueba real por texto. Ya corrige el fallo reportado.

### Incremental Delivery

1. US1 (texto) y US2 (voz): los dos P1.
2. US3: mensajes tardíos.
3. US4: verificación y bloqueo por seudónimo.
4. Polish: ADR, constitución, documentación y prueba real completa.

### Parallel Team Strategy

Trabajo secuencial en un solo portátil (restricción del proyecto). [P] solo indica que el orden entre esas tareas es
libre.

---

## Notes

- El parche nunca se aplica a mano; solo por `openclaw_env.ps1 -Install` (FR-012).
- Si `@openclaw/whatsapp` cambia de versión, el parche no toca nada y `ops check` lo reporta (FR-013).
- UI, comentarios y docstrings en español; identificadores en inglés; Ruff con `line-length = 100`.
- Commits, push y PR solo con autorización explícita de jasonCastano o Robertto48, sin `Co-authored-by`. La
  enmienda 2.10.0 requiere a ambos integrantes.

---

## Notas de implementación (2026-11-27)

- **Hecho**: T001–T025 y T027. **Pendiente**: T026 (activación y prueba real con la cuenta solo-ID), manual y
  con instrucciones previas al usuario.
- **Verificación automática**:
  - `make check` en verde: 2404 pruebas Python y 216 web;
  - `make openclaw-test` en verde: 8 pruebas del parche y 33 del plugin;
  - pre-commit sobre los archivos tocados en verde.
- **Parche sobre el código real**: se aplicó a una **copia** de los archivos instalados de
  `@openclaw/whatsapp` 2026.11.10, con resultado `aplicado`, marca en ambos archivos y `node --check` válido.
  La instalación real no se tocó: `--check` reporta `ausente` hasta que el usuario ejecute `-Install`.
- **Hallazgos durante la implementación**:
  - la API normaliza el remitente antes del bridge, así que `normalize_sender` acepta también `lid:<dígitos>`
    (idempotente);
  - la regla de antigüedad descarta solo entre 15 minutos y 1 día. Una marca más vieja o futura (por ejemplo, otra
    unidad de tiempo) se atiende, para que un error de marca nunca deje el canal en silencio;
  - `voiceCommandArgs` exige en WhatsApp un E.164, un JID de número o un ID `…@lid` (antes aceptaba cualquier
    texto con `@`).
- **Gobierno**: ADR 0038 y constitución 2.10.0 (reglas 8 y 10 e historial). Requieren la aprobación de ambos
  integrantes.
- **Fuera de alcance**:
  - reportar el defecto al proyecto OpenClaw (requiere autorización);
  - unificar identidades ID ↔ número (research R8).
