import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { CaneField } from "../components/CaneField";
import { ProductMotifs } from "../components/ProductMotifs";

describe("motivos visuales", () => {
  it("describe el cañaveral sin ocultar el texto alternativo", () => {
    render(<CaneField />);
    expect(screen.getByTitle(/Cañaveral lineal/i)).toBeInTheDocument();
  });

  it("presenta cinco motivos de producto", () => {
    render(<ProductMotifs />);
    expect(screen.getAllByRole("article")).toHaveLength(5);
    for (const name of ["Caña", "Azúcar", "Etanol", "Energía", "Palma"]) {
      expect(screen.getByRole("heading", { name })).toBeInTheDocument();
    }
  });
});
