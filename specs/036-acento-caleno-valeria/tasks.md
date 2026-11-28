# Tasks: Valer-IA con acento y expresiones caleñas, siempre profesional

**Input**: Design documents from `specs/036-acento-caleno-valeria/`
**Prerequisites**: plan.md, spec.md, research.md (R1–R8), data-model.md, contracts/style-rules.md, quickstart.md

**Tests**: incluidas. La spec exige un conjunto de verificación (FR-014) y el plan pide pruebas del léxico, del
nivel, del verificador, de la voz y de la evaluación. La DoD exige `make check` en verde.

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–035).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede ir en paralelo (archivo distinto, sin dependencias pendientes).
- **[Story]**: historia de usuario de la spec (US1–US4).

## Path Conventions

Proyecto único: `src/proyecto_modelos_lenguaje/`, `config/`, `prompts/`, `tests/`, `docs/` y `openclaw/` en la raíz
del repositorio.

**Reglas transversales**:

- tuteo, nunca voseo (P2: A);
- estilo en la web y en WhatsApp (P3: A);
- la voz se elige dentro del catálogo actual de Phonon (P1: A);
- sin datos personales en fixtures;
- los textos fijos de `conduct.md` no cambian.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: léxico versionado y conjunto de verificación.

- [X] T001 Crear `config/caleno.toml` con el esquema de data-model §1:
  - **`[style]`**: `enabled = true`, `max_written = 1`, `max_spoken = 2`, `suggestions = 3`, `memory = 3`, y las
    listas `opt_out` y `formal_markers` de data-model §1;
  - **`[[approved]]`**: las 12 expresiones de research R2, cada una con `text`, `meaning`, `levels` (⊆
    {`informal`, `neutral`, `formal`}), `spoken` y `example`, y `match = "interjection"` para «ve»;
  - **`[[banned]]`**: las vetadas de research R2 con su `reason`, incluidas todas las formas de voseo («vos»,
    «mirá», «sabés», «tenés», «oís»).

  Restricciones: al menos 8 aprobadas, al menos 3 con nivel `formal`, `text` único entre aprobadas y vetadas.
  Comentarios en español.
- [X] T002 [P] Crear `tests/fixtures/converse/caleno.jsonl` con 14 conversaciones en el formato de
  `tests/fixtures/converse/conversations.jsonl`.
  - **Conversaciones** (research R8):
    - c01 informal («qué más, ¿qué hace Manuelita?», «uy, qué bacano»);
    - c02 neutro («hola», «¿qué produce Manuelita?»);
    - c03 formal («Buenos días, quisiera información sobre su línea de productos para distribución»);
    - c04 queja;
    - c05 angustia;
    - c06 crisis (texto fijo);
    - c07 inglés;
    - c08 «¿qué significa "ve"?» después de una respuesta;
    - c09 «habla normal, por favor» y dos turnos más;
    - c10 respuesta con búsqueda y cita;
    - c11 conversación larga de 8 turnos;
    - c12 jerga y una grosería del visitante;
    - c13 un turno marcado con `"voice": true`;
    - c14 despedida.
  - **Claves `expect`**: `style_used` (solo en turnos informales o neutros), `no_banned` (en todos), `max_expressions`
    (1, o 2 en voz), `style_off` (queja, angustia, crisis, inglés y después de «habla normal»), `no_style_repeat` y
    `citations_kept` (en las respuestas con búsqueda).

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: módulo de estilo, plan y memoria. Todas las historias dependen de esta fase.

**⚠️ CRITICAL**: ninguna historia empieza antes de terminar esta fase.

- [X] T003 [P] Pruebas en `tests/unit/agent/test_style.py` (nuevo):
  - **`load_lexicon`**:
    - carga `config/caleno.toml`;
    - un archivo inválido (nivel desconocido, `text` duplicado, menos de 8 aprobadas) deja `enabled=False` sin
      lanzar error.
  - **`find_expressions`**:
    - encuentra «listo pues» y «a la orden» sin tildes ni mayúsculas;
    - cuenta «ve» solo como interjección («¡Ve, qué bueno!», «qué bueno, ve»), no en «ve a la página».
  - **`find_banned`**: detecta «parce», «mirá» y «vos».
  - **`wants_plain`**: verdadero para «habla normal, por favor» y «speak normally».
  - **`suggest`**:
    - devuelve expresiones del nivel, sin las recientes;
    - con `spoken=True` excluye `spoken = false`.
  - **`render_block`**:
    - devuelve `""` con `off`;
    - con `spoken=True` dice «como máximo dos».
- [X] T004 Implementar `src/proyecto_modelos_lenguaje/agent/style.py` según contracts §1 y §3:
  - `StyleLevel`, `Expression` y `Lexicon` (con `sha256` del archivo);
  - `load_lexicon` con `lru_cache` y validación;
  - `find_expressions`, `find_banned`, `wants_plain`, `suggest` y `render_block`.

  Detalles: coincidencia por palabra completa sobre `structured.normalize`. `level_for` se completa en T021.
- [X] T005 [P] Pruebas en `tests/unit/agent/test_plan_style.py` (nuevo) y en `tests/unit/agent/test_care_style.py`
  (nuevo):
  - `TurnPlan` serializa `style` (defecto `"off"`) y `style_hints` (defecto `()`) en `to_state`/`from_state`;
  - `update_conversation(..., expressions=[...], plain=True)` guarda como máximo `memory = 3` expresiones
    recientes y fija `style_opt_out = True` sin volver a `False`;
  - `copy_conversation(None)` trae los valores por defecto.
- [X] T006 Implementar en `src/proyecto_modelos_lenguaje/agent/plan.py` los campos `style: str = "off"` y
  `style_hints: tuple[str, ...] = ()`. Agregar los parámetros `style` y `style_hints` a `build_plan` y serializarlos.
- [X] T007 Implementar en `src/proyecto_modelos_lenguaje/agent/care.py`:
  - `style_opt_out: bool` y `last_expressions: list[str]` en `ConversationMemory`, `empty_conversation` y
    `copy_conversation`;
  - en `update_conversation`, los parámetros `expressions: Sequence[str] = ()` y `plain: bool = False`.

**Checkpoint**: el agente sabe qué expresiones sugerir y recuerda las usadas.

---

## Phase 3: User Story 1 - Respuestas escritas con sabor caleño y tono profesional (Priority: P1) 🎯 MVP

**Goal**: saludos, respuestas con datos y despedidas con como máximo una expresión caleña aprobada, variada, sin
vetadas y con las citas intactas.

**Independent Test**: c02, c10 y c14 en `agent converse --style --mode demo` cumplen estas claves: `style_used`
en al menos una respuesta, `no_banned`, `max_expressions`, `no_style_repeat` y `citations_kept`.

### Tests for User Story 1

- [X] T008 [P] [US1] Pruebas en `tests/unit/agent/test_review_style.py` (nuevo), con un plan de `style="neutral"`:
  - **`style_banned`**: «Listo, parce, te cuento» y «Mirá, te cuento»;
  - **`style_excess`**: «¡Ve, qué bueno! Listo pues, te cuento.»;
  - **`style_repeat`**: «Listo pues…» cuando `last_expressions` trae «listo pues»;
  - **`style_off`**: «A la orden» con `style="off"`;
  - **en las respuestas con búsqueda**: `RETRIEVAL_CHECKS` quita la frase con «parce» y conserva las citas;
  - **lo que pasa**: «Con mucho gusto te cuento: Manuelita produce azúcar [U1].»;
  - **`NOTES`**: hay una nota por check.
- [X] T009 [P] [US1] Prueba en `tests/unit/agent/test_prompts*.py` (o el archivo de pruebas de prompts existente):
  `converse.md` es 1.2 y `agent.md` es 1.11, y ambos tienen la sección «Estilo caleño» y siguen cargando con
  `load_converse` y `load_agent_prompt`.

### Implementation for User Story 1

- [X] T010 [US1] En `src/proyecto_modelos_lenguaje/agent/review.py`:
  - `STYLE_CHECKS` y `style_issues(text, plan, recent_expressions, *, spoken=False)` (contracts §5), con las
    funciones de `style.py`;
  - integrarlos en `review()` cuando hay plan;
  - sumar `style_banned` y `style_off` a `RETRIEVAL_CHECKS` y a `LOCAL_CHECKS` (por frase);
  - notas en `NOTES`;
  - extender `ReviewIssue`.
- [X] T011 [US1] En `src/proyecto_modelos_lenguaje/agent/graph.py`:
  - **`_turn_plan`**: calcula el nivel con `style.level_for` y las sugerencias con `style.suggest`, usando la
    semilla del hilo y del turno y `memory["last_expressions"]`, y los pasa a `build_plan`;
  - **bloque `<estilo>`**: `_converse_messages`, `_answer_node` y `_answer_by_sentences` agregan
    `style.render_block(...)` después del plan;
  - **revisión**: pasa `memory["last_expressions"]` como `recent_expressions`;
  - **memoria**: `update_conversation` recibe `expressions=style.find_expressions(answer)` y
    `plain=style.wants_plain(question)`.
- [X] T012 [US1] Actualizar `prompts/converse.md` a `prompt_version: 1.2`. Agregar la sección «Estilo caleño»:
  - obedece `<estilo>` y usa como máximo una expresión, solo si encaja, al inicio o al cierre;
  - tuteo, nunca voseo;
  - sin `<estilo>`, español neutro.

  Agregar ejemplos de estilo para un saludo («¡Hola, ve! Qué gusto…»), un tema ajeno con regreso a Manuelita
  (spec 035) y una despedida («Listo pues, que te vaya muy bien»). Mantener las secciones que lee `load_converse`.
- [X] T013 [US1] Actualizar `prompts/agent.md` a `prompt_version: 1.11` con la misma sección «Estilo caleño» para
  las respuestas con búsqueda:
  - la expresión nunca va dentro de una cifra, una cita `[U#]`/`[F#]` ni un nombre;
  - la respuesta debe tener todo su contenido aunque se quite la expresión.
- [X] T014 [US1] En `src/proyecto_modelos_lenguaje/agent/demo.py`:
  - **conversación**: con `plan.style` distinto de `off`, el modelo guionado antepone o pospone una expresión de
    `plan.style_hints` (rotando con la semilla) en una de cada dos respuestas aproximadamente;
  - **búsqueda**: las respuestas con búsqueda del modo demo hacen lo mismo al inicio, sin tocar las citas.
- [X] T015 [P] [US1] En `src/proyecto_modelos_lenguaje/channels/greeting.py`:
  - agregar una variante de presentación en español con «ve» («¡Hola{name}, ve! Soy Valer-IA…»), como máximo una
    expresión;
  - prueba en `tests/unit/channels/test_greeting*.py`: ninguna variante usa vetadas ni más de una expresión.

**Checkpoint**: US1 lista en pruebas y en demo.

---

## Phase 4: User Story 2 - Notas de voz que suenan caleñas (Priority: P1)

**Goal**: el guion hablado usa hasta dos expresiones de la lista hablada, con ritmo caleño, y suena con la voz
latinoamericana más cercana elegida por audición.

**Independent Test**: el turno con `"voice": true` de c13 genera un guion con `max_expressions` 2 y `no_banned`. La
audición produce los WAV y el índice.

### Tests for User Story 2

- [X] T016 [P] [US2] Pruebas en `tests/unit/channels/test_voice.py`:
  - **prompt**: el prompt del guion recibe el bloque `<estilo>` hablado («como máximo dos»);
  - **exceso**: un guion falso con tres expresiones se regenera una vez y, si sigue mal, se quitan las frases
    excedentes;
  - **vetadas**: un guion con «parce» no se sintetiza con esa frase;
  - **inglés**: el bloque está vacío.
- [X] T017 [P] [US2] Prueba en `tests/unit/voice/test_audition.py` (nuevo) con el motor `fake`: `--audition --out
  <tmp>` escribe un WAV por voz candidata y por expresión hablada, más `index.txt`, y termina con 0. Sin modelo ni
  token, termina con 2 y un mensaje claro.

### Implementation for User Story 2

- [X] T018 [US2] Actualizar `prompts/voice_script.md` a `prompt_version: 1.1`:
  - regla de estilo hablado: obedece `<estilo>`, hasta dos expresiones de la lista, frases cortas y cálidas, tuteo
    sin voseo;
  - sin `<estilo>`, español neutro.

  Mantener las reglas de cifras y citas.
- [X] T019 [US2] En `src/proyecto_modelos_lenguaje/channels/voice.py`:
  - calcular el nivel del turno (el del plan registrado o `style.level_for` con el mensaje);
  - pasar `style.render_block(level, style.suggest(..., spoken=True), spoken=True)` al prompt;
  - validar el guion con `style_issues(..., spoken=True)`: una regeneración y luego quitar las frases con
    expresiones vetadas o excedentes.
- [X] T020 [US2] Agregar `--audition [--out DIR]` al CLI de `src/proyecto_modelos_lenguaje/voice/` (contracts §6):
  - **voces candidatas**: Rebeca, Regina, Ximena, Celia, Alicia, Danae, Azucena, Jimena y Yael (research R6);
  - **frase de prueba**: «¡Hola, ve! Soy Valer-IA, la asistente virtual de Manuelita. Listo pues, te cuento de su
    historia.»;
  - **expresiones**: una muestra por cada expresión con `spoken = true`;
  - **salida**: `MANUELITA_STATE_DIR/voice_audition/` (fuera del repositorio) con `index.txt` (voz o expresión →
    archivo).

**Checkpoint**: la voz tiene estilo; la audición queda lista para el usuario (T038).

---

## Phase 5: User Story 3 - El perfil profesional nunca se pierde (Priority: P1)

**Goal**: sin expresiones en quejas, angustia, crisis ni inglés; solo cortesías suaves con el registro formal;
textos fijos sin cambios.

**Independent Test**: c03, c04, c05, c06 y c12 cumplen `style_off`, `no_banned` y `max_expressions`, y la respuesta
formal solo usa expresiones con nivel `formal`.

### Tests for User Story 3

- [X] T021 [P] [US3] Pruebas en `tests/unit/agent/test_style.py` para la matriz de `level_for` (data-model §2):
  - **`off`**: inglés, `frustrated`, `angry`, `distressed`, acto `complaint`, razón `crisis` y `style_opt_out`;
  - **`formal`**: «Buenos días, quisiera información»;
  - **`informal`**: «qué más, ve» y «uy, qué bacano»;
  - **`neutral`**: «¿Qué produce Manuelita?»;
  - **en formal**: `suggest` solo devuelve expresiones con nivel `formal`.
- [X] T022 [P] [US3] Prueba en `tests/unit/agent/test_review_style.py`:
  - **textos fijos**: ninguno de `conduct.md` ni los respaldos de `care.md` contiene expresiones aprobadas o vetadas;
  - **SHA**: el SHA de `conduct.md` no cambia (comparar con el valor registrado en el prompt log).

### Implementation for User Story 3

- [X] T023 [US3] Completar `style.level_for(plan, memory, message)` en
  `src/proyecto_modelos_lenguaje/agent/style.py` según research R3. Detalle: marcas formales de
  `formal_markers` y el registro de `plan.register`.
- [X] T024 [US3] En `src/proyecto_modelos_lenguaje/agent/plan.py`:
  - ampliar `INFORMAL` con marcas caleñas («ve», «oís», «qué más pues», «pues sí»), sin romper las pruebas de
    registro existentes;
  - cambiar «parce» en los ejemplos o comentarios donde se presente como caleño.

**Checkpoint**: US1–US3 completas: estilo con medida y perfil profesional.

---

## Phase 6: User Story 4 - La persona que no es de Cali entiende todo (Priority: P2)

**Goal**: la expresión es un adorno; se explica si la preguntan; «habla normal» la apaga en el hilo; en inglés no
hay estilo.

**Independent Test**: c07, c08 y c09 cumplen `style_off` (inglés y después de «habla normal»). La respuesta a «¿qué
significa "ve"?» contiene el significado del léxico y vuelve a Manuelita.

### Tests for User Story 4

- [X] T025 [P] [US4] Pruebas en `tests/unit/agent/test_style.py`:
  - **glosario**: `render_block(..., glossary=["ve"])` incluye «ve = llamado de atención afectuoso…»;
  - **«habla normal»**: después de `wants_plain`, `level_for` devuelve `off` en los turnos siguientes del hilo.
- [X] T026 [P] [US4] Prueba de integración en `tests/integration/agent/test_converse_style.py` (nuevo) en demo:
  - «habla normal, por favor» y luego «¿qué produce Manuelita?»: ninguna de las dos respuestas tiene expresiones;
  - «hola» y luego «¿qué significa "ve"?»: la segunda respuesta menciona el significado y a Manuelita.

### Implementation for User Story 4

- [X] T027 [US4] En `src/proyecto_modelos_lenguaje/agent/graph.py` y `style.py`:
  - **glosario**: el bloque `<estilo>` trae el significado de las expresiones de `last_expressions`, o de la que
    nombre el mensaje;
  - **«habla normal»**: el turno con `wants_plain` lleva en el plan la línea «el visitante pidió hablar sin
    modismos: confírmalo en media frase» y queda con nivel `off`.
- [X] T028 [US4] En `prompts/converse.md` 1.2:
  - regla para explicar una expresión en una frase con el glosario y volver a Manuelita;
  - regla para confirmar «habla normal» sin expresiones.

  En inglés no hay bloque, así que el español neutro y el inglés no cambian.
- [X] T029 [US4] En `src/proyecto_modelos_lenguaje/agent/demo.py`:
  - una pregunta por una expresión recibe la explicación con el glosario del bloque y un regreso a Manuelita;
  - «habla normal» recibe una confirmación sin expresiones.

**Checkpoint**: las cuatro historias pasan las pruebas.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T030 En `src/proyecto_modelos_lenguaje/agent/converse_eval.py` y en `src/proyecto_modelos_lenguaje/agent/__main__.py`:
  - **claves de `check_turn`**:
    - `style_used`, `no_banned`, `max_expressions`, `style_off` y `no_style_repeat`, con las funciones de
      `style.py`;
    - `citations_kept`: las etiquetas de la respuesta están en sus citas;
  - **voz**: los turnos con `"voice": true` evalúan además el guion hablado generado con el modelo del modo;
  - **`run_style`**: corre `caleno.jsonl` y calcula SC-001 a SC-005 y SC-008;
  - **bloque `--style`** en `agent converse`, que escribe `docs/evaluacion_caleno.{md,json}` con totales, porcentaje
    de uso, expresiones más usadas, turnos marcados y la sección de prueba humana vacía, sin datos personales;
  - **pruebas** en `tests/integration/agent/test_converse_style.py`.
- [X] T031 Crear `prompts/style_judge.md` 1.0. Califica `clarity` y `professionalism` de 1 a 5 por respuesta y
  devuelve JSON con `turns`. En `converse_eval.py`, el modo real lo usa (SC-006) y el demo usa una heurística
  determinista. Agregar `style_judge` a la carga de prompts si hace falta (`agent/prompts.py`).
- [X] T032 Ejecutar `uv run python -m proyecto_modelos_lenguaje.agent converse --style --mode demo`. Corregir el
  léxico, los prompts, la demo o el verificador hasta cumplir las metas. Correr también `--focus --mode demo` para
  verificar la regresión de la spec 035 (0 turnos marcados).
- [X] T033 [P] Agregar en `openclaw/workspace/AGENTS.md` la regla de estilo del modo degradado:
  - tuteo con, como máximo, una expresión caleña aprobada;
  - sin voseo ni modismos de otras regiones;
  - sin estilo en quejas, angustia, crisis o inglés.
- [X] T034 [P] Registrar en `docs/prompt_log.md` §3.30:
  - `converse.md` 1.2, `agent.md` 1.11, `voice_script.md` 1.1 y `style_judge.md` 1.0, cada uno con su SHA-256 de 12
    caracteres del archivo;
  - `config/caleno.toml` (SHA);
  - la voz elegida;
  - el motivo y la medición.
- [X] T035 [P] Actualizar `docs/manual_whatsapp.md`: Valer-IA habla con sabor caleño y profesional, y se le puede
  pedir «habla normal». Actualizar también la nota de voz y la tabla de ejemplos.
- [ ] T036 Medición en modo real, con instrucciones previas al usuario porque usa DeepSeek:
  - `agent converse --style --mode real` (SC-001 a SC-006 y SC-008);
  - `agent converse --mode real` frente a `docs/evaluacion_conversacion.json` (regla 21: la empatía y la naturalidad
    no bajan);
  - `agent converse --focus --mode real` (la spec 035 no retrocede).

  Registrar en `docs/evaluacion_caleno.md` y en las notas. Si algo baja, ajustar y repetir.
- [X] T037 Ejecutar `make check`; corregir hasta verde.
- [ ] T038 Audición de voces (manual; antes de ejecutar, dar al usuario instrucciones paso a paso):
  1. correr `voice --audition`;
  2. el usuario escucha y elige la voz, y marca las expresiones mal pronunciadas;
  3. actualizar `config/voice.toml` y `config/caleno.toml` (`spoken = false`);
  4. registrar la elección en `docs/prompt_log.md` §3.30.
- [ ] T039 Prueba en el teléfono y en la web (quickstart §4), con instrucciones previas paso a paso:
  - reiniciar el backend;
  - conversación de 8 mensajes;
  - calificación de una persona de Cali sobre 5 respuestas (SC-007), registrada en `docs/evaluacion_caleno.md`.

  Redactar el aviso para Roberto (cambio compartido con la web).
- [ ] T040 Marcar las tareas completadas con [X] y agregar notas de implementación al final de este archivo.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup**: T001 y T002 son libres.
- **Foundational**:
  - T004 depende de T001;
  - T006 y T007 son independientes entre sí.

  Bloquea las historias.
- **US1**: depende de la fase 2; T010 antes que T011; T012 y T013 después de T011.
- **US2**: depende de T004 y T010 (`style_issues`); T020 es independiente del resto de US2.
- **US3**: depende de T004; T023 alimenta a US1 y US2 en la ejecución real (antes de T023, `level_for` devuelve
  `neutral` o `off` según el idioma).
- **US4**: depende de US1 (graph y prompt).
- **Polish**: T030 depende de US1–US4; T032, T036, T037, T038 y T039 van al final, en ese orden.

### User Story Dependencies

- US1 es el MVP: Valer-IA escribe con sabor caleño y medido.
- US3 es el control de calidad del perfil profesional; se puede hacer antes que US2.
- US2 lleva el estilo a la voz.
- US4 agrega la claridad y la salida «habla normal».

### Within Each User Story

- Las pruebas se escriben primero y deben fallar.
- `style.py`, `review.py` y `plan.py` van antes que los prompts, para medir el efecto del prompt con el verificador
  ya activo.

### Parallel Opportunities

- T001 ∥ T002.
- T003 ∥ T005.
- T008 ∥ T009.
- T015 ∥ T016 ∥ T017.
- T021 ∥ T022.
- T025 ∥ T026.
- T033 ∥ T034 ∥ T035.

---

## Parallel Example: User Story 1

```text
# Pruebas primero (fallan):
T008 tests/unit/agent/test_review_style.py
T009 pruebas de prompts (converse 1.2, agent 1.11)

# Luego, en orden:
T010 agent/review.py → T011 agent/graph.py → T012 prompts/converse.md → T013 prompts/agent.md → T014 agent/demo.py
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Fases 1 y 2.
2. US1: verificador, bloque `<estilo>`, prompts y demo.
3. Validar con `converse --style --mode demo` (c02, c10 y c14).

### Incremental Delivery

1. US1 → US3: estilo escrito con perfil profesional.
2. US2: voz (guion y audición).
3. US4: claridad y «habla normal».
4. Evaluación, medición real, audición, registro de prompts y prueba en el teléfono y la web.

### Parallel Team Strategy

Trabajo secuencial en un solo portátil (restricción del proyecto). [P] solo indica que el orden entre esas tareas es
libre.

---

## Notes

- Sin datos personales en `caleno.jsonl`.
- La lista aprobada y la vetada las revisa el equipo antes de cerrar la spec.
- Comentarios y docstrings en español; identificadores en inglés; Ruff con `line-length = 100`.
- Commits, push y PR solo con autorización explícita de jasonCastano o Robertto48, sin `Co-authored-by`.
- Aviso a Roberto: el cambio afecta la web (agente compartido).

## Notas de implementación (2026-11-28)

- **Léxico** (`config/caleno.toml`):
  - 12 aprobadas y 19 vetadas;
  - `match` por expresión: `phrase`, `interjection` («ve» solo como interjección, también entre comas), `closing`
    («pues» solo al cierre) y `voseo` (exige la tilde: «mirá», no «mira»);
  - campo `suggest = false` para «pues» y «sucursal del cielo» (permitidas, pero no se sugieren);
  - los textos se comparan sin tildes con `structured.normalize`.
- **Cortesías**: con el estilo apagado, «con mucho gusto» y «a la orden» (nivel formal) no se marcan como
  `style_off`: son español profesional común. La evaluación aplica el mismo criterio en `style_off`.
- **Nivel `off` por malestar**: el análisis de sentimiento dejaba «me siento muy mal» en `neutral`, así que
  `style.py` tiene un léxico propio (`LOW_MOOD`) que apaga el estilo; no cambia el sentimiento de la spec 019.
- **Enrutador** (`agent/router.py`): «¿qué significa "ve"?» y «habla normal» van por la conversación (acto
  `smalltalk`). Antes se buscaban en el corpus. Las preguntas que nombran a Manuelita no se desvían.
- **Voz**:
  - el nivel del turno viaja en la decisión de ruta (`route.style`, también en `api_models`, `web/src/lib/types.ts`
    y el JSON Schema `specs/014-rag-agent-memory-router/contracts/route-decision.schema.json`);
  - el canal lo pasa a `ChannelVoice.for_answer(style=…)`;
  - en la evaluación demo el guion es el respaldo determinista; en real, DeepSeek.
- **Presentación**: para conservar las 3 variantes por idioma (prueba de la spec 038), la segunda variante en
  español cambió a «¡Hola{name}, ve, qué gusto saludarte!» en lugar de agregar una cuarta.
- **Demo**: tres de cada cuatro respuestas con estilo llevan una expresión, integrada en la primera frase.
  `--style --mode demo` da 0 turnos marcados y un uso del 60 % al 90 % según la corrida; `--focus --mode demo` sigue
  en 0.
- **Evaluación general de conversación en demo**: sin cambios. Su falla SC-005 por «Te atiendo como Cliente B2B»
  es anterior a esta spec.
- **`make check`**: verde (2578 pytest, 216 vitest y build web).
- **Pendiente**:
  - T036: medición con DeepSeek, con instrucciones previas;
  - T038: audición de voces; el usuario elige la voz y marca las expresiones mal pronunciadas;
  - T039: prueba en el teléfono y la web, calificación de una persona de Cali y aviso a Roberto;
  - revisión de las listas aprobada y vetada por el equipo;
  - T040 al cerrar lo anterior.
