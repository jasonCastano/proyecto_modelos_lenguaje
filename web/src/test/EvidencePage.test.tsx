import { afterEach, describe, expect, it, vi } from "vitest";
import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";

import * as evidenceApi from "../lib/evidence";
import { Evidence } from "../pages/Evidence";

afterEach(() => {
  vi.restoreAllMocks();
  window.sessionStorage.clear();
});

function mockApis() {
  vi.spyOn(evidenceApi, "getServices").mockResolvedValue({
    checked_at: "2026-11-24T20:00:00Z",
    services: [
      { id: "model", label: "Modelo DeepSeek", status: "up", reason: "Clave configurada.", action: "" },
      {
        id: "gateway",
        label: "Gateway OpenClaw",
        status: "down",
        reason: "Sin turnos del puente en 10 minutos.",
        action: "Ejecuta openclaw gateway status en el PC servidor.",
      },
    ],
  });
  vi.spyOn(evidenceApi, "getTools").mockResolvedValue({
    count: 2,
    tools: [
      {
        name: "search_documents",
        description: "Busca",
        kind: "read",
        requires_approval: false,
        routes: ["documental"],
        profiles: ["visitante", "cliente"],
        mcp_allowed: true,
      },
      {
        name: "save_production_proposal",
        description: "Guarda",
        kind: "write",
        requires_approval: true,
        routes: ["planning"],
        profiles: ["planificador"],
        mcp_allowed: false,
      },
    ],
  });
  vi.spyOn(evidenceApi, "getEvaluations").mockResolvedValue([
    {
      id: "herramientas",
      name: "Exactitud de herramienta",
      value: "86,0 % y 90,7 %",
      target: "≥ 90 %",
      meets: "partial",
      date: "2026-11-24",
      report: "docs/evaluacion_herramientas.md",
      note: "Variabilidad del modelo.",
    },
  ]);
  return vi.spyOn(evidenceApi, "getTrace").mockResolvedValue({
    thread_id: "t-1",
    turn: 1,
    turns: 1,
    question: "Tenemos 15 % menos caña",
    profile: "planificador",
    route: "planning",
    decided_by: "rules",
    plan_steps: ["estado", "compromisos", "optimizar"],
    tools: [
      { step: 1, name: "get_plant_state", args: {}, ok: true, duration_ms: 120, summary: "estado" },
      { step: 2, name: "optimize_production_plan", args: { cane_delta_pct: -15 }, ok: true, duration_ms: 310, summary: "plan" },
    ],
    duration_ms: 4200,
  });
}

describe("Evidence (spec 026, T056)", () => {
  it("filtra el catálogo por tipo y por perfil", async () => {
    mockApis();
    render(<Evidence />);
    const table = await screen.findByRole("table", { name: "Catálogo de herramientas del agente" });
    expect(within(table).getAllByRole("row")).toHaveLength(3);
    await userEvent.selectOptions(screen.getByLabelText("Tipo"), "write");
    expect(screen.getByText("1 de 2")).toBeInTheDocument();
    await userEvent.selectOptions(screen.getByLabelText("Tipo"), "all");
    await userEvent.selectOptions(screen.getByLabelText("Perfil"), "cliente");
    expect(screen.getByText("search_documents")).toBeInTheDocument();
    expect(screen.queryByText("save_production_proposal")).toBeNull();
  });

  it("muestra la traza con pasos numerados cuando hay hilo", async () => {
    window.sessionStorage.setItem("manuelita.chat.thread", JSON.stringify({ id: "t-1", variant: "agent" }));
    const trace = mockApis();
    render(<Evidence />);
    const steps = await screen.findByText("optimize_production_plan");
    expect(trace).toHaveBeenCalledWith("t-1", undefined);
    expect(steps.closest("ol")).not.toBeNull();
    expect(screen.getByText("planning")).toBeInTheDocument();
  });

  it("un servicio caído muestra qué hacer y las evaluaciones parciales no se ocultan", async () => {
    mockApis();
    render(<Evidence />);
    expect(await screen.findByText(/Ejecuta openclaw gateway status/)).toBeInTheDocument();
    expect(await screen.findByText("parcial")).toBeInTheDocument();
    expect(screen.getByText("Variabilidad del modelo.")).toBeInTheDocument();
    expect(screen.getByText(/Haz una pregunta en el agente/)).toBeInTheDocument();
  });
});
