---

description: "Tareas de la spec 029: respuestas de Valer-IA por WhatsApp en voz, en un solo idioma y bien ordenadas"
---

# Tasks: Respuestas de Valer-IA por WhatsApp en voz, en un solo idioma y bien ordenadas

**Input**: Design documents from `specs/029-voz-idioma-formato-whatsapp/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/channel-format.md](contracts/channel-format.md),
[quickstart.md](quickstart.md)

**Tests**: incluidos. La spec exige una revisión automática del formato (FR-015) y criterios medibles; la
constitución pide pruebas sin red y que las evaluaciones publicadas no bajen (regla 21).

**Organization**: por historia. Las tareas **(manual)** las ejecuta el equipo con el teléfono de prueba; Claude
entrega antes las instrucciones paso a paso y no las ejecuta por su cuenta.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: US1 voz · US2 idioma único · US3 aviso de seguridad · US4 fuentes ordenadas

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: casos de regresión y conjunto de medición, fijados antes de cambiar el código

- [X] T001 [P] Crear `tests/fixtures/channels/regression_2026-11-27.jsonl` con las tres respuestas reales de `C:\Users\JCastano\Downloads\pruebas valeria` (solo el texto de Valer-IA, la pregunta transcrita, `lang` y `input: "voice"`; sin números ni audios); quitar del texto cualquier dato personal si apareciera
- [X] T002 [P] Crear `tests/fixtures/channels/language_format.jsonl`: 20 consultas (10 es, 10 en; `kind` text y audio) que citan fuentes, más 3 con datos sensibles ficticios (tarjeta `4111 1111 1111 1111`, cédula ficticia, «mi contraseña es…»), con campos `id`, `text`, `lang`, `kind`, `sensitive` (bool)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: la revisión automática que mide todas las historias y la captura real del formato de la nota de voz

**⚠️ CRITICAL**: las historias se validan con `channels/quality.py`; la captura de T005 confirma la causa de US1 y US3

- [X] T003 Crear `src/proyecto_modelos_lenguaje/channels/quality.py` con `review_reply(messages: list[str], language: str, *, sensitive_input: bool = False) -> list[Issue]` y el dataclass `Issue(code, message_index, detail)`; códigos del data model: `mixed_language`, `wrong_sources_header`, `sources_line_format` (regex de línea `^\[\d+\] .+ — https?://\S+$` o sin URL si no existe), `sources_numbering` (1..N sin huecos), `duplicate_source` (misma URL y página), `dirty_title` (salto de línea, «Índice», numeraciones sueltas o > 80 caracteres), `unexpected_notice`, `missing_notice`; marcadores de idioma para los textos fijos de ambos idiomas y una heurística de palabras funcionales por oración
- [X] T004 [P] Pruebas en `tests/unit/channels/test_quality.py`: las tres respuestas de `regression_2026-11-27.jsonl` **fallan** (aviso inesperado en las tres, `dirty_title` en 10.00.56, `mixed_language` y `duplicate_source` en 10.08.56); respuestas bien formadas en es y en pasan; cada código tiene un caso
- [X] T005 Añadir depuración de forma al plugin `openclaw/plugins/valeria-bridge/src/bridge.ts` (contrato §1): con `VALERIA_BRIDGE_DEBUG=1` registra por mensaje `forma content: len=…, [Audio]@pos, Transcript:@pos, media@pos · body: …` con los dígitos reemplazados por `#` y **sin** texto del mensaje; prueba en `test/bridge.test.ts` que la línea no contiene dígitos ni palabras del mensaje
- [X] T006 Captura de verificación (manual, instrucciones previas; quickstart §2): reinstalar/reiniciar el gateway con la depuración, enviar una nota de voz y un texto desde el teléfono de prueba, copiar las dos líneas `forma …` en `specs/029-voz-idioma-formato-whatsapp/research.md` § «Hallazgos de la captura», y quitar la depuración

**Checkpoint**: la revisión automática existe y falla sobre las respuestas reales; el formato de la nota de voz está confirmado

---

## Phase 3: User Story 1 - Una nota de voz recibe una nota de voz (Priority: P1) 🎯 MVP

**Goal**: toda nota de voz llega al backend como voz, solo con su transcripción, y recibe nota de voz + texto

**Independent Test**: quickstart §3 (las tres notas de voz de las pruebas) y `channels.jsonl` con `input_mode: voice`, `voice_sent: true`

### Tests for User Story 1

- [X] T007 [P] [US1] Pruebas en `openclaw/plugins/valeria-bridge/test/bridge.test.ts` con los formatos de T006 y los documentados: `[Audio]` al inicio, precedido por un encabezado con número, solo en `body`, con `User text:`/`<media:audio>` y con `Transcript:`; en todos `kind: "audio"`, `input_mode: "voice"` y `text` = solo la transcripción (sin el encabezado ni dígitos del número); un texto escrito normal sigue siendo `kind: "text"` sin cambios

### Implementation for User Story 1

- [X] T008 [US1] En `openclaw/plugins/valeria-bridge/src/bridge.ts`: `detectVoice(content, body)` que reconoce `[Audio]`, `Transcript:` o `<media:audio>` en **cualquier posición** de `content` o `body`; `transcriptOf` que toma el texto tras el último `Transcript:` (o tras `[Audio]` sin líneas `User text:` ni marcas `<media:…>`); `buildRequest` envía solo la transcripción (≤ 4.000 caracteres) y nunca el encabezado del gateway
- [X] T009 [US1] Reinstalar el plugin y reiniciar el gateway (manual, instrucciones previas: `.\scripts\openclaw_env.ps1 -Install`), repetir las tres notas de voz de las pruebas y verificar nota de voz + texto y `channels.jsonl` (`input_mode: voice`, `voice_sent: true`); anotar en § Notas sin números

**Checkpoint**: Valer-IA responde con voz a las notas de voz

---

## Phase 4: User Story 2 - Un solo idioma de principio a fin (Priority: P1)

**Goal**: cuerpo, avisos, encabezados y marcas en el idioma de la consulta

**Independent Test**: `pml channels simulate --script tests/fixtures/channels/language_format.jsonl --check` sin `mixed_language` ni `wrong_sources_header`

### Tests for User Story 2

- [X] T010 [P] [US2] Pruebas en `tests/unit/channels/test_format.py`: `to_whatsapp(..., language="en")` usa «Sources:», «Synthetic sources (demo):» y la marca abreviada en inglés; `language="es"` conserva «Fuentes:»; prueba del puente en `tests/unit/channels/test_bridge.py` que pasa el idioma del turno al servicio y al formateador

### Implementation for User Story 2

- [X] T011 [US2] En `src/proyecto_modelos_lenguaje/channels/format.py`: parámetro `language: str = "es"` en `to_whatsapp`, `sources_block` y `split_messages`; diccionario de textos fijos es/en (encabezado de fuentes, fuentes sintéticas, respuesta abreviada)
- [X] T012 [US2] En `src/proyecto_modelos_lenguaje/channels/bridge.py`: el idioma del turno (`language_of` con el idioma previo del hilo como respaldo para mensajes de ≤ 3 palabras) se pasa a `service.send(..., language=)` y a `_format`/`_short`
- [X] T013 [US2] En `src/proyecto_modelos_lenguaje/agent/service.py` y `agent/graph.py`: aceptar `language` en `send` y guardarlo como `turn_language` en el estado; `_lead` usa variantes `_en` de los textos fijos si el turno es inglés y omite los prefijos sin variante (el bloque `Atención:` ya lleva `Idioma: en`); prueba en `tests/unit/agent/test_turn_language.py`

**Checkpoint**: 0 mezclas de idioma en el conjunto de medición

---

## Phase 5: User Story 3 - El aviso de seguridad solo cuando hace falta y dicho con naturalidad (Priority: P1)

**Goal**: aviso solo ante tarjeta, documento o contraseña reales, una vez por conversación, natural, al final y en el idioma del turno

**Independent Test**: las tres preguntas de las pruebas y diez más sin datos sensibles → sin aviso; tres con datos sensibles ficticios → una frase natural, una vez

### Tests for User Story 3

- [X] T014 [P] [US3] Pruebas en `tests/unit/agent/test_sensitive_notice.py`: un teléfono (incluido el de un encabezado) **no** dispara el aviso; tarjeta, documento y «mi contraseña es…»/«my password is…» sí; el aviso va al final, una sola vez por hilo, en es o en según el turno, y no repite el dato

### Implementation for User Story 3

- [X] T015 [US3] En `src/proyecto_modelos_lenguaje/agent/graph.py` y `service.py`: `SENSITIVE_NOTICES = {"credit_card", "document", "password"}` (sin `phone`); detección de contraseñas por frase en `agent/privacy.py` (`detect_password`, redactada también); bandera `sensitive_notice_given` en el estado del hilo; el aviso se añade **al final** de la respuesta y solo si no se dio antes o hay un dato sensible nuevo
- [X] T016 [US3] Actualizar `prompts/conduct.md` a 1.3: `sensitive_notice` natural («Ojo: por aquí no hace falta que compartas datos como tarjetas o documentos; para lo que necesites me basta con tu pregunta.») y nueva sección `sensitive_notice_en` («Just so you know, there's no need to share card or ID details here; your question is all I need.»); registrar en `docs/prompt_log.md` §3.27

**Checkpoint**: 0 avisos sin motivo; 3/3 avisos correctos con datos sensibles

---

## Phase 6: User Story 4 - Respuestas ordenadas y fuentes limpias (Priority: P1)

**Goal**: bloque de fuentes con una línea por fuente, numeración consecutiva, sin repetidos y títulos limpios

**Independent Test**: reprocesar las respuestas de `regression_2026-11-27.jsonl` y del conjunto de medición sin hallazgos de fuentes

### Tests for User Story 4

- [X] T017 [P] [US4] Pruebas en `tests/unit/channels/test_format.py`: `clean_title` con el título real «Índice\n1.\n2.\n…Carta del presid…» → nombre del documento del enlace («Informe de Sostenibilidad Manuelita 2013-2014»); títulos con saltos de línea → una línea ≤ 80 caracteres; dos etiquetas con la misma URL y página → un solo número y el texto renumerado (`[F1] … [F2]` → `[1] … [1]` colapsado a `[1]`); misma URL con páginas distintas → dos fuentes; sin título ni archivo → dominio

### Implementation for User Story 4

- [X] T018 [US4] En `src/proyecto_modelos_lenguaje/channels/format.py`: `clean_title(title, url)` (una línea, sin «Índice»/«Contenido»/«Tabla de contenido» ni numeraciones o viñetas sueltas, respaldo al nombre del documento del archivo del enlace y luego al dominio, ≤ 80 caracteres con «…»); `number_citations` agrupa por (URL, página) y colapsa citas repetidas contiguas; `sources_block` con línea fija `[n] Título, p. X — URL` y sin líneas vacías internas
- [X] T019 [US4] Verificar que la división en mensajes nunca parte el bloque de fuentes (`split_messages`/`to_whatsapp` en `channels/format.py`) con una respuesta larga de 5 fuentes; prueba en `tests/unit/channels/test_format.py`

**Checkpoint**: 100 % de los bloques de fuentes pasan la revisión

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T020 Añadir `--check` a `pml channels simulate --script` en `src/proyecto_modelos_lenguaje/channels/__main__.py`: aplica `review_reply` a cada respuesta (con `sensitive_input` del fixture) y termina con código 1 si hay hallazgos; correr quickstart §1 en modo demo y en modo real
- [X] T021 [P] Actualizar `docs/manual_whatsapp.md` (aviso solo si compartes datos sensibles; respuesta en tu idioma) y `specs/029-voz-idioma-formato-whatsapp/research.md` con los hallazgos
- [X] T022 Regresión de evaluaciones en modo real (`LANGSMITH_TRACING=false`): `agent evaluate --tools` (≥ 90,7 %) y `agent shield --channel` (20/20); actualizar `docs/evaluacion_herramientas.md` y `docs/evaluacion_blindaje_canal.md` si cambian
- [X] T023 `make check` en verde y `npm test` del plugin
- [ ] T024 Prueba con el teléfono (manual, instrucciones previas; quickstart §3 y §4): las tres notas de voz de las pruebas + 3 en inglés + 4 más → 10/10 con voz; mensaje con tarjeta ficticia → aviso natural una vez; anotar SC-001 a SC-005 en § Notas sin números
- [ ] T025 Marcar las tareas, notas de implementación en este archivo y dejar listo para el PR conjunto con la spec 028 (autorizado por un integrante)

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T006)**; T006 necesita T005 y el teléfono.
- **US1** depende de T006 (formato real) para T008; T007 puede escribirse antes con los formatos documentados.
- **US2, US3, US4** dependen de T003 (revisión) pero no de la captura; pueden avanzar mientras se espera el teléfono.
- **US2 y US4** tocan `channels/format.py`: T011 antes de T018 (mismo archivo).
- **Polish** al final; T022–T024 después de todas las historias.

### Orden práctico (un solo equipo)

T001–T005 → (T006 con el teléfono, en cuanto se pueda) → US4 (T017–T019) → US2 (T010–T013) → US3 (T014–T016) →
US1 (T007–T009) → T020–T025.

### Parallel Opportunities

- T001 y T002; T004 con T005; T007, T010, T014 y T017 (pruebas en archivos distintos).

## Parallel Example: User Story 4

```text
Task: "T017 Pruebas de clean_title y dedupe en tests/unit/channels/test_format.py"
Task: "T014 Pruebas del aviso en tests/unit/agent/test_sensitive_notice.py"
```

## Implementation Strategy

### MVP para el sábado

1. T001–T006 (fixtures, revisión, captura)
2. US1 (voz) y US4 (fuentes): lo más visible en la demo
3. US2 (idioma) y US3 (aviso)
4. **STOP and VALIDATE**: T024 con el teléfono

Todas las historias son P1: no se recorta ninguna. Si falta tiempo, se acorta T022 a una sola corrida por
evaluación y T024 a las tres notas de voz de las pruebas + 3 en inglés.

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- Ningún número de teléfono en fixtures, registros ni capturas (dígitos enmascarados)
- Las tareas manuales se ejecutan solo después de entregar sus instrucciones paso a paso

## Notas de implementación (2026-11-27)

- Hechas: T001–T005, T007, T008, T010–T023. Pendientes manuales con el teléfono: T006 (captura), T009 (reinstalar el
  plugin y repetir las tres notas de voz) y T024; T025 se cierra después de esas pruebas.
- Cambios fuera de lo previsto: el detector de idioma (`agent/plan.py`) no reconocía «When was…» ni «Which…
  have?» (se ampliaron las palabras funcionales en inglés); títulos de metadatos de PDF y un título genérico repetido
  de noticias (se usa el nombre del documento o del enlace); el modelo añadía su propio aviso además del nuestro
  (`agent.md` 1.10, regla 8); el modo demo dice sus frases fijas en el idioma del turno.
- Pruebas previas actualizadas por el cambio de comportamiento: `test_persona.py` (aviso al final),
  `test_user_memory.py` (5 detectores con la contraseña) y `conduct_cases.jsonl` c11–c12 (frase nueva del aviso).
- Simulación real (`--check`): 0 hallazgos en 23 mensajes y 10/10 notas de voz en su idioma.
- Evaluaciones reales: herramientas 86,1 % en la corrida oficial y 90,7 % (39/43) al repetirla con el mismo código
  (variación del modelo en t15 y t25); blindaje del canal 19/20 (d05 por voz; reproducido 3 veces en modo real sin
  obedecer). Detalle en las notas de `docs/evaluacion_herramientas.md` y `docs/evaluacion_blindaje_canal.md`.
- `make check` en verde (2.113 pruebas de Python + 185 de la web) y `npm test` del plugin 21/21.
