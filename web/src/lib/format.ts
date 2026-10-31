import type { Citation } from "./types";

const numberFormat = new Intl.NumberFormat("es-CO");

export function formatNumber(value: number): string {
  return numberFormat.format(value);
}

export function formatMetricValue(value: number): string {
  return numberFormat.format(value);
}

export function citationLocation(citation: Citation): string {
  const section = citation.section_path.length
    ? `sección: ${citation.section_path.join(" > ")}`
    : "sin sección";
  const page = citation.page ? `, p. ${citation.page}` : "";
  const time = citation.time_start !== null && citation.time_start !== undefined
    ? `, ${Math.round(citation.time_start)} s`
    : "";
  return `${section}${page}${time}`;
}

export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    ok: "Con evidencia",
    fallback: "Sin evidencia",
    error: "Error controlado",
    ready: "Lista",
    review: "Revisar",
    missing_evidence: "Sin evidencia",
    done: "Completado",
    partial: "En curso",
    pending: "Pendiente",
    complete: "Completo",
    incomplete: "Incompleto",
    unknown: "Desconocido",
  };
  return labels[status] ?? status;
}
