# Research: stickers que sí llegan y se usan de forma activa (spec 037)

## R1. ¿Por qué no llega ningún sticker?

**Evidencia** (2026-11-28, sin datos personales):

- **Registro del canal**: 79 respuestas; el backend eligió 4 stickers (`valeria-bienvenido` ×2 y
  `valeria-consulta` ×2) y los registró en `channel_stickers`.
- **Registro del gateway** (`~/.openclaw-valeria/tmp/openclaw/openclaw-YYYY-MM-DD.log`): cada intento, incluido
  «Pensando», termina en `valeria-bridge: sticker no enviado (listener no disponible)`.

**Causa raíz**:

- El plugin busca el listener activo así: importa `light-runtime-api.js` del componente
  `@openclaw/whatsapp` y llama a `getActiveWebListener()`.
- Esa función pide el controlador de conexión al **runtime de canales** del componente
  (`getOptionalWhatsAppChannelRuntime()`).
- Ese runtime vive en un `createPluginRuntimeStore`, cuyo «slot» se resuelve por **instancia de plugin**: OpenClaw
  usa un `AsyncLocalStorage` (`getPluginInstanceRuntimeSlot`).
- Llamada desde la instancia de `valeria-bridge`, la función lee el slot de nuestro plugin, que está vacío, y no el
  de WhatsApp. Devuelve `null` siempre.

No es un problema de tiempos ni de conexión. Por diseño, la vía elegida en la spec 034 nunca puede funcionar.

## R2. ¿Cómo obtener el listener activo?

**Hallazgos**:

- El componente registra su controlador con
  `registerChannelRuntimeContext({channelRuntime, channelId: "whatsapp", accountId, capability:
  "connection-controller"})`.
- El controlador expone `getActiveListener()`, que tiene `sendSticker(to, buffer, {mimetype})` (Baileys, mensaje
  `sticker` nativo).
- El registro de contextos (`runtimeContexts`) pertenece al **runtime de canales del gateway**. El administrador de
  canales lo crea una vez y lo pasa a cada cuenta con `createTaskScopedChannelRuntime`, que comparte el registro
  base.
- La API de plugins expone `api.runtime.channel`, con el mismo tipo de superficie (`runtimeContexts.get/register/
  watch`).

**Decisión**: probar las vías en orden y registrar en el log del gateway cuál funcionó:

1. **Runtime compartido** (sin parche): en `register(api)`, guardar `api.runtime?.channel`. Al enviar, pedir
   `runtimeContexts.get({channelId: "whatsapp", accountId, capability: "connection-controller"})` con
   `accountId` ∈ {el de la cuenta del evento, `"default"`, sin cuenta}, y luego `getActiveListener()`.
2. **Respaldo con parche versionado**, con el mismo patrón de la spec 033 (`openclaw/patches/whatsapp-lid.mjs`):
   - el script `openclaw/patches/whatsapp-sticker.mjs` (marcador `/* valeria-sticker v1 */`) modifica el
     `runtime-*.mjs` del componente: `setWhatsAppRuntime` también publica el runtime de canales en
     `globalThis[Symbol.for("valeria.whatsapp.channelRuntime")]`;
   - el plugin lee ese símbolo global, que no depende de la instancia de plugin;
   - el ancla debe coincidir exactamente. Si no coincide, el script no toca nada y lo reporta;
   - es idempotente y `ops check` lo verifica.
3. **Vía actual** (import directo): se conserva al final, por si una versión futura de OpenClaw comparte el
   runtime.

La vía 1 se prueba primero en vivo (T001, con un reinicio del gateway). La vía 2 solo se instala si la 1 no
encuentra el controlador.

**Alternativas descartadas**:

- **Enviar el `.webp` con `openclaw message send --media`**: el componente clasifica `image/webp` como documento
  (`send-*.mjs`: «sticker → document»), así que llegaría como archivo y no como sticker.
- **Abrir una segunda sesión de Baileys**: necesita otra vinculación y rompe la sesión única con la SIM.

## R3. Registro de entrega y estado del canal (FR-003, FR-004)

**Decisión**:

- **Plugin**: escribe en el log del gateway una línea por intento:
  - `valeria-bridge: sticker enviado (<nombre>) vía <ruta>`;
  - o `valeria-bridge: sticker no enviado (<nombre>): <motivo>`.

  El motivo es uno de `sin-listener`, `sin-archivo` o `error`, con los dígitos enmascarados. El texto siempre se
  entrega antes, o igual si el sticker falla.
- **`ops check`**: suma **elegidos** (registro del canal del día, campo `sticker`) y **entregados/fallidos**
  (líneas del log del gateway del día) y muestra `stickers hoy: elegidos N · entregados M · fallidos K (motivo
  principal)`.
  - Está en rojo si N > 0 y M = 0.
  - Está en amarillo si M < N.
  - Al arrancar, el plugin escribe una línea `valeria-bridge: stickers listos vía <ruta>` o `sin vía de stickers`.
    `ops check` la muestra.

**Racional**: no hace falta un endpoint nuevo ni que el backend sepa del gateway. Los dos registros ya existen y no
guardan datos personales.

## R4. Uso activo: situaciones y cadencia

**Decisión**: en `config/stickers.toml` y `channels/stickers.py`:

| Situación | Cuándo | Sticker | Posición |
|---|---|---|---|
| `greeting_first_contact` | presentación de primer contacto | `valeria-bienvenido` | antes |
| `greeting_new_conversation` | presentación tras inactividad o reinicio | `valeria-hola` | antes |
| `greeting_mid` | saludo a mitad de conversación | `valeria-consulta` | después |
| `useful_answer` (nueva) | respuesta respondida con citas, sin respaldo de evidencia insuficiente | `valeria-listo` o `valeria-pulgar`, alternando | después |
| `assent` | «ok», «dale», «perfecto» | `valeria-pulgar` | después |
| `thanks` | agradecimiento | `valeria-gracias` | después |
| `closing` | despedida | `valeria-lindo-dia` | después |
| `profile_saved` / `action_done` | acción completada | `valeria-gracias-confianza` / `valeria-listo` | después |

**Cadencia de `useful_answer`** (FR-005, al menos 1 de cada 3):

- lleva sticker si la respuesta anterior no lo llevó;
- si la anterior lo llevó, se salta;
- con preguntas seguidas, eso da una de cada dos respuestas informativas;
- alterna `valeria-listo` y `valeria-pulgar` según el último usado.

**Moderación** (FR-009):

- un sticker por respuesta y máximo 8 por conversación (`stickers_per_conversation = 8`);
- dos respuestas seguidas pueden llevar sticker si la **situación** cambia;
- el mismo sticker no va dos veces seguidas, salvo el pulgar y `valeria-lindo-dia`;
- se quita la regla «nunca dos respuestas seguidas»;
- `ThreadUsage` gana `last_sticker` y `last_situation`.

**Prioridad**: `profile_saved > action_done > closing > thanks > greeting_first_contact > greeting_new_conversation >
greeting_mid > assent > useful_answer`. Una presentación más una respuesta informativa da un solo sticker, el de
presentación.

## R5. Exclusiones y preferencia (FR-010, FR-012)

**Decisión**:

- **Se mantienen** las exclusiones de la spec 034 (`_excluded`): estado no respondido, evento de error, aviso
  `sensitive_data`, sentimiento negativo y acto `complaint`.
- **Se agregan**:
  - respuestas con respaldo de evidencia insuficiente (`fallback` del turno);
  - crisis (`route == "out_of_scope"` con `scope_reason == "crisis"`);
  - malestar detectado por el léxico `style.LOW_MOOD` de la spec 036.
- **«Sin stickers»** («no me mandes stickers», «sin stickers», «no more stickers»): `ChannelStore` guarda
  `stickers_off` por hilo, como `reply_format`, y `choose` devuelve `None`. El texto de la respuesta no cambia (el
  agente responde normal); una confirmación breve la agrega el canal en ese turno.

## R6. Verificación

**Decisión**:

- **Pruebas unitarias** de `situations_of`, la cadencia, la moderación y las exclusiones, más `stickers_off` en el
  store.
- **Conjunto** `tests/fixtures/channels/stickers.jsonl`, ampliado con conversaciones de uso activo:
  - seis mensajes (saludo, dos preguntas, «ok», «gracias», despedida);
  - tres preguntas seguidas;
  - queja, angustia, datos sensibles, inglés y «sin stickers»;
  - conversación larga de 12 turnos para el máximo.

  Una prueba de API mide SC-002 a SC-005 con el servicio demo.
- **Plugin**: pruebas en `test/bridge.test.ts` del orden de vías con dobles del runtime (registro compartido, símbolo
  global e import) y del formato del log.
- **Parche**: pruebas en `openclaw/patches/test/` (ancla exacta, idempotencia y sin cambios si no coincide), como en
  la spec 033.
- **Prueba en el teléfono** (SC-001, SC-006 y SC-007), con instrucciones previas: reiniciar el gateway y el backend,
  hacer la conversación de seis mensajes y revisar `ops check`.
