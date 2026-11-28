# Feature Specification: Respuesta automática a cuentas de WhatsApp identificadas solo por ID (LID)

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (se acumula con las specs 028–032 del canal)
**Created**: 2026-11-27
**Status**: Draft
**Input**: User description: "empieza las especificaciones para hacer estas correcciones y contestar de forma
automática a cuentas de WhatsApp que tengan ID"

## Contexto

En una prueba con un número nuevo, Valer-IA no respondió. WhatsApp entregó el mensaje identificando al remitente
solo con su identificador interno (LID), sin su número de teléfono ni la equivalencia entre ambos. El componente
de WhatsApp del gateway exige el número: deja el mensaje en una cola de reintentos indefinida y nunca lo entrega a
Valer-IA. La persona no recibe nada, y el equipo no ve el mensaje en los registros del canal.

Con el canal abierto a cualquier número (spec 031), cualquier invitado cuya cuenta llegue así queda sin respuesta.
Guardar a mano cada número en el teléfono de la SIM no es viable: la solución debe ser automática.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Una cuenta identificada solo por ID recibe respuesta por texto (Priority: P1)

Una persona que nunca ha escrito a Valer-IA, y cuya cuenta WhatsApp entrega solo con su ID, escribe una pregunta.
Valer-IA responde igual que a cualquier otra persona: saludo y presentación (spec 038) y la respuesta con
fuentes, sin que nadie del equipo intervenga.

**Why this priority**: es el fallo observado. Sin esto, parte del público del canal abierto no recibe respuesta.

**Independent Test**: desde una cuenta que llegue solo con ID, enviar «¿Qué produce Manuelita?» y verificar que
la respuesta llega en el mismo tiempo que para cualquier otro número, sin acciones manuales en el teléfono de la
SIM.

**Acceptance Scenarios**:

1. **Given** una cuenta que WhatsApp entrega solo con su ID y el canal en modo abierto, **When** envía una
   pregunta, **Then** recibe la respuesta completa (presentación, respuesta y fuentes) sin intervención humana.
2. **Given** esa misma cuenta, **When** envía un segundo mensaje, **Then** la conversación continúa en el mismo
   hilo: Valer-IA la reconoce como la misma persona.
3. **Given** una cuenta que sí llega con su número, **When** escribe, **Then** el comportamiento es idéntico al
   actual.

---

### User Story 2 - La misma cuenta recibe notas de voz (Priority: P1)

La persona identificada solo por ID envía una nota de voz y recibe la respuesta en nota de voz, con las fuentes
por escrito (spec 030), como cualquier otra persona.

**Why this priority**: la voz es una forma de entrada central del canal; una respuesta solo por texto a una nota
de voz sería un servicio incompleto.

**Independent Test**: desde una cuenta que llegue solo con ID, enviar una nota de voz con una pregunta y verificar
que llega la nota de voz de respuesta y las fuentes por escrito.

**Acceptance Scenarios**:

1. **Given** una cuenta identificada solo por ID, **When** envía una nota de voz con una pregunta, **Then**
   recibe una nota de voz de respuesta y, por escrito, solo las fuentes.
2. **Given** que la nota de voz de respuesta no se puede entregar a esa cuenta, **Then** la persona recibe la
   respuesta escrita completa (comportamiento de respaldo de la spec 030).

---

### User Story 3 - Los mensajes atascados no se pierden (Priority: P2)

Los mensajes que quedaron en la cola de reintentos antes de la corrección se atienden una sola vez cuando la
corrección entra en funcionamiento, o se descartan de forma explícita y visible si ya son muy viejos.

**Why this priority**: evita que una persona reciba una respuesta horas después sin contexto, y evita que el
equipo crea que el canal funciona cuando hay mensajes retenidos.

**Independent Test**: con un mensaje de una cuenta solo con ID retenido en la cola, aplicar la corrección y
verificar que se responde una vez si es reciente, o que queda registrado como descartado si es viejo.

**Acceptance Scenarios**:

1. **Given** un mensaje retenido de hace menos de 15 minutos, **When** la corrección entra en funcionamiento,
   **Then** se responde una sola vez.
2. **Given** un mensaje retenido de hace más de 15 minutos, **When** la corrección entra en funcionamiento,
   **Then** no se responde y el descarte queda registrado sin datos personales.

---

### User Story 4 - El equipo verifica y protege el canal con estas cuentas (Priority: P2)

El equipo puede comprobar en un solo paso que el soporte para cuentas identificadas por ID está activo en el
equipo principal y en el de respaldo. Las protecciones del canal abierto (límites, bloqueo, saludo, privacidad)
aplican igual a estas cuentas.

**Why this priority**: la corrección se apoya en un componente externo que una actualización o reinstalación
puede revertir; si se pierde en silencio, el fallo reaparece sin aviso.

**Independent Test**: ejecutar la verificación del canal y ver el soporte marcado como activo; reinstalar el
componente de WhatsApp y comprobar que la verificación lo detecta y la instalación lo restablece.

**Acceptance Scenarios**:

1. **Given** el equipo principal o el de respaldo preparados con la guía, **When** se ejecuta la verificación del
   canal, **Then** muestra si el soporte para cuentas por ID está activo.
2. **Given** que el componente de WhatsApp se reinstaló o actualizó y perdió la corrección, **When** se ejecuta la
   verificación, **Then** la marca como fallida, y el paso de instalación del gateway la vuelve a aplicar.
3. **Given** una cuenta identificada por ID que supera los límites del canal abierto, **Then** recibe el mismo
   aviso único y luego silencio (spec 031).
4. **Given** una cuenta identificada por ID que hay que bloquear, **Then** el operador puede bloquearla con el
   seudónimo que aparece en los registros, sin conocer su número.

---

### Edge Cases

- **La equivalencia ID ↔ número llega después**: la persona escribió primero solo con ID y luego WhatsApp
  entrega su número. Si el sistema conoce la equivalencia, la trata como la misma persona; si no, puede abrir una
  conversación nueva, que se presenta según la spec 038.
- **Modo cerrado**: una cuenta identificada solo por ID no coincide con los números de prueba autorizados. En modo
  cerrado sigue sin ser admitida, como hoy, salvo que su equivalencia con un número autorizado sea conocida.
- **Operadores**: un operador cuya cuenta llegue solo con ID no se reconoce por su número. Se reconoce si su
  seudónimo por ID se agrega a la lista de operadores.
- **Grupos**: siguen deshabilitados; esta spec solo cubre chats individuales.
- **Mensajes propios** (enviados desde el teléfono de la SIM): siguen ignorándose.
- **El componente de WhatsApp se actualiza a una versión que ya resuelve el problema**: la corrección no debe
  romper esa versión. La verificación debe reconocer que el soporte existe de forma nativa.
- **Varias cuentas solo con ID escriben a la vez**: cada una tiene su propio hilo y su propio seudónimo.
- **Una cuenta solo con ID envía una imagen, un sticker o una ubicación**: recibe la respuesta de «no soportado»
  con la presentación (spec 038).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El canal MUST atender los mensajes individuales de cuentas que WhatsApp entrega solo con su ID, sin
  intervención manual (ni guardar contactos ni aprobar mensajes).
- **FR-002**: Estas cuentas MUST recibir el mismo servicio que las identificadas por número: texto, notas de voz,
  presentación al iniciar (spec 038), idioma del turno, fuentes y avisos.
- **FR-003**: Cada cuenta identificada por ID MUST tener una identidad estable en el canal, de modo que sus
  mensajes sucesivos continúen la misma conversación.
- **FR-004**: El identificador de la cuenta MUST tratarse con la misma privacidad que un número de teléfono: se
  convierte en seudónimo, y nunca aparece completo en registros, estado del canal, pruebas ni archivos
  versionados.
- **FR-005**: Las respuestas MUST llegar a la misma conversación de WhatsApp desde la que escribió la persona.
- **FR-006**: Si la nota de voz no se puede entregar a una cuenta identificada por ID, la persona MUST recibir la
  respuesta escrita completa.
- **FR-007**: Los límites por persona, el aviso único y el bloqueo del canal abierto (spec 031) MUST aplicarse
  también a estas cuentas.
- **FR-008**: El operador MUST poder bloquear y desbloquear una cuenta a partir del seudónimo que muestran los
  registros, sin necesitar su número.
- **FR-009**: El modo cerrado MUST seguir admitiendo solo las cuentas autorizadas; una cuenta solo con ID no se
  admite en modo cerrado salvo que su equivalencia con un número autorizado sea conocida.
- **FR-010**: Los mensajes retenidos antes de la corrección MUST atenderse una sola vez si tienen menos de 15
  minutos; los más viejos se descartan y el descarte queda registrado sin datos personales.
- **FR-011**: Ningún mensaje individual MUST quedar retenido en reintentos por falta del número de teléfono.
- **FR-012**: La corrección MUST quedar aplicada de forma reproducible por el mismo paso de instalación del gateway
  que usan el equipo principal y el de respaldo; no depende de cambios manuales en archivos instalados.
- **FR-013**: La verificación del canal MUST indicar si el soporte para cuentas identificadas por ID está activo,
  fallar si falta, y reconocer una versión del componente que ya lo traiga de forma nativa.
- **FR-014**: El registro del canal MUST indicar, sin valores, si cada mensaje llegó identificado por número o solo
  por ID, para medir cuántas personas llegan así.
- **FR-015**: Cuando el sistema conozca la equivalencia entre el ID y el número de una persona, SHOULD tratarla como
  una sola persona.
- **FR-016**: La guía del respaldo, la guía de despliegue y el manual del canal MUST explicar el soporte, la
  verificación y qué hacer si el componente se actualiza.

### Key Entities

- **Cuenta identificada por ID**: remitente de WhatsApp del que solo se conoce su identificador interno, sin
  número. Tiene un seudónimo estable derivado del identificador.
- **Equivalencia ID ↔ número**: relación que WhatsApp puede entregar o no. Cuando existe, permite tratar ambas
  identidades como una persona.
- **Mensaje retenido**: mensaje que quedó en la cola de reintentos del gateway por falta del número; tiene una
  antigüedad que decide si se atiende o se descarta.
- **Soporte para cuentas por ID**: estado verificable del gateway (activo, ausente o nativo del componente).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100 % de los mensajes de prueba enviados desde cuentas identificadas solo por ID reciben
  respuesta sin intervención manual, en un tiempo comparable al de las cuentas con número (dentro del límite de
  espera vigente del canal).
- **SC-002**: El 100 % de las notas de voz de prueba desde esas cuentas reciben nota de voz de respuesta, o la
  respuesta escrita completa si la voz no se puede entregar.
- **SC-003**: 0 mensajes individuales quedan retenidos más de 2 minutos por falta del número.
- **SC-004**: 0 identificadores completos (números o IDs de WhatsApp) aparecen en registros, estado del canal,
  pruebas o archivos versionados.
- **SC-005**: Después de reinstalar el componente de WhatsApp, la verificación del canal detecta la falta del
  soporte en el 100 % de los casos, y el paso de instalación lo restablece.
- **SC-006**: Las cuentas identificadas por número no muestran ningún cambio de comportamiento: las pruebas
  vigentes del canal siguen en verde.

## Assumptions

- WhatsApp puede entregar algunas cuentas solo con su ID y sin la equivalencia con el número (por la privacidad
  del número o por cómo se establece el contacto). No se puede obtener el número en esos casos, así que el ID
  es la identidad de la persona en el canal.
- La conversación de WhatsApp de esa persona se puede contestar usando su ID, como lo hace la aplicación oficial.
  Si una verificación temprana demuestra lo contrario, la spec se revisa antes de implementar.
- El componente de WhatsApp del gateway es de un tercero (OpenClaw 2026.11.10) y no trae este soporte, ni siquiera
  en la beta publicada el 2026-11-27. La corrección se aplica sobre él de forma versionada en el repositorio.
  Reportar el problema al proyecto original es deseable, pero queda fuera de alcance y requiere autorización del
  equipo.
- El modo abierto es el modo de operación hasta el fin del proyecto (spec 031); el modo cerrado conserva su
  comportamiento.
- 15 minutos es el límite razonable para atender un mensaje retenido sin que la respuesta pierda sentido.
- Aplican la presentación (spec 038), el idioma (spec 029), la voz con solo fuentes (spec 030) y los límites
  (spec 031).
- La sustentación es inminente: la corrección solo se activa en el equipo principal después de probarla con una
  cuenta real identificada solo por ID; si no se logra a tiempo, se documenta la limitación para ese día.
