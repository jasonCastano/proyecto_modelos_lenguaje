# ADR 0018 — Qdrant, memoria de perfil, ruta mixta y streaming para la rúbrica del Módulo 2

- **Estado**: aceptada
- **Fecha**: 2026-11-13
- **Autor**: Roberto José Guerrero
- **Relacionadas**: ADR 0014 (recuperación semántica), ADR 0015 (alcance del Módulo 2), ADR 0016 (agente
  con LangGraph); `docs/rubrica_modulo2.md`.

## Contexto

El 2026-11-13 se publicó la rúbrica de sustentación del Módulo 2 (Anuncio 006,
`data/module2/Rubrica_de_Sustentacion_del_Modulo_2.md`). Al contrastarla con lo entregado en
`v0.2.0-modulo2` aparecieron cinco brechas:

1. **Base vectorial**: la rúbrica pide «RAG sobre Qdrant con recuperación top-k» e índice ANN (ítem 2.2). La
   ADR 0015 había descartado Qdrant por simplicidad y el proyecto usaba una matriz `numpy`.
2. **Memoria de largo plazo**: el caso 2 («Me llamo Ana y trabajo en Carvajal» → hilo nuevo) exige recuperar
   un dato de perfil desde el Store con `search()`. Solo guardábamos tres preferencias de formato.
3. **Enrutamiento mixto**: el caso 4 combina documento y dato en la misma respuesta. El enrutador solo tenía
   rutas excluyentes.
4. **Streaming**: el ítem 3.1 y el checklist piden streaming de respuestas en el frontend propio.
5. **Trazas**: piden trazas de LangSmith de los cuatro casos «o logs estructurados equivalentes».

## Decisión

1. **Qdrant como base vectorial** (`rag/vectorstore.py`). El índice versionado de la spec 013 sigue siendo
   la fuente; `rag qdrant build` lo carga en la colección `manuelita_fragments` (coseno, HNSW `m=16`,
   `ef_construct=128`) con *payload* por fragmento (unidad, título, URL, tema, autoridad y tipo). La consulta
   usa `query_points` con filtro por *payload* en una sola etapa.
   - Con `QDRANT_URL` se usa un servidor de Qdrant y su índice HNSW (ANN, `hnsw_ef=128`).
   - Sin ella, el modo local embebido en `data/module2/qdrant` (fuera de Git). Ese modo guarda la misma
     colección y filtros, pero busca de forma exacta.
   - Si la colección falta, la recuperación vuelve a `numpy` y lo anota en la traza.
   - El modo demo crea la colección en memoria.
2. **Perfil en el Store**: la herramienta de escritura `save_profile` guarda nombre, trabajo, cargo y ciudad
   en el namespace `("users", user_id, "profile")`.
   - Su esquema es Pydantic y pasa por aprobación humana, como toda escritura.
   - «¿Dónde trabajo?» se responde sin buscar, desde el Store (largo plazo) o desde el hilo (corto plazo), y
     la respuesta dice de qué memoria sale el dato.
   - `forget_memory` también borra el perfil.
3. **Ruta `mixed`**: el enrutador (`prompts/router.md` 1.1 y heurística demo) la elige cuando la pregunta
   pide comparar un dato con un texto. La cadena consulta la tabla y los documentos en el mismo turno; el
   agente decide sus herramientas.
4. **Streaming SSE**: `POST /api/chat/stream` emite `route`, `retrieval`/`tool`, `token` y `done`. El evento
   `done` lleva el mismo turno validado de `/api/chat`; si la validación de citas cambia el texto, la
   interfaz muestra el validado.
5. **Observabilidad**:
   - Cada turno lleva `run_name`, etiquetas y metadatos para LangSmith (`LANGSMITH_TRACING`,
     `LANGSMITH_API_KEY` y `LANGSMITH_PROJECT`).
   - Cada turno también se escribe como JSON en `$MANUELITA_STATE_DIR/logs/turns.jsonl`, sin la pregunta ni
     el usuario.
   - `GET /api/observability` informa el estado.
6. **Herramienta estructurada**:
   - `query_structured` declara `args_schema` Pydantic y cuenta entidades en la herramienta. La cadena
     antepone ese conteo como hecho citado, así que el modelo no hace aritmética.
   - `agent build-structured` exporta la tabla a `facts.csv` y `entities.json`.

## Alternativas consideradas

| Alternativa | Motivo para no elegirla |
|-------------|-------------------------|
| Mantener `numpy` y justificarlo | La rúbrica nombra Qdrant y ANN de forma explícita en el ítem 2.2 y en el checklist obligatorio. |
| Qdrant solo con servidor (Docker) | Docker no está disponible en los equipos del equipo; el modo local garantiza que la demo corre en cualquier clon. |
| Reemplazar SQLite por CSV en la herramienta estructurada | La tabla SQLite ya cumple «solo lectura, cita por fila». La exportación CSV/JSON muestra los mismos datos sin duplicar la lógica. |
| Guardar el perfil sin aprobación | Viola la regla de oro «lectura automática, escritura con aprobación» (constitución, Fase 2, regla 9). |

## Consecuencias

- Nueva dependencia: `qdrant-client`. La colección se reconstruye con `uv run python -m
  proyecto_modelos_lenguaje.rag qdrant build` (unos 2 minutos en modo local para 15.211 fragmentos).
- El modo local de Qdrant bloquea la carpeta a un solo proceso. Con la API abierta, la CLI vuelve a `numpy` y
  lo anota.
- Constitución 1.5.0: Fase 2, reglas 2, 6, 7 y 12, y §8.3 con la rúbrica oficial.
- `docs/rubrica_modulo2.md` mapea cada ítem de la rúbrica con su evidencia y el guion de 15 minutos.
