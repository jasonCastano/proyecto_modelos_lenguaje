import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it } from "vitest";

import { RetrievedFragments } from "../components/RetrievedFragments";
import type { RetrievalTrace } from "../lib/types";

const trace: RetrievalTrace = {
  mode: "hybrid",
  semantic_available: true,
  candidates: 3,
  threshold: 0.3,
  fragments: [
    {
      unit_id: "u1",
      title: "Agua y comunidades",
      url: "https://example.com/agua",
      score: 0.87,
      semantic_score: 0.91,
      lexical_score: 0.78,
      origin: "both",
      status: "used",
      reason: null,
    },
    {
      unit_id: "u2",
      title: "Programa de reforestación",
      url: "https://example.com/bosque",
      score: 0.55,
      semantic_score: 0.71,
      lexical_score: null,
      origin: "semantic",
      status: "omitted_budget",
      reason: "Presupuesto de contexto agotado",
    },
    {
      unit_id: "u3",
      title: "Historia del ingenio",
      url: "",
      score: 0.19,
      semantic_score: 0.19,
      lexical_score: null,
      origin: "semantic",
      status: "omitted_threshold",
      reason: "Similitud por debajo de 0.30",
    },
  ],
  used_unit_ids: ["u1"],
  notes: [],
  elapsed_ms: 41.7,
};

describe("RetrievedFragments", () => {
  it("muestra el modo y los fragmentos usados sin interacción", () => {
    render(<RetrievedFragments trace={trace} />);

    expect(screen.getByTestId("retrieval-mode")).toHaveTextContent(/Híbrida/i);
    expect(screen.getByText("Agua y comunidades")).toBeInTheDocument();
    expect(screen.getByText("0.87")).toBeInTheDocument();
    expect(screen.queryByTestId("omitted-fragments")).not.toBeInTheDocument();
  });

  it("muestra los descartados con su motivo al desplegar", async () => {
    render(<RetrievedFragments trace={trace} />);

    await userEvent.click(screen.getByRole("button", { name: /Ver descartados/i }));

    expect(screen.getByTestId("omitted-fragments")).toBeInTheDocument();
    expect(screen.getByText("Presupuesto de contexto agotado")).toBeInTheDocument();
    expect(screen.getByText("Similitud por debajo de 0.30")).toBeInTheDocument();
  });

  it("declara la ausencia de evidencia", () => {
    render(
      <RetrievedFragments
        trace={{ ...trace, mode: "none", fragments: [], used_unit_ids: [], candidates: 0 }}
      />,
    );

    expect(screen.getByText(/Sin evidencia recuperada/i)).toBeInTheDocument();
    expect(screen.getByTestId("retrieval-mode")).toHaveTextContent(/Sin evidencia/i);
  });

  it("no renderiza nada sin traza", () => {
    const { container } = render(<RetrievedFragments trace={null} />);

    expect(container).toBeEmptyDOMElement();
  });
});
