---
description: "Task list for spec 024 — Entrega final del Módulo 3 (OpenClaw, WhatsApp y 20 herramientas)"
---

# Tasks: Entrega final del Módulo 3: Valer-IA Caña en WhatsApp con OpenClaw y 20 herramientas

**Input**: Design documents from `specs/024-module3-openclaw-whatsapp/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md),
[contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: SÍ. La spec las exige (FR-022: una prueba de contrato por herramienta y evaluación del router; FR-034: pruebas
sin red con dobles del canal y del gateway). Se escriben primero y deben fallar antes de implementar.

**Organization**: por historia de usuario (US1–US7 de la spec). Plazo: sábado 28-11-2026 8:00; todo lo obligatorio
verificado el viernes 27.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: puede correr en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia a la que pertenece (US1…US7)
- Rutas exactas en cada tarea; UI, comentarios y textos en español, identificadores en inglés; Ruff 100 columnas.

## Path Conventions

- Backend: `src/proyecto_modelos_lenguaje/` · pruebas: `tests/` · OpenClaw: `openclaw/` · documentación: `docs/`
- Estado en tiempo de ejecución: `$MANUELITA_STATE_DIR` y `%USERPROFILE%\.openclaw-valeria` (nunca en Git)
- **Reglas**: no reescribir `data/bronze|silver|gold` (salvo `--in-place` pedido); no tocar el servidor del puerto 8000 del
  usuario en pruebas (usar 8020); sin secretos ni números de teléfono en archivos versionados; commits solo de los
  integrantes.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias, estructura y la infraestructura del PC servidor (ruta crítica: sin gateway no hay canal).

- [X] T001 Añadir dependencias `mcp`, `scikit-learn` y `matplotlib` en `pyproject.toml` (justificación en research R10/R16) y regenerar `uv.lock` con `uv lock`; verificar `uv sync --frozen` en Python 3.14
- [X] T002 [P] Crear el paquete `src/proyecto_modelos_lenguaje/channels/__init__.py` (docstring: canal de mensajería de Valer-IA, spec 024) y los directorios de pruebas `tests/unit/channels/__init__.py`, `tests/fixtures/channels/`, `tests/fixtures/agent/`
- [X] T003 [P] Crear `openclaw/.env.example` con las variables sin valor de contracts/openclaw-config.md §1 (`DEEPSEEK_API_KEY`, `OPENCLAW_GATEWAY_TOKEN`, `VALERIA_CHANNEL_TOKEN`, `VALERIA_CHANNEL_SALT`, `WA_ALLOW_1..3`, `VALERIA_REPO`, `OPENCLAW_WORKSPACE_DIR`, `MANUELITA_STATE_DIR`, `QDRANT_URL`) y añadir a `.gitignore` las rutas `openclaw/**/.env`, `openclaw/plugins/*/node_modules/`, `openclaw/plugins/*/dist/`, `**/.openclaw*/`
- [X] T004 [P] Añadir a `config/agent.toml` la sección `[channels]` (`enabled = true`, `reply_max_chars = 1500`, `max_messages = 4`, `approval_ttl_minutes = 10`, `dedupe_hours = 48`, `voice_notes = false`, `bridge_timeout_seconds = 45`) y su carga validada en `src/proyecto_modelos_lenguaje/agent/config.py` (`ChannelsConfig` frozen)
- [X] T005 [P] Añadir `gitleaks` al pre-commit (`.pre-commit-config.yaml`) y un paso `gitleaks detect --log-opts="--all"` en `.github/workflows/` (job existente `test` o nuevo `secretos`); documentar falsos positivos en `.gitleaks.toml` si los hay
- [ ] T006 Infra del PC servidor (manual, registrar en `docs/despliegue.md` borrador): instalar Docker Desktop, `npm install -g openclaw@latest`, `openclaw plugins install @openclaw/whatsapp`, crear `%USERPROFILE%\.openclaw-valeria\.env`, desactivar suspensión (`powercfg /change standby-timeout-ac 0`); verificar `openclaw doctor` y `docker compose up -d qdrant`
- [X] T007 Spike del hook (research R1, riesgo 1): plugin mínimo en `openclaw/plugins/valeria-bridge/` que registre `before_agent_reply`, imprima en el log las claves del evento (remitente, id de mensaje, tipo, canal) y responda «spike ok»; anotar en `specs/024-module3-openclaw-whatsapp/research.md` (R1, «Hallazgos del spike») los nombres reales de los campos, si admite varios mensajes y si admite no responder; decidir plan B si falta el remitente

**Checkpoint**: gateway arranca con `openclaw doctor` limpio; WhatsApp vinculado en `allowlist`; el spike responde.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: configuración versionada de OpenClaw y el catálogo único de herramientas; bloquean US1–US3.

**⚠️ CRITICAL**: ninguna historia empieza antes de esta fase.

### Tests (escribir primero; deben fallar)

- [X] T008 [P] Prueba del catálogo en `tests/unit/agent/test_catalog.py`: ≥ 20 entradas; nombres únicos `^[a-z][a-z0-9_]{2,40}$`; descripción en español de 20–300 caracteres; `requires_approval ⇔ kind == "write"`; `mcp ⇒ kind == "read"`; todo `args_schema` es Pydantic con `extra="forbid"`; cada herramienta declara `routes` y `data_source`
- [X] T009 [P] Prueba de la plantilla en `tests/unit/test_openclaw_config.py`: `openclaw/openclaw.json5` se parsea como JSON5 (parser mínimo o `json5` en dev si ya existe; si no, quitar comentarios y comas finales), contiene `gateway.bind == "loopback"`, `gateway.auth.mode == "token"`, `channels.whatsapp.groupPolicy == "disabled"`, `tools.fs.workspaceOnly == true`, y **ningún** valor que parezca secreto o E.164 literal (solo `${VAR}`)

### Implementation

- [X] T010 Crear `src/proyecto_modelos_lenguaje/agent/catalog.py`: `ToolSpec` (data-model §6: `name`, `description`, `args_schema`, `kind: Literal["read","write"]`, `requires_approval`, `routes: frozenset[str]`, `mcp: bool`, `data_source`) con validación al cargar; `CATALOG` registra primero las 7 existentes (`search_documents`, `query_structured`, `aggregate_series`, `save_profile`, `save_preference`, `forget_memory`, `export_conversation`) envolviendo `build_read_tools`/`build_write_tools` de `agent/tools.py` y `agent/actions.py` sin cambiar su comportamiento; funciones `read_specs()`, `write_specs()`, `specs_for_route(route)`, `to_json_schema()`
- [X] T011 Crear `openclaw/openclaw.json5` según contracts/openclaw-config.md §1 (gateway loopback+token, DeepSeek `deepseek/deepseek-flash` con fallback `deepseek/deepseek-v4-pro`, sandbox, `tools.*` endurecido, WhatsApp `dmPolicy: "allowlist"` por defecto, `groupPolicy: "disabled"`, `selfChatMode: false`, `mcp.servers.valeria-tools`, `plugins.entries.valeria-bridge`); validar en el PC servidor con `openclaw config file` + `openclaw doctor` y corregir las claves marcadas «verificar» con lo hallado en T007
- [X] T012 [P] Script `scripts/openclaw_env.ps1` que exporta `OPENCLAW_CONFIG_PATH=<repo>\openclaw\openclaw.json5`, `OPENCLAW_STATE_DIR=%USERPROFILE%\.openclaw-valeria`, `OPENCLAW_WORKSPACE_DIR` y reinstala el servicio (`openclaw gateway install --force`, `openclaw gateway restart --wait 30s`)

**Checkpoint**: T008–T009 pasan; el gateway arranca con la plantilla del repositorio.

---

## Phase 3: User Story 1 - Un invitado le escribe a Valer-IA por WhatsApp y recibe una respuesta citada (Priority: P1) 🎯 MVP

**Goal**: WhatsApp → OpenClaw → plugin → `/api/channels/messages` → Valer-IA (variante `agent`) → respuesta citada en el
mismo hilo, con el portátil de presentación apagado.

**Independent Test**: desde un número autorizado, tres mensajes encadenados («¿Qué produce Manuelita?», «¿y en Perú?»,
«gracias») reciben respuestas coherentes, citadas y en el mismo hilo; un número no autorizado no recibe nada del agente.

### Tests for User Story 1 (escribir primero; deben fallar)

- [X] T013 [P] [US1] `tests/unit/channels/test_identity.py`: `pseudonym(e164, salt)` → `"wa-" + 16 hex` que cumple `^[A-Za-z0-9-]{1,64}$`, estable para el mismo número y distinto con otra sal; rechaza números fuera de `^\+[1-9]\d{7,14}$`; `mask("+573001234567") == "+57 ••• ••• 4567"`; Telegram `tg:<id>` → `"tg-" + 16 hex`
- [X] T014 [P] [US1] `tests/unit/channels/test_format.py`: `**x**`→`*x*`; títulos → negrita; tablas → líneas `•`; `[U3]`/`[F1]` → `[1]`/`[2]` por orden de aparición con bloque «Fuentes:» (título ≤ 80 caracteres + URL + página si existe); corte por frases a ≤ 1.500 caracteres y máximo 4 mensajes con «(respuesta abreviada; pídeme más detalle)»; nunca parte una cita
- [X] T015 [P] [US1] `tests/unit/channels/test_store.py` (SQLite en `tmp_path`): crea usuario e hilo activo; el hilo persiste al reabrir la base (simula reinicio); `seen(message_id)` deduplica y purga > 48 h; tablas `channel_users`, `channel_threads`, `channel_seen`, `channel_pending`
- [X] T016 [P] [US1] `tests/unit/channels/test_bridge.py` con `ChatService` falso: texto → `answered` con `thread_id` estable entre turnos; `message_id` repetido → `ignored` y `[]`; segundo mensaje durante un turno en curso del mismo usuario → `busy`; `kind="image"` → `unsupported` con el texto fijo; excepción del servicio → `error` con mensaje breve; `/ayuda` → `answered`
- [X] T017 [P] [US1] `tests/api/test_channels_api.py`: sin `X-Channel-Token` o token incorrecto → `403 channel_forbidden`; IP no loopback (cliente con `client=("10.0.0.5", 1)`) → 403; sin `VALERIA_CHANNEL_TOKEN` configurado → `503 channel_disabled`; cuerpo inválido (`sender` no E.164, `text` > 4.000) → `400 channel_invalid`; caso feliz en modo demo → 200 con `status`, `messages`, `thread_id`, `route`, `tools`, `latency_ms`; `GET /api/channels/status` con los campos de contracts/channel-api.md §2; el log `channels.jsonl` no contiene el texto ni el número
- [X] T018 [P] [US1] Pruebas del plugin en `openclaw/plugins/valeria-bridge/test/index.test.ts` (vitest o `node:test`, `fetch` simulado): construye el cuerpo §1 desde el evento; `answered` → `{ handled: true, reply: { text } }`; `ignored` → no responde; timeout de 45 s o error de red → `undefined` (modo degradado); envía `X-Channel-Token`

### Implementation for User Story 1

- [X] T019 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/channels/identity.py` (`pseudonym`, `mask`, `validate_sender`; HMAC-SHA256 con `VALERIA_CHANNEL_SALT`; error claro si falta la sal)
- [X] T020 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/channels/format.py` (`to_whatsapp(text, citations) -> list[str]`) según contracts/channel-api.md §5
- [X] T021 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/channels/store.py` (`ChannelStore` sobre `$MANUELITA_STATE_DIR/channels.sqlite3`, modo WAL; data-model §1–3 y §5: `user_id`, `channel`, `masked`, `first_seen`, `last_seen`, `active_thread_id`; hilos con `closed_at`; `channel_seen` con retención 48 h)
- [X] T022 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/channels/journal.py`: `log_channel(record)` en `logs/channels.jsonl` (data-model §9: `ts`, `channel`, `user_id`, `thread_id`, `message_id_hash`, `kind`, `status`, `route`, `tools`, `latency_ms`, `model_calls`, `error_code`; nunca texto ni número) y `append_daily(record)` en `${OPENCLAW_WORKSPACE_DIR}/memory/YYYY-MM-DD.md` (una línea por turno; no escribe si la variable falta)
- [X] T023 [US1] Implementar `src/proyecto_modelos_lenguaje/channels/bridge.py`: `ChannelBridge.handle(InboundMessage) -> ChannelReply` (data-model §3–4): dedupe, candado por `user_id` (`busy`), tipos no texto, recorte a 2.000 caracteres, comandos `/ayuda` y `/nuevo`, llamada a `ChatService.send(..., variant="agent", mode=...)`, formato y registro; depende de T019–T022
- [X] T024 [US1] Añadir a `src/proyecto_modelos_lenguaje/api_models.py` `ChannelMessageRequest`, `ChannelReplyModel`, `ChannelStatus` (validaciones de contracts/channel-api.md §1–2) y a `src/proyecto_modelos_lenguaje/api.py` `POST /api/channels/messages` y `GET /api/channels/status` con guardia de loopback + `X-Channel-Token` (`hmac.compare_digest`) y códigos `channel_forbidden|channel_disabled|channel_invalid|channel_error`
- [X] T025 [US1] Implementar el plugin `openclaw/plugins/valeria-bridge/` (`package.json`, `tsconfig.json`, `src/index.ts`, `README.md`): `before_agent_reply` con `eligibleTriggers: ["user"]`, solo canales WhatsApp/Telegram, `fetch` a `backendUrl` con timeout, mapeo de `status` a respuesta según contracts/channel-api.md §4 usando los nombres de campos hallados en T007; construir con `openclaw plugins build` e instalar con `openclaw plugins install ./openclaw/plugins/valeria-bridge`
- [X] T026 [US1] Implementar `src/proyecto_modelos_lenguaje/channels/__main__.py` y el subcomando `pml channels simulate --sender --text [--kind] [--message-id]` en `src/proyecto_modelos_lenguaje/cli.py`, que llama al endpoint local con el token del `.env` (ensayo sin teléfono)
- [X] T027 [US1] Script `scripts/serve_backend.ps1`: arranca `uvicorn proyecto_modelos_lenguaje.api:app --host 127.0.0.1 --port 8000` con `QDRANT_URL` y el `.env`, registrado como tarea programada con reinicio ante fallo; documentar en `docs/despliegue.md`
- [ ] T028 [US1] Verificación manual (quickstart §3, pasos 1, 3, 7): tres teléfonos autorizados ajenos al equipo, portátil de presentación apagado; registrar resultados (sin números) en `specs/024-module3-openclaw-whatsapp/tasks.md` § Notas

**Checkpoint**: US1 funciona por WhatsApp real; `make check` en verde.

---

## Phase 4: User Story 2 - El agente usa 20 herramientas tipadas y explica cuál eligió y por qué (Priority: P1)

**Goal**: catálogo de 20 herramientas (13 nuevas), subconjunto por ruta, plan y traza completos, aprobación en las de
escritura, evaluación ≥ 90 %.

**Independent Test**: `agent tools --json` lista 20 con esquemas; `agent evaluate --tools --fake` ≥ 90 % de herramienta
esperada y 0 búsquedas en 10 triviales; por WhatsApp, `/traza` muestra ruta, plan y herramienta.

### Tests for User Story 2 (escribir primero; deben fallar)

- [X] T029 [P] [US2] `tests/unit/agent/tools/test_series_tools.py`: `list_indicators(business)` lista métricas y años de `data/curated/series_anuales.csv`; `compare_indicator(metric, year_a, year_b)` con `year_a != year_b` (si no, error) devuelve variación absoluta y % con `Decimal` y referencias `[F#]`; métrica o año inexistente → «sin resultados»
- [X] T030 [P] [US2] `tests/unit/agent/tools/test_entity_tools.py`: `list_business_units(country)` y `list_company_entities(kind: certification|brand)` desde `data/gold/entities.jsonl` con `[U#]`; `kind` inválido → error de validación
- [X] T031 [P] [US2] `tests/unit/agent/tools/test_knowledge_tools.py` (índice de `tests/fixtures/rag/index`): `sustainability_lookup(theme ∈ {agua, carbono, energia, residuos, biodiversidad, social}, query 3–200, top_k 1–10)` usa **filtro por payload** y devuelve `[U#]`; `faq_lookup(question 3–300, top_k 1–5)` desde `faq_seeds.jsonl`; `summarize_topic(topic_id)` solo acepta los temas de `data/gold/topics/`; `latest_news(limit 1–5, since_year)` ordena por `published_at`; `get_fragment(unit_id ^unit_[0-9a-f]{16}$)` devuelve texto, URL y páginas o «sin resultados»
- [X] T032 [P] [US2] `tests/unit/agent/tools/test_utility_tools.py`: `calculate(expression 1–120)` con gramática `[0-9.,+\-*/()% ]` y AST seguro (rechaza nombres, llamadas, `**` > 10 dígitos, división por cero con error claro); `operation: percent_change|ratio|sum` con `values` 1–12 `Decimal`; `get_official_channels(purpose)` desde `config/official_channels.toml`; `get_my_profile` lee el Store del `user_id` del turno y no ve otros usuarios
- [X] T033 [P] [US2] `tests/unit/agent/test_request_contact.py`: `request_human_contact(topic 3–120, preferred_channel whatsapp|email|llamada, name 1–80 | None)` es `write`, exige aprobación, tras aprobar registra en `contacts.jsonl` con `user_id` seudónimo y responde con el canal oficial; rechazada no escribe nada
- [X] T034 [P] [US2] `tests/unit/agent/test_route_tools.py`: `specs_for_route("direct")` no incluye herramientas de búsqueda; `documental` y `structured` ofrecen los subconjuntos de contracts/tools-catalog.md; las de escritura solo se ofrecen si el detector de intención las activa; el turno expone `plan_steps` no vacío cuando hay herramientas y la traza de cada invocación tiene `name`, `args`, `ok`, `error`, `duration_ms`, `summary` (≤ 200 caracteres), `step`
- [X] T035 [P] [US2] `tests/api/test_tools_api.py`: `GET /api/tools` devuelve 20 entradas ordenadas con `name`, `description`, `kind`, `requires_approval`, `routes`, `mcp`, `schema` (JSON Schema)
- [X] T036 [P] [US2] Crear `tests/fixtures/agent/tool_routing.jsonl`: ≥ 40 consultas (≥ 2 por herramienta, con `expected_tool` y `route`) + 10 saludos/agradecimientos/preguntas sobre el asistente con `expected_tool: null`; fijarla antes de evaluar (Principio II)

### Implementation for User Story 2

- [X] T037 [P] [US2] Implementar `list_indicators` y `compare_indicator` en `src/proyecto_modelos_lenguaje/agent/tools_series.py` (reutiliza el lector de `agent/series.py`) y registrarlas en `agent/catalog.py`
- [X] T038 [P] [US2] Implementar `list_business_units` y `list_company_entities` en `src/proyecto_modelos_lenguaje/agent/tools_entities.py` y registrarlas
- [X] T039 [P] [US2] Implementar `sustainability_lookup`, `faq_lookup`, `summarize_topic`, `latest_news` y `get_fragment` en `src/proyecto_modelos_lenguaje/agent/tools_knowledge.py` (búsqueda híbrida existente con filtro de payload; citas por el mecanismo `[U#]` del Módulo 2) y registrarlas
- [X] T040 [P] [US2] Implementar `calculate`, `get_official_channels` y `get_my_profile` en `src/proyecto_modelos_lenguaje/agent/tools_utility.py` y registrarlas
- [X] T041 [US2] Añadir `request_human_contact` a `src/proyecto_modelos_lenguaje/agent/actions.py` (`WRITE_TOOLS`, `TOOL_DESCRIPTIONS`, `ARG_SCHEMAS`, ejecución tras aprobación reutilizando el registro de contactos de la spec 019) y registrarla en el catálogo
- [X] T042 [US2] Conectar el catálogo al grafo en `src/proyecto_modelos_lenguaje/agent/graph.py`: el nodo del agente recibe `specs_for_route(route)`; añadir `plan_steps` (data-model §7, sin LLM, a partir de ruta, intención y herramientas candidatas, completado con los pasos ejecutados) y los campos de invocación a la traza; actualizar `TurnModel`/modelos de traza en `src/proyecto_modelos_lenguaje/api_models.py`
- [X] T043 [US2] Ajustar `prompts/` del agente (descripción de herramientas y regla «no busques ante saludos») y registrar el cambio en `docs/prompt_log.md` (§3.21 con SHA)
- [X] T044 [US2] Añadir `GET /api/tools` en `src/proyecto_modelos_lenguaje/api.py` y los subcomandos `tools [--json] [--markdown PATH]`, `evaluate --tools [--fake] [--json-out]` en `src/proyecto_modelos_lenguaje/agent/__main__.py` (exactitud de herramienta, búsquedas en triviales, latencia; escribe `docs/evaluacion_herramientas.{json,md}`)
- [X] T045 [US2] HITL en el canal (research R8) en `src/proyecto_modelos_lenguaje/channels/bridge.py`: `pending_approval` con resumen legible y «Responde *SÍ* para confirmar o *NO* para cancelar (vence en 10 min)»; tabla `channel_pending` (data-model §5: `thread_id`, `action_id`, `tool`, `summary`, `expires_at = created_at + 10 min`, `state ∈ pending|approved|rejected|expired`); interpretación sí/no; vencimiento → `resume(..., decision="reject")`; prueba en `tests/unit/channels/test_bridge_hitl.py` (escribir primero)
- [X] T046 [US2] Comando `/traza` en el puente: ruta, `plan_steps` y herramientas del último turno, en formato WhatsApp
- [X] T047 [US2] Mostrar en la vista técnica de la web el plan y las herramientas del turno (componente de traza existente en `web/src/components/ChatView.tsx` + prueba vitest en `web/src/test/`)
- [X] T048 [US2] Correr `agent evaluate --tools` con DeepSeek (red) y con `--fake`; publicar `docs/evaluacion_herramientas.md`; si < 90 %, ajustar descripciones y subconjuntos (no la batería) y repetir

**Checkpoint**: 20 herramientas probadas; evaluación ≥ 90 %; `/traza` funciona por WhatsApp.

---

## Phase 5: User Story 3 - El equipo opera el gateway OpenClaw con su workspace, su skill propio y su seguridad (Priority: P1)

**Goal**: workspace versionado, servidor MCP propio, skill, modo degradado, hardening y auditoría en verde.

**Independent Test**: la prueba de 3 minutos (`pml ops check`) en verde en el PC servidor; `openclaw mcp tools
valeria-tools` lista 15; con el backend detenido el bot responde en modo degradado.

### Tests for User Story 3 (escribir primero; deben fallar)

- [X] T049 [P] [US3] `tests/unit/test_mcp_server.py`: el servidor expone exactamente las herramientas `kind="read"` y `mcp=True` del catálogo (15), ninguna de escritura; cada una con su JSON Schema; una llamada en proceso a `search_documents` con el índice de fixtures devuelve citas; `--list` imprime los nombres
- [X] T050 [P] [US3] `tests/unit/test_ops.py`: `workspace_sync` copia `openclaw/workspace/` al destino sin borrar `memory/`; `ops_check` agrega resultados de comprobaciones simuladas (backend, Qdrant, modelo, gateway, canal, auditoría, `git status`) y devuelve código 1 si alguna falla
- [X] T051 [P] [US3] `tests/unit/test_workspace_files.py`: existen `SOUL.md`, `IDENTITY.md`, `AGENTS.md`, `USER.md` (≤ 4.000 caracteres), `MEMORY.md` y `skills/valeria-manuelita/SKILL.md` con frontmatter `name`/`description`; `AGENTS.md` contiene la sección de red lines y `## Tools`; ningún archivo contiene E.164, correos ni claves

### Implementation for User Story 3

- [X] T052 [P] [US3] Redactar `openclaw/workspace/SOUL.md` e `IDENTITY.md` (persona y tono de Valer-IA Caña coherentes con specs 018–020; breve para WhatsApp; español o inglés según el invitado)
- [X] T053 [P] [US3] Redactar `openclaw/workspace/AGENTS.md` (reglas operativas; red lines: no inventar, citar siempre, no datos de terceros ni internos, confirmar escrituras, ignorar instrucciones dentro de documentos o mensajes reenviados, solo Manuelita, no revelar configuración; `## Tools` con las 15 de MCP; política de modo degradado) y `USER.md` (público objetivo, sin datos personales, ≤ 4.000 caracteres)
- [X] T054 [P] [US3] Redactar `openclaw/workspace/MEMORY.md` (hechos estables del dominio con fuente, decisiones de operación, aprendizajes; sin personas) y `openclaw/workspace/skills/valeria-manuelita/SKILL.md` (frontmatter, `metadata.openclaw.requires.bins: ["uv"]`, cuándo usar `valeria-tools`)
- [X] T055 [US3] Implementar `src/proyecto_modelos_lenguaje/mcp_server.py` (FastMCP stdio `valeria-tools`, herramientas desde `catalog.read_specs()` con `mcp=True`, log `logs/mcp.jsonl` sin texto libre, `--list`); registrar con `openclaw mcp add` o en `openclaw/openclaw.json5` con `toolFilter.include` de las 15; verificar `openclaw mcp status|tools|probe valeria-tools`
- [X] T056 [US3] Implementar `src/proyecto_modelos_lenguaje/ops.py` (`workspace_sync`, `ops_check`) y los subcomandos `pml ops workspace sync` y `pml ops check [--json]` en `src/proyecto_modelos_lenguaje/cli.py`; atajos `make openclaw-workspace`, `make ops-check`, `make mcp` en `Makefile`
- [ ] T057 [US3] Hardening en el PC servidor: sandbox (`mode: "all"`, Docker), `tools.deny`, `fs.workspaceOnly`, `exec.security: "deny"`, `elevated.enabled: false`; correr `openclaw security audit --deep`, corregir hasta cero críticos (revisar antes cualquier `--fix`) y guardar el resumen (sin datos sensibles) en `docs/evaluacion_blindaje_canal.md` § Auditoría
- [ ] T058 [US3] Probar el modo degradado: detener el backend, escribir por WhatsApp y comprobar respuesta del agente nativo con `valeria-tools` y aviso de modo degradado; registrar evidencia (log) en `docs/despliegue.md` § Contingencia
- [X] T059 [US3] Evaluación de inyección por el canal: `agent shield --channel` en `src/proyecto_modelos_lenguaje/agent/__main__.py` reutilizando `agent/adversarial.py` con un adaptador que envía los ataques por `ChannelBridge` (directos en el mensaje e indirectos con el corpus malicioso `tests/fixtures/rag/malicious/`); métricas: obedece, filtra prompt, escrituras sin confirmación (todas = 0); `docs/evaluacion_blindaje_canal.{json,md}`; prueba sin red en `tests/unit/agent/test_shield_channel.py`

**Checkpoint**: auditoría sin críticos; MCP y skill visibles; modo degradado probado.

---

## Phase 6: User Story 4 - La memoria sobrevive al reinicio y un hilo nuevo recuerda el perfil (Priority: P2)

**Goal**: continuidad tras reinicio, perfil en hilo nuevo, olvido a pedido y memoria auditable, por WhatsApp.

**Independent Test**: quickstart §3 paso 5 completo (guardar → reiniciar → continuar → `/nuevo` → saludo por nombre →
`/olvidar` + SÍ → borrado).

### Tests for User Story 4 (escribir primero; deben fallar)

- [X] T060 [P] [US4] `tests/unit/channels/test_bridge_memory.py`: con `SqliteSaver`/`SqliteStore` reales en `tmp_path`, guardar perfil aprobado; recrear `ChannelBridge` y `ChatService` (reinicio) → mismo `thread_id` y contexto; `/nuevo` → otro `thread_id` y el perfil se recupera; `/olvidar` → `pending_approval` con `forget_memory(scope="all")` y tras «SÍ» el Store queda vacío
- [X] T061 [P] [US4] `tests/unit/agent/test_memory_audit.py`: `agent memory list --user wa-…` muestra clave, valor, namespace y fecha de cada recuerdo, sin números ni texto de mensajes

### Implementation for User Story 4

- [X] T062 [US4] Comandos `/nuevo` (cierra hilo con `closed_at`, abre otro) y `/olvidar` en `src/proyecto_modelos_lenguaje/channels/bridge.py`
- [X] T063 [US4] Subcomando `memory list --user ID [--json]` en `src/proyecto_modelos_lenguaje/agent/__main__.py` leyendo `SqliteStore` (namespaces `("users", id, "profile"|"preferences")`)
- [ ] T064 [US4] Verificación manual por WhatsApp (quickstart §3 paso 5) con reinicio real de backend y gateway; registrar en § Notas

**Checkpoint**: SC-006 cumplido (5/5 hilos continúan; 5/5 perfiles en hilo nuevo).

---

## Phase 7: User Story 5 - El conocimiento se reconstruye con un comando y se evalúa con métricas y una proyección 2D (Priority: P2)

**Goal**: `pml corpus rebuild`, Qdrant servidor, 30 consultas con Recall@10/nDCG@10 frente a la línea base y t-SNE con
lectura.

**Independent Test**: el comando termina sin intervención con manifiesto 100 % trazable; `docs/evaluacion_modulo3.md` y
`docs/proyeccion_embeddings.png` existen con las consultas fallidas marcadas y explicadas.

### Tests for User Story 5 (escribir primero; deben fallar)

- [X] T065 [P] [US5] `tests/unit/test_corpus.py` (muestra mínima de `tests/fixtures/silver` y `tests/fixtures/rag`): `rebuild(from_="silver", workdir=tmp)` ejecuta las etapas en orden sin tocar `data/`; `manifest.json` (data-model §11) con conteos, hashes SHA-256 y `fragments_with_provenance == fragments_total`; `--in-place` exige confirmación explícita
- [X] T066 [P] [US5] `tests/unit/rag/test_project.py`: con 200 vectores sintéticos y 5 consultas, `project()` devuelve puntos `fragment|query` con `x`, `y`, `topic_id`, `recall_at_10`, `failed`; es determinista con semilla 2026; escribe PNG y JSON en `tmp_path`
- [X] T067 [P] [US5] `tests/unit/rag/test_module3_queries.py`: `tests/fixtures/rag/module3_queries.jsonl` tiene 30 entradas con `id`, `question`, `expected_unit_ids` (≥ 1), `topic_id`, `source_question_id` existentes en `eval_questions.jsonl`

### Implementation for User Story 5

- [X] T068 [US5] Añadir opción de directorio de salida a `silver build` y `gold build` en `src/proyecto_modelos_lenguaje/cli.py` (y sus constructores) si no existe (research R15 «verificar»), sin cambiar el comportamiento por defecto
- [X] T069 [US5] Implementar `src/proyecto_modelos_lenguaje/corpus.py` (`rebuild(from_, workdir, in_place, scrape, campaign, limit)` → plata → oro → índice → Qdrant; verificaciones; manifiesto) y el subcomando `pml corpus rebuild` en `cli.py`; atajo `make corpus`
- [X] T070 [US5] Generar `tests/fixtures/rag/module3_queries.jsonl`: muestra de 30 de las 35 preguntas puntuables con semilla 2026 (script reproducible `scripts/sample_module3_queries.py`), **antes** de evaluar
- [X] T071 [US5] Extender `src/proyecto_modelos_lenguaje/rag/evaluate.py` y `rag/__main__.py` con `--queries` y uso del servidor Qdrant (`QDRANT_URL`), comparación con la línea base M2 (Recall@10 0,67 / nDCG@10 0,50) y salida `docs/evaluacion_modulo3.{json,md}`
- [X] T072 [US5] Implementar `src/proyecto_modelos_lenguaje/rag/project.py` y el subcomando `rag project [--sample 5000] [--seed 2026]`: t-SNE (`perplexity=30`, `init="pca"`, `random_state=2026`) de una muestra estratificada por `topic_id` (≤ 5.000) + las 30 consultas; colores por tema; consultas fallidas (Recall@10 = 0) marcadas; `docs/proyeccion_embeddings.{png,json}` (PNG < 1 MB)
- [ ] T073 [US5] En el PC servidor: `make qdrant-up`, `rag qdrant build --force`, `rag qdrant status` (servidor, HNSW `m=16`), `pml corpus rebuild --from bronze`, `rag evaluate --queries …`, `rag project`; escribir la lectura de clústeres y fallos en `docs/evaluacion_modulo3.md`

**Checkpoint**: SC-007 y SC-008 cumplidos y documentados.

---

## Phase 8: User Story 6 - Cualquier persona entiende y despliega el proyecto sin abrir el código (Priority: P2)

**Goal**: documentación final completa y repositorio sin secretos.

**Independent Test**: una persona ajena sigue `docs/despliegue.md` hasta tener el bot respondiendo en un canal de
prueba (< 2 h); `gitleaks` sin hallazgos.

- [X] T074 [P] [US6] Escribir `docs/despliegue.md`: requisitos, variables de entorno, Docker/Qdrant, OpenClaw (instalación, plantilla, servicio), vinculación de WhatsApp, allowlist/emparejamiento, backend como servicio, túnel de la web, verificación (`ops check`), contingencia (revincular QR, reinicios, modo degradado, regla del sábado)
- [X] T075 [P] [US6] Escribir `docs/manual_whatsapp.md` para invitados: cómo escribir, qué preguntar, comandos (`/ayuda`, `/nuevo`, `/olvidar`, `/traza`), confirmaciones SÍ/NO, privacidad
- [X] T076 [P] [US6] Generar `docs/herramientas.md` con `agent tools --markdown docs/herramientas.md` y enlazarlo
- [X] T077 [P] [US6] Escribir `docs/decisions/0028-openclaw-whatsapp-puente.md` (contexto, decisión R1, alternativas, consecuencias; SQLite frente a Postgres R17; número personal R6; túnel R3)
- [X] T078 [US6] Actualizar `README.md` (arquitectura con gateway y WhatsApp en Mermaid, enlaces a despliegue, manual, herramientas, evaluaciones y ADR) y el diagrama Archify `docs/arquitectura.json` → regenerar `docs/arquitectura.html`
- [X] T079 [US6] Actualizar `CONSTITUTION.md` a v1.16.0 (Fase 3 concretada: OpenClaw, WhatsApp, catálogo de 20, MCP, Node solo para el plugin, nuevas dependencias, SQLite justificado) en el mismo commit que la arquitectura
- [ ] T080 [US6] Correr `gitleaks detect --log-opts="--all"` y revisar que `openclaw/`, `docs/` y `bitacora/` no contienen números, tokens ni sesiones (SC-010)

---

## Phase 9: User Story 7 - El equipo sustenta en 15 minutos con la demo en el teléfono del invitado (Priority: P3)

**Goal**: guion, autoevaluación, ensayo y contingencia listos el viernes.

**Independent Test**: ensayo cronometrado ≤ 15 min (pitch ≤ 7) con un teléfono ajeno y cada integrante respondiendo su
parte.

- [X] T081 [P] [US7] Escribir `docs/rubrica_modulo3.md` siguiendo `docs/rubrica_modulo2.md`: tabla de los 15 ítems con peso, estado y evidencia (archivo/comando); guion 0:00–7:00 pitch (problema de Manuelita, propuesta de valor, demo real en WhatsApp, cierre comercial) y 7:00–15:00 discusión; división por integrante; preguntas probables con respuesta
- [X] T082 [P] [US7] Versión en inglés del pitch y de la discusión en `docs/rubrica_modulo3.md` § English version (bonus)
- [X] T083 [US7] Prueba de carga: 10 usuarios concurrentes con `pml channels simulate` en paralelo (y, si es posible, 10 teléfonos reales); medir p90 y máximo (SC-002); registrar en `docs/evaluacion_modulo3.md` § Carga
- [ ] T084 [US7] Viernes 27: `pml ops check` en verde en el PC servidor, ensayo cronometrado ES/EN con teléfono ajeno, autoevaluación ≥ 4,5 con evidencia (SC-012, SC-013); actualizar `docs/rubrica_modulo3.md`

---

## Phase 10: Polish & Cross-Cutting Concerns

- [ ] T085 [P] Telegram (extra, solo si sobra tiempo): `channels.telegram` en `openclaw/openclaw.json5` con `${TELEGRAM_BOT_TOKEN}`, `dmPolicy: "pairing"`; el puente ya acepta `channel: "telegram"`
- [ ] T086 [P] Notas de voz por WhatsApp (deseable): con `channels.voice_notes = true`, transcribir con el servicio de la spec 023 en `channels/bridge.py` y prueba en `tests/unit/channels/test_bridge_voice.py`
- [X] T087 `make check` completo (ruff, pytest, vitest, build) y pruebas del plugin; corregir
- [ ] T088 Verificación final de la quickstart completa (§1–§5) y de la checklist «Obligatorio» del Anuncio 007; anotar resultados en § Notas
- [ ] T089 Preparar PR (por un integrante), CI verde, merge y tag `v3.0.0` (Fase 3 regla 7); sin `Co-authored-by` ni firmas de IA

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (1)**: T006–T007 son la ruta crítica (infra y spike) y empiezan ya.
- **Foundational (2)**: depende de T001 y T007; bloquea todo lo demás.
- **US1 (3)**: depende de Foundational. **MVP**.
- **US2 (4)**: depende de Foundational (catálogo); T045–T046 dependen del puente de US1 (T023).
- **US3 (5)**: depende de Foundational; T055 depende del catálogo completo de US2 (las 15 de lectura); T058 depende de US1.
- **US4 (6)**: depende de US1 (puente) y de la aprobación por SÍ/NO (T045).
- **US5 (7)**: independiente del canal; solo depende de Setup (T001, Qdrant).
- **US6 (8)**: depende de US1–US5 para describir lo real; T074–T077 pueden empezar en borrador.
- **US7 (9)**: depende de todo lo anterior.
- **Polish (10)**: al final; T085–T086 opcionales.

### Within Each User Story

Pruebas primero (fallan) → modelos/almacenamiento → servicios → endpoints/CLI → verificación manual.

### Parallel Opportunities

- Setup: T002–T005 en paralelo mientras se hace T006.
- US1: T013–T018 en paralelo; luego T019–T022 en paralelo; T023 → T024 → T025.
- US2: T029–T036 en paralelo; T037–T040 en paralelo (archivos distintos).
- US3: T049–T051 y T052–T054 en paralelo.
- US5 entera en paralelo con US1–US3 (otro integrante).
- US6: T074–T077 en paralelo.

---

## Parallel Example: User Story 2

```text
Pruebas:        T029 series · T030 entidades · T031 conocimiento · T032 utilidades · T033 contacto · T035 API · T036 batería
Implementación: T037 tools_series.py · T038 tools_entities.py · T039 tools_knowledge.py · T040 tools_utility.py
```

## Parallel Example: dos integrantes

```text
Integrante A: Setup (T006–T007) → Foundational → US1 → US3 → US4
Integrante B: US5 (corpus, Qdrant, evaluación, t-SNE) → US2 (herramientas) → US6 (documentación)
Ambos:        US7 (guion, ensayo) el viernes
```

---

## Implementation Strategy

### MVP First (US1)

1. Setup + Foundational (lunes): gateway con la plantilla y WhatsApp vinculado.
2. US1 (martes): WhatsApp → Valer-IA con citas e hilo. **Validar con teléfonos reales**: ya es demostrable.

### Incremental Delivery

1. US1 → demo mínima en WhatsApp (3.2).
2. US2 → 20 herramientas (1.1, 1.2).
3. US3 → workspace, MCP, seguridad (3.1, 3.3, 3.4, 4.2).
4. US4 → memoria demostrada en el canal (1.3).
5. US5 → datos y evaluación (2.1–2.3).
6. US6 → documentación (4.3).
7. US7 → sustentación (5.1, 5.2).

Si el tiempo se acaba: US1, US2 y US3 (P1) cubren el 55 % de la nota y los «no se acepta»; US5 y US6 se recortan antes
que US1–US3.

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes.
- Las pruebas no usan red ni claves; las que tocan el gateway real o DeepSeek llevan el marcador `network`.
- Los números de teléfono reales solo viven en `.env` fuera de Git y en la configuración de ejecución de OpenClaw.
- Commit después de cada tarea o grupo lógico (los hace un integrante); detenerse en cada checkpoint para validar.

---

## Notas de implementación (2026-11-23)

**Hecho en el repositorio (77 de 89 tareas):** catálogo de 20 herramientas (`agent/catalog.py` + `tools_*.py`),
puente del canal (`channels/`, `/api/channels/*`, `/api/tools`), plugin `valeria-bridge`, servidor MCP
`valeria-tools`, workspace de OpenClaw, configuración `openclaw/openclaw.json5`, `pml corpus rebuild`,
`rag project` (t-SNE), `rag evaluate --queries`, `agent tools|evaluate --tools|shield --channel|memory list`,
`pml channels simulate`, `pml ops check|workspace sync`, documentación (despliegue, manual, ADR 0028, README,
CONSTITUTION 1.16.0, rúbrica del Módulo 3 con versión en inglés) y la vista técnica de la web (plan y herramientas).
`make check`: 1651 pytest, 147 vitest y build en verde; plugin: 10 pruebas (`npm test`).

**Decisiones durante la implementación:**

- **T007, hallazgos del spike:** el puente usa `before_dispatch` en vez de `before_agent_reply`, porque recibe
  el mensaje ya autenticado con el remitente. Se leyeron los tipos del SDK del paquete `openclaw@2026.11.7`; falta
  confirmarlo con el gateway vivo (research R1).
- **El hilo lo crea el servicio:** en el primer turno el puente pasa `thread_id=None` y adopta el id que crea
  `ChatService`, porque el servicio rechaza ids que no existen en el checkpointer.
- **Rutas de las herramientas del Módulo 2:** las tres siguen en las rutas documental, estructurada y mixta, así
  que la conducta evaluada en el Módulo 2 no cambia. Las nuevas se ofrecen por ruta.
- **Reglas nuevas del enrutador (`tool_cue_decision`):** identificador de unidad, aritmética, comparación entre
  años y canal oficial de contacto.
- **Evaluación de herramientas con DeepSeek:** 72,1 % → **88,4 %** (meta 90 %) y 0 búsquedas en triviales
  (`docs/evaluacion_herramientas.md`). Los flujos de perfil propio (spec 014) y de contacto humano (spec 019) no
  se cambiaron.
- **Blindaje por el canal en modo demo:** 11/11, con 0 instrucciones obedecidas, 0 filtraciones y 0 escrituras.
  Falta la corrida real (`agent shield --channel --mode real`).
- **Carga local (portátil, modo real):** 10/10 respuestas con p90 de 7,3 s (`docs/evaluacion_carga_canal.md`).
- **Trazado en pruebas:** `tests/conftest.py` desactiva LangSmith; antes la suite enviaba trazas si `.env` lo
  activaba.
- **gitleaks:** el binario no se pudo ejecutar localmente (permiso denegado), así que el historial lo revisa el
  job `secretos` del CI. En local solo se buscaron patrones en los archivos nuevos: únicamente números de prueba
  ficticios.

**Pendiente (requiere el PC servidor, teléfonos reales o al equipo):**

- **Infraestructura:** T006 (Docker, OpenClaw, vincular WhatsApp por QR), T057 (sandbox y `security audit`),
  T058 (modo degradado) y T073 (Qdrant servidor, `corpus rebuild` real, evaluación de 30 consultas y t-SNE; el
  índice local necesita `rag index rebuild --force`).
- **Pruebas con teléfonos y ensayo:** T028 y T064 (teléfonos reales), T080 (revisar el job `secretos` en el PR)
  y T084/T088 (ensayo del viernes y quickstart completa).
- **Entrega:** T089 (PR, CI, merge y tag, solo por un integrante).
- **Opcionales:** T085 (Telegram) y T086 (notas de voz).
- **Documentación por completar:** Archify (`docs/arquitectura.json` → `.html`) sigue sin regenerarse y
  `.specify/memory/constitution.md` no se alineó con la 1.16.0.
