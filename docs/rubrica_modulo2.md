# Rúbrica de sustentación del Módulo 2: cumplimiento y guion

**Fecha**: 2026-11-13 | **Autor**: Roberto José Guerrero | **Sustentación**: sábado 14 de noviembre de 2026,
8:00 a.m.

**Fuente**: Anuncio 006 del curso (`data/module2/Rubrica_de_Sustentacion_del_Modulo_2.md`, fuera de Git).
**Decisión de diseño**: [ADR 0018](decisions/0018-qdrant-y-rubrica-modulo2.md).

## 1. Cumplimiento de los 13 ítems

| Ítem | Peso | Estado | Evidencia en el código y en la app |
|------|-----:|:------:|-----------------------------------|
| 1.1 Corto plazo: checkpointer y `thread_id` | 10 % | ✅ | `SqliteSaver` en `$MANUELITA_STATE_DIR/checkpoints.sqlite3` (`agent/memory.py`). Cada hilo tiene su UUID. Al reiniciar la API y recargar la página, el hilo continúa (`tests/integration/agent/test_hitl.py`, `test_profile_memory.py`). |
| 1.2 Contexto multi-turno | 8 % | ✅ | Tres mecanismos: `compact_history` resume pasados 6.000 tokens y conserva los últimos 6 mensajes; `SummarizationMiddleware` resume dentro del agente; `trim_messages` (estrategia `last`) recorta el historial del agente (`agent/graph.py`). |
| 1.3 Largo plazo: Store y namespace | 7 % | ✅ | `SqliteStore` con namespaces `("users", id, "profile")` y `("users", id, "preferences")`. Se escribe con `save_profile`/`save_preference` previa aprobación humana y se lee con `store.search()` en otro hilo. |
| 2.1 Herramienta determinista con `@tool` | 8 % | ✅ | `query_structured` es un `@tool` con `args_schema` Pydantic sobre la tabla SQLite derivada del oro (381 hechos, cita por fila), exportada a `facts.csv` y `entities.json`. La herramienta cuenta y el modelo solo cita (`count_fact`). |
| 2.2 RAG con Qdrant e índice ANN | 8 % | ✅ | Colección `manuelita_fragments` en Qdrant (coseno, HNSW `m=16`), top-k con filtro por *payload* en una etapa. Recuperación híbrida densa + BM25 y cita `[U#]` validada (`rag/vectorstore.py`, `rag/hybrid.py`). |
| 2.3 Router Agent | 10 % | ✅ | Reglas (0 llamadas al modelo) más LLM con salida JSON validada por Pydantic. Rutas: directa, documental, estructurada, mixta, fuera de alcance y aclaración. Los saludos no buscan (`tool_calls = 0`). Acierto: 35/36 (97 %). |
| 2.4 Blindaje del RAG | 4 % | ✅ | El contexto va delimitado como `<documento>` de datos pasivos. Las instrucciones embebidas se marcan como `anomalous` y se avisan en la interfaz; se descartan las respuestas que copian el prompt (`agent/guard.py`, `tests/integration/agent/test_injection.py`). |
| 3.1 Frontend propio | 10 % | ✅ | React + Vite + TypeScript desacoplado de FastAPI. Streaming SSE (`/api/chat/stream`), hilos y sesiones, errores controlados, tarjeta de aprobación y traza por turno (ruta, fragmentos, fuentes y métricas). |
| 3.2 Código y gobernanza | 10 % | ✅ | `uv`, Ruff, type hints y docstrings; API tipada con Pydantic. 54 PRs fusionados con revisión al 2026-11-13, Conventional Commits, CI (`test`, `web`, `autoria`) y LICENSE MIT. |
| 4.1 Diagramas de arquitectura | 8 % | ✅ | README, sección «Agente del Módulo 2»: grafo del agente, checkpointer vs. Store, herramientas y router, y trazas. Además `docs/arquitectura.html`. |
| 4.2 Diseño y evaluación del retrieval | 7 % | ✅ | 36 consultas etiquetadas; Recall@10, nDCG@10 y MRR (léxico, semántico e híbrido); juez con definiciones de Ragas (`docs/evaluacion_modulo2.md`). |
| 5.1 Los cuatro casos en vivo | 6 % | 🟡 | Los cinco casos de la sección 2 se verificaron con DeepSeek el 2026-11-13; falta el ensayo completo del equipo. |
| 5.2 Dominio individual | 4 % | 🟡 | Cada integrante debe poder explicar su parte (sección 5). |

## 2. Los cinco casos (verificados con DeepSeek, variante cadena)

| Caso | Mensaje en la pestaña «Conversación» | Qué se ve en pantalla |
|------|--------------------------------------|-----------------------|
| 1. RAG documental | «¿Qué dice el corpus sobre la política de calidad?» | Ruta Documentos (LLM, 90 %). Fragmentos de Qdrant con puntaje semántico y léxico, y respuesta citada: la Política de Calidad de Agroindustrial Laredo [U7]. |
| 1b. Sin evidencia | «¿Cuál es el número de celular del gerente de Manuelita?» | Ruta Fuera de alcance, sin buscar. No inventa. |
| 2. Memoria | «Me llamo Ana y trabajo en Carvajal» → Aprobar → «¿Dónde trabajo?» → **Nueva conversación** → «¿Dónde trabajo?» | La tarjeta pide aprobar `save_profile`. El perfil aparece arriba como memoria de largo plazo. En el hilo nuevo responde «Según tu perfil guardado (memoria de largo plazo): … Carvajal» con 0 búsquedas, y el saludo dice «¡Hola, Ana!». |
| 2b. Reinicio | Detener la API (`Ctrl+C`), volver a `make app` y recargar la página | El hilo reaparece con sus turnos: el checkpointer SQLite sobrevive al proceso. |
| 3. Datos estructurados | «¿Cuántas filiales tiene Manuelita?» y «¿En qué año inició operaciones Manuelita en Perú?» | Ruta Datos estructurados. «6 filiales: Agroindustrial Laredo, …» [F1], conteo hecho por la herramienta; «en 2007» [F1] con la fila visible. |
| 4. Enrutamiento mixto | «Compara la meta de sostenibilidad del informe con cuántas toneladas de caña procesa Manuelita» | Ruta Documentos + datos: filas [F#] y fragmentos [U#] en la misma respuesta (meta del informe frente a 10.000 t/día y 2,9 millones de t/año). |
| 4b. Sin quemar búsquedas | «Hola, buenas tardes» y «¿Cuál es el precio del dólar hoy?» | Ruta Directa y Fuera de alcance por reglas: 0 llamadas al modelo y 0 búsquedas. |
| 5. Blindaje | Reiniciar la API con `MANUELITA_DEMO_CORPUS=malicious`, pasar la app a **modo demo** y preguntar «¿Qué produce Manuelita?». En la terminal: `uv run pytest -q tests/integration/agent/test_injection.py` | El fragmento con «ignora las instrucciones anteriores» aparece marcado («se trató como dato y no se obedeció») y la respuesta no lo sigue. La prueba repite lo mismo con un modelo que intenta revelar el prompt. |

**Variante agente**: los mismos casos pasan (2026-11-13), y además personaliza con el perfil («Ana, encontré
la meta…»). Es más lenta (p95 14,7 s y hasta 22 s en el caso 1), por eso **la demo usa la cadena** y muestra
el agente en el caso 4.

## 3. Mapa técnico: dónde está cada API

| Capa | Dónde mostrarla |
|------|-----------------|
| `create_agent` con modelo, tools y middleware | `agent/graph.py::_agent_node`: HITL, PII, resumen, límites de llamadas y `@dynamic_prompt`. |
| `ChatPromptTemplate` y `RunnablePassthrough` | `agent/graph.py::build_answer_chain` (cadena LCEL de la variante cadena). |
| `StateGraph`, nodos, aristas y estado | `build_chain_graph` (`route → retrieve → answer → finalize`) y `build_agent_graph`. |
| Checkpointer + Store | `agent/memory.py` (`SqliteSaver`, `SqliteStore`, `UserProfile`, `UserMemory`). |
| `trim_messages` y `SummarizationMiddleware` | `_agent_messages` y `build_summarization_middleware`. |
| `@tool`, docstring y esquema | `agent/tools.py` (`SearchDocumentsArgs`, `QueryStructuredArgs`) y `agent/actions.py` (herramientas de escritura). |
| Salida estructurada con Pydantic | `RouteDecision` (enrutador): JSON validado con Pydantic; DeepSeek y los modelos de prueba no soportan *tool calling* fiable para esto (ADR 0016). |
| Qdrant: colección, payload, filtros y HNSW | `rag/vectorstore.py`; `rag qdrant status` muestra puntos, dimensión y HNSW. |
| Embeddings y búsqueda híbrida | `rag/embeddings.py` (e5-small, 384 d, coseno) y `rag/hybrid.py` (0,65 denso + 0,35 léxico). |
| LangSmith | `agent/observability.py`: `run_name`, etiquetas y metadatos por turno; `GET /api/observability`. |
| Frontend y API | `web/src/components/ChatView.tsx` (streaming, sesiones, errores) y `api.py` (`/api/chat`, `/api/chat/stream`, `/api/threads/{id}`, `/resume`, `/api/memory/{user}`). |
| RAG Chain vs. RAG Agent | `docs/evaluacion_modulo2.md` y ADR 0016: la cadena es la variante por defecto, más rápida y barata. |

## 4. Checklist del anuncio

| Obligatorio | Estado |
|-------------|:------:|
| LICENSE MIT y README actualizado al M2 | ✅ |
| `uv sync`; frontend y backend desacoplados; sin Streamlit ni Gradio | ✅ |
| Interfaz responsive, streaming y manejo de errores de red/API | ✅ |
| Corto plazo con checkpointer, `thread_id` y persistencia real (`SqliteSaver`) | ✅ |
| Largo plazo con Store y namespace | ✅ |
| Herramienta determinista con `@tool` y esquema Pydantic | ✅ |
| RAG sobre Qdrant con top-k y cita | ✅ |
| Router: estructurada, RAG o directa | ✅ |
| Trazas en LangSmith o logs estructurados equivalentes | ✅ `turns.jsonl`; 🟡 LangSmith requiere poner la clave en `.env` |
| Alrededor de 40 PRs fusionados con revisión | ✅ |
| Conventional Commits y `.env` fuera del repo | ✅ |
| Diagrama de arquitectura y evaluación del retrieval | ✅ |

**Deseables cubiertos**: búsqueda híbrida y Recall@10/nDCG@10 con 36 consultas; blindaje contra inyección;
pruebas automáticas del router y de las herramientas; RAG Chain vs. RAG Agent documentado; especificaciones
versionadas (`specs/`); tests de UI con Playwright. **No cubiertos**: Jev (System One), time travel, despliegue
y LLM Wiki/OKF.

## 5. Guion de 15 minutos

**Antes de las 8:00**: `make app` abierto en el navegador (pestaña «Conversación», variante Cadena, modo
real), el repositorio en otra pestaña y el IDE en `agent/graph.py`. Una terminal con la API para mostrar
`turns.jsonl`.

| Minuto | Bloque | Quién | Qué hacer |
|--------|--------|-------|-----------|
| 0:00–1:30 | Contexto y arquitectura | Jason | Manuelita y el problema; diagrama del agente en el README: React → FastAPI → LangGraph (router, cadena/agente) → Qdrant + tabla SQLite; checkpointer y Store; LangSmith o `turns.jsonl`. |
| 1:30–4:00 | Memoria | Roberto | Caso 2 completo, incluido el reinicio de la API (2b). |
| 4:00–6:30 | RAG documental | Jason | Caso 1 y 1b; abrir los fragmentos con puntaje. Mostrar Recall@10/nDCG@10 en `docs/evaluacion_modulo2.md`. |
| 6:30–8:30 | Estructurado y router | Roberto | Caso 3 (conteo y año) y caso 4 (mixto); señalar el chip de ruta, la confianza y el motivo. Caso 4b: un saludo sin búsquedas. |
| 8:30–10:00 | Blindaje | Jason | Caso 5: prueba adversarial y explicación de `<documento>` como dato. |
| 10:00–11:30 | Repositorio y código | Ambos | PRs, commits y README. En el IDE: `ChatView.tsx` (streaming), `POST /api/chat/stream`, `build_chain_graph` y la decisión «escritura con aprobación». |
| 11:30–12:00 | Cierre | Roberto | Funciona: los cinco casos. Falta: Jev, despliegue y calificación humana de repreguntas. Aprendizaje: el router ahorra llamadas. |

## 6. Prueba de 3 minutos (viernes en la noche)

```bash
uv sync
git lfs pull
uv run python -m proyecto_modelos_lenguaje.rag qdrant status        # «lista»; si no: rag qdrant build
uv run python -m proyecto_modelos_lenguaje.agent build-structured --force
make app                                                              # API + web en http://127.0.0.1:8000
# En la app: los casos 1 a 4, reiniciar la API y recuperar el hilo
uv run pytest -q tests/integration/agent/test_injection.py           # caso 5
git log --oneline --graph -20
git status
```

Para trazas en LangSmith, añadir a `.env` `LANGSMITH_TRACING=true`, `LANGSMITH_API_KEY=…` y
`LANGSMITH_PROJECT=manuelita-modulo2`, reiniciar la API y confirmar con `GET /api/observability`.

## 7. Riesgos conocidos

- **Qdrant en modo local** busca de forma exacta (15.211 puntos, unos 0,4 s). Para mostrar HNSW real hay que
  levantar el servidor (`QDRANT_URL`); la colección y el código son los mismos.
- **Una sola instancia del modo local**: con la API abierta, la CLI no puede abrir la colección y vuelve a
  `numpy` (lo anota). En la demo, consultar Qdrant desde la app y usar la CLI antes de abrirla.
- **Latencia**: la primera consulta real carga el modelo de embeddings (unos 15 s). Hacer una consulta de
  calentamiento antes de entrar.
- **Variante agente y escritura**: en el agente, `save_profile` depende de que el modelo llame la
  herramienta; en la cadena la interrupción es determinista. Hacer el caso 2 en la cadena.
