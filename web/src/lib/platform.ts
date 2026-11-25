/**
 * Estado compartido entre áreas de la plataforma (spec 026, data-model §8): el perfil activo y el
 * mensaje que otra área deja para el agente («Explicar con el agente», consultas de ejemplo).
 * El perfil vive en `sessionStorage`; el mensaje pendiente solo en memoria y se consume una vez.
 */
import { useSyncExternalStore } from "react";

export const AUDIENCE_KEY = "manuelita.platform.audience";

export interface Outbox {
  id: number;
  text: string;
  /** `send`: se envía solo; `draft`: queda en el campo para revisarlo. */
  kind: "send" | "draft";
}

interface PlatformState {
  audience: string;
  outbox: Outbox | null;
}

function readAudience(): string {
  try {
    return window.sessionStorage.getItem(AUDIENCE_KEY) || "visitante";
  } catch {
    return "visitante";
  }
}

let state: PlatformState = { audience: readAudience(), outbox: null };
let counter = 0;
const listeners = new Set<() => void>();

function emit(next: PlatformState) {
  state = next;
  listeners.forEach((listener) => listener());
}

export function setAudience(audience: string): void {
  try {
    window.sessionStorage.setItem(AUDIENCE_KEY, audience);
  } catch {
    // sin almacenamiento: el perfil dura lo que dure la pestaña
  }
  emit({ ...state, audience });
}

export function queueMessage(text: string, kind: Outbox["kind"] = "send"): void {
  counter += 1;
  emit({ ...state, outbox: { id: counter, text, kind } });
}

/** Devuelve el mensaje pendiente y lo borra (se consume una sola vez). */
export function takeOutbox(id: number): void {
  if (state.outbox?.id === id) emit({ ...state, outbox: null });
}

export function resetPlatform(): void {
  emit({ audience: readAudience(), outbox: null });
}

export function usePlatform(): PlatformState {
  return useSyncExternalStore(
    (listener) => {
      listeners.add(listener);
      return () => listeners.delete(listener);
    },
    () => state,
    () => state,
  );
}

export const AUDIENCES: { key: string; label: string }[] = [
  { key: "visitante", label: "Visitante" },
  { key: "cliente", label: "Cliente B2B" },
  { key: "proveedor", label: "Proveedor" },
  { key: "colaborador", label: "Colaborador" },
  { key: "planificador", label: "Planificador industrial" },
];

export function audienceLabel(key: string): string {
  return AUDIENCES.find((item) => item.key === key)?.label ?? key;
}
