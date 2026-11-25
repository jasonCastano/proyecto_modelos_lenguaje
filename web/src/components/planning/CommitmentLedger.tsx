/**
 * Libro de compromisos (spec 026, design.md §3): una fila por contrato con una marca en el mínimo
 * contratado. Lo que falta va en trama diagonal, no solo en color. Sin solución, por prioridad.
 */
import { fmt, PRODUCT_LABEL } from "../../lib/planningFormat";
import type { CommitmentView, PlanResponse } from "../../lib/types";
import { PRODUCT_GLYPHS } from "../brand/ProductGlyphs";

interface Row {
  commitment: CommitmentView;
  produced: number;
  required: number;
  missing: number;
}

function rows(plan: PlanResponse, commitments: CommitmentView[]): Row[] {
  const required: Record<string, number> = {};
  for (const item of commitments) {
    required[item.product] = (required[item.product] ?? 0) + item.min_quantity;
  }
  const list = commitments.map((commitment) => {
    const shortfall = plan.shortfalls.find((item) => item.product === commitment.product);
    const total = required[commitment.product];
    const share = total ? commitment.min_quantity / total : 1;
    return {
      commitment,
      produced: plan.products[commitment.product] * share,
      required: commitment.min_quantity,
      missing: shortfall ? shortfall.missing * share : 0,
    };
  });
  return plan.status === "optimal"
    ? list
    : [...list].sort((a, b) => a.commitment.priority - b.commitment.priority);
}

interface LedgerProps {
  plan: PlanResponse;
  commitments: CommitmentView[];
}

export function CommitmentLedger({ plan, commitments }: LedgerProps) {
  return (
    <section aria-labelledby="ledger-title" className="ledger">
      <h2 className="panel-title" id="ledger-title">
        Libro de compromisos
      </h2>
      <svg aria-hidden="true" className="ledger__defs" height="0" width="0">
        <defs>
          <pattern
            height="6"
            id="shortfall-hatch"
            patternTransform="rotate(45)"
            patternUnits="userSpaceOnUse"
            width="6"
          >
            <rect fill="var(--shortfall)" height="6" opacity="0.18" width="6" />
            <line stroke="var(--shortfall)" strokeWidth="2.5" x1="0" x2="0" y1="0" y2="6" />
          </pattern>
        </defs>
      </svg>
      <ol className="ledger__rows">
        {rows(plan, commitments).map(({ commitment, produced, required, missing }) => {
          const Glyph = PRODUCT_GLYPHS[commitment.product];
          const scaleMax = Math.max(produced + missing, required) * 1.15 || 1;
          const met = missing <= 0;
          const margin = required > 0 ? (100 * (produced - required)) / required : 0;
          const at = (value: number) => (100 * Math.min(value, scaleMax)) / scaleMax;
          return (
            <li
              className={`ledger__row ledger__row--${commitment.product}`}
              data-met={met}
              key={commitment.id}
            >
              <Glyph className="ledger__glyph" />
              <div className="ledger__who">
                <span className="ledger__product">{PRODUCT_LABEL[commitment.product]}</span>
                <span className="ledger__party">
                  {commitment.counterparty}, prioridad {commitment.priority}
                </span>
              </div>
              <svg
                aria-hidden="true"
                className="ledger__bar"
                preserveAspectRatio="none"
                viewBox="0 0 100 12"
              >
                <rect className="ledger__track" height="12" width="100" />
                <rect className="ledger__fill" height="12" width={at(produced)} />
                {missing > 0 ? (
                  <rect
                    data-shortfall="true"
                    fill="url(#shortfall-hatch)"
                    height="12"
                    width={at(missing)}
                    x={at(produced)}
                  />
                ) : null}
                <line
                  className="ledger__minimum"
                  x1={at(required)}
                  x2={at(required)}
                  y1="-2"
                  y2="14"
                />
              </svg>
              <span className="ledger__verdict type-data">
                {met
                  ? `cumple ${margin >= 0.05 ? `+${fmt(margin, 1)} %` : "justo"}`
                  : `falta ${fmt(missing)} ${commitment.unit}`}
              </span>
            </li>
          );
        })}
      </ol>
    </section>
  );
}
