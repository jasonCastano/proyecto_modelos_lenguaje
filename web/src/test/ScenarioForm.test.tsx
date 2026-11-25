import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ScenarioForm } from "../components/planning/ScenarioForm";
import { snapshot } from "./planningFixtures";

function setup() {
  const onCalculate = vi.fn();
  const onCompare = vi.fn();
  render(
    <ScenarioForm busy={false} onCalculate={onCalculate} onCompare={onCompare} snapshot={snapshot} />,
  );
  return { onCalculate, onCompare };
}

describe("ScenarioForm (spec 026, T028)", () => {
  it("toma los rangos del estado de planta", () => {
    setup();
    const cane = screen.getByRole("spinbutton", { name: /Caña disponible/ });
    expect(cane).toHaveAttribute("min", "-50");
    expect(cane).toHaveAttribute("max", "50");
    const quality = screen.getByRole("spinbutton", { name: /Calidad/ });
    expect(quality).toHaveAttribute("min", "9");
    expect(quality).toHaveAttribute("max", "16");
  });

  it("fuera de rango muestra el rango válido y deshabilita «Calcular plan»", () => {
    setup();
    const cane = screen.getByRole("spinbutton", { name: /Caña disponible/ });
    fireEvent.change(cane, { target: { value: "-80" } });
    expect(screen.getByText("Usa un valor entre −50 % y 50 %")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Calcular plan" })).toBeDisabled();
  });

  it("envía solo los campos tocados", async () => {
    const { onCalculate, onCompare } = setup();
    const cane = screen.getByRole("spinbutton", { name: /Caña disponible/ });
    fireEvent.change(cane, { target: { value: "-15" } });
    await userEvent.click(screen.getByRole("button", { name: "Calcular plan" }));
    expect(onCalculate).toHaveBeenCalledWith({ cane_delta_pct: -15 });
    await userEvent.click(screen.getByRole("radio", { name: /Más energía/ }));
    await userEvent.click(screen.getByRole("button", { name: "Comparar con el plan base" }));
    expect(onCompare).toHaveBeenCalledWith({ cane_delta_pct: -15, prioritize: "power" });
  });
});
