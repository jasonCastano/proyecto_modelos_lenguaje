# Contrato: API de conversación del agente RAG

**Feature**: `014-rag-agent-memory-router` | **Fecha**: 2026-11-10 | **Autor**: Roberto José Guerrero

Endpoints nuevos de FastAPI (`src/proyecto_modelos_lenguaje/api.py`). `/api/ask`, `/api/summary` y `/api/faq` se
conservan sin cambios. Todas las respuestas son JSON UTF-8; los errores siguen el formato existente
`{"error": {"code": str, "message": str}}`. Ningún endpoint escribe en `data/` ni en el repositorio: el estado vive
en `MANUELITA_STATE_DIR`.

## POST `/api/chat`

Envía un mensaje a un hilo (lo crea si `thread_id` es nulo).

**Request**

```json
{
  "thread_id": "8f6c1e0a-…" ,
  "user_id": "anon-3b9f…",
  "message": "¿Y dónde lo produce?",
  "variant": "agent",
  "mode": "real"
}
```

| Campo | Tipo | Regla |
|-------|------|-------|
| `thread_id` | UUID4 o `null` | `null` crea un hilo nuevo; un UUID desconocido → 404 `thread_not_found`. |
| `user_id` | str 1–64 `[A-Za-z0-9-]` | Anónimo; namespace de la memoria larga. |
| `message` | str 1–500, sin caracteres de control | Igual que `question_max_chars` del Módulo 1. |
| `variant` | `chain` \| `agent` | Por defecto `chain`; no cambia dentro de un hilo (409 `variant_mismatch`). |
| `mode` | `real` \| `demo` | `demo` usa modelo y embeddings guionados (FR-021). |

**Response 200** — `status` ∈ `answered`, `fallback`, `clarify`, `pending_approval`

```json
{
  "thread_id": "8f6c1e0a-…",
  "turn": {
    "turn_id": 2,
    "question": "¿Y dónde lo produce?",
    "route": {"route": "documental", "confidence": 0.86, "reason": "pregunta por ubicación de producción", "decided_by": "llm", "alternative": "structured", "fallback_route": null},
    "fragments": [{"label": "U1", "unit_id": "unit_…", "title": "…", "url": "https://…", "score": 0.81, "lexical_score": 0.42, "semantic_score": 0.88, "anomalous": false}],
    "structured_rows": [],
    "answer": "Manuelita produce azúcar en el Valle del Cauca [U1] …",
    "citations": [{"label": "U1", "unit_id": "unit_…", "url": "https://…"}],
    "fallback": false,
    "metrics": {"latency_ms": 4210, "model_calls": 2, "tool_calls": 1, "input_tokens": 3120, "output_tokens": 210}
  },
  "status": "answered",
  "pending_action": null,
  "anomalies": []
}
```

- `route` sigue [route-decision.schema.json](./route-decision.schema.json).
- `fragments` reutiliza la forma de `RetrievedFragment` de la spec 013 (`contracts/retrieval-trace.md`) más
  `anomalous`.
- `structured_rows[]`: `{"fact_id", "subject_label", "attribute", "value", "year", "citations": [{"url", "title"}]}`.
- `direct` y `out_of_scope` → `fragments=[]`, `structured_rows=[]`, `metrics.tool_calls=0`.
- `clarify` → `answer` es la pregunta de aclaración; sin citas.
- `pending_approval` → `pending_action` no nulo y `answer` vacío hasta reanudar.

**Errores**: 400 `empty_question` / `question_too_long`; 404 `thread_not_found`; 409 `variant_mismatch` o
`thread_pending_approval` (hay una acción sin resolver); 503 `index_unavailable` (con acción «reconstruir»);
502/504 `model_error` / `model_timeout`.

## GET `/api/threads/{thread_id}`

Devuelve el historial visible del hilo.

```json
{"thread_id": "…", "variant": "chain", "turns": [ /* Turn */ ], "summary": "…", "status": "idle", "pending_action": null}
```

`status` ∈ `idle`, `pending_approval`. 404 `thread_not_found`. Incluye además `actions[]`: registro de
decisiones humanas (`action_id`, `tool`, `args` finales, `decision`, `proposed_at`, `decided_at`).

## POST `/api/threads/{thread_id}/resume`

Resuelve una acción pendiente (HITL) y continúa el hilo con `Command(resume=...)`.

**Request**

```json
{"action_id": "act_01", "decision": "edit", "args": {"key": "response_format", "value": "viñetas"}}
```

| Campo | Regla |
|-------|-------|
| `decision` | `approve` \| `edit` \| `reject`. |
| `args` | Solo con `edit`; se valida contra el esquema de la herramienta. |

**Response 200**: misma forma que `POST /api/chat`. **Errores**: 404 `thread_not_found`; 409
`no_pending_action` o `action_mismatch`; 400 `invalid_args` (edición que no cumple el esquema). Funciona tras reiniciar el servidor (checkpointer SQLite, US4-3).

## GET `/api/memory/{user_id}` · DELETE `/api/memory/{user_id}`

- **GET** → `{"user_id": "…", "items": [{"key": "response_format", "value": "viñetas", "created_at": "…", "expires_at": "…"}]}`.
- **DELETE** → no borra directamente: crea una acción `forget_memory` pendiente y responde 202
  `{"status": "pending_approval", "pending_action": {...}}`. Se confirma con `/resume` en el hilo indicado por
  `thread_id` (query param obligatorio). Regla de oro: escritura con aprobación.

## Garantías transversales

1. Toda respuesta factual trae al menos una cita resoluble o `fallback=true` (SC-003).
2. Los fragmentos con `anomalous=true` aparecen en `anomalies[]` con su motivo; nunca se ejecuta su contenido
   (FR-016).
3. Ninguna herramienta de escritura se ejecuta sin un registro de decisión en el estado del hilo (SC-009).
4. `mode=demo` es determinista: la misma secuencia de mensajes produce la misma respuesta y la misma ruta.
