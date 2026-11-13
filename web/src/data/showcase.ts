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
    title: "Qdrant: buscar por significado, no solo por palabras",
    body:
      "Los 15.211 fragmentos viven en una colección de Qdrant (coseno, índice HNSW) con payload filtrable por tema, fuente y tipo. La búsqueda densa top-k se fusiona con BM25 y se mide con Recall@10, nDCG@10 y MRR en 36 consultas etiquetadas.",
    status: "done",
    metrics: [],
    evidence: [
      { label: "Recuperación semántica", href: `${repo}/specs/013-semantic-rag-chatbot/spec.md`, kind: "spec" },
      { label: "ADR de Qdrant", href: `${repo}/docs/decisions/0018-qdrant-y-rubrica-modulo2.md`, kind: "adr" },
    ],
  },
  {
    id: "agent",
    order: 7,
    title: "Una conversación que recuerda y decide",
    body:
      "Corto plazo: cada hilo se guarda con SqliteSaver y sobrevive al reinicio. Largo plazo: el perfil y las preferencias viven en el Store y se recuperan en otro hilo. El enrutador elige respuesta directa, documentos, tabla, ambas o fuera de alcance (35 de 36 aciertos) y no busca ante un saludo.",
    status: "done",
    metrics: [],
    evidence: [
      { label: "Memoria, enrutador y agente", href: `${repo}/specs/014-rag-agent-memory-router/spec.md`, kind: "spec" },
      { label: "ADR del agente", href: `${repo}/docs/decisions/0016-rag-agent-langgraph.md`, kind: "adr" },
      { label: "Rúbrica del Módulo 2", href: `${repo}/docs/rubrica_modulo2.md`, kind: "report" },
    ],
  },
  {
    id: "safety",
    order: 8,
    title: "Leer solo, escribir con permiso",
    body:
      "El texto recuperado va delimitado como dato pasivo: si un documento dice «ignora las instrucciones», se marca y no se obedece. Guardar el perfil o una preferencia, olvidar la memoria o exportar una conversación espera la aprobación de una persona.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Política de memoria", href: `${repo}/docs/memoria.md`, kind: "report" }],
  },
  {
    id: "app",
    order: 9,
    title: "Una interfaz propia, en streaming",
    body:
      "React desacoplado de FastAPI: la respuesta llega en streaming (SSE), los hilos se retoman tras reiniciar, cada turno muestra ruta, fragmentos, fuentes, tokens y latencia, y los errores de red o del modelo se explican sin romper la página.",
    status: "done",
    metrics: [],
    evidence: [{ label: "Frontend", href: `${repo}/specs/012-manuelita-rag-showcase/spec.md`, kind: "spec" }],
  },
  {
    id: "metrics",
    order: 10,
    title: "Medir antes de afirmar",
    body:
      "Las cifras del corpus provienen de reportes reales. En el Módulo 2, cadena y agente citan bien el 100 % de las veces y la cadena responde en menos de 10 s. Cada turno queda trazado en LangSmith o en un log JSON con ruta, herramientas y tokens.",
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
      "Del Módulo 1 falta la evaluación real de 40 preguntas. Del Módulo 2 quedan la calificación humana de las repreguntas, Qdrant con servidor dedicado, el gatekeeper Jev y el despliegue. El sistema declara sus vacíos y no sustituye la información oficial.",
    status: "pending",
    metrics: [],
    evidence: [{ label: "Limitaciones", href: `${repo}/README.md`, kind: "report" }],
  },
];
