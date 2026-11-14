/**
 * Visita del navegador (spec 018, contracts/ui-views.md). El cliente y la conversación viven en
 * `sessionStorage`: cerrar el navegador inicia una visita nueva con un cliente anónimo limpio y
 * recargar la página no la termina.
 */

export const VISIT_USER_KEY = "manuelita.visit.user";
export const WELCOMED_KEY = "manuelita.visit.welcomed";
export const VIEW_KEY = "manuelita.view";
/** Clave antigua (spec 014): el cliente en `localStorage` hacía que todas las visitas fueran la misma. */
export const LEGACY_USER_KEY = "manuelita.chat.user";

export type ViewMode = "normal" | "tecnica";

function readSession(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeSession(key: string, value: string | null): void {
  try {
    if (value === null) window.sessionStorage.removeItem(key);
    else window.sessionStorage.setItem(key, value);
  } catch {
    // sin almacenamiento: la visita dura lo que dure la pestaña
  }
}

function newAnonymousId(): string {
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  return `anon-${random}`;
}

/** Cliente de la visita (lo crea si no existe) y elimina la clave antigua de `localStorage`. */
export function visitUser(): string {
  try {
    window.localStorage.removeItem(LEGACY_USER_KEY);
  } catch {
    // ignorado
  }
  const saved = readSession(VISIT_USER_KEY);
  if (saved) return saved;
  const user = newAnonymousId();
  writeSession(VISIT_USER_KEY, user);
  return user;
}

/** Adopta el cliente reconocido por el servidor (correo + nombre). */
export function adoptUser(userId: string): void {
  writeSession(VISIT_USER_KEY, userId);
}

/** «Empecemos de nuevo»: cliente anónimo nuevo en la misma visita. */
export function resetVisit(): string {
  const user = newAnonymousId();
  writeSession(VISIT_USER_KEY, user);
  return user;
}

export function welcomed(): boolean {
  return readSession(WELCOMED_KEY) === "1";
}

export function markWelcomed(): void {
  writeSession(WELCOMED_KEY, "1");
}

/** Vista del chat: `?vista=tecnica` la activa para la sustentación; `?vista=normal` la quita. */
export function viewMode(): ViewMode {
  if (typeof window !== "undefined") {
    const requested = new URLSearchParams(window.location.search).get("vista");
    if (requested === "tecnica" || requested === "normal") {
      writeSession(VIEW_KEY, requested);
      return requested;
    }
  }
  return readSession(VIEW_KEY) === "tecnica" ? "tecnica" : "normal";
}
