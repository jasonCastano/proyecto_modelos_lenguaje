# Feature Specification: Verificación y ajuste del panel de Métricas

**Feature Branch**: `010-metrics-panel-layout`

**Created**: 2026-10-31

**Status**: Draft

**Input**: User description: "verifica que en la interfaz desplegada por app.py, todos los elementos y textos en la ventana de 'Métricas' se visualicen de forma adecuada y no se sobrepongan"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Lectura completa de métricas en escritorio (Priority: P1)

Una persona que evalúa el proyecto abre la pestaña **Métricas** en un portátil o monitor de escritorio, con la barra lateral visible, y recorre las tarjetas, los gráficos, las notas y la explicación de las capas sin encontrar textos encimados, valores cortados ni bloques que se salgan del área de contenido.

**Why this priority**: Es el escenario principal de la demo y de la revisión académica. Si las cifras del corpus no se leen con claridad, se pierde la evidencia del trabajo de datos.

**Independent Test**: Abrir la pestaña **Métricas** en una ventana de escritorio y comprobar que las ocho tarjetas, los dos gráficos, las leyendas, los textos de ejecución y los tres bloques desplegables se ven completos, en orden y sin solaparse.

**Acceptance Scenarios**:

1. **Given** una ventana de 1440×900 con la barra lateral abierta, **When** la persona abre **Métricas**, **Then** las ocho tarjetas de indicadores se muestran en dos filas legibles, sin que sus etiquetas o valores invadan tarjetas vecinas.
2. **Given** la misma ventana, **When** la persona desplaza la pestaña hacia abajo, **Then** los gráficos, sus leyendas y los bloques de arquitectura aparecen separados por espacios consistentes y sin superposición.
3. **Given** una ventana de 1920×1080, **When** la persona recorre **Métricas**, **Then** todo el contenido permanece dentro del área visible y no aparece desplazamiento horizontal.

---

### User Story 2 - Reorganización en ventanas estrechas (Priority: P2)

Una persona abre la aplicación en una ventana reducida o en una tableta y necesita leer las mismas métricas sin que las tarjetas se aplasten ni los textos se monten unos sobre otros.

**Why this priority**: La app debe poder mostrarse en el proyector, en una videollamada o en una pantalla pequeña sin perder legibilidad.

**Independent Test**: Reducir la ventana a 1024×768, 768×1024 y 390×844, abrir **Métricas** y verificar que el contenido se reorganiza en menos columnas, que las etiquetas se ajustan y que no aparece desplazamiento horizontal.

**Acceptance Scenarios**:

1. **Given** una ventana de 1024×768, **When** la persona abre **Métricas**, **Then** las tarjetas se distribuyen en dos columnas como máximo y todos los valores siguen siendo legibles.
2. **Given** una ventana de 390×844, **When** la persona abre **Métricas**, **Then** las tarjetas se apilan en una sola columna, los gráficos ocupan el ancho disponible y no hay contenido cortado.
3. **Given** una tableta en orientación vertical, **When** la persona recorre **Métricas**, **Then** el orden de lectura se mantiene: indicadores, volumen, tokens, arquitectura y detalles.

---

### User Story 3 - Legibilidad con contenido y zoom extremos (Priority: P3)

Una persona usa el zoom del navegador, aumenta el tamaño de fuente o consulta valores largos como millones de tokens, identificadores de ejecución y textos de estado, y aun así puede leer cada elemento sin recortes ni superposiciones.

**Why this priority**: Los valores del corpus son grandes y los estados pueden cambiar; la interfaz debe resistir contenido real, no solo una maqueta con cifras cortas.

**Independent Test**: Aplicar zoom de 150 % y 200 %, revisar valores de siete o más dígitos, ejecutar la app con datos incompletos y comprobar que ningún texto se corta, se encima o queda fuera de su bloque.

**Acceptance Scenarios**:

1. **Given** un zoom de 200 % en una ventana de 1366×768, **When** la persona abre **Métricas**, **Then** las tarjetas y los gráficos se reorganizan y todos los textos siguen siendo legibles mediante desplazamiento vertical.
2. **Given** valores como 1.447.841 tokens y un identificador de ejecución largo, **When** se muestran en una tarjeta o leyenda, **Then** el valor completo es visible o se ajusta en varias líneas, sin puntos suspensivos que oculten cifras.
3. **Given** datos incompletos o desconocidos, **When** la persona abre **Métricas**, **Then** el aviso de datos incompletos aparece separado de las tarjetas y no tapa ni desplaza de forma incorrecta el resto del contenido.

---

### Edge Cases

- Ventana de 360 px de ancho con la barra lateral cerrada: no debe aparecer desplazamiento horizontal ni texto cortado.
- Barra lateral abierta en una ventana de 1024 px: el área de Métricas debe conservar espacio suficiente para dos columnas legibles.
- Zoom del navegador al 200 %: el contenido puede requerir desplazamiento vertical, pero no debe solaparse.
- Valores de siete o más dígitos, porcentajes de cobertura y nombres de ejecución largos: deben envolver o ajustarse sin ocultar información.
- Datos incompletos, desconocidos o con cero unidades: los estados deben ser visibles y no deben romper la cuadrícula.
- Gráficos con todos los valores en cero o con escalas muy dispares: las leyendas y los títulos deben seguir separados.
- Navegación rápida entre pestañas: el contenido de Métricas no debe conservar restos visuales de otra pestaña.
- Fuente del navegador aumentada: las etiquetas deben crecer sin invadir el bloque siguiente.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La pestaña **Métricas** MUST mostrar todos sus elementos dentro del área de contenido, sin superposiciones entre tarjetas, textos, gráficos, leyendas, avisos y bloques desplegables.
- **FR-002**: La cuadrícula de indicadores MUST reorganizarse según el ancho disponible: cuatro columnas en escritorio amplio, dos en ventanas medianas y una en ventanas estrechas.
- **FR-003**: Los valores numéricos MUST mostrarse completos; si no caben en una línea, MUST ajustarse en varias líneas antes que truncarse.
- **FR-004**: Las etiquetas de las tarjetas MUST poder ocupar varias líneas sin invadir la tarjeta contigua ni recortarse.
- **FR-005**: Los gráficos MUST conservar una altura mínima legible y mantener separación con sus títulos, leyendas y textos explicativos.
- **FR-006**: La pestaña MUST permitir desplazamiento vertical cuando el contenido exceda la altura de la ventana, sin desplazamiento horizontal en anchos de 360 px o superiores.
- **FR-007**: La barra lateral MUST poder abrirse y cerrarse sin tapar ni comprimir de forma ilegible el contenido de **Métricas**.
- **FR-008**: La interfaz MUST mantener la legibilidad con zoom del navegador entre 100 % y 200 % y con tamaños de fuente aumentados.
- **FR-009**: Los avisos de datos incompletos, desconocidos o no disponibles MUST mostrarse en un bloque propio, separado de las tarjetas y de los gráficos.
- **FR-010**: Los textos de ejecución, cobertura, tokens y arquitectura MUST mantener un orden de lectura comprensible después de cualquier reorganización.
- **FR-011**: La pestaña MUST conservar las cifras y el significado de las métricas existentes; la verificación no puede alterar datos ni cálculos.
- **FR-012**: La verificación MUST cubrir al menos seis tamaños de ventana: 360×640, 390×844, 768×1024, 1024×768, 1440×900 y 1920×1080.
- **FR-013**: La verificación MUST incluir los estados de datos completos, incompletos y desconocidos.
- **FR-014**: Los cambios de diseño MUST limitarse a la pestaña **Métricas** y no introducir regresiones visuales en **Consulta**, **Resumen** ni **FAQ**.

### Key Entities

- **Panel de Métricas**: conjunto de indicadores, gráficos, avisos y explicaciones que resume el corpus y la arquitectura medallion.
- **Elemento de métrica**: cada tarjeta, valor, etiqueta, leyenda, aviso o bloque desplegable que debe permanecer legible y separado.
- **Tamaño de ventana de verificación**: combinación de ancho, alto y zoom usada para comprobar la reorganización y la ausencia de solapamientos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En los seis tamaños de ventana definidos, el 100 % de los elementos de **Métricas** se muestra sin superposición visible.
- **SC-002**: En anchos de 360 px o superiores no aparece desplazamiento horizontal en la pestaña **Métricas**.
- **SC-003**: Las ocho tarjetas de indicadores, los dos gráficos, las tres secciones desplegables y sus leyendas son legibles al 100 % del zoom en 1024×768.
- **SC-004**: Con zoom de 200 % en 1366×768, el 100 % de los valores y etiquetas sigue siendo visible, aunque requiera desplazamiento vertical.
- **SC-005**: Ningún valor numérico de siete o más dígitos se muestra truncado, oculto o sustituido por puntos suspensivos.
- **SC-006**: La revisión visual completa de la pestaña se puede realizar en menos de 10 minutos siguiendo una lista de tamaños y estados.
- **SC-007**: Las pestañas **Consulta**, **Resumen** y **FAQ** conservan su comportamiento y no presentan regresiones visuales tras el ajuste.

## Assumptions

- El alcance se limita a la pestaña **Métricas**; el resto de la aplicación solo se revisa para detectar regresiones.
- La audiencia usa navegadores actuales de escritorio y móvil; no se exige compatibilidad con navegadores sin soporte para diseño adaptable.
- Los valores y cálculos de las métricas ya existen y son correctos; esta feature verifica presentación, no la lógica de datos.
- La identidad visual aprobada se conserva; no se rediseña la marca ni se añaden nuevos paneles.
- La verificación combina revisión visual en los tamaños definidos y comprobaciones automatizadas de estructura cuando sea posible.
- Los datos de oro pueden estar completos o incompletos según el entorno; ambos estados forman parte de la verificación.
- No se inventan capturas ni resultados: las evidencias se generan al ejecutar la app en el entorno local.
