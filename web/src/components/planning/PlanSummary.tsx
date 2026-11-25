/** Lo que limita el plan, las alternativas y los supuestos (spec 026, FR-013). Sin cálculos propios. */
import { fmt, millions, signed } from "../../lib/planningFormat";
import type { PlanResponse } from "../../lib/types";

export const DECISION_PHRASE = "El agente recomienda; el equipo de planta decide.";

export function PlanSummary({ plan }: { plan: PlanResponse }) {
  const binding = plan.binding;
  const optimal = plan.status === "optimal";
  return (
    <section aria-labelledby="summary-title" className="plan-summary">
      <h2 className="panel-title" id="summary-title">
        {optimal ? "Por qué este plan" : "Qué falta"}
      </h2>
      {optimal ? (
        <p className="plan-summary__margin">
          Margen de la semana: <strong className="type-data">{millions(plan.margin)}</strong>
        </p>
      ) : (
        <ul className="plan-summary__shortfalls">
          {plan.shortfalls.map((item) => (
            <li key={item.commitment_id}>
              {item.commitment_id}: faltan{" "}
              <span className="type-data">
                {fmt(item.missing)} {item.unit}
              </span>
            </li>
          ))}
        </ul>
      )}
      {binding ? (
        <p className="plan-summary__binding">
          Lo que limita: <strong>{binding.constraint}</strong>. Cada unidad que se relaje vale{" "}
          <span className="type-data">{fmt(binding.dual)}</span> {binding.unit}.
        </p>
      ) : null}
      {plan.alternatives.length ? (
        <ul className="plan-summary__alternatives">
          {plan.alternatives.map((alternative) => (
            <li key={alternative.name}>
              Alternativa «{alternative.name}»: margen{" "}
              <span className="type-data">{millions(alternative.margin)}</span> (
              <span className="type-data">
                {signed(alternative.delta_vs_best / 1_000_000)} millones
              </span>
              ){alternative.violations?.length ? `; incumple: ${alternative.violations.join(", ")}` : ""}.
            </li>
          ))}
        </ul>
      ) : null}
      <details className="plan-summary__assumptions">
        <summary>Supuestos del modelo</summary>
        <ul>
          {plan.assumptions.map((item) => (
            <li key={item}>{item}</li>
          ))}
        </ul>
      </details>
      <p className="plan-summary__decision">
        {plan.decision_phrase ?? DECISION_PHRASE}{" "}
        <span className="type-data">plan_id {plan.plan_id}</span>
      </p>
    </section>
  );
}
