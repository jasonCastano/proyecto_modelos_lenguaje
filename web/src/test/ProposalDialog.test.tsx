import { describe, expect, it, vi } from "vitest";
import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import { ProposalDialog } from "../components/planning/ProposalDialog";
import { ApiClientError } from "../lib/types";

const pending = {
  confirmation_id: "abc",
  plan_id: "p-0aed9288",
  summary: "Azúcar 86 % y etanol 14 % de la caña.",
  expires_at: "2026-11-28T15:05:00Z",
  question: "¿Guardar esta propuesta para revisión del equipo de planta?",
};

function setup(decide = vi.fn()) {
  const create = vi.fn().mockResolvedValue(pending);
  render(<ProposalDialog create={create} decide={decide} disabled={false} />);
  return { create, decide };
}

describe("ProposalDialog (spec 026, T029)", () => {
  it("abre el diálogo con la pregunta y el resumen, y atrapa el foco", async () => {
    setup();
    const opener = screen.getByRole("button", { name: "Guardar propuesta" });
    await userEvent.click(opener);
    const dialog = await screen.findByRole("dialog", { name: /Guardar esta propuesta/ });
    expect(dialog).toHaveTextContent(pending.summary);
    const yes = screen.getByRole("button", { name: "Sí, guardar" });
    const no = screen.getByRole("button", { name: "No" });
    expect(yes).toHaveFocus();
    await userEvent.tab();
    expect(no).toHaveFocus();
    await userEvent.tab();
    expect(yes).toHaveFocus();
  });

  it("«No» descarta y devuelve el foco al botón", async () => {
    const decide = vi.fn().mockResolvedValue({
      status: "discarded",
      plan_id: pending.plan_id,
      message: "Propuesta descartada. No se guardó nada.",
    });
    setup(decide);
    await userEvent.click(screen.getByRole("button", { name: "Guardar propuesta" }));
    await userEvent.click(await screen.findByRole("button", { name: "No" }));
    expect(decide).toHaveBeenCalledWith("abc", "no");
    expect(await screen.findByText(/Propuesta descartada/)).toBeInTheDocument();
    await waitFor(() =>
      expect(screen.getByRole("button", { name: "Guardar propuesta" })).toHaveFocus(),
    );
  });

  it("«Sí, guardar» muestra «Propuesta guardada»", async () => {
    const decide = vi.fn().mockResolvedValue({
      status: "saved",
      plan_id: pending.plan_id,
      message: "Propuesta guardada. El agente recomienda; el equipo de planta decide.",
    });
    setup(decide);
    await userEvent.click(screen.getByRole("button", { name: "Guardar propuesta" }));
    await userEvent.click(await screen.findByRole("button", { name: "Sí, guardar" }));
    expect(decide).toHaveBeenCalledWith("abc", "yes");
    expect(await screen.findByText(/Propuesta guardada/)).toBeInTheDocument();
  });

  it("una propuesta vencida lo explica", async () => {
    const decide = vi.fn().mockRejectedValue(
      new ApiClientError({
        code: "proposal_expired",
        message: "La propuesta venció; vuelve a calcular el plan.",
        retryable: false,
        action: "recalcular",
      }),
    );
    setup(decide);
    await userEvent.click(screen.getByRole("button", { name: "Guardar propuesta" }));
    await userEvent.click(await screen.findByRole("button", { name: "Sí, guardar" }));
    expect(
      await screen.findByText("La propuesta venció; vuelve a calcular el plan."),
    ).toBeInTheDocument();
  });
});
