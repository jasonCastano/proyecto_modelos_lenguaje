# Feature Specification: Saludo y presentación al iniciar una conversación

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (se acumula con las specs 028–031 del canal)
**Created**: 2026-11-27
**Status**: Draft
**Input**: User description: "he seguido haciendo pruebas a valeria y cuando valeria abre un nuevo chat no siempre
se está presentando. Necesito que cuando haya una nueva conversación, Valeria salude, describa brevemente su
propósito y continúe de forma natural atendiendo a la solicitud recibida sea por texto o por audio"

## Contexto

En las pruebas por WhatsApp, Valer-IA solo se presenta cuando el primer mensaje es un saludo («Hola») o una
pregunta sobre ella. Si la persona abre el chat con una pregunta directa («¿Qué produce Manuelita?») o con una
nota de voz, Valer-IA responde sin saludar ni decir quién es. Además, una persona que vuelve a escribir días
después continúa la conversación anterior sin ningún saludo. El resultado es una primera impresión
inconsistente: unas veces se presenta y otras no.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Primera pregunta directa, por texto (Priority: P1)

Una persona que nunca le ha escrito a Valer-IA abre el chat y escribe directamente una pregunta, sin saludar.
Valer-IA responde en un solo mensaje: un saludo breve, una o dos frases sobre quién es y para qué sirve, y a
continuación la respuesta a la pregunta, con sus fuentes, como en cualquier otro turno.

**Why this priority**: es el caso más frecuente en las pruebas y el que hoy falla: la persona no sabe con quién
habla ni qué más puede preguntar.

**Independent Test**: desde un número nuevo, enviar «¿Qué produce Manuelita?» y verificar que la respuesta
empieza con saludo y presentación breve y luego responde la pregunta con fuentes.

**Acceptance Scenarios**:

1. **Given** un número que nunca ha conversado con Valer-IA, **When** su primer mensaje es «¿Qué produce
   Manuelita?», **Then** la respuesta abre con un saludo y una presentación de una o dos frases, y continúa con
   la respuesta a la pregunta y sus fuentes, sin pedir que la persona repita la pregunta.
2. **Given** la misma conversación, **When** la persona envía una segunda pregunta, **Then** Valer-IA responde
   sin volver a saludar ni presentarse.
3. **Given** un número nuevo, **When** su primer mensaje es solo «Hola», **Then** Valer-IA saluda, se presenta
   brevemente e invita a preguntar (comportamiento actual, que se conserva).

---

### User Story 2 - Primera solicitud por nota de voz (Priority: P1)

Una persona nueva abre el chat con una nota de voz. La nota de voz de respuesta de Valer-IA empieza con el
saludo y la presentación breve y continúa con la respuesta; por escrito llegan solo las fuentes (spec 030).

**Why this priority**: la voz es la forma de entrada que más se mostró en las pruebas y la presentación debe
oírse, no solo leerse.

**Independent Test**: desde un número nuevo, enviar una nota de voz con una pregunta y verificar que el audio de
respuesta empieza con saludo y presentación y luego responde; el texto trae solo las fuentes.

**Acceptance Scenarios**:

1. **Given** un número nuevo, **When** su primer mensaje es una nota de voz con una pregunta, **Then** la nota
   de voz de respuesta abre con saludo y presentación breve, sigue con la respuesta y cierra como hoy; el texto
   acompañante trae solo las fuentes.
2. **Given** un número nuevo, **When** su primera nota de voz es solo un saludo, **Then** la respuesta en voz
   saluda, se presenta e invita a preguntar, sin texto duplicado.
3. **Given** una nota de voz en inglés como primer mensaje, **Then** el saludo, la presentación y la respuesta
   están en inglés.

---

### User Story 3 - Regreso después de un tiempo sin escribir (Priority: P2)

Una persona que ya conversó con Valer-IA vuelve a escribir después de un periodo largo sin actividad. Para ella
es un chat nuevo: Valer-IA la saluda de nuevo (por su nombre si lo aprobó guardar), recuerda en una frase para qué
sirve y atiende la solicitud, sin arrastrar el hilo anterior.

**Why this priority**: mejora la experiencia de quien vuelve, pero el impacto es menor que la primera impresión de
una persona nueva.

**Independent Test**: con un número que ya conversó, simular que pasó el periodo de inactividad y enviar una
pregunta; verificar el saludo de regreso, la presentación breve y la respuesta sin referencias a la conversación
anterior.

**Acceptance Scenarios**:

1. **Given** un número cuyo último mensaje fue hace más que el periodo de inactividad, **When** escribe una
   pregunta, **Then** Valer-IA saluda como en un chat nuevo, se presenta brevemente y responde; las preguntas de
   seguimiento («¿y en Perú?») ya no dependen del hilo anterior.
2. **Given** una persona que aprobó guardar su nombre, **When** regresa después del periodo de inactividad,
   **Then** el saludo usa su nombre y el perfil aprobado se conserva.
3. **Given** un número que escribió hace menos que el periodo de inactividad, **When** envía otro mensaje,
   **Then** la conversación continúa sin saludo nuevo.

---

### User Story 4 - Empezar de nuevo a pedido de la persona (Priority: P3)

Cuando la persona pide empezar de cero («empecemos de nuevo»), la siguiente solicitud se atiende como el inicio
de una conversación: con saludo breve y presentación solo si la persona no acaba de recibir una.

**Why this priority**: es un caso poco frecuente y hoy ya recibe una confirmación («Listo, empezamos de cero»).

**Independent Test**: pedir «empecemos de nuevo» y luego hacer una pregunta; verificar que no hay doble
presentación y que la pregunta se responde.

**Acceptance Scenarios**:

1. **Given** una conversación en curso, **When** la persona pide empezar de nuevo y en el mismo mensaje hace una
   pregunta, **Then** recibe la confirmación, una presentación breve y la respuesta, una sola vez cada una.

---

### Edge Cases

- **Primer mensaje no soportado** (imagen, sticker, ubicación): Valer-IA saluda, se presenta y explica en una
  frase qué puede recibir (texto y notas de voz).
- **Primer mensaje con datos sensibles**: el saludo va primero, la respuesta después y el aviso de datos
  sensibles al final (spec 029), sin repetir el saludo.
- **Primer mensaje sobre un tema ajeno a Manuelita**: saluda, se presenta y declina con amabilidad el tema
  ajeno, como en cualquier otro turno.
- **Primer mensaje que supera el límite del canal abierto** (spec 031): el aviso de límite no lleva
  presentación; la presentación se hace en el siguiente mensaje atendido si la conversación sigue siendo nueva.
- **Número bloqueado**: no recibe respuesta (spec 031); no se presenta.
- **Atajos ocultos del operador** (`/traza`, `/perfil`…): nunca llevan presentación.
- **Varios mensajes seguidos al abrir el chat**: la presentación aparece una sola vez, en la primera respuesta.
- **El modelo no está disponible** en el primer turno: el mensaje breve de indisponibilidad incluye quién es
  Valer-IA en una frase.
- **Modo degradado** (el backend no responde y atiende el agente básico): la presentación se pide en sus
  instrucciones, pero no se garantiza con la misma precisión.
- **Pregunta de seguimiento ambigua como primer mensaje de una conversación nueva** («¿y en Perú?»): Valer-IA
  se presenta y pide en una frase el contexto que falta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El canal MUST reconocer el inicio de una conversación nueva en tres casos: el primer mensaje de un
  número que nunca ha conversado, el primer mensaje después del periodo de inactividad y el primer mensaje
  después de que la persona pidió empezar de nuevo.
- **FR-002**: La primera respuesta de una conversación nueva MUST abrir con un saludo y una presentación de una o
  dos frases que diga quién es Valer-IA (la asistente virtual de Manuelita) y para qué sirve (contar de Manuelita
  con fuentes; recibir texto y notas de voz).
- **FR-003**: Si el primer mensaje trae una solicitud, la misma respuesta MUST continuar después de la
  presentación con la atención completa de esa solicitud (respuesta, fuentes y reglas existentes), sin pedirle a
  la persona que la repita.
- **FR-004**: Si el primer mensaje es solo un saludo o una pregunta sobre Valer-IA, la respuesta MUST saludar,
  presentarse e invitar a preguntar, sin agregar contenido no pedido.
- **FR-005**: Dentro de una misma conversación, Valer-IA MUST NOT volver a saludar ni presentarse, salvo que la
  persona pregunte quién es o qué puede hacer.
- **FR-006**: Cuando la respuesta sale por voz, la nota de voz MUST incluir el saludo y la presentación al
  inicio; el texto que la acompaña sigue llevando solo las fuentes (spec 030).
- **FR-007**: El saludo y la presentación MUST estar en el idioma del turno (español o inglés, spec 029).
- **FR-008**: Si la persona aprobó que se recuerde su nombre, el saludo de una conversación nueva SHOULD usarlo.
- **FR-009**: Una conversación retomada después del periodo de inactividad MUST empezar sin el contexto del hilo
  anterior; el perfil que la persona aprobó guardar MUST conservarse.
- **FR-010**: El periodo de inactividad MUST ser configurable por el equipo, con un valor por defecto de 12 horas.
- **FR-011**: La presentación MUST ser natural y variada en la forma, sin comandos, menús numerados ni
  instrucciones del tipo «responde SÍ o NO» (regla de conversación natural de la spec 028).
- **FR-012**: La presentación MUST NOT aparecer en avisos de límite, en respuestas a números bloqueados ni en los
  atajos ocultos del operador.
- **FR-013**: La presentación MUST ser breve: como máximo dos frases antes de empezar a atender la solicitud.
- **FR-014**: El registro del canal MUST indicar, sin texto ni números de teléfono, si cada turno inició una
  conversación nueva y por qué motivo (primer contacto, inactividad o reinicio), para poder medir el
  cumplimiento.
- **FR-015**: Las instrucciones del agente básico del modo degradado SHOULD pedir la misma presentación al inicio
  de una conversación.

### Key Entities

- **Conversación**: el hilo activo de una persona en el canal. Atributos relevantes: cuándo empezó, cuándo fue el
  último mensaje, si ya recibió la presentación y por qué motivo empezó.
- **Presentación**: el saludo más la descripción breve del propósito de Valer-IA, en el idioma del turno; ocurre
  a lo sumo una vez por conversación.
- **Periodo de inactividad**: tiempo sin mensajes después del cual el siguiente mensaje abre una conversación
  nueva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En una prueba con al menos 10 conversaciones nuevas (texto y voz, español e inglés, con saludo y
  sin saludo), el 100 % de las primeras respuestas incluye saludo y presentación.
- **SC-002**: En esas mismas conversaciones, el 100 % de las solicitudes del primer mensaje se responde en la
  misma respuesta, sin pedir que se repitan.
- **SC-003**: En los turnos siguientes de esas conversaciones, 0 respuestas repiten el saludo o la presentación.
- **SC-004**: La presentación ocupa como máximo dos frases en el 100 % de los casos revisados.
- **SC-005**: El 100 % de las primeras notas de voz de respuesta empieza con el saludo, y el texto acompañante
  trae solo las fuentes.
- **SC-006**: Al regresar después del periodo de inactividad, el 100 % de los casos probados recibe saludo
  nuevo, y ninguno arrastra contexto del hilo anterior.

## Assumptions

- El alcance es el canal de mensajería (WhatsApp, y Telegram por compartir el mismo puente). La web tiene su
  propia pantalla de bienvenida y queda fuera.
- Valer-IA no puede saber si la persona borró el chat en su teléfono; «chat nuevo» se aproxima con el primer
  contacto, la inactividad y el pedido de empezar de nuevo.
- El periodo de inactividad por defecto es de 12 horas: cubre una jornada de pruebas o de sustentación como una
  sola conversación y trata como nueva una visita al día siguiente.
- Las conversaciones que ya existían antes de este cambio se tratan con la misma regla de inactividad; no se
  migra ni se borra nada.
- La memoria aprobada por la persona (nombre, preferencias) se conserva entre conversaciones, como hoy con
  «empecemos de nuevo».
- El texto de la presentación se basa en la presentación actual de Valer-IA (asistente virtual de Manuelita que
  cuenta, con fuentes, de productos, negocios, sostenibilidad, cifras y canales oficiales, y que recibe notas de
  voz).
- Las reglas vigentes se mantienen: idioma del turno, fuentes ordenadas, aviso de datos sensibles al final,
  límites del canal abierto y voz con solo fuentes por escrito.
