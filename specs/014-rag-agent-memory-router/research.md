# Research: Agente RAG con memoria y enrutador

**Feature**: `014-rag-agent-memory-router` | **Fecha**: 2026-11-10 | **Autor**: Roberto José Guerrero

Cada decisión resuelve una incógnita del contexto técnico del [plan](./plan.md). Versiones verificadas en
`uv.lock` del 2026-11-10: `langchain` 1.4.9, `langgraph` 1.2.18, `langgraph-checkpoint` 4.3.1, `langsmith`
0.14.16. Middleware confirmado en `langchain.agents.middleware`: `HumanInTheLoopMiddleware`,
`SummarizationMiddleware`, `PIIMiddleware`, `ToolCallLimitMiddleware`, `ModelCallLimitMiddleware`.

## 1. Marco de orquestación del agente

- **Decision**: `langchain.agents.create_agent` (LangGraph por debajo) para la variante agente, y un grafo
  LangGraph explícito (`StateGraph`) de tres nodos para la variante cadena (`route → retrieve → answer`). Ambos
  comparten checkpointer, herramientas y prompts.
- **Rationale**: es la API que enseña la Clase 9 (`create_agent`, `@tool`, middleware HITL) y ya está en el
  lockfile como dependencia transitiva; acepta `checkpointer`, `store` y `middleware` en la misma firma, lo que
  hace comparables las dos variantes (FR-014).
- **Alternatives considered**: `AgentExecutor` clásico (obsoleto en LangChain 1.x); orquestación propia sin
  LangGraph (habría que reimplementar checkpointer e `interrupt()`); LlamaIndex (otra pila, rompe la
  continuidad con el Módulo 1).

## 2. Memoria corta, recorte y persistencia

- **Decision**: `SqliteSaver` de **`langgraph-checkpoint-sqlite`** con un archivo
  `checkpoints.sqlite3` en `MANUELITA_STATE_DIR`; `thread_id` = UUID4 generado por la API. Hilos largos:
  `SummarizationMiddleware` cuando el historial supera ~6.000 tokens, conservando los últimos 6 mensajes y las
  citas `[U#]` vigentes en el resumen (FR-008). En pruebas unitarias, `InMemorySaver`.
- **Rationale**: la Clase 6 exige checkpointer persistente con SQLite en local; sobrevive a reinicios (FR-007,
  US4-3). Guardarlo fuera del repo cumple la regla «la app no escribe en `data/` ni en el repositorio».
- **Alternatives considered**: `InMemorySaver` en producción (pierde el hilo al reiniciar); Postgres (servicio
  extra, pertenece a la Fase 3); guardar el historial en el navegador (no permite HITL con reanudación en
  servidor).

## 3. Memoria larga (P3)

- **Decision**: `BaseStore` respaldado por SQLite (`SqliteStore` del mismo paquete) con namespace
  `("users", user_id, "preferences")`; solo se guardan **preferencias declaradas** (formato de respuesta, temas
  de interés) extraídas por una herramienta explícita, nunca texto libre. TTL de 30 días; borrado por la
  herramienta `forget_memory`, que exige aprobación HITL. `PIIMiddleware` (correo, teléfono, documento, tarjeta)
  en modo `redact` antes de cualquier escritura (FR-010).
- **Rationale**: la Clase 6 distingue memoria de hilo y memoria entre hilos; acotar lo que se guarda simplifica
  la política de `docs/memoria.md`.
- **Alternatives considered**: guardar resúmenes completos de conversación (riesgo de datos sensibles); vector
  store de memorias (innecesario para < 10 preferencias por usuario).

## 4. Evidencia MTEB-es para el embedding (FR-004)

- **Decision**: mantener `intfloat/multilingual-e5-small` y ampliar la ADR 0014 con la tabla del leaderboard
  MTEB filtrada por *Retrieval* + *spa* (tareas como MIRACL-es, SpanishPassageRetrievalS2P, XPQA-es), comparando
  e5-small, e5-base, bge-m3 y paraphrase-multilingual-MiniLM en nDCG@10, tamaño y latencia. La tabla se obtiene
  del leaderboard en la fecha de redacción y se cita con URL y fecha.
- **Rationale**: la constitución exige evidencia de retrieval en español, no el promedio general. Cambiar de
  modelo obliga a reindexar; solo se cambiaría si la evaluación propia (SC-001) lo justifica.
- **Alternatives considered**: migrar ya a `bge-m3` (568 M parámetros, ~2 GB, latencia CPU muy superior; queda
  como configuración alternativa en la evaluación si el tiempo alcanza).

## 5. Chunking y búsqueda aproximada (F2-3)

- **Decision**: conservar las unidades de oro como fragmentos y trocear solo las que excedan 512 tokens con
  ventanas de ~400 tokens y **solapamiento de 60 (15 %)**; registrar `chunk_size`, `chunk_overlap` y la
  estrategia en `manifest.json` (FR-003). Búsqueda **exacta** (producto punto sobre 15.211 × 384), sin ANN.
- **Rationale**: con ~15 k vectores la búsqueda exacta tarda < 100 ms, así que no hay `ef_search` ni `nprobe` que
  calibrar; se documenta así en la arquitectura, como permite la regla 3 («calibrados con datos del proyecto»).
- **Alternatives considered**: FAISS HNSW o Chroma (agregan dependencia sin beneficio medible a esta escala).

## 6. Puerta de decisión (enrutador)

- **Decision**: enrutador en dos etapas.
  1. **Reglas deterministas** (0 llamadas): saludos, agradecimientos y despedidas → `direct`; patrones fuera de
     alcance (cotizaciones, clima, política, código) → `out_of_scope`.
  2. **Clasificador LLM con salida tipada** (`with_structured_output(RouteDecision)`, prompt
     `prompts/router.md`, temperatura 0) para el resto: `documental`, `structured`, `out_of_scope` o
     `clarify`, con `confidence` ∈ [0, 1] y `reason`.
  Con `confidence < 0,6` se fuerza `clarify` (FR-015). Si la ruta estructurada no devuelve filas, cae a
  documental y lo registra (`fallback_route`).
- **Rationale**: la revisión del PR #34 mostró que ningún umbral de similitud separa preguntas fuera de corpus
  (0,80–0,87) de válidas (≥ 0,84); la abstención debe venir de una decisión explícita. Las reglas eliminan
  llamadas en los casos triviales (SC-004) y hacen el modo demo determinista.
- **Alternatives considered**: solo similitud (descartado por los datos); solo LLM (más llamadas y latencia);
  Jev/System One (opcional según la Clase 9; se deja como extensión).

**Actualización 2026-11-10 (T034)**: la etapa 2 pide JSON y lo valida contra `RouteDecision` en lugar de
`with_structured_output`, que exige *tool calling* y no lo soportan los modelos guionados de la suite. Con
DeepSeek el enrutador acertó 35/36 rutas sin ninguna salida inválida.

## 7. Origen estructurado

- **Decision**: CLI `agent build-structured` que lee `data/gold/entities.jsonl` (15) y `data/gold/facts.jsonl`
  (381) y escribe `data/module2/structured/structured.sqlite3` con tres tablas (`entities`, `facts`,
  `citations`) y un `manifest.json` con el hash del oro. La consulta se expone como **herramientas tipadas y
  parametrizadas** (`list_entities(entity_type)`, `get_facts(subject, attribute)`), no SQL libre; conexión
  `file:...?mode=ro` + `PRAGMA query_only=ON`.
- **Rationale**: FR-012/013 piden solo lectura y cita por fila; las herramientas tipadas eliminan la superficie
  de inyección SQL y bastan para las preguntas tabulares del alcance (sedes, países, certificaciones, marcas,
  subsidiarias).
- **Alternatives considered**: text-to-SQL con `SQLDatabaseToolkit` (más flexible pero exige guardas de
  `SELECT`, más llamadas y riesgo); CSV con pandas (sin índices y añade dependencia).

## 8. Blindaje contra inyección indirecta

- **Decision**: cada fragmento o fila entra al prompt como
  `<documento id="U3" fuente="..."> ... </documento>` con escape de `<`/`>` del contenido; el system prompt
  declara que el contenido de `<documento>` es dato. Un detector heurístico (`guard.py`) marca fragmentos con
  patrones imperativos dirigidos al modelo («ignora las instrucciones», «revela tu prompt», «system:», etc.) como
  `anomalous=true`, los mantiene citables pero los reporta en la traza. Prueba adversarial con un índice de
  prueba que contiene un documento malicioso: la respuesta no debe contener el prompt del sistema ni seguir la
  orden (SC-005).
- **Rationale**: es el patrón del taller de la Clase 9; los prompts actuales ya usan `<context>`, así que se
  extiende sin romper el Módulo 1.
- **Alternatives considered**: descartar fragmentos anómalos (oculta evidencia y sesga la evaluación);
  clasificador LLM de inyección (más llamadas, no determinista en CI).

## 9. Human-in-the-Loop

- **Decision**: `HumanInTheLoopMiddleware(interrupt_on={"forget_memory": True, "save_preference": True,
  "export_conversation": True})` en la variante agente; en la cadena, `interrupt()` explícito antes de esas
  acciones. La API devuelve `status="pending_approval"` con la acción propuesta; `POST
  /api/threads/{id}/resume` envía `Command(resume={"decisions": [...]})` con `approve`, `edit` o `reject`. Las
  herramientas de lectura (`search_documents`, `query_structured`) nunca interrumpen.
- **Rationale**: regla de oro de la constitución: lectura automática, escritura con aprobación. El checkpointer
  SQLite permite reanudar tras reiniciar el servidor (US4-3, SC-009).
- **Alternatives considered**: confirmación solo en la UI (no queda registro en el estado del grafo).

## 10. Variantes Chain vs. Agent y su comparación

- **Decision**: misma entrada, mismo retriever, mismo prompt de respuesta. La cadena recupera siempre una vez
  (k = 8); el agente decide cuándo y cuántas veces buscar con `ToolCallLimitMiddleware(run_limit=3)` y
  `ModelCallLimitMiddleware(run_limit=5)`. Se registra por turno: latencia, número de llamadas al modelo, número
  de búsquedas, tokens y citas válidas.
- **Rationale**: FR-014 y la regla F2-8 piden comparar calidad, latencia y llamadas; los límites evitan bucles.
- **Alternatives considered**: comparar con modelos distintos (confunde la variable bajo estudio).

**Desviaciones al implementar (T042–T047, 2026-11-11)**:

- El checkpointer vive en un grafo exterior común a ambas variantes (`route → retrieve → answer → finalize` y
  `route → agent → finalize`); `create_agent` se invoca como subgrafo dentro del nodo `agent` y hereda ese
  checkpointer. Así las dos variantes comparten el estado del hilo (`turns`, `summary`) y la forma del turno.
- La memoria del hilo se resume en `finalize` con `prompts/memory_summary.md` (ambas variantes); dentro del
  agente, `SummarizationMiddleware` aplica la misma política a los mensajes de una ejecución.
- La repregunta elíptica se resuelve sin llamada extra al modelo: la consulta de búsqueda antepone la pregunta
  previa cuando el mensaje es corto o deíctico (`router.contextual_query`); el historial reciente va además en
  el prompt de respuesta.
- Saludos, fuera de alcance y aclaraciones responden con textos fijos (0 llamadas al modelo, 0 búsquedas).
- Toda respuesta sin una cita válida se reemplaza por la frase de fallo de evidencia (SC-003); la cadena
  reintenta una vez con el recordatorio de citas del Módulo 1.
- El modo demo usa `DemoChatModel`: pide una búsqueda y responde de forma extractiva con la primera oración de
  los documentos, sin red.

## 11. Evaluación ampliada

- **Decision**: extender `rag/evaluate.py` con `recall_at(10)`, `ndcg_at(10)` (relevancia binaria, log2), tasa de
  abstención en `type=out_of_corpus`, **calentamiento** (3 consultas descartadas) antes de medir latencia y p95
  correcto. Nuevo conjunto `tests/fixtures/rag/module2_queries.jsonl` de **30 consultas** reales con
  `expected_unit_ids`, `expected_route` y `type` (6 directas/saludo, 12 documentales, 6 estructuradas, 4 fuera de
  alcance, 2 ambiguas), más 6 pares de repregunta elíptica para SC-006. Nuevo subcomando `agent evaluate` que
  mide precisión del enrutador, chain vs. agent, fidelidad de citas y llamadas.
- **Rationale**: Clase 7 y FR-019/020; la corrección de p95 responde a la revisión del PR #34 (p95 < media).
- **Alternatives considered**: reutilizar solo las 40 preguntas de 013 (no tienen ruta esperada).

## 12. Ragas y LangSmith

- **Decision**: `ragas` en el grupo opcional `eval` (`uv sync --extra eval`) con `faithfulness`,
  `answer_relevancy` y `context_precision`, usando DeepSeek como juez vía `langchain-openai` y los embeddings
  locales; LangSmith solo si `LANGSMITH_TRACING=true`, con `hide_inputs`/`hide_outputs` desactivables y sin
  enviar claves. Los resultados se anexan a `docs/evaluacion_modulo2.md` con fecha y modelo juez.
- **Rationale**: regla F2-11; no deben romper la suite offline ni CI.
- **Alternatives considered**: DeepEval (otra API, menos alineada con la Clase 10); juez humano exclusivo
  (se mantiene para una muestra de 10 respuestas como control).

**Actualización 2026-11-10 (T002)**: Ragas no instala en el stack actual. `ragas` 0.4.3 depende de
`scikit-network`, que no publica wheel para Python 3.14 y falla al compilar; `ragas` 0.2.15 instala pero
importa `langchain_community.chat_models.vertexai`, eliminado en `langchain-community` reciente. Decisión
provisional: diferir el extra `eval` a T067 y, si sigue bloqueado, implementar fidelidad y relevancia como
juez LLM propio con las mismas definiciones de Ragas, documentando la desviación.

## 13. Interfaz y API

- **Decision**: cuatro endpoints nuevos (`POST /api/chat`, `GET /api/threads/{thread_id}`,
  `POST /api/threads/{thread_id}/resume`, `GET|DELETE /api/memory/{user_id}`) descritos en
  [contracts/chat-api.md](./contracts/chat-api.md); `/api/ask` se conserva para compatibilidad. Vista
  `ChatView` con turnos, chip de ruta y confianza, fragmentos con puntaje (reutiliza `RetrievedFragments`), fuentes
  y tarjeta de aprobación. El `thread_id` vive en `sessionStorage`; el `user_id` es un identificador anónimo
  local.
- **Rationale**: FR-018 y regla F2-12; reutilizar componentes de 013 reduce el trabajo de UI.
- **Alternatives considered**: streaming por SSE (deseable; se deja para la Fase 3 si complica las pruebas).
