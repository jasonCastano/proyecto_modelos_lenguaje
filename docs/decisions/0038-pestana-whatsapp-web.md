# ADR 0038 — Pestaña WhatsApp en la web: enlace al chat de Valer-IA sin número en el repositorio

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-27
- **Autor**: Roberto José Guerrero
- **Relacionadas**:
  - ADR 0028 (OpenClaw y WhatsApp) y ADR 0037 (Valer-IA natural en WhatsApp), que definen el canal;
  - ADR 0035 (frontend profesional, spec 031), cuyo sistema visual sigue la pestaña;
  - `specs/032-pestana-whatsapp-web/` (spec, plan, research, contratos, tareas).

## Contexto

Valer-IA responde por WhatsApp desde una SIM dedicada, pero la web solo lo mencionaba en una pregunta frecuente:
no había forma de pasar de la web al chat. El integrante pidió una pestaña nueva con el enlace al chatbot, con la
skill `design-taste-frontend` y la identidad de la spec 031. La constitución (§9) prohíbe que el número de la SIM
entre al repositorio.

## Decisión

1. **Quinta área `/whatsapp`** en la navegación, con hero «split»: qué es el chat, el modo del canal, el botón
   «Abrir WhatsApp», qué se necesita, la declaración académica y un QR sobre la foto de caña de la spec 031.
2. **El número vive solo en el servidor**: `VALERIA_WHATSAPP_NUMBER` en el `.env` del proyecto, en formato E.164
   con indicativo (`+57` y 10 dígitos). `GET /api/channels/whatsapp`, público y de solo lectura, devuelve los
   enlaces y el QR ya construidos. Cambiar de SIM o pasar al servidor de respaldo es editar el `.env` y reiniciar,
   sin recompilar la web.
3. **Enlace por dispositivo**: WhatsApp Web (`web.whatsapp.com/send`) en el computador y la aplicación
   (`wa.me`) en el teléfono, porque WhatsApp Web no funciona en navegadores móviles. Siempre un enlace normal con
   `target="_blank"` y `rel="noopener noreferrer"`, con el mensaje «Hola, Valer-IA» ya escrito.
4. **QR en el servidor con `segno`** (BSD-3, Python puro, sin dependencias), en SVG y sin servicios externos.
5. **Modo del canal** desde `ops.channel_mode()` (el `.env` del gateway): «Abierto: cualquier número puede
   escribir» o «Solo números de prueba del equipo»; sin `.env` del gateway no se muestra.
6. **Sin número válido no hay enlace**: la pestaña explica que el chat no está disponible y lleva al Agente. Un
   formato inválido se registra como «formato inválido», nunca con el valor.

## Alternativas descartadas

- **Número escrito en el código o en la web compilada**: viola la constitución §9 y obliga a recompilar al cambiar
  de SIM.
- **Reutilizar `/api/channels/status`**: exige token y loopback; no sirve para el navegador.
- **Solo `wa.me`**: en el computador muestra una página intermedia antes de WhatsApp Web.
- **Biblioteca de QR en la web o un servicio de QR en línea**: suma peso a la web o envía el número a terceros.

## Consecuencias

- El número es visible para quien abre el chat, porque WhatsApp lo muestra; es el número público del proyecto.
  No queda en Git ni en registros, y una prueba revisa que el código y la configuración no tengan números móviles
  colombianos.
- Cada servidor (el principal y el de respaldo) necesita su línea `VALERIA_WHATSAPP_NUMBER`.
- La versión en inglés de la pestaña queda para la spec 033.
