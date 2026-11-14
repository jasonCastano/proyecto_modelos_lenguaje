import type { PendingAction } from "../lib/types";

/** Etiquetas de consentimiento por acción (spec 018, contracts/ui-views.md). */
export const QUICK_REPLY_LABELS: Record<PendingAction["tool"], { approve: string; reject: string }> = {
  remember_client: { approve: "Sí, recuérdame", reject: "No, gracias" },
  save_profile: { approve: "Sí, guárdalo", reject: "No, gracias" },
  save_preference: { approve: "Sí, guárdala", reject: "No" },
  forget_memory: { approve: "Sí, olvida mis datos", reject: "Cancelar" },
  export_conversation: { approve: "Sí, descárgala", reject: "No" },
};

/** Pregunta de Valer-IA para cada acción pendiente. */
export function quickReplyQuestion(action: PendingAction): string {
  const name = typeof action.args?.name === "string" ? action.args.name : "";
  switch (action.tool) {
    case "remember_client":
      return `${name ? `Gracias, ${name}. ` : ""}¿Quieres que te recuerde para tus próximas visitas?`;
    case "save_profile":
      return "¿Quieres que guarde estos datos para tus próximas conversaciones?";
    case "save_preference":
      return "¿Quieres que recuerde esta preferencia?";
    case "forget_memory":
      return "¿Confirmas que olvide los datos que guardé sobre ti?";
    case "export_conversation":
      return "¿Quieres descargar esta conversación?";
    default:
      return "¿Confirmas esta acción?";
  }
}

/** Respuestas rápidas de la vista normal (sin «editar»: el visitante decide sí o no). */
export function QuickReplies({
  action,
  busy,
  onDecide,
}: {
  action: PendingAction;
  busy: boolean;
  onDecide: (decision: "approve" | "reject") => void;
}) {
  const labels = QUICK_REPLY_LABELS[action.tool] ?? { approve: "Sí", reject: "No" };
  return (
    <div className="quick-replies" data-testid="quick-replies">
      <p className="chat-question quick-replies-question">{quickReplyQuestion(action)}</p>
      <div className="quick-replies-buttons">
        <button className="btn btn-accent" disabled={busy} onClick={() => onDecide("approve")} type="button">
          {labels.approve}
        </button>
        <button className="btn btn-link" disabled={busy} onClick={() => onDecide("reject")} type="button">
          {labels.reject}
        </button>
      </div>
    </div>
  );
}
