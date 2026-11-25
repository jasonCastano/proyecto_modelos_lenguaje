# Feature Specification: Plataforma web profesional de Valer-IA para Manuelita (idea 7) con planificación industrial

**Feature Branch**: `026-plataforma-web-manuelita`

**Created**: 2026-11-24

**Status**: Draft

**Autor**: Roberto José Guerrero

**Input**: User description: "mejora y potencializa la interfaz gráfica de usuario, no utilices más streamlit. Mejora y
crea un frontend y backend profesional para Valer-IA como plataforma de agentes de Manuelita (idea 7) con
planificación industrial. Mantén el uso de los colores corporativos de la empresa Ingenio Manuelita, utiliza elementos
visuales que estén en relación con los productos producidos por la empresa. Mejora el frontend y backend que cumpla
con los requerimientos del módulo 3."

**Contexto**: La spec 025 convirtió a Valer-IA en la **plataforma de agentes de Manuelita**: un solo agente con cinco
perfiles (visitante, cliente B2B, proveedor, colaborador y planificador industrial) y un planificador que optimiza el
destino de la caña entre azúcar, etanol y energía sobre **datos sintéticos declarados**. Ese producto existe en
WhatsApp y en el backend, pero la web sigue siendo la página de los Módulos 1 y 2: un recorrido editorial con una
consola de preguntas, donde el chat del agente es una pestaña más y la planificación solo se ve como texto dentro de
la conversación.

Streamlit ya no es la interfaz desde la spec 012 (`CONSTITUTION.md` §3.7). Esta spec confirma esa regla: **ninguna
pantalla del producto puede depender de Streamlit, Gradio o notebooks**.

Esta spec rediseña la web como la **cara profesional de la plataforma**:

- una entrada pública que explica la plataforma con la identidad de Manuelita;
- un espacio de trabajo del agente organizado por perfil;
- una **consola de planificación industrial** visual para el planificador autorizado;
- un panel de evidencia técnica para la sustentación del Módulo 3.

El backend se completa con los servicios que esas pantallas necesitan, con las mismas garantías del agente: las cifras
salen del código, la escritura pide aprobación y los datos sintéticos se declaran.

La sustentación del Módulo 3 es el **sábado 28 de noviembre de 2026**. La demo principal sigue siendo WhatsApp desde
el teléfono de un invitado; la web es el respaldo visual y el lugar donde se muestra la planificación y la evidencia
técnica en la discusión de 8 minutos.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - El planificador arma y compara un programa de producción en una consola visual (Priority: P1)

Una persona del equipo de planta, autorizada como planificadora, entra a la consola de planificación. Ve de un vistazo
el estado de la planta de la semana:

- caña disponible;
- capacidad de molienda, de la refinería, de la destilería y de cogeneración;
- inventarios;
- compromisos de azúcar, etanol y energía con su prioridad.

Plantea un escenario con controles simples (por ejemplo, «15 % menos caña» o un cambio de precio del etanol), pide la
recomendación y recibe el **plan recomendado** de forma gráfica:

- cuánta caña va a azúcar, a etanol y a energía, como un flujo desde la caña hasta los productos;
- qué compromisos se cumplen y con qué margen;
- la restricción que limita el resultado;
- una alternativa.

Puede comparar el escenario con el plan base, lado a lado, y pedirle al agente que se lo explique. Si lo aprueba,
guarda la propuesta con una confirmación explícita.

**Why this priority**: Es la demostración estrella de la idea 7 (§7.4) y hoy solo se ve como texto en un chat. Una
consola visual hace evidente, en segundos y ante el jurado, que el plan sale de un optimizador verificable y no del
modelo de lenguaje.

**Independent Test**: Con el perfil planificador habilitado en la web, cargar la consola, aplicar «15 % menos caña»,
pedir la recomendación y comprobar que el reparto, los compromisos, la restricción limitante y la alternativa
coinciden con los que da el mismo escenario por el agente y por la línea de comandos.

**Acceptance Scenarios**:

1. **Given** una persona autorizada como planificadora, **When** abre la consola, **Then** ve el estado de planta y los
   compromisos de la semana con la etiqueta «Datos sintéticos de demostración» visible en todo momento.
2. **Given** el estado de planta cargado, **When** aplica «15 % menos caña» y pide la recomendación, **Then** ve el
   reparto de caña entre azúcar, etanol y energía, el cumplimiento de cada compromiso, la restricción limitante y una
   alternativa, en menos de 5 segundos.
3. **Given** un escenario sin solución factible, **When** pide la recomendación, **Then** la consola lo dice en
   palabras claras, muestra el faltante de cada compromiso por prioridad y no presenta ningún plan como factible.
4. **Given** un plan recomendado, **When** la persona pide «Explicar con el agente», **Then** el agente responde en el
   espacio de conversación con las mismas cifras que muestra la consola.
5. **Given** un plan recomendado, **When** la persona pulsa «Guardar propuesta», **Then** la consola pide una
   confirmación explícita y solo guarda si se confirma; el aviso final dice «Propuesta guardada».
6. **Given** una persona **no** autorizada, **When** intenta abrir la consola, **Then** ve un aviso que explica que la
   planificación es solo para el equipo de planta autorizado, sin datos de planta.

---

### User Story 2 - Cada público entra a su agente desde una plataforma con la identidad de Manuelita (Priority: P1)

Un visitante llega a la web y entiende en pocos segundos qué es Valer-IA: un agente para los públicos de Manuelita.
Elige su perfil (visitante, cliente B2B, proveedor o colaborador; planificador si está autorizado) con una tarjeta que
dice qué puede hacer cada uno, y entra al espacio de trabajo del agente:

- la conversación;
- las fuentes citadas;
- sugerencias propias del perfil;
- su memoria (qué recuerda el agente y cómo borrarlo);
- las acciones que piden aprobación.

Puede cambiar de perfil sin perder la conversación. Las funciones de los Módulos 1 y 2 (consulta, resumen, preguntas
frecuentes, voz y dictado) siguen disponibles dentro de la plataforma.

**Why this priority**: Es la cara de la plataforma para el pitch (minutos 1:00–4:00) y el respaldo si WhatsApp falla.
Sin ella, la web contradice el producto que se presenta.

**Independent Test**: Abrir la web en un navegador limpio, elegir «Cliente B2B», preguntar por certificaciones y
comprobar respuesta citada, sugerencias del perfil y chip de perfil visible. Luego cambiar a «Proveedor» en el mismo
hilo y verificar que el foco cambia.

**Acceptance Scenarios**:

1. **Given** un visitante nuevo, **When** entra a la web, **Then** la primera pantalla presenta la plataforma, los
   perfiles disponibles y la declaración de que es un proyecto académico, no un canal oficial de Manuelita.
2. **Given** el selector de perfiles, **When** el visitante elige «Cliente B2B», **Then** el espacio de trabajo muestra
   el perfil activo, sugerencias de ese perfil y solo las capacidades que ese perfil permite.
3. **Given** una conversación en curso, **When** el visitante cambia de perfil, **Then** la conversación se conserva y
   el siguiente turno usa el nuevo perfil.
4. **Given** una respuesta con fuentes, **When** se muestra, **Then** cada cita se puede abrir y lleva a su fuente.
5. **Given** una acción que escribe (por ejemplo, pedir un asesor o recordar el perfil), **When** el agente la propone,
   **Then** aparece una tarjeta de aprobación con «Sí» y «No», y nada se guarda sin «Sí».
6. **Given** que la voz o el dictado no están disponibles, **When** el visitante usa la plataforma, **Then** la
   conversación funciona igual por texto y se le dice por qué no hay voz.

---

### User Story 3 - El equipo muestra la evidencia técnica del Módulo 3 desde la web (Priority: P2)

En la discusión técnica de 8 minutos, un integrante del equipo abre el panel de evidencia y muestra, sin abrir la
terminal:

- el catálogo de 26 herramientas con su tipo (lectura o escritura con aprobación) y los perfiles que las usan;
- la traza del último turno: ruta, plan de pasos, herramientas llamadas, duración y resultado;
- el estado de los servicios: modelo, base vectorial, canal WhatsApp y gateway;
- las evaluaciones publicadas con su cifra honesta;
- la memoria de un usuario de prueba.

**Why this priority**: Varios ítems de la rúbrica (1.1, 1.2, 1.3, 3.2, 4.2) se demuestran mejor viendo la traza y el
catálogo. Es importante, pero la demo funciona sin este panel usando `/traza` y la terminal.

**Independent Test**: Hacer una pregunta en el espacio de trabajo, abrir el panel de evidencia y comprobar que la
traza del turno, el catálogo de 26 herramientas y el estado de servicios se ven y coinciden con lo que reporta la
línea de comandos.

**Acceptance Scenarios**:

1. **Given** un turno ya respondido, **When** se abre la traza, **Then** se ven la ruta, los pasos del plan y cada
   herramienta con sus argumentos validados, su duración y si tuvo éxito.
2. **Given** el panel de evidencia, **When** se abre el catálogo, **Then** lista 26 herramientas, marca las de
   escritura con aprobación y las que no están disponibles en modo degradado.
3. **Given** que un servicio externo no responde (modelo, base vectorial o gateway), **When** se abre el estado,
   **Then** ese servicio aparece como no disponible, con la razón y qué hacer.
4. **Given** las evaluaciones publicadas, **When** se abren, **Then** muestran la cifra vigente con su fecha y el
   enlace al informe, incluidas las que no alcanzan la meta.

---

### User Story 4 - La plataforma se ve y se usa bien en cualquier pantalla (Priority: P2)

Un invitado abre la web en su teléfono, un profesor la proyecta en un salón y un integrante la usa en un portátil. En
todos los casos:

- el contenido se lee sin desplazamiento horizontal;
- los controles se pueden operar con teclado y con lector de pantalla;
- el contraste cumple el mínimo de accesibilidad;
- la consola de planificación sigue siendo legible en una pantalla de teléfono.

**Why this priority**: La demo se hace en teléfonos y proyectores ajenos al equipo; un fallo visual en vivo cuesta
puntos de sustentación.

**Independent Test**: Recorrer los flujos de las historias 1 y 2 en anchos de 360 px, 768 px y 1440 px, solo con
teclado, y con la preferencia de movimiento reducido activada.

**Acceptance Scenarios**:

1. **Given** una pantalla de 360 px de ancho, **When** se recorre la plataforma, **Then** no hay desplazamiento
   horizontal y los gráficos del plan se reorganizan en vertical.
2. **Given** navegación solo con teclado, **When** se recorren los flujos principales, **Then** todos los controles
   tienen foco visible y orden lógico.
3. **Given** la preferencia de movimiento reducido, **When** se carga la plataforma, **Then** no hay animaciones que no
   respondan a una acción de la persona.

---

### Edge Cases

- El backend no responde al cargar la web: la entrada pública se muestra igual, el espacio de trabajo dice que el
  agente no está disponible y ofrece el modo demostración.
- Falta la clave del modelo: la plataforma funciona en modo demostración, marcado de forma explícita.
- El planificador pide un escenario fuera de rango (por ejemplo, más de 100 % de reducción de caña o un precio
  negativo): la consola lo rechaza antes de calcular y dice el rango válido.
- La consola y el agente dan cifras distintas para el mismo escenario: no debe pasar; si el validador de cifras falla,
  se muestra el plan calculado, como en la spec 025.
- Una persona cambia a «planificador» sin estar autorizada: el cambio se rechaza con un aviso, sin revelar datos de
  planta.
- La respuesta del agente tarda más de lo esperado: la interfaz muestra el progreso del turno y permite seguir leyendo
  lo anterior.
- El usuario rechaza una aprobación («No»): la interfaz lo confirma y no queda nada guardado.
- Se abre un enlace directo a la consola o al panel de evidencia: la pantalla correspondiente carga sin pasar por la
  entrada, con las mismas reglas de acceso.
- Los datos sintéticos de planta no están disponibles: la consola dice cómo regenerarlos y no muestra cifras vacías
  como si fueran ceros.

## Requirements *(mandatory)*

### Functional Requirements

**Plataforma e identidad**

- **FR-001**: La web DEBE presentarse como «Valer-IA, la plataforma de agentes de Manuelita» y organizarse en cuatro
  áreas navegables: entrada pública, espacio de trabajo del agente, consola de planificación y panel de evidencia
  técnica.
- **FR-002**: Ninguna pantalla del producto DEBE depender de Streamlit, Gradio ni notebooks.
- **FR-003**: La identidad visual DEBE usar la paleta corporativa de Manuelita ya verificada en el repositorio:
  - verde bosque `#387C2B`;
  - naranja `#E86D1F`;
  - verde lima `#B0BC22`;
  - amarillo `#FFD200`;
  - naranja claro `#F6A01A`.

  Con esa paleta, todo texto DEBE cumplir el contraste mínimo AA.
- **FR-004**: La plataforma DEBE usar elementos visuales propios de los productos de Manuelita, ligados a su
  significado y no como adorno genérico. Por ejemplo:
  - caña, azúcar, etanol y energía en la planificación;
  - palma, uvas y frutas, y camarón y mejillón en la presentación de los negocios.
- **FR-005**: Cada pantalla DEBE mostrar la declaración de proyecto académico no afiliado a Manuelita. Cada vista con
  datos de planta DEBE mostrar «Datos sintéticos de demostración» y «El agente recomienda; el equipo de planta
  decide».
- **FR-006**: Cada área DEBE tener su propia dirección web, para abrirse con un enlace directo y para que el botón
  «atrás» del navegador funcione.

**Espacio de trabajo del agente**

- **FR-007**: El espacio de trabajo DEBE permitir elegir el perfil con una descripción de lo que hace cada uno. El
  planificador DEBE ofrecerse solo a personas autorizadas.
- **FR-008**: El espacio de trabajo DEBE conservar todas las capacidades vigentes del chat:
  - respuestas citadas con fuentes que se pueden abrir;
  - aprobación humana con «Sí» y «No»;
  - memoria visible y borrable;
  - voz por oraciones y dictado;
  - hilo persistente y modo demostración.
- **FR-009**: El espacio de trabajo DEBE mostrar sugerencias propias del perfil activo y un chip con el perfil del
  turno.
- **FR-010**: Las funciones de Consulta, Resumen y FAQ con citas y respaldo (Módulo 1) DEBEN seguir disponibles dentro
  de la plataforma.

**Consola de planificación industrial**

- **FR-011**: La consola DEBE mostrar el estado de planta de la semana (caña, capacidades, inventarios) y los
  compromisos con su prioridad, tomados de los datos sintéticos declarados.
- **FR-012**: La consola DEBE permitir definir un escenario con controles acotados y validados:
  - variación de caña disponible;
  - calidad de la caña;
  - precios de azúcar, etanol y energía;
  - límite de vapor de las calderas;
  - prioridad entre margen y energía.

  Los valores fuera de rango DEBEN rechazarse antes de calcular, diciendo el rango válido.
- **FR-013**: La consola DEBE presentar el plan recomendado de forma gráfica:
  - el reparto de caña entre azúcar, etanol y energía;
  - el cumplimiento de cada compromiso;
  - la restricción limitante, con su valor marginal;
  - una alternativa;
  - los supuestos.
- **FR-014**: La consola DEBE permitir comparar el escenario con el plan base, mostrando las diferencias por producto y
  por compromiso.
- **FR-015**: Cuando no hay solución factible, la consola DEBE mostrar el faltante de cada compromiso por prioridad y
  NO DEBE presentar ningún plan como factible ni relajar capacidades físicas.
- **FR-016**: Las cifras de la consola DEBEN salir del mismo simulador y optimizador que usa el agente. Para el mismo
  escenario, consola, agente y línea de comandos DEBEN dar las mismas cifras.
- **FR-017**: La consola DEBE permitir pedir al agente que explique el plan, en el mismo hilo de conversación.
- **FR-018**: Guardar una propuesta de producción DEBE exigir una confirmación explícita y quedar registrado con fecha,
  escenario y plan, igual que la acción de escritura de la spec 025.
- **FR-019**: El acceso a la consola y a sus servicios DEBE respetar la autorización del planificador de la spec 025.
  Una persona no autorizada NO DEBE recibir datos de planta por ninguna vía, incluida la llamada directa al backend.

**Panel de evidencia técnica**

- **FR-020**: El panel DEBE mostrar el catálogo de herramientas: nombre, descripción, lectura o escritura con
  aprobación, perfiles que la usan y disponibilidad en modo degradado.
- **FR-021**: El panel DEBE mostrar la traza del último turno o de un turno elegido: ruta, plan de pasos, herramientas
  con argumentos validados, duración y resultado.
- **FR-022**: El panel DEBE mostrar el estado de los servicios (modelo, base vectorial, canal WhatsApp y gateway, voz),
  cada uno con su razón y qué hacer cuando no está disponible.
- **FR-023**: El panel DEBE mostrar las evaluaciones publicadas con su cifra vigente, su fecha, su meta y el enlace al
  informe, sin ocultar las que no alcanzan la meta.
- **FR-024**: El panel NO DEBE mostrar claves, números de teléfono completos ni datos personales. Los usuarios del
  canal aparecen con su seudónimo.

**Backend profesional**

- **FR-025**: El backend DEBE exponer los servicios que necesitan las cuatro áreas, con contratos documentados y
  versionados:
  - estado de planta;
  - escenarios;
  - recomendación;
  - comparación;
  - guardado con aprobación;
  - catálogo;
  - trazas;
  - estado de servicios;
  - evaluaciones.
- **FR-026**: Todo error del backend DEBE devolver un código estable, un mensaje en español que dice qué pasó y qué
  hacer, y nunca detalles internos ni secretos.
- **FR-027**: El backend DEBE validar cada entrada contra su contrato y rechazar lo inválido antes de ejecutar
  cálculos o llamar al modelo.
- **FR-028**: El backend DEBE registrar cada llamada a servicios de planificación (quién por seudónimo, escenario,
  duración, resultado) sin datos personales.
- **FR-029**: Los servicios existentes (chat, canales, voz, memoria y herramientas) NO DEBEN cambiar de conducta. Sus
  pruebas y evaluaciones vigentes DEBEN seguir pasando.

**Calidad y Módulo 3**

- **FR-030**: La plataforma DEBE cumplir accesibilidad AA:
  - foco visible;
  - navegación por teclado;
  - textos alternativos en gráficos;
  - respeto de la preferencia de movimiento reducido.
- **FR-031**: La plataforma DEBE verse sin desplazamiento horizontal desde 360 px hasta 1920 px de ancho.
- **FR-032**: Los flujos principales de las historias 1 y 2 DEBEN tener pruebas automáticas de extremo a extremo que
  corran sin red ni claves.
- **FR-033**: La documentación DEBE actualizarse en el mismo cambio:
  - README con capturas de las cuatro áreas;
  - diagramas Archify que lo requieran;
  - ADR de la decisión de interfaz;
  - `CONSTITUTION.md` §3.7;
  - la rúbrica del Módulo 3.

### Key Entities

- **Perfil**: público al que sirve el agente (visitante, cliente B2B, proveedor, colaborador o planificador), con su
  descripción, sus capacidades y si requiere autorización. Ya existe en la spec 025.
- **Estado de planta**: foto semanal de la planta sintética: caña disponible, capacidades por área, inventarios,
  rendimientos y precios. Siempre lleva la etiqueta de datos sintéticos.
- **Compromiso**: contrato de azúcar, etanol o energía con cantidad, fecha y prioridad.
- **Escenario**: cambios que el planificador aplica sobre el estado de planta (caña, precios, capacidades), con nombre
  y fecha.
- **Plan recomendado**: resultado del optimizador para un escenario: reparto de caña, producción por producto,
  cumplimiento por compromiso, restricción limitante con su valor marginal, alternativa y supuestos. Puede ser
  factible o infactible; si es infactible, lleva los faltantes.
- **Comparación**: diferencias entre dos planes por producto y por compromiso.
- **Propuesta guardada**: plan aprobado de forma explícita, con fecha, escenario, autor por seudónimo y estado.
- **Traza de turno**: ruta, plan de pasos, herramientas llamadas con argumentos, duración y resultado de un turno.
- **Estado de servicio**: disponibilidad de cada dependencia, con razón y acción sugerida.
- **Evaluación publicada**: nombre, cifra vigente, meta, fecha e informe.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Una persona que nunca vio la plataforma explica qué es Valer-IA y para quién es tras 10 segundos en la
  entrada, en al menos 4 de 5 pruebas con personas ajenas al equipo.
- **SC-002**: El planificador obtiene una recomendación para «15 % menos caña» en menos de 3 interacciones y menos de
  5 segundos desde que la pide.
- **SC-003**: En los 12 escenarios de la batería de planificación de la spec 025, la consola y el agente coinciden en
  el 100 % de las cifras del plan.
- **SC-004**: El 100 % de los intentos de una persona no autorizada de obtener datos de planta (por la interfaz o por
  llamada directa) se rechaza.
- **SC-005**: El 100 % de las acciones de escritura iniciadas desde la web pide confirmación, y ninguna se guarda tras
  un «No».
- **SC-006**: Las pantallas de las cuatro áreas pasan una revisión automática de accesibilidad sin fallas graves y se
  ven sin desplazamiento horizontal a 360, 768 y 1440 px.
- **SC-007**: Las pruebas y evaluaciones vigentes de los Módulos 1, 2 y 3 siguen en verde, sin regresión.
- **SC-008**: En el ensayo del viernes, el bloque de planificación y el de evidencia técnica se demuestran desde la web
  en el tiempo asignado (1:30 y 1:30 minutos), sin abrir la terminal.
- **SC-009**: La página de entrada muestra su contenido principal en menos de 2 segundos en un portátil con conexión
  normal.

## Alineación con la rúbrica del Módulo 3

| Ítem | Cómo lo refuerza esta spec |
|------|----------------------------|
| 1.1 Function calling y herramientas | Catálogo de 26 herramientas visible y explicable desde el panel (FR-020) |
| 1.2 Razonamiento, plan y router | Traza con ruta y plan de pasos (FR-021); planificación visual de varios pasos (FR-013) |
| 1.3 Memoria por capas | Memoria visible y borrable en el espacio de trabajo (FR-008) |
| 3.2 WhatsApp en producción | Estado del canal y del gateway en el panel (FR-022); la web es el respaldo de la demo |
| 4.1 Código y pruebas | Contratos versionados, validación y pruebas de extremo a extremo sin red (FR-025, FR-027, FR-032) |
| 4.2 Seguridad y hardening | Autorización del planificador en interfaz y backend; aprobación humana; errores sin secretos (FR-019, FR-024, FR-026) |
| 4.3 Documentación final | README con capturas, ADR, Archify y constitución (FR-033) |
| 5.1 y 5.2 Pitch y discusión | Entrada que explica la plataforma; consola y panel para los bloques técnicos (SC-008) |

## Assumptions

- La web sigue siendo una aplicación propia servida por el backend del proyecto, como desde la spec 012. «No usar
  Streamlit» se cumple ya y se refuerza como requisito (FR-002). No hace falta migrar nada desde Streamlit.
- La autorización del planificador en la web reutiliza la de la spec 025 (habilitación del perfil planificador para el
  canal web). No se añade un sistema de cuentas ni de contraseñas.
- Los datos de planta siguen siendo los sintéticos de `data/synthetic/planificacion/v1/`. No hay conexión con sistemas
  internos de Manuelita.
- Los colores corporativos son los que ya están verificados en el repositorio a partir del logotipo público. Las
  ilustraciones de productos se dibujan para el proyecto; no se copian fotos ni piezas de la marca.
- La prioridad por fecha es esta: historias 1 y 2 antes del ensayo del viernes 27; historias 3 y 4 si el tiempo
  alcanza. Si no alcanza, la evidencia técnica se muestra con `/traza` y la terminal, como hoy.
- La demo principal del pitch sigue siendo WhatsApp en el teléfono del invitado; la web no la reemplaza.
- La planta de palma sigue fuera de alcance (historia 4 de la spec 025, P3).

## Out of Scope

- Cuentas de usuario, inicio de sesión o roles más allá de la autorización del planificador vigente.
- Conexión a ERP, históricos reales o cualquier dato interno de Manuelita.
- Nuevas herramientas del agente o cambios a la conducta del router, la memoria o el blindaje.
- Aplicación móvil nativa.
- Edición del plan a mano dentro de la consola: la persona cambia el escenario, no las cifras del plan.
