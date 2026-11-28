# Implementation Plan: Conversación enfocada en Manuelita, con empatía y sin abrir charla ajena

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–034; `setup-plan` reporta
`035-enfoque-manuelita-conversacion` por `.specify/feature.json`) | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/035-enfoque-manuelita-conversacion/spec.md`

## Summary

Valer-IA abrió y sostuvo una charla ajena porque cuatro piezas de la conversación guiada (spec 020) lo permitían:

- el prompt pide «acompañar con naturalidad» y permite preguntas de vuelta;
- una de las aperturas sugeridas es una pregunta;
- el puente es intermitente y no hay redirección obligatoria;
- el verificador no revisa el enfoque.

Diseño (research R1–R7):

1. **Plan del turno** (`agent/plan.py`): en turnos sociales o ajenos, el plan exige el regreso a Manuelita y
   prohíbe preguntas ajenas. Lleva la racha de turnos ajenos seguidos, propone 2–3 temas rotativos de
   `care.md` y, desde la racha 3, limita la respuesta a dos frases.
2. **Prompt** `prompts/converse.md` 1.0 → 1.1:
   - cortesía o empatía en una frase;
   - preguntas solo sobre Manuelita;
   - ante «charlemos», propósito más temas;
   - sin frases de rechazo;
   - ejemplos nuevos.

   Las aperturas en forma de pregunta (`OPENINGS`) se excluyen en esos turnos.
3. **Verificador duro** (`agent/review.py`): checks `offtopic_question`, `chat_invite`, `no_redirect`, `rejection`
   y `closing_repeat`, con el reintento y el respaldo de `care.md` que ya existen.
4. **Evaluación**: `tests/fixtures/converse/focus.jsonl` (16 conversaciones, incluida la prueba seudonimizada),
   las comprobaciones nuevas en `converse_eval` y `agent converse --focus`. En modo real, regresión de la
   evaluación de conversación vigente.
5. **Registro**: `docs/prompt_log.md` §3.29, la línea del modo degradado en el workspace de OpenClaw y el aviso
   a Roberto (agente compartido con la web).

## Technical Context

**Language/Version**: Python 3.14; prompts en Markdown versionados.

**Primary Dependencies**: LangGraph (nodo `converse`), DeepSeek (modelo real), modelo guionado (demo). Sin
dependencias nuevas.

**Storage**: la memoria de conversación existente (`care.update_conversation`) agrega `offtopic_streak` y
`offered_topics`, dentro del estado del hilo y sin datos personales.

**Testing**:

- pytest: `tests/unit/agent/test_review.py` (checks nuevos), `test_plan*.py` (racha, redirección, temas),
  `test_converse*.py` (aperturas y prompt), `tests/unit/agent/test_converse_eval.py` (comprobaciones nuevas);
- `agent converse --focus --mode demo` en verde;
- `--mode real` para la medición (SC-001 a SC-006).

**Target Platform**: el backend compartido (web y WhatsApp).

**Project Type**: servicio web con agente LangGraph.

**Performance Goals**: sin llamadas nuevas al modelo, salvo los reintentos del verificador cuando un check
falla (como hoy).

**Constraints**:

- no bajar la empatía ni la evaluación publicada (regla 21);
- no inventar datos (los temas sugeridos no traen cifras);
- sin datos personales en fixtures (transcripción seudonimizada).

**Scale/Scope**: los turnos sociales y ajenos del agente; los demás actos no cambian.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §3.5 Prompts versionados y registrados | ✅ con tarea | `converse.md` sube a 1.1 y `care.md` gana `offer.topics`; ambos se registran en `docs/prompt_log.md` §3.29. |
| Regla 21 Evaluaciones publicadas no bajan | ✅ con tarea | Regresión en modo real de la evaluación de conversación. Si baja, no se cierra la spec. |
| Regla 22 Conversación natural | ✅ | Se conserva la calidez y se agrega el enfoque; sin comandos. |
| Regla 10 y §10 Datos personales y declaración de IA | ✅ | La transcripción va seudonimizada; la presentación de IA no cambia. |
| §3.3 Capas medallion | ✅ | No se toca `data/`; los temas sugeridos se apoyan en hechos públicos ya usados por los puentes. |
| §4.3 Proceso | ✅ | Spec Kit completo; aviso a Roberto por el cambio compartido. |
| Cambios de arquitectura → CONSTITUTION.md | ✅ sin enmienda | Ajuste de comportamiento dentro de la conversación guiada; sin cambio de arquitectura ni de tecnología. |

**Resultado**: pasa sin enmiendas.
**Re-check post-design**: igual. ✅

## Project Structure

### Documentation (this feature)

```text
specs/035-enfoque-manuelita-conversacion/
├── plan.md
├── research.md        # R1–R7
├── data-model.md
├── quickstart.md
├── contracts/
│   └── focus-rules.md  # plan, prompt, verificador y evaluación
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
prompts/converse.md                    # 1.1: enfoque, preguntas solo de Manuelita, ejemplos
prompts/care.md                        # offer.topics (temas sugeridos)
src/proyecto_modelos_lenguaje/agent/
├── plan.py                            # TurnPlan: redirect, streak, topics; render
├── graph.py                           # opening_hint sin preguntas en turnos ajenos; plan con temas
├── care.py                            # memoria: offtopic_streak, offered_topics
├── bridges.py                         # primer turno ajeno con puente (si hay)
├── review.py                          # checks de enfoque y NOTES
└── converse_eval.py                   # comprobaciones nuevas y bloque --focus
tests/fixtures/converse/focus.jsonl    # 16 conversaciones (incluida la prueba seudonimizada)
tests/unit/agent/...                   # pruebas de plan, review, aperturas y evaluación
openclaw/workspace/AGENTS.md           # modo degradado: regla breve
docs/prompt_log.md (§3.29), docs/evaluacion_conversacion.* (si se re-mide)
```

**Structure Decision**: el cambio vive en la conversación guiada del agente (spec 020), con el verificador como
garantía. El canal y el enrutador no cambian.

## Complexity Tracking

Sin violaciones que justificar.
