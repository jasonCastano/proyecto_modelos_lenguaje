// Spec 037: búsqueda del listener activo de WhatsApp para enviar stickers nativos.
//
// OpenClaw guarda el runtime de cada plugin por instancia (AsyncLocalStorage): si este plugin importa el
// componente de WhatsApp y llama a `getActiveWebListener()`, la función lee el slot de *este* plugin y
// devuelve `null` (causa raíz de la spec 034, research R1). Por eso se prueban, en orden:
//   1. «compartido»: el registro de contextos del runtime de canales que el gateway comparte con los
//      plugins (`api.runtime.channel.runtimeContexts`, capacidad `connection-controller`);
//   2. «parche»: el runtime de canales que publica el parche `openclaw/patches/whatsapp-sticker.mjs`
//      en `globalThis[Symbol.for("valeria.whatsapp.channelRuntime")]`;
//   3. «import»: la vía de la spec 034 (por si una versión futura comparte el runtime).
// Nunca lanza: sin vía devuelve `{ listener: null, route: null, reason }`.

export interface WhatsAppListenerLike {
  sendSticker?: (to: string, buffer: Buffer, options?: { mimetype?: string }) => Promise<unknown>;
}

interface ConnectionControllerLike {
  getActiveListener?: () => WhatsAppListenerLike | null | undefined;
}

export interface ChannelRuntimeLike {
  runtimeContexts?: {
    get?: (query: { channelId: string; accountId?: string; capability: string }) => unknown;
  };
}

export type StickerRoute = "compartido" | "parche" | "import";

export interface ListenerLookup {
  listener: WhatsAppListenerLike | null;
  route: StickerRoute | null;
  reason?: string;
  /** Diagnóstico sin datos personales: qué vía se probó y qué encontró. */
  detail: string[];
}

export const PATCH_SYMBOL = Symbol.for("valeria.whatsapp.channelRuntime");
const CAPABILITY = "connection-controller";
const ACCOUNT_IDS: (string | undefined)[] = ["default", undefined];

function fromRuntime(
  runtime: ChannelRuntimeLike | undefined,
  accountIds: (string | undefined)[],
  detail: string[],
  label: string,
): WhatsAppListenerLike | null {
  const get = runtime?.runtimeContexts?.get;
  if (typeof get !== "function") {
    detail.push(`${label}: sin registro de contextos`);
    return null;
  }
  for (const accountId of accountIds) {
    let controller: ConnectionControllerLike | undefined;
    try {
      controller = get.call(runtime?.runtimeContexts, {
        channelId: "whatsapp",
        accountId,
        capability: CAPABILITY,
      }) as ConnectionControllerLike | undefined;
    } catch {
      controller = undefined;
    }
    const listener = controller?.getActiveListener?.() ?? null;
    if (listener?.sendSticker) {
      detail.push(`${label}: listener (cuenta ${accountId ?? "sin cuenta"})`);
      return listener;
    }
    detail.push(`${label}: ${controller ? "controlador sin listener" : "sin controlador"} (cuenta ${accountId ?? "sin cuenta"})`);
  }
  return null;
}

export async function findWhatsAppListener(
  channelRuntime: ChannelRuntimeLike | undefined,
  options: {
    accountId?: string;
    importListener?: () => Promise<WhatsAppListenerLike | null>;
    globals?: Record<symbol, unknown>;
  } = {},
): Promise<ListenerLookup> {
  const detail: string[] = [];
  const accounts = options.accountId ? [options.accountId, ...ACCOUNT_IDS] : ACCOUNT_IDS;
  const shared = fromRuntime(channelRuntime, accounts, detail, "compartido");
  if (shared) return { listener: shared, route: "compartido", detail };
  const globals = options.globals ?? (globalThis as unknown as Record<symbol, unknown>);
  const patched = globals[PATCH_SYMBOL] as ChannelRuntimeLike | undefined;
  if (patched) {
    const listener = fromRuntime(patched, accounts, detail, "parche");
    if (listener) return { listener, route: "parche", detail };
  } else {
    detail.push("parche: no instalado");
  }
  if (options.importListener) {
    try {
      const listener = await options.importListener();
      if (listener?.sendSticker) return { listener, route: "import", detail };
      detail.push("import: sin listener");
    } catch {
      detail.push("import: error");
    }
  }
  return { listener: null, route: null, reason: "sin-listener", detail };
}
