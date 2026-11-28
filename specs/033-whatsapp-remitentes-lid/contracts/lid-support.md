# Contract: soporte para cuentas de WhatsApp identificadas solo por ID (spec 033)

## 1. Parche `openclaw/patches/whatsapp-lid.mjs`

```text
node openclaw/patches/whatsapp-lid.mjs [--state-dir <dir>] [--check]
```

- **Directorio**: `--state-dir`, o en su defecto `OPENCLAW_STATE_DIR`, o `%USERPROFILE%\.openclaw-valeria`.
- **Búsqueda**: localiza `npm/projects/openclaw-whatsapp-*/node_modules/@openclaw/whatsapp`, lee `package.json` y
  los archivos `dist/.setup/monitor-*.mjs` y `dist/.setup/normalize-target-*.mjs`.
- **Salida**: imprime una línea `soporte-lid: <estado>` (`nativo`, `parcheado`, `aplicado`, `ausente` o
  `sin-plugin`) y termina con código 0 si el estado final es `nativo`, `parcheado` o `aplicado`; 1 en otro caso.
- **`--check`**: solo diagnostica; no escribe.
- **Sin `--check`**:
  - con `version === "2026.11.10"` y los dos anclajes presentes exactamente una vez, guarda `*.orig`, aplica los
    reemplazos y vuelve a leer para confirmar la marca;
  - con otra versión y el `throw` de LID todavía presente, no toca nada y falla con un mensaje claro.

**Reemplazo A** (entrada, `monitor-*.mjs`). Anclaje:

```js
const from = group ? remoteJid : await socketSession.resolveInboundJid(remoteJid);
```

Queda así:

```js
const from = group ? remoteJid : (await socketSession.resolveInboundJid(remoteJid)) ?? (msg.key?.remoteJidAlt ? await socketSession.resolveInboundJid(msg.key.remoteJidAlt) : null) ?? (/^\d+@(lid|hosted\.lid)$/.test(remoteJid) ? remoteJid : null) /* valeria-lid v1 */;
```

**Reemplazo B** (salida, `normalize-target-*.mjs`). Anclaje:

```js
	const phone = extractUserJidPhone(candidate);
	if (phone) {
```

Queda así (los LID se conservan como destino):

```js
	const lidTarget = candidate.match(WHATSAPP_LID_RE); /* valeria-lid v1 */
	if (lidTarget) return `${lidTarget[1]}@lid`;
	const phone = extractUserJidPhone(candidate);
	if (phone) {
```

## 2. `scripts/openclaw_env.ps1 -Install`

Después de copiar la configuración y enlazar `valeria-bridge`, ejecuta `node openclaw\patches\whatsapp-lid.mjs`.
Si termina con un código distinto de 0, muestra la advertencia y sigue: el canal funciona igual para las cuentas
con número. El parche no corre en `-Run` ni en `-Restart`.

## 3. Backend

- **`normalize_sender("123…@lid")`** devuelve `"lid:123…"`; **`pseudonym`** devuelve `wa-<16 hex>`;
  **`mask`** devuelve `"ID ••••1234"`.
- **`POST /api/channels/messages`** acepta `sender` con forma `…@lid`. Si `received_at` tiene más de
  `stale_minutes`, responde `{"status": "ignored", "messages": []}` y registra `event: "stale"`.
- **`ChannelLogRecord.sender_kind`** toma los valores `phone`, `lid` o `telegram`.

## 4. CLI del operador

```text
pml channels block   --pseudonym wa-<16 hex>
pml channels unblock --pseudonym wa-<16 hex>
```

`--sender` y `--pseudonym` son mutuamente excluyentes. `--pseudonym` valida `^wa-[0-9a-f]{16}$`.

## 5. `ops check`

Agrega la comprobación `soporte-lid`, que llama al parche con `--check`. Interpreta los estados `nativo` y
`parcheado` como OK; los demás, como fallo con su instrucción.

## 6. Plugin `valeria-bridge`

`voiceCommandArgs` acepta destinos `^\d{5,20}@(lid|hosted\.lid)$` además de E.164. El envío de voz por el
adaptador recibe el mismo `senderId`, y el parche B evita que se convierta en `+<lid>`.
