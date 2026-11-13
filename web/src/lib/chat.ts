import { request } from "./api";
import {
  ApiClientError,
  type ChatStreamEvent,
} from "./types";
import type {
  ChatResponse,
  ChatVariant,
  MemoryView,
  Mode,
  PendingAction,
  ThreadView,
} from "./types";

export interface SendChatInput {
  message: string;
  threadId: string | null;
  userId: string;
  variant: ChatVariant;
  mode: Mode;
}

export function sendChat(input: SendChatInput, signal?: AbortSignal): Promise<ChatResponse> {
  return request<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({
      thread_id: input.threadId,
      user_id: input.userId,
      message: input.message,
      variant: input.variant,
      mode: input.mode,
    }),
    signal,
  });
}

export function getThread(threadId: string, signal?: AbortSignal): Promise<ThreadView> {
  return request<ThreadView>(`/threads/${encodeURIComponent(threadId)}`, { signal });
}

export function resumeThread(
  threadId: string,
  actionId: string,
  decision: NonNullable<PendingAction["decision"]>,
  args?: Record<string, unknown>,
): Promise<ChatResponse> {
  return request<ChatResponse>(`/threads/${encodeURIComponent(threadId)}/resume`, {
    method: "POST",
    body: JSON.stringify({ action_id: actionId, decision, ...(args ? { args } : {}) }),
  });
}

export function getMemory(userId: string): Promise<MemoryView> {
  return request<MemoryView>(`/memory/${encodeURIComponent(userId)}`);
}

export function deleteMemory(
  userId: string,
  threadId: string,
): Promise<{ status: "pending_approval"; thread_id: string; pending_action: PendingAction }> {
  return request(`/memory/${encodeURIComponent(userId)}?thread_id=${encodeURIComponent(threadId)}`, {
    method: "DELETE",
  });
}

function parseBlock(block: string): ChatStreamEvent | null {
  const data = block
    .split("\n")
    .filter((line) => line.startsWith("data:"))
    .map((line) => line.slice(5).trimStart())
    .join("\n");
  if (!data) return null;
  try {
    return JSON.parse(data) as ChatStreamEvent;
  } catch {
    return null;
  }
}

/**
 * Conversación en streaming (SSE sobre `fetch`): llama a `onEvent` con la ruta, la recuperación y
 * cada token, y resuelve con la respuesta final validada (la misma de `POST /api/chat`).
 */
export async function streamChat(
  input: SendChatInput,
  onEvent: (event: ChatStreamEvent) => void,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  let response: Response;
  try {
    response = await fetch("/api/chat/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json", Accept: "text/event-stream" },
      body: JSON.stringify({
        thread_id: input.threadId,
        user_id: input.userId,
        message: input.message,
        variant: input.variant,
        mode: input.mode,
      }),
      signal,
    });
  } catch {
    throw new ApiClientError({
      code: "network_error",
      message: "No se pudo conectar con el servicio. Revisa la conexión y vuelve a intentar.",
      retryable: true,
      action: "reintentar",
    });
  }
  if (!response.ok || !response.body) {
    const payload = (await response.json().catch(() => null)) as {
      error?: { code: string; message: string; retryable: boolean; action: string };
    } | null;
    throw new ApiClientError(
      payload?.error ?? {
        code: "http_error",
        message: "El servicio devolvió un error controlado.",
        retryable: response.status >= 500,
        action: response.status >= 500 ? "reintentar" : "revisar",
      },
    );
  }
  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let final: ChatResponse | null = null;
  for (;;) {
    const { done, value } = await reader.read();
    buffer += decoder.decode(value ?? new Uint8Array(), { stream: !done });
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const event = parseBlock(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      boundary = buffer.indexOf("\n\n");
      if (!event) continue;
      onEvent(event);
      if (event.event === "done") final = event.response;
      if (event.event === "error") {
        throw new ApiClientError({
          code: event.error.code,
          message: event.error.message,
          retryable: true,
          action: "reintentar",
        });
      }
    }
    if (done) break;
  }
  if (!final) {
    throw new ApiClientError({
      code: "stream_incomplete",
      message: "La respuesta se interrumpió antes de terminar. Vuelve a intentar.",
      retryable: true,
      action: "reintentar",
    });
  }
  return final;
}

export interface ObservabilityStatus {
  langsmith: boolean;
  project: string | null;
  structured_log: string | null;
}

export function getObservability(): Promise<ObservabilityStatus> {
  return request<ObservabilityStatus>("/observability");
}
