import type { ShowcaseSection } from "../lib/types";
import { formatMetricValue, statusLabel } from "../lib/format";
import { EvidenceLinks } from "./EvidenceLinks";

interface ShowcaseStoryProps {
  sections: ShowcaseSection[];
}

export function ShowcaseStory({ sections }: ShowcaseStoryProps) {
  return (
    <section className="story" id="modulo-1" data-testid="showcase-story" aria-labelledby="story-title">
      <div className="story-head">
        <div>
          <p className="section-label">Módulo 1 · lo que se construyó</p>
          <h2 id="story-title">Del cañaveral a una respuesta que se puede verificar.</h2>
        </div>
        <p className="story-intro">
          Un recorrido breve por las decisiones, los datos y las pruebas que sostienen el RAG.
          Cada bloque enlaza a su evidencia y declara lo que todavía falta.
        </p>
      </div>
      <div className="story-list">
        {sections.map((section, index) => (
          <article className="story-item" id={`modulo-${section.id}`} key={section.id}>
            <div className="story-number" aria-hidden="true">
              {String(index + 1).padStart(2, "0")}
            </div>
            <div className="story-body">
              <h3>{section.title}</h3>
              <p>{section.body}</p>
              <EvidenceLinks links={section.evidence} />
              <span className="story-status">{statusLabel(section.status)}</span>
            </div>
            <div className="story-metrics">
              {section.metrics.map((metric) => (
                <div className="story-metric" key={metric.key}>
                  <span>{metric.label}</span>
                  <strong>
                    {formatMetricValue(metric.value)} {metric.unit}
                  </strong>
                </div>
              ))}
            </div>
          </article>
        ))}
      </div>
    </section>
  );
}
