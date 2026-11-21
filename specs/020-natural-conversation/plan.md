# Implementation Plan: Conversación natural guiada para Valer-IA Caña

**Branch**: `020-natural-conversation` | **Date**: 2026-11-19 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/020-natural-conversation/spec.md`

## Summary

Valer-IA deja de responder con guiones lo que no es Manuelita. Un nodo nuevo, `converse`, redacta cada respuesta sin
búsqueda con DeepSeek. Lo guía un **plan del turno** determinista, y su texto pasa por una **revisión** antes de
mostrarse. Si la revisión falla dos veces o el modelo no responde, se usa como respaldo la composición de la spec 019.
Las respuestas de seguridad (crisis, terceros, extracción del prompt, daño, insulto solo) siguen siendo fijas.

1. **US1 (P1), naturalidad con límites**:
   - política de tres niveles por parte: `social`, `external`, `manuelita` (R3);
   - plan del turno con acto de diálogo, estrategia, longitud, idioma y registro (R4);
   - `prompts/converse.md` v1.0;
   - temperatura por tipo de turno (R7);
   - `review.py` con detección de hechos externos, contactos, promesas, citas, repetición y opiniones (R8);
   - respaldo (R9);
   - sin streaming en `converse` (R10);
   - los mensajes mixtos van a la búsqueda con un brief ampliado (R11).
2. **US2 (P2), puentes medidos**: `bridges.py` con elegibilidad (cuota, emoción, rechazo, cierre), candidatos
   buscados en el oro con un mapa de ángulos y selección sin repetir unidad ni ángulo en el hilo (R5).
3. **US3 (P3), memoria**: `ConversationMemory` por hilo con temas, puentes ofrecidos y rechazados, correcciones,
   registro, idioma y nombre solo dentro del hilo (R6). Despedida con resumen.
4. **US4 (P4), situaciones del chat**: actos `minimal`, `about_assistant`, `thanks` y `closing`; idioma y registro
   (R12).
5. **US5 (P5), evaluación**: `agent converse` con repetición entre hilos, conversaciones guionadas, simuladas con 5
   perfiles, juez de naturalidad, verificaciones duras y línea base `scripted` (R15). Las baterías de la spec 019
   pasan a evaluar intención en vez de texto literal (R16).

Las decisiones están en [research.md](./research.md), R1–R17.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5.9 + React 19 (frontend)

**Primary Dependencies**: las existentes (FastAPI, LangGraph/LangChain, langchain-openai, Pydantic). **Sin
dependencias nuevas.** `difflib` es de la biblioteca estándar.

**Storage**:
- Checkpointer de LangGraph: claves nuevas `conversation` (ConversationMemory) y `plan` (TurnPlan, por turno).
- `ContactRecord.turns`: etiquetas.
- Nada en el Store por usuario ni en `data/`.

**Testing**:
- pytest:
  - `plan.build_plan` con las tablas del contrato §2;
  - `review`: cada verificación, falsos positivos conocidos y respaldo;
  - `bridges`: elegibilidad, no repetición, candidatos con y sin oro;
  - flujo en ambos grafos: social, externo, mixto, cuota de puentes, rechazo, molestia, corrección, nombre, cierre,
    mínimos, inglés, error del modelo, regeneración y modo `scripted`;
  - contrato de la API;
  - `agent converse --mode demo`.
- Vitest: la línea «Actos» del panel técnico.
- Con red (`@network`): `agent converse --mode real`, `agent care --mode real` y `agent conduct --mode real`.

**Target Platform**: servidor local o de despliegue con `make app`; navegadores modernos.

**Project Type**: aplicación web (FastAPI + SPA React) con CLI de evaluación.

**Performance Goals**:
- `build_plan` + `review` + elegibilidad de puentes: menos de 10 ms.
- Búsqueda del puente: menos de 50 ms.
- Primera palabra en menos de 3 s en el 90 % de los turnos (SC-011).

**Constraints**:
- Cero hechos externos, contactos inventados o promesas en lo que ve el visitante (SC-005).
- Las respuestas de seguridad no cambian (SC-006).
- El nombre del hilo nunca sale del estado del hilo.
- Las pruebas corren sin red.
- El modo `scripted` reproduce la spec 019.
- CONSTITUTION §10: no se presenta como asesoría ni como canal oficial.

**Scale/Scope**:
- 4 módulos nuevos: `plan.py`, `bridges.py`, `review.py`, `converse_eval.py`.
- 1 nodo nuevo en cada grafo.
- 3 prompts nuevos: `converse.md`, `converse_judge.md`, `visitor_sim.md`.
- 3 prompts versionados: `agent.md` 1.6, `router.md` 1.5, `care.md` 1.1.
- 1 sección de configuración y 3 campos opcionales en la API.
- Unas 12 conversaciones guionadas y 5 perfiles simulados.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|-------------------------|----------------|--------|
| I. Reproducibilidad experimental | Los prompts nuevos (`converse.md`, `converse_judge.md`, `visitor_sim.md`) y sus versiones quedan en `prompts/` y en `docs/prompt_log.md`, con SHA. Los parámetros van en `[conversation]`. El demo es determinista con una semilla por hilo y turno. El modo real guarda transcripciones y configuración en el informe JSON. | ✅ |
| II. Evaluación con métricas y línea base | `agent converse` mide diversidad, puentes, juez, garantías duras y latencia contra la línea base `scripted` (spec 019), con informe en `docs/evaluacion_conversacion.*` y rúbrica humana. | ✅ |
| III. Procedencia y ética de datos | Todo puente sale del oro con cita. La revisión bloquea hechos externos sin procedencia. El nombre del hilo no se persiste fuera del hilo. Las crisis tienen respuesta fija con fuente oficial. | ✅ |
| IV. Experimentos como código versionado | La batería, los casos y los perfiles están versionados en `tests/fixtures/converse/`. El modo conmutable por configuración permite repetir la comparación. | ✅ |
| V. Simplicidad y alcance académico | No hay dependencias nuevas. Revisión por reglas y no con un juez LLM en línea (opcional y desactivado). Una sola llamada extra por turno sin búsqueda. Se reutilizan el retriever, la composición de la spec 019 y la validación de citas. | ✅ |
| CONSTITUTION §3.7 (app web y agente) | La vista de visitante no cambia en lo visual. Las etiquetas nuevas solo aparecen en la vista técnica. | ✅ |
| CONSTITUTION §3.9 (seguridad) | Los casos de seguridad se evalúan antes de `converse` y conservan su texto. La revisión se aplica antes de mostrar. Sin streaming en `converse`. | ✅ |
| CONSTITUTION §10 (ética, no es canal oficial) | La política de tres niveles precisa el límite: lo social se permite y los datos verificables externos se declinan. Debe registrarse en la Constitución (v1.12.0) y en el ADR 0024. | ✅ (con actualización) |
| §4.3 Autoría | Los commits los hace el equipo; Claude prepara los cambios. | ✅ |

**Resultado**: PASS. La actualización de §10 y §3.7 es un cambio de proceso o arquitectura que se hace en el mismo
commit, como exige la norma, no una violación.

**Re-check post-diseño (Phase 1)**: PASS.
- Los contratos solo añaden campos opcionales (`act`, `turns` y avisos nuevos).
- `conduct.md` y `care.md` conservan sus secciones (care.md 1.1 solo añade `angles.*`).
- El modo `scripted` permite verificar la no regresión con las baterías de las specs 018 y 019.

## Project Structure

### Documentation (this feature)

```text
specs/020-natural-conversation/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── conversation.md    # orden de decisión, plan, prompt de converse, revisión, brief, finalize, batería
│   └── api-changes.md     # RouteModel.act, ContactRecord.turns, notices, streaming, web y CLI
├── checklists/requirements.md
└── tasks.md               # /speckit-tasks
```

### Source Code (repository root)

```text
prompts/
├── converse.md           # NUEVO v1.0: identidad, tres niveles, estilo, puente, memoria, ejemplos de estilo
├── converse_judge.md     # NUEVO v1.0: rúbrica de naturalidad, empatía y pertinencia (JSON)
├── visitor_sim.md        # NUEVO v1.0: perfiles de visitante simulado
├── agent.md              # v1.6: brief ampliado (social, externo, idioma, registro), una sola respuesta fluida
├── router.md             # v1.5: campo opcional act
└── care.md               # v1.1: secciones angles.<tema> (mapa de ángulos); guiones como respaldo

config/agent.toml         # + [conversation] (mode, temperaturas, penalizaciones, cuota, umbrales, timeout)

src/proyecto_modelos_lenguaje/agent/
├── plan.py               # NUEVO: DialogueAct, Tier, TurnPlan, build_plan, léxicos de actos
├── bridges.py            # NUEVO: elegibilidad, candidatos (retriever + ángulos), selección, BridgeRecord
├── review.py             # NUEVO: review(), ReviewVerdict, notas de corrección
├── converse_eval.py      # NUEVO: bloques de repetición, guionadas, simuladas, juez, métricas e informe
├── care.py               # + tier por parte, actos nuevos, idioma y registro; ConversationMemory
├── graph.py              # + nodo converse en ambos grafos; route → plan; brief ampliado; finalize en guided
├── router.py             # + act desde el LLM; los motivos de seguridad siguen primero
├── models.py             # + DialogueAct; RouteDecision.act
├── demo.py               # + demo_converse() determinista con semilla
├── prompts.py            # + load_converse(), ángulos en load_care()
├── config.py             # + ConversationConfig
├── service.py            # «converse» fuera de STREAMED_NODES; ContactRecord.turns
└── __main__.py           # + subcomando converse; care --conversation-mode
src/proyecto_modelos_lenguaje/api_models.py   # DialogueAct, RouteModel.act, ContactTurnModel, notices

web/src/
├── lib/types.ts                        # DialogueAct, ChatRoute.act, ContactRecord.turns
├── components/ContactRecordPanel.tsx   # línea «Actos» (vista técnica)
├── components/ChatView.tsx             # etapa «Pensando la respuesta…»
└── test/ContactRecordPanel.test.tsx    # casos nuevos

tests/
├── unit/agent/test_plan.py, test_review.py, test_bridges.py
├── integration/agent/test_converse_flow.py (cadena y agente), test_converse_eval.py
├── integration/agent/test_converse_real.py          # @network
├── integration/agent/test_care_flow.py              # parametrizado por modo (scripted/guided)
├── api/test_converse_api.py
├── contract/ (route-decision.schema.json con act)
└── fixtures/converse/conversations.jsonl, repeats.jsonl, profiles.toml; fixtures/care (expectativas de intención)

docs/
├── decisions/0024-conversacion-guiada.md
├── evaluacion_conversacion.md / .json    # generado por `agent converse --mode real`
├── prompt_log.md §3.18, evaluacion_atencion.md y evaluacion_conducta.md (re-ejecución), demo.md, README.md
CONSTITUTION.md (v1.12.0: política de tres niveles en §10; redacción guiada con revisión en §3.7)
```

**Structure Decision**:
- La conversación se separa en tres responsabilidades probables por separado:
  - **qué hacer**: `plan.py`, determinista;
  - **cómo decirlo**: `converse` con DeepSeek;
  - **si se puede mostrar**: `review.py`, determinista.
- Los puentes tienen su propio módulo porque combinan reglas de memoria con búsqueda en el oro.
- `care.py` sigue siendo la fuente de las señales y del respaldo.
- El grafo gana un único nodo (`converse`), y `reply` queda solo para seguridad, identidad y perfil.
- Todo se apaga con `[conversation] mode = "scripted"`.

## Complexity Tracking

No aplica: el Constitution Check no tiene violaciones.
