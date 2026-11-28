/**
 * Marco común de la plataforma (spec 031): navegación centrada fija (nav-centre), barra de estado en las
 * áreas de trabajo y un pie que reúne el cierre y los enlaces (footer-statement), con la declaración
 * académica en todas las áreas, la etiqueta sintética en planificación y la línea de créditos de fotos.
 */
import { useEffect, useState, type ReactNode } from "react";

import { PHOTO_CREDITS_LINE, PHOTO_CREDITS_URL } from "../../data/photos";
import { audienceLabel, usePlatform } from "../../lib/platform";
import { Link, type Route } from "../../lib/router";
import type { AppVersion } from "../../lib/types";

export const ACADEMIC_NOTE =
  "Proyecto académico de la Maestría en IA y Ciencia de Datos (UAO). No es un canal oficial de Manuelita.";
export const SYNTHETIC_LABEL = "Datos sintéticos de demostración";
export const PRIMARY_ACTION = "Habla con Valer-IA";

export const AREAS: { route: Route; label: string }[] = [
  { route: "/", label: "Entrada" },
  { route: "/agente", label: "Agente" },
  { route: "/planificacion", label: "Planificación" },
  { route: "/evidencia", label: "Evidencia" },
  { route: "/whatsapp", label: "WhatsApp" },
];

function SiteNav({ route, demo }: { route: Route; demo: boolean }) {
  const [open, setOpen] = useState(false);

  useEffect(() => setOpen(false), [route]);

  return (
    <header className="site-nav" data-open={open || undefined}>
      <div className="wrap site-nav__bar">
        <Link aria-label="Valer-IA, entrada" className="site-nav__brand" to="/">
          Valer-IA
        </Link>
        <nav aria-label="Áreas de la plataforma" id="areas">
          <ul className="site-nav__links">
            {AREAS.map((area) => (
              <li key={area.route}>
                <Link aria-current={area.route === route ? "page" : undefined} to={area.route}>
                  {area.label}
                </Link>
              </li>
            ))}
          </ul>
        </nav>
        <div className="site-nav__end">
          {demo ? (
            <span
              className="site-nav__demo"
              title="Respuestas guionadas, sin llamar al modelo ni gastar la clave"
            >
              Modo demostración: respuestas guionadas
            </span>
          ) : null}
          {route !== "/agente" ? (
            <Link className="btn" to="/agente">
              {PRIMARY_ACTION}
            </Link>
          ) : null}
          <button
            aria-controls="areas"
            aria-expanded={open}
            className="btn btn--line site-nav__menu"
            onClick={() => setOpen((value) => !value)}
            type="button"
          >
            {open ? "Cerrar el menú" : "Menú"}
          </button>
        </div>
      </div>
    </header>
  );
}

export function TopBar() {
  const { audience } = usePlatform();
  return (
    <div className="top-bar">
      <span className="profile-chip" data-testid="active-profile">
        Perfil: {audienceLabel(audience)}
      </span>
    </div>
  );
}

function versionText(version: AppVersion): string {
  const web = version.web === "ok" ? "" : " · la web compilada está desactualizada: ejecuta make app";
  return `Versión ${version.commit}${web}`;
}

interface FooterProps {
  route: Route;
  version?: AppVersion | null;
}

export function SiteFooter({ route, version }: FooterProps) {
  const home = route === "/";
  return (
    <footer className="closing">
      <div className="wrap">
        {home ? (
          <section aria-labelledby="cierre-title" className="closing__close" id="cierre">
            <h2 className="closing__statement" id="cierre-title">
              Pregunta lo que necesitas saber de Manuelita
            </h2>
            <div>
              <Link className="btn" to="/agente">
                {PRIMARY_ACTION}
              </Link>
            </div>
          </section>
        ) : null}
        <div className="closing__links">
          <div>
            <p className="closing__brand">Valer-IA</p>
            <p className="closing__note">{ACADEMIC_NOTE}</p>
            {route === "/planificacion" ? (
              <p className="closing__note closing__synthetic">{SYNTHETIC_LABEL}</p>
            ) : null}
          </div>
          <nav aria-label="Pie de página">
            <p className="closing__heading">Áreas</p>
            <ul>
              {AREAS.map((area) => (
                <li key={area.route}>
                  <Link className="text-link" to={area.route}>
                    {area.label}
                  </Link>
                </li>
              ))}
            </ul>
          </nav>
          <div>
            <p className="closing__heading">Canales</p>
            <ul>
              <li>
                <Link className="text-link" to="/agente">
                  Web: conversación con el agente
                </Link>
              </li>
              <li>
                <span>WhatsApp: el número del proyecto</span>
              </li>
            </ul>
          </div>
        </div>
        <div className="closing__legal">
          <p>
            Valer-IA {new Date().getFullYear()} ·{" "}
            <a className="text-link" href={PHOTO_CREDITS_URL}>
              {PHOTO_CREDITS_LINE}
            </a>
          </p>
          {version ? <p data-testid="app-version">{versionText(version)}</p> : null}
        </div>
      </div>
    </footer>
  );
}

interface AppShellProps {
  route: Route;
  demo: boolean;
  notice?: string | null;
  version?: AppVersion | null;
  children: ReactNode;
}

export function AppShell({ route, demo, notice, version, children }: AppShellProps) {
  const home = route === "/";
  // La entrada y la pestaña WhatsApp (spec 032) no usan la barra del perfil activo.
  const bare = home || route === "/whatsapp";
  return (
    <div className="site-shell" data-route={route}>
      <a className="skip-link" href="#contenido">
        Saltar al contenido
      </a>
      <SiteNav demo={demo} route={route} />
      {bare ? null : <TopBar />}
      {notice ? (
        <p className="route-notice" role="status">
          {notice}
        </p>
      ) : null}
      <main className="app-main" id="contenido" tabIndex={-1}>
        {children}
      </main>
      <SiteFooter route={route} version={version} />
    </div>
  );
}
