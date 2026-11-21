# Implementation Plan: Respuesta progresiva por frases revisadas

**Branch**: `021-sentence-streaming` | **Date**: 2026-11-20 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/021-sentence-streaming/spec.md`

## Summary

Las respuestas de Valer-IA pasan a entregarse **frase por frase**, y cada frase se revisa antes de mostrarse. Los
nodos que generan texto (`converse`, `answer` y `agent`) consumen el modelo en streaming y pasan el texto por un
**filtro de frases** (`agent/sentences.py`), que arma frases con la regla de la voz, las revisa con `review()` de la
spec 020 y emite las aprobadas como eventos `sentence`. La respuesta final se arma con esas mismas frases, más las
que se entregan antes y después del texto del modelo (`lead`, `tail`), así que nunca se retira texto mostrado.

1. **US1 (P1), conversación**:
   - `converse` en streaming;
   - regeneración solo si falla la primera frase;
   - corte en la primera frase rechazada posterior;
   - respaldo por frases (R1–R5).
2. **US2 (P2), respuestas con búsqueda**:
   - `answer` y `agent` con frases revisadas;
   - frases sin cita retenidas hasta una citada;
   - frases descartadas que nunca se muestran (R6, R7).
3. **US3 (P3), voz**: `pushSentence` lee la primera oración sin esperar (R10, R14).
4. **US4 (P4), medición**:
   - tiempo hasta la primera frase y total por clase de turno;
   - texto retirado;
   - línea base `delivery = "complete"` (R13).

Las decisiones están en [research.md](./research.md), R1–R16.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5.9 + React 19 (frontend)

**Primary Dependencies**: las existentes. Usa `langgraph.config.get_stream_writer` (LangGraph 1.2.18, modo `custom`)
y `BaseChatModel.stream`. **Sin dependencias nuevas.**

**Storage**:
- Estado del hilo: claves de turno `lead`, `delivered` y `discarded`.
- `ContactTurnModel.discarded`.
- Nada en el Store ni en `data/`.

**Testing**:
- pytest:
  - `SentenceGate`: segmentación (abreviaturas, enumeradores, citas, fragmentos largos), decisiones `deliver`,
    `retry` y `stop`, retención de frases sin cita;
  - flujo en ambos grafos con modelos guionados que transmiten: G1–G4, primera frase rechazada, frase posterior
    rechazada, error a mitad del stream, tiempo vencido, frases exigidas y modo `complete`;
  - API SSE: eventos `sentence` y ausencia de `token`.
- Vitest: `liveStage` con `sentence`, `pushSentence` y la marca `✂N`.
- Con red: `agent converse --mode real --baseline-delivery`.

**Target Platform**: servidor local o de despliegue con `uvicorn`; navegadores modernos.

**Project Type**: aplicación web (FastAPI + SPA React) con CLI de evaluación.

**Performance Goals**:
- Primera frase en menos de 3 s en el p90 de los turnos de conversación (SC-001).
- En búsqueda, como máximo 1 s más que hoy (SC-002).
- Tiempo total como máximo un 10 % mayor (SC-006).
- Revisión por frase en menos de 5 ms.

**Constraints**:
- Nunca se retira texto mostrado (SC-003).
- Cero frases sin revisar (SC-004).
- Las metas duras de la spec 020 y la conducta 24/24 se mantienen (SC-005).
- Pruebas sin red.
- `delivery = "complete"` reproduce la spec 020.

**Scale/Scope**:
- 1 módulo nuevo (`agent/sentences.py`).
- 3 nodos modificados (`converse`, `answer`, `agent`), más `route` y `finalize`.
- 1 evento SSE nuevo.
- 5 claves de configuración.
- 5 secciones de `care.md` (1.2).
- Unas 25 pruebas nuevas.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|-------------------------|----------------|--------|
| I. Reproducibilidad | Parámetros en `[conversation]`. El demo es determinista. La evaluación guarda la medición de entrega y la configuración en el informe. | ✅ |
| II. Evaluación con línea base | `agent converse --baseline-delivery` compara contra la entrega completa (spec 020) con las mismas conversaciones. | ✅ |
| III. Procedencia | Cada frase con búsqueda conserva sus citas validadas. Las frases sin respaldo no se muestran. | ✅ |
| IV. Experimentos versionados | Fixtures y casos en `tests/fixtures/converse/` (reutilizados). Modo conmutable. | ✅ |
| V. Simplicidad | Sin dependencias nuevas. Se reutilizan `review()`, la regla de oraciones de la voz y el escritor de LangGraph. | ✅ |
| §3.7 (app web y agente) | Entrega por frases revisadas, sin retirar texto. Debe precisarse en la Constitución (v1.13.0): hoy dice que `converse` no se transmite token a token antes de revisarse, y la regla nueva lo cumple con más precisión. | ✅ (con actualización) |
| §3.9 (seguridad) | Las respuestas fijas no cambian. La revisión se aplica antes de cada frase. | ✅ |
| §10 (ética) | Sin cambios en la política de tres niveles. | ✅ |
| §4.3 Autoría | Los commits los hace el equipo; Claude prepara los cambios. | ✅ |

**Resultado**: PASS. La actualización de §3.7 y el ADR 0025 van en el mismo commit.

**Re-check post-diseño (Phase 1)**: PASS.
- El contrato es aditivo: un evento nuevo, `sentence`; el campo `discarded`, opcional con defecto 0; y un aviso.
- Los clientes que ignoran `sentence` siguen recibiendo la respuesta completa en `done`.
- `delivery = "complete"` mantiene el contrato de la spec 020.

## Project Structure

### Documentation (this feature)

```text
specs/021-sentence-streaming/
├── plan.md, research.md, data-model.md, quickstart.md
├── contracts/streaming.md     # eventos SSE, orden lead/delivered/tail, filtro de frases, API, web, evaluación
├── checklists/requirements.md
└── tasks.md                   # /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/agent/
├── sentences.py        # NUEVO: segmentador incremental, SentenceGate, decisiones deliver/retry/stop
├── graph.py            # converse/answer/agent en streaming con el filtro; lead en route; tail en finalize
├── review.py           # revisión de una frase (verificaciones locales); similitud de la primera frase
├── config.py           # delivery, sentence_max_chars, first_fragment_chars, timeouts del stream
├── demo.py             # demo_converse entregado por frases
├── service.py          # modo custom del stream → evento sentence; sin token en delivery=sentences
├── converse_eval.py    # medición de entrega, texto retirado, --baseline-delivery
├── care_eval.py        # primera frase en lugar de primer token
└── __main__.py         # converse --baseline-delivery
src/proyecto_modelos_lenguaje/api_models.py   # ContactTurnModel.discarded
src/proyecto_modelos_lenguaje/voice/text.py   # regla de oraciones compartida (sin cambios de comportamiento)

prompts/care.md         # 1.2: close.short y required.*
config/agent.toml       # claves nuevas de [conversation]

web/src/
├── lib/types.ts                      # evento sentence; ContactTurn.discarded
├── lib/useVoice.ts, lib/voice.ts     # pushSentence
├── components/ChatView.tsx           # liveStage con sentence
├── components/ContactRecordPanel.tsx # ✂N en «Actos»
└── test/ChatView.test.tsx, ChatViewVoice.test.tsx, voice.test.ts, ContactRecordPanel.test.tsx

tests/
├── unit/agent/test_sentences.py
├── integration/agent/test_sentence_flow.py     # ambos grafos, modelos guionados que transmiten
├── api/test_sentence_stream.py
└── (ajustes) test_converse_flow.py, test_converse_api.py, test_chat_stream.py, test_converse_eval.py

docs/
├── decisions/0025-entrega-por-frases.md
├── evaluacion_conversacion.md / .json (sección «Entrega»)
├── prompt_log.md §3.19 (care.md 1.2), README.md, demo.md
CONSTITUTION.md (v1.13.0, §3.7)
```

**Structure Decision**:
- El filtro de frases es un módulo puro y sin red, probado por separado.
- Los nodos solo cambian cómo consumen el modelo (`stream` en lugar de `invoke`) y emiten lo aprobado.
- `finalize` deja de anteponer y agregar texto por su cuenta: ensambla `lead + delivered + tail` y entrega `tail`.
- Todo se apaga con `[conversation] delivery = "complete"`.

## Complexity Tracking

No aplica: el Constitution Check no tiene violaciones.
