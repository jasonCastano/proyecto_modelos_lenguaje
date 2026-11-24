# Tasks: Valer-IA como plataforma de agentes de Manuelita (idea 7) con planificación industrial

**Input**: Design documents from `specs/025-agentes-manuelita-idea7/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md),
[contracts/](contracts/), [quickstart.md](quickstart.md)

**Autor**: Roberto José Guerrero | **Fecha**: 2026-11-24

**Tests**: SÍ. La spec los exige (SC-007: pruebas sin red del simulador, el optimizador, las herramientas y los
perfiles), y el proyecto trabaja con pruebas primero, como en la spec 024. En cada historia, las pruebas se escriben
antes y deben fallar.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia de la spec. US1 = planificación, US2 = perfiles, US3 = sustentación y US4 = palma (P3).

## Path Conventions

- Paquete: `src/proyecto_modelos_lenguaje/` (abreviado `pkg/` en estas tareas).
- Pruebas: `tests/`; web: `web/src/`; configuración: `config/`; prompts: `prompts/`.
- Datos sintéticos: `data/synthetic/planificacion/v1/`.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias, configuración y esqueletos que todo lo demás usa.

- [X] T001 Declarar `scipy>=1.14` en `[project].dependencies` de `pyproject.toml` (comentario `# spec 025: programación lineal (R5)`) y correr `uv lock` (debe quedar en 1.18.1, sin descargas nuevas); verificar `uv sync --frozen`
- [X] T002 [P] Crear `config/profiles.toml` con `[profiles] enabled = true` y los cinco perfiles de `contracts/profiles.md`:
  - campos `key`, `label` (3–40 caracteres), `tools`, `requires_authorization` (solo `planificador = true`) y `triggers`;
  - `visitante` lista exactamente las 20 herramientas de la spec 024.
- [X] T003 [P] Crear `prompts/profiles.md` con `<!-- prompt_version: 1.0 -->` y una sección `## <key>` por perfil con el foco:
  - **cliente**: nunca precios, cotización con un asesor;
  - **proveedor**: solo documentos públicos, no reemplaza la asistencia de campo;
  - **colaborador**: PTEE, línea ética y SST;
  - **planificador**: la secuencia estado → compromisos → optimizar → comparar, la etiqueta «Datos sintéticos» y «el equipo de planta decide».
- [X] T004 [P] Añadir a `config/agent.toml` la tabla `[agent.route_limits.planning]` con `tool_call_limit = 5` y `model_call_limit = 6` (R4)
- [X] T005 [P] Documentar vacías en `.env.example` `VALERIA_PLANNERS=`, `# MANUELITA_PLANNER_OPEN=1` y `# MANUELITA_PLANNER_WEB=1`, con un comentario de la spec 025 (R14)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: tipos compartidos, catálogo y núcleo de perfiles que necesitan US1 y US2.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

### Tests (escribir primero; deben fallar)

- [X] T006 [P] Pruebas de `pkg/agent/profiles.py` en `tests/unit/agent/test_profiles.py`:
  - carga de los cinco perfiles;
  - error si una herramienta no existe en el catálogo o falta una sección del prompt;
  - `visitante` coincide con el catálogo de 20;
  - `enabled = false` deja solo `visitante`;
  - `is_authorized` con `VALERIA_PLANNERS`, `MANUELITA_PLANNER_OPEN` y `MANUELITA_PLANNER_WEB` (canal `web`);
  - alias `b2b` → `cliente`, sin tildes ni mayúsculas.
- [X] T007 [P] Ampliar `tests/unit/agent/test_catalog.py`:
  - `ROUTES` incluye `planning`;
  - `ToolSpec.mcp` es falso si `mcp_allowed=False`;
  - `build_catalog_tools(..., profile=...)` ofrece la intersección `specs_for_route(route) ∩ profile.tools` y las escrituras comunes;
  - `PLAN_BY_ROUTE["planning"]` existe.

### Implementation

- [X] T008 Añadir `"planning"` al `Route` de `pkg/agent/models.py` y de `pkg/api_models.py`, y al tipo de ruta de `web/src/lib/types.ts` (incluido el texto en `DECIDED_LABEL` y los textos de ruta de `web/src/components/ChatView.tsx` si los hay)
- [X] T009 En `pkg/agent/catalog.py`:
  - añadir `planning` a `ROUTES`;
  - añadir el campo `mcp_allowed: bool = True` a `ToolSpec` y la propiedad `mcp = kind == "read" and mcp_allowed`, incluida en `to_dict`;
  - añadir el plan de la ruta en `PLAN_BY_ROUTE["planning"]`: «consultar estado de planta y compromisos», «optimizar el plan y simular la alternativa», «comparar margen, energía y cumplimiento», «explicar supuestos; datos sintéticos; el equipo decide».
- [X] T010 Implementar `pkg/agent/profiles.py` (R1, R14):
  - dataclass `Profile` y `load_profiles()`, que valida contra `catalog()` y `prompts/profiles.md`;
  - `profile_focus(key)`, `resolve_alias(text)`, `is_authorized(user_id, channel)` y `profiles_enabled()`.
- [X] T011 Añadir el parámetro `profile: str | None` a `build_catalog_tools` y `specs_for_route` en `pkg/agent/catalog.py`:
  - filtra la lectura por `Profile.tools`;
  - ofrece `save_production_proposal` solo en `planificador`;
  - las demás escrituras en todos los perfiles.
- [X] T012 En `pkg/agent/graph.py`:
  - añadir `profile: str` (por defecto `"visitante"`) y `last_plan: dict | None` a `ChatState`;
  - pasar `profile` a `build_catalog_tools`;
  - añadir `profile_focus` al system prompt dinámico (`system_with_preferences` + `personalized_prompt`);
  - aplicar `route_limits` por ruta a `ToolCallLimitMiddleware` y `ModelCallLimitMiddleware`, leídos en `pkg/agent/config.py`.
- [X] T013 [P] Añadir `profile` a `Turn` (`pkg/agent/models.py`), a `turn_record` (`pkg/agent/observability.py`) y a `TurnModel` (`pkg/api_models.py`); añadir `profile?: string` a `ChatTurn` en `web/src/lib/types.ts`
- [X] T014 [P] Registrar `prompts/profiles.md` v1.0 en `docs/prompt_log.md` (nueva §3.x, spec 025)

**Checkpoint**: `uv run pytest tests/unit/agent/test_profiles.py tests/unit/agent/test_catalog.py` en verde; la batería de herramientas en modo demo con el perfil `visitante` da el mismo resultado que antes.

---

## Phase 3: User Story 1 - Un planificador pide un programa de producción y recibe una recomendación explicada (Priority: P1) 🎯 MVP

**Goal**: perfil planificador autorizado → ruta `planning` → estado, compromisos, optimizador y comparación → plan
con supuestos, etiqueta sintética y decisión humana → guardar con «SÍ».

**Independent Test**: quickstart §1–§3 y §4 paso 3–4. Con el perfil planificador y los datos v1, la solicitud de
−15 % de caña produce un plan óptimo sin violaciones, con la traza completa. −35 % produce `infeasible_relaxed` con el
faltante. «SÍ» escribe en `proposals.jsonl` y «NO» no escribe.

### Tests for User Story 1 (escribir primero; deben fallar)

- [X] T015 [P] [US1] Pruebas del generador en `tests/unit/agent/test_planning_data.py`:
  - `generate_planning_data.py --check` es idempotente con `--seed 2026`;
  - cada archivo tiene `synthetic: true`, `seed` y `version`;
  - `cane_quality` está en [9, 16], `capacity_factor ∈ [0, 1]` y las contrapartes son genéricas, sin nombres reales;
  - la semana base es factible con ≥ 10 % de holgura y −15 % es factible con al menos una restricción activa (`contracts/planning-tools.md` § Calibración).
- [X] T016 [P] [US1] Pruebas del núcleo en `tests/unit/agent/test_planning.py`:
  - el simulador calcula los balances según `data-model.md` §4 y reporta violaciones sin lanzar error;
  - el LP de −15 % da `status: optimal`, `binding` y la `sensitivity` con su unidad;
  - −35 % da `infeasible_relaxed` con `shortfalls`, sin relajar capacidades;
  - `plan_id` cumple `^p-[0-9a-f]{8}$` y es estable para el mismo escenario;
  - `plan_card` contiene «Datos sintéticos» y «el equipo de planta decide»;
  - `check_answer` acepta números presentes en las salidas (con normalización de miles y coma decimal) y rechaza números ausentes o la falta de etiqueta.
- [X] T017 [P] [US1] Pruebas de la referencia en `tests/unit/agent/test_planning_reference.py`: la malla de 2001 × 2001 con resolución en forma cerrada de `b`, `v` y `g` coincide con el LP dentro del paso de malla en 3 escenarios; detecta la infactibilidad
- [X] T018 [P] [US1] Pruebas de herramientas en `tests/unit/agent/test_tools_planning.py`:
  - números 21–25, ruta `planning`, `extra="forbid"`;
  - rangos de `data-model.md` §3: `cane_delta_pct` en [-50, 50], `cane_quality` en [9, 16], `sugar_share` en [0, 1], `steam_limit ≥ 0`;
  - error controlado fuera de rango;
  - salidas con el prefijo `[Datos sintéticos de demostración · v1]`;
  - `search_operating_procedures` devuelve `[S#]` neutralizados;
  - 24 y 25 con `mcp_allowed=False`.
- [X] T019 [P] [US1] Pruebas de `save_production_proposal` en `tests/unit/agent/test_save_proposal.py`:
  - patrón `plan_id` `^p-[0-9a-f]{8}$` y `note` de ≤ 200 caracteres;
  - escribe desde `last_plan`, no desde los argumentos;
  - `plan_id` distinto → mensaje «Esa propuesta ya no está en esta conversación; vuelve a calcularla»;
  - número 26, tipo write, sin MCP.
- [X] T020 [P] [US1] Pruebas de rutas en `tests/unit/agent/test_router_planning.py`:
  - las señales de planificación con perfil `planificador` dan la ruta `planning` (`decided_by="rules"`);
  - con otro perfil, la respuesta fija de función restringida, sin herramientas;
  - el clasificador LLM y Jev nunca devuelven `planning`.
- [X] T021 [US1] Prueba de integración en `tests/integration/agent/test_planning_flow.py` con modelo guionizado (`build_scripted_model`):
  - planificador autorizado → `plan_steps` con estado, compromisos y optimización;
  - respuesta validada; una respuesta con un número inventado se reemplaza por el `plan_card` (`planning_guard: replaced`);
  - «guarda esta propuesta» → interrupción → «SÍ» escribe la línea en `$MANUELITA_STATE_DIR/planning/proposals.jsonl`; «NO» no escribe;
  - usuario no autorizado → rechazo.

### Implementation for User Story 1

- [X] T022 [US1] Implementar `scripts/generate_planning_data.py` (`--seed`, `--version`, `--check`; R10) y generar `data/synthetic/planificacion/v1/`:
  - `plant_cana.json` con los campos de `data-model.md` §2 y `sources` con IS 2023-2024, p. 57 y 124;
  - `state.json` (`week` ISO), `commitments.json` (`priority` de 1 a 3) y 10–12 `procedures/*.md` con frontmatter `id`, `title`, `synthetic: true`;
  - `DATA_CARD.md`;
  - calibración según `contracts/planning-tools.md`.
- [X] T023 [US1] Implementar `pkg/agent/planning.py`:
  - `load_plant(version)`, `Scenario` (Pydantic, `extra="forbid"`) y `simulate(scenario)` → `SimulationResult`;
  - `optimize(scenario)` con `scipy.optimize.linprog(method="highs")` y el modelo de `data-model.md` §4, con `binding` (compromisos activos primero; luego dual × lado derecho; holgura ≤ 1e-6) y `sensitivity`;
  - LP elástico con penalización `10³ · precio unitario · prioridad⁻¹` cuando el estado es 2;
  - alternativas `margin`, `power` y la mezcla actual (simulada);
  - `plan_card` y `plan_id`;
  - `check_answer(text, tool_outputs)` (R12);
  - límite de 5 s: el solver no debe superarlo.
- [X] T024 [P] [US1] Implementar `pkg/agent/planning_reference.py` (R9): búsqueda vectorizada en NumPy sobre `x_s`, `x_e`, con `b`, `v` y `g` en forma cerrada; no importa ni `scipy` ni `planning.optimize`
- [X] T025 [US1] Implementar `scripts/generate_planning_battery.py --seed 2026` → `tests/fixtures/agent/planning_scenarios.jsonl`: 12 escenarios (10 factibles y 2 infactibles: −35 % de caña, y vapor limitado más −25 %) con `reference_margin`, `reference_mix` y `grid_step`
- [X] T026 [US1] Implementar `pkg/agent/tools_planning.py` con `SPECS` 21–25 según `contracts/planning-tools.md`:
  - `get_plant_state`, `get_commitments`, `search_operating_procedures` (BM25 en memoria con `retrieval.tokenize` + `guard.neutralize`, citas `S#`), `simulate_production_scenario` y `optimize_production_plan`;
  - añadir `"tools_planning"` al bucle de `_new_read_specs` en `pkg/agent/catalog.py`.
- [X] T027 [US1] En `pkg/agent/graph.py`, aceptar evidencia `S#` con `kind="synthetic"` en `collect_evidence` y `validate_answer`; registrar las salidas de `ToolTrace` de las herramientas de planificación
- [X] T028 [US1] Añadir `save_production_proposal` en `pkg/agent/actions.py` (R13):
  - `WRITE_TOOLS`, `TOOL_DESCRIPTIONS`, `SaveProposalArgs` en `ARG_SCHEMAS`;
  - en `execute_action`, el plan se lee del `last_plan` del hilo y se añade una `ProductionProposal` a `$MANUELITA_STATE_DIR/planning/proposals.jsonl` (`plan_id`, `user_id`, `created_at`, `note`, `plan` sin `plan_card`, `approved_by: "user"`);
  - `WRITE_NUMBERS["save_production_proposal"] = 26` y su fuente en `pkg/agent/catalog.py`;
  - resumen del plan en la interrupción de aprobación.
- [X] T029 [US1] Detección de la ruta `planning` en `pkg/agent/router.py` (R3):
  - patrón de señales (programa o plan de producción, escenario, menos caña, vapor, contratos de azúcar o etanol, energía comprometida) en `tool_cue_decision`, condicionado a `profile == "planificador"` y a la autorización;
  - con otro perfil o sin autorización, una decisión `direct` con el motivo «planificación restringida» y una respuesta fija en `pkg/agent/graph.py`.
- [X] T030 [US1] En `pkg/agent/graph.py`:
  - tras el nodo agente en la ruta `planning`, guardar `last_plan` (último `PlanResult` del turno);
  - aplicar `planning.check_answer`, reemplazar la respuesta por el `plan_card` si falla y marcar `planning_guard` en la traza.
- [X] T031 [US1] Añadir a `prompts/agent.md` (subir versión y registrar en `docs/prompt_log.md`) las reglas de la ruta `planning`: secuencia de herramientas, no inventar cifras, mostrar alternativa y supuestos, etiqueta y frase de decisión humana
- [X] T032 [US1] Añadir el subcomando `planning --scenario <json> [--json]` en `pkg/agent/__main__.py`: imprime el `plan_card` o el JSON, sin LLM
- [X] T033 [US1] Respetar `spec.mcp` (que ahora incluye `mcp_allowed`) en `exposed_specs` de `pkg/mcp_server.py`, y ampliar `tests/unit/test_mcp_server.py`: expone 21–23 y no expone 24–26

**Checkpoint (corte del miércoles 25)**: T015–T021 en verde; `agent planning --scenario '{"cane_delta_pct": -15}'` funciona. Si no, la planificación queda solo en la web y la demo de WhatsApp usa la secuencia de la spec 024.

---

## Phase 4: User Story 2 - Cada público recibe un agente con su propio foco y herramientas (Priority: P1)

**Goal**: `/perfil` y selector web, autopresentación que propone el perfil, perfil recordado con «SÍ», traza con perfil
y batería de perfiles.

**Independent Test**: quickstart §4 pasos 1–2 y §5 (`/perfil`). Batería de perfiles en modo demo con perfil correcto
≥ 90 % y subconjunto 100 %. El perfil persiste tras reiniciar el backend (preferencia `audience`).

### Tests for User Story 2 (escribir primero; deben fallar)

- [X] T034 [P] [US2] Pruebas de memoria en `tests/unit/agent/test_memory.py`: `audience` admitida en `PREFERENCE_KEYS` y `SavePreferenceArgs`, con valores solo de claves de perfil válidas; `/olvidar` la borra
- [X] T035 [P] [US2] Pruebas del canal en `tests/unit/channels/test_bridge_profile.py`:
  - `/perfil` lista cinco perfiles y marca el activo;
  - `/perfil proveedor` lo activa en el hilo sin escribir en el Store y responde el texto del contrato;
  - `/perfil planificador` sin autorización se niega y registra `planner_denied` sin número ni texto en `channels.jsonl`;
  - `/ayuda` incluye `/perfil`.
- [X] T036 [P] [US2] Pruebas de API en `tests/api/test_profiles_api.py`:
  - `POST /api/chat` con `profile` válido;
  - `invalid_profile` → 400;
  - `planificador` no autorizado → 403 `planner_not_authorized`;
  - `GET /api/profiles` devuelve `key`, `label`, `requires_authorization` y `authorized`;
  - `TurnModel.profile`.
- [X] T037 [P] [US2] Pruebas de integración en `tests/integration/agent/test_profile_flow.py` (modelo guionizado):
  - «soy proveedor de caña…» → propuesta de perfil (`save_preference audience`) → «SÍ» → hilo nuevo con el perfil cargado;
  - el perfil cliente ante «cotización» propone `request_human_contact` y la respuesta no contiene cifras de precio.
- [X] T038 [P] [US2] Prueba vitest en `web/src/test/ChatView.test.tsx`: selector de perfil (opciones de `GET /api/profiles`, el planificador deshabilitado si `authorized=false`), chip del perfil activo y `profile` en la traza del turno

### Implementation for User Story 2

- [X] T039 [US2] En `pkg/agent/memory.py` y `pkg/agent/actions.py`: añadir `audience` a `PREFERENCE_KEYS`, `PREFERENCE_LABELS` («perfil de atención») y `PreferenceKey`, validando el valor con `profiles.load_profiles()`
- [X] T040 [US2] En `pkg/agent/graph.py` y `pkg/agent/service.py`:
  - resolver el perfil del turno por prioridad: parámetro explícito, luego `ChatState.profile`, luego la preferencia `audience`, luego `visitante`;
  - si cae en `planificador` sin autorización, usar `visitante`;
  - aceptar `profile` en `ChatService.send(...)`.
- [X] T041 [US2] Autopresentación en `pkg/agent/graph.py`: si los `triggers` de un perfil coinciden y el perfil activo es otro, el turno responde la pregunta y añade la propuesta de recordarlo con `save_preference(key="audience")` y «SÍ/NO»
- [X] T042 [US2] Implementar `/perfil` en `pkg/channels/bridge.py` según `contracts/profiles.md` (lista, activar, alias y rechazo con `planner_denied`), la línea de `/ayuda` y `Perfil: <label>` en `/traza`; añadir el bloque «Fuentes sintéticas (demostración):» para `S#` en `pkg/channels/format.py`
- [X] T043 [US2] En `pkg/api.py` y `pkg/api_models.py`: `ChatRequest.profile` (Literal de los cinco), errores 400 `invalid_profile` y 403 `planner_not_authorized` (canal `web` para `is_authorized`), y `GET /api/profiles`
- [X] T044 [US2] En la web (`web/src/lib/chat.ts`, `web/src/components/ChatView.tsx`): cargar `GET /api/profiles`, añadir el selector y el chip en la vista técnica, enviar `profile` en el chat y mostrar `turn.profile` en la traza
- [X] T045 [US2] Crear `tests/fixtures/agent/profile_routing.jsonl`: 20 consultas, al menos 4 por perfil, con `expected_profile` y `expected_tools_subset`, fijadas antes de evaluar (principio V)
- [X] T046 [US2] Implementar `profiles-eval --mode demo|real [--write-docs]` en `pkg/agent/planning_eval.py` y `pkg/agent/__main__.py`: mide perfil detectado o aplicado y subconjunto ofrecido (SC-003) y escribe `docs/evaluacion_perfiles.{md,json}`

**Checkpoint**: T034–T038 en verde; `profiles-eval --mode demo` ≥ 90 % y 100 %.

---

## Phase 5: User Story 3 - El equipo demuestra la plataforma en la sustentación sin perder lo ya evaluado (Priority: P1)

**Goal**: canal, workspace, evaluaciones reales y guion listos para el sábado, con respaldo.

**Independent Test**: ensayo cronometrado de 15 minutos el viernes 27 (SC-006), con un teléfono ajeno; la secuencia
de respaldo de la spec 024 también funciona.

### Tests for User Story 3 (escribir primero; deben fallar)

- [X] T047 [P] [US3] Ampliar `tests/unit/agent/test_channel_eval.py` y la batería de blindaje del canal con los casos de FR-019: forzar el perfil planificador sin autorización y pedir que afirme que los datos sintéticos son reales; el resultado esperado es el rechazo, sin fuga
- [X] T048 [P] [US3] Ampliar `tests/unit/test_workspace_files.py`: `openclaw/workspace/AGENTS.md` contiene las líneas rojas de la plataforma y el límite «hasta cinco herramientas en planificación»
- [X] T049 [P] [US3] Prueba de `pml channels simulate --profile planificador` en `tests/unit/channels/test_channels_cli.py` con el backend de prueba

### Implementation for User Story 3

- [X] T050 [US3] Actualizar `openclaw/workspace/AGENTS.md` (FR-018):
  - líneas rojas: nada de precios ni condiciones comerciales; nada de datos internos reales; la planificación solo para autorizados y marcada como sintética; el agente recomienda y no ejecuta;
  - «En modo degradado no se planifica»;
  - límite de cinco herramientas en planificación;
  - sincronizar con `pml ops workspace sync`.
- [X] T051 [US3] Añadir `--profile` a `pml channels simulate` en `pkg/channels/__main__.py`
- [X] T052 [US3] Implementar `planning-eval --mode direct|real [--write-docs]` en `pkg/agent/planning_eval.py` y `pkg/agent/__main__.py`:
  - `direct`: SC-001 contra `planning_scenarios.jsonl`;
  - `real`: SC-002 (secuencia y etiqueta) y SC-004 (p95 ≤ 20 s) con DeepSeek;
  - escribe `docs/evaluacion_planificacion.{md,json}`.
- [X] T053 [US3] Añadir 6 casos del planificador al final de `tests/fixtures/agent/tool_routing.jsonl` (`t54`–`t59`, con un campo `profile: "planificador"`); el resumen de `evaluate --tools` en `pkg/agent/cli_m3.py` los reporta aparte de la línea base de 53 (R17)
- [ ] T054 [US3] Corridas reales en el PC servidor, con informes escritos (sin números de teléfono):
  - `planning-eval --mode real --write-docs`;
  - `profiles-eval --mode real --write-docs`;
  - `evaluate --tools --mode real`: SC-005, ≥ 88,4 % y 0 búsquedas en triviales;
  - `agent shield --channel`.
- [ ] T055 [US3] Verificación manual por WhatsApp (quickstart §5–§6): `/perfil` y la solicitud de planificación desde un teléfono autorizado, el rechazo desde uno no autorizado y el modo degradado sin planificación; registrar en § Notas de este archivo, sin números
- [X] T056 [US3] Actualizar `docs/rubrica_modulo3.md` §7.1 con el estado real (✅/🟡/❌) y la evidencia de cada requisito; ajustar la secuencia de la demo de §7.2 con las frases que funcionaron en las corridas
- [ ] T057 [US3] Ensayo cronometrado de 15 minutos el viernes 27 con un teléfono ajeno (SC-006), probando también la secuencia de respaldo de §2; registrar los tiempos en § Notas

**Checkpoint**: SC-002 a SC-006 cumplidos o documentados con su cifra honesta.

---

## Phase 6: User Story 4 - El agente de planificación también cubre la planta de palma (Priority: P3)

**Goal**: el mismo flujo con `plant_id="palma"`. **Solo si las fases 3 a 5 están en verde el jueves 26 a mediodía**
(R18).

**Independent Test**: quickstart §2 con `{"plant_id": "palma", …}`; plan óptimo y caso con caída de la demanda de
biodiésel.

- [ ] T058 [P] [US4] Pruebas de la planta de palma en `tests/unit/agent/test_planning_palma.py`: balance de aceite crudo → refinado, biodiésel y palmiste; óptimo frente a la referencia; caída de la demanda de biodiésel
- [ ] T059 [US4] Añadir `plant_palma.json` al generador `scripts/generate_planning_data.py` y su modelo lineal en `pkg/agent/planning.py`; ampliar `plant_id` a `"cana" | "palma"` en los esquemas de `pkg/agent/tools_planning.py`
- [X] T060 [US4] Si no se hace a tiempo: dejar `plant_id` solo en `"cana"` y registrar la palma como pendiente en `specs/025-agentes-manuelita-idea7/spec.md` (Assumptions) y en `docs/rubrica_modulo3.md` §7.1

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T061 [P] Regenerar `docs/herramientas.md` desde el catálogo (26 herramientas) y actualizar `GET /api/tools` en las pruebas que cuentan 20 (`tests/unit/agent/test_catalog.py`, `tests/api/`)
- [X] T062 [P] Actualizar `README.md` con estos cambios:
  - badge de pruebas;
  - estado de la spec 025;
  - uso de `/perfil` y de `agent planning`;
  - enlaces a las evaluaciones nuevas.
- [X] T063 [P] Añadir los datos sintéticos de planificación a `docs/data_card.md`: limitación y changelog que remiten a `data/synthetic/planificacion/v1/DATA_CARD.md`
- [ ] T064 [P] Actualizar los diagramas Archify:
  - `docs/arquitectura.json` y `docs/diagramas/herramientas-router.json`: componente «Planificación (simulador + LP, datos sintéticos)», ruta `planning` y perfiles;
  - regenerar con `finalize` y `visual-check` (`--require-provenance`) y copiar los recibos y capturas a `docs/`.
- [X] T065 Actualizar el estado de los ítems de la spec 025 en `docs/rubrica_modulo3.md` §1 donde cambie la evidencia (1.1: 26 herramientas; 1.2: ruta `planning`), y la sección English version con el pitch de §7.2
- [X] T066 `make check` en verde (Ruff, pytest, vitest y build) y `uv run pre-commit run --all-files`; marcar las tareas `[X]` en este archivo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: sin dependencias.
- **Foundational (Phase 2)**: depende de Setup y bloquea todas las historias.
- **US1 (Phase 3)**: depende de Foundational. Es el MVP y la demo estrella.
- **US2 (Phase 4)**: depende de Foundational y puede ir en paralelo con US1, salvo T040 y T041, que tocan `graph.py` después de T030.
- **US3 (Phase 5)**: depende de US1 y US2 (evalúa y demuestra ambas).
- **US4 (Phase 6)**: opcional; depende de US1.
- **Polish (Phase 7)**: depende de las historias que se entreguen.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- En US1: datos (T022) → núcleo (T023, T024) → batería (T025) → herramientas (T026) → evidencia, acción y ruta (T027–T029) → grafo (T030) → prompt y CLI (T031–T033).
- `graph.py` se toca en T012, T027, T030, T040 y T041, en ese orden y sin paralelo.

### Parallel Opportunities

- Setup: T002, T003, T004 y T005.
- Foundational: T006 y T007 (pruebas), y T013 y T014.
- US1: T015–T020 (pruebas en archivos distintos) y T024 junto con T023.
- US2: T034–T038 (pruebas); T042 (canal), T043 (API) y T044 (web) tocan archivos distintos.
- US3: T047–T049.
- Polish: T061–T064.

## Parallel Example: User Story 1

```text
# Pruebas de US1 a la vez (archivos distintos):
T015 tests/unit/agent/test_planning_data.py
T016 tests/unit/agent/test_planning.py
T017 tests/unit/agent/test_planning_reference.py
T018 tests/unit/agent/test_tools_planning.py
T019 tests/unit/agent/test_save_proposal.py
T020 tests/unit/agent/test_router_planning.py

# Núcleo y referencia a la vez (no comparten código, R9):
T023 src/proyecto_modelos_lenguaje/agent/planning.py
T024 src/proyecto_modelos_lenguaje/agent/planning_reference.py
```

## Parallel Example: User Story 2

```text
T042 src/proyecto_modelos_lenguaje/channels/bridge.py (+ format.py)
T043 src/proyecto_modelos_lenguaje/api.py (+ api_models.py)
T044 web/src/components/ChatView.tsx (+ lib/chat.ts)
```

## Implementation Strategy

### MVP First (User Story 1)

1. Fases 1 y 2 (martes 24 por la noche o miércoles temprano).
2. Fase 3, US1, el miércoles 25. **Corte por la noche**: validar `planning-eval --mode direct` y el flujo con `/perfil planificador` en la web.
3. Si el corte falla, se activa el respaldo: `[profiles] enabled = false` para WhatsApp, y la planificación se muestra solo en la web.

### Incremental Delivery

1. US1, la planificación: el diferenciador del pitch.
2. US2, los perfiles: la plataforma de la idea 7 (jueves 26 en la mañana).
3. US3, las evaluaciones reales, el canal y el ensayo (jueves en la tarde y viernes).
4. US4, la palma, solo si sobra tiempo.
5. Polish: documentación y `make check` (viernes 27).

### Reparto sugerido (bus factor 2)

- **Roberto**: US1 (núcleo, herramientas, ruta), US2 (perfiles y memoria) y el pitch.
- **Jason**: US3 (canal, workspace, evaluaciones en el PC servidor y blindaje) y Archify.

---

## Notes

- [P] = archivos distintos y sin dependencias pendientes.
- Nada de datos reales de Manuelita en `data/synthetic/`. Las contrapartes son genéricas.
- Cada tarea que cambia un prompt sube la versión y registra la entrada en `docs/prompt_log.md`.
- Commits pequeños por grupo lógico, en Conventional Commits y a nombre de los integrantes.
- Resultados al 2026-11-24 (corridas locales con DeepSeek, sin teléfonos):
  - `planning-eval --mode direct`: 10/10 ≥ 99 % del óptimo de referencia, 0 violaciones, 2/2 sin solución.
  - `planning-eval --mode real`: ruta `planning` 12/12, secuencia 12/12, etiqueta y frase 12/12, p95 10,8 s.
  - `profiles-eval --mode real`: perfil 19/20 (r13 lo toma la detección de perfil personal de la spec 014),
    herramientas dentro del perfil 20/20.
  - `evaluate --tools --mode real`: línea base 86,0 % y 90,7 % en dos corridas (publicado 88,4 %), 0 búsquedas
    en triviales; planificador 6/6. No se reescribió `docs/evaluacion_herramientas.md`.
- Pendiente: T054 en el PC servidor (incluye `agent shield --channel` con d06–d07), T055 por WhatsApp, T057
  ensayo, T064 Archify (requiere el commit fijado) y la palma (T058–T059, P3).
