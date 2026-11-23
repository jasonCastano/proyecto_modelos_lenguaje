/**
 * Dictado por voz (spec 023): utilidades sin estado de React.
 *
 * - `encodeWav16k`: bloques Float32 del micrófono → WAV PCM16 mono a 16 kHz (research R5).
 * - `EndpointDetector`: nivel de voz y fin de habla por energía (research R6).
 * - `echoSimilarity` / `isEcho`: guarda de eco del modo manos libres (research R10).
 * - `DictationError` y `ERROR_MESSAGES`: errores tipados con su mensaje en español (contracts/ui.md §3).
 */

export const TARGET_RATE = 16_000;

/** Concatena bloques, remuestrea linealmente a 16 kHz y codifica WAV PCM16 mono. */
export function encodeWav16k(
  chunks: Float32Array | Float32Array[],
  sampleRate: number,
): ArrayBuffer {
  const blocks = Array.isArray(chunks) ? chunks : [chunks];
  const total = blocks.reduce((sum, block) => sum + block.length, 0);
  const source = new Float32Array(total);
  let offset = 0;
  for (const block of blocks) {
    source.set(block, offset);
    offset += block.length;
  }
  const count = sampleRate === TARGET_RATE ? total : Math.round((total * TARGET_RATE) / sampleRate);
  const buffer = new ArrayBuffer(44 + count * 2);
  const view = new DataView(buffer);
  const write = (at: number, text: string) => {
    for (let i = 0; i < text.length; i += 1) view.setUint8(at + i, text.charCodeAt(i));
  };
  write(0, "RIFF");
  view.setUint32(4, 36 + count * 2, true);
  write(8, "WAVE");
  write(12, "fmt ");
  view.setUint32(16, 16, true);
  view.setUint16(20, 1, true); // PCM
  view.setUint16(22, 1, true); // mono
  view.setUint32(24, TARGET_RATE, true);
  view.setUint32(28, TARGET_RATE * 2, true);
  view.setUint16(32, 2, true);
  view.setUint16(34, 16, true);
  write(36, "data");
  view.setUint32(40, count * 2, true);
  const ratio = total > 1 && count > 1 ? (total - 1) / (count - 1) : 0;
  for (let i = 0; i < count; i += 1) {
    const position = i * ratio;
    const left = Math.floor(position);
    const right = Math.min(left + 1, total - 1);
    const weight = position - left;
    const value = total ? source[left] * (1 - weight) + source[right] * weight : 0;
    const clipped = Math.max(-1, Math.min(1, value));
    view.setInt16(44 + i * 2, Math.round(clipped < 0 ? clipped * 32768 : clipped * 32767), true);
  }
  return buffer;
}

export type EndReason = "manual" | "silence" | "limit" | "cancel" | "hidden";

export interface EndpointOptions {
  silenceMs: number;
  minSpeechMs: number;
  maxSeconds: number;
  /** Tiempo inicial para medir el ruido de fondo. */
  calibrationMs?: number;
  /** Umbral mínimo de RMS para considerar que hay voz. */
  minThreshold?: number;
}

export interface EndpointUpdate {
  /** Nivel de voz 0–100 para el medidor. */
  level: number;
  rms: number;
  speaking: boolean;
  /** Fin automático (`silence` o `limit`), o `null` si sigue escuchando. */
  done: EndReason | null;
}

export function rmsOf(block: Float32Array): number {
  if (!block.length) return 0;
  let sum = 0;
  for (let i = 0; i < block.length; i += 1) sum += block[i] * block[i];
  return Math.sqrt(sum / block.length);
}

/** Detector de fin de habla por energía (research R6): umbral = ruido de fondo × 3. */
export class EndpointDetector {
  readonly options: Required<EndpointOptions>;
  elapsedMs = 0;
  speechMs = 0;
  silenceMs = 0;
  private noise: number[] = [];
  private threshold: number;

  constructor(options: EndpointOptions) {
    this.options = { calibrationMs: 300, minThreshold: 0.015, ...options };
    this.threshold = this.options.minThreshold;
  }

  get currentThreshold(): number {
    return this.threshold;
  }

  /** Continúa una voz que ya empezó (interrupción en manos libres): sin recalibrar. */
  seed(speechMs: number, threshold: number): void {
    this.speechMs = speechMs;
    this.elapsedMs = Math.max(this.elapsedMs, this.options.calibrationMs) + speechMs;
    this.threshold = Math.max(this.options.minThreshold, threshold);
  }

  push(block: Float32Array, blockMs: number): EndpointUpdate {
    const rms = rmsOf(block);
    this.elapsedMs += blockMs;
    if (this.elapsedMs <= this.options.calibrationMs) {
      this.noise.push(rms);
      const mean = this.noise.reduce((sum, value) => sum + value, 0) / this.noise.length;
      this.threshold = Math.max(this.options.minThreshold, mean * 3);
    }
    const speaking = rms >= this.threshold;
    if (speaking) {
      this.speechMs += blockMs;
      this.silenceMs = 0;
    } else if (this.speechMs > 0) {
      this.silenceMs += blockMs;
    }
    let done: EndReason | null = null;
    if (this.elapsedMs >= this.options.maxSeconds * 1000) done = "limit";
    else if (this.speechMs >= this.options.minSpeechMs && this.silenceMs >= this.options.silenceMs)
      done = "silence";
    return { level: Math.min(100, Math.round((rms / 0.25) * 100)), rms, speaking, done };
  }
}

// Palabras funcionales que no distinguen una frase de otra (guarda de eco).
const STOPWORDS = new Set(
  "a al con de del el en es la las lo los me mi no o para por que se si su sus te tu un una y ya".split(" "),
);

function tokens(text: string): string[] {
  return text
    .replace(/\[[A-Z]+\d+\]/g, " ")
    .toLowerCase()
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "")
    .split(/[^a-z0-9ñ]+/)
    .filter((word) => word && !STOPWORDS.has(word));
}

function pairs(words: string[]): string[] {
  return words.slice(1).map((word, index) => `${words[index]} ${word}`);
}

/**
 * Proporción de pares de palabras seguidas de la transcripción que también dijo Valer-IA (0–1).
 * Comparar pares, y no palabras sueltas, evita confundir una pregunta de seguimiento («¿qué produce
 * Manuelita?») con el eco de una respuesta que usó esas mismas palabras en otro orden.
 */
export function echoSimilarity(transcript: string, spoken: string): number {
  const heard = pairs(tokens(transcript));
  if (!heard.length) return 0;
  const said = new Set(pairs(tokens(spoken)));
  return heard.filter((pair) => said.has(pair)).length / heard.length;
}

export const ECHO_THRESHOLD = 0.6;

/** La transcripción repite lo que acaba de decir Valer-IA: no se envía (FR-015). */
export function isEcho(transcript: string, spoken: string | null | undefined): boolean {
  if (!spoken) return false;
  return tokens(transcript).length >= 2 && echoSimilarity(transcript, spoken) > ECHO_THRESHOLD;
}

export type DictationErrorCode =
  | "permission"
  | "no_device"
  | "insecure"
  | "unsupported"
  | "unavailable"
  | "busy"
  | "too_long"
  | "empty"
  | "network"
  | "server";

export const ERROR_MESSAGES: Record<DictationErrorCode, string> = {
  permission:
    "Necesito permiso para usar el micrófono. Puedes habilitarlo en el candado de la barra de direcciones, o escribir tu mensaje.",
  no_device: "No encontré un micrófono conectado. Puedes escribir tu mensaje.",
  insecure: "El micrófono solo funciona en una conexión segura. Puedes escribir tu mensaje.",
  unsupported: "Este navegador no permite usar el micrófono. Puedes escribir tu mensaje.",
  unavailable: "El dictado no está disponible en este momento. Puedes escribir tu mensaje.",
  busy: "El dictado está ocupado; intenta de nuevo en unos segundos.",
  too_long: "Llegaste al límite de 60 segundos; reconocí lo que alcanzaste a decir.",
  empty: "No te entendí, ¿puedes repetirlo?",
  network: "No pude convertir tu voz en texto. Intenta de nuevo o escribe tu mensaje.",
  server: "No pude convertir tu voz en texto. Intenta de nuevo o escribe tu mensaje.",
};

export class DictationError extends Error {
  readonly code: DictationErrorCode;

  constructor(code: DictationErrorCode) {
    super(ERROR_MESSAGES[code]);
    this.name = "DictationError";
    this.code = code;
  }
}

/** Traduce la excepción de `getUserMedia` (FR-002, contracts/ui.md §3). */
export function mediaErrorCode(error: unknown): DictationErrorCode {
  const name = (error as { name?: string } | null)?.name ?? "";
  if (name === "NotAllowedError" || name === "PermissionDeniedError") return "permission";
  if (name === "NotFoundError" || name === "OverconstrainedError" || name === "NotReadableError")
    return "no_device";
  if (name === "SecurityError") return "insecure";
  return "unsupported";
}

/** Traduce el `code` del contrato de `POST /api/stt` (contracts/stt-api.md §2). */
export function apiErrorCode(code: string | undefined): DictationErrorCode {
  switch (code) {
    case "stt_busy":
      return "busy";
    case "stt_unavailable":
      return "unavailable";
    case "stt_too_large":
      return "too_long";
    case "network_error":
      return "network";
    default:
      return "server";
  }
}

/** El navegador permite pedir el micrófono (contexto seguro y `getUserMedia`). */
export function dictationSupported(): boolean {
  if (typeof window === "undefined" || typeof navigator === "undefined") return false;
  return Boolean(window.isSecureContext && navigator.mediaDevices?.getUserMedia);
}
