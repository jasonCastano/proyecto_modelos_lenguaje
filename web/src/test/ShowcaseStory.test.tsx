import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { ShowcaseStory } from "../components/ShowcaseStory";
import { fallbackSections } from "../data/showcase";

describe("ShowcaseStory", () => {
  it("renderiza la secuencia narrativa completa", () => {
    render(<ShowcaseStory sections={fallbackSections} />);
    expect(screen.getByRole("heading", { name: /Del cañaveral/i })).toBeInTheDocument();
    expect(screen.getAllByRole("article")).toHaveLength(8);
    expect(
      screen.getByRole("heading", { name: "La información estaba dispersa" }),
    ).toBeInTheDocument();
    expect(screen.getByRole("heading", { name: "Lo que todavía falta" })).toBeInTheDocument();
  });

  it("incluye enlaces de evidencia y estados", () => {
    render(<ShowcaseStory sections={fallbackSections} />);
    expect(screen.getAllByText(/Alcance y 40 preguntas/).length).toBeGreaterThan(0);
    expect(screen.getByText("Pendiente")).toBeInTheDocument();
  });

  it("ofrece un rail de recorrido accesible", () => {
    render(<ShowcaseStory sections={fallbackSections} />);
    const rail = screen.getByRole("navigation", { name: "Recorrido del Módulo 1" });
    expect(rail).toBeInTheDocument();
    const links = within(rail).getAllByRole("link");
    expect(links).toHaveLength(8);
    expect(links[0]).toHaveAttribute("aria-current", "true");
    expect(links[0]).toHaveAttribute("href", "#modulo-problem");
    expect(links[7]).toHaveAttribute("href", "#modulo-limits");
  });
});
