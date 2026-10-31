import type { CitedAnswer, HealthStatus, ShowcaseResponse } from "../lib/types";

export const healthy: HealthStatus = {
  ok: true,
  provider: "deepseek",
  model: "deepseek-flash",
  configured: true,
  demo_available: true,
  detail: "Proveedor configurado.",
};

export const answerWithCitation: CitedAnswer = {
  query_id: "q-1",
  status: "ok",
  answer: "Manuelita ofrece azúcar y derivados con valor agregado.",
  citations: [
    {
      label: "U1",
      title: "Manuelita — Productos",
      url: "https://www.manuelita.com/manuelita-productos",
      section_path: ["Productos", "Azúcar"],
      page: 3,
      time_start: null,
      authority: "first_party",
      snippet: null,
    },
  ],
  model: "deepseek-flash",
  provider: "deepseek",
  prompt_version: "1.0",
  latency_ms: 2378,
  input_tokens: 1117,
  output_tokens: 230,
  cost_usd: null,
  review_required: false,
  error: null,
};

export const fallbackAnswer: CitedAnswer = {
  ...answerWithCitation,
  status: "fallback",
  answer: "No hay evidencia suficiente en el corpus para responder.",
  citations: [],
};

export const showcase: ShowcaseResponse = {
  generated_at: "2026-10-31T15:00:00Z",
  data_status: "complete",
  sections: [
    {
      id: "problem",
      order: 1,
      title: "La información estaba dispersa",
      body: "La pregunta se repartía entre muchas fuentes.",
      status: "done",
      metrics: [],
      evidence: [{ label: "Alcance", href: "https://example.com/alcance", kind: "spec" }],
    },
    {
      id: "data",
      order: 2,
      title: "Un corpus público y trazable",
      body: "Cada artefacto conserva procedencia.",
      status: "done",
      metrics: [
        {
          key: "chunks",
          label: "Fragmentos",
          value: 3810,
          unit: "fragmentos",
          source: "data/silver/reports/2026-10-silver-01/quality.json",
          status: "complete",
        },
      ],
      evidence: [],
    },
  ],
  metrics: [
    {
      key: "units",
      label: "Unidades de conocimiento",
      value: 15211,
      unit: "unidades",
      source: "data/gold/reports/2026-10-gold-01/quality.json",
      status: "complete",
    },
  ],
};
