# Tasks: Respuesta progresiva por frases revisadas

**Input**: Design documents from `/specs/021-sentence-streaming/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluidas. La spec exige verificar que nada sin revisar se muestra (FR-002, SC-004), que no se retira texto
(FR-003, SC-003) y medir la entrega contra la línea base (FR-015, FR-016). Todas las pruebas usan modelos guionados o
simulados que transmiten, salvo las marcadas `@network`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US4)

## Path Conventions

- Backend: `src/proyecto_modelos_lenguaje/agent/` (abreviado `agent/`), prompts en `prompts/` y configuración en
  `config/agent.toml`.
- Frontend: `web/src/`.
- Pruebas: `tests/unit/agent/`, `tests/integration/agent/`, `tests/api/` y `web/src/test/`.
- Contrato: [contracts/streaming.md](./contracts/streaming.md) (abreviado C).
- Comandos: `UV_PROJECT_ENVIRONMENT=.venv uv run …`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: línea base, configuración y guiones nuevos.

- [X] T001 Registrar la línea base en `specs/021-sentence-streaming/quickstart.md`, sección «0. Línea base», con los
  datos de la última corrida real de la spec 020 (`docs/evaluacion_conversacion.json`):
  - p90 de primera palabra en conversación: 5.9 s en cadena y 6.3 s en agente;
  - p90 en todos los turnos;
  - el tiempo total no se midió en la spec 020; se mide en T032 con `--baseline-delivery`.

  Verificar `UV_PROJECT_ENVIRONMENT=.venv make check` en verde antes de cambiar código.
- [X] T002 [P] Agregar a `[conversation]` en `config/agent.toml`, y a `ConversationConfig` y `_conversation_config`
  en `agent/config.py`, las claves de `data-model.md` §4:
  - `delivery` (`sentences | complete`, defecto `sentences`, enum);
  - `sentence_max_chars` (220, 80–600);
  - `first_fragment_chars` (160, 40–400 y ≤ `sentence_max_chars`);
  - `stream_first_timeout_seconds` (8, 1–30);
  - `stream_idle_timeout_seconds` (6, 1–30).

  Propiedad `sentences` (verdadera si `delivery == "sentences"`). Pruebas de rango en
  `tests/unit/agent/test_config.py`.
- [X] T003 [P] Subir `prompts/care.md` a 1.2 con las secciones nuevas:
  - `close.short` (2–3 cierres breves de conversación);
  - `required.valeria`, `required.ai`, `required.professional` y `required.manuelita` (2–3 variantes cada una, que
    contengan «Valer-IA Caña», «inteligencia artificial», «profesional» y «Manuelita»).

  Actualizar `tests/unit/agent/test_care_playbook.py` (versión 1.2 y presencia de las secciones).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: segmentador, filtro de frases, revisión por frase, estado del turno, evento SSE y ensamblaje en
`finalize`.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Crear `agent/sentences.py` con `SentenceSplitter`, un segmentador incremental con la regla de
  `voice/text.py` (importar `SENTENCE_END` y `_is_abbreviation`):
  - `push(chunk) -> list[str]` devuelve las frases cerradas; un punto al final del búfer espera más texto (como la
    voz);
  - un enumerador al inicio de línea («1.», «2)», «**3)**») no cierra frase;
  - la etiqueta `[U#]`/`[F#]` que sigue al texto queda en la frase;
  - si el búfer supera `max_chars` (o `first_chars` para el primer fragmento) sin cierre, devuelve el fragmento hasta
    el último espacio (FR-006);
  - `close() -> list[str]` entrega el resto.
- [X] T005 Agregar en `agent/sentences.py` (depende de T004) `SentenceGate` con los campos de `data-model.md` §1:
  `mode: conversation | retrieval`, `buffer`, `held`, `delivered`, `discarded`, `stopped` y `first_check_failed`.
  - `push(chunk)` y `close()` devuelven `Decision(kind: deliver | retry | stop, text, index)` según la tabla de C §3.
  - Recibe una función `check(sentence, is_first) -> list[ReviewIssue]`.
  - En `retrieval`, una frase sin etiqueta de cita va a `held` y se entrega junto con la siguiente frase citada y
    aprobada; `close()` sin ninguna frase citada no entrega nada y marca `no_evidence`.
  - Invariante: el texto unido de `delivered` es prefijo del texto final.
- [X] T006 [P] Agregar en `agent/review.py`:
  - `LOCAL_CHECKS = {"external_fact", "contact", "promise", "citation", "opinion"}`;
  - `review_sentence(sentence, plan, *, evidence, labels, names, playbook, recent_answers, threshold, is_first)`:
    aplica `LOCAL_CHECKS` y, si `is_first`, la repetición frente a las respuestas recientes (umbral 0.5, o 0.7 si la
    frase tiene menos de 8 palabras, R3);
  - `missing_required(text, plan) -> list[str]`, con las frases exigidas que faltan en la respuesta completa.
- [X] T007 [P] Extender `ChatState` en `agent/graph.py` con `lead: list[str]`, `delivered: list[str]` y
  `discarded: int`, e incluirlas en `TURN_RESET` (vacías y 0).
- [X] T008 [P] `src/proyecto_modelos_lenguaje/api_models.py`: `ContactTurnModel.discarded: int = Field(0, ge=0,
  le=20)`. `agent/care.py::update_contact` guarda `discarded` en cada entrada de `acts`.
- [X] T009 `agent/service.py`: con `delivery = "sentences"`, `_events` usa `stream_mode=["updates", "messages",
  "custom"]` y `stream_event` traduce `("custom", {"sentence": text, "index": i})` a
  `{"event": "sentence", "text", "index"}`. No emite `token` (G1). Con `complete`, el comportamiento es el de la spec
  020.
- [X] T010 `agent/graph.py` (depende de T005–T007): ensamblaje `lead + delivered + tail` (R8).
  - `route` calcula `lead`: límite por hostilidad, aviso de datos sensibles y, en `scripted`, la apertura empática
    (sale de `care.prefixes` y del aviso de `finalize`).
  - Helper `emit(state_or_list, texts)` que entrega frases con `get_stream_writer()` y devuelve la lista entregada.
  - Los nodos que generan entregan `lead` antes de su primera frase.
  - `finalize` arma la respuesta con `lead + delivered + tail` y entrega `tail` (`best_guess`, truncadas, oferta de
    recordar y frases exigidas). En las rutas sin generación (seguridad, identidad, perfil, acciones,
    `reply_node`), entrega la respuesta completa como frases con `SentenceSplitter` (G4).
  - Con `delivery = "complete"`, `finalize` se comporta como en la spec 020.
- [X] T011 [P] Pruebas en `tests/unit/agent/test_sentences.py`:
  - segmentación: abreviaturas («Sr.», «No. 3»), cifras con punto («4.416.312»), enumeradores, citas al final,
    fragmentos largos con corte en un espacio y primer fragmento más corto;
  - `SentenceGate`: `deliver`, `retry` en la primera frase, `stop` en conversación, descarte y continuidad en
    `retrieval`, frases retenidas sin cita y `no_evidence`;
  - invariante de prefijo con una propiedad sobre textos aleatorios.

**Checkpoint**: filtro, revisión por frase, evento `sentence` y ensamblaje listos. Las historias pueden empezar.

---

## Phase 3: User Story 1 - Ver la respuesta de la conversación sin esperar (Priority: P1) 🎯 MVP

**Goal**: `converse` entrega por frases revisadas; regenera solo si falla la primera; corta en la primera rechazada
posterior; usa el respaldo por frases si el modelo falla.

**Independent Test**: `pytest tests/integration/agent/test_sentence_flow.py -k us1 tests/api/test_sentence_stream.py`.

### Tests for User Story 1

- [X] T012 [P] [US1] Crear `tests/integration/agent/test_sentence_flow.py`, parametrizado por variante, con un
  `StreamingScriptModel` que transmite por palabras y puede fallar a mitad. Casos `us1`:
  - charla: varios eventos `sentence` y la unión igual a `turn.answer` (G2);
  - segunda frase con un dato externo: corte, la frase nunca aparece y aviso `sentence_discarded`;
  - primera frase con un dato externo: regeneración sin eventos previos;
  - error antes de la primera frase: respaldo por frases;
  - error a mitad: se conservan las frases y la respuesta cierra (SC-008);
  - primer saludo sin «Valer-IA Caña»: frase exigida al final en `tail`;
  - crisis y seguridad: texto fijo entregado por `finalize` (G4);
  - `delivery = "complete"`: sin `sentence`, comportamiento de la spec 020.
- [X] T013 [P] [US1] Crear `tests/api/test_sentence_stream.py`: `POST /api/chat/stream` en demo con «¡qué calor hace
  hoy!» emite `start`, `route`, uno o más `sentence` y `done`, sin `token` (G1). La unión es igual a
  `response.turn.answer`.

### Implementation for User Story 1

- [X] T014 [US1] Reescribir `_converse_node` en `agent/graph.py` para `delivery = "sentences"`:
  - consumir `model.stream(messages)` en un hilo con una cola;
  - leer con `stream_first_timeout_seconds` hasta la primera frase y `stream_idle_timeout_seconds` entre fragmentos;
  - pasar el texto por `SentenceGate(mode="conversation")` con `review_sentence`;
  - entregar `lead` y cada frase aprobada con `emit`;
  - ante `retry` (nada entregado), regenerar con `correction_note` hasta `max_regenerations` y después el respaldo;
  - ante `stop`, cortar el stream y, si la última frase no cierra con signo, agregar `close.short` a `tail`;
  - devolver `delivered`, `discarded`, `reviewed` y `turn_notices`.
- [X] T015 [US1] Respaldo por frases en `agent/graph.py`: cuando `converse` cae al respaldo (`_scripted_reply`), el
  texto se divide con `SentenceSplitter` y se entrega (`reviewed = "fallback"`). Si ya se entregaron frases antes del
  error, el respaldo no se entrega: el turno cierra con `close.short`.
- [X] T016 [US1] Modo demo en `agent/graph.py` y `agent/demo.py`: `demo_converse` produce el texto completo y se
  entrega por frases con el mismo filtro, con la revisión por frase (FR-017).
- [X] T017 [US1] Frases exigidas en `finalize` (`agent/graph.py`): si `missing_required(lead + delivered, plan)` no
  está vacío, se agrega una variante de `required.*` a `tail` (FR-008). Las respuestas a mensajes mínimos conservan
  2 frases o menos: el filtro corta después de la segunda frase entregada cuando `plan.length == "short"`
  (FR-011).
- [X] T018 [US1] Validar US1: `pytest tests/unit/agent tests/integration/agent/test_sentence_flow.py -k us1
  tests/api/test_sentence_stream.py tests/integration/agent/test_converse_flow.py` en verde, y
  `agent conduct --mode demo` en 24/24.

**Checkpoint**: la conversación llega frase por frase, revisada y sin texto retirado.

---

## Phase 4: User Story 2 - Respuestas sobre Manuelita sin frases que desaparecen (Priority: P2)

**Goal**: `answer` (cadena) y `agent` entregan frases citadas y revisadas; las frases sin respaldo nunca se
muestran.

**Independent Test**: `pytest tests/integration/agent/test_sentence_flow.py -k us2`.

### Tests for User Story 2

- [X] T019 [P] [US2] Casos `us2` en `tests/integration/agent/test_sentence_flow.py`:
  - pregunta sobre Manuelita: varios `sentence` con citas válidas;
  - frase con una cifra ausente de la evidencia: no aparece y la siguiente sí;
  - respuesta sin ninguna frase citada: un solo `sentence` con el mensaje de evidencia insuficiente;
  - «Según los documentos públicos de Manuelita:» retenida y entregada junto con la primera frase citada;
  - variante agente con una llamada a herramienta: lo previo a la herramienta no se entrega y `retracted` es falso.

### Implementation for User Story 2

- [X] T020 [US2] `_answer_node` en `agent/graph.py` con `delivery = "sentences"`:
  - consumir `chain.stream(...)` con `SentenceGate(mode="retrieval")` y la evidencia del turno (`evidence_text`);
  - el reintento con `STRICT_REMINDER` solo si no se entregó nada;
  - sin frases citadas, `FALLBACK_ANSWER` entregado como frase y `fallback = True`;
  - `citations` a partir de las etiquetas presentes en `delivered`.
- [X] T021 [US2] `_agent_node` en `agent/graph.py`: un `BaseCallbackHandler` con `on_llm_start` (reinicia el filtro
  de la llamada) y `on_llm_new_token(token, chunk)` (alimenta el filtro). Si `chunk.tool_call_chunks` no está vacío,
  se descarta el búfer de la llamada. La primera frase de cada llamada se retiene hasta la segunda frase o el fin sin
  herramientas (R7). La evidencia sale del texto de las herramientas ejecutadas (`ToolTrace` y
  `retriever.units_by_id`). Las frases aprobadas se entregan con `emit`.
- [X] T022 [US2] En el modo `sentences`, `finalize` (`agent/graph.py`) ya no ejecuta `_review_retrieval`, porque las
  frases llegan revisadas. En el modo `complete` lo mantiene. Las citas del turno se recalculan a partir de lo
  entregado.
- [X] T023 [US2] Validar US2: `pytest tests/integration/agent/test_sentence_flow.py -k us2
  tests/integration/agent/test_graph_chain.py tests/integration/agent/test_graph_agent.py` en verde.

**Checkpoint**: las respuestas con búsqueda llegan frase por frase y con citas, sin frases que desaparezcan.

---

## Phase 5: User Story 3 - La voz empieza con la primera frase (Priority: P3)

**Goal**: la web muestra los `sentence` y la voz los lee en cuanto llegan.

**Independent Test**: `cd web && npx vitest run src/test/ChatView.test.tsx src/test/ChatViewVoice.test.tsx
src/test/voice.test.ts`.

### Tests for User Story 3

- [X] T024 [P] [US3] Vitest en `web/src/test/ChatView.test.tsx`: un flujo SSE simulado con `sentence` muestra el
  texto en vivo frase por frase y termina con la respuesta de `done`.
- [X] T025 [P] [US3] Vitest en `web/src/test/ChatViewVoice.test.tsx` y `web/src/test/voice.test.ts`:
  - `pushSentence` encola la oración y pide el audio en el mismo ciclo, sin esperar texto nuevo;
  - `finishLive` no repite lo encolado.

### Implementation for User Story 3

- [X] T026 [P] [US3] `web/src/lib/types.ts`: `ChatStreamEvent` con `{event: "sentence"; text: string; index:
  number}` y `ContactTurn.discarded?: number`.
- [X] T027 [US3] `web/src/lib/voice.ts` y `web/src/lib/useVoice.ts`:
  - `pushSentence(text)` encola sin pasar por `SentenceSegmenter`;
  - `finishLive` lleva la cuenta de lo encolado para no leerlo otra vez.
- [X] T028 [US3] `web/src/components/ChatView.tsx`: en `liveStage`, ante `sentence`, agregar el texto (con un espacio,
  o un salto de línea si lo trae) con la etapa «Escribiendo…» y llamar a `voice.pushSentence(event.text)`.

**Checkpoint**: la web y la voz siguen el ritmo de las frases.

---

## Phase 6: User Story 4 - Medir el tiempo de respuesta (Priority: P4)

**Goal**: la evaluación mide la primera frase, el tiempo total, el texto retirado y las frases descartadas contra la
línea base `complete`.

**Independent Test**: `pytest tests/integration/agent/test_converse_eval.py` y `agent converse --mode demo`.

### Tests for User Story 4

- [X] T029 [P] [US4] `tests/integration/agent/test_converse_eval.py`:
  - el informe trae la sección `delivery` con `first_sentence_ms`, `done_ms`, `retracted_turns` y `discarded_rate`
    por clase;
  - `--baseline-delivery` agrega la línea base;
  - un turno inyectado con texto retirado hace fallar SC-003.

### Implementation for User Story 4

- [X] T030 [US4] `agent/converse_eval.py`: `send_turn` registra el tiempo del primer `sentence` (o del primer `token`
  en `complete`), el tiempo de `done`, el texto transmitido y `retracted` (el texto transmitido, sin contar
  espacios, no es prefijo de la respuesta final). `summarize_block` agrega `delivery` por clase de turno (conversación
  o búsqueda) y las metas de C §6.
- [X] T031 [US4] `agent/__main__.py` y `agent/converse_eval.py`:
  - `converse --baseline-delivery` repite los bloques con `delivery = "complete"`;
  - el informe Markdown agrega la sección «Entrega»;
  - `meets_hard` incluye SC-003, SC-004, SC-005 y SC-008, y en `real` también SC-001, SC-002 y SC-006.

  `agent/care_eval.py` mide la primera frase en lugar del primer token.
- [X] T032 [US4] Ejecutar `agent converse --mode real --variants chain agent --baseline --baseline-delivery
  --simulate --repeats 10 --json-out docs/evaluacion_conversacion.json`, más `agent care --mode real` y
  `agent conduct --mode real`. Registrar los resultados.

**Checkpoint**: las cuatro historias están completas y medidas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T033 [P] Crear `docs/decisions/0025-entrega-por-frases.md`:
  - decisión: filtro dentro de los nodos, nunca retirar texto, corte en conversación y descarte en búsqueda,
    retención de frases sin cita, callback por llamada en el agente;
  - alternativas descartadas de R1 y R7.
- [X] T034 [P] `CONSTITUTION.md` a v1.13.0: §3.7, la conversación guiada se entrega por frases revisadas y nunca se
  retira texto mostrado; `delivery = "complete"` como línea base.
- [X] T035 [P] `docs/prompt_log.md` §3.19: `care.md` 1.2 (SHA y secciones nuevas) y los resultados de T032.
- [X] T036 [P] `README.md` y `docs/demo.md`: la entrega por frases, la opción `delivery` y el recorrido de la
  quickstart §3.
- [X] T037 Ejecutar `UV_PROJECT_ENVIRONMENT=.venv make check` y corregir lo que falle. Ajustar
  `tests/api/test_chat_stream.py` y `tests/api/test_converse_api.py` donde esperan eventos `token`: en el modo
  `sentences` esperan `sentence`.
- [X] T038 Recorrido visual con Playwright y Chrome en un puerto distinto de 8000: vistas de visitante, técnica y
  móvil; frases que aparecen una por una; «Actos» con `✂N`; sin errores de consola.
- [X] T039 [P] `web/src/components/ContactRecordPanel.tsx`: la línea «Actos» marca `✂N` en los turnos con
  `discarded > 0`, con Vitest en `web/src/test/ContactRecordPanel.test.tsx`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias. T002 y T003 en paralelo.
- **Foundational (Phase 2)**: depende de T002. T004, T006, T007 y T008 en paralelo; T005 depende de T004; T009 de
  T002; T010 depende de T005 a T007; T011 de T004 y T005.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US2 (Phase 4)**: depende de Foundational. Comparte `graph.py` con US1, así que conviene hacerla después.
- **US3 (Phase 5)**: depende de T009 (evento `sentence`). Es independiente del backend de US1 y US2 para las
  pruebas con SSE simulado.
- **US4 (Phase 6)**: depende de US1 y US2 para medir; T029–T031 pueden avanzar en paralelo con US3.
- **Polish (Phase 7)**: depende de las historias elegidas. T034 va en el mismo commit que el código.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Orden: `sentences.py` → `review.py` → `graph.py` → `service.py` → web → evaluación.
- `graph.py` es compartido: sus tareas no se paralelizan entre historias.

### Parallel Opportunities

- Setup: T002 y T003.
- Foundational: T004, T006, T007 y T008; luego T011.
- US1: T012 y T013.
- US2: T019.
- US3: T024, T025 y T026.
- Polish: T033, T034, T035, T036 y T039.

---

## Parallel Example: Foundational

```bash
Task: "T004 SentenceSplitter en agent/sentences.py"
Task: "T006 review_sentence y missing_required en agent/review.py"
Task: "T007 lead/delivered/discarded en ChatState (agent/graph.py)"
Task: "T008 ContactTurnModel.discarded en api_models.py"
```

## Parallel Example: User Story 3

```bash
Task: "T024 Vitest de sentence en web/src/test/ChatView.test.tsx"
Task: "T025 Vitest de pushSentence en web/src/test/voice.test.ts"
Task: "T026 Evento sentence en web/src/lib/types.ts"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 y Phase 2: configuración, filtro, revisión por frase, evento `sentence` y ensamblaje.
2. Phase 3 (US1): `converse` por frases.
3. **Validar**: `pytest -k us1`, conducta en 24/24 y una medición rápida en real de la primera frase en
   conversación.
4. Ya resuelve la deuda principal: la primera frase de la conversación llega antes de 3 s.

### Incremental Delivery

1. US1 → conversación por frases (MVP).
2. US2 → respuestas con búsqueda sin frases que desaparecen.
3. US3 → web y voz al ritmo de las frases.
4. US4 → medición contra la línea base.
5. Polish → ADR 0025, Constitución v1.13.0, prompt log, documentación y verificación visual.

---

## Notes

- [P] = archivos distintos, sin dependencias.
- La etiqueta [Story] vincula cada tarea con su historia.
- Las pruebas corren sin red; `@network` solo en las corridas reales de T032.
- Autoría (§4.3): Claude Code no hace commit, push ni PR sin autorización explícita del integrante.
- No escribir en `data/` ni regenerar las capas.
- No tocar el servidor del usuario en el puerto 8000.
- Antes de las corridas reales, verificar que DeepSeek genera texto: `llm --check` no detecta la falta de saldo.

## Notas de implementación

- **Separadores**: cada frase entregada conserva su separador inicial (espacio, salto de línea o párrafo), así que
  `"".join(delivered)` reproduce el formato del modelo, incluidas las listas numeradas. La web agrega el texto tal
  cual llega; la voz recibe la frase sin espacios (`pushSentence(text.trim())`).
- **T005**: en las respuestas con búsqueda, una frase rechazada se descarta y la respuesta sigue, también si es la
  primera. El reintento estricto (`STRICT_REMINDER`) solo ocurre si al final no se entregó ninguna frase citada, que
  es el equivalente del reintento por falta de citas de la spec 020. El contrato §3 decía «retry» para la primera
  frase; se simplificó así porque una cifra mala en la primera frase no justifica regenerar una respuesta con citas.
- **T009**: la entrega por frases solo aplica en la conversación guiada (`ConversationConfig.sentences`). Con
  `mode = "scripted"` vale la spec 019 sin cambios, y las pruebas de las specs 014 a 019 siguen igual.
- **T010**: `lead` solo se calcula en los turnos que genera el modelo (`converse` o búsqueda). En los demás
  (seguridad, identidad, perfil, acciones), `finalize` arma la respuesta como antes y la entrega completa en frases.
- **T014**: el primer tiempo de espera de `converse` es el menor entre `stream_first_timeout_seconds` y
  `converse_timeout_seconds`, para respetar la configuración de la spec 020. Si el modelo falla a mitad, la última
  frase completa del búfer también se revisa y se entrega; un fragmento cortado nunca se muestra.
- **T021**: el agente usa un `BaseCallbackHandler` por turno (`_AgentSentences`). Si la variante se invoca sin
  streaming (por ejemplo `POST /api/chat`), la respuesta final se revisa completa por frases al terminar.
- **R17 (hallazgo)**: DeepSeek genera las respuestas cortas en unos 0.3 s después del primer fragmento (1.1–1.7 s).
  El retraso extra de la charla venía de la búsqueda del puente (~1.66 s por turno). Se resolvió con caché por tema y
  precalentamiento en segundo plano (`bridges.warm_up`), ver `research.md` R17.

**Cierre de T032–T038 (2026-11-20)**: evaluación real ejecutada (`docs/evaluacion_conversacion.md`); se corrigieron
`scrub_name` (texto mostrado), la URL de la cita como evidencia en el evaluador y la regresión «(no) soy una
persona» en la revisión por frase (`human_claim`; conducta real 24/24 en ambas variantes). Metas no cumplidas y
documentadas en `docs/prompt_log.md` §3.19: E-SC-001 (p90 3.6–3.9 s por el clasificador LLM del enrutador),
E-SC-002 / E-SC-006 (retención hasta la primera frase citada) y SC-002 (0.7, variación del muestreo).
`make check` en verde (pytest 1226, vitest 108, build) y recorrido visual en el puerto 8020 sin errores de consola.
