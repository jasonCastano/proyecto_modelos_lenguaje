// Lógica pura del puente OpenClaw → Valer-IA (spec 024 y spec 028, contracts/channel-api-v2.md §4).
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
  /** Spec 029: el mensaje trajo un adjunto de audio (visto en `message_received`). */
  voice?: boolean;
}

/** Adjunto de un mensaje entrante como lo entrega el hook `message_received` de OpenClaw. */
export interface MediaFact {
  contentType?: string;
  kind?: string;
  transcribed?: boolean;
}

/** Claves para cruzar `message_received` con `before_dispatch`: id del mensaje y sesión + contenido. */
export function voiceKeys(event: {
  messageId?: string;
  sessionKey?: string;
  content?: string;
}): string[] {
  const keys: string[] = [];
  if (event.messageId) keys.push(`id:${event.messageId}`);
  if (event.sessionKey) keys.push(`sc:${event.sessionKey}:${(event.content ?? "").trim().slice(0, 200)}`);
  return keys;
}

/** Spec 029: ¿algún adjunto es audio (nota de voz)? */
export function hasAudio(media: MediaFact[] | undefined): boolean {
  return (media ?? []).some(
    (fact) =>
      (fact.kind ?? "").toLowerCase() === "audio" ||
      (fact.contentType ?? "").toLowerCase().startsWith("audio/"),
  );
}

/**
 * Spec 029: `before_dispatch` no trae los adjuntos y, con la transcripción de OpenClaw, su `content` es solo el
 * texto transcrito. `message_received` sí trae los adjuntos y se emite antes: aquí se recuerda qué mensajes
 * llegaron con audio (por id, con vencimiento) para tratarlos como nota de voz.
 */
export class VoiceMemory {
  private readonly ids = new Map<string, number>();
  private readonly ttlMs: number;
  private readonly max: number;
  private readonly now: () => number;

  constructor(ttlMs = 10 * 60 * 1000, max = 500, now: () => number = Date.now) {
    this.ttlMs = ttlMs;
    this.max = max;
    this.now = now;
  }

  remember(keys: string[]): void {
    const now = this.now();
    for (const [key, at] of this.ids) {
      if (now - at > this.ttlMs || this.ids.size >= this.max) this.ids.delete(key);
    }
    for (const key of keys) this.ids.set(key, now);
  }

  /** ¿Alguna clave es de un mensaje con audio? La clave se consume para no afectar a otro mensaje. */
  take(keys: string[]): boolean {
    let found = false;
    for (const key of keys) {
      const at = this.ids.get(key);
      if (at !== undefined && this.now() - at <= this.ttlMs) found = true;
      this.ids.delete(key);
    }
    return found;
  }

  private peek(keys: string[]): boolean {
    return keys.some((key) => {
      const at = this.ids.get(key);
      return at !== undefined && this.now() - at <= this.ttlMs;
    });
  }

  /** Espera breve por si `message_received` aún no terminó de registrarse. */
  async waitFor(keys: string[], graceMs = 300, stepMs = 25): Promise<boolean> {
    for (let waited = 0; waited < graceMs && !this.peek(keys); waited += stepMs) {
      await new Promise((resolve) => setTimeout(resolve, stepMs));
    }
    return this.take(keys);
  }
}

export interface BridgeConfig {
  backendUrl: string;
  token: string;
  timeoutMs: number;
  channels: string[];
  debug?: boolean;
}

export interface DispatchResult {
  handled: boolean;
  text?: string;
}

export interface VoiceNote {
  audio_path: string;
  language?: string;
  duration_ms?: number;
  mime?: string;
}

interface BackendReply {
  status?: string;
  messages?: string[];
  /** Spec 030: solo el bloque de fuentes, para acompañar una nota de voz entregada. */
  sources_messages?: string[];
  voice?: VoiceNote | null;
}

type Fetch = (url: string, init: RequestInit) => Promise<Response>;
// Envía una nota de voz al remitente (spec 028); la implementa index.ts con el adaptador saliente
// del canal y, como respaldo, el CLI de OpenClaw.
// Spec 030: devuelve `true` si la nota de voz quedó entregada (decide qué texto la acompaña).
export type VoiceSender = (channel: string, target: string, audioPath: string) => Promise<boolean>;

/** Oculta secuencias largas de dígitos (números de teléfono) antes de escribirlas en el log. */
export function maskDigits(text: string): string {
  return text.replace(/\d{5,}/g, "#");
}

const MEDIA = /^\s*<media:(image|video|audio|document|sticker|location)[^>]*>\s*$/i;
// Spec 029 (R1): OpenClaw arma «[Audio]\nUser text:\n…\nTranscript:\n<texto>» (formatMediaUnderstandingBody)
// y puede anteponer un encabezado del mensaje (con el número del remitente) o dejar el bloque solo en `body`.
// La voz se reconoce en CUALQUIER posición de `content` o `body` y al backend solo viaja la transcripción.
const AUDIO_MARK = /\[audio(?:\s+\d+\/\d+)?\]/i;
const TRANSCRIPT_MARK = /(?:^|\n)[ \t]*(?:transcript|transcripci[oó]n)[ \t]*:[ \t]*/gi;
const MEDIA_AUDIO_ANY = /<media:audio[^>]*>/i;
const MEDIA_ANY = /<media:[a-z]+[^>]*>/gi;
const SECTION_HEADER = /\n[ \t]*\[[^\]\n]{1,40}\][ \t]*(?:\n|$)/;
const USER_TEXT_LABEL = /^[ \t]*user text[ \t]*:[ \t]*$/i;
// Encabezado del gateway al inicio («[WhatsApp +57 … 2026-11-27 10:08]»): nunca viaja al backend.
const ENVELOPE = /^\s*\[[^\]\n]*(?:whatsapp|\+?\d[\d\s-]{6,})[^\]\n]*\]\s*/i;
const TRANSCRIPT_LABEL = /^\s*(?:transcript(?:ion)?|transcripci[oó]n|user text|texto)\s*:\s*/i;
const HANDLED_STATUSES = new Set([
  "answered",
  "pending_approval",
  "approval_resolved",
  "unsupported",
  "busy",
  "error",
]);

function hasVoiceMarks(text: string): boolean {
  TRANSCRIPT_MARK.lastIndex = 0;
  return AUDIO_MARK.test(text) || MEDIA_AUDIO_ANY.test(text) || TRANSCRIPT_MARK.test(text);
}

export function messageKind(text: string): string {
  if (hasVoiceMarks(text)) return "audio";
  const match = MEDIA.exec(text);
  if (!match) return "text";
  return match[1].toLowerCase();
}

/** Texto que sigue a la última etiqueta «Transcript:», hasta la siguiente sección «[…]». */
function afterLastTranscript(text: string): string | null {
  let last: RegExpExecArray | null = null;
  TRANSCRIPT_MARK.lastIndex = 0;
  for (let match = TRANSCRIPT_MARK.exec(text); match; match = TRANSCRIPT_MARK.exec(text)) last = match;
  if (!last) return null;
  const rest = text.slice(last.index + last[0].length);
  const end = rest.search(SECTION_HEADER);
  return end >= 0 ? rest.slice(0, end) : rest;
}

function clean(text: string): string {
  return text.replace(MEDIA_ANY, " ").replace(/\s+/g, " ").trim();
}

/** Transcripción de una nota de voz ("" si OpenClaw no pudo transcribirla). */
export function transcriptOf(text: string): string {
  if (MEDIA.test(text)) return "";
  const labelled = afterLastTranscript(text);
  if (labelled !== null) return clean(labelled);
  const mark = AUDIO_MARK.exec(text);
  const tail = mark ? text.slice(mark.index + mark[0].length) : text.replace(ENVELOPE, "");
  const lines = tail
    .split(/\r?\n/)
    .filter((line) => !USER_TEXT_LABEL.test(line))
    .map((line) => line.replace(TRANSCRIPT_LABEL, ""));
  return clean(lines.join(" "));
}

/** Decide si el mensaje es una nota de voz mirando `content` y `body`, y extrae solo la transcripción. */
export function detectVoice(content: string, body: string): { voice: boolean; transcript: string } {
  const voice = hasVoiceMarks(content) || hasVoiceMarks(body);
  if (!voice) return { voice: false, transcript: "" };
  for (const source of [content, body]) {
    const labelled = afterLastTranscript(source);
    if (labelled !== null && clean(labelled)) return { voice: true, transcript: clean(labelled) };
  }
  // Sin etiqueta: si `content` ya es la transcripción (sin marcas), se usa tal cual.
  if (content && !hasVoiceMarks(content)) return { voice: true, transcript: clean(content.replace(ENVELOPE, "")) };
  return { voice: true, transcript: transcriptOf(content || body) };
}

/** Forma del texto para depurar sin exponerlo: longitud y posición de las marcas (spec 029, T005). */
export function shapeOf(label: string, text: string): string {
  TRANSCRIPT_MARK.lastIndex = 0;
  const transcript = TRANSCRIPT_MARK.exec(text);
  const audio = AUDIO_MARK.exec(text);
  const media = MEDIA_AUDIO_ANY.exec(text);
  const envelope = ENVELOPE.test(text);
  return (
    `${label}: len=${text.length}, [Audio]@${audio ? audio.index : -1}, ` +
    `Transcript:@${transcript ? transcript.index : -1}, media@${media ? media.index : -1}, ` +
    `encabezado=${envelope ? "sí" : "no"}`
  );
}

export function buildRequest(event: DispatchEvent): Record<string, unknown> | null {
  const channel = (event.channel ?? "").toLowerCase();
  if (!event.senderId || event.isGroup) return null;
  const content = (event.content ?? "").trim();
  const rawBody = (event.body ?? "").trim();
  const detected = detectVoice(content, rawBody);
  // Texto escrito: `content` (sin el encabezado del gateway); `body` solo si no hay `content`.
  const typed = (content || rawBody).replace(ENVELOPE, "").trim();
  const voice = detected.voice || Boolean(event.voice);
  // Con el adjunto de audio y sin marcas, `content` ya es la transcripción (o vacío si no se pudo transcribir).
  const transcript = detected.voice ? detected.transcript : MEDIA.test(typed) ? "" : clean(typed);
  const kind = voice ? "audio" : messageKind(typed);
  const fallbackId = `${event.sessionKey ?? event.senderId}:${event.timestamp ?? Date.now()}`;
  const body: Record<string, unknown> = {
    channel,
    message_id: (event.messageId ?? fallbackId).slice(0, 128),
    sender: event.senderId,
    kind,
    text: kind === "text" ? typed.slice(0, 4000) : null,
    received_at: new Date(event.timestamp ?? Date.now()).toISOString(),
  };
  if (kind === "audio") {
    body.input_mode = "voice";
    body.text = transcript.slice(0, 4000) || null;
  }
  return body;
}

export function toResult(payload: BackendReply): DispatchResult {
  if (payload.status === "ignored") return { handled: true };
  if (!payload.status || !HANDLED_STATUSES.has(payload.status)) {
    throw new Error(`estado desconocido del backend: ${payload.status}`);
  }
  const text = (payload.messages ?? []).filter((m) => m.trim()).join("\n\n");
  return text ? { handled: true, text } : { handled: true };
}

/**
 * Envía el mensaje al backend y devuelve la respuesta para el canal.
 * Si la respuesta trae una nota de voz, la envía primero (spec 028) y después devuelve el texto.
 * `undefined` deja seguir el despacho normal de OpenClaw (modo degradado: agente nativo + MCP).
 */
export async function dispatch(
  event: DispatchEvent,
  config: BridgeConfig,
  fetchImpl: Fetch = fetch,
  log: (message: string) => void = () => {},
  sendVoice?: VoiceSender,
): Promise<DispatchResult | undefined> {
  const channel = (event.channel ?? "").toLowerCase();
  if (!config.channels.includes(channel)) return undefined;
  if (config.debug) {
    // Solo durante la prueba técnica (VALERIA_BRIDGE_DEBUG=1): nunca dejarlo activo.
    log(
      `valeria-bridge: forma ${shapeOf("content", event.content ?? "")} · ` +
        `${shapeOf("body", event.body ?? "")} · audio adjunto=${event.voice ? "sí" : "no"}`,
    );
  }
  const body = buildRequest(event);
  if (body === null) return undefined;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), config.timeoutMs);
  let payload: BackendReply;
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
    payload = (await response.json()) as BackendReply;
  } catch (error) {
    log(`valeria-bridge: backend no disponible (${String(error)}); modo degradado`);
    return undefined;
  } finally {
    clearTimeout(timer);
  }
  let result: DispatchResult;
  try {
    result = toResult(payload);
  } catch (error) {
    log(`valeria-bridge: ${String(error)}; modo degradado`);
    return undefined;
  }
  const audio = payload.voice?.audio_path;
  if (!audio || !sendVoice || !event.senderId) return result;
  let delivered = false;
  try {
    delivered = await sendVoice(channel, event.senderId, audio);
  } catch (error) {
    // El texto se entrega igual: la voz nunca impide responder.
    log(`valeria-bridge: no se pudo enviar la nota de voz (${maskDigits(String(error)).slice(0, 160)})`);
  }
  return withVoiceText(payload, result, delivered, log);
}

/**
 * Spec 030: con la nota de voz entregada, por escrito van solo las fuentes (o nada); si no se entregó,
 * la respuesta completa. Un backend anterior sin `sources_messages` conserva la respuesta completa.
 */
export function withVoiceText(
  payload: BackendReply,
  full: DispatchResult,
  delivered: boolean,
  log: (message: string) => void = () => {},
): DispatchResult {
  if (!delivered) {
    log("valeria-bridge: voz no entregada; texto completo");
    return full;
  }
  if (!Array.isArray(payload.sources_messages)) return full;
  const text = payload.sources_messages.filter((m) => m.trim()).join("\n\n");
  log(`valeria-bridge: voz entregada; texto: ${text ? "solo fuentes" : "sin texto"}`);
  return text ? { handled: true, text } : { handled: true };
}

export function resolveConfig(
  raw: Record<string, unknown> | undefined,
  env: Record<string, string | undefined>,
): BridgeConfig {
  const backendUrl = String(raw?.backendUrl ?? env.VALERIA_BACKEND_URL ?? "http://127.0.0.1:8000");
  const timeoutMs = Number(raw?.timeoutMs ?? 90000);
  const channels = Array.isArray(raw?.channels) ? (raw.channels as string[]) : ["whatsapp", "telegram"];
  const token = env.VALERIA_CHANNEL_TOKEN ?? "";
  if (!/^https?:\/\/(127\.0\.0\.1|localhost|\[::1\])(:\d+)?$/.test(backendUrl.replace(/\/$/, ""))) {
    throw new Error("valeria-bridge: backendUrl debe ser loopback (127.0.0.1, localhost o ::1)");
  }
  const debug = ["1", "true", "yes"].includes((env.VALERIA_BRIDGE_DEBUG ?? "").toLowerCase());
  return { backendUrl, token, timeoutMs, channels: channels.map((c) => c.toLowerCase()), debug };
}

/** Argumentos del CLI de OpenClaw para enviar una nota de voz (sin shell: sin inyección). */
export function voiceCommandArgs(channel: string, target: string, audioPath: string): string[] {
  if (!/^[+\w@.:-]{3,80}$/.test(target)) throw new Error("destinatario inválido");
  return ["message", "send", "--channel", channel, "--target", target, "--media", audioPath];
}
