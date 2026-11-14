import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { DemoBanner } from "../components/DemoBanner";
import { healthy } from "./fixtures";

describe("DemoBanner", () => {
  it("marca el modo demostración y permite volver al proveedor real", async () => {
    const onUseReal = vi.fn();
    render(
      <DemoBanner
        health={healthy}
        mode="demo"
        onEnableDemo={vi.fn()}
        onUseReal={onUseReal}
      />,
    );
    expect(screen.getByTestId("demo-banner")).toHaveTextContent(/simuladas/i);
    await userEvent.click(screen.getByRole("button", { name: /Volver al proveedor real/i }));
    expect(onUseReal).toHaveBeenCalled();
  });

  it("avisa cuando el servidor usa el corpus de prueba adversarial", () => {
    render(
      <DemoBanner
        health={{ ...healthy, adversarial_corpus: true }}
        mode="real"
        onEnableDemo={vi.fn()}
        onUseReal={vi.fn()}
      />,
    );
    expect(screen.getByTestId("adversarial-banner")).toHaveTextContent(
      /Corpus de prueba adversarial activo/i,
    );
  });

  it("no muestra el aviso adversarial con el corpus real", () => {
    render(
      <DemoBanner
        health={{ ...healthy, adversarial_corpus: false }}
        mode="real"
        onEnableDemo={vi.fn()}
        onUseReal={vi.fn()}
      />,
    );
    expect(screen.queryByTestId("adversarial-banner")).toBeNull();
  });

  it("ofrece demo cuando falta la clave", async () => {
    const onEnableDemo = vi.fn();
    render(
      <DemoBanner
        health={{ ...healthy, configured: false, ok: false }}
        mode="real"
        onEnableDemo={onEnableDemo}
        onUseReal={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: /Usar modo demostración/i }));
    expect(onEnableDemo).toHaveBeenCalled();
  });
});
