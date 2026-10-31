import type { ReactNode } from "react";

import type { ApiError, CitedAnswer } from "../lib/types";
import { statusLabel } from "../lib/format";
import { SourceList } from "./SourceList";

function inline(text: string): ReactNode[] {
  return text.split(/(\*\*[^*]+\*\*)/g).map((part, index) => {
    if (part.startsWith("**") && part.endsWith("**")) {
      return <strong key={index}>{part.slice(2, -2)}</strong>;
    }
    return <span key={index}>{part}</span>;
  });
}

function RichText({ text }: { text: string }) {
  return (
    <>
      {text.split("\n").map((line, index) => {
        const trimmed = line.trim();
        if (!trimmed) {
          return <span key={index} className="rich-line" aria-hidden="true" />;
        }
        if (trimmed.startsWith("- ") || trimmed.startsWith("* ")) {
          return (
            <p className="rich-bullet" key={index}>
              <span aria-hidden="true">• </span>
              {inline(trimmed.slice(2))}
            </p>
          );
        }
        return <p key={index}>{inline(line)}</p>;
      })}
    </>
  );
}

interface AnswerPanelProps {
  answer: CitedAnswer | null;
  error: ApiError | null;
  status: "idle" | "submitting" | "success" | "fallback" | "error";
  onRetry: () => void;
  onDemo: () => void;
}

export function AnswerPanel({ answer, error, status, onRetry, onDemo }: AnswerPanelProps) {
  if (status === "submitting") {
    return (
      <div className="answer" data-testid="answer-panel" aria-live="polite">
        <div className="answer-head">
          <h3>Buscando evidencia</h3>
          <span className="loading-dots" aria-label="Cargando">
            <span />
            <span />
            <span />
          </span>
        </div>
        <p className="answer-body">Recuperando unidades y preparando una respuesta citada…</p>
      </div>
    );
  }

  if (status === "error" || error) {
    const safeError: ApiError =
      error ?? {
        code: "unexpected_error",
        message: "No se pudo completar la consulta.",
        retryable: true,
        action: "reintentar",
      };
    return (
      <div
        className="answer answer-error"
        data-testid="answer-panel"
        role="alert"
        aria-live="assertive"
      >
        <div className="answer-head">
          <h3>La consulta no se completó</h3>
          <span className="answer-meta">{safeError.code}</span>
        </div>
        <p className="answer-body">{safeError.message}</p>
        <div className="answer-actions">
          {safeError.retryable ? (
            <button className="btn btn-primary" type="button" onClick={onRetry}>
              Reintentar
            </button>
          ) : null}
          {safeError.action === "usar demo" || safeError.code === "config_missing_key" ? (
            <button className="btn btn-accent" type="button" onClick={onDemo}>
              Usar modo demostración
            </button>
          ) : null}
        </div>
      </div>
    );
  }

  if (!answer) {
    return null;
  }

  const fallback = answer.status === "fallback";
  return (
    <div
      className={`answer ${fallback ? "answer-fallback" : ""}`}
      data-testid="answer-panel"
      aria-live="polite"
    >
      <div className="answer-head">
        <h3>{fallback ? "No hay evidencia suficiente" : "Respuesta con fuentes"}</h3>
        <span className="answer-meta">
          {statusLabel(answer.status)} · {answer.model}
          <br />
          {answer.latency_ms.toFixed(0)} ms · {answer.citations.length} citas
        </span>
      </div>
      <div className="answer-body">
        <RichText text={answer.answer} />
      </div>
      <SourceList citations={answer.citations} />
      <div className="answer-actions">
        <button className="btn btn-secondary" type="button" onClick={onRetry}>
          Volver a preguntar
        </button>
      </div>
    </div>
  );
}
