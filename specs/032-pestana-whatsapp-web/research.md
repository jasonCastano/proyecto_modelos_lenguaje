# Research: Pestaña «WhatsApp» (spec 032)

Fecha: 2026-11-27. No quedan aclaraciones abiertas: Q1 y Q2 se resolvieron con el integrante en la spec.

## R1. Cómo llega el número a la web

- **Decision**: el backend lee `VALERIA_WHATSAPP_NUMBER` del entorno (el `.env` del proyecto, que ya carga
  `serve_backend.ps1`) y expone `GET /api/channels/whatsapp`, público y sin token, con los enlaces y el QR ya
  construidos. La web lo pide al montar la página.
- **Rationale**: el número no entra a Git ni a la web compilada (constitución §9). Cambiar de SIM o pasar al
  servidor de respaldo es editar el `.env` y reiniciar, sin recompilar (decisión Q1 = A).
- **Alternatives considered**: inyectarlo al compilar con una variable de Vite (obliga a recompilar en cada
  servidor); reutilizar `/api/channels/status` (exige `X-Channel-Token` y loopback: no sirve para el navegador).

## R2. Validación del número

- **Decision**: E.164 estricto, `^\+[1-9]\d{7,14}$`, igual que `WA_ALLOW_*`. Para Colombia: `+57` y 10 dígitos. Se
  quitan espacios al leer; cualquier otro carácter invalida. El enlace usa solo los dígitos.
- **Rationale**: WhatsApp necesita el indicativo; un número mal escrito daría un chat inexistente (SC-004).
- **Alternatives considered**: aceptar números sin `+` y suponer `57` (adivina y puede abrir el chat de otra persona).

## R3. Enlaces: computador y teléfono

- **Decision**:
  - computador: `https://web.whatsapp.com/send?phone=<dígitos>&text=<mensaje codificado>`;
  - teléfono y QR: `https://wa.me/<dígitos>?text=<mensaje codificado>`;
  - la web elige con `navigator.userAgentData.mobile` y, si no existe, con el agente de usuario
    (`Android|iPhone|iPad|iPod|Mobile`). El botón es un `<a target="_blank" rel="noopener noreferrer">`.
- **Rationale**: WhatsApp Web no funciona en navegadores móviles (decisión Q2 = A). Un enlace normal no lo bloquea
  el navegador.
- **Alternatives considered**: solo `wa.me` (en computador muestra una página intermedia); `whatsapp://send`
  (falla sin la app instalada y no tiene respaldo).

## R4. Código QR

- **Decision**: `segno` en el backend genera un SVG del enlace `wa.me` (corrección de errores M, borde de 4
  módulos, color tinta `#14240f` sobre blanco). Se entrega como texto en el JSON y la web lo inserta.
- **Rationale**: Python puro, BSD-3, sin dependencias; ya se usó con autorización en la spec 030. Ningún servicio
  externo recibe el número (FR-006).
- **Alternatives considered**: biblioteca JS `qrcode` (suma peso a la web); servicios de QR en línea (filtran el
  número).

## R5. Modo del canal

- **Decision**: reutilizar `ops.channel_mode()`, que lee `WA_DM_POLICY` del `.env` del gateway. Se traduce a
  `open`, `closed` o `unknown` (sin `.env` del gateway, como en un equipo de desarrollo).
- **Rationale**: una sola fuente de verdad, ya probada en `ops check`; no muestra números.
- **Alternatives considered**: una variable nueva en el `.env` del proyecto (duplicaría el modo y se desincroniza).

## R6. Mensaje sugerido

- **Decision**: «Hola, Valer-IA» fijo en español, codificado en la URL. La versión en inglés queda para la spec 033.

## R7. Diseño (skill `design-taste-frontend`)

- **Decision**: una sección por pantalla con hero `split`, igual que la entrada:
  - izquierda: h1 «Habla con Valer-IA por WhatsApp», lead con lo que se puede preguntar, estado del canal, botón
    verde «Abrir WhatsApp», qué se necesita y la declaración académica;
  - derecha: el QR en una tarjeta blanca sobre la foto de caña de la spec 031 (stand-in con licencia, ya citada en
    `CREDITOS.md`);
  - entrada con `data-enter`, sin momento nuevo; ícono real de WhatsApp (`/media/iconos/whatsapp.svg`, CC0, ya
    versionado) junto al botón.
- **Rationale**: misma identidad de la spec 031; la página es corta y un solo propósito.
- **Alternatives considered**: tarjeta dentro de la entrada (el integrante pidió una pestaña).

## R8. Constitución y ADR

- **Decision**: enmienda **MINOR 2.10.0** en §3.7 (quinta área, endpoint público del enlace, `segno`) y ADR 0038.
  Requiere la aprobación de ambos integrantes en el PR.
