# Feature Specification: Modelo DeepSeek vía API en lugar de Ollama local

**Feature Branch**: `010-deepseek-api-model`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "Cambiar el modelo de ollama llama3.1:8b por el de DeepSeek V4.1 Flash 1017 consumido por API"

**Contexto**: el Módulo 1 responde hoy con un modelo local de Ollama (`llama3.1:8b`) a través de
`config/llm.toml` y de las tareas de Resumen, FAQ y Q&A. El equipo quiere dejar de depender de una
instalación local y consumir **DeepSeek V4.1 Flash 1017** como servicio remoto por API. La app, el CLI y
las pruebas deben seguir funcionando, el corpus y las capas medallion no cambian, y el proyecto sigue
siendo académico y sin afiliación.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obtener respuestas con el modelo en la nube (Priority: P1)

Un usuario abre la app, pregunta sobre Manuelita y recibe la misma respuesta citada de siempre, pero
generada por el modelo DeepSeek en lugar del modelo local.

**Why this priority**: es el objetivo del cambio. Si la calidad o el contrato de las tareas se degrada, el
resto de la funcionalidad del Módulo 1 pierde valor.

**Independent Test**: configurar el proveedor, ejecutar Q&A, Resumen y FAQ con el modelo nuevo y verificar
que cada resultado conserva su contrato: citas `[U#]`, fallback explícito, metadatos de modelo y latencia.

**Acceptance Scenarios**:

1. **Given** una clave de API válida configurada, **When** el usuario hace una pregunta con evidencia,
   **Then** la respuesta llega con al menos una cita y el campo de modelo muestra el identificador de
   DeepSeek.
2. **Given** el mismo corpus y la misma pregunta, **When** se ejecuta con el modelo nuevo, **Then** el
   formato de la respuesta, las citas y el fallback se mantienen igual que con el modelo anterior.
3. **Given** una pregunta sin evidencia suficiente, **When** se envía, **Then** la app responde el mensaje
   de fallback y no se envía ninguna petición al proveedor remoto.

---

### User Story 2 - Configurar el proveedor sin exponer la clave (Priority: P2)

Un integrante del equipo configura el proveedor en el repositorio, aporta la clave por variable de entorno
y comprueba en un comando que el servicio responde, sin que la clave aparezca en archivos versionados,
registros ni salidas de la app.

**Why this priority**: una clave filtrada en un repositorio público es un incidente irreversible; el cambio
introduce por primera vez un secreto real en el proyecto.

**Independent Test**: revisar la configuración versionada, ejecutar la verificación de salud y buscar la
clave en el historial, en los resultados y en la descarga de la sesión.

**Acceptance Scenarios**:

1. **Given** un clon limpio sin clave, **When** el usuario ejecuta la verificación del modelo,
   **Then** recibe un mensaje accionable que indica qué variable de entorno definir.
2. **Given** una clave válida en el entorno, **When** se ejecuta la verificación, **Then** confirma el
   proveedor, el modelo y la latencia sin imprimir la clave.
3. **Given** cualquier respuesta de la app o descarga de sesión, **When** se inspecciona su contenido,
   **Then** no aparece la clave, ni cabeceras de autorización, ni rutas absolutas.

---

### User Story 3 - Trabajar sin red ni costo (Priority: P3)

Un usuario sin conexión, o que no quiere consumir cuota, activa el modo demostración y recorre las cuatro
vistas con respuestas de prueba claramente rotuladas.

**Why this priority**: hoy el modo local permitía trabajar sin internet; al pasar a un servicio remoto, el
modo de demostración es la única vía offline y debe quedar explícita.

**Independent Test**: desconectar la red, activar el modo demostración y verificar que las cuatro vistas
responden sin errores y con el rótulo visible.

**Acceptance Scenarios**:

1. **Given** una red no disponible, **When** el usuario activa el modo demostración, **Then** las tres
   tareas responden con el modelo falso sin intentar ninguna llamada remota.
2. **Given** el modo demostración activo, **When** el usuario mira la interfaz, **Then** un distintivo
   persistente indica que las respuestas son de prueba.
3. **Given** el modo demostración desactivado y sin red, **When** el usuario pregunta, **Then** recibe un
   error accionable que sugiere activar el modo demostración.

---

### User Story 4 - Auditar el uso y el costo de las llamadas (Priority: P4)

Un evaluador revisa qué modelo respondió, cuántos tokens de entrada y salida se consumieron, cuánto tardó
la llamada y con qué parámetros se ejecutó.

**Why this priority**: la constitución exige reproducibilidad y evaluación con métricas; un servicio
remoto añade costo variable y latencia que deben quedar registrados.

**Independent Test**: generar una respuesta y revisar el resultado estructurado y el panel: modelo,
versión, tokens, latencia y configuración.

**Acceptance Scenarios**:

1. **Given** una respuesta generada por el servicio remoto, **When** se revisa el resultado, **Then**
   incluye modelo, tokens de entrada y salida, latencia y la versión del prompt.
2. **Given** una ejecución de las tres tareas, **When** se revisa el panel de métricas, **Then** se ve el
   proveedor activo y el costo estimado de la sesión.
3. **Given** dos ejecuciones con la misma pregunta, **When** se comparan, **Then** ambas registran el
   identificador exacto del modelo utilizado.

---

### User Story 5 - Recibir errores accionables del proveedor (Priority: P5)

Un usuario se encuentra con una clave inválida, un límite de cuota, un timeout o una caída del proveedor y
recibe un mensaje claro que le dice qué hacer, sin perder la sesión ni romper la app.

**Why this priority**: un servicio externo falla de formas que el modelo local no tenía; la interfaz debe
seguir siendo usable y transparente.

**Independent Test**: simular clave inválida, cuota agotada, timeout y error del servidor, y verificar que
cada caso muestra un mensaje distinto y accionable y que la app sigue operativa.

**Acceptance Scenarios**:

1. **Given** una clave inválida o revocada, **When** se ejecuta una tarea, **Then** el mensaje indica que la
   clave no es válida y cómo corregirla, sin mostrarla.
2. **Given** un límite de cuota alcanzado, **When** se ejecuta una tarea, **Then** el mensaje sugiere
   esperar o usar el modo demostración.
3. **Given** un timeout o una caída del proveedor, **When** se ejecuta una tarea, **Then** el resultado es
   un error controlado y el usuario puede reintentar sin reiniciar la sesión.

---

### Edge Cases

- La clave no está definida, está vacía o tiene espacios: error de configuración antes de llamar al
  proveedor.
- La clave está bien pero el identificador del modelo no existe o fue retirado: mensaje que distingue
  «modelo no disponible» de «clave inválida».
- La respuesta del proveedor llega vacía, truncada por límite de tokens o con formato inesperado: error
  controlado, nunca una respuesta vacía al usuario.
- El proveedor devuelve una respuesta sin citas: se aplica el reintento único y, si persiste, el error de
  citas faltantes ya definido.
- La red se corta a mitad de la llamada: error controlado con reintento disponible.
- La cuota se agota durante una sesión con varias respuestas: las respuestas previas se conservan.
- El corpus completo no cabe en el contexto del modelo: se usa el paquete de 8k y se declara.
- Se ejecuta en un equipo sin la variable de entorno pero con modo demostración activo: funciona sin
  llamadas remotas.
- El resultado se descarga como sesión: no incluye la clave ni cabeceras de autorización.
- El servicio remoto tarda más que el timeout configurado: se cancela y se informa.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST usar DeepSeek V4.1 Flash 1017 como modelo de generación para Resumen, FAQ y
  Q&A, en lugar del modelo local anterior.
- **FR-002**: El sistema MUST obtener la clave del proveedor únicamente de una variable de entorno y MUST
  NOT incluirla en archivos versionados.
- **FR-003**: El sistema MUST registrar en la configuración versionada el proveedor, el identificador del
  modelo, la URL base, el timeout y los reintentos, sin secretos.
- **FR-004**: El sistema MUST permitir verificar la disponibilidad del proveedor sin imprimir la clave y
  con un mensaje accionable cuando falle.
- **FR-005**: El sistema MUST conservar el contrato de las tres tareas: citas `[U#]`, fallback explícito,
  estados `ok|fallback|review|error` y metadatos del resultado.
- **FR-006**: El sistema MUST registrar en cada resultado el modelo exacto, la latencia y los tokens de
  entrada y salida reportados o estimados.
- **FR-007**: El sistema MUST ofrecer un modo demostración con modelo falso que funcione sin red y MUST
  rotularlo de forma persistente en la interfaz.
- **FR-008**: El sistema MUST distinguir y reportar al menos estos errores del proveedor: configuración
  ausente, clave inválida, modelo no disponible, límite de cuota, timeout y fallo del servidor.
- **FR-009**: El sistema MUST reintentar una vez ante errores transitorios y MUST NOT reintentar ante
  errores de autenticación.
- **FR-010**: El sistema MUST mantener la app y el CLI operativos con el proveedor nuevo, sin dependencia
  de una instalación local de Ollama.
- **FR-011**: El sistema MUST NOT enviar al proveedor datos distintos de los fragmentos de evidencia
  seleccionados y del enunciado de la tarea.
- **FR-012**: El sistema MUST aplicar el timeout configurado y cancelar la llamada cuando se exceda.
- **FR-013**: El sistema MUST conservar el funcionamiento en español y los nombres propios, siglas y cifras
  del corpus sin alterarlos.
- **FR-014**: El sistema MUST NOT escribir en las capas medallion ni modificar el corpus por efecto del
  cambio de proveedor.
- **FR-015**: El sistema MUST documentar en la configuración de ejemplo qué variable de entorno se requiere,
  sin valor real.
- **FR-016**: El sistema MUST permitir volver al modelo de demostración sin editar código, mediante
  configuración o variable de entorno.
- **FR-017**: El sistema MUST registrar el costo estimado de la sesión a partir de los tokens consumidos y
  una tarifa configurable.
- **FR-018**: El sistema MUST fallar con un error de configuración claro cuando la clave esté presente pero
  el modelo configurado no sea válido.
- **FR-019**: El sistema MUST NOT exponer encabezados de autorización, claves ni rutas absolutas en la
  interfaz, los registros ni la descarga de sesión.
- **FR-020**: El sistema MUST mantener las pruebas automatizadas sin red, usando el modelo falso para la
  suite por defecto.

### Key Entities *(include if feature involves data)*

- **Provider Config**: proveedor, modelo exacto, URL base, timeout, reintentos, tarifa y variable de
  entorno asociada; nunca contiene la clave.
- **Remote Call**: una invocación al proveedor con su prompt, tokens de entrada, tokens de salida, latencia
  y resultado o error.
- **Usage Summary**: acumulado de llamadas, tokens y costo estimado de una sesión.
- **Model Health**: estado del proveedor (disponible, clave inválida, modelo no disponible, sin red, cuota
  agotada) con su mensaje accionable.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las respuestas de las tres tareas se generan con el modelo nuevo cuando el
  proveedor está disponible y el modo demostración está desactivado.
- **SC-002**: El 100% de las respuestas conserva al menos una cita válida o el fallback explícito.
- **SC-003**: Cero apariciones de la clave en el repositorio, en los resultados, en los registros y en la
  descarga de sesión, verificado por búsqueda automatizada.
- **SC-004**: El 100% de los errores del proveedor produce un mensaje accionable y la interfaz sigue
  operativa.
- **SC-005**: La suite de pruebas se ejecuta sin red y pasa en menos de 2 minutos.
- **SC-006**: El modo demostración permite recorrer las cuatro vistas sin red en el 100% de los intentos.
- **SC-007**: Una respuesta típica se completa dentro del timeout configurado en el 95% de las llamadas al
  proveedor disponible.
- **SC-008**: El panel muestra modelo, tokens y costo estimado en el 100% de las sesiones con al menos una
  respuesta.
- **SC-009**: Un integrante nuevo configura el proveedor y obtiene su primera respuesta en menos de 10
  minutos siguiendo el README.
- **SC-010**: El cambio no altera ninguna cifra del corpus ni escribe en las capas medallion.

## Assumptions

- La clave del proveedor ya existe y se entregará por variable de entorno; no se solicita ni se versiona.
- El uso es académico y el contenido enviado son fragmentos públicos de Manuelita ya citados en el corpus.
- El modelo de demostración (respuestas enlatadas) sigue siendo el mecanismo offline; no se mantiene un
  modelo local como alternativa.
- El proveedor expone una interfaz compatible con el cliente HTTP actual del proyecto, por lo que no se
  requiere un SDK nuevo.
- La tarifa por token se configura manualmente y solo se usa para estimar costos, no para facturar.
- Las pruebas por defecto no consumen cuota: usan el modelo falso.
- La evaluación de 40 preguntas y el informe (M1-08 y M1-10) se ejecutarán después de este cambio.

## Out of Scope

- Entrenamiento, ajuste fino o despliegue del modelo.
- Cambios en el corpus, los prompts o las capas medallion.
- Comparación de calidad entre modelos o evaluación de 40 preguntas.
- Gestión de múltiples proveedores simultáneos o enrutamiento por costo.
- Facturación, cuotas por usuario o autenticación de usuarios de la app.
- Interfaz de administración de claves.
