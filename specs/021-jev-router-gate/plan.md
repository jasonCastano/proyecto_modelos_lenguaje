# Implementation Plan: Gatekeeper System One (Jev) para el enrutador de Valer-IA

**Branch**: `021-jev-router-gate` | **Date**: 2026-11-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-jev-router-gate/spec.md`

## Summary

El enrutador del agente pasa de dos etapas (reglas → clasificador LLM) a tres: **reglas → gatekeeper Jev →
clasificador LLM**. Un módulo nuevo, `agent/jev.py`, hace como máximo **una** solicitud por turno a TypeSafe con cuatro
preguntas tipadas (ruta, motivo de fuera de alcance, molestia y crisis) y devuelve un `GateOutcome` que nunca lanza
excepciones. Con esa respuesta:

1. **US1 (P1), ruta rápida**: si la probabilidad de la ruta elegida alcanza el umbral (0,75 inicial), decide Jev
   (`decided_by="jev"`) y se evita la llamada a DeepSeek; si no, decide el clasificador actual (research R4, R5).
2. **US2 (P1), respaldo**: desactivado por defecto; sin clave, en demo, ante error, rechazo o timeout de 2 s, el turno
   sigue exactamente como hoy. Las pruebas y el modo demo usan `FakeJevGate` (R8, R9, R12).
3. **US3 (P2), señales de atención**: la crisis es la **unión** del regex vigente y la probabilidad de Jev; la molestia
   solo intensifica la emoción detectada; el motivo de fuera de alcance llena `scope_reason` (R6).
4. **US4 (P3), evidencia**: `agent jev --validate` (24 consultas nuevas en español, fija el umbral) y
   `agent jev --compare` (44 consultas, 36 casos de atención, 12 conversaciones), con informe en
   `docs/evaluacion_jev.{md,json}` (R10, R14).

El texto enviado pasa por `redact_pii()` (R7). Las instrucciones viven en `prompts/jev.md` (R11).

## Technical Context

**Language/Version**: Python ≥ 3.14 (backend); TypeScript (solo la etiqueta en la web)

**Primary Dependencies**: existentes (`langgraph`, `langchain-core`, `pydantic`, `python-dotenv`); `httpx` pasa del
grupo `dev` a dependencias del proyecto (ya llega como transitiva de `langchain-openai`). Sin SDK de TypeSafe (R1).

**Storage**: sin almacenamiento nuevo. Bloque `jev` en `$MANUELITA_STATE_DIR/logs/turns.jsonl`; informes en `docs/`.

**Testing**: `pytest` (unitarias y de contrato con `FakeJevGate` y transporte `httpx` simulado); prueba real con el
marcador `network`, excluida por defecto y en CI; `vitest` para la etiqueta web.

**Target Platform**: servidor local (FastAPI + uvicorn) en Windows y Linux.

**Project Type**: servicio web (backend FastAPI + SPA React) con CLI.

**Performance Goals**: decisión del gatekeeper ≤ 2 s en el peor caso (timeout) y alrededor de 100–500 ms en el caso
típico, según el proveedor; ≥ 50 % de las consultas que hoy llegan al LLM se deciden sin él; ≥ 95 % de respuestas en
menos de 10 s en ambas variantes (SC-002, SC-003).

**Constraints**: sin red ni clave en pruebas y CI; la clave solo en `.env`; versión del modelo fija; ninguna
detección de crisis puede perderse; costo de evaluación < 1 USD.

**Scale/Scope**: una solicitud por turno; conjuntos de 24 (validación), 44, 36 y 12 casos (evaluación).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / regla | Cumplimiento | Estado |
|---|---|---|
| I. Reproducibilidad | Versión del modelo fija y registrada en cada respuesta; umbrales en `config/agent.toml`; prompts versionados con hash; informes con `run_id`, commit y configuración. El proveedor es externo, así que los resultados reales se reproducen con la misma versión fijada, igual que con DeepSeek. | ✅ |
| II. Métricas y línea base | La línea base es el enrutador actual (`variants-real-2026-11-14` y `evaluate_router`). Las métricas y umbrales de éxito se fijan en la spec antes de medir. El umbral se ajusta con un conjunto de validación **distinto** del de evaluación (R10). | ✅ |
| III. Procedencia y ética | Sin datos nuevos de terceros; los mensajes se enmascaran antes de salir (R7); el segundo proveedor externo se documenta en la data card y el ADR. | ✅ |
| IV. Experimentos como código | Validación y comparación por CLI (`agent jev`); configuración TOML validada al inicio; sin credenciales en el código. | ✅ |
| V. Simplicidad | Cliente HTTP propio de ~100 líneas en lugar de SDK; una solicitud por turno; reutiliza `evaluate_router`, `agent care`, `agent converse` y `redact_pii`. Sin circuito abierto ni reintentos hasta que la evaluación lo justifique. Dependencia: solo se declara `httpx`, ya presente. | ✅ |
| Secretos (Restricciones técnicas) | `TYPESAFE_API_KEY` solo en el entorno; nunca en logs, respuestas ni web (FR-019, SC-008). | ✅ |
| Pruebas sin red | `FakeJevGate` y transporte simulado; real solo con `network`. | ✅ |
| `CONSTITUTION.md` (canónica) | Cambio tecnológico (nuevo proveedor externo) ⇒ actualizar §3.5/§3.6 y la sección de la Fase 2 en el mismo PR, más ADR 0025. Prompts nuevos ⇒ `docs/prompt_log.md`. | ✅ (tarea en el plan) |
| Autoría (§4.3, ADR 0017) | Commits y PR a nombre del integrante; sin coautores ni firmas de asistentes. | ✅ |

**Resultado**: sin violaciones; Complexity Tracking vacío.

**Re-check post-diseño**: el diseño de Phase 1 (data-model, contrato, quickstart) mantiene los mismos compromisos:
`GateOutcome` sin excepciones, una solicitud por turno, crisis como unión y desactivado por defecto. ✅

## Project Structure

### Documentation (this feature)

```text
specs/021-jev-router-gate/
├── plan.md              # este archivo
├── research.md          # Phase 0: R1–R14
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── jev-gate.md      # solicitud/respuesta, interfaz interna, orden de decisión, CLI
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/agent/
├── jev.py               # NUEVO: JevConfig, cliente HTTP, FakeJevGate, GateOutcome, merge_signals, check
├── config.py            # + sección [jev] → JevConfig
├── models.py            # DecidedBy += "jev"; TurnMetrics.gate_calls
├── router.py            # route_message(..., gate=...) entre reglas y LLM; RouterResult.gate
├── graph.py             # nodo route: gate.assess() tras care.analyze(); merge_signals(); métricas
├── observability.py     # bloque jev en turn_record
├── evaluate.py          # evaluate_router con gatekeeper opcional; métricas de Jev
└── __main__.py          # subcomando `jev` (--check, --validate, --compare)

prompts/jev.md                          # NUEVO: instrucciones y opciones de las 4 preguntas
config/agent.toml                       # + [jev]
.env.example                            # + TYPESAFE_API_KEY= (vacía), MANUELITA_JEV_ENABLED
pyproject.toml / uv.lock                # httpx a dependencias del proyecto

web/src/lib/types.ts                    # decided_by += "jev"
web/src/components/ChatView.tsx         # etiqueta «Jev»

tests/fixtures/jev/validation_es.jsonl  # NUEVO: 24 consultas de validación (4 por ruta)
tests/unit/test_jev.py                  # NUEVO: cliente, validación, fallos, privacidad, merge_signals
tests/unit/test_router_jev.py           # NUEVO: orden reglas → Jev → LLM, umbral, decided_by
tests/contract/test_jev_contract.py     # NUEVO: [jev] en TOML, prompts, .env.example sin valores
tests/integration/test_jev_real.py      # NUEVO: @pytest.mark.network
web/src/test/ChatView.test.tsx          # etiqueta «Jev»

docs/decisions/0025-jev-gatekeeper.md   # NUEVO ADR
docs/evaluacion_jev.{md,json}           # NUEVO (generado)
docs/evaluacion_modulo2.md, docs/informe_modulo2.md, docs/rubrica_modulo2.md, docs/prompt_log.md,
docs/data_card.md, README.md, CONSTITUTION.md   # actualizaciones
```

**Structure Decision**: proyecto único existente (`src/` + `web/`). Toda la lógica nueva queda en un módulo del
paquete `agent/` y en puntos de inserción acotados del router y del nodo `route`, siguiendo el patrón de `care.py`
(spec 019).

## Fases de implementación (guía para `/speckit-tasks`)

1. **Validación preliminar primero** (bloqueante): script de validación con la clave real y las 24 consultas en
   español. Confirma la forma de la API (R1), la versión (R2) y el umbral (R5). Si la exactitud es < 80 %, se registra
   como descartado y se detiene la integración (SC-009).
2. **Fundamentos**: `JevConfig`, `GateOutcome`, cliente HTTP con validación y fallos, `FakeJevGate`, `prompts/jev.md`,
   `[jev]`, `.env.example`, `httpx`.
3. **US1 + US2**: inserción en `route_message` y en el nodo `route`, `decided_by="jev"`, métricas y registro, chequeo
   `jev --check`, pruebas offline, etiqueta web.
4. **US3**: `merge_signals` (crisis como unión, molestia, motivo) y pruebas con los casos de crisis.
5. **US4**: `jev --compare`, informe, corrida de extremo a extremo, actualización de documentos, ADR y constitución.

## Riesgos

| Riesgo | Mitigación |
|---|---|
| La API real difiere de lo que dicen las guías | La validación preliminar se hace antes del cliente definitivo; el contrato se ajusta ahí |
| Jev no entiende bien el español | SC-009: se documenta y queda desactivado; el entregable sigue siendo válido como «evaluado y descartado» |
| Servicio caído o sin crédito durante la sustentación | Desactivado por defecto; con fallo, el sistema sigue como hoy (US2) |
| Latencia real mayor que la reportada | Timeout de 2 s; se mide en la comparación y se reporta tal cual |
| Pérdida de una crisis | La crisis es unión con el regex; prueba que lo garantiza con los casos de crisis |

## Complexity Tracking

Sin violaciones que justificar.
