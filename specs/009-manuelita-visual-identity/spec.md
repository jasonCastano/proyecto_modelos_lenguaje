# Feature Specification: Identidad visual Manuelita para la app Q&A

**Feature Branch**: `009-manuelita-visual-identity`

**Created**: 2026-10-30

**Status**: Draft

**Input**: User description: "Adapta la interfaz de mi aplicación Streamlit utilizando una identidad visual inspirada en la página web de Grupo Empresarial Manuelita (https://www.manuelita.com/)"

**Contexto**: la aplicación del Módulo 1 (spec `008-streamlit-qa-app`) ya expone Resumen, FAQ, Q&A y un
panel de métricas. Hoy su apariencia es la de un panel genérico: no comunica de qué organización habla ni
se reconoce como parte del trabajo sobre Manuelita. Esta especificación define **cómo debe verse y
sentirse** esa interfaz tomando como referencia la identidad pública de Grupo Manuelita, sin alterar la
funcionalidad existente ni el contenido de las respuestas.

## Identidad visual de referencia (evidencia)

La referencia es el sitio público https://www.manuelita.com/ y su logotipo oficial
(`wp-content/uploads/2016/10/logo.svg`), consultados el 2026-10-30. De ahí se extrae:

- **Paleta institucional**: verde bosque `#387C2B`, naranja `#E86D1F`, verde lima `#B0BC22`, amarillo
  `#FFD200`, naranja claro `#F6A01A` y blanco.
- **Tono**: agroindustrial, sobrio y optimista; mensajes sobre progreso, bienestar, sostenibilidad y 160
  años de historia.
- **Jerarquía visual**: logotipo a la izquierda, navegación horizontal limpia, titulares en mayúsculas
  cortas, bloques de contenido con mucho aire y fotografías de campo.

El manual de marca oficial no es público (requiere inicio de sesión), por lo que esta especificación se
limita a lo observable en el sitio y el logotipo.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Reconocer la marca al abrir la app (Priority: P1)

Un evaluador abre la aplicación y, sin leer con detalle, reconoce que se trata de un trabajo sobre Grupo
Manuelita: ve el nombre, el logotipo o firma visual y los colores institucionales en la cabecera y en la
primera pantalla.

**Why this priority**: es el objetivo central del pedido. Sin reconocimiento de marca, el resto de mejoras
visuales no cumple su propósito en la demo ni en la sustentación.

**Independent Test**: abrir la app en una ventana nueva, mostrar la pantalla inicial a tres personas
ajenas al proyecto y comprobar que identifican la organización de la que trata antes de leer el cuerpo.

**Acceptance Scenarios**:

1. **Given** la app recién abierta, **When** el usuario ve la cabecera, **Then** aparecen el nombre del
   proyecto, la referencia a Grupo Manuelita y la firma visual institucional.
2. **Given** la pantalla inicial, **When** un observador la mira durante cinco segundos, **Then** al menos
   dos de tres observadores mencionan a Manuelita o el sector agroindustrial.
3. **Given** una conexión a internet ausente, **When** el usuario abre la app, **Then** la cabecera y la
   firma visual se muestran igual.

---

### User Story 2 - Leer las respuestas con una jerarquía clara (Priority: P2)

Un usuario formula una pregunta y lee la respuesta sin esfuerzo: distingue de un vistazo el titular, el
cuerpo, las citas y los metadatos, con contraste suficiente y sin elementos que compitan por su atención.

**Why this priority**: una identidad visual solo aporta si mejora la lectura. La app se usa para leer
respuestas con fuentes, no para contemplar un logotipo.

**Independent Test**: leer tres respuestas reales en una pantalla de 1440 px y en una de 360 px de ancho,
y verificar que se distinguen título, cuerpo, citas y metadatos sin hacer zoom ni scroll horizontal.

**Acceptance Scenarios**:

1. **Given** una respuesta generada, **When** se muestra, **Then** el texto de la respuesta tiene mayor
   peso visual que sus metadatos y que el panel.
2. **Given** texto normal sobre fondo institucional, **When** se mide el contraste, **Then** cumple la
   relación mínima de accesibilidad definida en los requisitos.
3. **Given** una ventana de 360 px de ancho, **When** el usuario recorre la app, **Then** no aparece scroll
   horizontal y los textos siguen siendo legibles.

---

### User Story 3 - Distinguir una fuente citada de un enlace cualquiera (Priority: P3)

Un lector revisa las fuentes de una respuesta y reconoce cada cita como una tarjeta de fuente: etiqueta,
título del documento, sección y enlace verificable, con el mismo tratamiento visual en las tres pestañas.

**Why this priority**: la trazabilidad es el argumento académico del proyecto; la identidad visual debe
reforzarla, no decorarla.

**Independent Test**: generar una respuesta con al menos dos citas y comprobar que cada una muestra
etiqueta, título, ubicación y enlace, y que el enlace es accesible con teclado.

**Acceptance Scenarios**:

1. **Given** una respuesta con citas, **When** el usuario las revisa, **Then** cada cita muestra su
   etiqueta, el título del documento y su ubicación (sección, página o marca temporal).
2. **Given** una cita con enlace, **When** el usuario navega con teclado, **Then** el foco es visible y el
   enlace se abre en una pestaña nueva sin perder la app.
3. **Given** una URL muy larga, **When** se muestra la cita, **Then** el enlace sigue siendo legible y no
   rompe el ancho de la tarjeta.

---

### User Story 4 - Entender los estados sin depender del color (Priority: P4)

Un usuario ve resultados en fallback, advertencias de revisión, errores de modelo y el modo de
demostración, y comprende cada estado por su texto e icono, no solo por su color.

**Why this priority**: la app ya comunica estados críticos; aplicar la marca no puede degradar esa
claridad ni excluir a personas con daltonismo.

**Independent Test**: activar el modo de demostración, forzar un fallback y un error controlado, y
verificar que cada estado se entiende con el color desaturado.

**Acceptance Scenarios**:

1. **Given** un resultado en fallback, **When** se muestra, **Then** el mensaje se lee como información y
   no como error, con texto e icono propios.
2. **Given** un error controlado, **When** se muestra, **Then** incluye un mensaje accionable y un
   indicador visual distinto del fallback.
3. **Given** el modo de demostración activo, **When** el usuario recorre la app, **Then** un distintivo
   visible lo indica en todo momento.

---

### User Story 5 - Saber que es un trabajo académico (Priority: P5)

Un visitante entiende que la app es un proyecto académico construido con información pública y que no es
un canal oficial de la empresa.

**Why this priority**: usar la identidad de una organización real exige evitar cualquier apariencia de
afiliación o respaldo oficial.

**Independent Test**: abrir la app y localizar, sin buscar en documentación externa, la nota de proyecto
académico y la atribución de la marca.

**Acceptance Scenarios**:

1. **Given** la app abierta, **When** el usuario llega al pie de página, **Then** lee que es un proyecto
   académico no afiliado a Grupo Manuelita.
2. **Given** la identidad visual aplicada, **When** se revisa la app, **Then** en ningún lugar se afirma
   respaldo, patrocinio o afiliación oficial.

---

### Edge Cases

- El logotipo o la firma visual no están disponibles en el equipo: se usa una firma tipográfica con el
  nombre, sin íconos rotos ni espacios vacíos.
- La app se abre sin conexión: la identidad se compone solo con recursos locales y colores.
- El usuario tiene el tema oscuro del sistema: los textos y componentes mantienen contraste suficiente.
- Una respuesta o un título de documento es muy largo: se ajusta en varias líneas sin desbordar la tarjeta.
- La paleta institucional se usa sobre fondos claros y oscuros: ningún par texto/fondo incumple el
  contraste mínimo.
- El usuario navega solo con teclado: todos los controles y enlaces muestran foco visible.
- Una cita apunta a un documento sin sección ni página: la tarjeta lo declara en lugar de dejar el campo
  vacío.
- El modo de demostración y un error ocurren a la vez: ambos estados son visibles y no se tapan entre sí.
- La app se proyecta en un videobeam con colores lavados: la jerarquía sigue siendo legible.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La app MUST mostrar en su cabecera el nombre del proyecto, la referencia a Grupo Manuelita y
  una firma visual institucional.
- **FR-002**: La identidad visual MUST usar la paleta institucional documentada en esta especificación como
  base de color, con el verde bosque como color primario y el naranja como color de acento.
- **FR-003**: La app MUST aplicar una tipografía sans-serif con al menos cuatro niveles jerárquicos
  distinguibles: título de página, título de sección, cuerpo y metadatos.
- **FR-004**: Todo par texto/fondo de la app MUST cumplir una relación de contraste mínima de 4.5:1 para
  texto normal y 3:1 para texto grande, medida con una herramienta de contraste.
- **FR-005**: La app MUST NOT depender únicamente del color para comunicar un estado: cada estado incluye
  texto y, cuando aplique, un icono.
- **FR-006**: La app MUST mostrar el estado de datos y de modelo en la cabecera, de forma persistente y
  legible, en todas las pestañas.
- **FR-007**: Cada cita visible MUST presentarse como una tarjeta de fuente con etiqueta, título del
  documento, ubicación y enlace verificable.
- **FR-008**: Los enlaces de las citas MUST ser accesibles con teclado, mostrar foco visible y abrirse en
  una pestaña nueva.
- **FR-009**: La app MUST distinguir visualmente el fallback, la advertencia de revisión, el error
  controlado y el modo de demostración, manteniendo el significado que ya define la especificación 008.
- **FR-010**: La app MUST mostrar un distintivo permanente cuando esté activo el modo de demostración.
- **FR-011**: La app MUST incluir en el pie de página una nota de proyecto académico no afiliado a Grupo
  Manuelita y la atribución de la marca a su titular.
- **FR-012**: La app MUST NOT afirmar ni sugerir respaldo, patrocinio o afiliación oficial de la empresa.
- **FR-013**: La app MUST mantener la identidad visual sin conexión a internet, usando solo recursos
  locales y colores.
- **FR-014**: La app MUST mantener la legibilidad y evitar el scroll horizontal en ventanas de 360 px de
  ancho o más.
- **FR-015**: La app MUST conservar íntegras las funcionalidades y validaciones de la especificación 008:
  tres pestañas, panel de métricas, validación de pregunta, fallback, manejo de errores y modo de
  demostración.
- **FR-016**: La app MUST usar español como idioma de interfaz y conservar nombres propios, siglas y cifras
  sin alterarlos.
- **FR-017**: La app MUST aplicar la identidad de forma consistente en las tres pestañas y en el panel, sin
  estilos contradictorios entre secciones.
- **FR-018**: La app MUST permitir identificar la organización en la primera pantalla sin necesidad de
  desplazarse.
- **FR-019**: La app MUST NOT incorporar fotografías, videos ni tipografías licenciadas del sitio oficial;
  solo la paleta, el tratamiento tipográfico y la firma visual.
- **FR-020**: La app MUST seguir siendo importable y comprobable sin lanzar el servidor de interfaz, y su
  suite de pruebas MUST seguir en verde.

### Key Entities *(include if feature involves data)*

- **Brand Tokens**: conjunto mínimo de color, tipografía, espaciado y radios que define la apariencia y se
  aplica de forma uniforme.
- **Page Chrome**: cabecera, firma visual, estado del sistema y pie de página presentes en toda la app.
- **Source Card**: representación visual de una cita con etiqueta, título, ubicación y enlace.
- **Status Badge**: indicador textual e icónico de fallback, revisión, error o modo de demostración.
- **Brand Asset**: firma visual o logotipo utilizado, con su atribución y su alternativa tipográfica.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: El 100% de los pares texto/fondo visibles cumple la relación de contraste mínima (4.5:1 en
  texto normal, 3:1 en texto grande).
- **SC-002**: Al menos dos de cada tres observadores ajenos identifican la organización de la que trata la
  app en menos de cinco segundos, sin leer el cuerpo.
- **SC-003**: El 100% de las citas visibles presenta etiqueta, título, ubicación y enlace.
- **SC-004**: La app mantiene las 22 capacidades funcionales de la especificación 008 y su suite de pruebas
  sigue pasando.
- **SC-005**: La app no introduce dependencias de red para mostrar su identidad: funciona sin conexión.
- **SC-006**: En una ventana de 360 px de ancho no aparece scroll horizontal en ninguna pestaña.
- **SC-007**: El 100% de los estados (fallback, revisión, error, demostración) se distingue con el color
  desaturado, usando solo texto e iconos.
- **SC-008**: El tiempo de arranque de la app no aumenta en más de 2 segundos respecto de la versión
  anterior en el equipo de referencia.
- **SC-009**: Un revisor encuentra la nota de proyecto académico y la atribución de marca en menos de diez
  segundos desde que abre la app.
- **SC-010**: La app no muestra en ningún momento logotipos, fotografías ni textos que sugieran afiliación
  oficial.

## Assumptions

- La aplicación de la especificación 008 ya está implementada y funciona; esta especificación cambia su
  apariencia, no su comportamiento.
- Se usa el logotipo público y la paleta observada en el sitio oficial; el manual de marca no es público.
- No se dispone de licencia para fotografías ni tipografías del sitio, así que se sustituyen por color,
  jerarquía tipográfica y una firma visual propia.
- El uso es académico y local; la app no se publica en internet ni se presenta como canal oficial.
- La identidad se resuelve con recursos locales versionados en el repositorio.
- La evaluación de 40 preguntas y el informe siguen siendo M1-08 y M1-10.

## Out of Scope

- Cambios de funcionalidad, nuevas pestañas o nuevos modelos.
- Manual de marca, papelería, plantillas corporativas o material impreso.
- Fotografías, videos, ilustraciones o tipografías licenciadas del sitio oficial.
- Tema oscuro dedicado, internacionalización o aplicación móvil nativa.
- Despliegue público, autenticación o multiusuario.
- Rediseño de la arquitectura de datos o del pipeline.
