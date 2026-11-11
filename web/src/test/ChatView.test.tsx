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
  });
});

describe("ChatView", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
    window.sessionStorage.clear();
  });

  it("envía el mensaje, conserva el hilo y lo reutiliza en la repregunta", async () => {
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
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(first), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(second), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ChatView mode="demo" />);
    await user.type(screen.getByTestId("chat-input"), "¿Qué produce Manuelita?");
    await user.click(screen.getByTestId("chat-send"));
    await screen.findByText("¿Qué produce Manuelita?");
    await user.type(screen.getByTestId("chat-input"), "¿Y dónde lo produce?");
    await user.click(screen.getByTestId("chat-send"));
    await screen.findByText("¿Y dónde lo produce?");

    const bodies = fetchMock.mock.calls.map((call) => JSON.parse(String(call[1]?.body)));
    expect(bodies[0]).toMatchObject({ thread_id: null, variant: "chain", mode: "demo" });
    expect(bodies[1].thread_id).toBe(first.thread_id);
    expect(screen.getAllByTestId("chat-turn")).toHaveLength(2);
    expect(window.sessionStorage.getItem("manuelita.chat.thread")).toContain(first.thread_id);
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
    const fetchMock = vi
      .fn()
      .mockResolvedValueOnce(new Response(JSON.stringify(pending), { status: 200 }))
      .mockResolvedValueOnce(new Response(JSON.stringify(resumed), { status: 200 }));
    vi.stubGlobal("fetch", fetchMock);
    const user = userEvent.setup();

    render(<ChatView mode="demo" />);
    await user.type(screen.getByTestId("chat-input"), "Prefiero respuestas en viñetas");
    await user.click(screen.getByTestId("chat-send"));
    await screen.findByTestId("approval-card");
    expect(screen.getByTestId("chat-send")).toBeDisabled();
    await user.click(screen.getByRole("button", { name: "Aprobar" }));
    await screen.findByText(/Guardé tu preferencia/);

    expect(String(fetchMock.mock.calls[1][0])).toContain(`/threads/${pending.thread_id}/resume`);
    expect(JSON.parse(String(fetchMock.mock.calls[1][1]?.body))).toEqual({
      action_id: "act_01",
      decision: "approve",
    });
    expect(screen.queryByTestId("approval-card")).not.toBeInTheDocument();
  });
});
