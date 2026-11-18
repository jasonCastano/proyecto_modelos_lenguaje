import type { ContactCategory, ContactRecord, ContactStatus, Sentiment } from "../lib/types";

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
