import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";

vi.mock("../pages/Home", () => ({ Home: () => <h1>Entrada</h1> }));
vi.mock("../pages/Agent", () => ({ Agent: () => <h1>Agente</h1> }));
vi.mock("../pages/Planning", () => ({ Planning: () => <h1>Planificación</h1> }));
vi.mock("../pages/Evidence", () => ({ Evidence: () => <h1>Evidencia</h1> }));
vi.mock("../pages/WhatsApp", () => ({ WhatsApp: () => <h1>WhatsApp</h1> }));
vi.mock("../lib/api", () => ({
  getVersion: vi.fn().mockResolvedValue({ commit: "abc1234", web: "ok", web_build: "0123456789ab" }),
  health: vi.fn().mockResolvedValue({
    ok: false,
    provider: "deepseek",
    model: "deepseek-chat",
    configured: false,
    demo_available: true,
  }),
}));
const planning = vi.hoisted(() => ({ getAccess: vi.fn() }));
vi.mock("../lib/planning", () => planning);

const { default: App } = await import("../App");

beforeEach(() => window.history.replaceState(null, "", "/"));
afterEach(() => vi.clearAllMocks());

describe("App (spec 026, T021)", () => {
  it.each([
    ["/", "Entrada"],
    ["/agente", "Agente"],
    ["/planificacion", "Planificación"],
    ["/evidencia", "Evidencia"],
    ["/whatsapp", "WhatsApp"],
  ])("la ruta %s muestra su área y la navegación la marca", async (path, title) => {
    window.history.replaceState(null, "", path);
    render(<App />);
    expect(screen.getByRole("heading", { level: 1, name: title })).toBeInTheDocument();
    const current = screen
      .getByRole("navigation", { name: "Áreas de la plataforma" })
      .querySelector('[aria-current="page"]');
    expect(current).toHaveAttribute("href", path);
    expect(await screen.findByText(/Modo demostración/)).toBeInTheDocument();
  });

  it("la navegación tiene cinco áreas en orden y /whatsapp tiene su título (spec 032)", () => {
    window.history.replaceState(null, "", "/whatsapp");
    render(<App />);
    const nav = screen.getByRole("navigation", { name: "Áreas de la plataforma" });
    const labels = Array.from(nav.querySelectorAll("a")).map((link) => link.textContent?.trim());
    expect(labels).toEqual(["Entrada", "Agente", "Planificación", "Evidencia", "WhatsApp"]);
    expect(document.title).toBe("WhatsApp · Valer-IA");
  });

  it("una ruta desconocida vuelve a la entrada con aviso", () => {
    window.history.replaceState(null, "", "/gerencia");
    render(<App />);
    expect(screen.getByRole("status")).toHaveTextContent("Esa página no existe; te llevamos a la entrada.");
    expect(screen.getByRole("heading", { level: 1, name: "Entrada" })).toBeInTheDocument();
  });

  it("no consulta el acceso a la planificación al cargar (spec 027)", () => {
    render(<App />);
    expect(planning.getAccess).not.toHaveBeenCalled();
  });

  it("el pie muestra la versión que sirve el backend", async () => {
    render(<App />);
    expect(await screen.findByTestId("app-version")).toHaveTextContent("Versión abc1234");
  });

  it("la declaración académica está en todas las áreas", () => {
    render(<App />);
    expect(screen.getByText(/No es un canal oficial de Manuelita/)).toBeInTheDocument();
  });
});
