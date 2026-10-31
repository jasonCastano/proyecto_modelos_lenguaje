import type { CorpusMetric } from "../lib/types";
import { formatMetricValue, statusLabel } from "../lib/format";

export function MetricsBand({ metrics }: { metrics: CorpusMetric[] }) {
  if (metrics.length === 0) {
    return null;
  }
  return (
    <section className="metrics-band" data-testid="metric-band" aria-labelledby="metrics-title">
      <div className="metrics-inner">
        <div className="metrics-head">
          <h2 className="metrics-title" id="metrics-title">
            Lo que el corpus puede sostener.
          </h2>
          <p className="metrics-note">
            Cifras de la última ejecución de oro. Se cargan desde los reportes, no se escriben a
            mano en la página.
          </p>
        </div>
        <div className="metrics-grid">
          {metrics.map((metric) => (
            <div className="metric" key={metric.key}>
              <span className="metric-label">{metric.label}</span>
              <strong className="metric-value">{formatMetricValue(metric.value)}</strong>
              <span className="metric-unit">
                {metric.unit} · {statusLabel(metric.status)}
              </span>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
