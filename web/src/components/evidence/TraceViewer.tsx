/**
 * Traza del turno (spec 026, FR-021): ruta, perfil y pasos numerados (sí son una secuencia), cada
 * herramienta con su duración y resultado; los argumentos se despliegan a pedido.
 */
import { audienceLabel } from "../../lib/platform";
import type { TurnTrace } from "../../lib/types";

const DECIDED_BY: Record<string, string> = {
  rules: "reglas",
  llm: "modelo",
  demo: "guion de demostración",
  jev: "gatekeeper Jev",
};

interface TraceViewerProps {
  trace: TurnTrace | null;
  message: string | null;
  onTurn: (turn: number) => void;
}

export function TraceViewer({ trace, message, onTurn }: TraceViewerProps) {
  return (
    <section aria-labelledby="trace-title" className="trace">
      <h2 className="panel-title" id="trace-title">
        Traza del turno
      </h2>
      {!trace ? (
        <p className="side-panel__empty">{message}</p>
      ) : (
        <>
          <div className="trace__head">
            <label>
              Turno
              <select onChange={(event) => onTurn(Number(event.target.value))} value={trace.turn}>
                {Array.from({ length: trace.turns }, (_item, index) => index + 1).map((turn) => (
                  <option key={turn} value={turn}>
                    {turn}
                  </option>
                ))}
              </select>
            </label>
            <p>
              Ruta <strong>{trace.route}</strong>, decidida por {DECIDED_BY[trace.decided_by] ?? trace.decided_by};
              perfil {audienceLabel(trace.profile).toLowerCase()};{" "}
              <span className="type-data">{trace.duration_ms} ms</span>.
            </p>
          </div>
          <p className="trace__question">«{trace.question}»</p>
          {trace.plan_steps.length ? (
            <p className="trace__plan">Plan: {trace.plan_steps.join(", ")}.</p>
          ) : null}
          {trace.tools.length ? (
            <ol className="trace__steps">
              {trace.tools.map((tool) => (
                <li data-ok={tool.ok} key={`${tool.step}-${tool.name}`}>
                  <span className="trace__tool type-data">{tool.name}</span>
                  <span className="trace__time type-data">{tool.duration_ms} ms</span>
                  <span className="trace__result">{tool.ok ? "correcta" : `falló: ${tool.error ?? ""}`}</span>
                  <details>
                    <summary>Argumentos y resumen</summary>
                    <pre className="trace__args">{JSON.stringify(tool.args, null, 2)}</pre>
                    <p>{tool.summary}</p>
                  </details>
                </li>
              ))}
            </ol>
          ) : (
            <p className="side-panel__empty">Este turno no llamó herramientas.</p>
          )}
        </>
      )}
    </section>
  );
}
