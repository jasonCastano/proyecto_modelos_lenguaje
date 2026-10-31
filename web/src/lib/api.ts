import {
  ApiClientError,
  type CitedAnswer,
  type FaqResponse,
  type HealthStatus,
  type Mode,
  type ShowcaseResponse,
} from "./types";

const API_BASE = "/api";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
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
  });
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

export function health(probe = false): Promise<HealthStatus> {
  return request<HealthStatus>(`/health${probe ? "?probe=true" : ""}`);
}

export function showcase(): Promise<ShowcaseResponse> {
  return request<ShowcaseResponse>("/showcase");
}
