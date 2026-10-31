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
