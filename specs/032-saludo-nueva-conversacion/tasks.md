# Tasks: Saludo y presentación al iniciar una conversación

**Input**: Design documents from `specs/032-saludo-nueva-conversacion/`
**Prerequisites**: plan.md, spec.md, research.md (R1–R7), data-model.md, contracts/conversation-start.md,
quickstart.md

**Tests**: incluidas. El plan pide pruebas unitarias por módulo y un guion de simulación con `--check`, y la DoD
del repositorio exige `make check` en verde.

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–031).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: historia de usuario de la spec (US1–US4)

## Path Conventions

Proyecto único: `src/proyecto_modelos_lenguaje/`, `tests/`, `config/`, `docs/` y `openclaw/` en la raíz del
repositorio.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuración del periodo de inactividad.

- [X] T001 Agregar `conversation_idle_hours: int = 12` a `ChannelsConfig` en `src/proyecto_modelos_lenguaje/agent/config.py`, con validación «1 ≤ valor ≤ 720» (`AgentConfigError` con mensaje en español que nombre `channels.conversation_idle_hours`), y la clave `conversation_idle_hours = 12` con comentario en español («horas sin mensajes tras las que el siguiente abre una conversación nueva, spec 032») en `[channels]` de `config/agent.toml`
- [X] T002 [P] Pruebas de la clave en `tests/unit/agent/test_config.py`: valor por defecto 12, lectura desde TOML y rechazo de 0 y 721 (agregar los casos a `test_channel_config_rejects_unsafe_values`)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: la marca de presentación por hilo, la apertura de conversaciones y los textos de la presentación.
Todas las historias dependen de esta fase.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T003 En `src/proyecto_modelos_lenguaje/channels/store.py`:
  - agregar a `MIGRATIONS` la entrada `("channel_threads", "introduced", "INTEGER NOT NULL DEFAULT 1")` y la
    columna `introduced INTEGER NOT NULL DEFAULT 1` en `SCHEMA`. Así los hilos anteriores a la migración quedan
    presentados (research R5);
  - hacer que `ensure_user` y `new_thread` inserten los hilos con `introduced = 0` explícito;
  - agregar `is_introduced(thread_id) -> bool` y `mark_introduced(thread_id) -> None`;
  - verificar que `adopt_thread` conserva el valor de `introduced`.
- [X] T004 En `src/proyecto_modelos_lenguaje/channels/store.py`, agregar
  `open_conversation(user_id, channel, masked, *, idle_hours) -> tuple[str, Literal["first_contact", "inactivity"] | None]`
  (contrato §1):
  - lee `last_seen` y `active_thread_id` **antes** de actualizar `last_seen`;
  - un usuario nuevo crea el usuario y el hilo, y devuelve `"first_contact"`;
  - si `now - last_seen > idle_hours`, cierra el hilo activo (`closed_at`), abre uno nuevo con `introduced = 0` y
    devuelve `"inactivity"`;
  - en otro caso actualiza `last_seen` y devuelve `(hilo_activo, None)`;
  - todo bajo `self._lock` y en una sola transacción;
  - mantener `ensure_user` por compatibilidad, delegando en `open_conversation`.
- [X] T005 [P] Pruebas del almacén en `tests/unit/channels/test_store.py`:
  - migración de una base vieja sin `introduced`: los hilos existentes quedan en 1;
  - los hilos nuevos y `new_thread` quedan en 0;
  - `mark_introduced` e `is_introduced`;
  - `open_conversation` con reloj simulado: `first_contact`; sin motivo antes de 12 h; `inactivity` después de
    12 h, con un hilo distinto y el anterior con `closed_at`;
  - `adopt_thread` conserva `introduced`.
- [X] T006 [P] Crear `src/proyecto_modelos_lenguaje/channels/greeting.py` (contrato §2, research R2 y R3):
  - **`introduction(language, thread_id, name=None)`**:
    - tres variantes por idioma (es/en), elegidas con un hash estable de `thread_id` (`hashlib`, no `hash()`);
    - cada una con dos frases como máximo, que mencionan «Valer-IA», Manuelita, «con fuentes» y que acepta notas de
      voz;
    - sin comandos ni menús;
    - con `name`, el saludo es «¡Hola, {name}!» / «Hi, {name}!».
  - **`identity_line(language)`**: una frase para los errores.
  - **`already_introduced(answer)`**: verdadero si las dos primeras frases mencionan «Valer-IA» o «Valeria», sin
    distinguir mayúsculas ni tildes.
  - **`merge(intro, answer)`**: quita un saludo suelto al inicio de `answer` («¡Hola!», «Hola,», «Hola.», «Hi!»,
    «Hello,», «Buenas,» y variantes con emoji o signos) y antepone `intro` con un espacio.

  Docstrings y comentarios en español.
- [X] T007 [P] Crear `tests/unit/channels/test_greeting.py`:
  - las tres variantes existen y difieren;
  - la misma variante para el mismo hilo;
  - idioma es/en;
  - ≤ 2 frases (contar `.`, `!` y `?` finales);
  - menciona Valer-IA y notas de voz;
  - el nombre aparece en el saludo;
  - `already_introduced` con y sin mención;
  - `merge` quita «¡Hola!», «Hola,» y «Hi!» iniciales pero no un «hola» en medio del texto;
  - sin `/` ni números de menú (`1.`, `2.`).
- [X] T008 [P] Agregar a `ChannelLogRecord` en `src/proyecto_modelos_lenguaje/channels/journal.py` los campos `conversation_start: str | None = None` (valores `first_contact`, `inactivity`, `restart`) e `introduced: str | None = None` (valores `bridge`, `agent`), con comentario «Spec 032: sin texto ni números»; y la prueba en `tests/unit/channels/test_journal.py` de que se serializan y de que su valor por defecto es `None`

**Checkpoint**: el almacén sabe cuándo empieza una conversación y existen los textos de presentación.

---

## Phase 3: User Story 1 - Primera pregunta directa, por texto (Priority: P1) 🎯 MVP

**Goal**: la primera respuesta de un número nuevo abre con saludo y presentación y responde la pregunta en el mismo
mensaje; los turnos siguientes no repiten la presentación.

**Independent Test**: `pml channels simulate --sender +570000000201 --text "¿Qué produce Manuelita?"` en modo demo
devuelve un primer mensaje que empieza con la presentación y trae la respuesta con fuentes. Un segundo mensaje no
la repite.

### Tests for User Story 1

- [X] T009 [P] [US1] Pruebas en `tests/unit/channels/test_bridge.py`, con `FakeService`:
  - número nuevo y pregunta directa: `messages[0]` empieza con la presentación y contiene la respuesta;
    `reply.introduced == "bridge"`;
  - segundo mensaje sin presentación y `introduced is None`;
  - «Hola» con una respuesta del servicio que ya dice «Soy Valer-IA…»: no se duplica (`introduced == "agent"`);
  - respuesta del servicio «¡Hola! ¿En qué te ayudo?»: un solo saludo, sin «¡Hola!» repetido;
  - inglés: presentación en inglés;
  - con `client.name` en el resultado: el saludo usa el nombre;
  - registro con `conversation_start == "first_contact"` solo en el primer turno.
- [X] T010 [P] [US1] Pruebas de exclusiones en `tests/unit/channels/test_bridge.py` (research R7):
  - el aviso de límite (spec 031) no lleva presentación y no marca el hilo;
  - un número bloqueado no recibe nada;
  - los atajos del operador (`/traza`) no presentan ni marcan;
  - una imagen como primer mensaje presenta y explica qué puede recibir;
  - un error del servicio en el primer turno lleva `identity_line` y el hilo queda sin presentar: el siguiente
    turno atendido se presenta;
  - con datos sensibles, el aviso sigue al final y la presentación al inicio.

### Implementation for User Story 1

- [X] T011 [US1] En `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - `ChannelReply` gana `conversation_start: str | None`, `introduced: str | None` y `opening: str | None`;
  - `handle` usa `self.store.open_conversation(..., idle_hours=self.config.conversation_idle_hours)` en lugar de
    `ensure_user` y guarda el motivo en `reply.conversation_start`;
  - `_record` escribe `conversation_start` e `introduced` en `ChannelLogRecord`.
- [X] T012 [US1] En `src/proyecto_modelos_lenguaje/channels/bridge.py`, agregar `_introduce(reply, thread_id, language, name)` (contrato §3) y llamarla en `handle` después de `_dispatch` y antes de `_attach_voice`:
  - aplica solo a `status in {"answered", "unsupported"}` y a eventos que no sean atajos, avisos de límite,
    aprobaciones (`confirm`, `reask`, `expired`) ni la confirmación de reinicio sin pregunta;
  - si `already_introduced(reply.spoken or messages[0])`, marca el origen `agent`;
  - si no, `messages[0] = merge(intro, messages[0])`, `reply.spoken = merge(intro, reply.spoken)`,
    `reply.opening = intro` y el origen `bridge`;
  - en ambos casos llama `store.mark_introduced(thread_id)`;
  - con `status == "error"` en un hilo sin presentar, antepone `identity_line(language)` sin marcar;
  - toma el nombre de `getattr(outcome, "client", None)`. Hay que propagarlo desde `_from_outcome` en
    `reply.client_name`.
- [X] T013 [US1] Verificar que `_short`/`_format` respeten `reply_max_chars` con la presentación antepuesta. Si `messages[0]` excede el límite, la presentación va como mensaje propio antes del resto, en `src/proyecto_modelos_lenguaje/channels/bridge.py`, con prueba en `tests/unit/channels/test_bridge.py`

**Checkpoint**: US1 funciona por texto. Es el MVP.

---

## Phase 4: User Story 2 - Primera solicitud por nota de voz (Priority: P1)

**Goal**: la primera nota de voz de respuesta empieza con el saludo y la presentación; el texto acompañante trae
solo las fuentes.

**Independent Test**: simular con `input_mode: "voice"` una pregunta desde un número nuevo. `reply.voice` existe,
el guion empieza con la presentación y `sources_messages` trae solo las fuentes.

### Tests for User Story 2

- [X] T014 [P] [US2] Pruebas en `tests/unit/channels/test_voice.py`:
  - `for_answer(..., opening="¡Hola! Soy Valer-IA…")` produce un guion que empieza con `opening`, tanto con el
    guion del modelo falso como con el de respaldo;
  - `valid_script` se evalúa sin la presentación;
  - con `with_sources=True` termina en la frase de cierre de la spec 030;
  - sin `opening` el comportamiento es idéntico al actual.
- [X] T015 [P] [US2] Pruebas en `tests/unit/channels/test_bridge.py` con `FakeVoice`:
  - primera nota de voz de un número nuevo: `FakeVoice.for_answer` recibe `opening` y una respuesta sin la
    presentación;
  - `sources_messages` trae solo fuentes;
  - una segunda nota de voz va sin `opening`;
  - una primera nota de voz que es solo un saludo usa `for_text` con la presentación una sola vez;
  - una nota de voz en inglés lleva la presentación en inglés.

### Implementation for User Story 2

- [X] T016 [US2] En `src/proyecto_modelos_lenguaje/channels/voice.py`, agregar `opening: str | None = None` a `ConversationVoice.for_answer`: el guion (modelo o respaldo) se construye con la respuesta recibida y luego queda `f"{opening} {script}"` antes de `with_sources_closing`, con `_unspoken` aplicado a `opening`
- [X] T017 [US2] En `_attach_voice` de `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - si `reply.opening`, pasar `opening=reply.opening` a `for_answer` y la respuesta **sin** la presentación;
  - guardar esa respuesta en `reply.spoken_body` al hacer el `merge` en T012;
  - `for_text` sigue recibiendo `reply.spoken` completo;
  - actualizar el protocolo `VoiceProvider` (o equivalente) y `FakeVoice` en las pruebas.

**Checkpoint**: US1 y US2 funcionan por texto y por voz.

---

## Phase 5: User Story 3 - Regreso después de un tiempo sin escribir (Priority: P2)

**Goal**: después de `conversation_idle_hours`, el siguiente mensaje abre un hilo nuevo con presentación, sin el
contexto anterior y con el perfil conservado.

**Independent Test**: con el reloj del almacén simulado, dos mensajes separados por 13 h. El segundo tiene
`conversation_start == "inactivity"`, otro `thread_id`, la presentación, y el servicio lo recibe como hilo nuevo
(`thread_id=None`).

### Tests for User Story 3

- [X] T018 [P] [US3] Pruebas en `tests/unit/channels/test_bridge.py`:
  - inactividad de 13 h: hilo nuevo, presentación y `FakeService.send` con `thread_id=None`;
  - 11 h: mismo hilo y sin presentación;
  - con `client.name`, el saludo de regreso usa el nombre;
  - el registro marca `conversation_start == "inactivity"`;
  - la memoria aprobada no se borra: `forget` no se llama.

### Implementation for User Story 3

- [X] T019 [US3] Confirmar en `src/proyecto_modelos_lenguaje/channels/bridge.py` que el hilo nuevo por inactividad pasa por `_send` como hilo fresco (`is_started == False`, `adopt_thread`) y que la referencia en memoria de la última traza (`self._last`) no filtra el hilo anterior; ajustar si hace falta

**Checkpoint**: US1–US3 completas.

---

## Phase 6: User Story 4 - Empezar de nuevo a pedido de la persona (Priority: P3)

**Goal**: «empecemos de nuevo» abre un hilo sin presentar. Con una pregunta en el mismo mensaje, la respuesta lleva
la confirmación, la presentación y la respuesta, una vez cada una. Sin pregunta, solo la confirmación, y la
siguiente solicitud se presenta.

**Independent Test**: «empecemos de nuevo y cuéntame de sostenibilidad» da `conversation_start == "restart"` y,
en orden: «Listo, empezamos de cero.», la presentación y la respuesta.

### Tests for User Story 4

- [X] T020 [P] [US4] Pruebas en `tests/unit/channels/test_bridge.py`:
  - reinicio con pregunta: orden confirmación → presentación → respuesta, cada una una sola vez;
  - reinicio sin pregunta: solo «Listo, empezamos de cero. ¿Sobre qué quieres conversar?», sin presentación;
  - el siguiente mensaje sí se presenta;
  - `conversation_start == "restart"`.

### Implementation for User Story 4

- [X] T021 [US4] En `_dispatch` de `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - cuando `intent == "restart"`, fijar el motivo `restart` en la respuesta;
  - excluir de `_introduce` la confirmación sin pregunta (evento `restart`);
  - con pregunta, que `_with_notices` deje la confirmación antes de la presentación: aplicar `_introduce` sobre la
    respuesta del agente **antes** de anteponer los avisos, o insertar la presentación después de los avisos.

**Checkpoint**: las cuatro historias funcionan de forma independiente.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T022 [P] Crear `tests/fixtures/channels/conversation_start.jsonl` con ≥ 10 conversaciones de números ficticios (`+5700000002NN`):
  - pregunta directa, «Hola», nota de voz (`input_mode: "voice"`) y pregunta en inglés;
  - imagen como primer mensaje, datos sensibles y reinicio con pregunta;
  - inactividad simulada;
  - cada una con un segundo turno;
  - el primer mensaje de cada conversación marcado con `"new_conversation": true`.
- [X] T023 Extender `simulate --check` en `src/proyecto_modelos_lenguaje/channels/__main__.py` (contrato §6) para reportar como hallazgo:
  - una primera respuesta sin presentación (`new_conversation` sin `introduced`);
  - una presentación repetida (`introduced` en un turno sin `new_conversation`);
  - una presentación de más de dos frases.

  Agregar el soporte de reloj simulado para la inactividad si el guion lo pide (`"advance_hours": 13`). Con prueba
  en `tests/unit/channels/` que corra el guion en modo demo con 0 hallazgos.
- [X] T024 [P] Agregar en `openclaw/workspace/AGENTS.md` la regla de mejor esfuerzo para el modo degradado: «al inicio de una conversación, saluda y preséntate en una o dos frases (Valer-IA, asistente virtual de Manuelita; cuentas con fuentes y recibes notas de voz) y atiende enseguida la solicitud». Verificar que `tests/unit/test_openclaw_config.py` y la sincronización del workspace siguen en verde
- [X] T025 [P] Documentar en `docs/manual_whatsapp.md` (qué esperar en el primer mensaje y al volver después de 12 h), en `docs/despliegue.md` (`conversation_idle_hours` y los campos `conversation_start`/`introduced` del registro) y en `docs/prompt_log.md` (§3.28: workspace de OpenClaw, presentación del modo degradado; textos fijos de `channels/greeting.py`)
- [X] T026 Ejecutar `make check` (Ruff, formato, pytest y vitest) y `uv run python -m proyecto_modelos_lenguaje.channels simulate --script tests/fixtures/channels/conversation_start.jsonl --check`; corregir hasta tener todo en verde y 0 hallazgos
- [ ] T027 Prueba en el teléfono (manual, quickstart §2). Antes de ejecutar, dar al usuario instrucciones paso a paso:
  1. reiniciar el backend (tarea `ValerIA-Backend`) y esperar ~2 min si se reinicia el gateway;
  2. escribir desde números nuevos por texto y por voz, con y sin «Hola»;
  3. probar «empecemos de nuevo» con pregunta;
  4. revisar `channels.jsonl` (sin números).

  Registrar SC-001 a SC-006 en las notas de este archivo.
- [X] T028 Marcar las tareas completadas con [X] y agregar notas de implementación al final de este archivo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de T001 (`conversation_idle_hours` lo usa `open_conversation`). Bloquea
  todas las historias.
- **US1 (Phase 3)**: depende de la fase 2.
- **US2 (Phase 4)**: depende de la fase 2 y de T012 (`reply.opening` y `spoken_body`).
- **US3 (Phase 5)**: depende de la fase 2 y de T011 (uso de `open_conversation`).
- **US4 (Phase 6)**: depende de T012.
- **Polish (Phase 7)**: depende de las historias que se entreguen. T026 y T027 van al final.

### User Story Dependencies

- US1 es el MVP y la base de US2 y US4 (la función `_introduce`).
- US3 es independiente de US2 y US4: solo necesita la fase 2 y T011.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- `store.py` va antes que `bridge.py`, y `voice.py` antes de `_attach_voice`.

### Parallel Opportunities

- T002, T005, T006, T007 y T008 van en paralelo: son archivos distintos.
- En US1: T009 ∥ T010 (mismo archivo de pruebas; si los escribe una sola persona, en secuencia).
- En US2: T014 ∥ T015.
- En Polish: T022 ∥ T024 ∥ T025.

---

## Parallel Example: User Story 1

```text
# Fase 2, en paralelo:
T005 pruebas del almacén (tests/unit/channels/test_store.py)
T006 channels/greeting.py
T007 tests/unit/channels/test_greeting.py
T008 journal.py + test_journal.py

# US1: pruebas primero (fallan), luego T011 → T012 → T013 en bridge.py (secuencial, mismo archivo)
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fase 1 y fase 2.
2. US1 (T009–T013): un número nuevo recibe la presentación por texto.
3. Validar con `simulate` y `make check`. Ya corrige el caso más reportado.

### Incremental Delivery

1. US1, el MVP por texto.
2. US2, la voz. Con eso quedan cubiertos los dos casos P1 del reporte.
3. US3, la inactividad.
4. US4, el reinicio.
5. Polish: guion de simulación, modo degradado, documentación y prueba en el teléfono.

### Parallel Team Strategy

Trabajo secuencial en un solo portátil (restricción del proyecto). El paralelismo [P] solo indica que el orden entre
esas tareas es libre.

---

## Notes

- Nunca números reales en pruebas ni guiones: solo `+5700000002NN`. Seudónimos `wa-<16 hex>` en el registro.
- UI, comentarios y docstrings en español; identificadores en inglés; Ruff con `line-length = 100`.
- Commits, push y PR solo con autorización explícita de jasonCastano o Robertto48, sin `Co-authored-by` ni
  firmas.
- No se cambian `prompts/agent.md` ni `prompts/voice_script.md` (research R1 y R6).

---

## Notas de implementación (2026-11-27)

- **Hecho**: T001–T026 y T028. **Pendiente**: T027 (prueba en el teléfono, manual), con las instrucciones que se dan
  al usuario antes de ejecutarla.
- **Verificación automática**:
  - `make check` en verde: 2382 pruebas Python y 216 web;
  - pruebas nuevas en `test_greeting.py` (15), `test_store.py`, `test_bridge.py` (15 nuevas), `test_voice.py`,
    `test_journal.py`, `test_config.py` y `tests/api/test_channels_conversation_start.py`.
- **Simulación real** (DeepSeek, voz Phonon; backend temporal en el puerto 8011 con estado temporal, sin tocar el
  servicio en uso): `conversation_start.jsonl` con 11 conversaciones y 22 mensajes, **0 hallazgos** de formato
  y presentación, y 0 comandos.
  - En el registro: 10 aperturas con presentación del canal (`bridge`), 1 del modelo (`agent`, ante «Hola») y
    1 por reinicio (`restart`).
  - Los 10 turnos de seguimiento salieron sin presentación, y se enviaron 6 notas de voz.
  - Una primera corrida se cortó por un error de codificación de la consola al imprimir «✗» con la salida
    redirigida (código de la spec 029). Se repitió con `PYTHONIOENCODING=utf-8`; ese hallazgo no se repitió.
- **SC-006** (inactividad): no se puede simular por HTTP (reloj real). Queda cubierto con reloj simulado en
  `test_store.py` y `test_bridge.py` (13 h: hilo nuevo, presentación con nombre y perfil conservado; 11 h: mismo
  hilo). El guion usa números ficticios nuevos en cada corrida (`fresh_sender`) para poder repetirse.
- **Desvíos menores del plan**:
  - la clase de voz es `ChannelVoice` (el contrato decía `ConversationVoice`);
  - la longitud de la presentación (≤ 2 frases) se garantiza con las variantes y `test_greeting.py`, no en
    `--check`;
  - `simulate --sender` ahora tiene un valor ficticio por defecto (`+570000000001`), para que el comando
    documentado con `--script` funcione sin él;
  - en modo demo, el `--check` de la prueba de API solo evalúa la presentación, porque el modelo guionado mezcla
    idiomas: las revisiones de formato de la spec 029 se miden en modo real.
- **Sin enmienda constitucional** (regla 22 vigente). No cambian `prompts/agent.md` ni `prompts/voice_script.md`.
