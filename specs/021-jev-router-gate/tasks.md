---

description: "Tareas de implementación del gatekeeper System One (Jev) para el enrutador de Valer-IA"
---

# Tasks: Gatekeeper System One (Jev) para el enrutador de Valer-IA

**Input**: Documentos de diseño en `specs/021-jev-router-gate/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md),
[data-model.md](./data-model.md), [contracts/jev-gate.md](./contracts/jev-gate.md), [quickstart.md](./quickstart.md)

**Tests**: incluidas. La spec las exige (FR-013, SC-006: la suite pasa sin red ni clave) y la constitución pide
pruebas unitarias y de extremo a extremo sin red. Se escriben antes de la implementación de cada historia.

**Organization**: por historia de usuario. US1 y US2 son P1; US2 (respaldo) se implementa junto con US1 porque es lo que
hace seguro desplegarla.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: paralelizable (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de la spec (US1–US4)
- Rutas relativas a la raíz del repositorio; el paquete es `src/proyecto_modelos_lenguaje/`

---

## Phase 1: Setup (configuración compartida)

**Purpose**: dependencias, configuración, prompts y datos de validación

- [X] T001 Mover `httpx>=0.28.1` del grupo `dev` a `[project].dependencies` en `pyproject.toml` y regenerar `uv.lock` con `uv lock` (research R1)
- [X] T002 [P] Añadir la sección `[jev]` a `config/agent.toml` con comentarios: `enabled = false`, `base_url = "https://api.typesafe.ai"`, `model = "jev-1.14.0"`, `route_threshold = 0.75`, `crisis_threshold = 0.5`, `timeout_seconds = 2.0`, `max_input_chars = 4000`, `signals = ["route", "scope", "annoyance", "crisis"]` (data-model `JevConfig`)
- [X] T003 [P] Añadir a `.env.example` el bloque comentado de Jev: `TYPESAFE_API_KEY=` vacía y `# MANUELITA_JEV_ENABLED=1`, sin valores reales (FR-019)
- [X] T004 [P] Crear `prompts/jev.md` con versión y secciones `route`, `scope`, `annoyance` y `crisis` en el formato que lee `agent/prompts.py`: instrucciones en español y descripción de cada opción (rutas redactadas a partir de `prompts/router.md`; motivos `off_topic`, `abuse`, `harmful`, `third_party`, `prompt_extraction`, `advice`; niveles «calmado», «inconforme», «molesto», «muy molesto»; crisis = riesgo para la vida o la integridad) (research R11, data-model `GateQuestionSet`)
- [X] T005 [P] Crear `tests/fixtures/jev/validation_es.jsonl` con 24 consultas nuevas en español, 4 por ruta (`direct`, `documental`, `structured`, `mixed`, `out_of_scope`, `clarify`), con campos `query_id` (`v01`–`v24`), `question`, `history` y `expected_route`; ninguna puede estar en `tests/fixtures/rag/module2_queries.jsonl` (research R10)

---

## Phase 2: Foundational (prerrequisitos bloqueantes)

**Purpose**: configuración tipada, cliente que nunca lanza excepciones, simulación y **validación preliminar en español**

**⚠️ CRITICAL**: ninguna historia empieza hasta cerrar esta fase. Si T014 da una exactitud < 80 %, se detiene la
integración y se salta directo a T046–T048 (documentar como descartado, SC-009).

- [X] T006 Añadir `JevConfig` (dataclass congelada) y su carga desde `[jev]` en `src/proyecto_modelos_lenguaje/agent/config.py`, incluida en `AgentConfig`, con estas validaciones exactas: `base_url` empieza por `https://` y sin barra final; `model` no vacío y MUST NOT terminar en `latest`; `0.5 ≤ route_threshold ≤ 1.0`; `0.1 ≤ crisis_threshold ≤ 0.9`; `0.2 ≤ timeout_seconds ≤ 10`; `500 ≤ max_input_chars ≤ 30000`; `signals` subconjunto de `route`, `scope`, `annoyance`, `crisis` con `route` obligatorio; `MANUELITA_JEV_ENABLED=1|0` sobrescribe `enabled`; errores con `AgentConfigError` (data-model `JevConfig`)
- [X] T007 [P] Ampliar `src/proyecto_modelos_lenguaje/agent/models.py`: `DecidedBy = Literal["rules", "llm", "demo", "jev"]` y `TurnMetrics.gate_calls: int = Field(default=0, ge=0)` (data-model, research R13)
- [X] T008 [P] Escribir pruebas de configuración en `tests/unit/test_jev.py`: valores por defecto, cada rango rechazado, `model` con `latest` rechazado, `signals` sin `route` rechazado y sobrescritura por `MANUELITA_JEV_ENABLED`
- [X] T009 Crear `src/proyecto_modelos_lenguaje/agent/jev.py` con los modelos Pydantic `GateDecision` (`route`, `probabilities` de las seis rutas con suma ≈ 1 ± 0,01, `confidence = probabilities[route]`, `alternative` = segunda más probable, `scope_reason` solo si `route == "out_of_scope"`), `GateSignals` (`crisis_probability`, `annoyance` 0–3, `annoyance_level = round(annoyance)`) y `GateOutcome` (`status` en `ok|failed|skipped`; `reason` en `timeout`, `network`, `http_401`, `http_402`, `http_422`, `http_429`, `http_5xx`, `invalid_response`, `refusal`, `disabled`, `no_key`, `smalltalk`, `write_intent`; `latency_ms ≥ 0`; `cost`; `model`) y el protocolo `JevGate.assess(message, history) -> GateOutcome` (data-model, contrato §3)
- [X] T010 Implementar en `src/proyecto_modelos_lenguaje/agent/jev.py` el cliente `TypeSafeJevGate` con `httpx`: `POST {base_url}/v1/systemone` con `Authorization: Bearer` y el cuerpo `{model, state, questions}` del contrato §1, solo con las preguntas de `signals`; `state` con `mensaje` e `historial` pasados por `privacy.redact_pii()` y recortados a `max_input_chars` empezando por el historial; timeout total `timeout_seconds`, sin reintentos; validación de la respuesta (contrato §2) y conversión de **todo** fallo en `GateOutcome(status="failed", reason=...)` sin lanzar excepciones; la clave se lee de `TYPESAFE_API_KEY` (con el `load_dotenv` del proyecto) y nunca se guarda en atributos serializables ni en mensajes de error (research R1, R7, R8)
- [X] T011 Implementar en `src/proyecto_modelos_lenguaje/agent/jev.py` `FakeJevGate` determinista (ruta desde `router.heuristic_decision()` con probabilidad configurable, crisis desde `care.detect_crisis()`, molestia desde `care.detect_sentiment()`, y respuestas o fallos inyectables para las pruebas) y `build_gate(config, *, demo=False) -> JevGate | None` (devuelve `None` si `enabled` es falso o falta la clave y registra el motivo una sola vez; `FakeJevGate` en demo) (research R9, R12)
- [X] T012 [P] Escribir pruebas del cliente en `tests/unit/test_jev.py` con `httpx.MockTransport`: cuerpo de la solicitud (modelo fijo, preguntas según `signals`), enmascaramiento de correo, teléfono y documento, recorte del historial, respuesta válida → `ok` con confianza y alternativa correctas, y cada fallo (`timeout`, red, 401, 402, 422, 429, 5xx, sin `answers`, opción desconocida, `refusal`, probabilidades que no suman 1) → `failed` con su `reason`; ninguna excepción escapa y la clave no aparece en `repr()` ni en los mensajes
- [X] T013 Añadir el subcomando `jev` con `--validate [--json]` en `src/proyecto_modelos_lenguaje/agent/__main__.py`: envía `tests/fixtures/jev/validation_es.jsonl` al gatekeeper real y reporta exactitud, cobertura y exactitud por umbral (0,60; 0,70; 0,75; 0,80; 0,90) y matriz de confusión; sin clave termina con código 2 y el mensaje «añade TYPESAFE_API_KEY a .env» (contrato §5, FR-024)
- [X] T014 **Puerta**: ejecutar `uv run python -m proyecto_modelos_lenguaje.agent jev --validate` con la clave real; confirmar la forma real de la API (ajustar `contracts/jev-gate.md` y T010 si difiere), la versión disponible (si 1.14 no está, fijar 1.13 y anotarlo) y el umbral; registrar el resultado en `specs/021-jev-router-gate/research.md` (R5, R10) y fijar `route_threshold` en `config/agent.toml`. Exactitud < 80 % ⇒ detener y pasar a T046–T048 (SC-009)

**Checkpoint**: gatekeeper validado en español, cliente probado offline y umbral congelado.

---

## Phase 3: User Story 1 — Decisión de ruta rápida con el gatekeeper (Priority: P1) 🎯 MVP

**Goal**: reglas → Jev → clasificador LLM; si Jev alcanza el umbral, decide y se ahorra la llamada a DeepSeek.

**Independent Test**: con el gatekeeper activado, las 44 consultas del Módulo 2 registran qué etapa decidió, con qué
confianza, y la ruta coincide con la etiqueta (quickstart, escenario 5).

### Tests for User Story 1 ⚠️

- [X] T015 [P] [US1] Escribir `tests/unit/test_router_jev.py`: confianza ≥ umbral (incluido el valor exacto) → `decided_by="jev"`, `model_calls == 0` y alternativa registrada; confianza < umbral → decide el LLM y `RouterResult.gate` conserva la sugerencia; las reglas ganan aunque Jev diga otra cosa; `clarify` de Jev con confianza alta se respeta; `effective(min_confidence)` se aplica a la decisión final; `scope_reason` del gatekeeper solo con `out_of_scope`
- [X] T016 [P] [US1] Escribir en `tests/integration/agent/test_jev_flow.py` pruebas del nodo `route` con `FakeJevGate`: se consulta una sola vez por turno, recibe el historial de `ROUTER_HISTORY_TURNS`, no se consulta en charla trivial (solo palabras de `SMALLTALK`), ni en acciones de escritura ni en preguntas de perfil (`GateOutcome.status="skipped"` con su `reason`), y `TurnMetrics.gate_calls` cuenta las consultas

### Implementation for User Story 1

- [X] T017 [US1] Añadir el parámetro `gate: GateOutcome | None = None` a `route_message()` en `src/proyecto_modelos_lenguaje/agent/router.py`, evaluado después de `rule_decision()` y antes del clasificador LLM; con `status == "ok"` y `confidence ≥ route_threshold` construir `RouteDecision(decided_by="jev", confidence, alternative, scope_reason, reason="gatekeeper Jev: …")`; añadir `gate` a `RouterResult` (contrato §4, pasos 4–7)
- [X] T018 [US1] Integrar en `_route_node` de `src/proyecto_modelos_lenguaje/agent/graph.py`: `GraphDeps` recibe el gatekeeper (`build_gate`), se llama a `gate.assess(routed_text(...), history)` tras `care.analyze()` salvo charla trivial, escritura o perfil, se pasa el resultado a `route_message(..., gate=...)`, se suma a `TurnMetrics.gate_calls` y se guarda el `GateOutcome` en el estado del turno
- [X] T019 [US1] Construir el gatekeeper donde se crean las dependencias del grafo (`src/proyecto_modelos_lenguaje/agent/service.py` y la API) con `build_gate(config.jev, demo=...)`, de modo que el modo demo use `FakeJevGate` solo si `[jev].enabled` está activo
- [X] T020 [US1] Añadir el bloque `jev` a `turn_record()` en `src/proyecto_modelos_lenguaje/agent/observability.py` (`status`, `reason`, `route`, `confidence`, `alternative`, `accepted`, `latency_ms`, `cost`, `model`), sin texto del visitante ni clave (FR-021, research R13)
- [X] T021 [P] [US1] Mostrar `decided_by="jev"`: ampliar el tipo en `web/src/lib/types.ts` a `"rules" | "llm" | "demo" | "jev"`, añadir la etiqueta «Jev» en `DECIDED_LABEL` de `web/src/components/ChatView.tsx` y un caso en `web/src/test/ChatView.test.tsx`
- [X] T022 [US1] Hacer que `agent chat` imprima `ruta <ruta> (<confianza>, jev)` cuando decide el gatekeeper en `src/proyecto_modelos_lenguaje/agent/__main__.py` y verificar el escenario 5 del quickstart con la clave real

**Checkpoint**: US1 funcional; con `[jev].enabled = false` todo sigue igual que antes.

---

## Phase 4: User Story 2 — Funcionamiento seguro sin el gatekeeper (Priority: P1)

**Goal**: sin clave, sin red, en demo o con el servicio fallando, la conversación funciona exactamente igual que hoy.

**Independent Test**: suite completa y una conversación demo sin clave ni red; fallos simulados resueltos por el
respaldo (quickstart, escenarios 1, 2 y 6).

### Tests for User Story 2 ⚠️

- [X] T023 [P] [US2] Añadir a `tests/integration/agent/test_jev_flow.py` pruebas de extremo a extremo del grafo en modo demo: sin clave (`build_gate` devuelve `None`) las rutas de las 44 consultas coinciden con las de la línea base sin gatekeeper; con `FakeJevGate` configurado para fallar (timeout, 401, 402, 429, `refusal`, respuesta inválida) cada turno responde, decide `llm`/`demo` y registra `jev.status="failed"` con su motivo
- [X] T024 [P] [US2] Escribir `tests/contract/test_jev_contract.py`: `[jev]` de `config/agent.toml` carga y valida; `enabled` es `false` por defecto; `model` no termina en `latest`; `prompts/jev.md` tiene las cuatro secciones y las seis rutas y seis motivos exactos; `.env.example` contiene `TYPESAFE_API_KEY=` sin valor; ningún archivo versionado contiene un valor con forma de clave (`sk-` seguido de caracteres) junto a `TYPESAFE_API_KEY` (SC-008)

### Implementation for User Story 2

- [X] T025 [US2] Añadir `--check` al subcomando `jev` en `src/proyecto_modelos_lenguaje/agent/__main__.py` y una función `health_check(config)` en `src/proyecto_modelos_lenguaje/agent/jev.py` que consulta `GET {base_url}/v1/models` y devuelve `{ok, model, base_url, latency_ms, detail}`; código 0 si la versión fijada está disponible, 2 si falta la clave, no hay red o la versión no existe; nunca imprime la clave (FR-014, contrato §5)
- [X] T026 [US2] Registrar una sola vez al iniciar la API y el CLI el estado del gatekeeper («Jev desactivado: sin clave» / «desactivado en configuración» / «activo, modelo jev-1.14.0») en `src/proyecto_modelos_lenguaje/agent/jev.py` (`build_gate`), sin repetir el aviso por turno
- [X] T027 [P] [US2] Escribir `tests/integration/test_jev_real.py` con `@pytest.mark.network`: `health_check` real y una consulta real de cada ruta; se omite si no hay `TYPESAFE_API_KEY`
- [X] T028 [US2] Ejecutar `make check` sin clave ni red y los escenarios 1, 2 y 6 del quickstart; corregir cualquier diferencia de comportamiento frente a `main` — pytest, ruff, vitest (105/105) y build en verde; escenarios 1, 2 y 6 verificados (clave inválida ⇒ `decided_by=llm`, `jev.reason=http_401`).

**Checkpoint**: US1 + US2 listas para fusionar con el gatekeeper desactivado por defecto.

---

## Phase 5: User Story 3 — Señales de atención reforzadas (Priority: P2)

**Goal**: crisis como unión regex ∪ Jev, molestia que intensifica la emoción y motivo de fuera de alcance.

**Independent Test**: los 36 casos de atención y las 12 conversaciones con y sin gatekeeper, comparando las señales
con lo esperado (quickstart, escenario 7).

### Tests for User Story 3 ⚠️

- [X] T029 [P] [US3] Añadir a `tests/unit/test_jev.py` pruebas de `merge_signals`: regex = crisis y Jev = 0,01 → crisis; regex = no y Jev ≥ `crisis_threshold` → crisis; regex = no y Jev < umbral → no; molestia 2 con emoción neutral → `frustrated`; molestia 3 → `angry`; emoción negativa léxica más intensa se conserva; señal desactivada en `signals` → no altera nada; `GateOutcome` fallido → señales intactas
- [X] T030 [P] [US3] Añadir a `tests/integration/agent/test_jev_flow.py` una prueba que recorre los 3 casos con `"skill": "crisis"` de `tests/fixtures/care/care_cases.jsonl` con un `FakeJevGate` que siempre dice «no crisis» y verifica que **todos** siguen tratándose como crisis (Línea 106 y 123) (SC-004)

### Implementation for User Story 3

- [X] T031 [US3] Implementar `merge_signals(signals, outcome, config) -> CareSignals` en `src/proyecto_modelos_lenguaje/agent/jev.py` según research R6: `crisis = crisis_regex OR crisis_probability ≥ crisis_threshold`; molestia ≥ 2 con emoción neutral ⇒ `frustrated`, 3 ⇒ `angry`, sin rebajar una emoción ya detectada; guardar `jev_annoyance` y `jev_crisis_probability` en las señales para el registro
- [X] T032 [US3] Llamar a `merge_signals()` en `_route_node` de `src/proyecto_modelos_lenguaje/agent/graph.py` justo después de `gate.assess()` y antes de `route_message()`, de modo que `rule_decision()` vea la crisis fusionada; con `route == "out_of_scope"` y la señal `scope` activa, usar el motivo del gatekeeper solo si las reglas no fijaron uno
- [X] T033 [US3] Añadir a las baterías `agent care` y `agent converse` (`src/proyecto_modelos_lenguaje/agent/care_eval.py` y `src/proyecto_modelos_lenguaje/agent/converse_eval.py`) columnas con las señales del gatekeeper (crisis, molestia, motivo, decidió) cuando está activo, y ejecutar el escenario 7 del quickstart con la clave real — Hecho en `care_eval.py` (`decided_by` y `jev` por caso, que resume `agent jev --compare`); `converse_eval.py` no se modificó: la batería de conversación no mide rutas.

**Checkpoint**: señales reforzadas sin perder ninguna crisis.

---

## Phase 6: User Story 4 — Evidencia comparativa para la sustentación (Priority: P3)

**Goal**: informe con números que muestre si el gatekeeper aporta.

**Independent Test**: `agent jev --compare` genera `docs/evaluacion_jev.{md,json}` con ambas configuraciones y todas las
métricas, enlazado desde la evaluación y el informe del Módulo 2 (quickstart, escenario 8).

### Tests for User Story 4 ⚠️

- [X] T034 [P] [US4] Escribir en `tests/unit/test_jev_compare.py` pruebas offline de la comparación con `FakeJevGate` y un modelo guionado: el informe tiene las configuraciones `baseline` y `jev`, exactitud, llamadas LLM por consulta, latencia media y p95, porcentaje de decisiones del gatekeeper, costo total, crisis detectadas/esperadas y `meta` con `run_id`, fecha, modelo, umbrales y commit; sin clave el comando termina con código 2 y mensaje accionable

### Implementation for User Story 4

- [X] T035 [US4] Permitir un gatekeeper opcional en `evaluate_router()` de `src/proyecto_modelos_lenguaje/agent/evaluate.py` y sumar al `RouterReport` las decisiones de Jev, su latencia y costo (research R14)
- [X] T036 [US4] Añadir `--compare [--json]` al subcomando `jev` en `src/proyecto_modelos_lenguaje/agent/__main__.py`: ejecuta `evaluate_router` sin y con gatekeeper sobre `tests/fixtures/rag/module2_queries.jsonl`, las baterías `care` y `converse` con gatekeeper, e incorpora la validación de T014; escribe `docs/evaluacion_jev.json` y `docs/evaluacion_jev.md` (data-model `JevComparisonReport`) y una sección entre marcadores en `docs/evaluacion_modulo2.md`
- [X] T037 [US4] Ejecutar `uv run python -m proyecto_modelos_lenguaje.agent jev --compare` con la clave real y verificar SC-001 (exactitud sin caer más de 2 puntos), SC-002 (≥ 50 % sin LLM), SC-004 (0 crisis perdidas) y SC-007 (costo < 1 USD) — Resultado: SC-002 ✅ (73–77 % de llamadas evitadas), SC-004 ✅ (crisis 100 %), SC-007 ✅ (0,005 USD); **SC-001 ❌** (93,2 % frente a 97,7 %, dos ejecuciones con los mismos tres errores). No se ajustó nada con las 44 consultas (principio II); Jev queda desactivado por defecto.
- [X] T038 [US4] Ejecutar `MANUELITA_JEV_ENABLED=1 uv run python -m proyecto_modelos_lenguaje.agent evaluate --mode real --compare --skip-router --run-id variants-real-jev-<fecha>` y añadir a `docs/evaluacion_jev.md` el porcentaje de respuestas < 10 s y el p95 por variante frente a `variants-real-2026-11-14` (SC-003) — Con línea base del mismo día sin Jev (`variants-real-sinjev-2026-11-21`): agente 90,9 % → 97,7 % < 10 s, cadena 100 % → 97,7 %; SC-003 ✅ (≥ 95 % en ambas).

**Checkpoint**: evidencia lista para la sustentación.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: documentación, gobernanza y verificación final

- [X] T039 [P] Escribir `docs/decisions/0025-jev-gatekeeper.md`: contexto (ítem 2.3 de la rúbrica, SC-007), decisión (TypeSafe directo, cliente `httpx`, versión fija, una solicitud por turno, crisis como unión), alternativas (SDK, OpenRouter, Vercel, Cloudflare), consecuencias, privacidad (segundo proveedor en EE. UU.) y resultados de T014 y T037 — Renumerado a 0025: el 0022 ya era `0022-valeria-asistente.md` (spec 018).
- [X] T040 [P] Actualizar `CONSTITUTION.md` en el mismo PR: §3.5 (proveedor auxiliar Jev, versión fija, desactivado por defecto), §3.6 (`prompts/jev.md`), estado de la Fase 2 (gatekeeper System One) y la versión semántica y fecha de enmienda
- [X] T041 [P] Registrar `prompts/jev.md` (versión y hash) y el umbral elegido en `docs/prompt_log.md`
- [X] T042 [P] Añadir a `docs/data_card.md` el envío de mensajes enmascarados a TypeSafe (EE. UU.) cuando el gatekeeper está activo
- [X] T043 [P] Actualizar `docs/rubrica_modulo2.md` (ítem 2.3 y deseable «Gatekeeper System One (Jev)»), `docs/informe_modulo2.md` (sección del enrutador y limitaciones) y `docs/arquitectura.json` / diagrama del enrutador si muestra las etapas — Diagramas Archify sin cambios: muestran el flujo por defecto, que no cambia con Jev desactivado.
- [X] T044 [P] Actualizar `README.md`: cómo activar Jev (`TYPESAFE_API_KEY`, `[jev].enabled`, `agent jev --check`), resultados de `docs/evaluacion_jev.md`, la lista de pendientes («gatekeeper Jev» deja de estar pendiente) y la limitación de privacidad; actualizar los textos de límites de `src/proyecto_modelos_lenguaje/showcase.py`, `web/src/data/showcase.ts` y `web/src/components/LimitsNote.tsx` que dicen que falta el gatekeeper
- [X] T045 Ejecutar `make check` completo (ruff, pytest, vitest, build web) y todo el `quickstart.md`; confirmar que `git grep -n "sk-"` no muestra ninguna clave — Hecho el 2026-11-21: sin claves en archivos versionados.
- [ ] T046 (solo si T014 < 80 %) Escribir `docs/evaluacion_jev.md` con los resultados de la validación en español y la conclusión «evaluado y descartado» — **No aplica**: T014 dio 24/24 (100 %).
- [ ] T047 (solo si T014 < 80 %) Registrar en `docs/decisions/0025-jev-gatekeeper.md` la decisión de no integrar, con las cifras — **No aplica**: T014 dio 24/24 (100 %).
- [ ] T048 (solo si T014 < 80 %) Actualizar `docs/rubrica_modulo2.md` y `README.md` con el gatekeeper como evaluado y descartado, y dejar `enabled = false` — **No aplica**: T014 dio 24/24 (100 %).

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup; **T014 es la puerta** de todo lo demás.
- **US1 (Phase 3)** y **US2 (Phase 4)**: dependen de la Phase 2. US2 comparte archivos con US1 (`graph.py`,
  `__main__.py`, `jev.py`), así que se hacen en ese orden.
- **US3 (Phase 5)**: depende de T018 (el gatekeeper ya se consulta en el nodo `route`).
- **US4 (Phase 6)**: depende de US1 y US3 para medir todo; con solo US1 puede medir el enrutador.
- **Polish (Phase 7)**: al final. T046–T048 sustituyen a las fases 3–6 si la puerta falla.

### Within Each User Story

- Pruebas primero (deben fallar), luego implementación.
- `router.py` antes de `graph.py`; `graph.py` antes de las baterías y la comparación.

### Parallel Opportunities

- Setup: T002–T005 en paralelo tras T001.
- Foundational: T007 y T008 en paralelo con T006; T012 en paralelo con T011 cuando T010 exista.
- US1: T015, T016 y T021 en paralelo.
- US2: T023, T024 y T027 en paralelo.
- US3: T029 y T030 en paralelo.
- Polish: T039–T044 en paralelo.

---

## Parallel Example: User Story 1

```bash
Task: "T015 Pruebas del router con gatekeeper en tests/unit/test_router_jev.py"
Task: "T016 Pruebas del nodo route con FakeJevGate en tests/integration/agent/test_jev_flow.py"
Task: "T021 Etiqueta «Jev» en web/src/lib/types.ts y web/src/components/ChatView.tsx"
```

---

## Implementation Strategy

### MVP (US1 + US2)

1. Phase 1 y Phase 2, con la puerta T014 en español.
2. Phase 3 (US1) y Phase 4 (US2).
3. **Validar**: `make check` sin clave y quickstart 1–6. Se puede abrir el PR aquí con el gatekeeper desactivado por
   defecto.

### Entrega incremental

1. MVP → PR 1 (gatekeeper de ruta y respaldo).
2. US3 → PR 2 (señales de atención).
3. US4 + Polish → PR 3 (evidencia, ADR, constitución y documentos). ADR y constitución pueden ir antes si la revisión
   lo pide.

### Notes

- Commits atómicos por tarea o grupo lógico, en Conventional Commits y en español.
- La clave solo vive en `.env`; ningún commit, PR ni registro la incluye.
- Las pruebas con red llevan `@pytest.mark.network` y no corren en CI.
