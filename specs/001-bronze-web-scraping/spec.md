# Feature Specification: Capa Bronce de Recolección Web para el RAG de Manuelita

**Feature Branch**: `001-bronze-web-scraping`

**Created**: 2026-10-27

**Status**: Draft

**Input**: User description: "Recolectar información pública de Ingenio Manuelita (identidad, oferta,
presencia digital y datos duros) desde internet como capa bronce de un futuro RAG, con un límite de
10 GB para esta fase."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Captura del sitio oficial de Manuelita (Priority: P1)

Como integrante del equipo del proyecto, quiero capturar el contenido público del sitio web oficial de
Manuelita (páginas, documentos y archivos PDF) en su forma original, para que el futuro RAG cuente con
una base autoritativa de primera fuente.

**Why this priority**: El sitio oficial es la fuente primaria y la única controlada por la empresa. Sin
esta base, cualquier respuesta del RAG carecería de respaldo institucional.

**Independent Test**: Ejecutar la adquisición contra el dominio oficial en un entorno limpio y verificar
que las páginas y documentos alcanzables quedan almacenados con su metadata completa, y que lo bloqueado
queda registrado como exclusión.

**Acceptance Scenarios**:

1. **Given** el dominio oficial y un archivo de políticas que permite el rastreo, **When** se ejecuta una
   campaña de adquisición, **Then** cada página y documento alcanzable dentro del alcance se almacena una
   sola vez con URL de origen, fecha y hora de captura, tipo de contenido, tamaño, huella de integridad y
   categoría asignada.
2. **Given** una página que enlaza un documento PDF, **When** el documento se descubre, **Then** se descarga
   y se asocia a la página que lo referencia.
3. **Given** una ruta prohibida por las políticas del sitio, **When** se descubre, **Then** no se solicita y
   se registra como exclusión con su motivo.
4. **Given** una campaña finalizada, **When** el operador consulta el reporte de ejecución, **Then** obtiene
   los conteos de elementos capturados, omitidos y fallidos, y el espacio total ocupado.

---

### User Story 2 - Trazabilidad y reanudación de la adquisición (Priority: P2)

Como analista de datos, quiero auditar el origen de cualquier elemento almacenado y reanudar una campaña
interrumpida sin duplicar ni corromper información, para que la capa bronce sea confiable y reproducible.

**Why this priority**: Una capa bronce sin procedencia verificable no sirve como evidencia; además, las
campañas de rastreo extensas fallan o se interrumpen y deben poder retomarse.

**Independent Test**: Interrumpir una campaña a mitad de ejecución, reiniciarla y comprobar que no hay
duplicados ni archivos corruptos; luego tomar elementos al azar y verificar que su origen y huella coinciden.

**Acceptance Scenarios**:

1. **Given** un elemento almacenado, **When** el analista lo consulta, **Then** obtiene su URL de origen, fecha
   de captura, huella de integridad, categoría y campaña a la que pertenece.
2. **Given** una campaña ya completada, **When** se ejecuta de nuevo, **Then** no se generan copias duplicadas y
   los conteos del catálogo se mantienen.
3. **Given** una campaña interrumpida, **When** se reanuda, **Then** continúa desde el último punto registrado sin
   volver a descargar lo ya completado ni dejar archivos parciales.
4. **Given** una página cuyo contenido cambió desde la captura anterior, **When** se vuelve a capturar, **Then**
   se conserva la versión previa y se registra la nueva con su propia fecha.
5. **Given** una muestra aleatoria de elementos, **When** se verifica su huella, **Then** coincide con el contenido
   almacenado.

---

### User Story 3 - Cobertura de las cuatro categorías de información (Priority: P3)

Como líder del proyecto, quiero conocer qué elementos de la lista de información requerida están cubiertos y
cuáles faltan, para priorizar las siguientes campañas y sustentar el alcance ante la evaluación del curso.

**Why this priority**: La lista de identidad, oferta, presencia digital y datos duros define el valor del RAG;
sin un mapa de cobertura no se puede demostrar completitud ni justificar vacíos.

**Independent Test**: Tras una campaña, generar la matriz de cobertura y verificar que cada uno de los 24
elementos requeridos reporta estado y evidencia o una justificación de ausencia.

**Acceptance Scenarios**:

1. **Given** una campaña finalizada, **When** se consulta la matriz de cobertura, **Then** cada elemento requerido
   reporta estado cubierto, parcial o faltante, y los elementos que lo respaldan.
2. **Given** un elemento faltante, **When** se revisa su registro, **Then** existe una razón documentada (no
   publicado, acceso restringido, fuera de alcance o agotado en el límite de almacenamiento).
3. **Given** una categoría con cobertura insuficiente, **When** se genera el reporte, **Then** se destacan las
   prioridades sugeridas para la siguiente campaña.
4. **Given** una categoría seleccionada, **When** el analista filtra el catálogo, **Then** obtiene únicamente los
   elementos asociados a esa categoría.

---

### User Story 4 - Presencia digital y contenido audiovisual (Priority: P4)

Como integrante del equipo, quiero incorporar noticias, blogs, redes sociales, entrevistas y transcripciones de
YouTube relacionadas con Manuelita, para enriquecer el RAG con la voz pública de la empresa y de terceros.

**Why this priority**: Complementa la fuente oficial con contexto, actualidad y evidencia externa; es valiosa pero
depende de que la base oficial y la trazabilidad ya funcionen.

**Independent Test**: Procesar un conjunto de videos, publicaciones y noticias conocidas y verificar que se
capturan sus textos, metadatos y transcripciones disponibles, y que lo restringido se registra como exclusión.

**Acceptance Scenarios**:

1. **Given** un video de YouTube relacionado con Manuelita, **When** se procesa, **Then** se almacenan sus metadatos
   y los subtítulos o transcripciones disponibles; si no existen, se registra como vacío de información.
2. **Given** una publicación pública en una red social, **When** se captura, **Then** se registran plataforma, cuenta,
   fecha, texto y referencias a contenido multimedia.
3. **Given** una plataforma que exige autenticación o prohíbe la automatización, **When** se evalúa, **Then** se excluye
   y se documenta, sin intentar eludir el control.
4. **Given** un video, **When** se almacena, **Then** no se guarda el archivo de video o audio completo, solo su texto y
   metadatos.
5. **Given** una noticia, artículo de blog o vacante pública, **When** se captura, **Then** se registra su fuente,
   fecha de publicación y vínculo con la categoría correspondiente.

---

### Edge Cases

- **Sitio reestructurado durante la campaña**: enlaces que dejan de existir, redirecciones o contenido movido; se
  registra el fallo y se continúa sin abortar la campaña.
- **Contenido duplicado en varias URL**: una misma pieza accesible desde rutas distintas; se almacena una sola copia y
  se conservan las URL alternas como alias.
- **Contenido generado dinámicamente o paginación infinita**: listados que solo se materializan al interactuar; se
  define un límite de profundidad y se registra lo no alcanzado.
- **Límite de almacenamiento alcanzado**: un archivo grande excede el espacio restante; se prioriza por valor de
  categoría y se registra como diferido, sin superar el tope.
- **Bloqueo por tasa de solicitudes o por la plataforma**: respuestas de límite de tasa, bloqueos temporales o
  desafíos anti-automatización; se aplica espera y reintento acotado, y se registra el bloqueo sin evadirlo.
- **Transcripciones ausentes o solo automáticas**: videos sin subtítulos disponibles o con calidad insuficiente; se
  almacena lo disponible y se marca la limitación.
- **Redes sociales que exigen inicio de sesión**: el contenido no es público; se excluye con justificación.
- **Descarga parcial o corrupta**: archivo truncado o con tipo de contenido inesperado; se descarta, se reintenta y se
  registra el fallo.
- **Contenido en varios idiomas**: páginas o documentos en español e inglés; se registra el idioma detectado.
- **Páginas vacías o de error disfrazadas**: respuestas exitosas sin contenido útil; se detectan y no cuentan como
  cobertura.
- **Solicitud de retiro o corrección de contenido**: se retira del acceso sin borrar el registro de procedencia.
- **Cambio en las políticas del sitio entre campañas**: se vuelve a evaluar el permiso en cada ejecución.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST descubrir y recuperar el contenido público del dominio oficial de Manuelita, incluyendo
  páginas, documentos y archivos PDF enlazados o declarados en su mapa del sitio.
- **FR-002**: El sistema MUST recuperar contenido público complementario de las fuentes exigidas por la lista de
  información: noticias y sala de prensa, blogs, redes sociales, YouTube, portales de empleo, datos abiertos y
  rankings sectoriales.
- **FR-003**: El sistema MUST registrar para cada elemento: URL de origen, URL canónica, plataforma, fecha y hora de
  captura en UTC, estado de la respuesta, tipo de contenido, tamaño en bytes, huella criptográfica de integridad,
  categoría y subcategoría, idioma y campaña.
- **FR-004**: El sistema MUST preservar el contenido original sin transformarlo, resumirlo ni limpiarlo; la
  normalización y el enriquecimiento corresponden a etapas posteriores.
- **FR-005**: El sistema MUST almacenar la información en un área bronce dedicada dentro del directorio de datos del
  proyecto, separada de las etapas posteriores y organizada por fuente y campaña.
- **FR-006**: El sistema MUST mantener un catálogo legible por máquina de todos los elementos y campañas, consultable
  sin recorrer manualmente los archivos.
- **FR-007**: El sistema MUST generar una matriz de cobertura que asocie cada uno de los 24 elementos requeridos con
  los artefactos que lo respaldan o con la justificación de su ausencia.
- **FR-008**: El sistema MUST evaluar y respetar las políticas de cada fuente (archivo de exclusión de robots, términos
  de servicio y límites de tasa) antes de solicitar contenido, y registrar la decisión por fuente.
- **FR-009**: El sistema MUST NOT eludir autenticación, muros de pago, captchas ni controles de acceso, ni recolectar
  datos personales que no sean de carácter público corporativo.
- **FR-010**: El sistema MUST garantizar que el área bronce nunca supere los 10 GB; debe medir el espacio antes de cada
  escritura, priorizar por valor de categoría al acercarse al límite y reportar el uso final.
- **FR-011**: El sistema MUST deduplicar por huella de integridad: un mismo contenido se almacena una sola vez y las URL
  alternas se registran como alias.
- **FR-012**: El sistema MUST ser idempotente y reanudable: una nueva ejecución omite lo ya capturado, retoma desde el
  último punto registrado y no deja archivos parciales.
- **FR-013**: El sistema MUST reintentar fallos transitorios con espera progresiva y un número máximo de intentos, y
  registrar los fallos definitivos con su causa sin detener la campaña.
- **FR-014**: El sistema MUST normalizar las URL para evitar duplicados por parámetros de seguimiento, fragmentos,
  mayúsculas o barras finales, conservando la URL original como referencia.
- **FR-015**: El sistema MUST registrar metadatos de videos de YouTube (identificador, título, canal, fecha, duración e
  idioma) y los subtítulos o transcripciones disponibles, sin almacenar el archivo de video o audio.
- **FR-016**: El sistema MUST registrar publicaciones sociales públicas con plataforma, cuenta, fecha, texto y
  referencias multimedia, respetando las restricciones de acceso de cada plataforma.
- **FR-017**: El sistema MUST producir un reporte por campaña con elementos intentados, capturados, omitidos y fallidos,
  bytes almacenados, duración, porcentaje de cobertura y vacíos identificados.
- **FR-018**: El sistema MUST operar a partir de una configuración versionada que declare fuentes semilla, categorías,
  límites de profundidad, volumen y exclusiones, de modo que una campaña sea reproducible.
- **FR-019**: El sistema MUST distinguir y etiquetar el contenido de primera fuente (sitio y canales oficiales) del de
  terceros, para que las etapas posteriores puedan priorizar autoridad.
- **FR-020**: El sistema MUST preservar versiones anteriores cuando el contenido de una misma URL cambie entre
  campañas, registrando la fecha de cada versión.
- **FR-021**: El sistema MUST permitir excluir manualmente URL o dominios y aplicar esa lista en todas las campañas.
- **FR-022**: El sistema MUST registrar el idioma detectado de cada elemento y conservar tanto contenido en español como
  en inglés relacionado con Manuelita.

### Required Information Checklist

Los 24 elementos que la capa bronce debe contabilizar, usados como base de la matriz de cobertura (FR-007):

| ID | Categoría | Elemento requerido |
|----|-----------|--------------------|
| I-01 | Identidad | Misión y visión |
| I-02 | Identidad | Valores y propósito |
| I-03 | Identidad | Historia (año de fundación, hitos) |
| I-04 | Identidad | Fundador / dueño y junta |
| I-05 | Identidad | Gerente y equipo directivo |
| I-06 | Identidad | Sedes y ubicaciones |
| O-01 | Oferta | Productos y servicios |
| O-02 | Oferta | Fichas técnicas y especificaciones |
| O-03 | Oferta | Precios y planes |
| O-04 | Oferta | Catálogos en PDF |
| O-05 | Oferta | Casos de éxito y clientes |
| O-06 | Oferta | Certificaciones (ISO, BASC, INVIMA, etc.) |
| D-01 | Presencia digital | Noticias y sala de prensa |
| D-02 | Presencia digital | Blog y artículos |
| D-03 | Presencia digital | Videos de YouTube y subtítulos |
| D-04 | Presencia digital | Entrevistas del gerente (audio o video) |
| D-05 | Presencia digital | Redes sociales (publicaciones y descripciones) |
| D-06 | Presencia digital | Vacantes de empleo (Glassdoor, Computrabajo) |
| H-01 | Datos duros | Informes financieros y memoria anual |
| H-02 | Datos duros | NIT y registro en Cámara de Comercio |
| H-03 | Datos duros | Indicadores de sostenibilidad |
| H-04 | Datos duros | Precios públicos y tarifas |
| H-05 | Datos duros | Datos abiertos (Superintendencia, SECOP) |
| H-06 | Datos duros | Rankings sectoriales |

### Key Entities *(include if feature involves data)*

- **Fuente**: plataforma o dominio de origen (sitio oficial, red social, portal de datos abiertos); atributos: dominio,
  tipo de fuente, autoridad (primera fuente o tercero), política de acceso y estado de cumplimiento.
- **Objetivo de adquisición**: URL descubierta que debe evaluarse; atributos: URL original, URL canónica, categoría,
  prioridad, profundidad y estado.
- **Artefacto crudo**: contenido recuperado tal como se obtuvo; atributos: bytes, tipo de contenido, tamaño, huella de
  integridad, fecha de captura y ubicación lógica.
- **Registro de catálogo**: vínculo entre artefacto, objetivo, fuente y campaña, con toda la metadata de procedencia.
- **Campaña**: ejecución de adquisición; atributos: identificador, configuración usada, fecha de inicio y fin, conteos,
  bytes almacenados y estado.
- **Elemento de cobertura**: cada uno de los 24 requisitos de información; atributos: categoría, subcategoría, estado,
  artefactos asociados y justificación de ausencia.
- **Registro de exclusión o fallo**: URL no procesada; atributos: causa (política, acceso, fuera de alcance, error,
  límite de espacio), intentos y fecha.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los 24 elementos de información requeridos queda contabilizado: con al menos un artefacto que
  lo respalde o con una justificación verificable de su ausencia.
- **SC-002**: El 100% de los artefactos almacenados cuenta con URL de origen, fecha de captura, huella de integridad y
  categoría; una auditoría de 50 elementos aleatorios no encuentra campos faltantes.
- **SC-003**: El espacio ocupado por la capa bronce se mantiene en 10 GB o menos durante toda la campaña, y el reporte
  muestra el consumo máximo alcanzado.
- **SC-004**: Repetir una campaña completada produce cero artefactos duplicados nuevos y conteos de catálogo idénticos.
- **SC-005**: Una campaña interrumpida y reanudada no pierde ni corrompe ningún artefacto ya completado y no vuelve a
  descargar elementos finalizados.
- **SC-006**: Un revisor puede rastrear cualquier artefacto hasta su URL pública y verificar su integridad en menos de
  dos minutos; la prueba con 20 elementos aleatorios tiene 100% de éxito.
- **SC-007**: El registro de solicitudes muestra cero accesos a rutas prohibidas por las políticas de las fuentes.
- **SC-008**: Al menos el 95% de las páginas y documentos alcanzables y permitidos del dominio oficial queda capturado en
  la primera campaña completa, excluyendo lo bloqueado o fuera de alcance.
- **SC-009**: Cada campaña genera su reporte de cobertura y ejecución de forma automática en un máximo de 15 minutos tras
  finalizar.
- **SC-010**: Al menos el 90% de los elementos requeridos que estén públicamente disponibles queda cubierto al finalizar
  la primera campaña completa; el resto cuenta con justificación registrada.

## Assumptions

- **Alcance de fase**: esta especificación cubre únicamente la capa bronce de recolección. Quedan fuera la limpieza,
  normalización, resolución de entidades, indexación, embeddings, base vectorial y la interfaz de preguntas del RAG.
- **Contenido público**: solo se recolecta información accesible sin autenticación ni pago. El uso es académico y debe
  respetar los términos de cada fuente.
- **Datos personales**: se admiten nombres y cargos de directivos y voceros por ser información corporativa pública; no
  se recolectan datos de personas naturales ajenas a la actividad pública de la empresa.
- **Video y audio**: de YouTube se conservan metadatos y texto (subtítulos o transcripciones), no los archivos de medios.
- **Redes sociales**: se cubren únicamente páginas públicas; las plataformas que prohíben la automatización o exigen
  sesión se excluyen y se documentan como vacío.
- **Profundidad histórica**: se intenta todo el contenido público alcanzable; para noticias y redes sociales se priorizan
  los últimos cinco años.
- **Idioma**: el contenido principal está en español; se incluye contenido en inglés cuando sea relevante para Manuelita.
- **Tope de almacenamiento**: el límite de 10 GB se interpreta en sentido decimal (10.000.000.000 bytes) y se monitorea
  al 90% para activar la priorización.
- **Inmutabilidad**: la capa bronce es de solo adición; las correcciones se registran como nuevas versiones, no como
  sobrescrituras.
- **Duplicados**: se conserva una copia por contenido único; las URL alternas son alias, no copias.
- **Fuente de verdad**: el sitio y los canales oficiales de Manuelita prevalecen sobre terceros cuando hay conflicto.
- **Disponibilidad externa**: la cobertura depende de que las fuentes sigan en línea y permitan el acceso; la
  indisponibilidad se registra como limitación, no como fallo del sistema.
- **Herramientas y ubicación física**: las decisiones de herramienta de recolección y de organización de archivos serán
  detalladas en el plan técnico, respetando las restricciones del proyecto.
