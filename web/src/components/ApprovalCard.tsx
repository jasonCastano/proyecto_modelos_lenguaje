import { useState } from "react";

import type { PendingAction } from "../lib/types";

type Decision = "approve" | "edit" | "reject";

const TOOL_LABEL: Record<PendingAction["tool"], string> = {
  save_preference: "Guardar una preferencia",
  save_profile: "Guardar datos de tu perfil",
  forget_memory: "Olvidar tus preferencias y tu perfil",
  export_conversation: "Exportar la conversación",
};

const ARG_LABEL: Record<string, string> = {
  key: "Preferencia",
  value: "Valor",
  format: "Formato",
  name: "Nombre",
  workplace: "Lugar de trabajo",
  role: "Cargo",
  city: "Ciudad",
};

interface ApprovalCardProps {
  action: PendingAction;
  busy?: boolean;
  onDecide: (decision: Decision, args?: Record<string, unknown>) => void;
}

export function ApprovalCard({ action, busy = false, onDecide }: ApprovalCardProps) {
  const [args, setArgs] = useState<Record<string, string>>(() =>
    Object.fromEntries(Object.entries(action.args).map(([key, value]) => [key, String(value)])),
  );
  const edited = Object.entries(args).some(([key, value]) => String(action.args[key]) !== value);
  const keys = Object.keys(args);

  return (
    <section
      className="approval-card"
      data-testid="approval-card"
      role="alertdialog"
      aria-labelledby="approval-title"
    >
      <p className="console-kicker">Requiere tu aprobación</p>
      <h3 id="approval-title">{TOOL_LABEL[action.tool]}</h3>
      <p className="fragments-meta">
        El asistente propone esta acción. No se ejecuta hasta que decidas.
      </p>
      {keys.length > 0 ? (
        <div className="approval-args">
          {keys.map((key) => (
            <div className="field" key={key}>
              <label htmlFor={`approval-${key}`}>{ARG_LABEL[key] ?? key}</label>
              <input
                className="select-input"
                id={`approval-${key}`}
                onChange={(event) => setArgs((current) => ({ ...current, [key]: event.target.value }))}
                value={args[key]}
              />
            </div>
          ))}
        </div>
      ) : null}
      <div className="answer-actions">
        <button
          className="btn btn-accent"
          disabled={busy}
          onClick={() => (edited ? onDecide("edit", args) : onDecide("approve"))}
          type="button"
        >
          {edited ? "Aprobar con cambios" : "Aprobar"}
        </button>
        <button
          className="btn btn-secondary"
          disabled={busy}
          onClick={() => onDecide("reject")}
          type="button"
        >
          Rechazar
        </button>
      </div>
    </section>
  );
}
