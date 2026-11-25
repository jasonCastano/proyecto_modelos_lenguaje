/**
 * Fuentes del último turno (spec 026, FR-008): cada cita pública abre su fuente; las citas [S#] de
 * la planta sintética van aparte y con su etiqueta.
 */
import type { ChatTurn } from "../../lib/types";

export function SourcesPanel({ turn }: { turn: ChatTurn | null }) {
  const citations = turn?.citations ?? [];
  const synthetic = citations.filter((item) => item.label.toUpperCase().startsWith("S"));
  const public_ = citations.filter((item) => !item.label.toUpperCase().startsWith("S"));
  return (
    <section aria-labelledby="sources-title" className="side-panel">
      <h2 className="panel-title" id="sources-title">
        Fuentes del turno
      </h2>
      {citations.length === 0 ? (
        <p className="side-panel__empty">
          Cuando el agente cite un documento, aquí verás el enlace para comprobarlo.
        </p>
      ) : null}
      {public_.length ? (
        <ul className="sources-list">
          {public_.map((item) => (
            <li key={`${item.label}-${item.unit_id}`}>
              <span className="sources-list__label type-data">[{item.label}]</span>{" "}
              {item.url ? (
                <a href={item.url} rel="noreferrer" target="_blank">
                  {item.title || item.url}
                </a>
              ) : (
                <span>{item.title || item.unit_id}</span>
              )}
            </li>
          ))}
        </ul>
      ) : null}
      {synthetic.length ? (
        <>
          <p className="synthetic-tag">Datos sintéticos de demostración</p>
          <ul className="sources-list">
            {synthetic.map((item) => (
              <li key={`${item.label}-${item.unit_id}`}>
                <span className="sources-list__label type-data">[{item.label}]</span>{" "}
                {item.title || item.unit_id}
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}
