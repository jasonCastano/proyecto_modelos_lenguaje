import { request } from "./api";
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
