/**
 * Memoria de largo plazo visible y borrable (spec 026, FR-008). «Borrar mi memoria» pide la misma
 * acción con aprobación que el chat: no se borra nada hasta que respondas «Sí» en la conversación.
 */
import type { MemoryItem, ProfileItem } from "../../lib/types";

const PROFILE_LABEL: Record<string, string> = {
  name: "Nombre",
  workplace: "Trabajo",
  role: "Cargo",
  city: "Ciudad",
};
const PREFERENCE_LABEL: Record<string, string> = {
  response_format: "Formato de respuesta",
  topics_of_interest: "Temas",
  language: "Idioma",
};

interface MemoryPanelProps {
  preferences: MemoryItem[];
  profile: ProfileItem[];
  canForget: boolean;
  requested: boolean;
  onForget: () => void;
}

export function MemoryPanel({ preferences, profile, canForget, requested, onForget }: MemoryPanelProps) {
  const empty = preferences.length === 0 && profile.length === 0;
  return (
    <section aria-labelledby="memory-title" className="side-panel">
      <h2 className="panel-title" id="memory-title">
        Lo que recuerda el agente
      </h2>
      {empty ? (
        <p className="side-panel__empty">
          Nada por ahora. Solo recuerda algo si se lo pides y respondes «Sí».
        </p>
      ) : (
        <dl className="memory-list">
          {profile.map((item) => (
            <div key={item.key}>
              <dt>{PROFILE_LABEL[item.key] ?? item.key}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
          {preferences.map((item) => (
            <div key={item.key}>
              <dt>{PREFERENCE_LABEL[item.key] ?? item.key}</dt>
              <dd>{item.value}</dd>
            </div>
          ))}
        </dl>
      )}
      {!empty ? (
        <button
          className="action action--quiet"
          disabled={!canForget || requested}
          onClick={onForget}
          type="button"
        >
          Borrar mi memoria
        </button>
      ) : null}
      {requested ? (
        <p className="side-panel__note" role="status">
          Responde «Sí» en la conversación para borrarla.
        </p>
      ) : null}
    </section>
  );
}
