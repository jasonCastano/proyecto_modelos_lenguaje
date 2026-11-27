# Feature Specification: Frontend profesional de Valer-IA, plataforma de agentes de Manuelita

**Feature Branch**: `031-frontend-profesional-valeria`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "usando la skill de /design-taste-frontend mejora y potencializa la interfaz gráfica de usuario. Mejora y crea un frontend profesional para Valer-IA como plataforma de agentes de Manuelita. Mantén el uso de los colores corporativos de la empresa Ingenio Manuelita, utiliza elementos visuales que estén en relación con los productos producidos por la empresa. Inspírate de la página oficial de Ingenio Manuelita https://www.manuelita.com/. Mejora el frontend que cumpla con los requerimientos del módulo 3."

## Contexto

La plataforma web de Valer-IA (specs 026 y 027) tiene cuatro áreas: **entrada** (con el video pitch de las specs
028 y 029), **agente por perfil**, **consola de planificación** y **evidencia**. Funciona y cumple los requisitos
del Módulo 3 (`docs/rubrica_modulo3.md` §7), pero se ve como una herramienta técnica. Esta feature eleva la
interfaz a un **sitio de producto profesional**: identidad propia de Valer-IA, colores corporativos de Manuelita,
elementos visuales de sus productos y la estructura cálida y clara del sitio oficial de Manuelita como
inspiración, sin perder ninguna capacidad ni garantía.

Del sitio oficial se toma la **inspiración**, no la marca:

- su estructura: entrada con un mensaje fuerte, carrusel de negocios, bloque de sostenibilidad en cuatro tarjetas,
  noticias y pie con accesos;
- su tono: frases cortas, cálidas y en primera persona del plural;
- sus negocios: caña de azúcar (azúcar, bioetanol, energía renovable, derivados), palma de aceite, frutas y
  hortalizas (uva de mesa) y acuicultura (mejillones).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Entrada que presenta la plataforma como producto (Priority: P1)

Una persona del jurado o un invitado abre la web. En segundos entiende qué es Valer-IA (la plataforma de agentes de
Manuelita), para quién es (cinco perfiles), qué la hace confiable (citas, cifras calculadas, permiso antes de
guardar) y cómo empezar. La entrada se siente como un sitio de producto profesional con la identidad y los colores
de Manuelita, no como un tablero técnico.

**Why this priority**: Es la primera impresión en la sustentación y en cualquier visita; si la entrada no comunica
el producto, el resto no se explora.

**Independent Test**: Mostrar la entrada a 5 personas durante 10 segundos y pedirles que digan qué es, para quién y
cómo se empieza: al menos 4 de 5 lo explican correctamente.

**Acceptance Scenarios**:

1. **Given** una visita nueva, **When** carga la entrada, **Then** primero ve el video pitch (saltable, como hoy) y
   luego un mensaje principal que nombra a Valer-IA, su propuesta y una acción clara para empezar.
2. **Given** la entrada, **When** la persona baja, **Then** encuentra los negocios y productos de Manuelita con
   elementos visuales propios de cada uno, los cinco perfiles con lo que pueden preguntar, las garantías de la
   plataforma y el acceso a la planificación y a la evidencia.
3. **Given** cualquier ancho de pantalla de 360 a 1920 px, **When** se recorre la entrada, **Then** no hay
   desplazamiento horizontal y todo el texto se lee.

---

### User Story 2 - Conversar con el agente en una interfaz clara (Priority: P1)

Una persona elige su perfil y conversa con Valer-IA. La conversación se lee cómoda, las fuentes de cada dato se ven
sin esfuerzo, las acciones que piden permiso son evidentes y la voz y el dictado siguen disponibles.

**Why this priority**: Es la tarea principal del producto y el centro de la demostración del Módulo 3.

**Independent Test**: Completar en la vista del agente tres tareas: elegir el perfil Cliente B2B, preguntar por
certificaciones y abrir la fuente de un dato. Una persona nueva las completa en menos de 2 minutos sin ayuda.

**Acceptance Scenarios**:

1. **Given** la vista del agente, **When** la persona elige un perfil, **Then** ve con quién habla y qué puede
   preguntar, con el color y el elemento visual de ese perfil.
2. **Given** una respuesta con citas, **When** se muestra, **Then** cada cita se distingue y se abre la fuente en un
   paso.
3. **Given** una acción que requiere permiso («SÍ»), **When** el agente la propone, **Then** la tarjeta de
   aprobación se distingue del resto de la conversación y explica qué pasará.

---

### User Story 3 - Consola de planificación y evidencia con el mismo nivel profesional (Priority: P2)

El perfil planificador y el jurado usan la consola de planificación (reparto de la caña entre azúcar, etanol y
energía) y la vista de evidencia (herramientas, traza, servicios y evaluaciones). Ambas comparten la identidad
nueva y presentan las cifras con claridad.

**Why this priority**: Son el respaldo técnico de la sustentación; ya funcionan, pero deben verse coherentes con el
resto.

**Independent Test**: Ejecutar el escenario «caña −15 %» en la consola y abrir la traza del turno en evidencia: las
cifras, la restricción que limita y la alternativa se leen sin desplazamiento horizontal en un teléfono de 360 px.

**Acceptance Scenarios**:

1. **Given** la consola de planificación, **When** se ejecuta un escenario, **Then** el reparto de la caña, los
   compromisos y la restricción que limita se muestran con el color fijo de cada producto y cifras alineadas.
2. **Given** la vista de evidencia, **When** se abre, **Then** el catálogo de herramientas, la traza y los servicios
   se leen con la misma tipografía y jerarquía que el resto del sitio.

---

### User Story 4 - Identidad coherente con los productos de Manuelita (Priority: P2)

Quien navega reconoce en toda la plataforma los colores corporativos de Manuelita y elementos visuales de sus
productos (caña, azúcar, etanol, energía, palma, uva, mejillón), usados con un significado fijo, sin que la
plataforma se confunda con un canal oficial de Manuelita.

**Why this priority**: Es lo que pidió el integrante y lo que diferencia el producto; depende de US1–US3.

**Independent Test**: Revisar las cuatro áreas: cada producto usa siempre el mismo color y pictograma, y en ninguna
aparece el logotipo de Manuelita ni una frase que la presente como sitio oficial.

**Acceptance Scenarios**:

1. **Given** cualquier área, **When** se muestra un producto, **Then** usa su color y su elemento visual propios,
   iguales en todas las áreas.
2. **Given** cualquier área, **When** se revisa, **Then** está visible que Valer-IA es un proyecto académico con IA y
   no un canal oficial de Manuelita.

---

### Edge Cases

- La persona tiene activado «reducir movimiento»: no hay animaciones automáticas; el video pitch sigue la regla
  actual (sin reproducción automática con movimiento reducido).
- La API o el modelo no responden: la entrada y la evidencia siguen visibles y el agente muestra un aviso claro del
  modo degradado, como hoy.
- Un dato o una imagen no carga: el espacio no se rompe y queda un texto alternativo.
- Pantallas de 360 px y de 1920 px, zoom del navegador al 200 % y navegación solo con teclado.
- Tema oscuro del sistema: el sitio lo respeta si el plan lo hace viable sin perder contraste; si no, fija el tema
  claro y lo documenta (ver supuestos).
- Una fotografía externa no tiene licencia de uso libre, no permite uso sin atribución clara o muestra la marca de
  Manuelita: no se usa.
- Una fotografía pesa demasiado para cargar rápido: se sirve reducida y en un formato ligero.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La plataforma MUST conservar todas las capacidades actuales: las cuatro áreas, el video pitch como
  primer elemento (saltable, sin repetirse en la sesión), los cinco perfiles de libre elección en la web, voz y
  dictado, citas con fuente, aprobación con «SÍ», consola de planificación con cifras del optimizador, evidencia
  con catálogo, traza y servicios, y el modo degradado.
- **FR-002**: El rediseño MUST cubrir las **cuatro áreas** en esta feature: entrada, agente, planificación y
  evidencia (decisión del integrante, 2026-11-27).
- **FR-003**: La interfaz MUST usar los colores corporativos de Manuelita (verde, rojo anaranjado, naranja y
  amarillo del logotipo, más los colores de producto ya fijados en la plataforma) con un significado fijo por
  producto, y contraste AA en todo texto.
- **FR-004**: La interfaz MUST incluir elementos visuales de los productos de Manuelita (caña, azúcar, bioetanol,
  energía, palma, uva de mesa, mejillón) propios del proyecto, usados de forma coherente en todas las áreas.
- **FR-005**: Las imágenes de la plataforma MUST combinar ilustraciones y pictogramas propios, la presentadora
  sintética y **fotografías de stock con licencia libre** (campos de caña, productos y negocios), cada una con su
  autor, fuente y licencia registrados y citados (decisión del integrante, 2026-11-27). No se usan fotografías ni
  piezas del sitio oficial de Manuelita, ni fotos donde se vea su marca o personas identificables sin licencia de
  modelo.
- **FR-006**: La entrada MUST presentar, en este orden aproximado y con el tono cálido del sitio oficial: video
  pitch, mensaje principal con acción para empezar, negocios y productos, perfiles, garantías, planificación y
  evidencia, y un pie con accesos y la declaración de proyecto académico.
- **FR-007**: La plataforma MUST NOT mostrar el logotipo de Manuelita ni presentarse como su sitio o canal oficial;
  la declaración de IA y proyecto académico MUST seguir visible junto al video y en el pie (constitución §3.7 y §10).
- **FR-008**: La interfaz MUST funcionar de 360 a 1920 px sin desplazamiento horizontal, con navegación por teclado,
  foco visible, textos alternativos y respeto por «reducir movimiento».
- **FR-009**: Las cifras de planta MUST seguir saliendo del optimizador; la interfaz solo las presenta.
- **FR-010**: El movimiento MUST limitarse a una entrada orquestada en la página principal, un único momento
  animado dentro de su propia sección y respuestas a las acciones de la persona; sin animaciones decorativas
  repetidas ni apariciones al hacer scroll fuera de ese momento (plan, research R8).
- **FR-011**: La experiencia MUST seguir pasando las pruebas de interfaz y de extremo a extremo actuales, ajustadas
  al nuevo diseño donde cambien textos o estructura.

### Key Entities

- **Área**: entrada, agente, planificación y evidencia; cada una con su propósito y su navegación.
- **Producto de Manuelita**: nombre, negocio al que pertenece, color fijo y elemento visual propio.
- **Perfil**: nombre, para quién es, qué puede preguntar, ejemplo, color y elemento visual (ya definidos en la
  plataforma).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Al menos 4 de 5 personas nuevas explican qué es Valer-IA, para quién es y cómo empezar tras ver la
  entrada 10 segundos.
- **SC-002**: Una persona nueva elige un perfil, hace una pregunta y abre la fuente de un dato en menos de 2 minutos
  sin ayuda.
- **SC-003**: El 100 % del texto cumple contraste AA y no hay desplazamiento horizontal de 360 a 1920 px en las
  cuatro áreas.
- **SC-004**: La entrada muestra su contenido principal en menos de 2,5 s en un portátil de la sustentación con la
  app local.
- **SC-005**: El 100 % de las capacidades listadas en FR-001 siguen funcionando (pruebas de interfaz y de extremo a
  extremo en verde).
- **SC-007**: El 100 % de las fotografías de stock tiene autor, fuente y licencia libre registrados y citados.
- **SC-006**: En una revisión de las cuatro áreas, 0 apariciones del logotipo de Manuelita y la declaración de
  proyecto académico visible en la entrada y el pie.

## Assumptions

- **Skill**: el diseño se hace con la skill `design-taste-frontend` (pedida por el integrante), con su guía para
  sitios de producto; donde contradiga la constitución (por ejemplo, fotografías reales de la empresa), manda la
  constitución.
- **Colores**: los del logotipo medidos en la spec 030 (rojo anaranjado `#d64729`, verde `#497536`, amarillo
  `#ffd100`, naranja `#f39200`) se suman a la paleta de producto de la spec 026; el valor exacto de cada token se
  fija en el plan.
- **Fotografías**: de bancos con licencia libre y uso comercial y sin atribución obligatoria o con atribución
  simple (por ejemplo Unsplash, Pexels o Wikimedia Commons con CC0 o CC BY); el banco y la lista concreta se fijan
  en el plan. Se descargan una vez, se reducen y se versionan con su ficha.
- **Sitio oficial**: se consultó el 2026-11-27 para estructura, tono y lista de negocios; no se copian textos largos,
  imágenes, logotipo ni tipografía.
- **Alcance técnico**: cambia la capa de presentación de la web; la API, el agente, el optimizador y los datos no
  cambian.
- **Tema oscuro**: valor por defecto, respetar la preferencia del sistema si el plan lo considera viable; si no,
  tema claro fijo documentado.
- La rama parte de `main` (ya incluye los videos de las specs 028 y 029); es independiente del PR #86 (spec 030).
