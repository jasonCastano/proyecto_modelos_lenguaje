import { vi } from "vitest";

import type { SttResult, SttStatus } from "../lib/types";

/**
 * Micrófono simulado para el dictado (spec 023): `getUserMedia`, `AudioContext` con
 * `audioWorklet` y `AudioWorkletNode`. Las pruebas empujan bloques de 20 ms con `speak` y `quiet`.
 */

export const RATE = 48_000;
export const BLOCK = RATE / 50; // 20 ms

export const STT_READY: SttStatus = {
  available: true,
  state: "ready",
  engine: "fake",
  model: "fake",
  language: "es",
  detail: null,
  max_seconds: 60,
  silence_ms: 1500,
  min_speech_ms: 300,
  handsfree_idle_seconds: 60,
  privacy: "Tu voz se convierte en texto en el servidor del proyecto y el audio no se guarda.",
};

export function sttResult(text: string, overrides: Partial<SttResult> = {}): SttResult {
  return {
    text,
    empty: !text,
    truncated: false,
    language: "es",
    audio_ms: 2040,
    stt_ms: 451,
    model: "fake",
    ...overrides,
  };
}

export class FakeWorkletNode {
  static last: FakeWorkletNode | null = null;
  port: { onmessage: ((event: { data: Float32Array }) => void) | null } = { onmessage: null };
  constructor() {
    FakeWorkletNode.last = this;
  }
  connect() {}
  disconnect() {}
}

export class FakeCaptureContext {
  static closed = 0;
  sampleRate = RATE;
  state = "running";
  destination = {};
  currentTime = 0;
  audioWorklet = { addModule: vi.fn(async () => undefined) };
  createMediaStreamSource() {
    return { connect() {}, disconnect() {} };
  }
  async close() {
    FakeCaptureContext.closed += 1;
  }
  async resume() {}
}

export interface MediaHandles {
  getUserMedia: ReturnType<typeof vi.fn>;
  stopped: () => number;
}

/** Instala el micrófono simulado; `error` hace fallar `getUserMedia` con ese nombre. */
export function installMedia(error?: string): MediaHandles {
  let stopped = 0;
  const getUserMedia = vi.fn(async () => {
    if (error) throw Object.assign(new Error(error), { name: error });
    return {
      getTracks: () => [
        {
          stop: () => {
            stopped += 1;
          },
        },
      ],
    };
  });
  Object.defineProperty(window, "isSecureContext", { value: true, configurable: true });
  Object.defineProperty(navigator, "mediaDevices", {
    value: { getUserMedia },
    configurable: true,
  });
  vi.stubGlobal("AudioContext", FakeCaptureContext);
  vi.stubGlobal("AudioWorkletNode", FakeWorkletNode);
  if (!("createObjectURL" in URL)) {
    Object.defineProperty(URL, "createObjectURL", { value: () => "blob:worklet", configurable: true });
  } else {
    vi.spyOn(URL, "createObjectURL").mockReturnValue("blob:worklet");
  }
  FakeWorkletNode.last = null;
  return { getUserMedia, stopped: () => stopped };
}

export function uninstallMedia(): void {
  Reflect.deleteProperty(navigator, "mediaDevices");
  Object.defineProperty(window, "isSecureContext", { value: false, configurable: true });
  vi.unstubAllGlobals();
}

function push(block: Float32Array, count: number): void {
  const node = FakeWorkletNode.last;
  if (!node?.port.onmessage) throw new Error("el micrófono no está abierto");
  for (let i = 0; i < count; i += 1) node.port.onmessage({ data: block });
}

const SPEECH = new Float32Array(BLOCK).map((_, i) => 0.2 * Math.sin((i / BLOCK) * Math.PI * 16));
const LOUD = new Float32Array(BLOCK).map((_, i) => 0.5 * Math.sin((i / BLOCK) * Math.PI * 16));
const SILENCE = new Float32Array(BLOCK);
// Resto de la voz de Valer-IA tras la cancelación de eco del navegador (bajo el umbral ×2).
const MURMUR = new Float32Array(BLOCK).map((_, i) => 0.03 * Math.sin((i / BLOCK) * Math.PI * 16));

/** `ms` de voz (bloques de 20 ms). */
export function speak(ms: number, loud = false): void {
  push(loud ? LOUD : SPEECH, Math.round(ms / 20));
}

/** `ms` de eco residual (no interrumpe a Valer-IA). */
export function murmur(ms: number): void {
  push(MURMUR, Math.round(ms / 20));
}

/** `ms` de silencio. */
export function quiet(ms: number): void {
  push(SILENCE, Math.round(ms / 20));
}

export function micOpen(): boolean {
  return Boolean(FakeWorkletNode.last?.port.onmessage);
}

type Route = (url: string, init?: RequestInit) => Response | undefined;

/** `fetch` con `/api/stt` (estado y transcripción) y un manejador para lo demás. */
export function sttFetch(options: {
  status?: SttStatus | (() => SttStatus);
  transcribe?: (init?: RequestInit) => Response | Promise<Response>;
  other?: Route;
}) {
  return vi.fn(async (url: string, init?: RequestInit) => {
    if (url.endsWith("/api/stt") && (!init?.method || init.method === "GET")) {
      const status = typeof options.status === "function" ? options.status() : options.status;
      return new Response(JSON.stringify(status ?? STT_READY), { status: 200 });
    }
    if (url.endsWith("/api/stt") && init?.method === "POST") {
      if (options.transcribe) return options.transcribe(init);
      return new Response(JSON.stringify(sttResult("¿Qué produce Manuelita?")), { status: 200 });
    }
    return (
      options.other?.(url, init) ??
      new Response(JSON.stringify({ user_id: "anon", items: [], profile: [] }), { status: 200 })
    );
  });
}

export function sttPosts(fetchMock: ReturnType<typeof sttFetch>) {
  return fetchMock.mock.calls.filter(
    (call) => String(call[0]).endsWith("/api/stt") && call[1]?.method === "POST",
  );
}
