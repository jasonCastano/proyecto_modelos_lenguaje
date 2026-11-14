import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ChatView, visitorText } from "../components/ChatView";
import { QUICK_REPLY_LABELS, QuickReplies } from "../components/QuickReplies";
import { adoptUser, resetVisit, viewMode, visitUser, VISIT_USER_KEY } from "../lib/session";
import type { ChatResponse, ChatTurn, PendingAction } from "../lib/types";

// Valer-IA Caña (spec 018): visita, bienvenida, cliente y vistas.

const WELCOME = {
  assistant: "Valer-IA Caña",
  version: "1.0",
  text: "¡Hola! Soy Valer-IA Caña, la asistente virtual de Manuelita. Manuelita inició en 1864 [U1].",
  citations: [{ label: "U1", unit_id: "unit_1", url: "https://www.manuelita.com/a", title: "Historia" }],
};

function makeTurn(overrides: Partial<ChatTurn> = {}): ChatTurn {
  return {
    turn_id: 1,
    question: "¿Qué produce Manuelita?",
    route: { route: "documental", confidence: 0.9, reason: "narrativa", decided_by: "llm", alternative: null, fallback_route: null },
    fragments: [],
    structured_rows: [],
    answer: "Manuelita produce azúcar [U1].",
    citations: [],
    sources: [],
    fallback: false,
    metrics: { latency_ms: 10, model_calls: 1, tool_calls: 1, input_tokens: 0, output_tokens: 0 },
    ...overrides,
  };
}

function response(overrides: Partial<ChatResponse> = {}): ChatResponse {
  return {
    thread_id: "8f6c1e0a-0000-4000-8000-0000000000bb",
    turn: makeTurn(),
    status: "answered",
    pending_action: null,
    anomalies: [],
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

type Handler = (url: string, init?: RequestInit) => Response | undefined;

function routed(handler: Handler, welcome: object | null = WELCOME) {
  return vi.fn((url: string, init?: RequestInit) => {
    if (url.endsWith("/api/welcome")) {
      return Promise.resolve(
        welcome ? new Response(JSON.stringify(welcome), { status: 200 }) : new Response("{}", { status: 503 }),
      );
    }
    return Promise.resolve(
      handler(url, init) ?? new Response(JSON.stringify({ user_id: "anon", items: [], profile: [] }), { status: 200 }),
    );
  });
}

function chatBodies(fetchMock: ReturnType<typeof routed>) {
  return fetchMock.mock.calls
    .filter((call) => String(call[0]).includes("/chat"))
    .map((call) => JSON.parse(String(call[1]?.body)) as { user_id: string; thread_id: string | null });
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

describe("session (visita)", () => {
  it("crea el cliente en sessionStorage, migra la clave antigua y permite adoptar o reiniciar", () => {
    window.localStorage.setItem("manuelita.chat.user", "anon-viejo");
    const first = visitUser();
    expect(first).toMatch(/^anon-/);
    expect(first).not.toBe("anon-viejo");
    expect(window.localStorage.getItem("manuelita.chat.user")).toBeNull();
    expect(visitUser()).toBe(first);
    adoptUser("anon-ana");
    expect(window.sessionStorage.getItem(VISIT_USER_KEY)).toBe("anon-ana");
    const fresh = resetVisit();
    expect(fresh).not.toBe("anon-ana");
    expect(visitUser()).toBe(fresh);
  });

  it("elige la vista con ?vista=tecnica y la recuerda en la visita", () => {
    expect(viewMode()).toBe("normal");
    window.history.replaceState(null, "", "/?vista=tecnica");
    expect(viewMode()).toBe("tecnica");
    window.history.replaceState(null, "", "/");
    expect(viewMode()).toBe("tecnica");
    window.history.replaceState(null, "", "/?vista=normal");
    expect(viewMode()).toBe("normal");
  });
});

describe("QuickReplies", () => {
  const action: PendingAction = { action_id: "a1", tool: "remember_client", args: { name: "Ana" }, proposed_at: "2026-11-14T00:00:00Z" };

  it("muestra la pregunta y las etiquetas de la acción, sin editar", async () => {
    const onDecide = vi.fn();
    render(<QuickReplies action={action} busy={false} onDecide={onDecide} />);
    expect(screen.getByTestId("quick-replies")).toHaveTextContent("Gracias, Ana");
    const user = userEvent.setup();
    await user.click(screen.getByRole("button", { name: QUICK_REPLY_LABELS.remember_client.approve }));
    await user.click(screen.getByRole("button", { name: QUICK_REPLY_LABELS.remember_client.reject }));
    expect(onDecide.mock.calls).toEqual([["approve"], ["reject"]]);
    expect(screen.queryByText(/editar/i)).not.toBeInTheDocument();
  });
});

describe("ChatView como Valer-IA", () => {
  beforeEach(() => {
    window.sessionStorage.clear();
  });

  it("muestra la bienvenida sin interacción, con fuentes", async () => {
    vi.stubGlobal("fetch", routed(() => undefined));
    render(<ChatView mode="demo" />);
    const welcome = await screen.findByTestId("welcome-message");
    expect(welcome).toHaveTextContent("Soy Valer-IA Caña");
    expect(welcome).toHaveTextContent("Historia");
  });

  it("usa un saludo local si la bienvenida no está disponible", async () => {
    vi.stubGlobal("fetch", routed(() => undefined, null));
    render(<ChatView mode="demo" />);
    expect(await screen.findByTestId("welcome-message")).toHaveTextContent("Soy Valer-IA Caña");
  });

  it("la vista normal no muestra elementos técnicos; la técnica sí", async () => {
    const fetchMock = routed((url) => (url.endsWith("/chat/stream") ? sse(response()) : undefined));
    vi.stubGlobal("fetch", fetchMock);
    const { unmount } = render(<ChatView mode="demo" />);
    await ask("¿Qué produce Manuelita?");
    await screen.findByTestId("chat-turn");
    for (const id of ["route-chip", "turn-trace", "demo-cases", "observability", "recent-threads"]) {
      expect(screen.queryByTestId(id)).not.toBeInTheDocument();
    }
    expect(screen.queryByLabelText("Variante")).not.toBeInTheDocument();
    unmount();
    window.sessionStorage.clear(); // sin hilo guardado: solo interesa la vista

    window.history.replaceState(null, "", "/?vista=tecnica");
    vi.stubGlobal("fetch", routed((url) => (url.endsWith("/chat/stream") ? sse(response()) : undefined)));
    render(<ChatView mode="demo" />);
    expect(screen.getByLabelText("Variante")).toBeInTheDocument();
    expect(screen.getByTestId("demo-cases")).toBeInTheDocument();
  });

  it("adopta el cliente reconocido para los turnos siguientes", async () => {
    const queue = [
      response({ client: { user_id: "anon-ana", recognized: true, name: "Ana", reset: false, masked_email: null } }),
      response({ turn: makeTurn({ turn_id: 2 }) }),
    ];
    const fetchMock = routed((url) => (url.endsWith("/chat/stream") ? sse(queue.shift() as ChatResponse) : undefined));
    vi.stubGlobal("fetch", fetchMock);
    render(<ChatView mode="demo" />);
    await ask("Ana");
    await screen.findByTestId("chat-turn");
    await ask("¿Y dónde?");
    await waitFor(() => expect(chatBodies(fetchMock)).toHaveLength(2));
    expect(chatBodies(fetchMock)[1].user_id).toBe("anon-ana");
    expect(window.sessionStorage.getItem(VISIT_USER_KEY)).toBe("anon-ana");
  });

  it("«empecemos de nuevo» crea un cliente anónimo nuevo y limpia la conversación", async () => {
    const reset = response({
      client: { user_id: "anon-x", recognized: false, name: null, reset: true, masked_email: null },
    });
    vi.stubGlobal("fetch", routed((url) => (url.endsWith("/chat/stream") ? sse(reset) : undefined)));
    render(<ChatView mode="demo" />);
    const before = window.sessionStorage.getItem(VISIT_USER_KEY);
    await ask("empecemos de nuevo");
    await waitFor(() => expect(window.sessionStorage.getItem(VISIT_USER_KEY)).not.toBe(before));
    expect(screen.queryByTestId("chat-turn")).not.toBeInTheDocument();
    expect(screen.getByTestId("welcome-message")).toBeInTheDocument();
  });

  it("en la vista normal la acción pendiente es una respuesta rápida y bloquea el campo", async () => {
    const pending = response({
      status: "pending_approval",
      pending_action: {
        action_id: "act-1",
        tool: "remember_client",
        args: { name: "Ana" },
        proposed_at: "2026-11-14T00:00:00Z",
      },
      turn: makeTurn({ answer: "" }),
    });
    const fetchMock = routed((url) => {
      if (url.endsWith("/chat/stream")) return sse(pending);
      if (url.endsWith("/resume")) {
        return new Response(JSON.stringify(response({ turn: makeTurn({ answer: "Listo, Ana" }) })), { status: 200 });
      }
      return undefined;
    });
    vi.stubGlobal("fetch", fetchMock);
    render(<ChatView mode="demo" />);
    await ask("Soy Ana, mi correo es ana@ejemplo.com");
    expect(await screen.findByTestId("quick-replies")).toBeInTheDocument();
    expect(screen.queryByText("Aprobar")).not.toBeInTheDocument();
    expect(screen.getByTestId("chat-input")).toBeDisabled();
    expect(screen.getByTestId("chat-input")).toHaveAttribute("placeholder", "Responde a la pregunta de Valer-IA");
    await userEvent.setup().click(screen.getByRole("button", { name: "Sí, recuérdame" }));
    await waitFor(() => expect(screen.queryByTestId("quick-replies")).not.toBeInTheDocument());
    const resume = fetchMock.mock.calls.find((call) => String(call[0]).endsWith("/resume"));
    expect(JSON.parse(String(resume?.[1]?.body))).toMatchObject({ action_id: "act-1", decision: "approve" });
  });
});

it("la vista de visitante muestra las redacciones en lenguaje natural", () => {
  expect(visitorText("mi correo es [REDACTED_EMAIL] y mi tarjeta [REDACTED_CREDIT_CARD]")).toBe(
    "mi correo es ‹correo protegido› y mi tarjeta ‹tarjeta protegida›",
  );
  expect(visitorText("[REDACTED_OTRO]")).toBe("[REDACTED_OTRO]");
});
