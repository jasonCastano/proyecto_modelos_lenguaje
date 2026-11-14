# Evaluación docente del Módulo 2 — RAG Ingenio Manuelita

| Campo | Valor |
|-------|-------|
| Curso | Técnicas Avanzadas de IA aplicadas en Modelos de Lenguaje — Maestría en IA y Ciencia de Datos, UAO, 2026-2S |
| Equipo | Jason Alejandro Castaño (`jasonCastano`) · Roberto José Guerrero Criollo (`Robertto48`) |
| Repositorio | <https://github.com/jasonCastano/proyecto_modelos_lenguaje> · `main` en `f571aa9` |
| Referencia | Anuncio 006 — Rúbrica de Sustentación del Módulo 2 (13 ítems ponderados) |
| Fecha de la revisión | 2026-11-13, víspera de la sustentación |
| Alcance | Ítems 1.1–4.2 (90 %), verificados con el repositorio, la app y pruebas offline. Los ítems 5.1 y 5.2 (10 %) se califican en vivo; aquí solo se evalúa su preparación. |
| Método | Lectura de código, documentos e historial de GitHub; pruebas offline (`pytest`, `vitest`, `ruff`); ejecución del agente en `--mode demo`. No se modificó ningún archivo del proyecto. |

> **Nota sobre las fuentes.** `docs/rubrica_modulo2.md` es la autoevaluación del equipo. Se tomó como lista de
> afirmaciones por verificar, no como evidencia. En varios ítems (3.2, 4.1, 4.2) declara un cumplimiento mayor
> que el comprobado.

---

## 1. Resultado

**Nota parcial (ítems 1.1–4.2, 90 % del módulo): 3,77 de 4,50 posibles → equivalente a 4,18 / 5,0.**

| Ítem | Peso | Puntaje | Aporte |
|------|-----:|--------:|-------:|
| 1.1 Corto plazo: checkpointer y `thread_id` | 10 % | 5,0 | 0,500 |
| 1.2 Gestión del contexto multi-turno | 8 % | 4,5 | 0,360 |
| 1.3 Largo plazo: Store y namespace | 7 % | 4,7 | 0,329 |
| 2.1 Herramienta determinista CSV/JSON con `@tool` | 8 % | 3,5 | 0,280 |
| 2.2 RAG documental con Qdrant e índice ANN | 8 % | 3,8 | 0,304 |
| 2.3 Router Agent | 10 % | 4,2 | 0,420 |
| 2.4 Blindaje del RAG | 4 % | 4,3 | 0,172 |
| 3.1 Aplicación interactiva con frontend propio | 10 % | 4,5 | 0,450 |
| 3.2 Calidad del código y gobernanza | 10 % | 3,5 | 0,350 |
| 4.1 Diagramas de arquitectura | 8 % | 4,0 | 0,320 |
| 4.2 Diseño y evaluación del retrieval | 7 % | 4,0 | 0,280 |
| **Subtotal verificable** | **90 %** | — | **3,765** |
| 5.1 Los cuatro casos, en vivo | 6 % | en sustentación | — |
| 5.2 Dominio individual | 4 % | en sustentación | — |

**Proyección de la nota final según la sustentación:**

| Desempeño en 5.1 y 5.2 | Nota del Módulo 2 |
|------------------------|------------------:|
| 5,0 en ambos | 4,27 |
| 4,0 en ambos | 4,17 |
| 3,0 en ambos | 4,07 |

### Valoración general

Es un trabajo de ingeniería sólido y por encima del promedio:
- La memoria persistente es real: `SqliteSaver` y `SqliteStore`.
- El router es híbrido: reglas primero y LLM después, con confianza.
- El streaming SSE funciona de punta a punta y el contexto llega delimitado como datos.
- Hay más de 650 pruebas offline.

Las pérdidas de puntos no vienen de la arquitectura, sino de tres frentes:
1. **El caso de datos estructurados de la rúbrica no se puede responder.** La «tabla» son hechos extraídos automáticamente y ruidosos, sin series numéricas agregables.
2. **Lo que la demo va a mostrar no está construido en el repositorio.** Faltan la tabla estructurada y la colección Qdrant, y el Qdrant embebido hace búsqueda exacta, no ANN.
3. **La gobernanza está sobredeclarada.** Solo 11 de los 49 PRs humanos fusionados tienen aprobación, aunque la autoevaluación dice «54 PRs con revisión».

---

## 2. Evaluación por ítem

### 1.1 Corto plazo: checkpointer y `thread_id` — 5,0

**Evidencia**
- El checkpointer es `SqliteSaver` sobre `checkpoints.sqlite3` y se inicializa con `setup()` (`agent/memory.py:39-45`).
- El directorio de estado se toma de `MANUELITA_STATE_DIR` o `%LOCALAPPDATA%`, y se rechaza cualquier ruta dentro del repo (`agent/config.py:152-165`).
- El servicio de producción construye checkpointer y Store persistentes (`api.py:446-454`). `InMemorySaver` solo aparece en pruebas y en `evaluate --compare`.
- Cada hilo tiene un UUID y se invoca con `{"configurable": {"thread_id": …}}` (`agent/service.py:232, 360`).
- El frontend envía `thread_id` y retoma el hilo con `GET /api/threads/{id}` (`web/src/lib/chat.ts:27,95`, `ChatView.tsx:341-369`).
- Hay pruebas de reinicio (`tests/unit/agent/test_memory.py::test_sqlite_checkpointer_survives_a_restart`), de aislamiento entre hilos y de una interrupción HITL que sobrevive al reinicio (`test_hitl.py:29`).

**Mejora menor (no resta):** el hilo activo vive en `sessionStorage`, así que al cerrar la pestaña se pierde la referencia aunque el estado siga en SQLite. Se resuelve con la URL por conversación de 3.1.

### 1.2 Gestión del contexto multi-turno — 4,5

**Evidencia**
- La variante agente usa `trim_messages` con `count_tokens_approximately`, `strategy="last"` y `start_on="human"` (`graph.py:602-608`).
- Hay un resumen persistente cuando el historial supera 6000 tokens, que conserva los últimos 6 mensajes (`memory.py:85-131`, `config/agent.toml:14-15`).
- `SummarizationMiddleware` está conectado al `create_agent` (`memory.py:134-144`, `graph.py:669-671`).

**Corregir y mejorar**
1. Ninguna prueba demuestra que `trim_messages` actúe. Agregar una prueba de conversación larga (por ejemplo, 50 turnos con respuestas extensas) que verifique que los tokens del prompt quedan por debajo de la ventana configurada.
2. El resumen no tiene tope. En modo demo, `_demo_summary` (`memory.py:93-100`) solo agrega líneas y crece sin límite. Hay que re-resumir o truncar por tokens.
3. La variante cadena se limita a «resumen + últimos N turnos», sin recorte por tokens (`graph.py:514-525`). Hay que aplicar `trim_messages` también ahí.
4. `estimate_tokens` = `len/4` es una aproximación. Conviene documentarla o usar el tokenizador del modelo.

### 1.3 Largo plazo: Store y namespace — 4,7

**Evidencia**
- `SqliteStore` en `memory.sqlite3`, con perfil en `("users", user_id, "profile")` recuperado con `store.search` (`memory.py:48-56, 259-317`).
- Las preferencias tienen TTL de 30 días y redacción de PII (`memory.py:163-230`).
- El grafo inyecta el perfil y responde «¿Dónde trabajo?» desde el Store (`graph.py:345-350, 410-423`).
- `tests/integration/agent/test_profile_memory.py:30` reproduce el caso exacto de la rúbrica, con reinicio y un hilo nuevo.

**Corregir y mejorar**
1. La extracción del perfil es una expresión regular (`actions.py:118-184`) y es frágil ante variaciones que el docente puede pedir en vivo («soy Ana, laboro en…», «mi empresa es…»). Hay que extraer los hechos con el LLM y salida estructurada (Pydantic), con la regex como respaldo.
2. `store.search()` se usa como listado del namespace, sin búsqueda semántica. Configurar el Store con `index` de embeddings y llamar `search(ns, query=…)` para recuperar hechos libres.
3. Guardar el perfil exige aprobación HITL. En la demo hay que mostrar ese paso con fluidez, o explicar por qué la escritura requiere consentimiento.

### 2.1 Herramienta determinista CSV/JSON con `@tool` — 3,5

**Evidencia**
- `query_structured` se expone con `@tool(args_schema=QueryStructuredArgs)`, con `extra="forbid"` y validador (`agent/tools.py:45-66, 238`).
- Los conteos se calculan en código (`tools.py:88-126`).
- Las consultas a SQLite de solo lectura son parametrizadas (`structured.py:204-525`).

**Hallazgos**
- **La fuente no es un CSV/JSON tabular.** Es una tabla SQLite derivada de `data/gold/facts.jsonl` (381 hechos extraídos) y `entities.jsonl` (15 entidades). El CSV es solo una exportación (`structured.py:486`).
- **Los datos son ruidosos** (por ejemplo, atributo «nuestra meta» = «2020»), y el propio docstring lo reconoce (`structured.py:10-13`).
- **La única agregación es contar.** No hay sumas, promedios ni filtros por período, así que una pregunta del tipo «¿cuántas unidades se vendieron en el tercer trimestre?» no tiene respuesta.
- **La tabla no está en el repositorio:** `data/module2/` está en `.gitignore`. En una ejecución limpia, «¿Cuántas filiales tiene Manuelita?» se enruta bien a `structured` pero se responde desde documentos, con texto residual.
- El modelo de demo nunca invoca `query_structured` (`agent/demo.py:115`).

**Corregir y mejorar (prioridad alta)**
1. Versionar un **CSV/JSON curado** con series numéricas reales del corpus y su fuente. Por ejemplo, producción o ventas por año y negocio, tomadas de los informes de sostenibilidad, con columna `fuente`.
2. Agregar una herramienta de agregación (`aggregate(metric, period, op)`) con suma, promedio, máximo y filtro por período, validada con Pydantic y con pruebas de valor exacto.
3. Hacer que la tabla exista sin pasos manuales: versionarla, o construirla en el arranque o en `make app`.
4. Hacer que el modelo de demo invoque la herramienta estructurada, para que el caso 3 se pueda mostrar sin red.

### 2.2 RAG documental con Qdrant e índice ANN — 3,8

**Evidencia**
- La colección usa coseno con `HnswConfigDiff(m=16, ef_construct=128)` (`rag/vectorstore.py:146-154`).
- El payload tiene tema, autoridad y tipo, y los filtros `must/MatchAny` se aplican en una sola etapa (`vectorstore.py:101-116, 208-227`).
- La recuperación es híbrida: e5-small (384 dimensiones) más BM25 con pesos 0,65 / 0,35 (`hybrid.py:325-368`).
- Las citas `[U#]` se validan contra la evidencia y, si no hay evidencia, se declara el fallo (`graph.py:244-257`).
- Hay pruebas de filtro y de paridad del top-k con numpy (`tests/unit/test_rag_vectorstore.py`).

**Hallazgos**
- **Sin `QDRANT_URL` se usa el modo embebido, que hace búsqueda exacta, no ANN.** `hnsw_ef` y los índices de payload solo aplican con servidor (`vectorstore.py:156, 224`).
- **Si la colección no existe, todo cae silenciosamente a numpy** (`vectorstore.py:256-263`). En el checkout no existe `data/module2/qdrant/`.
- **El índice local está desactualizado.** `rag index verify` falla con «manifiesto anterior a la spec 014».
- **Los filtros por payload solo se usan si el LLM pasa `section`** en la variante agente (`tools.py:171`). La cadena nunca filtra (`graph.py:496`).

**Corregir y mejorar**
1. Agregar un `docker-compose.yml` con Qdrant servidor y usarlo en la demo, para que el índice ANN (HNSW) esté de verdad en juego. Mostrar `hnsw_ef` y el tiempo de consulta.
2. Avisar en la UI y en los logs cuando se usa el respaldo numpy, en lugar de degradar en silencio.
3. Inferir filtros (tema o autoridad) desde el router y aplicarlos también en la cadena. Mostrar en la traza qué filtro se usó.
4. Opcional: comparar la fusión por pesos con RRF.

### 2.3 Router Agent — 4,2

**Evidencia**
- Las reglas deterministas no usan el modelo (`router.py:77-100`).
- Después viene el LLM, que responde en JSON validado (`RouteDecision`); con confianza menor a 0,6 la ruta pasa a `clarify`, y una salida inválida cae a la heurística (`router.py:149-190`).
- `direct`, `out_of_scope` y `clarify` no buscan.
- En la ejecución verificada, «hola» se resolvió con 0 llamadas al modelo y 0 búsquedas.
- Evaluación con el modelo real: 35/36 aciertos (97,2 %) y 10/10 casos sin búsqueda (`docs/evaluacion_enrutador.json`).

**Hallazgos**
- **El conjunto de evaluación del router no tiene ningún caso `mixed`**, aunque el caso 4 de la rúbrica es justamente el enrutamiento mixto.
- **En la variante agente, la ruta solo decide si se busca o no.** No restringe qué herramientas usa el LLM (`graph.py:644`).
- **La prueba de la ruta mixta solo verifica la ruta y `tool_calls >= 1`**, no que la respuesta combine ambas fuentes.
- En la ejecución verificada, una pregunta mixta solo citó `[U#]` (documentos) y ningún `[F#]` (hechos), porque la tabla no estaba construida.

**Corregir y mejorar**
1. Agregar al menos 5 casos `mixed` etiquetados a la evaluación del router y reportarlos en la matriz de confusión.
2. Agregar una prueba de extremo a extremo: una pregunta mixta debe devolver al menos un `[F#]` y un `[U#]`.
3. En la variante agente, pasar la ruta como restricción de herramientas (o al menos como pista explícita).
4. Mostrar en vivo la decisión del router (ruta, confianza, quién decidió). La UI ya lo permite, así que hay que usarlo en el guion.

### 2.4 Blindaje del RAG — 4,3

**Evidencia**
- Cada fragmento va en `<documento>` con escape de `<`, `>` y `&` (`guard.py:56-81`).
- Un detector de 6 patrones marca los fragmentos `anomalous` (`guard.py:7-53`).
- `leaks_prompt` descarta respuestas que filtran el system prompt.
- La regla 4.1 del prompt declara los documentos como datos.
- Hay un corpus adversarial (`tests/fixtures/rag/malicious`) con pruebas para las dos variantes, y se activa en vivo con `MANUELITA_DEMO_CORPUS=malicious`.

**Corregir y mejorar**
1. Todas las pruebas de «no obedece» usan un modelo guionado. Falta evidencia con el LLM real: correr el corpus adversarial contra DeepSeek y guardar el resultado en `docs/`.
2. Permitir cargar el corpus adversarial también en modo real; hoy la demostración en vivo solo funciona en modo demo.
3. El fragmento marcado `anomalous` llega igual al modelo. Hay que neutralizar o resaltar la oración inyectada, y mostrar en la traza que se detectó.

### 3.1 Aplicación interactiva con frontend propio — 4,5

**Evidencia**
- React 19 + Vite + TypeScript en `web/`, que solo habla con `/api/*` y nunca con el modelo.
- Streamlit ya no aparece en dependencias ni en código.
- El streaming SSE funciona de punta a punta:
  - Backend: `POST /api/chat/stream` con `graph.stream(...)` (`api.py:511-529`, `service.py:295-331`).
  - Frontend: lector `fetch` con parser propio (`web/src/lib/chat.ts:85-160`).
- Sesiones: nueva conversación, conversaciones recientes, retomar hilo y tarjeta HITL.
- Cada turno es trazable: ruta, confianza, fragmentos, fuentes, tokens y latencia (`ChatView.tsx:199-243`).
- Los errores de red y de API se muestran con `role="alert"`.
- Hay diseño responsive con prueba e2e (`tests/e2e/test_responsive.py`).
- 29 pruebas de vitest en verde.

**Corregir y mejorar**
1. **No hay enrutamiento del lado del cliente,** aunque la rúbrica lo nombra explícitamente. Agregar `react-router` con `/`, `/chat/:threadId` y `/memoria`, para que la conversación quede en la URL y sobreviva a recargas.
2. **No hay timeout ni cancelación.** Usar `AbortController` con tiempo límite y un botón «Detener generación»; `streamChat` ya acepta `signal`, pero nadie se lo pasa.
3. **La lista de conversaciones solo vive en `localStorage`.** Exponer `GET /api/threads?user_id=` desde el checkpointer.
4. **El fallback a `/api/chat` se activa con cualquier `http_error`** (`ChatView.tsx:460-463`), incluidos los 5xx. Limitarlo al 404, como dice el propio comentario.

### 3.2 Calidad del código y gobernanza — 3,5

**Evidencia positiva**
- Ruff limpio en lint y formato.
- `uv.lock` versionado, sin `requirements.txt` ni notebooks.
- `.env` fuera del repo y LICENSE MIT.
- API tipada con Pydantic y `response_model` en los endpoints del agente.
- CI con los checks obligatorios `autoria`, `test` y `web`.
- 117 de 119 commits siguen Conventional Commits.
- 143 pruebas de API/contrato, más de 650 en total.

**Hallazgos**
- **PRs con revisión:** de 58 PRs fusionados, 9 son de Dependabot. De los 49 PRs humanos, **solo 11 tienen aprobación** y 15 tienen alguna revisión. Casi ninguno tiene comentarios de revisión, y no hay revisión del profesor ni del Code Reviewer (G3/G4). La rúbrica pide «alrededor de 40 PRs fusionados con revisión».
- **La autoevaluación es inexacta:** `docs/rubrica_modulo2.md:21, 74` declara «54 PRs fusionados con revisión».
- **La protección de `main` no exige revisión** (`required_pull_request_reviews` ausente) y `enforce_admins` está desactivado.
- **Tipado y docstrings incompletos en `api.py` y `agent/`:**
  - 14 funciones públicas sin tipo de retorno; entre ellas, todos los endpoints de `api.py:378-590`.
  - 19 usos de `Any`.
  - 35 funciones, 33 métodos y 22 clases públicas sin docstring.
  - `/api/ask`, `/api/summary` y `/api/showcase` no tienen `response_model`.

**Corregir y mejorar (prioridad alta)**
1. Exigir al menos 1 aprobación en la protección de `main` y hacer revisiones reales del otro integrante, con comentarios. Solicitar revisión del docente o del Code Reviewer cuando corresponda.
2. Corregir `docs/rubrica_modulo2.md` y el README con las cifras reales: 49 PRs humanos fusionados y 11 aprobados.
3. Tipar los retornos y agregar `response_model` a todos los endpoints, y reducir los `Any`.
4. Activar en Ruff las reglas `ANN` y `D` (pydocstyle, convención Google) para `src/` y completar los docstrings públicos.

### 4.1 Diagramas de arquitectura — 4,0

**Evidencia:** el README tiene 5 diagramas Mermaid legibles sin leer el código (`README.md:121-233`):
- el pipeline;
- el grafo LangGraph;
- checkpointer `SqliteSaver` frente a Store `SqliteStore`, con sus namespaces;
- las herramientas y el router;
- las trazas.

**Corregir y mejorar**
1. El diagrama interactivo `docs/arquitectura.json/.html` (Archify) y `docs/capturas/arquitectura.png` siguen diciendo «numpy + SQLite». No muestran Qdrant, el Store ni LangSmith. Hay que regenerarlos.
2. No hay ninguna traza real de LangSmith (ni captura ni enlace). Agregar capturas o enlaces públicos de las trazas de los cuatro casos, con la latencia por herramienta.
3. Desplegar el nodo del agente (`create_agent`) para mostrar el bucle modelo ↔ herramientas y el punto de interrupción HITL.

### 4.2 Diseño y evaluación del retrieval — 4,0

**Evidencia**
- El conjunto `tests/fixtures/rag/eval_questions.jsonl` tiene 40 preguntas, 35 puntuables, con `expected_unit_ids`.
- Se reportan Recall@1/3/5/10, nDCG@10, MRR y latencia para los modos léxico, semántico e híbrido.
- Con las 40 preguntas, Recall@10 da 0,371 / 0,686 / 0,671 y nDCG@10 da 0,333 / 0,493 / 0,499.
- Las cifras salen de ejecuciones reales, con `run_id` y manifiesto.
- El análisis es honesto: el híbrido no supera al semántico y ningún modo se abstiene.
- La elección del embedding está justificada con MIRACL-es (ADR 0014).

**Corregir y mejorar**
1. **Las métricas son del índice numpy (10-nov), no de Qdrant,** que es lo que se mostrará en la demo. Hay que volver a correr `rag evaluate` sobre Qdrant.
2. **No se justifican empíricamente el top-k (12/8), los pesos 0,65 / 0,35 ni el troceo 400/60.** Hacer un barrido corto (k ∈ {5, 8, 12}; α ∈ {0,5; 0,65; 0,8}) y documentarlo.
3. **«36 consultas etiquetadas» exagera:** del conjunto del Módulo 2 solo 18 tienen etiqueta de recuperación. Corregir la cifra o completar las etiquetas.
4. **Las etiquetas las hizo un solo integrante y la revisión cruzada está pendiente** (T018). Hay que registrarla.
5. **La fidelidad del juez aparece como cifra en la tabla de `evaluacion_modulo2.md` pero está declarada «no válida».** Marcarla en la tabla o completar la ejecución.
6. Opcional: evaluación con datasets de LangSmith.

---

## 3. Preparación para la sustentación (ítems 5.1 y 5.2)

| Caso | ¿Se puede mostrar hoy? | Riesgo |
|------|------------------------|--------|
| 1. RAG documental con cita | Sí, con DeepSeek | Alto si no se reconstruye el índice: `rag index verify` falla y no existe la colección Qdrant (`data/module2/` no se versiona). |
| 2. Memoria corto y largo plazo | Sí | Medio: el perfil depende de la regex (1.3) y de la aprobación HITL. `MANUELITA_STATE_DIR` debe ser estable para sobrevivir al reinicio. |
| 3. Datos estructurados | **Parcialmente** | Alto: sin `agent build-structured` la ruta cae a documentos; aun construida, no hay series numéricas para una pregunta tipo «unidades vendidas por trimestre». |
| 4. Enrutamiento mixto | Parcialmente | Alto: hoy la respuesta mixta solo cita documentos (`[U#]`). |
| 5. Blindaje | Sí, en modo demo | Medio: exige reiniciar con `MANUELITA_DEMO_CORPUS=malicious`; no hay evidencia con el modelo real. |

**Acciones obligatorias antes de las 8:00 a.m.**
1. En el equipo de la demo, ejecutar en este orden:
   - `rag index rebuild --force`;
   - `rag qdrant build` (idealmente con Qdrant servidor);
   - `agent build-structured`.
   Después verificar con `rag qdrant status`. La primera consulta tarda unos 15 s mientras cargan los embeddings, así que conviene precalentar.
2. **Unificar el guion.** `docs/demo.md` (variante agente) y `docs/rubrica_modulo2.md` §7 (caso 2 con la cadena) se contradicen y usan comandos de preparación distintos. Dejar un solo guion de 12 minutos y ensayarlo cronometrado: `docs/demo.md` §4 sigue sin marcar.
3. Configurar `LANGSMITH_TRACING`, `LANGSMITH_API_KEY` y `LANGSMITH_PROJECT`, que no están en el `.env` local, y abrir las trazas en una pestaña.
4. Tener preparado el plan B (`--mode demo`) por si falla la red o la API de DeepSeek.
5. **Para 5.2:** cada integrante debe poder explicar sin leer:
   - el grafo, el checkpointer frente al Store y el router;
   - el blindaje y la API SSE;
   - por qué el híbrido no supera al semántico.

---

## 4. Checklist obligatorio de la rúbrica

| Requisito | Estado |
|-----------|--------|
| LICENSE MIT y README actualizado de M1 a M2 | ✅ |
| `uv sync`; frontend y backend desacoplados; sin Streamlit/Gradio | ✅ |
| Interfaz responsive, streaming y manejo de errores de red/API | ✅ (faltan timeout y cancelación) |
| Corto plazo con checkpointer, `thread_id` y persistencia real | ✅ |
| Largo plazo con Store y namespace | ✅ |
| Herramienta determinista CSV/JSON con `@tool` y Pydantic | 🟡 (SQLite derivado y ruidoso; sin agregaciones) |
| RAG sobre Qdrant con top-k y cita | 🟡 (Qdrant embebido sin ANN; colección no construida en el checkout) |
| Router: herramienta estructurada / RAG / respuesta directa | ✅ (ruta mixta sin evaluar) |
| Trazas en LangSmith de los cuatro casos (o logs equivalentes) | 🟡 (`turns.jsonl` sí; sin trazas de LangSmith) |
| Alrededor de 40 PRs fusionados con revisión | ❌ (11 PRs humanos aprobados) |
| Conventional Commits y `.env` fuera del repo | ✅ |
| Diagrama de arquitectura y evidencia de evaluación del retrieval | ✅ (Archify desactualizado; métricas sobre numpy) |

**Deseables**

| Deseable | Estado |
|----------|--------|
| Búsqueda híbrida y recall@10/nDCG@10 | ✅ |
| Blindaje con contexto delimitado | ✅ |
| Pruebas automáticas del router y la herramienta | ✅ |
| RAG Chains vs. RAG Agents documentado (ADR 0016, `evaluacion_variantes.json`) | ✅ |
| Especificación versionada (`specs/`) | ✅ |
| Pruebas de UI con Playwright | ✅ |
| Gatekeeper System One (Jev) | ❌ |
| Time travel (`get_state_history`, fork) | ❌ |
| Evaluación con datasets de LangSmith | ❌ |
| Despliegue (Vercel/Render) | ❌ |
| Comparación de orquestadores y LLM Wiki/OKF | ❌ |

---

## 5. Inconsistencias en la documentación que deben corregirse

| Tema | Inconsistencia |
|------|----------------|
| Sobrecosto del BM25 | `docs/evaluacion_modulo2.md` dice ~1,3 s; `docs/informe_modulo2.md:128,215` y `README.md:933` dicen ~1,6 s. |
| Conteo de PRs | El README (l. 307) y la autoevaluación dicen 54 «con revisión»; la realidad es 58 fusionados (49 humanos), 11 aprobados. |
| Manifiesto del índice | `informe_modulo2.md:72` y el README dicen que se versiona, pero `.gitignore:41` excluye todo `data/module2/`. |
| Base vectorial | El Archify dice «numpy»; el README y ADR 0018 dicen Qdrant. |
| Abstención 4/4 | La logra el router, no la recuperación (que da 0). La fila del README (l. 300) se presta a confusión. |
| Fidelidad del juez | En la tabla aparece con cifras (0,705 / 0,661), pero el informe la declara no válida. |
| Autoevaluación | Marca 3.2, 4.1 y 4.2 como cumplidos al 100 % pese a los huecos señalados. |

---

## 6. Plan de corrección priorizado

**Antes de la sustentación** (impacta 5.1 y es lo que el docente verá):
1. Reconstruir el índice, la colección Qdrant y la tabla estructurada en el equipo de la demo, y verificarlos (§3).
2. Unificar y ensayar el guion; activar LangSmith y tener el plan B listo.
3. Preparar una pregunta estructurada y una mixta que hoy sí funcionen con los hechos disponibles, y explicar con transparencia la limitación del caso «ventas por trimestre».

**Para la entrega final del módulo** (impacta 2.1, 2.2, 3.2, 4.1 y 4.2):
1. **2.1:** CSV/JSON curado con series numéricas y fuente, más una herramienta de agregación con pruebas de valor exacto. Es la mejora de mayor impacto.
2. **3.2:** revisión obligatoria en `main`, revisiones reales en cada PR y cifras corregidas en la autoevaluación.
3. **2.2:** Qdrant servidor con HNSW en `docker-compose`, aviso explícito del respaldo numpy y filtros por payload en ambas variantes.
4. **2.3:** casos `mixed` en la evaluación del router y prueba de que la respuesta combina `[F#]` y `[U#]`.
5. **4.2:** reevaluación sobre Qdrant, barrido de top-k y α, y etiquetas revisadas.
6. **4.1:** Archify regenerado y trazas de LangSmith de los cuatro casos.
7. **3.1:** `react-router` con hilo en la URL, cancelación con timeout y fallback limitado al 404.
8. **1.2 y 1.3:** prueba de conversación larga, tope al resumen, extracción del perfil con LLM y `search` semántico en el Store.
9. **2.4:** evidencia del blindaje con el modelo real.
10. **3.2:** tipado de retornos, `response_model` y docstrings públicos.

Con las cinco primeras correcciones, la nota de los ítems verificables subiría de 4,18 a un rango aproximado de 4,6–4,7.

---

*Evaluación elaborada en el rol del docente del curso, sobre el estado de `main` en `f571aa9` (2026-11-13).
Las cifras provienen del repositorio, de GitHub y de pruebas offline ejecutadas durante la revisión.*
