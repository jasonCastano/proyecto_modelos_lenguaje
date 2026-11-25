/** Diferencias contra el plan base (spec 026, FR-014): signos y palabras explícitos. */
import { fmt, millions, PRODUCT_LABEL, signed } from "../../lib/planningFormat";
import type { PlanComparison } from "../../lib/types";

function commitmentChange(metBase: boolean, metScenario: boolean): string {
  if (metBase === metScenario) return "sin cambio";
  return metScenario ? "pasa a cumplir" : "deja de cumplir";
}

export function ComparisonView({ comparison }: { comparison: PlanComparison }) {
  const { base, scenario } = comparison;
  return (
    <section aria-labelledby="compare-title" className="comparison">
      <h2 className="panel-title" id="compare-title">
        Frente al plan base
      </h2>
      <div className="table-scroll">
        <table className="comparison__table">
          <caption className="visually-hidden">Diferencias entre el escenario y el plan base</caption>
          <thead>
            <tr>
              <th scope="col">Concepto</th>
              <th scope="col">Plan base</th>
              <th scope="col">Escenario</th>
              <th scope="col">Diferencia</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <th scope="row">Caña a azúcar</th>
              <td className="type-data">{fmt(base.mix.x_s)} t</td>
              <td className="type-data">{fmt(scenario.mix.x_s)} t</td>
              <td className="type-data">{signed(comparison.mix_delta.sugar.points, 1)} puntos a azúcar</td>
            </tr>
            <tr>
              <th scope="row">Caña a etanol</th>
              <td className="type-data">{fmt(base.mix.x_e)} t</td>
              <td className="type-data">{fmt(scenario.mix.x_e)} t</td>
              <td className="type-data">
                {signed(comparison.mix_delta.ethanol.points, 1)} puntos a etanol
              </td>
            </tr>
            {comparison.products_delta.map((row) => (
              <tr key={row.product}>
                <th scope="row">{PRODUCT_LABEL[row.product]}</th>
                <td className="type-data">
                  {fmt(row.base)} {row.unit}
                </td>
                <td className="type-data">
                  {fmt(row.scenario)} {row.unit}
                </td>
                <td className="type-data">
                  {signed(row.delta)} {row.unit}
                </td>
              </tr>
            ))}
            {comparison.commitments.map((row) => (
              <tr key={row.id}>
                <th scope="row">Compromiso de {PRODUCT_LABEL[row.product].toLowerCase()}</th>
                <td>{row.met_base ? "cumple" : `falta ${fmt(row.gap_base)} ${row.unit}`}</td>
                <td>{row.met_scenario ? "cumple" : `falta ${fmt(row.gap_scenario)} ${row.unit}`}</td>
                <td>{commitmentChange(row.met_base, row.met_scenario)}</td>
              </tr>
            ))}
            <tr>
              <th scope="row">Margen</th>
              <td className="type-data">{millions(base.margin)}</td>
              <td className="type-data">{millions(scenario.margin)}</td>
              <td className="type-data">{signed(comparison.margin_delta / 1_000_000)} millones</td>
            </tr>
          </tbody>
        </table>
      </div>
    </section>
  );
}
