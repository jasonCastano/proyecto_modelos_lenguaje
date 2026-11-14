import { describe, expect, it, vi } from "vitest";

import { ApiClientError } from "../lib/types";
import {
  type AudioContextLike,
  type AudioSourceLike,
  normalizeForCompare,
  SentenceSegmenter,
  type SpeechRequest,
  VoicePlayer,
} from "../lib/voice";

describe("SentenceSegmenter", () => {
  it("corta oraciones completas aunque los fragmentos partan palabras", () => {
    const segmenter = new SentenceSegmenter();
    const chunks = ["Manuelita pro", "duce azú", "car. ¿Y eta", "nol? ¡Sí! Fin"];
    const out = chunks.flatMap((chunk) => segmenter.push(chunk));
    expect(out).toEqual(["Manuelita produce azúcar.", "¿Y etanol?", "¡Sí!"]);
    expect(segmenter.flush()).toEqual(["Fin"]);
  });

  it("no corta en abreviaturas ni decimales", () => {
    const segmenter = new SentenceSegmenter();
    const text = "La Sra. Pérez y la Dra. Gómez, p. ej. en la planta No. 3, producen 3.5 millones. Fin.";
    const out = [...segmenter.push(text), ...segmenter.flush()];
    expect(out).toEqual([
      "La Sra. Pérez y la Dra. Gómez, p. ej. en la planta No. 3, producen 3.5 millones.",
      "Fin.",
    ]);
  });

  it("espera texto después de un punto final antes de cerrar la oración", () => {
    const segmenter = new SentenceSegmenter();
    expect(segmenter.push("Dijo que no. ")).toEqual([]);
    expect(segmenter.push("Luego aceptó.")).toEqual(["Dijo que no."]);
    expect(segmenter.flush()).toEqual(["Luego aceptó."]);
  });

  it("limita solo el primer segmento para que el primer audio llegue pronto", () => {
    const segmenter = new SentenceSegmenter(600, 50);
    const first = "La historia de Manuelita, y la de los ingenios, comienza en 1864 en el Valle. ";
    const out = [...segmenter.push(`${first}Otra oración bastante larga, con varias partes y más texto aquí. `), ...segmenter.flush()];
    expect(out[0].length).toBeLessThanOrEqual(50);
    expect(out.join(" ")).toContain("comienza en 1864 en el Valle.");
    expect(out[out.length - 1]).toBe("Otra oración bastante larga, con varias partes y más texto aquí.");
  });

  it("parte las oraciones demasiado largas", () => {
    const segmenter = new SentenceSegmenter(40, 40);
    const parts = [...segmenter.push(`${"producción de azúcar, ".repeat(6)}fin. `), ...segmenter.flush()];
    expect(parts.length).toBeGreaterThan(1);
    expect(parts.every((part) => part.length <= 40)).toBe(true);
  });
});

it("normalizeForCompare ignora citas, espacios y mayúsculas", () => {
  expect(normalizeForCompare("Azúcar  y etanol [U1, U2].")).toBe(normalizeForCompare("azúcar y etanol ."));
});

/** Contexto de audio simulado: cada fuente termina cuando la prueba llama a `end()`. */
function fakeContext() {
  const sources: Array<AudioSourceLike & { text: string; end: () => void; stopped: boolean }> = [];
  const context: AudioContextLike = {
    state: "running",
    destination: {},
    currentTime: 0,
    resume: vi.fn(async () => undefined),
    decodeAudioData: vi.fn(async (data: ArrayBuffer) => new TextDecoder().decode(data)),
    createBufferSource: () => {
      const source = {
        buffer: null as unknown,
        onended: null as (() => void) | null,
        stopped: false,
        text: "",
        connect: vi.fn(),
        start: vi.fn(() => {
          source.text = String(source.buffer);
        }),
        stop: vi.fn(() => {
          source.stopped = true;
        }),
        end: () => source.onended?.(),
      };
      sources.push(source);
      return source;
    },
  };
  return { context, sources };
}

function deferred() {
  const resolvers: Array<{ request: SpeechRequest; resolve: (value: ArrayBuffer | null) => void }> = [];
  const fetcher = vi.fn(
    (request: SpeechRequest, _signal?: AbortSignal) =>
      new Promise<ArrayBuffer | null>((resolve) => {
        resolvers.push({ request, resolve });
      }),
  );
  const answer = (index: number, value: string | null = null) =>
    resolvers[index].resolve(value === null ? null : (new TextEncoder().encode(value).buffer as ArrayBuffer));
  return { fetcher, resolvers, answer };
}

const flush = () => new Promise((resolve) => setTimeout(resolve, 0));

describe("VoicePlayer", () => {
  it("pide como máximo 2 oraciones a la vez y reproduce en orden", async () => {
    const { context, sources } = fakeContext();
    const { fetcher, resolvers, answer } = deferred();
    let now = 1000;
    const onFirstAudio = vi.fn();
    const player = new VoicePlayer({ createContext: () => context, fetcher, now: () => now, onFirstAudio });

    const key = player.start("t-1");
    player.push("Uno. Dos. Tres. Cuatro. ");
    expect(fetcher).toHaveBeenCalledTimes(2);
    expect(resolvers.map((item) => item.request.segment)).toEqual([0, 1]);
    expect(resolvers[0].request.threadId).toBe("t-1");

    now = 1300;
    answer(1, "Dos.");
    answer(0, "Uno.");
    await flush();
    await flush();
    expect(sources.map((source) => source.text)).toEqual(["Uno."]);
    expect(onFirstAudio).toHaveBeenCalledWith(key, 300);

    sources[0].end();
    await flush();
    await flush();
    expect(sources.map((source) => source.text)).toEqual(["Uno.", "Dos."]);
    expect(fetcher).toHaveBeenCalledTimes(3);
  });

  it("salta las oraciones sin audio (204) y los errores puntuales", async () => {
    const { context, sources } = fakeContext();
    const fetcher = vi.fn(async (request: SpeechRequest) => {
      if (request.segment === 0) return null;
      if (request.segment === 1) throw new ApiClientError({ code: "voice_error", message: "x", retryable: true, action: "reintentar" });
      return new TextEncoder().encode(request.text).buffer as ArrayBuffer;
    });
    const player = new VoicePlayer({ createContext: () => context, fetcher });
    player.speakText("[U1]. Falla. Suena.", "t");
    for (let i = 0; i < 6; i += 1) await flush();
    expect(sources.map((source) => source.text)).toEqual(["Suena."]);
  });

  it("stop corta el audio y aborta las peticiones", async () => {
    const { context, sources } = fakeContext();
    const { fetcher, resolvers, answer } = deferred();
    const onSpeaking = vi.fn();
    const player = new VoicePlayer({ createContext: () => context, fetcher, onSpeaking });
    player.start("t");
    player.push("Uno. Dos. Tres");
    answer(0, "Uno.");
    await flush();
    await flush();
    player.stop();
    expect(sources[0].stopped).toBe(true);
    expect(fetcher.mock.calls[1][1]?.aborted).toBe(true);
    expect(onSpeaking).toHaveBeenLastCalledWith(false);
    answer(1, "Dos.");
    await flush();
    expect(sources).toHaveLength(1);
    expect(resolvers).toHaveLength(2);
  });

  it("si la respuesta final difiere, corta y lee la final desde el principio", async () => {
    const { context } = fakeContext();
    const fetcher = vi.fn(async (_request: SpeechRequest, _signal?: AbortSignal): Promise<ArrayBuffer | null> => null);
    const player = new VoicePlayer({ createContext: () => context, fetcher });
    player.start("t");
    player.push("Texto filtrado del prompt. Más ");
    player.finish("No tengo evidencia suficiente para responder.");
    const texts = fetcher.mock.calls.map((call) => call[0].text);
    expect(texts).toEqual(["Texto filtrado del prompt.", "No tengo evidencia suficiente para responder."]);
    expect(fetcher.mock.calls[1][0].segment).toBe(0);
  });

  it("si la final coincide, lee solo lo pendiente", async () => {
    const { context } = fakeContext();
    const fetcher = vi.fn(async (_request: SpeechRequest, _signal?: AbortSignal): Promise<ArrayBuffer | null> => null);
    const player = new VoicePlayer({ createContext: () => context, fetcher });
    player.start("t");
    player.push("Manuelita produce azúcar [U1]. Y etanol");
    player.finish("Manuelita produce azúcar [U1]. Y etanol");
    await flush();
    expect(fetcher.mock.calls.map((call) => call[0].text)).toEqual(["Manuelita produce azúcar [U1].", "Y etanol"]);
  });

  it("un 503 desactiva la voz", async () => {
    const { context } = fakeContext();
    const onUnavailable = vi.fn();
    const fetcher = vi.fn(async () => {
      throw new ApiClientError({ code: "voice_unavailable", message: "Sin modelo.", retryable: false, action: "continuar sin voz" });
    });
    const player = new VoicePlayer({ createContext: () => context, fetcher, onUnavailable });
    player.speakText("Hola.", null);
    await flush();
    await flush();
    expect(onUnavailable).toHaveBeenCalledWith("Sin modelo.");
    expect(player.activeKey).toBeNull();
  });

  it("sin AudioContext no está soportado", () => {
    expect(new VoicePlayer({ createContext: () => null }).supported()).toBe(false);
  });
});
