# Implementation Plan: Valer-IA Caña con habilidades de agente de call center

**Branch**: `019-callcenter-skills` | **Date**: 2026-11-17 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/019-callcenter-skills/spec.md`

## Summary

Valer-IA deja de responder con frases fijas a lo que está fuera de Manuelita y atiende como una agente de call center.
Un módulo determinista nuevo, `agent/care.py`, analiza cada mensaje: emoción, hostilidad, rechazo, crítica, crisis y
solicitudes múltiples. A partir de ese análisis, Valer-IA:

1. **US1 (P1), temas ajenos**: compone la respuesta desde guiones versionados (`prompts/care.md`):
   - reconoce el tema concreto;
   - pone un límite cordial;
   - ofrece un puente a Manuelita con cita al oro;
   - rota variantes por hilo.

   No hay llamadas al LLM, así que nunca aparecen hechos externos (R1, R2). Si el mensaje mezcla un tema ajeno con
   una pregunta de Manuelita, responde la parte de Manuelita y declina la otra (R7).
2. **US2 (P2), empatía y paciencia**:
   - la emoción se detecta con reglas (R3);
   - la apertura empática se antepone de forma determinista en `finalize` (R4);
   - los insultos reciben un límite cordial escalonado sin cortar la atención (R6);
   - las crisis tienen un motivo propio con la Línea 106 y el 123, por encima de todo (R5).
3. **US3 (P3), escucha y claridad**:
   - una sola aclaración con opciones y después la mejor interpretación (R10);
   - hasta 5 solicitudes por mensaje, con búsqueda por parte (R7);
   - parafraseo tras una confusión (R11);
   - reglas de forma pensadas para la voz (R12).
4. **US4 (P4), asertividad y resiliencia**:
   - motivo `unattainable`, con los tipos `pricing`, `commitment` y `human`; solo menciona los canales oficiales
     verificados en el oro (sitio web, Línea Ética, protección de datos) (R8);
   - alternativas que no se repiten ante rechazos, y escalamiento en la tercera queja (R9).
5. **US5 (P5), CRM**:
   - `ContactRecord` por hilo, con etiquetas controladas y sin texto del visitante (R13);
   - se muestra solo en la vista técnica;
   - la batería `agent care` genera el reporte agregado y mide SC-001 a SC-010 (R14).

Las decisiones están en [research.md](./research.md), R1–R16.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5.9 + React 19 (frontend)

**Primary Dependencies**: las existentes (FastAPI, LangGraph/LangChain, Pydantic). **Sin dependencias nuevas.**

**Storage**:
- Checkpointer de LangGraph (estado del hilo): claves nuevas `care` (CareState) y `contact` (ContactRecord).
- Nada nuevo en el Store por usuario ni en `data/`.

**Testing**:
- pytest:
  - `care.analyze`: emociones, sarcasmo, hostilidad, crisis, división de solicitudes y catálogo de temas;
  - composición y rotación de variantes;
  - saneamiento de `topic`;
  - estructura de `care.md` y verificación de citas contra el oro (se omite sin LFS);
  - flujo en los dos grafos (crisis, insulto con pregunta, varias partes, aclaración repetida, rechazo, tercera
    queja);
  - registro del contacto sin datos personales;
  - contrato de los campos nuevos de la API;
  - batería `agent care --mode demo`.
- Vitest: `ContactRecordPanel` solo en la vista técnica.
- Pruebas con red (`@network`): `agent care --mode real` y `agent conduct --mode real`.

**Target Platform**: servidor local o de despliegue con `make app`; navegadores modernos.

**Project Type**: aplicación web (FastAPI + SPA React) con CLI de evaluación.

**Performance Goals**:
- `care.analyze` y `care.compose` tardan menos de 5 ms por mensaje.
- Las respuestas compuestas no llaman al LLM.
- La primera palabra no tarda más de un 20 % que con `[care] enabled=false` (SC-010).

**Constraints**:
- Las respuestas compuestas no contienen hechos externos.
- Los teléfonos, correos y URLs solo salen de canales citados en el oro.
- Los motivos de seguridad de la spec 018 no cambian (FR-005, SC-008).
- El CRM no guarda texto del visitante ni datos personales.
- Las pruebas corren sin red.
- No se presenta como asesoría oficial (CONSTITUTION §10).

**Scale/Scope**:
- 1 módulo nuevo (`care.py`), 1 prompt nuevo (`care.md`) y 3 prompts versionados;
- 2 motivos nuevos y 3 campos opcionales en la ruta;
- 2 claves de estado, 1 campo opcional en la API y 1 panel web;
- unos 14 temas en el catálogo y unos 36 casos de evaluación.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|-------------------------|----------------|--------|
| I. Autoría y uso de IA | Los commits los hace el equipo (§4.3). Valer-IA sigue declarándose IA y, ante «quiero una persona», lo aclara (FR-018). | ✅ |
| II. Reproducibilidad | Los guiones (`care.md`) y las versiones de `agent.md`, `router.md` y `conduct.md` quedan en `prompts/` y `docs/prompt_log.md`. La batería y sus casos están versionados. La composición es determinista con una rotación reproducible. | ✅ |
| III. Ética y legalidad | La respuesta de crisis remite a la línea oficial del Ministerio de Salud. El CRM no guarda datos personales (FR-022). No se analiza la voz del visitante. | ✅ |
| IV. Generación anclada | Los puentes y canales llevan cita verificada contra el oro. Las declinaciones no afirman hechos. Las citas del modelo se siguen validando (FR-028). | ✅ |
| V. Evaluación empírica | `agent care` en modo demo y real, con métricas por habilidad, línea base de latencia y una rúbrica humana. Se repite `agent conduct` para descartar regresiones. | ✅ |
| VII. Simplicidad | No hay dependencias nuevas. Se usan reglas y guiones en vez de un clasificador o un LLM adicional, y una sola llamada al modelo por turno. | ✅ |
| §3.7 App web | La vista de visitante no cambia en lo visual. El CRM vive en la vista técnica. | ✅ |
| §3.9 Seguridad | El `topic` del LLM se sanea antes de mostrarse. Los motivos de seguridad se evalúan antes que las habilidades nuevas. | ✅ |
| §10 No es asesoría oficial | Los consejos profesionales se declinan, se recomienda acudir a un profesional y no se promete nada en nombre de la empresa. | ✅ |

**Resultado**: PASS. No hay violaciones que justificar.

**Re-check post-diseño (Phase 1)**: PASS. Los contratos solo añaden campos opcionales. `conduct.md` conserva sus
secciones como respaldo, y los motivos `third_party`, `prompt_extraction`, `harmful` y `abuse` (solo hostil)
mantienen su texto exacto.

## Project Structure

### Documentation (this feature)

```text
specs/019-callcenter-skills/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/
│   ├── care-skills.md     # prioridad de decisión, composición, antepuestos, crisis, brief, batería
│   └── api-changes.md     # ChatResponse.contact, campos nuevos de la ruta, panel técnico
├── checklists/requirements.md
└── tasks.md               # /speckit-tasks
```

### Source Code (repository root)

```text
prompts/
├── care.md               # NUEVO v1.0: guiones de atención con variantes y citas
├── agent.md              # v1.5: claridad verbal, varias solicitudes, críticas, sin apertura propia
├── router.md             # v1.4: crisis, unattainable+kind, topic y sentiment opcionales
└── conduct.md            # v1.1: off_topic, advice y clarify como respaldo

config/agent.toml         # + [care] enabled, max_requests, hostility_levels, complaint_escalation

src/proyecto_modelos_lenguaje/agent/
├── care.py               # NUEVO: analyze, TOPICS, split_requests, compose, CareState, ContactRecord
├── router.py             # + crisis primero; abuse solo hostil; temas desde care.TOPICS; topic/sentiment/kind
├── models.py             # + ScopeReason crisis/unattainable; RouteDecision.topic/sentiment/kind
├── graph.py              # route: analyze + aclaración repetida; reply: compose; retrieve: por parte;
│                         # finalize: antepuestos, declinaciones, CareState y ContactRecord
├── demo.py               # parafraseo y respuestas por parte en el modelo guionizado
├── prompts.py            # + load_care() con variantes y citas
├── config.py             # + CareConfig
├── service.py            # ChatOutcome.contact; ThreadView.contact
├── care_eval.py          # NUEVO: casos, ejecución, métricas y reporte de `agent care`
└── __main__.py           # + subcomando `care`
src/proyecto_modelos_lenguaje/api_models.py   # ContactRecordModel; ChatResponse/ThreadView.contact

web/src/
├── lib/types.ts                        # ContactRecord, Sentiment y campos de ruta
├── components/ContactRecordPanel.tsx   # NUEVO (vista técnica)
├── components/ChatView.tsx             # guarda y pasa contact
└── test/ContactRecordPanel.test.tsx    # NUEVO

tests/
├── unit/agent/test_care.py, test_care_playbook.py
├── integration/agent/test_care_flow.py (cadena y agente), test_care_eval.py
├── integration/agent/test_care_real.py          # @network
├── api/test_care_api.py
├── contract/ (esquema de la decisión de ruta con los campos nuevos)
└── fixtures/care/care_cases.jsonl, fixtures/conduct/conduct_cases.jsonl (expectativas de off_topic/advice)

docs/
├── decisions/0023-atencion-call-center.md
├── evaluacion_atencion.md / .json       # generado por `agent care --mode real`
├── prompt_log.md, evaluacion_conducta.md (re-ejecución), demo.md, README.md
CONSTITUTION.md (v1.11.0: conducta de atención, crisis y CRM sin datos personales)
```

**Structure Decision**:
- Las habilidades de atención se concentran en un módulo determinista (`care.py`) con guiones versionados. Así, la
  ausencia de hechos externos, el trato ante crisis y el CRM sin datos personales se garantizan por construcción, y
  funcionan igual en demo y en real y en las dos variantes del grafo.
- El LLM solo se usa donde hay evidencia del corpus: responde las partes de Manuelita en orden, con claridad y
  parafraseo, guiado por un brief breve.
- El grafo no gana nodos: `route`, `reply`, `retrieve` y `finalize` se amplían.

## Complexity Tracking

No aplica: el Constitution Check no tiene violaciones.
