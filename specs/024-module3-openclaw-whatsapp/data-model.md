# Data Model: Entrega final del Módulo 3

**Fecha**: 2026-11-23 | **Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md)

Todo el estado nuevo vive en `$MANUELITA_STATE_DIR` (fuera del repositorio), igual que los checkpoints y el Store del
Módulo 2. Ningún registro guarda números de teléfono completos ni el texto de los mensajes fuera del checkpointer.

## 1. ChannelUser (usuario de canal)

| Campo | Tipo | Regla |
|---|---|---|
| `user_id` | str | `wa-` + 16 hex de `HMAC-SHA256(VALERIA_CHANNEL_SALT, e164)`; cumple `^[A-Za-z0-9-]{1,64}$`. Clave. |
| `channel` | Literal["whatsapp", "telegram"] | Canal de origen. |
| `masked` | str | Solo para mostrar al equipo: `+57 ••• ••• 1234` (últimos 4 dígitos). Nunca en archivos versionados. |
| `first_seen` / `last_seen` | datetime (UTC) | |
| `active_thread_id` | str (UUID) | Hilo activo; cambia con `/nuevo`. |

El estado autorizado/no autorizado lo decide OpenClaw (`allowFrom` + emparejamiento); el backend solo recibe mensajes
ya admitidos por el gateway y autenticados con `X-Channel-Token`.

Tabla `channel_users` en `channels.sqlite3`.

## 2. ChannelThread (hilo de canal)

| Campo | Tipo | Regla |
|---|---|---|
| `thread_id` | str (UUID) | Mismo identificador que usa el `SqliteSaver`; equivale al hilo de la web. |
| `user_id` | str | FK → ChannelUser. |
| `created_at` | datetime | |
| `closed_at` | datetime \| None | Se fija al abrir otro con `/nuevo`; el hilo cerrado sigue legible. |

Transiciones: `activo → cerrado` (solo con `/nuevo`). Sobrevive a reinicios porque el checkpointer y esta tabla son
SQLite en disco.

## 3. InboundMessage (mensaje entrante)

| Campo | Tipo | Regla |
|---|---|---|
| `message_id` | str (1–128) | Id del canal; **clave de deduplicación** (tabla `channel_seen`, retención 48 h). |
| `channel` | Literal | |
| `sender` | str | E.164 (`^\+[1-9]\d{7,14}$`); se convierte en `user_id` y se descarta. |
| `kind` | Literal["text", "audio", "image", "video", "document", "sticker", "location", "other"] | |
| `text` | str \| None | ≤ 4.000 caracteres; se recorta a 2.000 para el agente (mismo límite que `ChatRequest`). |
| `received_at` | datetime | |

No se persiste completo: solo `message_id` (dedupe) y el turno que el checkpointer ya guarda.

## 4. ChannelReply (respuesta)

| Campo | Tipo | Regla |
|---|---|---|
| `messages` | list[str] (1–4) | Texto en formato WhatsApp, cada uno ≤ 1.500 caracteres, cortado por frases. |
| `thread_id` | str | |
| `status` | Literal["answered", "pending_approval", "approval_resolved", "unsupported", "busy", "error", "ignored"] | |
| `route` | str \| None | Ruta del router (`direct`, `documental`, `structured`, `mixed`, `out_of_scope`, `clarify`). |
| `tools` | list[str] | Herramientas invocadas en el turno. |
| `latency_ms` | int | |

## 5. PendingApproval (aprobación pendiente en el canal)

| Campo | Tipo | Regla |
|---|---|---|
| `thread_id` | str | Una sola pendiente por hilo. |
| `action_id` | str | El de `ChatService` (HITL del Módulo 2). |
| `tool` | str | Herramienta de escritura propuesta. |
| `summary` | str | Texto legible de la acción y sus argumentos. |
| `expires_at` | datetime | `created_at + 10 min`. |
| `state` | Literal["pending", "approved", "rejected", "expired"] | |

Transiciones: `pending → approved` (respuesta afirmativa) · `pending → rejected` (negativa o `/cancelar`) ·
`pending → expired` (vence; se llama `resume(..., decision="reject")`). Ninguna acción se ejecuta fuera de `approved`.

Tabla `channel_pending`.

## 6. ToolSpec (herramienta del catálogo)

| Campo | Tipo | Regla |
|---|---|---|
| `name` | str | `^[a-z][a-z0-9_]{2,40}$`, único. |
| `description` | str | Español, 20–300 caracteres; dice qué hace y cuándo usarla. |
| `args_schema` | type[BaseModel] | Pydantic v2, `extra="forbid"`, cada campo con tipo, descripción y restricciones. |
| `kind` | Literal["read", "write"] | |
| `requires_approval` | bool | `True` si y solo si `kind == "write"` (validado al cargar el catálogo). |
| `routes` | frozenset[str] | Rutas del router en las que se ofrece. |
| `mcp` | bool | Se expone por MCP; siempre `False` para `write`. |
| `data_source` | str | Origen (`gold/knowledge_units`, `curated/series_anuales.csv`, `config/...`, `store`, …). |

Invariantes del catálogo: ≥ 20 entradas; nombres únicos; toda herramienta tiene al menos una prueba de contrato
(`tests/unit/agent/tools/test_<name>.py` o parametrizada). Lista completa en
[contracts/tools-catalog.md](contracts/tools-catalog.md).

## 7. ToolInvocation (invocación en la traza)

Se extiende el registro de herramientas de la traza del turno (`TurnModel.trace.tools`):

| Campo | Tipo | Regla |
|---|---|---|
| `name` | str | |
| `args` | dict | Argumentos **ya validados**. |
| `ok` | bool | |
| `error` | str \| None | Mensaje de validación o ejecución, sin trazas internas. |
| `duration_ms` | int | |
| `summary` | str | ≤ 200 caracteres del resultado. |
| `step` | int | Orden dentro del turno (ReAct). |

Y el turno añade `plan_steps: list[str]` (pasos previstos según ruta y herramientas ofrecidas, p. ej.
`["consultar series: cana_molida 2022–2024", "comparar variación", "responder con cita"]`), generado sin LLM a partir de
la ruta, la intención y las herramientas candidatas; se completa con los pasos realmente ejecutados.

## 8. Workspace (OpenClaw)

| Archivo | Versionado | Contenido |
|---|---|---|
| `SOUL.md` | Sí (`openclaw/workspace/`) | Persona y tono de Valer-IA Caña. |
| `IDENTITY.md` | Sí | Nombre, emoji, presentación corta. |
| `AGENTS.md` | Sí | Reglas operativas, red lines y sección `## Tools`. |
| `USER.md` | Sí | Público objetivo (invitados de empresas, visitantes); sin datos personales. ≤ 4.000 caracteres. |
| `MEMORY.md` | Sí | Memoria curada del dominio y de la operación. |
| `skills/valeria-manuelita/SKILL.md` | Sí | Skill propio. |
| `memory/YYYY-MM-DD.md` | **No** (workspace de ejecución) | Bitácora diaria generada por el backend: hora, `user_id` seudónimo, ruta, herramientas, latencia, estado. |

## 9. ChannelLogRecord (`$MANUELITA_STATE_DIR/logs/channels.jsonl`)

`ts`, `channel`, `user_id` (seudónimo), `thread_id`, `message_id_hash`, `kind`, `status`, `route`, `tools`,
`latency_ms`, `model_calls`, `error_code`. Nunca texto ni número.

## 10. EvalQuery y ProjectionPoint (ítem 2.3)

- **EvalQuery** (`tests/fixtures/rag/module3_queries.jsonl`): `id`, `question`, `expected_unit_ids` (≥ 1), `topic_id`,
  `source_question_id` (de `eval_questions.jsonl`). 30 entradas, elegidas con semilla 2026 antes de evaluar.
- **ProjectionPoint** (`docs/proyeccion_embeddings.json`): `id`, `kind` (`fragment`|`query`), `x`, `y`, `topic_id`,
  `unit_id` (fragmentos), `recall_at_10` y `failed` (consultas).

## 11. CorpusRebuildManifest

`run_id`, `started_at`, `finished_at`, `from` (`bronze`|`silver`), `workdir`, etapas (`silver`, `gold`, `index`,
`qdrant`) con conteos, duración y hash SHA-256 de cada salida, `fragments_with_provenance` / `fragments_total`, commit
de Git y versión de Python. Se escribe en `<workdir>/manifest.json`.
