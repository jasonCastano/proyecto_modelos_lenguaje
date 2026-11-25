import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import * as planningApi from "../lib/planning";
import { resetPlatform, usePlatform } from "../lib/platform";
import { Planning } from "../pages/Planning";
import { comparison, plan, snapshot } from "./planningFixtures";

beforeEach(() => {
  window.sessionStorage.clear();
  window.history.replaceState(null, "", "/planificacion");
  resetPlatform();
});

afterEach(() => {
  vi.restoreAllMocks();
});

function Probe() {
  const { audience, outbox } = usePlatform();
  return (
    <output data-testid="probe">
      {audience}|{outbox?.text ?? ""}
    </output>
  );
}

describe("Planning (spec 026, T030)", () => {
  it("sin acceso muestra el aviso y no pide el estado de planta", async () => {
    vi.spyOn(planningApi, "getAccess").mockResolvedValue({ authorized: false, reason: "Solo equipo de planta." });
    const state = vi.spyOn(planningApi, "getState");
    render(<Planning />);
    expect(await screen.findByTestId("planner-gate")).toHaveTextContent("Solo equipo de planta.");
    expect(state).not.toHaveBeenCalled();
  });

  it("con acceso calcula, compara y lleva la explicación al agente", async () => {
    vi.spyOn(planningApi, "getAccess").mockResolvedValue({ authorized: true, reason: "ok" });
    vi.spyOn(planningApi, "getState").mockResolvedValue(snapshot);
    const postPlan = vi.spyOn(planningApi, "postPlan").mockResolvedValue(plan);
    const postCompare = vi.spyOn(planningApi, "postCompare").mockResolvedValue(comparison);
    render(
      <>
        <Planning />
        <Probe />
      </>,
    );
    expect(await screen.findByTestId("cane-flow")).toBeInTheDocument();
    expect(postPlan).toHaveBeenCalledWith({});
    expect(screen.getByText("Datos sintéticos de demostración", { selector: ".synthetic-tag" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Comparar con el plan base" }));
    expect(postCompare).toHaveBeenCalled();
    expect(await screen.findByRole("heading", { name: "Frente al plan base" })).toBeInTheDocument();

    await userEvent.click(screen.getByRole("button", { name: "Explicar con el agente" }));
    expect(window.location.pathname).toBe("/agente");
    const probe = screen.getByTestId("probe").textContent ?? "";
    expect(probe.startsWith("planificador|Explica el plan recomendado")).toBe(true);
    expect(probe).toContain(plan.plan_id);
  });
});
