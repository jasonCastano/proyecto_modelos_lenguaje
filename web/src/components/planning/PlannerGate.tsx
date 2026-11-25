/** Aviso de acceso de la consola (spec 026, FR-019): sin datos ni cifras de planta. */
import { Link } from "../../lib/router";
import { Cane } from "../brand/ProductGlyphs";

export const GATE_TEXT =
  "La planificación es solo para el equipo de planta autorizado. Puedes hablar con el agente en otro perfil.";

export function PlannerGate({ reason }: { reason?: string }) {
  return (
    <section aria-labelledby="gate-title" className="planner-gate" data-testid="planner-gate">
      <Cane className="planner-gate__glyph" size={56} />
      <div>
        <h1 className="type-display planner-gate__title" id="gate-title">
          Planificación industrial
        </h1>
        <p>{reason ?? GATE_TEXT}</p>
        <Link className="action action--quiet" to="/agente">
          Hablar con el agente en otro perfil
        </Link>
      </div>
    </section>
  );
}
