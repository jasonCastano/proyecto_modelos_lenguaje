# Feature Specification: Capa Plata (Silver) de la Arquitectura Medallion

**Feature Branch**: `003-silver-medallion-layer`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "según el contexto del proyecto, realiza las especificaciones para la etapa silver de la arquitectura medallion"

**Corpus de entrada**: la capa bronce activa contiene 524 artefactos (290,5 MB): 322 páginas HTML,
113 PDF, 44 JSON de YouTube, 34 transcripciones VTT, 10 XML de sitemap y 1 hoja de cálculo. 394 artefactos
están en español, 9 en inglés y 121 sin idioma detectado; 114 no tienen título. Los 26.347 artefactos en
cuarentena y los retirados quedan fuera de esta etapa. Los PDF incluyen informes de sostenibilidad y de
gestión de hasta 28 MB, con cientos de páginas y tablas. Al cierre de la implementación, el backfill de
metadatos de YouTube elevó el corpus activo a 557 artefactos (76 JSON y 35 VTT); los criterios se miden sobre
ese corte.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Texto limpio y citable a partir de cualquier artefacto bronce (Priority: P1)

Como integrante del equipo, quiero que cada artefacto activo de la capa bronce se convierta en texto limpio,
legible y verificable, conservando su origen exacto, para que el futuro RAG pueda responder con información
de Manuelita y citar la fuente sin ambigüedad.

**Why this priority**: sin texto limpio y trazable no existe base de conocimiento; la capa plata es el puente
entre los bytes crudos y cualquier tarea de resumen, FAQ o Q&A. Si solo se implementa esta historia, el equipo
ya puede leer, buscar y citar el corpus depurado.

**Independent Test**: procesar una muestra de páginas HTML, PDF, transcripciones y metadatos, y comprobar que
cada uno produce texto legible, que el texto conserva cifras, nombres y fechas, y que cada unidad puede
rastrearse hasta su artefacto bronce y su URL pública.

**Acceptance Scenarios**:

1. **Given** un artefacto bronce activo con texto extraíble, **When** se procesa, **Then** se genera un
   documento plata con texto limpio, su artefacto de origen, URL, título, fuente, fecha de captura y hash de
   contenido.
2. **Given** una página HTML con menús, avisos de cookies, pies de página y contenido principal, **When** se
   limpia, **Then** se conserva el contenido informativo y se elimina el marco de navegación repetitivo.
3. **Given** un PDF con capa de texto, **When** se procesa, **Then** se extrae su texto por página y se
   conserva el número de página de cada fragmento.
4. **Given** una transcripción VTT, **When** se procesa, **Then** se obtiene texto continuo sin marcas de
   tiempo redundantes, conservando el rango temporal de cada intervención.
5. **Given** un artefacto cuyo texto no puede extraerse (PDF escaneado, página vacía o solo navegación),
   **When** se evalúa, **Then** se omite con una razón explícita y no se genera un documento vacío.
6. **Given** un documento plata, **When** el revisor toma una frase al azar, **Then** esa frase aparece
   literalmente en el texto extraído del artefacto bronce original, salvo cambios de espacios y saltos de
   línea declarados.

---

### User Story 2 - Secciones y fragmentos recuperables con contexto (Priority: P2)

Como responsable de la base de conocimiento, quiero que cada documento se divida en secciones identificables
y en fragmentos de tamaño controlado que incluyan su contexto, para que la recuperación posterior encuentre
pasajes completos y las respuestas puedan citar la sección correcta.

**Why this priority**: un texto plano de cientos de páginas no es utilizable por un modelo; la fragmentación
con contexto y metadatos es lo que hace que el corpus sea recuperable y que las citas sean precisas.

**Independent Test**: procesar un informe extenso y una página con encabezados, y verificar que cada fragmento
pertenece a una sola sección, respeta el tamaño máximo, incluye el título de la sección y puede reconstruirse
en el orden original del documento.

**Acceptance Scenarios**:

1. **Given** un documento con encabezados jerárquicos, **When** se estructura, **Then** cada fragmento registra
   la ruta de secciones a la que pertenece y el título de la sección inmediata.
2. **Given** una sección más larga que el tamaño máximo de fragmento, **When** se divide, **Then** se corta en
   límites de párrafo u oración, con solapamiento controlado y sin mezclar contenido de otra sección.
3. **Given** una sección más corta que el tamaño mínimo, **When** se procesa, **Then** se conserva como un
   único fragmento y no se fusiona con una sección distinta.
4. **Given** un documento sin encabezados detectables, **When** se estructura, **Then** todos sus fragmentos
   quedan marcados como "sin sección" y el documento se reporta para revisión, sin dejar el campo vacío.
5. **Given** un fragmento, **When** el revisor lo consulta, **Then** obtiene su posición en el documento, el
   rango de páginas o de tiempo, el número de tokens y un identificador estable para citarlo.

---

### User Story 3 - Deduplicación y selección de la versión canónica (Priority: P3)

Como analista del corpus, quiero detectar contenido repetido o casi idéntico entre fuentes, campañas y
versiones, y conservar una sola representación canónica con sus alias, para evitar que el RAG repita la misma
información y para preferir siempre la fuente más autoritativa y reciente.

**Why this priority**: el corpus proviene de varias campañas y de fuentes que replican contenido; sin
deduplicación, la recuperación devuelve pasajes redundantes y las citas pierden calidad.

**Independent Test**: introducir dos copias exactas y dos versiones casi idénticas del mismo texto, ejecutar la
deduplicación y comprobar que se conserva una representación canónica, que las demás quedan como alias y que
la elección respeta autoridad, vigencia y completitud.

**Acceptance Scenarios**:

1. **Given** dos artefactos con texto normalizado idéntico, **When** se deduplica, **Then** se conserva un solo
   documento canónico y el otro se registra como alias con su URL.
2. **Given** dos versiones del mismo documento capturadas en fechas distintas, **When** se deduplica, **Then**
   se conserva la versión más reciente como canónica y la anterior queda registrada como versión previa.
3. **Given** dos textos casi idénticos con diferencias menores de formato, **When** se comparan, **Then** se
   agrupan como duplicados cercanos y se marca el grado de similitud.
4. **Given** un contenido replicado por una fuente oficial y por un tercero, **When** se elige el canónico,
   **Then** prevalece la fuente oficial, salvo que la de terceros aporte contenido sustancialmente distinto.
5. **Given** dos idiomas distintos del mismo contenido, **When** se deduplica, **Then** no se colapsan entre sí:
   cada idioma conserva su propia representación.

---

### User Story 4 - Control de calidad, reproceso e idempotencia (Priority: P4)

Como líder del proyecto, quiero un reporte verificable del procesamiento y la posibilidad de reprocesar solo lo
que cambió, para demostrar que la capa plata es completa, reproducible y auditable antes de construir la capa
oro.

**Why this priority**: la rúbrica y la constitución exigen reproducibilidad y métricas reales; sin un reporte de
calidad no se puede afirmar que el corpus está listo ni detectar extracciones defectuosas.

**Independent Test**: ejecutar el procesamiento dos veces sin cambios y comprobar que no se generan duplicados;
luego modificar un artefacto bronce y verificar que solo ese documento se reprocesa y que el reporte refleja el
cambio.

**Acceptance Scenarios**:

1. **Given** el corpus activo, **When** se ejecuta la etapa, **Then** cada artefacto recibe un estado:
   procesado, omitido con razón o fallido con causa.
2. **Given** una ejecución sin cambios en bronce, **When** se repite, **Then** no se crean documentos ni
   fragmentos nuevos y los identificadores permanecen estables.
3. **Given** un artefacto bronce modificado o una nueva versión, **When** se reprocesa, **Then** solo se
   actualiza ese documento y se conserva la trazabilidad de la versión anterior.
4. **Given** el reporte de calidad, **When** el líder lo consulta, **Then** obtiene conteos por fuente, formato
   y estado, tokens, fragmentos, duplicados, omisiones, fallos y duración.
5. **Given** una muestra aleatoria de fragmentos, **When** se audita, **Then** todos se rastrean hasta su
   artefacto bronce y su URL en menos de dos minutos.

### Edge Cases

- **PDF escaneado o sin capa de texto**: no se inventa contenido; se omite y se marca para una futura etapa de
  reconocimiento óptico.
- **PDF con varias columnas, tablas o notas al pie**: la extracción puede intercalar texto; se marca la
  calidad como dudosa y se conserva el original para revisión.
- **PDF de gran tamaño**: informes de hasta 28 MB y cientos de páginas; el procesamiento debe completarse sin
  agotar memoria ni abortar el resto del lote.
- **HTML renderizado dinámicamente**: el bronce solo contiene el HTML capturado; si el contenido principal no
  está presente, se omite con la razón "contenido no presente en la captura".
- **HTML con texto oculto o duplicado para accesibilidad**: se excluye el texto invisible y se evita duplicar
  el contenido visible.
- **Página de solo navegación, listado vacío o error disfrazado**: no genera fragmentos y se registra como
  omitida.
- **Encoding dañado o caracteres de reemplazo**: se intenta una reparación reversible; si no es posible, se
  conserva el texto y se marca la incidencia.
- **Transcripciones con cues solapados, repetidos o generados automáticamente**: se consolidan sin perder el
  orden temporal y se eliminan muletillas de la herramienta de transcripción.
- **Subtítulos en varios idiomas o variantes automáticas y manuales del mismo video**: se conservan las
  variantes idiomáticas y se prefiere la transcripción manual sobre la automática cuando compiten.
- **JSON de metadatos sin cuerpo narrativo**: se convierte en un registro estructurado legible, no en un
  documento vacío.
- **XML de sitemap, robots o feeds**: son instrumentos de navegación, no conocimiento; se omiten con razón.
- **Hoja de cálculo con varias hojas o fórmulas**: se conservan los valores y el nombre de la hoja; no se
  ejecutan fórmulas.
- **Sección sin título detectable**: se asigna "sin sección" y se marca para revisión; nunca queda nula.
- **Documento duplicado dentro de la misma campaña**: se detecta antes de fragmentar para no duplicar trabajo.
- **Artefacto retirado, en cuarentena o con relevancia descartada**: no entra a la capa plata.
- **Contenido en inglés**: se aplican las mismas reglas y se conserva el idioma original.
- **Falló el procesamiento de un artefacto**: se registra y se continúa con el resto; la etapa no aborta.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST procesar exclusivamente artefactos activos del corpus bronce, excluyendo
  cuarentena, retiros y contenido sin relevancia aprobada.
- **FR-002**: El sistema MUST registrar para cada artefacto de entrada un estado final: procesado, omitido con
  razón o fallido con causa, sin dejar artefactos sin evaluar.
- **FR-003**: El sistema MUST extraer texto de todos los formatos admitidos en el corpus: HTML, PDF con capa de
  texto, JSON, XML, texto plano, VTT y hojas de cálculo.
- **FR-004**: El sistema MUST conservar el linaje completo de cada documento y fragmento: artefacto bronce,
  hash de contenido, URL original y canónica, título, fuente, autoridad, fecha de captura, fecha de
  publicación, idioma y categoría.
- **FR-005**: El sistema MUST eliminar el marco repetitivo de las páginas (navegación, menús, avisos de
  cookies, pies, barras laterales, publicidad y enlaces sociales) sin eliminar contenido informativo.
- **FR-006**: El sistema MUST normalizar espacios, saltos de línea, caracteres de control y entidades HTML,
  preservando cifras, unidades, fechas, nombres propios y signos.
- **FR-007**: El sistema MUST reparar encoding dañado solo cuando la reparación sea reversible; en caso
  contrario, MUST conservar el texto y marcar la incidencia.
- **FR-008**: El sistema MUST detectar y registrar el idioma de cada documento, conservar español e inglés y
  marcar como desconocido lo que no pueda determinarse.
- **FR-009**: El sistema MUST segmentar cada documento en secciones jerárquicas cuando existan encabezados,
  marcadores de PDF o estructura numerada.
- **FR-010**: El sistema MUST asignar a cada fragmento la ruta de secciones y el título de su sección
  inmediata; si no hay título detectable, MUST usar "sin sección" y marcar el documento para revisión.
- **FR-011**: El sistema MUST fragmentar por sección, sin mezclar contenido de secciones distintas en un mismo
  fragmento.
- **FR-012**: El sistema MUST respetar un tamaño objetivo y un máximo de tokens por fragmento, con
  solapamiento controlado, y MUST cortar en límites de párrafo u oración siempre que sea posible.
- **FR-013**: El sistema MUST conservar como fragmento único toda sección más corta que el mínimo, sin
  fusionarla con otra sección.
- **FR-014**: El sistema MUST registrar en cada fragmento su orden, posición o desplazamiento, número de
  tokens, rango de páginas para PDF y rango temporal para transcripciones.
- **FR-015**: El sistema MUST generar identificadores de documento y fragmento deterministas y estables: el
  mismo contenido de entrada y la misma configuración producen los mismos identificadores.
- **FR-016**: El sistema MUST detectar duplicados exactos mediante el texto normalizado y agrupar duplicados
  cercanos mediante un umbral de similitud configurable.
- **FR-017**: El sistema MUST elegir una representación canónica por grupo de duplicados, priorizando
  autoridad de la fuente, vigencia y completitud; las demás MUST quedar registradas como alias.
- **FR-018**: El sistema MUST conservar versiones anteriores cuando cambie el contenido de una misma URL y MUST
  procesar la versión más reciente como canónica.
- **FR-019**: El sistema MUST tratar por separado las variantes en distintos idiomas y MUST preferir la
  transcripción manual sobre la automática cuando ambas existan para el mismo video e idioma.
- **FR-020**: El sistema MUST omitir con razón explícita los artefactos sin texto extraíble, las páginas de
  solo navegación, los sitemaps, los archivos robots y el contenido vacío.
- **FR-021**: El sistema MUST marcar la calidad de extracción cuando la densidad de texto, la estructura
  tabular o la proporción de caracteres no textuales superen los umbrales configurados y versionados.
- **FR-022**: El sistema MUST producir como salida un registro por documento con el texto limpio y su
  estructura de secciones, y un registro por fragmento con el texto y toda su metadata.
- **FR-023**: El sistema MUST emitir los registros en formato JSONL y una representación Markdown con
  frontmatter para revisión humana, en UTF-8.
- **FR-024**: El sistema MUST incluir en cada registro la nota de licencia o uso y los campos necesarios para
  citar la fuente (título, URL, fecha, sección y posición).
- **FR-025**: El sistema MUST conservar el texto de cada fragmento de forma literal respecto al texto extraído,
  salvo la normalización de espacios declarada, para permitir citas exactas.
- **FR-026**: El sistema MUST NOT resumir, parafrasear, traducir, generar embeddings ni interpretar el
  contenido con un modelo de lenguaje en esta etapa.
- **FR-027**: El sistema MUST NOT modificar, mover ni reescribir los artefactos de la capa bronce.
- **FR-028**: El sistema MUST ser idempotente e incremental: reprocesa solo artefactos nuevos o cuyo hash de
  contenido cambió y reutiliza los resultados de los demás.
- **FR-029**: El sistema MUST versionar la configuración de limpieza, estructuración y fragmentación, y MUST
  registrar la versión usada en cada ejecución.
- **FR-030**: El sistema MUST generar un reporte de calidad con conteos por fuente, formato y estado, tokens
  de entrada y salida, fragmentos, duplicados, omisiones, fallos, cobertura de secciones y duración.
- **FR-031**: El sistema MUST permitir auditar una muestra aleatoria de fragmentos y verificar su trazabilidad
  hasta el artefacto bronce y la URL pública.
- **FR-032**: El sistema MUST procesar el corpus activo completo en una sola ejecución acotada, sin requerir
  red ni intervención manual por artefacto.
- **FR-033**: El sistema MUST registrar los fallos por artefacto sin abortar el lote y MUST permitir reintentar
  solo los fallidos.

### Key Entities *(include if feature involves data)*

- **Documento plata**: representación limpia de un artefacto bronce; atributos: identificador, artefacto y hash
  de origen, URL, título, fuente, autoridad, idioma, fechas, categoría, texto limpio, estructura de secciones,
  estado y marcas de calidad.
- **Sección**: división lógica del documento; atributos: identificador, título, ruta jerárquica, nivel, orden,
  rango de texto y rango de páginas o tiempo.
- **Fragmento**: unidad recuperable y citable; atributos: identificador estable, documento, sección, orden,
  texto, tokens, desplazamiento, rango de páginas o tiempo y marcas de calidad.
- **Linaje**: vínculo verificable entre fragmento, documento, artefacto bronce y URL pública; atributos: hashes,
  fechas, campaña y fuente.
- **Regla de limpieza**: transformación versionada aplicada al texto; atributos: identificador, versión,
  descripción, tipo y estado.
- **Configuración de fragmentación**: parámetros versionados de tamaño, solapamiento, mínimos y criterios de
  corte; atributos: versión, valores y fecha de vigencia.
- **Grupo de duplicados**: conjunto de documentos con texto igual o similar; atributos: representante canónico,
  miembros, tipo (exacto o cercano), similitud y criterio de elección.
- **Artefacto omitido o fallido**: entrada no convertida en documento; atributos: artefacto, motivo, detalle,
  intentos y fecha.
- **Reporte de calidad**: resumen verificable de una ejecución; atributos: fecha, configuración, conteos por
  estado, tokens, fragmentos, duplicados, cobertura y duración.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los artefactos activos del corte (524 al momento de esta especificación) recibe un
  estado final verificable (procesado, omitido o fallido); ningún artefacto queda sin evaluar.
- **SC-002**: Al menos el 95% de los artefactos con texto extraíble genera al menos un documento y un fragmento;
  el 100% de los PDF sin capa de texto queda identificado como omitido, no como vacío.
- **SC-003**: El 100% de los fragmentos contiene documento de origen, sección, orden, tokens, posición y linaje;
  una auditoría de 50 fragmentos aleatorios no encuentra campos faltantes.
- **SC-004**: El 100% de los fragmentos tiene una sección asignada, real o marcada como "sin sección"; no existe
  ningún valor nulo en ese campo.
- **SC-005**: Al menos el 85% de las secciones de documentos estructurados tiene un título explícito; el resto
  queda marcado para revisión con su motivo.
- **SC-006**: El 100% de una muestra de 100 fragmentos se rastrea hasta su artefacto bronce y su URL pública en
  menos de dos minutos, y su texto coincide con el original tras la normalización declarada.
- **SC-007**: El 100% de los duplicados exactos se detecta y se colapsa en una representación canónica; los
  duplicados cercanos por encima del umbral se agrupan y se reportan.
- **SC-008**: Una segunda ejecución sin cambios en bronce produce cero documentos y cero fragmentos nuevos, y
  mantiene idénticos los identificadores y los hashes de salida.
- **SC-009**: Tras modificar un solo artefacto bronce, el reproceso actualiza únicamente ese documento y deja
  constancia de la versión anterior.
- **SC-010**: Al menos el 99% de los fragmentos respeta el tamaño máximo configurado; el 100% respeta el límite
  de sección y no mezcla contenido de secciones distintas.
- **SC-011**: El procesamiento completo del corpus activo termina en 30 minutos o menos en un equipo de
  referencia de 4 núcleos y 8 GB de memoria, sin agotar memoria ni abortar por un artefacto grande.
- **SC-012**: El reporte de calidad se genera automáticamente al finalizar y permite reconstruir los conteos de
  entrada, salida, omisiones, fallos y duplicados sin revisar archivos manualmente.
- **SC-013**: Los hashes de todos los artefactos bronce activos del corte son idénticos antes y después de la
  ejecución; la capa bronce no registra ninguna modificación.
- **SC-014**: La capa plata se regenera desde un clon limpio y el corpus bronce activo, sin acceso a internet,
  y produce los mismos documentos, fragmentos e identificadores.

## Assumptions

- **Alcance de fase**: esta especificación cubre únicamente la conversión de bronce a plata (texto limpio,
  secciones y fragmentos). La base de conocimiento consolidada, los resúmenes, las FAQ, los embeddings, la
  base vectorial y la interfaz Q&A pertenecen a las etapas oro y de aplicación.
- **Corpus de entrada**: se parte de los 524 artefactos activos descritos arriba; nuevas campañas pueden
  ampliar el corpus y se procesarán con las mismas reglas.
- **PDF**: se asume que los informes principales tienen capa de texto. El reconocimiento óptico de PDF
  escaneados e imágenes queda fuera de alcance y se declara como vacío.
- **Idioma**: el contenido principal está en español; el inglés se procesa con las mismas reglas y no se
  traduce.
- **Fragmentación por defecto**: tamaño objetivo de 800 tokens, máximo de 1.000 y solapamiento de 120 tokens;
  los valores definitivos se fijan en la configuración versionada y pueden ajustarse con medición.
- **Tokens**: se cuentan con el tokenizador configurado y documentado; el mismo tokenizador se usa en todas las
  mediciones para que los conteos sean comparables.
- **Duplicados cercanos**: el umbral inicial de similitud es 0,90 y se valida con una muestra antes de
  considerarse definitivo.
- **Autoridad**: ante contenido equivalente, prevalece la fuente oficial sobre terceros, y la versión más
  reciente sobre la anterior.
- **Contenido no textual**: imágenes, videos, audio y figuras no se describen ni se transcriben en esta etapa;
  solo se procesa el texto disponible en bronce.
- **Licencia y uso**: cada documento conserva la nota de uso académico y la atribución de su fuente.
- **Datos no versionados**: la salida de plata vive bajo `data/silver/` y no se versiona; se reproduce desde
  bronce con la configuración versionada.
- **Dependencia de calidad del bronce**: si un artefacto bronce está incompleto o corrupto, la plata hereda la
  limitación y la declara; no se corrige el bronce en esta etapa.
