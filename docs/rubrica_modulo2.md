# Rúbrica de sustentación del Módulo 2: cumplimiento y guion

**Fecha**: 2026-11-14 (revisado tras la evaluación docente) | **Autor**: Roberto José Guerrero |
**Sustentación**: sábado 14 de noviembre de 2026, 8:00 a.m.

**Fuente**: Anuncio 006 del curso (`data/module2/Rubrica_de_Sustentacion_del_Modulo_2.md`, fuera de Git).
**Decisión de diseño**: [ADR 0018](decisions/0018-qdrant-y-rubrica-modulo2.md). **Evaluación docente**:
`evaluación/evaluacion_modulo2_docente.md` (2026-11-13, sobre `f571aa9`).

Este es el **único guion de la demo**: `docs/demo.md` remite aquí.

## 1. Cumplimiento de los 13 ítems

Autoevaluación corregida tras la revisión docente: donde queda un hueco se dice y no se marca como cumplido.

| Ítem | Peso | Estado | Evidencia en el código y en la app |
|------|-----:|:------:|-----------------------------------|
| 1.1 Corto plazo: checkpointer y `thread_id` | 10 % | ✅ | `SqliteSaver` en `$MANUELITA_STATE_DIR/checkpoints.sqlite3` (`agent/memory.py`). Cada hilo tiene su UUID y ahora vive en la URL (`#/chat/<uuid>`): sobrevive a recargas y al reinicio de la API (`test_hitl.py`, `test_profile_memory.py`). |
| 1.2 Contexto multi-turno | 8 % | ✅ | `trim_messages` recorta por tokens **en las dos variantes**; resumen persistente con tope (¼ de la ventana); `SummarizationMiddleware` dentro del agente. Prueba de 50 turnos largos: el prompt queda dentro de la ventana (`tests/unit/agent/test_long_context.py`). |
| 1.3 Largo plazo: Store y namespace | 7 % | ✅ | `SqliteStore` con `("users", id, "profile")` y `("users", id, "preferences")`. El perfil se extrae con regex («me llamo», «soy Ana», «laboro en», «mi empresa es», «resido en»…) y, si no alcanza, con el LLM y JSON validado por Pydantic (`prompts/profile_extract.md`). Se escribe con aprobación humana y se lee en otro hilo. 🟡 `store.search()` lista el namespace; no hay búsqueda semántica en el Store. |
| 2.1 Herramienta determinista con `@tool` | 8 % | ✅ | **CSV curado y versionado** `data/curated/series_anuales.csv`: 74 cifras anuales de los informes de sostenibilidad (ventas, EBITDA, utilidad, patrimonio, caña, azúcar, bioetanol, biodiésel, aceite de palma, camarón, mejillón, inversión social), cada una con `unit_id`, URL y página; una prueba verifica cada valor contra su unidad de oro. `@tool aggregate_series` (`AggregateArgs` Pydantic) suma, promedia, halla máximo/mínimo y variación con `Decimal`; pruebas de valor exacto (`test_series.py`). Además `query_structured` sobre la tabla SQLite del oro (conteos). El modo demo también llama las herramientas. |
| 2.2 RAG con Qdrant e índice ANN | 8 % | 🟡 | Colección `manuelita_fragments` (coseno, HNSW `m=16`, `ef_construct=128`), filtro por *payload* en una etapa, híbrida densa + BM25 y cita `[U#]` validada. El modo local embebido busca de forma **exacta**; el HNSW real requiere el servidor (`docker-compose.yml`, `make qdrant-up`, `QDRANT_URL`), aún sin probar en vivo. El respaldo numpy ya **no es silencioso**: se registra y la UI muestra «⚠ Respaldo numpy». `rag qdrant status` muestra `hnsw_ef` y la latencia. |
| 2.3 Router Agent | 10 % | ✅ | Reglas (0 llamadas) + LLM con JSON validado. Rutas: directa, documental, estructurada, **mixta**, fuera de alcance y aclaración. Evaluación real 2026-11-14: **43/44 (97,7 %)**, mixed 5/5, 10/10 sin búsqueda. La ruta se pasa al agente como pista de herramientas. Prueba: la respuesta mixta cita al menos un `[F#]` y un `[U#]` en ambas variantes (`test_series_routes.py`). |
| 2.4 Blindaje del RAG | 4 % | ✅ | `<documento>` con escape; detector de 6 patrones; la **oración inyectada se neutraliza** antes del modelo y la traza lo registra. Con DeepSeek (`docs/evaluacion_blindaje.md`): 6/6 marcados y neutralizados, 0 obedecen, 0 filtran el prompt, 6/6 citan la evidencia legítima. El corpus adversarial funciona también en modo real. |
| 3.1 Frontend propio | 10 % | ✅ | React + Vite + TypeScript desacoplado de FastAPI; streaming SSE; hilo en la URL; **cancelación** («Detener generación») y tiempo límite de 90 s con `AbortController`; la caída a `/api/chat` solo ante un 404 sin cuerpo; recientes, aprobación, atajos de los casos y traza por turno. 🟡 Enrutamiento por *hash* sin `react-router`; la lista de recientes vive en `localStorage`. |
| 3.2 Código y gobernanza | 10 % | 🟡 | `uv`, Ruff, CI (`test`, `web`, `autoria`), Conventional Commits, LICENSE MIT; endpoints con tipo de retorno y `response_model`. **Revisión de PRs insuficiente**: de 60 PRs fusionados (51 del equipo), solo 12 tienen aprobación formal y 16 alguna revisión; `main` exige checks pero no aprobación. Pendiente: exigir 1 aprobación y revisiones con comentarios. |
| 4.1 Diagramas de arquitectura | 8 % | ✅ | README: pipeline, grafo LangGraph con el bucle del agente y el punto HITL, checkpointer vs. Store, herramientas y router, trazas. Archify regenerado con Qdrant (PR #62). 🟡 Sin capturas de trazas reales de LangSmith (falta la clave). |
| 4.2 Diseño y evaluación del retrieval | 7 % | ✅ | 40 preguntas (35 puntuables) con Recall@1/3/5/10, nDCG@10 y MRR en tres modos, **reevaluadas sobre Qdrant** (2026-11-14) y barrido de top-k × α (`docs/barrido_retrieval.json`). 44 consultas etiquetadas por ruta, 18 con etiqueta de recuperación. 🟡 Revisión cruzada de etiquetas (T018) pendiente; fidelidad del juez no válida y marcada como tal. |
| 5.1 Los cuatro casos en vivo | 6 % | 🟡 | Sección 2; falta el ensayo cronometrado del equipo. |
| 5.2 Dominio individual | 4 % | 🟡 | Sección 5. |

## 2. Los casos de la demo

Todos se pueden mostrar en **modo real** (DeepSeek) y en **modo demo** (sin red) con la variante cadena.

| Caso | Mensaje en «Conversación» | Qué se ve |
|------|---------------------------|-----------|
| 1. RAG documental | «¿Qué dice el corpus sobre la política de calidad?» | Ruta Documentos; fragmentos con puntaje semántico y léxico; respuesta citada [U#]. El chip superior dice si la búsqueda va por Qdrant o por el respaldo numpy. |
| 1b. Sin evidencia | «¿Cuál es el número de celular del gerente de Manuelita?» | Fuera de alcance, sin buscar. No inventa. |
| 2. Memoria | «Soy Ana y laboro en Carvajal» → Aprobar → **Nueva conversación** → «¿Dónde trabajo?» | La tarjeta pide aprobar `save_profile` (la escritura exige consentimiento: regla «lectura automática, escritura con aprobación»). En el hilo nuevo responde desde el Store con 0 búsquedas; el saludo dice «¡Hola, Ana!». |
| 2b. Reinicio | Detener la API, `make app` y recargar | La URL conserva `#/chat/<uuid>`: el hilo reaparece desde el checkpointer SQLite. |
| 3. Datos estructurados | «¿Cuánto vendió Manuelita en total entre 2019 y 2022?» y «¿Cuál fue el año de mayor EBITDA?» | Ruta Datos estructurados: «7.476.475 millones de COP» y «720.297 millones en 2022» [F1], calculados por `aggregate_series` con la fuente (informe 2021-2022, p. 6). |
| 3b. Límite honesto | «¿Cuántas toneladas de azúcar se produjeron en el tercer trimestre de 2022?» | «Los informes no publican cifras trimestrales…; dato anual 2022: 395.663 toneladas» [F1]. |
| 4. Enrutamiento mixto | «Compara el crecimiento de la producción de biodiésel con lo que dice el informe sobre sostenibilidad» | Ruta mixta: variación 2017–2022 (+26,7 millones de litros, +25,85 %) [F1] y contexto del informe [U#] en la misma respuesta. |
| 4b. Sin quemar búsquedas | «Hola, buenas tardes» y «¿Cuál es el precio del dólar hoy?» | Directa y fuera de alcance por reglas: 0 llamadas y 0 búsquedas. |
| 5. Blindaje | Reiniciar la API con `MANUELITA_DEMO_CORPUS=malicious` (modo real o demo) y preguntar «¿Qué produce Manuelita?» | El fragmento aparece marcado y con «oración neutralizada»; la respuesta no obedece. Evidencia con DeepSeek en `docs/evaluacion_blindaje.md`. |

## 3. Mapa técnico: dónde está cada API

| Capa | Dónde mostrarla |
|------|-----------------|
| `create_agent` con modelo, tools y middleware | `agent/graph.py::_agent_node`: HITL, PII, resumen, límites y `@dynamic_prompt` con la pista de ruta. |
| `ChatPromptTemplate` y `RunnablePassthrough` | `agent/graph.py::build_answer_chain`. |
| `StateGraph`, nodos, aristas y estado | `build_chain_graph` (`route → retrieve → answer → finalize`) y `build_agent_graph`. |
| Checkpointer + Store | `agent/memory.py` (`SqliteSaver`, `SqliteStore`, `UserProfile`, `UserMemory`). |
| `trim_messages` y resumen | `recent_within_budget`, `_agent_messages`, `cap_summary`, `build_summarization_middleware`. |
| `@tool`, docstring y esquema | `agent/tools.py` (`aggregate_series`, `query_structured`, `search_documents`) y `agent/series.py` (`AggregateArgs`). |
| Salida estructurada con Pydantic | `RouteDecision` (enrutador) y `ProfileFacts` (perfil). |
| Qdrant | `rag/vectorstore.py`; `rag qdrant status` (puntos, HNSW, `hnsw_ef`, latencia); `docker-compose.yml`. |
| Embeddings y búsqueda híbrida | `rag/embeddings.py` (e5-small, 384 d) y `rag/hybrid.py` (α = 0,65; barrido en `docs/barrido_retrieval.json`). |
| Trazas | `agent/observability.py` y `GET /api/observability?mode=` (LangSmith, `turns.jsonl` y búsqueda vectorial). |
| Frontend y API | `ChatView.tsx` (streaming, cancelación, URL) y `api.py`. |

## 4. Checklist del anuncio

| Obligatorio | Estado |
|-------------|:------:|
| LICENSE MIT y README actualizado al M2 | ✅ |
| `uv sync`; frontend y backend desacoplados; sin Streamlit ni Gradio | ✅ |
| Interfaz responsive, streaming y manejo de errores de red/API (con cancelación y tiempo límite) | ✅ |
| Corto plazo con checkpointer, `thread_id` y persistencia real | ✅ |
| Largo plazo con Store y namespace | ✅ |
| Herramienta determinista CSV/JSON con `@tool` y Pydantic | ✅ CSV curado + agregaciones |
| RAG sobre Qdrant con top-k y cita | 🟡 local exacto; servidor HNSW preparado sin probar en vivo |
| Router: estructurada, RAG o directa (más mixta) | ✅ |
| Trazas en LangSmith o logs equivalentes | ✅ `turns.jsonl`; 🟡 LangSmith requiere la clave |
| Alrededor de 40 PRs fusionados con revisión | ❌ 12 aprobados de 51 PRs del equipo |
| Conventional Commits y `.env` fuera del repo | ✅ |
| Diagrama de arquitectura y evaluación del retrieval | ✅ |

**Deseables cubiertos**: híbrida y Recall@10/nDCG@10 (también sobre Qdrant); blindaje con evidencia del modelo
real; pruebas automáticas del router y las herramientas; RAG Chain vs. RAG Agent; `specs/`; Playwright. **No
cubiertos**: Jev (System One), time travel, datasets de LangSmith, despliegue y LLM Wiki/OKF.

## 5. Guion de 12 minutos

**Antes de las 8:00** (en este orden, en el equipo de la demo):

```bash
git pull && uv sync && git lfs pull
make demo-prep        # índice (verify o rebuild), colección Qdrant, tabla estructurada y status
make app              # API + web en http://127.0.0.1:8000
```

Precalentar con una consulta real (la primera carga los embeddings, ~15 s). Si hay clave de LangSmith, ponerla
en `.env` y abrir el proyecto en otra pestaña. **Plan B**: el interruptor «modo demo» de la app (sin red).

| Minuto | Bloque | Quién | Qué hacer |
|--------|--------|-------|-----------|
| 0:00–1:00 | Contexto y arquitectura | Jason | Problema y diagramas del README: React → FastAPI → LangGraph → Qdrant + CSV curado + tabla SQLite; checkpointer y Store. |
| 1:00–3:30 | Memoria | Roberto | Caso 2 y 2b (URL con el hilo, reinicio). Explicar por qué la escritura pide aprobación. |
| 3:30–5:30 | RAG documental | Jason | Casos 1 y 1b; chip de Qdrant; fragmentos con puntaje; Recall@10/nDCG@10 sobre Qdrant y el barrido. |
| 5:30–8:00 | Estructurado y router | Roberto | Casos 3, 3b y 4; chip de ruta, confianza y «decidió». Caso 4b. |
| 8:00–9:30 | Blindaje | Jason | Caso 5 y `docs/evaluacion_blindaje.md`. |
| 9:30–11:00 | Código y repositorio | Ambos | `series.py` + `aggregate_series`, `build_chain_graph`, `ChatView.tsx` (streaming y cancelación), PRs y commits. |
| 11:00–12:00 | Cierre | Roberto | Qué funciona, qué falta (HNSW con servidor, LangSmith, revisión de PRs, Jev) y aprendizaje. |

Cada integrante debe poder explicar sin leer: el grafo, checkpointer frente a Store, el router, el blindaje, la
API SSE y por qué el híbrido no supera al semántico (las preguntas son paráfrasis; el BM25 aporta en nombres
propios y cifras pero suma ~0,9 s).

## 6. Riesgos conocidos

- **Qdrant local** busca de forma exacta y admite una sola instancia por carpeta: con la API abierta, la CLI
  no puede abrir la colección. Usar la CLI antes de `make app`.
- **Latencia**: precalentar; la variante agente es más lenta (p95 14,7 s), por eso la demo usa la cadena.
- **Variante agente y escritura**: en el agente, `save_profile` depende de que el modelo llame la herramienta;
  hacer el caso 2 en la cadena.
