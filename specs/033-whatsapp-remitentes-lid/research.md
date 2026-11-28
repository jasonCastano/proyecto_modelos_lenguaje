# Research: cuentas de WhatsApp identificadas solo por ID (spec 033)

Fuentes revisadas: el código instalado de `@openclaw/whatsapp` 2026.11.10 (`dist/.setup/monitor-*.mjs`,
`normalize-target-*.mjs`, `targets-runtime-*.mjs`, `send-*.mjs`), la beta `2026.12.1-beta.1` (descargada en el
scratchpad, solo lectura), el registro del gateway del 2026-11-27 y la carpeta `credentials/whatsapp/default`
(solo nombres).

## R1. Dónde se pierde el mensaje

- **Decision**: el punto de falla es el normalizador de entrada:
  - `const from = group ? remoteJid : await socketSession.resolveInboundJid(remoteJid);`
  - si `from` es nulo y `remoteJid` termina en `@lid` o `@hosted.lid`, lanza
    `Error("WhatsApp inbound LID identity unavailable")`;
  - la cola durable (`whatsapp ingress drain`) reintenta con espera creciente y nunca entrega.

  `resolveInboundJid` solo traduce el LID si existe `lid-mapping-<lid>_reverse.json` o si Baileys lo conoce
  (`signalRepository.lidMapping.getPNForLID`).
- **Rationale**: es lo que muestra el registro (`spooled update … failed; keeping for retry`). El 2026-11-27 a las
  20:34:58 se creó la sesión `tctoken-…@lid` sin archivo de equivalencia. Los números nuevos de la spec 031 sí
  la tuvieron (archivos `lid-mapping-*` de las 15:40).
- **Alternatives considered**: ninguna; el diagnóstico es directo.

## R2. ¿Se puede contestar usando el ID?

- **Decision**: sí, para el texto.
  - El mensaje armado conserva `platform.chatJid = inbound.remoteJid` (el `…@lid`).
  - La respuesta (`platform.reply`) se envía a ese `chatJid` por el socket de Baileys 7, que ya direcciona por LID.
  - Basta con que el normalizador no descarte el mensaje.
- **Rationale**:
  - El acceso usa `from` como identidad. Con `dmPolicy: "open"` y `allowFrom: ["*"]` se admite cualquier
    remitente.
  - Con `"allowlist"` un `…@lid` no coincide con ningún número y queda bloqueado (FR-009, sin cambios).
- **Alternatives considered**: pedirle el número a WhatsApp (no hay consulta pública LID → número: es justamente
  la privacidad del número); guardar contactos (manual, descartado en la spec).
- **Riesgo residual**: se confirma con una cuenta real en el quickstart (spec: verificación temprana).

## R3. Segundo defecto: la salida convierte el ID en un número falso

- **Decision**: parchear también `normalizeWhatsAppTarget`.
  - Hoy `extractUserJidPhone` acepta `(\d+)@lid` y `normalizeE164` lo convierte en `+<lid>`: un número que no
    existe.
  - La nota de voz del puente usa el adaptador saliente con `to: senderId`, así que iría a ese número falso.
  - El parche devuelve `<lid>@lid` intacto. `toWhatsappJid` ya respeta los valores con `@`.
- **Rationale**: sin esto, la US2 (voz) falla, o envía a un destino incorrecto, que es peor.
- **Alternatives considered**: enviar la voz por el `sendMedia` del mensaje entrante (no está al alcance del hook
  `before_dispatch`); responder solo texto a estas cuentas (incumple FR-002).

## R4. Cómo aplicar el cambio sobre un componente de terceros

- **Decision**: un parche versionado en el repositorio, `openclaw/patches/whatsapp-lid.mjs` (Node, sin
  dependencias).
  - **Ubicación**: localiza la instalación del plugin en `$OPENCLAW_STATE_DIR/npm/projects/openclaw-whatsapp-*/
    node_modules/@openclaw/whatsapp`.
  - **Versión**: verifica `package.json` → `2026.11.10`.
  - **Reemplazos**: aplica dos reemplazos anclados en texto exacto, cada uno con conteo esperado igual a 1.
  - **Marca**: deja la marca `/* valeria-lid v1 */`.
  - **Idempotente**: si la marca ya está, no hace nada.
  - **Respaldo**: guarda copia `.orig` del archivo antes de cambiarlo.
  - **Fallo**: si los anclajes no aparecen, termina con un error explicativo y no toca nada.
  - **Integración**: `openclaw_env.ps1 -Install` lo ejecuta después de instalar o enlazar plugins y antes de
    arrancar el gateway. `--check` solo informa el estado.
- **Rationale**:
  - FR-012: reproducible en el equipo principal y en el de respaldo; una reinstalación lo revierte, y `-Install`
    lo restablece.
  - Anclajes exactos: si OpenClaw cambia el código, el parche no adivina; avisa.
- **Alternatives considered**:
  - `patch-package`: requiere un proyecto npm propio; el plugin vive en el estado de OpenClaw.
  - Hacer un fork del plugin: costoso y frágil antes de la sustentación.
  - Editar a mano: incumple FR-012.

## R5. Versión nativa futura

- **Decision**: el estado del soporte se clasifica en tres valores:
  - **`nativo`**: el archivo del normalizador ya no contiene el `throw` de LID. El parche no se aplica y
    `ops check` lo reporta en verde.
  - **`parcheado`**: la marca `valeria-lid v1` está en los dos archivos.
  - **`ausente`**: el `throw` sigue y no hay marca. `ops check` falla con la instrucción de ejecutar `-Install`.
- **Rationale**: FR-013 y el caso límite de la spec.

## R6. Identidad y privacidad del ID en el backend

- **Decision**:
  - **Formato**: `identity.normalize_sender` acepta `^\d{5,20}@(lid|hosted\.lid)$` y lo normaliza a
    `lid:<dígitos>`.
  - **Seudónimo**: `pseudonym` aplica el mismo HMAC con la sal, así que queda `wa-<16 hex>` estable. No colisiona
    con un número porque la entrada lleva el prefijo `lid:`.
  - **Máscara**: `mask` muestra `ID ••••1234`.
  - **Puente**: `voiceCommandArgs` (respaldo por CLI) acepta `…@lid`, y `maskDigits` ya oculta los dígitos en los
    logs.
- **Rationale**: FR-003 y FR-004. El ID es un identificador personal; se trata como el número (regla 10).
- **Alternatives considered**: un prefijo de seudónimo distinto (`wl-`): rompería listas y comandos que esperan
  `wa-`, sin beneficio.

## R7. Mensajes retenidos y antigüedad

- **Decision**: el backend descarta los mensajes cuyo `received_at` (marca del mensaje original, que el plugin ya
  envía) tenga más de `stale_minutes` (15, en `[channels]`).
  - El mensaje se responde con `status: "ignored"` y `event: "stale"`, y queda registrado sin datos.
  - Los mensajes retenidos menos tiempo se responden normalmente, una sola vez: la deduplicación por
    `message_id` ya existe.
- **Rationale**: FR-010 sin tocar la cola de OpenClaw; además protege de cualquier otra entrega tardía.
- **Alternatives considered**: purgar la cola de OpenClaw (interno y frágil).

## R8. Equivalencia ID ↔ número

- **Decision**: no se unifican identidades en el backend.
  - Cuando OpenClaw conoce la equivalencia, ya entrega el número, y la persona queda con su seudónimo por número.
  - Si una persona pasa de ID a número, puede abrir una conversación nueva con presentación (spec 032).
- **Rationale**: FR-015 es SHOULD. Unificar exigiría guardar la relación ID ↔ número, un dato personal adicional.
- **Alternatives considered**: tabla de equivalencias seudonimizadas (posible después de la sustentación).

## R9. Medición y operación

- **Decision**:
  - **Registro**: `ChannelLogRecord.sender_kind` con valores `phone` o `lid` (FR-014).
  - **Operación**: `pml channels block|unblock --pseudonym wa-…` (FR-008).
  - **Verificación**: `ops check` suma la comprobación `soporte-lid`.
  - **Documentación**: la guía de respaldo, `docs/despliegue.md` y `docs/manual_whatsapp.md` documentan el
    parche y la verificación.
- **Rationale**: FR-008, FR-013, FR-014 y FR-016.
