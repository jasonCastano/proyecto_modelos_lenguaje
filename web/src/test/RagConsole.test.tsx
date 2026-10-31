import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";

import { RagConsole } from "../components/RagConsole";
import type { ApiError } from "../lib/types";
import { answerWithCitation, fallbackAnswer, healthy } from "./fixtures";

const rag = vi.hoisted(() => ({
  mode: "real" as "real" | "demo",
  setMode: vi.fn(),
  task: "qa" as "qa" | "summary" | "faq",
  setTask: vi.fn(),
  status: "idle" as "idle" | "submitting" | "success" | "fallback" | "error",
  answer: null as typeof answerWithCitation | null,
  faqItems: [],
  error: null as ApiError | null,
  ask: vi.fn(),
  summarize: vi.fn(),
  faq: vi.fn(),
  retry: vi.fn(),
  clearError: vi.fn(),
}));

vi.mock("../hooks/useRag", () => ({
  useRag: () => rag,
}));

describe("RagConsole", () => {
  beforeEach(() => {
    rag.mode = "real";
    rag.task = "qa";
    rag.status = "idle";
    rag.answer = null;
    rag.error = null;
    rag.ask.mockReset();
    rag.setTask.mockReset();
  });

  it("rechaza una pregunta vacía sin llamar a la API", async () => {
    render(<RagConsole health={healthy} />);
    await userEvent.click(screen.getByTestId("ask-button"));
    expect(await screen.findByText("Escribe una pregunta antes de enviar.")).toBeInTheDocument();
    expect(rag.ask).not.toHaveBeenCalled();
  });

  it("envía la pregunta limpia", async () => {
    render(<RagConsole health={healthy} />);
    await userEvent.type(screen.getByTestId("question-input"), "  ¿Qué productos ofrece Manuelita?  ");
    await userEvent.click(screen.getByTestId("ask-button"));
    expect(rag.ask).toHaveBeenCalledWith("¿Qué productos ofrece Manuelita?");
  });

  it("muestra una respuesta con cita", () => {
    rag.status = "success";
    rag.answer = answerWithCitation;
    render(<RagConsole health={healthy} />);
    expect(screen.getByText(/azúcar y derivados/i)).toBeInTheDocument();
    expect(screen.getByText(/Manuelita — Productos/)).toBeInTheDocument();
    expect(screen.getByTestId("source-list")).toBeInTheDocument();
  });

  it("muestra el fallback sin fuentes", () => {
    rag.status = "fallback";
    rag.answer = fallbackAnswer;
    render(<RagConsole health={healthy} />);
    expect(screen.getByRole("heading", { name: /No hay evidencia suficiente/i })).toBeInTheDocument();
    expect(screen.queryByTestId("source-list")).not.toBeInTheDocument();
  });

  it("muestra un error accionable y permite reintentar", async () => {
    rag.status = "error";
    rag.error = {
      code: "timeout",
      message: "El proveedor tardó demasiado.",
      retryable: true,
      action: "reintentar",
    };
    render(<RagConsole health={healthy} />);
    expect(screen.getByText("El proveedor tardó demasiado.")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Reintentar" }));
    expect(rag.retry).toHaveBeenCalled();
  });
});
