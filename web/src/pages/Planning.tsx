/**
 * Consola de planificación industrial (spec 026, historia 1). Todas las cifras vienen del backend
 * (`/api/v1/planning`, el mismo optimizador del agente); aquí solo se piden y se dibujan. Desde la
 * spec 027 la consola es de libre elección en la web: abrirla activa el perfil planificador.
 */
import { useEffect, useState } from "react";

import { CaneFlow } from "../components/planning/CaneFlow";
import { CommitmentLedger } from "../components/planning/CommitmentLedger";
import { ComparisonView } from "../components/planning/ComparisonView";
import { PlanSummary } from "../components/planning/PlanSummary";
import { PlantStatePanel } from "../components/planning/PlantStatePanel";
import { ProposalDialog } from "../components/planning/ProposalDialog";
import { ScenarioForm } from "../components/planning/ScenarioForm";
import * as planningApi from "../lib/planning";
import { describeScenario } from "../lib/planningFormat";
import { queueMessage, setAudience } from "../lib/platform";
import { navigate } from "../lib/router";
import {
  ApiClientError,
  type PlanComparison,
  type PlanResponse,
  type PlantSnapshot,
  type Scenario,
} from "../lib/types";

function message(caught: unknown): string {
  return caught instanceof ApiClientError
    ? caught.apiError.message
    : "No se pudo calcular el plan. Revisa la conexión y vuelve a intentarlo.";
}

export function Planning() {
  const [snapshot, setSnapshot] = useState<PlantSnapshot | null>(null);
  const [plan, setPlan] = useState<PlanResponse | null>(null);
  const [scenario, setScenario] = useState<Scenario>({});
  const [comparison, setComparison] = useState<PlanComparison | null>(null);
  const [busy, setBusy] = useState(false);
  const [status, setStatus] = useState<string>("");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let active = true;
    setAudience("planificador");
    setBusy(true);
    setStatus("Calculando el plan…");
    void (async () => {
      const state = await planningApi.getState();
      if (!active) return;
      setSnapshot(state);
      const base = await planningApi.postPlan({});
      if (!active) return;
      setPlan(base);
      setStatus("Plan calculado");
    })()
      .catch((caught) => {
        if (active) setError(message(caught));
      })
      .finally(() => active && setBusy(false));
    return () => {
      active = false;
    };
  }, []);

  async function calculate(next: Scenario) {
    setBusy(true);
    setError(null);
    setStatus("Calculando el plan…");
    try {
      setPlan(await planningApi.postPlan(next));
      setScenario(next);
      setComparison(null);
      setStatus("Plan calculado");
    } catch (caught) {
      setError(message(caught));
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  async function compare(next: Scenario) {
    setBusy(true);
    setError(null);
    setStatus("Comparando con el plan base…");
    try {
      const result = await planningApi.postCompare(next);
      setComparison(result);
      setPlan({ ...result.scenario, label: plan?.label, decision_phrase: plan?.decision_phrase });
      setScenario(next);
      setStatus("Comparación lista");
    } catch (caught) {
      setError(message(caught));
      setStatus("");
    } finally {
      setBusy(false);
    }
  }

  function explain() {
    if (!plan) return;
    setAudience("planificador");
    queueMessage(
      `Explica el plan recomendado para este escenario: ${describeScenario(scenario)}. ` +
        `Usa los datos de la planta de esta semana (plan_id ${plan.plan_id}).`,
    );
    navigate("/agente");
  }

  return (
    <div className="planning">
      <header className="area-head">
        <h1 className="type-display area-head__title">Planificación industrial</h1>
        <p className="area-head__lead">
          Cuánta caña va a azúcar, a etanol y a energía esta semana, con los compromisos a la vista.
        </p>
        <p className="synthetic-tag">Datos sintéticos de demostración</p>
      </header>
      <p aria-live="polite" className="visually-hidden">
        {status}
      </p>
      {error ? (
        <p className="inline-error" role="alert">
          {error}
        </p>
      ) : null}
      {!snapshot ? (
        <p className="loading-line">{busy ? "Calculando el plan…" : "Cargando el estado de la planta…"}</p>
      ) : (
        <div className="planning__grid">
          <div className="planning__side">
            <ScenarioForm
              busy={busy}
              onCalculate={(next) => void calculate(next)}
              onCompare={(next) => void compare(next)}
              snapshot={snapshot}
            />
            <PlantStatePanel snapshot={snapshot} />
          </div>
          <div className="planning__main" aria-busy={busy || undefined}>
            {plan ? (
              <>
                <section aria-labelledby="flow-heading" className="flow-panel">
                  <h2 className="panel-title" id="flow-heading">
                    Plan recomendado
                  </h2>
                  {busy ? <p className="loading-line">Calculando el plan…</p> : null}
                  <CaneFlow compareTo={comparison?.base ?? null} plan={plan} />
                </section>
                <PlanSummary plan={plan} />
                {comparison ? <ComparisonView comparison={comparison} /> : null}
                <CommitmentLedger commitments={snapshot.commitments} plan={plan} />
                <div className="planning__actions">
                  <button
                    className="action action--quiet"
                    disabled={busy}
                    onClick={explain}
                    type="button"
                  >
                    Explicar con el agente
                  </button>
                  <ProposalDialog
                    create={() => planningApi.createProposal(scenario)}
                    decide={planningApi.decideProposal}
                    disabled={busy || plan.status !== "optimal"}
                  />
                </div>
              </>
            ) : null}
          </div>
        </div>
      )}
    </div>
  );
}
