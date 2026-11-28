/**
 * Pestaña WhatsApp (spec 032, contracts/ui-contract.md). Solo enlaces ficticios: ningún número real.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import type { WhatsAppLink } from "../lib/types";

const api = vi.hoisted(() => ({ fetchWhatsAppLink: vi.fn() }));
vi.mock("../lib/api", () => api);

const { WhatsApp } = await import("../pages/WhatsApp");

const AVAILABLE: WhatsAppLink = {
  available: true,
  mode: "open",
  message: "Hola, Valer-IA",
  web_url: "https://web.whatsapp.com/send?phone=570000000000&text=Hola%2C%20Valer-IA",
  app_url: "https://wa.me/570000000000?text=Hola%2C%20Valer-IA",
  qr_svg: '<svg xmlns="http://www.w3.org/2000/svg" data-qr="ficticio"></svg>',
};

const UNAVAILABLE: WhatsAppLink = {
  available: false,
  mode: "unknown",
  message: "Hola, Valer-IA",
  web_url: null,
  app_url: null,
  qr_svg: null,
};

const DESKTOP_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/140.0";
const IPHONE_UA = "Mozilla/5.0 (iPhone; CPU iPhone OS 18_0 like Mac OS X) Mobile/15E148";

function setDevice(userAgent: string, mobile?: boolean) {
  Object.defineProperty(window.navigator, "userAgent", { value: userAgent, configurable: true });
  Object.defineProperty(window.navigator, "userAgentData", {
    value: mobile === undefined ? undefined : { mobile },
    configurable: true,
  });
}

beforeEach(() => setDevice(DESKTOP_UA, false));
afterEach(() => vi.clearAllMocks());

describe("Pestaña WhatsApp: abrir el chat (US1)", () => {
  it("primero explica el chat y después ofrece las dos formas de conectarse", async () => {
    api.fetchWhatsAppLink.mockResolvedValue(AVAILABLE);
    const { container } = render(<WhatsApp />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Habla con Valer-IA por WhatsApp" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/El mismo agente de esta web te responde en WhatsApp/)).toBeInTheDocument();
    expect(
      screen.getByText("Proyecto académico con IA. No es un canal oficial de Manuelita."),
    ).toBeInTheDocument();
    const sections = Array.from(container.querySelectorAll("section")).map((s) => s.id);
    expect(sections).toEqual(["whatsapp", "conectar"]);
    expect(screen.getByRole("link", { name: "Ver cómo conectarte" })).toHaveAttribute("href", "#conectar");
    expect(screen.getByRole("heading", { level: 2, name: "Elige cómo conectarte" })).toBeInTheDocument();
    expect(await screen.findByRole("heading", { level: 3, name: "Desde este computador" })).toBeInTheDocument();
    expect(screen.getByRole("heading", { level: 3, name: "Desde tu celular" })).toBeInTheDocument();
    expect(screen.getByTestId("wa-mode")).toHaveTextContent("Abierto: cualquier número puede escribir");
    expect(screen.getByText("Necesitas WhatsApp Web vinculado a tu celular.")).toBeInTheDocument();
  });

  it("el botón abre WhatsApp Web en una pestaña nueva en el computador", async () => {
    api.fetchWhatsAppLink.mockResolvedValue(AVAILABLE);
    render(<WhatsApp />);
    const button = await screen.findByTestId("wa-open");
    expect(button.tagName).toBe("A");
    expect(button).toHaveAttribute("href", AVAILABLE.web_url);
    expect(button).toHaveAttribute("target", "_blank");
    expect(button).toHaveAttribute("rel", "noopener noreferrer");
    expect(button).toHaveTextContent("(se abre en una pestaña nueva)");
    expect(button).toHaveAccessibleName(/Abrir WhatsApp Web/);
  });

  it.each([
    ["userAgentData.mobile", DESKTOP_UA, true],
    ["agente de un iPhone", IPHONE_UA, undefined],
  ])("en el teléfono (%s) abre la aplicación", async (_label, ua, mobile) => {
    setDevice(ua, mobile);
    api.fetchWhatsAppLink.mockResolvedValue(AVAILABLE);
    render(<WhatsApp />);
    expect(await screen.findByTestId("wa-open")).toHaveAttribute("href", AVAILABLE.app_url);
  });

  it("modo cerrado: solo números de prueba; modo desconocido: sin estado", async () => {
    api.fetchWhatsAppLink.mockResolvedValue({ ...AVAILABLE, mode: "closed" });
    const { unmount } = render(<WhatsApp />);
    expect(await screen.findByTestId("wa-mode")).toHaveTextContent("Solo números de prueba del equipo");
    unmount();
    api.fetchWhatsAppLink.mockResolvedValue({ ...AVAILABLE, mode: "unknown" });
    render(<WhatsApp />);
    await screen.findByTestId("wa-open");
    expect(screen.queryByTestId("wa-mode")).not.toBeInTheDocument();
  });
});

describe("Pestaña WhatsApp: QR para el teléfono (US2)", () => {
  it("muestra el QR del servidor con su etiqueta y leyenda", async () => {
    api.fetchWhatsAppLink.mockResolvedValue(AVAILABLE);
    render(<WhatsApp />);
    const qr = await screen.findByTestId("wa-qr");
    expect(qr).toHaveAttribute("role", "img");
    expect(qr).toHaveAttribute("aria-label", "Código QR para abrir el chat en tu teléfono");
    expect(qr.querySelector('svg[data-qr="ficticio"]')).not.toBeNull();
    expect(
      screen.getByText("Escanea el código con la cámara de tu celular y se abre el chat."),
    ).toBeInTheDocument();
  });
});

describe("Pestaña WhatsApp: canal no disponible (US3)", () => {
  it("sin número: aviso y enlace al Agente, sin botón, QR ni estado", async () => {
    api.fetchWhatsAppLink.mockResolvedValue(UNAVAILABLE);
    render(<WhatsApp />);
    expect(
      await screen.findByText("El chat de WhatsApp no está disponible en este momento"),
    ).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Habla con Valer-IA aquí" })).toHaveAttribute("href", "/agente");
    expect(screen.queryByTestId("wa-open")).not.toBeInTheDocument();
    expect(screen.queryByTestId("wa-qr")).not.toBeInTheDocument();
    expect(screen.queryByTestId("wa-mode")).not.toBeInTheDocument();
  });

  it("respuesta inesperada del servidor: aviso y «Reintentar», nunca un botón sin enlace", async () => {
    api.fetchWhatsAppLink.mockRejectedValueOnce(new Error("invalid_response"));
    render(<WhatsApp />);
    expect(
      await screen.findByText("El chat de WhatsApp no está disponible en este momento"),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Reintentar" })).toBeInTheDocument();
    expect(screen.queryByTestId("wa-open")).not.toBeInTheDocument();
  });

  it("error de red: el mismo aviso y «Reintentar» vuelve a consultar", async () => {
    api.fetchWhatsAppLink.mockRejectedValueOnce(new Error("sin red")).mockResolvedValueOnce(AVAILABLE);
    render(<WhatsApp />);
    expect(
      await screen.findByText("El chat de WhatsApp no está disponible en este momento"),
    ).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    await waitFor(() => expect(api.fetchWhatsAppLink).toHaveBeenCalledTimes(2));
    expect(await screen.findByTestId("wa-open")).toBeInTheDocument();
  });
});
