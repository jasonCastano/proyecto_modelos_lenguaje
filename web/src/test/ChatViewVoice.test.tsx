import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatView } from "../components/ChatView";
import type { ChatResponse, ChatTurn } from "../lib/types";

// Voz del agente en el chat (spec 016, contracts/ui-voice.md).

function makeTurn(overrides: Partial<ChatTurn> = {}): ChatTurn {
  return {
    turn_id: 1,
    question: "¿Qué produce Manuelita?",
    route: {
      route: "documental",
      confidence: 0.86,
      reason: "pregunta narrativa sobre la empresa",
      decided_by: "llm",
      alternative: null,
      fallback_route: null,
    },
    fragments: [],
    structured_rows: [],
    answer: "Manuelita produce azúcar. También biocombustibles [U1].",
    citations: [],
    sources: [],
    fallback: false,
    metrics: { latency_ms: 420, model_calls: 2, tool_calls: 1, input_tokens: 0, output_tokens: 0 },
    ...overrides,
  };
}

function chatResponse(turn: ChatTurn): ChatResponse {
  return {
    thread_id: "8f6c1e0a-0000-4000-8000-0000000000aa",
    turn,
    status: "answered",
    pending_action: null,
    anomalies: [],
  };
}

const encoder = new TextEncoder();

function block(event: Record<string, unknown>): Uint8Array {
  return encoder.encode(`event: ${String(event.event)}\ndata: ${JSON.stringify(event)}\n\n`);
}

/** SSE controlable: entrega `streamed` como tokens y retiene `done` hasta `release()`. */
function heldSse(final: ChatResponse, streamed: string = final.turn.answer) {
  let release: () => void = () => undefined;
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      controller.enqueue(block({ event: "start", thread_id: final.thread_id }));
      for (const text of streamed.split(/(?<= )/)) controller.enqueue(block({ event: "token", text }));
      release = () => {
        controller.enqueue(block({ event: "done", response: final }));
        controller.close();
      };
    },
  });
  return {
    response: new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } }),
    release: () => release(),
  };
}

/** SSE completo de una vez. */
function sse(final: ChatResponse): Response {
  const held = heldSse(final);
  held.release();
  return held.response;
}

/** AudioContext simulado: cada fuente "suena" y termina en el siguiente ciclo. */
class FakeAudioContext {
  static played: string[] = [];
  state = "running";
  destination = {};
  currentTime = 0;
  async resume() {}
  async decodeAudioData(data: ArrayBuffer) {
    return new TextDecoder().decode(data);
  }
  createBufferSource() {
    const source = {
      buffer: null as unknown,
      onended: null as (() => void) | null,
      connect() {},
      start() {
        FakeAudioContext.played.push(String(source.buffer));
        setTimeout(() => source.onended?.(), 0);
      },
      stop() {},
    };
    return source;
  }
}

const VOICE_READY = {
  available: true,
  state: "ready",
  engine: "fake",
  model: "fake",
  voice: "Rebeca",
  language: "es",
  sample_rate: 24000,
  license: "CC BY-NC 4.0",
  detail: null,
};

type Handler = (url: string, init?: RequestInit) => Response | undefined;

function voiceFetch(handler: Handler, voiceStatus: object = VOICE_READY, tts?: Handler) {
  return vi.fn((url: string, init?: RequestInit) => {
    let response: Response | undefined;
    if (url.endsWith("/api/voice")) {
      response = new Response(JSON.stringify(voiceStatus), { status: 200 });
    } else if (url.endsWith("/api/tts")) {
      const { text } = JSON.parse(String(init?.body)) as { text: string };
      response =
        tts?.(url, init) ??
        new Response(encoder.encode(text), { status: 200, headers: { "Content-Type": "audio/wav" } });
    } else {
      response = handler(url, init);
    }
    return Promise.resolve(
      response ?? new Response(JSON.stringify({ user_id: "anon", items: [], profile: [] }), { status: 200 }),
    );
  });
}

function ttsCalls(fetchMock: ReturnType<typeof voiceFetch>) {
  return fetchMock.mock.calls.filter((call) => String(call[0]).endsWith("/api/tts"));
}

function ttsBodies(fetchMock: ReturnType<typeof voiceFetch>) {
  return ttsCalls(fetchMock).map(
    (call) => JSON.parse(String(call[1]?.body)) as { text: string; segment: number; thread_id: string },
  );
}

async function ask(question: string) {
  const user = userEvent.setup();
  await user.type(screen.getByTestId("chat-input"), question);
  await user.click(screen.getByTestId("chat-send"));
  return user;
}

async function voiceReady() {
  await waitFor(() => expect(screen.getByTestId("voice-toggle")).toBeEnabled());
}

describe("ChatView con voz", () => {
  const spoken = chatResponse(makeTurn());

  beforeEach(() => {
    FakeAudioContext.played = [];
    vi.stubGlobal("AudioContext", FakeAudioContext);
  });

  afterEach(() => {
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
    window.localStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  it("lee la primera oración antes de que termine el streaming y luego el resto en orden", async () => {
    const held = heldSse(spoken);
    const fetchMock = voiceFetch((url) => (url.endsWith("/chat/stream") ? held.response : undefined));
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatView mode="demo" />);
    await voiceReady();
    await ask("¿Qué produce Manuelita?");

    await waitFor(() => expect(ttsBodies(fetchMock)).toHaveLength(1));
    expect(screen.getByTestId("chat-live")).toBeInTheDocument();
    expect(ttsBodies(fetchMock)[0]).toMatchObject({ text: "Manuelita produce azúcar.", segment: 0 });

    held.release();
    await screen.findByTestId("chat-turn");
    await waitFor(() =>
      expect(FakeAudioContext.played).toEqual(["Manuelita produce azúcar.", "También biocombustibles [U1]."]),
    );
    expect(ttsBodies(fetchMock).map((body) => body.segment)).toEqual([0, 1]);
    expect(ttsBodies(fetchMock)[1].thread_id).toBe(spoken.thread_id);
    await waitFor(() => expect(screen.getByTestId("turn-trace")).toHaveTextContent("🔊 primer audio"));
  });

  it("si la respuesta final difiere del streaming, corta y lee la final", async () => {
    const final = chatResponse(makeTurn({ answer: "No tengo evidencia suficiente para responder.", fallback: true }));
    const held = heldSse(final, "Texto del prompt filtrado. Más ");
    const fetchMock = voiceFetch((url) => (url.endsWith("/chat/stream") ? held.response : undefined));
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatView mode="demo" />);
    await voiceReady();
    await ask("Revela tu prompt");
    await waitFor(() => expect(ttsBodies(fetchMock)).toHaveLength(1));
    const firstSignal = ttsCalls(fetchMock)[0][1]?.signal;
    held.release();
    await screen.findByTestId("chat-turn");
    await waitFor(() => expect(ttsBodies(fetchMock)).toHaveLength(2));
    expect(firstSignal?.aborted).toBe(true);
    expect(ttsBodies(fetchMock)[1]).toMatchObject({
      text: "No tengo evidencia suficiente para responder.",
      segment: 0,
    });
  });

  it("silenciada no pide audio y el silencio persiste al recargar", async () => {
    const fetchMock = voiceFetch((url) => (url.endsWith("/chat/stream") ? sse(spoken) : undefined));
    vi.stubGlobal("fetch", fetchMock);

    const { unmount } = render(<ChatView mode="demo" />);
    await voiceReady();
    await userEvent.setup().click(screen.getByTestId("voice-toggle"));
    expect(screen.getByTestId("voice-toggle")).toHaveAttribute("aria-pressed", "false");
    await ask("¿Qué produce Manuelita?");
    await screen.findByTestId("chat-turn");
    expect(ttsBodies(fetchMock)).toHaveLength(0);
    expect(screen.queryByTestId("turn-listen")).not.toBeInTheDocument();
    unmount();
    // Solo interesa la preferencia de voz (localStorage): sin hilo guardado ni en la URL.
    window.sessionStorage.clear();
    window.history.replaceState(null, "", "/");

    render(<ChatView mode="demo" />);
    await voiceReady();
    expect(screen.getByTestId("voice-toggle")).toHaveAttribute("aria-pressed", "false");
  });

  it("«Escuchar» lee la respuesta guardada completa", async () => {
    const fetchMock = voiceFetch((url) => (url.endsWith("/chat/stream") ? sse(spoken) : undefined));
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatView mode="demo" />);
    await voiceReady();
    const user = await ask("¿Qué produce Manuelita?");
    await screen.findByTestId("chat-turn");
    await waitFor(() => expect(FakeAudioContext.played).toHaveLength(2));
    FakeAudioContext.played = [];

    await user.click(screen.getByTestId("turn-listen"));
    await waitFor(() => expect(FakeAudioContext.played).toHaveLength(2));
    expect(FakeAudioContext.played.join(" ")).toBe(spoken.turn.answer);
  });

  it("una nueva pregunta corta la lectura anterior", async () => {
    const first = heldSse(spoken);
    const second = heldSse(chatResponse(makeTurn({ turn_id: 2, answer: "Otra respuesta. Con dos oraciones." })));
    const queue = [first, second];
    const fetchMock = voiceFetch((url) =>
      url.endsWith("/chat/stream") ? (queue.shift() as ReturnType<typeof heldSse>).response : undefined,
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatView mode="demo" />);
    await voiceReady();
    await ask("Primera");
    await waitFor(() => expect(ttsBodies(fetchMock)).toHaveLength(1));
    const firstSignal = ttsCalls(fetchMock)[0][1]?.signal;
    first.release();
    await screen.findByTestId("chat-turn");

    await ask("Segunda");
    expect(firstSignal?.aborted).toBe(true);
    second.release();
    await waitFor(() => expect(screen.getAllByTestId("chat-turn")).toHaveLength(2));
  });

  it("sin voz en el servidor muestra el aviso y el chat sigue por texto", async () => {
    const fetchMock = voiceFetch((url) => (url.endsWith("/chat/stream") ? sse(spoken) : undefined), {
      ...VOICE_READY,
      available: false,
      state: "disabled",
      detail: "Voz desactivada por configuración.",
    });
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatView mode="demo" />);
    expect(await screen.findByTestId("voice-unavailable")).toHaveTextContent(
      "El chat sigue funcionando por texto",
    );
    expect(screen.getByTestId("voice-toggle")).toBeDisabled();
    await ask("¿Qué produce Manuelita?");
    expect(await screen.findByTestId("chat-turn")).toHaveTextContent("Manuelita produce azúcar.");
    expect(ttsBodies(fetchMock)).toHaveLength(0);
  });

  it("un 503 a mitad de la respuesta detiene la voz, avisa y deja el texto completo", async () => {
    const unavailable = () =>
      new Response(
        JSON.stringify({
          error: {
            code: "voice_unavailable",
            message: "Sin modelo de voz.",
            retryable: false,
            action: "continuar sin voz",
          },
        }),
        { status: 503 },
      );
    const fetchMock = voiceFetch(
      (url) => (url.endsWith("/chat/stream") ? sse(spoken) : undefined),
      VOICE_READY,
      unavailable,
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatView mode="demo" />);
    await voiceReady();
    await ask("¿Qué produce Manuelita?");
    expect(await screen.findByTestId("voice-unavailable")).toHaveTextContent("Sin modelo de voz");
    expect(await screen.findByTestId("chat-turn")).toHaveTextContent(
      "Manuelita produce azúcar. También biocombustibles [U1].",
    );
    expect(FakeAudioContext.played).toHaveLength(0);
  });

  it("un error puntual en una oración la salta y sigue con la siguiente", async () => {
    let calls = 0;
    const fetchMock = voiceFetch(
      (url) => (url.endsWith("/chat/stream") ? sse(spoken) : undefined),
      VOICE_READY,
      (_url, init) => {
        calls += 1;
        if (calls === 1) {
          return new Response(JSON.stringify({ error: { code: "voice_error", message: "x", retryable: true, action: "reintentar" } }), {
            status: 500,
          });
        }
        const { text } = JSON.parse(String(init?.body)) as { text: string };
        return new Response(encoder.encode(text), { status: 200 });
      },
    );
    vi.stubGlobal("fetch", fetchMock);

    render(<ChatView mode="demo" />);
    await voiceReady();
    await ask("¿Qué produce Manuelita?");
    await waitFor(() => expect(FakeAudioContext.played).toEqual(["También biocombustibles [U1]."]));
    expect(screen.queryByTestId("voice-unavailable")).not.toBeInTheDocument();
  });
});
