import type {
  ContactCategory,
  ContactRecord,
  ContactStatus,
  ContactTurn,
  DialogueAct,
  Sentiment,
} from "../lib/types";

/** Etiquetas en español del registro del contacto (spec 019, contracts/api-changes.md). */
export const CATEGORY_LABEL: Record<ContactCategory, string> = {
  manuelita: "Manuelita",
  off_topic: "Tema ajeno",
  advice: "Consejo profesional",
  complaint: "Queja",
  unattainable: "No atendible",
  crisis: "Crisis",
  conduct: "Conducta",
  other: "Conversación",
};

export const STATUS_LABEL: Record<ContactStatus, string> = {
  resolved: "Resuelta",
  out_of_scope: "Fuera de alcance",
  not_attainable: "No atendible",
  needs_clarification: "Pide aclaración",
  referred: "Derivada a canal oficial",
  no_evidence: "Sin evidencia",
};

export const SENTIMENT_LABEL: Record<Sentiment, string> = {
  neutral: "neutral",
  satisfied: "satisfecho",
  confused: "confundido",
  frustrated: "frustrado",
  angry: "molesto",
  distressed: "angustiado",
};

/** Spec 020: actos de diálogo en español. */
export const ACT_LABEL: Record<DialogueAct, string> = {
  greeting: "saludo",
  smalltalk: "charla",
  off_topic: "fuera de tema",
  manuelita: "Manuelita",
  complaint: "queja",
  correction: "corrección",
  minimal: "mínimo",
  about_assistant: "sobre la asistente",
  closing: "cierre",
  thanks: "gracias",
  clarify: "aclaración",
};

/**
 * «saludo → charla ◆ → mínimo ↺ → fuera de tema ✂1»: ◆ marca un puente, ↺ una respuesta de respaldo
 * y ✂N las frases descartadas en la revisión (spec 021).
 */
export function actsTrail(acts: ContactTurn[]): string {
  return acts
    .map((turn) => {
      const cut = turn.discarded ? ` ✂${turn.discarded}` : "";
      const marks = `${turn.bridged ? " ◆" : ""}${turn.reviewed === "fallback" ? " ↺" : ""}${cut}`;
      return `${ACT_LABEL[turn.act] ?? turn.act}${marks}`;
    })
    .join(" → ");
}

/** Evolución emocional sin repeticiones seguidas: «frustrado → satisfecho». */
export function sentimentTrail(sentiments: Sentiment[]): string {
  const trail: string[] = [];
  for (const sentiment of sentiments) {
    const label = SENTIMENT_LABEL[sentiment] ?? sentiment;
    if (trail[trail.length - 1] !== label) trail.push(label);
  }
  return trail.join(" → ");
}

/**
 * Registro del contacto, como el CRM de un agente de call center: solicitudes con su categoría y
 * estado, evolución emocional y motivo. Solo aparece en la vista técnica y no contiene datos
 * personales (el servidor guarda únicamente etiquetas controladas).
 */
export function ContactRecordPanel({ record }: { record: ContactRecord }) {
  return (
    <section aria-label="Registro del contacto" className="contact-record" data-testid="contact-record">
      <header className="contact-record-header">
        <strong>Registro del contacto</strong>
        <span className="fragments-badge" data-kind={record.resolved ? "ok" : "warning"}>
          {record.resolved ? "Resuelto" : "Pendiente"}
        </span>
        {record.crisis ? (
          <span className="fragments-badge" data-kind="warning">
            Crisis atendida
          </span>
        ) : null}
        {record.hostile_turns > 0 ? (
          <span className="fragments-badge" data-kind="warning">
            Turnos hostiles: {record.hostile_turns}
          </span>
        ) : null}
      </header>
      <p className="contact-record-line">
        <span>Turnos: {record.turns}</span>
        <span data-testid="contact-sentiments">Emoción: {sentimentTrail(record.sentiments)}</span>
        {record.motive.length > 0 ? <span>Motivo: {record.motive.join(", ")}</span> : null}
      </p>
      {record.acts && record.acts.length > 0 ? (
        <p className="contact-record-line" data-testid="contact-acts">
          <span>Actos: {actsTrail(record.acts)}</span>
        </p>
      ) : null}
      <ul className="contact-record-requests">
        {record.requests.map((request, index) => (
          <li data-status={request.status} key={`${request.turn}-${index}`}>
            <span className="contact-record-turn">T{request.turn}</span> {CATEGORY_LABEL[request.category]} ·{" "}
            {request.topic} · <em>{STATUS_LABEL[request.status]}</em>
          </li>
        ))}
      </ul>
    </section>
  );
}
