# Research: Entrega final del Módulo 3 (OpenClaw, WhatsApp y 20 herramientas)

**Fecha**: 2026-11-23 | **Spec**: [spec.md](spec.md) | **Plan**: [plan.md](plan.md)

Fuentes de OpenClaw: documentación oficial leída el 2026-11-23 (`https://docs.openclaw.ai`, índice en
`/llms.txt`). Las claves marcadas como **verificar** no se pudieron confirmar literalmente y se comprueban con
`openclaw config get` / `openclaw doctor` en la tarea de instalación antes de versionar la configuración.

---

## R1. Cómo conectar Valer-IA con OpenClaw

**Decisión**: **plugin puente propio** (`valeria-bridge`, TypeScript) que usa el hook `before_agent_reply` para enviar
cada mensaje entrante de WhatsApp al backend FastAPI (`POST /api/channels/messages`, solo loopback, con token) y
devolver la respuesta de Valer-IA (`{ handled: true, reply: { text } }`). Si el backend no responde a tiempo o está
caído, el hook no maneja el turno y **responde el agente nativo de OpenClaw** con DeepSeek (primario y respaldo) y el
**servidor MCP propio** `valeria-tools` (herramientas de solo lectura), bajo las reglas de `AGENTS.md`.

**Razones**:

- El razonamiento, el router (reglas → Jev → LLM), la memoria (`SqliteSaver` + `SqliteStore`), el blindaje y las citas
  siguen siendo los de Valer-IA: web y WhatsApp se comportan igual (FR-003) y los ítems 1.2 y 1.3 se demuestran con lo
  que ya está evaluado.
- OpenClaw aporta lo que la rúbrica pide de él (gateway, canal, emparejamiento, workspace, skills/MCP, sandbox,
  auditoría) y, además, un **modo degradado real**: si el backend cae, el bot sigue contestando (edge case y FR-006).
- El hook está documentado (`plugins/hooks`) y requiere `plugins.entries.valeria-bridge.hooks.allowConversationAccess:
  true`, un permiso explícito que el equipo puede mostrar (ítem 3.4).

**Alternativas consideradas**:

- *Proveedor de modelo personalizado* (`models.providers.<id>` con `api: "openai-completions"`) apuntando a un endpoint
  OpenAI-compatible del backend: no requiere TypeScript, pero OpenClaw antepone su prompt de sistema y sus definiciones
  de herramientas y espera semántica de modelo (streaming, tool calls); el backend tendría que fingir ser un LLM.
  Rechazada por frágil.
- *Solo MCP* (el agente nativo de OpenClaw con DeepSeek usa las 20 herramientas por MCP): documentado y sencillo, pero
  sustituye el router, la memoria y el blindaje evaluados en el Módulo 2 por los de OpenClaw; se perdería la evidencia de
  1.2/1.3 y habría dos agentes con conductas distintas en web y WhatsApp. Se conserva **como modo degradado**.
- `/hooks/agent` y `/v1/chat/completions` de OpenClaw: van en sentido contrario (alguien externo llama a OpenClaw); se usa
  `/hooks/agent` solo si hace falta un envío proactivo (no previsto).

### Hallazgos del spike (T007, 2026-11-23, `openclaw@2026.11.7`, tipos del SDK y docs del paquete)

- Se usa **`before_dispatch`** y no `before_agent_reply`: recibe el mensaje entrante **ya autenticado** (después de
  `dmPolicy`/`allowFrom`/emparejamiento) antes de cualquier llamada al modelo, y su evento trae lo que el puente
  necesita: `messageId`, `content`/`body`, `channel`, `senderId`, `sessionKey`, `isGroup`, `timestamp`. El
  `cleanedBody` de `before_agent_reply` es el prompt preparado (con contexto del canal), no el texto del remitente.
- Resultado: `{ handled: true, text }` envía una respuesta final; `{ handled: true }` sin texto atiende en silencio
  (duplicados); devolver `undefined` deja seguir el despacho normal → **modo degradado** (agente nativo + MCP).
- Una sola respuesta por turno: los mensajes del backend se unen con línea en blanco; el canal trocea a 4.000
  caracteres (`textChunkLimit`).
- `senderId` puede llegar como E.164 o como JID (`573001234567@s.whatsapp.net`); el backend normaliza ambos a E.164
  antes del seudónimo. Los adjuntos llegan como marcadores `<media:image>`, `<media:audio>`… en el contenido.
- Registro: `definePluginEntry` de `openclaw/plugin-sdk/plugin-entry`, `api.on(hook, handler)`, configuración en
  `api.pluginConfig` (validada por `configSchema` de `openclaw.plugin.json`). Instalación local:
  `openclaw plugins install --link ./openclaw/plugins/valeria-bridge --force` y `openclaw plugins enable
  valeria-bridge`. `before_dispatch` no requiere `allowConversationAccess`; se declara igual por transparencia.
- Pendiente de confirmar con el gateway vivo: que `before_dispatch` corre para DMs de WhatsApp en la versión instalada
  (la documentación lo cita para Telegram) y el formato exacto de `senderId`.

## R2. Instalación y servicio en el PC del equipo (Windows)

**Decisión**: OpenClaw nativo en Windows 11 (Node 24.22.1 ya instalado ≥ 24.16 requerido), `npm install -g
openclaw@latest`, plugin oficial `@openclaw/whatsapp`, servicio con `openclaw gateway install` (tarea programada con
disparadores de arranque e inicio de sesión) y `openclaw gateway restart --wait 30s` tras cada cambio. El backend
(`uvicorn`) se registra también como tarea programada (script `scripts/serve_backend.ps1`) con reinicio ante fallo.
Suspensión desactivada (`powercfg`), inicio de sesión automático del usuario de servicio.

**Razones**: la documentación recomienda el modo nativo en Windows cuando está disponible; WSL2 añadiría otra capa
(systemd, red). Windows Server no está soportado, pero el PC es Windows 11.

**Alternativas**: WSL2 + systemd (más compatible con Linux, más piezas); VM en la nube (descartada por el equipo).

## R3. Túnel

**Decisión**: **WhatsApp no necesita túnel**: el canal usa WhatsApp Web (Baileys) con conexión **saliente** desde el
gateway, así que el bot funciona detrás de NAT sin abrir puertos. El túnel (**Cloudflare Tunnel**, `cloudflared`, sin
cuenta para el *quick tunnel* o con cuenta para nombre fijo) solo expone la **web** de Valer-IA por HTTPS para que los
invitados también la vean (y para que el micrófono funcione fuera de `localhost`). El gateway (18789) nunca se expone:
sigue en `bind: "loopback"` con token.

**Razones**: menor superficie de ataque; la parte obligatoria (WhatsApp) no depende del túnel.

**Alternativas**: ngrok (límite de sesiones en plan gratuito), Tailscale Funnel (requiere cuenta y nodos), abrir puertos
del router (inseguro, depende de la red del sitio).

## R4. Configuración versionada y secretos

**Decisión**: plantilla versionada `openclaw/openclaw.json5` (JSON5, `$schema` permitido) con `${VAR}` para todo
secreto; el servicio arranca con `OPENCLAW_CONFIG_PATH=<repo>/openclaw/openclaw.json5`,
`OPENCLAW_STATE_DIR=%USERPROFILE%\.openclaw-valeria` y `OPENCLAW_WORKSPACE_DIR=%USERPROFILE%\.openclaw-valeria\workspace`.
Los secretos (`DEEPSEEK_API_KEY`, `OPENCLAW_GATEWAY_TOKEN`, `VALERIA_CHANNEL_TOKEN`, `VALERIA_CHANNEL_SALT`) viven en
`%USERPROFILE%\.openclaw-valeria\.env` y en el `.env` del proyecto, ambos fuera de Git. La validación estricta de
OpenClaw (claves desconocidas impiden el arranque, código 78) se cubre con `openclaw config file` + `openclaw doctor` en
la verificación.

**Puntos a verificar** en la instalación: anidamiento exacto de `session.dmScope`, `tools.fs.workspaceOnly`,
`tools.exec.*`, forma de `mcp.servers` con `env`.

## R5. Modelo primario y respaldo

**Decisión**: `agents.defaults.model.primary = "deepseek/deepseek-flash"` y `fallbacks = ["deepseek/deepseek-v4-pro"]`
(proveedor `deepseek`, `DEEPSEEK_API_KEY`). Es el mismo modelo que ya usa el backend (`config/llm.toml`:
`deepseek-flash`), así que hay una sola cuenta, cuota y facturación. Nada de Ollama en la demo (FR-010).

**Nota**: la documentación de OpenClaw indica que `deepseek-chat`/`deepseek-reasoner` se retiraron el 2026-07-24; el
proyecto ya usa `deepseek-flash`, sin cambios.

## R6. WhatsApp con el número de un integrante

**Decisión**:

```json5
channels: { whatsapp: {
  dmPolicy: "pairing",                 // desconocidos piden código; el equipo aprueba
  allowFrom: ["${WA_ALLOW_1}", ...],   // E.164 de integrantes e invitados confirmados (desde .env)
  groupPolicy: "disabled",             // nunca en grupos (FR-001a)
  selfChatMode: false,                 // ignora lo que escribe el propio titular
} }
```

Aprobación: `openclaw pairing list whatsapp` → `openclaw pairing approve whatsapp <CODE>` (vence en 1 h, máx. 3
pendientes). Vinculación por QR: `openclaw channels login --channel whatsapp`. Diagnóstico: `openclaw channels status
--probe`.

**Razones**: combina lista de autorizados E.164 (rúbrica 3.2) con emparejamiento para invitados no registrados
(aclaración de la spec). `groupPolicy: "disabled"` y `dmScope` por remitente evitan tocar los chats del titular.

**Riesgo**: un número personal con muchos chats recibe mensajes de contactos que no son invitados; con `pairing` esos
contactos recibirían el mensaje de emparejamiento. **Mitigación**: durante la jornada se usa `pairing`; antes y después,
`dmPolicy: "allowlist"` (cambio en caliente con `openclaw config set`). Verificar en la instalación si el mensaje de
emparejamiento puede personalizarse o silenciarse para contactos existentes; si no, el titular avisa a sus contactos.

**Alternativas**: SIM dedicada (recomendada por OpenClaw, descartada por el equipo); WhatsApp Business Cloud API
(verificación de Meta fuera de plazo).

## R7. Identidad, hilos y comandos del canal

**Decisión**:

- `user_id = "wa-" + HMAC-SHA256(VALERIA_CHANNEL_SALT, e164)[:16]` (cumple `^[A-Za-z0-9-]{1,64}$`); el número completo
  nunca se guarda ni se registra (FR-013, FR-025).
- Hilo activo por usuario en una tabla `channel_threads` del estado (`$MANUELITA_STATE_DIR/channels.sqlite3`):
  `thread_id` UUID persistente → sobrevive reinicios (FR-023). Comando `/nuevo` abre otro hilo (para demostrar que el
  perfil se recupera en un hilo nuevo, US4); `/olvidar` propone `forget_memory`; `/ayuda` lista capacidades.
- Variante `agent` siempre en el canal (es la que usa herramientas); `mode` = `real`.

## R8. Human-in-the-loop por WhatsApp

**Decisión**: cuando el turno termina en `pending_approval`, el puente envía un texto con la acción y sus argumentos
legibles y «Responde *SÍ* para confirmar o *NO* para cancelar». El siguiente mensaje del mismo usuario se interpreta
primero como decisión (`sí|si|confirmo|dale|ok` → `approve`; `no|cancela` → `reject`; otro texto → se recuerda la
pendiente). Vencimiento de 10 minutos (`channel_pending.expires_at`): al vencer se rechaza sin ejecutar (edge case).
Usa el mismo `ChatService.resume` que la web.

## R9. Catálogo de 20 herramientas

**Decisión**: un registro único `agent/catalog.py` que declara las 20 herramientas (nombre, descripción en español,
esquema Pydantic, tipo lectura/escritura, requiere aprobación, rutas en las que se ofrecen) y del que salen: las
herramientas del agente LangGraph, el servidor MCP, el endpoint `GET /api/tools` y la documentación generada
(`docs/herramientas.md`). Detalle en [contracts/tools-catalog.md](contracts/tools-catalog.md).

**Razones**: una sola fuente evita que el MCP, la traza y la documentación diverjan; el evaluador ve el catálogo en un
comando (`agent tools --json`).

**Router**: la ruta sigue decidiéndose con reglas → Jev → LLM; cada ruta ofrece al agente un **subconjunto** del catálogo
(`documental` → búsqueda, fragmento, sostenibilidad, FAQ, resumen, noticias; `structured` → consultas, series,
comparación, entidades, cálculo; `direct` → ninguna; las de escritura solo cuando el detector de intención lo indica).
Así se cumple «no busca por reflejo» y el plan es legible. El **plan** (`agent/plan.py`, ya existente) se expone en la
traza como lista de pasos previstos y se resume en el canal solo en modo técnico (`/traza`).

## R10. Servidor MCP propio y skill

**Decisión**: servidor MCP en Python con el SDK oficial `mcp` (FastMCP), transporte **stdio**, módulo
`proyecto_modelos_lenguaje.mcp_server`, que expone **solo las 15 herramientas de lectura** del catálogo (las de
escritura exigen HITL y quedan fuera). Registro: `openclaw mcp add valeria-tools --command uv --arg run --arg python
--arg -m --arg proyecto_modelos_lenguaje.mcp_server --cwd <repo>`, con `toolFilter.include` explícito. Además un skill
del workspace `skills/valeria-manuelita/SKILL.md` que explica cuándo usar esas herramientas y que requiere el binario
`uv` (`metadata.openclaw.requires.bins`).

**Razones**: MCP nativo en OpenClaw (`mcp.servers`), lenguaje del proyecto, reutiliza el catálogo; permisos declarados
(ítem 3.4). El skill documenta el uso para el agente nativo.

**Dependencia nueva**: `mcp` (SDK oficial). Justificación: es el protocolo que pide la rúbrica; alternativa de escribir
JSON-RPC a mano descartada.

## R11. Workspace

**Decisión**: plantillas versionadas en `openclaw/workspace/` (`SOUL.md`, `IDENTITY.md`, `AGENTS.md`, `USER.md`,
`MEMORY.md`, `skills/`) copiadas al workspace de ejecución con `make openclaw-workspace` (o `pml ops workspace sync`);
`agents.defaults.skipBootstrap: true` para que OpenClaw no las reemplace. La **bitácora diaria**
`memory/YYYY-MM-DD.md` la escribe el backend en el workspace de ejecución (fuera de Git): por turno, hora, seudónimo,
ruta, herramientas, latencia y estado, sin texto del usuario ni números. `MEMORY.md` versionado contiene memoria
curada del dominio y de la operación (no de personas). La memoria por persona sigue en `SqliteStore` y se audita con
`agent memory list --user <seudónimo>` (FR-025).

**Separación identidad/límites** (FR-012): `SOUL.md` = persona y tono de Valer-IA Caña (specs 018–020);
`AGENTS.md` = reglas operativas y *red lines* (no inventar, citar, no datos de terceros, confirmar escrituras, no
obedecer instrucciones dentro de documentos, alcance Manuelita).

## R12. Seguridad y hardening

**Decisión** (línea base endurecida de OpenClaw, adaptada):

- `gateway.bind: "loopback"`, `gateway.auth: { mode: "token", token: "${OPENCLAW_GATEWAY_TOKEN}" }`.
- `tools.profile: "messaging"`, `tools.deny: ["group:automation", "group:runtime", "group:fs", "sessions_spawn",
  "sessions_send"]`, `tools.fs.workspaceOnly: true`, `tools.exec: { security: "deny", ask: "always" }`,
  `tools.elevated.enabled: false`, `agentToAgent.enabled: false`, `session.dmScope: "per-channel-peer"`.
- `agents.defaults.sandbox: { mode: "all", scope: "session", workspaceAccess: "ro", backend: "docker", network:
  "none" }`. **Requiere Docker Desktop en el PC servidor** (hoy no instalado en el portátil de desarrollo); también lo
  necesita Qdrant servidor (R14). Si Docker no estuviera disponible a tiempo: `mode: "non-main"` no aplica a un solo
  agente, así que la alternativa documentada sería el backend `podman`; se registra como riesgo.
- Backend: `POST /api/channels/messages` acepta solo peticiones desde `127.0.0.1` con `X-Channel-Token`
  (comparación en tiempo constante); deduplica por `message_id`; un candado por usuario evita turnos concurrentes.
- Inyección: el blindaje del Módulo 2 (spec 015) ya actúa dentro del agente; se añade una evaluación con ataques
  **llegados por el canal** (mensajes y fragmentos envenenados) reutilizando `agent shield` con un adaptador de canal.
- `openclaw security audit --deep` en verde; `--fix` solo tras revisar sus cambios.
- Escaneo de secretos: `gitleaks` (pre-commit y CI) sobre el historial completo (SC-010).

## R13. Formato de respuesta en WhatsApp

**Decisión**: renderizador `channels/format.py`: Markdown → formato de WhatsApp (`*negrita*`, `_cursiva_`, listas con
«•»), citas `[U#]` → «[1]» y bloque final «Fuentes:» con título corto y URL; máx. 1.500 caracteres por mensaje (el
`textChunkLimit` del canal es 4.000; se corta por frases para no partir citas). Mensajes no textuales: respuesta fija
(«Por ahora solo leo texto…»); notas de voz → transcripción con el dictado de la spec 023 si `channels.voice_notes =
true` (deseable, desactivado por defecto).

## R14. Qdrant en servidor (ítem 2.2)

**Decisión**: Qdrant servidor con `docker compose up -d qdrant` (ya existe `docker-compose.yml`) en el PC servidor,
`QDRANT_URL=http://127.0.0.1:6333`, colección reconstruida con `rag qdrant build --force`; `rag qdrant status` debe
mostrar HNSW (`m=16`, `ef_construct=128`) y la evaluación corre contra el servidor. Respaldo: binario nativo de Qdrant
para Windows si Docker falla.

## R15. Reconstrucción del corpus con un comando (ítem 2.1)

**Decisión**: `uv run pml corpus rebuild [--from bronze|silver] [--workdir DIR] [--scrape --campaign ID] [--json]`
(y `make corpus`): ejecuta plata → oro → índice denso → colección Qdrant **sobre un directorio de trabajo**
(`PML_*_DIR` / `--out`), sin reescribir `data/silver|gold` versionados salvo `--in-place`. Por defecto parte del bronce
versionado (offline); `--scrape` re-ejecuta la adquisición respetuosa (red). Al final verifica (`silver verify`,
`gold verify`, conteo de fragmentos con `unit_id` + URL + página) y escribe un manifiesto con hashes.

**Verificar**: que `silver build` y `gold build` aceptan directorio de salida; si no, añadir la opción (cambio pequeño
en `cli.py`).

## R16. Evaluación del retrieval y proyección 2D (ítem 2.3)

**Decisión**:

- Conjunto de **30 consultas** etiquetadas: muestra fija (semilla 2026) de las 35 puntuables de
  `tests/fixtures/rag/eval_questions.jsonl`, elegida **antes** de correr (`tests/fixtures/rag/module3_queries.jsonl`).
  Métricas: Recall@10 y nDCG@10 (más MRR) sobre el servidor Qdrant; línea base = híbrida del Módulo 2 (0,67 / 0,50).
- Proyección **t-SNE** (`scikit-learn`, `perplexity=30`, `init="pca"`, `random_state=2026`) de los embeddings de los
  fragmentos indexados (muestra estratificada por `topic_id`, ≤ 5.000 puntos) más las 30 consultas; colores por tema,
  consultas fallidas (Recall@10 = 0) marcadas; salida `docs/proyeccion_embeddings.png` + `.json` (coordenadas) y
  lectura en `docs/evaluacion_modulo3.md`. Comando `uv run python -m proyecto_modelos_lenguaje.rag project`.
- **Dependencias nuevas**: `scikit-learn` (t-SNE) y `matplotlib` (figura). UMAP (`umap-learn`, con `numba`) se descarta
  por compatibilidad incierta con Python 3.14.

## R17. Persistencia: SQLite frente a PostgresSaver

**Decisión**: conservar `SqliteSaver`/`SqliteStore` (modo WAL) en un solo servidor. La rúbrica acepta «PostgresSaver o
equivalente»; con un único proceso backend y ≤ 20 usuarios simultáneos, SQLite es suficiente y no añade un servicio.
`CONSTITUTION.md` Fase 3 regla 0 dice «p. ej. PostgreSQL»: se registra la justificación en el ADR.

## R18. Monitoreo, registros y contingencia

**Decisión**: `GET /api/channels/status` (último mensaje, errores, latencia p90 de la última hora, estado del modelo);
`channels.jsonl` sin texto ni números; script `pml ops check` que ejecuta la «prueba de 3 minutos» (uv sync,
`openclaw gateway status`, `openclaw channels status --probe`, `openclaw security audit`, salud del backend y de
Qdrant, `git status`) y devuelve código ≠ 0 si algo falla. Plan de contingencia en `docs/despliegue.md`: revincular QR,
reiniciar servicios, modo degradado (agente nativo + MCP), y regla del sábado (no cambiar de computador).

## R19. Documentación y sustentación

**Decisión**: `docs/rubrica_modulo3.md` (autoevaluación de 15 ítems con evidencia, guion 7 + 8 min por integrante,
versión en inglés, contingencia), `docs/despliegue.md`, `docs/manual_whatsapp.md`, `docs/herramientas.md` (generado),
`docs/evaluacion_modulo3.md`, ADR 0028 (OpenClaw + puente + MCP), README y Archify (`docs/arquitectura.json`)
actualizados, `CONSTITUTION.md` v1.16.0 (Fase 3 concretada, OpenClaw, Node para el plugin, nuevas dependencias).
