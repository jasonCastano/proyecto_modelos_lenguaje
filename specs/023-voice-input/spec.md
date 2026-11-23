# Feature Specification: Hablarle a Valer-IA Caña con la voz (dictado en la interfaz)

**Feature Branch**: `023-voice-input`

**Created**: 2026-11-23

**Status**: Draft

**Input**: User description: "implementemos speech-to-text para hablar con Valer-IA en la interfaz"

**Contexto**: Desde la spec 016, Valer-IA Caña responde con voz: el visitante escribe y escucha la respuesta, frase por
frase (spec 021), con el avatar moviendo la boca (spec 017). La conversación sigue siendo de un solo sentido por voz:
el visitante tiene que escribir. Esta funcionalidad cierra el ciclo y deja que el visitante le hable a Valer-IA con el
micrófono. Lo que dice se convierte en texto en español y entra al mismo chat, con las mismas reglas, revisiones y
citas que un mensaje escrito.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Dictar una pregunta y enviarla (Priority: P1)

Un visitante abre el chat, pulsa el botón del micrófono, dice «¿Qué produce Manuelita?» y vuelve a pulsar para
terminar (o deja de hablar). El texto reconocido aparece en el campo del mensaje, donde puede revisarlo y corregirlo
antes de enviarlo como cualquier mensaje escrito. Valer-IA responde igual que si lo hubiera escrito.

**Why this priority**: Es el núcleo del pedido: hablarle a Valer-IA. Con solo esto el visitante ya puede usar la voz
para preguntar, y revisar el texto antes de enviarlo evita que un error de reconocimiento llegue al agente.

**Independent Test**: En modo demo y en modo real, dictar cinco preguntas de la batería de demostración, comprobar que
el texto aparece en el campo del mensaje, corregir una palabra a mano y enviar; la respuesta debe ser la misma que con
el texto escrito.

**Acceptance Scenarios**:

1. **Given** el chat abierto y el permiso del micrófono concedido, **When** el visitante pulsa el micrófono, habla y
   termina la grabación, **Then** el texto reconocido, en español, queda en el campo del mensaje sin enviarse.
2. **Given** un texto dictado en el campo, **When** el visitante lo edita y pulsa enviar, **Then** se envía el texto
   editado y la conversación sigue como con un mensaje escrito.
3. **Given** que el visitante habla con nombres propios de la empresa («Manuelita», «Palmira», «Valer-IA Caña»),
   **When** termina, **Then** esos nombres aparecen bien escritos en la mayoría de los casos (ver SC-002).
4. **Given** una grabación en curso, **When** el visitante deja de hablar durante unos segundos, **Then** la
   grabación termina sola y se procesa lo dicho.
5. **Given** una grabación en curso, **When** el visitante pulsa cancelar, **Then** no se reconoce ni se escribe nada.

---

### User Story 2 - Saber qué está pasando con el micrófono (Priority: P1)

Mientras graba, el visitante ve claramente que el micrófono está escuchando (indicador visible y nivel de voz), luego
que se está procesando y, al final, el texto. Si algo falla (permiso denegado, sin micrófono, nada entendido, servicio
de voz no disponible), recibe un mensaje claro en español y puede seguir escribiendo.

**Why this priority**: Sin estado visible, el visitante no sabe si debe hablar, esperar o repetir, y en la
sustentación un micrófono «mudo» parece un error. Grabar sin indicación también es un problema de privacidad.

**Independent Test**: Probar con el permiso concedido, denegado y sin micrófono; hablar en silencio; detener el
servicio de reconocimiento; en cada caso comprobar el mensaje y que el campo de texto sigue funcionando.

**Acceptance Scenarios**:

1. **Given** el micrófono escuchando, **When** el visitante habla, **Then** ve un indicador de grabación y un nivel de
   voz que se mueve con lo que dice.
2. **Given** que el navegador niega el permiso, **When** el visitante pulsa el micrófono, **Then** ve cómo
   habilitarlo y el chat por texto sigue disponible.
3. **Given** una grabación sin voz reconocible, **When** termina, **Then** el visitante ve «No te entendí, ¿puedes
   repetirlo?» (o equivalente) y el campo queda como estaba.
4. **Given** que el reconocimiento no está disponible en el servidor, **When** se carga la interfaz, **Then** el botón
   del micrófono no aparece o aparece deshabilitado con su motivo, y nada más cambia.

---

### User Story 3 - Conversación manos libres con Valer-IA (Priority: P2)

El visitante activa un modo de conversación por voz: habla, el mensaje se envía solo al terminar, escucha la
respuesta de Valer-IA y el micrófono vuelve a escuchar cuando ella termina. Si el visitante empieza a hablar mientras
Valer-IA habla, la voz de ella se detiene y se escucha al visitante.

**Why this priority**: Hace la experiencia de «hablar con Valer-IA» natural, pero depende de la US1 y conlleva más
riesgos (enviar algo mal reconocido, captar la voz de la propia asistente), por eso va después.

**Independent Test**: Activar el modo manos libres, mantener una conversación de cuatro turnos solo con la voz y
comprobar que cada mensaje se envía al terminar de hablar, que el micrófono no capta la voz de Valer-IA como mensaje
y que hablar encima de ella la interrumpe.

**Acceptance Scenarios**:

1. **Given** el modo manos libres activo, **When** el visitante termina de hablar, **Then** el texto reconocido se
   muestra y se envía sin pulsar nada.
2. **Given** que Valer-IA está hablando, **When** el visitante empieza a hablar, **Then** la voz de Valer-IA se detiene
   y el micrófono escucha al visitante.
3. **Given** que Valer-IA terminó su respuesta, **When** el modo manos libres sigue activo, **Then** el micrófono vuelve
   a escuchar.
4. **Given** el modo manos libres, **When** la voz de Valer-IA sale por los altavoces, **Then** no se envía como
   mensaje del visitante.
5. **Given** el modo manos libres, **When** el visitante lo desactiva o pasa un minuto sin hablar, **Then** el
   micrófono se apaga.

---

### User Story 4 - Ver el reconocimiento en la vista técnica (Priority: P3)

En la vista técnica (`?vista=tecnica`), el equipo ve, por cada mensaje dictado, que llegó por voz, cuánto duró la
grabación y cuánto tardó el reconocimiento, para explicar el flujo en la sustentación y medir la latencia.

**Why this priority**: Aporta trazabilidad y métricas para la evaluación, pero no cambia la experiencia del visitante.

**Independent Test**: Dictar dos mensajes y escribir uno en la vista técnica; los dictados muestran su origen, duración
y tiempo de reconocimiento; el escrito no.

**Acceptance Scenarios**:

1. **Given** la vista técnica, **When** el visitante envía un mensaje dictado, **Then** el turno muestra «por voz», la
   duración del audio y el tiempo de reconocimiento.
2. **Given** la vista de visitante, **When** se envía un mensaje dictado, **Then** no se muestran esos datos técnicos.

---

### Edge Cases

- El visitante habla más de lo permitido (por ejemplo, más de 60 segundos): la grabación se corta en el límite, se
  avisa y se reconoce lo grabado.
- El texto reconocido supera el máximo de un mensaje: se recorta al máximo y se avisa, como con un mensaje escrito.
- El visitante habla en otro idioma o mezcla idiomas: se reconoce lo posible; Valer-IA responde según sus reglas de
  idioma ya existentes.
- Ruido de fondo, voz muy baja o solo silencio: no se envía nada; se pide repetir.
- El visitante dice datos personales (correo, teléfono, documento): el texto pasa por las mismas protecciones de datos
  personales que un mensaje escrito; el audio no se guarda.
- El visitante cambia de pestaña o bloquea la pantalla mientras graba: la grabación se detiene y no se envía nada.
- Dos grabaciones seguidas muy rápidas, o pulsar enviar mientras se procesa: solo cuenta la última, sin mensajes
  duplicados.
- El navegador no permite micrófono (página sin conexión segura, navegador sin soporte): el botón no aparece y el chat
  por texto sigue igual.
- El reconocimiento tarda demasiado o falla a mitad: se avisa, se descarta el audio y el visitante puede repetir o
  escribir.
- La primera vez que se usa, el reconocimiento necesita preparar su modelo: la interfaz muestra que se está
  preparando, sin bloquear el chat por texto.
- Varios visitantes dictando a la vez: cada uno recibe solo su propio texto.

## Requirements *(mandatory)*

### Functional Requirements

**Captura**

- **FR-001**: La interfaz MUST ofrecer un botón de micrófono junto al campo del mensaje, en la vista de visitante y en
  la técnica, en escritorio y en móvil.
- **FR-002**: La interfaz MUST pedir el permiso del micrófono solo cuando el visitante pulsa el botón por primera vez,
  nunca al cargar la página.
- **FR-003**: Mientras graba, la interfaz MUST mostrar un indicador de grabación inequívoco y el nivel de voz, y
  ofrecer terminar y cancelar.
- **FR-004**: La grabación MUST terminar por cualquiera de estas causas: el visitante la termina, un silencio
  sostenido después de haber hablado, o el límite máximo de duración.
- **FR-005**: La grabación MUST detenerse sin enviar nada si el visitante cancela, cambia de pestaña o la página
  pierde el foco del micrófono.

**Reconocimiento**

- **FR-006**: El sistema MUST convertir la voz en texto en español, con puntuación y mayúsculas razonables.
- **FR-007**: El reconocimiento MUST hacerse con un modelo que corre en el propio servidor del proyecto, sin enviar el
  audio a servicios de terceros, y MUST funcionar también en modo demo, sin la clave del proveedor del modelo de
  lenguaje.
- **FR-008**: El sistema MUST favorecer la escritura correcta del vocabulario propio (Manuelita, Valer-IA Caña,
  Palmira, nombres de negocios y sedes) a partir de una lista configurable.
- **FR-009**: Si no se reconoce voz (silencio, ruido o habla ininteligible), el sistema MUST devolver «sin texto» en
  lugar de inventar palabras, y la interfaz MUST pedir que se repita.
- **FR-010**: El sistema MUST limitar la duración y el tamaño del audio aceptado y rechazar formatos no admitidos con
  un mensaje claro.

**Integración con el chat**

- **FR-011**: En el modo normal, el texto reconocido MUST quedar en el campo del mensaje, editable y sin enviarse;
  el visitante decide cuándo enviarlo.
- **FR-012**: Un mensaje dictado MUST seguir exactamente el mismo camino que uno escrito: mismas reglas de conducta,
  revisión, citas, protección de datos personales, memoria y registro del contacto.
- **FR-013**: Al empezar a grabar, la voz de Valer-IA que esté sonando MUST detenerse.
- **FR-014**: En el modo manos libres, el mensaje MUST enviarse al terminar de hablar, el micrófono MUST volver a
  escuchar cuando Valer-IA termina su respuesta, y hablar mientras ella habla MUST interrumpirla.
- **FR-015**: En el modo manos libres, la voz de Valer-IA MUST NOT reconocerse ni enviarse como mensaje del visitante.
- **FR-016**: El modo manos libres MUST apagarse solo tras un minuto sin voz del visitante, y el visitante MUST poder
  desactivarlo en cualquier momento.
- **FR-017**: La preferencia del modo (normal o manos libres) MUST conservarse en el navegador del visitante entre
  recargas; el permiso del micrófono lo gestiona el navegador.

**Privacidad y disponibilidad**

- **FR-018**: El audio MUST procesarse en memoria y descartarse al terminar el reconocimiento: no se guarda en disco,
  en `data/`, en registros ni en trazas; solo se conserva el texto que el visitante envía, como cualquier mensaje.
- **FR-019**: La interfaz MUST informar, junto al micrófono, que el audio se procesa en el servidor del proyecto y no
  se guarda.
- **FR-020**: Si el reconocimiento no está disponible (modelo no instalado o error al cargar), el sistema MUST
  informarlo en su estado de salud y la interfaz MUST ocultar o deshabilitar el micrófono sin afectar el chat por
  texto ni la voz de salida.
- **FR-021**: Los mensajes de error MUST estar en español, sin detalles técnicos para el visitante.

**Trazabilidad**

- **FR-022**: Cada mensaje dictado MUST registrar su origen («voz»), la duración del audio y el tiempo de
  reconocimiento, visibles solo en la vista técnica.
- **FR-023**: El proyecto MUST incluir una evaluación reproducible del reconocimiento con grabaciones de prueba en
  español (incluido el vocabulario propio) que informe la tasa de error de palabras, el acierto en nombres propios y
  la latencia.

### Key Entities *(include if feature involves data)*

- **Grabación**: audio de una intervención del visitante; vive solo en memoria mientras se reconoce. Atributos:
  duración, motivo de fin (manual, silencio, límite, cancelación).
- **Transcripción**: texto reconocido de una grabación, con idioma, duración del audio y tiempo de reconocimiento; puede
  estar vacía («sin texto»).
- **Mensaje dictado**: mensaje del chat cuyo origen es una transcripción (editada o no); se comporta como un mensaje
  escrito y lleva su origen y sus tiempos para la vista técnica.
- **Preferencia de voz de entrada**: modo normal o manos libres, guardado en el navegador del visitante.
- **Vocabulario propio**: lista configurable de nombres y términos de Manuelita que el reconocimiento debe favorecer.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En la batería de grabaciones de prueba, la tasa de error de palabras es de 15 % o menos con habla clara
  en español.
- **SC-002**: En esa batería, al menos el 90 % de las apariciones de nombres del vocabulario propio quedan bien
  escritas.
- **SC-003**: Para intervenciones de hasta 10 segundos, el texto aparece en menos de 2 segundos después de terminar de
  hablar en el 90 % de los casos, en el equipo de la sustentación.
- **SC-004**: En 100 % de las grabaciones de silencio o ruido de la batería, no se escribe ni se envía texto.
- **SC-005**: En el modo manos libres, en 20 turnos de prueba con altavoces, la voz de Valer-IA se envía como mensaje
  del visitante 0 veces.
- **SC-006**: Ningún archivo de audio queda guardado en el servidor después de usar el dictado (comprobado tras la
  batería y la prueba manual).
- **SC-007**: Un visitante nuevo completa una pregunta dictada y recibe la respuesta en su primer intento en al menos
  4 de 5 pruebas con usuarios del equipo.
- **SC-008**: Con el reconocimiento no disponible, el chat por texto y la voz de Valer-IA funcionan igual que hoy
  (todas las pruebas existentes siguen pasando).

## Assumptions

- **Idioma**: el dictado se centra en español de Colombia; otros idiomas no son objetivo de esta versión.
- **Dónde se reconoce**: en el servidor del proyecto con un modelo local, coherente con la voz de salida local de la
  spec 016 y con la regla de no enviar datos del visitante a terceros. Se descarta el reconocimiento integrado del
  navegador porque en varios navegadores envía el audio a servicios externos y no funciona igual en todos.
- **Equipo**: el equipo de la sustentación puede correr un modelo de reconocimiento pequeño en CPU; la primera vez
  puede necesitar descargarlo, como el modelo de voz de la spec 016.
- **Navegador**: Chrome, Edge o Firefox recientes, por `localhost` o por una conexión segura (los navegadores solo
  permiten el micrófono en esos casos).
- **Modo por defecto**: el normal (texto al campo y el visitante envía); el modo manos libres se activa a mano.
- **Límites por defecto**: 60 segundos por grabación y fin automático tras 1.5 segundos de silencio después de hablar;
  ambos configurables.
- **Fuera de alcance**: identificar a quien habla, traducir, transcribir audios subidos como archivo, dictar en
  formularios distintos del chat y llamadas telefónicas.
- **Dependencias**: chat y servicio del agente (specs 018–022), voz de salida (016), avatar (017) y entrega por frases
  (021); el modo manos libres se apoya en el control de reproducción ya existente para detener y reanudar la voz.
