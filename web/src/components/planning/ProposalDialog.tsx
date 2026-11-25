/**
 * Guardar propuesta en dos pasos (spec 026, R9; contracts/web-ui.md): el backend recalcula el plan
 * y devuelve la pregunta; nada se guarda sin «Sí, guardar». El diálogo atrapa el foco y lo devuelve
 * al botón al cerrarse. El aviso repite el verbo: «Propuesta guardada» o «Propuesta descartada».
 */
import { useEffect, useRef, useState, type KeyboardEvent } from "react";

import { ApiClientError, type PendingProposal, type ProposalOutcome } from "../../lib/types";

interface ProposalDialogProps {
  disabled: boolean;
  create: () => Promise<PendingProposal>;
  decide: (confirmationId: string, decision: "yes" | "no") => Promise<ProposalOutcome>;
}

export function ProposalDialog({ disabled, create, decide }: ProposalDialogProps) {
  const [pending, setPending] = useState<PendingProposal | null>(null);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<{ kind: "ok" | "error"; text: string } | null>(null);
  const opener = useRef<HTMLButtonElement>(null);
  const yes = useRef<HTMLButtonElement>(null);
  const no = useRef<HTMLButtonElement>(null);

  useEffect(() => {
    if (pending) yes.current?.focus();
  }, [pending]);

  function errorText(caught: unknown): string {
    return caught instanceof ApiClientError
      ? caught.apiError.message
      : "No se pudo completar la acción. Vuelve a intentarlo.";
  }

  async function open() {
    setBusy(true);
    setNotice(null);
    try {
      setPending(await create());
    } catch (caught) {
      setNotice({ kind: "error", text: errorText(caught) });
    } finally {
      setBusy(false);
    }
  }

  function close() {
    setPending(null);
    window.setTimeout(() => opener.current?.focus(), 0);
  }

  async function answer(decision: "yes" | "no") {
    if (!pending) return;
    setBusy(true);
    try {
      const outcome = await decide(pending.confirmation_id, decision);
      setNotice({ kind: "ok", text: outcome.message });
    } catch (caught) {
      setNotice({ kind: "error", text: errorText(caught) });
    } finally {
      setBusy(false);
      close();
    }
  }

  function trap(event: KeyboardEvent<HTMLDivElement>) {
    if (event.key === "Escape") {
      event.preventDefault();
      void answer("no");
      return;
    }
    if (event.key !== "Tab") return;
    event.preventDefault();
    const next = document.activeElement === yes.current ? no.current : yes.current;
    next?.focus();
  }

  return (
    <div className="proposal">
      <button
        className="action action--primary"
        disabled={disabled || busy}
        onClick={() => void open()}
        ref={opener}
        type="button"
      >
        Guardar propuesta
      </button>
      {notice ? (
        <p className="proposal__notice" data-kind={notice.kind} role="status">
          {notice.text}
        </p>
      ) : null}
      {pending ? (
        <div className="proposal__backdrop">
          <div
            aria-describedby="proposal-summary"
            aria-labelledby="proposal-question"
            aria-modal="true"
            className="proposal__dialog"
            onKeyDown={trap}
            role="dialog"
          >
            <p className="proposal__question" id="proposal-question">
              {pending.question}
            </p>
            <p className="proposal__summary" id="proposal-summary">
              {pending.summary}
            </p>
            <p className="proposal__meta type-data">plan_id {pending.plan_id}</p>
            <div className="proposal__actions">
              <button
                className="action action--primary"
                disabled={busy}
                onClick={() => void answer("yes")}
                ref={yes}
                type="button"
              >
                Sí, guardar
              </button>
              <button
                className="action action--quiet"
                disabled={busy}
                onClick={() => void answer("no")}
                ref={no}
                type="button"
              >
                No
              </button>
            </div>
          </div>
        </div>
      ) : null}
    </div>
  );
}
