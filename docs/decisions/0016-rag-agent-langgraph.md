# ADR 0016 — Agente RAG con LangGraph: memoria, enrutador, herramientas tipadas y HITL

- **Estado**: aceptada (implementada en los PR #44, #45, #47, #48, #49 y #50 de la spec 014)
- **Fecha**: 2026-11-11
- **Autor**: Roberto José Guerrero
- **Contexto**: spec `specs/014-rag-agent-memory-router/` (Fase 2 de la constitución); ADR 0014 (RAG
  semántico) y ADR 0015 (alcance del Módulo 2)

## Contexto

La Fase 2 exige un asistente con memoria multi-turno, enrutamiento documental vs. estructurado, blindaje contra
inyección indirecta y aprobación humana de escrituras, comparado en dos variantes (RAG Chain vs. RAG Agent). El
Módulo 1 ya tenía tareas LangChain con citas `[U#]` y fallo de evidencia; la spec 013 dejó el índice semántico e
híbrido. Faltaba decidir el marco de orquestación, dónde vive el estado, cómo se decide la ruta, cómo se consulta
el origen estructurado y cómo se detiene una escritura.

## Decisión

1. **Orquestación con LangGraph.** Dos grafos sobre el mismo estado de hilo (`agent/graph.py`):
   - *Cadena*: `route → retrieve → answer → finalize`, una búsqueda fija (k = 8) y una respuesta con
     reintento si faltan citas.
   - *Agente*: `route → agent → finalize`, donde `agent` es `langchain.agents.create_agent` con
     `ToolCallLimitMiddleware(3)`, `ModelCallLimitMiddleware(5)`, `SummarizationMiddleware`,
     `PIIMiddleware` y `HumanInTheLoopMiddleware`.

   El checkpointer vive en el grafo exterior; el agente corre como subgrafo y lo hereda. Así ambas variantes
   comparten la forma del turno y se comparan con la misma entrada.
2. **Estado fuera del repositorio.** `SqliteSaver` (`checkpoints.sqlite3`) para hilos y `SqliteStore`
   (`memory.sqlite3`) para preferencias, en `MANUELITA_STATE_DIR` (por defecto `%LOCALAPPDATA%\manuelita-rag`).
   `resolve_state_dir` rechaza rutas dentro del repositorio.
3. **Enrutador en dos etapas.** Reglas deterministas para saludos y temas ajenos (0 llamadas al modelo) y, si
   no deciden, DeepSeek a temperatura 0 con `prompts/router.md`, que responde JSON validado contra
   `RouteDecision`. Con confianza < 0,6 la ruta efectiva es `clarify`. Los pedidos de escritura se detectan con
   reglas antes del enrutador.
4. **Herramientas tipadas en lugar de text-to-SQL.** El origen estructurado es una tabla SQLite de solo
   lectura derivada del oro (`agent build-structured`), abierta con `mode=ro` y `PRAGMA query_only=ON`. El
   modelo solo ve `query_structured(query, subject, attribute, entity_type)`, que ejecuta consultas
   parametrizadas; nunca escribe SQL.
5. **Blindaje.** Todo fragmento o fila entra como `<documento id="U#|F#" fuente="…">` con `<`, `>` y `&`
   escapados; el system prompt lo declara dato. Un detector marca fragmentos con instrucciones embebidas
   (`anomalous`, `anomalies[]`) sin descartarlos, y `leaks_prompt` descarta respuestas que copian el prompt.
6. **Human-in-the-Loop.** `save_preference`, `forget_memory` y `export_conversation` se detienen antes de
   ejecutarse: `HumanInTheLoopMiddleware` en el agente, `interrupt()` con la misma forma de solicitud en la
   cadena. `POST /api/threads/{id}/resume` aplica `approve`, `edit` o `reject`; la decisión queda en `actions[]`
   y la pausa sobrevive al reinicio. Las herramientas de escritura toman el usuario y el hilo del servidor, no
   del modelo.

## Alternativas consideradas

| Alternativa | Por qué no |
|---|---|
| Solo `create_agent` con su propio checkpointer | Las dos variantes tendrían estados distintos y la comparación cadena vs. agente no sería con la misma entrada |
| `RunnableWithMessageHistory` o memoria manual en la API | No ofrece interrupciones persistentes ni reanudación tras reinicio |
| Text-to-SQL con el modelo | Riesgo de consultas arbitrarias e inyección; la tabla tiene pocas columnas y las consultas parametrizadas cubren el conjunto |
| Enrutador solo con LLM | Gasta una llamada en saludos y temas ajenos; las reglas resuelven 10/10 de esos casos sin modelo |
| `with_structured_output` para el enrutador | Los modelos guionados de las pruebas no soportan *tool calling*; JSON validado funciona igual con DeepSeek |
| Descartar fragmentos anómalos | Oculta evidencia y sesga la evaluación; se marcan y se reportan |
| Confirmación de escrituras solo en la interfaz | No queda registro en el estado del grafo ni sobrevive a un reinicio |
| Chroma o FAISS para el índice | Ya decidido en la ADR 0014: `numpy` + SQLite basta para 15.211 unidades y se reconstruye con un comando |

## Consecuencias

- Positivas: ambas variantes se miden con la misma entrada y métricas por turno; el modo demo es determinista y
  sin red; la app sigue sin escribir en `data/` ni en el repositorio.
- Negativas: el agente gasta más llamadas al modelo por turno que la cadena; la detección de pedidos de escritura
  por reglas solo cubre frases previstas (el agente con DeepSeek también llama las herramientas por su cuenta).
- Ragas no instala en Python 3.14; se usa un juez propio con sus definiciones (`agent/judge.py`,
  `prompts/judge.md`).

## Referencias

- `specs/014-rag-agent-memory-router/research.md` §1, §2, §6–§10
- `docs/memoria.md`, `docs/evaluacion_modulo2.md`, `docs/prompt_log.md` §3.6–§3.10
