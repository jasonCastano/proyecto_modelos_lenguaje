/**
 * Voz del agente (spec 016, contracts/ui-voice.md).
 *
 * - `SentenceSegmenter` corta en oraciones completas el texto que llega por streaming.
 * - `VoicePlayer` pide cada oración a `POST /api/tts` (hasta 2 en vuelo) y las reproduce en orden con
 *   Web Audio. Una sola sesión suena a la vez; `stop()` corta el audio y aborta las peticiones.
 * La limpieza del texto (citas, Markdown, marcas) la hace el servidor.
 */
import { request } from "./api";
import type { AnalyserLike } from "./lipsync";
import { ApiClientError, type VoiceStatus } from "./types";

export const MAX_SEGMENT_CHARS = 600;
/**
 * El primer segmento de cada respuesta se limita para que su audio llegue pronto (SC-001): Phonon
 * tarda ~12 ms por carácter en CPU; los siguientes se sintetizan mientras suena el anterior.
 */
export const FIRST_SEGMENT_CHARS = 120;
const MAX_IN_FLIGHT = 2;
const ABBREVIATIONS = new Set([
  "sr",
  "sra",
  "srta",
  "dr",
  "dra",
  "etc",
  "ej",
  "núm",
  "art",
  "av",
  "ing",
  "lic",
  "pág",
]);
const END = /([.!?…;]+)(?=\s)|\n\s*\n/g;

function isAbbreviation(chunk: string, following: string): boolean {
  const words = chunk.replace(/\.+$/, "").trim().split(/\s+/);
  const word = words[words.length - 1] ?? "";
  const last = word.toLowerCase();
  if (!last) return false;
  if (ABBREVIATIONS.has(last)) return true;
  if (word === "No" && /^\s*\d/.test(following)) return true;
  return last.length === 1 && /\p{L}/u.test(last);
}

function splitLong(sentence: string, maxChars: number): string[] {
  const parts: string[] = [];
  let rest = sentence;
  while (rest.length > maxChars) {
    const window = rest.slice(0, maxChars);
    let cut = Math.max(window.lastIndexOf(", "), window.lastIndexOf("; "));
    if (cut <= 0) cut = window.lastIndexOf(" ");
    cut = cut <= 0 ? maxChars : cut + 1;
    parts.push(rest.slice(0, cut).trim());
    rest = rest.slice(cut).trim();
  }
  if (rest) parts.push(rest);
  return parts;
}

/** Segmentador incremental: misma regla que `voice/text.py::split_sentences`. */
export class SentenceSegmenter {
  private buffer = "";
  private emitted = 0;

  constructor(
    private readonly maxChars = MAX_SEGMENT_CHARS,
    private readonly firstMaxChars = FIRST_SEGMENT_CHARS,
  ) {}

  private split(sentence: string): string[] {
    const clean = sentence.replace(/\s+/g, " ").trim();
    if (!clean) return [];
    let parts: string[];
    if (this.emitted === 0 && clean.length > this.firstMaxChars) {
      const [head, ...rest] = splitLong(clean, this.firstMaxChars);
      const tail = rest.join(" ");
      parts = [head, ...(tail ? splitLong(tail, this.maxChars) : [])];
    } else {
      parts = splitLong(clean, this.maxChars);
    }
    this.emitted += parts.length;
    return parts;
  }

  /** Acumula `chunk` y devuelve las oraciones que quedaron completas. */
  push(chunk: string): string[] {
    this.buffer += chunk;
    const sentences: string[] = [];
    let start = 0;
    let pending = "";
    END.lastIndex = 0;
    for (let match = END.exec(this.buffer); match; match = END.exec(this.buffer)) {
      const end = match[1] ? match.index + match[1].length : match.index + match[0].length;
      const candidate = pending + this.buffer.slice(start, end);
      const following = this.buffer.slice(end);
      if (match[1] === ".") {
        // Sin texto después no sabemos si es abreviatura con número («No. 3»): esperamos.
        if (!/\S/.test(following)) break;
        if (isAbbreviation(candidate, following)) {
          pending = candidate;
          start = end;
          continue;
        }
      }
      start = end;
      pending = "";
      if (candidate.trim()) sentences.push(candidate.trim());
    }
    this.buffer = pending + this.buffer.slice(start);
    return sentences.flatMap((sentence) => this.split(sentence));
  }

  /** Spec 021: una oración ya cerrada por el servidor; solo se parte si es muy larga. */
  sentence(text: string): string[] {
    return this.split(text);
  }

  /** Devuelve lo pendiente al terminar el turno. */
  flush(): string[] {
    const rest = this.buffer;
    this.buffer = "";
    return this.split(rest);
  }
}

/** Texto comparable entre el streaming y la respuesta final: sin citas ni espacios repetidos. */
export function normalizeForCompare(text: string): string {
  return text
    .replace(/\[\s*U\d+(?:\s*[,;]\s*U\d+)*\s*\]/gi, " ")
    .replace(/\s+/g, " ")
    .trim()
    .toLowerCase();
}

export function getVoiceStatus(): Promise<VoiceStatus> {
  return request<VoiceStatus>("/voice");
}

export interface SpeechRequest {
  text: string;
  threadId: string | null;
  segment: number;
  voice?: string | null;
}

/** Pide una oración a `POST /api/tts`. `null` = nada pronunciable (204). */
export async function fetchSpeech(input: SpeechRequest, signal?: AbortSignal): Promise<ArrayBuffer | null> {
  const response = await fetch("/api/tts", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      text: input.text,
      thread_id: input.threadId,
      segment: input.segment,
      voice: input.voice ?? null,
    }),
    signal,
  });
  if (response.status === 204) return null;
  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as {
      error?: { code: string; message: string; retryable: boolean; action: string };
    } | null;
    throw new ApiClientError(
      payload?.error ?? {
        code: response.status === 503 ? "voice_unavailable" : "voice_error",
        message: "La voz no está disponible.",
        retryable: response.status !== 503,
        action: response.status === 503 ? "continuar sin voz" : "reintentar",
      },
    );
  }
  return response.arrayBuffer();
}

export interface AudioContextLike {
  state: string;
  destination: unknown;
  currentTime: number;
  /** Spec 017: frecuencia del contexto (para las bandas del lip-sync). */
  sampleRate?: number;
  resume(): Promise<void>;
  decodeAudioData(data: ArrayBuffer): Promise<unknown>;
  createBufferSource(): AudioSourceLike;
  /** Spec 017: analizador intercalado entre la voz y los parlantes. */
  createAnalyser?(): AnalyserNodeLike;
}

export interface AnalyserNodeLike extends AnalyserLike {
  smoothingTimeConstant: number;
  connect(destination: unknown): unknown;
}

export interface VoiceAnalyser {
  node: AnalyserLike;
  sampleRate: number;
}

export interface AudioSourceLike {
  buffer: unknown;
  onended: (() => void) | null;
  connect(destination: unknown): unknown;
  start(when?: number): void;
  stop(when?: number): void;
}

export interface VoicePlayerOptions {
  createContext?: () => AudioContextLike | null;
  fetcher?: typeof fetchSpeech;
  now?: () => number;
  onSpeaking?: (speaking: boolean) => void;
  onFirstAudio?: (sessionKey: string, ms: number) => void;
  onUnavailable?: (detail: string) => void;
  onBlocked?: (blocked: boolean) => void;
}

interface QueueItem {
  segment: number;
  text: string;
  closedAt: number;
  audio?: Promise<ArrayBuffer | null>;
}

interface Session {
  key: string;
  threadId: string | null;
  items: QueueItem[];
  fetched: number;
  played: number;
  finished: boolean;
  playing: boolean;
  firstAudioReported: boolean;
  controller: AbortController;
  source: AudioSourceLike | null;
  segmenter: SentenceSegmenter;
  enqueuedText: string;
}

/** Crea un `AudioContext` del navegador, o `null` si no existe (jsdom, navegadores viejos). */
export function browserAudioContext(): AudioContextLike | null {
  const Ctor =
    (globalThis as { AudioContext?: new () => AudioContextLike }).AudioContext ??
    (globalThis as { webkitAudioContext?: new () => AudioContextLike }).webkitAudioContext;
  return Ctor ? new Ctor() : null;
}

export class VoicePlayer {
  private context: AudioContextLike | null = null;
  private analyserNode: AnalyserNodeLike | null = null;
  private analyserFailed = false;
  private session: Session | null = null;
  private counter = 0;
  private readonly options: Required<Omit<VoicePlayerOptions, "createContext">> & {
    createContext: () => AudioContextLike | null;
  };

  constructor(options: VoicePlayerOptions = {}) {
    this.options = {
      createContext: options.createContext ?? browserAudioContext,
      fetcher: options.fetcher ?? fetchSpeech,
      now: options.now ?? (() => performance.now()),
      onSpeaking: options.onSpeaking ?? (() => undefined),
      onFirstAudio: options.onFirstAudio ?? (() => undefined),
      onUnavailable: options.onUnavailable ?? (() => undefined),
      onBlocked: options.onBlocked ?? (() => undefined),
    };
  }

  /**
   * Spec 017: analizador único del contexto (fftSize 1024), conectado a los parlantes. Cada
   * oración pasa por él, así el avatar mide exactamente lo que suena. `null` si no se puede.
   */
  analyser(): VoiceAnalyser | null {
    const node = this.ensureAnalyser();
    const context = this.context;
    if (!node || !context) return null;
    return { node, sampleRate: context.sampleRate ?? 48_000 };
  }

  private ensureAnalyser(): AnalyserNodeLike | null {
    if (this.analyserNode || this.analyserFailed) return this.analyserNode;
    const context = this.ensureContext();
    if (!context?.createAnalyser) {
      this.analyserFailed = true;
      return null;
    }
    try {
      const node = context.createAnalyser();
      node.fftSize = 1024;
      node.smoothingTimeConstant = 0.5;
      node.connect(context.destination);
      this.analyserNode = node;
    } catch {
      this.analyserFailed = true;
    }
    return this.analyserNode;
  }

  /** ¿El navegador puede reproducir audio? */
  supported(): boolean {
    return this.ensureContext() !== null;
  }

  private ensureContext(): AudioContextLike | null {
    if (!this.context) {
      try {
        this.context = this.options.createContext();
      } catch {
        this.context = null;
      }
    }
    return this.context;
  }

  /** Reanuda el contexto (llamar dentro de un gesto del usuario). */
  async unlock(): Promise<boolean> {
    const context = this.ensureContext();
    if (!context) return false;
    try {
      if (context.state === "suspended") await context.resume();
    } catch {
      // se informa abajo
    }
    const blocked = context.state === "suspended";
    this.options.onBlocked(blocked);
    return !blocked;
  }

  get speaking(): boolean {
    return Boolean(this.session && (this.session.playing || this.session.played < this.session.items.length));
  }

  get activeKey(): string | null {
    return this.session?.key ?? null;
  }

  /** Abre una sesión nueva (detiene la anterior) y devuelve su clave. */
  start(threadId: string | null): string {
    this.stop();
    this.counter += 1;
    this.session = {
      key: `voz-${this.counter}`,
      threadId,
      items: [],
      fetched: 0,
      played: 0,
      finished: false,
      playing: false,
      firstAudioReported: false,
      controller: new AbortController(),
      source: null,
      segmenter: new SentenceSegmenter(),
      enqueuedText: "",
    };
    return this.session.key;
  }

  setThread(threadId: string | null): void {
    if (this.session) this.session.threadId = threadId;
  }

  /** Texto nuevo del streaming. */
  push(chunk: string): void {
    const session = this.session;
    if (!session || session.finished) return;
    for (const sentence of session.segmenter.push(chunk)) this.enqueue(session, sentence);
  }

  /** Spec 021: oración revisada (evento ``sentence``); se encola sin esperar texto nuevo. */
  pushSentence(text: string): void {
    const session = this.session;
    if (!session || session.finished) return;
    for (const part of session.segmenter.sentence(text)) this.enqueue(session, part);
  }

  /**
   * Fin del turno: si la respuesta final coincide con lo recibido, se lee lo pendiente; si no
   * (respuesta descartada, respaldo, ruta clásica sin tokens), se corta y se lee la final (R3).
   */
  finish(finalAnswer: string | null): void {
    const session = this.session;
    if (!session) return;
    const rest = session.segmenter.flush();
    const combined = [session.enqueuedText, ...rest].join(" ");
    const final = (finalAnswer ?? "").trim();
    if (!final || normalizeForCompare(final) === normalizeForCompare(combined)) {
      for (const sentence of rest) this.enqueue(session, sentence);
      session.finished = true;
      this.pump(session);
      return;
    }
    this.speakText(final, session.threadId, session.key);
  }

  /** Lee un texto completo en una sesión nueva («Escuchar» o corrección). */
  speakText(text: string, threadId: string | null, key?: string): string {
    const sessionKey = this.start(threadId);
    const session = this.session as Session;
    if (key) session.key = key;
    for (const sentence of session.segmenter.push(`${text} `)) this.enqueue(session, sentence);
    for (const sentence of session.segmenter.flush()) this.enqueue(session, sentence);
    session.finished = true;
    this.pump(session);
    return key ?? sessionKey;
  }

  /** Corta el audio y cancela lo pendiente (< 0,5 s). */
  stop(): void {
    const session = this.session;
    if (!session) return;
    this.session = null;
    session.controller.abort();
    try {
      session.source?.stop();
    } catch {
      // ya terminó
    }
    session.source = null;
    this.options.onSpeaking(false);
  }

  private enqueue(session: Session, text: string): void {
    session.items.push({ segment: session.items.length, text, closedAt: this.options.now() });
    session.enqueuedText = `${session.enqueuedText} ${text}`.trim();
    this.pump(session);
  }

  private pump(session: Session): void {
    if (this.session !== session) return;
    while (session.fetched < session.items.length && session.fetched - session.played < MAX_IN_FLIGHT) {
      const item = session.items[session.fetched];
      item.audio = this.options
        .fetcher(
          { text: item.text, threadId: session.threadId, segment: item.segment },
          session.controller.signal,
        )
        .catch((error: unknown) => {
          if (error instanceof ApiClientError && error.apiError.code === "voice_unavailable") {
            this.stop();
            this.options.onUnavailable(error.apiError.message);
          }
          return null; // otros errores: se salta la oración
        });
      session.fetched += 1;
    }
    if (!session.playing) void this.playNext(session);
  }

  private async playNext(session: Session): Promise<void> {
    if (this.session !== session || session.playing) return;
    const item = session.items[session.played];
    if (!item) {
      if (session.finished) this.options.onSpeaking(false);
      return;
    }
    if (!item.audio) return;
    session.playing = true;
    const data = await item.audio;
    const context = this.ensureContext();
    if (this.session !== session) return;
    if (!data || !context) {
      session.playing = false;
      session.played += 1;
      this.pump(session);
      return;
    }
    try {
      const buffer = await context.decodeAudioData(data);
      if (this.session !== session) return;
      const source = context.createBufferSource();
      source.buffer = buffer;
      source.connect(this.ensureAnalyser() ?? context.destination);
      source.onended = () => {
        if (this.session !== session) return;
        session.source = null;
        session.playing = false;
        session.played += 1;
        this.pump(session);
      };
      session.source = source;
      source.start();
      this.options.onSpeaking(true);
      if (!session.firstAudioReported) {
        session.firstAudioReported = true;
        this.options.onFirstAudio(session.key, Math.max(0, this.options.now() - session.items[0].closedAt));
      }
      if (context.state === "suspended") this.options.onBlocked(true);
    } catch {
      session.playing = false;
      session.played += 1;
      this.pump(session);
    }
  }
}
