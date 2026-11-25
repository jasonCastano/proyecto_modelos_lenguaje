import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { act, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { ChatViewProps } from "../components/ChatView";
import type { ChatTurn } from "../lib/types";

const mounts = { count: 0 };
const latest: { props: ChatViewProps | null } = { props: null };

vi.mock("../components/ChatView", async () => {
  const { useEffect } = await import("react");
  return {
    ChatView: (props: ChatViewProps) => {
      latest.props = props;
      useEffect(() => {
        mounts.count += 1;
      }, []);
      useEffect(() => {
        if (props.outbox) props.onOutboxTaken?.(props.outbox.id);
      }, [props.outbox]);
      return <div data-testid="chat-stub">{props.audience}</div>;
    },
  };
});

vi.mock("../lib/chat", () => ({
  getProfiles: vi.fn().mockResolvedValue([
    { key: "visitante", label: "Visitante", requires_authorization: false, authorized: true },
    { key: "cliente", label: "Cliente B2B", requires_authorization: false, authorized: true },
    { key: "proveedor", label: "Proveedor", requires_authorization: false, authorized: true },
    { key: "colaborador", label: "Colaborador", requires_authorization: false, authorized: true },
    { key: "planificador", label: "Planificador industrial", requires_authorization: true, authorized: false },
  ]),
}));

const { Agent } = await import("../pages/Agent");
const platform = await import("../lib/platform");

const turn = {
  turn_id: 1,
  question: "¿Qué certificaciones tienen?",
  answer: "Tiene Bonsucro [U1].",
  citations: [
    { label: "U1", unit_id: "u-1", url: "https://www.manuelita.com/certificaciones", title: "Certificaciones" },
  ],
} as unknown as ChatTurn;

beforeEach(() => {
  window.sessionStorage.clear();
  platform.resetPlatform();
  mounts.count = 0;
});

afterEach(() => vi.clearAllMocks());

describe("Agent (spec 026, T043)", () => {
  it("lista los perfiles y cambiar de perfil no reinicia la conversación", async () => {
    render(<Agent mode="demo" />);
    const radios = await screen.findAllByRole("radio");
    expect(radios).toHaveLength(5);
    expect(screen.getByRole("radio", { name: /Planificador industrial/ })).toBeDisabled();
    await userEvent.click(screen.getByRole("radio", { name: "Cliente B2B" }));
    expect(screen.getByTestId("chat-stub")).toHaveTextContent("cliente");
    expect(mounts.count).toBe(1);
    expect(screen.getByRole("heading", { name: /Para empezar como cliente B2B/ })).toBeInTheDocument();
  });

  it("muestra las fuentes del último turno como enlaces", async () => {
    render(<Agent mode="demo" />);
    await screen.findAllByRole("radio");
    act(() => latest.props?.onTurn?.(turn, "t-1"));
    expect(screen.getByRole("link", { name: "Certificaciones" })).toHaveAttribute(
      "href",
      "https://www.manuelita.com/certificaciones",
    );
  });

  it("«Borrar mi memoria» pide la acción con aprobación", async () => {
    render(<Agent mode="demo" />);
    await screen.findAllByRole("radio");
    act(() => {
      latest.props?.onTurn?.(turn, "t-1");
      latest.props?.onMemory?.({
        preferences: [],
        profile: [{ key: "role", value: "compras", created_at: "2026-11-24" }],
      });
    });
    expect(screen.getByText("compras")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Borrar mi memoria" }));
    expect(latest.props?.forgetRequest).toBe(1);
    expect(screen.getByText(/Responde «Sí» en la conversación/)).toBeInTheDocument();
  });

  it("el mensaje pendiente de otra área se entrega una sola vez", async () => {
    platform.queueMessage("Explica el plan recomendado", "send");
    render(<Agent mode="demo" />);
    await screen.findAllByRole("radio");
    expect(latest.props?.outbox ?? null).toBeNull();
  });
});
