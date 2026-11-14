# Feature Specification: Avatar del agente con sincronización de labios

**Feature Branch**: `017-avatar-lipsync`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "crea el avatar local con sincronización de labios"

**Contexto**: Desde la spec 016, el agente lee sus respuestas en voz alta con la voz femenina «Rebeca», oración por
oración y mientras se generan. Esta funcionalidad le da una cara: un avatar ilustrado junto al chat que mueve la boca
al ritmo exacto del audio que se escucha, parpadea y muestra cuándo está pensando. Todo funciona en el equipo del
visitante, sin servicios externos de pago ni envío del audio a terceros. Se descartó un avatar fotorrealista en la
nube (HeyGen LiveAvatar) por costo, dependencia de red y privacidad.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Ver al agente hablar con la boca sincronizada (Priority: P1)

Un visitante pregunta «¿Qué produce Manuelita?» en el chat. Junto a la conversación está el avatar del agente. Cuando
empieza a sonar la respuesta, la boca del avatar se abre y se cierra al ritmo de la voz: se abre en las sílabas
sonoras, cambia de forma según el sonido (más redonda, más abierta o más estirada) y se cierra en las pausas y
al terminar cada oración. Cuando la voz se detiene, la boca queda cerrada.

**Why this priority**: Es el núcleo del pedido. Sin la boca sincronizada, el avatar es solo una imagen.

**Independent Test**: Hacer una pregunta con la voz activada y observar que la boca se mueve solo mientras hay voz, que
se cierra en los silencios entre oraciones y que queda cerrada al terminar, en los modos demo y real.

**Acceptance Scenarios**:

1. **Given** el chat con voz activada, **When** suena una respuesta, **Then** la boca del avatar se mueve mientras se
   escucha la voz y se cierra cuando hay silencio.
2. **Given** una respuesta con varias oraciones, **When** se reproduce, **Then** en la pausa entre oraciones la boca
   se cierra y vuelve a moverse con la siguiente.
3. **Given** que la voz termina o el visitante pulsa «Detener», **When** el audio se corta, **Then** la boca se cierra
   de inmediato y el avatar vuelve al reposo.
4. **Given** sonidos distintos en la voz, **When** se reproducen, **Then** la boca cambia entre al menos tres formas
   abiertas además de la cerrada, sin saltos bruscos de un cuadro a otro.

---

### User Story 2 - Un avatar que transmite su estado (Priority: P2)

Mientras el visitante lee o escribe, el avatar está en reposo: respira suavemente y parpadea de vez en cuando. Cuando
el visitante envía una pregunta y el agente busca evidencia y genera la respuesta, el avatar muestra que está
pensando (por ejemplo, mira hacia un lado). Cuando empieza a hablar, pasa al estado de habla.

**Why this priority**: Los estados hacen que el avatar se sienta vivo y comunican qué está haciendo el agente, pero la
funcionalidad sigue siendo útil sin ellos.

**Independent Test**: Observar el avatar sin interacción (parpadeo y respiración), durante la generación de una
respuesta (pensando) y al hablar (boca sincronizada), y comprobar que vuelve al reposo al terminar.

**Acceptance Scenarios**:

1. **Given** el avatar sin actividad, **When** pasan 10 segundos, **Then** parpadea al menos una vez, a intervalos
   irregulares.
2. **Given** una pregunta enviada, **When** el agente está generando la respuesta, **Then** el avatar muestra el
   estado «pensando» hasta que empieza a hablar o termina el turno.
3. **Given** un turno que termina sin audio (voz silenciada o no disponible), **When** llega la respuesta, **Then** el
   avatar sale del estado «pensando» y vuelve al reposo con la boca cerrada.

---

### User Story 3 - Accesible, discreto y sin riesgos (Priority: P3)

El avatar respeta la preferencia de movimiento reducido del sistema, no tapa la conversación en pantallas pequeñas y
se puede ocultar. Si la voz está silenciada o no disponible, el avatar sigue mostrando sus estados pero no mueve la
boca. Nada de esto cambia el funcionamiento del chat.

**Why this priority**: Evita que el avatar moleste o rompa la experiencia, pero no es lo que el visitante percibe
primero.

**Independent Test**: Activar «reducir movimiento» en el sistema, abrir la app en ancho de teléfono, ocultar el
avatar y recargar, y silenciar la voz; en todos los casos el chat funciona igual.

**Acceptance Scenarios**:

1. **Given** la preferencia de movimiento reducido activa, **When** el avatar está en reposo o pensando, **Then** no
   hay respiración ni movimientos de mirada; solo se mueve la boca al hablar.
2. **Given** una pantalla de teléfono, **When** se abre el chat, **Then** el avatar se muestra en tamaño reducido sin
   tapar los mensajes ni el campo de escritura.
3. **Given** que el visitante oculta el avatar, **When** recarga la página, **Then** el avatar sigue oculto y la voz
   sigue funcionando.
4. **Given** la voz silenciada o no disponible, **When** el agente responde, **Then** la boca no se mueve y el chat
   responde por texto igual que antes.

---

### Edge Cases

- El navegador bloquea el audio hasta que hay interacción: la boca solo se mueve cuando el audio realmente suena.
- Respuestas muy largas: la animación no se degrada ni consume más recursos con el tiempo.
- Pestaña en segundo plano: la animación se detiene y se reanuda sin desfase al volver.
- «Escuchar» una respuesta anterior: el avatar habla igual que en vivo.
- Una nueva pregunta mientras habla: la boca se cierra y el avatar pasa a «pensando».
- Voz muy baja o con ruido de fondo: la boca no tiembla con el ruido; solo se abre con voz audible.
- Corpus adversarial activo: el avatar no cambia de comportamiento; solo refleja el audio de la respuesta final.
- El navegador no permite analizar el audio: el avatar muestra los estados de reposo y pensando, con la boca cerrada.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El chat del agente MUST mostrar un avatar ilustrado del agente junto a la conversación.
- **FR-002**: La boca del avatar MUST moverse siguiendo el audio de la voz del agente que se está reproduciendo en ese
  momento, abriéndose con la voz y cerrándose en los silencios.
- **FR-003**: La boca MUST tener al menos cinco formas: cerrada, entreabierta y tres formas abiertas distintas
  (abierta, redondeada y estirada). La transición entre formas MUST ser suave, sin parpadeos.
- **FR-004**: Al detenerse el audio (fin de la respuesta, «Detener», silenciar, nueva pregunta o error), la boca MUST
  cerrarse en menos de 0,2 segundos.
- **FR-005**: El avatar MUST tener tres estados visibles: reposo (respiración y parpadeo irregular), pensando (mientras
  el agente genera la respuesta) y hablando.
- **FR-006**: Con la preferencia de movimiento reducido del sistema activa, el avatar MUST suprimir respiración y
  miradas, y conservar solo el movimiento de la boca al hablar.
- **FR-007**: El visitante MUST poder ocultar y volver a mostrar el avatar; la preferencia MUST conservarse al
  recargar la página en ese navegador.
- **FR-008**: El avatar MUST funcionar sin servicios externos y en los modos demo y real; MUST NOT enviar audio ni
  texto a terceros ni requerir claves nuevas.
- **FR-009**: Si la voz está silenciada, no disponible o el navegador no permite analizar el audio, el avatar MUST
  mostrar sus estados con la boca cerrada, y el chat MUST seguir funcionando igual que antes de esta funcionalidad.
- **FR-010**: El avatar MUST ser decorativo para tecnologías de asistencia (no anuncia contenido), y el estado del
  agente MUST seguir comunicándose por texto como hoy.
- **FR-011**: La ilustración MUST ser original: no imitar a una persona real ni usar la marca de Manuelita, y MUST
  presentarse como una asistente femenina coherente con la voz de Rebeca y con la paleta de la app.
- **FR-012**: El avatar MUST adaptarse a pantallas de teléfono sin tapar los mensajes ni el campo de escritura.
- **FR-013**: Las pruebas automáticas MUST cubrir el comportamiento de la boca y de los estados sin red ni audio real.

### Key Entities *(include if feature involves data)*

- **Estado del avatar**: reposo, pensando o hablando; se deriva del estado del turno y de la voz.
- **Forma de la boca**: cerrada, entreabierta, abierta, redondeada o estirada, con un nivel de apertura.
- **Preferencia de visibilidad**: avatar visible u oculto, guardada en el navegador.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Durante la reproducción de 10 respuestas, la boca está cerrada en al menos el 90 % de los silencios de
  más de 0,3 segundos y abierta en al menos el 90 % de los tramos con voz audible.
- **SC-002**: La boca se cierra en menos de 0,2 segundos después de que el audio se detiene, en el 100 % de los casos.
- **SC-003**: La animación se mantiene fluida (sin saltos perceptibles) durante respuestas de hasta 2 minutos en el
  equipo de la sustentación.
- **SC-004**: Al menos 2 de cada 3 personas del equipo y evaluadores perciben que la boca va sincronizada con la voz.
- **SC-005**: Con el avatar oculto, voz silenciada o movimiento reducido, el 100 % de las preguntas se responden igual
  que antes de esta funcionalidad.
- **SC-006**: La verificación completa del proyecto sigue pasando sin red.

## Assumptions

- **Técnica de sincronización**: la boca reacciona al volumen y al timbre del audio que se reproduce (no a fonemas
  exactos). Esto da sincronización inmediata con lo que se escucha; el cierre perfecto en «m», «b» o «p» queda fuera
  del alcance.
- **Estilo**: ilustración plana y sencilla, dibujada para el proyecto, con aspecto de asistente femenina, en los
  colores de la app. Si el equipo aporta otra ilustración, sirve siempre que tenga la boca en capas separadas.
- **Ubicación**: junto a la conversación en escritorio y en tamaño reducido en teléfono; visible por defecto.
- **Alcance**: solo el chat del agente (no Resumen, FAQ ni consola RAG). Sin cámara, sin reconocimiento de voz ni
  avatar fotorrealista.
- **Sin cambios en el servidor**: el audio ya llega al navegador por la voz de la spec 016.

## Dependencies

- La voz del agente (spec 016): reproducción por oraciones en el navegador, controles de silenciar y detener, y
  estados del turno en el chat.
