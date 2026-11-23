import type { DictationControl } from "../lib/useDictation";

/**
 * Micrófono del chat (spec 023, contracts/ui.md).
 *
 * No aparece si el navegador no permite pedir el micrófono (contexto inseguro o sin
 * `getUserMedia`); aparece deshabilitado, con su motivo, si el servidor no tiene dictado.
 */

const STATE_TEXT: Partial<Record<DictationControl["state"], string>> = {
  requesting: "Esperando el permiso del micrófono…",
  listening: "Escuchando…",
  processing: "Procesando…",
  waiting_reply: "Enviando tu mensaje…",
  speaking: "Valer-IA está hablando; háblale para interrumpirla.",
};

function statusText(dictation: DictationControl): string {
  if (dictation.message) return dictation.message.text;
  const fromState = STATE_TEXT[dictation.state];
  if (fromState) return fromState;
  const status = dictation.status;
  if (status?.state === "loading") return "Preparando el micrófono…";
  if (status && !status.available) {
    return status.detail ?? "El dictado no está disponible en este momento.";
  }
  if (dictation.handsfree) return "Manos libres activo: habla cuando quieras.";
  return "";
}

export function MicButton({
  dictation,
  disabled = false,
}: {
  dictation: DictationControl;
  disabled?: boolean;
}) {
  if (!dictation.supported) return null;
  const { state, status, handsfree, level } = dictation;
  const unavailable = status !== null && !status.available;
  const recording = state === "listening" || (state === "speaking" && !handsfree);
  const label = recording ? "Terminar de hablar" : "Hablar con Valer-IA";
  const text = statusText(dictation);
  const reason = unavailable ? (status?.detail ?? "El dictado no está disponible.") : undefined;

  return (
    <div className="mic" data-state={state} data-testid="mic">
      <div className="mic-row">
        <button
          aria-label={label}
          aria-pressed={recording}
          className="mic-button"
          data-recording={recording ? "true" : "false"}
          data-testid="mic-button"
          disabled={unavailable || disabled || state === "processing" || state === "requesting"}
          onClick={() => dictation.toggle()}
          title={reason ?? label}
          type="button"
        >
          <span aria-hidden="true" className="mic-icon">
            {recording ? "■" : "🎙"}
          </span>
        </button>
        {state === "listening" ? (
          <div
            aria-label="Nivel de voz"
            aria-valuemax={100}
            aria-valuemin={0}
            aria-valuenow={level}
            className="mic-level"
            data-testid="mic-level"
            role="meter"
          >
            <span className="mic-level-bar" style={{ width: `${level}%` }} />
          </div>
        ) : null}
        {state === "listening" && !handsfree ? (
          <button
            className="btn btn-link"
            data-testid="mic-cancel"
            onClick={() => dictation.cancel()}
            type="button"
          >
            Cancelar
          </button>
        ) : null}
        <button
          aria-checked={handsfree}
          className="mic-switch"
          data-testid="mic-handsfree"
          disabled={unavailable || disabled}
          onClick={() => dictation.setHandsfree(!handsfree)}
          role="switch"
          type="button"
        >
          Manos libres
        </button>
      </div>
      <p
        aria-live="polite"
        className="mic-status"
        data-kind={dictation.message ? "error" : "info"}
        data-testid="mic-status"
      >
        {text}
      </p>
      {status?.privacy ? (
        <p className="mic-privacy" data-testid="mic-privacy">
          {status.privacy}
        </p>
      ) : null}
    </div>
  );
}
