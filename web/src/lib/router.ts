/**
 * Enrutador mínimo de la plataforma (spec 026, research R2; spec 032): cinco rutas fijas sobre la History
 * API. El backend ya sirve `index.html` en cualquier ruta, así que los enlaces directos funcionan.
 */
import { createElement, useSyncExternalStore, type AnchorHTMLAttributes, type MouseEvent } from "react";

export type Route = "/" | "/agente" | "/planificacion" | "/evidencia" | "/whatsapp";

export const ROUTES: readonly Route[] = ["/", "/agente", "/planificacion", "/evidencia", "/whatsapp"];

export interface Location {
  route: Route;
  notFound: boolean;
}

export function parseRoute(pathname: string): Location {
  const clean = pathname.length > 1 ? pathname.replace(/\/+$/, "") : pathname;
  const route = ROUTES.find((item) => item === clean);
  return route ? { route, notFound: false } : { route: "/", notFound: true };
}

const listeners = new Set<() => void>();
let cached: Location | null = null;
let cachedPath = "";

function snapshot(): Location {
  const path = window.location.pathname;
  if (!cached || path !== cachedPath) {
    cached = parseRoute(path);
    cachedPath = path;
  }
  return cached;
}

function notify() {
  listeners.forEach((listener) => listener());
}

function subscribe(listener: () => void): () => void {
  listeners.add(listener);
  window.addEventListener("popstate", listener);
  return () => {
    listeners.delete(listener);
    window.removeEventListener("popstate", listener);
  };
}

export function navigate(route: Route): void {
  if (window.location.pathname !== route) window.history.pushState(null, "", route);
  notify();
  try {
    window.scrollTo({ top: 0 });
  } catch {
    // jsdom y navegadores sin scrollTo
  }
}

export function useRoute(): Location {
  return useSyncExternalStore(subscribe, snapshot, snapshot);
}

type LinkProps = AnchorHTMLAttributes<HTMLAnchorElement> & { to: Route };

/** Enlace interno: intercepta el clic izquierdo sin modificadores; lo demás lo hace el navegador. */
export function Link({ to, onClick, ...rest }: LinkProps) {
  function handle(event: MouseEvent<HTMLAnchorElement>) {
    onClick?.(event);
    if (
      event.defaultPrevented ||
      event.button !== 0 ||
      event.metaKey ||
      event.ctrlKey ||
      event.shiftKey ||
      event.altKey
    ) {
      return;
    }
    event.preventDefault();
    navigate(to);
  }
  return createElement("a", { ...rest, href: to, onClick: handle });
}
