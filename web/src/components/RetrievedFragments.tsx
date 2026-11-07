import { useState } from "react";

import type { RetrievalMode, RetrievalTrace } from "../lib/types";

const MODE_LABEL: Record<RetrievalMode, string> = {
  hybrid: "Híbrida",
  semantic: "Semántica",
  lexical: "Léxica",
  none: "Sin evidencia",
};

const ORIGIN_LABEL: Record<string, string> = {
  semantic: "semántica",
  lexical: "léxica",
  both: "ambas",
};

interface RetrievedFragmentsProps {
  trace: RetrievalTrace | null | undefined;
}

export function RetrievedFragments({ trace }: RetrievedFragmentsProps) {
  const [open, setOpen] = useState(false);

  if (!trace) {
    return null;
  }

  const used = trace.fragments.filter((fragment) => fragment.status === "used");
  const omitted = trace.fragments.filter((fragment) => fragment.status !== "used");

  return (
    <section
      className="fragments"
      data-testid="retrieved-fragments"
      aria-label="Fragmentos recuperados"
    >
      <div className="fragments-head">
        <span className="fragments-badge" data-testid="retrieval-mode">
          Recuperación: {MODE_LABEL[trace.mode]}
        </span>
        <span className="fragments-meta">
          {trace.candidates} candidatos · umbral {trace.threshold.toFixed(2)} ·{" "}
          {trace.elapsed_ms.toFixed(0)} ms
        </span>
      </div>

      {used.length === 0 ? (
        <p className="fragments-empty">Sin evidencia recuperada.</p>
      ) : (
        <ol className="fragments-list">
          {used.map((fragment) => (
            <li key={fragment.unit_id}>
              <span className="fragment-score">{fragment.score.toFixed(2)}</span>
              {fragment.url ? (
                <a href={fragment.url} target="_blank" rel="noreferrer">
                  {fragment.title || fragment.unit_id}
                </a>
              ) : (
                <span>{fragment.title || fragment.unit_id}</span>
              )}
              <span className="fragment-origin">
                {ORIGIN_LABEL[fragment.origin] ?? fragment.origin}
              </span>
            </li>
          ))}
        </ol>
      )}

      {omitted.length > 0 ? (
        <div className="fragments-omitted-block">
          <button
            className="btn btn-link"
            type="button"
            onClick={() => setOpen((value) => !value)}
            aria-expanded={open}
          >
            {open ? "Ocultar" : "Ver"} descartados ({omitted.length})
          </button>
          {open ? (
            <ul className="fragments-omitted" data-testid="omitted-fragments">
              {omitted.map((fragment) => (
                <li key={`${fragment.unit_id}-${fragment.status}`}>
                  <span className="fragment-score">{fragment.score.toFixed(2)}</span>
                  <span>{fragment.title || fragment.unit_id}</span>
                  <span className="fragment-reason">{fragment.reason}</span>
                </li>
              ))}
            </ul>
          ) : null}
        </div>
      ) : null}

      {trace.notes.length > 0 ? (
        <ul className="fragments-notes">
          {trace.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
      ) : null}
    </section>
  );
}
