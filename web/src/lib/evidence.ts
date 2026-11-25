/** Cliente de `/api/v1/evidence` (spec 026, contracts/evidence-api.md). */
import { request } from "./api";
import type {
  PublishedEvaluation,
  ServicesEvidence,
  ToolCatalogEvidence,
  TurnTrace,
} from "./types";

const BASE = "/v1/evidence";

export function getTools(): Promise<ToolCatalogEvidence> {
  return request<ToolCatalogEvidence>(`${BASE}/tools`);
}

export function getTrace(threadId: string, turn?: number): Promise<TurnTrace> {
  const query = turn ? `?turn=${turn}` : "";
  return request<TurnTrace>(`${BASE}/traces/${encodeURIComponent(threadId)}${query}`);
}

export function getServices(): Promise<ServicesEvidence> {
  return request<ServicesEvidence>(`${BASE}/services`);
}

export function getEvaluations(): Promise<PublishedEvaluation[]> {
  return request<PublishedEvaluation[]>(`${BASE}/evaluations`);
}
