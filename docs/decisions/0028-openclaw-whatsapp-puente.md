# ADR 0028 — Valer-IA en WhatsApp con OpenClaw y un plugin puente

- **Estado**: aceptada
- **Fecha**: 2026-11-23
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0016 (agente RAG con LangGraph), ADR 0018 (Qdrant y rúbrica del Módulo 2), ADR 0019
  (blindaje), ADR 0022 (Valer-IA Caña); `specs/024-module3-openclaw-whatsapp/` (spec, plan, research R1–R19,
  contratos, tasks). Guía: [`docs/despliegue.md`](../despliegue.md).

## Contexto

El Anuncio 007 fija la sustentación final del Módulo 3 para el sábado 28 de noviembre de 2026. Los invitados
de las empresas prueban el agente **desde sus teléfonos por WhatsApp**, y la rúbrica exige:

- un despliegue con **OpenClaw**: gateway, canales, workspace, skills/plugins/MCP y sandbox;
- **20 herramientas** tipadas y trazables;
- un modelo en la nube (nada de Ollama) y `bind: loopback` con token;
- una lista de autorizados E.164 y emparejamiento.

Valer-IA Caña ya tenía un router evaluado (reglas → Jev → LLM), memoria (`SqliteSaver` + `SqliteStore`),
blindaje, aprobación humana y citas, todo detrás de `ChatService`. La pregunta era cómo conectar las dos
piezas sin perder lo evaluado en el Módulo 2 ni tener dos agentes que se comporten distinto en la web y en
WhatsApp.

Restricciones:
- el número es el **personal** de un integrante (no hay SIM dedicada ni verificación de Meta a tiempo);
- el servidor es un PC Windows 11 del equipo, detrás de NAT;
- quedan cinco días; las pruebas deben correr sin red;
- ningún número ni secreto en Git.

## Decisión

1. **Un solo agente, un puente mínimo.** Un plugin propio de OpenClaw, `valeria-bridge` (TypeScript), registra
   el hook **`before_dispatch`**. Recibe cada mensaje entrante ya autenticado por el gateway (después de
   `dmPolicy`, `allowFrom` y emparejamiento) y antes de cualquier llamada al modelo. Lo envía a
   `POST http://127.0.0.1:8000/api/channels/messages` con `X-Channel-Token`. La respuesta de Valer-IA vuelve
   como `{ handled: true, text }`. El spike (research R1) descartó `before_agent_reply`, cuyo `cleanedBody` es
   el prompt preparado y no el texto del remitente.
2. **El backend no sabe de OpenClaw.** El paquete `channels/` traduce el canal a lo que ya existía:
   - número → seudónimo `wa-<16 hex>` (HMAC-SHA256 con sal);
   - hilo persistente por usuario (`channels.sqlite3`);
   - deduplicación por `message_id` y candado por usuario;
   - comandos `/ayuda`, `/nuevo`, `/olvidar` y `/traza`;
   - aprobaciones por «SÍ/NO» que vencen a los 10 minutos;
   - formato de WhatsApp con «Fuentes:»;
   - bitácora `channels.jsonl` y `memory/YYYY-MM-DD.md` sin texto ni números.
   El grafo recibe `user_id`, `thread_id` y texto como cualquier cliente.
3. **Modo degradado real.** Si el backend falla o tarda más de 45 s, el plugin devuelve `undefined` y OpenClaw
   sigue su despacho normal: responde el **agente nativo** (DeepSeek `deepseek-flash`, respaldo
   `deepseek-v4-pro`) con el **servidor MCP propio** `valeria-tools`, bajo las red lines de `AGENTS.md`. Ese
   servidor (FastMCP, stdio) expone solo las 15 herramientas de lectura: las de escritura no existen en él.
4. **Catálogo único de 20 herramientas** (`agent/catalog.py`, Pydantic con `extra="forbid"`): 15 de lectura y
   5 de escritura con aprobación. De él salen el agente, el MCP, `GET /api/tools` y `docs/herramientas.md`.
   Cada ruta del router ofrece un subconjunto, y la traza expone `plan_steps`.
5. **Configuración versionada sin secretos**: `openclaw/openclaw.json5` usa `${VAR}` para todo lo sensible.
   Fija loopback + token, sandbox Docker sin red, `tools.deny`, `fs.workspaceOnly`, `groupPolicy: "disabled"`
   y `dmPolicy: "allowlist"`, que pasa a `"pairing"` solo durante la jornada. El workspace (`SOUL`,
   `IDENTITY`, `AGENTS`, `USER`, `MEMORY` y el skill `valeria-manuelita`) vive en `openclaw/workspace/` y se
   sincroniza con `pml ops workspace sync`.

## Alternativas descartadas

- **Proveedor de modelo personalizado** (`models.providers.<id>` con `api: "openai-completions"` hacia un
  endpoint del backend): evita TypeScript, pero OpenClaw antepone su prompt de sistema y sus definiciones de
  herramientas y espera semántica de LLM (streaming, tool calls). El backend tendría que fingir ser un modelo:
  frágil.
- **Solo MCP** (el agente nativo usa las 20 herramientas por MCP): sencillo y documentado, pero reemplaza el
  router, la memoria y el blindaje evaluados en el Módulo 2. Se perdería la evidencia de los ítems 1.2 y 1.3,
  y habría dos conductas distintas en web y WhatsApp. Se conserva como **modo degradado**.
- **Webhooks de OpenClaw** (`/hooks/agent`, `/v1/chat/completions`): van en sentido contrario (alguien externo
  llama al gateway). Solo servirían para envíos proactivos, que no están previstos.
- **WhatsApp Business Cloud API**: la verificación de Meta no cabe en el plazo y exigiría exponer un webhook
  público.

## Persistencia: SQLite en lugar de PostgresSaver

La Fase 3 de la constitución decía «persistencia productiva (p. ej. PostgreSQL)», y el checklist del Anuncio
007 pide «PostgresSaver **o equivalente**». Se conservan `SqliteSaver` y `SqliteStore` en modo WAL, más
`channels.sqlite3`. Hay un solo proceso backend y como máximo unos 20 usuarios simultáneos; un candado por
usuario serializa los turnos de cada número. Las ventajas:

- el hilo sobrevive al reinicio;
- la memoria se audita con `agent memory list --user wa-…`;
- no hay que añadir otro servicio ni migrar checkpoints a cinco días de la entrega.

Si el despliegue creciera a varios procesos o máquinas, el cambio es de *saver*, no de diseño.

## Número personal: riesgos y mitigaciones

| Riesgo | Mitigación |
|---|---|
| El bot lee o responde chats del titular | `groupPolicy: "disabled"`, `selfChatMode: false`, `dmScope: "per-channel-peer"`; solo DM admitidos llegan al puente (FR-001a). |
| Contactos del titular reciben el código de emparejamiento | `allowlist` fuera de la jornada y `pairing` solo el sábado; el titular avisa a sus contactos. |
| WhatsApp desvincula la sesión (Baileys) | Revinculación por QR en minutos (`docs/despliegue.md` § Contingencia), teléfono del titular en la sala, `ops check` sondea el canal. |
| Exposición del número en registros | Seudónimo HMAC; el número se descarta; registros sin texto ni números; sesión fuera de Git. |
| Percepción de «solo funciona en el PC de un integrante» | Servicio con reinicio automático, demo con el portátil de presentación apagado, guía de despliegue reproducible. |

## Túnel solo para la web

WhatsApp no necesita túnel: Baileys abre una conexión **saliente** desde el gateway, que funciona detrás de
NAT y sigue en `bind: "loopback"`. Cloudflare Tunnel (`cloudflared`) es opcional y solo publica la web de
Valer-IA por HTTPS (también para que el micrófono funcione fuera de `localhost`). El gateway nunca se expone.

## Consecuencias

- **Segundo lenguaje**: TypeScript sobre Node ≥ 24.16, solo para el plugin, porque OpenClaw solo admite
  plugins en TS. Es lógica pura sin dependencias del SDK (`src/bridge.ts`), con pruebas `node --test`
  (`npm test`). Python sigue siendo el único lenguaje del backend.
- **Dependencias Python nuevas**: `mcp` (SDK oficial, servidor MCP), `scikit-learn` (t-SNE) y `matplotlib`
  (figura de la proyección). UMAP se descartó por compatibilidad incierta con Python 3.14.
- **Dependencias externas al paquete**: OpenClaw (`npm i -g openclaw`), `@openclaw/whatsapp`, Docker Desktop
  (Qdrant servidor y sandbox) y, opcional, `cloudflared`. `gitleaks` revisa el historial en CI.
- La conducta en WhatsApp es la misma que en la web, con la misma evidencia (router, memoria, blindaje,
  aprobación humana y citas). El canal añade el formato y la confirmación por texto.
- En modo degradado no hay escrituras ni memoria por persona: el agente lo avisa («Estoy en modo básico…»).
- Las pruebas corren sin red: el puente y la API usan `ChatService` falso; el plugin, un `fetch` simulado. La
  verificación con el gateway vivo y teléfonos reales es manual (quickstart §3) y queda en el PC servidor.
- Quedan claves de configuración por **verificar** con el gateway vivo (`docs/despliegue.md` §7).
