# Implementation Plan: Entrega final del Módulo 3: Valer-IA Caña en WhatsApp con OpenClaw y 20 herramientas

**Branch**: `024-module3-openclaw-whatsapp` | **Date**: 2026-11-23 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/024-module3-openclaw-whatsapp/spec.md`

## Summary

Llevar Valer-IA Caña a WhatsApp a través de **OpenClaw** y completar lo que exige el Anuncio 007 para el sábado 28 de
noviembre. El diseño (research R1) mantiene **un solo agente**:

```text
Teléfono del invitado ──WhatsApp Web (saliente)──▶ OpenClaw gateway (PC servidor, loopback + token)
   allowFrom E.164 + emparejamiento · groupPolicy disabled · sandbox · tools.deny · workspace
        │ hook before_dispatch (plugin propio valeria-bridge)
        ▼
FastAPI /api/channels/messages (loopback + X-Channel-Token) ──▶ ChatService (variante agent)
   router reglas → Jev → LLM · catálogo de 20 herramientas · HITL por «SÍ/NO» · blindaje · citas
   SqliteSaver (hilo) + SqliteStore (perfil) · Qdrant servidor (HNSW, híbrida) · DeepSeek API
        │ si el backend cae o tarda > 45 s
        ▼
Modo degradado: agente nativo de OpenClaw (deepseek-flash → deepseek-v4-pro) + servidor MCP propio valeria-tools
(15 herramientas de lectura) + skill valeria-manuelita, bajo las red lines de AGENTS.md
```

Además: catálogo único de 20 herramientas tipadas (13 nuevas), plan visible en la traza, workspace versionado
(`SOUL/IDENTITY/AGENTS/USER/MEMORY.md` + bitácora diaria), reconstrucción del corpus con un comando, Qdrant en servidor,
evaluación sobre 30 consultas con proyección t-SNE, hardening y auditoría, documentación final y guion de sustentación.
El túnel (Cloudflare) solo publica la web; WhatsApp no lo necesita (R3).

## Technical Context

**Language/Version**: Python 3.14 (backend, `uv`); TypeScript sobre Node 24.22.1 solo para el plugin puente de OpenClaw;
React 19 + Vite (web existente, cambios menores).

**Primary Dependencies**: existentes: FastAPI, LangChain/LangGraph 1.2, `langgraph-checkpoint-sqlite`, `qdrant-client`
1.20, `sentence-transformers` (e5-small), DeepSeek (cliente OpenAI-compatible). **Nuevas** (justificadas en research):
`mcp` (servidor MCP, R10), `scikit-learn` (t-SNE, R16), `matplotlib` (figura, R16). Externas al paquete: OpenClaw
(`npm i -g openclaw`), `@openclaw/whatsapp`, Docker Desktop (Qdrant + sandbox), `cloudflared` (web), `gitleaks` (CI).

**Storage**: SQLite en `$MANUELITA_STATE_DIR` (checkpoints, Store, nuevo `channels.sqlite3`), Qdrant servidor (Docker,
volumen local), estado de OpenClaw en `%USERPROFILE%\.openclaw-valeria` (sesión de WhatsApp, emparejamientos, logs).
Nada en `data/` ni en el repositorio en tiempo de ejecución.

**Testing**: pytest (unit, api, integration con marcadores `network`/`voice`), vitest (web), pruebas del plugin con
`node:test` o vitest en `openclaw/plugins/valeria-bridge/`; dobles para el gateway (cliente que imita el hook) y modelo
falso (`build_fake_model`/`build_scripted_model`). Pruebas manuales con teléfonos reales según quickstart §3.

**Target Platform**: PC Windows 11 del equipo, encendido como servidor (OpenClaw nativo con tarea programada; backend
uvicorn como tarea programada; Docker Desktop). Web pública opcional vía Cloudflare Tunnel.

**Project Type**: servicio web + CLI + plugin de gateway (monorepo existente).

**Performance Goals**: p90 < 15 s y máx. 45 s por respuesta en WhatsApp con ≥ 10 usuarios simultáneos (SC-002);
emparejamiento < 1 min; arranque del servicio < 2 min tras reinicio.

**Constraints**: entrega el **sábado 28-11-2026 8:00**, verificación el viernes 27; costo de modelo con la cuenta
DeepSeek existente; número personal (no tocar grupos ni otros chats); sin secretos ni números en Git; `data/` intacto
salvo pedido; pruebas sin red; Windows (rutas `pathlib`, PowerShell para servicios).

**Scale/Scope**: ~30–60 invitados en la jornada, ≤ 20 simultáneos; 20 herramientas; 30 consultas de evaluación;
≤ 5.000 puntos en la proyección.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / regla | Evaluación | Estado |
|---|---|---|
| I. Reproducibilidad | `uv sync --frozen`; corpus con un comando y manifiesto con hashes (R15); semillas fijas (30 consultas y t-SNE, 2026); configuración de OpenClaw versionada como plantilla con `${VAR}`. | ✅ |
| II. Métricas y línea base | Línea base fijada antes de evaluar: híbrida M2 (Recall@10 0,67 / nDCG@10 0,50); batería de herramientas con umbral 90 % definido en la spec; blindaje con línea base del M2. | ✅ |
| III. Procedencia y ética | Teléfonos solo como seudónimo HMAC; sin texto en logs; workspace sin datos personales; invitados fuera del repo; consentimiento para memoria (HITL). | ✅ |
| IV. Experimentos como código | Todo por CLI documentada (`contracts/cli.md`); proyección y evaluación por comando, no notebook. | ✅ |
| V. Simplicidad | OpenClaw es obligatorio por rúbrica; se usa un solo agente y un puente mínimo; SQLite en lugar de Postgres (R17); 3 dependencias nuevas justificadas. Ver Complexity Tracking (TypeScript, Docker). | ⚠️ justificado |
| Restricciones técnicas | Python 3.14 + `uv`; Ruff; type hints; secretos en env; `pathlib`; archivos > 10 MB fuera de Git (la figura PNG < 1 MB). | ✅ |
| Fase 2 (CONSTITUTION.md) | Se conservan memoria por `thread_id`, enrutamiento, blindaje, HITL y Recall@10/nDCG@10; se extienden al canal. | ✅ |
| Fase 3 (CONSTITUTION.md §5) | Canal real ✅; persistencia productiva: SQLite en lugar de «p. ej. PostgreSQL» (justificado, R17); guardrails ✅; evaluación ✅; despliegue reproducible (guía + servicio) ✅; observabilidad (`channels.jsonl`, `ops check`) ✅; documentación y demo ✅; **tag de release** al cerrar. | ✅ |
| Autoría (§4.3, ADR 0017) | Commits y PRs solo de los integrantes; Claude prepara cambios. | ✅ |
| Documentación viva | ADR 0028, `CONSTITUTION.md` v1.16.0, README, Archify, prompt_log si cambian prompts. | ✅ |

**Re-check post-diseño**: sin nuevas violaciones; los riesgos (Docker, número personal, túnel) están en research y en
Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/024-module3-openclaw-whatsapp/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── channel-api.md
│   ├── tools-catalog.md
│   ├── openclaw-config.md
│   └── cli.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── agent/
│   ├── catalog.py            # NUEVO: registro único de las 20 herramientas (ToolSpec)
│   ├── tools.py              # se amplía: 10 lecturas nuevas (o tools_*.py por dominio si crece)
│   ├── actions.py            # + request_human_contact (escritura con HITL)
│   ├── graph.py / router.py  # subconjunto de herramientas por ruta; plan_steps en la traza
│   ├── service.py            # sin cambios de contrato; lo usa el canal
│   └── __main__.py           # + tools, evaluate --tools, shield --channel, memory list
├── channels/                 # NUEVO
│   ├── __init__.py
│   ├── identity.py           # E.164 → user_id seudónimo (HMAC), máscara
│   ├── store.py              # channels.sqlite3: usuarios, hilos, dedupe, pendientes
│   ├── bridge.py             # orquesta: comandos, HITL por SÍ/NO, candado por usuario, ChatService
│   ├── format.py             # Markdown → WhatsApp, citas numeradas, corte por frases
│   ├── journal.py            # bitácora diaria memory/YYYY-MM-DD.md + channels.jsonl
│   └── __main__.py           # simulate
├── mcp_server.py             # NUEVO: FastMCP stdio con las 15 de lectura
├── ops.py                    # NUEVO: ops check, workspace sync
├── corpus.py                 # NUEVO: corpus rebuild (orquesta silver → gold → index → qdrant)
├── rag/project.py            # NUEVO: t-SNE + figura
├── rag/evaluate.py           # --queries / servidor
├── api.py / api_models.py    # /api/channels/messages, /api/channels/status, /api/tools
└── cli.py                    # pml corpus / channels / ops

openclaw/                     # NUEVO (versionado, sin secretos)
├── openclaw.json5
├── .env.example
├── workspace/{SOUL,IDENTITY,AGENTS,USER,MEMORY}.md + skills/valeria-manuelita/SKILL.md
└── plugins/valeria-bridge/   # package.json, src/index.ts, test/, README.md

scripts/serve_backend.ps1     # NUEVO: backend como tarea programada
tests/
├── unit/agent/test_catalog.py, tools/test_*.py
├── unit/channels/test_{identity,format,store,bridge,journal}.py
├── unit/test_{mcp_server,corpus,ops}.py, unit/rag/test_project.py
├── api/test_channels_api.py, api/test_tools_api.py
├── fixtures/agent/tool_routing.jsonl, fixtures/rag/module3_queries.jsonl, fixtures/channels/*.json
└── integration/openclaw/      # marcador network: gateway real (manual/CI excluido)

docs/
├── rubrica_modulo3.md, despliegue.md, manual_whatsapp.md, herramientas.md (generado)
├── evaluacion_modulo3.{md,json}, evaluacion_herramientas.{md,json}, evaluacion_blindaje_canal.{md,json}
├── proyeccion_embeddings.{png,json}
└── decisions/0028-openclaw-whatsapp-puente.md
```

**Structure Decision**: se mantiene el monorepo; lo nuevo del canal vive en un paquete `channels/` desacoplado del
grafo (el grafo no sabe de WhatsApp: recibe `user_id`, `thread_id` y texto como cualquier cliente). Lo específico de
OpenClaw (configuración, workspace, plugin TypeScript) vive en `openclaw/`, fuera de `src/`.

## Implementation Phases (orden y calendario)

| Día | Fase | Entregable verificable | Ítems |
|---|---|---|---|
| Lun 23 (tarde) | 0. Infra en el PC servidor | Docker Desktop, OpenClaw instalado, `openclaw doctor` limpio, WhatsApp vinculado en `allowlist` con el agente nativo respondiendo «hola». **Spike** del hook `before_agent_reply` (claves y formato reales). | 3.1, 3.2 |
| Mar 24 | 1. Puente y canal | `channels/` + `/api/channels/messages` + plugin; WhatsApp → Valer-IA con citas e hilo; HITL por SÍ/NO; formato; bitácora; pruebas. | 3.2, 1.3 |
| Mar 24–Mié 25 | 2. Catálogo de 20 | `catalog.py`, 13 herramientas nuevas con pruebas, subconjuntos por ruta, `plan_steps`, `GET /api/tools`, batería ≥ 40 y evaluación. | 1.1, 1.2 |
| Mié 25 | 3. Workspace, MCP y hardening | Workspace versionado y sincronizado; `mcp_server` registrado; sandbox/deny/workspaceOnly; modo degradado probado; `security audit` verde; gitleaks. | 3.3, 3.4, 4.2 |
| Jue 26 | 4. Datos y evaluación | `corpus rebuild`; Qdrant servidor; 30 consultas; t-SNE con lectura; blindaje por canal. | 2.1–2.3, 4.2 |
| Jue 26 | 5. Documentación | README, Archify, ADR 0028, despliegue, manual, herramientas, `CONSTITUTION.md` v1.16.0, `rubrica_modulo3.md`. | 4.3 |
| Vie 27 | 6. Ensayo y congelamiento | Prueba de 3 minutos verde; prueba de carga (10 teléfonos o `channels simulate` concurrente); ensayo cronometrado ES/EN; PR, CI, tag `v3.0.0`. | 5.1, 5.2 |

Ruta crítica: Fase 0 → 1 (sin canal real no hay demo). Las fases 2 y 4 son paralelizables entre integrantes.

## Risks

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Hook `before_dispatch` (antes `before_agent_reply`, ver R1 «Hallazgos del spike») no permite respuestas en varios mensajes o no recibe el remitente E.164 | Medio | Spike el lunes; si falta el remitente, usar la clave de sesión (`per-channel-peer`) como identidad; un solo mensaje concatenado. Plan B: proveedor OpenAI-compatible (R1). |
| Docker no disponible en el PC servidor | Alto (sandbox 4.2, Qdrant 2.2) | Instalar el lunes; Qdrant binario nativo; sandbox `podman` como alternativa documentada. |
| Número personal: contactos reciben el mensaje de emparejamiento | Medio | `allowlist` fuera de la jornada, `pairing` solo el sábado; avisar a contactos. |
| WhatsApp desvincula la sesión (Baileys) | Alto el día | Revinculación por QR documentada; teléfono del titular en la sala; `channels status --probe` cada hora en `ops check`. |
| Cuota/latencia de DeepSeek con 10+ usuarios | Medio | Fallback de modelo, candado por usuario, recorte de contexto existente, prueba de carga el viernes. |
| Percepción de «solo funciona en el PC de un integrante» (3.2) | Medio | Servicio con reinicio automático, demo con el portátil de presentación apagado, guía de despliegue reproducible. |
| Retrieval no supera la línea base en servidor | Bajo | El HNSW con `ef=128` debería igualar al exacto; se reporta honestamente (Principio II). |

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Plugin en TypeScript (segundo lenguaje) | OpenClaw solo admite plugins en TS; el hook es la vía documentada para que Valer-IA responda en el canal. | Proveedor OpenAI-compatible: obliga al backend a imitar un LLM con prompts y tool-calls de OpenClaw; solo MCP: reemplaza el router y la memoria evaluados. |
| Docker Desktop en el servidor | Sandbox exigido por 4.2 y Qdrant servidor por 2.2. | Sin sandbox no se cumple la rúbrica; Qdrant embebido no usa HNSW. |
| SQLite en lugar de PostgreSQL (Fase 3 regla 0) | Un solo proceso, ≤ 20 simultáneos; la rúbrica acepta «equivalente». | Postgres añade un servicio, migración de checkpoints y riesgo a 5 días de la entrega. |
| Tres dependencias Python nuevas (`mcp`, `scikit-learn`, `matplotlib`) | Protocolo MCP (3.4) y proyección t-SNE (2.3). | JSON-RPC manual y t-SNE propio: más código y más riesgo. |
