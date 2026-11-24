import { useEffect, useRef, useState, type FormEvent } from "react";

import {
  deleteMemory,
  getMemory,
  getObservability,
  getProfiles,
  getThread,
  type ObservabilityStatus,
  resumeThread,
  sendChat,
  STREAM_TIMEOUT_MS,
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
  type ContactRecord,
  type InputMeta,
  type Citation,
  type MemoryItem,
  type Mode,
  type PendingAction,
  type ProfileItem,
  type ProfileOption,
  type RetrievalTrace,
} from "../lib/types";
import { useDictation, type TranscriptInfo } from "../lib/useDictation";
import { useVoice } from "../lib/useVoice";
import { adoptUser, resetVisit, viewMode, visitUser } from "../lib/session";
import { AgentAvatar } from "./AgentAvatar";
import { ApprovalCard } from "./ApprovalCard";
import { ContactRecordPanel } from "./ContactRecordPanel";
import { MicButton } from "./MicButton";
import { RetrievedFragments } from "./RetrievedFragments";
import { QuickReplies } from "./QuickReplies";
import { SourceList } from "./SourceList";
import { VoiceControls } from "./VoiceControls";
import { WelcomeMessage } from "./WelcomeMessage";

const THREAD_KEY = "manuelita.chat.thread";
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

/** Spec 025: etiquetas de los perfiles de la plataforma (iguales a config/profiles.toml). */
export const AUDIENCE_LABEL: Record<string, string> = {
  visitante: "Visitante",
  cliente: "Cliente B2B",
  proveedor: "Proveedor",
  colaborador: "Colaborador",
  planificador: "Planificador industrial",
};

const ROUTE_LABEL: Record<ChatRouteName, string> = {
  direct: "Directa",
  documental: "Documentos",
  structured: "Datos estructurados",
  mixed: "Documentos + datos",
  out_of_scope: "Fuera de alcance",
  clarify: "Aclaración",
  planning: "Planificación industrial",
};

/** Spec 022: resumen de lo que hizo el gatekeeper Jev en el turno (vista técnica). */
export function jevSummary(jev: ChatTurn["jev"]): string | null {
  if (!jev || jev.status === "skipped") return null;
  if (jev.status === "failed") return `Jev no disponible (${jev.reason ?? "error"}) → decidió el LLM`;
  const confidence = (jev.confidence ?? 0).toLocaleString("es-CO", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  });
  const route = jev.route ? ROUTE_LABEL[jev.route] : "—";
  const latency = jev.latency_ms !== undefined ? ` · ${jev.latency_ms} ms` : "";
  return jev.accepted
    ? `Jev: ${route} ${confidence}${latency}`
    : `Jev sugirió ${route} (${confidence})${latency} → decidió el LLM`;
}

const GATEKEEPER_LABEL: Record<string, string> = {
  active: "activo",
  simulated: "simulado (demo)",
  no_key: "sin clave (desactivado)",
  disabled: "desactivado",
};

const DECIDED_LABEL: Record<ChatRoute["decided_by"], string> = {
  rules: "reglas",
  llm: "LLM",
  demo: "heurística demo",
  jev: "Jev (System One)",
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
const AVATAR_HIDDEN_KEY = "manuelita.avatar.hidden";
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

interface StoredThread {
  id: string;
  variant: ChatVariant;
}

/** Hilo en la URL (`#/chat/<uuid>`): la conversación sobrevive a recargas y se puede compartir. */
const THREAD_HASH = /^#\/chat\/([0-9a-f-]{36})$/i;

export function threadFromHash(hash: string): string | null {
  return THREAD_HASH.exec(hash)?.[1] ?? null;
}

function writeThreadHash(threadId: string | null) {
  try {
    const next = threadId ? `#/chat/${threadId}` : "#/chat";
    if (window.location.hash !== next) window.history.replaceState(null, "", next);
  } catch {
    // Sin History API (entornos de prueba restringidos): el hilo sigue en sessionStorage.
  }
}

function readThread(): StoredThread | null {
  const fromUrl = typeof window !== "undefined" ? threadFromHash(window.location.hash) : null;
  if (fromUrl) {
    const saved = readSession(THREAD_KEY);
    let variant: ChatVariant = "chain";
    try {
      const parsed = saved ? (JSON.parse(saved) as StoredThread) : null;
      if (parsed?.id === fromUrl && parsed.variant === "agent") variant = "agent";
    } catch {
      variant = "chain";
    }
    return { id: fromUrl, variant };
  }
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

const REDACTED_LABEL: Record<string, string> = {
  EMAIL: "‹correo protegido›",
  PHONE: "‹teléfono protegido›",
  DOCUMENT: "‹documento protegido›",
  CREDIT_CARD: "‹tarjeta protegida›",
};

/** Spec 018: en la vista de visitante, las marcas de redacción se muestran en lenguaje natural. */
export function visitorText(text: string): string {
  return text.replace(/\[REDACTED_([A-Z_]+)\]/g, (match, kind: string) => REDACTED_LABEL[kind] ?? match);
}

function seconds(ms: number, digits = 1): string {
  return (ms / 1000).toLocaleString("es-CO", {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });
}

/** Spec 023: «🎙 por voz · audio 2,0 s · reconocimiento 0,45 s» (vista técnica). */
export function inputSummary(input: ChatTurn["input"]): string | null {
  if (!input || input.source !== "voice") return null;
  const parts = [
    "🎙 por voz",
    `audio ${seconds(input.audio_ms)} s`,
    `reconocimiento ${seconds(input.stt_ms, 2)} s`,
  ];
  if (input.edited) parts.push("editado");
  if (input.handsfree) parts.push("manos libres");
  return parts.join(" · ");
}

/** Texto dictado recortado al máximo del campo, en un límite de palabra. */
export function clipDictated(text: string, limit: number): string {
  const clean = text.trim();
  if (clean.length <= limit) return clean;
  const cut = clean.slice(0, limit);
  const space = cut.lastIndexOf(" ");
  return (space > limit / 2 ? cut.slice(0, space) : cut).trimEnd();
}

export function ChatTurnCard({
  turn,
  firstAudioMs,
  onListen,
  technical = true,
}: {
  turn: ChatTurn;
  /** Spec 018: en la vista normal (visitantes) se ocultan ruta, fragmentos y métricas. */
  technical?: boolean;
  /** Spec 016: tiempo hasta el primer audio de la lectura en vivo. */
  firstAudioMs?: number;
  /** Spec 016: lee la respuesta en voz alta; sin voz no se muestra el botón. */
  onListen?: () => void;
}) {
  const route = turn.route;
  const kind = route.route === "clarify" ? "clarify" : turn.fallback ? "fallback" : "answered";
  const anomalous = turn.fragments.filter((fragment) => fragment.anomalous);
  return (
    <li className="chat-turn" data-testid="chat-turn" data-kind={kind}>
      <p className="chat-question">
        <span className="sr-only">Pregunta: </span>
        {technical ? turn.question : visitorText(turn.question)}
      </p>
      {technical ? (
        <div className="chat-route">
          <span className="fragments-badge" data-testid="route-chip">
            Ruta: {ROUTE_LABEL[route.route]} · {Math.round(route.confidence * 100)} %
          </span>
          <span className="fragments-meta">{route.reason}</span>
        </div>
      ) : null}
      {technical && anomalous.length > 0 ? (
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
      {technical ? <RetrievedFragments trace={turnTrace(turn)} showMeta={false} /> : null}
      {technical && turn.structured_rows.length > 0 ? (
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
        {technical ? (
        <p className="answer-meta" data-testid="turn-trace">
          Decidió: {DECIDED_LABEL[route.decided_by] ?? route.decided_by}
          {route.alternative ? ` (alternativa: ${ROUTE_LABEL[route.alternative]})` : ""} ·{" "}
          {turn.metrics.latency_ms} ms · {turn.metrics.model_calls} llamadas al modelo ·{" "}
          {turn.metrics.tool_calls} búsquedas · {turn.metrics.input_tokens + turn.metrics.output_tokens}{" "}
          tokens
          {firstAudioMs !== undefined
            ? ` · 🔊 primer audio ${(firstAudioMs / 1000).toLocaleString("es-CO", {
                minimumFractionDigits: 1,
                maximumFractionDigits: 1,
              })} s`
            : ""}
          {inputSummary(turn.input) ? (
            <span data-testid="turn-input"> · {inputSummary(turn.input)}</span>
          ) : null}
          {turn.profile ? (
            <span data-testid="turn-profile"> · Perfil: {AUDIENCE_LABEL[turn.profile] ?? turn.profile}</span>
          ) : null}
          {jevSummary(turn.jev) ? (
            <span data-kind={turn.jev?.status} data-testid="turn-jev">
              {" "}
              · {jevSummary(turn.jev)}
            </span>
          ) : null}
        </p>
        ) : null}
        {technical && (turn.plan_steps?.length || turn.tools?.length) ? (
          <details className="answer-meta turn-tools" data-testid="turn-tools">
            <summary>
              Plan y herramientas ({turn.tools?.length ?? 0}
              {turn.tools?.length === 1 ? " herramienta" : " herramientas"})
            </summary>
            {turn.plan_steps?.length ? (
              <ol data-testid="turn-plan">
                {turn.plan_steps.map((step, index) => (
                  <li key={`${index}-${step}`}>{step}</li>
                ))}
              </ol>
            ) : null}
            {turn.tools?.length ? (
              <ul data-testid="turn-tool-list">
                {turn.tools.map((call) => (
                  <li data-ok={call.ok} key={`${call.step}-${call.name}`}>
                    <code>{call.name}</code> · {call.duration_ms} ms
                    {call.ok ? "" : ` · error: ${call.error ?? "desconocido"}`}
                  </li>
                ))}
              </ul>
            ) : null}
          </details>
        ) : null}
        {onListen && turn.answer ? (
          <button className="btn btn-link" data-testid="turn-listen" onClick={onListen} type="button">
            🔊 Escuchar
          </button>
        ) : null}
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
          ? event.route.act
            ? "Pensando la respuesta…"
            : "Respondiendo sin buscar…"
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
    case "sentence":
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
  // Spec 025: perfil de atención elegido en la vista técnica (null = el del hilo).
  const [audience, setAudience] = useState<string | null>(null);
  const [profileOptions, setProfileOptions] = useState<ProfileOption[]>([]);
  // Spec 019: registro del contacto (CRM) del hilo; solo se muestra en la vista técnica.
  const [contact, setContact] = useState<ContactRecord | null>(null);
  const userId = useRef(visitUser());
  // Spec 018: vista de visitante (normal) o de sustentación (técnica, con ?vista=tecnica).
  const technical = useRef(viewMode() === "tecnica").current;
  const controller = useRef<AbortController | null>(null);

  useEffect(() => {
    if (!technical) return;
    void getProfiles(userId.current)
      .then((rows) => setProfileOptions(Array.isArray(rows) ? rows : []))
      .catch(() => setProfileOptions([]));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function chooseProfile(key: string) {
    setAudience(key || null);
    // La planificación industrial solo existe en la variante agente.
    if (key === "planificador" && variant !== "agent") startOver("agent");
  }

  function refreshObservability() {
    void getObservability(mode)
      .then(setObservability)
      .catch(() => setObservability(null));
  }
  const voice = useVoice();
  const [voiceKeys, setVoiceKeys] = useState<Record<number, string>>({});
  // Spec 023: dictado. `pendingInput` guarda el texto insertado para saber si se editó.
  const pendingInput = useRef<{ meta: InputMeta; text: string } | null>(null);
  const [handsfreeSend, setHandsfreeSend] = useState<{ text: string; meta: InputMeta } | null>(null);
  const [replies, setReplies] = useState(0);
  const lastSpoken = turns.length ? turns[turns.length - 1].answer : null;
  const dictation = useDictation({
    voice,
    threadId,
    busy,
    replies,
    lastSpoken,
    onTranscript: receiveTranscript,
  });

  function receiveTranscript(text: string, meta: InputMeta, _info: TranscriptInfo) {
    if (meta.handsfree) {
      const clean = clipDictated(text, MAX_CHARS);
      setMessage(clean);
      pendingInput.current = null;
      setHandsfreeSend({ text: clean, meta });
      return;
    }
    setMessage((previous) => {
      const joined = previous.trim() ? `${previous.trimEnd()} ${text.trim()}` : text.trim();
      const next = clipDictated(joined, MAX_CHARS);
      pendingInput.current = { meta, text: next };
      return next;
    });
  }

  function inputFor(text: string): InputMeta | undefined {
    const pending = pendingInput.current;
    if (!pending) return undefined;
    return { ...pending.meta, edited: text !== pending.text.trim() };
  }

  // Manos libres: el texto se ve 400 ms en el campo y se envía cuando no hay otra petición.
  useEffect(() => {
    if (!handsfreeSend || busy || action !== null) return undefined;
    const timer = window.setTimeout(() => {
      const pending = handsfreeSend;
      setHandsfreeSend(null);
      void send(pending.text, pending.meta);
    }, 400);
    return () => window.clearTimeout(timer);
    // `send` lee el estado vigente; basta con reaccionar a estos tres valores.
  }, [handsfreeSend, busy, action]);
  // Spec 017: avatar con sincronización de labios (visible por defecto; preferencia en el navegador).
  const [avatarHidden, setAvatarHidden] = useState(() => readLocal(AVATAR_HIDDEN_KEY) === "1");
  const avatarDebug = useRef(
    typeof window !== "undefined" && new URLSearchParams(window.location.search).has("avatarDebug"),
  );
  const avatarState = voice.speaking ? "speaking" : busy || voice.pending ? "thinking" : "idle";

  function toggleAvatar() {
    setAvatarHidden((previous) => {
      const next = !previous;
      writeLocal(AVATAR_HIDDEN_KEY, next ? "1" : "0");
      return next;
    });
  }

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
    refreshObservability();
    const saved = stored.current;
    if (!saved) return;
    let active = true;
    void getThread(saved.id)
      .then((view) => {
        if (!active) return;
        setVariant(view.variant);
        setTurns(view.turns);
        setAction(view.pending_action);
        setContact(view.contact ?? null);
        writeThreadHash(saved.id);
        refreshPreferences();
      })
      .catch(() => {
        if (!active) return;
        writeSession(THREAD_KEY, null);
        writeThreadHash(null);
        setThreadId(null);
      });
    return () => {
      active = false;
    };
  }, []);

  /** Retoma un hilo guardado: el estado vive en el checkpointer del servidor, no en el navegador. */
  async function openThread(entry: RecentThread) {
    voice.stop();
    setBusy(true);
    setError(null);
    try {
      const view = await getThread(entry.id);
      setVariant(view.variant);
      setThreadId(entry.id);
      setTurns(view.turns);
      setAction(view.pending_action);
      setContact(view.contact ?? null);
      setActionQuestion("");
      writeSession(THREAD_KEY, JSON.stringify({ id: entry.id, variant: view.variant }));
      writeThreadHash(entry.id);
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
    voice.stop();
    setVoiceKeys({});
    writeSession(THREAD_KEY, null);
    writeThreadHash(null);
    setVariant(nextVariant);
    setThreadId(null);
    setTurns([]);
    setAction(null);
    setContact(null);
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
      if (response.client?.user_id && response.client.user_id !== userId.current) {
        userId.current = response.client.user_id;
        adoptUser(response.client.user_id);
      }
      setTurns((previous) => [...previous, response.turn]);
      if (response.contact) setContact(response.contact);
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
    await send(clean, inputFor(clean));
  }

  async function send(clean: string, inputMeta?: InputMeta) {
    pendingInput.current = null;
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
    const input = {
      message: clean,
      threadId,
      userId: userId.current,
      variant,
      mode,
      ...(inputMeta ? { input: inputMeta } : {}),
      ...(audience ? { profile: audience } : {}),
    };
    let current: LiveTurn = { question: clean, route: null, stage: "Enrutando…", text: "" };
    setLive(current);
    // Spec 016: el envío es el gesto que habilita el audio; corta cualquier lectura anterior.
    const voiceKey = voice.startLive(threadId);
    const abort = new AbortController();
    controller.current = abort;
    const timer = window.setTimeout(() => abort.abort("timeout"), STREAM_TIMEOUT_MS);
    try {
      let response: ChatResponse;
      try {
        response = await streamChat(
          input,
          (event) => {
            current = liveStage(event, current);
            setLive(current);
            if (event.event === "token") voice.pushToken(event.text);
            if (event.event === "sentence") voice.pushSentence(event.text.trim());
          },
          abort.signal,
        );
      } catch (caught) {
        // Solo un servidor sin la ruta de streaming (404 sin cuerpo de error) cae a POST /api/chat;
        // un 5xx, un hilo inexistente o una cancelación se informan tal cual.
        const unavailable =
          caught instanceof ApiClientError && caught.apiError.code === "stream_unavailable";
        if (!unavailable) throw caught;
        response = await sendChat(input, abort.signal);
      }
      if (response.client?.reset) {
        // «Empecemos de nuevo»: cliente anónimo nuevo y conversación limpia.
        voice.finishLive(response.turn.answer, response.thread_id);
        userId.current = resetVisit();
        startOver();
        setMessage("");
        return;
      }
      if (response.client?.user_id && response.client.user_id !== userId.current) {
        // Cliente reconocido por correo y nombre: los turnos siguientes usan su memoria.
        userId.current = response.client.user_id;
        adoptUser(response.client.user_id);
      }
      setThreadId(response.thread_id);
      if (response.contact) setContact(response.contact);
      voice.finishLive(response.turn.answer, response.thread_id);
      if (voiceKey) setVoiceKeys((previous) => ({ ...previous, [response.turn.turn_id]: voiceKey }));
      writeSession(THREAD_KEY, JSON.stringify({ id: response.thread_id, variant }));
      writeThreadHash(response.thread_id);
      setRecent(rememberThread({ id: response.thread_id, variant, title: clean.slice(0, 60) }));
      if (response.status === "pending_approval") {
        setAction(response.pending_action);
        setActionQuestion(response.turn.question);
      } else {
        setTurns((previous) => [...previous, response.turn]);
      }
      setMessage("");
      refreshPreferences();
      refreshObservability();
    } catch (caught) {
      voice.stop();
      report(caught);
    } finally {
      window.clearTimeout(timer);
      controller.current = null;
      setLive(null);
      setBusy(false);
      setReplies((count) => count + 1);
    }
  }

  function stopGeneration() {
    controller.current?.abort("user");
  }

  return (
    <div className="chat-view" data-testid="chat-view">
      <div className="console-options" data-testid="chat-controls">
        {technical ? (
          <>
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
            {profileOptions.length > 0 ? (
              <>
                <label htmlFor="chat-profile">Perfil</label>
                <select
                  className="select-input"
                  data-testid="profile-select"
                  id="chat-profile"
                  onChange={(event) => chooseProfile(event.target.value)}
                  value={audience ?? ""}
                >
                  <option value="">Del hilo</option>
                  {profileOptions.map((option) => (
                    <option disabled={!option.authorized} key={option.key} value={option.key}>
                      {option.label}
                      {option.authorized ? "" : " (solo autorizados)"}
                    </option>
                  ))}
                </select>
              </>
            ) : null}
          </>
        ) : null}
        <VoiceControls voice={voice} showUnavailable />
        <button
          aria-pressed={!avatarHidden}
          className="btn btn-link"
          data-testid="avatar-toggle"
          onClick={toggleAvatar}
          type="button"
        >
          {avatarHidden ? "Mostrar avatar" : "Ocultar avatar"}
        </button>
        {technical && observability ? (
          <span className="fragments-badge" data-testid="observability">
            Trazas:{" "}
            {observability.langsmith
              ? `LangSmith (${observability.project ?? "proyecto"})`
              : "log JSON por turno"}
          </span>
        ) : null}
        {technical && observability?.vector_store?.[mode] ? (
          <span
            className="fragments-badge"
            data-kind={observability.vector_store[mode].startsWith("Respaldo") ? "warning" : "ok"}
            data-testid="vector-store"
            title={observability.vector_store[mode]}
          >
            {observability.vector_store[mode].startsWith("Respaldo")
              ? "⚠ Respaldo numpy (sin Qdrant)"
              : observability.vector_store[mode].replace("Búsqueda vectorial en ", "Vectores: ")}
          </span>
        ) : null}
        {technical && observability?.gatekeeper?.state ? (
          <span
            className="fragments-badge"
            data-kind={observability.gatekeeper.state === "no_key" ? "warning" : "ok"}
            data-testid="gatekeeper"
            title={
              observability.gatekeeper.model
                ? `${observability.gatekeeper.model} · umbral ${observability.gatekeeper.route_threshold ?? "—"}`
                : undefined
            }
          >
            Jev: {GATEKEEPER_LABEL[observability.gatekeeper.state] ?? observability.gatekeeper.state}
            {observability.gatekeeper.state === "active" && observability.gatekeeper.model
              ? ` · ${observability.gatekeeper.model}`
              : ""}
          </span>
        ) : null}
      </div>

      {technical && recent.length > 0 ? (
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

      {technical ? (
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
      ) : null}

      {technical && (preferences.length > 0 || profile.length > 0) ? (
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

      {technical && contact ? <ContactRecordPanel record={contact} /> : null}

      <div className={`chat-layout${avatarHidden ? "" : " chat-layout--avatar"}`}>
        {avatarHidden ? null : (
          <AgentAvatar analyser={voice.analyser} debug={avatarDebug.current} state={avatarState} />
        )}
        <div className="chat-main">
          <ol className="chat-turns" aria-label="Conversación con Valer-IA Caña">
            <WelcomeMessage conversationStarted={turns.length > 0 || live !== null} voice={voice} />
            {turns.map((turn) => (
              <ChatTurnCard
                firstAudioMs={voiceKeys[turn.turn_id] ? voice.firstAudio[voiceKeys[turn.turn_id]] : undefined}
                key={turn.turn_id}
                onListen={
                  voice.available && !voice.muted
                    ? () => {
                        const key = voice.speak(turn.answer, threadId);
                        if (key) setVoiceKeys((previous) => ({ ...previous, [turn.turn_id]: key }));
                      }
                    : undefined
                }
                technical={technical}
                turn={turn}
              />
            ))}
            {live ? <LiveTurnCard live={live} /> : null}
          </ol>
        </div>
      </div>

      {action ? (
        technical ? (
          <>
            {actionQuestion ? <p className="chat-question">{actionQuestion}</p> : null}
            <ApprovalCard
              action={action}
              busy={busy}
              key={action.action_id}
              onDecide={(decision, args) => void decide(decision, args)}
            />
          </>
        ) : (
          <QuickReplies
            action={action}
            busy={busy}
            key={action.action_id}
            onDecide={(decision) => void decide(decision)}
          />
        )
      ) : null}

      <form className="console-form" onSubmit={(event) => void submit(event)}>
        <div className="field">
          <label htmlFor="chat-message">Tu mensaje</label>
          <textarea
            className="question-input"
            data-testid="chat-input"
            id="chat-message"
            maxLength={MAX_CHARS}
            onChange={(event) => {
              setMessage(event.target.value);
              if (!event.target.value.trim()) pendingInput.current = null;
            }}
            disabled={!technical && action !== null}
            placeholder={
              !technical && action !== null
                ? "Responde a la pregunta de Valer-IA"
                : "Escríbele a Valer-IA Caña, por ejemplo: ¿Qué produce Manuelita?"
            }
            value={message}
          />
          <div className="console-options">
            <span>
              {message.length}/{MAX_CHARS} caracteres
            </span>
          </div>
        </div>
        <MicButton dictation={dictation} disabled={!technical && action !== null} />
        <button
          className="btn btn-accent"
          data-testid="chat-send"
          disabled={busy || action !== null}
          type="submit"
        >
          {busy
            ? "Pensando…"
            : action
              ? technical
                ? "Decide la acción pendiente"
                : "Responde arriba"
              : "Enviar"}
        </button>
        {busy && live ? (
          <button
            className="btn btn-link"
            data-testid="chat-stop"
            onClick={stopGeneration}
            type="button"
          >
            Detener generación
          </button>
        ) : null}
      </form>

      {error ? (
        <div className="console-message" data-kind="error" role="alert">
          {error.message}
        </div>
      ) : null}
    </div>
  );
}
