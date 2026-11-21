import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatView } from "../components/ChatView";
import { actsTrail, ContactRecordPanel, sentimentTrail } from "../components/ContactRecordPanel";
import type { ChatResponse, ChatTurn, ContactRecord } from "../lib/types";

// Registro del contacto (spec 019, US5): solo en la vista técnica y sin datos personales.

const RECORD: ContactRecord = {
  version: "1.0",
  opened_at: "2026-11-17T00:00:00Z",
  updated_at: "2026-11-17T00:01:00Z",
  turns: 2,
  requests: [
    { turn: 1, category: "complaint", topic: "atencion", status: "needs_clarification" },
    { turn: 2, category: "manuelita", topic: "productos", status: "resolved" },
  ],
  sentiments: ["frustrated", "satisfied"],
  motive: ["atencion", "productos"],
  resolved: true,
  hostile_turns: 0,
  crisis: false,
};

function makeTurn(): ChatTurn {
  return {
    turn_id: 1,
    question: "¿Qué produce Manuelita?",
    route: { route: "documental", confidence: 0.9, reason: "narrativa", decided_by: "llm" },
    fragments: [],
    structured_rows: [],
    answer: "Manuelita produce azúcar [U1].",
    citations: [],
    sources: [],
    fallback: false,
    metrics: { latency_ms: 10, model_calls: 1, tool_calls: 1, input_tokens: 0, output_tokens: 0 },
  };
}

function response(overrides: Partial<ChatResponse> = {}): ChatResponse {
  return {
    thread_id: "8f6c1e0a-0000-4000-8000-0000000000cc",
    turn: makeTurn(),
    status: "answered",
    pending_action: null,
    anomalies: [],
    contact: RECORD,
    ...overrides,
  };
}

function sse(final: ChatResponse): Response {
  const events = [
    { event: "start", thread_id: final.thread_id },
    { event: "done", response: final },
  ];
  const body = events.map((event) => `event: ${event.event}\ndata: ${JSON.stringify(event)}\n\n`).join("");
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

function routed(final: ChatResponse) {
  return vi.fn((url: string) => {
    if (url.endsWith("/api/welcome")) return Promise.resolve(new Response("{}", { status: 503 }));
    if (url.endsWith("/chat/stream")) return Promise.resolve(sse(final));
    return Promise.resolve(new Response(JSON.stringify({ user_id: "anon", items: [], profile: [] }), { status: 200 }));
  });
}

async function ask(text: string) {
  const user = userEvent.setup();
  await user.type(screen.getByTestId("chat-input"), text);
  await user.click(screen.getByTestId("chat-send"));
}

afterEach(() => {
  vi.unstubAllGlobals();
  window.sessionStorage.clear();
  window.localStorage.clear();
  window.history.replaceState(null, "", "/");
});

describe("ContactRecordPanel", () => {
  it("muestra solicitudes, estados, evolución emocional y si quedó resuelto", () => {
    render(<ContactRecordPanel record={RECORD} />);
    const panel = screen.getByTestId("contact-record");
    expect(panel).toHaveTextContent("Queja");
    expect(panel).toHaveTextContent("Pide aclaración");
    expect(panel).toHaveTextContent("Resuelta");
    expect(panel).toHaveTextContent("Resuelto");
    expect(screen.getByTestId("contact-sentiments")).toHaveTextContent("frustrado → satisfecho");
  });

  it("spec 020: muestra la línea «Actos» con puentes (◆) y respaldos (↺)", () => {
    render(
      <ContactRecordPanel
        record={{
          ...RECORD,
          acts: [
            { act: "greeting", bridged: false, reviewed: "show" },
            { act: "smalltalk", bridged: true, reviewed: "show" },
            { act: "off_topic", bridged: false, reviewed: "fallback" },
          ],
        }}
      />,
    );
    expect(screen.getByTestId("contact-acts")).toHaveTextContent(
      "Actos: saludo → charla ◆ → fuera de tema ↺",
    );
  });

  it("spec 020: sin actos (modo de guiones) no hay línea «Actos»", () => {
    render(<ContactRecordPanel record={RECORD} />);
    expect(screen.queryByTestId("contact-acts")).not.toBeInTheDocument();
    expect(actsTrail([])).toBe("");
  });

  it("resume la evolución sin repetir emociones seguidas", () => {
    expect(sentimentTrail(["neutral", "neutral", "frustrated", "frustrated", "satisfied"])).toBe(
      "neutral → frustrado → satisfecho",
    );
  });
});

describe("ChatView y el registro del contacto", () => {
  it("la vista técnica muestra el registro tras responder", async () => {
    window.history.replaceState(null, "", "/?vista=tecnica");
    vi.stubGlobal("fetch", routed(response()));
    render(<ChatView mode="demo" />);
    await ask("¿Qué produce Manuelita?");
    expect(await screen.findByTestId("contact-record")).toHaveTextContent("Registro del contacto");
  });

  it("la vista normal nunca muestra el registro", async () => {
    vi.stubGlobal("fetch", routed(response()));
    render(<ChatView mode="demo" />);
    await ask("¿Qué produce Manuelita?");
    await screen.findByTestId("chat-turn");
    expect(screen.queryByTestId("contact-record")).not.toBeInTheDocument();
  });

  it("al reiniciar la visita se limpia el registro", async () => {
    window.history.replaceState(null, "", "/?vista=tecnica");
    const queue = [
      response(),
      response({ client: { user_id: "anon-x", recognized: false, name: null, reset: true, masked_email: null } }),
    ];
    vi.stubGlobal(
      "fetch",
      vi.fn((url: string) => {
        if (url.endsWith("/api/welcome")) return Promise.resolve(new Response("{}", { status: 503 }));
        if (url.endsWith("/chat/stream")) return Promise.resolve(sse(queue.shift() as ChatResponse));
        return Promise.resolve(new Response(JSON.stringify({ user_id: "anon", items: [], profile: [] }), { status: 200 }));
      }),
    );
    render(<ChatView mode="demo" />);
    await ask("¿Qué produce Manuelita?");
    await screen.findByTestId("contact-record");
    await ask("empecemos de nuevo");
    await waitFor(() => expect(screen.queryByTestId("contact-record")).not.toBeInTheDocument());
  });
});
