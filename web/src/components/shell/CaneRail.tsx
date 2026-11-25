/**
 * Rail de navegación (spec 026, design.md §3): un tallo de caña vertical cuyos nudos son las
 * cuatro áreas. En pantallas estrechas pasa a una barra inferior de cuatro destinos.
 */
import { Link, type Route } from "../../lib/router";

export const AREAS: { route: Route; label: string; short: string }[] = [
  { route: "/", label: "Entrada", short: "Entrada" },
  { route: "/agente", label: "Agente", short: "Agente" },
  { route: "/planificacion", label: "Planificación", short: "Planificar" },
  { route: "/evidencia", label: "Evidencia técnica", short: "Evidencia" },
];

export function CaneRail({ current }: { current: Route }) {
  return (
    <nav aria-label="Áreas de la plataforma" className="cane-rail">
      <Link className="cane-rail__brand" to="/" aria-label="Valer-IA, entrada">
        Valer-IA
      </Link>
      <svg aria-hidden="true" className="cane-rail__stalk" focusable="false" viewBox="0 0 12 400">
        <path d="M6 0V400" />
      </svg>
      <ol className="cane-rail__nodes">
        {AREAS.map((area) => {
          const active = area.route === current;
          return (
            <li key={area.route}>
              <Link
                aria-current={active ? "page" : undefined}
                className="cane-rail__node"
                data-active={active || undefined}
                to={area.route}
              >
                <svg aria-hidden="true" className="cane-rail__knot" viewBox="0 0 24 12">
                  <rect height="8" rx="4" width="22" x="1" y="2" />
                </svg>
                <span className="cane-rail__label">{area.label}</span>
                <span className="cane-rail__short">{area.short}</span>
              </Link>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}
