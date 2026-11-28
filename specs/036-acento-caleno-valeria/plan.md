# Implementation Plan: Valer-IA con acento y expresiones caleñas, siempre profesional

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–035; `setup-plan` reporta
`036-acento-caleno-valeria` por `.specify/feature.json`) | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/036-acento-caleno-valeria/spec.md`

## Summary

Valer-IA debe sonar caleña, por escrito y en sus notas de voz, sin perder el perfil profesional. Hoy escribe en
español neutro. Su léxico informal es genérico y tiene modismos paisas («parce»). Habla con una voz mexicana
(«Rebeca»), y el motor de voz local no ofrece voces colombianas.

El usuario decidió tres cosas:

- el acento se logra con las palabras y el ritmo, más la voz latinoamericana más cercana;
- el trato es tuteo, sin voseo;
- el estilo aplica en la web y en WhatsApp.

Diseño (research R1–R8):

1. **Léxico versionado** `config/caleno.toml`. Lista aprobada con significado, niveles permitidos (`informal`,
   `neutral`, `formal`), uso hablado y ejemplo. Lista vetada con motivo: groserías, doble sentido, modismos de otras
   regiones y voseo. Lleva además los límites (1 por respuesta escrita, 2 por guion hablado) y las frases de
   «habla normal».
2. **Módulo `agent/style.py`**. Carga el léxico y fija el **nivel de estilo** del turno:
   - `off` con inglés, queja, angustia, crisis, textos fijos o si la persona pidió hablar normal;
   - si no, según el registro: `formal`, `neutral` o `informal`.

   Sugiere 2–3 expresiones sin repetir la última y renderiza el bloque `<estilo>` para los prompts. También cuenta
   expresiones y detecta las vetadas en una respuesta.
3. **Plan del turno** (`agent/plan.py`): campo `style` con el nivel y las expresiones sugeridas.
4. **Prompts**:
   - `converse.md` 1.1 → 1.2 y `agent.md` 1.10 → 1.11: sección de estilo caleño que obedece el bloque
     `<estilo>`;
   - `voice_script.md` 1.0 → 1.1: hasta dos expresiones habladas y ritmo caleño (frases cortas, «pues» de cierre),
     solo de la lista hablada.

   `conduct.md` (textos fijos) y `qa.md` (tareas de la Fase 1) no cambian.
5. **Verificador** (`agent/review.py`), con checks nuevos:
   - `style_banned`: expresión vetada o voseo; en las respuestas con búsqueda se quita la frase;
   - `style_excess`: más de una expresión;
   - `style_repeat`: la misma expresión que la respuesta anterior;
   - `style_off`: expresión con el nivel `off`.

   Usan el reintento y el respaldo existentes.
6. **Memoria del hilo** (`agent/care.py`): `style_opt_out` (pidió hablar normal) y `last_expressions` (para no
   repetir).
7. **Voz**: comando de audición `voice --audition`, que sintetiza una frase caleña con las voces femeninas de
   español candidatas y las expresiones habladas, fuera del repositorio. El usuario elige la voz y marca las
   expresiones mal pronunciadas, que pasan a `spoken = false`. Después se actualiza `config/voice.toml`.
8. **Modo demo**: el modelo guionado usa una expresión del bloque `<estilo>` para que la evaluación sin red sea
   representativa.
9. **Evaluación**:
   - `agent converse --style` corre `tests/fixtures/converse/caleno.jsonl` (registros informal, neutro y formal,
     queja, angustia, inglés, «¿qué significa ve?», «habla normal» y voz) y escribe
     `docs/evaluacion_caleno.{md,json}` con SC-001 a SC-005 y SC-008;
   - en modo real, juez de claridad y profesionalismo (`prompts/style_judge.md` 1.0, SC-006);
   - regresión de la conversación general (regla 21).
10. **Prueba humana** (SC-007): una persona de Cali califica 5 respuestas escritas y habladas.

## Technical Context

**Language/Version**: Python 3.14; prompts en Markdown versionados; TOML para el léxico.

**Primary Dependencies**:

- LangGraph (nodos `converse` y de respuesta);
- DeepSeek (modelo real) y el modelo guionado (demo);
- Phonon (`ptts`) para la voz, con su catálogo actual.

Sin dependencias nuevas.

**Storage**: memoria de conversación existente (`style_opt_out`, `last_expressions`), sin datos personales;
`config/caleno.toml` versionado. Los audios de audición se escriben fuera del repositorio (`MANUELITA_STATE_DIR`).

**Testing**:

- pytest:
  - `tests/unit/agent/test_style.py`: léxico, nivel, sugerencias, conteo, vetadas y «habla normal»;
  - `test_review_style.py`: checks nuevos;
  - `test_plan*.py`: campo `style`;
  - pruebas de prompts que verifican las secciones requeridas;
  - `tests/integration/agent/test_converse_style.py`: bloque `--style` en demo;
- `tests/unit/channels/test_voice*.py`: el guion hablado no excede dos expresiones;
- `agent converse --style --mode demo` en verde; `--mode real` para la medición.

**Target Platform**: el backend compartido (web y WhatsApp) y la voz local del PC servidor.

**Project Type**: servicio web con agente LangGraph.

**Performance Goals**: sin llamadas nuevas al modelo en el turno, salvo los reintentos del verificador (como hoy).
El juez de estilo solo corre en la evaluación real.

**Constraints**:

- perfil profesional: sin groserías ni voseo, y sin estilo en quejas, angustia y crisis;
- citas intactas (spec 018) y textos fijos sin cambios;
- no bajar la empatía ni la naturalidad publicadas (regla 21);
- licencia de las voces CC BY-NC 4.0 (uso académico, ya aceptada).

**Scale/Scope**: todas las respuestas en español del agente (conversación, respuestas con búsqueda y voz). Quedan
fuera las tareas de la Fase 1 (`/api/ask`, `/api/summary`, `/api/faq`) y los textos fijos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §3.5 Prompts versionados y registrados | ✅ con tarea | `converse.md` 1.2, `agent.md` 1.11, `voice_script.md` 1.1 y `style_judge.md` 1.0 se registran en `docs/prompt_log.md` §3.30. |
| IV. Generación anclada y citas | ✅ | Las expresiones son adornos sin hechos; el verificador impide que toquen cifras y citas (SC-008). |
| V. Evaluación empírica | ✅ con tarea | Conjunto `caleno.jsonl`, evaluación demo y real, y prueba humana (SC-007). |
| Regla 21 Evaluaciones publicadas no bajan | ✅ con tarea | Regresión en modo real de la evaluación de conversación; si baja, no se cierra la spec. |
| Regla 22 Conversación natural | ✅ | El estilo suma identidad; sin comandos. La persona puede pedir hablar «normal». |
| §10 Ética y privacidad | ✅ | Sin estereotipos ni burlas (lista vetada); la declaración de IA no cambia; voces con licencia académica. |
| VII. Simplicidad | ✅ | Léxico en TOML más un módulo; sin cambiar de modelo ni de motor de voz. |
| §4.3 Proceso | ✅ | Spec Kit completo; aviso a Roberto (cambio compartido con la web). |
| Cambios de arquitectura → CONSTITUTION.md | ✅ sin enmienda | Ajuste de estilo dentro del agente; sin cambio de arquitectura ni de tecnología. |

**Resultado**: pasa sin enmiendas.
**Re-check post-design**: igual. ✅ La voz se elige dentro del catálogo actual (sin tecnología nueva).

## Project Structure

### Documentation (this feature)

```text
specs/036-acento-caleno-valeria/
├── plan.md
├── research.md        # R1–R8
├── data-model.md
├── quickstart.md
├── contracts/
│   └── style-rules.md # léxico, nivel, plan, prompts, verificador, voz y evaluación
├── checklists/requirements.md
└── tasks.md           # /speckit-tasks
```

### Source Code (repository root)

```text
config/caleno.toml                     # nuevo: léxico aprobado, vetado, límites y «habla normal»
config/voice.toml                      # voz elegida en la audición (si cambia)
prompts/converse.md                    # 1.2: estilo caleño con <estilo>
prompts/agent.md                       # 1.11: estilo caleño en respuestas con búsqueda
prompts/voice_script.md                # 1.1: hasta dos expresiones habladas y ritmo caleño
prompts/style_judge.md                 # nuevo 1.0: juez de claridad y profesionalismo
src/proyecto_modelos_lenguaje/agent/
├── style.py                           # nuevo: léxico, nivel, sugerencias, conteo, vetadas
├── plan.py                            # TurnPlan.style; render
├── graph.py                           # bloque <estilo> en converse y en la respuesta con búsqueda
├── care.py                            # memoria: style_opt_out, last_expressions
├── review.py                          # checks style_*; vetadas también en RETRIEVAL_CHECKS
├── demo.py                            # expresión del bloque en el modelo guionado
├── converse_eval.py                   # comprobaciones de estilo y bloque --style
└── __main__.py                        # agent converse --style
src/proyecto_modelos_lenguaje/channels/voice.py   # <estilo> hablado al guion
src/proyecto_modelos_lenguaje/channels/greeting.py # una variante de presentación con «ve»
src/proyecto_modelos_lenguaje/voice/   # --audition (voces candidatas y expresiones habladas)
tests/fixtures/converse/caleno.jsonl   # conjunto de verificación
tests/unit/agent/..., tests/integration/agent/..., tests/unit/channels/...
openclaw/workspace/AGENTS.md           # modo degradado: regla breve de estilo
docs/prompt_log.md (§3.30), docs/manual_whatsapp.md, docs/evaluacion_caleno.*
```

**Structure Decision**: el estilo vive en el agente compartido, sobre el plan del turno (spec 020). El verificador
es la garantía. El canal solo pasa el bloque de estilo al guion hablado. El enrutador, el corpus y los textos fijos
no cambian.

## Complexity Tracking

Sin violaciones que justificar.
