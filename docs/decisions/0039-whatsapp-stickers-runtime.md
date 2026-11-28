# ADR 0039 — Stickers nativos por WhatsApp: parche versionado del componente

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-28
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**:
  - ADR 0028 (OpenClaw con un solo agente y plugin puente);
  - ADR 0038 (parche versionado del componente de WhatsApp para cuentas por ID);
  - `specs/034-stickers-whatsapp/` (stickers);
  - `specs/037-stickers-activos/` (spec, plan, research R1–R6, contrato y tareas).

## Contexto

La spec 034 le dio a Valer-IA nueve stickers aprobados. El backend decide cuándo usarlos, y el plugin
`valeria-bridge` debía enviarlos con `sendSticker` del listener activo de WhatsApp. En producción no llegó ninguno:
el 2026-11-28, el backend eligió 4 stickers en 79 respuestas y el gateway no entregó ninguno.

**Diagnóstico** (spec 037, research R1–R2 y pruebas en vivo del 2026-11-28):

1. OpenClaw 2026.11.10 aísla el runtime de cada plugin. El componente `@openclaw/whatsapp` registra su
   controlador de conexión en **su** runtime de canales, que `valeria-bridge` no alcanza. La prueba dio
   «compartido: sin controlador»; un símbolo global publicado por un parche (v1) tampoco fue visible desde el
   plugin, porque los plugins no comparten `globalThis`.
2. Aunque se alcanzara, el listener activo **no expone `sendSticker`**: solo `sendComposingTo`, `sendMessage`,
   `sendPoll` y `sendReaction`. La API de envío interna sí tiene `sendSticker`.
3. Lo que el plugin sí alcanza es el **adaptador de salida del canal** (`runtime.channel.outbound.loadAdapter`),
   con el que ya envía las notas de voz. Pero ese envío clasifica un `.webp` como documento («sticker →
   document»).

## Decisión

1. **Parche versionado y anclado** `openclaw/patches/whatsapp-sticker.mjs` (Node, sin dependencias), con la marca
   `/* valeria-sticker v2 */` y dos reemplazos de texto exacto:
   - **listener** (`monitor-*.mjs`): el listener activo expone `sendSticker` de la API de envío;
   - **envío** (`send-*.mjs`): si el archivo del medio es uno de los stickers aprobados de Valer-IA
     (`…/valeria-<nombre>.webp`), se envía con `sendSticker`; cualquier otro medio sigue exactamente igual.

   Solo actúa sobre la versión 2026.11.10 y si cada anclaje aparece exactamente una vez; si no, no escribe nada y
   sale con 3. Es idempotente, guarda `*.orig` y retira el cambio de la versión 1.
2. **Plugin**: con el parche instalado (la marca se verifica en disco), envía el sticker por el adaptador de salida
   (vía «adaptador»). Sin el parche no lo usa, porque llegaría como documento, y prueba las vías de
   `src/listener.ts`. El texto de la respuesta nunca depende del sticker.
3. **Aplicación reproducible**: `scripts/openclaw_env.ps1 -Install` aplica el parche después de `whatsapp-lid`,
   en el equipo principal y en el de respaldo. Nunca se edita la instalación a mano.
4. **Verificación**:
   - `uv run pml ops check` muestra `soporte-sticker` (las dos partes del parche) y `stickers-hoy` (elegidos,
     entregados y fallidos del día; en rojo si se eligen y no llega ninguno);
   - el log del gateway dice «stickers listos vía adaptador (parche valeria-sticker v2)» al arrancar, y una línea
     por sticker enviado o fallido.

## Alternativas consideradas

- **Medio `.webp` sin parche**: llega como documento, no como sticker.
- **Símbolo global con el runtime de canales (v1)**: los plugins no comparten `globalThis`; descartado tras la
  prueba en vivo.
- **Segunda sesión de Baileys**: requiere otra vinculación o SIM y rompe la sesión única.
- **Fork del componente o `patch-package`**: costoso y frágil antes de la sustentación.

## Consecuencias

- Los stickers elegidos por el backend llegan como stickers nativos con la misma sesión de WhatsApp.
- Solo cambian los envíos de los archivos `valeria-*.webp`; el resto de medios, el texto y las notas de voz siguen
  igual.
- **Riesgo**: una actualización del componente revierte el parche. Mitigación: `ops check` lo detecta e
  `-Install` lo restablece. Si cambia el código, el parche no adivina y los stickers dejan de enviarse, sin afectar
  el texto.
- **Salida**: si OpenClaw expone el envío de stickers a los plugins, el plugin deja de necesitar el parche.
