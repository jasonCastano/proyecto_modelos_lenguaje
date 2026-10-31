# Feature Specification: App Streamlit — Resumen, FAQ y Q&A

**Feature Branch**: `008-streamlit-qa-app`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "realiza las especificaciones para la tarea con ID M1-07"

**Contexto**: la app es la interfaz de prueba del Módulo 1. Debe exponer las tres tareas ya implementadas
en `tasks.py` —Resumen, FAQ y Q&A— sobre la base de oro de Manuelita, con citas verificables, panel de
métricas y manejo de errores. Se ejecuta con `uv run streamlit run app.py` y no requiere claves de API.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preguntar y recibir una respuesta citada (Priority: P1)

Un usuario abre la app, escribe una pregunta sobre Manuelita y recibe una respuesta breve con las fuentes
citadas. Si no hay evidencia, la app lo dice y no inventa.

**Why this priority**: es la funcionalidad principal de la app y la que se mostrará en la demo y en la
evaluación de 40 preguntas.

**Independent Test**: abrir la pestaña Q&A, formular 5 preguntas del alcance y verificar que cada respuesta
tiene al menos una cita visible o un fallback explícito, sin errores no controlados.

**Acceptance Scenarios**:

1. **Given** una pregunta con evidencia en la base de oro, **When** el usuario la envía, **Then** la app
   muestra la respuesta, las citas `[U#]` y enlaces a las fuentes.
2. **Given** una pregunta sin evidencia, **When** el usuario la envía, **Then** la app muestra el mensaje
   “No hay evidencia suficiente en el corpus para responder.” y no inventa contenido.
3. **Given** una pregunta vacía, **When** el usuario intenta enviarla, **Then** la app muestra una
   validación y no llama al modelo.
4. **Given** un modelo no disponible o un timeout, **When** el usuario envía la pregunta, **Then** la app
   muestra un error accionable y mantiene la interfaz usable.

---

### User Story 2 - Consultar el resumen del corpus (Priority: P2)

Un integrante del equipo abre la pestaña Resumen y obtiene una síntesis estructurada del corpus con citas,
lista para la demo y el informe.

**Why this priority**: el Resumen es una de las tres funcionalidades obligatorias y alimenta la narrativa
de la demo.

**Independent Test**: generar el resumen desde la app y verificar que tiene 8–12 citas, secciones legibles
y fuentes visibles.

**Acceptance Scenarios**:

1. **Given** la base de oro disponible, **When** el usuario pulsa “Generar resumen”, **Then** la app
   muestra la síntesis con 8–12 citas y la lista de fuentes.
2. **Given** un contexto vacío o insuficiente, **When** el usuario pulsa el botón, **Then** la app muestra
   el fallback y no inventa secciones.
3. **Given** una generación previa en la misma sesión, **When** el usuario cambia de pestaña y vuelve,
   **Then** el resultado se conserva sin volver a llamar al modelo.

---

### User Story 3 - Consultar preguntas frecuentes (Priority: P3)

Un usuario abre la pestaña FAQ y revisa entre 10 y 20 preguntas frecuentes con respuesta, citas y estado de
revisión.

**Why this priority**: la FAQ es la tercera funcionalidad obligatoria y reduce el trabajo manual de
seleccionar preguntas para la demo.

**Independent Test**: generar la FAQ desde la app y verificar que hay 10–20 elementos, cada uno con
respuesta y cita o estado `missing_evidence`.

**Acceptance Scenarios**:

1. **Given** las preguntas semilla y sus evidencias, **When** el usuario pulsa “Generar FAQ”, **Then** la
   app muestra 10–20 preguntas expandibles con respuesta y citas.
2. **Given** una semilla sin evidencia, **When** se genera la FAQ, **Then** la app la muestra como
   `missing_evidence` o la omite, sin inventar.
3. **Given** una FAQ ya generada en la sesión, **When** el usuario interactúa con la app, **Then** no se
   regenera automáticamente.

---

### User Story 4 - Auditar métricas, citas y estados de error (Priority: P4)

Un evaluador necesita ver en la app las métricas del corpus, el modelo, la latencia, los tokens y los
descartes, además de comprobar que no se exponen claves ni rutas absolutas.

**Why this priority**: la rúbrica evalúa la calidad de la app y la transparencia del pipeline; el panel es
la evidencia visible.

**Independent Test**: abrir el panel y verificar que muestra URLs, páginas, tokens, descartes, cobertura,
modelo, latencia y número de citas; revisar que no hay secretos ni rutas absolutas.

**Acceptance Scenarios**:

1. **Given** los reportes del corpus, **When** el usuario abre el panel, **Then** ve al menos: artefactos
   activos, documentos canónicos, fragmentos, unidades, cobertura, tokens, descartes y omisiones.
2. **Given** una respuesta generada, **When** el usuario revisa el panel, **Then** ve el modelo, la versión
   del prompt, la latencia y el número de citas de esa respuesta.
3. **Given** un error de modelo o de datos, **When** ocurre, **Then** el panel muestra el estado y un
   mensaje accionable, sin bloquear la app.

---

### Edge Cases

- El modelo local no está en ejecución o el modelo no está descargado: mostrar un mensaje con los comandos
  `ollama serve` y `ollama pull`.
- El modelo supera el timeout: mostrar un error controlado y permitir reintentar.
- La base de oro no está materializada por Git LFS o falta un archivo: mostrar un estado de datos
  incompletos y no romper la app.
- La pregunta está vacía, es muy larga o contiene caracteres de control: validar antes de llamar al modelo.
- La respuesta no tiene citas o cita unidades fuera del contexto: mostrar una advertencia y marcar el
  resultado para revisión.
- El paquete de 32k no cabe en el modelo: usar 8k y declararlo en la interfaz.
- El usuario cambia de pestaña o recarga: conservar los resultados de la sesión cuando sea posible.
- El usuario hace doble clic en generar: evitar llamadas duplicadas y mostrar un estado de carga.
- La pantalla es estrecha: las tarjetas, tablas y citas deben seguir siendo legibles.
- El contenido de una fuente es largo: truncar la vista previa, pero mantener el enlace completo.
- La app se abre sin conexión: funcionar con el modelo local y los datos locales; no depender de servicios
  externos.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La app MUST ejecutarse con `uv run streamlit run app.py` desde un clon con dependencias
  sincronizadas.
- **FR-002**: La app MUST ofrecer tres pestañas visibles: **Resumen**, **FAQ** y **Q&A**.
- **FR-003**: La pestaña Q&A MUST incluir un campo de pregunta, un botón de envío y un área de respuesta.
- **FR-004**: La app MUST mostrar, para cada respuesta Q&A, las citas `[U#]` y una lista de fuentes con
  título, URL y sección, página o marca temporal.
- **FR-005**: La app MUST mostrar el fallback explícito cuando no haya evidencia, sin inventar contenido.
- **FR-006**: La pestaña Resumen MUST generar una síntesis estructurada con 8–12 citas y una lista de
  fuentes.
- **FR-007**: La pestaña FAQ MUST mostrar entre 10 y 20 preguntas frecuentes, cada una con respuesta, citas
  y estado `ready`, `review` o `missing_evidence`.
- **FR-008**: La app MUST mostrar un panel con métricas del corpus: artefactos activos, documentos
  canónicos, fragmentos, unidades, cobertura, tokens, descartes y omisiones.
- **FR-009**: La app MUST mostrar, para la última respuesta, el modelo, la versión del prompt, la latencia,
  el número de citas y el estado de fallback.
- **FR-010**: La app MUST manejar errores de modelo, timeout, datos incompletos, pregunta vacía y contexto
  vacío con mensajes accionables y sin romper la interfaz.
- **FR-011**: La app MUST validar la pregunta antes de llamar al modelo y MUST rechazar preguntas vacías o
  demasiado largas.
- **FR-012**: La app MUST conservar los resultados de la sesión al cambiar de pestaña y MUST evitar
  regeneraciones automáticas por cada interacción.
- **FR-013**: La app MUST ofrecer un modo de demostración con modelo falso para funcionar sin Ollama,
  claramente identificado en la interfaz.
- **FR-014**: La app MUST NOT exponer claves, credenciales, cookies ni rutas absolutas.
- **FR-015**: La app MUST ser de solo lectura sobre `data/gold/`, `data/silver/` y `data/bronze/`; no MUST
  escribir en las capas medallion.
- **FR-016**: La app MUST mostrar las citas como enlaces clicables y mantener el texto completo de la URL
  disponible.
- **FR-017**: La app MUST usar español como idioma principal y conservar nombres propios, siglas y cifras.
- **FR-018**: La app MUST ser importable y testeable sin lanzar el servidor de Streamlit.
- **FR-019**: La app MUST declarar `streamlit` como dependencia de ejecución y MUST ejecutarse desde un
  clon limpio con `uv sync`.
- **FR-020**: La app MUST distinguir entre datos completos, datos incompletos y modelo no disponible en el
  panel de estado.
- **FR-021**: La app MUST mostrar un estado de carga mientras genera una respuesta y MUST deshabilitar el
  botón para evitar envíos duplicados.
- **FR-022**: La app MUST permitir reintentar una operación fallida sin reiniciar la sesión.

### Key Entities *(include if feature involves data)*

- **App Session**: estado de la interfaz con la pregunta actual, la respuesta, la FAQ, el resumen y el modo
  de modelo.
- **Answer View**: respuesta visible, citas, fuentes, fallback y metadatos de modelo/prompt/latencia.
- **Metrics Panel**: métricas del corpus y de la última respuesta.
- **FAQ View**: lista de preguntas frecuentes con respuesta, citas y estado.
- **Source Citation**: enlace y metadatos de la unidad usada como evidencia.
- **App Status**: estado de datos, modelo y errores de la sesión.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La app abre desde un clon limpio con `uv run streamlit run app.py` en menos de 15 segundos
  en el equipo de referencia.
- **SC-002**: Una pregunta Q&A se responde en menos de 30 segundos con el modelo local y muestra cita o
  fallback en el 100% de los casos.
- **SC-003**: El 100% de las respuestas Q&A visibles incluye al menos una cita o el fallback explícito.
- **SC-004**: El panel muestra al menos 8 métricas del corpus y 5 de la última respuesta.
- **SC-005**: El resumen visible contiene entre 8 y 12 citas y una lista de fuentes.
- **SC-006**: La FAQ visible contiene entre 10 y 20 preguntas, todas con cita o `missing_evidence`.
- **SC-007**: La app no muestra claves, credenciales ni rutas absolutas en el 100% de las pruebas.
- **SC-008**: Los errores de modelo, timeout, datos incompletos y pregunta vacía se manejan sin excepción
  no controlada en el 100% de los casos probados.
- **SC-009**: El modo de demostración funciona sin Ollama y permite recorrer las tres pestañas.
- **SC-010**: La app es importable y la suite de pruebas asociada pasa sin red en menos de 2 minutos.

## Assumptions

- Las tareas de Resumen, FAQ y Q&A ya existen en `src/proyecto_modelos_lenguaje/tasks.py` y son reutilizables.
- El modelo Ollama `llama3.1:8b` está instalado y activo; si no, la app usa el modo de demostración.
- Los datos de oro están disponibles por Git LFS; si faltan, la app muestra un estado de datos incompletos.
- La app es local, para un solo usuario y uso académico; no se despliega en internet.
- El paquete de 8k es el valor por defecto; 32k solo si el modelo lo soporta.
- No se usan embeddings, base vectorial, memoria ni servicios externos.
- La evaluación de 40 preguntas y el informe son M1-08 y M1-10, no M1-07.

## Out of Scope

- Autenticación, usuarios, permisos o multiusuario.
- Despliegue público, contenedores o alta disponibilidad.
- Embeddings, base vectorial o memoria conversacional.
- Edición de datos, curaduría o escritura en las capas medallion.
- Evaluación automática de las 40 preguntas.
- Informe, demo o guion de sustentación.
- Traducción, OCR o generación de imágenes.
