import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApprovalCard } from "../components/ApprovalCard";
import type { PendingAction } from "../lib/types";

const action: PendingAction = {
  action_id: "act_01",
  tool: "save_preference",
  args: { key: "response_format", value: "viñetas" },
  proposed_at: "2026-11-11T10:00:00Z",
};

describe("ApprovalCard", () => {
  it("muestra la acción propuesta y aprueba sin cambios", async () => {
    const onDecide = vi.fn();
    const user = userEvent.setup();
    render(<ApprovalCard action={action} onDecide={onDecide} />);

    expect(screen.getByRole("alertdialog")).toHaveTextContent("Guardar una preferencia");
    expect(screen.getByLabelText("Valor")).toHaveValue("viñetas");
    await user.click(screen.getByRole("button", { name: "Aprobar" }));

    expect(onDecide).toHaveBeenCalledWith("approve");
  });

  it("envía los argumentos editados como edit", async () => {
    const onDecide = vi.fn();
    const user = userEvent.setup();
    render(<ApprovalCard action={action} onDecide={onDecide} />);

    const value = screen.getByLabelText("Valor");
    await user.clear(value);
    await user.type(value, "breve");
    await user.click(screen.getByRole("button", { name: "Aprobar con cambios" }));

    expect(onDecide).toHaveBeenCalledWith("edit", { key: "response_format", value: "breve" });
  });

  it("rechaza la acción", async () => {
    const onDecide = vi.fn();
    const user = userEvent.setup();
    render(<ApprovalCard action={{ ...action, tool: "forget_memory", args: {} }} onDecide={onDecide} />);

    expect(screen.getByRole("alertdialog")).toHaveTextContent("Olvidar tus preferencias");
    await user.click(screen.getByRole("button", { name: "Rechazar" }));

    expect(onDecide).toHaveBeenCalledWith("reject");
  });
});
