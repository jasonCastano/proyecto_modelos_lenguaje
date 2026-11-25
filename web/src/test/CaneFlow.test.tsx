import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { CaneFlow, FLOW_HEIGHT } from "../components/planning/CaneFlow";
import { comparison, infeasible, plan } from "./planningFixtures";

function thickness(id: string): number {
  const band = document.querySelector(`[data-band="${id}"]`);
  return Number(band?.getAttribute("data-thickness"));
}

describe("CaneFlow (spec 026, T027)", () => {
  it("el grosor de cada banda es proporcional y azúcar + etanol llenan la altura útil", () => {
    render(<CaneFlow plan={plan} />);
    const sugar = thickness("sugar");
    const ethanol = thickness("ethanol");
    expect(sugar + ethanol).toBeCloseTo(FLOW_HEIGHT, 5);
    expect(sugar / ethanol).toBeCloseTo(plan.mix.x_s / plan.mix.x_e, 5);
    expect(thickness("power") / sugar).toBeCloseTo(plan.mix.b / plan.mix.x_s, 5);
  });

  it("se anuncia como imagen con las tres cifras y trae la tabla equivalente", () => {
    render(<CaneFlow plan={plan} />);
    const figure = screen.getByRole("img", { name: /Reparto de la caña/ });
    const desc = figure.querySelector("desc")?.textContent ?? "";
    expect(desc).toContain("39.513");
    expect(desc).toContain("6.506");
    expect(desc).toContain("12.977");
    const table = screen.getByRole("table");
    expect(table.closest("details")).not.toBeNull();
  });

  it("sin solución factible no dibuja bandas y lo dice", () => {
    render(<CaneFlow plan={infeasible} />);
    expect(document.querySelectorAll("[data-band]")).toHaveLength(0);
    expect(screen.getByText(/No hay un plan que cumpla todos los compromisos/)).toBeInTheDocument();
  });

  it("con movimiento reducido no aplica la animación", () => {
    const { container } = render(<CaneFlow plan={plan} reducedMotion />);
    expect(container.querySelector(".cane-flow--animate")).toBeNull();
  });

  it("al comparar dibuja el plan base en contorno", () => {
    render(<CaneFlow compareTo={comparison.base} plan={plan} />);
    expect(document.querySelectorAll("[data-base-band]").length).toBe(3);
  });
});
