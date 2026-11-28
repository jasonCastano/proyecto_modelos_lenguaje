# Feature Specification: Pestaña «WhatsApp» para hablar con Valer-IA desde la web

**Feature Branch**: `032-pestana-whatsapp-web`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "usando la skill /design-taste-frontend agregar una pestaña nueva donde el cliente pueda
conectarse a WhatsApp Web. En esa nueva pestaña debe estar el link del chatbot que al darle clic abra en una nueva
pestaña la aplicación de WhatsApp Web para que el cliente hable con Valer-IA. Manten el uso de los colores
corporativos de la empresa Ingenio Manuelita, utiliza elementos visuales que estén en relación con los productos
producidos por la empresa. Inspirate de la pagina oficial de Ingenio Manuelita https://www.manuelita.com/ Mejora el
frontend que cumpla con los requerimiento del modulo 3."

## Contexto

La plataforma web de Valer-IA tiene cuatro áreas (Entrada, Agente, Planificación y Evidencia, spec 031). El mismo
agente responde también por WhatsApp desde una SIM dedicada (specs 024 y 028 a 031), pero la web solo lo menciona en
una pregunta frecuente: no hay forma de pasar de la web al chat. Esta spec agrega una quinta área, **WhatsApp**,
desde la que cualquier visitante abre la conversación con Valer-IA en un clic.

La constitución (§9, canal) prohíbe que el número de la SIM entre al repositorio; la spec respeta esa regla.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Abrir el chat de WhatsApp desde la web (Priority: P1)

Un visitante (cliente, proveedor, colaborador o invitado de la sustentación) entra a la web, va a la pestaña
**WhatsApp** y pulsa «Abrir WhatsApp». Se abre una pestaña nueva con la conversación con Valer-IA lista para
escribir, con un primer mensaje sugerido.

**Why this priority**: es el pedido central y el único camino de la web al canal de WhatsApp, que es la experiencia
del Módulo 3 que se evalúa con teléfonos de invitados.

**Independent Test**: desde la navegación, abrir la pestaña WhatsApp, pulsar el enlace y comprobar que se abre una
pestaña nueva hacia WhatsApp con el chat de Valer-IA y el mensaje sugerido, sin salir de la web.

**Acceptance Scenarios**:

1. **Given** el canal está configurado, **When** el visitante abre la pestaña WhatsApp, **Then** ve qué es el chat,
   qué puede preguntar, la declaración de proyecto académico con IA y un botón principal «Abrir WhatsApp».
2. **Given** la pestaña WhatsApp abierta, **When** pulsa «Abrir WhatsApp», **Then** se abre una pestaña nueva hacia
   la conversación con Valer-IA, con el texto sugerido ya escrito, y la web sigue abierta en la pestaña original.
3. **Given** cualquier área de la web, **When** el visitante mira la navegación, **Then** encuentra «WhatsApp» como
   quinta área, con el mismo comportamiento que las otras (estado activo, teclado, menú en móvil).

---

### User Story 2 - Pasar del computador al teléfono (Priority: P2)

Un visitante ve la web en un computador pero quiere hablar desde su teléfono. En la pestaña WhatsApp encuentra un
código QR que, escaneado con la cámara del teléfono, abre el mismo chat con Valer-IA.

**Why this priority**: en la sustentación los invitados prueban desde su propio teléfono mientras la web se proyecta;
el QR evita dictar un número.

**Independent Test**: escanear el QR de la pestaña con un teléfono y comprobar que abre el chat de Valer-IA con el
mensaje sugerido.

**Acceptance Scenarios**:

1. **Given** la pestaña WhatsApp en un computador, **When** el visitante escanea el QR, **Then** su teléfono abre el
   chat de Valer-IA con el mismo mensaje sugerido.
2. **Given** la pestaña WhatsApp en un teléfono, **When** el visitante pulsa «Abrir WhatsApp», **Then** se abre la
   aplicación de WhatsApp del teléfono y no una página que no funciona en móviles.
3. **Given** la pestaña WhatsApp en un computador, **When** pulsa «Abrir WhatsApp», **Then** se abre WhatsApp Web
   en una pestaña nueva.

---

### User Story 3 - Canal no disponible (Priority: P3)

Si el número del canal no está configurado en el servidor (por ejemplo, el servidor de respaldo con WhatsApp sin
vincular), la pestaña no muestra un enlace roto: explica que el chat no está disponible y ofrece hablar con Valer-IA
en la web.

**Why this priority**: evita que un invitado pulse un enlace que no lleva a nada; es poco frecuente pero visible.

**Independent Test**: arrancar la web sin el número configurado y comprobar que la pestaña muestra el aviso y el
enlace al agente de la web, sin botón ni QR.

**Acceptance Scenarios**:

1. **Given** el número no está configurado, **When** el visitante abre la pestaña WhatsApp, **Then** ve «El chat de
   WhatsApp no está disponible en este momento» y un enlace «Habla con Valer-IA aquí» al área Agente.
2. **Given** el número no está configurado, **Then** la pestaña no muestra el botón «Abrir WhatsApp» ni el QR.

---

### Edge Cases

- El visitante no tiene WhatsApp instalado ni sesión en WhatsApp Web: WhatsApp muestra su propia página para
  descargar la app o vincular; la pestaña dice antes qué se necesita.
- El navegador bloquea la pestaña nueva: el enlace es un enlace normal que el visitante abre con un clic (nunca una
  ventana emergente automática).
- Movimiento reducido: la pestaña no anima su elemento visual.
- Lectores de pantalla: el enlace anuncia que abre una pestaña nueva y el QR tiene una alternativa en texto (el
  propio botón).
- El número cambia (otra SIM o el servidor de respaldo): basta cambiar la configuración del servidor, sin tocar el
  código ni el repositorio.
- El número está mal escrito (sin `+57`, con letras o con menos dígitos): la pestaña muestra el aviso de chat no
  disponible en vez de un enlace roto, y el registro del servidor indica que el formato es inválido sin mostrar el
  número.
- El canal está en modo cerrado: el chat solo responde a números de prueba; la pestaña no lo anuncia como abierto
  al público y lo indica.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La web DEBE tener una quinta área, **WhatsApp**, en la navegación de todas las áreas, con el mismo
  comportamiento que las demás (estado activo, foco visible, teclado y menú móvil).
- **FR-002**: La pestaña DEBE mostrar un botón principal «Abrir WhatsApp» que abre la conversación con Valer-IA en
  una **pestaña nueva**, conservando la web en la pestaña original. En un computador abre **WhatsApp Web**; en un
  teléfono abre **la aplicación de WhatsApp**, porque WhatsApp Web no funciona en navegadores móviles.
- **FR-003**: El enlace DEBE llevar un primer mensaje sugerido en español («Hola, Valer-IA») ya escrito en el chat.
- **FR-004**: El número del canal NO DEBE aparecer en ningún archivo versionado del repositorio. El servidor lo lee
  de su configuración externa (`VALERIA_WHATSAPP_NUMBER` en el `.env` del proyecto, fuera de Git) y la web lo pide
  al abrir la pestaña. Cambiar de SIM o pasar al servidor de respaldo es editar esa línea y reiniciar el servidor,
  sin recompilar la web.
- **FR-004a**: `VALERIA_WHATSAPP_NUMBER` DEBE estar en formato internacional E.164 con el indicativo del país
  (Colombia: `+57` seguido de los 10 dígitos del celular, sin espacios ni guiones), igual que `WA_ALLOW_*`. El
  servidor construye el enlace solo con los dígitos. Un valor vacío o con formato inválido se trata como canal no
  configurado (FR-005).
- **FR-005**: Si el número no está configurado, la pestaña DEBE mostrar el aviso de chat no disponible y el enlace
  al área Agente, sin botón ni QR (User Story 3).
- **FR-006**: La pestaña DEBE mostrar un código QR que abre el mismo chat desde un teléfono, generado en la propia
  plataforma, sin servicios externos.
- **FR-007**: La pestaña DEBE explicar en lenguaje sencillo qué es el chat, qué se le puede preguntar (los mismos
  perfiles y fuentes que la web) y qué se necesita (WhatsApp en el teléfono o WhatsApp Web en el computador).
- **FR-008**: La pestaña DEBE mostrar la declaración «Proyecto académico con IA. No es un canal oficial de
  Manuelita.» junto al botón, como en el resto de la plataforma.
- **FR-009**: La pestaña DEBE indicar si el chat está abierto a cualquier número o solo a números de prueba, según
  el modo del canal, sin mostrar números.
- **FR-010**: El diseño DEBE seguir el sistema de la spec 031 (skill `design-taste-frontend`): paleta de marca con
  los colores del logotipo de Manuelita (verde para la acción), tipografía Archivo, un elemento visual relacionado
  con los productos de Manuelita (caña, azúcar, palma, uvas o mejillones), una sección por pantalla, sin el logotipo,
  la figura ni la tipografía de Manuelita, y con la estructura y el tono de manuelita.com como inspiración, no su
  marca.
- **FR-011**: La entrada DEBE enlazar a la nueva pestaña donde ya se menciona WhatsApp (la pregunta frecuente
  «¿Puedo usarla por WhatsApp?»).
- **FR-012**: La pestaña DEBE cumplir lo que la constitución exige a la web del Módulo 3: contraste AA, sin
  desplazamiento horizontal de 360 a 1920 px, foco visible, movimiento reducido respetado y declaración visible.

### Key Entities

- **Canal de WhatsApp**: número de la SIM dedicada (solo en la configuración del servidor), modo (abierto o
  cerrado) y si está disponible. La web solo recibe lo necesario para construir el enlace y el QR.
- **Enlace al chat**: destino (WhatsApp Web, la aplicación o el chooser de WhatsApp), mensaje sugerido y pestaña
  nueva.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Desde cualquier área, un visitante llega al chat de Valer-IA en WhatsApp en **2 clics o menos**
  (pestaña WhatsApp y botón) y en menos de 15 segundos.
- **SC-002**: En una prueba con 5 personas, al menos 4 abren el chat desde el computador y al menos 4 desde el
  teléfono escaneando el QR, sin ayuda.
- **SC-003**: Una búsqueda del número de la SIM en el repositorio devuelve **cero** resultados.
- **SC-004**: Sin el número configurado, la pestaña nunca muestra un enlace ni un QR que lleve a un chat inexistente
  (0 enlaces rotos).
- **SC-005**: La pestaña pasa las mismas comprobaciones de la web que las otras cuatro áreas: contraste AA, sin
  desplazamiento horizontal en 360, 768, 1024, 1440 y 1920 px, y declaración visible.
- **SC-006**: Las pruebas de la plataforma (unitarias, web y de extremo a extremo) siguen en verde, con pruebas
  nuevas que cubren las tres historias.

## Assumptions

- Valer-IA responde por la misma SIM dedicada de las specs 028 a 031; esta spec no cambia el canal, el gateway ni el
  backend del chat, solo agrega el camino desde la web.
- El mensaje sugerido es fijo y en español; la versión en inglés de la web queda para la spec 033.
- El QR se genera en la plataforma con una biblioteca de licencia libre; no se usa ningún servicio externo que
  reciba el número.
- La pestaña no muestra el número escrito: el enlace y el QR bastan. El número sí será visible para quien abra el
  chat, porque WhatsApp lo muestra; es el número público del proyecto.
- El elemento visual de producto reutiliza las fotos con licencia libre o las ilustraciones propias de la spec 031.
- La validación con personas (SC-002) la hace el integrante después de la implementación.
