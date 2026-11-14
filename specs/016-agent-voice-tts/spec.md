# Feature Specification: Voz del agente en español con síntesis natural (Phonon)

**Feature Branch**: `016-agent-voice-tts`

**Created**: 2026-11-14

**Status**: Draft

**Input**: User description: "implementa phonon en el proyecto para traer natural text-to-speech, el agente debe tener voz
en español, preferiblemente voz de mujer, y cuando se genere una respuesta en el chatbot con el agente debe ejecutarse
el audio del texto producido de la respuesta en tiempo real"

**Contexto**: Hoy el chatbot del agente RAG de Ingenio Manuelita responde solo por texto, que aparece en streaming
mientras el modelo genera. Esta funcionalidad le da voz al agente: la respuesta se escucha en español, con una voz
femenina natural, a medida que se va produciendo, sin esperar a que termine el texto completo. El equipo pidió
expresamente el motor Phonon (modelo de síntesis de voz liviano y local, con voces en español).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Escuchar la respuesta del agente mientras se genera (Priority: P1)

Un visitante escribe una pregunta en el chat del agente («¿Qué produce Manuelita?»). Mientras el texto de la
respuesta aparece en pantalla, el visitante empieza a escuchar esa misma respuesta leída en voz alta, en español y con
una voz femenina natural. La lectura avanza al ritmo de la generación: la primera oración suena antes de que termine
de escribirse la respuesta completa.

**Why this priority**: Es el núcleo del pedido: el agente debe «tener voz» y la respuesta debe sonar en tiempo real.
Sin esto la funcionalidad no aporta valor.

**Independent Test**: Abrir el chat, hacer una pregunta en modo demo y en modo real, y comprobar que el audio empieza
mientras el texto sigue llegando, que la voz es femenina y en español, y que lo que se escucha coincide con el texto
mostrado.

**Acceptance Scenarios**:

1. **Given** el chat del agente abierto con la voz activada, **When** el visitante envía una pregunta, **Then** la
   primera oración de la respuesta empieza a sonar antes de que termine el streaming del texto.
2. **Given** una respuesta de varias oraciones, **When** se reproduce, **Then** las oraciones suenan en orden, sin
   repeticiones, sin saltos y sin superponerse.
3. **Given** una respuesta con citas y marcas internas (por ejemplo `[U3]`, marcas de fragmento omitido o formato
   Markdown), **When** se reproduce, **Then** la voz lee solo el texto natural y no pronuncia símbolos, etiquetas ni
   enlaces.
4. **Given** una respuesta en modo demo (sin clave del proveedor del modelo de lenguaje), **When** se genera,
   **Then** también se escucha, porque la voz no depende del proveedor del modelo de lenguaje.

---

### User Story 2 - Controlar la voz (Priority: P2)

El visitante puede silenciar o reactivar la voz del agente, detener la lectura en curso y volver a escuchar una
respuesta anterior. Si envía una nueva pregunta mientras suena una respuesta, la lectura anterior se detiene y empieza
la nueva.

**Why this priority**: El audio automático sin control resulta molesto en salas, presentaciones o equipos compartidos;
el control es necesario para que la voz sea usable en la sustentación.

**Independent Test**: Con una respuesta sonando, pulsar detener, silenciar, reactivar y «escuchar de nuevo»; enviar una
segunda pregunta durante la lectura; recargar la página y comprobar que la preferencia de silencio se conserva.

**Acceptance Scenarios**:

1. **Given** una respuesta sonando, **When** el visitante pulsa «detener», **Then** el audio se interrumpe en menos de
   medio segundo y el texto sigue visible completo.
2. **Given** la voz silenciada, **When** llega una nueva respuesta, **Then** no se reproduce audio y el texto se
   muestra igual que hoy.
3. **Given** una respuesta anterior del hilo, **When** el visitante pulsa «escuchar», **Then** esa respuesta se lee
   completa con la misma voz.
4. **Given** una respuesta sonando, **When** el visitante envía otra pregunta, **Then** la lectura anterior se detiene
   y no se mezcla con la nueva.
5. **Given** que el visitante silenció la voz, **When** recarga la página, **Then** la voz sigue silenciada.

---

### User Story 3 - Degradación segura cuando la voz no está disponible (Priority: P3)

Si el motor de voz no está instalado, el modelo de voz no se pudo descargar, el equipo no es compatible o la síntesis
falla a mitad de una respuesta, el chat sigue funcionando por texto exactamente como hoy y el visitante ve un aviso
breve de que la voz no está disponible.

**Why this priority**: La voz es una mejora; nunca debe romper el chat ni la evaluación de la rúbrica.

**Independent Test**: Arrancar la aplicación sin el modelo de voz disponible (o forzando un fallo) y comprobar que el
chat responde por texto, que aparece el aviso y que el estado del servidor informa que la voz no está disponible.

**Acceptance Scenarios**:

1. **Given** el motor de voz no disponible, **When** se abre el chat, **Then** el control de voz aparece deshabilitado
   con un aviso y el chat responde por texto con normalidad.
2. **Given** un fallo de síntesis en mitad de una respuesta, **When** ocurre, **Then** la lectura se detiene, el texto
   llega completo y el error no interrumpe el turno del agente.
3. **Given** el estado del servidor, **When** se consulta, **Then** informa si la voz está disponible y qué voz está
   configurada.

---

### Edge Cases

- El navegador bloquea la reproducción automática de audio hasta que hay interacción del usuario: el envío de la
  pregunta cuenta como interacción; si aun así se bloquea, se muestra un botón para reproducir.
- Respuestas muy largas (resúmenes o FAQ extensas): la lectura sigue oración por oración sin acumular retrasos ni
  memoria sin límite.
- Respuestas de respaldo («no tengo evidencia suficiente») y mensajes de error del agente también se leen, pero nunca
  se leen los mensajes técnicos internos.
- Pausas del agente por aprobación de una acción de escritura (tarjeta de aprobación): se lee el texto explicativo, no
  los datos técnicos de la acción.
- Números, siglas, cifras con unidades, porcentajes, fechas y nombres propios del dominio (Manuelita, Valle del Cauca,
  etanol, kWh) se pronuncian de forma comprensible en español.
- Texto en otro idioma dentro de la respuesta (por ejemplo, un nombre en inglés) no detiene la lectura.
- Varias pestañas o varios visitantes a la vez: cada uno escucha solo su propia respuesta.
- La conexión se corta en medio del streaming: el audio se detiene con el texto ya recibido, sin quedar sonando en
  bucle.
- Corpus adversarial activo: la voz lee la respuesta final del agente, nunca el contenido de los documentos
  recuperados ni oraciones neutralizadas.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST leer en voz alta, en español, las respuestas del agente en el chat, usando el motor de
  síntesis Phonon con un modelo de voz en español.
- **FR-002**: La voz por defecto MUST ser femenina y en español; la voz concreta MUST ser configurable por el
  operador sin cambiar código, eligiendo entre las voces en español del catálogo del motor.
- **FR-003**: La reproducción MUST empezar mientras la respuesta se sigue generando, avanzando por oraciones completas
  a medida que el texto llega, sin esperar al final de la respuesta.
- **FR-004**: Las oraciones MUST sonar en el mismo orden del texto, una sola vez cada una, sin superponerse.
- **FR-005**: Antes de sintetizar, el texto MUST limpiarse de citas (`[U#]`), marcas de fragmento omitido, formato
  Markdown, URLs y símbolos que no deban pronunciarse.
- **FR-006**: El visitante MUST poder silenciar y reactivar la voz, detener la lectura en curso y volver a escuchar
  cualquier respuesta del hilo; la preferencia de silencio MUST conservarse al recargar la página en ese navegador.
- **FR-007**: Al enviar una nueva pregunta, la lectura en curso MUST detenerse antes de que empiece la nueva.
- **FR-008**: La voz MUST funcionar en los modos demo y real del agente, y en sus dos variantes (chain y agent).
- **FR-009**: Si el motor o el modelo de voz no está disponible o falla, el chat MUST seguir funcionando por texto sin
  errores visibles para el turno, mostrando un aviso de que la voz no está disponible.
- **FR-010**: El estado del servidor MUST informar si la voz está disponible y qué voz y modelo están configurados.
- **FR-011**: La síntesis MUST ejecutarse en el equipo donde corre la aplicación, sin enviar el texto de las respuestas
  a servicios externos de voz, y sin requerir la clave del proveedor del modelo de lenguaje.
- **FR-012**: La aplicación MUST NOT escribir audio ni archivos del modelo de voz en `data/` ni en el repositorio;
  los archivos del modelo se guardan en una caché fuera del repositorio.
- **FR-013**: Las pruebas automáticas (unitarias, de contrato y de la interfaz) MUST pasar sin red y sin descargar el
  modelo de voz, usando un sintetizador simulado; las pruebas con el modelo real quedan marcadas aparte, como las
  pruebas con red.
- **FR-014**: Cada respuesta leída MUST registrarse en la observabilidad existente con la voz usada, el número de
  oraciones sintetizadas, el tiempo hasta el primer audio y si hubo fallos, sin guardar el audio.
- **FR-015**: La licencia del modelo de voz (uso no comercial) MUST quedar documentada junto con la decisión de
  adoptarlo.

### Key Entities *(include if feature involves data)*

- **Configuración de voz**: motor, modelo de voz, voz seleccionada (nombre e identificador), idioma, velocidad,
  disponibilidad.
- **Segmento de voz**: una oración limpia de la respuesta, con su posición en la respuesta y su audio sintetizado.
- **Sesión de lectura**: la lectura de una respuesta concreta del hilo; estados: en espera, sonando, detenida,
  terminada, fallida.
- **Preferencia de voz del visitante**: voz activada o silenciada, guardada en el navegador.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En el 90 % de las preguntas del chat, el visitante escucha la primera oración en menos de 1,5 segundos
  desde que esa oración aparece completa en pantalla, en el equipo de la sustentación.
- **SC-002**: El 100 % de las respuestas leídas suenan en el orden del texto, sin oraciones repetidas ni omitidas
  (verificado sobre al menos 10 respuestas de las preguntas de la rúbrica).
- **SC-003**: Ninguna lectura pronuncia citas, etiquetas, enlaces ni marcas internas en una muestra de 10 respuestas
  con citas.
- **SC-004**: Al menos 2 de cada 3 personas del equipo y evaluadores que escuchan las respuestas califican la voz como
  natural y comprensible en español.
- **SC-005**: Detener o silenciar corta el audio en menos de 0,5 segundos en el 100 % de los intentos.
- **SC-006**: Con la voz no disponible, el 100 % de las preguntas se responden por texto igual que antes de esta
  funcionalidad.
- **SC-007**: La verificación completa del proyecto sigue pasando sin red y sin descargar el modelo de voz.

## Assumptions

- **Motor elegido por el equipo**: Phonon (Gradium), modelo en español `phonon-40m-es`, de unos 40 millones de
  parámetros, que corre en CPU sin GPU, genera audio mono a 24 kHz y permite reproducir por fragmentos mientras
  sintetiza. Su catálogo tiene 13 voces femeninas en español (España y México).
- **Voz por defecto**: una voz femenina en español latinoamericano (catálogo de México), por cercanía con el público
  colombiano del proyecto; la elección final de la voz se hace escuchando las muestras durante el plan.
- **Licencia**: los pesos y voces del modelo en español son CC BY-NC 4.0 (no comercial); el uso académico del curso
  encaja en esa licencia. El motor de ejecución es MIT/Apache-2.0.
- **Acceso al modelo**: el modelo en Hugging Face requiere aceptar sus condiciones con una cuenta; la descarga usa un
  token de Hugging Face guardado como secreto local (`.env`), nunca versionado.
- **Equipo de la sustentación**: CPU x86-64 compatible con AVX2 (requisito de los binarios precompilados del motor) o
  Apple Silicon.
- **Alcance**: solo se da voz a las respuestas del chat del agente; las vistas de Resumen, FAQ y la consola RAG quedan
  fuera de esta funcionalidad. No se incluye reconocimiento de voz (dictar preguntas) ni clonación de voz.
- **Activación por defecto**: la voz está activada por defecto y el visitante puede silenciarla.
- **Velocidad de lectura**: velocidad normal del motor; ajustes finos de velocidad o tono quedan fuera del alcance.

## Dependencies

- Motor de síntesis Phonon y su modelo en español, descargable tras aceptar las condiciones del modelo.
- El streaming actual de respuestas del agente (que ya entrega el texto por fragmentos) como fuente del texto a leer.
- Reproducción de audio del navegador del visitante.
