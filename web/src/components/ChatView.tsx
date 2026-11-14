import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  deleteMemory,
  getMemory,
  getObservability,
  getThread,
  type ObservabilityStatus,
  resumeThread,
  sendChat,
  streamChat,
} from "../lib/chat";
import {
  ApiClientError,
  type ApiError,
  type ChatResponse,
  type ChatRoute,
  type ChatRouteName,
  type ChatStreamEvent,
  type ChatTurn,
  type ChatVariant,
  type Citation,
  type MemoryItem,
  type Mode,
  type PendingAction,
  type ProfileItem,
  type RetrievalTrace,
} from "../lib/types";
import { ApprovalCard } from "./ApprovalCard";
import { RetrievedFragments } from "./RetrievedFragments";
import { SourceList } from "./SourceList";

const THREAD_KEY = "manuelita.chat.thread";
const USER_KEY = "manuelita.chat.user";
const MAX_CHARS = 500;
const PREFERENCE_LABEL: Record<string, string> = {
  response_format: "formato",
  topics_of_interest: "temas",
  language: "idioma",
};

const PROFILE_LABEL: Record<ProfileItem["key"], string> = {
  name: "nombre",
  workplace: "trabajo",
  role: "cargo",
  city: "ciudad",
};

const ROUTE_LABEL: Record<ChatRouteName, string> = {
  direct: "Directa",
  documental: "Documentos",
  structured: "Datos estructurados",
  mixed: "Documentos + datos",
  out_of_scope: "Fuera de alcance",
  clarify: "Aclaración",
};

const DECIDED_LABEL: Record<ChatRoute["decided_by"], string> = {
  rules: "reglas",
  llm: "LLM",
  demo: "heurística demo",
};

/** Mensajes de los casos de la rúbrica del Módulo 2 (docs/rubrica_modulo2.md). */
export const DEMO_CASES: Array<{ label: string; message: string }> = [
  { label: "RAG documental", message: "¿Qué dice el corpus sobre la política de calidad?" },
  { label: "Memoria: presentarse", message: "Me llamo Ana y trabajo en Carvajal" },
  { label: "Memoria: recordar", message: "¿Dónde trabajo?" },
  { label: "Dato estructurado", message: "¿Cuántas filiales tiene Manuelita?" },
  {
    label: "Ruta mixta",
    message:
      "Compara la meta de sostenibilidad del informe con cuántas toneladas de caña procesa Manuelita",
  },
  { label: "Saludo sin buscar", message: "Hola, buenas tardes" },
];

const RECENT_KEY = "manuelita.chat.recent";
const RECENT_MAX = 6;

interface RecentThread {
  id: string;
  variant: ChatVariant;
  title: string;
}

function readRecent(): RecentThread[] {
  try {
    const parsed = JSON.parse(readLocal(RECENT_KEY) ?? "[]") as RecentThread[];
    return Array.isArray(parsed) ? parsed.filter((item) => item && item.id) : [];
  } catch {
    return [];
  }
}

function rememberThread(entry: RecentThread): RecentThread[] {
  const others = readRecent().filter((item) => item.id !== entry.id);
  const existing = readRecent().find((item) => item.id === entry.id);
  const next = [existing ?? entry, ...others].slice(0, RECENT_MAX);
  writeLocal(RECENT_KEY, JSON.stringify(next));
  return next;
}

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

function readLocal(key: string): string | null {
  try {
    return window.localStorage.getItem(key);
  } catch {
    return readSession(key);
  }
}

function writeLocal(key: string, value: string): void {
  try {
    window.localStorage.setItem(key, value);
  } catch {
    writeSession(key, value);
  }
}

/** Usuario anónimo estable en este navegador: la memoria de largo plazo lo usa como namespace. */
function anonymousUser(): string {
  const saved = readLocal(USER_KEY);
  if (saved) return saved;
  const random =
    typeof crypto !== "undefined" && "randomUUID" in crypto
      ? crypto.randomUUID().slice(0, 12)
      : Math.random().toString(36).slice(2, 14);
  const user = `anon-${random}`;
  writeLocal(USER_KEY, user);
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
              {fragment.neutralized_sentences
                ? ` ${fragment.neutralized_sentences} ${
                    fragment.neutralized_sentences === 1 ? "oración neutralizada" : "oraciones neutralizadas"
                  } antes de llegar al modelo.`
                : ""}
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
        <p className="answer-meta" data-testid="turn-trace">
          Decidió: {DECIDED_LABEL[route.decided_by] ?? route.decided_by}
          {route.alternative ? ` (alternativa: ${ROUTE_LABEL[route.alternative]})` : ""} ·{" "}
          {turn.metrics.latency_ms} ms · {turn.metrics.model_calls} llamadas al modelo ·{" "}
          {turn.metrics.tool_calls} búsquedas · {turn.metrics.input_tokens + turn.metrics.output_tokens}{" "}
          tokens
        </p>
      </div>
    </li>
  );
}

interface LiveTurn {
  question: string;
  route: ChatRoute | null;
  stage: string;
  text: string;
}

function liveStage(event: ChatStreamEvent, current: LiveTurn): LiveTurn {
  switch (event.event) {
    case "route":
      return {
        ...current,
        route: event.route,
        stage: ["direct", "out_of_scope", "clarify"].includes(event.route.route)
          ? "Respondiendo sin buscar…"
          : "Recuperando evidencia…",
      };
    case "tool":
      return { ...current, stage: `Herramienta: ${event.tools.join(", ")}` };
    case "retrieval":
      return {
        ...current,
        stage: `${event.fragments} fragmentos · ${event.structured_rows} filas · generando…`,
      };
    case "token":
      return { ...current, stage: "Escribiendo…", text: current.text + event.text };
    default:
      return current;
  }
}

function LiveTurnCard({ live }: { live: LiveTurn }) {
  return (
    <li className="chat-turn" data-testid="chat-live" data-kind="streaming" aria-busy="true">
      <p className="chat-question">{live.question}</p>
      <div className="chat-route">
        {live.route ? (
          <span className="fragments-badge">
            Ruta: {ROUTE_LABEL[live.route.route]} · {Math.round(live.route.confidence * 100)} %
          </span>
        ) : null}
        <span className="fragments-meta">{live.stage}</span>
      </div>
      {live.text ? (
        <div className="answer">
          <p className="answer-body" aria-live="polite">
            {live.text}
          </p>
        </div>
      ) : null}
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
  const [preferences, setPreferences] = useState<MemoryItem[]>([]);
  const [profile, setProfile] = useState<ProfileItem[]>([]);
  const [live, setLive] = useState<LiveTurn | null>(null);
  const [recent, setRecent] = useState<RecentThread[]>(() => readRecent());
  const [observability, setObservability] = useState<ObservabilityStatus | null>(null);
  const userId = useRef(anonymousUser());

  function refreshPreferences() {
    void getMemory(userId.current)
      .then((view) => {
        setPreferences(view.items ?? []);
        setProfile(view.profile ?? []);
      })
      .catch(() => {
        setPreferences([]);
        setProfile([]);
      });
  }

  useEffect(() => {
    refreshPreferences();
    void getObservability()
      .then(setObservability)
      .catch(() => setObservability(null));
    const saved = stored.current;
    if (!saved) return;
    let active = true;
    void getThread(saved.id)
      .then((view) => {
        if (!active) return;
        setTurns(view.turns);
        setAction(view.pending_action);
        refreshPreferences();
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

  /** Retoma un hilo guardado: el estado vive en el checkpointer del servidor, no en el navegador. */
  async function openThread(entry: RecentThread) {
    setBusy(true);
    setError(null);
    try {
      const view = await getThread(entry.id);
      setVariant(view.variant);
      setThreadId(entry.id);
      setTurns(view.turns);
      setAction(view.pending_action);
      setActionQuestion("");
      writeSession(THREAD_KEY, JSON.stringify({ id: entry.id, variant: view.variant }));
    } catch (caught) {
      setRecent(() => {
        const next = readRecent().filter((item) => item.id !== entry.id);
        writeLocal(RECENT_KEY, JSON.stringify(next));
        return next;
      });
      report(caught);
    } finally {
      setBusy(false);
    }
  }

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
      refreshPreferences();
    } catch (caught) {
      report(caught);
    } finally {
      setBusy(false);
    }
  }

  async function forgetPreferences() {
    if (!threadId) return;
    setBusy(true);
    setError(null);
    try {
      const response = await deleteMemory(userId.current, threadId);
      setAction(response.pending_action);
      setActionQuestion("Olvida mis preferencias guardadas");
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
    const input = { message: clean, threadId, userId: userId.current, variant, mode };
    let current: LiveTurn = { question: clean, route: null, stage: "Enrutando…", text: "" };
    setLive(current);
    try {
      let response: ChatResponse;
      try {
        response = await streamChat(input, (event) => {
          current = liveStage(event, current);
          setLive(current);
        });
      } catch (caught) {
        // Un servidor sin streaming (404) responde igual por la ruta clásica.
        const notFound =
          caught instanceof ApiClientError && caught.apiError.code === "http_error";
        if (!notFound) throw caught;
        response = await sendChat(input);
      }
      setThreadId(response.thread_id);
      writeSession(THREAD_KEY, JSON.stringify({ id: response.thread_id, variant }));
      setRecent(rememberThread({ id: response.thread_id, variant, title: clean.slice(0, 60) }));
      if (response.status === "pending_approval") {
        setAction(response.pending_action);
        setActionQuestion(response.turn.question);
      } else {
        setTurns((previous) => [...previous, response.turn]);
      }
      setMessage("");
      refreshPreferences();
    } catch (caught) {
      report(caught);
    } finally {
      setLive(null);
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
        {observability ? (
          <span className="fragments-badge" data-testid="observability">
            Trazas:{" "}
            {observability.langsmith
              ? `LangSmith (${observability.project ?? "proyecto"})`
              : "log JSON por turno"}
          </span>
        ) : null}
      </div>

      {recent.length > 0 ? (
        <nav className="console-options" aria-label="Conversaciones recientes" data-testid="recent-threads">
          <span>Conversaciones recientes:</span>
          {recent.map((entry) => (
            <button
              aria-current={entry.id === threadId ? "true" : undefined}
              className="btn btn-link"
              disabled={busy}
              key={entry.id}
              onClick={() => void openThread(entry)}
              title={entry.id}
              type="button"
            >
              {entry.title || entry.id.slice(0, 8)} · {VARIANT_LABEL[entry.variant]}
            </button>
          ))}
        </nav>
      ) : null}

      <div className="console-options" aria-label="Casos de la demo" data-testid="demo-cases">
        <span>Casos de la demo:</span>
        {DEMO_CASES.map((item) => (
          <button
            className="chip"
            disabled={busy || action !== null}
            key={item.label}
            onClick={() => setMessage(item.message)}
            type="button"
          >
            {item.label}
          </button>
        ))}
      </div>

      {preferences.length > 0 || profile.length > 0 ? (
        <div className="console-options" data-testid="preferences">
          {profile.length > 0 ? (
            <span data-testid="profile">
              Tu perfil (memoria de largo plazo):{" "}
              {profile.map((item) => `${PROFILE_LABEL[item.key]}: ${item.value}`).join(" · ")}
            </span>
          ) : null}
          {preferences.length > 0 ? (
            <span>
              Tus preferencias:{" "}
              {preferences
                .map((item) => `${PREFERENCE_LABEL[item.key] ?? item.key}: ${item.value}`)
                .join(" · ")}
            </span>
          ) : null}
          <button
            className="btn btn-link"
            disabled={busy || action !== null || !threadId}
            onClick={() => void forgetPreferences()}
            type="button"
          >
            Olvidar
          </button>
        </div>
      ) : null}

      {turns.length > 0 || live ? (
        <ol className="chat-turns" aria-label="Historial de la conversación">
          {turns.map((turn) => (
            <ChatTurnCard key={turn.turn_id} turn={turn} />
          ))}
          {live ? <LiveTurnCard live={live} /> : null}
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
