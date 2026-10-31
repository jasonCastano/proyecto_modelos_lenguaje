import { useCallback, useEffect, useRef, useState } from "react";

import { ApiClientError } from "../lib/types";
import type { ApiError, CitedAnswer, FaqItem, Mode, TaskKind } from "../lib/types";
import * as api from "../lib/api";

export type RagStatus = "idle" | "submitting" | "success" | "fallback" | "error";

type RagRequest =
  | { task: "qa"; question: string }
  | { task: "summary"; pack: "8000" | "32000" }
  | { task: "faq"; limit: number };

function toApiError(error: unknown): ApiError {
  if (error instanceof ApiClientError) {
    return error.apiError;
  }
  return {
    code: "unexpected_error",
    message: "Ocurrió un error inesperado. Revisa la consola y vuelve a intentar.",
    retryable: true,
    action: "reintentar",
  };
}

export function useRag() {
  const [mode, setMode] = useState<Mode>("real");
  const [task, setTask] = useState<TaskKind>("qa");
  const [status, setStatus] = useState<RagStatus>("idle");
  const [answer, setAnswer] = useState<CitedAnswer | null>(null);
  const [faqItems, setFaqItems] = useState<FaqItem[]>([]);
  const [error, setError] = useState<ApiError | null>(null);
  const [lastRequest, setLastRequest] = useState<RagRequest | null>(null);
  const controller = useRef<AbortController | null>(null);

  useEffect(
    () => () => {
      controller.current?.abort();
    },
    [],
  );

  const execute = useCallback(
    async (request: RagRequest) => {
      controller.current?.abort();
      const nextController = new AbortController();
      controller.current = nextController;
      setLastRequest(request);
      setStatus("submitting");
      setError(null);
      setAnswer(null);
      setFaqItems([]);
      try {
        if (request.task === "qa") {
          const result = await api.ask(request.question, mode, nextController.signal);
          setAnswer(result);
          setStatus(result.status === "ok" ? "success" : result.status === "fallback" ? "fallback" : "error");
          if (result.status === "error" && result.error) {
            setError(result.error);
          }
          return;
        }
        if (request.task === "summary") {
          const result = await api.summarize(request.pack, mode, nextController.signal);
          setAnswer(result);
          setStatus(result.status === "ok" ? "success" : result.status === "fallback" ? "fallback" : "error");
          if (result.status === "error" && result.error) {
            setError(result.error);
          }
          return;
        }
        const result = await api.generateFaq(request.limit, mode, nextController.signal);
        setFaqItems(result.items);
        setStatus("success");
      } catch (caught) {
        if (caught instanceof DOMException && caught.name === "AbortError") {
          return;
        }
        setError(toApiError(caught));
        setStatus("error");
      }
    },
    [mode],
  );

  const ask = useCallback(
    (question: string) => execute({ task: "qa", question }),
    [execute],
  );
  const summarize = useCallback(
    (pack: "8000" | "32000") => execute({ task: "summary", pack }),
    [execute],
  );
  const faq = useCallback(
    (limit: number) => execute({ task: "faq", limit }),
    [execute],
  );
  const retry = useCallback(() => {
    if (lastRequest) {
      void execute(lastRequest);
    }
  }, [execute, lastRequest]);

  return {
    mode,
    setMode,
    task,
    setTask,
    status,
    answer,
    faqItems,
    error,
    ask,
    summarize,
    faq,
    retry,
    clearError: () => setError(null),
  };
}
