# Feature Specification: Capa Oro (Gold): Base de Conocimiento Consolidada y Citable

**Feature Branch**: `004-gold-medallion-layer`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "según el contexto del proyecto, realiza las especificaciones para la etapa gold de la arquitectura medallion"

**Corpus de entrada**: la capa plata activa contiene 404 documentos canónicos y 3.810 fragmentos, más 92
alias que no se indexan. Proviene de 557 artefactos bronce (sitio oficial, YouTube, Fundación Manuelita y
terceros) y de 61 artefactos omitidos con razón. La plata ocupa 23,5 MB y sus fragmentos ya tienen sección,
offsets, páginas/tiempos y linaje hasta la URL pública.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Base de conocimiento consolidada y citable (Priority: P1)

Como integrante del equipo, quiero convertir los documentos y fragmentos de la capa plata en una base de
conocimiento organizada por temas, con afirmaciones respaldadas por evidencia y citas verificables, para que
las tareas de Resumen, FAQ y Q&A trabajen sobre un corpus pequeño, ordenado y confiable en lugar de recorrer
todos los fragmentos crudos.

**Why this priority**: sin una base consolidada, el modelo recibe fragmentos dispersos, repite información y
no puede citar con precisión. La capa oro es el insumo directo del Módulo 1.

**Independent Test**: construir la base a partir de la plata y comprobar que cada unidad de conocimiento tiene
tema, texto, al menos una cita y linaje hasta un fragmento y una URL; que no existen afirmaciones sin
evidencia; y que el conjunto cubre los temas principales de Manuelita.

**Acceptance Scenarios**:

1. **Given** un fragmento canónico de la plata, **When** se incorpora a la base, **Then** queda asociado a un
   tema y a una o más unidades de conocimiento con su cita y su linaje.
2. **Given** una unidad de conocimiento, **When** el revisor la consulta, **Then** obtiene el texto de la
   afirmación, el tema, la autoridad de la fuente, la fecha y los fragmentos que la sustentan.
3. **Given** una unidad sin evidencia suficiente, **When** se evalúa, **Then** no se publica como conocimiento y
   se registra como vacío o candidata a revisión.
4. **Given** dos fragmentos que repiten la misma información, **When** se consolidan, **Then** se conserva una
   sola unidad con todas las evidencias y no se duplica el contenido.
5. **Given** la base publicada, **When** el equipo la abre, **Then** puede navegar por temas y llegar desde
   cualquier afirmación hasta la URL pública original.

---

### User Story 2 - Entidades, hechos y resolución de conflictos (Priority: P2)

Como analista del corpus, quiero identificar las entidades y afirmaciones relevantes de Manuelita y resolver
los conflictos entre fuentes con reglas explícitas, para que la base no mezcle versiones contradictorias ni
presente datos obsoletos como vigentes.

**Why this priority**: el corpus reúne fuentes oficiales, videos, la Fundación y terceros; sin una capa de
entidades y conflictos, el RAG puede responder con cifras o fechas contradictorias.

**Independent Test**: introducir dos fuentes con el mismo hecho y valores distintos, y verificar que el
conflicto queda registrado, que se identifica la fuente preferente y que la versión anterior no se pierde.

**Acceptance Scenarios**:

1. **Given** dos afirmaciones sobre el mismo sujeto y atributo con valores distintos, **When** se comparan,
   **Then** se registra un conflicto con ambas evidencias y fechas.
2. **Given** un conflicto entre una fuente oficial y una de terceros, **When** se elige la versión principal,
   **Then** prevalece la oficial y la otra queda como evidencia secundaria.
3. **Given** dos versiones del mismo dato en fechas distintas, **When** se consolida, **Then** se conserva la
   más reciente como vigente y la anterior como histórica.
4. **Given** un conflicto sin fuente claramente preferente, **When** se publica, **Then** la unidad queda
   marcada como disputada y no se afirma una única verdad.
5. **Given** una entidad con nombres alternativos (filial, marca, sigla), **When** se consolida, **Then** todos
   los nombres se agrupan bajo la misma entidad canónica.

---

### User Story 3 - Cobertura verificable de los 24 ítems de información (Priority: P3)

Como líder del proyecto, quiero una matriz que indique qué información de la lista de 24 ítems está realmente
cubierta por la base de conocimiento, con evidencia y vacíos justificados, para priorizar el contenido y
sustentar el alcance ante la evaluación.

**Why this priority**: la matriz actual del bronce es un conteo por palabras clave con falsos positivos. La
capa oro debe demostrar cobertura con afirmaciones y citas reales, no con coincidencias superficiales.

**Independent Test**: generar la matriz y verificar que cada ítem tiene estado, evidencia o razón de vacío, y
que un ítem sin unidades verificables no aparece como cubierto.

**Acceptance Scenarios**:

1. **Given** la base consolidada, **When** se genera la matriz, **Then** cada uno de los 24 ítems reporta
   estado cubierto, parcial o faltante, con las unidades que lo respaldan.
2. **Given** un ítem sin evidencia suficiente, **When** se evalúa, **Then** se registra como faltante o parcial
   con una razón y una recomendación de fuente.
3. **Given** un ítem cubierto por una fuente de terceros, **When** se reporta, **Then** se indica la autoridad
   y se distingue de la cobertura oficial.
4. **Given** un ítem con información contradictoria, **When** se reporta, **Then** se muestran las unidades
   disputadas y no se oculta el conflicto.
5. **Given** el reporte de cobertura, **When** el líder lo consulta, **Then** ve el porcentaje de ítems
   cubiertos y la lista priorizada de vacíos.

---

### User Story 4 - Paquete de contexto listo para las tareas del Módulo 1 (Priority: P4)

Como responsable de la aplicación, quiero paquetes de contexto con tamaño controlado, priorizados por
cobertura, autoridad y vigencia, para alimentar Resumen, FAQ y Q&A sin exceder la ventana del modelo y sin
perder las citas.

**Why this priority**: el Módulo 1 necesita un contexto que quepa en el modelo y que sea representativo; un
volcado completo del corpus no es viable ni útil para la demo.

**Independent Test**: generar paquetes de distintos tamaños y verificar que respetan el presupuesto de tokens,
que incluyen citas y que cubren los temas prioritarios sin fragmentos duplicados.

**Acceptance Scenarios**:

1. **Given** la base consolidada, **When** se genera un paquete de contexto, **Then** su tamaño no excede el
   presupuesto configurado y cada bloque conserva su cita.
2. **Given** varios paquetes de distinto tamaño, **When** se comparan, **Then** el paquete mayor conserva todos
   los temas del menor y agrega contenido, sin duplicar unidades.
3. **Given** un tema sin evidencia, **When** se genera el paquete, **Then** no se inventa contenido y el tema se
   declara fuera de cobertura.
4. **Given** un paquete para FAQ, **When** se revisa, **Then** incluye preguntas semilla derivadas de la
   estructura y la cobertura, con la evidencia que las respalda.
5. **Given** un paquete para Q&A, **When** se usa, **Then** cada unidad es recuperable por tema y conserva su
   URL y su fragmento de origen.

---

### User Story 5 - Calidad, incrementalidad y auditoría (Priority: P5)

Como líder del proyecto, quiero un reporte de calidad y la posibilidad de regenerar la capa oro solo cuando
cambie la plata, para demostrar que la base es reproducible, auditable y no introduce información inventada.

**Why this priority**: la constitución exige reproducibilidad y evidencia; la capa oro alimenta directamente
las respuestas que se evaluarán con 20 preguntas.

**Independent Test**: ejecutar dos veces sin cambios y comprobar que no se generan unidades nuevas; modificar
un documento de la plata y verificar que solo se actualizan las unidades afectadas.

**Acceptance Scenarios**:

1. **Given** una ejecución, **When** finaliza, **Then** existe un reporte con unidades, temas, evidencias,
   conflictos, cobertura, tokens y duración.
2. **Given** una segunda ejecución sin cambios en la plata, **When** se repite, **Then** los archivos de salida
   son idénticos y no se duplican unidades.
3. **Given** un cambio en un documento de la plata, **When** se regenera, **Then** solo cambian las unidades
   afectadas y se conserva la trazabilidad anterior.
4. **Given** una muestra aleatoria de unidades, **When** se audita, **Then** todas se rastrean hasta una URL
   pública y un fragmento de la plata.
5. **Given** la base publicada, **When** se compara con la plata, **Then** no se modificó ningún artefacto de
   bronce o plata.

### Edge Cases

- **Cifras contradictorias**: dos fuentes reportan ingresos, hectáreas o empleos distintos; se registra el
  conflicto con fechas y autoridad, y no se promedian ni se inventa un valor.
- **Dato con y sin fecha**: una fuente declara el año y otra no; la unidad sin fecha se marca como histórica o
  no vigente, no se presenta como actual.
- **Versiones del mismo informe**: informes anuales sucesivos con cifras actualizadas; la versión más reciente
  es la vigente y la anterior queda como histórica.
- **Nombres alternativos**: filiales, marcas, siglas y nombres en inglés; se agrupan bajo la entidad canónica.
- **Contenido en inglés**: se conserva el texto original y se asocia al mismo tema; no se traduce en esta
  etapa.
- **Fragmento que cubre varios temas**: se asocia a más de un tema sin duplicar el texto ni perder la cita.
- **Tabla o cifra sin contexto**: si el fragmento no permite interpretar la cifra, se marca como ambiguo y no
  se publica como afirmación.
- **Unidad sin evidencia**: se descarta o se envía a revisión; nunca se publica como conocimiento.
- **Fuente oficial vs. tercero**: ante el mismo hecho, prevalece la oficial; el tercero se conserva como
  evidencia secundaria.
- **Conflicto no resoluble**: se publica como disputado con ambas versiones.
- **Duplicados entre documentos**: se consolidan en una unidad con varias evidencias.
- **Linaje roto**: si una unidad no puede rastrearse hasta un fragmento y una URL, no se publica.
- **Presupuesto de tokens excedido**: se prioriza cobertura y autoridad, y se excluye lo menos relevante con
  registro de lo omitido.
- **Tema vacío**: se declara fuera de cobertura; no se crea una página vacía.
- **Contenido de terceros con licencia restrictiva**: se cita y se limita su uso; si no se puede usar, se
  excluye.
- **Falló la consolidación de un documento**: se registra y se continúa con el resto.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: El sistema MUST construir la capa oro exclusivamente a partir de documentos y fragmentos
  canónicos de la capa plata, excluyendo alias, cuarentena y contenido retirado.
- **FR-002**: El sistema MUST conservar el linaje de cada unidad de conocimiento hasta el fragmento, el
  documento, el artefacto bronce y la URL pública.
- **FR-003**: El sistema MUST organizar el conocimiento con una taxonomía versionada de temas que cubra los 24
  ítems de información y las entidades principales de Manuelita.
- **FR-004**: El sistema MUST identificar entidades, productos, sedes, personas, fechas, cifras y unidades de
  medida relevantes mediante reglas deterministas y vocabulario controlado.
- **FR-005**: El sistema MUST producir unidades de conocimiento con un texto afirmativo o extractivo, su tema,
  su evidencia y su nivel de confianza.
- **FR-006**: El sistema MUST NOT publicar una unidad sin al menos una evidencia verificable; las unidades sin
  respaldo MUST registrarse como vacío o revisión.
- **FR-007**: El sistema MUST asignar identificadores deterministas y estables a unidades, temas y paquetes de
  contexto.
- **FR-008**: El sistema MUST deduplicar unidades equivalentes y fusionar sus evidencias sin perder ninguna
  cita.
- **FR-009**: El sistema MUST detectar conflictos cuando dos evidencias atribuyan valores distintos al mismo
  sujeto y atributo.
- **FR-010**: El sistema MUST resolver conflictos con reglas explícitas: autoridad de la fuente, vigencia y
  completitud; la fuente oficial prevalece sobre terceros.
- **FR-011**: El sistema MUST conservar los conflictos no resolubles como unidades disputadas con ambas
  versiones y sus fechas.
- **FR-012**: El sistema MUST reconocer nombres alternativos de una misma entidad y agruparlos bajo una entidad
  canónica.
- **FR-013**: El sistema MUST generar páginas de tema con secciones, afirmaciones y citas, en Markdown con
  frontmatter.
- **FR-014**: El sistema MUST generar un glosario de entidades y términos relevantes con su definición y
  evidencia.
- **FR-015**: El sistema MUST generar la matriz de los 24 ítems con estado, unidades de evidencia, autoridad y
  razón de vacío.
- **FR-016**: El sistema MUST distinguir cobertura oficial de cobertura de terceros y no ocultar información
  disputada.
- **FR-017**: El sistema MUST generar paquetes de contexto con presupuesto de tokens configurable, priorizados
  por cobertura, autoridad y vigencia.
- **FR-018**: El sistema MUST incluir citas y linaje en cada bloque de los paquetes de contexto.
- **FR-019**: El sistema MUST generar material de entrada para Resumen, FAQ y Q&A: contexto consolidado,
  preguntas semilla con evidencia y corpus recuperable por tema.
- **FR-020**: El sistema MUST NOT resumir, responder, traducir ni generar embeddings con un modelo de lenguaje
  en esta etapa; esas tareas pertenecen al Módulo 1.
- **FR-021**: El sistema MUST emitir las salidas en JSONL y Markdown con frontmatter YAML, en UTF-8.
- **FR-022**: El sistema MUST incluir en cada registro la nota de licencia o uso y la atribución de la fuente.
- **FR-023**: El sistema MUST generar un manifiesto con hashes, conteos y configuración de la ejecución.
- **FR-024**: El sistema MUST generar un reporte de calidad con unidades, temas, evidencias, conflictos,
  cobertura, tokens, omisiones y duración.
- **FR-025**: El sistema MUST ser idempotente e incremental: reprocesa solo documentos de plata nuevos o
  modificados y reutiliza el resto.
- **FR-026**: El sistema MUST NOT modificar, mover ni reescribir artefactos de bronce o plata.
- **FR-027**: El sistema MUST operar sin red y sin dependencias de servicios externos.
- **FR-028**: El sistema MUST versionar la taxonomía, las reglas de extracción y los presupuestos de contexto, y
  registrar la versión usada en cada ejecución.
- **FR-029**: El sistema MUST marcar como ambiguas las unidades cuya cifra, fecha o entidad no pueda
  interpretarse con el contexto disponible.
- **FR-030**: El sistema MUST conservar el texto en su idioma original y asociar contenido en inglés al mismo
  tema cuando corresponda.
- **FR-031**: El sistema MUST permitir auditar una muestra de unidades y verificar su evidencia y su linaje.
- **FR-032**: El sistema MUST registrar los documentos de plata que no produjeron unidades y la razón.
- **FR-033**: El sistema MUST priorizar, en los paquetes de contexto, las unidades con cobertura de ítems
  obligatorios y autoridad oficial.
- **FR-034**: El sistema MUST excluir datos personales sensibles y contenido privado; solo admite información
  corporativa pública.

### Key Entities *(include if feature involves data)*

- **Unidad de conocimiento**: afirmación o pasaje consolidado sobre Manuelita; atributos: identificador, tema,
  texto, tipo, confianza, estado (vigente, histórica, disputada, ambigua), evidencia y fechas.
- **Tema**: agrupación navegable del conocimiento; atributos: identificador, nombre, descripción, ítems de
  cobertura, orden y estado.
- **Entidad**: persona, empresa, filial, marca, producto, sede o certificación; atributos: identificador,
  nombre canónico, alias, tipo y evidencia.
- **Evidencia**: vínculo entre una unidad y un fragmento de plata; atributos: fragmento, documento, URL,
  autoridad, fecha de captura, sección y página/tiempo.
- **Conflicto**: contradicción entre evidencias; atributos: sujeto, atributo, valores, fuentes, fechas,
  preferencia y estado.
- **Ítem de cobertura**: cada uno de los 24 requisitos; atributos: estado, unidades, autoridad, razón de vacío y
  recomendación.
- **Paquete de contexto**: selección acotada por tokens para una tarea; atributos: tarea, presupuesto, tokens,
  unidades incluidas, citas y omisiones.
- **Pregunta semilla**: pregunta candidata para FAQ; atributos: texto, tema, evidencia y estado.
- **Manifiesto oro**: inventario de salidas; atributos: hashes, conteos, configuración y fecha.
- **Reporte de calidad**: resumen verificable de la ejecución; atributos: conteos, cobertura, conflictos,
  tokens, duración y fallos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los 404 documentos canónicos de la plata se evalúa y queda con al menos una unidad,
  una razón de omisión o un estado de revisión.
- **SC-002**: La base contiene al menos 300 unidades de conocimiento y al menos 12 temas navegables.
- **SC-003**: El 100% de las unidades publicadas tiene al menos una evidencia y linaje completo hasta una URL
  pública; una auditoría de 100 unidades no encuentra campos faltantes.
- **SC-004**: En una muestra aleatoria de 100 unidades, el 100% de las afirmaciones está respaldado por el
  texto citado; no se detectan afirmaciones inventadas.
- **SC-005**: Los 24 ítems de información reportan estado, evidencia o razón de vacío; ningún ítem queda sin
  evaluar.
- **SC-006**: Cada paquete de contexto respeta su presupuesto de tokens, incluye citas en el 100% de sus
  bloques y no repite unidades.
- **SC-007**: El 100% de los conflictos detectados queda registrado con al menos dos evidencias y su estado de
  resolución.
- **SC-008**: Una segunda ejecución sin cambios en la plata produce archivos idénticos y cero unidades nuevas.
- **SC-009**: La regeneración completa desde la plata termina en 10 minutos o menos en el equipo de referencia
  y no requiere red.
- **SC-010**: Menos del 5% de las unidades publicadas resulta duplicada en una muestra de 100.
- **SC-011**: Una muestra de 50 unidades se rastrea hasta su URL pública en menos de dos minutos.
- **SC-012**: El reporte de calidad se genera automáticamente y permite reconstruir conteos, cobertura,
  conflictos y tokens sin revisar archivos manualmente.
- **SC-013**: Los hashes de los artefactos de bronce y plata son idénticos antes y después de la ejecución.
- **SC-014**: El contenido en inglés se conserva en su idioma y se asocia a un tema; no se traduce en esta
  etapa.
- **SC-015**: Al menos el 80% de los ítems cubiertos por la plata queda cubierto por al menos una unidad
  verificable en la matriz oro.

## Assumptions

- **Alcance de fase**: esta especificación cubre la consolidación de la plata en una base de conocimiento
  citable y en paquetes de contexto. La generación de resúmenes, FAQ y respuestas con LangChain, la app
  Streamlit y la evaluación de 20 preguntas pertenecen al Módulo 1.
- **Entrada**: se parte de 404 documentos canónicos y 3.810 fragmentos de la plata; los 92 alias no se indexan.
- **Sin LLM**: la capa oro es determinista y extractiva; no resume, no responde, no traduce y no genera
  embeddings.
- **Taxonomía**: los 24 ítems de información son la base de la taxonomía, complementados con entidades y temas
  propios de Manuelita.
- **Unidades**: una unidad puede ser una afirmación breve o un pasaje extractivo; no se inventan tripletas si
  el texto no las respalda.
- **Conflictos**: se conservan y se marcan; no se promedian cifras ni se elige una versión sin evidencia.
- **Paquetes de contexto**: presupuestos iniciales de 8.000 y 32.000 tokens, usando el mismo proxy de tokens
  de la capa plata; se recalibrarán con el modelo del Módulo 1.
- **Cobertura**: se mide por evidencia verificable, no por palabras clave; un ítem sin unidad se declara
  faltante.
- **Idioma**: el contenido principal está en español; el inglés se conserva y se asocia al mismo tema.
- **Licencia**: cada unidad conserva la atribución y la nota de uso académico de su fuente.
- **Datos no versionados**: las salidas viven en `data/gold/` y se regeneran desde la plata.
- **Dependencia de calidad**: si un fragmento de plata es ambiguo o incompleto, la unidad oro hereda la
  limitación y la declara; no se corrige la plata en esta etapa.

## Out of Scope

- Generación de resúmenes, FAQ o respuestas con un modelo de lenguaje.
- Embeddings, base vectorial, recuperación semántica y memoria conversacional.
- Interfaz Streamlit/Gradio.
- Traducción automática.
- OCR de PDF escaneados o descifrado de PDF protegidos.
- Evaluación de las 20 preguntas y redacción del informe del Módulo 1.
