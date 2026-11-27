# Feature Specification: Imágenes de perfil y banner de Valer-IA

**Feature Branch**: `030-imagenes-perfil-valeria`

**Created**: 2026-11-27

**Status**: Draft

**Input**: User description: "necesito que usando la skill /ai-image-generation generes lo siguiente: Imagen para foto de perfil de Vale-IA; Baner para perfil en páginas web como linkin, facebook, whatsapp. Autorizo el uso de la imagen `docs/referencias/avatar_ingenio_manuelita.png` para que generes lo solicitado. Esa imagen es generada, no es una persona real, se puede usar. Las imágenes generadas resultantes guardalas en la carpeta `whatsapp` dentro de la carpeta `docs`, no existe la carpeta `whatsapp` creala. También recomiéndame qué otras imágenes se podrían generar para ser usadas en el chat bot de WhatsApp."

## Contexto

Valer-IA ya atiende por la web (specs 026 y 027) y por WhatsApp (spec 024), pero no tiene una identidad visual para
los perfiles de esos canales. La presentadora del video pitch (specs 028 y 029) parte de una imagen sintética con
ficha de origen (`docs/referencias/avatar_ingenio_manuelita.md`: generada con IA, `real_person: false`,
`brand_elements: false`). Esta feature produce, a partir de esa misma imagen, la foto de perfil y los banners de
Valer-IA para WhatsApp, LinkedIn y Facebook, de modo que la asistente se vea igual en todos los canales.

El nombre del producto es **Valer-IA** (la descripción dice «Vale-IA»; se asume el nombre del producto).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Foto de perfil de Valer-IA (Priority: P1)

El equipo necesita una foto de perfil de Valer-IA para la cuenta de WhatsApp del bot y para las páginas de LinkedIn
y Facebook. La foto muestra a la misma presentadora de la imagen de referencia, se reconoce en tamaño miniatura
(la lista de chats de WhatsApp) y se ve bien recortada en círculo.

**Why this priority**: Es la imagen que más se ve: aparece en cada chat y en cada mensaje del bot. Sin ella, el canal
de WhatsApp muestra la silueta genérica y no se distingue de un número cualquiera.

**Independent Test**: Abrir la imagen entregada en `docs/whatsapp/`, recortarla en círculo y verla a 48 px y a 640 px:
el rostro queda centrado y completo, sin texto ni logotipos, y una persona del equipo confirma que es la misma
presentadora del video.

**Acceptance Scenarios**:

1. **Given** la imagen de referencia autorizada, **When** se produce la foto de perfil, **Then** queda guardada en
   `docs/whatsapp/` en formato cuadrado, con el rostro y los hombros dentro del círculo central.
2. **Given** la foto producida, **When** se muestra como miniatura de 48 px, **Then** el rostro se distingue y no hay
   texto ilegible ni elementos cortados por el círculo.
3. **Given** la foto producida, **When** una persona del equipo la revisa, **Then** la aprueba o la rechaza, y solo una
   foto aprobada se considera entregada.

---

### User Story 2 - Banners de perfil para LinkedIn, Facebook y WhatsApp (Priority: P2)

El equipo necesita un banner (imagen de portada) para cada plataforma, con las proporciones que cada una exige, que
presente a Valer-IA. La declaración de IA va en el texto del perfil de cada red, no en la imagen.

**Why this priority**: Completa la presencia de Valer-IA en las páginas de perfil, pero el canal funciona sin banner.

**Independent Test**: Para cada plataforma, cargar el banner en una vista previa con su recorte real (escritorio y
teléfono) y comprobar que el nombre y el lema quedan dentro de la zona segura y no quedan tapados por la foto
de perfil.

**Acceptance Scenarios**:

1. **Given** la foto de perfil aprobada, **When** se producen los banners, **Then** hay uno por plataforma en
   `docs/whatsapp/`, cada uno con las medidas recomendadas por esa plataforma.
2. **Given** un banner, **When** se muestra con la foto de perfil superpuesta en la posición que usa la plataforma,
   **Then** ningún texto queda tapado ni cortado en escritorio ni en teléfono.
3. **Given** un banner, **When** se lee, **Then** dice «Valer-IA» y un lema corto en español, sin la frase de
   declaración; esa frase va en el texto del perfil (`docs/whatsapp/README.md`).

---

### User Story 3 - Recomendaciones de otras imágenes para el bot de WhatsApp (Priority: P3)

El equipo quiere saber qué otras imágenes conviene generar después para el bot de WhatsApp, con el propósito de
cada una y dónde se usaría en la conversación.

**Why this priority**: Orienta el trabajo siguiente; no bloquea el uso de la foto ni de los banners.

**Independent Test**: Leer la lista de recomendaciones: cada imagen dice para qué momento de la conversación sirve,
qué contiene y qué regla de la constitución debe respetar.

**Acceptance Scenarios**:

1. **Given** la spec, **When** se lee la sección de recomendaciones, **Then** cada recomendación indica su uso en el
   chat, su contenido y su prioridad, y ninguna se genera dentro de esta feature.

---

### User Story 4 - Tarjetas del bot de WhatsApp (Priority: P2)

*Ampliación pedida por el integrante el 2026-11-27: producir las recomendaciones 1–6, 8 y 9.*

El bot envía imágenes en momentos fijos de la conversación: bienvenida, elección de perfil, ayuda, sin
evidencia, mantenimiento, resultado de planificación, enlace al proyecto y Estados. Todas siguen el sistema
de las portadas.

**Independent Test**: abrir cada tarjeta en `docs/whatsapp/tarjetas/` a su tamaño: el texto se lee completo,
con contraste ≥ 4,5 y dentro de su zona segura; la plantilla de planificación no trae cifras.

**Acceptance Scenarios**:

1. **Given** una tarjeta, **When** se exporta, **Then** mide 1080×1080, 1080×1350 o 1080×1920 (Estados) y su
   texto queda en la zona segura (en los Estados, fuera de las franjas que tapa WhatsApp).
2. **Given** la plantilla de planificación, **When** se revisa, **Then** tiene los recuadros vacíos: las cifras
   las pone el optimizador, nunca la imagen.
3. **Given** el código QR, **When** se escanea, **Then** abre el repositorio público del proyecto.

---

### User Story 5 - Stickers animados de Valer-IA (Priority: P2)

*Ampliación pedida por el integrante el 2026-11-27.*

Nueve stickers animados de Valer-IA en caricatura, en el estilo de las caricaturas de los años 50 de la
imagen de referencia de estilo (contorno grueso, colores planos, guiño, insignia redonda y borde blanco):
pulgar arriba, «¡Bienvenido!», «¡Gracias por confiar en nosotros!», «¿Cuál es tu consulta?», «Hola»
(saludando), «Lindo día», «¡Gracias!», «Pensando» y «¡Listo!».

**Independent Test**: abrir cada `.webp` de `docs/whatsapp/stickers/` en un navegador: se anima en bucle,
mide 512×512, pesa ≤ 500 KB y el texto se lee bajo la ilustración.

**Acceptance Scenarios**:

1. **Given** un sticker, **When** se exporta, **Then** es un WebP animado de 512×512, fondo transparente y
   ≤ 500 KB, con el ícono del paquete de 96×96 (≤ 50 KB).
2. **Given** los stickers, **When** se revisan, **Then** muestran a Valer-IA (pelo oscuro ondulado, chaqueta
   verde, camisa blanca, aretes dorados), no al personaje de la imagen de estilo.

---

### Edge Cases

- Una pieza no convence en la revisión (encuadre, contraste, legibilidad): se ajusta el diseño y se vuelve a
  exportar; no se entrega una pieza que una persona del equipo no haya aprobado.
- El texto de una pieza tiene un error: se corrige en el diseño; el texto es editable y nunca se entrega con errores.
- La imagen de referencia es vertical (941×1672) y los banners son muy anchos: el diseño ocupa el ancho con
  fondo, pictogramas y texto, y la presentadora va recortada a un lado; nunca se estira ni se deforma.
- La resolución de la referencia no alcanza para un tamaño: la pieza se diseña para que la presentadora ocupe un
  área que no exija ampliarla más de su resolución original, y el resto lo dibuja el diseño.
- Una tipografía o un recurso del diseño no tiene licencia de uso libre: se reemplaza por uno que sí la tenga.
- Una plataforma cambia sus medidas recomendadas: se documenta la fuente y la fecha de las medidas usadas.
- WhatsApp no ofrece portada en el tipo de cuenta usado por el bot: el banner de WhatsApp queda listo para WhatsApp
  Business y se anota que en la cuenta personal solo aplica la foto de perfil.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: La feature MUST crear la carpeta `docs/whatsapp/` y guardar allí todas las imágenes entregadas.
- **FR-002**: MUST producirse una foto de perfil cuadrada de Valer-IA, de al menos 640×640 px, a partir de la imagen
  de referencia autorizada, con el rostro dentro del círculo central y sin texto, logotipos ni marca de Manuelita.
- **FR-003**: La foto de perfil MUST ser fotorrealista: usa a la presentadora tal como aparece en la imagen de
  referencia (la misma del video), sin alterar sus rasgos, sobre el fondo de la referencia armonizado con la paleta
  de Valer-IA (plan, research R4). Un estilo
  ilustrado necesitaría un modelo generativo, y esta feature no usa ninguno (FR-010).
- **FR-004**: MUST producirse un banner para LinkedIn, uno para Facebook y uno para WhatsApp Business, cada uno con las
  medidas recomendadas por la plataforma y una zona segura donde no lo tape la foto de perfil.
- **FR-005**: Cada banner MUST mostrar «Valer-IA» y un lema corto en español, sin errores, y NO la frase de
  declaración; la declaración de IA (asistente con IA de un proyecto académico, no canal oficial de Manuelita) va en el
  texto del perfil de cada red («Info» de WhatsApp, descripción de LinkedIn y Facebook), no en la imagen
  (decisión del integrante, 2026-11-27).
  Los textos de perfil MUST incluir esa declaración.
- **FR-006**: Las imágenes MUST usar los colores corporativos (rojo anaranjado, naranja, amarillo y verde, tomados
  del logotipo de Manuelita como inspiración por pedido del integrante, 2026-11-27) y formas propias (un abanico de
  hojas de caña), sin el logotipo, su figura circular de pétalos ni su tipografía (§3.7 y §10 de la constitución).
- **FR-007**: Ninguna imagen MUST presentar a la presentadora como vocera de Manuelita ni representar a una persona
  real.
- **FR-008**: Cada imagen entregada MUST tener una ficha de origen junto a ella que registre cómo se produjo (skill
  y fuente del diseño), la fecha, la imagen de referencia usada, las tipografías y recursos con su licencia, el
  costo (0) y quién la aprobó.
- **FR-009**: Solo MUST entregarse imágenes que una persona del equipo haya revisado y aprobado; las rechazadas no se
  versionan.
- **FR-010**: Las piezas MUST producirse sin costo y con las skills de Claude ya instaladas (decisión del
  integrante, 2026-11-27): se diseñan como composiciones a la medida exacta de cada plataforma, a partir de la
  imagen de referencia, y se exportan a PNG en el equipo del integrante. No se usa la skill `ai-image-generation`
  ni ningún modelo o servicio de generación de imágenes, de pago o gratuito.
- **FR-011**: Las tipografías y los recursos gráficos MUST tener licencia de uso libre, registrada en la ficha.
- **FR-012**: La imagen de referencia y las piezas MUST quedarse en el equipo del integrante; nada se envía a
  servicios externos.
- **FR-014**: Las tarjetas del bot (US4) MUST quedar en `docs/whatsapp/tarjetas/`, con texto exacto, contraste
  ≥ 4,5, zona segura, ficha y aprobación humana; la plantilla de planificación MUST NOT llevar cifras.
- **FR-015**: Los stickers (US5) MUST quedar en `docs/whatsapp/stickers/` como WebP animado de 512×512 en bucle,
  ≤ 500 KB, más el ícono del paquete de 96×96 ≤ 50 KB (requisitos de WhatsApp), con ficha y aprobación.
- **FR-016**: Valer-IA en caricatura MUST ser una ilustración vectorial propia dibujada en código
  (`fuente/personaje.js`), inspirada en la imagen de referencia; toma el **estilo** de la imagen de estilo
  aportada (caricatura de los años 50), no su personaje, y no usa modelos generativos (FR-010).
- **FR-017**: El código QR MUST apuntar al repositorio público del proyecto (decisión del integrante) y
  generarse en local.
- **FR-013**: La spec MUST incluir una lista priorizada de otras imágenes recomendadas para el bot de WhatsApp, con su
  uso y contenido, sin generarlas.

### Key Entities

- **Imagen de referencia**: la imagen sintética autorizada (`docs/referencias/avatar_ingenio_manuelita.png`) y su
  ficha de origen; es la entrada de todas las piezas.
- **Pieza de perfil**: una imagen entregada (foto de perfil o banner de una plataforma), con su destino, sus medidas,
  su zona segura y su estado (en diseño, aprobada, rechazada).
- **Ficha de la pieza**: el registro de origen de cada pieza: cómo se produjo, fecha, referencia, tipografías y
  recursos con su licencia, costo y aprobación.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: La foto de perfil y los tres banners quedan en `docs/whatsapp/`, aprobados por una persona del equipo,
  cada uno con su ficha.
- **SC-002**: Una persona que vea la foto de perfil junto a un cuadro del video pitch reconoce a la misma presentadora
  (al menos 4 de 5 personas consultadas).
- **SC-003**: En la vista previa de cada plataforma, en escritorio y en teléfono, el 100 % del texto de los banners
  queda visible y sin errores.
- **SC-004**: El rostro de la foto de perfil se distingue a 48 px.
- **SC-005**: El costo es 0 USD: ninguna pieza requiere pago, créditos, claves ni cuentas de terceros.
- **SC-006**: Ninguna pieza muestra el logotipo ni la marca de Manuelita, ni representa a una persona real.

## Recomendaciones: otras imágenes para el bot de WhatsApp

Ordenadas por utilidad para la conversación. El integrante pidió producirlas todas el 2026-11-27 (US4 y US5).

| Prioridad | Imagen | Uso en el chat | Contenido |
|---|---|---|---|
| 1 | **Tarjeta de bienvenida** | Primer mensaje a un número nuevo | Valer-IA saluda, qué puede hacer en una línea y la declaración de IA y proyecto académico |
| 2 | **Tarjeta de perfiles** | Cuando la persona elige con quién hablar | Los cinco perfiles con el pictograma y el color de su producto (caña, azúcar, etanol, energía) |
| 3 | **Guía rápida de uso** | Respuesta a «ayuda» o «¿cómo funciona?» | Tres o cuatro ejemplos de preguntas y cómo pedir una cita de la fuente |
| 4 | **Sin evidencia** | Cuando la respuesta es `fallback` | Valer-IA indica con amabilidad que no encontró información verificable y sugiere reformular |
| 5 | **Fuera de servicio** | Mantenimiento o fallo del modelo | Aviso de que vuelve pronto, sin tono de error técnico |
| 6 | **Plantilla de planificación** | Al entregar un resultado del planificador industrial | Fondo con zona libre para superponer las cifras reales del optimizador (las cifras nunca las dibuja el modelo) |
| 7 | **Stickers de Valer-IA** | Reacciones: gracias, pensando, listo, no entendí | 4 a 6 stickers 512×512 en WebP con fondo transparente, mismo personaje |
| 8 | **Código QR del canal** | Web, README y presentaciones | QR al chat de WhatsApp con la foto de perfil al centro (el QR se genera localmente, no con IA) |
| 9 | **Imágenes para Estados** | Anuncios en los Estados de WhatsApp | Formato 1080×1920 con una novedad o un consejo de uso |

Reglas que todas comparten: misma presentadora y paleta, sin marca de Manuelita, texto compuesto aparte cuando deba
ser exacto, declaración de IA cuando la imagen se muestre fuera del chat, ficha de origen y aprobación humana.

## Assumptions

- El integrante autoriza el uso de la imagen de referencia y confirma que es sintética; su ficha ya declara
  `real_person: false` y `brand_elements: false` (Roberto José Guerrero, 2026-11-26).
- **Herramientas** (decisiones del integrante, 2026-11-27): sin costo y con las skills de Claude ya instaladas.
  Se usa la skill `design` (diseño de banners y de imágenes para redes, a la medida de cada plataforma, exportadas a
  PNG con un navegador local) con la guía de `frontend-design`. La skill `ai-image-generation` queda descartada:
  todos sus modelos pasan por un servicio de pago. Las funciones de `design` que llaman a APIs con clave (logos e
  íconos con Gemini) tampoco se usan.
- Como no hay modelo generativo, la presentadora aparece tal como está en la imagen de referencia (recortada y
  compuesta, sin cambiar sus rasgos), lo que asegura que sea la misma del video.
- Las herramientas de diseño son de producción fuera de línea: no se añaden a la app ni a sus pruebas.
- Medidas (plan, research R2): foto de perfil 640×640 px; LinkedIn banner personal 1584×396 px; Facebook
  1640×624 px con zona segura central para el recorte de teléfono; WhatsApp Business 1920×1080 px (16:9).
- Las imágenes son material de difusión del proyecto: no cambian la app, el bot ni sus pruebas, y no se publican en
  ninguna red social dentro de esta feature; subirlas a cada perfil lo hace el integrante.
- Las imágenes entregadas se versionan por Git LFS, como las demás imágenes de `docs/referencias/`.
- La rama parte de `029-pitch-escenas-sincronizadas` porque la imagen de referencia aún no está en `main` y la
  constitución ya va en 2.4.0; depende de los PR #84 y #85.
