# Feature Specification: Respuesta progresiva por frases revisadas

**Feature Branch**: `021-sentence-streaming`

**Created**: 2026-11-20

**Status**: Draft

**Input**: User description: «Implementemos la solución de streaming para reducir el tiempo de respuesta». La propuesta,
acordada en la conversación previa, es mostrar la respuesta de Valer-IA por frases a medida que se generan, revisando
cada frase antes de mostrarla.

**Contexto**: La spec 020 hizo que Valer-IA redacte con el modelo de lenguaje todo lo que no es Manuelita y que revise
la respuesta antes de mostrarla. Para que el visitante nunca vea un dato externo, esas respuestas se muestran
**completas** al final. El resultado es correcto, pero lento:

- en los turnos de conversación (saludos, charla, temas ajenos, preguntas sobre la asistente), el visitante espera
  entre 5.9 y 6.3 segundos en el 90 % de los turnos antes de ver la primera palabra, frente a unos 2 segundos con los
  guiones de la spec 019 (meta incumplida SC-011 de la spec 020);
- en las respuestas sobre Manuelita, el texto se muestra palabra por palabra **antes** de la revisión final. Si la
  revisión quita una frase sin respaldo, el visitante alcanzó a verla y luego desaparece.

Esta funcionalidad cambia la forma de entregar la respuesta, no su contenido: la respuesta aparece **frase por frase**,
y cada frase se muestra solo después de pasar la revisión. Así se recupera la sensación de inmediatez sin renunciar a
la garantía de que nada sin revisar llega al visitante.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver la respuesta de la conversación sin esperar a que esté completa (Priority: P1)

Un visitante saluda, comenta algo o pregunta por un tema ajeno. En lugar de esperar varios segundos frente a un
indicador de «pensando», ve aparecer la primera frase de Valer-IA en poco tiempo y el resto de la respuesta a medida
que se completa. Lo que ve ya fue revisado: nunca aparece un dato externo, un contacto inventado ni una promesa.

**Why this priority**: Es la deuda que motivó la funcionalidad. El tiempo hasta la primera palabra en la conversación
es hoy unas tres veces el de los guiones, y es lo que el visitante percibe primero.

**Independent Test**: Enviar una batería de mensajes de charla y temas ajenos y medir cuánto tarda en aparecer la
primera frase. Verificar que cada frase mostrada pasó la revisión y que el texto final es igual a lo que se fue
mostrando.

**Acceptance Scenarios**:

1. **Given** un visitante que escribe «¡qué calor hace hoy en Cali!», **When** Valer-IA responde, **Then** la primera
   frase aparece antes de que termine la respuesta completa y el resto se agrega frase por frase.
2. **Given** una respuesta en la que la segunda frase afirmaría un dato externo, **When** se revisa esa frase,
   **Then** nunca se muestra, y la respuesta termina de forma coherente con las frases ya aprobadas.
3. **Given** una primera frase que no pasa la revisión, **When** todavía no se ha mostrado nada, **Then** la
   respuesta se corrige o se usa el respaldo sin que el visitante vea el texto rechazado.
4. **Given** cualquier turno, **When** termina la respuesta, **Then** el texto final es exactamente la suma de las
   frases mostradas, sin retirar ni reemplazar nada de lo ya visto.
5. **Given** un mensaje de crisis o un caso de seguridad, **When** Valer-IA responde, **Then** la respuesta fija se
   muestra igual que hoy.

---

### User Story 2 - Respuestas sobre Manuelita sin frases que luego desaparecen (Priority: P2)

Un visitante pregunta por Manuelita. La respuesta con citas aparece frase por frase y cada frase se revisa antes de
mostrarse. Si una frase trae una cifra o un nombre sin respaldo en la evidencia, no se muestra, en lugar de mostrarse
y desaparecer al final como ocurre hoy.

**Why this priority**: Cierra una brecha de la garantía de la spec 020 en las respuestas con búsqueda. Afecta a pocos
turnos, pero el visitante ve un texto que luego cambia, lo que resta confianza.

**Independent Test**: Simular respuestas con búsqueda en las que una frase no tiene respaldo y verificar que esa frase
nunca llega al visitante y que las citas de las frases mostradas son válidas.

**Acceptance Scenarios**:

1. **Given** una pregunta sobre Manuelita, **When** Valer-IA responde, **Then** el texto aparece frase por frase con
   sus citas.
2. **Given** una frase con una cifra que no está en la evidencia, **When** se revisa, **Then** no se muestra y la
   respuesta sigue con las frases siguientes que sí tienen respaldo.
3. **Given** una respuesta en la que ninguna frase queda con cita válida, **When** termina, **Then** el visitante ve
   el mensaje de evidencia insuficiente, como hoy, y no un texto parcial sin citas.

---

### User Story 3 - La voz empieza a hablar con la primera frase (Priority: P3)

Con la voz activada (spec 016), Valer-IA empieza a leer en voz alta la primera frase aprobada, sin esperar la
respuesta completa. El avatar mueve la boca desde ese momento.

**Why this priority**: Aprovecha la entrega por frases para que la experiencia hablada también sea inmediata. Depende
de la historia 1.

**Independent Test**: Con la voz activada, medir el tiempo entre la primera frase mostrada y el inicio del audio en
los turnos de conversación.

**Acceptance Scenarios**:

1. **Given** la voz activada, **When** aparece la primera frase de un turno de conversación, **Then** el audio de esa
   frase empieza poco después, sin esperar el resto.
2. **Given** una frase que no pasó la revisión, **When** se descarta, **Then** tampoco se lee en voz alta.

---

### User Story 4 - Medir el tiempo de respuesta con la nueva entrega (Priority: P4)

El equipo puede comparar, con la misma evaluación de la spec 020, el tiempo hasta la primera frase, el tiempo total y
las garantías de contenido con la entrega por frases y con la entrega completa de la spec 020.

**Why this priority**: Sin medición no se puede afirmar que la deuda quedó saldada ni que no se perdió calidad.

**Independent Test**: Ejecutar la evaluación de naturalidad en los dos modos de entrega y verificar que el informe
muestra el tiempo hasta la primera frase, el tiempo total y las metas duras de la spec 020 en ambos.

**Acceptance Scenarios**:

1. **Given** la evaluación en modo real, **When** termina, **Then** el informe muestra el tiempo hasta la primera
   frase y el tiempo total por tipo de turno, junto con la línea base de la entrega completa.
2. **Given** la evaluación, **When** termina, **Then** también informa cuántas veces se mostró texto que luego se
   retiró (la meta es cero).

---

### Edge Cases

- **Frase muy larga sin puntuación**: si el modelo escribe un párrafo sin cerrar frases, se muestra por fragmentos
  revisados de tamaño razonable, sin cortar palabras, para que el visitante no espere la respuesta completa.
- **El modelo falla o se detiene a mitad de la respuesta**: se conservan las frases ya mostradas y la respuesta
  termina con una frase de cierre coherente, sin mensaje de error técnico.
- **Repetición de una respuesta anterior**: si la primera frase ya hace que la respuesta repita a otra del hilo, se
  corrige antes de mostrar. Si la repetición solo se detecta al final, no se retira lo mostrado y se registra en la
  evaluación.
- **Frases que el plan exige** (presentarse como Valer-IA Caña, decir que es inteligencia artificial, recomendar un
  profesional): si al terminar no aparecen, se agregan al final con una frase de respaldo, sin retirar lo mostrado.
- **Citas**: una frase con una etiqueta de cita que no existe no se muestra.
- **Mensajes mínimos** («ok», «jaja»): siguen teniendo como máximo dos frases.
- **Visitante que envía otro mensaje mientras llega la respuesta**: se mantiene el comportamiento actual del chat
  (el envío espera a que termine el turno).
- **Modo de demostración**: la respuesta también aparece por frases, sin red, para que la demo muestre el mismo
  comportamiento.
- **Volver a la entrega completa**: debe poder elegirse por configuración, como línea base y como plan B.

## Requirements *(mandatory)*

### Functional Requirements

**Entrega por frases**

- **FR-001**: Las respuestas redactadas por Valer-IA (conversación y respuestas sobre Manuelita) DEBEN mostrarse de
  forma progresiva, por frases o fragmentos completos, a medida que se generan.
- **FR-002**: Ninguna frase o fragmento DEBE mostrarse sin haber pasado la revisión de contenido de la spec 020
  (hechos externos, contactos, promesas, citas y opiniones).
- **FR-003**: Lo que ya se mostró NO DEBE retirarse ni reemplazarse. El texto final del turno DEBE ser igual a la
  secuencia de frases mostradas, más, si hace falta, una frase final de cierre o de respaldo.
- **FR-004**: Si la primera frase no pasa la revisión, la respuesta DEBE corregirse o pasar al respaldo antes de
  mostrar nada, como hoy.
- **FR-005**: Si una frase posterior no pasa la revisión, DEBE descartarse sin mostrarse. En la conversación, la
  respuesta DEBE terminar de forma coherente con las frases ya aprobadas. En las respuestas sobre Manuelita, puede
  continuar con las frases siguientes que sí tengan respaldo.
- **FR-006**: Una frase que no termina en un tiempo o longitud razonable DEBE poder mostrarse por fragmentos revisados,
  sin cortar palabras.
- **FR-007**: Las respuestas fijas de seguridad, identidad y perfil DEBEN mostrarse como hoy.

**Coherencia del turno**

- **FR-008**: Las verificaciones que dependen de la respuesta completa (repetición frente al hilo y frases que el plan
  exige) DEBEN aplicarse sin retirar lo mostrado: la repetición se evalúa lo antes posible, desde la primera frase, y
  las frases exigidas que falten se agregan al final.
- **FR-009**: Si el modelo falla o no responde a mitad de la respuesta, el visitante DEBE recibir una respuesta
  coherente que conserve lo mostrado, sin mensaje de error técnico.
- **FR-010**: Las citas de las frases mostradas DEBEN ser válidas. Una respuesta sobre Manuelita sin ninguna frase
  citada DEBE terminar en el mensaje de evidencia insuficiente, como hoy.
- **FR-011**: Las respuestas a mensajes mínimos DEBEN seguir teniendo como máximo dos frases.

**Voz y vista técnica**

- **FR-012**: Con la voz activada, la lectura en voz alta DEBE empezar con la primera frase aprobada y NO DEBE leer
  frases descartadas.
- **FR-013**: La vista técnica DEBE indicar, por turno, cuántas frases se descartaron en la revisión, sin mostrar su
  contenido.

**Configuración y evaluación**

- **FR-014**: La entrega por frases DEBE poder desactivarse por configuración para volver a la entrega completa de la
  spec 020, sin cambiar el código.
- **FR-015**: La evaluación de naturalidad DEBE medir, por tipo de turno, el tiempo hasta la primera frase visible y
  el tiempo hasta la respuesta completa, y compararlos con la entrega completa como línea base.
- **FR-016**: La evaluación DEBE verificar que ningún turno mostró texto que luego se retiró y que todas las frases
  mostradas pasan la revisión.
- **FR-017**: El modo de demostración DEBE entregar las respuestas por frases sin red.

### Key Entities *(include if feature involves data)*

- **Frase entregada**: un fragmento de la respuesta que pasó la revisión y se mostró al visitante. Tiene su orden en
  el turno y, si corresponde, sus citas.
- **Frase descartada**: un fragmento que no pasó la revisión. Solo se registra el motivo (hecho externo, cita
  inválida, etc.), nunca su texto, y solo en la vista técnica y en la evaluación.
- **Medición de entrega**: por turno, el tiempo hasta la primera frase visible, el tiempo total, el número de frases
  entregadas y descartadas, y si hubo texto retirado.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En los turnos de conversación (sin búsqueda), el visitante ve la primera frase en menos de 3 segundos en
  el 90 % de los turnos.
- **SC-002**: En las respuestas sobre Manuelita, el tiempo hasta la primera frase no supera en más de 1 segundo, en el
  90 % de los turnos, al de la entrega palabra por palabra actual.
- **SC-003**: En el 100 % de los turnos evaluados, el texto final es igual a lo que se fue mostrando: no se retira ni
  reemplaza nada ya visto.
- **SC-004**: El 100 % de las frases mostradas pasa la revisión de contenido: cero hechos externos, contactos
  inventados o promesas.
- **SC-005**: Se mantienen las metas duras de la spec 020 (no repetición en el hilo, variedad entre hilos, puentes
  medidos, garantías de contenido, respuestas de seguridad fijas y respuesta con el modelo caído) y la batería de
  conducta en 24/24.
- **SC-006**: El tiempo hasta la respuesta completa no aumenta más de un 10 % frente a la entrega completa de la spec
  020.
- **SC-007**: Con la voz activada, el audio de la primera frase empieza en menos de 1.5 segundos después de que la
  frase aparece, en el 90 % de los turnos de conversación.
- **SC-008**: Cuando el modelo falla a mitad de la respuesta, el 100 % de los turnos termina con una respuesta
  coherente y sin error visible.

## Assumptions

- El proveedor actual (DeepSeek) entrega su respuesta de forma progresiva, como ya ocurre en las respuestas sobre
  Manuelita. No se cambia de proveedor ni de modelo.
- La revisión por reglas de la spec 020 es lo bastante rápida para aplicarse a cada frase sin un retraso perceptible.
- Se considera frase un fragmento que termina en punto, signo de cierre de pregunta o exclamación, o salto de línea;
  las abreviaturas y cifras con punto no cortan una frase.
- La regeneración completa solo es posible mientras no se haya mostrado nada. Después de la primera frase, los
  problemas se resuelven descartando frases o agregando un cierre, nunca retirando texto.
- La voz (spec 016) ya lee por oraciones; esta funcionalidad le entrega antes la primera.
- La meta de 3 segundos se mide con la conexión y el proveedor habituales del equipo, como en la spec 020.

## Dependencies

- Spec 020 (conversación natural guiada): plan del turno, revisión, respaldo, memoria y evaluación `agent converse`.
- Spec 016 (voz) y spec 017 (avatar): lectura por oraciones y movimiento de la boca.
- Spec 014 (agente con memoria): flujo de eventos de la conversación hacia la web.
