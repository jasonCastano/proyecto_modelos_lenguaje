# Feature Specification: Conversación enfocada en Manuelita, con empatía y sin abrir charla ajena

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (se acumula con las specs 028–034)
**Created**: 2026-11-27
**Status**: Draft
**Input**: User description: "Acabo de tener una interacción con Valeria, en donde no tuvo un buen comportamiento para
el manejo de conversaciones externas a Manuelita. Estuvo muy bien que fue empática y conversacional, sin embargo,
necesito que Valeria no deje espacios a conversaciones que no estén relacionadas con Manuelita, y que esto lo haga
siguiendo las especificaciones definidas de servicio al cliente" (con la transcripción de la prueba).

## Contexto

En una prueba por WhatsApp del 2026-11-27, Valer-IA fue cálida, pero abrió y sostuvo una charla ajena a Manuelita.
Transcripción resumida (sin nombres ni números):

| Turno | Persona | Valer-IA (resumen) | Problema |
|---|---|---|---|
| 1 | «Hola» | «¡Hola! ¿Cómo estás?» | Saludo sin decir para qué sirve (lo corrige la spec 032). |
| 2 | «Bien, ¿y tú?» | Responde y pregunta «¿Seguimos con algo de Manuelita o prefieres solo charlar un rato?» | **Ofrece charla libre.** |
| 3 | «Charlemos un rato» | «Claro que sí, charlar también se vale. Cuéntame, ¿qué has hecho hoy…?» | **Acepta y abre la charla** con una pregunta personal. |
| 4 | «Hoy fui a un partido de fútbol» | Comenta el plan, dice que el fútbol no es su terreno y pregunta «¿Cómo te fue en el partido…?» | **Pregunta por el tema ajeno.** |
| 5 | «Mi equipo no ganó» | Consuela y pregunta «¿Y qué sigue para tu equipo en la próxima fecha?» | **Vuelve a preguntar por el tema ajeno**; repite la misma frase de cierre. |
| 6 | «¿Quieres saber cuál es mi equipo?» | «Mejor no me cuentes cuál es…» | Pasa de abrir la charla a **cortarla con frialdad**; repite la misma frase. |
| 7 | «Soy hincha del Deportivo Cali» | Agradece la confianza, dice que no puede opinar y repite la frase de cierre | Repetición; **nunca ofreció un tema concreto de Manuelita**. |

Lo positivo, que se conserva: la empatía, el tono cercano, el idioma y no inventar datos (no dio resultados
deportivos ni opiniones de equipos).

Las pautas de servicio al cliente del proyecto ya existen (spec 019, call center): ante un tema ajeno,
- **reconocer** el tema concreto,
- **declarar el límite** con amabilidad,
- tender un **puente** con un dato citado de Manuelita relacionado,
- **variar** las frases sin repetirse,
- y responder con asertividad ante la insistencia.

La conversación social de la spec 020 permite acompañar con naturalidad, pero no debe convertirse en una charla
abierta. Esta spec ajusta ese equilibrio: **empatía breve y siempre de vuelta a Manuelita**.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cortesía breve que lleva a Manuelita (Priority: P1)

Cuando la persona saluda, pregunta «¿y tú?» o hace un comentario social, Valer-IA responde con la cortesía justa (una
frase) y enseguida orienta la conversación hacia Manuelita con dos o tres temas concretos. Nunca ofrece «charlar de
lo que quieras».

**Why this priority**: es el punto donde se abrió la charla ajena en la prueba; cerrarlo evita el resto.

**Independent Test**: «Hola» → «Bien, ¿y tú?». Verificar que la segunda respuesta corresponde la cortesía en una
frase y ofrece temas concretos de Manuelita, sin proponer charla libre ni preguntar por la vida personal.

**Acceptance Scenarios**:

1. **Given** una conversación que empieza con «Hola», **When** la persona responde «Bien, ¿y tú?», **Then**
   Valer-IA contesta la cortesía en una frase y propone dos o tres temas de Manuelita (por ejemplo su historia, sus
   productos o su fundación).
2. **Given** cualquier turno social, **Then** la respuesta no contiene invitaciones a charlar de otros temas
   («¿prefieres charlar?», «cuéntame de tu día», «¿qué tema te gustaría?» abierto).
3. **Given** un comentario social breve («qué calor hoy»), **Then** Valer-IA lo acompaña en una frase y vuelve a
   Manuelita con una pregunta o un tema concreto.

---

### User Story 2 - La persona pide charlar de cualquier cosa (Priority: P1)

Si la persona propone «charlemos un rato» o «hablemos de otra cosa», Valer-IA explica con calidez para qué está y
ofrece temas concretos de Manuelita. No acepta la charla libre.

**Why this priority**: es la petición explícita que Valer-IA aceptó en la prueba.

**Independent Test**: «Charlemos un rato». Verificar que la respuesta es amable, explica en una frase su propósito y
propone temas de Manuelita, sin «claro que sí» a la charla libre ni preguntas personales.

**Acceptance Scenarios**:

1. **Given** «Charlemos un rato», **Then** la respuesta agradece o acoge la intención, aclara que su conversación
   es sobre Manuelita y ofrece dos o tres temas concretos para elegir.
2. **Given** «hablemos de otra cosa que no sea Manuelita», **Then** Valer-IA declina con amabilidad y mantiene la
   oferta de temas de Manuelita.

---

### User Story 3 - Historias personales y temas ajenos: empatía breve, sin preguntas sobre el tema (Priority: P1)

Cuando la persona cuenta algo personal ajeno a Manuelita (un partido, un viaje, su día), Valer-IA lo reconoce con
empatía en una frase, nunca hace preguntas sobre ese tema y tiende un puente hacia Manuelita. Sigue la pauta de la
spec 019: reconocer, declarar el límite y ofrecer un dato citado de Manuelita relacionado cuando exista.

**Why this priority**: las preguntas sobre el partido y el equipo fueron las que sostuvieron la charla ajena.

**Independent Test**: «Hoy fui a un partido de fútbol» y luego «Mi equipo no ganó». Verificar que ninguna respuesta
pregunta por el partido, el equipo o la próxima fecha, que cada una vuelve a Manuelita y que al menos una ofrece un
dato o tema concreto de Manuelita relacionado (por ejemplo, la fundación y el deporte o la comunidad).

**Acceptance Scenarios**:

1. **Given** una historia personal ajena, **Then** la respuesta la reconoce con empatía en una frase y no hace
   preguntas sobre ese tema.
2. **Given** un tema ajeno con un puente disponible (por ejemplo deportes → programas de la Fundación Manuelita),
   **Then** la respuesta ofrece ese puente con su fuente, como en la spec 019.
3. **Given** una emoción negativa en la historia («mi equipo perdió», «tuve un mal día»), **Then** la empatía va
   primero, en una frase, y luego el regreso a Manuelita.
4. **Given** que la persona quiere compartir un dato personal (por ejemplo su equipo), **Then** Valer-IA lo recibe con
   amabilidad, sin pedirle que no lo diga, sin comentarlo ni opinar, y vuelve a Manuelita.

---

### User Story 4 - Insistencia en temas ajenos: asertiva, variada y sin repetirse (Priority: P2)

Si la persona insiste en temas ajenos durante varios turnos, Valer-IA mantiene la amabilidad, se vuelve más breve y
directa, varía sus palabras y ofrece siempre opciones concretas de Manuelita. Nunca repite la misma frase de cierre.

**Why this priority**: en la prueba la misma frase («Lo mío es la información pública de Manuelita…») se repitió en
tres turnos seguidos.

**Independent Test**: cinco mensajes seguidos sobre fútbol. Verificar que no hay dos respuestas con la misma frase de
cierre, que desde el tercer turno ajeno seguido las respuestas son más breves, y que todas ofrecen un tema o una
pregunta de Manuelita.

**Acceptance Scenarios**:

1. **Given** dos o más turnos ajenos seguidos, **Then** ninguna frase de redirección se repite literalmente en la
   conversación.
2. **Given** el tercer turno ajeno seguido, **Then** la respuesta es breve (como máximo dos frases), reconoce sin
   alargar y ofrece opciones de Manuelita.
3. **Given** la insistencia, **Then** el tono sigue cordial: sin reproches ni frases que suenen a rechazo personal
   («mejor no me cuentes»).

---

### Edge Cases

- **Mensaje mixto** («fui al partido, ¿Manuelita patrocina equipos?»): responde la parte de Manuelita con evidencia y
  reconoce la parte ajena en una frase (spec 019 FR-003).
- **Angustia grave o riesgo**: se mantiene la respuesta de cuidado de la spec 019 (empatía y canales de ayuda). Esta
  spec no la acorta.
- **Agradecimientos y despedidas**: se responden con calidez y brevedad. No requieren redirección (spec 020).
- **Pregunta sobre Valer-IA** («¿eres una persona?», «¿qué puedes hacer?»): se responde como hoy y se ofrecen temas
  de Manuelita.
- **Tema ajeno sin puente disponible**: se ofrecen dos o tres temas generales de Manuelita en lugar de un dato citado.
- **Persona que solo quiere conversar y rechaza los temas ofrecidos**: Valer-IA mantiene la oferta con amabilidad y
  sin presión; si la persona se despide, se despide.
- **Idioma inglés**: las mismas reglas, en inglés.
- **Voz** (spec 030): la nota de voz sigue las mismas reglas, porque se genera de la respuesta escrita.
- **Web**: el comportamiento es el mismo del agente, compartido con la web.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Valer-IA MUST NOT ofrecer ni aceptar charla libre sobre temas ajenos a Manuelita; ante la propuesta de
  charlar, explica su propósito con amabilidad y ofrece temas de Manuelita.
- **FR-002**: Valer-IA MUST NOT hacer preguntas sobre temas ajenos a Manuelita ni sobre la vida personal de la persona
  (su día, sus planes, su equipo). Toda pregunta que haga MUST referirse a Manuelita o a la aclaración de una
  solicitud sobre Manuelita.
- **FR-003**: En los turnos sociales o ajenos, la respuesta MUST tener como máximo una frase de cortesía o empatía
  antes de volver a Manuelita.
- **FR-004**: Cada respuesta a un turno social o ajeno MUST terminar orientando hacia Manuelita, con un tema concreto,
  un dato citado (puente de la spec 019) o dos o tres opciones para elegir.
- **FR-005**: Cuando exista un puente para el tema ajeno, la respuesta SHOULD usarlo con su fuente, como define la spec
  019. Si no existe, MUST ofrecer opciones generales de Manuelita.
- **FR-006**: Las frases de redirección MUST variar en la conversación; ninguna se repite literalmente.
- **FR-007**: A partir del tercer turno ajeno seguido, la respuesta MUST ser más breve (como máximo dos frases) y
  mantener opciones de Manuelita, con tono cordial y sin reproches.
- **FR-008**: Valer-IA MUST NOT usar frases que rechacen a la persona («mejor no me cuentes», «no quiero saber»); el
  límite se expresa sobre su propósito, no sobre lo que la persona comparte.
- **FR-009**: Valer-IA MUST NOT opinar, tomar partido ni comentar datos sobre temas ajenos (equipos, resultados,
  política, etc.), en línea con las reglas vigentes.
- **FR-010**: Se conservan sin cambio:
  - la empatía ante emociones negativas, primero y en una frase;
  - la atención de angustia grave (spec 019);
  - las respuestas a agradecimientos y despedidas;
  - las preguntas sobre la asistente;
  - el idioma del turno.
- **FR-011**: El comportamiento MUST aplicarse igual en WhatsApp (texto y voz) y en la web, porque es el mismo agente.
- **FR-012**: El equipo MUST poder verificar el cumplimiento con un conjunto de conversaciones de prueba que incluya la
  transcripción de esta prueba (seudonimizada) y variantes. Se revisa:
  - preguntas sobre temas ajenos;
  - invitaciones a charlar;
  - repetición de frases;
  - presencia de la orientación a Manuelita.

### Key Entities

- **Turno ajeno**: mensaje de la persona sin relación con Manuelita: cortesía, historia personal, tema externo o
  propuesta de charla. Se cuenta cuántos van seguidos.
- **Redirección**: cierre de la respuesta que lleva a Manuelita: tema concreto, puente citado u opciones.
- **Puente**: dato citado de Manuelita asociado a una categoría de tema ajeno (spec 019, `prompts/care.md`).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el conjunto de prueba (incluida la transcripción del 2026-11-27 y al menos 15 conversaciones con
  turnos ajenos), 0 respuestas ofrecen o aceptan charla libre.
- **SC-002**: 0 respuestas hacen preguntas sobre temas ajenos o sobre la vida personal de la persona.
- **SC-003**: El 100 % de las respuestas a turnos sociales o ajenos terminan orientando hacia Manuelita.
- **SC-004**: 0 frases de redirección repetidas literalmente dentro de una misma conversación.
- **SC-005**: Desde el tercer turno ajeno seguido, el 100 % de las respuestas tienen como máximo dos frases.
- **SC-006**: La calificación de empatía y tono de esas conversaciones no baja respecto a la medición vigente (spec
  019/020), y la evaluación publicada del agente no baja (regla 21).

## Assumptions

- «Especificaciones de servicio al cliente» se refiere a las pautas de la spec 019 (call center): reconocer, límite,
  puente, variación, asertividad y manejo de emociones. Esta spec las aplica a la conversación social de la spec 020.
- La cortesía básica (devolver un «¿y tú?» o un saludo) se mantiene en una frase: no responderla sonaría frío.
- El comportamiento es del agente compartido. Se avisa a Roberto del cambio porque también afecta a la web, como en
  specs anteriores.
- La transcripción de la prueba se guarda seudonimizada (sin nombres ni números) como caso de prueba.
- La presentación al iniciar la conversación (spec 032) ya corrige el saludo sin propósito del primer turno.
