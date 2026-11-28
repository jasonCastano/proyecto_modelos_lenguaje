# Contract: entrega y uso activo de stickers (spec 037)

## 1. Plugin `valeria-bridge` (`openclaw/plugins/valeria-bridge/index.ts`)

```ts
type StickerRoute = "compartido" | "parche" | "import";

interface ListenerLookup {
  listener: WhatsAppListenerLike | null;
  route: StickerRoute | null;
  reason?: "sin-listener";
}

// Orden: runtime compartido → símbolo global del parche → import directo (vía de la spec 034).
export async function findWhatsAppListener(
  channelRuntime: ChannelRuntimeLike | undefined,
  accountId?: string,
): Promise<ListenerLookup>;
```

- **`register(api)`**:
  - guarda `api.runtime?.channel`;
  - a los 30 s del arranque, y cada vez que no haya vía, escribe la línea de arranque (data-model §6).
- **`stickerSender`**: devuelve `{ ok: boolean; route?: StickerRoute; reason?: string }`.
  - `deliverSticker` registra `enviado` o `no enviado` con el nombre del archivo, sin la ruta completa.
  - Nunca lanza.
- **Símbolo del parche**: `Symbol.for("valeria.whatsapp.channelRuntime")` en `globalThis`, con el objeto
  `channelRuntime` del componente.

## 2. Parche opcional (`openclaw/patches/whatsapp-sticker.mjs`)

- **Uso**: `node openclaw/patches/whatsapp-sticker.mjs [--check] [--state <dir>]`.
- **Qué busca**: en `npm/projects/openclaw-whatsapp-*/node_modules/@openclaw/whatsapp/dist/.setup/runtime-*.mjs`,
  la línea ancla `const setWhatsAppRuntime = runtimeStore.setRuntime;`.
- **Qué hace**: la reemplaza por un `setWhatsAppRuntime` que, además, publica `runtime.channel` en el símbolo global.
  Agrega el marcador `/* valeria-sticker v1 */`.
- **Códigos de salida**: 0 aplicado o ya aplicado; 3 ancla no encontrada (no se toca nada); 2 componente no
  instalado. `--check` solo informa.

## 3. Backend: política (`channels/stickers.py`)

```python
PRIORITY = (
    "profile_saved",
    "action_done",
    "closing",
    "thanks",
    "greeting_first_contact",
    "greeting_new_conversation",
    "greeting_mid",
    "assent",
    "useful_answer",
)
REPEATABLE = {"valeria-pulgar", "valeria-lindo-dia"}


def situations_of(signals: TurnSignals) -> list[str]: ...
def choose(signals, usage, catalog, config) -> StickerChoice | None: ...


OPT_OUT: re.Pattern[str]  # «sin stickers», «no me mandes stickers», «no more stickers»
```

`StickerChoice` incluye `situation`. `ChannelStore.record_sticker(thread, name, turn, situation)`,
`ChannelStore.set_stickers_off(thread)` y `sticker_usage(...)` devuelven `last_sticker`, `last_situation` y `off`.

## 4. `ops check` (`src/proyecto_modelos_lenguaje/ops.py`)

`stickers_today(journal_path, gateway_log_dir, day) -> CheckResult` devuelve `elegidos`, `entregados`, `fallidos`,
`motivo` y el estado (rojo, amarillo o verde). La salida JSON gana `stickers_today`.
