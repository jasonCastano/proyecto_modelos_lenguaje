# Tasks: Conversación enfocada en Manuelita, con empatía y sin abrir charla ajena

**Input**: Design documents from `specs/035-enfoque-manuelita-conversacion/`
**Prerequisites**: plan.md, spec.md, research.md (R1–R7), data-model.md, contracts/focus-rules.md, quickstart.md

**Tests**: incluidas. La spec exige un conjunto de verificación (FR-012) y el plan pide pruebas del plan, del
verificador y de la evaluación; la DoD exige `make check` en verde.

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–034).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivo distinto, sin dependencias pendientes)
- **[Story]**: historia de usuario de la spec (US1–US4)

## Path Conventions

Proyecto único: `src/proyecto_modelos_lenguaje/agent/`, `prompts/`, `tests/`, `docs/` y `openclaw/` en la raíz del
repositorio.

**Privacidad**: la transcripción de la prueba va seudonimizada (sin nombre ni número de teléfono); el equipo de
fútbol se reemplaza por «mi equipo».

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: conjunto de verificación y temas sugeridos.

- [X] T001 Crear `tests/fixtures/converse/focus.jsonl` con 16 conversaciones en el formato de `tests/fixtures/converse/conversations.jsonl`:
  - **f01**: la transcripción del 2026-11-27, seudonimizada: «Hola» → «Bien, ¿y tú?» → «Charlemos un rato» →
    «Hoy fui a un partido de fútbol, ¿puedes creerlo?» → «Me fue muy bien, pero mi equipo no ganó» →
    «Mi equipo quedó eliminado, ¿quieres saber cuál es?» → «Quiero compartirlo contigo: soy hincha de mi
    equipo».
  - **Variantes**:
    - «charlemos de cualquier cosa» y «hablemos de otra cosa que no sea Manuelita»;
    - el día de la persona, cine, clima, viajes y comida;
    - insistencia de 5 turnos en fútbol;
    - inglés («let's just chat», «I went to a game today»);
    - mensaje mixto («fui al partido, ¿Manuelita apoya el deporte?»);
    - comentario social breve («qué calor hoy»);
    - «¿eres una persona?» seguido de un tema ajeno;
    - angustia («tuve un día terrible, me siento muy mal»);
    - agradecimiento y despedida.
  - **Claves `expect` por turno ajeno**: `no_offtopic_question`, `no_chat_invite`, `redirects`, `no_rejection`,
    `no_closing_repeat`, y `max_sentences: 2` desde el tercer turno ajeno seguido.
  - **Turnos de angustia, agradecimiento y despedida**: solo las claves que ya existen.
- [X] T002 [P] Agregar a `prompts/care.md` la sección `## offer.topics` con 6–8 líneas `clave | texto`:
  - `historia`, `productos`, `energia`, `fundacion`, `paises`, `sostenibilidad`, `diversificacion`;
  - los textos solo usan hechos ya presentes en los puentes o en la presentación (sin cifras nuevas);
  - verificar que `agent/care.py` (carga del playbook) acepta la sección o extender el parser, con una prueba en
    `tests/unit/agent/test_care*.py`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: memoria de racha y temas, y campos del plan. Todas las historias dependen de esta fase.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T003 [P] Pruebas en `tests/unit/agent/test_plan_focus.py` (nuevo):
  - `needs_redirect(act, turn, assent_to_offer)` es verdadero para `smalltalk`, `off_topic`, `minimal` sin
    asentimiento y `greeting` desde el turno 2; falso para `thanks`, `closing`, `about_assistant`, `complaint`,
    `clarify`, `manuelita` y el `greeting` del turno 1;
  - `build_plan` fija `redirect`, `streak` y `topics`;
  - desde `streak >= 3`, la longitud es `short` y `render()` incluye «máximo dos frases»;
  - `render()` incluye «regreso a Manuelita: obligatorio», «preguntas: solo sobre Manuelita» y «temas
    sugeridos: …» cuando no hay puente.
- [X] T004 [P] Pruebas en `tests/unit/agent/test_care_focus.py` (nuevo):
  - `update_conversation` suma `offtopic_streak` en los actos de enfoque y lo pone en 0 con `manuelita`,
    `clarify`, `about_assistant`, `thanks` y `closing`;
  - `offered_topics` acumula sin duplicar, con máximo 8 elementos, y se reinicia al agotarse;
  - `pick_topics(playbook, offered, k=3)` devuelve temas no ofrecidos y rota.
- [X] T005 Implementar en `src/proyecto_modelos_lenguaje/agent/care.py`:
  - los campos `offtopic_streak` y `offered_topics` en la memoria de conversación (data-model), con valores por
    defecto compatibles con hilos existentes;
  - `pick_topics`;
  - la lectura de `offer.topics` desde el playbook.
- [X] T006 Implementar en `src/proyecto_modelos_lenguaje/agent/plan.py`:
  - `FOCUS_ACTS` y `needs_redirect`;
  - en `TurnPlan`, los campos `redirect: bool = False`, `streak: int = 0` y `topics: tuple[str, ...] = ()`,
    serializados en `to_state`/`from_state`;
  - en `build_plan`, que reciba la racha y los temas y aplique la longitud `short` desde la racha 3;
  - en `render()`, las líneas del data-model.

**Checkpoint**: el plan sabe cuándo exigir el regreso a Manuelita.

---

## Phase 3: User Story 1 - Cortesía breve que lleva a Manuelita (Priority: P1) 🎯 MVP

**Goal**: «Bien, ¿y tú?» y los comentarios sociales reciben una frase de cortesía y temas concretos de
Manuelita, sin ofrecer charla libre.

**Independent Test**: el turno «Bien, ¿y tú?» de f01 en `converse --focus --mode demo` pasa `no_chat_invite`,
`redirects` y `no_offtopic_question`.

### Tests for User Story 1

- [X] T007 [P] [US1] Pruebas en `tests/unit/agent/test_review_focus.py` (nuevo), para `focus_issues` y los checks en `review()` con un plan de `redirect=True`:
  - `chat_invite` detecta «¿prefieres solo charlar un rato?», «charlar también se vale», «cuéntame qué has hecho
    hoy» y «¿qué tema te gustaría conversar?», y no marca «¿Te cuento sobre la Fundación Manuelita?»;
  - `no_redirect` marca una respuesta sin términos de Manuelita;
  - los checks no se aplican con `redirect=False`.
- [X] T008 [P] [US1] Prueba en `tests/unit/agent/test_converse_openings.py` (o el archivo de pruebas de `opening_hint`): con `plan.redirect=True`, `opening_hint` nunca devuelve la apertura «empieza con una pregunta corta que muestre interés…» ni «…una pregunta muy breve», para todas las semillas de 0 a 30

### Implementation for User Story 1

- [X] T009 [US1] En `src/proyecto_modelos_lenguaje/agent/review.py`:
  - `FOCUS_CHECKS`, `focus_issues(text, plan, recent_answers)`, `chat_invite` y `no_redirect`, con el léxico de
    Manuelita y los patrones de research R5 en español e inglés, sin tildes;
  - entrada en `NOTES` para cada check;
  - integración en `review()` solo cuando `plan.redirect`.
- [X] T010 [US1] En `src/proyecto_modelos_lenguaje/agent/graph.py`:
  - `opening_hint` filtra las aperturas en forma de pregunta cuando `plan.redirect`;
  - `_turn_plan` pasa a `build_plan` la racha y los temas desde la memoria (`care.pick_topics`) y guarda los
    ofrecidos.
- [X] T011 [US1] Actualizar `prompts/converse.md` a `prompt_version: 1.1`:
  - **nivel social**: una frase de cortesía o empatía y regreso a Manuelita, sin «acompaña con naturalidad»
    abierto;
  - **preguntas**: solo sobre Manuelita;
  - **estilo de `greeting`, `smalltalk` y `minimal`**: siempre terminan con el puente, un tema de los «temas
    sugeridos» del plan o dos o tres opciones;
  - **ejemplos**: se retira el que cerraba con «¡Espero que haya ganado tu equipo!»; se agregan ejemplos de
    estilo para «Bien, ¿y tú?» y «qué calor hoy».

  Mantener las secciones que lee `load_converse`.

**Checkpoint**: US1 lista en pruebas y en demo.

---

## Phase 4: User Story 2 - La persona pide charlar de cualquier cosa (Priority: P1)

**Goal**: «Charlemos un rato» recibe el propósito de Valer-IA y temas de Manuelita, sin aceptar la charla libre.

**Independent Test**: los turnos «Charlemos un rato» y «hablemos de otra cosa» del conjunto pasan
`no_chat_invite`, `redirects` y `no_offtopic_question`.

### Tests for User Story 2

- [X] T012 [P] [US2] Pruebas en `tests/unit/agent/test_review_focus.py`: las respuestas «Claro que sí, charlemos de lo que quieras» y «Claro, cuéntame de qué quieres hablar» se marcan (`chat_invite`); «Me encanta conversar contigo; lo mío es Manuelita: ¿te cuento de su historia o de su fundación?» pasa

### Implementation for User Story 2

- [X] T013 [US2] En `prompts/converse.md` 1.1: regla explícita para la propuesta de charla (acoger la intención, decir su propósito en una frase y ofrecer dos o tres temas) y un ejemplo de estilo para «Charlemos un rato» y otro en inglés para «let's just chat». Revisar en `src/proyecto_modelos_lenguaje/agent/demo.py` las respuestas guionadas del modelo demo para `smalltalk` y `off_topic`: no deben invitar a charlar y deben terminar en Manuelita, para que la evaluación demo sea representativa

**Checkpoint**: US1 y US2 completas.

---

## Phase 5: User Story 3 - Historias personales y temas ajenos (Priority: P1)

**Goal**: ante historias personales, empatía en una frase, ninguna pregunta sobre el tema y regreso a Manuelita
(con puente cuando existe), sin rechazar a la persona.

**Independent Test**: los turnos de fútbol de f01 pasan `no_offtopic_question`, `redirects` y `no_rejection`, y al
menos uno usa el puente de deportes (Fundación Manuelita) con su etiqueta.

### Tests for User Story 3

- [X] T014 [P] [US3] Pruebas en `tests/unit/agent/test_review_focus.py`:
  - `offtopic_question` marca «¿Cómo te fue en el partido?», «¿Y qué sigue para tu equipo?» y «How was the
    game?», y no marca «¿Quieres que te cuente qué hace la Fundación Manuelita?»;
  - `rejection` marca «Mejor no me cuentes cuál es» y «no me interesa», y no marca «Gracias por contármelo».
- [X] T015 [P] [US3] Prueba en `tests/unit/agent/test_bridges*.py`: con racha 1 (primer turno ajeno) y un puente disponible, `eligible` lo permite aunque `bridge_every=2`; en turnos siguientes conserva la cadencia

### Implementation for User Story 3

- [X] T016 [US3] En `src/proyecto_modelos_lenguaje/agent/review.py`: los checks `offtopic_question` y `rejection` (research R5). En `src/proyecto_modelos_lenguaje/agent/bridges.py`: `eligible` acepta `streak` y permite el puente en el primer turno ajeno.
- [X] T017 [US3] En `prompts/converse.md` 1.1:
  - historia personal: empatía en una frase, sin preguntas sobre el tema, sin opinar y regreso a Manuelita;
  - recibir con amabilidad lo que la persona comparte, sin «mejor no me cuentes»;
  - ejemplos de estilo para «fui a un partido» y «mi equipo no ganó» (con puente).

**Checkpoint**: US1–US3 completas: la conversación de la prueba se corrige.

---

## Phase 6: User Story 4 - Insistencia: asertiva, variada y sin repetirse (Priority: P2)

**Goal**: desde el tercer turno ajeno seguido, como máximo dos frases; ningún cierre repetido.

**Independent Test**: la conversación de insistencia de 5 turnos pasa `max_sentences: 2` desde el tercer turno y
`no_closing_repeat` en todos.

### Tests for User Story 4

- [X] T018 [P] [US4] Pruebas en `tests/unit/agent/test_review_focus.py`:
  - `closing_repeat` marca una respuesta cuya última oración es «Lo mío es la información pública de Manuelita,
    por si algo de eso te sirve.» cuando una anterior termina igual;
  - no marca cierres distintos.

  Y en `test_plan_focus.py`: con la racha 3, `render()` exige «máximo dos frases».

### Implementation for User Story 4

- [X] T019 [US4] En `src/proyecto_modelos_lenguaje/agent/review.py`:
  - el check `closing_repeat`, que compara la última oración con las de `recent_answers` (similitud > 0,8);
  - `max_sentences` desde el plan cuando `streak >= 3`, usando el conteo de oraciones existente.

  En `prompts/converse.md` 1.1: la regla de insistencia (más breve, cordial, temas distintos cada vez).

**Checkpoint**: las cuatro historias pasan las pruebas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T020 En `src/proyecto_modelos_lenguaje/agent/converse_eval.py`:
  - `check_turn` soporta `no_offtopic_question`, `no_chat_invite`, `redirects`, `no_rejection` y
    `no_closing_repeat`, reutilizando las funciones de `review.py` sobre la respuesta registrada;
  - un bloque `--focus` en el CLI `agent converse` (`src/proyecto_modelos_lenguaje/agent/__main__.py`) que corre
    `focus.jsonl` y escribe `docs/evaluacion_enfoque.md` y `.json`: totales por check, juez de empatía y turnos
    marcados, sin datos personales.

  Pruebas en `tests/unit/agent/test_converse_eval.py` con las claves nuevas y el bloque en modo demo.
- [X] T021 Ejecutar `uv run python -m proyecto_modelos_lenguaje.agent converse --focus --mode demo`; corregir prompts, plan o verificador hasta 0 turnos marcados
- [X] T022 [P] Agregar en `openclaw/workspace/AGENTS.md` la regla de enfoque para el modo degradado: cortesía en una frase, sin preguntas sobre temas ajenos y siempre de vuelta a Manuelita
- [X] T023 [P] Registrar en `docs/prompt_log.md` §3.29: `converse.md` 1.1 (SHA-256 de 12 caracteres), `care.md` (`offer.topics`), motivo (prueba del 2026-11-27, seudonimizada), los checks nuevos y la medición. Actualizar `docs/manual_whatsapp.md`: Valer-IA conversa con calidez y siempre vuelve a Manuelita
- [ ] T024 Medición en modo real (con instrucciones previas al usuario, porque usa DeepSeek):
  - `agent converse --focus --mode real`, con SC-001 a SC-005;
  - regresión con `agent converse --mode real` frente a `docs/evaluacion_conversacion.json` (SC-006: la empatía
    y la naturalidad no bajan; regla 21).

  Registrar los resultados en `docs/evaluacion_enfoque.md` y en las notas. Si algo baja, ajustar y repetir antes de
  cerrar.
- [X] T025 Ejecutar `make check`; corregir hasta verde
- [ ] T026 Prueba en el teléfono (quickstart §3). Antes de ejecutar, dar al usuario instrucciones paso a paso: reiniciar el backend y repetir la conversación de la prueba. Registrar el resultado y redactar el aviso para Roberto (cambio compartido con la web).
- [ ] T027 Marcar las tareas completadas con [X] y agregar notas de implementación al final de este archivo

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: T001 y T002 son libres.
- **Foundational**: T005 depende de T002; T006 depende de T005. Bloquea las historias.
- **US1**: depende de la fase 2; T011 después de T009 y T010, para comprobar con pruebas.
- **US2, US3 y US4**: dependen de US1 (`review.py` y `converse.md` compartidos); se hacen en orden.
- **Polish**: T020 depende de T009, T016 y T019; T021, T024, T025 y T026 van al final.

### User Story Dependencies

- US1 es el MVP: cierra la puerta por donde se abrió la charla.
- US2 y US3 completan la corrección de la prueba.
- US4 agrega la insistencia.

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- `review.py` y `plan.py` van antes que el prompt, para medir el efecto del prompt con el verificador ya activo.

### Parallel Opportunities

- T001 ∥ T002.
- T003 ∥ T004.
- T007 ∥ T008.
- T014 ∥ T015.
- T022 ∥ T023.

---

## Parallel Example: User Story 1

```text
# Pruebas primero (fallan):
T007 tests/unit/agent/test_review_focus.py (chat_invite, no_redirect)
T008 tests/unit/agent/test_converse_openings.py (sin aperturas en forma de pregunta)

# Luego, en orden:
T009 agent/review.py → T010 agent/graph.py → T011 prompts/converse.md 1.1
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1 y 2.
2. US1: verificador (`chat_invite`, `no_redirect`), aperturas sin preguntas y prompt 1.1.
3. Validar con `converse --focus --mode demo`.

### Incremental Delivery

1. US1 → US2 → US3: la conversación de la prueba queda corregida.
2. US4: insistencia.
3. Evaluación, medición real, registro de prompts y prueba en el teléfono.

### Parallel Team Strategy

Trabajo secuencial en un solo portátil (restricción del proyecto). [P] solo indica que el orden entre esas tareas es
libre.

---

## Notes

- La transcripción va seudonimizada: sin nombre, número ni equipo.
- Los temas sugeridos no traen cifras nuevas.
- Comentarios y docstrings en español; identificadores en inglés; Ruff con `line-length = 100`.
- Commits, push y PR solo con autorización explícita de jasonCastano o Robertto48, sin `Co-authored-by`.

## Notas de implementación (2026-11-27)

- **Plan** (`agent/plan.py`): `needs_redirect(act, turn, assent_to_offer=False)` conserva la firma del contrato, pero
  `build_plan` ya no marca el asentimiento: el plan no ve el texto y no distingue «ok» de «jaja». Un acto `minimal`
  después de un puente también vuelve a Manuelita; aceptar el puente con contenido («sí, cuéntame») lo resuelve el
  router. `render(topic_texts)` muestra el texto de los temas sugeridos, no la clave.
- **Respaldo y streaming** (`agent/graph.py`): en la racha (`short`), el respaldo de `care.md` se recorta a dos frases
  y conserva la que vuelve a Manuelita (`_focus_fallback`). En la entrega por frases, `review_sentence` aplica
  `offtopic_question`, `chat_invite` y `rejection`; `no_redirect` y `closing_repeat` necesitan la respuesta completa.
  Si lo entregado no nombra a Manuelita, `_deliver_tail` cierra con `care.topics_offer`, salvo que una respuesta
  breve ya tenga dos frases. Los textos de
  `offer.topics` entran a la evidencia del verificador (`_topics_evidence`), para que «1864» no cuente como dato
  externo.
- **Demo** (`agent/demo.py`): con `plan.redirect` (salvo límites y consejos), la respuesta es una frase de cortesía
  más el puente («De Manuelita, …», «Te cuento algo de Manuelita: …») o la frase de temas. Se retiró «Me alegra que
  conversemos un rato».
- **Conjunto** (`focus.jsonl`): en f08 el tercer turno es «dime cuál es tu club de fútbol favorito», no «dime tu
  equipo favorito»: con «equipo» el router demo lo enviaba a búsqueda (equipo de Manuelita) y cortaba la racha.
- **Evaluación**: `agent converse --focus --mode demo` da 0 turnos marcados en `chain` y `agent` (tres corridas).
  `agent converse --mode demo` sigue con SC-005 y E-SC-004 en rojo por la nota de perfil «Te atiendo como
  Cliente B2B» en el turno simulado «llevo rato buscando cómo comprar azúcar al por mayor». Esa nota y ese turno ya
  están en `HEAD` y esta spec no los toca.
- **`make check`**: verde (2508 pytest, 216 vitest y build web). Una corrida previa se cayó con el *access
  violation* intermitente de HiGHS/scipy; la repetición pasó.
- **Pendiente**: T024 (medición con DeepSeek, con instrucciones previas), T026 (prueba en el teléfono y aviso a
  Roberto) y T027 al cerrar esas dos.
