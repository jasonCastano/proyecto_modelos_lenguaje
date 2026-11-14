export type Mode = "real" | "demo";
export type TaskKind = "qa" | "summary" | "faq" | "chat";
export type AnswerStatus = "ok" | "fallback" | "error";
export type RetrievalMode = "semantic" | "lexical" | "hybrid" | "none";
export type FragmentOrigin = "semantic" | "lexical" | "both";
export type FragmentStatus =
  | "used"
  | "omitted_threshold"
  | "omitted_budget"
  | "omitted_duplicate";

export interface RetrievalFragment {
  unit_id: string;
  title: string;
  url: string;
  score: number;
  semantic_score: number | null;
  lexical_score: number | null;
  origin: FragmentOrigin;
  status: FragmentStatus;
  reason: string | null;
  anomalous?: boolean;
  anomaly_reasons?: string[];
  neutralized_sentences?: number;
}

export interface RetrievalTrace {
  mode: RetrievalMode;
  semantic_available: boolean;
  candidates: number;
  threshold: number;
  fragments: RetrievalFragment[];
  used_unit_ids: string[];
  notes: string[];
  elapsed_ms: number;
}

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
  retrieval?: RetrievalTrace | null;
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
  adversarial_corpus?: boolean;
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
    | "retrieval"
    | "agent"
    | "safety"
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

// ---------------------------------------------------------------- conversación (spec 014, US1)

export type ChatVariant = "chain" | "agent";
export type ChatRouteName =
  | "direct"
  | "documental"
  | "structured"
  | "mixed"
  | "out_of_scope"
  | "clarify";
export type ChatStatus = "answered" | "fallback" | "clarify" | "pending_approval";

export interface ChatRoute {
  route: ChatRouteName;
  confidence: number;
  reason: string;
  decided_by: "rules" | "llm" | "demo";
  alternative?: ChatRouteName | null;
  fallback_route?: "documental" | null;
}

export interface ChatFragment extends RetrievalFragment {
  label: string;
}

export interface StructuredRow {
  label: string;
  fact_id: string;
  subject_label: string;
  attribute: string;
  value: string;
  year?: number | null;
  unit_id: string;
  citations: Array<{ url: string; title: string }>;
}

export interface ChatCitation {
  label: string;
  unit_id: string;
  url: string;
  title: string;
  fact_id?: string | null;
}

export interface TurnMetrics {
  latency_ms: number;
  model_calls: number;
  tool_calls: number;
  input_tokens: number;
  output_tokens: number;
}

export interface ChatTurn {
  turn_id: number;
  question: string;
  route: ChatRoute;
  fragments: ChatFragment[];
  structured_rows: StructuredRow[];
  answer: string;
  citations: ChatCitation[];
  sources: string[];
  fallback: boolean;
  metrics: TurnMetrics;
}

export interface PendingAction {
  action_id: string;
  tool: "forget_memory" | "save_preference" | "save_profile" | "export_conversation";
  args: Record<string, unknown>;
  proposed_at: string;
  decision?: "approve" | "edit" | "reject" | null;
}

export interface ChatAnomaly {
  label?: string | null;
  unit_id?: string | null;
  reasons: string[];
}

export interface ChatResponse {
  thread_id: string;
  turn: ChatTurn;
  status: ChatStatus;
  pending_action: PendingAction | null;
  anomalies: ChatAnomaly[];
}

export interface ThreadView {
  thread_id: string;
  variant: ChatVariant;
  turns: ChatTurn[];
  summary: string;
  status: "idle" | "pending_approval";
  pending_action: PendingAction | null;
  actions?: Array<PendingAction & { decided_at?: string }>;
}

export interface MemoryItem {
  key: string;
  value: string;
  created_at: string;
  expires_at: string;
}

export interface ProfileItem {
  key: "name" | "workplace" | "role" | "city";
  value: string;
  created_at: string;
}

export interface MemoryView {
  user_id: string;
  items: MemoryItem[];
  profile?: ProfileItem[];
}

/** Eventos de `POST /api/chat/stream` (Server-Sent Events). */
export type ChatStreamEvent =
  | { event: "start"; thread_id: string }
  | { event: "route"; route: ChatRoute }
  | { event: "retrieval"; fragments: number; structured_rows: number; tool_calls: number }
  | { event: "tool"; tools: string[] }
  | { event: "token"; text: string }
  | { event: "done"; response: ChatResponse }
  | { event: "error"; error: { code: string; message: string } };
