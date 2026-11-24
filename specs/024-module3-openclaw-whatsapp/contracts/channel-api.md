# Contrato: API del canal (puente OpenClaw → Valer-IA)

Todas las rutas nuevas viven en `api.py`; modelos en `api_models.py`. Solo aceptan conexiones desde loopback
(`127.0.0.1`/`::1`) y exigen `X-Channel-Token: ${VALERIA_CHANNEL_TOKEN}` (comparación en tiempo constante). Sin token o
desde otra IP → `403 channel_forbidden`. Sin `VALERIA_CHANNEL_TOKEN` configurado → las rutas responden `503
channel_disabled`.

## 1. `POST /api/channels/messages`

Un mensaje entrante ya admitido por el gateway (allowlist/emparejamiento).

```json
{
  "channel": "whatsapp",
  "message_id": "3EB0C4A1F2...",
  "sender": "+573001234567",
  "kind": "text",
  "text": "¿Qué produce Manuelita?",
  "received_at": "2026-11-28T13:05:12Z"
}
```

Validación: `channel ∈ {whatsapp, telegram}`; `message_id` 1–128; `sender` E.164 `^\+[1-9]\d{7,14}$` (Telegram: id
numérico `^tg:\d{1,20}$`); `kind` del enumerado; `text` ≤ 4.000 (requerido si `kind = text`).

Respuesta `200`:

```json
{
  "status": "answered",
  "messages": ["Manuelita produce *azúcar*, bioetanol… [1]\n\nFuentes:\n[1] Informe de Sostenibilidad 2023-2024, p. 8 — https://…"],
  "thread_id": "6f1c…",
  "route": "documental",
  "tools": ["search_documents"],
  "latency_ms": 5321
}
```

Comportamiento:

| Situación | `status` | Mensajes |
|---|---|---|
| Turno normal | `answered` | Respuesta formateada (1–4 mensajes, ≤ 1.500 caracteres c/u). |
| Turno que propone una escritura | `pending_approval` | Resumen de la acción + «Responde *SÍ* para confirmar o *NO* para cancelar (vence en 10 min)». |
| Hay pendiente y llega sí/no | `approval_resolved` | Resultado de `resume` (ejecutada o cancelada). |
| `kind` ≠ text | `unsupported` | «Por ahora solo leo mensajes de texto…» (o transcripción si `voice_notes` está activo). |
| `message_id` repetido | `ignored` | `[]` (el puente no envía nada). |
| Turno en curso del mismo usuario | `busy` | «Sigo con tu mensaje anterior; enseguida te respondo.» |
| Comando `/nuevo` | `answered` | Confirma hilo nuevo (el perfil se conserva). |
| Comando `/olvidar` | `pending_approval` | Propone `forget_memory(scope="all")`. |
| Comando `/ayuda` | `answered` | Qué sabe hacer y comandos. |
| Comando `/traza` | `answered` | Ruta, plan y herramientas del último turno (modo técnico para la sustentación). |
| Error del modelo/servicio | `error` | Mensaje breve de indisponibilidad; HTTP 200 para que el puente no reintente en bucle. |

Errores HTTP: `400 channel_invalid` (validación), `403 channel_forbidden`, `503 channel_disabled`, `500 channel_error`
(sin trazas internas). Timeout del puente: 45 s; si vence, el plugin no maneja el turno y responde el agente nativo
(modo degradado).

## 2. `GET /api/channels/status`

```json
{
  "enabled": true,
  "channels": {"whatsapp": {"last_message_at": "…", "messages_1h": 37, "errors_1h": 0, "p90_latency_ms": 8200}},
  "model": {"provider": "deepseek", "model": "deepseek-flash", "ok": true},
  "qdrant": {"mode": "server", "ok": true},
  "pending_approvals": 1
}
```

## 3. `GET /api/tools`

Catálogo público (sin token, también para la web): `[{name, description, kind, requires_approval, routes, mcp,
schema}]` donde `schema` es el JSON Schema del modelo Pydantic. Orden estable por número del catálogo.

## 4. Plugin `valeria-bridge` (lado OpenClaw)

- Hook `before_dispatch` (research R1, hallazgos del spike: recibe el mensaje ya autenticado con `messageId`, `content`, `channel`, `senderId`, `isGroup`); solo canales `whatsapp` (y `telegram` si se activa).
- Construye el cuerpo §1 a partir del evento (`cleanedBody`, remitente, id del mensaje, tipo) y llama
  `http://127.0.0.1:${VALERIA_BACKEND_PORT:-8000}/api/channels/messages` con `X-Channel-Token`.
- `status ∈ {answered, pending_approval, approval_resolved, unsupported, busy, error}` → `{ handled: true, reply: { text:
  messages.join("\n\n") } }` (o varios envíos si el SDK lo permite; **verificar**).
- `ignored` → `{ handled: true, reply: null }` (**verificar** que el SDK admite no responder; si no, texto vacío no se
  envía).
- Excepción de red o timeout → `undefined` (no maneja; responde el agente nativo con DeepSeek + MCP).
- Configuración: `plugins.entries.valeria-bridge: { enabled: true, hooks: { allowConversationAccess: true }, config: {
  backendUrl, timeoutMs: 45000 } }`; el token se lee de `${VALERIA_CHANNEL_TOKEN}`.

## 5. Formato del canal

`channels/format.py`: Markdown → WhatsApp (`**x**`→`*x*`, `_x_`, títulos → negrita, tablas → líneas `•`), `[U#]`/`[F#]`
→ `[n]` numeradas por orden de aparición, bloque «Fuentes:» con título ≤ 80 caracteres y URL (página si existe). Corte
por frases a 1.500 caracteres, máximo 4 mensajes; el resto se resume en «(respuesta abreviada; pídeme más detalle)».
