# ADR 0039 — Respuesta a cuentas de WhatsApp identificadas solo por ID: parche versionado del componente

- **Estado**: propuesta (requiere la aprobación de ambos integrantes, constitución §11)
- **Fecha**: 2026-11-27
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**:
  - ADR 0028 (OpenClaw con un solo agente y plugin puente);
  - ADR 0037 (Valer-IA natural y con voz por WhatsApp; SIM dedicada);
  - `specs/031-valeria-cualquier-numero/` (canal abierto);
  - `specs/033-whatsapp-remitentes-lid/` (spec, plan, research R1–R9, contrato, tareas).

## Contexto

WhatsApp identifica a cada cuenta con un ID interno (LID, `…@lid`). Cuando además comparte la equivalencia con el
número de teléfono, OpenClaw la guarda (`lid-mapping-*.json`) y trabaja con el número. Algunas cuentas llegan solo
con el ID, sin esa equivalencia; ocurrió el 2026-11-27 con un número nuevo de prueba. Ahí el componente
`@openclaw/whatsapp` 2026.11.10 falla de dos maneras:

1. **Entrada**: lanza `WhatsApp inbound LID identity unavailable` y deja el mensaje en una cola de reintentos
   indefinida. El mensaje nunca llega al plugin `valeria-bridge`, y la persona no recibe nada.
2. **Salida**: `normalizeWhatsAppTarget` convierte `<lid>@lid` en `+<lid>`, un número que no existe. Una nota de
   voz enviada a esa cuenta iría a ese destino falso.

La beta `2026.12.1-beta.1` (publicada el 2026-11-27) tiene el mismo código. Con el canal abierto a cualquier número
(spec 031), parte del público quedaría sin respuesta, y guardar contactos a mano en el teléfono de la SIM no escala.

## Decisión

1. **Parche versionado y anclado** en `openclaw/patches/whatsapp-lid.mjs` (Node, sin dependencias), con dos
   reemplazos de texto exacto y la marca `/* valeria-lid v1 */`:
   - **entrada** (`monitor-*.mjs`): si no hay número, intenta `remoteJidAlt` y, si tampoco hay, usa el propio
     `…@lid` como identidad. La respuesta de texto ya vuelve al `chatJid` de origen;
   - **salida** (`normalize-target-*.mjs`): conserva `<lid>@lid` como destino.

   Solo actúa sobre la versión 2026.11.10 y cuando cada anclaje aparece exactamente una vez; si no, no escribe
   nada y lo explica. Es idempotente y guarda `*.orig`.
2. **Aplicación reproducible**: lo ejecuta `scripts/openclaw_env.ps1 -Install` en el equipo principal y en el de
   respaldo. Nunca se edita a mano la instalación.
3. **Verificación**: `uv run pml ops check` muestra `soporte-lid` como parcheado, nativo o ausente. Una
   reinstalación o actualización del componente que pierda el parche aparece en rojo, con la instrucción para
   aplicarlo.
4. **Privacidad**: el backend acepta `…@lid`, lo normaliza a `lid:<dígitos>` y lo seudonimiza con la misma sal
   (`wa-<16 hex>`), con máscara `ID ••••1234`. El registro solo guarda el tipo de remitente
   (`sender_kind`: phone o lid).
5. **Entregas tardías**: el backend descarta como `stale` los mensajes con más de `stale_minutes` (15) y menos de un
   día. Una marca más vieja o futura se considera inconsistente y se atiende.
6. **Operación**: `pml channels block|unblock --pseudonym wa-…` permite bloquear cuentas sin número conocido.

## Alternativas consideradas

- **Guardar contactos en el teléfono de la SIM**: manual y no escala.
- **Responder solo texto a estas cuentas**: incumple el servicio por voz (spec 028).
- **Fork del componente o `patch-package`**: costoso y frágil antes de la sustentación; el componente vive en el
  estado de OpenClaw, no en un proyecto npm propio.
- **Esperar la corrección oficial**: no existe ni en la beta.

## Consecuencias

- Las cuentas que WhatsApp entrega solo con su ID reciben el mismo servicio (texto, voz, presentación, límites y
  bloqueo).
- Una persona que pase de ID a número puede abrir otra conversación, que se presenta según la spec 038. No se
  guarda la equivalencia ID ↔ número.
- El modo cerrado no admite cuentas solo con ID, porque no coinciden con los números autorizados.
- **Riesgo**: una actualización del componente revierte el parche. Mitigación: `ops check` lo detecta e
  `-Install` lo restablece; si cambia el código, el parche no adivina.
- **Salida**: cuando OpenClaw corrija el defecto, `ops check` reporta «nativo del componente», el parche se aparta
  solo y puede retirarse del repositorio.
- Reportar el defecto al proyecto OpenClaw es deseable; requiere autorización del equipo.
