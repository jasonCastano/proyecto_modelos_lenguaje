# Implementation Plan: Valer-IA como plataforma de agentes de Manuelita (idea 7) con planificación industrial

**Branch**: `025-agentes-manuelita-idea7` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/025-agentes-manuelita-idea7/spec.md`

**Autor**: Roberto José Guerrero

## Summary

Valer-IA pasa de asistente para visitantes a **plataforma de agentes por perfil**: visitante, cliente B2B, proveedor,
colaborador y planificador. Se conservan el agente, el router (reglas → Jev → LLM), la memoria, el blindaje, el
canal de WhatsApp por OpenClaw y el catálogo único.

- **Perfiles:** cada perfil es una lista blanca del catálogo más una sección de foco en el prompt. El perfil vive en
  el hilo (`/perfil`) y se recuerda como preferencia `audience`, solo con aprobación.
- **Planificación industrial (idea 7.4):**
  - una ruta nueva, `planning`, que deciden solo las reglas y solo para el perfil planificador autorizado;
  - 5 herramientas de lectura (estado, compromisos, procedimientos `[S#]`, simulador y optimizador) y 1 de escritura
    con «SÍ» (guardar la propuesta);
  - un modelo lineal semanal de la planta de caña resuelto con `scipy.optimize.linprog` (HiGHS), con duales para la
    sensibilidad y un LP elástico para los casos infactibles;
  - todo sobre datos sintéticos generados con semilla.

  El LLM coordina y explica. Un validador garantiza que cada cifra sale de las herramientas; si no, responde con el
  `plan_card` renderizado en código. El optimizador se valida contra un óptimo de referencia independiente
  (búsqueda por malla).

## Technical Context

**Language/Version**: Python ≥ 3.14 (uv); TypeScript y React 19 en `web/`; TypeScript del plugin sin cambios.

**Primary Dependencies**:

- LangChain y LangGraph: `create_agent`, `HumanInTheLoopMiddleware`;
- FastAPI;
- Qdrant, sin cambios;
- `scipy>=1.14`: hoy transitiva (1.18.1 en `uv.lock`), pasa a explícita (R5);
- NumPy, para el óptimo de referencia (R9);
- `mcp` (FastMCP).

**Storage**:

- `data/synthetic/planificacion/v1/` (versionado, unos 50 KB, sin LFS);
- `$MANUELITA_STATE_DIR/planning/proposals.jsonl`;
- `SqliteStore`: preferencia `audience`;
- `SqliteSaver`: `ChatState.profile` y `last_plan`.

**Testing**: pytest sin red, con dobles del modelo (`build_fake_model` y `build_scripted_model`); vitest para el
selector web; `node --test` del plugin, sin cambios.

**Target Platform**: el PC servidor Windows 11 de la spec 024, con FastAPI, el gateway OpenClaw y WhatsApp.

**Project Type**: servicio web, CLI y agente con canal de mensajería (monorepo existente).

**Performance Goals**:

- optimización ≤ 1 s;
- planificación por WhatsApp con p95 ≤ 20 s (SC-004);
- los demás perfiles, con el objetivo conversacional de la spec 024.

**Constraints**:

- sin datos reales de Manuelita;
- cifras solo desde código;
- 26 herramientas o más con invariantes del catálogo;
- MCP sin simulación ni optimización;
- sin regresión en las evaluaciones vigentes;
- corte del calendario el miércoles 25 por la noche.

**Scale/Scope**: hasta 20 usuarios simultáneos (regla 13); 5 perfiles; 1 planta (caña) y la palma como P3.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Referencia: `CONSTITUTION.md` 2.0.0.

| Regla | Cumplimiento del diseño | Estado |
|---|---|:-:|
| I. Autoría | Commits y PR a nombre de los integrantes; sin coautores | ✅ |
| II. Reproducibilidad | `uv`; datos y baterías generados con semilla; `--check` de idempotencia | ✅ |
| III. Procedencia y ética | Datos sintéticos declarados, con ficha y sin nombres reales; anclajes de magnitud citados (R10) | ✅ |
| IV. Generación anclada | Perfiles públicos con citas `[U#]`/`[F#]`; planificación con cifras de herramientas, validador y `plan_card` (R12) | ✅ |
| V. Evaluación antes de afirmar | Baterías fijadas antes de evaluar; óptimo independiente (R9); sin regresión (R17) | ✅ |
| VI. Repositorio como producto | README, herramientas, ADR 0029, informes de evaluación, Archify | ✅ |
| VII. Simplicidad | Perfiles como configuración; LP lineal; BM25 en memoria para unos 12 procedimientos | ✅ |
| VIII. Revisión cruzada | PR a `main` con revisión de Jason; la enmienda 2.0.0 requiere su aprobación | ⏳ al PR |
| IX. Transparencia de IA | `prompts/profiles.md` en `prompt_log.md`; etiqueta sintética en cada respuesta | ✅ |
| Fase 3, reglas 8–15 | Un solo agente, catálogo único, seudónimos, MCP de solo lectura, SQLite, hardening: sin cambios | ✅ |
| Fase 3, regla 16 (perfiles) | `config/profiles.toml` y `prompts/profiles.md`; traza con perfil; persistencia con aprobación | ✅ |
| Fase 3, regla 17 (información pública) | Listas blancas sin herramientas de planta; precios vetados en el prompt y en `AGENTS.md` | ✅ |
| Fase 3, regla 18 (datos sintéticos) | Directorio propio, `synthetic: true`, citas `[S#]` separadas | ✅ |
| Fase 3, regla 19 (cifras de planificación) | Simulador y LP; LP elástico sin relajar capacidad; frase de decisión humana | ✅ |
| Fase 3, regla 20 (autorización) | `VALERIA_PLANNERS` y variables de jornada; «SÍ/NO» con vencimiento; MCP sin 24 y 25 | ✅ |
| Fase 3, regla 21 (evaluación) | `planning-eval`, `profiles-eval` y las baterías vigentes | ✅ |

**Re-check post-diseño (Fase 1)**: sin violaciones. La ruta nueva `planning` toca tipos compartidos (API y web); se
justifica en Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/025-agentes-manuelita-idea7/
├── spec.md
├── plan.md              # este archivo
├── research.md          # R1–R18
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── planning-tools.md
│   ├── profiles.md
│   └── cli.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
config/
├── profiles.toml                       # NUEVO: cinco perfiles (R1)
└── agent.toml                          # + [agent.route_limits.planning] (R4)
prompts/
├── profiles.md                         # NUEVO: foco por perfil (prompt_log §3.x)
└── agent.md                            # + reglas de la ruta planning y de los perfiles
data/synthetic/planificacion/v1/        # NUEVO: plant_cana.json, state.json, commitments.json,
                                        #        procedures/*.md, DATA_CARD.md (R10)
scripts/
├── generate_planning_data.py           # NUEVO
└── generate_planning_battery.py        # NUEVO
src/proyecto_modelos_lenguaje/
├── agent/
│   ├── profiles.py                     # NUEVO: carga, validación, is_authorized, triggers
│   ├── planning.py                     # NUEVO: datos, simulador, LP, LP elástico, plan_card, check_answer
│   ├── planning_reference.py           # NUEVO: óptimo de referencia por malla (R9)
│   ├── tools_planning.py               # NUEVO: SPECS 21–25 (patrón tools_*.py)
│   ├── planning_eval.py                # NUEVO: planning-eval y profiles-eval
│   ├── catalog.py                      # ROUTES + planning, mcp_allowed, filtro por perfil, PLAN_BY_ROUTE
│   ├── actions.py                      # save_production_proposal (26), ejecución desde last_plan
│   ├── models.py                       # Route + "planning"
│   ├── router.py                       # señales de planificación según perfil (R3)
│   ├── graph.py                        # ChatState.profile/last_plan, límites por ruta, validador de planning
│   ├── memory.py                       # PREFERENCE_KEYS + "audience"
│   ├── service.py / __main__.py        # perfil en send(); subcomandos planning, planning-eval, profiles-eval
│   └── observability.py                # profile en turns.jsonl
├── channels/bridge.py, format.py       # /perfil, planner_denied, «Fuentes sintéticas»
├── mcp_server.py                       # respeta mcp_allowed
├── api.py, api_models.py               # ChatRequest.profile, GET /api/profiles, Route
web/src/
├── lib/types.ts, lib/chat.ts           # Route, profile
└── components/ChatView.tsx             # selector y chip de perfil, profile en la traza
openclaw/workspace/AGENTS.md            # líneas rojas de la plataforma; planificación ≤ 5 herramientas
tests/
├── unit/agent/test_profiles.py, test_planning.py, test_planning_reference.py, test_tools_planning.py
├── unit/agent/test_catalog.py          # 26 herramientas, mcp_allowed
├── integration/agent/test_planning_flow.py   # perfil → ruta planning → HITL guardar
├── api/test_profiles_api.py
├── unit/channels/test_bridge_profile.py
└── fixtures/agent/planning_scenarios.jsonl, profile_routing.jsonl, tool_routing.jsonl (+6)
docs/
├── evaluacion_planificacion.{md,json}, evaluacion_perfiles.{md,json}   # NUEVOS
├── herramientas.md (regenerado), rubrica_modulo3.md §7, prompt_log.md, data_card.md
└── arquitectura.json/.html             # componente de planificación (Archify)
```

**Structure Decision**: se usa el monorepo existente. La planificación va en módulos nuevos del paquete `agent/`
(mismo patrón que `tools_*.py`), y los perfiles son configuración más un módulo de carga. No se crea ningún servicio
nuevo.

## Implementation Phases (orden y calendario)

| Fase | Cuándo | Contenido | Puerta |
|---|---|---|---|
| A. Datos y núcleo | Mié 25, mañana | Generador de datos (R10), `planning.py` (simulador, LP, elástico, `plan_card`), `planning_reference.py`, batería de 12 escenarios, `agent planning` CLI | `planning-eval --mode direct` cumple SC-001 |
| B. Herramientas y ruta | Mié 25, tarde | `tools_planning.py`, `mcp_allowed`, `save_production_proposal`, ruta `planning`, límites por ruta, validador R12, pruebas de catálogo con 26 | Pruebas sin red en verde. **Corte**: si no, la planificación queda solo en la web |
| C. Perfiles | Jue 26, mañana | `profiles.toml`, `profiles.md`, `profiles.py`, filtro por perfil, `/perfil`, `ChatRequest.profile`, `GET /api/profiles`, selector web, preferencia `audience`, autorización | Batería de perfiles en demo ≥ 90 % |
| D. Canal y evaluaciones reales | Jue 26, tarde | `channels simulate --profile`, formato WhatsApp, `AGENTS.md`, casos de blindaje (FR-019), corridas reales y docs | SC-002 a SC-005 |
| E. Documentación y ensayo | Vie 27 | README, herramientas, rúbrica §7, Archify, `prompt_log`, `data_card`, `make check`, ensayo de 15 min | SC-006, SC-007 |
| F. Palma (P3) | Solo si A–D están en verde el jueves a mediodía | `plant_palma.json` y `plant_id="palma"` | Igual que la fase A |

## Risks

| Riesgo | Mitigación |
|---|---|
| El LLM no encadena las herramientas o parafrasea mal las cifras | Ruta `planning` con plan y límites propios; validador R12 con respaldo `plan_card`; prompt con la secuencia esperada |
| Latencia > 20 s por WhatsApp | Optimizador < 1 s; respuesta resumida en el canal; `deepseek-flash`; medir en la fase D |
| Regresión de la batería de herramientas | El perfil visitante ofrece exactamente el catálogo anterior; prueba que lo verifica |
| Tiempo (4 días) | Corte del miércoles; palma como P3; la secuencia de la spec 024 queda como respaldo |
| Confusión entre datos sintéticos y reales en el pitch | Etiqueta obligatoria, citas `[S#]` separadas, ficha y guion explícito (rúbrica §7.4, pregunta 16) |
| Jason no aprueba la enmienda 2.0.0 a tiempo | PR temprano de requerimientos y plan; el diseño es aditivo y se puede desactivar con `[profiles].enabled = false` |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Ruta nueva `planning` en tipos compartidos (`models.py`, `api_models.py`, `types.ts`) | Da un subconjunto propio de herramientas, un plan visible y límites de llamadas sin tocar el clasificador evaluado | Reusar `structured` mezcla herramientas de planta con las públicas y altera la batería de 53 casos |
| Campo `mcp_allowed` en `ToolSpec` | Permite herramientas de lectura que no deben ir al modo degradado (simular, optimizar) | Marcarlas como `write` exigiría una aprobación absurda para un cálculo de lectura |
