/**
 * Perfil activo (spec 027, FR-008 y FR-009): una línea que dice con qué perfil atiende el agente.
 * Con el planificador recuerda, sin bloquear, que los datos de planta son sintéticos y ofrece la
 * consola de planificación.
 */
import { audienceCard } from "../../data/profileSuggestions";
import { Link } from "../../lib/router";

export function ProfileNotice({ audience }: { audience: string }) {
  const card = audienceCard(audience);
  const planner = card.key === "planificador";
  return (
    <p aria-live="polite" className="profile-notice" data-testid="profile-notice">
      <span>
        Te atiende como {card.label}.{planner ? null : ` ${card.canAsk}`}
      </span>
      {planner ? (
        <>
          <span className="profile-notice__synthetic">
            Los datos de planta son sintéticos, no la operación real de Manuelita.
          </span>
          <Link className="action action--quiet" to="/planificacion">
            Abrir la planificación
          </Link>
        </>
      ) : null}
    </p>
  );
}
