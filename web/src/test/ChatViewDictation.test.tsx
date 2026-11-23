import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatTurnCard, ChatView, inputSummary } from "../components/ChatView";
import type { ChatResponse, ChatTurn, InputMeta, SttStatus } from "../lib/types";
import {
  STT_READY,
  installMedia,
  quiet,
  speak,
  sttFetch,
  sttPosts,
  sttResult,
  uninstallMedia,
} from "./mediaMocks";

// Dictado en el chat (spec 023): texto al campo, `input` al enviar, manos libres y traza.

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
    answer: "Manuelita produce azúcar, etanol y energía en el Valle del Cauca [U1].",
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

function sse(final: ChatResponse): Response {
  const body = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of [
        { event: "start", thread_id: final.thread_id },
        { event: "done", response: final },
      ]) {
        controller.enqueue(encoder.encode(`event: ${event.event}\ndata: ${JSON.stringify(event)}\n\n`));
      }
      controller.close();
    },
  });
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

const VOICE_OFF = {
  available: false,
  state: "disabled",
  engine: "fake",
  model: "fake",
  voice: "Rebeca",
  language: "es",
  sample_rate: null,
  license: "",
  detail: "Voz desactivada.",
};

function setup(options: { status?: SttStatus; heard?: () => string } = {}) {
  const fetchMock = sttFetch({
    status: options.status,
    transcribe: () =>
      new Response(JSON.stringify(sttResult(options.heard?.() ?? "¿Qué produce Manuelita?")), {
        status: 200,
      }),
    other: (url, init) => {
      if (url.endsWith("/api/voice")) return new Response(JSON.stringify(VOICE_OFF), { status: 200 });
      if (url.endsWith("/api/chat/stream")) {
        const body = JSON.parse(String(init?.body)) as { message: string; input?: InputMeta };
        return sse(chatResponse(makeTurn({ question: body.message, input: body.input ?? null })));
      }
      return undefined;
    },
  });
  vi.stubGlobal("fetch", fetchMock);
  render(<ChatView mode="demo" />);
  return fetchMock;
}

function streamBodies(fetchMock: ReturnType<typeof sttFetch>) {
  return fetchMock.mock.calls
    .filter((call) => String(call[0]).endsWith("/api/chat/stream"))
    .map((call) => JSON.parse(String(call[1]?.body)) as { message: string; input?: InputMeta });
}

async function dictate(user: ReturnType<typeof userEvent.setup>) {
  await user.click(screen.getByTestId("mic-button"));
  await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
  act(() => {
    quiet(300);
    speak(600);
  });
  await user.click(screen.getByTestId("mic-button"));
}

describe("ChatView con dictado", () => {
  beforeEach(() => {
    installMedia();
    window.sessionStorage.clear();
    window.localStorage.clear();
    window.history.replaceState(null, "", "/"); // sin el hilo del caso anterior
  });

  afterEach(() => {
    uninstallMedia();
    vi.restoreAllMocks();
  });

  it("el texto dictado llena el campo y no se envía solo", async () => {
    const fetchMock = setup();
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByTestId("mic-privacy")).toBeInTheDocument());
    await dictate(user);
    await waitFor(() => expect(screen.getByTestId("chat-input")).toHaveValue("¿Qué produce Manuelita?"));
    expect(streamBodies(fetchMock)).toHaveLength(0);
  });

  it("agrega lo dictado al texto que ya había", async () => {
    setup();
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByTestId("mic-privacy")).toBeInTheDocument());
    await user.type(screen.getByTestId("chat-input"), "Hola,");
    await dictate(user);
    await waitFor(() =>
      expect(screen.getByTestId("chat-input")).toHaveValue("Hola, ¿Qué produce Manuelita?"),
    );
  });

  it("al enviar incluye `input` (editado o no) y un mensaje escrito después no lo lleva", async () => {
    const fetchMock = setup();
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByTestId("mic-privacy")).toBeInTheDocument());
    await dictate(user);
    await waitFor(() => expect(screen.getByTestId("chat-input")).toHaveValue("¿Qué produce Manuelita?"));
    await user.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(streamBodies(fetchMock)).toHaveLength(1));
    expect(streamBodies(fetchMock)[0].input).toEqual({
      source: "voice",
      audio_ms: 2040,
      stt_ms: 451,
      edited: false,
      handsfree: false,
    });

    await waitFor(() => expect(screen.getByTestId("chat-send")).toBeEnabled());
    await dictate(user);
    await waitFor(() => expect(screen.getByTestId("chat-input")).toHaveValue("¿Qué produce Manuelita?"));
    await user.type(screen.getByTestId("chat-input"), " ¿Y en Perú?");
    await user.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(streamBodies(fetchMock)).toHaveLength(2));
    expect(streamBodies(fetchMock)[1].input?.edited).toBe(true);

    await waitFor(() => expect(screen.getByTestId("chat-send")).toBeEnabled());
    await user.type(screen.getByTestId("chat-input"), "gracias");
    await user.click(screen.getByTestId("chat-send"));
    await waitFor(() => expect(streamBodies(fetchMock)).toHaveLength(3));
    expect(streamBodies(fetchMock)[2].input).toBeUndefined();
  });

  it("manos libres: envía al terminar de hablar y vuelve a escuchar tras la respuesta", async () => {
    const fetchMock = setup();
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByTestId("mic-privacy")).toBeInTheDocument());
    await user.click(screen.getByTestId("mic-handsfree"));
    expect(screen.getByTestId("mic-handsfree")).toHaveAttribute("aria-checked", "true");
    expect(window.localStorage.getItem("manuelita.stt.handsfree")).toBe("1");
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
    act(() => {
      quiet(300);
      speak(500);
      quiet(1500);
    });
    await waitFor(() => expect(streamBodies(fetchMock)).toHaveLength(1));
    expect(streamBodies(fetchMock)[0].input?.handsfree).toBe(true);
    await waitFor(() => expect(screen.getAllByTestId("chat-turn")).toHaveLength(1));
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
  });

  it("manos libres: no envía lo que repite la voz de Valer-IA", async () => {
    let heard = "¿Qué produce Manuelita?";
    const fetchMock = setup({ heard: () => heard });
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByTestId("mic-privacy")).toBeInTheDocument());
    await user.click(screen.getByTestId("mic-handsfree"));
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
    act(() => {
      quiet(300);
      speak(500);
      quiet(1500);
    });
    await waitFor(() => expect(screen.getAllByTestId("chat-turn")).toHaveLength(1));
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
    heard = "Manuelita produce azúcar, etanol y energía en el Valle del Cauca.";
    act(() => {
      quiet(300);
      speak(500);
      quiet(1500);
    });
    await waitFor(() => expect(sttPosts(fetchMock)).toHaveLength(2));
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
    await new Promise((resolve) => setTimeout(resolve, 500));
    expect(streamBodies(fetchMock)).toHaveLength(1);
  });

  it("manos libres se apaga tras el tiempo sin voz", async () => {
    setup({ status: { ...STT_READY, handsfree_idle_seconds: 10 } });
    const user = userEvent.setup();
    await waitFor(() => expect(screen.getByTestId("mic-privacy")).toBeInTheDocument());
    await user.click(screen.getByTestId("mic-handsfree"));
    await waitFor(() => expect(screen.getByTestId("mic-status")).toHaveTextContent("Escuchando…"));
    act(() => quiet(10_000));
    await waitFor(() =>
      expect(screen.getByTestId("mic-handsfree")).toHaveAttribute("aria-checked", "false"),
    );
    expect(window.localStorage.getItem("manuelita.stt.handsfree")).toBe("0");
  });
});

describe("traza del dictado en la vista técnica (US4)", () => {
  const input: InputMeta = { source: "voice", audio_ms: 2040, stt_ms: 451, edited: true, handsfree: false };

  it("resume origen, duración y reconocimiento", () => {
    expect(inputSummary(input)).toBe("🎙 por voz · audio 2,0 s · reconocimiento 0,45 s · editado");
    expect(inputSummary({ ...input, edited: false, handsfree: true })).toBe(
      "🎙 por voz · audio 2,0 s · reconocimiento 0,45 s · manos libres",
    );
    expect(inputSummary(null)).toBeNull();
  });

  it("solo aparece en la vista técnica y en turnos dictados", () => {
    const { rerender } = render(
      <ul>
        <ChatTurnCard technical turn={makeTurn({ input })} />
      </ul>,
    );
    expect(screen.getByTestId("turn-input")).toHaveTextContent("🎙 por voz · audio 2,0 s");
    rerender(
      <ul>
        <ChatTurnCard technical={false} turn={makeTurn({ input })} />
      </ul>,
    );
    expect(screen.queryByTestId("turn-input")).not.toBeInTheDocument();
    rerender(
      <ul>
        <ChatTurnCard technical turn={makeTurn()} />
      </ul>,
    );
    expect(screen.queryByTestId("turn-input")).not.toBeInTheDocument();
  });
});
