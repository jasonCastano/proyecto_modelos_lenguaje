import { useEffect, useRef, useState, type FormEvent } from "react";

import { getThread, resumeThread, sendChat } from "../lib/chat";
import {
  ApiClientError,
  type ApiError,
  type ChatRouteName,
  type ChatTurn,
  type ChatVariant,
  type Citation,
  type Mode,
  type PendingAction,
  type RetrievalTrace,
} from "../lib/types";
import { ApprovalCard } from "./ApprovalCard";
import { RetrievedFragments } from "./RetrievedFragments";
import { SourceList } from "./SourceList";

const THREAD_KEY = "manuelita.chat.thread";
const USER_KEY = "manuelita.chat.user";
const MAX_CHARS = 500;

const ROUTE_LABEL: Record<ChatRouteName, string> = {
  direct: "Directa",
  documental: "Documentos",
  structured: "Datos estructurados",
  out_of_scope: "Fuera de alcance",
  clarify: "Aclaración",
};

const VARIANT_LABEL: Record<ChatVariant, string> = {
  chain: "Cadena",
  agent: "Agente",
};

function readSession(key: string): string | null {
  try {
    return window.sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function writeSession(key: string, value: string | null): void {
  try {
    if (value === null) {
      window.sessionStorage.removeItem(key);
    } else {
      window.sessionStorage.setItem(key, value);
    }
  } catch {
    // Sin almacenamiento de sesión el hilo dura lo que dure la página.
  }
}

function anonymousUser(): string {
  const saved = readSession(USER_KEY);
  if (saved) return saved;
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  const user = `anon-${random}`;
  writeSession(USER_KEY, user);
  return user;
}

interface StoredThread {
  id: string;
  variant: ChatVariant;
}

function readThread(): StoredThread | null {
  const raw = readSession(THREAD_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw) as StoredThread;
    return parsed.id && (parsed.variant === "chain" || parsed.variant === "agent") ? parsed : null;
  } catch {
    return null;
  }
}

function turnTrace(turn: ChatTurn): RetrievalTrace | null {
  if (turn.fragments.length === 0) return null;
  return {
    mode: "hybrid",
    semantic_available: true,
    candidates: turn.fragments.length,
    threshold: 0,
    fragments: turn.fragments,
    used_unit_ids: turn.fragments.map((fragment) => fragment.unit_id),
    notes: [],
    elapsed_ms: turn.metrics.latency_ms,
  };
}

function turnCitations(turn: ChatTurn): Citation[] {
  return turn.citations.map((citation) => ({
    label: citation.label,
    title: (citation.title || citation.url).split("\n")[0].slice(0, 120),
    url: citation.url,
    section_path: [],
    authority: "first_party",
  }));
}

export function ChatTurnCard({ turn }: { turn: ChatTurn }) {
  const route = turn.route;
  const kind = route.route === "clarify" ? "clarify" : turn.fallback ? "fallback" : "answered";
  const anomalous = turn.fragments.filter((fragment) => fragment.anomalous);
  return (
    <li className="chat-turn" data-testid="chat-turn" data-kind={kind}>
      <p className="chat-question">
        <span className="sr-only">Pregunta: </span>
        {turn.question}
      </p>
      <div className="chat-route">
        <span className="fragments-badge" data-testid="route-chip">
          Ruta: {ROUTE_LABEL[route.route]} · {Math.round(route.confidence * 100)} %
        </span>
        <span className="fragments-meta">{route.reason}</span>
      </div>
      {anomalous.length > 0 ? (
        <div className="console-message" data-kind="warning" data-testid="anomaly-warning" role="note">
          {anomalous.map((fragment) => (
            <p key={fragment.label}>
              El fragmento [{fragment.label}] contiene instrucciones dirigidas al asistente (
              {(fragment.anomaly_reasons ?? []).join(", ")}). Se trató como dato y no se obedeció.
            </p>
          ))}
        </div>
      ) : null}
      <RetrievedFragments trace={turnTrace(turn)} showMeta={false} />
      {turn.structured_rows.length > 0 ? (
        <ul className="chat-rows" data-testid="structured-rows">
          {turn.structured_rows.map((row) => (
            <li key={row.fact_id}>
              [{row.label}] {row.subject_label} · {row.attribute}: {row.value}
              {row.year ? ` (${row.year})` : ""}
            </li>
          ))}
        </ul>
      ) : null}
      <div className={`answer ${turn.fallback ? "answer-fallback" : ""}`}>
        <p className="answer-body">{turn.answer}</p>
        <SourceList citations={turnCitations(turn)} />
        <p className="answer-meta">
          {turn.metrics.latency_ms} ms · {turn.metrics.model_calls} llamadas al modelo ·{" "}
          {turn.metrics.tool_calls} búsquedas
        </p>
      </div>
    </li>
  );
}

export function ChatView({ mode }: { mode: Mode }) {
  const stored = useRef(readThread());
  const [variant, setVariant] = useState<ChatVariant>(stored.current?.variant ?? "chain");
  const [threadId, setThreadId] = useState<string | null>(stored.current?.id ?? null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const [action, setAction] = useState<PendingAction | null>(null);
  const [actionQuestion, setActionQuestion] = useState("");
  const [error, setError] = useState<ApiError | null>(null);
  const userId = useRef(anonymousUser());

  useEffect(() => {
    const saved = stored.current;
    if (!saved) return;
    let active = true;
    void getThread(saved.id)
      .then((view) => {
        if (!active) return;
        setTurns(view.turns);
        setAction(view.pending_action);
      })
      .catch(() => {
        if (!active) return;
        writeSession(THREAD_KEY, null);
        setThreadId(null);
      });
    return () => {
      active = false;
    };
  }, []);

  function startOver(nextVariant: ChatVariant = variant) {
    writeSession(THREAD_KEY, null);
    setVariant(nextVariant);
    setThreadId(null);
    setTurns([]);
    setAction(null);
    setError(null);
  }

  function report(caught: unknown) {
    setError(
      caught instanceof ApiClientError
        ? caught.apiError
        : {
            code: "unexpected_error",
            message: "No se pudo completar la solicitud.",
            retryable: true,
            action: "reintentar",
          },
    );
  }

  async function decide(decision: "approve" | "edit" | "reject", args?: Record<string, unknown>) {
    if (!threadId || !action) return;
    setBusy(true);
    setError(null);
    try {
      const response = await resumeThread(threadId, action.action_id, decision, args);
      setTurns((previous) => [...previous, response.turn]);
      setAction(response.status === "pending_approval" ? response.pending_action : null);
    } catch (caught) {
      report(caught);
    } finally {
      setBusy(false);
    }
  }

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const clean = message.trim();
    if (!clean) {
      setError({
        code: "empty_question",
        message: "Escribe un mensaje antes de enviar.",
        retryable: false,
        action: "revisar",
      });
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const response = await sendChat({
        message: clean,
        threadId,
        userId: userId.current,
        variant,
        mode,
      });
      setThreadId(response.thread_id);
      writeSession(THREAD_KEY, JSON.stringify({ id: response.thread_id, variant }));
      if (response.status === "pending_approval") {
        setAction(response.pending_action);
        setActionQuestion(response.turn.question);
      } else {
        setTurns((previous) => [...previous, response.turn]);
      }
      setMessage("");
    } catch (caught) {
      report(caught);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="chat-view" data-testid="chat-view">
      <div className="console-options">
        <label htmlFor="chat-variant">Variante</label>
        <select
          className="select-input"
          id="chat-variant"
          onChange={(event) => startOver(event.target.value as ChatVariant)}
          value={variant}
        >
          {(Object.keys(VARIANT_LABEL) as ChatVariant[]).map((key) => (
            <option key={key} value={key}>
              {VARIANT_LABEL[key]}
            </option>
          ))}
        </select>
        <button className="btn btn-link" type="button" onClick={() => startOver()}>
          Nueva conversación
        </button>
      </div>

      {turns.length > 0 ? (
        <ol className="chat-turns" aria-label="Historial de la conversación">
          {turns.map((turn) => (
            <ChatTurnCard key={turn.turn_id} turn={turn} />
          ))}
        </ol>
      ) : (
        <p className="console-subtitle">
          Pregunta y repregunta: el asistente recuerda el hilo, enruta cada mensaje y cita sus
          fuentes.
        </p>
      )}

      {action ? (
        <>
          {actionQuestion ? <p className="chat-question">{actionQuestion}</p> : null}
          <ApprovalCard
            action={action}
            busy={busy}
            key={action.action_id}
            onDecide={(decision, args) => void decide(decision, args)}
          />
        </>
      ) : null}

      <form className="console-form" onSubmit={(event) => void submit(event)}>
        <div className="field">
          <label htmlFor="chat-message">Tu mensaje</label>
          <textarea
            className="question-input"
            data-testid="chat-input"
            id="chat-message"
            maxLength={MAX_CHARS}
            onChange={(event) => setMessage(event.target.value)}
            placeholder="¿Qué produce Manuelita?"
            value={message}
          />
          <div className="console-options">
            <span>
              {message.length}/{MAX_CHARS} caracteres
            </span>
          </div>
        </div>
        <button
          className="btn btn-accent"
          data-testid="chat-send"
          disabled={busy || action !== null}
          type="submit"
        >
          {busy ? "Pensando…" : action ? "Decide la acción pendiente" : "Enviar"}
        </button>
      </form>

      {error ? (
        <div className="console-message" data-kind="error" role="alert">
          {error.message}
        </div>
      ) : null}
    </div>
  );
}
