import { useState, type FormEvent } from "react";

import { useRag } from "../hooks/useRag";
import type { HealthStatus } from "../lib/types";
import { AnswerPanel } from "./AnswerPanel";
import { DemoBanner } from "./DemoBanner";
import { FaqResults } from "./FaqResults";
import { TaskTabs } from "./TaskTabs";

export function RagConsole({ health }: { health: HealthStatus | null }) {
  const rag = useRag();
  const [question, setQuestion] = useState("");
  const [pack, setPack] = useState<"8000" | "32000">("8000");
  const [limit, setLimit] = useState(12);
  const [formError, setFormError] = useState<string | null>(null);

  const statusState =
    rag.mode === "demo"
      ? "demo"
      : health?.ok
        ? "ready"
        : health
          ? "warning"
          : "waiting";
  const statusText =
    rag.mode === "demo"
      ? "Modo demostración"
      : health?.ok
        ? "Proveedor listo"
        : health
          ? "Requiere atención"
          : "Conectando";

  function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setFormError(null);
    if (rag.task === "qa") {
      const clean = question.trim();
      if (!clean) {
        setFormError("Escribe una pregunta antes de enviar.");
        return;
      }
      if (clean.length > 500) {
        setFormError("La pregunta supera 500 caracteres.");
        return;
      }
      void rag.ask(clean);
      return;
    }
    if (rag.task === "summary") {
      void rag.summarize(pack);
      return;
    }
    void rag.faq(limit);
  }

  return (
    <section className="section console-section" id="consola" aria-labelledby="console-title">
      <div className="console-frame" data-testid="rag-console">
        <div className="console-head">
          <div>
            <p className="console-kicker">Consulta el corpus</p>
            <h2 className="console-title" id="console-title">
              Pregunta como se pregunta en el campo.
            </h2>
            <p className="console-subtitle">
              Tres tareas, una misma regla: responder solo con evidencia y citar la fuente. Si el
              corpus no alcanza, la interfaz lo dice.
            </p>
          </div>
          <span className="console-status" data-state={statusState}>
            {statusText}
          </span>
        </div>

        <DemoBanner
          health={health}
          mode={rag.mode}
          onEnableDemo={() => rag.setMode("demo")}
          onUseReal={() => rag.setMode("real")}
        />

        <TaskTabs
          task={rag.task}
          onChange={(task) => {
            rag.setTask(task);
            setFormError(null);
          }}
        />

        <form className="console-form" onSubmit={submit}>
          {rag.task === "qa" ? (
            <div className="field">
              <label htmlFor="question">Tu pregunta</label>
              <textarea
                className="question-input"
                data-testid="question-input"
                id="question"
                maxLength={500}
                onChange={(event) => setQuestion(event.target.value)}
                placeholder="¿Qué productos ofrece Manuelita?"
                value={question}
              />
              <div className="console-options">
                <span>{question.length}/500 caracteres</span>
              </div>
            </div>
          ) : null}

          {rag.task === "summary" ? (
            <div className="field">
              <label htmlFor="pack">Paquete de contexto</label>
              <select
                className="select-input"
                id="pack"
                onChange={(event) => setPack(event.target.value as "8000" | "32000")}
                value={pack}
              >
                <option value="8000">8.000 tokens · lectura completa</option>
                <option value="32000">32.000 tokens · contexto amplio</option>
              </select>
            </div>
          ) : null}

          {rag.task === "faq" ? (
            <div className="field">
              <label htmlFor="limit">Número de preguntas</label>
              <select
                className="select-input"
                id="limit"
                onChange={(event) => setLimit(Number(event.target.value))}
                value={limit}
              >
                {Array.from({ length: 11 }, (_, index) => index + 10).map((value) => (
                  <option key={value} value={value}>
                    {value} preguntas
                  </option>
                ))}
              </select>
            </div>
          ) : null}

          <button
            className="btn btn-accent"
            data-testid="ask-button"
            disabled={rag.status === "submitting"}
            type="submit"
          >
            {rag.status === "submitting"
              ? "Consultando…"
              : rag.task === "qa"
                ? "Preguntar"
                : rag.task === "summary"
                  ? "Generar resumen"
                  : "Generar FAQ"}
          </button>
        </form>

        {formError ? (
          <div className="console-message" data-kind="error" role="alert">
            {formError}
          </div>
        ) : null}

        {rag.task === "faq" ? <FaqResults items={rag.faqItems} /> : null}

        {rag.task !== "faq" ? (
          <AnswerPanel
            answer={rag.answer}
            error={rag.error}
            onDemo={() => rag.setMode("demo")}
            onRetry={rag.retry}
            status={rag.status}
          />
        ) : null}

        {rag.task === "faq" && rag.status === "submitting" ? (
          <div className="console-message" role="status">
            Generando preguntas con evidencia…
          </div>
        ) : null}
      </div>
    </section>
  );
}
