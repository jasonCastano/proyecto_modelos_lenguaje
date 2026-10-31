import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { MetricsBand } from "../components/MetricsBand";
import { showcase } from "./fixtures";

describe("MetricsBand", () => {
  it("muestra cifras y fuente desde la API", () => {
    render(<MetricsBand metrics={showcase.metrics} />);
    expect(screen.getByTestId("metric-band")).toBeInTheDocument();
    expect(screen.getByText("15.211")).toBeInTheDocument();
    expect(screen.getByText(/unidades/)).toBeInTheDocument();
  });
});
