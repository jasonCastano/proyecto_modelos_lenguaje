# Data Model: Conversación natural guiada (spec 020)

Todas las entidades viven en el estado del hilo (checkpointer de LangGraph) o en los informes de evaluación. Nada
se escribe en `data/` ni en el Store por usuario.

## 1. TurnPlan (por turno, no persistente)

Lo calcula `plan.build_plan(signals, decision, memory, config)` en el nodo `route`.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `act` | `DialogueAct` | Uno de `greeting`, `smalltalk`, `off_topic`, `manuelita`, `complaint`, `correction`, `minimal`, `about_assistant`, `closing`, `thanks` o `clarify` |
| `tiers` | `list[Tier]` | Uno por parte (`social`, `external`, `manuelita`), en el orden de `care.split_requests`; como máximo `[care] max_requests` |
| `sentiment` | `Sentiment` | Viene de `care.analyze`; el LLM del enrutador puede refinarlo (spec 019, R3) |
| `strategy` | `list[Strategy]` | Uno o más de `accompany`, `empathize`, `decline`, `answer`, `clarify`, `limit` y `farewell`; nunca vacío |
| `bridge` | `BridgeChoice \| None` | Solo si `bridge_allowed` es verdadero (ver §3) |
| `bridge_allowed` | `bool` | Resultado de la elegibilidad de R5 |
| `length` | `short \| medium \| long` | `short` para `minimal`, `thanks` y `closing` sin resumen; `medium` por defecto; `long` solo con evidencia |
| `language` | `es \| en \| other` | Viene de la memoria o de la detección del turno |
| `register` | `formal \| informal` | Viene de la memoria o de la detección del turno |
| `best_guess` | `bool` | Spec 019: aclaración repetida |

**Invariantes**:
- No contiene texto del visitante, solo etiquetas.
- `bridge_allowed` es falso si se cumple cualquiera de estas condiciones:
  - `sentiment ∈ {frustrated, angry, distressed}`;
  - `act ∈ {closing, minimal, complaint}`;
  - hubo un rechazo pendiente;
  - hubo un puente en el turno fuera de tema anterior.

## 2. ConversationMemory (estado del hilo, clave `conversation`)

| Campo | Tipo | Reglas |
|-------|------|--------|
| `topics` | `list[str]` | Etiquetas saneadas (`TOPIC_PATTERN`), únicas; se conservan las últimas 20 |
| `bridges_offered` | `list[BridgeRecord]` | Se agrega una cuando la respuesta final contiene la cita del puente |
| `bridge_rejected_at` | `int \| None` | Turno del último rechazo explícito a una sugerencia |
| `interest_after_rejection` | `bool` | Se vuelve verdadero si el visitante pregunta por Manuelita o acepta («sí, cuéntame») después del rechazo |
| `last_bridge_turn` | `int \| None` | Último turno con puente, para la cuota `bridge_every` |
| `corrections` | `int` | Contador de actos `correction` |
| `register` | `formal \| informal` | Se actualiza con cada turno (mayoría de los 3 últimos) |
| `language` | `es \| en \| other` | Idioma del último turno con más de 3 palabras |
| `thread_name` | `str \| None` | Nombre dado en el hilo («me llamo Ana»). Nunca pasa a `contact`, al Store ni a los informes. Se borra con el hilo |

**Transiciones**:
- Si `act = correction`, se incrementa `corrections` y se reinicia `clarify_streak` (spec 019).
- Si hay un rechazo de puente (`signals.rejection` con un puente ofrecido en el turno anterior), se asigna
  `bridge_rejected_at = turno` y `interest_after_rejection = false`.
- Si hay interés después del rechazo, se asigna `interest_after_rejection = true` y vuelve a permitirse el puente.
- Si `[care]` está desactivado o `[conversation] mode = "scripted"`, la memoria no se actualiza (línea base).

## 3. BridgeChoice / BridgeRecord

| Campo | Tipo | Reglas |
|-------|------|--------|
| `unit_id` | `str` | Unidad del oro (`unit_…`) |
| `angle` | `str` | Uno de `historia`, `sostenibilidad`, `agua`, `comunidad`, `educacion`, `productos`, `energia`, `innovacion`, `gobierno`, `etica` o `otro` |
| `title`, `url` | `str` | Vienen de la unidad del oro |
| `text` | `str` | Extracto citable, de 300 caracteres como máximo |
| `source` | `retrieval \| curated` | De dónde salió el candidato (R5) |
| `score` | `float` | Puntaje del retriever (0 si es `curated`) |
| `turn` | `int` | Solo en `BridgeRecord` |

**Reglas**:
- No se repiten un `unit_id` ni un `angle` dentro del hilo mientras queden ángulos sin ofrecer.
- La cita se valida contra el oro igual que las demás.

## 4. ReviewVerdict (por respuesta, no persistente)

| Campo | Tipo | Reglas |
|-------|------|--------|
| `ok` | `bool` | Verdadero si `issues` está vacío |
| `issues` | `list[ReviewIssue]` | Elementos de `external_fact`, `contact`, `promise`, `citation`, `repetition` y `opinion` |
| `spans` | `list[str]` | Fragmentos que dispararon cada problema, solo para la traza técnica y las pruebas; no van al registro del contacto |
| `action` | `show \| retry \| fallback` | `retry` solo una vez por turno |

## 5. Cambios en entidades existentes

- **`RouteDecision`** (spec 014/019): nuevo campo opcional `act: DialogueAct | None`, que el enrutador LLM puede
  proponer. Se ignora si las reglas ya lo determinaron.
- **`ChatState`**: claves nuevas `conversation` (ConversationMemory) y `plan` (TurnPlan, se reinicia en
  `TURN_RESET`).
- **`ContactRecord`** (spec 019): nuevo campo `turns: list[ContactTurn]`, con un máximo de 50 entradas, donde
  `ContactTurn = {act: DialogueAct, bridged: bool, reviewed: show|retry|fallback}`. Siempre lleva etiquetas
  controladas.
- **`notices`**: valores nuevos `review_retry` y `review_fallback`.
- **`AgentConfig`**: nuevo `ConversationConfig`:

  | Clave | Tipo | Defecto | Validación |
  |-------|------|---------|------------|
  | `mode` | `guided \| scripted` | `guided` | enum |
  | `temperature_social` | float | 0.8 | [0, 1] |
  | `temperature_facts` | float | 0.3 | [0, 1] |
  | `presence_penalty` | float | 0.3 | [0, 1] |
  | `frequency_penalty` | float | 0.3 | [0, 1] |
  | `bridge_every` | int | 2 | ≥ 1 |
  | `bridge_min_score` | float | 0.2 | [0, 1] |
  | `repetition_threshold` | float | 0.5 | (0, 1) |
  | `recent_window` | int | 10 | 1–10 (comparación con todo el hilo, SC-001) |
  | `max_regenerations` | int | 1 | 0–2 |
  | `converse_max_tokens` | int | 220 | 50–600 |
  | `converse_timeout_seconds` | float | 8 | 1–30 |
  | `review_llm` | bool | false | — |

## 6. Evaluación (informes, no estado)

- **ConverseCase** (`tests/fixtures/converse/conversations.jsonl`):
  - `id`;
  - `profile`;
  - `turns: [{message, expect}]`, donde `expect` admite `act`, `bridge` (`none \| allowed \| required_new`),
    `max_sentences`, `language`, `no_external_fact`, `refers_back`, `no_clarify`, `farewell_summary`,
    `no_bridge_repeat` y `fixed` (texto exacto, solo en los casos de seguridad).
- **SimulatedConversation**:
  - `profile ∈ {curioso, molesto, bromista, estudiante, disperso}`;
  - `turns: [{visitor, assistant, act, bridged, review}]`;
  - `scores: {naturalness, empathy, relevance}` (1–5, del juez).
- **ConversationReport**:
  - `mode`, `variant`, `created_at`;
  - `diversity: {within_thread_max_similarity, cross_thread_distinct}`;
  - `bridges: {per_offtopic_turn, repeats, after_rejection, with_upset}`;
  - `judge: {naturalness, empathy, relevance}`;
  - `hard: {external_facts, contacts, promises, crisis, conduct}`;
  - `latency_ms: {p50, p90}`;
  - `baseline` (la misma estructura en `scripted`);
  - `human: {raters, average}`.
