# Contract: stickers en el canal de WhatsApp (spec 034)

## 1. Backend: decisión (`channels/stickers.py`)

```python
@dataclass(frozen=True)
class StickerChoice:
    name: str
    path: Path
    position: Literal["before", "after"]

def load_catalog(path: Path = CONFIG_DIR / "stickers.toml") -> StickerCatalog
def situation_of(signals: TurnSignals) -> Situation | None
def choose(signals: TurnSignals, usage: ThreadUsage, catalog: StickerCatalog,
           config: ChannelsConfig) -> StickerChoice | None
```

`TurnSignals` reúne:

- `status`, `event` y `route`;
- `act` y `sentiment` (`turn.route`);
- `notices` (contiene `sensitive_data`);
- `language`, `conversation_start` e `introduced`;
- `approved_action`: `save_preference`, `forget` u otra;
- `text`, el mensaje de la persona, solo para el léxico de asentimiento; no se guarda.

`ThreadUsage` reúne `answered_turns`, `last_sticker_turn` y `sent`, la lista de nombres ya enviados en el hilo.

Orden de reglas: research R4. La función es pura y no tiene red.

## 2. `ChannelBridge`

- Después de armar la respuesta atendida (y de la presentación de la spec 038), llama a `choose`.
- Si hay elección, la guarda en `channel_stickers` y fija `reply.sticker`.
- Incrementa `answered_turns` del hilo con cada respuesta atendida.
- `_resolve`, cuando una aprobación se ejecuta, deja en la respuesta el `approved_action` para la decisión.

## 3. API: `POST /api/channels/messages`

La respuesta agrega `"sticker": {"name", "path", "position"} | null`. Los demás campos no cambian; un cliente que
ignore el campo sigue funcionando.

## 4. Plugin `valeria-bridge`

```ts
export type StickerSender = (channel: string, target: string, stickerPath: string) => Promise<boolean>;
```

- **`index.ts`**: `stickerSender` ubica `light-runtime-api.js` de `@openclaw/whatsapp` (mismo patrón de rutas que
  el parche de la spec 033) e importa `getActiveWebListener`. Con el listener, llama a
  `listener.sendSticker(target, await readFile(stickerPath))`. Si no hay listener o la llamada falla, devuelve
  `false` sin lanzar. El log no lleva el destinatario (`maskDigits`).
- **`dispatch`**, el orden de envío:
  - `position: "before"`: sticker, luego voz si la hay, luego texto;
  - `position: "after"`: voz si la hay, luego el texto retornado y el sticker con `setTimeout(1500)`, sin
    esperar.
- **«Pensando»**:
  - antes del `fetch` al backend arma `setTimeout(stickerThinkingMs)`; si vence, envía `valeria-pensando.webp`;
  - máximo uno cada 10 minutos por `senderId`, en memoria;
  - se cancela al llegar la respuesta;
  - si la respuesta es `ignored`, no hay diferencia, porque ya se envió o no se envía.
- **Configuración del plugin**: `stickersDir` y `stickerThinkingMs` (con 0 se desactiva).

## 5. `ops check`

Agrega `stickers` con dos detalles posibles:

- «N/9 disponibles», con ✅ si el interruptor está activo y hay al menos 1;
- «apagados», cuando el interruptor está desactivado (✅ informativo).

Un archivo faltante o inválido aparece en el detalle por nombre, sin fallar la comprobación salvo que no quede
ninguno.
