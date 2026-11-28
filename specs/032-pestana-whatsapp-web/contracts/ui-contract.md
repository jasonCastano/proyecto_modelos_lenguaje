# Contrato de interfaz: área `/whatsapp` (spec 032)

## Navegación

- `AREAS` tiene cinco entradas en este orden: Entrada, Agente, Planificación, Evidencia, **WhatsApp**.
- La entrada activa lleva `aria-current="page"`; el menú móvil (`data-open`) también la incluye.
- Título del documento: «WhatsApp · Valer-IA».

## Página: dos secciones, una por pantalla (revisión del integrante, 2026-11-28)

El integrante pidió que la pestaña primero explique el chat y después ofrezca, en la misma página, el enlace a
WhatsApp Web y el QR como dos opciones.

### 1. `section#whatsapp`: información (`data-enter`, hero split)

| Elemento | Contenido | Selector de prueba |
|---|---|---|
| Declaración | «Proyecto académico con IA. No es un canal oficial de Manuelita.» | `.wa-notice` |
| h1 | «Habla con Valer-IA por WhatsApp» (`tabIndex -1`) | `#whatsapp-title` |
| Lead | «El mismo agente de esta web te responde en WhatsApp, desde el computador o desde tu celular.» | `.wa-lead` |
| Puntos | Qué se puede preguntar, la fuente de cada dato, texto o nota de voz en español o inglés | `.wa__points` |
| Enlace | «Ver cómo conectarte» → `#conectar` | — |
| Visual | Foto de caña (`PHOTOS.cana`, `data-source="stand-in"`) | `.wa__visual img` |

### 2. `section#conectar`: las dos opciones

| Elemento | Contenido | Selector de prueba |
|---|---|---|
| h2 | «Elige cómo conectarte» | `#conectar-title` |
| Estado del canal | `open`: «Abierto: cualquier número puede escribir»; `closed`: «Solo números de prueba del equipo»; `unknown`: no se muestra | `[data-testid=wa-mode]` |
| Opción 1 (h3) | Computador: «Desde este computador»; teléfono: «Desde este celular» | `#wa-option-web` |
| Botón | Computador: «Abrir WhatsApp Web» (`web_url`); teléfono: «Abrir WhatsApp» (`app_url`). `<a class="btn" target="_blank" rel="noopener noreferrer">` con el texto oculto «(se abre en una pestaña nueva)» | `[data-testid=wa-open]` |
| Requisito | «Necesitas WhatsApp Web vinculado a tu celular.» o «Necesitas la aplicación de WhatsApp instalada.» | `.wa-needs` |
| Opción 2 (h3) | Computador: «Desde tu celular»; teléfono: «Desde otro celular» | `#wa-option-qr` |
| QR | SVG del servidor, `role="img"`, `aria-label="Código QR para abrir el chat en tu teléfono"`, texto «Escanea el código con la cámara de tu celular y se abre el chat.» | `[data-testid=wa-qr]` |

## Estados

| Estado | Se muestra | No se muestra |
|---|---|---|
| Cargando | Esqueleto de la sección con `aria-busy="true"` | Botón y QR |
| Disponible | Todo lo anterior | — |
| No disponible | «El chat de WhatsApp no está disponible en este momento» y enlace «Habla con Valer-IA aquí» a `/agente` | Botón, QR, estado del canal |
| Error de red o respuesta inesperada (p. ej., un backend viejo que devuelve la página) | El mismo aviso, el enlace al Agente y un botón «Reintentar» | Botón y QR |

## Otros

- Faq: la respuesta de «¿Puedo usarla por WhatsApp?» enlaza a `/whatsapp` («Ve a la pestaña WhatsApp»).
- Movimiento reducido: sin animación de entrada.
- Accesibilidad: contraste AA, foco visible, axe sin violaciones serias, sin desplazamiento horizontal de 360 a 1920.
