import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ShowcaseStory } from "../components/ShowcaseStory";
import { fallbackSections } from "../data/showcase";

describe("ShowcaseStory", () => {
  it("renderiza la secuencia narrativa completa", () => {
    render(<ShowcaseStory sections={fallbackSections} />);
    expect(screen.getByRole("heading", { name: /Del cañaveral/i })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(8);
    expect(screen.getByText("La información estaba dispersa")).toBeInTheDocument();
    expect(screen.getByText("Lo que todavía falta")).toBeInTheDocument();
  });

  it("incluye enlaces de evidencia y estados", () => {
    render(<ShowcaseStory sections={fallbackSections} />);
    expect(screen.getAllByText(/Alcance y 40 preguntas/).length).toBeGreaterThan(0);
    expect(screen.getByText("Pendiente")).toBeInTheDocument();
  });
});
