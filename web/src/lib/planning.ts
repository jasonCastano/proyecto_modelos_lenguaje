/** Cliente de `/api/v1/planning` (spec 026, contracts/planning-api.md). */
import { request } from "./api";
import { visitUser } from "./session";
import type {
  PendingProposal,
  PlanComparison,
  PlanningAccess,
  PlanResponse,
  PlantSnapshot,
  ProposalOutcome,
  Scenario,
} from "./types";

const BASE = "/v1/planning";

function headers(): Record<string, string> {
  return { "Content-Type": "application/json", "X-User-Id": visitUser() };
}

export function getAccess(): Promise<PlanningAccess> {
  return request<PlanningAccess>(`${BASE}/access`, { headers: headers() });
}

export function getState(): Promise<PlantSnapshot> {
  return request<PlantSnapshot>(`${BASE}/state`, { headers: headers() });
}

export function postPlan(scenario: Scenario): Promise<PlanResponse> {
  return request<PlanResponse>(`${BASE}/plan`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(scenario),
  });
}

export function postCompare(scenario: Scenario): Promise<PlanComparison> {
  return request<PlanComparison>(`${BASE}/compare`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(scenario),
  });
}

export function createProposal(scenario: Scenario, note?: string): Promise<PendingProposal> {
  return request<PendingProposal>(`${BASE}/proposals`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify(note ? { scenario, note } : { scenario }),
  });
}

export function decideProposal(
  confirmationId: string,
  decision: "yes" | "no",
): Promise<ProposalOutcome> {
  return request<ProposalOutcome>(`${BASE}/proposals/${encodeURIComponent(confirmationId)}`, {
    method: "POST",
    headers: headers(),
    body: JSON.stringify({ decision }),
  });
}
