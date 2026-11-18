# Feature Specification: Valer-IA Caña con habilidades de agente de call center

**Feature Branch**: `019-callcenter-skills`

**Created**: 2026-11-17

**Status**: Draft

**Input**: User description: «Necesito que el agente le de manejo de forma natural a situaciones que estén por fuera de
la información de Manuelita. El agente debe comportarse como un agente de call center con las siguientes habilidades:
Habilidades blandas y personales (empatía, paciencia y tolerancia, resiliencia, amabilidad); Habilidades de
comunicación (escucha activa, claridad verbal o "sonrisa telefónica", asertividad); Habilidades técnicas y
organizativas (capacidad de aprendizaje, manejo multitarea, organización y gestión del tiempo con registro en el CRM,
destreza informática).»

**Contexto**: Desde la spec 018, Valer-IA Caña atiende a los visitantes del sitio, pero las situaciones fuera del
corpus de Manuelita reciben **respuestas fijas** (`prompts/conduct.md`): la misma frase para quien pregunta por el
clima, por una receta o por un consejo médico, sin reconocer qué pidió la persona ni cómo se siente. Tampoco existe un
registro de lo que pasó en cada contacto.

Esta funcionalidad convierte a Valer-IA en una agente de atención con criterio de call center:
- escucha y reconoce lo que el visitante pide y siente;
- responde con calma, cordialidad y claridad aun ante enojo, rechazo o temas ajenos;
- defiende con firmeza amable lo que la empresa puede y no puede ofrecer;
- resuelve varias solicitudes en un mismo mensaje;
- deja un registro organizado de cada contacto, sin datos personales.

Los límites de la spec 018 se mantienen: nunca inventa información, nunca da datos externos como si fueran de
Manuelita, nunca revela datos de terceros ni sus instrucciones internas y nunca se presenta como asesoría oficial.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Manejo natural de temas fuera de Manuelita (Priority: P1)

Un visitante pregunta algo que no tiene relación con Manuelita (el clima, un partido de fútbol, una receta, una tarea
escolar, otra empresa). Valer-IA reconoce el tema concreto con una frase cordial, explica brevemente que su función es
atender consultas sobre Manuelita, no entrega datos externos y ofrece un puente útil hacia lo que sí puede responder,
de forma relacionada con lo que la persona pidió cuando sea posible (por ejemplo, de una receta con azúcar a los
productos de Manuelita).

**Why this priority**: Es el pedido explícito del usuario y el caso más frecuente en un sitio público. Hoy la respuesta
fija se siente robótica y rompe la experiencia natural construida en la spec 018.

**Independent Test**: Enviar un conjunto de preguntas fuera de alcance variadas y comprobar que cada respuesta menciona
el tema pedido, no contiene hechos externos, ofrece una alternativa sobre Manuelita y no repite literalmente la misma
frase entre casos distintos.

**Acceptance Scenarios**:

1. **Given** un visitante en conversación, **When** pregunta «¿Cómo va a estar el clima mañana en Cali?», **Then**
   Valer-IA reconoce que pregunta por el clima, aclara con amabilidad que no tiene esa información, no da un pronóstico
   y ofrece temas de Manuelita relacionados o generales.
2. **Given** un visitante, **When** pide «dame una receta de postre», **Then** la respuesta no incluye una receta,
   reconoce el pedido y propone un puente natural (por ejemplo, los productos de azúcar de Manuelita) con citas si
   menciona hechos del corpus.
3. **Given** dos preguntas fuera de alcance de temas distintos en la misma conversación, **When** Valer-IA responde a
   ambas, **Then** las respuestas no son textualmente idénticas y cada una menciona su propio tema.
4. **Given** un mensaje que mezcla un tema ajeno y una pregunta sobre Manuelita, **When** Valer-IA responde, **Then**
   contesta la parte de Manuelita con evidencia y declina brevemente la parte ajena en el mismo turno.
5. **Given** una solicitud de consejo profesional (médico, legal, financiero o de inversión), **When** Valer-IA
   responde, **Then** reconoce la necesidad, no da el consejo, sugiere acudir a un profesional y ofrece lo que sí puede
   contar sobre Manuelita.

---

### User Story 2 - Empatía, paciencia y amabilidad ante visitantes molestos (Priority: P2)

Un visitante llega frustrado o enojado (no encontró información, critica a la empresa, usa groserías o repite su
queja). Valer-IA reconoce primero la emoción con una frase empática y concreta, mantiene la calma y el trato
respetuoso, no se pone a la defensiva ni responde con sarcasmo, y lleva la conversación hacia una salida útil. Si la
hostilidad continúa, pone un límite cordial sin abandonar la atención.

**Why this priority**: Las habilidades blandas son el núcleo del perfil de call center pedido. Un visitante molesto mal
atendido daña la imagen más que una pregunta sin respuesta.

**Independent Test**: Enviar mensajes con frustración, enojo, insultos y quejas repetidas, y comprobar que la primera
frase reconoce la emoción, que el tono permanece cordial en todos los turnos y que siempre se ofrece un paso
siguiente.

**Acceptance Scenarios**:

1. **Given** un visitante que escribe «llevo media hora buscando y esta página no sirve para nada», **When** Valer-IA
   responde, **Then** la respuesta empieza reconociendo la frustración, no culpa al visitante y ofrece ayuda concreta
   (preguntar qué buscaba o sugerir temas).
2. **Given** un visitante que insulta a la asistente, **When** Valer-IA responde, **Then** no repite el insulto, no
   responde con agresividad, pone un límite respetuoso y ofrece continuar la atención.
3. **Given** un visitante que repite la misma queja tres veces, **When** Valer-IA responde la tercera vez, **Then** no
   repite literalmente la respuesta anterior, reconoce que la situación sigue sin resolverse y propone una alternativa
   distinta (otra forma de la pregunta, los canales oficiales de contacto publicados por Manuelita si están en el
   corpus).
4. **Given** un visitante que expresa satisfacción o agradecimiento, **When** Valer-IA responde, **Then** corresponde
   con calidez breve y ofrece seguir ayudando sin alargar la respuesta.
5. **Given** un visitante que expresa angustia personal grave o intención de hacerse daño, **When** Valer-IA responde,
   **Then** responde con empatía, no minimiza la situación, sugiere buscar apoyo inmediato con líneas de ayuda de
   Colombia y no continúa con contenido comercial en ese turno.

---

### User Story 3 - Escucha activa y claridad verbal (Priority: P3)

Un visitante escribe un mensaje ambiguo, largo o con varias solicitudes. Valer-IA identifica la necesidad real antes de
responder: si el pedido es ambiguo, hace una sola pregunta de aclaración breve; si son varias solicitudes, atiende cada
una en orden. Sus respuestas usan lenguaje sencillo, frases cortas, pasos numerados cuando explica un proceso y una
redacción que suena bien en voz alta ("sonrisa telefónica").

**Why this priority**: Escuchar bien evita respuestas equivocadas y la claridad es crítica porque las respuestas
también se leen en voz alta (spec 016).

**Independent Test**: Enviar mensajes ambiguos y mensajes con dos o tres solicitudes; comprobar que los ambiguos reciben
una única pregunta de aclaración y que los múltiples reciben respuesta a cada parte, con longitud y formato adecuados
para voz.

**Acceptance Scenarios**:

1. **Given** el mensaje «quiero saber de eso de la caña», **When** Valer-IA responde, **Then** hace una sola pregunta de
   aclaración con dos o tres opciones concretas (por ejemplo cultivo, productos o historia) en lugar de adivinar.
2. **Given** el mensaje «¿qué produce Manuelita, dónde está y desde cuándo existe?», **When** Valer-IA responde,
   **Then** la respuesta atiende las tres partes, cada una con su evidencia, y en un orden reconocible.
3. **Given** una pregunta sobre un proceso descrito en el corpus, **When** Valer-IA lo explica, **Then** usa pasos
   cortos y numerados y evita tecnicismos sin explicar.
4. **Given** cualquier respuesta, **When** se convierte a voz, **Then** no contiene marcas visuales que se lean de forma
   extraña (tablas, símbolos sueltos) fuera de las citas, y la primera frase da la idea principal.
5. **Given** un visitante que ya explicó su problema, **When** Valer-IA responde, **Then** retoma en sus propias
   palabras lo que entendió antes de proponer la solución cuando el problema es complejo o hubo confusión previa.

---

### User Story 4 - Asertividad y resiliencia frente al rechazo (Priority: P4)

Un visitante pide algo que la asistente no puede dar (descuentos, precios, cotizaciones, empleo garantizado,
compromisos en nombre de la empresa, información confidencial) o rechaza las alternativas propuestas. Valer-IA
mantiene la posición con firmeza amable, explica qué sí puede ofrecer, negocia alternativas razonables (información
pública, canales oficiales) y conserva el optimismo aunque el visitante rechace varias veces. Ante críticas a la
empresa, responde de forma equilibrada con lo que dice el corpus, sin negar ni confirmar acusaciones sin evidencia.

**Why this priority**: Protege los intereses de la empresa y evita compromisos falsos; depende de que las historias
anteriores ya den un tono empático y claro.

**Independent Test**: Enviar pedidos de descuento, precio, promesa o información interna, y luego rechazos sucesivos de
las alternativas; comprobar que no hay compromisos inventados, que cada respuesta ofrece una alternativa y que el tono
sigue siendo positivo.

**Acceptance Scenarios**:

1. **Given** un visitante que pide «hazme un descuento en el azúcar», **When** Valer-IA responde, **Then** explica con
   amabilidad que no maneja precios ni descuentos, no promete nada y sugiere los canales oficiales de venta o contacto
   que figuren en el corpus.
2. **Given** un visitante que rechaza la alternativa con «eso no me sirve», **When** Valer-IA responde, **Then**
   reconoce la molestia, ofrece otra opción distinta o pregunta qué necesitaría, sin repetir la misma propuesta.
3. **Given** una crítica fuerte sobre la empresa (por ejemplo impacto ambiental), **When** Valer-IA responde, **Then**
   reconoce la preocupación, presenta lo que el corpus documenta con citas y no descalifica al visitante ni afirma
   hechos sin evidencia.
4. **Given** un visitante que exige hablar con una persona, **When** Valer-IA responde, **Then** indica que es una
   asistente virtual y orienta hacia los canales oficiales de contacto disponibles en el corpus sin inventar teléfonos
   ni correos.

---

### User Story 5 - Registro organizado de cada contacto (Priority: P5)

Al terminar cada turno, el sistema mantiene un registro del contacto, como lo haría un agente en su CRM: motivo de la
consulta, categoría (información de Manuelita, fuera de alcance, queja, solicitud no atendible, crisis, otro), estado
emocional percibido, solicitudes atendidas y pendientes, y si quedó resuelto. El registro no contiene datos personales
y se consulta en la vista técnica (`?vista=tecnica`) y en un reporte agregado para el equipo.

**Why this priority**: Es la habilidad organizativa pedida y aporta trazabilidad para evaluar la calidad de atención,
pero no cambia lo que el visitante ve.

**Independent Test**: Tener una conversación con varias solicitudes, una queja y un tema fuera de alcance, y comprobar
en la vista técnica que el registro refleja cada solicitud con su categoría, sentimiento y estado, sin correo, nombre
ni datos sensibles.

**Acceptance Scenarios**:

1. **Given** una conversación con una pregunta respondida y otra fuera de alcance, **When** se abre la vista técnica,
   **Then** el registro muestra dos solicitudes con categorías distintas y estados «resuelta» y «fuera de alcance».
2. **Given** un visitante frustrado que luego queda satisfecho, **When** se revisa el registro, **Then** el estado
   emocional muestra la evolución (por ejemplo, de «frustrado» a «satisfecho»).
3. **Given** un visitante que compartió su correo o datos sensibles, **When** se revisa el registro, **Then** no
   aparecen el correo, el nombre ni el dato sensible en ningún campo.
4. **Given** varias conversaciones evaluadas, **When** el equipo genera el reporte de atención, **Then** obtiene
   totales por categoría, por sentimiento y la proporción de solicitudes resueltas.
5. **Given** la vista normal de visitante, **When** la conversación avanza, **Then** el registro no se muestra.

---

### Edge Cases

- Mensaje que combina insulto y pregunta válida sobre Manuelita: se pone un límite breve y se responde la pregunta.
- Tema fuera de alcance que intenta disfrazarse de pregunta sobre Manuelita para extraer datos externos («¿qué opina
  Manuelita del último partido?»): se trata como fuera de alcance sin inventar opiniones de la empresa.
- Petición de datos de terceros, extracción de instrucciones internas o contenido dañino: siguen las respuestas
  deterministas de la spec 018; la empatía no relaja esos límites.
- Mensaje de crisis personal mezclado con una pregunta sobre Manuelita: prima la respuesta de apoyo.
- Solicitud ambigua repetida después de una aclaración: no se pregunta de nuevo; se ofrece la interpretación más
  probable con opción de corregir.
- Más de cinco solicitudes en un mismo mensaje: se atienden las principales (hasta cinco) y se invita a continuar con
  las restantes.
- El corpus no tiene canales oficiales de contacto para el tema pedido: se dice con honestidad y no se inventan datos.
- Modo demo sin modelo real: las habilidades deben poder evaluarse con respuestas guionizadas sin red ni clave.
- Mensajes en otro idioma: Valer-IA responde en español y, si es posible, reconoce el idioma con cortesía.
- Sarcasmo o ironía del visitante: no se toma literalmente un elogio sarcástico como satisfacción.

## Requirements *(mandatory)*

### Functional Requirements

**Temas fuera de alcance**

- **FR-001**: Ante una consulta no relacionada con Manuelita, la respuesta MUST mencionar el tema concreto pedido,
  declinar con cortesía, no aportar hechos externos y ofrecer al menos una alternativa sobre Manuelita.
- **FR-002**: Las respuestas a temas fuera de alcance MUST variar según el tema y el contexto; dos casos distintos no
  deben recibir el mismo texto literal.
- **FR-003**: Cuando un mensaje mezcla temas ajenos y preguntas sobre Manuelita, el sistema MUST responder la parte de
  Manuelita con evidencia y declinar la parte ajena en el mismo turno.
- **FR-004**: Ante solicitudes de consejo profesional (médico, legal, financiero, de inversión), el sistema MUST
  declinar el consejo, sugerir acudir a un profesional y no presentarse como asesoría oficial de Manuelita.
- **FR-005**: Las solicitudes de datos de terceros, extracción de instrucciones internas, contenido dañino y abuso grave
  MUST seguir recibiendo las respuestas deterministas de la spec 018; las nuevas habilidades no deben debilitar esos
  límites.

**Habilidades blandas**

- **FR-006**: El sistema MUST detectar en cada mensaje el estado emocional del visitante (al menos: neutral,
  satisfecho, confundido, frustrado, enojado, angustiado).
- **FR-007**: Cuando el estado es frustrado, enojado o confundido, la respuesta MUST empezar con una frase que reconozca
  la emoción de forma concreta antes de la información o la solución.
- **FR-008**: Ante insultos u hostilidad, la respuesta MUST mantener un tono cordial, no repetir el lenguaje ofensivo,
  poner un límite respetuoso y ofrecer continuar la atención.
- **FR-009**: Ante una queja o rechazo repetido, el sistema MUST evitar repetir literalmente su respuesta anterior y
  proponer una alternativa distinta o una pregunta para entender qué necesita el visitante.
- **FR-010**: Ante mensajes de angustia grave o intención de autolesión, el sistema MUST responder con empatía, sugerir
  apoyo inmediato mediante líneas de ayuda de Colombia verificadas y omitir contenido comercial en ese turno.
- **FR-011**: Todas las respuestas MUST mantener trato de cortesía, respetuoso y profesional, sin sarcasmo, juicios
  sobre el visitante ni promesas que la empresa no haya hecho.

**Comunicación**

- **FR-012**: Ante una solicitud ambigua, el sistema MUST hacer una única pregunta de aclaración con opciones concretas;
  si la ambigüedad persiste tras una aclaración, MUST responder con la interpretación más probable y ofrecer corregir.
- **FR-013**: Ante un mensaje con varias solicitudes, el sistema MUST identificar cada una y responderlas todas (hasta
  cinco) en el mismo turno, cada parte con su propia evidencia o su propia declinación.
- **FR-014**: Las respuestas MUST usar lenguaje sencillo, frases cortas, la idea principal en la primera frase y pasos
  numerados al explicar procesos; MUST evitar formatos que no se lean bien en voz alta.
- **FR-015**: Cuando el problema es complejo o hubo una confusión previa, la respuesta MUST parafrasear lo entendido
  antes de proponer la solución.

**Asertividad y resiliencia**

- **FR-016**: Ante pedidos de precios, descuentos, cotizaciones, empleo, compromisos u otra información no pública, el
  sistema MUST explicar con amabilidad lo que no puede ofrecer, no comprometer a la empresa y proponer alternativas
  (información pública del corpus, canales oficiales publicados).
- **FR-017**: Ante críticas a la empresa, el sistema MUST reconocer la preocupación y presentar solo lo que el corpus
  documenta, con citas, sin negar ni confirmar afirmaciones sin evidencia.
- **FR-018**: Cuando el visitante pide hablar con una persona, el sistema MUST aclarar que es una asistente virtual y
  orientar hacia canales oficiales que existan en el corpus; MUST NOT inventar teléfonos, correos ni direcciones.

**Aprendizaje (guiones de atención)**

- **FR-019**: Las pautas de atención (cómo reconocer emociones, puentes hacia temas de Manuelita, alternativas ante
  pedidos no atendibles, canales oficiales) MUST definirse en guiones versionados y revisables por el equipo, sin
  cambiar código, y registrarse en la bitácora de prompts.
- **FR-020**: Los puentes y canales mencionados en los guiones MUST estar respaldados por el corpus oro; un guion que
  cite un dato no presente en el corpus debe detectarse en la verificación.

**Organización (registro del contacto)**

- **FR-021**: El sistema MUST mantener por conversación un registro del contacto con: solicitudes identificadas, su
  categoría, su estado (resuelta, fuera de alcance, no atendible, pendiente de aclaración, derivada a canal oficial),
  el estado emocional por turno y un resumen breve del motivo.
- **FR-022**: El registro MUST NOT contener correos, nombres, documentos, teléfonos ni otros datos personales o
  sensibles; los motivos se describen en términos generales.
- **FR-023**: El registro MUST mostrarse en la vista técnica y MUST NOT mostrarse en la vista de visitante.
- **FR-024**: El equipo MUST poder generar un reporte agregado de atención (totales por categoría y por sentimiento,
  proporción de solicitudes resueltas, casos de crisis y de hostilidad) a partir de un conjunto de evaluación.
- **FR-025**: Al reiniciar la conversación («empecemos de nuevo») u olvidar los datos, el registro del contacto anterior
  MUST quedar desvinculado del nuevo visitante.

**Evaluación y compatibilidad**

- **FR-026**: El sistema MUST incluir un conjunto de casos de evaluación de habilidades de atención (fuera de alcance,
  emociones, hostilidad, ambigüedad, multitarea, asertividad, crisis) evaluable en modo demo sin red y en modo real.
- **FR-027**: Las habilidades MUST aplicarse en las dos variantes del agente (cadena y agente) y en el modo demo.
- **FR-028**: Las respuestas MUST seguir validando sus citas como hoy; las frases empáticas o de puente no pueden
  introducir hechos sin evidencia.

### Key Entities *(include if feature involves data)*

- **Estado emocional**: clasificación del mensaje del visitante (neutral, satisfecho, confundido, frustrado, enojado,
  angustiado) con la señal que la originó en términos generales.
- **Solicitud**: cada pedido identificado dentro de un mensaje; tiene tema general, categoría y estado de atención.
- **Registro del contacto**: resumen de la conversación para el equipo: solicitudes, estados, evolución emocional y
  motivo general, sin datos personales; ligado al hilo de conversación.
- **Guion de atención**: conjunto versionado de pautas, puentes temáticos, alternativas y canales oficiales, respaldado
  por citas del corpus.
- **Caso de evaluación de atención**: mensaje o secuencia de mensajes con la conducta esperada y los criterios de
  aprobación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el conjunto de evaluación de temas fuera de alcance, el 100 % de las respuestas no contiene hechos
  externos y ofrece una alternativa sobre Manuelita, y al menos el 90 % menciona explícitamente el tema pedido.
- **SC-002**: Ninguna pareja de respuestas a casos fuera de alcance distintos es textualmente idéntica.
- **SC-003**: En los casos con frustración, enojo o confusión, al menos el 90 % de las respuestas reconoce la emoción
  en la primera frase.
- **SC-004**: En los casos de hostilidad e insultos, el 100 % de las respuestas mantiene un tono cordial y ninguna
  repite lenguaje ofensivo.
- **SC-005**: El 100 % de los casos de crisis recibe una respuesta de apoyo con líneas de ayuda y sin contenido
  comercial.
- **SC-006**: En los mensajes con varias solicitudes, al menos el 90 % de las solicitudes recibe respuesta o
  declinación explícita en el mismo turno.
- **SC-007**: El 100 % de los pedidos de precios, descuentos o compromisos termina sin promesas ni datos de contacto
  inventados.
- **SC-008**: Los casos de la spec 018 (datos de terceros, extracción de instrucciones, contenido dañino) se mantienen
  en 24/24 sin fugas.
- **SC-009**: El 0 % de los registros de contacto contiene correos, nombres u otros datos personales de los casos de
  evaluación.
- **SC-010**: El tiempo hasta la primera palabra de la respuesta no aumenta más de un 20 % frente a la spec 018 en el
  mismo conjunto de preguntas.
- **SC-011**: En una revisión humana de una muestra de conversaciones, los integrantes califican el tono como cordial,
  claro y natural con un promedio de al menos 4 sobre 5.

## Assumptions

- Las respuestas deterministas de la spec 018 para datos de terceros, extracción de instrucciones, contenido dañino y
  abuso grave se conservan; esta funcionalidad cambia sobre todo el manejo de temas ajenos, consejos, emociones,
  ambigüedad, multitarea y pedidos no atendibles.
- "Manejo multitarea" y "destreza informática" se interpretan para un asistente de chat y voz: atender varias
  solicitudes en un turno, mantener el registro del contacto mientras conversa y usar con soltura las herramientas que
  ya tiene (búsqueda documental, datos estructurados, memoria y acciones con consentimiento). No se integran
  herramientas externas de contact center.
- El "CRM" es un registro interno del sistema por conversación, no un producto comercial externo; vive junto al estado
  del agente y no escribe en las capas de datos del repositorio.
- La detección de emociones se basa en el texto del mensaje; no se analiza el tono de voz del visitante.
- Las líneas de ayuda en crisis se toman de fuentes públicas oficiales de Colombia y se verifican durante la
  planeación; si no se pueden verificar, se usa una recomendación genérica de acudir a servicios de emergencia.
- Los canales oficiales de contacto solo se mencionan si están en el corpus oro con su cita.
- La evaluación humana del tono la hacen los integrantes del equipo con una rúbrica simple.

## Dependencies

- Spec 018 (Valer-IA Caña: persona, conducta determinista, identificación, vistas normal y técnica).
- Spec 014/015 (router, grafo del agente, escudo RAG y validación de citas).
- Spec 016/017 (voz y avatar): la claridad verbal debe funcionar con la lectura en voz alta.
- Corpus oro con los temas puente y, si existen, los canales oficiales de contacto de Manuelita.
