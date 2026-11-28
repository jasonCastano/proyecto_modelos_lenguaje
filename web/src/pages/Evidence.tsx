/**
 * Panel de evidencia técnica del Módulo 3 (spec 026, historia 3): servicios, catálogo, traza del
 * turno y evaluaciones publicadas, sin abrir la terminal. Todo es de solo lectura. Desde la spec 031
 * también aloja la consulta, el resumen y la FAQ de los Módulos 1 y 2, que salieron de la entrada.
 */
import { useEffect, useState } from "react";

import { EvaluationsTable } from "../components/evidence/EvaluationsTable";
import { LimitsNote } from "../components/LimitsNote";
import { RagConsole } from "../components/RagConsole";
import { ServiceStatusBar } from "../components/evidence/ServiceStatusBar";
import { ToolCatalogTable } from "../components/evidence/ToolCatalogTable";
import { TraceViewer } from "../components/evidence/TraceViewer";
import { getEvaluations, getServices, getTools, getTrace } from "../lib/evidence";
import {
  ApiClientError,
  type PublishedEvaluation,
  type ServiceStatus,
  type ToolEvidence,
  type HealthStatus,
  type TurnTrace,
} from "../lib/types";

const THREAD_KEY = "manuelita.chat.thread";
const NO_THREAD = "Haz una pregunta en el agente y vuelve aquí para ver su traza.";

export function currentThreadId(): string | null {
  try {
    const raw = window.sessionStorage.getItem(THREAD_KEY);
    const parsed = raw ? (JSON.parse(raw) as { id?: string }) : null;
    return parsed?.id ?? null;
  } catch {
    return null;
  }
}

export function Evidence({ health = null }: { health?: HealthStatus | null }) {
  const [services, setServices] = useState<ServiceStatus[]>([]);
  const [tools, setTools] = useState<ToolEvidence[]>([]);
  const [evaluations, setEvaluations] = useState<PublishedEvaluation[]>([]);
  const [trace, setTrace] = useState<TurnTrace | null>(null);
  const [traceMessage, setTraceMessage] = useState<string | null>(NO_THREAD);
  const [error, setError] = useState<string | null>(null);

  function loadTrace(turn?: number) {
    const threadId = currentThreadId();
    if (!threadId) {
      setTrace(null);
      setTraceMessage(NO_THREAD);
      return;
    }
    void getTrace(threadId, turn)
      .then(setTrace)
      .catch((caught) => {
        setTrace(null);
        setTraceMessage(caught instanceof ApiClientError ? caught.apiError.message : NO_THREAD);
      });
  }

  useEffect(() => {
    void getServices()
      .then((result) => setServices(result.services))
      .catch(() => setError("No se pudo consultar el estado de los servicios."));
    void getTools()
      .then((result) => setTools(result.tools))
      .catch(() => setError("No se pudo cargar el catálogo de herramientas."));
    void getEvaluations()
      .then(setEvaluations)
      .catch(() => setError("No se pudieron cargar las evaluaciones publicadas."));
    loadTrace();
  }, []);

  return (
    <div className="evidence">
      <header className="area-head">
        <h1 className="type-display area-head__title">Evidencia técnica</h1>
        <p className="area-head__lead">
          Lo que el jurado puede comprobar: qué herramientas tiene el agente, qué hizo en el último
          turno, qué servicios responden y cuánto midieron las evaluaciones.
        </p>
      </header>
      {error ? (
        <p className="inline-error" role="alert">
          {error}
        </p>
      ) : null}
      <ServiceStatusBar services={services} />
      <div className="evidence__grid">
        <ToolCatalogTable tools={tools} />
        <TraceViewer message={traceMessage} onTurn={(turn) => loadTrace(turn)} trace={trace} />
      </div>
      <EvaluationsTable evaluations={evaluations} />
      <section aria-labelledby="modules-heading" className="modules">
        <h2 className="section-title" id="modules-heading">
          Consulta, resumen y preguntas frecuentes
        </h2>
        <p className="modules__lead">
          Las funciones de los Módulos 1 y 2 responden solo con el corpus público y citan cada
          fragmento.
        </p>
        <RagConsole health={health} />
      </section>
      <div id="limites">
        <LimitsNote />
      </div>
    </div>
  );
}
