import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ChatTurnCard, ChatView } from "../components/ChatView";
import type { ChatResponse, ChatTurn } from "../lib/types";

function makeTurn(overrides: Partial<ChatTurn> = {}): ChatTurn {
  return {
    turn_id: 1,
    question: "¿Qué produce Manuelita?",
    route: {
      route: "documental",
      confidence: 0.86,
      reason: "pregunta narrativa sobre la empresa",
      decided_by: "llm",
      alternative: "structured",
      fallback_route: null,
    },
    fragments: [
      {
        label: "U1",
        unit_id: "unit_1",
        title: "Productos de Manuelita",
        url: "https://www.manuelita.com/productos",
        score: 0.81,
        semantic_score: 0.88,
        lexical_score: 0.42,
        origin: "both",
        status: "used",
        reason: null,
      },
    ],
    structured_rows: [],
    answer: "Manuelita produce azúcar y biocombustibles [U1].",
    citations: [
      {
        label: "U1",
        unit_id: "unit_1",
        url: "https://www.manuelita.com/productos",
        title: "Productos de Manuelita",
      },
    ],
    sources: ["https://www.manuelita.com/productos"],
    fallback: false,
    metrics: { latency_ms: 420, model_calls: 2, tool_calls: 1, input_tokens: 0, output_tokens: 0 },
    ...overrides,
  };
}

function renderTurn(turn: ChatTurn) {
  return render(
    <ol>
      <ChatTurnCard turn={turn} />
    </ol>,
  );
}

describe("ChatTurnCard", () => {
  it("muestra ruta, fragmentos, respuesta y fuentes", () => {
    renderTurn(makeTurn());

    expect(screen.getByTestId("route-chip")).toHaveTextContent("Ruta: Documentos · 86 %");
    expect(screen.getByTestId("turn-trace")).toHaveTextContent(
      "Decidió: LLM (alternativa: Datos estructurados)",
    );
    expect(screen.getByTestId("retrieved-fragments")).toHaveTextContent("Productos de Manuelita");
    expect(screen.getByText(/produce azúcar/)).toBeInTheDocument();
    expect(within(screen.getByTestId("source-list")).getByText("[U1]")).toBeInTheDocument();
    expect(screen.getByTestId("chat-turn")).toHaveAttribute("data-kind", "answered");
  });

  it("un turno de aclaración no muestra fragmentos ni fuentes", () => {
    renderTurn(
      makeTurn({
        question: "¿Y lo anterior?",
        route: { route: "clarify", confidence: 0.4, reason: "referencia sin historial", decided_by: "demo" },
        fragments: [],
        citations: [],
        sources: [],
        answer: "No estoy seguro de a qué te refieres.",
      }),
    );

    expect(screen.getByTestId("route-chip")).toHaveTextContent("Aclaración");
    expect(screen.queryByTestId("retrieved-fragments")).not.toBeInTheDocument();
    expect(screen.queryByTestId("source-list")).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-turn")).toHaveAttribute("data-kind", "clarify");
  });

  it("un turno sin evidencia se marca como fallback", () => {
    renderTurn(
      makeTurn({
        answer: "No hay evidencia suficiente en el corpus para responder.",
        citations: [],
        fallback: true,
      }),
    );

    expect(screen.getByTestId("chat-turn")).toHaveAttribute("data-kind", "fallback");
    expect(screen.queryByTestId("source-list")).not.toBeInTheDocument();
  });
});

describe("ChatTurnCard con fragmentos anómalos", () => {
  it("avisa del fragmento con instrucciones embebidas", () => {
    const turn = makeTurn();
    renderTurn(
      makeTurn({
        fragments: [
          { ...turn.fragments[0], anomalous: true, anomaly_reasons: ["revela_prompt"] },
        ],
      }),
    );

    expect(screen.getByTestId("anomaly-warning")).toHaveTextContent("[U1]");
    expect(screen.getByTestId("anomaly-warning")).toHaveTextContent("revela_prompt");
    expect(screen.getByTestId("anomaly-warning")).not.toHaveTextContent(/neutralizada/);
  });

  it("indica cuántas oraciones se neutralizaron antes de llegar al modelo", () => {
    const turn = makeTurn();
    renderTurn(
      makeTurn({
        fragments: [
          {
            ...turn.fragments[0],
            anomalous: true,
            anomaly_reasons: ["ignora_instrucciones"],
            neutralized_sentences: 2,
          },
        ],
      }),
    );

    expect(screen.getByTestId("anomaly-warning")).toHaveTextContent(
      "2 oraciones neutralizadas antes de llegar al modelo",
    );
  });
});

const EMPTY_MEMORY = { user_id: "anon-x", items: [], profile: [] };

/** Respuesta SSE como la de `POST /api/chat/stream`: ruta, tokens y turno final. */
function sse(response: ChatResponse): Response {
  const events: Array<Record<string, unknown>> = [
    { event: "start", thread_id: response.thread_id },
    { event: "route", route: response.turn.route },
    ...response.turn.answer.split(/(?<= )/).map((text) => ({ event: "token", text })),
    { event: "done", response },
  ];
  const body = events.map((event) => `event: ${event.event}\ndata: ${JSON.stringify(event)}\n\n`).join("");
  return new Response(body, { status: 200, headers: { "Content-Type": "text/event-stream" } });
}

type Handler = (url: string, init?: RequestInit) => Response | undefined;

/** `fetch` simulado por ruta; la memoria responde vacía salvo que un handler diga otra cosa. */
function routedFetch(handler: Handler) {
  return vi.fn((url: string, init?: RequestInit) => {
    const response =
      handler(url, init) ?? new Response(JSON.stringify(EMPTY_MEMORY), { status: 200 });
    return Promise.resolve(response);
  });
}

function chatCalls(fetchMock: ReturnType<typeof routedFetch>) {
  return fetchMock.mock.calls.filter((call) => String(call[0]).includes("/chat"));
}

describe("ChatView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
    window.localStorage.clear();
  });

  it("envía el mensaje en streaming, conserva el hilo y lo reutiliza en la repregunta", async () => {
    const first: ChatResponse = {
      thread_id: "8f6c1e0a-0000-4000-8000-000000000001",
      turn: makeTurn(),
      status: "answered",
      pending_action: null,
      anomalies: [],
    };
    const second: ChatResponse = {
      ...first,
      turn: makeTurn({ turn_id: 2, question: "¿Y dónde lo produce?" }),
    };
    const queue = [first, second];
    const fetchMock = routedFetch((url) =>
      url.endsWith("/chat/stream") ? sse(queue.shift() as ChatResponse) : undefined,
    );
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ChatView mode="demo" />);
    await user.type(screen.getByTestId("chat-input"), "¿Qué produce Manuelita?");
    await user.click(screen.getByTestId("chat-send"));
    await screen.findByText("¿Qué produce Manuelita?");
    await user.type(screen.getByTestId("chat-input"), "¿Y dónde lo produce?");
    await user.click(screen.getByTestId("chat-send"));
    await screen.findByText("¿Y dónde lo produce?");

    const bodies = chatCalls(fetchMock).map((call) => JSON.parse(String(call[1]?.body)));
    expect(String(chatCalls(fetchMock)[0][0])).toContain("/api/chat/stream");
    expect(bodies[0]).toMatchObject({ thread_id: null, variant: "chain", mode: "demo" });
    expect(bodies[1].thread_id).toBe(first.thread_id);
    expect(screen.getAllByTestId("chat-turn")).toHaveLength(2);
    expect(screen.queryByTestId("chat-live")).not.toBeInTheDocument();
    expect(window.sessionStorage.getItem("manuelita.chat.thread")).toContain(first.thread_id);
  });

  it("si el servidor no tiene streaming usa la ruta clásica", async () => {
    const answered: ChatResponse = {
      thread_id: "8f6c1e0a-0000-4000-8000-000000000009",
      turn: makeTurn(),
      status: "answered",
      pending_action: null,
      anomalies: [],
    };
    const fetchMock = routedFetch((url) => {
      if (url.endsWith("/chat/stream")) return new Response("{}", { status: 404 });
      if (url.endsWith("/chat")) return new Response(JSON.stringify(answered), { status: 200 });
      return undefined;
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ChatView mode="demo" />);
    await user.type(screen.getByTestId("chat-input"), "¿Qué produce Manuelita?");
    await user.click(screen.getByTestId("chat-send"));

    expect(await screen.findByText(/produce azúcar/)).toBeInTheDocument();
    expect(chatCalls(fetchMock).map((call) => String(call[0]))).toEqual([
      "/api/chat/stream",
      "/api/chat",
    ]);
  });

  it("pausa ante una acción de escritura y la reanuda al aprobar", async () => {
    const pending: ChatResponse = {
      thread_id: "8f6c1e0a-0000-4000-8000-000000000002",
      turn: makeTurn({ question: "Prefiero respuestas en viñetas", answer: "", citations: [], fragments: [] }),
      status: "pending_approval",
      pending_action: {
        action_id: "act_01",
        tool: "save_preference",
        args: { key: "response_format", value: "viñetas" },
        proposed_at: "2026-11-11T10:00:00Z",
      },
      anomalies: [],
    };
    const resumed: ChatResponse = {
      ...pending,
      turn: makeTurn({
        question: "Prefiero respuestas en viñetas",
        answer: "Guardé tu preferencia: response_format = viñetas.",
        citations: [],
        fragments: [],
      }),
      status: "answered",
      pending_action: null,
    };
    const fetchMock = routedFetch((url) => {
      if (url.endsWith("/chat/stream")) return sse(pending);
      if (url.endsWith("/resume")) return new Response(JSON.stringify(resumed), { status: 200 });
      return undefined;
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ChatView mode="demo" />);
    await user.type(screen.getByTestId("chat-input"), "Prefiero respuestas en viñetas");
    await user.click(screen.getByTestId("chat-send"));
    await screen.findByTestId("approval-card");
    expect(screen.getByTestId("chat-send")).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Aprobar" }));
    await screen.findByText(/Guardé tu preferencia/);

    const resumeCall = fetchMock.mock.calls.find((call) => String(call[0]).endsWith("/resume"));
    expect(String(resumeCall?.[0])).toContain(`/threads/${pending.thread_id}/resume`);
    expect(JSON.parse(String(resumeCall?.[1]?.body))).toEqual({
      action_id: "act_01",
      decision: "approve",
    });
    expect(screen.queryByTestId("approval-card")).not.toBeInTheDocument();
  });

  it("muestra el perfil y las preferencias guardadas y pide aprobación para olvidarlas", async () => {
    const threadId = "8f6c1e0a-0000-4000-8000-000000000003";
    const pending: ChatResponse = {
      thread_id: threadId,
      turn: makeTurn({ question: "Me llamo Ana y trabajo en Carvajal", answer: "", citations: [], fragments: [] }),
      status: "pending_approval",
      pending_action: {
        action_id: "act_01",
        tool: "save_profile",
        args: { name: "Ana", workplace: "Carvajal" },
        proposed_at: "2026-11-11T10:00:00Z",
      },
      anomalies: [],
    };
    const saved: ChatResponse = {
      ...pending,
      turn: makeTurn({ answer: "Guardé en tu perfil.", citations: [], fragments: [] }),
      status: "answered",
      pending_action: null,
    };
    let approved = false;
    const memory = () => ({
      user_id: "anon-x",
      items: approved
        ? [
            {
              key: "response_format",
              value: "viñetas",
              created_at: "2026-11-11T10:00:00Z",
              expires_at: "2026-12-11T10:00:00Z",
            },
          ]
        : [],
      profile: approved
        ? [
            { key: "name", value: "Ana", created_at: "2026-11-11T10:00:00Z" },
            { key: "workplace", value: "Carvajal", created_at: "2026-11-11T10:00:00Z" },
          ]
        : [],
    });
    const forget = {
      status: "pending_approval",
      thread_id: threadId,
      pending_action: { action_id: "act_02", tool: "forget_memory", args: {}, proposed_at: "x" },
    };
    const fetchMock = routedFetch((url, init) => {
      if (url.endsWith("/chat/stream")) return sse(pending);
      if (url.endsWith("/resume")) {
        approved = true;
        return new Response(JSON.stringify(saved), { status: 200 });
      }
      if (init?.method === "DELETE") return new Response(JSON.stringify(forget), { status: 202 });
      return new Response(JSON.stringify(memory()), { status: 200 });
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ChatView mode="demo" />);
    await user.type(screen.getByTestId("chat-input"), "Me llamo Ana y trabajo en Carvajal");
    await user.click(screen.getByTestId("chat-send"));
    const card = await screen.findByTestId("approval-card");
    expect(card).toHaveTextContent("Guardar datos de tu perfil");
    expect(within(card).getByLabelText("Lugar de trabajo")).toHaveValue("Carvajal");
    await user.click(within(card).getByRole("button", { name: "Aprobar" }));
    expect(await screen.findByTestId("profile")).toHaveTextContent("nombre: Ana · trabajo: Carvajal");
    expect(screen.getByTestId("preferences")).toHaveTextContent("formato: viñetas");
    await user.click(screen.getByRole("button", { name: "Olvidar" }));

    expect(await screen.findByTestId("approval-card")).toHaveTextContent("Olvidar tus preferencias");
    const deleteCall = fetchMock.mock.calls.find((call) => call[1]?.method === "DELETE");
    expect(String(deleteCall?.[0])).toContain(`/memory/anon-`);
    expect(String(deleteCall?.[0])).toContain(`thread_id=${threadId}`);
    expect(window.localStorage.getItem("manuelita.chat.user")).toMatch(/^anon-/);
  });

  it("ofrece los casos de la rúbrica y retoma una conversación reciente", async () => {
    const answered: ChatResponse = {
      thread_id: "8f6c1e0a-0000-4000-8000-000000000010",
      turn: makeTurn({ question: "¿Cuántas filiales tiene Manuelita?" }),
      status: "answered",
      pending_action: null,
      anomalies: [],
    };
    const thread = {
      thread_id: answered.thread_id,
      variant: "chain",
      turns: [answered.turn],
      summary: "",
      status: "idle",
      pending_action: null,
    };
    const fetchMock = routedFetch((url) => {
      if (url.endsWith("/chat/stream")) return sse(answered);
      if (url.includes("/threads/")) return new Response(JSON.stringify(thread), { status: 200 });
      if (url.endsWith("/observability")) {
        return new Response(
          JSON.stringify({ langsmith: false, project: null, structured_log: "turns.jsonl" }),
          { status: 200 },
        );
      }
      return undefined;
    });
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ChatView mode="demo" />);
    expect(await screen.findByTestId("observability")).toHaveTextContent("log JSON por turno");
    await user.click(screen.getByRole("button", { name: "Dato estructurado" }));
    expect(screen.getByTestId("chat-input")).toHaveValue("¿Cuántas filiales tiene Manuelita?");
    await user.click(screen.getByTestId("chat-send"));
    const recent = await screen.findByTestId("recent-threads");
    expect(recent).toHaveTextContent("¿Cuántas filiales tiene Manuelita? · Cadena");
    await user.click(screen.getByRole("button", { name: "Nueva conversación" }));
    expect(screen.queryByTestId("chat-turn")).not.toBeInTheDocument();
    await user.click(within(recent).getByRole("button", { name: /Cuántas filiales/ }));

    expect(await screen.findByTestId("chat-turn")).toBeInTheDocument();
    expect(
      fetchMock.mock.calls.some((call) => String(call[0]).endsWith(`/threads/${answered.thread_id}`)),
    ).toBe(true);
  });
});
