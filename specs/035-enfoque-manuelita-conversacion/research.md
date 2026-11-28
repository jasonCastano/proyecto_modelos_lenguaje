# Research: conversación enfocada en Manuelita (spec 035)

Fuentes:

- prompts: `prompts/converse.md` 1.0 (spec 020), `prompts/care.md` y `prompts/conduct.md` (spec 019);
- código del agente: `agent/plan.py` (`STRATEGIES`, `render`), `agent/graph.py` (`OPENINGS`, `opening_hint`,
  `_converse_messages`), `agent/bridges.py` (`eligible`, `bridge_every = 2`) y `agent/review.py` (verificador
  duro);
- evaluación: `agent/converse_eval.py` con `tests/fixtures/converse/conversations.jsonl`;
- la transcripción de la prueba del 2026-11-27.

## R1. Causas del comportamiento observado

1. **El prompt invita a la charla**:
   - el nivel 1 de `converse.md` pide «acompaña con naturalidad y responde a lo que dijo»;
   - el estilo permite «una pregunta de vuelta si ayuda a seguir la conversación»;
   - un ejemplo cierra con «¡Espero que haya ganado tu equipo!».

   El modelo lo interpretó como permiso para charlar y preguntar.
2. **Una apertura sugerida es una pregunta**: `OPENINGS` incluye «empieza con una pregunta corta que muestre
   interés». En turnos sociales empuja preguntas sobre el tema ajeno («¿Cómo te fue en el partido?»).
3. **El puente es intermitente y no hay redirección obligatoria**:
   - `bridge_every = 2` permite un puente como máximo cada dos turnos ajenos;
   - el plan no exige terminar en Manuelita cuando no hay puente;
   - la memoria pide «no vuelvas a ofrecer lo que ya ofreciste», así que el modelo cayó en la frase genérica «Lo
     mío es la información pública de Manuelita» y la repitió.
4. **El verificador no mira el enfoque**: `review.py` detecta cifras externas, promesas, opiniones, citas,
   respuestas parecidas y frases requeridas. No detecta preguntas sobre temas ajenos, invitaciones a charlar, falta
   de redirección, rechazo a la persona ni el cierre repetido.

## R2. Enfoque de la corrección

- **Decision**: corrección en tres capas, sin cambiar el enrutador ni la arquitectura.
  1. **Plan**:
     - en turnos `smalltalk` y `off_topic`, y en `greeting` después del primer turno, el plan exige redirección
       (`regreso a Manuelita: obligatorio`) y prohíbe preguntas ajenas;
     - lleva la cuenta de turnos ajenos seguidos (`racha`);
     - ofrece 2–3 **temas sugeridos** rotativos cuando no hay puente;
     - desde la racha 3, longitud «breve: máximo dos frases».
  2. **Prompt** `converse.md` 1.1:
     - nivel social acotado (una frase de cortesía o empatía y regreso a Manuelita);
     - preguntas solo sobre Manuelita;
     - regla para la propuesta de charla;
     - frases de rechazo prohibidas;
     - ejemplos nuevos basados en la prueba (seudonimizada), sin los que invitaban a seguir el tema ajeno.
  3. **Verificador duro** (`review.py`) con checks nuevos: `offtopic_question`, `chat_invite`, `no_redirect`,
     `rejection` y `closing_repeat`.
     - Si fallan, se reintenta con la nota del check, como hoy.
     - Si persiste, se usa el respaldo de `care.md`: reconocer, límite y puente u oferta de temas, que no tiene
       preguntas ajenas.
- **Rationale**:
  - el prompt solo no garantiza el 100 % (SC-001 a SC-004);
  - el verificador ya existe y tiene reintento y respaldo (spec 020);
  - el plan ya transporta las reglas por turno.
- **Alternatives considered**:
  - **Solo prompt**: insuficiente; es el estado actual.
  - **Respuesta fija sin modelo para todo lo ajeno**: pierde la empatía que el integrante valoró.
  - **Clasificar «charlemos» como acto nuevo**: no hace falta; el enrutador ya lo marca `smalltalk` u
    `off_topic`, y las reglas aplican a ambos.

## R3. Qué turnos llevan las reglas

- **Decision**: llevan las reglas los actos `smalltalk`, `off_topic`, `minimal` (cuando no es asentimiento a una
  oferta de Manuelita) y `greeting` desde el segundo turno.
  - **Sin cambio**: `thanks`, `closing`, `about_assistant` (ya ofrece temas), `complaint` (spec 019: empatía y
    ayuda concreta), `clarify` y `manuelita`.
  - **Angustia grave**: la respuesta de cuidado de la spec 019 tiene prioridad y no se acorta.
- **Rationale**: FR-010 y los casos límite de la spec.

## R4. Temas sugeridos y puente

- **Decision**:
  - se agrega a `prompts/care.md` una sección `offer.topics` con 6–8 temas generales verificables de Manuelita
    (historia desde 1864, azúcar y productos, energía y bioetanol, Fundación Manuelita, países donde opera,
    sostenibilidad, uvas y camarones), sin cifras nuevas;
  - el plan elige 2–3 que el hilo no haya ofrecido todavía;
  - el puente sigue con `bridge_every`, pero `bridge_every` baja a 1 solo cuando la racha es 1 (primer turno ajeno),
    para que el primer turno ajeno lleve un dato concreto cuando hay puente (FR-005).
- **Rationale**: FR-004 y FR-006. Rotar temas evita repetir la misma oferta; los temas no afirman cifras.
- **Alternatives considered**: repetir siempre «historia, productos, fundación» (repetición, SC-004).

## R5. Detección determinista para el verificador

- **Decision**: funciones puras en `review.py`, en español e inglés, sin tildes ni mayúsculas.
  - **`offtopic_question`**: una oración interrogativa (`¿…?` o que termina en `?`) que no menciona términos de
    Manuelita (léxico: manuelita, fundación, azúcar, ingenio, empresa, productos, historia, energía,
    sostenibilidad, países, uvas, camarones, aceite, bioetanol, planta, negocio, «te cuento», «quieres saber»).
  - **`chat_invite`**: patrones como «charlar», «solo charlar», «cuéntame de tu día», «qué has hecho», «qué tema te
    gustaría», «de lo que quieras» o «charlar también se vale».
  - **`no_redirect`**: la respuesta no menciona ningún término de Manuelita.
  - **`rejection`**: patrones como «mejor no me cuentes», «no me cuentes», «no quiero saber» o «no me interesa».
  - **`closing_repeat`**: la última oración tiene similitud > 0,8 con la última oración de una respuesta anterior
    del hilo.
  - **`max_sentences`**: el plan lo exige desde la racha 3.
- **Rationale**: los patrones salen de la transcripción y de las variantes; son verificables en pruebas.

## R6. Medición

- **Decision**:
  - **Conjunto**: `tests/fixtures/converse/focus.jsonl` con 16 conversaciones; la primera es la transcripción
    seudonimizada del 2026-11-27, y el resto son variantes con cine, clima, viajes, el día, «charlemos», inglés,
    mezcla con Manuelita, insistencia de 5 turnos y angustia.
  - **Comprobaciones nuevas por turno** en `converse_eval.check_turn`: `no_offtopic_question`, `no_chat_invite`,
    `redirects`, `no_rejection`, `no_closing_repeat` y `max_sentences`.
  - **Bloque nuevo**: `agent converse --focus`, que corre ese conjunto.
  - **Regresión**: en modo real se vuelve a correr la evaluación de conversación vigente
    (`docs/evaluacion_conversacion.json`), y la empatía no debe bajar (SC-006, regla 21).
- **Rationale**: reutiliza la evaluación de la spec 020 (juez y verificador) en lugar de crear otra.

## R7. Alcance en canales

- **Decision**:
  - el cambio vive en el agente compartido, así que aplica a la web, a WhatsApp y a la voz (la voz se genera
    desde la respuesta escrita);
  - el modo degradado de OpenClaw recibe una línea en `openclaw/workspace/AGENTS.md`: cortesía breve y regreso a
    Manuelita;
  - se avisa a Roberto del cambio compartido.
