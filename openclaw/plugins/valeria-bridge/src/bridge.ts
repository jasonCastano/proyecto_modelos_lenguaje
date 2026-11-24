// Lógica pura del puente OpenClaw → Valer-IA (spec 024, contracts/channel-api.md §4).
// Sin dependencias del SDK para poder probarla con `node --test`.

export interface DispatchEvent {
  messageId?: string;
  content?: string;
  body?: string;
  channel?: string;
  senderId?: string;
  sessionKey?: string;
  isGroup?: boolean;
  timestamp?: number;
}

export interface BridgeConfig {
  backendUrl: string;
  token: string;
  timeoutMs: number;
  channels: string[];
}

export interface DispatchResult {
  handled: boolean;
  text?: string;
}

type Fetch = (url: string, init: RequestInit) => Promise<Response>;

const MEDIA = /^\s*<media:(image|video|audio|document|sticker|location)[^>]*>\s*$/i;
const HANDLED_STATUSES = new Set([
  "answered",
  "pending_approval",
  "approval_resolved",
  "unsupported",
  "busy",
  "error",
]);

export function messageKind(text: string): string {
  const match = MEDIA.exec(text);
  if (!match) return "text";
  const kind = match[1].toLowerCase();
  return kind === "audio" ? "audio" : kind;
}

export function buildRequest(event: DispatchEvent): Record<string, unknown> | null {
  const channel = (event.channel ?? "").toLowerCase();
  const text = (event.content ?? event.body ?? "").trim();
  if (!event.senderId || event.isGroup) return null;
  const kind = messageKind(text);
  const fallbackId = `${event.sessionKey ?? event.senderId}:${event.timestamp ?? Date.now()}`;
  return {
    channel,
    message_id: (event.messageId ?? fallbackId).slice(0, 128),
    sender: event.senderId,
    kind,
    text: kind === "text" ? text.slice(0, 4000) : null,
    received_at: new Date(event.timestamp ?? Date.now()).toISOString(),
  };
}

export function toResult(payload: { status?: string; messages?: string[] }): DispatchResult {
  if (payload.status === "ignored") return { handled: true };
  if (!payload.status || !HANDLED_STATUSES.has(payload.status)) {
    throw new Error(`estado desconocido del backend: ${payload.status}`);
  }
  const text = (payload.messages ?? []).filter((m) => m.trim()).join("\n\n");
  return text ? { handled: true, text } : { handled: true };
}

/**
 * Envía el mensaje al backend y devuelve la respuesta para el canal.
 * `undefined` deja seguir el despacho normal de OpenClaw (modo degradado: agente nativo + MCP).
 */
export async function dispatch(
  event: DispatchEvent,
  config: BridgeConfig,
  fetchImpl: Fetch = fetch,
  log: (message: string) => void = () => {},
): Promise<DispatchResult | undefined> {
  const channel = (event.channel ?? "").toLowerCase();
  if (!config.channels.includes(channel)) return undefined;
  const body = buildRequest(event);
  if (body === null) return undefined;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.timeoutMs);
  try {
    const response = await fetchImpl(`${config.backendUrl.replace(/\/$/, "")}/api/channels/messages`, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-Channel-Token": config.token },
      body: JSON.stringify(body),
      signal: controller.signal,
    });
    if (!response.ok) {
      log(`valeria-bridge: backend respondió ${response.status}; modo degradado`);
      return undefined;
    }
    return toResult((await response.json()) as { status?: string; messages?: string[] });
  } catch (error) {
    log(`valeria-bridge: backend no disponible (${String(error)}); modo degradado`);
    return undefined;
  } finally {
    clearTimeout(timer);
  }
}

export function resolveConfig(
  raw: Record<string, unknown> | undefined,
  env: Record<string, string | undefined>,
): BridgeConfig {
  const backendUrl = String(raw?.backendUrl ?? env.VALERIA_BACKEND_URL ?? "http://127.0.0.1:8000");
  const timeoutMs = Number(raw?.timeoutMs ?? 45000);
  const channels = Array.isArray(raw?.channels) ? (raw.channels as string[]) : ["whatsapp", "telegram"];
  const token = env.VALERIA_CHANNEL_TOKEN ?? "";
  if (!/^https?:\/\/(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/.test(backendUrl.replace(/\/$/, ""))) {
    throw new Error("valeria-bridge: backendUrl debe ser loopback (127.0.0.1, localhost o ::1)");
  }
  return { backendUrl, token, timeoutMs, channels: channels.map((c) => c.toLowerCase()) };
}
