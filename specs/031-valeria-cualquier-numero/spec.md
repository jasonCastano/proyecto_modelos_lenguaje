# Feature Specification: Valer-IA atiende a cualquier número de WhatsApp

**Feature Branch**: `028-valeria-natural-voz-whatsapp` (trabajo continuo de las specs 028–030; la rama la decide el equipo)

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "He hecho una prueba de contactarme con Valeria a través de un número que no está dentro de los números habilitados para contactar a Valeria, necesito que Valeria esté en la capacidad de comunicarse y responder a diferentes números que le consulten, así no sean números que estén habilitados directamente. Hagamos estos ajustes"

## Contexto

Hoy el canal de WhatsApp de Valer-IA funciona en **modo cerrado**: solo responden los números de prueba habilitados
(tres como máximo). Un número fuera de esa lista no recibe respuesta. La spec 028 previó un **modo abierto** para el
ensayo y la sustentación, pero:

- nunca se activó ni se probó con un número desconocido;
- no hay protecciones para un canal abierto al público: ni límite de mensajes por número, ni tope diario, ni forma
  de bloquear a quien abuse.

La SIM es dedicada y se desactivará al terminar el proyecto.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Cualquier persona puede escribirle a Valer-IA (Priority: P1)

Una persona cuyo número no está registrado le escribe (o le envía una nota de voz) a Valer-IA por WhatsApp y recibe
una respuesta igual a la que recibiría un número de prueba: en su idioma, con voz ante voz y con fuentes. No
necesita códigos de emparejamiento ni pasos previos.

**Why this priority**: es el pedido explícito y la condición para la sustentación: cualquier asistente debe poder
probar a Valer-IA desde su propio teléfono.

**Independent Test**: desde un número que nunca le ha escrito, enviar «Hola» y una pregunta sobre Manuelita (texto y
nota de voz); ambas reciben respuesta completa, sin códigos de emparejamiento ni avisos de acceso.

**Acceptance Scenarios**:

1. **Given** el canal en modo abierto y un número que nunca ha escrito, **When** envía un mensaje de texto, **Then**
   recibe la respuesta de Valer-IA como cualquier número de prueba.
2. **Given** el mismo número, **When** envía una nota de voz, **Then** recibe nota de voz y, por escrito, solo las
   fuentes (specs 029 y 030).
3. **Given** dos números distintos escribiendo a la vez, **When** ambos preguntan, **Then** cada uno recibe su propia
   respuesta y su propia conversación, sin mezclarse.
4. **Given** el canal en modo abierto, **When** alguien escribe desde un grupo, **Then** Valer-IA no responde (los
   grupos siguen deshabilitados).

---

### User Story 2 - Abrir y cerrar el canal es un paso simple y verificable (Priority: P1)

El equipo puede pasar el canal a modo abierto (y volver a cerrado) con un solo paso, y comprobar en qué modo está
antes de una prueba o de la sustentación.

**Why this priority**: sin una forma clara y verificable de abrir el canal, el día de la sustentación podría quedar
cerrado por error.

**Independent Test**: cambiar a modo abierto y consultar el estado (dice «abierto»); escribir desde un número nuevo y
recibir respuesta. Cambiar a cerrado; el estado dice «cerrado» y el número nuevo ya no recibe respuesta, mientras los
de prueba sí.

**Acceptance Scenarios**:

1. **Given** el canal cerrado, **When** el operador lo abre, **Then** después de reiniciarse el canal cualquier número
   recibe respuesta, y el chequeo de salud del sistema muestra el modo «abierto».
2. **Given** el canal abierto, **When** el operador lo cierra, **Then** solo los números de prueba guardados reciben
   respuesta y el estado muestra «cerrado».
3. **Given** cualquier cambio de modo, **When** se reinicia el equipo o el canal, **Then** el modo elegido se mantiene.
4. **Given** el canal abierto, **When** el chequeo de salud se ejecuta, **Then** advierte que el canal está abierto al
   público (para no olvidarlo abierto después del proyecto).

---

### User Story 3 - Protecciones del canal abierto (Priority: P2)

Con el canal abierto al público, Valer-IA se protege de usos abusivos o accidentales que agoten recursos o costos:
cada número tiene un límite razonable de mensajes y el operador puede bloquear un número concreto.

**Why this priority**: abrir el canal sin límites expone el costo del modelo y el equipo servidor; es necesario, pero
no impide la historia 1.

**Independent Test**: simular un número que envía muchos mensajes seguidos; después del límite recibe un mensaje
amable y deja de consumir respuestas del modelo hasta que pase la ventana. Bloquear un número: deja de recibir
respuestas.

**Acceptance Scenarios**:

1. **Given** un número que supera el límite de mensajes en una ventana corta, **When** envía otro mensaje, **Then**
   recibe una sola vez un aviso amable en su idioma («dame un momento…») y sus mensajes extra no se procesan hasta
   que pase la ventana.
2. **Given** un número que supera el tope diario, **When** escribe, **Then** recibe una sola vez un aviso amable de que
   puede volver mañana, y no se procesan más mensajes ese día.
3. **Given** un número bloqueado por el operador, **When** escribe, **Then** no recibe respuesta y el intento queda en
   el registro (sin el número completo).
4. **Given** los números de prueba del equipo, **When** escriben, **Then** no tienen límites (para las pruebas y la
   sustentación).

---

### User Story 4 - Operación y privacidad con personas desconocidas (Priority: P3)

El equipo ve cuántas personas distintas usaron el canal y cuántos mensajes se limitaron, sin ver números ni
contenido, y las personas nuevas reciben la misma protección de datos que las de prueba.

**Why this priority**: útil para el informe y la sustentación; no bloquea la atención.

**Independent Test**: después de varias conversaciones desde números distintos, el estado del canal muestra personas
distintas, mensajes y limitados en la última hora y el día; los registros no contienen ningún número completo.

**Acceptance Scenarios**:

1. **Given** varias personas que escribieron, **When** el operador consulta el estado del canal, **Then** ve el modo,
   el número de personas distintas (por seudónimo), mensajes y mensajes limitados del día.
2. **Given** cualquier conversación de una persona nueva, **When** se revisan registros y memoria, **Then** solo
   aparecen seudónimos y números enmascarados.

### Edge Cases

- **Primer mensaje de un número nuevo durante un reinicio**: se pierde como cualquier mensaje enviado durante el
  reinicio (ya documentado); la persona puede volver a escribir.
- **Atajos del operador** (traza, perfiles): en modo abierto solo funcionan para los números de prueba; para el resto
  el texto se trata como una conversación normal.
- **Planificador y perfiles restringidos**: siguen las reglas de autorización actuales; abrir el canal no otorga
  permisos especiales a números nuevos.
- **Mensajes simultáneos de muchos números**: cada persona espera su turno en su propia cola; un número que abusa no
  retrasa a los demás más allá del límite.
- **Números de otros países**: se atienden igual (el canal no restringe por país).
- **Volver a cerrado sin números de prueba guardados**: el cambio advierte que nadie podrá escribir y no se hace sin
  confirmación del operador.
- **Fin del proyecto**: cerrar el canal (o desvincular la SIM) deja de atender a todos; el estado lo refleja.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: En modo abierto, el canal MUST responder a cualquier número de WhatsApp que escriba por chat directo,
  sin códigos de emparejamiento ni registro previo.
- **FR-002**: Un número nuevo MUST recibir el mismo comportamiento que un número de prueba: idioma del turno, voz ante
  voz con solo fuentes por escrito, aviso de datos sensibles y fuentes ordenadas (specs 028–030).
- **FR-003**: Cada número MUST tener su propia conversación y memoria (seudónimo por número); nunca se mezclan
  conversaciones entre números.
- **FR-004**: Los mensajes de grupos MUST seguir sin respuesta en cualquier modo.
- **FR-005**: El operador MUST poder pasar de modo cerrado a abierto y viceversa con un solo paso documentado; el modo
  MUST conservarse tras reinicios del canal y del equipo.
- **FR-006**: El chequeo de salud del sistema MUST mostrar el modo actual del canal (abierto/cerrado) y advertir cuando
  está abierto.
- **FR-007**: En modo abierto, cada número que no sea de prueba MUST tener un límite de mensajes por ventana corta y un
  tope diario; al superarlos recibe un único aviso amable en su idioma y los mensajes extra no se procesan.
- **FR-008**: El operador MUST poder bloquear y desbloquear un número concreto; un número bloqueado no recibe
  respuesta.
- **FR-009**: Los atajos del operador MUST funcionar solo para los números de prueba cuando el canal está abierto.
- **FR-010**: El estado del canal MUST informar, sin números ni contenido, el modo, las personas distintas y los
  mensajes y limitados de la última hora y del día.
- **FR-011**: Los registros y la memoria MUST contener solo seudónimos y números enmascarados para todos los números
  (regla de privacidad del proyecto).
- **FR-012**: Los avisos de límite y bloqueo MUST ser naturales, en el idioma del mensaje y sin mencionar comandos.

### Key Entities

- **Modo del canal**: abierto o cerrado; cerrado incluye la lista de números de prueba.
- **Número de prueba**: número del equipo, sin límites y con acceso a los atajos del operador.
- **Contador por número**: mensajes en la ventana corta y en el día, por seudónimo; se reinicia al pasar la ventana o
  el día.
- **Número bloqueado**: seudónimo marcado por el operador; no recibe respuesta.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Desde al menos 2 números que nunca han escrito, 10 de 10 mensajes (texto y voz) reciben respuesta con el
  canal abierto.
- **SC-002**: Con el canal cerrado, 0 respuestas a números fuera de la lista de prueba; con el canal abierto, el cambio
  se completa y se verifica en menos de 5 minutos, incluido el reinicio.
- **SC-003**: Un número que envía 3 veces el límite de mensajes recibe exactamente 1 aviso de límite y el modelo
  procesa como máximo el límite configurado.
- **SC-004**: El chequeo de salud muestra el modo correcto en el 100 % de las consultas, después de cada cambio y de
  cada reinicio.
- **SC-005**: 0 números completos en registros, memoria o estado del canal tras una prueba con 3 números distintos.

## Assumptions

- El modo abierto es el que se usa desde ahora hasta el fin del proyecto (ensayo y sustentación); el cerrado queda
  para mantenimiento.
- Límites por defecto, ajustables en la configuración: 20 mensajes por número cada 10 minutos y 100 por día; los
  números de prueba no tienen límites.
- El bloqueo se hace por un paso del operador en el servidor (no desde WhatsApp) y se guarda junto con el resto del
  estado del canal, fuera del repositorio.
- La SIM es dedicada, no tiene límite de mensajes del operador móvil y se desactivará al terminar el proyecto (ver
  spec 028).
- No se cambia el agente, la recuperación ni los prompts: solo el acceso y las protecciones del canal.
- Los números reales de prueba nunca se guardan en archivos versionados.
