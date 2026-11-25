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

describe("Home (spec 026, T042)", () => {
  it("presenta la plataforma, la declaración y cinco perfiles", () => {
    render(<Home health={null} />);
    expect(
      screen.getByRole("heading", { level: 1, name: /Un agente para cada persona/ }),
    ).toBeInTheDocument();
    expect(screen.getByText(/No es\s+un canal oficial de Manuelita/)).toBeInTheDocument();
    const ledger = screen.getByRole("heading", { name: "¿Quién eres?" }).closest("section")!;
    expect(within(ledger).getAllByRole("listitem")).toHaveLength(5);
  });

  it("el planificador está abierto como los demás perfiles (spec 027)", () => {
    const { container } = render(<Home health={null} />);
    const row = container.querySelector('[data-profile="planificador"]')!;
    expect(within(row as HTMLElement).getByRole("button", { name: /15 % menos caña/ })).toBeInTheDocument();
    expect(container.querySelector(".profile-ledger__locked")).toBeNull();
    expect(screen.queryByText(/Solo equipo de planta autorizado/)).toBeNull();
    expect(screen.getByRole("link", { name: "Abrir la planificación" })).toHaveAttribute("href", "/planificacion");
  });

  it("la consulta de ejemplo del cliente B2B abre el agente con ese perfil y el mensaje listo", async () => {
    render(
      <>
        <Home health={null} />
        <Probe />
      </>,
    );
    await userEvent.click(screen.getByRole("button", { name: /Compro azúcar para mi empresa/ }));
    expect(window.location.pathname).toBe("/agente");
    expect(screen.getByTestId("probe")).toHaveTextContent(
      "cliente|draft|Compro azúcar para mi empresa, ¿qué certificaciones tienen?",
    );
  });

  it("conserva la consola de Consulta, Resumen y FAQ", () => {
    render(<Home health={null} />);
    expect(screen.getByTestId("rag-console")).toBeInTheDocument();
  });
});
