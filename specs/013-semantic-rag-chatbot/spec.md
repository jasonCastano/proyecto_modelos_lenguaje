# Feature Specification: Chatbot con recuperación semántica (RAG)

**Feature Branch**: `013-semantic-rag-chatbot`

**Created**: 2026-11-06

**Status**: Draft

**Input**: User description: "necesito que ahora el chat bot funcione con un RAG."

**Contexto**: el chatbot del Módulo 1 responde citando unidades de oro que encuentra con una búsqueda
léxica (coincidencia de palabras, tema y entidades). Funciona, pero falla cuando el usuario pregunta con
sinónimos, paráfrasis o preguntas compuestas que no repiten los términos del corpus. Esta especificación
define el paso al Módulo 2: recuperar evidencia por **similitud semántica** (embeddings) y responder solo
con esos fragmentos, conservando citas, fallback explícito y lectura en solo de las capas medallion.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Obtener respuestas con recuperación semántica (Priority: P1)

Un usuario pregunta con sus propias palabras —sin repetir los términos del documento— y recibe una
respuesta correcta, citada, porque el sistema encontró los fragmentos por significado y no solo por
coincidencia literal.

**Why this priority**: es el objetivo del cambio. Si la recuperación no mejora en preguntas parafraseadas,
el RAG no aporta nada frente a la búsqueda actual.

**Independent Test**: formular 10 preguntas reformuladas (sinónimos y paráfrasis) y verificar que al menos
8 obtienen una respuesta `ok` con una cita cuyo texto responde realmente a la pregunta.

**Acceptance Scenarios**:

1. **Given** una pregunta que usa sinónimos ausentes en el corpus, **When** el usuario la envía,
   **Then** el sistema recupera fragmentos por significado y responde con al menos una cita.
2. **Given** una pregunta idéntica a la del Módulo 1, **When** se envía, **Then** la respuesta conserva el
   mismo formato, las citas `[U#]` y los metadatos.
3. **Given** una pregunta fuera del corpus, **When** se envía, **Then** el sistema responde el fallback
   explícito y no inventa.

---

### User Story 2 - Mantener la calidad cuando la semántica falla (Priority: P2)

Un usuario hace una pregunta con nombres propios, siglas o cifras exactas; la recuperación semántica no
basta y el sistema sigue encontrando la evidencia correcta.

**Why this priority**: la búsqueda semántica es peor que la léxica para términos exactos (códigos, cifras,
nombres de filiales); perder esa capacidad sería una regresión frente al Módulo 1.

**Independent Test**: ejecutar 10 preguntas con cifras, siglas y nombres propios y comparar los resultados
con la línea base léxica del Módulo 1.

**Acceptance Scenarios**:

1. **Given** una pregunta con una cifra o un nombre propio exacto, **When** se envía, **Then** la evidencia
   recuperada contiene ese término.
2. **Given** que la recuperación semántica no devuelve nada por encima del umbral, **When** el sistema
   responde, **Then** usa la recuperación léxica como respaldo antes de declarar fallback.
3. **Given** ambas recuperaciones coinciden en una unidad, **When** se construye el contexto, **Then** la
   unidad aparece una sola vez.

---

### User Story 3 - Ver qué fragmentos sustentan la respuesta (Priority: P3)

Un evaluador quiere ver, junto a la respuesta, los fragmentos recuperados con su puntuación y su fuente,
para poder auditar por qué el sistema respondió eso.

**Why this priority**: la constitución exige que la app muestre pregunta, fragmentos recuperados, respuesta
y fuentes; sin esa vista el RAG es una caja negra.

**Independent Test**: abrir una respuesta en la interfaz y comprobar que se listan los fragmentos usados con
su similitud y su enlace de origen.

**Acceptance Scenarios**:

1. **Given** una respuesta generada, **When** el usuario abre el detalle, **Then** ve los fragmentos
   recuperados, su puntuación y su fuente.
2. **Given** un fragmento descartado por presupuesto o umbral, **When** se revisa el detalle,
   **Then** aparece como descartado con su motivo.
3. **Given** una respuesta en fallback, **When** se revisa el detalle, **Then** se explica que no hubo
   fragmentos por encima del umbral.

---

### User Story 4 - Trabajar sin red y sin costo (Priority: P4)

Un usuario sin conexión activa el modo demostración y recorre el chatbot con respuestas de prueba, sin
llamadas remotas ni descargas.

**Why this priority**: el Módulo 1 ya perdió el modelo local al pasar a API; el modo demostración es la
única vía offline y no puede depender de servicios externos.

**Independent Test**: sin red, activar el modo demostración y verificar que la recuperación y la respuesta
funcionan con datos locales.

**Acceptance Scenarios**:

1. **Given** una red no disponible, **When** el usuario activa el modo demostración, **Then** el chatbot
   responde con el modelo falso y fragmentos recuperados del índice local.
2. **Given** el modo demostración activo, **When** el usuario mira la interfaz, **Then** un distintivo
   persistente lo indica.

---

### User Story 5 - Medir si el RAG mejoró (Priority: P5)

Un integrante del equipo compara la recuperación semántica con la línea base léxica y decide, con números,
si el cambio se mantiene.

**Why this priority**: la constitución exige medir Recall@k, MRR y calidad de citas, y comparar contra la
línea base del Módulo 1.

**Independent Test**: ejecutar el conjunto de evaluación y obtener un informe con Recall@k y MRR de ambos
modos.

**Acceptance Scenarios**:

1. **Given** un conjunto de preguntas con su unidad esperada, **When** se evalúa la recuperación,
   **Then** se reportan Recall@k y MRR para semántica, léxica e híbrida.
2. **Given** los resultados, **When** se comparan, **Then** el informe declara si el RAG supera la línea
   base y en qué tipos de pregunta.
3. **Given** una regresión en preguntas exactas, **When** se revisa el informe, **Then** queda registrada
   como riesgo con su causa.

---

### Edge Cases

- El corpus no tiene índice construido: el sistema avisa y ofrece el comando para construirlo, sin fallar.
- El índice fue construido con un modelo distinto al configurado: se detecta y se rechaza con mensaje claro.
- El índice está desactualizado respecto de la capa de oro: se informa la diferencia y se permite reindexar.
- Una pregunta es tan corta que no produce una señal útil: se aplica el umbral mínimo y, si no hay
  evidencia, fallback.
- El texto de una unidad es enorme: se respeta el límite de tokens del modelo de embeddings y se trocea.
- La red cae durante la generación: error controlado con reintento, conservando los fragmentos recuperados.
- El usuario pregunta en inglés: el modelo multilingüe recupera igual y la respuesta se da en español.
- Dos fragmentos casi idénticos: se deduplican antes de construir el contexto.
- El presupuesto de contexto se llena: se recortan fragmentos y se declaran los descartados.
- El modo demostración se activa sin índice: se usa un índice de prueba incluido en el repositorio.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST recuperar evidencia por similitud semántica a partir de la capa de oro, sin
  modificar el corpus.
- **FR-002**: El sistema MUST construir el índice semántico con un comando reproducible a partir de
  `data/gold/`, registrando modelo, dimensión, normalización y fecha de construcción.
- **FR-003**: El sistema MUST rechazar un índice construido con un modelo o dimensión distintos de los
  configurados, con un mensaje accionable.
- **FR-004**: El sistema MUST combinar la recuperación semántica con la léxica existente y MUST usar la
  léxica como respaldo cuando la semántica no supere el umbral.
- **FR-005**: El sistema MUST NOT incluir la misma unidad dos veces en el contexto, aunque ambas
  recuperaciones la devuelvan.
- **FR-006**: El sistema MUST conservar el contrato de respuesta: citas `[U#]`, estados
  `ok|fallback|review|error`, fallback explícito y metadatos de modelo, tokens y latencia.
- **FR-007**: El sistema MUST responder solo con los fragmentos recuperados para esa pregunta.
- **FR-008**: El sistema MUST exponer en la interfaz los fragmentos recuperados, su puntuación y su fuente,
  incluidos los descartados con su motivo.
- **FR-009**: El sistema MUST permitir construir, verificar y reindexar el índice sin tocar los datos de
  origen.
- **FR-010**: El sistema MUST funcionar en modo demostración sin red, con un índice de prueba incluido.
- **FR-011**: El sistema MUST registrar en cada respuesta si la evidencia provino de recuperación
  semántica, léxica o híbrida.
- **FR-012**: El sistema MUST respetar un presupuesto de contexto y declarar los fragmentos omitidos.
- **FR-013**: El sistema MUST deduplicar fragmentos casi idénticos antes de construir el contexto.
- **FR-014**: El sistema MUST soportar preguntas en español y en inglés, respondiendo en español.
- **FR-015**: El sistema MUST ofrecer una evaluación reproducible con Recall@k y MRR para comparar
  semántica, léxica e híbrida.
- **FR-016**: El sistema MUST mantener las pruebas automatizadas sin red, usando un generador de
  embeddings falso.
- **FR-017**: El sistema MUST documentar el modelo de embeddings elegido, su dimensión, su límite de tokens
  y su justificación de calidad, costo y latencia.
- **FR-018**: El sistema MUST NOT versionar el índice completo; solo el manifiesto y un índice de prueba
  reducido.
- **FR-019**: El sistema MUST conservar el tiempo de respuesta del Módulo 1 o mejorarlo, medido de extremo a
  extremo.
- **FR-020**: El sistema MUST declarar en el informe de evaluación si el RAG supera o no la línea base
  léxica.

### Key Entities *(include if feature involves data)*

- **Embedding Model**: identificador, dimensión, normalización, límite de tokens y fecha de uso.
- **Vector Index**: representación del corpus para búsqueda por similitud, con su manifiesto de
  construcción (modelo, versión de oro, número de vectores, fecha).
- **Retrieved Fragment**: unidad recuperada con puntuación, origen (semántica, léxica o ambas) y estado
  (usada, descartada por umbral o por presupuesto).
- **Retrieval Trace**: resumen de la recuperación de una pregunta: modos ejecutados, candidatos, umbral y
  fragmentos finales.
- **Evaluation Run**: conjunto de preguntas con unidad esperada, métricas por modo y comparación con la
  línea base.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al menos 8 de cada 10 preguntas parafraseadas obtienen respuesta `ok` con una cita
  pertinente, frente a la línea base léxica medida.
- **SC-002**: Recall@5 de la recuperación híbrida es mayor o igual que el de la búsqueda léxica del
  Módulo 1 en el mismo conjunto de preguntas.
- **SC-003**: MRR de la recuperación híbrida no es inferior al de la línea base léxica.
- **SC-004**: El 100% de las respuestas conserva al menos una cita válida o el fallback explícito.
- **SC-005**: El 100% de las respuestas permite ver en la interfaz los fragmentos que las sustentan.
- **SC-006**: El tiempo de respuesta de extremo a extremo no aumenta más de un 20% respecto del Módulo 1
  en el equipo de referencia.
- **SC-007**: El índice se reconstruye desde la capa de oro con un comando y produce el mismo número de
  vectores en dos ejecuciones consecutivas.
- **SC-008**: La suite de pruebas sigue sin red y se ejecuta en menos de 3 minutos.
- **SC-009**: El modo demostración funciona sin índice construido, usando el índice de prueba.
- **SC-010**: Ninguna ejecución escribe en `data/bronze`, `data/silver` ni `data/gold`.

## Assumptions

- El corpus de oro (15.211 unidades) ya existe y se considera la fuente única de evidencia.
- Los embeddings se generan en local con un modelo multilingüe: sin costo por consulta y sin enviar corpus
  a terceros; la descarga del modelo se hace una sola vez.
- El índice se genera como artefacto local reproducible; no se versiona completo por tamaño.
- La generación de la respuesta sigue a cargo del proveedor ya configurado (DeepSeek), que solo recibe los
  fragmentos recuperados.
- La memoria conversacional queda fuera de esta especificación.
- El conjunto de evaluación del Módulo 2 amplía el de 40 preguntas del Módulo 1.
- El umbral de similitud inicial se fija en la implementación y se ajusta con la evaluación.

## Out of Scope

- Memoria conversacional persistente entre sesiones.
- Reentrenamiento o ajuste fino del modelo de embeddings.
- Búsqueda híbrida con reordenamiento por un modelo externo (reranking).
- Despliegue público o multiusuario.
- Cambios en los prompts de las tres tareas más allá de la evidencia que reciben.
- Migración de la capa de oro o cambios en el pipeline medallion.
