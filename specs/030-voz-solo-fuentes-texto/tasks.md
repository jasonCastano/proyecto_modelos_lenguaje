# Tasks: Respuesta por voz sin texto duplicado (solo fuentes por escrito)

**Input**: Design documents from `specs/030-voz-solo-fuentes-texto/`

**Prerequisites**:

- plan.md
- spec.md
- research.md (R1–R6)
- data-model.md
- contracts/channel-voice-text.md
- quickstart.md

**Tests**: incluidas. La DoD del proyecto exige pruebas y la spec define criterios verificables: SC-001 a SC-005,
FR-008 y la regresión con las pruebas reales del 2026-11-27.

**Organization**: por historia de usuario (US1 y US2 son P1; US3 es P3).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1, US2, US3)

## Path Conventions

- Backend: `src/proyecto_modelos_lenguaje/channels/`, `src/proyecto_modelos_lenguaje/api_models.py`
- Plugin: `openclaw/plugins/valeria-bridge/{index.ts,src/bridge.ts,test/bridge.test.ts}`
- Pruebas: `tests/unit/channels/`, `tests/api/`, `tests/fixtures/channels/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: casos de regresión fijados antes de cambiar código.

- [X] T001 [P] Crear `tests/fixtures/channels/regression_2026-11-27b.jsonl` con las dos respuestas reales de
  `C:\Users\JCastano\Downloads\pruebas valeria\2`:
  - ids `v1` (13:26) y `v2` (13:31);
  - campos: `question` (transcripción aproximada, sin datos personales), `lang: "es"`, `input: "voice"`, `reply`
    (texto completo de Valer-IA con su bloque «Fuentes:») y `sources_lines` (3 y 1);
  - sin audios ni números de teléfono.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: el bloque de fuentes aislado y la revisión que lo valida. US1 y US2 dependen de esta fase.

- [X] T002 [P] En `src/proyecto_modelos_lenguaje/channels/format.py`, agregar
  `sources_only(answer, citations, *, language="es", max_chars=1500) -> list[str]`:
  - **Reutiliza** `markdown_to_whatsapp` + `number_citations` (mismo orden, misma deduplicación por URL y página de la
    spec 029) y `sources_block(used, language)`.
  - **Salida** (data-model §1):
    - lista vacía si no hay fuentes;
    - si el bloque supera `max_chars`, se parte en mensajes de líneas completas;
    - el encabezado aparece una sola vez por bloque, sin repetirlo en la continuación;
    - cada elemento ≤ `max_chars`.
  - **Contenido**: cada mensaje contiene solo encabezados («Fuentes:», «Sources:», «Fuentes sintéticas
    (demostración):», «Synthetic sources (demo):») y líneas `[n] Título[, p. X] — URL`.
- [X] T003 [P] En `src/proyecto_modelos_lenguaje/channels/quality.py`, agregar el parámetro keyword `voice: bool = False`
  a `review_reply`:
  - Con `voice=True`, todo mensaje con texto fuera de los bloques de fuentes genera
    `Issue("voice_text_duplicate", index, …)`.
  - Con `voice=True`, una lista vacía o solo bloques de fuentes es conforme.
  - Las reglas de la spec 029 (idioma, formato de líneas, numeración, títulos) se siguen aplicando a los bloques.
  - Actualizar el docstring del módulo.
- [X] T004 Pruebas en `tests/unit/channels/test_format.py`:
  - `sources_only` devuelve `["Fuentes:\n[1] …\n[2] …"]` con los mismos números que `to_whatsapp` para la misma
    respuesta;
  - `[]` sin citas;
  - «Sources:» con `language="en"`;
  - bloque sintético aparte;
  - 30 fuentes con `max_chars=300` → varios mensajes, cada uno ≤ 300, todas las líneas completas, el encabezado una
    sola vez.
- [X] T005 Pruebas en `tests/unit/channels/test_quality.py`:
  - las dos respuestas de `regression_2026-11-27b.jsonl` con `voice=True` dan `voice_text_duplicate`;
  - su bloque de fuentes aislado con `voice=True` pasa sin hallazgos (4 y 2 líneas: SC-005);
  - `review_reply([], "es", voice=True) == []`;
  - una respuesta completa con `voice=False` sigue conforme.

**Checkpoint**: `uv run pytest tests/unit/channels/test_format.py tests/unit/channels/test_quality.py` en verde.

---

## Phase 3: User Story 1 - Nota de voz + solo las fuentes por escrito (Priority: P1) 🎯 MVP

**Goal**: ante una nota de voz con respuesta respaldada, la persona recibe la nota de voz y un texto con solo el bloque
de fuentes; sin fuentes, solo la voz; por texto, nada cambia.

**Independent Test**:

- `uv run pytest tests/unit/channels/test_bridge.py tests/api/test_channels_api.py` y `npm test` del plugin.
- Simulación: `pml channels simulate --script … --check` sin hallazgos `voice_text_duplicate`.

### Tests for User Story 1

- [X] T006 [P] [US1] Pruebas del puente en `tests/unit/channels/test_bridge.py`:
  - **Nota de voz respaldada**: `audio(...)` con respuesta y cita →
    - `reply.voice` presente;
    - `reply.sources_messages == ["Fuentes:\n[1] Informe — https://manuelita.com"]`;
    - `reply.messages` sigue con la respuesta completa.
  - **Texto**: `msg(...)` → `sources_messages == []` y `voice is None`.
  - **Nota de voz sin citas** (saludo): `voice` presente y `sources_messages == []`.
  - **Inglés**: con `language_hint="en"`, «Sources:».
  - **Preferencia «mándame audio» y pregunta escrita**: `sources_messages` con fuentes.
- [X] T007 [P] [US1] Prueba de contrato en `tests/api/test_channels_api.py`:
  - una nota de voz (`kind: "audio"`, `input_mode: "voice"`) en modo demo devuelve `sources_messages` con solo el
    bloque de fuentes, sin oraciones de la respuesta (verificado con `review_reply(..., voice=True) == []`);
  - un texto devuelve `sources_messages == []`;
  - el modelo de respuesta acepta y serializa el campo.
- [X] T008 [P] [US1] Pruebas del plugin en `openclaw/plugins/valeria-bridge/test/bridge.test.ts`:
  - con `voice` y `sendVoice` que resuelve `true`, `dispatch` devuelve `{handled: true, text: sources_messages
    unidos por "\n\n"}`;
  - con `sources_messages: []`, devuelve `{handled: true}` sin `text`;
  - sin `voice`, devuelve `messages` como hoy;
  - un backend anterior sin `sources_messages` y con voz entregada devuelve `messages`
    (compatibilidad, contrato §1).

### Implementation for User Story 1

- [X] T009 [US1] En `src/proyecto_modelos_lenguaje/channels/bridge.py`:
  - **Campo nuevo**: `sources_messages: list[str] = field(default_factory=list)` en `ChannelReply`, incluido en
    `to_dict()`.
  - **Respuesta original**: guardar en `ChannelReply` la respuesta y sus citas (campos internos, no serializados), en
    `_from_outcome` y `_resolve`.
  - **Al adjuntar la voz**: en `_attach_voice`, cuando `reply.voice` queda asignado, calcular
    `reply.sources_messages = sources_only(answer, citations, language=reply.language, max_chars=self.config.reply_max_chars)`.
  - **Sin voz**: dejar `[]`, tanto si no hubo voz como si falló al generarse.
- [X] T010 [US1] En `src/proyecto_modelos_lenguaje/api_models.py`, agregar
  `sources_messages: list[str] = Field(default_factory=list)` a `ChannelReplyModel` con su descripción («solo el bloque
  de fuentes; el plugin lo entrega cuando la nota de voz se envió»).
- [X] T011 [US1] En `openclaw/plugins/valeria-bridge/src/bridge.ts`:
  - **Tipos**: `BackendReply.sources_messages?: string[]`.
  - **Envío**: `VoiceSender` pasa a devolver `Promise<boolean>` (entregada o no).
  - **Selección del texto en `dispatch`**:
    - si hubo voz entregada **y** el backend envió el campo `sources_messages`, el texto es
      `sources_messages.filter(trim).join("\n\n")`, o sin texto si está vacío;
    - en otro caso, `toResult(payload)`.
- [X] T012 [US1] En `openclaw/plugins/valeria-bridge/index.ts`:
  - `voiceSender` devuelve `true` cuando `sendMedia` del adaptador resuelve sin error;
  - `false` cuando falla, después de lanzar el CLI de respaldo en segundo plano;
  - registrar `valeria-bridge: voz entregada; texto: solo fuentes` o `… sin texto`.
- [X] T013 [US1] En `src/proyecto_modelos_lenguaje/channels/journal.py` y `channels/bridge.py` (`_record`), agregar al
  registro del canal el campo `written`:
  - `"sources"` si hay voz y `sources_messages`;
  - `"none"` si hay voz sin fuentes;
  - `"full"` sin voz.
  - Sin texto ni números (data-model §3).
  - Prueba en `tests/unit/channels/test_bridge.py`: leer el registro y comprobar el valor en los tres casos.

**Checkpoint**: US1 funciona con la voz entregada. Pruebas de puente, API y plugin en verde.

---

## Phase 4: User Story 2 - Si la voz no llega, la respuesta escrita completa (Priority: P1)

**Goal**: una falla al generar o al entregar la voz nunca deja a la persona solo con enlaces.

**Independent Test**: las pruebas de falla del puente y del plugin. Con la síntesis caída llega la respuesta completa
y el aviso; si el adaptador lanza error, el plugin devuelve `messages`.

### Tests for User Story 2

- [X] T014 [P] [US2] Prueba en `tests/unit/channels/test_bridge.py`: con `FakeVoice(fail=True)` y una nota de voz,
  - `reply.voice is None`;
  - `reply.sources_messages == []`;
  - `reply.messages` trae la respuesta completa con fuentes y el aviso `voice_failed`;
  - `written == "full"`.
- [X] T015 [P] [US2] Pruebas en `openclaw/plugins/valeria-bridge/test/bridge.test.ts`:
  - **`sendVoice` resuelve `false`**: `dispatch` devuelve `messages` (respuesta completa) y no `sources_messages`.
  - **`sendVoice` lanza**: mismo resultado.
  - **Registro**: se registra «voz no entregada; texto completo».

### Implementation for User Story 2

- [X] T016 [US2] En `openclaw/plugins/valeria-bridge/src/bridge.ts` (`dispatch`):
  - ante `false` o una excepción de `sendVoice`, usar `toResult(payload)` (respuesta completa);
  - registrar `valeria-bridge: voz no entregada; texto completo`, sin contenido ni números.
- [X] T017 [US2] Revisar `src/proyecto_modelos_lenguaje/channels/bridge.py` (`_attach_voice`):
  - en la rama de falla (`result is None`), `sources_messages` queda `[]` y el aviso `voice_failed` va en `messages`
    (comportamiento de la spec 028);
  - documentar en el docstring la regla «sin voz → texto completo».

**Checkpoint**: US1 + US2 cubren el comportamiento completo; ninguna combinación deja solo enlaces.

---

## Phase 5: User Story 3 - La voz menciona que las fuentes van por escrito (Priority: P3)

**Goal**: si hay fuentes, la nota de voz cierra con una frase natural en el idioma del turno.

**Independent Test**: `uv run pytest tests/unit/channels/test_voice.py`. El guion termina con la frase si hay fuentes;
sin fuentes no la lleva.

### Tests for User Story 3

- [X] T018 [P] [US3] Pruebas en `tests/unit/channels/test_voice.py`:
  - `ChannelVoice.for_answer(question, answer, "es", with_sources=True)` produce un guion que termina en «Te dejo las
    fuentes por escrito.»;
  - en inglés termina en «I've left the sources for you in writing.»;
  - con `with_sources=False`, sin la frase;
  - la frase no rompe `valid_script` (no tiene cifras);
  - con el respaldo determinista (modelo `None`), también la lleva.

### Implementation for User Story 3

- [X] T019 [US3] En `src/proyecto_modelos_lenguaje/channels/voice.py`:
  - constante `SOURCES_CLOSING = {"es": "Te dejo las fuentes por escrito.", "en": "I've left the sources for you in
    writing."}`;
  - parámetro keyword `with_sources: bool = False` en `ChannelVoice.for_answer`, que añade la frase al final del guion
    (modelo o respaldo) antes de sintetizar, sin duplicarla si el guion ya la trae;
  - actualizar `VoicePort` en `channels/bridge.py` con el parámetro nuevo.
- [X] T020 [US3] En `src/proyecto_modelos_lenguaje/channels/bridge.py` (`_attach_voice`):
  - calcular primero `sources_messages` y llamar a `self.voice.for_answer(..., with_sources=bool(sources_messages))`;
  - ajustar `FakeVoice` en `tests/unit/channels/test_bridge.py` para aceptar el parámetro.

**Checkpoint**: las tres historias funcionan juntas.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T021 En `src/proyecto_modelos_lenguaje/channels/__main__.py` (`run_script` y `_check_reply`), hacer que
  `simulate --check` use el texto que se entregaría:
  - con `voice` presente, revisa `sources_messages` con `review_reply(..., voice=True)`;
  - sin voz, revisa `messages`.
  - Imprimir «(texto: solo fuentes)» o «(texto: completo)» por mensaje.
  - Correr quickstart §1 en modo real contra un backend en el puerto 8010 (estado en el scratchpad) con
    `tests/fixtures/channels/language_format.jsonl`: 0 hallazgos esperados.
- [X] T022 [P] Actualizar `docs/manual_whatsapp.md` (§ Notas de voz): «Si le hablas, te responde con una nota de voz y,
  por escrito, solo las fuentes; si la voz no llega, recibes la respuesta escrita completa».
- [X] T023 [P] Actualizar `specs/028-valeria-natural-voz-whatsapp/contracts/` o la referencia del contrato del canal en
  `docs/` si describe `messages` como único texto, enlazando `specs/030-voz-solo-fuentes-texto/contracts/channel-voice-text.md`.
- [X] T024 `make check` en verde (ruff, pytest, vitest, build web) y `npm test` del plugin.
- [ ] T025 Prueba con el teléfono (manual, quickstart §3). Antes de ejecutar, dar al usuario instrucciones paso a paso:
  - reiniciar el backend y el gateway, y esperar ~2 min a que el gateway escuche WhatsApp;
  - repetir por voz las pruebas de las 13:26 y 13:31: nota de voz con la frase de cierre y un texto con solo fuentes
    (3 y 1 líneas);
  - «Hola Valeria» por voz: solo la voz;
  - una pregunta escrita: respuesta completa;
  - verificar `written` en `channels.jsonl`;
  - anotar SC-001 a SC-005 en § Notas, sin números.
- [ ] T026 Marcar las tareas y agregar notas de implementación en este archivo. Queda listo para el PR conjunto con las
  specs 028 y 029, que necesita la autorización de un integrante.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (T001)**: sin dependencias.
- **Foundational (T002–T005)**: T004 depende de T002; T005 depende de T001 y T003. Bloquea US1 y US2.
- **US1 (T006–T013)**:
  - depende de la fase 2;
  - T009 antes de T013;
  - T011 antes de T012;
  - T010 en paralelo con T011.
- **US2 (T014–T017)**: depende de T009 y T011, porque reutiliza `sources_messages` y el `VoiceSender` booleano.
- **US3 (T018–T020)**: depende de T009 (`sources_messages` se calcula antes de la voz).
- **Polish (T021–T026)**: después de US1–US3; T025 al final, antes de T026.

### User Story Dependencies

- **US1 (P1)**: MVP; depende solo de la fase 2.
- **US2 (P1)**: depende de US1 (mismo `dispatch` y `_attach_voice`), pero se prueba sola con fallas simuladas.
- **US3 (P3)**: independiente en la voz; se integra sobre US1.

### Within Each User Story

- Pruebas primero, y deben fallar antes de implementar.
- Backend (bridge, modelos) antes del plugin.
- Plugin (`src/bridge.ts`) antes de `index.ts`.

### Parallel Opportunities

- T001, T002 y T003 en paralelo (archivos distintos).
- T006, T007 y T008 en paralelo (pruebas en archivos distintos).
- T014 y T015 en paralelo.
- T022 y T023 en paralelo.

---

## Parallel Example: User Story 1

```text
# Pruebas de US1 juntas:
T006 tests/unit/channels/test_bridge.py
T007 tests/api/test_channels_api.py
T008 openclaw/plugins/valeria-bridge/test/bridge.test.ts

# Modelo de API y plugin en paralelo (archivos distintos), después de T009:
T010 src/proyecto_modelos_lenguaje/api_models.py
T011 openclaw/plugins/valeria-bridge/src/bridge.ts
```

---

## Implementation Strategy

### MVP First (User Story 1 + User Story 2)

1. Fase 1 y fase 2: regresión, `sources_only` y la revisión con `voice=True`.
2. US1: texto solo con fuentes cuando la voz se entrega.
3. US2 en la misma entrega: sin ella, una falla de voz dejaría solo enlaces, así que no se publica US1 sin US2.
4. **Validar**: pruebas, simulación real y una nota de voz con el teléfono.

### Incremental Delivery

1. Fases 1–2 → base verificable.
2. US1 + US2 → reinicio del backend y del gateway; prueba con el teléfono.
3. US3 → frase de cierre; reinicio del backend.
4. Polish → manual, `make check` y notas.

### Parallel Team Strategy

No aplica: el trabajo es secuencial en un solo equipo (acuerdo del proyecto).

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes.
- Pasos con el teléfono: instrucciones detalladas antes de ejecutarlos. Después de reiniciar el gateway, esperar
  ~2 min.
- Datos: ningún número ni texto de conversación en archivos versionados ni en registros.
- Autoría: sin commits, push ni PR sin autorización de un integrante; nunca agregar `Co-authored-by` ni firmas.

## Notas de implementación (2026-11-27)

- Hechas: T001–T024. Pendientes: T025 (prueba con el teléfono, manual) y T026 (cierre, después de T025).
- **Backend**:
  - `ChannelReply` incluye `sources_messages`, calculado con `format.sources_only` antes de generar la voz.
  - El registro del canal anota `written` (`full` / `sources` / `none`).
  - Si la voz falla al generarse, `sources_messages` queda vacío y va el texto completo con el aviso.
- **Plugin**:
  - el sender de voz devuelve `true` solo si el adaptador del canal confirma la entrega;
  - `withVoiceText` entrega `sources_messages` (o nada) con voz entregada y `messages` en cualquier otro caso,
    incluido un backend anterior sin el campo;
  - si el adaptador falla, el CLI reintenta la voz en segundo plano y el texto va completo.
- **Voz**: `with_sources_closing` añade «Te dejo las fuentes por escrito.» / «I've left the sources for you in
  writing.» al guion (del modelo o de respaldo) solo cuando hay fuentes.
- **Revisión**:
  - `review_reply(..., voice=True)` marca `voice_text_duplicate`;
  - acepta bloques de fuentes partidos en varios mensajes (la continuación sin encabezado);
  - con voz no exige el aviso de datos sensibles por escrito, porque va en el audio.
- **Regresión**: las dos respuestas reales (`regression_2026-11-27b.jsonl`) fallan como turno con voz; su bloque de
  fuentes aislado pasa (4 y 2 líneas).
- **Simulación real**:
  - `--check` sobre `language_format.jsonl` (backend aparte en el puerto 8010) da 0 hallazgos;
  - las 10 consultas por voz llevan nota de voz + solo fuentes y las 13 escritas, texto completo.
- **`make check`** (la primera corrida cayó por el crash nativo intermitente de HiGHS/scipy en Windows, conocido; la
  segunda pasó):
  - 2.130 pruebas de Python y 185 de la web;
  - plugin: 30/30.
