export type Mode = "real" | "demo";
export type TaskKind = "qa" | "summary" | "faq";
export type AnswerStatus = "ok" | "fallback" | "error";

export interface Citation {
  label: string;
  title: string;
  url: string;
  section_path: string[];
  page?: number | null;
  time_start?: number | null;
  authority: "first_party" | "third_party" | "unknown";
  snippet?: string | null;
}

export interface ApiError {
  code: string;
  message: string;
  retryable: boolean;
  action: string;
}

export interface CitedAnswer {
  query_id: string;
  status: AnswerStatus;
  answer: string;
  citations: Citation[];
  model: string;
  provider: string;
  prompt_version: string;
  latency_ms: number;
  input_tokens: number;
  output_tokens: number;
  cost_usd?: number | null;
  review_required: boolean;
  error?: ApiError | null;
}

export interface FaqItem {
  question: string;
  answer: string;
  citations: Citation[];
  status: "ready" | "review" | "missing_evidence";
  model: string;
  prompt_version: string;
}

export interface FaqResponse {
  items: FaqItem[];
}

export interface HealthStatus {
  ok: boolean;
  provider: string;
  model: string;
  configured: boolean;
  demo_available: boolean;
  latency_ms?: number | null;
  detail?: string | null;
}

export interface CorpusMetric {
  key: string;
  label: string;
  value: number;
  unit: string;
  source: string;
  status: "complete" | "incomplete" | "unknown";
}

export interface EvidenceLink {
  label: string;
  href: string;
  kind: "spec" | "adr" | "report" | "code" | "bitacora";
}

export interface ShowcaseSection {
  id:
    | "problem"
    | "data"
    | "medallion"
    | "prompts"
    | "tasks"
    | "app"
    | "metrics"
    | "limits";
  order: number;
  title: string;
  body: string;
  status: "done" | "partial" | "pending";
  metrics: CorpusMetric[];
  evidence: EvidenceLink[];
}

export interface ShowcaseResponse {
  generated_at: string;
  data_status: "complete" | "incomplete" | "unknown";
  sections: ShowcaseSection[];
  metrics: CorpusMetric[];
}

export class ApiClientError extends Error {
  readonly apiError: ApiError;

  constructor(apiError: ApiError) {
    super(apiError.message);
    this.name = "ApiClientError";
    this.apiError = apiError;
  }
}
