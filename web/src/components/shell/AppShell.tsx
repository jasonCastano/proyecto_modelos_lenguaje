/**
 * Marco común de la plataforma (spec 026, contracts/web-ui.md): rail, barra superior, contenido y
 * pie con la declaración académica (y la etiqueta sintética en las áreas con datos de planta).
 */
import type { ReactNode } from "react";

import { audienceLabel, usePlatform } from "../../lib/platform";
import type { Route } from "../../lib/router";
import { AREAS, CaneRail } from "./CaneRail";

export const ACADEMIC_NOTE =
  "Proyecto académico de la Maestría en IA y Ciencia de Datos (UAO). No es un canal oficial de Manuelita.";
export const SYNTHETIC_LABEL = "Datos sintéticos de demostración";

export function TopBar({ route, demo }: { route: Route; demo: boolean }) {
  const { audience } = usePlatform();
  const area = AREAS.find((item) => item.route === route)?.label ?? "Entrada";
  return (
    <header className="top-bar">
      <p className="top-bar__area">{area}</p>
      <div className="top-bar__status">
        <span className="profile-chip" data-testid="active-profile">
          Perfil: {audienceLabel(audience)}
        </span>
        {demo ? (
          <span className="demo-flag" title="Respuestas guionadas, sin llamar al modelo ni gastar la clave">
            Modo demostración: respuestas guionadas
          </span>
        ) : null}
      </div>
    </header>
  );
}

export function AcademicFooter({ synthetic }: { synthetic: boolean }) {
  return (
    <footer className="academic-footer">
      <p>{ACADEMIC_NOTE}</p>
      {synthetic ? <p className="academic-footer__synthetic">{SYNTHETIC_LABEL}</p> : null}
    </footer>
  );
}

interface AppShellProps {
  route: Route;
  demo: boolean;
  notice?: string | null;
  children: ReactNode;
}

export function AppShell({ route, demo, notice, children }: AppShellProps) {
  const synthetic = route === "/planificacion";
  return (
    <div className="app-shell">
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <CaneRail current={route} />
      <div className="app-shell__body">
        <TopBar demo={demo} route={route} />
        {notice ? (
          <p className="route-notice" role="status">
            {notice}
          </p>
        ) : null}
        <main className="app-main" id="contenido" tabIndex={-1}>
          {children}
        </main>
        <AcademicFooter synthetic={synthetic} />
      </div>
    </div>
  );
}
