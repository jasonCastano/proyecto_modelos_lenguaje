# Feature Specification: Stickers que sí llegan y se usan de forma activa

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (se acumula con las specs 028–036)
**Created**: 2026-11-28
**Status**: Draft
**Input**: User description: "haz las correcciones para que Valeria pueda hacer uso de los stickers y haz las
modificaciones necesarias para que su uso sea de forma activa"

## Contexto

La spec 034 le dio a Valer-IA nueve stickers aprobados (`docs/whatsapp/stickers/`). La idea era usarlos de forma
dinámica y natural en WhatsApp. En las pruebas por teléfono la persona responsable **no ha recibido ningún
sticker**. El diagnóstico del 2026-11-28 encontró dos causas.

1. **La entrega nunca funcionó.** En 79 respuestas del canal, Valer-IA decidió enviar 4 stickers: dos de bienvenida
   y dos de «¿Cuál es tu consulta?». En todos los intentos, incluido el sticker de «Pensando», el registro del
   canal dice que el sticker no se pudo enviar porque no encontró la conexión activa de WhatsApp. El sticker se
   descarta en silencio y la persona solo recibe el texto. La verificación de entrega real de la spec 034 (T001)
   quedó pendiente, y esta es la falla que debía detectar.
2. **La política es demasiado prudente.** Solo hay sticker en el saludo, «gracias», la despedida, un «ok» suelto
   o una acción completada. Nunca lo hay en una respuesta con información, nunca en dos respuestas seguidas, y hay
   como máximo cuatro por conversación. En una conversación típica de preguntas sobre Manuelita casi nunca aplica:
   4 de 79 respuestas (5 %).

La persona responsable pide dos cosas: que los stickers lleguen, y que Valer-IA los use **de forma activa**. Deben
ser parte visible de su personalidad en WhatsApp, sin perder el perfil profesional ni el cuidado de las specs 019,
035 y 036.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El sticker elegido llega al teléfono (Priority: P1)

Cuando Valer-IA decide acompañar una respuesta con un sticker, la persona lo recibe en WhatsApp como sticker
nativo, en el orden correcto respecto al texto.

**Why this priority**: sin entrega no hay sticker posible; es la falla que hoy deja la función en cero.

**Independent Test**: escribir «Hola» desde un número que nunca ha hablado con Valer-IA. Verificar que llega el
sticker de bienvenida como sticker de WhatsApp (no como imagen ni archivo) junto con la presentación, y que el
registro del canal lo marca como enviado.

**Acceptance Scenarios**:

1. **Given** una respuesta con sticker «antes del texto», **When** se entrega, **Then** el sticker llega primero y
   el texto después.
2. **Given** una respuesta con sticker «después del texto», **When** se entrega, **Then** el texto llega primero y
   el sticker unos instantes después.
3. **Given** una respuesta que tarda más de lo normal, **When** pasa el tiempo de espera, **Then** llega el sticker
   de «Pensando» una sola vez y luego la respuesta.
4. **Given** que el sticker no se puede enviar por un problema del canal, **When** se entrega la respuesta,
   **Then** el texto llega igual y el registro guarda el motivo del fallo (sin números ni datos personales).
5. **Given** el reporte de estado del canal, **When** el operador lo consulta, **Then** ve cuántos stickers se
   eligieron y cuántos se entregaron en el día. Una entrega en cero con stickers elegidos aparece como alerta.

---

### User Story 2 - Uso activo y natural en toda la conversación (Priority: P1)

Valer-IA usa los stickers como parte de su forma de conversar. Saluda con uno, acompaña una respuesta útil con un
«¡Listo!» o un pulgar, celebra un agradecimiento y se despide con «Lindo día». Esto incluye las respuestas con
información de Manuelita, sin saturar la conversación.

**Why this priority**: es la petición explícita: «que su uso sea de forma activa».

**Independent Test**: una conversación de seis mensajes: saludo, dos preguntas sobre Manuelita, «ok», «gracias» y
despedida. Verificar que llegan entre dos y cuatro stickers, distintos o repetidos solo si están permitidos, en
momentos que encajan, y que nunca llegan dos en la misma respuesta.

**Acceptance Scenarios**:

1. **Given** el primer mensaje de una conversación nueva, **When** Valer-IA se presenta, **Then** la acompaña el
   sticker de bienvenida (primer contacto) o el de «Hola» (conversación que se retoma).
2. **Given** una respuesta con información útil de Manuelita (con fuentes), **When** se entrega, **Then** puede ir
   acompañada de un sticker de cierre positivo, como «¡Listo!» o el pulgar, después del texto. Ocurre en al menos
   una de cada tres respuestas informativas de la conversación, sin repetir el mismo sticker seguido.
3. **Given** un saludo a mitad de la conversación o la presentación seguida de una pregunta abierta, **When**
   Valer-IA invita a consultar, **Then** puede ir el sticker «¿Cuál es tu consulta?».
4. **Given** un «gracias», **When** Valer-IA responde, **Then** va el sticker «¡Gracias!». Con una despedida va
   «Lindo día», aunque la respuesta anterior haya llevado sticker.
5. **Given** un «ok», «dale» o «perfecto», **When** Valer-IA responde, **Then** puede ir el pulgar.
6. **Given** una conversación larga, **When** se cuentan los stickers, **Then** hay como máximo ocho por
   conversación. El mismo sticker no se repite en dos respuestas seguidas, salvo el pulgar y la despedida.

---

### User Story 3 - Los stickers nunca restan profesionalismo ni cuidado (Priority: P1)

Hay momentos en que un sticker sería inoportuno: una queja, molestia, angustia o crisis, un error, un aviso de
datos sensibles o una acción rechazada. En ellos Valer-IA no envía sticker. Tampoco usa stickers con texto en
español cuando la conversación es en inglés.

**Why this priority**: el uso activo no puede romper la atención de la spec 019 ni el perfil profesional.

**Independent Test**: enviar una queja, un mensaje de angustia y un mensaje con un número de tarjeta. Verificar que
ninguna respuesta lleva sticker. Escribir en inglés y verificar que solo puede llegar el pulgar (sin texto).

**Acceptance Scenarios**:

1. **Given** una queja, molestia, angustia o crisis, **When** Valer-IA responde, **Then** no envía sticker.
2. **Given** una respuesta de error, de evidencia insuficiente o con aviso de datos sensibles, **When** se entrega,
   **Then** no lleva sticker.
3. **Given** una conversación en inglés, **When** corresponde un sticker, **Then** solo se usan stickers sin
   texto.
4. **Given** que la persona dice que no quiere stickers («sin stickers», «no me mandes stickers»), **When** sigue
   la conversación, **Then** Valer-IA deja de enviarlos en ese hilo.

---

### Edge Cases

- El sticker se elige, pero WhatsApp no está conectado en ese momento: el texto llega y el sticker se descarta y
  se registra.
- La respuesta se divide en varios mensajes, o va como nota de voz más fuentes: el sticker va una sola vez, antes
  del primer mensaje o después del último.
- La respuesta lleva presentación (spec 038) y además es informativa: como máximo un sticker. Gana el de
  presentación.
- La persona pide hablar «normal» (spec 036): los stickers siguen; solo se apagan si pide no recibirlos.
- Conversaciones de prueba o mensajes del propio número: mismo comportamiento que hoy (spec 031).
- Un archivo de sticker falta o está dañado: no se envía, el texto llega y el estado del canal lo reporta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Todo sticker que Valer-IA decida enviar MUST llegar a WhatsApp como sticker nativo cuando el canal
  está conectado.
- **FR-002**: El orden respecto al texto MUST respetarse: «antes» o «después» según el sticker.
- **FR-003**: Si la entrega falla, la respuesta escrita o hablada MUST llegar igual. El fallo MUST quedar
  registrado con su motivo, sin números de teléfono ni contenido.
- **FR-004**: El estado del canal MUST mostrar los stickers elegidos y entregados del día, y alertar si se eligen
  pero ninguno se entrega.
- **FR-005**: Las respuestas con información útil y fuentes MUST poder llevar un sticker de cierre positivo
  («¡Listo!» o el pulgar). Deben aparecer en al menos una de cada tres respuestas informativas de una conversación.
- **FR-006**: La presentación del primer mensaje MUST llevar el sticker de bienvenida o el de «Hola», según sea un
  primer contacto o una conversación retomada.
- **FR-007**: El sticker «¿Cuál es tu consulta?» MUST poder acompañar una invitación a preguntar: un saludo a mitad
  de la conversación o una presentación sin pregunta concreta.
- **FR-008**: Agradecimientos, despedidas, asentimientos breves y acciones completadas MUST conservar sus stickers
  de la spec 034.
- **FR-009**: Moderación del uso:
  - como máximo un sticker por respuesta y ocho por conversación;
  - el mismo sticker no va en dos respuestas seguidas, salvo el pulgar y la despedida;
  - dos respuestas seguidas pueden llevar sticker si la situación cambia.
- **FR-010**: No MUST enviarse sticker en estos casos:
  - quejas, molestia, angustia o crisis;
  - errores, evidencia insuficiente, avisos de datos sensibles o acciones rechazadas.
- **FR-011**: En inglés MUST usarse solo stickers sin texto.
- **FR-012**: Si la persona pide no recibir stickers, MUST dejar de enviarlos en esa conversación.
- **FR-013**: El sticker de «Pensando» MUST llegar cuando la respuesta tarde más del tiempo de espera configurado,
  como máximo uno cada diez minutos por conversación.
- **FR-014**: Los nueve stickers aprobados y sus textos MUST seguir siendo los mismos; no se agregan diseños
  nuevos.
- **FR-015**: MUST existir un conjunto de verificación con conversaciones de distintos tipos. Debe medir el uso
  (stickers por conversación y por respuesta informativa), la moderación y las exclusiones. También debe haber una
  prueba de entrega real en el teléfono.

### Key Entities

- **Sticker aprobado**: archivo, texto visible, idioma, situaciones en que se usa y posición (antes o después).
- **Situación del turno**: momento de la conversación que admite sticker: bienvenida, retomar, invitar a
  consultar, respuesta útil, asentimiento, agradecimiento, despedida, acción completada o pensando.
- **Uso por conversación**: stickers enviados, el último enviado y la preferencia de no recibirlos.
- **Registro de entrega**: sticker elegido, entregado o fallido, con su motivo, sin datos personales.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En la prueba por teléfono, el 100 % de los stickers elegidos llega como sticker nativo cuando
  WhatsApp está conectado, y 0 respuestas pierden su texto por culpa de un sticker.
- **SC-002**: En el conjunto de verificación, una conversación típica de seis mensajes recibe entre dos y cuatro
  stickers, y al menos el 80 % de las conversaciones con saludo y despedida reciben dos o más.
- **SC-003**: Al menos una de cada tres respuestas informativas lleva sticker de cierre positivo, y nunca dos
  stickers en la misma respuesta.
- **SC-004**: 0 stickers en quejas, molestia, angustia, crisis, errores, avisos de datos sensibles o acciones
  rechazadas, y 0 stickers con texto en conversaciones en inglés.
- **SC-005**: 0 conversaciones con más de ocho stickers o con el mismo sticker (salvo pulgar y despedida) en dos
  respuestas seguidas.
- **SC-006**: El estado del canal reporta stickers elegidos frente a entregados. En la prueba por teléfono la
  entrega es igual a la elección.
- **SC-007**: En la prueba por teléfono, la persona responsable percibe el uso como «activo y natural» en una
  conversación de seis mensajes, con al menos dos stickers recibidos.

## Assumptions

- La conexión de WhatsApp la mantiene el gateway de OpenClaw. La corrección usa la conexión activa que el propio
  gateway expone a sus extensiones, sin una segunda sesión de WhatsApp ni otro número.
- Los nueve stickers aprobados en la spec 030 y catalogados en la spec 034 no cambian. Para las respuestas
  informativas se reutilizan «¡Listo!» y el pulgar.
- «Uso activo» significa que el sticker aparece en los momentos naturales de casi toda conversación y en una de cada
  tres respuestas informativas, sin volverse ruido. El máximo por conversación sube de cuatro a ocho.
- El canal web no tiene stickers; el cambio es solo de WhatsApp.
- La verificación de entrega se hace en el teléfono, con instrucciones previas al usuario, después de reiniciar el
  gateway y el backend.
- Las reglas de cuidado (spec 019), enfoque (spec 035) y estilo caleño (spec 036) no cambian.
