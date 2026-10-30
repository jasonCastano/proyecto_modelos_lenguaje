# Feature Specification: Filtro de Relevancia del Corpus de Manuelita

**Feature Branch**: `002-manuelita-relevance-filter`

**Created**: 2026-10-28

**Status**: Draft

**Input**: User description: "Analizar los datos adquiridos y eliminar toda la información que no esté
directamente relacionada con Ingenio Manuelita del Valle del Cauca, Colombia (https://www.manuelita.com/).
Toda aquella información en donde sí se haga una mención al Ingenio Manuelita o tenga relación, dejarla."

**Corpus analizado**: la campaña `2026-10-baseline` almacenó 26.746 artefactos (9,86 GB) y la campaña
`smoke-001` otros 6. Del total, 397 provienen del dominio oficial y solo 13 artefactos de terceros contienen
una mención verificable a Manuelita. La matriz de cobertura actual reporta 24/24 ítems cubiertos, pero ese
resultado está inflado por páginas genéricas de portal que coinciden con palabras clave sin tratar sobre la
empresa.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Clasificar cada artefacto por relevancia (Priority: P1)

Como líder del proyecto, quiero que cada artefacto adquirido se clasifique como relevante, irrelevante o
ambiguo con evidencia verificable, para asegurar que el futuro RAG solo se alimente de información sobre
Ingenio Manuelita y su entorno directo.

**Why this priority**: El corpus actual está dominado por contenido genérico de portales (Cámara de Comercio,
datos.gov.co, SECOP, Superintendencia) que no trata sobre la empresa. Sin una clasificación explícita no es
posible limpiar el corpus ni confiar en la cobertura.

**Independent Test**: Ejecutar el análisis sobre el corpus actual y verificar que los 26.752 artefactos reciben
una decisión con su evidencia, que los 397 del dominio oficial se conservan y que las páginas genéricas sin
mención se marcan para eliminación.

**Acceptance Scenarios**:

1. **Given** el corpus bronce completo, **When** se ejecuta el análisis de relevancia, **Then** cada artefacto
   recibe una decisión (`conservar`, `eliminar` o `revisar`), una puntuación y la evidencia que la sustenta.
2. **Given** un artefacto del dominio oficial de Manuelita, **When** se evalúa, **Then** se conserva sin
   excepción.
3. **Given** una página genérica de un portal público que no menciona ni se relaciona con Manuelita, **When**
   se evalúa, **Then** se marca para eliminación.
4. **Given** una página con una mención genuina a la empresa (noticia, ranking, contrato, registro, gremio),
   **When** se evalúa, **Then** se conserva y se registra el fragmento que lo justifica.
5. **Given** una página con la palabra "Manuelita" usada como nombre de persona, canción, lugar o correo
   electrónico sin relación con la empresa, **When** se evalúa, **Then** no se conserva automáticamente y se
   envía a revisión o se elimina según la evidencia.

---

### User Story 2 - Eliminar lo irrelevante con auditoría y liberar espacio (Priority: P2)

Como responsable de datos, quiero retirar del corpus activo los artefactos irrelevantes, conservar un registro
de auditoría de lo eliminado y recuperar el espacio ocupado, para dejar una base depurada y permitir nuevas
campañas dentro del límite de 10 GB.

**Why this priority**: El corpus ocupa 9,86 GB y solo una fracción mínima es útil; sin liberar espacio, la capa
bronce queda prácticamente cerrada para nueva información.

**Independent Test**: Aprobar un conjunto de eliminación, ejecutar la depuración y verificar que los artefactos
retirados desaparecen de manifiestos, exportaciones, reportes y cobertura, que existe una auditoría por
artefacto y que el espacio ocupado baja del umbral definido.

**Acceptance Scenarios**:

1. **Given** un conjunto de artefactos marcados para eliminación, **When** se aprueba y ejecuta la depuración,
   **Then** dejan de aparecer en el corpus activo, en los manifiestos, en las exportaciones y en la cobertura.
2. **Given** un artefacto eliminado, **When** se consulta la auditoría, **Then** se obtienen su URL, huella de
   integridad, motivo, puntuación y fecha de decisión, aunque el archivo ya no esté disponible.
3. **Given** el corpus de 9,86 GB, **When** finaliza la depuración, **Then** el espacio ocupado por la capa
   bronce es de 1,5 GB o menos y el reporte indica los bytes liberados.
4. **Given** la depuración en curso, **When** se intenta eliminar un artefacto del dominio oficial, **Then** la
   operación se bloquea y se registra la protección.
5. **Given** un artefacto en cuarentena, **When** el revisor solicita restaurarlo dentro del periodo de
   retención, **Then** vuelve al corpus activo sin pérdida de integridad.
6. **Given** una eliminación ya ejecutada, **When** se repite la operación, **Then** no hay errores, no se
   duplican auditorías y el espacio liberado no se cuenta dos veces.

---

### User Story 3 - Recalcular la cobertura con el corpus depurado (Priority: P3)

Como líder del proyecto, quiero que la matriz de los 24 ítems se recalcule únicamente con los artefactos
relevantes, para conocer la cobertura real y planificar la información que falta.

**Why this priority**: La cobertura actual de 24/24 es un falso positivo producido por coincidencias de
palabras clave en páginas genéricas; presentarla como válida induce a error en la evaluación del proyecto.

**Independent Test**: Generar la matriz de cobertura después de la depuración y comprobar que los ítems
sustentados solo por páginas genéricas pasan a faltantes o parciales y que cada vacío tiene justificación.

**Acceptance Scenarios**:

1. **Given** el corpus depurado, **When** se genera la matriz de cobertura, **Then** solo se contabilizan
   artefactos conservados.
2. **Given** un ítem que estaba cubierto únicamente por páginas genéricas, **When** se recalcula, **Then** pasa
   a faltante o parcial con su justificación.
3. **Given** el reporte de depuración, **When** el líder lo consulta, **Then** ve cuántos artefactos se
   conservaron, eliminaron y enviaron a revisión, y cuántos bytes se liberaron.
4. **Given** un ítem sin evidencia tras la depuración, **When** se revisa, **Then** se registra una razón de
   vacío y una recomendación de fuente para la siguiente campaña.

---

### User Story 4 - Revisar casos ambiguos y nombres homónimos (Priority: P4)

Como revisor, quiero una cola de casos ambiguos con contexto suficiente para decidir, para no eliminar
contenido relevante ni conservar falsos positivos por el nombre "Manuelita".

**Why this priority**: "Manuelita" es un nombre común (personas, canción, lugares, correos) y varias menciones
detectadas son incidentales; una decisión automática sin revisión podría destruir evidencia válida o mantener
ruido.

**Independent Test**: Revisar la cola de ambiguos, aprobar o rechazar cada caso y verificar que las decisiones
manuales persisten y prevalecen sobre la clasificación automática.

**Acceptance Scenarios**:

1. **Given** un artefacto ambiguo, **When** se encola, **Then** el revisor ve URL, título, fragmento de contexto,
   puntuación y motivo de ambigüedad.
2. **Given** una decisión manual de conservar o eliminar, **When** se guarda, **Then** prevalece sobre la
   clasificación automática y queda registrada con autor y fecha.
3. **Given** una nueva ejecución del análisis, **When** encuentra un artefacto ya revisado, **Then** respeta la
   decisión manual.
4. **Given** una mención a "Manuelita" sin contexto de la empresa, **When** el revisor la evalúa, **Then** puede
   eliminarla y la auditoría conserva el motivo.

### Edge Cases

- **Homónimos y nombres comunes**: personas llamadas Manuelita, la canción "Manuelita", la tortuga, fincas o
  veredas con ese nombre; se eliminan salvo que el contexto demuestre relación con la empresa.
- **Menciones incidentales**: correos `@manuelita.com`, dominios en listados, nombres de archivo o etiquetas de
  datos que contienen la palabra sin tratar sobre la empresa; se envían a revisión, no se conservan por defecto.
- **Listados y rankings**: una página que menciona a Manuelita entre decenas de empresas se conserva como mención
  contextual, pero con relevancia menor que una página dedicada.
- **Empresas del grupo con otro nombre**: filiales y marcas que no incluyen "Manuelita" en su nombre pero
  pertenecen al grupo; se conservan si la evidencia las vincula explícitamente.
- **PDF e imágenes con texto no extraíble**: si no se puede verificar el contenido, se envían a revisión en lugar
  de eliminarse automáticamente.
- **Contenido en inglés**: se aplican las mismas reglas y términos equivalentes.
- **Duplicados entre campañas**: un mismo contenido con varias URL se evalúa una vez por huella y se conserva o
  elimina de forma consistente.
- **Artefactos del dominio oficial**: nunca se eliminan, aunque una página no mencione el nombre en el texto.
- **Fallo durante la depuración**: la operación debe poder reanudarse sin dejar el corpus en estado inconsistente.
- **Restauración desde cuarentena**: debe conservar la huella y la metadata originales.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST evaluar la relevancia de cada artefacto del corpus bronce, incluyendo todas las
  campañas y tipos de contenido admitidos.
- **FR-002**: El sistema MUST determinar la relevancia a partir del contenido y del contexto, no únicamente de la
  URL, el dominio o el título.
- **FR-003**: El sistema MUST conservar todo artefacto cuyo contenido trate sobre Ingenio Manuelita, lo mencione
  de forma genuina o tenga una relación verificable con la empresa, sus filiales, directivos, productos,
  instalaciones, indicadores o reconocimientos.
- **FR-004**: El sistema MUST conservar sin excepción los artefactos recuperados del dominio oficial
  `manuelita.com`.
- **FR-005**: El sistema MUST marcar para eliminación todo artefacto que no mencione ni se relacione con la
  empresa, incluidos portales genéricos, noticias no relacionadas y conjuntos de datos sin vínculo.
- **FR-006**: El sistema MUST distinguir entre mención directa, mención contextual y ausencia de relación, y
  asignar una puntuación de relevancia a cada artefacto.
- **FR-007**: El sistema MUST detectar homónimos y usos incidentales de "Manuelita" y enviarlos a revisión o
  eliminarlos cuando no exista contexto de la empresa.
- **FR-008**: El sistema MUST registrar para cada decisión la evidencia utilizada: términos encontrados,
  ubicación, fragmento de contexto, fuente, título y puntuación.
- **FR-009**: El sistema MUST permitir tres decisiones: conservar, eliminar y revisar; los artefactos ambiguos no
  se eliminan automáticamente.
- **FR-010**: El sistema MUST excluir los artefactos eliminados de los manifiestos activos, exportaciones,
  reportes y matrices de cobertura.
- **FR-011**: El sistema MUST conservar un registro de auditoría permanente por artefacto eliminado con URL,
  huella de integridad, motivo, puntuación, evidencia y fecha.
- **FR-012**: El sistema MUST liberar el espacio ocupado por los artefactos eliminados una vez aprobada la
  depuración, y reportar los bytes recuperados.
- **FR-013**: El sistema MUST ofrecer una cuarentena reversible antes de la purga definitiva, con un periodo de
  retención configurable.
- **FR-014**: El sistema MUST bloquear cualquier intento de eliminar artefactos del dominio oficial o artefactos
  con decisión manual de conservar.
- **FR-015**: El sistema MUST recalcular la matriz de los 24 ítems usando exclusivamente artefactos conservados y
  justificar cada vacío.
- **FR-016**: El sistema MUST ser idempotente y reanudable: repetir el análisis o la depuración no altera
  decisiones ya aplicadas ni duplica auditorías.
- **FR-017**: El sistema MUST preservar las decisiones manuales de revisión en ejecuciones posteriores.
- **FR-018**: El sistema MUST generar un reporte de depuración con conteos por fuente, decisiones, bytes liberados
  y una muestra de artefactos conservados y eliminados.
- **FR-019**: El sistema MUST operar con listas de términos, umbrales y patrones de exclusión versionados y
  auditables.
- **FR-020**: El sistema MUST mantener intactos los bytes y la metadata de los artefactos conservados.
- **FR-021**: El sistema MUST aplicar las mismas reglas a contenido en español e inglés.
- **FR-022**: El sistema MUST registrar el resultado de la depuración en el catálogo sin sobrescribir el historial
  de adquisición.

### Key Entities *(include if feature involves data)*

- **Evaluación de relevancia**: decisión y puntuación asignadas a un artefacto; atributos: artefacto, decisión,
  nivel (directa, contextual, nula), puntuación, método, fecha y revisor.
- **Evidencia de relevancia**: prueba que sustenta una decisión; atributos: término o entidad, ubicación,
  fragmento, título, URL y peso.
- **Ejecución de depuración**: proceso de análisis y retiro; atributos: identificador, configuración, fecha,
  artefactos evaluados, conservados, eliminados, en revisión y bytes liberados.
- **Elemento de revisión**: artefacto ambiguo pendiente; atributos: motivo de ambigüedad, fragmento, puntuación y
  decisión del revisor.
- **Registro de auditoría**: constancia permanente de un artefacto eliminado; atributos: URL, huella, tamaño,
  motivo, evidencia, fecha de decisión y fecha de purga.
- **Entrada de cuarentena**: artefacto retirado temporalmente; atributos: ubicación, fecha de ingreso, fecha de
  expiración y estado.
- **Manifiesto del corpus activo**: conjunto de artefactos conservados que alimentan las siguientes capas.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los 26.752 artefactos del corpus recibe una evaluación con decisión y evidencia.
- **SC-002**: El 100% de los artefactos del dominio oficial se conserva.
- **SC-003**: Al menos el 95% de los artefactos conservados tiene una mención o relación verificable con Manuelita
  en una muestra aleatoria de 100.
- **SC-004**: Menos del 1% de los artefactos eliminados resulta relevante en una muestra aleatoria de 100.
- **SC-005**: El espacio ocupado por la capa bronce baja de 9,86 GB a 1,5 GB o menos después de la purga.
- **SC-006**: El 100% de los artefactos eliminados cuenta con registro de auditoría con URL, huella y motivo.
- **SC-007**: Cero artefactos eliminados aparecen en manifiestos, exportaciones, reportes o matrices de cobertura
  posteriores.
- **SC-008**: La matriz de cobertura se recalcula con el corpus depurado y cada ítem conserva una justificación
  verificable de su estado.
- **SC-009**: El análisis completo del corpus termina en menos de 2 horas y la depuración en menos de 30 minutos.
- **SC-010**: Repetir el análisis produce decisiones idénticas y repetir la depuración no libera bytes ya contados
  ni duplica registros.
- **SC-011**: Todos los artefactos ambiguos quedan revisados antes de la purga definitiva.
- **SC-012**: El reporte de depuración se genera automáticamente al finalizar y muestra conteos por fuente y bytes
  liberados.

## Assumptions

- **Identidad de la organización**: "Ingenio Manuelita" se refiere a Manuelita S.A. / Manuelita Agroindustria,
  con sede en el Valle del Cauca, Colombia, y su sitio oficial `https://www.manuelita.com/`.
- **Alcance de relación**: se consideran relacionadas las menciones a filiales, marcas, directivos, instalaciones,
  productos, certificaciones, indicadores, reconocimientos y participación en el sector agroindustrial.
- **Menciones incidentales**: una palabra o dominio que aparece en un correo, un listado de contactos o una ruta
  no basta para conservar un artefacto; requiere contexto y, si es dudoso, revisión humana.
- **Eliminación con trazabilidad**: la eliminación retira el artefacto del corpus activo y de los reportes, pero
  conserva una auditoría permanente. Los bytes se mantienen en cuarentena durante 30 días antes de la purga
  definitiva, salvo aprobación explícita de purga inmediata.
- **Espacio**: la purga es necesaria para recuperar capacidad dentro del límite de 10 GB; sin ella, el corpus
  seguiría ocupando 9,86 GB.
- **Conservación**: los artefactos conservados no se modifican; la evaluación es metadata adicional.
- **Revisión humana**: la persona responsable del proyecto actúa como revisor de los casos ambiguos y aprueba la
  purga definitiva.
- **Cobertura previa no confiable**: el resultado 24/24 de la campaña anterior se considera inválido a efectos de
  planificación hasta que se recalcule con el corpus depurado.
- **Sin recolección nueva**: esta fase no vuelve a rastrear la web ni amplía fuentes; solo depura lo ya adquirido.
- **Idioma**: la mayor parte del corpus está en español; se incluye contenido en inglés cuando mencione a la
  empresa o a su sector.
