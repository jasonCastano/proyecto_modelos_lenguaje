import {
  ApiClientError,
  type CitedAnswer,
  type FaqResponse,
  type AppVersion,
  type HealthStatus,
  type Mode,
  type RetrievalFragment,
  type RetrievalTrace,
  type ShowcaseResponse,
  type SttResult,
  type SttStatus,
  type WelcomeResponse,
} from "./types";

const API_BASE = "/api";

function asNumber(value: unknown, fallback = 0): number {
  return typeof value === "number" && Number.isFinite(value) ? value : fallback;
}

function normalizeFragment(raw: Partial<RetrievalFragment>): RetrievalFragment {
  return {
    unit_id: String(raw.unit_id ?? ""),
    title: String(raw.title ?? ""),
    url: String(raw.url ?? ""),
    score: asNumber(raw.score),
    semantic_score:
      typeof raw.semantic_score === "number" ? raw.semantic_score : null,
    lexical_score:
      typeof raw.lexical_score === "number" ? raw.lexical_score : null,
    origin: raw.origin ?? "semantic",
    status: raw.status ?? "used",
    reason: raw.reason ?? null,
  };
}

function normalizeTrace(raw: Partial<RetrievalTrace> | null | undefined): RetrievalTrace | null {
  if (!raw || !Array.isArray(raw.fragments)) {
    return null;
  }
  return {
    mode: raw.mode ?? "none",
    semantic_available: Boolean(raw.semantic_available),
    candidates: asNumber(raw.candidates, raw.fragments.length),
    threshold: asNumber(raw.threshold),
    fragments: raw.fragments.map(normalizeFragment),
    used_unit_ids: Array.isArray(raw.used_unit_ids) ? raw.used_unit_ids : [],
    notes: Array.isArray(raw.notes) ? raw.notes : [],
    elapsed_ms: asNumber(raw.elapsed_ms),
  };
}

function normalizeAnswer(payload: CitedAnswer): CitedAnswer {
  return { ...payload, retrieval: normalizeTrace(payload.retrieval) };
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
      ...init,
    });
  } catch (error) {
    throw new ApiClientError({
      code: "network_error",
      message:
        "No se pudo conectar con el servicio. Revisa la conexión y vuelve a intentar.",
      retryable: true,
      action: "reintentar",
    });
  }

  const payload = (await response.json().catch(() => null)) as unknown;
  if (!response.ok) {
    const envelope = payload as { error?: unknown } | null;
    const candidate = envelope?.error;
    if (
      candidate &&
      typeof candidate === "object" &&
      "code" in candidate &&
      "message" in candidate
    ) {
      throw new ApiClientError(candidate as {
        code: string;
        message: string;
        retryable: boolean;
        action: string;
      });
    }
    throw new ApiClientError({
      code: "http_error",
      message:
        response.status === 404
          ? "El servicio no encontró esa ruta."
          : "El servicio devolvió un error controlado.",
      retryable: response.status >= 500,
      action: response.status >= 500 ? "reintentar" : "revisar",
    });
  }
  return payload as T;
}

export function ask(
  question: string,
  mode: Mode,
  signal?: AbortSignal,
): Promise<CitedAnswer> {
  return request<CitedAnswer>("/ask", {
    method: "POST",
    body: JSON.stringify({ question, mode }),
    signal,
  }).then(normalizeAnswer);
}

export function summarize(
  pack: "8000" | "32000",
  mode: Mode,
  signal?: AbortSignal,
): Promise<CitedAnswer> {
  return request<CitedAnswer>("/summary", {
    method: "POST",
    body: JSON.stringify({ pack, mode }),
    signal,
  });
}

export function generateFaq(
  limit: number,
  mode: Mode,
  signal?: AbortSignal,
): Promise<FaqResponse> {
  return request<FaqResponse>("/faq", {
    method: "POST",
    body: JSON.stringify({ limit, mode }),
    signal,
  });
}

/** Versión del servidor: el pie la muestra para saber qué versión se está viendo. */
export function getVersion(): Promise<AppVersion> {
  return request<AppVersion>("/version");
}

export function health(probe = false): Promise<HealthStatus> {
  return request<HealthStatus>(`/health${probe ? "?probe=true" : ""}`);
}

/** Spec 018: bienvenida de Valer-IA Caña (sin modelo de lenguaje). */
export function getWelcome(): Promise<WelcomeResponse> {
  return request<WelcomeResponse>("/welcome");
}

export function showcase(): Promise<ShowcaseResponse> {
  return request<ShowcaseResponse>("/showcase");
}

// ---------------------------------------------------------------- dictado (spec 023)

/** Estado del dictado; siempre 200 (la indisponibilidad va en el cuerpo). */
export function getSttStatus(signal?: AbortSignal): Promise<SttStatus> {
  return request<SttStatus>("/stt", { signal });
}

/**
 * Envía el WAV (PCM16 mono a 16 kHz) y devuelve el texto. El audio no se guarda en el servidor.
 * Los errores llegan como `ApiClientError` con el `code` del contrato (`stt_busy`, …).
 */
export async function transcribe(
  wav: Blob,
  threadId: string | null,
  signal?: AbortSignal,
): Promise<SttResult> {
  const headers: Record<string, string> = { "Content-Type": "audio/wav" };
  if (threadId) headers["X-Thread-Id"] = threadId;
  return request<SttResult>("/stt", { method: "POST", body: wav, headers, signal });
}
