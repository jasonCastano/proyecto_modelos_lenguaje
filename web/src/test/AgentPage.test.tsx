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
    { key: "planificador", label: "Planificador industrial", requires_authorization: false, authorized: true },
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
    await userEvent.click(screen.getByRole("radio", { name: /Cliente B2B/ }));
    expect(screen.getByTestId("chat-stub")).toHaveTextContent("cliente");
    expect(mounts.count).toBe(1);
    expect(screen.getByRole("heading", { name: /Para empezar como cliente B2B/ })).toBeInTheDocument();
  });

  it("los cinco perfiles son elegibles y dicen para quién son (spec 027)", async () => {
    render(<Agent mode="demo" />);
    const radios = await screen.findAllByRole("radio");
    for (const radio of radios) {
      expect(radio).toBeEnabled();
      expect(radio).not.toHaveAttribute("aria-disabled");
    }
    for (const text of [
      "Quieres conocer Manuelita",
      "Compras para tu empresa",
      "Entregas caña al ingenio",
      "Trabajas en Manuelita",
      "Planeas la producción de la semana",
    ]) {
      expect(screen.getByText(text)).toBeInTheDocument();
    }
    expect(screen.queryByText(/solo autorizados|Solo equipo de planta/i)).not.toBeInTheDocument();
  });

  it("el teclado recorre los cinco perfiles, planificador incluido", async () => {
    render(<Agent mode="demo" />);
    await screen.findAllByRole("radio");
    const first = screen.getByRole("radio", { name: /Visitante/ });
    first.focus();
    await userEvent.keyboard("{End}");
    expect(screen.getByRole("radio", { name: /Planificador industrial/ })).toHaveAttribute("aria-checked", "true");
    await userEvent.keyboard("{ArrowRight}");
    expect(screen.getByRole("radio", { name: /Visitante/ })).toHaveAttribute("aria-checked", "true");
    await userEvent.keyboard("{ArrowLeft}");
    expect(screen.getByRole("radio", { name: /Planificador industrial/ })).toHaveAttribute("aria-checked", "true");
    await userEvent.keyboard("{Home}");
    expect(screen.getByRole("radio", { name: /Visitante/ })).toHaveAttribute("aria-checked", "true");
  });

  it("el aviso dice el perfil activo y, con el planificador, ofrece la consola", async () => {
    render(<Agent mode="demo" />);
    await screen.findAllByRole("radio");
    expect(screen.getByTestId("profile-notice")).toHaveTextContent("Te atiende como Visitante.");
    expect(screen.queryByRole("link", { name: "Abrir la planificación" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("radio", { name: /Planificador industrial/ }));
    const notice = screen.getByTestId("profile-notice");
    expect(notice).toHaveTextContent("Te atiende como Planificador industrial.");
    expect(notice).toHaveTextContent("Los datos de planta son sintéticos");
    expect(screen.getByRole("link", { name: "Abrir la planificación" })).toHaveAttribute("href", "/planificacion");
    expect(screen.getByTestId("chat-stub")).toHaveTextContent("planificador");
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
