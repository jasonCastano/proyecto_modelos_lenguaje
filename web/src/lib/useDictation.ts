import { useEffect, useRef, useState, useSyncExternalStore } from "react";

import { getSttStatus, transcribe } from "./api";
import {
  DictationError,
  EndpointDetector,
  apiErrorCode,
  dictationSupported,
  encodeWav16k,
  isEcho,
  mediaErrorCode,
  rmsOf,
  type DictationErrorCode,
  type EndReason,
} from "./dictation";
import { CAPTURE_PROCESSOR, workletUrl } from "./dictation-worklet";
import { ApiClientError, type InputMeta, type SttStatus } from "./types";

/**
 * Dictado por voz (spec 023, data-model §6).
 *
 * Modo normal: pulsar → escuchar → fin (manual, silencio o límite) → texto al campo.
 * Manos libres: el micrófono queda abierto; tras enviar espera la respuesta, la vigila mientras
 * Valer-IA habla (hablar encima la interrumpe) y vuelve a escuchar cuando ella termina.
 */

export const HANDSFREE_KEY = "manuelita.stt.handsfree";
const BARGE_FACTOR = 2;
const BARGE_MS = 250;
const WAITING_GRACE_MS = 3000;
const LEVEL_INTERVAL_MS = 1000 / 15;

export type DictationState =
  | "idle"
  | "requesting"
  | "listening"
  | "processing"
  | "waiting_reply"
  | "speaking";

export interface DictationMessage {
  code: DictationErrorCode;
  text: string;
}

export interface TranscriptInfo {
  reason: EndReason;
}

export interface DictationSnapshot {
  state: DictationState;
  level: number;
  message: DictationMessage | null;
  handsfree: boolean;
}

export interface DictationEnv {
  voiceStop(): void;
  threadId(): string | null;
  onTranscript(text: string, meta: InputMeta, info: TranscriptInfo): void;
  status(): SttStatus | null;
  lastSpoken(): string | null;
  now?(): number;
}

function readHandsfree(): boolean {
  try {
    return window.localStorage.getItem(HANDSFREE_KEY) === "1";
  } catch {
    return false;
  }
}

function writeHandsfree(value: boolean): void {
  try {
    window.localStorage.setItem(HANDSFREE_KEY, value ? "1" : "0");
  } catch {
    // preferencia solo en memoria
  }
}

interface Capture {
  stream: MediaStream;
  context: AudioContext;
  source: MediaStreamAudioSourceNode;
  node: AudioWorkletNode;
}

/** Máquina de estados del dictado, sin React (se prueba empujando bloques de audio). */
export class DictationEngine {
  private snapshot: DictationSnapshot;
  private listeners = new Set<() => void>();
  private capture: Capture | null = null;
  private chunks: Float32Array[] = [];
  private detector: EndpointDetector | null = null;
  private generation = 0;
  private lastLevelAt = 0;
  private bargeMs = 0;
  private idleMs = 0;
  private sawReply = false;
  private waitingSince = 0;
  private busy = false;
  private speaking = false;
  private replies = 0;
  private graceTimer: ReturnType<typeof setTimeout> | null = null;
  private visibility: (() => void) | null = null;

  constructor(private readonly env: DictationEnv) {
    this.snapshot = { state: "idle", level: 0, message: null, handsfree: readHandsfree() };
  }

  // -- suscripción ---------------------------------------------------------------------------
  subscribe = (listener: () => void): (() => void) => {
    this.listeners.add(listener);
    return () => this.listeners.delete(listener);
  };

  getSnapshot = (): DictationSnapshot => this.snapshot;

  private set(patch: Partial<DictationSnapshot>): void {
    this.snapshot = { ...this.snapshot, ...patch };
    this.listeners.forEach((listener) => listener());
  }

  private now(): number {
    return this.env.now ? this.env.now() : performance.now();
  }

  private fail(code: DictationErrorCode): void {
    this.set({ message: { code, text: new DictationError(code).message } });
  }

  clearMessage(): void {
    if (this.snapshot.message) this.set({ message: null });
  }

  // -- acciones del visitante ----------------------------------------------------------------
  /** Botón del micrófono: empieza, o termina la grabación en curso. */
  async toggle(): Promise<void> {
    const { state } = this.snapshot;
    if (state === "listening" || state === "speaking") {
      if (this.snapshot.handsfree && state === "speaking") return;
      this.finish("manual");
      return;
    }
    if (state === "idle") await this.start();
  }

  async start(): Promise<void> {
    if (this.snapshot.state !== "idle") return;
    this.clearMessage();
    this.env.voiceStop(); // FR-013: hablar corta la voz de Valer-IA
    const status = this.env.status();
    if (status && !status.available) {
      this.fail("unavailable");
      return;
    }
    if (!dictationSupported()) {
      this.fail("unsupported");
      return;
    }
    this.set({ state: "requesting", level: 0 });
    const generation = this.generation;
    try {
      await this.open();
    } catch (error) {
      this.teardown();
      this.set({ state: "idle", level: 0 });
      if (this.snapshot.handsfree) this.setHandsfree(false);
      this.fail(error instanceof DictationError ? error.code : mediaErrorCode(error));
      return;
    }
    if (generation !== this.generation) {
      this.teardown(); // se canceló mientras el navegador pedía el permiso
      return;
    }
    this.listen();
  }

  cancel(): void {
    this.finish("cancel");
  }

  setHandsfree(value: boolean): void {
    writeHandsfree(value);
    this.set({ handsfree: value });
    if (!value && this.capture && this.snapshot.state !== "processing") {
      this.teardown();
      this.set({ state: "idle", level: 0 });
    } else if (value && this.snapshot.state === "idle") {
      void this.start();
    }
  }

  /**
   * Estado del chat y de la voz (lo llama el hook en cada render). `replies` cuenta las respuestas
   * terminadas: una respuesta rápida puede no dejar ver nunca `busy = true`.
   */
  update(busy: boolean, speaking: boolean, replies = this.replies): void {
    this.busy = busy;
    this.speaking = speaking;
    const replied = replies !== this.replies;
    this.replies = replies;
    const { state, handsfree } = this.snapshot;
    if (!handsfree || !this.capture) return;
    if (state === "waiting_reply") {
      if (busy || speaking || replied) this.sawReply = true;
      if (speaking) {
        this.monitor();
      } else if (!busy && (this.sawReply || this.now() - this.waitingSince > WAITING_GRACE_MS)) {
        this.listen();
      }
    } else if (state === "speaking" && !speaking && !busy) {
      this.listen();
    } else if (state === "listening" && speaking) {
      this.monitor();
    }
  }

  dispose(): void {
    this.generation += 1;
    this.clearGrace();
    this.teardown();
  }

  private clearGrace(): void {
    if (this.graceTimer) clearTimeout(this.graceTimer);
    this.graceTimer = null;
  }

  // -- captura -------------------------------------------------------------------------------
  private async open(): Promise<void> {
    if (this.capture) return;
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
    });
    const Context =
      window.AudioContext ??
      (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
    if (!Context || typeof AudioWorkletNode === "undefined") {
      stream.getTracks().forEach((track) => track.stop());
      throw new DictationError("unsupported");
    }
    const context = new Context();
    await context.audioWorklet.addModule(workletUrl());
    const source = context.createMediaStreamSource(stream);
    const node = new AudioWorkletNode(context, CAPTURE_PROCESSOR);
    node.port.onmessage = (event: MessageEvent<Float32Array>) => this.onBlock(event.data);
    source.connect(node);
    node.connect(context.destination);
    this.capture = { stream, context, source, node };
    this.visibility = () => {
      if (document.visibilityState === "hidden") this.finish("hidden");
    };
    document.addEventListener("visibilitychange", this.visibility);
  }

  private teardown(): void {
    if (this.visibility) document.removeEventListener("visibilitychange", this.visibility);
    this.visibility = null;
    const capture = this.capture;
    this.capture = null;
    this.chunks = [];
    this.detector = null;
    if (!capture) return;
    capture.node.port.onmessage = null;
    try {
      capture.source.disconnect();
      capture.node.disconnect();
    } catch {
      // ya desconectado
    }
    capture.stream.getTracks().forEach((track) => track.stop());
    void capture.context.close().catch(() => undefined);
  }

  private newDetector(): EndpointDetector {
    const status = this.env.status();
    return new EndpointDetector({
      silenceMs: status?.silence_ms ?? 1500,
      minSpeechMs: status?.min_speech_ms ?? 300,
      maxSeconds: status?.max_seconds ?? 60,
    });
  }

  private listen(): void {
    this.clearGrace();
    this.chunks = [];
    this.detector = this.newDetector();
    this.idleMs = 0;
    this.set({ state: "listening", level: 0 });
  }

  private monitor(): void {
    this.chunks = [];
    this.bargeMs = 0;
    this.set({ state: "speaking", level: 0 });
  }

  /** Un bloque del micrófono (~20 ms). Público para las pruebas. */
  onBlock(block: Float32Array): void {
    const capture = this.capture;
    if (!capture) return;
    const blockMs = (block.length / capture.context.sampleRate) * 1000;
    const { state, handsfree } = this.snapshot;
    if (state === "speaking") {
      // Valer-IA habla: solo una voz claramente más fuerte que el umbral la interrumpe (R10).
      const threshold = (this.detector?.currentThreshold ?? 0.015) * BARGE_FACTOR;
      if (rmsOf(block) >= threshold) {
        this.bargeMs += blockMs;
        this.chunks.push(block);
      } else {
        this.bargeMs = 0;
        this.chunks = [];
      }
      if (this.bargeMs >= BARGE_MS) {
        const spoken = this.chunks;
        const threshold = this.detector?.currentThreshold ?? 0.015;
        this.env.voiceStop();
        this.listen();
        this.chunks = spoken;
        this.detector?.seed(this.bargeMs, threshold);
      }
      return;
    }
    if (state !== "listening" || !this.detector) return;
    this.chunks.push(block);
    const update = this.detector.push(block, blockMs);
    const now = this.now();
    // 15 fps como máximo, salvo saltos grandes (de silencio a voz) que se muestran de inmediato.
    if (
      now - this.lastLevelAt >= LEVEL_INTERVAL_MS ||
      Math.abs(update.level - this.snapshot.level) >= 20
    ) {
      this.lastLevelAt = now;
      this.set({ level: update.level });
    }
    if (handsfree) {
      this.idleMs = this.detector.speechMs > 0 ? 0 : this.idleMs + blockMs;
      const limit = (this.env.status()?.handsfree_idle_seconds ?? 60) * 1000;
      if (this.idleMs >= limit) {
        this.setHandsfree(false); // FR-016: un minuto sin voz apaga el modo
        return;
      }
    }
    if (update.done) this.finish(update.done);
  }

  private finish(reason: EndReason): void {
    const { state, handsfree } = this.snapshot;
    if (state !== "listening" && state !== "speaking" && state !== "requesting") return;
    const capture = this.capture;
    const chunks = this.chunks;
    const sampleRate = capture?.context.sampleRate ?? 48_000;
    if (reason === "cancel" || reason === "hidden") {
      this.generation += 1;
      this.teardown();
      this.set({ state: "idle", level: 0 });
      if (handsfree) this.setHandsfree(false);
      return;
    }
    const speechMs = this.detector?.speechMs ?? 0;
    if (!handsfree) this.teardown();
    else this.chunks = [];
    const audible = chunks.some((chunk) => rmsOf(chunk) > 0.005);
    if (!chunks.length || (speechMs === 0 && !audible)) {
      this.set({ state: handsfree ? "listening" : "idle", level: 0 });
      if (handsfree) this.listen();
      this.fail("empty");
      return;
    }
    const wav = encodeWav16k(chunks, sampleRate);
    this.set({ state: "processing", level: 0 });
    void this.recognize(wav, reason);
  }

  private async recognize(wav: ArrayBuffer, reason: EndReason): Promise<void> {
    const generation = (this.generation += 1);
    try {
      const result = await transcribe(
        new Blob([wav], { type: "audio/wav" }),
        this.env.threadId(),
      );
      if (generation !== this.generation) return; // una grabación más nueva manda
      const { handsfree } = this.snapshot;
      if (result.empty) {
        this.afterResult();
        this.fail("empty");
        return;
      }
      if (handsfree && isEcho(result.text, this.env.lastSpoken())) {
        this.afterResult(); // FR-015: era la voz de Valer-IA
        return;
      }
      const meta: InputMeta = {
        source: "voice",
        audio_ms: result.audio_ms,
        stt_ms: result.stt_ms,
        edited: false,
        handsfree,
      };
      if (handsfree) {
        this.sawReply = false;
        this.waitingSince = this.now();
        this.set({ state: "waiting_reply" });
        // Si no llega ninguna respuesta (envío descartado), vuelve a escuchar.
        this.clearGrace();
        this.graceTimer = setTimeout(() => this.update(this.busy, this.speaking), WAITING_GRACE_MS + 50);
      } else {
        this.set({ state: "idle" });
      }
      this.env.onTranscript(result.text, meta, { reason });
      if (reason === "limit") this.fail("too_long");
    } catch (error) {
      if (generation !== this.generation) return;
      this.afterResult();
      this.fail(error instanceof ApiClientError ? apiErrorCode(error.apiError.code) : "server");
    }
  }

  private afterResult(): void {
    if (this.snapshot.handsfree && this.capture) this.listen();
    else this.set({ state: "idle", level: 0 });
  }
}

export interface DictationControl extends DictationSnapshot {
  supported: boolean;
  status: SttStatus | null;
  toggle(): void;
  cancel(): void;
  setHandsfree(value: boolean): void;
  clearMessage(): void;
}

export interface DictationOptions {
  voice: { stop(): void; speaking: boolean };
  threadId: string | null;
  busy: boolean;
  /** Respuestas terminadas en el chat (manos libres vuelve a escuchar tras cada una). */
  replies?: number;
  /** Texto de la última respuesta que Valer-IA leyó en voz alta (guarda de eco). */
  lastSpoken: string | null;
  onTranscript(text: string, meta: InputMeta, info: TranscriptInfo): void;
}

const STATUS_RETRY_MS = 3000;
const MESSAGE_MS = 6000;

/** Hook del dictado: estado del servidor, máquina de estados y mensajes temporales. */
export function useDictation(options: DictationOptions): DictationControl {
  const latest = useRef(options);
  latest.current = options;
  const [status, setStatus] = useState<SttStatus | null>(null);
  const statusRef = useRef<SttStatus | null>(null);
  statusRef.current = status;
  const [engine] = useState(
    () =>
      new DictationEngine({
        voiceStop: () => latest.current.voice.stop(),
        threadId: () => latest.current.threadId,
        onTranscript: (text, meta, info) => latest.current.onTranscript(text, meta, info),
        status: () => statusRef.current,
        lastSpoken: () => latest.current.lastSpoken,
      }),
  );
  const snapshot = useSyncExternalStore(engine.subscribe, engine.getSnapshot);
  const supported = dictationSupported();

  useEffect(() => {
    if (!supported) return undefined;
    let timer: number | undefined;
    let alive = true;
    const load = () => {
      getSttStatus()
        .then((value) => {
          if (!alive) return;
          setStatus(value);
          if (value.state === "loading") timer = window.setTimeout(load, STATUS_RETRY_MS);
        })
        .catch(() => {
          if (alive) timer = window.setTimeout(load, STATUS_RETRY_MS * 2);
        });
    };
    load();
    return () => {
      alive = false;
      if (timer) window.clearTimeout(timer);
    };
  }, [supported]);

  useEffect(() => () => engine.dispose(), [engine]);

  useEffect(() => {
    engine.update(options.busy, options.voice.speaking, options.replies ?? 0);
  });

  useEffect(() => {
    if (!snapshot.message) return undefined;
    const timer = window.setTimeout(() => engine.clearMessage(), MESSAGE_MS);
    return () => window.clearTimeout(timer);
  }, [engine, snapshot.message]);

  return {
    ...snapshot,
    supported,
    status,
    toggle: () => void engine.toggle(),
    cancel: () => engine.cancel(),
    setHandsfree: (value: boolean) => engine.setHandsfree(value),
    clearMessage: () => engine.clearMessage(),
  };
}
