# Feature Specification: Tareas LangChain — Resumen, FAQ y Q&A

**Feature Branch**: `007-langchain-qa-tasks`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "crea las especificaciones para implementar la tarea M1-05"

**Contexto**: la tarea M1-05 debe implementar las tres tareas del Módulo 1 con LangChain sobre la base de
conocimiento de oro: Resumen, FAQ y Q&A. La entrada está en `data/gold/`: 15.211 unidades citables,
3.810 fragmentos de plata, paquetes de contexto de 8.000 y 32.000 tokens, 53 preguntas semilla y una
matriz de cobertura de 24/24 ítems. El modelo local Ollama ya está configurado y validado (M1-04), con un
adaptador falso para pruebas offline. Cada respuesta debe citar la fuente o declarar que no hay evidencia.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Preguntar y recibir una respuesta citada o un fallback (Priority: P1)

Un usuario formula una pregunta sobre Manuelita y recibe una respuesta breve, basada **solo** en la base de
conocimiento de oro, con las fuentes citadas. Si no hay evidencia suficiente, el sistema lo dice de forma
explícita en lugar de inventar.

**Why this priority**: es la funcionalidad central del asistente y la que se evaluará con las 40 preguntas
del alcance. Sin Q&A citable y con fallback, el proyecto no cumple su promesa principal.

**Independent Test**: formular 10 preguntas del alcance con el modelo falso y verificar que cada resultado
es una respuesta con al menos una cita o un fallback explícito, sin texto ajeno al contexto.

**Acceptance Scenarios**:

1. **Given** una pregunta con evidencia suficiente en las unidades de oro, **When** el usuario pregunta,
   **Then** la respuesta incluye al menos una cita `[U#]` y una lista de fuentes con URL y sección o página.
2. **Given** una pregunta sin unidades relevantes o con evidencia insuficiente, **When** el usuario
   pregunta, **Then** la respuesta declara que no hay evidencia suficiente y no incluye afirmaciones
   inventadas.
3. **Given** un contexto que contiene instrucciones maliciosas o ajenas a la tarea, **When** el modelo
   responde, **Then** ignora esas instrucciones y solo usa el contexto como datos.
4. **Given** una pregunta fuera del alcance de Manuelita, **When** el usuario pregunta, **Then** el sistema
   responde que la pregunta está fuera del alcance o que no hay evidencia, sin usar conocimiento externo.

---

### User Story 2 - Generar un resumen del corpus con citas (Priority: P2)

Un integrante del equipo necesita un resumen ejecutivo del corpus de Manuelita para la app y el informe,
con afirmaciones respaldadas por fuentes y sin generalizaciones no documentadas.

**Why this priority**: el Resumen es una de las tres funcionalidades obligatorias y alimenta la app y el
informe del Módulo 1.

**Independent Test**: generar el resumen con el paquete de contexto de 8.000 tokens y el modelo falso;
verificar que tiene la estructura esperada, entre 8 y 12 citas y ninguna afirmación sin fuente.

**Acceptance Scenarios**:

1. **Given** el paquete de contexto de 8.000 tokens, **When** se solicita el resumen, **Then** el resultado
   contiene una síntesis estructurada con citas y una lista de fuentes.
2. **Given** un contexto vacío o insuficiente, **When** se solicita el resumen, **Then** el sistema declara
   que no hay información suficiente y no inventa secciones.
3. **Given** el paquete de 32.000 tokens y un modelo que lo soporta, **When** se solicita el resumen,
   **Then** el resultado conserva las citas y no repite unidades.

---

### User Story 3 - Generar preguntas frecuentes con evidencia (Priority: P3)

Un integrante del equipo necesita un conjunto inicial de preguntas frecuentes, derivadas de las preguntas
semilla y de las unidades de oro, para publicarlas en la app y revisarlas antes de la demo.

**Why this priority**: la FAQ es la tercera funcionalidad obligatoria y reduce el trabajo manual de
seleccionar preguntas representativas.

**Independent Test**: generar al menos 10 preguntas frecuentes con el modelo falso y verificar que cada una
tiene respuesta, citas y un estado de revisión.

**Acceptance Scenarios**:

1. **Given** las 53 preguntas semilla y sus unidades de evidencia, **When** se solicita la FAQ, **Then** se
   generan entre 10 y 20 preguntas con respuesta y citas.
2. **Given** una pregunta semilla sin evidencia, **When** se genera la FAQ, **Then** se marca como
   `missing_evidence` o se omite, sin inventar una respuesta.
3. **Given** dos preguntas semilla equivalentes, **When** se genera la FAQ, **Then** se deduplican por
   texto normalizado y se conserva una sola entrada.

---

### User Story 4 - Auditar prompts, citas y reproducibilidad (Priority: P4)

Un evaluador necesita comprobar que los prompts están versionados, que las respuestas citan fuentes y que
las pruebas pueden ejecutarse sin red ni costo de tokens.

**Why this priority**: la rúbrica evalúa la calidad del Prompt Engineering y la transparencia; sin auditoría
no se puede defender el resultado.

**Independent Test**: revisar los tres prompts, ejecutar la suite con el modelo falso y verificar que cada
resultado registra versión de prompt, modelo, latencia y citas.

**Acceptance Scenarios**:

1. **Given** los tres prompts versionados, **When** se inspecciona el repositorio, **Then** cada uno declara
   rol, tarea, contexto delimitado, reglas, formato de cita y comportamiento sin evidencia.
2. **Given** una ejecución de prueba, **When** se revisa el resultado, **Then** incluye `prompt_version`,
   `model`, `latency_seconds`, `citations` y `fallback`.
3. **Given** un contexto con instrucciones embebidas, **When** se ejecuta la prueba de inyección, **Then**
   ninguna instrucción del contexto se ejecuta como instrucción del sistema.

---

### Edge Cases

- La pregunta está vacía o solo contiene espacios: rechazarla antes de llamar al modelo.
- La pregunta es muy larga o contiene caracteres de control: normalizarla y limitar su longitud.
- No hay unidades de oro disponibles: fallback explícito, sin llamada al modelo o con respuesta controlada.
- El contexto supera el presupuesto de tokens: recortar por prioridad y registrar las unidades omitidas.
- El modelo devuelve una respuesta sin citas: rechazarla y reintentar una vez con una instrucción más
  estricta; si vuelve a fallar, devolver un error controlado.
- El modelo devuelve citas a unidades que no estaban en el contexto: descartar esas citas y marcar el
  resultado para revisión.
- El modelo no responde o supera el timeout: devolver un error accionable, sin bloquear la app.
- El contexto contiene instrucciones maliciosas: tratarlas como texto y no como instrucciones.
- La pregunta pide una comparación o una síntesis: usar varias unidades y citar cada lado.
- La pregunta es sobre contenido bloqueado (Instagram, Linktree): declarar que la fuente no está disponible.
- La respuesta contiene una cifra que no aparece en el contexto: marcarla como no soportada y no publicarla.
- El paquete de 32.000 tokens no cabe en el modelo: usar el de 8.000 y declararlo.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST implementar tres tareas: Resumen, FAQ y Q&A, usando LangChain y el adaptador
  de modelo configurado en M1-04.
- **FR-002**: El sistema MUST versionar los prompts en `prompts/summary.md`, `prompts/faq.md` y
  `prompts/qa.md`, con rol, tarea, contexto delimitado, reglas, formato de cita y comportamiento ante falta
  de información.
- **FR-003**: El sistema MUST cargar las unidades, los paquetes de contexto y las preguntas semilla desde
  `data/gold/` y MUST NOT consultar fuentes externas ni usar conocimiento del modelo fuera del contexto.
- **FR-004**: El sistema MUST responder Q&A con al menos una cita por afirmación factual y una lista de
  fuentes con título, URL y sección, página o marca temporal.
- **FR-005**: El sistema MUST declarar explícitamente “no hay evidencia suficiente” cuando no haya unidades
  relevantes o cuando la evidencia no permita responder.
- **FR-006**: El sistema MUST seleccionar la evidencia de Q&A por tema y palabras clave de forma determinista,
  sin embeddings ni base vectorial, y MUST respetar un presupuesto de tokens.
- **FR-007**: El sistema MUST limitar el número de unidades usadas por respuesta y MUST registrar las
  unidades seleccionadas y las omitidas.
- **FR-008**: El sistema MUST generar un resumen estructurado con citas, usando el paquete de 8.000 tokens
  por defecto y el de 32.000 solo si el modelo lo soporta.
- **FR-009**: El sistema MUST generar entre 10 y 20 preguntas frecuentes con respuesta, citas y estado de
  revisión a partir de `faq_seeds.jsonl` y sus unidades de evidencia.
- **FR-010**: El sistema MUST deduplicar preguntas frecuentes por texto normalizado y MUST omitir o marcar
  como `missing_evidence` las que no tengan evidencia.
- **FR-011**: El sistema MUST tratar el contexto como datos no confiables: delimitarlo, ignorar instrucciones
  embebidas y no ejecutar código contenido en los documentos.
- **FR-012**: El sistema MUST validar que cada cita corresponde a una unidad incluida en el contexto;
  las citas inventadas MUST descartarse y el resultado MUST marcarse para revisión.
- **FR-013**: El sistema MUST devolver un resultado estructurado con tarea, respuesta, citas, unidades
  usadas, versión de prompt, modelo, latencia y estado de fallback.
- **FR-014**: El sistema MUST rechazar preguntas vacías o demasiado largas antes de llamar al modelo.
- **FR-015**: El sistema MUST manejar timeout, errores del modelo y respuestas vacías con mensajes
  accionables y sin bloquear la interfaz.
- **FR-016**: El sistema MUST usar un modelo falso determinista para las pruebas unitarias, de contrato y de
  integración, sin red ni consumo de tokens.
- **FR-017**: El sistema MUST permitir una prueba de integración opcional contra Ollama, deshabilitada por
  defecto.
- **FR-018**: El sistema MUST registrar la versión del prompt y el modelo usado en cada resultado para que
  M1-06 pueda construir el prompt log.
- **FR-019**: El sistema MUST responder en español y conservar nombres propios, siglas y cifras tal como
  aparecen en la fuente.
- **FR-020**: El sistema MUST distinguir entre Manuelita, Manuelita Azúcar y Energía, Laredo, Aceites y
  Energía, Fundación Manuelita y demás filiales cuando la evidencia lo permita.
- **FR-021**: El sistema MUST NOT promediar cifras contradictorias ni resolver conflictos por frecuencia;
  si hay conflicto, MUST mostrarlo o remitir a la unidad que lo declara.
- **FR-022**: El sistema MUST exponer una interfaz de biblioteca reutilizable por la app de M1-07 y por la
  evaluación de M1-08, sin depender de Streamlit.

### Key Entities *(include if feature involves data)*

- **Prompt Template**: plantilla versionada de una tarea, con rol, instrucciones, reglas, formato de cita y
  comportamiento sin evidencia.
- **Context Unit**: unidad de oro seleccionada para una tarea, con `unit_id`, texto y cita.
- **Citation**: referencia a una unidad, con título, URL y sección, página o marca temporal.
- **Task Result**: resultado de Resumen, FAQ o Q&A, con respuesta, citas, unidades usadas, versión de prompt,
  modelo, latencia, uso de tokens y estado de fallback.
- **FAQ Item**: pregunta frecuente con respuesta, citas y estado `ready`, `review` o `missing_evidence`.
- **Evidence Selection**: conjunto determinista de unidades elegidas para una pregunta, con puntuación,
  presupuesto y unidades omitidas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de las respuestas de Q&A incluye al menos una cita válida o un fallback explícito.
- **SC-002**: En una muestra de 20 preguntas del alcance, cero respuestas contienen afirmaciones factuales
  que no estén respaldadas por una unidad del contexto.
- **SC-003**: El 100% de las pruebas con contexto vacío o sin evidencia devuelve el fallback y no inventa
  contenido.
- **SC-004**: El resumen se genera en menos de 120 segundos en el equipo de referencia y contiene entre 8 y
  12 citas.
- **SC-005**: La FAQ genera entre 10 y 20 preguntas, y el 100% tiene respuesta y al menos una cita o estado
  `missing_evidence`.
- **SC-006**: El 100% de los prompts está versionado y contiene las seis secciones obligatorias.
- **SC-007**: La suite de pruebas con modelo falso pasa sin red y sin Ollama en menos de 2 minutos.
- **SC-008**: La prueba de inyección de contexto produce cero ejecuciones de instrucciones embebidas.
- **SC-009**: El 100% de las citas emitidas corresponde a una unidad incluida en el contexto.
- **SC-010**: Una prueba de humo de 10 preguntas termina sin intervención manual y cada resultado es una
  respuesta citada o un fallback.

## Assumptions

- La capa de oro está construida y validada: 15.211 unidades, 3.810 fragmentos, paquetes de 8k/32k y 53
  preguntas semilla.
- El modelo Ollama está configurado (M1-04) y existe un adaptador falso para pruebas offline.
- El paquete de 8.000 tokens es el valor por defecto; el de 32.000 se usa solo si el modelo lo soporta.
- No se usarán embeddings, base vectorial ni memoria en esta tarea; la recuperación es determinista por
  tema y palabras clave.
- La app Streamlit y la evaluación de 40 preguntas son tareas posteriores (M1-07 y M1-08).
- El prompt log detallado es M1-06; M1-05 solo deja la versión y los metadatos necesarios.
- El corpus es mayoritariamente español; las unidades en inglés se conservan y se citan como tales.
- Las respuestas se revisarán con el modelo real antes de la demo, pero las pruebas automatizadas usan el
  modelo falso.

## Out of Scope

- Embeddings, base vectorial, recuperación semántica o memoria conversacional.
- Fine-tuning o entrenamiento de modelos.
- App Streamlit, interfaz web o panel de métricas.
- Evaluación completa de las 40 preguntas y análisis de errores.
- Recolección de nuevas fuentes o modificación de bronce, plata u oro.
- Traducción automática, OCR o generación de imágenes.
- Afirmaciones sobre información privada o no publicada.
