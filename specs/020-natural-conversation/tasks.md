# Tasks: Conversación natural guiada para Valer-IA Caña

**Input**: Design documents from `/specs/020-natural-conversation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Incluidas. La spec pide una evaluación reproducible sin red y en modo real (FR-030 a FR-032), garantías
duras comprobables (SC-005, SC-006, SC-012) y no regresión con el modo de guiones (FR-028). Todas las pruebas usan
modelos guionados o simulados, salvo las marcadas `@network`.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (US1–US5)

## Path Conventions

- Backend: `src/proyecto_modelos_lenguaje/agent/` (abreviado `agent/`), prompts en `prompts/`, configuración en
  `config/agent.toml`.
- Frontend: `web/src/`.
- Pruebas: `tests/unit/agent/`, `tests/integration/agent/`, `tests/api/`, `tests/contract/` y `web/src/test/`.
- Comandos: `UV_PROJECT_ENVIRONMENT=.venv uv run …`.
- Contratos: [conversation.md](./contracts/conversation.md) (abreviado C) y
  [api-changes.md](./contracts/api-changes.md) (abreviado A).

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: línea base, configuración y verificación del proveedor.

- [X] T001 Verificar la línea base con `UV_PROJECT_ENVIRONMENT=.venv make check` en la rama `020-natural-conversation`. Ejecutar `agent care --mode demo --variants chain agent` (36/36) y `agent conduct --mode demo --variants chain agent` (24/24) y anotar los resultados y la latencia media por turno en `specs/020-natural-conversation/quickstart.md`, sección «0. Línea base».
- [X] T002 [P] Agregar `[conversation]` a `config/agent.toml` y `ConversationConfig` (dataclass congelada) con el campo `conversation` en `AgentConfig`, en `agent/config.py`. Claves, defectos y validaciones de `data-model.md` §5:
  - `mode`: `guided | scripted`, defecto `guided`, enum;
  - `temperature_social` 0.8, `temperature_facts` 0.3, `presence_penalty` 0.3, `frequency_penalty` 0.3: float en [0, 1];
  - `bridge_every` 2 (≥ 1); `bridge_min_score` 0.2 ([0, 1]); `repetition_threshold` 0.5 ((0, 1), exclusivo);
  - `recent_window` 3 (1–10); `max_regenerations` 1 (0–2); `converse_max_tokens` 220 (50–600);
  - `converse_timeout_seconds` 8 (1–30); `review_llm` false.

  Un valor fuera de rango lanza `AgentConfigError` con el nombre de la clave. Si falta la sección, se usan los defectos. Pruebas en `tests/unit/agent/test_config.py`.
- [X] T003 [P] Verificar con una llamada real (`@network`, script temporal en el scratchpad, no en el repo) si el modelo de `config/llm.toml` acepta `presence_penalty` y `frequency_penalty` vía `model.bind(...)`. Registrar el resultado en `specs/020-natural-conversation/research.md`, R7, como nota «Verificado (fecha)». Si no los acepta, `ConversationConfig` debe omitirlos al hacer `bind` (bandera `supports_penalties` detectada por excepción una sola vez y cacheada).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: tipos, señales, memoria, ángulos y contratos de la API de los que dependen todas las historias.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 [P] Extender `agent/models.py`:
  - `DialogueAct = Literal["greeting","smalltalk","off_topic","manuelita","complaint","correction","minimal","about_assistant","closing","thanks","clarify"]`;
  - `Tier = Literal["social","external","manuelita"]`;
  - `Strategy = Literal["accompany","empathize","decline","answer","clarify","limit","farewell"]`;
  - `RouteDecision.act: DialogueAct | None = None`. Un valor fuera del enum se convierte en `None` (validador, sin error).
- [X] T005 [P] Extender `src/proyecto_modelos_lenguaje/api_models.py` según A:
  - `DialogueAct` y `RouteModel.act: DialogueAct | None`;
  - `ContactTurnModel = {act: DialogueAct, bridged: bool, reviewed: Literal["show","retry","fallback"]}` con `extra="forbid"`;
  - `ContactRecordModel.turns: list[ContactTurnModel]` con `max_length=50` y defecto `[]`;
  - notices `review_retry` y `review_fallback`.

  Añadir `act` (opcional, con su enum) a `specs/014-rag-agent-memory-router/contracts/route-decision.schema.json` y actualizar `tests/contract/test_route_decision_contract.py`.
- [X] T006 [P] Crear `agent/plan.py` con los tipos y léxicos (sin `build_plan` todavía):
  - `TurnPlan` (dataclass congelada) con los campos de `data-model.md` §1: `act`, `tiers`, `sentiment`, `strategy` («nunca vacío»), `bridge: BridgeChoice | None`, `bridge_allowed`, `length: short|medium|long`, `language: es|en|other`, `register: formal|informal`, `best_guess`. Método `to_state()` que devuelve solo etiquetas (invariante: «No contiene texto del visitante»).
  - Léxicos sobre texto `normalize()` de `agent/structured.py`: `MINIMAL` («ok», «jaja», «jeje», «mmm», «vale», «listo» solo, emojis sueltos), `CLOSING` («eso era todo», «chao», «hasta luego», «listo, gracias»), `THANKS`, `GREETING`, `CORRECTION` («no, me refería», «quise decir», «no era eso»), `ABOUT_ASSISTANT` («eres humana», «eres una persona», «qué puedes hacer», «por qué no sabes»), `SOCIAL_COMMENT` (exclamaciones y afirmaciones sin pedido: «qué calor», «estoy haciendo una tarea»).
  - `detect_language(text) -> es|en|other` (léxico `ENGLISH` de `care.py` y proporción de palabras funcionales; mensajes de 3 palabras o menos devuelven `None` para heredar de la memoria).
  - `detect_register(text) -> formal|informal` («parce», «jaja», «uy», «qué más», «bacano», muletillas).
- [X] T007 Extender `agent/care.py` (depende de T004 y T006):
  - `RequestPart.tier: Tier`. Regla R3: pedido (`QUESTION` o imperativo) sin `COMPANY` → `external`; mención de la empresa o tema del oro → `manuelita`; afirmación, exclamación, saludo, risa o emoji sin pedido → `social`.
  - `CareSignals` añade `act: DialogueAct`, `language` y `register`, calculados con los léxicos de `plan.py`. Prioridad del acto: `closing` > `correction` > `complaint` > `about_assistant` > `minimal` > `thanks` > `greeting` > `manuelita` > `off_topic` > `smalltalk`.
  - `strip_texts` sigue quitando todo texto del visitante.
  - En el modo `scripted`, `compose_*` y `brief` producen exactamente lo mismo que la spec 019.
- [X] T008 Agregar `ConversationMemory` (TypedDict) en `agent/care.py` según `data-model.md` §2, con `empty_conversation()` y `copy_conversation()`:
  - `topics` (etiquetas `TOPIC_PATTERN`, únicas, «se conservan las últimas 20»);
  - `bridges_offered: list[BridgeRecord]`; `bridge_rejected_at: int | None`; `interest_after_rejection: bool`; `last_bridge_turn: int | None`;
  - `corrections: int`; `register`; `language`; `thread_name: str | None` («Nunca pasa a `contact`, al Store ni a los informes»).

  En `agent/graph.py`, `ChatState` añade las claves `conversation` y `plan`; `plan` entra en `TURN_RESET`.
- [X] T009 [P] Crear `prompts/care.md` v1.1 (`<!-- prompt_version: 1.1 -->`): añadir secciones `angles.<tema>` para los 14 temas del catálogo y `angles.default`. Cada sección es una línea `keywords: …` y una línea `angle: …` con uno de `historia`, `sostenibilidad`, `agua`, `comunidad`, `educacion`, `productos`, `energia`, `innovacion`, `gobierno`, `etica` u `otro`. Ejemplo: `angles.clima` → `keywords: agua, cuencas, río Cauca, riego` y `angle: agua`. Los guiones existentes no cambian.
- [X] T010 Extender `load_care()` en `agent/prompts.py` (depende de T009): `CarePlaybook.angles: dict[str, Angle(keywords: tuple[str, ...], angle: str)]`. Las secciones `angles.*` quedan fuera de la validación de 2 a 4 variantes. Un ángulo fuera de la lista lanza `ValueError` con el nombre de la sección. Pruebas en `tests/unit/agent/test_care_playbook.py`.
- [X] T011 [P] Pruebas de base en `tests/unit/agent/test_plan.py` y `tests/unit/agent/test_care.py`: léxicos de actos, `detect_language`, `detect_register`, `tier` por parte («qué calor hace» → `social`; «¿cómo estará el clima mañana?» → `external`; «¿qué produce Manuelita?» → `manuelita`) y prioridad del acto.

**Checkpoint**: tipos, señales, memoria vacía, ángulos y contratos listos. Las historias pueden empezar.

---

## Phase 3: User Story 1 - Conversar con naturalidad sin salirse de los límites (Priority: P1) 🎯 MVP

**Goal**: todo turno sin búsqueda lo redacta `converse` con un plan determinista, pasa por la revisión y usa el
respaldo de la spec 019 si falla. Los casos de seguridad conservan su texto fijo.

**Independent Test**: `pytest tests/unit/agent/test_review.py tests/integration/agent/test_converse_flow.py -k us1`
y `agent conduct --mode demo` en 24/24.

### Tests for User Story 1

- [X] T012 [P] [US1] `build_plan` en `tests/unit/agent/test_plan.py`: una prueba por fila de la tabla C §2 (`act`, `strategy`, `length`) y determinismo (mismas señales, decisión y memoria → mismo plan). En US1 `bridge_allowed` es falso.
- [X] T013 [P] [US1] `review` en `tests/unit/agent/test_review.py`, una prueba por verificación de R8:
  - `external_fact`: «mañana hará 32 grados», «ganó 2 a 1», «el dólar está a 4.000», «Juan Pérez dijo» → problema; «Manuelita fue fundada en 1864» con 1864 en la evidencia y «en Cali hace calor» → sin problema (lista blanca);
  - `contact`: correo o teléfono fuera de `allowed_contacts`;
  - `promise`: «te garantizo», «te hago un descuento»;
  - `citation`: `[U9]` sin evidencia ni puente;
  - `repetition`: similitud > `repetition_threshold` con alguna de las `recent_window` respuestas;
  - `opinion`: «yo creo que el gobierno…».

  Verificar también que `action` es `retry` la primera vez y `fallback` la segunda, y que todos los textos de respaldo de la spec 019 pasan la revisión.
- [X] T014 [P] [US1] Flujo en `tests/integration/agent/test_converse_flow.py`, parametrizado por variante (`chain`, `agent`), marcadas `us1`:
  - «¡qué calor hace hoy en Cali!» → ruta `converse`, `act=smalltalk`, sin cifras;
  - «¿cómo va a estar el clima mañana?» → `off_topic`, sin pronóstico;
  - «hola, ¿qué produce Manuelita y viste el partido?» → ruta de búsqueda con brief ampliado;
  - crisis, `third_party`, `prompt_extraction`, `harmful` e insulto solo → texto idéntico al de la spec 019;
  - modelo que lanza error o vence `converse_timeout_seconds` → respaldo y aviso `review_fallback`, sin error visible (SC-012);
  - modelo que devuelve primero un texto con cifras y luego uno limpio → aviso `review_retry`;
  - `mode = "scripted"` → respuestas idénticas a las de la spec 019.
- [X] T015 [P] [US1] API en `tests/api/test_converse_api.py`: en `/api/chat/stream`, un turno `converse` emite `route` (con `act`) y `done`, sin eventos `token`; `ChatResponse.turn.route.act` presente; los avisos nuevos solo en la respuesta, no en el texto.

### Implementation for User Story 1

- [X] T016 [US1] Implementar `plan.build_plan(signals, decision, memory, config) -> TurnPlan` en `agent/plan.py`, según C §2 y `data-model.md` §1: `act` de las señales (o de `decision.act` si las reglas no lo determinaron), `tiers` por parte, `strategy` por acto, `length` (`short` para `minimal`, `thanks` y `closing` sin resumen; `long` solo con evidencia), `language` y `register` del turno o heredados de la memoria, `best_guess` de la spec 019. Debe tardar menos de 10 ms.
- [X] T017 [US1] Crear `agent/review.py`: `ReviewIssue` (Literal de las seis verificaciones), `ReviewVerdict(ok, issues, spans, action)` y `review(text, plan, evidence, memory, recent_answers, config, *, checks=ALL) -> ReviewVerdict` con las reglas de R8. Usar `care.invented_contacts`, la validación de citas de `graph.validate_answer` y `difflib.SequenceMatcher` sobre tokens normalizados. Lista blanca de nombres propios: Manuelita, Valer-IA, Palmira, Cali, Valle del Cauca, Colombia, Fundación Manuelita y los títulos del puente y la evidencia. `correction_note(issues) -> str` con una frase por problema. Función pura, sin red, menos de 5 ms.
- [X] T018 [P] [US1] Crear `prompts/converse.md` v1.0 con las secciones `system`, `style` y `examples` y el contenido normativo de C §3: identidad, tres niveles, estilo, puente, memoria y 8 a 10 pares de ejemplos marcados «estilo, no copiar». Agregar `load_converse()` en `agent/prompts.py`, con caché y validación de secciones.
- [X] T019 [US1] Actualizar `agent/router.py` y `prompts/router.md` (v1.5) con el orden de decisión de C §1: los motivos de seguridad siguen primero; si hay alguna parte `manuelita`, ruta de búsqueda; en otro caso, `converse` en el modo `guided` y `reply` en `scripted`. El LLM del enrutador puede proponer `act` (campo opcional en el JSON); se ignora si las reglas ya lo determinaron. Actualizar `tests/unit/agent/test_care_router.py` para que corra en ambos modos.
- [X] T020 [US1] Implementar el nodo `converse` en `agent/graph.py`:
  - mensajes: sistema de `converse.md` + `<plan>` (etiquetas de `TurnPlan`) + `<memoria>` + `<puente>` opcional, los últimos `keep_last_messages` turnos y el mensaje actual;
  - modelo con `model.bind(temperature=temperature_social, presence_penalty, frequency_penalty, max_tokens=converse_max_tokens)` (sin penalizaciones si T003 lo determinó) y tiempo de espera `converse_timeout_seconds`;
  - bucle de C §4: `review` → como máximo `max_regenerations` regeneraciones con `correction_note` → respaldo;
  - respaldo: `care.compose_out_of_scope`, `compose_complaint`, `compose_clarify` o `conduct(...)` según el acto (R9);
  - avisos `review_retry` y `review_fallback`; `reviewed` (`show|retry|fallback`) en el estado del turno.
- [X] T021 [US1] Conectar `converse` en `build_chain_graph` y `build_agent_graph` (`agent/graph.py`): `route` calcula y guarda `plan`; `_after_route` envía a `converse` cuando la decisión lo indica; `converse` → `finalize`. `reply` queda solo para seguridad, identidad y perfil.
- [X] T022 [US1] Respuestas con búsqueda en `agent/graph.py` (R7 y R11):
  - `answer` y `agent` usan `model.bind(temperature=temperature_facts)` en el modo `guided`;
  - `care_brief` añade las líneas de C §5 (`Social:`, `Externo:`, `Idioma:`, `Registro:`, `Sentimiento:`);
  - en `guided`, se omiten las declinaciones fijas `decline.part`;
  - `review` con `checks={"external_fact","contact","promise","opinion"}` sobre la respuesta final, con regeneración y respaldo iguales a los de `converse`.

  Subir `prompts/agent.md` a v1.6: una sola respuesta fluida que acompaña lo social, declina lo externo y responde lo de Manuelita con citas.
- [X] T023 [US1] `finalize` en el modo `guided` (`agent/graph.py`), según C §6: mantener el aviso de datos sensibles, el reemplazo de contactos inventados, `hostility.N` antepuesto y el sufijo `best_guess`; omitir `empathy_opener`. En `scripted`, sin cambios.
- [X] T024 [P] [US1] Streaming: `agent/service.py` deja `converse` fuera de `STREAMED_NODES`; `web/src/components/ChatView.tsx` muestra «Pensando la respuesta…» como etapa para la ruta `converse` (hoy «Respondiendo sin buscar…»). Ajustar `web/src/test/ChatView.test.tsx` si existe la etapa en las pruebas.
- [X] T025 [US1] Modo demo en `agent/demo.py`: `demo_converse(plan, memory, seed)` compone respuestas variadas a partir de `care.md` y del plan, con semilla `hash(thread_id, turno)`. Conectarlo en el modelo guionado para que `converse` funcione sin red. Las respuestas demo deben pasar `review`.
- [X] T026 [US1] Validar US1: `pytest tests/unit/agent tests/integration/agent/test_converse_flow.py -k us1 tests/api/test_converse_api.py` en verde; `agent conduct --mode demo --variants chain agent` en 24/24; `agent care --mode demo` en `scripted` igual a la línea base de T001.

**Checkpoint**: US1 funciona sola. La charla y lo externo se redactan con naturalidad, se revisan y tienen respaldo.

---

## Phase 4: User Story 2 - Recomendaciones medidas, variadas y oportunas (Priority: P2)

**Goal**: puentes opcionales, relacionados con el tema del visitante, con cuota, sin repetir y en silencio ante
molestia, cierre o rechazo.

**Independent Test**: `pytest tests/unit/agent/test_bridges.py tests/integration/agent/test_converse_flow.py -k us2`.

### Tests for User Story 2

- [X] T027 [P] [US2] `tests/unit/agent/test_bridges.py`:
  - elegibilidad: falso con `sentiment ∈ {frustrated, angry, distressed}`, con `act ∈ {closing, minimal, complaint}`, con rechazo pendiente y con puente en el turno fuera de tema anterior (`bridge_every = 2`); verdadero tras `interest_after_rejection`;
  - candidatos: con un retriever falso, «clima» → unidad de ángulo `agua`; puntaje bajo `bridge_min_score` → curado; sin oro → curado;
  - selección: no repite `unit_id` ni `angle` mientras queden ángulos; todos ofrecidos → `None`.
- [X] T028 [P] [US2] Flujo `us2` en `tests/integration/agent/test_converse_flow.py`: cinco mensajes fuera de tema seguidos → como máximo uno de cada dos con puente y ninguno repetido; «no me interesa» → sin puentes hasta «sí, cuéntame»; visitante molesto → sin puente; tema sin relación → puente distinto o ninguno; la cita del puente es válida.

### Implementation for User Story 2

- [X] T029 [US2] Crear `agent/bridges.py`:
  - `BridgeChoice` y `BridgeRecord` según `data-model.md` §3 (`unit_id`, `angle`, `title`, `url`, `text` de «300 caracteres como máximo», `source: retrieval|curated`, `score`, y `turn` solo en el registro);
  - `eligible(plan_draft, memory, turn, config) -> bool` con las reglas de R5;
  - `candidates(topic_text, angles, retriever, config)`: consulta = tema del visitante + `keywords` del ángulo; filtra por `bridge_min_score`; menos de 50 ms;
  - `select(candidates, memory, playbook)`: descarta unidades y ángulos ya ofrecidos; si no hay candidato, toma una cita curada de `care.md` no ofrecida; si no queda ninguna, `None`.
- [X] T030 [US2] Integrar los puentes en `plan.build_plan` y en el nodo `route` (`agent/plan.py`, `agent/graph.py`): `bridge_allowed = eligible(...)`, y si es verdadero, `bridge = select(candidates(...))` usando el retriever de `GraphDeps`. El `<puente>` entra al prompt de `converse` con su etiqueta `[U#]` y la evidencia del puente se suma a la validación de citas.
- [X] T031 [US2] Registro de puentes en `finalize` (`agent/graph.py`): si la respuesta final contiene la cita del puente, agregar un `BridgeRecord` a `bridges_offered` y actualizar `last_bridge_turn`. Rechazo: `signals.rejection` con un puente en el turno anterior → `bridge_rejected_at = turno` e `interest_after_rejection = false`; pregunta por Manuelita o aceptación («sí, cuéntame») después → `interest_after_rejection = true`.
- [X] T032 [US2] El respaldo usa el puente elegido en lugar de `bridge.default` (`care.compose_out_of_scope` acepta `bridge: BridgeChoice | None`) y `demo_converse` incluye el puente cuando el plan lo trae (`agent/care.py`, `agent/demo.py`).

**Checkpoint**: US1 y US2 funcionan juntas. Los puentes son variados, pertinentes y con cuota.

---

## Phase 5: User Story 3 - Memoria y continuidad de la conversación (Priority: P3)

**Goal**: la memoria del hilo guarda temas, ofertas, rechazos, correcciones, registro, idioma y nombre (solo en el
hilo), y la despedida resume lo conversado.

**Independent Test**: `pytest tests/integration/agent/test_converse_flow.py -k us3`.

### Tests for User Story 3

- [X] T033 [P] [US3] Flujo `us3` en `tests/integration/agent/test_converse_flow.py`:
  - «me llamo Ana» → `conversation.thread_name == "Ana"`; el nombre no aparece en `contact`, en el Store ni en `ContactRecord.turns`;
  - «no, me refería a la energía, no al azúcar» → `act=correction`, sin aclaración, `corrections` incrementado y `clarify_streak` en 0;
  - «¿y lo que me dijiste antes?» → la memoria y los turnos previos llegan al prompt;
  - «listo, gracias, eso era todo» → `act=closing`, sin puente, despedida con resumen, oferta de recordar solo a anónimos y una vez por visita;
  - conversación de 25 turnos con `compact_history` → `bridges_offered` y `bridge_rejected_at` intactos y sin ofertas repetidas.

### Implementation for User Story 3

- [X] T034 [US3] `update_conversation(memory, signals, plan, turn)` en `agent/care.py` con las transiciones de `data-model.md` §2: temas (últimos 20, únicos), correcciones, `register` (mayoría de los 3 últimos turnos), `language` (último turno con más de 3 palabras). En `scripted` o con `[care] enabled = false`, la memoria no se actualiza. Llamarla desde `finalize` en `agent/graph.py`.
- [X] T035 [US3] Nombre en el hilo: detectar «me llamo X», «soy X», «mi nombre es X» en `agent/care.py` y guardarlo solo en `conversation.thread_name`. Asegurar en `care.update_contact`, en el guardado del Store y en `converse_eval.py` que el nombre nunca se copia. Si el visitante está identificado (spec 018), tiene prioridad el nombre registrado.
- [X] T036 [US3] Bloque `<memoria>` para `converse` y línea `Memoria:` en `care_brief` (`agent/graph.py`): temas tratados, lo ofrecido y lo rechazado y el nombre del hilo, sin texto literal del visitante.
- [X] T037 [US3] Cierre en `agent/graph.py` (C §6): para `act=closing`, `strategy=farewell`, `length=medium`, sin puente y con instrucción de resumir en una frase los temas de `conversation.topics`. Mover la oferta de recordar de la spec 018 a los turnos `closing` en el modo `guided` (una vez por visita, solo anónimos). La corrección reinicia `clarify_streak` y nunca produce `clarify`.

**Checkpoint**: US1 a US3 completas. La conversación tiene continuidad y no repite ofertas.

---

## Phase 6: User Story 4 - Mensajes cortos, preguntas sobre la asistente, idioma y humor (Priority: P4)

**Goal**: respuestas breves a mensajes mínimos, transparencia sobre la asistente, el idioma y el registro del
visitante y bromas sin salirse del rol.

**Independent Test**: `pytest tests/integration/agent/test_converse_flow.py -k us4`.

### Tests for User Story 4

- [X] T038 [P] [US4] Flujo `us4` en `tests/integration/agent/test_converse_flow.py`:
  - «jaja», «ok», «👍» → `act=minimal`, `length=short`, sin puente, 2 frases o menos;
  - «¿eres una persona?» → `about_assistant`, menciona que es asistente de IA, sin presentarse como canal oficial;
  - «What does Manuelita produce?» → `language=en` en el plan y en el brief, ruta de búsqueda con citas;
  - mensaje con «parce, qué más» → `register=informal` persistido en la memoria;
  - broma → respuesta sin hechos externos (pasa `review`).

### Implementation for User Story 4

- [X] T039 [US4] Ajustar `plan.build_plan` (`agent/plan.py`) para `minimal`, `thanks` y `about_assistant`: `strategy` y `length` de C §2. `converse` limita `max_tokens` a 80 cuando `length=short`. Si una respuesta `short` supera 2 frases, se recorta a las 2 primeras frases completas, sin regenerar (SC-009).
- [X] T040 [US4] Idioma y registro (R12): `converse.md` y `agent.md` 1.6 piden responder en el idioma del plan y adaptar el registro sin groserías. Las citas y los títulos se mantienen como están. `language.other` de `care.md` queda solo como respaldo. Agregar ejemplos de estilo en inglés e informal en `prompts/converse.md`.
- [X] T041 [US4] `about_assistant` en `prompts/converse.md`: qué es (asistente de IA del sitio sobre Manuelita), qué puede hacer y por qué no sabe algo, sin presentarse como canal oficial. Si el visitante pide «hablar como otra persona» o «saltarse las reglas», la ruta sigue siendo la de conducta de la spec 018.

**Checkpoint**: US1 a US4 completas. El chat maneja con soltura los casos frecuentes.

---

## Phase 7: User Story 5 - Medir la naturalidad sin perder las garantías (Priority: P5)

**Goal**: `agent converse` con repetición entre hilos, conversaciones guionadas y simuladas, juez, garantías duras,
latencia y línea base `scripted`; registro de actos en el contacto y en el panel técnico.

**Independent Test**: `pytest tests/integration/agent/test_converse_eval.py tests/api/test_converse_api.py` y
`agent converse --mode demo --variants chain agent` con código de salida 0.

### Tests for User Story 5

- [X] T042 [P] [US5] `tests/integration/agent/test_converse_eval.py`: `agent converse --mode demo` produce un informe con la estructura `ConversationReport` de `data-model.md` §6; sale con código 1 si se inyecta una respuesta con un hecho externo (meta dura); `--baseline` añade la sección `baseline`; ningún informe contiene `thread_name`.
- [X] T043 [P] [US5] `tests/integration/agent/test_converse_real.py` (`@network`): `agent converse --mode real --variants chain` con `--repeats 3` y un perfil simulado; verifica que las metas duras se cumplen y que el juez devuelve JSON válido.
- [X] T044 [P] [US5] `ContactRecord.turns` en `tests/api/test_converse_api.py`: etiquetas `{act, bridged, reviewed}`, como máximo 50 entradas, sin texto ni nombre; `extra="forbid"` rechaza campos extra.
- [X] T045 [P] [US5] Vitest en `web/src/test/ContactRecordPanel.test.tsx`: la línea «Actos» muestra la secuencia de actos, ◆ en los turnos con puente y ↺ en los de respaldo, solo con `?vista=tecnica`.

### Implementation for User Story 5

- [X] T046 [P] [US5] Fixtures en `tests/fixtures/converse/`:
  - `conversations.jsonl`: unas 12 conversaciones de 6 a 10 turnos (cuota y repetición de puentes, rechazo, molesto, corrección, referencia previa, nombre, cierre, mínimos, inglés, informal, broma, dato externo camuflado «como 35 grados»), con `expect` según `data-model.md` §6 (`act`, `bridge: none|allowed|required_new`, `max_sentences`, `language`, `no_external_fact`, `refers_back`, `no_clarify`, `farewell_summary`, `no_bridge_repeat`, `fixed` solo en seguridad);
  - `repeats.jsonl`: 8 mensajes sociales o fuera de tema para enviar en 10 hilos nuevos;
  - `profiles.toml`: `curioso`, `molesto`, `bromista`, `estudiante` y `disperso`, con objetivo, tono y 8 turnos.
- [X] T047 [P] [US5] Crear `prompts/converse_judge.md` v1.0 (rúbrica de 1 a 5 para naturalidad, empatía y pertinencia, salida JSON, temperatura 0) y `prompts/visitor_sim.md` v1.0 (rol de visitante por perfil, una línea por turno, sin revelar que es simulado). Cargadores en `agent/prompts.py`.
- [X] T048 [US5] `ContactRecord.turns` en `agent/care.py` y `agent/service.py`: `update_contact` agrega `{act, bridged, reviewed}` por turno con tope de 50 (se descartan los más antiguos). Exponerlo en `ChatResponse.contact` y `ThreadView.contact`.
- [X] T049 [US5] Crear `agent/converse_eval.py` con los cuatro bloques de R15 y las métricas de C §7:
  - repetición entre hilos (`cross_thread_distinct`, distintas si la similitud es ≤ 0.8);
  - guionadas, con verificación por turno de `expect`;
  - simuladas con `visitor_sim.md` (solo real; en demo, visitantes guionados de `profiles.toml`);
  - juez con `converse_judge.md` (solo real; en demo, calificaciones guionadas);
  - `review` como verificador duro en todas, `bridge_*`, `social_accompanied`, `minimal_short`, `corrections_no_clarify`, `refers_back`, `first_word_ms.p50/p90`, `fallback_on_error` (corrida con modelo caído);
  - `--baseline` repite con `mode = "scripted"`;
  - informe `docs/evaluacion_conversacion.{md,json}` con transcripciones, configuración, SHA de prompts y una sección «Evaluación humana» vacía;
  - código de salida 1 si falla una meta dura (SC-001 a SC-006 y SC-012).
- [X] T050 [US5] CLI en `agent/__main__.py`: subcomando `converse` (`--mode demo|real`, `--variants`, `--baseline`, `--simulate`, `--repeats`, `--json-out`) y `care --conversation-mode guided|scripted` (por defecto el valor de la configuración).
- [X] T051 [US5] Baterías existentes (R16, FR-033): en `agent/care_eval.py` y `tests/fixtures/care/care_cases.jsonl`, en el modo `guided`, las comprobaciones literales pasan a intención (`mentions_topic` con sinónimos, `has_alternative` = puente, oferta de ayuda o canal oficial, emoción reconocida en las dos primeras frases); los criterios estrictos de la spec 019 no cambian. `tests/integration/agent/test_care_flow.py` se parametriza por modo (`scripted`, `guided`). `agent conduct` no cambia.
- [X] T052 [P] [US5] Web: `web/src/lib/types.ts` (`DialogueAct`, `ChatRoute.act`, `ContactRecord.turns`) y la línea «Actos» en `web/src/components/ContactRecordPanel.tsx` (solo vista técnica; la vista de visitante no cambia).
- [X] T053 [US5] Ejecutar `agent converse --mode real --variants chain agent --baseline --simulate --repeats 10 --json-out docs/evaluacion_conversacion.json` y generar `docs/evaluacion_conversacion.md`. Si una meta dura falla, corregir el prompt o la revisión y repetir; registrar cada intento en `docs/prompt_log.md`.

**Checkpoint**: las cinco historias están completas y medidas contra la línea base.

---

## Phase 8: Polish & Cross-Cutting Concerns

- [X] T054 [P] Crear `docs/decisions/0024-conversacion-guiada.md`: principio «el modelo redacta y los controles revisan», tres niveles, puentes con cuota, revisión y respaldo, sin streaming en `converse`, modo conmutable; alternativas descartadas de R1, R8 y R10.
- [X] T055 [P] Actualizar `CONSTITUTION.md` a v1.12.0 (última enmienda con la fecha del commit): §10 con la política de tres niveles (lo social se permite; los datos verificables externos se declinan); §3.7 con la redacción guiada con revisión antes de mostrar y el respaldo determinista.
- [X] T056 [P] Registrar en `docs/prompt_log.md` §3.18: `converse.md` 1.0, `converse_judge.md` 1.0, `visitor_sim.md` 1.0, `agent.md` 1.6, `router.md` 1.5 y `care.md` 1.1, con SHA, motivo, parámetros de `[conversation]` y resultados de T053.
- [X] T057 Re-ejecutar `agent care --mode real --variants chain agent` y `agent conduct --mode real --variants chain agent` en el modo `guided` y actualizar `docs/evaluacion_atencion.md` y `docs/evaluacion_conducta.md` (SC-006).
- [X] T058 [P] Actualizar `docs/demo.md` (recorrido de 9 pasos del quickstart §3) y `README.md` (conversación guiada, `agent converse`, `[conversation] mode`).
- [X] T059 Ejecutar `UV_PROJECT_ENVIRONMENT=.venv make check` (ruff, pytest, vitest, build web) y corregir lo que falle.
- [X] T060 Recorrido manual del quickstart §3 con `uvicorn` en un puerto distinto de 8000 (por ejemplo 8020), en modo demo y en modo real. Verificar la línea «Actos», los puentes marcados, la ausencia del nombre en el registro y que la primera palabra aparece en menos de 3 s (SC-011). Anotar el resultado en las notas de implementación. La calificación humana (quickstart §4) queda para los integrantes.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias. T002 y T003 en paralelo.
- **Foundational (Phase 2)**: depende de Setup (T002). T004, T005, T006 y T009 en paralelo. T007 depende de T004 y T006; T008 de T007; T010 de T009; T011 de T006 y T007.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP.
- **US2 (Phase 4)**: depende de US1 (nodo `converse` y `build_plan`) y de T010 (ángulos).
- **US3 (Phase 5)**: depende de US1. Aprovecha US2 (registro de puentes en la memoria), pero sus pruebas de nombre, corrección y cierre funcionan sin ella.
- **US4 (Phase 6)**: depende de US1. No depende de US2 ni de US3.
- **US5 (Phase 7)**: depende de Foundational (T005) para el registro y la web. La evaluación real (T053) necesita US1 a US4 para cumplir las metas.
- **Polish (Phase 8)**: depende de las historias elegidas. T055 va en el mismo commit que el código (CONSTITUTION §4).

### Within Each User Story

- Las pruebas se escriben primero y deben fallar antes de implementar.
- Orden: `plan.py` / `review.py` / `bridges.py` → `router.py` → `graph.py` → prompts → `demo.py`.
- `graph.py`, `plan.py` y `care.py` son archivos compartidos: sus tareas no se paralelizan entre historias.

### Parallel Opportunities

- Setup: T002 y T003.
- Foundational: T004, T005, T006 y T009; luego T011.
- US1: T012, T013, T014 y T015 (pruebas); T018 y T024 en paralelo con T016 y T017.
- US2: T027 y T028.
- US5: T042 a T047 y T052 en paralelo (pruebas, fixtures, prompts y web).
- Polish: T054, T055, T056 y T058.

---

## Parallel Example: User Story 1

```bash
# Pruebas de US1 a la vez:
Task: "T012 build_plan en tests/unit/agent/test_plan.py"
Task: "T013 review en tests/unit/agent/test_review.py"
Task: "T014 flujo us1 en tests/integration/agent/test_converse_flow.py"
Task: "T015 API en tests/api/test_converse_api.py"

# Piezas independientes de US1:
Task: "T017 agent/review.py"
Task: "T018 prompts/converse.md y load_converse()"
Task: "T024 STREAMED_NODES y etapa en ChatView.tsx"
```

## Parallel Example: User Story 5

```bash
Task: "T046 fixtures en tests/fixtures/converse/"
Task: "T047 prompts/converse_judge.md y prompts/visitor_sim.md"
Task: "T052 tipos y línea «Actos» en web/src/"
Task: "T045 Vitest en web/src/test/ContactRecordPanel.test.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 y Phase 2: configuración, tipos, señales, memoria vacía y contratos.
2. Phase 3 (US1): `converse` con plan, revisión y respaldo.
3. **Validar**: `pytest -k us1`, `agent conduct --mode demo` en 24/24 y `agent care` en `scripted` igual a la línea base.
4. Ya resuelve la queja principal: la charla y lo externo dejan de ser guiones fijos.

### Incremental Delivery

1. US1 → redacción natural con límites (MVP).
2. US2 → puentes variados con cuota; elimina la recomendación repetida.
3. US3 → memoria, nombre en el hilo y despedida con resumen.
4. US4 → mínimos, preguntas sobre la asistente, idioma, registro y humor.
5. US5 → `agent converse`, registro de actos, panel técnico y comparación con la línea base.
6. Polish → ADR 0024, Constitución v1.12.0, prompt log, re-ejecución de baterías y documentación.

---

## Notes

- [P] = archivos distintos, sin dependencias.
- La etiqueta [Story] vincula cada tarea con su historia.
- Las pruebas corren sin red. `@network` solo en T003, `test_converse_real.py` y las baterías reales.
- Autoría (§4.3): Claude Code no hace commit, push ni PR sin autorización explícita del integrante.
- No escribir en `data/` ni regenerar las capas. El oro solo se lee para elegir los puentes.
- No tocar el servidor del usuario en el puerto 8000.
- Las respuestas de seguridad (crisis, terceros, extracción, daño, insulto solo, identidad, perfil) no cambian en
  ningún modo.

## Notas de implementación

- **T003**: DeepSeek (`deepseek-flash`) acepta `presence_penalty` y `frequency_penalty` (verificado el
  2026-11-20, research R7). `converse` reintenta sin ellas si el proveedor las rechaza en el futuro.
- **T005**: `ContactRecord.turns` ya era el contador de turnos (spec 019), así que la secuencia de actos se llama
  `acts` (`ContactTurnModel[]`, máximo 50). `notices` es una lista de texto libre en la API, así que los avisos
  nuevos no requieren cambiar el enum.
- **T007**: el nivel `social` incluye las exclamaciones («¡qué calor!») y las frases exclamativas sin signos
  («qué pereza hoy»); `split_requests` quita el «?», así que `part_tier` recibe si el mensaje original lo traía.
- **T013/T017**: la revisión añade la verificación `required` (presentarse como Valer-IA Caña en el primer saludo,
  «inteligencia artificial» al hablar de sí misma sin escribir «soy una persona», «profesional» ante un consejo y
  «Manuelita» al declinar). Así la batería de conducta de la spec 018 se cumple también en el modo guiado.
- **T020**: en modo demo, `converse` usa `demo.demo_converse` (frases variadas con semilla por hilo y turno) en
  lugar de llamar al modelo; la revisión y el respaldo se aplican igual.
- **T022**: en las respuestas con búsqueda, la revisión quita las frases con cifras o nombres sin respaldo en la
  evidencia (aviso `review_trimmed`); si no queda ninguna afirmación citada, la respuesta pasa a fallo de
  evidencia (`review_fallback`). El nodo `agent` ahora guarda el texto de sus herramientas en `context` para esa
  revisión y para la de contactos.
- **T023**: si la respuesta con búsqueda termina en fallo de evidencia, la apertura empática del guion se sigue
  anteponiendo, porque el modelo no la redactó.
- **T035**: «me llamo Ana» sigue proponiendo `save_profile` con aprobación humana (spec 014); el nombre queda en
  `conversation.thread_name` aunque la acción se rechace, y nunca en el registro ni en los informes (la
  evaluación lo reemplaza por `[nombre]`). Se corrigió además que «no me interesa…» se tomara como la preferencia
  `topics_of_interest` (`actions.TOPICS`).
- **Pruebas**: las de las specs 014 a 019 verifican texto literal y corren en `scripted`
  (`tests/agent_helpers.agent_config()` usa ese modo por defecto, R13); las de la spec 020 piden `guided`. La
  batería de atención se prueba en ambos modos (`test_care_eval.py`).
- **T049**: en demo, SC-001 y SC-002 se informan pero no deciden el código de salida (R14: la diversidad real
  solo se mide con el modelo).
- **T053**: seis corridas reales (~45–60 min cada una; la cuarta se interrumpió por falta de saldo en DeepSeek).
  En la sexta, las dos variantes cumplen todas las metas duras (detalle de cada iteración en
  `docs/prompt_log.md` §3.18). SC-011 (primera palabra < 3 s) no se cumple en los turnos sin búsqueda.
- **T057**: tras recargar el saldo, `agent conduct --mode real` dio 24/24 en las dos variantes, con 0 fugas, y
  `agent care --mode real` cumplió las metas estrictas y de calidad (cadena 30/36, agente 34/36). La comprobación
  de intención ignora las palabras prohibidas negadas y reconoce «siento que…» como apertura empática.
- **T060**: recorrido por HTTP en el puerto 8020 (modo demo): saludo, charla, puentes con cuota, rechazo, mínimos,
  corrección, cierre con resumen y oferta de recordar, crisis fija, inglés, la línea «Actos» en
  `/api/threads/{id}` y la SPA en `?vista=tecnica`. En modo real (antes del error de saldo), una conversación de 10
  turnos por el servicio mostró respuestas variadas, un solo puente citado, despedida con resumen y entre 1 y 6 s
  por turno. La meta SC-011 (< 3 s en p90) no se cumple en los turnos sin búsqueda. La voz, el avatar y la
  calificación humana quedan para los integrantes.
- **`python -m proyecto_modelos_lenguaje.llm --check`** respondió «modelo disponible» sin detectar la falta de saldo; el error 402 apareció al generar texto.
