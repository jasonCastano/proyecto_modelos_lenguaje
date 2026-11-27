import { beforeEach, describe, expect, it } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { resetPlatform, usePlatform } from "../lib/platform";
import { Home } from "../pages/Home";

beforeEach(() => {
  window.sessionStorage.clear();
  window.history.replaceState(null, "", "/");
  resetPlatform();
});

function Probe() {
  const { audience, outbox } = usePlatform();
  return (
    <output data-testid="probe">
      {audience}|{outbox?.kind ?? ""}|{outbox?.text ?? ""}
    </output>
  );
}

describe("Home (spec 026, T042; spec 031)", () => {
  it("presenta la plataforma, la declaración y cinco perfiles", () => {
    render(<Home />);
    expect(
      screen.getByRole("heading", { level: 1, name: "Agentes de IA para consultar a Manuelita" }),
    ).toBeInTheDocument();
    expect(screen.getByText(/^Proyecto académico con IA\. No es un canal oficial de Manuelita\.$/)).toBeInTheDocument();
    const profiles = screen.getByRole("heading", { name: "Un agente para cada perfil" }).closest("section")!;
    expect(within(profiles).getAllByRole("listitem")).toHaveLength(5);
  });

  it("el planificador está abierto como los demás perfiles (spec 027)", () => {
    const { container } = render(<Home />);
    const row = container.querySelector('[data-profile="planificador"]')!;
    expect(within(row as HTMLElement).getByRole("button", { name: /15 % menos caña/ })).toBeInTheDocument();
    expect(container.querySelector(".profile-ledger__locked")).toBeNull();
    expect(screen.queryByText(/Solo equipo de planta autorizado/)).toBeNull();
    expect(screen.getByRole("link", { name: "Abrir la planificación" })).toHaveAttribute("href", "/planificacion");
  });

  it("la consulta de ejemplo del cliente B2B abre el agente con ese perfil y el mensaje listo", async () => {
    render(
      <>
        <Home />
        <Probe />
      </>,
    );
    await userEvent.click(screen.getByRole("button", { name: /Compro azúcar para mi empresa/ }));
    expect(window.location.pathname).toBe("/agente");
    expect(screen.getByTestId("probe")).toHaveTextContent(
      "cliente|draft|Compro azúcar para mi empresa, ¿qué certificaciones tienen?",
    );
  });

  it("la consola de Consulta, Resumen y FAQ pasó a la evidencia (spec 031)", () => {
    render(<Home />);
    expect(screen.queryByTestId("rag-console")).toBeNull();
    expect(screen.getByRole("link", { name: "Ver la evidencia" })).toHaveAttribute("href", "/evidencia");
  });

  it("cada sección es hija directa del contenido con su título (spec 031)", () => {
    const { container } = render(<Home />);
    const sections = Array.from(container.children);
    expect(sections.map((s) => s.id)).toEqual([
      "inicio",
      "producto",
      "perfiles",
      "negocios",
      "frase",
      "planificacion",
      "garantias",
      "evidencia",
      "preguntas",
    ]);
    for (const section of sections.slice(1)) {
      expect(section.querySelector("h2")).not.toBeNull();
    }
  });

  it("las fotos son sustitutas con texto alternativo y sin pie de foto (spec 031)", () => {
    const { container } = render(<Home />);
    const photos = container.querySelectorAll('img[data-source="stand-in"]');
    expect(photos.length).toBeGreaterThanOrEqual(5);
    for (const img of Array.from(photos)) {
      expect(img.closest("figure")?.querySelector("figcaption") ?? null).toBeNull();
    }
    expect(container.querySelectorAll("img[data-source='stand-in'][alt='']")).toHaveLength(1);
  });
});
