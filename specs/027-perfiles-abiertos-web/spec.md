# Feature Specification: Perfiles abiertos en la web, incluido el planificador

**Feature Branch**: `027-perfiles-abiertos-web`

**Created**: 2026-11-25

**Status**: Draft

**Input**: User description: "Necesito que usando la skill /frontend-design dejes en el codigo frontend y backend que cualquier personsa que use la aplicacion web pueda usar cualquier tipo de perfil, incluyendo el perfil de Planificador. Actualmente ese perfil solo esta permitido por autorizacion, quiero que quites ese filtro, y deje todos los perfiles para uso de cualquier cliente. El cliente escogera cual le conviene mas"

## Contexto

Hoy la aplicación web ofrece cinco perfiles: visitante, cliente B2B, proveedor, colaborador y planificador
industrial. Los cuatro primeros los elige cualquiera. El planificador está **bloqueado**: solo se abre si quien
administra el servidor activa una autorización, y sin ella:

- El selector de perfil lo muestra deshabilitado con «Solo equipo de planta autorizado».
- La entrada muestra su tarjeta con candado.
- El área de planificación muestra una pantalla de acceso denegado.
- El servidor rechaza las consultas de planificación.

Esto confunde a quien clona el repositorio o prueba la app (le pasó al propietario del repositorio). Además, impide
mostrar la capacidad principal de la idea 7 sin configuración previa. Los datos de planificación son
**sintéticos**, así que abrir el perfil no expone información real de Manuelita.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Usar el planificador sin pedir permiso (Priority: P1)

Una persona abre la aplicación web, por primera vez y sin configurar nada, y quiere ver qué hace el planificador
industrial. Lo elige como cualquier otro perfil y puede:

- Abrir el área de planificación.
- Ajustar un escenario y ver el plan, el flujo de caña y los compromisos.
- Comparar con el plan base.
- Pedirle al agente que explique el plan.

**Why this priority**: es el bloqueo que hoy impide ver la capacidad central del producto (idea 7). Sin esto, el
resto no aporta.

**Independent Test**: en un equipo recién instalado, sin ninguna variable de autorización, abrir la web, elegir
«Planificador» y obtener un plan en el área de planificación y una respuesta del agente con el perfil
planificador.

**Acceptance Scenarios**:

1. **Given** una instalación sin autorización configurada, **When** la persona abre el área de planificación,
   **Then** ve el estado de la planta, el escenario y el plan, sin pantalla de acceso denegado.
2. **Given** el perfil planificador elegido en el agente, **When** la persona pregunta «Tenemos 15 % menos caña
   esta semana, ¿cómo cumplimos?», **Then** el agente responde con el plan calculado, la restricción que lo
   limita y la advertencia de datos sintéticos.
3. **Given** cualquier visitante, **When** consulta las funciones de planificación (estado, plan, comparación),
   **Then** el servidor responde con los datos y nunca con un rechazo por falta de autorización.
4. **Given** una persona con el perfil planificador, **When** guarda una propuesta, **Then** se le pide
   confirmarla en dos pasos, igual que hoy, y la propuesta queda registrada con su identificador seudónimo.

---

### User Story 2 - Elegir el perfil que más le conviene (Priority: P2)

La persona no sabe qué perfil le sirve. La entrada y el selector le muestran los cinco en igualdad de condiciones.
Cada perfil dice, en lenguaje simple, para quién es y qué puede hacer, con un ejemplo de pregunta. La persona
elige uno y lo cambia cuando quiera, sin perder la conversación.

**Why this priority**: abrir el filtro sin orientar la elección deja a la persona adivinando. La decisión es del
cliente («el cliente escogerá cuál le conviene más»), así que la interfaz debe ayudarle a decidir.

**Independent Test**: un usuario nuevo puede, solo con lo que ve en pantalla, decir para qué sirve cada perfil y
elegir uno en menos de 30 segundos.

**Acceptance Scenarios**:

1. **Given** la entrada de la web, **When** la persona la recorre, **Then** ve los cinco perfiles sin candados,
   rótulos de «solo autorizados» ni estilos deshabilitados.
2. **Given** el selector de perfil en el área del agente, **When** la persona lo abre, **Then** los cinco perfiles
   se pueden elegir. Cada uno muestra para quién es y un ejemplo de pregunta.
3. **Given** una conversación en curso, **When** la persona cambia de perfil, **Then** el cambio se aplica a la
   siguiente pregunta y la interfaz indica el perfil activo.
4. **Given** el perfil planificador, **When** la persona lo elige, **Then** la interfaz le ofrece abrir el área de
   planificación. También le recuerda, sin bloquearla, que los datos son sintéticos.

---

### User Story 3 - Documentación y reglas coherentes con el acceso abierto (Priority: P3)

Quien clona el repositorio, el docente o el propietario leen el README, la constitución y el ejemplo de
configuración, y entienden que en la web todos los perfiles están abiertos. Ya no encuentran instrucciones para
activar autorizaciones que ya no existen en la web.

**Why this priority**: evita que se repita la confusión de esta semana. No cambia el comportamiento.

**Independent Test**: buscar en la documentación vigente cualquier instrucción que exija autorizar el planificador
en la web. No debe quedar ninguna.

**Acceptance Scenarios**:

1. **Given** el README y el ejemplo de configuración, **When** alguien sigue los pasos tras clonar, **Then** puede
   usar los cinco perfiles sin editar variables de autorización.
2. **Given** la constitución, **When** se lee la regla del perfil planificador, **Then** dice que en la web es de
   libre elección y conserva la regla vigente para WhatsApp.

---

### Edge Cases

- **Configuraciones viejas**: alguien tiene la variable de autorización de la web en su configuración. Se ignora
  sin errores y el resultado es el mismo.
- **Detección automática del perfil**: alguien escribe «soy planificador» en el chat web. El agente cambia al
  perfil planificador como con los otros perfiles, sin pedir autorización.
- **Muchas propuestas a la vez**: varias personas guardan propuestas. Se mantienen el vencimiento de 5 minutos y el
  límite de propuestas pendientes actuales; cada propuesta conserva el identificador seudónimo de quien la guardó.
- **Fallo del optimizador**: el área de planificación sigue mostrando el error accionable actual, no una pantalla
  de acceso.
- **Llegada directa por dirección**: alguien abre la dirección del área de planificación sin haber elegido perfil.
  La ve completa y el perfil activo pasa a planificador.
- **Otros canales**: alguien usa WhatsApp. Ahí el perfil planificador sigue exigiendo estar en la lista de
  autorizados (fuera del alcance, ver supuestos).

## Requirements *(mandatory)*

### Functional Requirements

**Acceso**

- **FR-001**: En la aplicación web, el sistema MUST permitir a cualquier persona elegir cualquiera de los cinco
  perfiles (visitante, cliente B2B, proveedor, colaborador y planificador industrial), sin autorización previa ni
  configuración del servidor.
- **FR-002**: El servidor MUST atender todas las funciones de planificación de la web (acceso, estado de planta,
  plan, comparación, rangos del escenario y propuesta) para cualquier visitante, sin rechazos por autorización.
- **FR-003**: El agente MUST aceptar el perfil planificador en conversaciones web de cualquier usuario. Esto
  incluye elegirlo en el selector, pedirlo en el chat («soy planificador») y recordarlo con confirmación.
- **FR-004**: La regla que decide la ruta de planificación del agente MUST depender solo del perfil elegido, no de
  quién es el usuario.
- **FR-005**: El sistema MUST ignorar sin errores las variables de autorización del planificador para la web que
  existan en configuraciones previas.

**Interfaz**

- **FR-006**: La interfaz MUST retirar todo indicio de bloqueo del perfil planificador: candados, rótulos «Solo
  equipo de planta autorizado» o «solo autorizados», opciones deshabilitadas y la pantalla de acceso denegado del
  área de planificación.
- **FR-007**: El selector de perfil y la entrada MUST presentar los cinco perfiles en igualdad visual. Cada uno
  muestra para quién es, qué puede hacer y un ejemplo de pregunta, con lenguaje del usuario y no del sistema.
- **FR-008**: La interfaz MUST mostrar en todo momento cuál es el perfil activo y permitir cambiarlo en un paso
  desde el área del agente.
- **FR-009**: Al elegir el perfil planificador, la interfaz MUST ofrecer ir al área de planificación. Además, MUST
  mantener visible la advertencia de que los datos son sintéticos.

**Salvaguardas que se conservan**

- **FR-010**: El sistema MUST conservar la confirmación en dos pasos para guardar propuestas, su vencimiento de 5
  minutos y el límite de propuestas pendientes.
- **FR-011**: El sistema MUST registrar cada propuesta y cada consulta de la consola con el identificador
  seudónimo de quien la hizo, como hoy.
- **FR-012**: Toda respuesta y pantalla del planificador MUST seguir diciendo que los datos son sintéticos y que no
  representan la operación real de Manuelita.
- **FR-013**: Las cifras del plan MUST seguir saliendo solo de las herramientas del servidor. La paridad entre
  consola, herramienta del agente y línea de comandos no MUST cambiar.

**Fuera de la web**

- **FR-014**: El acceso al perfil planificador por WhatsApp y el modo degradado MUST quedar como están hoy (lista
  de autorizados y sin planificación en modo degradado).

**Documentación y reglas**

- **FR-015**: El README, el ejemplo de configuración y la evidencia de la web MUST describir que en la web los
  cinco perfiles son de libre elección. MUST retirar las instrucciones para autorizar el planificador en la web.
- **FR-016**: La constitución MUST registrar el cambio de la regla del perfil planificador en una enmienda, que
  requiere la aprobación del propietario del repositorio.

### Key Entities

- **Perfil**: una forma de atención del agente: nombre, para quién es, qué puede hacer, ejemplo de pregunta y
  herramientas que ofrece. En la web, todos son de libre elección. La marca de «requiere autorización» solo aplica
  fuera de la web.
- **Perfil activo**: el perfil elegido por la persona en su sesión. Decide las herramientas del agente y si se
  ofrece el área de planificación.
- **Propuesta de producción**: un plan que una persona decidió guardar tras confirmar. Lleva el identificador
  seudónimo de quien la guardó, la fecha y la advertencia de datos sintéticos.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: En una instalación nueva sin configuración de autorización, 5 de 5 perfiles se pueden elegir y usar
  en la web.
- **SC-002**: 0 rechazos por autorización en las funciones de planificación de la web durante la batería de
  escenarios (12/12 escenarios responden con un plan o con el aviso de que no hay solución factible).
- **SC-003**: Una persona nueva elige el perfil que necesita en menos de 30 segundos desde que abre la web.
- **SC-004**: 0 apariciones de candados, rótulos de «solo autorizados» u opciones deshabilitadas de perfil en la
  web, de 360 a 1920 px de ancho.
- **SC-005**: La paridad de cifras entre consola, herramienta y línea de comandos se mantiene en 12/12 escenarios.
  La confirmación en dos pasos se exige en el 100 % de las propuestas guardadas.
- **SC-006**: El comportamiento por WhatsApp no cambia: un usuario fuera de la lista de autorizados sigue sin poder
  usar el planificador en ese canal.
- **SC-007**: La documentación vigente no contiene ninguna instrucción para autorizar el planificador en la web.

## Assumptions

- **Alcance**: la petición habla de «la aplicación web», así que el cambio aplica solo a la web. WhatsApp conserva
  su lista de autorizados, porque es un número real de un integrante y otro canal con otro riesgo. Si se quiere
  abrir también WhatsApp, será otra spec.
- **Datos**: los datos de planificación son sintéticos y declarados como tales. Abrir el perfil no expone
  información operativa real, y esa es la razón de que el filtro ya no sea necesario en la web.
- **Identidad**: no se añade inicio de sesión. La web sigue identificando a cada visitante con su identificador
  seudónimo actual.
- **Propuestas**: guardar propuestas sigue disponible para cualquiera, con las salvaguardas actuales (dos pasos,
  vencimiento, límite y registro). No hay aprobación humana adicional, porque las propuestas no se ejecutan en
  ninguna planta.
- **Diseño**: se conserva la identidad visual de la spec 026 (colores de Manuelita por producto, flujo de caña,
  tipografía). Este cambio solo retira el bloqueo y mejora la orientación para elegir perfil.
- **Gobierno**: el cambio de la regla del planificador requiere una enmienda de la constitución aprobada por el
  propietario del repositorio (jasonCastano).
- **Dependencia**: se construye sobre `main` con la plataforma web de la spec 026 ya fusionada.
