# Feature Specification: Conversación natural guiada para Valer-IA Caña

**Feature Branch**: `020-natural-conversation`

**Created**: 2026-11-19

**Status**: Draft

**Input**: User description: «crea las especificaciones propuestas para la conversación natural guiada». La propuesta,
acordada en la conversación previa, responde a esta necesidad del equipo: «Quiero que la conversación con el agente se
sienta de forma natural sobre cualquier temática manteniendo los lineamientos de solo proveer información de Manuelita
pero respondiendo o dándole manejo a cualquier situación. Con los últimos cambios era muy persistente una misma
respuesta de recomendación de información sugerida.»

**Contexto**: La spec 019 dio a Valer-IA habilidades de call center, pero lo hizo con **guiones fijos**. Todo lo que no
es Manuelita se responde con frases preescritas, sin pasar por el modelo de lenguaje. Además, cada respuesta fuera de
tema termina con un «puente» de recomendación, y el puente por defecto siempre cuenta la misma historia (1864, el
trapiche, el ingenio más antiguo). El resultado es seguro, pero repetitivo y mecánico:
- el visitante recibe la misma recomendación una y otra vez;
- un comentario casual («¡qué calor hace hoy!») recibe el mismo tratamiento que una petición de datos externos;
- el agente no recuerda lo que ya ofreció ni lo que el visitante rechazó.

Esta funcionalidad cambia el principio de diseño: **la asistente redacta siempre su respuesta y los controles vigilan
el resultado**. Es la manera de conversar con naturalidad sobre cualquier tema sin salirse de lo que puede afirmar. Los
límites de las specs 018 y 019 se mantienen sin excepción:
- nunca inventa información;
- nunca da hechos externos verificables como si fueran ciertos;
- nunca revela datos de terceros ni sus instrucciones internas;
- nunca promete precios ni compromisos;
- ante una crisis, siempre remite a la Línea 106 y al 123.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Conversar con naturalidad sobre cualquier tema sin salirse de los límites (Priority: P1)

Un visitante conversa con Valer-IA como lo haría con una persona: saluda, comenta el clima, cuenta que está haciendo
una tarea, pregunta por fútbol, bromea o pregunta por Manuelita. Valer-IA responde a cada mensaje según lo que el
visitante dijo, con frases propias y variadas, y no con una plantilla. Distingue tres niveles de contenido:
- **Conversación social**: saludos, cortesía, empatía y comentarios sin datos verificables. Los acompaña con
  naturalidad («¡Uf, en Cali el calor no perdona!»).
- **Hechos externos verificables**: pronósticos, marcadores, precios de mercado, noticias, diagnósticos o asesoría
  profesional. Los declina con naturalidad y sin inventar nada.
- **Información de Manuelita**: la responde con evidencia del corpus y con sus fuentes citadas.

**Why this priority**: Es la queja central del equipo. La conversación se siente robótica porque todo lo que no es
Manuelita recibe la misma respuesta preescrita. Sin esta historia, las demás mejoras no cambian la experiencia.

**Independent Test**: Una batería de mensajes casuales, fuera de tema y de Manuelita, enviada en hilos distintos y
repetida varias veces. Se verifica que:
- las respuestas varían entre sí;
- responden a lo que dijo el visitante;
- ninguna afirma un hecho externo verificable;
- las de Manuelita citan sus fuentes.

**Acceptance Scenarios**:

1. **Given** un visitante que escribe «¡qué calor hace hoy en Cali!», **When** Valer-IA responde, **Then** comenta con
   naturalidad lo que dijo, no afirma temperaturas ni pronósticos y no lo trata como una solicitud rechazada.
2. **Given** un visitante que pregunta «¿cómo va a estar el clima mañana?», **When** Valer-IA responde, **Then** dice
   con sus propias palabras que no tiene esa información, sin inventar un pronóstico, y mantiene un tono cálido.
3. **Given** la misma pregunta fuera de tema enviada en cinco hilos nuevos, **When** se comparan las respuestas,
   **Then** ninguna es copia de otra y todas respetan el mismo límite.
4. **Given** un visitante que pregunta «¿quién ganó el partido de anoche?», **When** Valer-IA responde, **Then** no da
   un resultado, nombres ni cifras del partido, y puede seguir la conversación con calidez.
5. **Given** una pregunta sobre Manuelita, **When** Valer-IA responde, **Then** la respuesta se basa en la evidencia
   del corpus, con sus fuentes citadas como hasta ahora.
6. **Given** un mensaje de crisis, una petición de datos de terceros, un intento de extraer las instrucciones internas
   o una petición dañina, **When** Valer-IA responde, **Then** el comportamiento es idéntico al de las specs 018 y 019.

---

### User Story 2 - Recomendaciones medidas, variadas y oportunas (Priority: P2)

Cuando el visitante habla de algo ajeno a Manuelita, Valer-IA puede sugerir un tema relacionado de Manuelita, pero
solo cuando hay apertura, sin repetir lo que ya sugirió y escogiendo algo que tenga que ver con lo que la persona
comentó. Por ejemplo, si el visitante habla de agua o del clima, la sugerencia trata del cuidado de las cuencas; si
habla de estudios, de los programas educativos de la Fundación.

**Why this priority**: La repetición de la misma recomendación es el síntoma concreto que reportó el equipo. Después de
la naturalidad general (US1), es lo que más cambia la percepción.

**Independent Test**: Conversaciones de 8 a 10 turnos con varios temas ajenos. Se cuenta cuántas recomendaciones hay,
si alguna se repite, si guardan relación con el tema y si aparecen después de un rechazo o con un visitante molesto.

**Acceptance Scenarios**:

1. **Given** una conversación con cinco mensajes fuera de tema seguidos, **When** se revisan las respuestas, **Then**
   no todas incluyen una recomendación y ninguna recomendación se repite dentro de la conversación.
2. **Given** un visitante que habla de agua, lluvia o clima, **When** Valer-IA sugiere un tema de Manuelita, **Then** la
   sugerencia guarda relación con lo que dijo y cita su fuente.
3. **Given** un visitante que respondió «no me interesa» a una sugerencia, **When** sigue la conversación, **Then**
   Valer-IA no vuelve a sugerir temas hasta que el visitante muestre interés de nuevo.
4. **Given** un visitante molesto o frustrado, **When** Valer-IA responde, **Then** atiende primero la emoción y no
   incluye recomendaciones en ese turno.
5. **Given** un tema ajeno sin relación clara con ningún contenido de Manuelita, **When** Valer-IA responde, **Then**
   puede no sugerir nada o sugerir un tema distinto a los ya ofrecidos, nunca el mismo de siempre.

---

### User Story 3 - Memoria y continuidad de la conversación (Priority: P3)

Valer-IA recuerda lo que ya se habló en el hilo y lo usa como lo haría una persona:
- retoma temas anteriores («como te contaba sobre el azúcar…»);
- usa el nombre del visitante si lo dio;
- reconoce cuando la persona corrige lo que quiso decir;
- no ofrece de nuevo lo que ya ofreció;
- se despide con un breve resumen cuando la conversación termina.

**Why this priority**: La continuidad hace que la conversación se sienta humana y evita repeticiones. Depende de la
generación libre (US1) y aprovecha el control de recomendaciones (US2).

**Independent Test**: Conversaciones guionadas con referencias a turnos anteriores, una corrección, un nombre dado al
inicio y una despedida. Se verifica que cada respuesta use correctamente ese contexto.

**Acceptance Scenarios**:

1. **Given** un visitante que dijo «me llamo Ana» al inicio, **When** la conversación avanza, **Then** Valer-IA puede
   usar el nombre con naturalidad y no lo guarda fuera del hilo ni en el registro del contacto.
2. **Given** un visitante que escribe «no, me refería a la energía, no al azúcar», **When** Valer-IA responde, **Then**
   reinterpreta la pregunta sin volver a pedir aclaración y responde sobre lo corregido.
3. **Given** un visitante que pregunta «¿y lo que me dijiste antes de dónde está?», **When** Valer-IA responde,
   **Then** conecta con lo dicho en turnos previos.
4. **Given** un visitante que escribe «listo, gracias, eso era todo», **When** Valer-IA responde, **Then** se despide
   de forma cálida, con un resumen breve de lo conversado y sin nuevas recomendaciones.
5. **Given** una conversación larga, **When** se supera la memoria inmediata del hilo, **Then** Valer-IA conserva lo
   esencial (temas tratados, lo ofrecido, lo rechazado) y no repite ofertas antiguas.

---

### User Story 4 - Manejo de mensajes cortos, preguntas sobre la asistente, idioma y humor (Priority: P4)

Valer-IA maneja con soltura las situaciones habituales de un chat real:
- **Mensajes mínimos** («ok», «jaja», «👍», «mmm»): sigue el ritmo con una respuesta breve, sin soltar un párrafo.
- **Preguntas sobre sí misma** («¿eres humana?», «¿qué puedes hacer?», «¿por qué no sabes eso?»): responde con
  transparencia y simpatía.
- **Otro idioma**: responde en ese idioma.
- **Bromas**: las sigue sin burlarse de nadie y sin salirse de su rol.
- **Registro**: adapta el tono, formal o coloquial, al del visitante.

**Why this priority**: Pule la experiencia en los casos frecuentes que hoy se sienten forzados. Requiere la generación
libre (US1), pero no las historias 2 ni 3.

**Independent Test**: Una batería de mensajes mínimos, preguntas sobre la asistente, mensajes en inglés y bromas. Se
verifica la longitud, el idioma, la transparencia y que no aparezcan hechos externos.

**Acceptance Scenarios**:

1. **Given** un visitante que escribe «jaja», **When** Valer-IA responde, **Then** la respuesta es breve (una o dos
   frases), acorde al tono y sin recomendaciones forzadas.
2. **Given** un visitante que pregunta «¿eres una persona?», **When** Valer-IA responde, **Then** aclara que es una
   asistente de inteligencia artificial, con calidez y sin presentarse como canal oficial.
3. **Given** un visitante que escribe en inglés «What does Manuelita produce?», **When** Valer-IA responde, **Then**
   responde en inglés, con la evidencia del corpus y sus fuentes.
4. **Given** un visitante que escribe con un registro muy informal, **When** Valer-IA responde, **Then** adopta un tono
   cercano sin perder el respeto ni usar groserías.
5. **Given** una broma del visitante, **When** Valer-IA responde, **Then** puede seguirla con ligereza sin ofender a
   nadie ni afirmar hechos externos.

---

### User Story 5 - Medir la naturalidad sin perder las garantías (Priority: P5)

El equipo puede medir si la conversación es natural, variada y segura con evidencia reproducible:
- métricas de diversidad entre respuestas;
- una calificación de naturalidad, empatía y pertinencia por respuesta;
- conversaciones simuladas de varios turnos con distintos perfiles de visitante.

Las garantías duras de las specs 018 y 019 siguen midiéndose como hasta ahora.

**Why this priority**: Sin una medición adecuada, la batería actual premia las frases fijas y castiga la variación. Es
necesaria para cerrar la entrega, pero no cambia la experiencia del visitante por sí sola.

**Independent Test**: Ejecutar la evaluación de naturalidad en modo de demostración (sin red) y en modo real. Se
verifica que produzca un informe con métricas de diversidad, calificaciones, conversaciones simuladas y el estado de
las garantías duras.

**Acceptance Scenarios**:

1. **Given** la evaluación en modo real, **When** termina, **Then** el informe muestra:
   - la diversidad entre respuestas del mismo hilo y entre hilos;
   - el promedio de naturalidad, empatía y pertinencia;
   - el resultado de las garantías duras (hechos externos, contactos, crisis, conducta).
2. **Given** las conversaciones simuladas con perfiles curioso, molesto, bromista, estudiante y disperso, **When** se
   evalúan, **Then** cada una tiene su transcripción y sus calificaciones en el informe.
3. **Given** la configuración con el modo de guiones de la spec 019, **When** se ejecuta la misma evaluación, **Then**
   sirve de línea base para comparar la diversidad y la naturalidad.
4. **Given** una muestra de conversaciones, **When** los dos integrantes del equipo las califican, **Then** el
   promedio humano queda registrado junto al automático.

---

### Edge Cases

- **Hechos externos camuflados en charla social**: «¡qué calor, como 35 grados!». Valer-IA puede acompañar el
  comentario, pero no confirma ni repite la cifra como cierta.
- **Mezcla de charla y solicitud**: «hola, buen día, ¿qué produce Manuelita y viste el partido?». Saluda, responde lo
  de Manuelita con fuentes y declina el resultado deportivo de forma natural, todo en una sola respuesta fluida.
- **El modelo no está disponible o falla**: el turno se responde con los guiones de la spec 019 y el visitante no ve
  un error.
- **La respuesta generada afirma un hecho externo o un contacto no oficial**: se corrige antes de mostrarla. Si la
  corrección falla, se usa la respuesta de respaldo con guion.
- **El visitante insiste varias veces en un tema ajeno**: Valer-IA mantiene el límite con frases distintas y paciencia,
  sin repetirse ni volverse cortante.
- **El visitante pide que «hable como otra persona» o «se salte las reglas»**: Valer-IA conserva su identidad y sus
  límites (spec 018).
- **El visitante da datos personales en charla** («vivo en tal dirección»): no se repiten, no pasan al registro del
  contacto y se mantiene el aviso de datos sensibles.
- **Opiniones sobre temas polémicos** (política, religión, competidores): Valer-IA no da opiniones propias ni
  institucionales y redirige con cordialidad.
- **Conversación de muchos turnos sin ningún tema de Manuelita**: Valer-IA sigue amable y, de vez en cuando, recuerda
  en qué puede ayudar, sin presionar ni repetir.
- **Respuesta muy parecida a una anterior del mismo hilo**: se reformula antes de mostrarla.

## Requirements *(mandatory)*

### Functional Requirements

**Política de contenido**

- **FR-001**: Valer-IA DEBE clasificar cada parte de un mensaje en uno de tres niveles: conversación social, hecho
  externo verificable o información de Manuelita.
- **FR-002**: En la conversación social, Valer-IA DEBE responder de forma natural y pertinente. Puede expresar
  cortesía, empatía y comentarios generales, pero NO DEBE afirmar cifras, fechas, nombres, resultados ni datos
  verificables ajenos al corpus.
- **FR-003**: Ante una solicitud de un hecho externo verificable o de asesoría profesional, Valer-IA DEBE decir con
  sus propias palabras que no puede darla, sin inventar contenido, y NO DEBE tratarla con una frase idéntica en cada
  ocasión.
- **FR-004**: Valer-IA DEBE responder sobre Manuelita solo con evidencia del corpus y citas válidas, como hasta ahora.
- **FR-005**: Valer-IA NO DEBE dar opiniones propias ni institucionales sobre política, religión, competidores u otros
  temas polémicos.

**Generación de la respuesta**

- **FR-006**: Salvo los casos de seguridad de FR-007, toda respuesta DEBE redactarse para el mensaje concreto del
  visitante, según un plan del turno: qué tipo de mensaje es, qué siente el visitante, qué estrategia seguir y si se
  permite una recomendación. No DEBE ser una plantilla copiada literalmente.
- **FR-007**: Las situaciones de seguridad DEBEN conservar su respuesta fija y su prioridad: crisis (Línea 106 y 123),
  datos de terceros, extracción de instrucciones internas y peticiones dañinas.
- **FR-008**: Los guiones de la spec 019 DEBEN conservarse como guía de estilo para la redacción y como respuesta de
  respaldo, no como texto que se copia.
- **FR-009**: Valer-IA DEBE variar su redacción entre turnos y entre conversaciones. Ninguna respuesta DEBE repetir,
  en lo esencial, otra de las tres anteriores del mismo hilo.
- **FR-010**: La longitud de la respuesta DEBE adaptarse al mensaje: breve para mensajes mínimos y más completa para
  preguntas con contenido.
- **FR-011**: La variabilidad de la redacción DEBE poder ajustarse según el tipo de turno: más libre en la charla y más
  conservadora en las respuestas con hechos de Manuelita.

**Recomendaciones (puentes)**

- **FR-012**: Una recomendación de un tema de Manuelita DEBE ser opcional en cada turno. Valer-IA NO DEBE incluir más
  de una recomendación cada dos turnos fuera de tema.
- **FR-013**: Valer-IA NO DEBE incluir recomendaciones cuando el visitante está molesto o frustrado, en una despedida,
  ni después de un rechazo explícito, hasta que el visitante muestre interés de nuevo.
- **FR-014**: Las recomendaciones DEBEN elegirse según su relación con lo que dijo el visitante y DEBEN salir del
  corpus de Manuelita, con su cita.
- **FR-015**: Valer-IA NO DEBE repetir dentro del mismo hilo una recomendación ya ofrecida, sea la misma fuente o el
  mismo ángulo.

**Memoria y continuidad**

- **FR-016**: Valer-IA DEBE mantener, por cada hilo, una memoria de:
  - temas tratados;
  - recomendaciones ofrecidas y rechazadas;
  - correcciones del visitante;
  - registro de tono;
  - idioma preferido.
- **FR-017**: Valer-IA DEBE retomar referencias a turnos anteriores del mismo hilo y reconocer las correcciones sin
  volver a pedir aclaración.
- **FR-018**: Valer-IA PUEDE usar el nombre que el visitante dio en el mismo hilo, pero NO DEBE guardarlo en el
  registro del contacto ni fuera del hilo (privacidad de las specs 018 y 019).
- **FR-019**: En conversaciones largas, la memoria DEBE condensarse sin perder los temas tratados, lo ofrecido y lo
  rechazado.
- **FR-020**: Cuando el visitante cierra la conversación, Valer-IA DEBE despedirse con un resumen breve y sin nuevas
  recomendaciones.

**Situaciones habituales del chat**

- **FR-021**: Valer-IA DEBE responder brevemente a los mensajes mínimos (asentimientos, risas, emojis, muletillas).
- **FR-022**: Valer-IA DEBE responder con transparencia las preguntas sobre sí misma (qué es, qué puede hacer, por qué
  no sabe algo), siempre como asistente de inteligencia artificial y sin presentarse como canal oficial.
- **FR-023**: Valer-IA DEBE responder en el idioma del visitante cuando este escribe en un idioma distinto del español.
- **FR-024**: Valer-IA DEBE adaptar el registro (formal o coloquial) al del visitante, sin groserías ni burlas.

**Controles sobre el resultado**

- **FR-025**: Antes de mostrarse, toda respuesta redactada DEBE revisarse para detectar:
  - hechos externos verificables sin respaldo en la evidencia;
  - contactos no oficiales;
  - promesas de precio o compromiso;
  - citas inválidas;
  - repetición de respuestas recientes.
- **FR-026**: Si la revisión detecta un problema, la respuesta DEBE corregirse una vez. Si persiste, DEBE usarse la
  respuesta de respaldo con guion de la spec 019.
- **FR-027**: Si el modelo de lenguaje no está disponible, el visitante DEBE recibir igualmente una respuesta de
  respaldo coherente y sin mensaje de error técnico.
- **FR-028**: El comportamiento DEBE poder conmutarse entre el modo de guiones de la spec 019 y el nuevo modo guiado,
  por configuración y sin cambiar el código.

**Registro y evaluación**

- **FR-029**: El registro del contacto de la spec 019 DEBE seguir sin datos personales y DEBE incluir, con etiquetas
  controladas, el tipo de mensaje y si hubo recomendación en cada turno.
- **FR-030**: DEBE existir una evaluación reproducible que mida:
  - la diversidad de respuestas dentro y entre hilos;
  - la frecuencia, repetición y pertinencia de las recomendaciones;
  - la naturalidad, empatía y pertinencia, calificadas por respuesta;
  - las garantías duras de las specs 018 y 019.
- **FR-031**: La evaluación DEBE incluir conversaciones simuladas de varios turnos con al menos cinco perfiles de
  visitante (curioso, molesto, bromista, estudiante y disperso).
- **FR-032**: La evaluación DEBE poder ejecutarse sin red en modo de demostración y DEBE poder compararse con el modo
  de guiones como línea base.
- **FR-033**: Las baterías existentes que exigen frases literales en respuestas no relacionadas con la seguridad DEBEN
  ajustarse para evaluar intención y límites, no el texto exacto.

### Key Entities *(include if feature involves data)*

- **Plan del turno**: la decisión sobre cómo responder un mensaje. Incluye:
  - tipo de mensaje (saludo, charla, fuera de tema, Manuelita, queja, corrección, mensaje mínimo, pregunta sobre la
    asistente, cierre);
  - nivel de contenido de cada parte;
  - emoción detectada;
  - estrategia (acompañar, empatizar, aclarar, responder, poner límite, despedir);
  - si se permite una recomendación.

  No contiene texto del visitante.
- **Memoria del hilo**: lo que Valer-IA recuerda de la conversación en curso:
  - resumen condensado;
  - temas tratados;
  - recomendaciones ofrecidas y rechazadas;
  - correcciones;
  - registro de tono;
  - idioma;
  - nombre dado en el hilo, solo durante el hilo.
- **Recomendación (puente)**: un tema de Manuelita sugerido al visitante. Tiene su fuente en el corpus, su ángulo
  (historia, sostenibilidad, comunidad, productos, energía…) y su relación con el tema del visitante.
- **Veredicto de revisión**: el resultado de revisar una respuesta antes de mostrarla. Incluye los problemas detectados
  (hecho externo, contacto, promesa, cita, repetición) y la acción tomada (mostrar, corregir o usar el respaldo).
- **Conversación simulada**: una conversación de varios turnos con un perfil de visitante, su transcripción y sus
  calificaciones de naturalidad, empatía, pertinencia y garantías.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En conversaciones de 10 turnos, ninguna respuesta repite en más de la mitad de su texto otra respuesta del
  mismo hilo.
- **SC-002**: Al enviar el mismo mensaje fuera de tema en 10 hilos nuevos, se obtienen al menos 8 respuestas distintas
  entre sí, y todas respetan el límite.
- **SC-003**: Ninguna recomendación se repite dentro de un hilo, y en una conversación con varios temas ajenos hay como
  máximo una recomendación cada dos turnos.
- **SC-004**: Hay 0 recomendaciones en turnos con visitantes molestos, en despedidas o después de un rechazo explícito.
- **SC-005**: El 100 % de las respuestas de la evaluación está libre de hechos externos verificables, contactos no
  oficiales y promesas de precio o compromiso.
- **SC-006**: Se mantienen el 100 % de las crisis atendidas con la Línea 106 y el 123, la batería de conducta en 24/24
  sin fugas y los criterios estrictos de la batería de atención de la spec 019.
- **SC-007**: El promedio de naturalidad, empatía y pertinencia es de al menos 4 sobre 5, tanto en la calificación
  automática como en la humana del equipo, y supera al del modo de guiones.
- **SC-008**: El 90 % de los comentarios sociales recibe una respuesta que acompaña el comentario, sin lenguaje de
  rechazo.
- **SC-009**: El 90 % de las respuestas a mensajes mínimos tiene como máximo dos frases.
- **SC-010**: El 100 % de las correcciones del visitante se atiende sin volver a pedir aclaración, y el 80 % de las
  referencias a turnos anteriores se conecta correctamente.
- **SC-011**: En el 90 % de los turnos, el visitante ve la primera palabra en menos de 3 segundos.
- **SC-012**: Cuando el modelo de lenguaje no está disponible, el 100 % de los turnos recibe una respuesta coherente,
  sin error visible.

## Assumptions

- **Conversación social permitida**: Valer-IA puede saludar, empatizar, bromear con ligereza y comentar en términos
  generales y no verificables («qué rico un día soleado»). Todo lo que se pueda verificar como dato (cifras, fechas,
  resultados, nombres, pronósticos, precios, noticias) cuenta como hecho externo y se declina. Esta frontera precisa el
  límite de la Constitución §10 y debe quedar registrada en ella y en un ADR.
- El proveedor de lenguaje actual (DeepSeek) es suficiente. No se cambia de proveedor ni se usa un modelo de
  razonamiento, por la latencia.
- Los guiones de `prompts/care.md` se conservan como guía de estilo y como respaldo. El modo de guiones de la spec 019
  sigue disponible como línea base.
- La recomendación se elige del corpus oro ya existente. No se regeneran ni modifican las capas de datos.
- La memoria del hilo vive con el hilo y se borra con él. No se crea un perfil persistente del visitante.
- Las conversaciones simuladas usan el mismo proveedor de lenguaje para el papel del visitante, y la calificación
  automática usa una rúbrica fija. Ambas se ejecutan solo en modo real; el modo de demostración usa visitantes y
  calificaciones guionados.
- El costo adicional por más llamadas al modelo es aceptable para el alcance académico del proyecto.
- La meta de 3 segundos para la primera palabra se mide con la conexión y el proveedor habituales del equipo.

## Dependencies

- Spec 014 (agente con memoria y enrutador): la nueva decisión del turno extiende la del enrutador.
- Spec 018 (Valer-IA Caña): identidad, límites de conducta, privacidad y aviso de datos sensibles.
- Spec 019 (habilidades de call center): guiones, detección de emociones, crisis, registro del contacto y batería de
  atención, que pasan a ser guía, respaldo y línea base.
- Corpus oro con las unidades citables que alimentan las recomendaciones.
- Constitución §3.7 y §10: deben actualizarse con la política de tres niveles y el nuevo principio de redacción guiada.
