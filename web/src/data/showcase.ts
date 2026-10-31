import type { ShowcaseSection } from "../lib/types";

const repo = "https://github.com/jasonCastano/proyecto_modelos_lenguaje/blob/main";

export const fallbackSections: ShowcaseSection[] = [
  {
    id: "problem",
    order: 1,
    title: "La información estaba dispersa",
    body:
      "La pregunta de un cliente primerizo se repartía entre el sitio oficial, informes, noticias, videos y portales públicos. Un asistente genérico podía responder rápido, pero no siempre con evidencia.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Alcance y 40 preguntas", href: `${repo}/docs/alcance.md`, kind: "spec" }],
  },
  {
    id: "data",
    order: 2,
    title: "Un corpus público y trazable",
    body:
      "La adquisición respeta robots.txt, sitemap, límites de tasa y una campaña reanudable. Cada artefacto conserva URL, fecha UTC, tipo y hash; la cuarentena queda auditada y fuera del corpus activo.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Ficha de datos", href: `${repo}/docs/data_card.md`, kind: "report" }],
  },
  {
    id: "medallion",
    order: 3,
    title: "Bronce, plata y oro",
    body:
      "El bronce guarda bytes inmutables; la plata produce documentos canónicos, alias y fragmentos; el oro consolida unidades extractivas, hechos, entidades, conflictos y paquetes de contexto con citas.",
    status: "done",
    metrics: [],
    evidence: [
      { label: "Capa oro", href: `${repo}/specs/004-gold-medallion-layer/spec.md`, kind: "spec" },
      { label: "ADR de oro", href: `${repo}/docs/decisions/0004-gold-layer.md`, kind: "adr" },
    ],
  },
  {
    id: "prompts",
    order: 4,
    title: "Prompts que prohíben inventar",
    body:
      "Cada prompt declara rol, tarea, contexto delimitado, reglas, formato de citación y fallback. El texto recuperado es dato no confiable; nunca se ejecuta como instrucción.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Prompt log", href: `${repo}/docs/prompt_log.md`, kind: "report" }],
  },
  {
    id: "tasks",
    order: 5,
    title: "Tres tareas, una misma regla",
    body:
      "Resumen, FAQ y Q&A usan LangChain y recuperación léxica determinista. DeepSeek genera la respuesta, pero las citas [U#] se validan contra el contexto recuperado.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Tareas LangChain", href: `${repo}/specs/011-deepseek-api-model/spec.md`, kind: "spec" }],
  },
  {
    id: "app",
    order: 6,
    title: "Una interfaz para preguntar y entender",
    body:
      "Esta página reemplaza el prototipo: hero editorial, consola RAG, fuentes visibles, modo demo y un recorrido que explica el sistema sin diapositivas.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Frontend", href: `${repo}/specs/012-manuelita-rag-showcase/spec.md`, kind: "spec" }],
  },
  {
    id: "metrics",
    order: 7,
    title: "Medir antes de afirmar",
    body:
      "Las cifras del corpus, la cobertura y los tokens provienen de reportes reales. La evaluación de 40 preguntas medirá calidad, citas y alucinaciones con una línea base.",
    status: "partial",
    metrics: [],
    evidence: [{ label: "Cobertura", href: `${repo}/data/gold/coverage.json`, kind: "report" }],
  },
  {
    id: "limits",
    order: 8,
    title: "Lo que todavía falta",
    body:
      "La evaluación de 40 preguntas, el informe y el guion de demo están en curso. El sistema declara sus vacíos y no sustituye la información oficial de Manuelita.",
    status: "pending",
    metrics: [],
    evidence: [{ label: "Limitaciones", href: `${repo}/README.md`, kind: "report" }],
  },
];
