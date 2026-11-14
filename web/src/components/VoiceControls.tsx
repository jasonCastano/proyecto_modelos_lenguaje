import type { VoiceControl } from "../lib/useVoice";

/** Controles de la voz del agente (spec 016, contracts/ui-voice.md). */
export function VoiceControls({ voice, showUnavailable }: { voice: VoiceControl; showUnavailable: boolean }) {
  const active = voice.available && !voice.muted;
  return (
    <div className="voice-controls" data-testid="voice-controls">
      <button
        aria-pressed={active}
        className="btn btn-link"
        data-testid="voice-toggle"
        disabled={!voice.available}
        onClick={voice.toggleMuted}
        title={active ? "Silenciar la voz del asistente" : "Activar la voz del asistente"}
        type="button"
      >
        {active ? "🔊 Voz activada" : "🔇 Voz silenciada"}
      </button>
      {voice.speaking ? (
        <>
          <button className="btn btn-link" data-testid="voice-stop" onClick={voice.stop} type="button">
            ⏹ Detener
          </button>
          <span aria-live="polite" className="fragments-meta" data-testid="voice-speaking">
            Leyendo respuesta…
          </span>
        </>
      ) : null}
      {voice.blocked && active ? (
        <button className="btn btn-link" data-testid="voice-resume" onClick={voice.resume} type="button">
          ▶ Reproducir voz
        </button>
      ) : null}
      {showUnavailable && !voice.available && voice.detail ? (
        <span className="fragments-meta" data-testid="voice-unavailable" role="note">
          La voz no está disponible: {voice.detail.replace(/\.$/, "")}. El chat sigue funcionando por texto.
        </span>
      ) : null}
    </div>
  );
}
