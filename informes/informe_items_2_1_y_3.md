# Informe técnico — Ítems 2.1 y 3 de la rúbrica del Módulo 2

| Campo | Valor |
|-------|-------|
| Proyecto | RAG Ingenio Manuelita — agente conversacional (Módulo 2) |
| Referencia | Anuncio 006, Rúbrica de Sustentación del Módulo 2: ítem 2.1 (8 %), ítems 3.1 y 3.2 (20 %) |
| Versión del código | `main` en `edb4a72` (2026-11-13) más los cambios de la spec 015 (blindaje con el modelo real, rama `015-rag-injection-shield-real`). Las rutas y líneas citadas corresponden a esa versión. |
| Público | Integrantes del equipo, para estudiar y defender la implementación en la sustentación |

**Cómo leer este informe.** Para cada punto que pide el docente, el informe responde tres preguntas:

- **Qué se hizo y cómo funciona.**
- **Dónde está:** archivo y líneas. Las rutas de Python son relativas a `src/proyecto_modelos_lenguaje/`, salvo que se indique otra raíz.
- **Por qué se hizo así:** la decisión de diseño y la alternativa descartada.

Al final de cada ítem hay una sección **Límites conocidos**, para que puedan responder con honestidad si el
docente pregunta por ellos.

---

## Índice

1. [Ítem 2.1 — Herramienta determinista CSV/JSON con `@tool`](#ítem-21--herramienta-determinista-csvjson-con-tool)
2. [Ítem 3.1 — Aplicación interactiva con frontend propio](#ítem-31--aplicación-interactiva-con-frontend-propio)
3. [Ítem 3.2 — Calidad del código y gobernanza](#ítem-32--calidad-del-código-y-gobernanza)
4. [Cómo demostrarlo en vivo](#cómo-demostrarlo-en-vivo)

---

## Ítem 2.1 — Herramienta determinista CSV/JSON con `@tool`

> **Lo que pide el docente (nivel 5):** «La función va expuesta como tool, valida con un esquema Pydantic y
> devuelve el dato exacto; el LLM no inventa cifras ni hace aritmética a ojo.»
> Caso de la demo: «¿Cuántas unidades se vendieron en el tercer trimestre?» → la herramienta consulta el
> CSV/JSON y devuelve el dato exacto.

### Visión general del flujo

```text
data/gold/facts.jsonl + entities.jsonl        (datos extraídos en el Módulo 1)
        │  agent build-structured  (CLI, una vez)
        ▼
data/module2/structured/structured.sqlite3   + manifest.json  + facts.csv / entities.json
        │  StructuredStore  (solo lectura, consultas parametrizadas)
        ▼
query_structured  (@tool + esquema Pydantic)  ──►  hechos etiquetados [F1], [F2]…
        │
        ▼
LLM redacta y cita [F#]  ──►  validate_answer comprueba que cada cita exista
```

### 2.1.a La fuente de datos: tabla estructurada derivada, con exportación CSV/JSON

**Qué y cómo**
- `build_structured_store` lee `entities.jsonl` y `facts.jsonl` de la capa oro y publica una base SQLite con su manifiesto. Solo carga los hechos con estado aceptado.
- Para cada hecho guarda la frase original (`snippet`) y sus citas (URL, título, hash).
- La misma tabla se exporta en formato legible a `facts.csv` y `entities.json`.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Propósito y contrato del módulo (docstring) | `agent/structured.py:1-14` |
| Esquema de las tablas `entities`, `facts`, `citations` e índices | `agent/structured.py:203-235` |
| Construcción a partir del oro | `agent/structured.py:249-355` (`build_structured_store`) |
| Exportación a `facts.csv` y `entities.json` | `agent/structured.py:486-510` (`export_tables`) |
| Comando de CLI que construye y exporta | `agent/__main__.py:95-117` (`_build_structured`) |
| Ruta configurada | `config/agent.toml:18-19` (`[structured] path`) |

**Por qué**
- **SQLite, y no leer el CSV con pandas en cada consulta.** Permite índices (`facts_subject`), consultas parametrizadas y abrir la base en **solo lectura**. El CSV/JSON queda como vista legible del mismo contenido, para inspeccionarlo y mostrarlo.
- **Se deriva del oro, no se escribe a mano.** Así cada dato conserva la trazabilidad hasta el documento original (`unit_id` y citas), igual que el RAG.
- **El manifiesto guarda el hash del manifiesto del oro.** Si el oro cambia, la tabla queda marcada como desactualizada (`structured.py:374-383`) y se exige reconstruirla. Así se evitan respuestas con datos viejos.

### 2.1.b La función expuesta como herramienta con `@tool`

**Qué y cómo**
- `build_read_tools` es una fábrica que construye dos herramientas de lectura: `search_documents` (RAG) y `query_structured` (datos estructurados).
- Las dos se declaran con el decorador `@tool` de LangChain.
- El **docstring** de cada función es la descripción que lee el modelo para decidir cuándo usarla.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Fábrica de herramientas de lectura | `agent/tools.py:229-296` |
| `@tool(args_schema=QueryStructuredArgs)` y firma tipada | `agent/tools.py:256-263` |
| Docstring que describe la herramienta al modelo | `agent/tools.py:264-266` |
| Registro de las herramientas en el agente (`create_agent`) | `agent/graph.py:648` y `agent/graph.py:663` |
| Regla del prompt que indica cuándo usarla | `prompts/agent.md:20-21` |

**Por qué**
- **Es una fábrica (closure).** El índice y la tabla se cargan **una sola vez por proceso** y las herramientas los reutilizan (docstring en `tools.py:7-8`). Además, cada herramienta registra lo que recuperó en `ToolTrace` (`tools.py:129-140`), que luego alimenta las citas y la traza de la UI.
- **Son de solo lectura y no piden aprobación.** La constitución fija la regla «lectura automática, escritura con aprobación» (`tools.py:3-5`). Las herramientas que escriben (memoria, exportación) sí pasan por Human-in-the-Loop.

### 2.1.c Validación con esquema Pydantic

**Qué y cómo**
- Los argumentos de la herramienta se definen con el modelo Pydantic `QueryStructuredArgs`, que LangChain convierte en el **JSON Schema** que ve el modelo.
- `extra="forbid`: rechaza argumentos inventados.
- Límites de longitud en los textos y `limit` entre 1 y 20 (`ge=1, le=20`).
- `entity_type` restringido a un `Literal` (`subsidiary`, `brand`, `certification`, `company`).
- Un `model_validator` exige al menos un criterio de búsqueda.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| `EntityType` como `Literal` | `agent/tools.py:26` |
| Esquema `QueryStructuredArgs` | `agent/tools.py:46-61` |
| `extra="forbid"` | `agent/tools.py:49` |
| Validador «indica al menos un criterio» | `agent/tools.py:63-67` |
| Esquema análogo de `search_documents` | `agent/tools.py:35-43` |

**Por qué**
- Si el modelo llama la herramienta con argumentos mal formados, Pydantic lo rechaza **antes** de tocar la base. El modelo recibe el error y puede corregir la llamada.
- El `Literal` y `extra="forbid"` reducen la superficie de alucinación: el modelo no puede inventar un tipo de entidad ni un parámetro.
- **No se acepta SQL libre**, solo parámetros. Es la defensa contra la inyección SQL desde el prompt (docstring en `tools.py:46` y `tools.py:194`).

### 2.1.d Devuelve el dato exacto: consultas parametrizadas de solo lectura

**Qué y cómo**
- `StructuredStore` abre la base con URI `?mode=ro` y activa `PRAGMA query_only = ON`, así que es imposible escribir.
- Todas las consultas usan marcadores `?`, nunca concatenan texto del usuario.
- Los métodos públicos son: `list_entities` (por tipo), `get_facts` (por sujeto o alias y atributo) y `search_facts` (por coincidencia de términos).
- Cada hecho vuelve con su valor literal, su frase de origen y sus citas.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Conexión en solo lectura | `agent/structured.py:384-387` |
| `list_entities` parametrizado | `agent/structured.py:435-451` |
| Resolución de sujeto por nombre o alias | `agent/structured.py:453-462` |
| `get_facts` con `?` y `LIMIT ?` | `agent/structured.py:464-484` |
| `search_facts` (coincidencia de términos) | `agent/structured.py:518-533` |
| Implementación de la herramienta (combina las consultas) | `agent/tools.py:200-226` (`query_structured_impl`) |
| Hechos entregados como `<documento id="F#">` | `agent/tools.py:218-225` y `agent/tools.py:280-283` |

**Por qué**
- **Solo lectura:** la app no debe modificar datos (regla de la constitución), y además protege ante errores o ataques.
- **El valor se devuelve tal como está en la tabla,** con su fuente. El modelo solo lo redacta.
- **Cada hecho lleva la etiqueta `F#`,** distinta de `U#` (fragmentos de documentos). Así la respuesta y la UI distinguen qué vino de la tabla y qué de los textos.

### 2.1.e El LLM no inventa cifras ni hace aritmética

Hay **cuatro capas**:

| Capa | Qué hace | Archivo:líneas |
|------|----------|----------------|
| 1. Cálculo en código | Los conteos («¿cuántas filiales…?») los calcula Python con `count_entities`, no el modelo. `count_fact` crea un hecho sintético con el total exacto y la lista de nombres. | `agent/tools.py:89-127` |
| 2. Detección de la intención de contar | `count_intent` reconoce con una expresión regular las preguntas de conteo o lista y decide qué tipo de entidad contar. | `agent/tools.py:70-86` |
| 3. El conteo va primero en la evidencia | En la cadena, el hecho con el conteo se antepone a los demás para que el modelo lo **cite**, no lo calcule. | `agent/graph.py:476-491` (comentario en la l. 480) |
| 4. Reglas del prompt y validación de citas | El prompt prohíbe completar cifras que no estén en la evidencia. `validate_answer` descarta toda respuesta que no cite etiquetas `[U#]`/`[F#]` válidas del turno y la convierte en fallo de evidencia. | `prompts/agent.md:38-40`; `agent/graph.py:92` (`LABEL_PATTERN`), `agent/graph.py:219-258` |

**Por qué**
- Los LLM son poco fiables contando y sumando. La rúbrica pide explícitamente que «el LLM no haga aritmética a ojo», por eso la operación numérica vive en la herramienta.
- **Validar las citas** convierte la regla «no inventes» en algo comprobable por código. Una cifra sin cita válida nunca llega al usuario como respuesta.

### 2.1.f Cómo llega la herramienta al flujo de la conversación

**Variante cadena (determinista)**
- El router clasifica la pregunta (por ejemplo, `STRUCTURED_CUES` en `agent/router.py:54-57`).
- Si la ruta es `structured` o `mixed`, el nodo `retrieve` llama a `query_structured_impl` (`agent/graph.py:467-514`).
- Si la tabla no tiene filas, `apply_structured_fallback` cambia la ruta a `documental` y lo deja registrado (`agent/router.py:214-218`, invocado en `agent/graph.py:492-493`).
- En la ruta `mixed` conviven hechos `F#` y fragmentos `U#` en el mismo contexto (`agent/graph.py:494-502`).

**Variante agente (ReAct)**
- El modelo decide llamar `query_structured`, porque está registrada en `create_agent` (`agent/graph.py:648-663`).

**Por qué hay dos variantes:** comparar cadena RAG y agente RAG es un punto del curso (ADR 0016). En la cadena, la herramienta se invoca siempre que la ruta lo pida; en el agente, decide el modelo.

### 2.1.g Pruebas que lo respaldan

| Prueba | Qué verifica | Archivo:línea |
|--------|--------------|---------------|
| `test_query_structured_schema_is_pydantic_and_rejects_empty_calls` | El esquema es Pydantic y rechaza llamadas sin criterio | `tests/unit/agent/test_tools.py:125` |
| `test_entity_count_is_exact_and_not_left_to_the_model` | El conteo lo hace la herramienta | `tests/unit/agent/test_tools.py:144` |
| `test_count_fact_carries_the_exact_total_and_a_citation` | El total exacto viaja con su cita | `tests/unit/agent/test_tools.py:169` |
| `test_query_structured_by_subject_and_by_free_text` | Consulta por sujeto y por texto | `tests/unit/agent/test_tools.py:77` |
| `test_query_structured_without_store_is_declared` | Sin tabla, la herramienta lo declara | `tests/unit/agent/test_tools.py:95` |
| `test_readonly_connection_cannot_write` | La base no admite escrituras | `tests/unit/agent/test_structured.py:166` |
| `test_store_rejects_outdated_gold` | Tabla desactualizada respecto al oro | `tests/unit/agent/test_structured.py:155` |
| `test_generated_manifest_satisfies_schema` | Contrato del manifiesto | `tests/contract/test_structured_manifest_contract.py:18` |

### 2.1.h Límites conocidos (prepárense para esta pregunta)

1. **La fuente no es un CSV/JSON tabular de negocio.** Es una vista derivada de hechos extraídos automáticamente del corpus. Algunos atributos son ruidosos, y el propio módulo lo reconoce en `agent/structured.py:10-13`.
2. **La única agregación es contar entidades.** No hay sumas, promedios ni filtros por período, así que el caso de ejemplo de la rúbrica («unidades vendidas en el tercer trimestre») no tiene datos para responderse. Defiéndanlo con el diseño (cálculo en la herramienta) y reconozcan el alcance de los datos.
3. **`data/module2/` no se versiona.** La tabla se construye en cada máquina con `agent build-structured`. Si no existe, la ruta estructurada cae a documentos.
4. **Mejora natural:** un CSV curado con series numéricas por año y fuente, más una herramienta `aggregate(metric, period, op)` con pruebas de valor exacto.

---

## Ítem 3.1 — Aplicación interactiva con frontend propio

> **Lo que pide el docente (nivel 5):** «Frontend propio (React, Next.js, Vue, Svelte o equivalente)
> desacoplado del backend/API: componentes, estado, routing, streaming, sesiones, errores controlados y
> respuesta trazable. Streamlit y Gradio no se aceptan.» Del checklist: interfaz responsive, streaming de
> respuestas y manejo de errores de red/API.

### Arquitectura

```text
Navegador ── React 19 + Vite + TypeScript (web/)
   │  fetch /api/chat/stream  (SSE)      fetch /api/threads/{id}, /api/memory/{id}, /resume
   ▼
FastAPI (api.py) ──► ChatService (agent/service.py) ──► grafo LangGraph (agent/graph.py)
                                   │                          │
                                   └── checkpointer + Store   └── router, herramientas, LLM
```

### 3.1.a Frontend propio y desacoplado del backend

**Qué y cómo**
- El frontend es una SPA en **React 19 + Vite + TypeScript**, en `web/`, y solo habla con el backend por HTTP bajo el prefijo `/api`. Nunca llama al modelo ni conoce la clave de DeepSeek.
- En desarrollo, Vite corre en el puerto 5173 y el backend en el 8000, con CORS restringido a ese origen.
- En producción, FastAPI sirve el build compilado (`web/dist`).

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Dependencias del frontend (React 19, sin Streamlit/Gradio) | `web/package.json:13-18` |
| Base de la API en el cliente (`/api`) | `web/src/lib/api.ts:12` |
| Cliente HTTP genérico `request<T>` | `web/src/lib/api.ts:54-80` |
| CORS restringido al dev server | `api.py:87-92` |
| La clave se lee solo en el servidor (`.env`) | `api.py:83` |
| FastAPI sirve el build de la SPA | `api.py:566-585` |

**Por qué**
- La rúbrica exige una separación real: la interfaz habla con una API y el agente se ejecuta en el backend. Así la clave nunca sale del servidor y el backend se puede probar (y desplegar) por separado.
- Servir el build desde FastAPI deja **un solo proceso** para la demo (`make app`) sin perder el desacople: el navegador sigue llamando a `/api/*`.

### 3.1.b Componentes

**Qué y cómo:** la interfaz está dividida en componentes de una sola responsabilidad.

| Componente | Responsabilidad | Archivo |
|------------|-----------------|---------|
| `App` | Estructura de la página, salud del proveedor, navegación | `web/src/App.tsx:14-94` |
| `RagConsole` | Consola: modo real/demo, pestañas de tarea, monta el chat | `web/src/components/RagConsole.tsx:59-92` |
| `ChatView` | Conversación: estado, envío, streaming, hilos, memoria, errores | `web/src/components/ChatView.tsx:309-641` |
| `ChatTurnCard` | Un turno ya respondido, con su traza | `web/src/components/ChatView.tsx:198-253` |
| `LiveTurnCard` | El turno en curso mientras llega el streaming | `web/src/components/ChatView.tsx:286-307` |
| `ApprovalCard` | Aprobar, editar o rechazar una acción de escritura (HITL) | `web/src/components/ApprovalCard.tsx` |
| `RetrievedFragments`, `SourceList` | Fragmentos recuperados y fuentes citadas | `web/src/components/RetrievedFragments.tsx`, `SourceList.tsx` |
| `DemoBanner`, `TaskTabs` | Aviso del modo demo y selector de tarea | `web/src/components/DemoBanner.tsx`, `TaskTabs.tsx` |

**Por qué:** separar la presentación de un turno de la lógica de envío permite probar cada pieza por aparte (`web/src/test/`) y reutilizar `ChatTurnCard` para turnos en vivo y turnos recuperados de un hilo.

### 3.1.c Estado

**Qué y cómo**
- `ChatView` maneja su estado con hooks de React: hilo actual, turnos, mensaje, ocupado, acción pendiente, error, preferencias, perfil, turno en vivo, recientes y observabilidad.
- El identificador de usuario anónimo se guarda en un `useRef`.

**Dónde:** `web/src/components/ChatView.tsx:310-324`. Funciones de persistencia en el navegador: `ChatView.tsx:87-171` (`readRecent`, `rememberThread`, `readSession`/`writeSession`, `readLocal`/`writeLocal`, `anonymousUser`, `readThread`).

**Por qué:**
- **Hooks locales, no una librería de estado global:** el estado pertenece a una sola vista y no se comparte entre páginas, así que no se justifica la complejidad extra.
- **El estado «de verdad» de la conversación vive en el servidor** (checkpointer). El navegador solo guarda punteros: el `thread_id` y la lista de recientes.

### 3.1.d Routing

**Qué y cómo**
- **Backend:** FastAPI define rutas REST por recurso: `/api/chat`, `/api/chat/stream`, `/api/threads/{id}`, `/api/threads/{id}/resume` y `/api/memory/{user_id}` (`api.py:481-563`).
- **SPA:** la ruta comodín `/{path:path}` devuelve `index.html` para cualquier ruta que no sea un archivo (`api.py:571-577`). Así una SPA funciona al recargar.
- **Frontend:** la navegación es por anclas dentro de una sola página (`#consola`, `#recorrido`, `#productos`, `#limites`), en `web/src/App.tsx:67-72`.

**Por qué:** la experiencia se diseñó como una sola página con secciones, donde la conversación es la consola principal.

**Límite:** no hay enrutador del lado del cliente (`react-router` no está en `web/package.json`) ni una URL por conversación (`/chat/:threadId`). Es la mejora pendiente más visible del ítem 3.1.

### 3.1.e Streaming

**Qué y cómo — de punta a punta**

1. **Backend, endpoint SSE.** `POST /api/chat/stream` devuelve un `StreamingResponse` con `media_type="text/event-stream"`. Desactiva caché y buffering (`X-Accel-Buffering: no`) para que cada evento salga en cuanto se produce.
2. **Backend, origen de los eventos.** `ChatService.open_stream` valida antes de abrir el flujo, así que los errores de validación salen como HTTP normal. Luego `_events` recorre `graph.stream(..., stream_mode=["updates", "messages"], subgraphs=True)`.
3. **Backend, traducción a eventos del cliente.** `stream_event` convierte cada elemento del stream de LangGraph en:
   - `route`: decisión del router;
   - `tool`: herramienta terminada;
   - `retrieval`: cuántos fragmentos y filas;
   - `token`: texto del modelo.

   Al final se emite `done` con la respuesta **ya validada** (con citas). Si algo falla a mitad del flujo, se emite `error`.
4. **Frontend, consumidor.** `streamChat` usa `fetch` + `response.body.getReader()` y un parser SSE propio (`parseBlock`) que separa los eventos por `\n\n`.
5. **Frontend, presentación.** `liveStage` transforma cada evento en la etapa visible («Enrutando…», «Recuperando evidencia…», «Herramienta: …», «Escribiendo…») y va concatenando los tokens. `LiveTurnCard` los muestra con `aria-live="polite"`.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Endpoint SSE | `api.py:496-520` (`_sse` y `chat_stream`) |
| Validación previa y generador de eventos | `agent/service.py:302-342` |
| Traducción del stream de LangGraph a eventos | `agent/service.py:53-89` (`stream_event`) |
| Tipos de los eventos en el cliente (unión discriminada) | `web/src/lib/types.ts:267-274` (`ChatStreamEvent`) |
| Cliente SSE sobre `fetch` | `web/src/lib/chat.ts:66-159` |
| Etapas en vivo y tarjeta de streaming | `web/src/components/ChatView.tsx:262-307` |
| Uso en el envío | `web/src/components/ChatView.tsx:455-463` |

**Por qué**
- **`fetch` + SSE manual y no `EventSource`:** `EventSource` solo admite `GET` y la conversación necesita `POST` con un cuerpo JSON (hilo, variante, modo).
- **SSE y no WebSocket:** el flujo es unidireccional (servidor → cliente). SSE es más simple, pasa por proxies HTTP y basta para este caso.
- **El evento final `done` trae la misma respuesta validada que `POST /api/chat`.** Los tokens en vivo son una vista previa; lo que queda en pantalla es la versión cuyas citas pasaron por `validate_answer`. Así el streaming no rompe la garantía de «no inventar».
- **Se emiten `route` y `tool`:** la rúbrica pide que «se vea la decisión del router, no solo la respuesta».

### 3.1.f Sesiones

**Qué y cómo**
- **Conversación (hilo):**
  - El backend asigna un `thread_id` (UUID) al primer turno.
  - El frontend lo guarda en `sessionStorage` y lo reenvía en cada mensaje.
  - Al recargar, se recupera el hilo con `GET /api/threads/{id}`.
  - «Nueva conversación» limpia el hilo; las conversaciones recientes se listan y se pueden retomar.
- **Usuario:** se genera un `user_id` anónimo estable en `localStorage`. Lo usa la memoria de largo plazo (perfil y preferencias).
- **Validación en la API:** el `thread_id` debe ser un UUID v4 y el `user_id`, alfanumérico.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Restaurar el hilo al cargar | `web/src/components/ChatView.tsx:338-361` |
| Retomar un hilo reciente | `web/src/components/ChatView.tsx:363-385` |
| Nueva conversación | `web/src/components/ChatView.tsx:387-394` y botón en `:507` |
| Guardar el hilo tras cada respuesta | `web/src/components/ChatView.tsx:471-473` |
| Lista de conversaciones recientes | `web/src/components/ChatView.tsx:519-532` |
| Validación de `thread_id` y `user_id` | `api_models.py:215-225` (`ChatRequest`) |
| Endpoint de lectura del hilo | `api.py:558-563` |

**Por qué**
- **`sessionStorage` para el hilo activo:** cada pestaña tiene su propia conversación y no se mezclan.
- **`localStorage` para el usuario:** su memoria de largo plazo debe sobrevivir entre sesiones.
- **El contenido de la conversación no se guarda en el navegador.** Vive en el checkpointer SQLite del servidor. Eso es lo que permite el caso de la rúbrica de «reiniciar el proceso y que el hilo continúe».

**Límite:** la lista de recientes solo existe en el navegador. No hay un `GET /api/threads?user_id=` que liste los hilos desde el servidor.

### 3.1.g Errores controlados

**Qué y cómo — un solo contrato de error de punta a punta**
- **Backend.** Todo error se responde con el sobre `{"error": {code, message, retryable, action}}` y un código HTTP coherente:
  - 422: validación;
  - 503: falta la clave o la configuración;
  - 504: tiempo agotado del modelo;
  - 502: fallo del proveedor;
  - `index_unavailable` con la acción «reconstruir».
- **Frontend, red caída:** `fetch` falla y se convierte en `network_error` («No se pudo conectar…», reintentable).
- **Frontend, HTTP 4xx/5xx:** se usa el sobre del backend; si no viene, se arma un `http_error` genérico.
- **Error a mitad del streaming:** llega el evento `error`. Si el flujo se corta sin `done`, se genera `stream_incomplete`.
- **Validación local:** un mensaje vacío se rechaza antes de enviarlo.
- **Presentación:** el error se muestra en un bloque con `role="alert"` (accesible) y los botones se deshabilitan mientras hay una operación en curso.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Sobre de error común | `api.py:205-223` (`_api_error`) |
| Mapeo de excepciones del proveedor a códigos HTTP | `api.py:226-250` (`_exception_response`) |
| Errores de validación de Pydantic → 422 en español | `api.py:301-326` |
| Errores del agente (índice, configuración) | `api.py:461-478` (`_chat_error`) |
| Errores de streaming como evento | `agent/service.py:337-342` |
| Clase `ApiClientError` en el cliente | `web/src/lib/types.ts:140-148` |
| Red, HTTP, evento `error` y flujo incompleto en el cliente | `web/src/lib/chat.ts:103-157` |
| Conversión a mensaje visible | `web/src/components/ChatView.tsx:396-407` (`report`) |
| Validación de mensaje vacío | `web/src/components/ChatView.tsx:442-451` |
| Alerta accesible | `web/src/components/ChatView.tsx:635` |

**Por qué**
- Un contrato único permite que la UI muestre siempre un mensaje útil y sepa si conviene reintentar (`retryable`) o qué hacer (`action`).
- **Sin Python en pantalla:** nunca se muestran trazas de Python al usuario.

**Límite:** no hay timeout ni cancelación desde el cliente (`AbortController`), y el respaldo a `/api/chat` (`ChatView.tsx:459-465`) se activa con cualquier `http_error`, no solo con el 404 que indica el comentario.

### 3.1.h Respuesta trazable

**Qué y cómo:** cada turno respondido muestra:
- la **ruta** del router con su confianza y la razón;
- **quién decidió** (reglas, LLM o demo) y la ruta alternativa;
- los **fragmentos recuperados** `U#` y las **filas estructuradas** `F#`;
- las **fuentes citadas** con enlace;
- un aviso si algún fragmento traía instrucciones inyectadas;
- las métricas del turno: latencia, llamadas al modelo, búsquedas y tokens.

Además, la consola indica si las trazas van a **LangSmith** o al log JSON local.

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Tarjeta del turno con ruta, fragmentos, filas, fuentes y métricas | `web/src/components/ChatView.tsx:198-253` |
| Aviso de fragmentos anómalos (blindaje) | `web/src/components/ChatView.tsx:214-228` |
| Indicador de observabilidad | `web/src/components/ChatView.tsx:509-513` |
| Modelos tipados de la ruta y las métricas | `api_models.py:228-246` (`RouteModel`, `TurnMetricsModel`) |
| Endpoint de observabilidad | `api.py:449-458` |

**Por qué:** la rúbrica pide «respuesta trazable», y en la demo hay que mostrar la decisión del router y la cita verificable. Exponer las métricas por turno permite además explicar el costo de cada ruta; por ejemplo, un saludo no hace búsquedas.

### 3.1.i Interfaz responsive

**Qué y cómo:** hay puntos de quiebre a 1100, 860 y 560 px y un ajuste para pantallas grandes (1024 px). También se respeta `prefers-reduced-motion`. Una prueba E2E con Playwright verifica la presentación en distintos anchos.

**Dónde:** `web/src/styles/global.css:917, 1292, 1316, 1386, 1460`; `tests/e2e/test_responsive.py`.

**Por qué:** es un requisito obligatorio del checklist, y la demo puede proyectarse en resoluciones distintas.

### 3.1.j Pruebas del frontend y de la API de conversación

- `web/src/test/`: 8 archivos y 29 pruebas de Vitest + Testing Library, entre ellas `ChatView.test.tsx`.
- `tests/api/test_chat_stream.py`: pruebas del endpoint SSE.
- `tests/e2e/`: Playwright (`make e2e`).

---

## Ítem 3.2 — Calidad del código y gobernanza

> **Lo que pide el docente (nivel 5):** «Modularidad, PEP 8, type hints, docstrings, reproducibilidad con uv,
> separación frontend/backend y API tipada; historial de alrededor de 40 PRs fusionados con revisión; nada de
> notebooks sueltos.»

### 3.2.a Modularidad

**Qué y cómo:** el agente está dividido en 19 módulos de una sola responsabilidad, dentro de `agent/`.

| Módulo | Responsabilidad |
|--------|-----------------|
| `graph.py` | Grafos LangGraph (cadena y agente), nodos y validación de respuestas |
| `router.py` | Decisión de ruta (reglas → LLM) |
| `tools.py` | Herramientas de lectura (`search_documents`, `query_structured`) |
| `structured.py` | Tabla estructurada de solo lectura |
| `memory.py` | Checkpointer, Store, perfil, preferencias y resumen |
| `guard.py` | Blindaje contra inyección indirecta |
| `actions.py` | Herramientas de escritura con aprobación (HITL) |
| `service.py` | Servicio de conversación (send, stream, resume, hilos) |
| `observability.py` | LangSmith y log estructurado |
| `config.py`, `prompts.py`, `models.py` | Configuración, carga de prompts y modelos de dominio |
| `evaluate.py`, `judge.py`, `compare.py` | Evaluación del router, juez y comparación cadena vs. agente |
| `demo.py`, `privacy.py`, `__main__.py` | Modelo de demo sin red, redacción de PII y CLI |

Fuera del agente, cada capa del proyecto tiene su paquete: `rag/` (índice, Qdrant, recuperación híbrida), `silver/`, `gold/`, `api.py` + `api_models.py` (HTTP) y `web/` (frontend). Los prompts viven fuera del código, en `prompts/*.md`, y los parámetros en `config/*.toml`.

**Por qué:** cada módulo se prueba de forma aislada (`tests/unit/agent/` tiene un archivo por módulo). Los prompts y parámetros se pueden cambiar sin tocar el código, y quedan versionados y registrados en `docs/prompt_log.md`.

### 3.2.b PEP 8 y estilo

**Qué y cómo:** **Ruff** cumple el papel de linter y formateador, con `line-length = 100` y las reglas `E`, `F`, `I`, `UP`, `B`, `SIM` y `RUF`. Corre en tres lugares:
- en local con `make check`;
- en el hook de pre-commit;
- en la CI, que falla si hay errores.

**Dónde:** `pyproject.toml:64-71`; `Makefile:41-53`; `.github/workflows/ci.yml:56-63`.

**Por qué:** automatizar el estilo evita discusiones en las revisiones y garantiza el mismo resultado en todas las máquinas. Estado actual: `ruff check` y `ruff format --check` limpios.

### 3.2.c Type hints y docstrings

**Qué y cómo**
- Se usa `from __future__ import annotations` en todos los módulos.
- **Python:** los tipos se declaran con `Literal`, `dataclass(slots=True)`, `Sequence`/`Iterator` y modelos Pydantic. Ejemplos: `agent/tools.py:26, 130-136, 170-177`; `agent/service.py:302-310`.
- **Docstrings:** las clases y funciones centrales tienen docstrings en español que explican el **porqué**, no solo el qué. Ejemplos: `agent/structured.py:1-14`, `agent/tools.py:90-93`, `agent/graph.py:248-251`, `agent/service.py:311-316`.
- **Frontend:** TypeScript tipa todo el contrato, con una unión discriminada para los eventos de streaming (`web/src/lib/types.ts:267-274`).

**Por qué:** los tipos documentan el contrato entre capas y permiten detectar errores antes de ejecutar. Los docstrings de las herramientas, además, son leídos por el modelo.

**Límite:** la cobertura no es completa. Los endpoints de `api.py` no declaran tipo de retorno (por ejemplo `api.py:482`, `api.py:503`) y hay funciones y métodos públicos sin docstring. Ruff todavía no aplica las reglas `ANN` (anotaciones) ni `D` (docstrings).

### 3.2.d Reproducibilidad con uv

**Qué y cómo**
- Todas las dependencias se declaran en `pyproject.toml` y se fijan en `uv.lock`, que está versionado. No hay `requirements.txt`.
- La versión de Python se fija en `.python-version` (3.14) y en `requires-python`.
- El paquete se construye con `uv_build`.
- La CI instala con `uv sync --frozen`, así que falla si el lock no corresponde al `pyproject`.
- El frontend se instala con `npm ci` sobre `package-lock.json`.

**Dónde:** `pyproject.toml:12-13, 50-51`; `.python-version`; `.github/workflows/ci.yml:34-35`; `Makefile:30-33` (`make install`, `make dev`).

**Por qué:** cualquier integrante (o el docente) obtiene exactamente el mismo entorno con `uv sync`. Esto responde al punto de la rúbrica «demo que solo funciona en el computador de un integrante».

### 3.2.e Separación frontend/backend y API tipada

**Qué y cómo**
- Todos los contratos HTTP se declaran con **Pydantic** en `api_models.py`.
- Las peticiones heredan de `RequestModel` y validan patrones (UUID del hilo, `user_id`, longitud del mensaje).
- Las respuestas usan `ConfigDict(extra="forbid")` para no filtrar campos inesperados.
- Los endpoints principales declaran `response_model`, así FastAPI valida la salida y genera OpenAPI (`/docs`).

**Dónde**
| Qué | Archivo:líneas |
|-----|----------------|
| Rutas y estados como `Literal` | `api_models.py:211-212` |
| `ChatRequest` con validaciones | `api_models.py:215-225` |
| `RouteModel`, `TurnMetricsModel`, `ChatFragmentModel` | `api_models.py:228-262` |
| Endpoints con `response_model` | `api.py:329, 408, 481, 523, 534, 558` |
| Espejo de tipos en TypeScript | `web/src/lib/types.ts` |

**Por qué:** el contrato tipado en los dos lados hace que un cambio incompatible falle en las pruebas de contrato (`tests/contract/`) y no en la demo.

**Límite:** `/api/ask`, `/api/summary`, `/api/showcase` y `/api/observability` (`api.py:368-458`) no declaran `response_model`.

### 3.2.f Historial: PRs, revisión y commits

**Qué y cómo**
- **Flujo por ramas y PR:** no se hace push directo a `main`. La rama está protegida y exige los checks de CI `autoria`, `test` y `web`.
- **Conventional Commits:** 118 de 120 commits sin merge cumplen el formato.
- **Regla de autoría:** el hook `commit-msg` y el job `autoria` de la CI verifican que solo los dos integrantes figuren como autores (`scripts/check_commit_authors.py`, ADR 0017).
- **Especificaciones versionadas por feature** en `specs/` (Spec Kit) y decisiones en `docs/decisions/` (ADR 0003–0018).

**Cifras actuales (GitHub, 2026-11-13):**

| Indicador | Valor |
|-----------|------:|
| PRs fusionados | 59 |
| PRs de los integrantes | 50 (los otros 9 son de Dependabot, ya retirado) |
| PRs con aprobación formal | 11 |
| PRs con alguna revisión | 15 |

**Dónde:** `.github/workflows/ci.yml`; `.pre-commit-config.yaml`; `CONTRIBUTING.md`; `CONSTITUTION.md` §4.2–4.3.

**Por qué:** los PRs pequeños con CI permiten rastrear la evolución del proyecto y detectan regresiones antes de fusionar. La rúbrica pide «alrededor de 40 PRs fusionados con revisión».

**Límite importante:** el volumen de PRs se cumple, pero **la revisión no**: solo 11 de 50 tienen aprobación y casi ninguno tiene comentarios. Para el nivel 5 hay que exigir al menos una aprobación en la protección de `main` y revisar de verdad el PR del compañero. Si les preguntan, no digan «54 PRs con revisión»: es la cifra que figura en `docs/rubrica_modulo2.md` y no es correcta.

### 3.2.g Nada de notebooks sueltos

**Qué y cómo:** el repositorio no tiene ningún `.ipynb` versionado. Todo se ejecuta con módulos y CLI:
- `python -m proyecto_modelos_lenguaje.agent`;
- el comando `pml`;
- `scripts/`;
- objetivos del `Makefile`.

Las pruebas viven en `tests/` (unitarias, integración, contrato, API y E2E).

**Por qué:** los notebooks no son reproducibles ni revisables en un PR. Los scripts y módulos sí se prueban en la CI.

### 3.2.h Otros requisitos de gobernanza

| Requisito | Evidencia |
|-----------|-----------|
| Licencia MIT | `LICENSE` |
| `.env` fuera del repositorio | `.gitignore:16`; solo se versiona `.env.example` |
| Datos pesados en Git LFS | `CONSTITUTION.md` §1; `.gitattributes` |
| Interfaz de comandos única | `Makefile` (`make help`, `make check`, `make app`, `make e2e`) |

---

## Cómo demostrarlo en vivo

**Preparación (una vez, en el equipo de la demo):**

```bash
uv sync
uv run python -m proyecto_modelos_lenguaje.agent build-structured   # tabla estructurada + CSV/JSON
make app                                                             # build web + API en :8000
```

**Ítem 2.1, en la app (modo real):**
1. Pregunta «¿Cuántas filiales tiene Manuelita?». Debe verse:
   - la ruta **Estructurada**;
   - la fila `[F1]` con «Conteo exacto calculado por la herramienta»;
   - la respuesta citando `[F1]`.
2. Muestren en el IDE:
   - `agent/tools.py:46-67` (esquema Pydantic);
   - `agent/tools.py:256-266` (`@tool`);
   - `agent/tools.py:89-121` (conteo en código);
   - `agent/graph.py:245-258` (validación de citas).
3. Abran `data/module2/structured/facts.csv` para mostrar la vista CSV de la tabla.

**Ítem 3.1:**
1. Envíen una pregunta y señalen las etapas en vivo (ruta → recuperación → «Escribiendo…»).
2. Recarguen la página: el hilo se recupera.
3. Pulsen «Nueva conversación».
4. Detengan el backend y envíen un mensaje: aparece el error de red controlado.
5. Muestren en el IDE `api.py:502-520` y `web/src/lib/chat.ts:84-159`.

**Ítem 3.2:**
1. Muestren en GitHub la lista de PRs y los checks de CI.
2. En la terminal: `make check` (Ruff + pytest + vitest + build).

---

*Informe preparado sobre `main` en `edb4a72` (2026-11-13), con las líneas actualizadas a la spec 015. Si el código cambia, las líneas citadas pueden
desplazarse: búsquenlas por el nombre de la función indicado entre paréntesis.*
