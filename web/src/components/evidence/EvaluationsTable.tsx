/** Evaluaciones publicadas (spec 026, FR-023): la cifra honesta, también las que no cumplen. */
import type { PublishedEvaluation } from "../../lib/types";

const REPO = "https://github.com/jasonCastano/proyecto_modelos_lenguaje/blob/main/";

function verdict(meets: PublishedEvaluation["meets"]): { key: string; text: string } {
  if (meets === "partial") return { key: "partial", text: "parcial" };
  return meets ? { key: "yes", text: "cumple" } : { key: "no", text: "no cumple" };
}

export function EvaluationsTable({ evaluations }: { evaluations: PublishedEvaluation[] }) {
  return (
    <section aria-labelledby="evaluations-title" className="evaluations">
      <h2 className="panel-title" id="evaluations-title">
        Evaluaciones publicadas
      </h2>
      <div className="table-scroll">
        <table className="evaluations__table">
          <caption className="visually-hidden">Evaluaciones publicadas con su meta</caption>
          <thead>
            <tr>
              <th scope="col">Evaluación</th>
              <th scope="col">Resultado</th>
              <th scope="col">Meta</th>
              <th scope="col">Estado</th>
              <th scope="col">Fecha</th>
            </tr>
          </thead>
          <tbody>
            {evaluations.map((row) => {
              const state = verdict(row.meets);
              return (
                <tr key={row.id}>
                  <th scope="row">
                    <a href={`${REPO}${row.report}`} rel="noreferrer" target="_blank">
                      {row.name}
                    </a>
                    {row.note ? <span className="evaluations__note">{row.note}</span> : null}
                  </th>
                  <td className="type-data">{row.value}</td>
                  <td className="type-data">{row.target}</td>
                  <td>
                    <span className="verdict" data-verdict={state.key}>
                      {state.text}
                    </span>
                  </td>
                  <td className="type-data">{row.date}</td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}
