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
    id: "retrieval",
    order: 6,
    title: "Buscar por significado, no solo por palabras",
    body:
      "El Módulo 2 suma un índice semántico local (fastembed) y una recuperación híbrida con BM25. Se mide con Recall@10, nDCG@10 y MRR frente a la línea base léxica del Módulo 1.",
    status: "done",
    metrics: [],
    evidence: [
      { label: "Recuperación semántica", href: `${repo}/specs/013-semantic-rag-chatbot/spec.md`, kind: "spec" },
    ],
  },
  {
    id: "agent",
    order: 7,
    title: "Una conversación que recuerda y decide",
    body:
      "Cada hilo guarda su memoria. Un enrutador elige entre respuesta directa, documentos, tabla estructurada o fuera de alcance (35 de 36 aciertos). La misma conversación corre como cadena (una búsqueda por turno) o como agente con LangGraph.",
    status: "done",
    metrics: [],
    evidence: [
      { label: "Memoria, enrutador y agente", href: `${repo}/specs/014-rag-agent-memory-router/spec.md`, kind: "spec" },
      { label: "ADR del agente", href: `${repo}/docs/decisions/0016-rag-agent-langgraph.md`, kind: "adr" },
    ],
  },
  {
    id: "safety",
    order: 8,
    title: "Leer solo, escribir con permiso",
    body:
      "El texto recuperado no puede dar órdenes: hay blindaje contra inyección y se redactan datos personales. Guardar una preferencia, olvidar la memoria o exportar una conversación espera la aprobación de una persona.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Política de memoria", href: `${repo}/docs/memoria.md`, kind: "report" }],
  },
  {
    id: "app",
    order: 9,
    title: "Una interfaz para preguntar y entender",
    body:
      "Esta página reemplaza el prototipo: hero editorial, consola RAG con pestaña de conversación, fuentes visibles, modo demo y un recorrido que explica el sistema sin diapositivas.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Frontend", href: `${repo}/specs/012-manuelita-rag-showcase/spec.md`, kind: "spec" }],
  },
  {
    id: "metrics",
    order: 10,
    title: "Medir antes de afirmar",
    body:
      "Las cifras del corpus, la cobertura y los tokens provienen de reportes reales. En el Módulo 2, cadena y agente citan bien el 100 % de las veces; la cadena responde en menos de 10 s siempre y el agente en el 94 % de las consultas.",
    status: "partial",
    metrics: [],
    evidence: [
      { label: "Cobertura", href: `${repo}/data/gold/coverage.json`, kind: "report" },
      { label: "Evaluación del Módulo 2", href: `${repo}/docs/evaluacion_modulo2.md`, kind: "report" },
    ],
  },
  {
    id: "limits",
    order: 11,
    title: "Lo que todavía falta",
    body:
      "Falta correr la evaluación de 40 preguntas del Módulo 1 y ensayar la demo. En el Módulo 2 quedan la calificación humana de las repreguntas y repetir la fidelidad del juez. El sistema declara sus vacíos y no sustituye la información oficial.",
    status: "pending",
    metrics: [],
    evidence: [{ label: "Limitaciones", href: `${repo}/README.md`, kind: "report" }],
  },
];
