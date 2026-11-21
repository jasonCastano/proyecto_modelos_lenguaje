# Contrato: cambios en la API y la web (spec 020)

Todos los cambios son **aditivos y opcionales**. Los clientes de las specs 018 y 019 siguen funcionando sin
modificaciones.

## `RouteModel` (`ChatResponse.turn.route`, eventos `route`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `act` | `DialogueAct \| null` | Nuevo. Etiqueta controlada del acto de diálogo |

El esquema `specs/014-rag-agent-memory-router/contracts/route-decision.schema.json` añade `act`, opcional, con su
enum.

## `ChatResponse.notices`

Valores nuevos:
- `review_retry`: la respuesta se regeneró una vez tras la revisión;
- `review_fallback`: se usó la respuesta de respaldo.

Solo se muestran en la vista técnica.

## `ContactRecordModel` (`ChatResponse.contact`, `ThreadView.contact`)

| Campo | Tipo | Notas |
|-------|------|-------|
| `turns` | `ContactTurnModel[]` | Nuevo, con un máximo de 50 entradas |

`ContactTurnModel = { act: DialogueAct, bridged: boolean, reviewed: "show" | "retry" | "fallback" }`.

Siempre son etiquetas controladas, sin texto del visitante, sin nombre y sin datos personales (FR-018 y FR-029). Los
modelos usan `extra="forbid"`, igual que los demás.

## Streaming (`/api/chat/stream`)

- Los turnos de `converse` **no** emiten eventos `token`. El cliente ve `route` y luego `done`, con la respuesta ya
  revisada.
- El texto de la etapa en vivo para estas rutas es «Pensando la respuesta…». Hoy es «Respondiendo sin buscar…».
- La voz (spec 016) empieza a leer con el `done` en estos turnos. Ya lo hace así cuando no hay tokens.

## Web (`web/src`)

- `lib/types.ts`: `DialogueAct`, `ChatRoute.act` y `ContactRecord.turns`.
- `components/ContactRecordPanel.tsx`: una línea nueva, «Actos», con la secuencia de actos del hilo; marca los turnos
  con puente (◆) y los que usaron respaldo (↺). Solo en `?vista=tecnica`.
- `components/ChatView.tsx`: etiqueta de la etapa para `converse`.
- La vista de visitante no cambia visualmente.

## CLI

- Subcomando nuevo: `agent converse` (ver [conversation.md](./conversation.md) §7).
- `agent care` acepta `--conversation-mode guided|scripted`. Por defecto usa el valor de la configuración.
