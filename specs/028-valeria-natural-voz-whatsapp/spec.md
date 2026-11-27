# Feature Specification: Valer-IA natural y con voz por WhatsApp, abierta el día de la sustentación

**Feature Branch**: `028-valeria-natural-voz-whatsapp`

**Created**: 2026-11-26

**Status**: Draft

**Input**: User description: "Valer-IA natural y conversacional por WhatsApp, con voz en español e inglés,
planificador abierto y automático y acceso abierto el día de la sustentación (Módulo 3, sábado 28-nov-2026
8:00). Continúa la spec 024 y las 025/027. Decisiones ya tomadas: número dedicado (SIM prepago que se
desactiva tras la prueba); cualquier número puede escribir el día de la prueba y en el ensayo del viernes, sin
límite de mensajes; conversación sin comandos; notas de voz obligatorias (voz natural, fuentes en el texto),
en español e inglés; planificador abierto para todos y activado por contexto; el MCP vuelve a 15 herramientas
de lectura; nueva medición de las 20 herramientas de atención."

## Contexto

La spec 024 llevó a Valer-IA Caña a WhatsApp a través de un gateway con un puente propio, con acceso por lista
de números y emparejamiento, y un conjunto de comandos (`/ayuda`, `/nuevo`, `/olvidar`, `/traza`, `/perfil`,
`/cancelar`) para las acciones del canal. Las specs 025 y 027 sumaron el perfil planificador industrial (datos
sintéticos), abierto en la web y restringido en WhatsApp.

Para la sustentación del Módulo 3 (sábado 28 de noviembre de 2026, 8:00, demo desde el teléfono de un
invitado), el equipo decidió que la experiencia por WhatsApp sea la de hablar con una persona: sin comandos,
con voz cuando el invitado habla, en su idioma, y abierta a cualquiera que tenga el número. Esta spec define
ese comportamiento y reemplaza tres decisiones previas: el acceso por lista + emparejamiento (spec 024), la
autorización del planificador fuera de la web (ADR 0031, spec 027) y las herramientas de planificación
expuestas en el servidor de herramientas del modo degradado (spec 025).

## Clarifications

### Session 2026-11-26

- Q: ¿Número personal o dedicado? → A: Dedicado: una SIM prepago exclusiva para Valer-IA, que se desactiva
  después de la prueba del sábado. El número nunca se versiona.
- Q: ¿Quién puede escribirle el día de la prueba? → A: Cualquier número, sin aprobación ni emparejamiento,
  durante el ensayo del viernes por la tarde y la jornada del sábado. Antes y después, solo números de prueba.
- Q: ¿Límite de mensajes por persona? → A: No. Sin límite.
- Q: ¿Comandos para el usuario? → A: Ninguno necesario ni anunciado; todo por contexto. Pueden quedar atajos
  ocultos del operador.
- Q: ¿Plan B si la voz no funciona? → A: No hay plan B de solo texto: el sábado Valer-IA responde con voz.
- Q: ¿Qué dice la nota de voz? → A: Un guion natural y conversacional; las citas y las fuentes van solo en el
  mensaje de texto que la acompaña.
- Q: ¿Idiomas de voz? → A: Español e inglés: responde por voz en el idioma en que le hablaron.
- Q: ¿Quién accede al planificador? → A: Todas las personas, en la web y en WhatsApp; se activa por contexto,
  por turno, con continuidad en la repregunta siguiente.
- Q: ¿Planificación en el modo degradado? → A: No: el servidor de herramientas del modo degradado vuelve a las
  15 herramientas de lectura de atención.
- Q: ¿Qué herramientas se miden? → A: Las 20 de atención; la planificación se presenta con su evaluación
  propia («20 de atención + 6 de planificación = 26»).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El invitado le habla a Valer-IA con una nota de voz y ella le responde con voz (Priority: P1)

Un invitado del jurado, con su propio teléfono, graba una nota de voz en español o en inglés preguntando por
Manuelita. Valer-IA le responde con una nota de voz natural, en el mismo idioma, como lo haría una persona, y
además con un mensaje de texto que trae la respuesta completa con sus citas y fuentes.

**Why this priority**: Es el momento central de la demo y la decisión del equipo es que el sábado se responda
con voz sin alternativa. Además demuestra la memoria, el razonamiento y las citas en un solo gesto.

**Independent Test**: Desde un teléfono habilitado, enviar una nota de voz en español y otra en inglés con
preguntas del corpus; verificar que llegan, para cada una, una nota de voz en el idioma correcto sin citas ni
URLs habladas y un mensaje de texto con citas y fuentes.

**Acceptance Scenarios**:

1. **Given** un invitado con acceso, **When** envía una nota de voz en español («¿Qué produce Manuelita?»),
   **Then** recibe una nota de voz en español con una respuesta conversacional y un mensaje de texto con la
   respuesta, las citas numeradas y el bloque de fuentes.
2. **Given** un invitado con acceso, **When** envía una nota de voz en inglés, **Then** la transcripción, la
   respuesta y la nota de voz están en inglés, con la misma regla de fuentes en el texto.
3. **Given** una respuesta con cifras y citas, **When** se genera la nota de voz, **Then** la voz no pronuncia
   etiquetas de cita, números de fuente, URLs, símbolos de formato ni el bloque de fuentes, y expresa las
   cifras de forma natural.
4. **Given** un invitado que escribe en texto, **When** pregunta algo, **Then** recibe solo texto (sin nota de
   voz).
5. **Given** un invitado que envió audio, **When** dice «respóndeme por escrito» (o en inglés «text me»),
   **Then** las siguientes respuestas de esa conversación llegan solo en texto hasta que pida audio de nuevo;
   y si escribe «mándame audio», recibe voz aunque haya preguntado por texto.
6. **Given** una nota de voz inaudible, vacía o demasiado larga, **When** llega, **Then** Valer-IA lo dice con
   naturalidad y pide repetir, sin inventar una pregunta.

---

### User Story 2 - Conversación natural, sin comandos (Priority: P1)

Cualquier persona conversa con Valer-IA como con una asesora: la saluda, pregunta qué sabe hacer, cambia de
tema, pide empezar de nuevo, pide que olvide sus datos o confirma una acción, todo con sus propias palabras.
Valer-IA nunca le pide ni le sugiere comandos.

**Why this priority**: Los invitados no conocen comandos; una sola instrucción tipo «/ayuda» rompe la
experiencia que el equipo quiere mostrar.

**Independent Test**: Con un guion de mensajes naturales (saludo, «¿qué puedes hacer?», cambio de tema,
«empecemos de nuevo», «olvida lo que sabes de mí», confirmaciones y negaciones coloquiales), verificar que
cada acción ocurre y que ninguna respuesta menciona un comando.

**Acceptance Scenarios**:

1. **Given** el primer mensaje de una persona («hola»), **When** Valer-IA responde, **Then** se presenta en
   una o dos frases con lo que puede hacer, en tono conversacional, sin listar comandos.
2. **Given** una conversación sobre un tema, **When** la persona pregunta por otro tema, **Then** Valer-IA
   responde el tema nuevo sin pedir que reinicie nada.
3. **Given** una conversación en curso, **When** la persona dice «empecemos de nuevo» (o equivalente),
   **Then** Valer-IA confirma con naturalidad y la conversación siguiente no arrastra el contexto anterior,
   conservando lo que la persona aprobó que recordara.
4. **Given** datos guardados de la persona, **When** dice «olvida lo que sabes de mí», **Then** Valer-IA pide
   confirmación con naturalidad y, al confirmar, olvida los datos.
5. **Given** una acción pendiente de confirmación, **When** la persona responde «dale», «sí, guárdalo»,
   «claro», «mejor no» o «déjalo así», **Then** la acción se ejecuta o se cancela según la intención.
6. **Given** una acción pendiente, **When** la respuesta es ambigua o habla de otra cosa, **Then** Valer-IA
   vuelve a preguntar por la acción en una frase (o atiende la pregunta nueva y recuerda que la acción sigue
   pendiente), y nunca la ejecuta sin una confirmación clara.
7. **Given** cualquier respuesta de Valer-IA por WhatsApp, **When** se revisa su texto, **Then** no contiene
   la sugerencia de escribir un comando.

---

### User Story 3 - Cualquier persona puede escribirle el día de la prueba (Priority: P1)

El día de la prueba (y en el ensayo del viernes por la tarde), cualquier persona que tenga el número dedicado
de Valer-IA le escribe y recibe respuesta de inmediato, sin códigos ni aprobaciones del equipo. Antes y después
de esa ventana solo responden los números de prueba del equipo, y tras el sábado el número se desactiva.

**Why this priority**: La demo depende de que un invitado cualquiera escriba desde su teléfono sin preparación.

**Independent Test**: Con el modo abierto activo, escribir desde un teléfono que nunca ha escrito y recibir
respuesta; con el modo cerrado, comprobar que ese mismo teléfono no recibe respuesta.

**Acceptance Scenarios**:

1. **Given** el modo abierto activo, **When** un número desconocido escribe por primera vez, **Then** recibe
   respuesta sin pasos previos.
2. **Given** el modo cerrado, **When** escribe un número que no es de prueba, **Then** no recibe respuesta y el
   intento queda registrado sin el número en claro.
3. **Given** el modo abierto, **When** alguien escribe desde un grupo, **Then** Valer-IA no responde (grupos
   deshabilitados).
4. **Given** el modo abierto, **When** una persona envía muchos mensajes seguidos, **Then** todos se atienden
   en orden, sin límite, y los mensajes que llegan mientras otro se procesa no se pierden.
5. **Given** el modo abierto, **When** se revisa el registro, **Then** las personas aparecen solo con
   seudónimo.

---

### User Story 4 - El planificador se activa solo cuando la conversación lo pide (Priority: P2)

Cualquier persona, en WhatsApp o en la web, puede plantear un problema de planificación de producción («este
mes tenemos 15 % menos caña, ¿cómo cumplimos los compromisos?») y Valer-IA responde como planificador
industrial, con los datos sintéticos y el aviso correspondiente, sin que la persona cambie de perfil. Las
preguntas parecidas que no son de planificación siguen yendo a la atención general.

**Why this priority**: Muestra el razonamiento y las herramientas de planificación en la demo sin comandos;
depende de las historias 1 a 3 para el canal.

**Independent Test**: Con 15 frases de planificación y 15 parecidas que no lo son, medir cuántas activan el
planificador; y comprobar que una repregunta («¿y si baja 20 %?») sigue en el planificador.

**Acceptance Scenarios**:

1. **Given** cualquier persona en WhatsApp o en la web, **When** plantea una consulta de planificación,
   **Then** la respuesta usa el planificador, declara que los datos son sintéticos y que el equipo de planta
   decide.
2. **Given** una respuesta de planificación, **When** el siguiente mensaje es una repregunta del mismo
   escenario, **Then** también la atiende el planificador.
3. **Given** una pregunta sobre programas sociales o producción histórica («¿qué programas tiene Manuelita con
   cultivadores de caña?»), **When** se enruta, **Then** no activa el planificador.
4. **Given** el planificador activo en un turno, **When** la persona vuelve a un tema general, **Then**
   Valer-IA responde como antes, sin quedarse en planificación.

---

### User Story 5 - El modo degradado y las cifras del catálogo son coherentes (Priority: P3)

Si el backend de Valer-IA no está disponible, el agente de respaldo del gateway responde solo con las 15
herramientas de lectura de atención. Y la exactitud de selección de herramientas se mide de nuevo sobre las 20
herramientas de atención, con el discurso «20 de atención + 6 de planificación = 26».

**Why this priority**: Es evidencia para la discusión técnica; no cambia la experiencia del invitado.

**Independent Test**: Listar las herramientas del servidor del modo degradado (15) y correr la medición de 43
consultas en modo real.

**Acceptance Scenarios**:

1. **Given** el servidor de herramientas del modo degradado, **When** se listan sus herramientas, **Then** son
   exactamente las 15 de lectura de atención, sin herramientas de planificación.
2. **Given** las 43 consultas de evaluación, **When** se corre la medición en modo real, **Then** se reporta la
   exactitud sobre las 20 herramientas de atención y el número de búsquedas en mensajes triviales.
3. **Given** los documentos del proyecto, **When** se revisan, **Then** todos usan el mismo conteo de
   herramientas y la misma cifra de exactitud.

### Edge Cases

- Nota de voz en un idioma distinto de español o inglés: se transcribe si es posible y se responde en texto en
  español, invitando con naturalidad a hablar en español o inglés.
- Nota de voz mezclando idiomas: se responde en el idioma predominante.
- Respuesta muy larga para voz: la nota de voz resume en tono conversacional (máximo ~60 segundos) y el texto
  trae el detalle completo.
- Falla la síntesis de voz en un turno: llega el texto completo y una frase breve que pida disculpas por no
  enviar audio en ese momento; el incidente queda registrado para el operador.
- Falla la transcripción: Valer-IA pide con naturalidad que repita la pregunta o la escriba.
- Una persona envía audio mientras Valer-IA aún responde un mensaje anterior: se atiende después, en orden.
- Llega un sí/no sin acción pendiente: se trata como conversación normal.
- Una acción pendiente vence: si la persona confirma después, Valer-IA explica con naturalidad que la acción
  expiró y ofrece repetirla.
- «Empecemos de nuevo» dicho en medio de una acción pendiente: la acción se cancela y se avisa.
- Una frase con palabras de planificación pero intención informativa no activa el planificador.
- Los atajos ocultos del operador siguen funcionando, pero ninguna respuesta los anuncia.
- El modo abierto queda activo por error después del sábado: el número se desactiva de todos modos, y la
  documentación de cierre incluye volver al modo cerrado.

## Requirements *(mandatory)*

### Functional Requirements

**Voz (Historia 1)**

- **FR-001**: Valer-IA MUST aceptar notas de voz por WhatsApp, transcribirlas en el idioma hablado (español o
  inglés) y atenderlas igual que un mensaje de texto.
- **FR-002**: Cuando la pregunta llega por voz, Valer-IA MUST responder con una nota de voz y con un mensaje de
  texto; cuando llega por texto, MUST responder solo con texto.
- **FR-003**: La nota de voz MUST ser un guion conversacional derivado de la respuesta, sin etiquetas de cita,
  números de fuente, URLs, símbolos de formato ni bloque de fuentes, con cifras expresadas de forma natural y
  una duración máxima aproximada de 60 segundos.
- **FR-004**: El mensaje de texto que acompaña a la nota de voz MUST contener la respuesta con sus citas
  numeradas y el bloque de fuentes, con las mismas reglas de formato del canal de la spec 024.
- **FR-005**: La nota de voz MUST estar en el idioma de la pregunta: voz oficial en español y una voz en inglés
  para preguntas en inglés.
- **FR-006**: Valer-IA MUST respetar, por contexto y sin comandos, la preferencia de la persona de recibir solo
  texto o de recibir voz, y mantenerla en la conversación hasta que la cambie.
- **FR-007**: Si una nota de voz no se puede transcribir o no tiene habla, Valer-IA MUST pedir con naturalidad
  que la repita o la escriba, sin inventar contenido.
- **FR-008**: El audio recibido y el generado MUST tratarse como temporales: no se guardan después de
  responder ni se versionan.

**Conversación natural (Historia 2)**

- **FR-009**: Ningún mensaje de Valer-IA por WhatsApp MUST sugerir o requerir comandos.
- **FR-010**: Ante un saludo o una pregunta sobre sus capacidades, Valer-IA MUST presentarse en lenguaje
  natural, en una o dos frases.
- **FR-011**: Valer-IA MUST reconocer por contexto la intención de empezar una conversación nueva y abrir un
  hilo nuevo, conservando lo que la persona aprobó recordar.
- **FR-012**: Valer-IA MUST reconocer por contexto la intención de olvidar los datos de la persona y pedir
  confirmación antes de olvidarlos.
- **FR-013**: Las confirmaciones de acciones pendientes MUST aceptar expresiones naturales afirmativas y
  negativas en español e inglés; ante una respuesta ambigua, Valer-IA MUST volver a preguntar y nunca
  ejecutar sin confirmación clara.
- **FR-014**: Los comandos existentes MAY seguir funcionando como atajos del operador, pero no MUST aparecer
  en ningún texto dirigido a las personas.
- **FR-015**: La traza técnica del último turno MUST seguir disponible para el equipo durante la discusión
  técnica, sin que las personas la necesiten.

**Acceso abierto (Historia 3)**

- **FR-016**: El canal MUST ofrecer dos modos operables por el equipo sin cambiar el código: cerrado (solo
  números de prueba) y abierto (cualquier número, sin aprobación).
- **FR-017**: En modo abierto MUST seguir deshabilitado el uso en grupos.
- **FR-018**: El canal MUST no imponer un límite de mensajes por persona y MUST atender en orden los mensajes
  que llegan mientras se procesa otro de la misma persona.
- **FR-019**: Las personas MUST seguir registradas solo con seudónimo; ningún número de teléfono MUST quedar en
  el repositorio, en los registros ni en la documentación.
- **FR-020**: La documentación de operación MUST incluir el paso a paso para activar el modo abierto antes del
  ensayo y la prueba, volver al modo cerrado y desvincular el número tras el sábado.

**Planificador (Historia 4)**

- **FR-021**: El perfil planificador MUST estar disponible para todas las personas en la web y en WhatsApp.
- **FR-022**: Valer-IA MUST reconocer por contexto las consultas de planificación de producción y atenderlas
  con el planificador sin que la persona cambie de perfil.
- **FR-023**: La activación del planificador MUST aplicar al turno y a la repregunta inmediata del mismo
  escenario; después MUST volver al perfil de la conversación.
- **FR-024**: Las respuestas del planificador MUST declarar que los datos son sintéticos y que el equipo de
  planta decide.
- **FR-025**: El proyecto MUST incluir un conjunto de evaluación de la activación con al menos 15 consultas de
  planificación y 15 consultas parecidas que no lo son, con su resultado documentado.

**Coherencia técnica (Historia 5)**

- **FR-026**: El servidor de herramientas del modo degradado MUST exponer solo las 15 herramientas de lectura
  de atención.
- **FR-027**: La exactitud de selección de herramientas MUST medirse de nuevo en modo real sobre las 20
  herramientas de atención con las 43 consultas existentes, reportando también las búsquedas en mensajes
  triviales.
- **FR-028**: La documentación (catálogo, rúbrica, guion, constitución y decisiones) MUST quedar coherente con
  este alcance, incluidas las decisiones reemplazadas de las specs 024, 025 y 027.
- **FR-029**: Toda configuración manual del gateway que requiera esta spec MUST entregarse al equipo como
  instrucciones paso a paso antes de ejecutarse.

### Key Entities

- **Mensaje entrante**: texto o nota de voz de una persona; atributos: tipo, idioma detectado, transcripción
  (si es voz), seudónimo del remitente.
- **Respuesta del canal**: mensaje de texto (respuesta, citas, fuentes) y, si aplica, guion hablado y nota de
  voz en un idioma.
- **Preferencia de formato**: por conversación; texto, voz o «igual que la pregunta» (por defecto).
- **Acción pendiente**: escritura propuesta que espera confirmación natural; vence a los 10 minutos.
- **Modo de acceso del canal**: cerrado (números de prueba) o abierto (cualquiera); operado por el equipo.
- **Activación de planificación**: decisión por turno de usar el planificador, con continuidad en la
  repregunta inmediata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En la prueba con teléfonos ajenos, 10 de 10 notas de voz (al menos 3 en inglés) reciben nota de
  voz en el idioma correcto más el mensaje de texto con fuentes.
- **SC-002**: 0 notas de voz pronuncian etiquetas de cita, números de fuente, URLs o el bloque de fuentes.
- **SC-003**: La primera parte de la respuesta a una nota de voz llega en menos de 30 segundos en el 90 % de
  los casos de la prueba.
- **SC-004**: En el guion de conversación natural (al menos 15 mensajes que cubren saludo, capacidades, cambio
  de tema, empezar de nuevo, olvidar, confirmar y negar), el 100 % de las acciones ocurre sin comandos y 0
  respuestas sugieren un comando.
- **SC-005**: Ninguna acción pendiente se ejecuta con una respuesta ambigua en el conjunto de pruebas.
- **SC-006**: Con el modo abierto, 3 de 3 teléfonos que nunca habían escrito reciben respuesta en su primer
  mensaje; con el modo cerrado, 0 de 3.
- **SC-007**: La activación del planificador acierta en al menos 14 de 15 consultas de planificación y no se
  activa en al menos 14 de 15 consultas parecidas.
- **SC-008**: El servidor de herramientas del modo degradado expone exactamente 15 herramientas.
- **SC-009**: La exactitud de selección de herramientas queda medida y documentada sobre las 20 de atención,
  con 0 búsquedas en mensajes triviales; la meta es ≥ 90 %.
- **SC-010**: 0 números de teléfono, tokens o audios en el repositorio (escaneo de secretos en verde).
- **SC-011**: El sábado 28 antes de las 8:00, la verificación operativa de 3 minutos sale en verde y una
  pregunta por voz y otra por texto se responden desde un teléfono ajeno.

## Assumptions

- El equipo es un único portátil que hace de servidor (backend, gateway, base vectorial); queda conectado a la
  corriente y a internet durante la jornada.
- El número dedicado se activa en WhatsApp el 26 o 27 de noviembre y se vincula al gateway; se desactiva
  después del sábado 28.
- La transcripción y la voz se ejecutan localmente con los servicios de voz ya existentes del proyecto (specs
  016 y 023); para inglés se usa una voz local si existe y, si no, una voz en línea sin clave que ofrece el
  gateway.
- El modelo de lenguaje en la nube sigue siendo el mismo del proyecto; el costo de uso sin límite durante la
  ventana abierta es asumido por el equipo.
- La ruta técnica de la voz (configuración del gateway o envío del audio desde el puente) se decide con una
  prueba técnica temprana; ambas rutas cumplen los mismos requisitos.
- Las 43 consultas de evaluación de herramientas de la spec 024 siguen vigentes; las de planificación se
  evalúan aparte (spec 025).
- Los mensajes y la interfaz siguen en español; las respuestas van en el idioma de la persona.
- Fuera de alcance: Telegram, llamadas de voz, grupos, nuevas herramientas, cambios en la plataforma web más
  allá de la activación automática del planificador (la web es responsabilidad de Roberto y se le informa del
  cambio).

## Dependencies

- Spec 024 (canal y puente), specs 025 y 027 (perfiles y planificador), spec 016 (voz) y spec 023 (dictado).
- Tareas operativas pendientes de la spec 024 en el portátil servidor (instalación, vinculación, hardening,
  base vectorial) para probar extremo a extremo.
- Herramienta de conversión de audio instalada en el portátil servidor.
