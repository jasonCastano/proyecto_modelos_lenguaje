import { describe, expect, it } from "vitest";
import { render, screen } from "@testing-library/react";

import { PRODUCT_GLYPHS } from "../components/brand/ProductGlyphs";

describe("ProductGlyphs (spec 026, T019)", () => {
  it("renderiza los nueve pictogramas como decorativos por defecto", () => {
    const entries = Object.entries(PRODUCT_GLYPHS);
    expect(entries).toHaveLength(9);
    for (const [key, Glyph] of entries) {
      const { container, unmount } = render(<Glyph data-testid={key} />);
      const svg = container.querySelector("svg");
      expect(svg).not.toBeNull();
      expect(svg).toHaveAttribute("aria-hidden", "true");
      expect(svg).toHaveAttribute("stroke", "currentColor");
      unmount();
    }
  });

  it("con title se anuncia como imagen", () => {
    const Sugar = PRODUCT_GLYPHS.sugar;
    render(<Sugar title="Azúcar" />);
    expect(screen.getByRole("img", { name: "Azúcar" })).toBeInTheDocument();
  });
});
