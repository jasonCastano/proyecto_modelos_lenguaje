# Tasks: Valer-IA atiende a cualquier número de WhatsApp

**Input**: Design documents from `specs/031-valeria-cualquier-numero/`

**Prerequisites**:

- plan.md
- spec.md
- research.md (R1–R7)
- data-model.md
- contracts/channel-open-access.md
- quickstart.md

**Tests**: incluidas. La DoD del proyecto exige pruebas y la spec define criterios verificables (SC-001 a SC-005).

**Organization**: por historia de usuario:

- US1 y US2 son P1;
- US3 es P2;
- US4 es P3.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1–US4)

## Path Conventions

- Backend: `src/proyecto_modelos_lenguaje/{channels,agent}/`, `src/proyecto_modelos_lenguaje/ops.py`
- Configuración: `config/agent.toml`, `.env.example`
- Gateway: `scripts/openclaw_env.ps1`
- Pruebas: `tests/unit/channels/`, `tests/unit/test_ops.py`, `tests/api/test_channels_api.py`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuración de límites y operadores.

- [X] T001 [P] En `src/proyecto_modelos_lenguaje/agent/config.py` (`ChannelsConfig`) y `config/agent.toml`
  (`[channels]`), agregar con comentarios en español:
  - `rate_window_minutes = 10`
  - `rate_max_messages = 20`
  - `daily_max_messages = 100`
  - Actualizar la prueba de configuración en `tests/unit/agent/test_config.py` para leer los tres valores.
- [X] T002 [P] En `.env.example`, agregar `VALERIA_OPERATORS=` con el comentario «Seudónimos wa-<16 hex> de los
  números de prueba del equipo (sin límites; únicos con atajos del operador en modo abierto). Se calculan con
  `pml channels pseudonym`. Nunca números.»

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: lógica pura de límites y almacenamiento. US3 y US4 dependen de esta fase; US1 y US2 no.

- [X] T003 Crear `src/proyecto_modelos_lenguaje/channels/limits.py` con:
  - **`operators() -> frozenset[str]`**: lee `VALERIA_OPERATORS`, separados por comas, sin vacíos.
  - **`@dataclass Usage(window_start: datetime, window_count: int, window_notified: bool, day: str, day_count: int,
    day_notified: bool)`**.
  - **`limit_decision(usage: Usage | None, now: datetime, config: ChannelsConfig, *, operator: bool) -> tuple[str,
    Usage]`**, con decisión `"allow" | "notify_rate" | "notify_daily" | "silent"`, en este orden (data-model §3):
    1. operador → `allow` sin contar;
    2. `day_count ≥ daily_max_messages` → `notify_daily` si `!day_notified`; si no, `silent`;
    3. `window_count ≥ rate_max_messages` → `notify_rate` si `!window_notified`; si no, `silent`;
    4. si no, `allow` e incrementa los dos contadores.
  - **Reinicios**: la ventana se reinicia cuando `now − window_start ≥ rate_window_minutes`, y el día cuando cambia
    `day` (`YYYY-MM-DD` en hora local).
- [X] T004 [P] Pruebas en `tests/unit/channels/test_limits.py`:
  - **Ventana**: 20 mensajes `allow`, el 21 `notify_rate` y del 22 al 60 `silent`. A los 10 minutos vuelve a `allow`.
  - **Día**: con 100 en el día → `notify_daily` una vez y luego `silent`; al día siguiente, `allow`.
  - **Operador**: siempre `allow` y sin contar.
  - **`operators()`**: ignora espacios y vacíos.
  - **SC-003**: con 60 mensajes seguidos, 1 aviso y como máximo 20 `allow`.
- [X] T005 En `src/proyecto_modelos_lenguaje/channels/store.py`:
  - **Migración aditiva** en `_migrate`, con las tablas `channel_usage(user_id TEXT PRIMARY KEY, window_start TEXT,
    window_count INTEGER, window_notified INTEGER, day TEXT, day_count INTEGER, day_notified INTEGER)` y
    `channel_blocked(user_id TEXT PRIMARY KEY, blocked_at TEXT)`.
  - **Métodos**:
    - `get_usage(user_id) -> Usage | None`;
    - `save_usage(user_id, usage)`;
    - `block(user_id) -> bool`;
    - `unblock(user_id) -> bool`;
    - `is_blocked(user_id) -> bool`;
    - `blocked() -> list[tuple[str, str]]`.
  - Todo con seudónimos, nunca números.
- [X] T006 [P] Pruebas en `tests/unit/channels/test_store.py`:
  - el uso se guarda y se lee igual;
  - bloquear dos veces no duplica;
  - desbloquear un desconocido devuelve `False`;
  - una base anterior sin las tablas nuevas migra sin perder hilos.

**Checkpoint**: `uv run pytest tests/unit/channels/test_limits.py tests/unit/channels/test_store.py` en verde.

---

## Phase 3: User Story 1 - Cualquier persona puede escribirle a Valer-IA (Priority: P1) 🎯 MVP

**Goal**: con el canal abierto, un número desconocido recibe el mismo trato que un número de prueba, con su propia
conversación.

**Independent Test**: pruebas del puente y de la API con números que nunca escribieron. Luego, quickstart §3 con un
número real nuevo.

### Tests for User Story 1

- [X] T007 [P] [US1] Prueba en `tests/unit/channels/test_bridge.py`: dos remitentes nuevos distintos
  (`+570000000101` y `+570000000102`) →
  - cada uno recibe `answered`;
  - `thread_id` distintos;
  - las llamadas al servicio tienen `user_id` distintos (seudónimos `wa-…`);
  - una nota de voz de uno de ellos recibe `voice` y `sources_messages` (specs 029–030).
- [X] T008 [P] [US1] Prueba de privacidad en `tests/api/test_channels_api.py` (SC-005):
  - 3 remitentes distintos escriben (texto y voz);
  - después, ni `channels.jsonl`, ni el registro diario del espacio de trabajo, ni `channels.sqlite3` (leído como
    bytes), ni `GET /api/channels/status` contienen ninguno de los tres números completos.

### Implementation for User Story 1

- [X] T009 [US1] Verificar en `openclaw/openclaw.json5` que el modo abierto cumple la regla de OpenClaw:
  - `dmPolicy: "${WA_DM_POLICY}"` y `allowFrom` con `"*"` cuando `WA_DM_POLICY=open`;
  - `groupPolicy: "disabled"`.
  - Actualizar el comentario de la plantilla citando la regla («dmPolicy="open" requiere allowFrom con "*"») y que
    `pairing` no se usa, porque enviaría códigos a cada persona nueva.
- [X] T010 [US1] En `scripts/openclaw_env.ps1` (`-Mode open`), después de abrir:
  - imprimir el aviso «Modo ABIERTO: cualquier número puede escribirle a Valer-IA. Espera ~2 min a que el gateway
    escuche WhatsApp antes de probar. Ciérralo al terminar el proyecto: -Mode closed»;
  - en `-Mode closed` sin números de prueba guardados, pedir confirmación (`Read-Host`), salvo con el parámetro nuevo
    `-Force`.

**Checkpoint**: con `-Mode open`, cualquier número recibe respuesta. Sin límites todavía.

---

## Phase 4: User Story 2 - Abrir y cerrar el canal es un paso simple y verificable (Priority: P1)

**Goal**: el operador sabe en todo momento si el canal está abierto o cerrado.

**Independent Test**: `uv run pytest tests/unit/test_ops.py`. `ops check` muestra `modo-canal` según
`WA_DM_POLICY` del `.env` externo.

### Tests for User Story 2

- [X] T011 [P] [US2] Pruebas en `tests/unit/test_ops.py` con un `.env` temporal (vía `OPENCLAW_STATE_DIR`):
  - **Abierto**: `WA_DM_POLICY=open` → `CheckResult("modo-canal", True, "ABIERTO al público (recuerda cerrarlo al
    terminar el proyecto)")`.
  - **Cerrado**: `allowlist` con dos `WA_ALLOW_n` → `"cerrado (2 números de prueba)"`.
  - **Sin archivo**: `ok=False` y «sin .env de OpenClaw».
  - **Privacidad**: la salida nunca contiene dígitos de los números.

### Implementation for User Story 2

- [X] T012 [US2] En `src/proyecto_modelos_lenguaje/ops.py`:
  - función `channel_mode(state_dir: Path | None = None) -> CheckResult`;
  - lee **solo** las claves `WA_DM_POLICY` y `WA_ALLOW_1..3` de `<OPENCLAW_STATE_DIR o %USERPROFILE%\.openclaw-valeria>\.env`;
  - cuenta los números sin mostrarlos;
  - se agrega a `ops_check` antes de `gateway`.
- [X] T013 [P] [US2] Documentar en `docs/despliegue.md` y `docs/manual_whatsapp.md`:
  - abrir y cerrar con `-Mode open|closed`;
  - esperar ~2 min;
  - verificar con `ops check`;
  - el canal abierto atiende a cualquier persona y se cierra al terminar el proyecto.

**Checkpoint**: US1 + US2 listas: el canal se abre y su estado es verificable.

---

## Phase 5: User Story 3 - Protecciones del canal abierto (Priority: P2)

**Goal**: límites por número, bloqueo y atajos del operador restringidos.

**Independent Test**: `uv run pytest tests/unit/channels/test_bridge.py -k "limit or block or operator"` y la prueba
de API de límites.

### Tests for User Story 3

- [X] T014 [P] [US3] Pruebas en `tests/unit/channels/test_bridge.py`, con `rate_max_messages=3` y
  `daily_max_messages=5` en la config de prueba:
  - **Ventana**: 3 mensajes `answered`; el 4.º es `busy` con el aviso del contrato §1 en español; el 5.º es `ignored`
    sin mensajes; el servicio se llamó 3 veces.
  - **Inglés**: el aviso del 4.º en inglés si el mensaje es en inglés.
  - **Día**: aviso diario y `ignored` después.
  - **Operador**: con `VALERIA_OPERATORS` = su seudónimo, sin límites.
  - **Registro**: `event` en `channels.jsonl` (`rate_limited`, `daily_capped`).
- [X] T015 [P] [US3] Pruebas en `tests/unit/channels/test_bridge.py`:
  - **Bloqueo**: `store.block(seudónimo)` → `ignored`, `event: "blocked"`, sin llamada al servicio.
  - **Atajos**: con `VALERIA_OPERATORS` definido, `/traza` de un no operador se trata como conversación (llama al
    servicio y no devuelve la traza); de un operador, devuelve la traza.
  - **Compatibilidad**: sin `VALERIA_OPERATORS`, el comportamiento actual no cambia.
- [X] T016 [P] [US3] Pruebas del CLI en `tests/unit/channels/test_cli_operator.py`:
  - **`pseudonym --sender +570000000101`**: imprime `wa-` + 16 hex, igual a `pseudonym()` con la sal del entorno.
  - **`block` / `unblock` / `blocked`**: afectan el almacén del estado temporal.
  - **Privacidad**: ninguna salida contiene el número.

### Implementation for User Story 3

- [X] T017 [US3] En `src/proyecto_modelos_lenguaje/channels/bridge.py` (`handle`), justo después de la deduplicación
  (`store.seen`) y antes de adquirir el candado de la persona:
  - **Bloqueados**: si `store.is_blocked(user_id)`, devolver `ChannelReply("ignored", event="blocked")` y
    registrar.
  - **Límites**:
    - calcular `limit_decision(store.get_usage(user_id), now, config, operator=user_id in operators())`;
    - guardar el uso;
    - `notify_rate` / `notify_daily` → `ChannelReply("busy", self._short(TEXTS[language]["rate_limited" |
      "daily_capped"], language))` con `event` igual;
    - `silent` → `ChannelReply("ignored", event="rate_limited" | "daily_capped")`.
  - **Textos**: agregar en `TEXTS` (es/en) los avisos del contrato §1. Sin comandos, sin cifras del límite.
- [X] T018 [US3] En `src/proyecto_modelos_lenguaje/channels/bridge.py` (`_dispatch` / `_shortcut`): si `operators()`
  no está vacío y `user_id` no está en él, ignorar `OPERATOR_SHORTCUTS` (el texto sigue el flujo normal).
  `/olvidar` y `/cancelar` siguen funcionando como hoy: son de la persona, no del operador.
- [X] T019 [US3] En `src/proyecto_modelos_lenguaje/channels/__main__.py`, agregar los subcomandos `pseudonym`,
  `block`, `unblock` y `blocked` (contrato §3):
  - usan `channel_salt()` y `pseudonym()` del canal y el almacén en `resolve_state_dir(...)/channels.sqlite3`;
  - nunca imprimen el número;
  - documentar los usos en el docstring del módulo.

**Checkpoint**: el canal abierto queda protegido.

---

## Phase 6: User Story 4 - Operación y privacidad con personas desconocidas (Priority: P3)

**Goal**: el estado del canal muestra el uso sin números ni contenido.

**Independent Test**: `uv run pytest tests/unit/channels/test_journal.py tests/api/test_channels_api.py -k status`.

### Tests for User Story 4

- [X] T020 [P] [US4] Prueba en `tests/unit/channels/test_journal.py` (o el archivo de pruebas del registro existente):
  - con registros de 3 seudónimos (uno limitado y uno bloqueado), `recent_stats` devuelve `people_today=3`,
    `limited_today=1` y `blocked_today=1`;
  - solo cuenta los registros del día local.

### Implementation for User Story 4

- [X] T021 [US4] En `src/proyecto_modelos_lenguaje/channels/journal.py` (`recent_stats`), agregar sobre el registro
  del día:
  - `people_today`: seudónimos distintos con estado distinto de `ignored`;
  - `limited_today`: eventos `rate_limited` + `daily_capped`;
  - `blocked_today`: eventos `blocked`.
  - Se exponen en `GET /api/channels/status` (sin cambios en `api.py` si `channels` ya devuelve `recent_stats`).
  - Si el modelo del estado es estricto, actualizar `src/proyecto_modelos_lenguaje/api_models.py`.

**Checkpoint**: las cuatro historias funcionan.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T022 [P] Actualizar `CONSTITUTION.md` (regla del canal de la spec 028):
  - el canal puede abrirse a cualquier número con límites por seudónimo, bloqueo y atajos solo para operadores;
  - cerrarlo al terminar el proyecto.
  - Subir la versión PATCH y anotar en el historial.
- [X] T023 [P] Actualizar `docs/manual_whatsapp.md`:
  - cualquier persona puede escribir;
  - si escribe muchos mensajes seguidos, Valer-IA le pide unos minutos;
  - hay un máximo diario;
  - grupos no.
- [X] T024 `make check` en verde (ruff, pytest, vitest, build web).
- [ ] T025 Configuración y prueba en el teléfono (manual, quickstart §2–§4). Antes de ejecutar, dar al usuario
  instrucciones paso a paso:
  - calcular los seudónimos de los números de prueba;
  - completar `VALERIA_OPERATORS` en el `.env` del repo sin mostrar los valores;
  - reiniciar el backend;
  - `-Mode open` y esperar ~2 min;
  - `ops check` debe mostrar «ABIERTO»;
  - escribir desde 2 números nuevos (texto y voz): 10/10 respuestas (SC-001);
  - revisar `people_today`;
  - anotar SC-001 a SC-005 en § Notas sin números.
- [ ] T026 Marcar las tareas y agregar notas de implementación en este archivo. Queda listo para el PR conjunto con las
  specs 028–030, que necesita la autorización de un integrante.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001–T002)**: sin dependencias.
- **Foundational (T003–T006)**:
  - T003 depende de T001;
  - T005 depende de T003, por el tipo `Usage`;
  - bloquea US3 y US4.
- **US1 (T007–T010)**: no depende de la fase 2; puede ir justo después del setup.
- **US2 (T011–T013)**: independiente de US1 (otro archivo).
- **US3 (T014–T019)**: depende de la fase 2. T017 antes de T018; T019 depende de T005.
- **US4 (T020–T021)**: depende de T017, porque necesita los eventos nuevos.
- **Polish (T022–T026)**: al final; T025 antes de T026.

### User Story Dependencies

- **US1 (P1)**: MVP; solo configuración y verificación del modo abierto.
- **US2 (P1)**: independiente; se entrega con US1.
- **US3 (P2)**: depende de la fase 2.
- **US4 (P3)**: depende de US3 (eventos).

### Within Each User Story

- Pruebas primero, y deben fallar antes de implementar.
- Almacén y lógica pura antes del puente; puente antes del CLI.

### Parallel Opportunities

- T001 y T002.
- T004 y T006, después de T003 y T005.
- T007, T008 y T011.
- T014, T015 y T016.
- T022 y T023.

---

## Parallel Example: User Story 3

```text
# Pruebas de US3 juntas:
T014 tests/unit/channels/test_bridge.py (límites)
T015 tests/unit/channels/test_bridge.py (bloqueo y atajos)   # mismo archivo: secuencial con T014 al escribir
T016 tests/unit/channels/test_cli_operator.py
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Setup.
2. US1 + US2: modo abierto verificable. Ya permite que cualquier número reciba respuesta.
3. **Validar**: `ops check` muestra «ABIERTO» y un número nuevo recibe respuesta.

### Incremental Delivery

1. US1 + US2 → canal abierto para la sustentación.
2. Fase 2 + US3 → protecciones (límites, bloqueo, atajos).
3. US4 → estado con personas y limitados.
4. Polish → constitución, manual, `make check`, prueba con el teléfono.

### Parallel Team Strategy

No aplica: el trabajo es secuencial en un solo equipo (acuerdo del proyecto).

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes.
- Pasos con el teléfono y cambios de modo: instrucciones detalladas antes de ejecutarlos. Esperar ~2 min tras
  reiniciar el gateway.
- Ningún número real en archivos versionados, registros ni salidas de comandos; solo seudónimos.
- Autoría: sin commits, push ni PR sin autorización de un integrante; nunca agregar `Co-authored-by` ni firmas.

## Notas de implementación (2026-11-27)

- Hechas: T001–T024. Pendientes: T025 (configuración de operadores y prueba con números nuevos, manual) y T026
  (cierre, después de T025).
- Al implementar, `ops check` mostró que el canal ya estaba **abierto** en el servidor (`-Mode open` ejecutado por
  el equipo). Sin el backend reiniciado, todavía no aplicaban los límites ni el bloqueo.
- **Backend**:
  - `channels/limits.py`: decisión pura;
  - `ChannelStore`: tablas `channel_usage` y `channel_blocked`, creadas con `CREATE TABLE IF NOT EXISTS`, así que
    las bases existentes las ganan sin migración destructiva;
  - `ChannelBridge._gate`: bloqueo y límites después de la deduplicación y antes de la cola, sin llamar al agente;
  - los atajos ocultos quedan solo para operadores cuando `VALERIA_OPERATORS` tiene valores (`/olvidar` y
    `/cancelar` siguen siendo de cada persona).
- **Operación**:
  - `pml channels pseudonym|block|unblock|blocked` no necesitan el token del canal y nunca imprimen el número;
  - `ops check` agrega `modo-canal`, que lee solo `WA_DM_POLICY` y `WA_ALLOW_1..3` del `.env` externo;
  - `GET /api/channels/status` agrega `people_today`, `limited_today` y `blocked_today` por canal.
- **Constitución 2.4.0** (MINOR, no PATCH como decía la tarea): se enmendó la regla 9, que antes decía «modo
  abierto sin límite y solo en el ensayo y la jornada». El repositorio versiona como MINOR los cambios de reglas
  normativas. Requiere la aprobación de ambos integrantes.
- **Pruebas**:
  - nuevas: `test_limits.py`, `test_journal.py`, `test_cli_operator.py`, US1 y US3 en `test_bridge.py`,
    privacidad con 3 números en `test_channels_api.py`, `modo-canal` en `test_ops.py`;
  - `make check` en verde: 2.155 pruebas de Python y 185 de la web.
