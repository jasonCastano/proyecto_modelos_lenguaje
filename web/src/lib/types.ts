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

/** Versión que sirve el backend (`GET /api/version`): commit y compilación web. */
export interface AppVersion {
  commit: string;
  web: "ok" | "stale" | "missing";
  web_build: string | null;
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
  voice_available?: boolean;
  /** Spec 023: el dictado está listo o cargando. */
  stt_available?: boolean;
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
  | "clarify"
  | "planning";
export type ChatStatus = "answered" | "fallback" | "clarify" | "pending_approval";

export interface ChatRoute {
  route: ChatRouteName;
  confidence: number;
  reason: string;
  decided_by: "rules" | "llm" | "demo" | "jev";
  alternative?: ChatRouteName | null;
  fallback_route?: "documental" | null;
  scope_reason?:
    | "off_topic"
    | "abuse"
    | "harmful"
    | "third_party"
    | "prompt_extraction"
    | "advice"
    | "identity"
    | "crisis"
    | "unattainable"
    | null;
  /** Spec 019: tema ajeno saneado, emoción propuesta por el enrutador y tipo de pedido no atendible. */
  topic?: string | null;
  sentiment?: Sentiment | null;
  kind?: "pricing" | "commitment" | "human" | null;
  /** Spec 020: acto de diálogo del turno. */
  act?: DialogueAct | null;
  /** Spec 036: nivel del estilo caleño del turno. */
  style?: "off" | "formal" | "neutral" | "informal" | null;
}

/** Spec 020: acto de diálogo (etiqueta controlada). */
export type DialogueAct =
  | "greeting"
  | "smalltalk"
  | "off_topic"
  | "manuelita"
  | "complaint"
  | "correction"
  | "minimal"
  | "about_assistant"
  | "closing"
  | "thanks"
  | "clarify";

/** Spec 020: etiquetas de un turno del registro del contacto. */
export interface ContactTurn {
  act: DialogueAct;
  bridged: boolean;
  reviewed: "show" | "retry" | "fallback";
  /** Spec 021: frases descartadas en la revisión (solo el conteo). */
  discarded?: number;
}

/** Spec 019: emoción del visitante en un turno. */
export type Sentiment = "neutral" | "satisfied" | "confused" | "frustrated" | "angry" | "distressed";

export type ContactCategory =
  | "manuelita"
  | "off_topic"
  | "advice"
  | "complaint"
  | "unattainable"
  | "crisis"
  | "conduct"
  | "other";

export type ContactStatus =
  | "resolved"
  | "out_of_scope"
  | "not_attainable"
  | "needs_clarification"
  | "referred"
  | "no_evidence";

export interface ContactRequest {
  turn: number;
  category: ContactCategory;
  topic: string;
  status: ContactStatus;
}

/** Spec 019: registro del contacto (CRM) sin datos personales; solo en la vista técnica. */
export interface ContactRecord {
  version: "1.0";
  opened_at: string;
  updated_at: string;
  turns: number;
  requests: ContactRequest[];
  sentiments: Sentiment[];
  motive: string[];
  resolved: boolean;
  hostile_turns: number;
  crisis: boolean;
  /** Spec 020: secuencia de actos del hilo (como máximo 50). */
  acts?: ContactTurn[];
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
  gate_calls?: number;
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
  /** Spec 022: traza del gatekeeper Jev del turno (null si está desactivado). */
  jev?: JevTrace | null;
  /** Spec 023: el mensaje llegó por dictado (solo vista técnica). */
  input?: InputMeta | null;
  /** Spec 024: plan del turno (pasos previstos y ejecutados). */
  plan_steps?: string[];
  /** Spec 024: herramientas invocadas en el turno. */
  tools?: ToolInvocation[];
  /** Spec 025: perfil que atendió el turno (visitante, cliente, proveedor, …). */
  profile?: string;
}

/** Spec 025: perfil de la plataforma de agentes (`GET /api/profiles`). */
export interface ProfileOption {
  key: string;
  label: string;
  requires_authorization: boolean;
  authorized: boolean;
}

/** Spec 024: una herramienta del catálogo invocada en el turno (vista técnica). */
export interface ToolInvocation {
  step: number;
  name: string;
  args: Record<string, unknown>;
  ok: boolean;
  error?: string | null;
  duration_ms: number;
  summary: string;
}

export interface JevTrace {
  status: "ok" | "failed" | "skipped";
  reason?: string | null;
  route?: ChatRouteName | null;
  confidence?: number | null;
  alternative?: ChatRouteName | null;
  accepted?: boolean;
  latency_ms?: number;
  cost?: number | null;
  model?: string | null;
}

export interface PendingAction {
  action_id: string;
  tool: "forget_memory" | "save_preference" | "save_profile" | "export_conversation" | "remember_client";
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
  /** Spec 018: cliente activo tras el turno (reconocimiento o reinicio). */
  client?: ClientInfo | null;
  notices?: string[];
  /** Spec 019: registro del contacto tras el turno. */
  contact?: ContactRecord | null;
}

export interface ClientInfo {
  user_id: string;
  recognized: boolean;
  name: string | null;
  reset: boolean;
  masked_email: string | null;
}

export interface WelcomeCitation {
  label: string;
  unit_id: string;
  url: string;
  title: string;
}

export interface WelcomeResponse {
  assistant: string;
  version: string;
  text: string;
  citations: WelcomeCitation[];
}

export interface ThreadView {
  thread_id: string;
  variant: ChatVariant;
  turns: ChatTurn[];
  summary: string;
  status: "idle" | "pending_approval";
  pending_action: PendingAction | null;
  actions?: Array<PendingAction & { decided_at?: string }>;
  contact?: ContactRecord | null;
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
  /** Spec 021: frase revisada, en orden; el texto trae su separador inicial. */
  | { event: "sentence"; text: string; index: number }
  | { event: "done"; response: ChatResponse }
  | { event: "error"; error: { code: string; message: string } };

// ---------------------------------------------------------------- voz del agente (spec 016)

export interface VoiceStatus {
  available: boolean;
  state: "disabled" | "loading" | "ready" | "unavailable";
  engine: string;
  model: string;
  voice: string;
  language: string;
  sample_rate: number | null;
  license: string;
  detail: string | null;
}

// ---------------------------------------------------------------- dictado (spec 023)

export type SttState = "disabled" | "loading" | "ready" | "unavailable";

/** `GET /api/stt` (contracts/stt-api.md §1). */
export interface SttStatus {
  available: boolean;
  state: SttState;
  engine: string;
  model: string;
  language: string;
  detail: string | null;
  max_seconds: number;
  silence_ms: number;
  min_speech_ms: number;
  handsfree_idle_seconds: number;
  privacy: string;
}

/** `POST /api/stt` (contracts/stt-api.md §2). */
export interface SttResult {
  text: string;
  empty: boolean;
  truncated: boolean;
  language: string;
  audio_ms: number;
  stt_ms: number;
  model: string;
}

/** Origen de un mensaje dictado (data-model §4): sin texto ni audio. */
export interface InputMeta {
  source: "voice";
  audio_ms: number;
  stt_ms: number;
  edited: boolean;
  handsfree: boolean;
}

// ---------------------------------------------------------------- plataforma v1 (spec 026)

export type ProductName = "sugar" | "ethanol" | "power";

/** Escenario de la consola (data-model §1). Solo se envían los campos tocados. */
export interface Scenario {
  cane_delta_pct?: number;
  cane_available?: number;
  cane_quality?: number;
  steam_limit?: number;
  prioritize?: "margin" | "power";
  price_sugar_pct?: number;
  price_ethanol_pct?: number;
  price_power_pct?: number;
}

export type ScenarioField = Exclude<keyof Scenario, "prioritize">;

export interface PlanningAccess {
  authorized: boolean;
  reason: string;
}

export interface CapacityView {
  area: string;
  nominal: number;
  factor: number;
  effective: number;
  unit: string;
}

export interface CommitmentView {
  id: string;
  product: ProductName;
  min_quantity: number;
  unit: string;
  priority: number;
  counterparty: string;
}

export interface PlantSnapshot {
  week: string;
  data_version: string;
  seed: number;
  cane_available: number;
  cane_quality: number;
  capacities: CapacityView[];
  equipment: { id: string; kind: string; status: string; capacity_factor: number }[];
  inventories: Record<string, number>;
  current_mix: Record<string, number>;
  commitments: CommitmentView[];
  prices: Record<ProductName, number>;
  ranges: Partial<Record<ScenarioField, { min: number; max?: number }>>;
  synthetic: true;
  label: string;
}

export interface Sensitivity {
  constraint: string;
  dual: number;
  unit: string;
  weight: number;
  commitment: boolean;
}

export interface Shortfall {
  commitment_id: string;
  product: ProductName;
  missing: number;
  unit: string;
}

export interface PlanAlternative {
  name: string;
  margin: number;
  products: Record<ProductName, number>;
  delta_vs_best: number;
  violations?: string[];
}

/** Plan recomendado: `PlanResult.to_dict(card=True)` más la etiqueta y la frase de decisión. */
export interface PlanResponse {
  plan_id: string;
  status: "optimal" | "infeasible_relaxed";
  scenario: Scenario & { plant_id?: string };
  resolved: Record<string, number>;
  mix: { x_s: number; x_e: number; b: number; v: number; g: number };
  products: Record<ProductName, number>;
  margin: number;
  binding: Sensitivity | null;
  sensitivity: Sensitivity[];
  shortfalls: Shortfall[];
  alternatives: PlanAlternative[];
  assumptions: string[];
  week: string;
  data_version: string;
  synthetic: true;
  plan_card?: string;
  label?: string;
  decision_phrase?: string;
}

export interface PlanComparison {
  base: PlanResponse;
  scenario: PlanResponse;
  mix_delta: Record<"sugar" | "ethanol", { tonnes: number; points: number }>;
  products_delta: {
    product: ProductName;
    base: number;
    scenario: number;
    delta: number;
    unit: string;
  }[];
  commitments: {
    id: string;
    product: ProductName;
    required: number;
    unit: string;
    met_base: boolean;
    met_scenario: boolean;
    gap_base: number;
    gap_scenario: number;
  }[];
  margin_delta: number;
  synthetic: true;
}

export interface PendingProposal {
  confirmation_id: string;
  plan_id: string;
  summary: string;
  expires_at: string;
  question: string;
}

export interface ProposalOutcome {
  status: "saved" | "discarded";
  plan_id: string;
  message: string;
}

export interface ToolEvidence {
  name: string;
  description: string;
  kind: "read" | "write";
  requires_approval: boolean;
  routes: string[];
  profiles: string[];
  mcp_allowed: boolean;
}

export interface ToolCatalogEvidence {
  count: number;
  tools: ToolEvidence[];
}

export interface TurnTrace {
  thread_id: string;
  turn: number;
  turns: number;
  question: string;
  profile: string;
  route: string;
  decided_by: string;
  plan_steps: string[];
  tools: ToolInvocation[];
  duration_ms: number;
}

export interface ServiceStatus {
  id: "model" | "qdrant" | "whatsapp" | "gateway" | "voice" | "stt";
  label: string;
  status: "up" | "down" | "degraded" | "unknown";
  reason: string;
  action: string;
}

export interface ServicesEvidence {
  checked_at: string;
  services: ServiceStatus[];
}

export interface PublishedEvaluation {
  id: string;
  name: string;
  value: string;
  target: string;
  meets: boolean | "partial";
  date: string;
  report: string;
  note: string;
}
