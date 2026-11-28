# Feature Specification: Stickers de Valer-IA en las conversaciones de WhatsApp

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (se acumula con las specs 028–033 del canal)
**Created**: 2026-11-27
**Status**: Draft
**Input**: User description: "quiero que valeria tenga la capacidad de utilizar stickers en sus conversaciones de
whatsapp. En esta carpeta … tengo los stickers para que Valeria los pueda usar bajo distintas situaciones en … README.md
se describe el uso que se le puede dar a los stickers. Necesito que solo te centres en los stickers y que se puedan
implementar de forma dinámica y natural en las conversaciones de whatsapp"

## Contexto

La spec 030 dejó en el repositorio nueve stickers animados de Valer-IA en caricatura, aprobados y con su ficha de
origen (`docs/whatsapp/stickers/`). Los de la carpeta de descargas del integrante son idénticos (mismo contenido).
Cada sticker tiene un uso natural en una conversación:

| Sticker | Texto | Uso natural |
|---|---|---|
| Hola | «Hola» | Saludo al iniciar una conversación |
| Bienvenido | «¡Bienvenido!» | Primer contacto de una persona nueva |
| ¿Cuál es tu consulta? | «¿Cuál es tu consulta?» | La persona saluda sin preguntar nada |
| Pensando | «Pensando» | Una respuesta que va a tardar |
| ¡Listo! | «¡Listo!» | Se completó algo que la persona pidió (guardar, olvidar, un plan) |
| Pulgar | — | La persona confirma o asiente («dale», «ok», «perfecto») |
| ¡Gracias! | «¡Gracias!» | La persona agradece |
| ¡Gracias por confiar en nosotros! | ídem | La persona aprueba que se recuerden sus datos |
| Lindo día | «Lindo día» | La persona se despide |

Hoy Valer-IA no envía stickers. El objetivo es que los use de forma **dinámica y natural**: en el momento
oportuno, sin abusar y nunca en lugar de la respuesta. El alcance es solo los stickers. Las tarjetas, las imágenes
de perfil y los audios de los stickers quedan fuera.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stickers en los momentos sociales de la conversación (Priority: P1)

Cuando la conversación tiene un momento social (saludo, agradecimiento, despedida o asentimiento), Valer-IA
acompaña su respuesta escrita o hablada con el sticker que corresponde, como lo haría una persona en WhatsApp.

**Why this priority**: son los momentos más frecuentes y donde un sticker se siente más natural; dan
personalidad sin interferir con la información.

**Independent Test**: en una conversación nueva, enviar «Hola», luego una pregunta, luego «gracias» y luego
«chao». Verificar que llegan los stickers «Hola» al inicio, «¡Gracias!» y «Lindo día», cada uno junto a su
respuesta, y que la pregunta factual no lleva sticker.

**Acceptance Scenarios**:

1. **Given** una conversación nueva que empieza con un saludo, **When** Valer-IA responde con su presentación
   (spec 038), **Then** también envía el sticker «Hola», o «¡Bienvenido!» si es la primera vez que esa persona
   escribe.
2. **Given** una conversación en curso, **When** la persona escribe «muchas gracias», **Then** recibe la
   respuesta breve y el sticker «¡Gracias!».
3. **Given** una conversación en curso, **When** la persona se despide («chao», «hasta luego», «buen día»),
   **Then** recibe la despedida y el sticker «Lindo día».
4. **Given** que la persona solo saluda, sin preguntar nada, **When** Valer-IA la invita a preguntar, **Then**
   puede usar el sticker «¿Cuál es tu consulta?» en lugar del saludo genérico.
5. **Given** una pregunta factual (por ejemplo «¿Qué produce Manuelita?»), **Then** la respuesta no lleva
   sticker.

---

### User Story 2 - Uso moderado: nunca recargar la conversación (Priority: P1)

Valer-IA usa los stickers con moderación. Envía como máximo uno por respuesta, evita repetirlos seguido y nunca
los usa en momentos delicados.

**Why this priority**: un sticker en cada mensaje deja de ser natural y resta seriedad. La moderación es lo que
hace que el uso se sienta humano.

**Independent Test**: conversación de 10 turnos con varios saludos, agradecimientos y una queja. Verificar el
máximo por respuesta, el límite por conversación, que no se repite el mismo sticker seguido y que la queja no
lleva sticker.

**Acceptance Scenarios**:

1. **Given** cualquier respuesta, **Then** lleva como máximo un sticker.
2. **Given** que Valer-IA ya envió un sticker en la respuesta anterior, **Then** la siguiente no lleva sticker,
   salvo la despedida.
3. **Given** una conversación, **Then** el total de stickers no supera el máximo por conversación, y el mismo
   sticker no se repite dentro de esa conversación, salvo el pulgar.
4. **Given** que la persona expresa molestia, una queja, frustración o un tema sensible (salud, accidentes,
   datos personales), **Then** la respuesta no lleva sticker.
5. **Given** un aviso de límite, un error, un mensaje bloqueado, un mensaje no soportado o una confirmación
   pendiente, **Then** no lleva sticker.

---

### User Story 3 - Stickers que acompañan acciones completadas y asentimientos (Priority: P2)

Cuando Valer-IA completa algo que la persona pidió (guardar o borrar sus datos, entregar un plan de producción) o
la persona confirma con un «dale» u «ok», Valer-IA usa «¡Listo!», «Pulgar» o «¡Gracias por confiar en nosotros!».

**Why this priority**: refuerza que la acción se hizo, de forma amable; es menos frecuente que los momentos
sociales.

**Independent Test**: pedir que recuerde el nombre y aprobar con «dale»; verificar la confirmación con «¡Gracias
por confiar en nosotros!». Pedir que olvide los datos y verificar la confirmación con «¡Listo!».

**Acceptance Scenarios**:

1. **Given** que la persona aprueba que Valer-IA recuerde sus datos, **When** queda guardado, **Then** la
   confirmación lleva «¡Gracias por confiar en nosotros!».
2. **Given** que la persona pide olvidar sus datos o termina una acción pedida, **When** se completa, **Then** la
   confirmación lleva «¡Listo!».
3. **Given** que la persona solo asiente («ok», «perfecto», «entendido») sin pedir nada nuevo, **Then** la
   respuesta breve puede llevar el «Pulgar».

---

### User Story 4 - «Pensando» cuando la respuesta va a tardar (Priority: P3)

Si la respuesta a una pregunta va a tardar más de lo habitual, Valer-IA envía primero el sticker «Pensando», para
que la persona sepa que su mensaje se está atendiendo, y luego la respuesta.

**Why this priority**: mejora la percepción de espera en las respuestas largas (planificación o voz), pero el canal
funciona bien sin esto.

**Independent Test**: hacer una pregunta cuya respuesta tarde más del umbral; verificar que llega «Pensando»
antes de la respuesta. Una respuesta rápida no lo lleva.

**Acceptance Scenarios**:

1. **Given** una respuesta que todavía no está lista pasado el umbral de espera, **Then** la persona recibe
   «Pensando» y después la respuesta completa.
2. **Given** una respuesta que llega antes del umbral, **Then** no se envía «Pensando».
3. **Given** que ya se envió «Pensando» en esa conversación hace poco, **Then** no se repite.

---

### Edge Cases

- **Conversación en inglés**: los stickers con texto están en español. Con el idioma del turno en inglés (spec
  029) solo se usa el «Pulgar», que no tiene texto.
- **Respuesta por voz** (spec 030): el sticker acompaña a la nota de voz igual que al texto; no reemplaza la voz
  ni las fuentes.
- **El sticker no se puede entregar**: la persona recibe la respuesta igual; la falla del sticker nunca bloquea ni
  retrasa el texto ni la voz.
- **Cuentas identificadas solo por ID** (spec 033): reciben stickers como cualquier otra.
- **Modo degradado** (agente básico de OpenClaw): sin stickers.
- **Respuesta con aviso de datos sensibles** (spec 029): sin sticker.
- **La persona envía un sticker**: hoy recibe la respuesta de «no soportado»; esta spec no cambia la lectura de
  stickers entrantes.
- **Primer mensaje con una pregunta directa** (spec 038): la presentación va por texto y no lleva sticker de
  saludo, porque la prioridad es la respuesta. El sticker de saludo solo acompaña saludos.
- **Varios mensajes seguidos**: un sticker como máximo por respuesta, y las reglas de no repetir se mantienen.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Valer-IA MUST poder enviar en WhatsApp los nueve stickers aprobados de la spec 030, tomados del
  repositorio como única fuente.
- **FR-002**: Cada sticker MUST tener asociadas las situaciones de conversación en que se usa, según la tabla del
  contexto. La asociación es configurable por el equipo sin cambiar el comportamiento del agente.
- **FR-003**: El sticker MUST acompañar a la respuesta, nunca reemplazarla: el texto, las fuentes y la nota de
  voz se entregan igual.
- **FR-004**: Cada respuesta MUST llevar como máximo un sticker.
- **FR-005**: Valer-IA MUST NOT enviar sticker en dos respuestas consecutivas, salvo la despedida.
- **FR-006**: Cada conversación MUST tener un máximo de stickers, por defecto 4, configurable. El mismo sticker
  no se repite en una conversación, salvo el «Pulgar».
- **FR-007**: Valer-IA MUST NOT enviar stickers ante quejas, molestia o frustración, temas sensibles, avisos de
  datos sensibles, errores, avisos de límite, mensajes no soportados, confirmaciones pendientes, números
  bloqueados ni respuestas factuales.
- **FR-008**: Con el idioma del turno en inglés, Valer-IA MUST usar solo stickers sin texto.
- **FR-009**: Si el sticker no se puede entregar, la respuesta MUST llegar completa y sin demora adicional; la
  falla queda registrada sin datos personales.
- **FR-010**: El orden MUST ser natural: el sticker de saludo va antes del texto; los de agradecimiento,
  despedida, asentimiento y acción completada van después.
- **FR-011**: «Pensando» MUST enviarse solo cuando la respuesta no está lista pasado un umbral de espera
  configurable (8 segundos por defecto), y como máximo una vez por conversación cada 10 minutos.
- **FR-012**: El equipo MUST poder activar o desactivar los stickers del canal con un solo ajuste, sin desplegar
  código.
- **FR-013**: El registro del canal MUST indicar qué sticker se envió en cada turno (su nombre, nunca contenido
  de la conversación), para medir la frecuencia.
- **FR-014**: Las conversaciones en la web no cambian; los stickers son solo del canal de WhatsApp.

### Key Entities

- **Sticker**: una pieza aprobada de la spec 030, con nombre, archivo, texto visible (o ninguno) e idioma del
  texto.
- **Situación**: momento de la conversación que admite un sticker: saludo, primer contacto, invitación a
  preguntar, agradecimiento, despedida, asentimiento, acción completada, datos guardados o espera larga.
- **Uso en la conversación**: los stickers ya enviados en un hilo (cuáles, cuántos y en qué turno), para aplicar
  la moderación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En una prueba guionada de al menos 10 conversaciones, el 100 % de los saludos iniciales,
  agradecimientos y despedidas reciben el sticker que les corresponde, cuando las reglas de moderación lo
  permiten.
- **SC-002**: 0 respuestas llevan más de un sticker, y ninguna conversación supera el máximo configurado.
- **SC-003**: 0 stickers en respuestas factuales, quejas, avisos de datos sensibles, errores o avisos de límite.
- **SC-004**: 0 stickers con texto en español en conversaciones en inglés.
- **SC-005**: Cuando un sticker no se puede entregar, el 100 % de las respuestas llegan completas y sin demora
  perceptible.
- **SC-006**: En la prueba con el teléfono, quien prueba percibe los stickers como naturales: no los califica de
  repetitivos ni de inoportunos en ninguna de las conversaciones probadas.

## Assumptions

- Los stickers del repositorio (`docs/whatsapp/stickers/`, spec 030) son la fuente; ya cumplen el formato de
  sticker de WhatsApp (512×512, animados, ≤ 500 KB) y tienen aprobación humana.
- El canal de WhatsApp puede enviar un archivo como mensaje de tipo sticker. Si una verificación temprana muestra
  que no se puede, la spec se revisa antes de implementar.
- La decisión de cuándo usar un sticker se basa en señales que el canal ya reconoce: intenciones, saludo y
  presentación (spec 038), agradecimiento, cierre, acciones aprobadas y sentimiento. No depende de que el modelo
  de lenguaje lo pida.
- El máximo por conversación (4) y el umbral de espera (8 s) son valores razonables, ajustables tras la prueba.
- Quedan fuera de alcance:
  - las tarjetas (`tarjetas/`), las imágenes de perfil y los audios de los stickers (spec 030 US6);
  - interpretar stickers recibidos;
  - la web.
- Los stickers no llevan la declaración de IA. La presentación de Valer-IA (spec 038) ya lo hace por escrito.
