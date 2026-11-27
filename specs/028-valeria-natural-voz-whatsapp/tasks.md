---

description: "Tareas de la spec 028: Valer-IA natural y con voz por WhatsApp, abierta el día de la sustentación"
---

# Tasks: Valer-IA natural y con voz por WhatsApp, abierta el día de la sustentación

**Input**: Design documents from `specs/028-valeria-natural-voz-whatsapp/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: incluidos. La spec fija criterios medibles (SC-001…SC-011) y la constitución exige pruebas sin red
(§3.8) y que ninguna evaluación publicada baje (regla 21).

**Organization**: por historia de usuario. Las tareas **(manual)** las ejecuta el equipo en el portátil
servidor; Claude entrega antes sus instrucciones paso a paso (FR-029, [openclaw-ops.md](contracts/openclaw-ops.md))
y no las ejecuta por su cuenta.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de la spec (US1 voz · US2 conversación natural · US3 acceso abierto · US4 planificador ·
  US5 coherencia técnica)

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: configuración y esqueletos compartidos

- [ ] T001 Confirmar la Fase A de la spec 024 en el portátil **sin Docker** (manual: `ffmpeg -version`, energía, `.env` externo, variables, workspace, plugin enlazado, backend y gateway como servicios; Docker Desktop desinstalado si no arranca) y anotar el resultado (sin secretos) en `specs/028-valeria-natural-voz-whatsapp/tasks.md` § Notas
- [X] T002 [P] Crear `scripts/qdrant_native.ps1` (research R12): `-Install` descarga `qdrant-x86_64-pc-windows-msvc.zip` v1.15.4 de las releases oficiales de GitHub a `%USERPROFILE%\.qdrant-valeria\`, verifica el archivo y escribe `config\config.yaml` con `service.host: 127.0.0.1`, puertos 6333/6334 y `storage.storage_path` en `%USERPROFILE%\.qdrant-valeria\storage`; `-Register` crea la tarea programada «ValerIA-Qdrant» (al iniciar sesión, reinicio si falla) y la inicia; `-Status` consulta `http://127.0.0.1:6333/` y muestra la versión; añadir el objetivo `qdrant-native` al `Makefile` y la sección «Qdrant sin Docker» en `docs/despliegue.md` (`make qdrant-up` queda como alternativa con Docker)
- [ ] T003 Instalar y registrar Qdrant nativo, fijar `QDRANT_URL=http://127.0.0.1:6333`, reconstruir el índice y verificar `rag qdrant status` en modo servidor con HNSW `m=16` (manual, instrucciones en `contracts/openclaw-ops.md` § O0); reemplaza el uso de Docker en las tareas T006 y T073 de la spec 024
- [X] T004 Ampliar `[channels]` en `config/agent.toml` y `ChannelsConfig` en `src/proyecto_modelos_lenguaje/agent/config.py`: `voice_notes = true`, `bridge_timeout_seconds = 90`, `queue_wait_seconds = 60`, `voice_max_seconds = 60`, `voice_retention_minutes = 10`, `voice_dir = "channels/voice"` (relativo a `MANUELITA_STATE_DIR`); pruebas de carga en `tests/unit/agent/test_config.py`
- [X] T005 [P] Añadir `[voice.languages.en]` en `config/voice.toml` (`model = "hf://gradium/phonon-31m-en"`, `voice` provisional `"Harper"`, `quant = "q8_0"`, licencia CC BY-NC 4.0) y leerlo en `src/proyecto_modelos_lenguaje/voice/config.py` como mapa `language → (model, voice, quant)` conservando `es` como hoy
- [X] T006 [P] Permitir `language = "auto"` en `src/proyecto_modelos_lenguaje/stt/config.py` y `stt/engine.py` (faster-whisper con `language=None`; `Transcription.language` devuelve el idioma detectado; idiomas aceptados `es`/`en`, otro → `es` con marca `language_fallback`); pruebas con transcriptor simulado en `tests/unit/stt/test_language_auto.py`
- [X] T007 [P] Crear los fixtures `tests/fixtures/channels/natural_conversation.jsonl` (≥ 15 mensajes: saludo, capacidades, cambio de tema, «empecemos de nuevo», «olvida lo que sabes de mí», «dale», «mejor no», «mmm», pregunta nueva con acción pendiente, «respóndeme por escrito», «mándame audio», 3 en inglés) y `tests/fixtures/agent/planning_activation.jsonl` (15 de planificación + 15 parecidas que no lo son, con `expected: true|false` y `follow_up` para 3 repreguntas), fijados antes de medir (regla 21)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: prueba técnica de voz y piezas que usan varias historias

**⚠️ CRITICAL**: la voz (US1) no se implementa hasta cerrar T008–T013; US2, US4 y US5 pueden avanzar antes

- [X] T008 Entregar al equipo las instrucciones exactas de la prueba técnica (S1–S5) en `specs/028-valeria-natural-voz-whatsapp/contracts/openclaw-ops.md` § O2 (comandos, qué observar, criterio de éxito y salida alternativa de cada punto, research R1)
- [X] T009 Crear el CLI de transcripción `src/proyecto_modelos_lenguaje/channels/transcribe_cli.py` (contrato channel-api-v2 §3: lee la ruta, envía a `POST /api/channels/transcriptions` con `X-Channel-Token`, timeout 20 s, respaldo en proceso con `stt.engine.get_stt_service()` y `faster_whisper.decode_audio`; stdout = transcripción de una línea; sin habla → vacío y código 0; error → código 1) y su prueba en `tests/unit/channels/test_transcribe_cli.py`
- [X] T010 Implementar `POST /api/channels/transcriptions` en `src/proyecto_modelos_lenguaje/api.py` y su modelo en `api_models.py` (loopback + token como `_channel_guard`; `multipart/form-data` `file` ≤ 16 MB y ≤ 120 s; decodifica Ogg/Opus/MP3/WAV/M4A en memoria; respuesta `{text, language, audio_ms, latency_ms}`; errores `400 audio_invalid`, `413 audio_too_long`, `503 stt_unavailable`; no registra texto) con pruebas en `tests/api/test_channels_transcriptions.py`
- [X] T011 Añadir en `openclaw/openclaw.json5` `tools.media.audio` (`enabled: true`) con un modelo `type: "cli"`, `command: "uv"`, `args: ["run", "--project", "${VALERIA_REPO}", "python", "-m", "proyecto_modelos_lenguaje.channels.transcribe_cli", "{{AttachmentPath}}"]`, `timeoutSeconds: 45`, `capabilities: ["audio"]`; `dmPolicy: "${WA_DM_POLICY}"`; `timeoutMs: 90000` del puente; ajustar `tests/unit/test_openclaw_config.py`
- [X] T012 Sandbox sin Docker en `openclaw/openclaw.json5` (research R12): `sandbox.mode: "off"`; reforzar `tools.deny` para que el agente nativo solo use el MCP `valeria-tools` (grupos `runtime`, `fs`, `automation`, navegador, web y mensajería, además de `sessions_spawn`/`sessions_send`), conservar `exec.security: "deny"`, `elevated.enabled: false` y `fs.workspaceOnly: true`; validar con `openclaw doctor`; ajustar `tests/unit/test_openclaw_config.py` (sin backend Docker, denegaciones presentes) y documentar el riesgo aceptado en `docs/despliegue.md` § Seguridad
- [ ] T013 Ejecutar la prueba técnica S1–S5 (manual, con la SIM vinculada según O1) y registrar en `specs/028-valeria-natural-voz-whatsapp/research.md` § «Hallazgos de la prueba» el formato exacto del bloque `[Audio]`, el método de envío de audio que funcionó (gateway `send` o `openclaw message send`), la voz inglesa elegida, si PyAV codifica Opus y si `dmPolicy` por variable valida; actualizar `contracts/channel-api-v2.md` §4 si algo cambia
- [X] T014 [P] Ampliar `ChannelStore` en `src/proyecto_modelos_lenguaje/channels/store.py`: columnas `reply_format TEXT DEFAULT 'auto'` (valores `auto` | `text` | `voice`) y `last_route TEXT` en `channel_threads` con migración idempotente; métodos `get/set_reply_format`, `get/set_last_route`; estado `superseded` en `channel_pending`; pruebas en `tests/unit/channels/test_store.py`
- [X] T015 [P] Crear `src/proyecto_modelos_lenguaje/channels/intents.py` con `detect_intent(text) -> Intent` (`restart`, `format_text`, `format_voice`, `none`) y `decision_of(text) -> approve | reject | ambiguous | None` según data-model «Intent» y research R6 (frases ≤ 8 palabras, español e inglés, mezcla de afirmación y negación → `ambiguous`), y `looks_like_new_question(text)` («?» o ≥ 6 palabras sin decisión); pruebas exhaustivas en `tests/unit/channels/test_intents.py`
- [X] T016 Ampliar `InboundMessage`, `ChannelReply` y `ChannelLogRecord` (`input_mode` `text`|`voice`, `language_hint` `es`|`en`|null, `voice` opcional; registro con `input_mode`, `language`, `reply_format`, `voice_ms`, `script_ms`, `voice_sent`, sin texto ni audio) en `src/proyecto_modelos_lenguaje/channels/bridge.py` y `channels/journal.py`, y `ChannelMessageRequest`/`ChannelReplyModel` en `api_models.py` (contrato channel-api-v2 §1: `text` requerido si `kind ∈ {text, audio}`)

**Checkpoint**: prueba técnica cerrada, almacenamiento, intenciones y contrato listos

---

## Phase 3: User Story 1 - Nota de voz con respuesta en voz (Priority: P1) 🎯 MVP

**Goal**: un audio en español o inglés recibe nota de voz conversacional en el mismo idioma + texto con fuentes

**Independent Test**: quickstart §4 (simulador) y §5 pasos 2–4 (WhatsApp)

### Tests for User Story 1

- [X] T017 [P] [US1] Pruebas del guion hablado en `tests/unit/channels/test_voice.py`: sin `[`, `http`, «Fuentes», viñetas ni Markdown; 40–110 palabras; toda cifra del guion aparece en la respuesta; respaldo determinista si el modelo falla; idioma `en` produce guion en inglés (modelo guionado)
- [X] T018 [P] [US1] Pruebas del puente con voz en `tests/unit/channels/test_bridge.py`: `input_mode=voice` + `auto` → `voice` presente; texto + `auto` → sin `voice`; `reply_format=text` anula la voz; `format_voice` la fuerza; audio sin transcripción → «No te escuché bien…» sin turno del agente; falla de síntesis → texto + disculpa y `voice_error` registrado
- [X] T019 [P] [US1] Pruebas del plugin en `openclaw/plugins/valeria-bridge/test/bridge.test.ts`: contenido con bloque `[Audio]` (formato de T013) → `kind: "audio"`, `input_mode: "voice"`, `text` = transcripción; respuesta con `voice` → se llama primero al emisor de audio y luego se devuelve el texto; si el envío del audio falla, igual se devuelve el texto; `timeoutMs` 90000 por defecto

### Implementation for User Story 1

- [X] T020 [US1] Crear `prompts/voice_script.md` (versión 1.0, secciones como `prompts/agent.md`): entrada pregunta + respuesta citada + idioma; salida 40–110 palabras, conversacional, segunda persona, cifras habladas, sin citas/URLs/listas/fuentes, sin hechos nuevos, cierre breve; versiones es/en; registrar en `docs/prompt_log.md` §3.24
- [X] T021 [US1] Soportar varios idiomas en `src/proyecto_modelos_lenguaje/voice/engine.py`: un sintetizador Phonon por idioma con carga perezosa (`es` existente, `en` con el modelo y la voz de T005/T013), `synthesize(text, voice=None, language="es")`, estado por idioma en `status()`, precalentamiento del inglés cuando `channels.voice_notes` está activo; motor simulado por idioma para pruebas; pruebas en `tests/unit/voice/test_languages.py`
- [X] T022 [US1] Crear `src/proyecto_modelos_lenguaje/channels/voice.py`: `build_script(question, answer, language, model)` (prompt T020 + `voice.text.clean_for_speech` + validación de cifras + respaldo de 600 caracteres), `render_voice(script, language) -> VoiceReply` (síntesis T021, recorte a `voice_max_seconds`, Ogg/Opus 48 kHz mono con PyAV o WAV según T013, archivo `<uuid>` en `$MANUELITA_STATE_DIR/channels/voice/`) y `purge_old(dir, minutes=10)` al arrancar y en cada turno (FR-008)
- [X] T023 [US1] Integrar la voz en `ChannelBridge` (`src/proyecto_modelos_lenguaje/channels/bridge.py`): idioma = `language_hint` o `agent.plan.detect_language(text)`; decidir voz con data-model «VoiceReply» (`reply_format` × `input_mode`); generar guion y audio tras la respuesta de texto; mensajes de acción/confirmación con guion corto si la entrada fue voz; medir `script_ms` y `voice_ms`
- [X] T024 [US1] Exponer `voice` en la respuesta de `POST /api/channels/messages` (`src/proyecto_modelos_lenguaje/api.py`) y en `pml channels simulate` (`src/proyecto_modelos_lenguaje/channels/__main__.py`: `--kind audio`, `--language`, muestra la ruta y la duración del audio) con pruebas en `tests/api/test_channels_api.py`
- [X] T025 [US1] Implementar en el plugin (`openclaw/plugins/valeria-bridge/src/bridge.ts` e `index.ts`) la extracción de la transcripción del bloque `[Audio]` y el envío de la nota de voz con el método confirmado en T013 (`api.runtime.gateway.request("send", …)` o `openclaw message send --channel whatsapp --target <senderId> --media <ruta>`), antes de devolver `{ handled: true, text }`; `timeoutMs` 90000 en `openclaw.plugin.json`
- [ ] T026 [US1] Reinstalar el plugin y reiniciar el gateway (manual, instrucciones previas en `contracts/openclaw-ops.md`), y verificar quickstart §5 pasos 2–4 con un teléfono de prueba (nota de voz es y en, y «respóndeme por escrito»); anotar resultados sin números en § Notas

**Checkpoint**: la voz funciona de punta a punta en modo cerrado

---

## Phase 4: User Story 2 - Conversación natural, sin comandos (Priority: P1)

**Goal**: todo se pide con palabras propias; ningún texto sugiere comandos

**Independent Test**: quickstart §2 con `natural_conversation.jsonl`

### Tests for User Story 2

- [X] T027 [P] [US2] Prueba «sin comandos» en `tests/unit/channels/test_no_commands.py`: recorre todas las constantes de texto de `channels/bridge.py`, los textos de `contracts/conversation.md` implementados y las respuestas del guion `natural_conversation.jsonl` (modo demo) y falla si aparece `/` seguido de una palabra
- [X] T028 [P] [US2] Pruebas de confirmación natural en `tests/unit/channels/test_bridge.py`: «dale», «sí, guárdalo», «go ahead» aprueban; «mejor no», «déjalo así», «no thanks» rechazan; «mmm» re-pregunta; una pregunta nueva marca la acción `superseded`, avisa y responde; confirmar tras vencer explica y no ejecuta; ninguna ejecución sin afirmación clara (SC-005)

### Implementation for User Story 2

- [X] T029 [US2] Reescribir los textos del canal en `src/proyecto_modelos_lenguaje/channels/bridge.py` según `contracts/conversation.md` (presentación, acción pendiente «¿Lo hago?», hecho/cancelado, re-pregunta, cambio de tema, vencimiento, reinicio, formato, medios no soportados, audio inaudible, error) en español e inglés según el idioma del mensaje; eliminar `HELP_TEXT` con comandos y `PLANNER_DENIED_TEXT`
- [X] T030 [US2] Enrutar intenciones en `ChannelBridge._dispatch` con `channels/intents.py`: `restart` → `store.new_thread` + texto natural (si trae pregunta, se responde en el hilo nuevo); `format_text`/`format_voice` → `store.set_reply_format` + confirmación natural (o respuesta a la pregunta que lo acompaña); acción pendiente con `decision_of` natural, `ambiguous` → re-pregunta, `looks_like_new_question` → `superseded` + aviso + turno normal
- [X] T031 [US2] Mantener los comandos como atajos ocultos del operador (`/traza`, `/nuevo`, `/olvidar`, `/perfil`, `/cancelar`; `/ayuda` → presentación natural) sin mencionarlos en ningún texto; retirar las menciones de comandos de `channels/__main__.py` y de la ayuda de la CLI dirigida a personas
- [X] T032 [US2] Actualizar `prompts/agent.md` a 1.9 (la 1.8 es de la spec 025): ante saludo o «¿qué puedes hacer?» presentarse en 1–2 frases (incluye que acepta notas de voz), nunca sugerir comandos, olvidar datos y cambiar de perfil por intención natural; registrar en `docs/prompt_log.md` §3.24 con la evidencia del guion natural
- [X] T033 [US2] Cola por usuario sin perder mensajes en `ChannelBridge.handle`: el candado espera hasta `queue_wait_seconds` (60) en vez de responder `busy`; si vence, respuesta natural breve y registro `queue_timeout`; pruebas de dos mensajes concurrentes del mismo usuario respondidos en orden en `tests/unit/channels/test_bridge.py`
- [X] T034 [US2] Ampliar `pml channels simulate` con `--script <jsonl>` (envía los mensajes de un archivo como un mismo remitente y muestra cada respuesta) en `src/proyecto_modelos_lenguaje/channels/__main__.py` y validar quickstart §2 en modo demo
- [X] T035 [P] [US2] Quitar comandos de `openclaw/workspace/AGENTS.md`, `SOUL.md` y `skills/valeria-manuelita/SKILL.md` (el agente nativo del modo degradado también conversa sin comandos) y ajustar `tests/unit/test_workspace_files.py`

**Checkpoint**: conversación natural validada sin teléfono

---

## Phase 5: User Story 3 - Acceso abierto el día de la prueba (Priority: P1)

**Goal**: cualquier número escribe y recibe respuesta en la ventana abierta; modo cerrado fuera de ella

**Independent Test**: quickstart §6

### Implementation for User Story 3

- [X] T036 [US3] Añadir `-Mode open|closed` a `scripts/openclaw_env.ps1` (research R8): cerrado → `WA_DM_POLICY=allowlist` y restaura `WA_ALLOW_1..3` desde `WA_TEST_1..3`; abierto → guarda los números de prueba en `WA_TEST_*`, `WA_DM_POLICY=open`, `WA_ALLOW_1=*`, vacía `WA_ALLOW_2..3`; edita solo `%USERPROFILE%\.openclaw-valeria\.env`, reinicia el gateway (`openclaw gateway restart --wait 30s`) y muestra `openclaw channels status`; nunca imprime números (los enmascara)
- [X] T037 [US3] Si la prueba S5 (T013) falló: crear `openclaw/openclaw.open.json5` (igual a `openclaw.json5` con `dmPolicy: "open"`, `allowFrom: ["*"]`) y hacer que `-Mode` cambie `OPENCLAW_CONFIG_PATH`; si S5 pasó, marcar esta tarea como no aplicable en § Notas
- [X] T038 [P] [US3] Actualizar `openclaw/.env.example` (`WA_DM_POLICY`, `WA_TEST_1..3`, sin valores reales) y `tests/unit/test_openclaw_config.py` (`groupPolicy: "disabled"`, `selfChatMode: false`, `dmPolicy` por variable)
- [X] T039 [US3] Documentar O3–O6 definitivos en `docs/despliegue.md` (§ Modo abierto/cerrado, § Cierre tras la sustentación: modo cerrado, `openclaw channels logout --channel whatsapp`, desvincular y desactivar la SIM) y en `docs/manual_whatsapp.md` (cómo hablarle a Valer-IA: texto o voz, sin comandos)
- [ ] T040 [US3] Verificar quickstart §6 (manual, con instrucciones previas): con `-Mode open` un teléfono que nunca escribió recibe respuesta; con `-Mode closed` ya no; un grupo no recibe respuesta (SC-006); anotar en § Notas

**Checkpoint**: modos abierto y cerrado operables con un comando

---

## Phase 6: User Story 4 - Planificador activado por contexto (Priority: P2)

**Goal**: cualquiera plantea un problema de planificación y Valer-IA responde como planificador, sin cambiar de perfil

**Independent Test**: quickstart §3

### Tests for User Story 4

- [X] T041 [P] [US4] Pruebas en `tests/unit/agent/test_planning_activation.py`: cada caso de `planning_activation.jsonl` (≥ 14/15 en cada lado), repregunta tras un turno `planning` sigue en planificación, vuelta a un tema general sale de planificación, el perfil del hilo no cambia, la advertencia de datos sintéticos aparece

### Implementation for User Story 4

- [X] T042 [US4] `config/profiles.toml`: `planificador.requires_authorization = false`; revisar `src/proyecto_modelos_lenguaje/agent/profiles.py` (el código de autorización queda inactivo, documentado) y las pruebas de perfiles afectadas (`tests/unit/agent/test_profiles*.py`, `tests/api/test_planning_api.py`, `tests/api/test_evidence_api.py`)
- [X] T043 [US4] Ajustar `PLANNING_CUE` y `planning_decision` en `src/proyecto_modelos_lenguaje/agent/router.py`: activar `planning` por señal en cualquier perfil (`reason="cue"`) o por repregunta cuando la ruta anterior fue `planning` (`reason="follow_up"`: «¿y si…?», «¿y con…?», «what if…», porcentaje o cifra sin tema nuevo); excluir usos informativos («programas sociales con cultivadores de caña», «¿cuánta caña molió en 2022?»)
- [X] T044 [US4] En `src/proyecto_modelos_lenguaje/agent/graph.py`: pasar la ruta anterior del hilo al router, aplicar el foco y las herramientas del planificador solo a ese turno sin modificar el perfil del hilo, guardar `last_route` (también vía `ChannelStore.set_last_route` en el canal), mostrar `reason` en la traza y retirar `PLANNER_ONLY_NOTE` del flujo abierto
- [X] T045 [US4] Añadir `agent evaluate --planning-activation [--markdown]` en `src/proyecto_modelos_lenguaje/agent/cli_m3.py` y `agent/__main__.py`; correrlo y escribir `docs/evaluacion_activacion_planificador.md` (aciertos, falsos positivos/negativos y lectura)
- [X] T046 [US4] Avisar a Roberto del cambio compartido con la web (activación automática del planificador también en la web) con un resumen en la descripción del PR y una línea en `docs/decisions/0032-valeria-natural-voz-whatsapp.md`

**Checkpoint**: planificación por contexto medida y documentada

---

## Phase 7: User Story 5 - Modo degradado y cifras coherentes (Priority: P3)

**Goal**: MCP de 15 herramientas y medición vigente de las 20 de atención

**Independent Test**: quickstart §1 (lista del MCP) y §7 (medición)

- [X] T047 [P] [US5] `mcp_allowed=False` en `get_plant_state`, `get_commitments` y `search_operating_procedures` (`src/proyecto_modelos_lenguaje/agent/tools_planning.py` o donde se declaren) y prueba que fija exactamente 15 herramientas en `tests/unit/test_mcp_server.py`; actualizar la lista de `openclaw/workspace/AGENTS.md`
- [X] T048 [US5] Correr `agent evaluate --tools --mode real --markdown` (43 consultas, 20 herramientas de atención) después de T032–T044; actualizar `docs/evaluacion_herramientas.{json,md}` con la nueva cifra y búsquedas en triviales; si baja de 88,4 % (regla 21), corregir router o prompt antes de publicar y documentar el análisis
- [X] T049 [P] [US5] Regenerar `docs/herramientas.md` (`agent tools --markdown`) con el discurso «20 de atención + 6 de planificación = 26» y unificar cifras en `docs/rubrica_modulo3.md` y `README.md`

**Checkpoint**: modo degradado coherente y cifras únicas en la documentación

---

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: constitución, decisiones, documentación, prueba final y entrega

- [ ] T050 Auditoría de seguridad sin Docker (manual, instrucciones previas): `openclaw security audit --deep` con el sandbox apagado; corregir hasta cero hallazgos críticos (revisar antes cualquier `--fix`) o documentar la excepción, y guardar el resumen sin datos sensibles en `docs/evaluacion_blindaje_canal.md` § Auditoría (reemplaza T057 de la spec 024)
- [X] T051 Enmienda MINOR 2.3.0 en `CONSTITUTION.md` (reglas 9, 11, 12, 14 (sandbox apagado sin virtualización, Qdrant nativo), 16 y 20 según plan § Constitution Check; nueva regla 22 de voz: transcripción y síntesis locales, audio temporal, guion sin citas, texto con fuentes; aclaración de la regla 8) con fila en el historial, en el mismo commit que el código
- [X] T052 [P] Escribir `docs/decisions/0032-valeria-natural-voz-whatsapp.md` (contexto, decisión, ruta B de voz, acceso abierto con SIM dedicada, conversación sin comandos, planificador por contexto, operación sin Docker: Qdrant nativo y sandbox apagado con controles compensatorios; reemplaza puntos de ADR 0028 y ADR 0031)
- [X] T053 [P] Actualizar `docs/rubrica_modulo3.md` (guion de la demo con nota de voz en español y en inglés, sin comandos; discusión técnica con `/traza` como atajo del operador), `docs/demo.md` y la sección del Módulo 3 en `README.md`
- [ ] T054 [P] Ampliar la evaluación de carga del canal en `docs/evaluacion_carga_canal.md` con 10 notas de voz simuladas (modo real, motores reales): latencia p90 del primer mensaje < 30 s (SC-003)
- [X] T055 Correr `agent shield --channel` en modo demo y real con los ataques también como transcripción de voz; actualizar el resultado en la documentación de blindaje del canal
- [X] T056 `make check` en verde (pytest sin red, vitest, build, Ruff) y `npm test` del plugin
- [ ] T057 Prueba con teléfonos ajenos en modo abierto (manual, viernes por la tarde): 10 notas de voz (≥ 3 en inglés), guion natural de 15 mensajes, planificación con repregunta, dos mensajes seguidos; registrar SC-001, SC-003, SC-004, SC-006 y SC-007 en § Notas sin números
- [ ] T058 Verificar quickstart completo (§1–§8) y escaneo de secretos (SC-010); anotar en § Notas
- [ ] T059 Preparar el PR (por un integrante, con autorización), CI verde, merge y sincronizar `main`; sin `Co-authored-by` ni firmas de IA
- [ ] T060 Sábado 6:30–8:00 (manual, O6): `pml ops check`, `-Mode open`, prueba de texto y de voz (es y en) desde un teléfono ajeno (SC-011); después de la sustentación, O5 (modo cerrado, desvincular, desactivar la SIM)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 manual; T003 (Qdrant nativo, manual) depende de T002 (script); T004–T007 sin dependencias entre sí (salvo T005/T006 que dependen de T004 solo por la configuración del canal)
- **Foundational (Phase 2)**: T013 (prueba técnica) depende de T001, T008–T012 y de tener la SIM vinculada (O1); T014–T016 no dependen de la SIM; T050 (auditoría) depende de T012
- **US1 (voz)**: depende de T013–T016
- **US2 (conversación natural)**: depende de T014–T016; no necesita la SIM
- **US3 (acceso abierto)**: depende de T013 (resultado S5); T040 necesita la SIM
- **US4 (planificador)**: depende de T007; independiente del canal salvo `last_route` (T014)
- **US5**: T047 independiente; T048 después de T032 y T043–T044 (cambios de router y prompt)
- **Polish**: después de las historias; T059 después de T056–T058; T060 el sábado

### Orden de trabajo recomendado (un solo equipo, en secuencia)

Como la SIM se vincula hoy más tarde, el orden práctico es: T001–T007 (incluye Qdrant nativo) → T008–T012 (incluye sandbox sin Docker) → T014–T016 → **US2**
(T027–T035) → **US4** (T041–T046) → T047 → (SIM vinculada) **T013** → **US1** (T017–T026) → **US3**
(T036–T040) → T048–T049 → Polish.

### Within Each User Story

- Pruebas primero (deben fallar), luego implementación
- Backend antes que plugin; plugin antes de la verificación manual
- Cada historia se cierra con su checkpoint antes de seguir

### Parallel Opportunities

- T002, T005, T006, T007 en paralelo
- T014, T015 en paralelo; T017, T018, T019 en paralelo
- T027, T028, T035 en paralelo; T041 en paralelo con T042
- T047, T049, T052, T053, T054 en paralelo

---

## Parallel Example: User Story 1

```text
Task: "T017 Pruebas del guion hablado en tests/unit/channels/test_voice.py"
Task: "T018 Pruebas del puente con voz en tests/unit/channels/test_bridge.py"
Task: "T019 Pruebas del plugin en openclaw/plugins/valeria-bridge/test/bridge.test.ts"
```

## Parallel Example: User Story 2

```text
Task: "T027 Prueba «sin comandos» en tests/unit/channels/test_no_commands.py"
Task: "T028 Pruebas de confirmación natural en tests/unit/channels/test_bridge.py"
Task: "T035 Quitar comandos del workspace de OpenClaw"
```

---

## Implementation Strategy

### MVP para el sábado

1. Phase 1 + Phase 2 (incluida la prueba técnica de voz)
2. US2 (sin comandos) y US1 (voz): son lo que ve el jurado
3. US3 (modo abierto): imprescindible para el teléfono del invitado
4. **STOP and VALIDATE**: quickstart §5 y §6 con un teléfono de prueba
5. US4 y US5 si el tiempo alcanza en el orden indicado; nunca se recorta la voz

### Orden de recorte si falta tiempo

1. T054 (carga con voz) y T055 en modo real → se documenta la medición de la spec 024
2. Continuidad del planificador en repreguntas (parte de T043–T044) → se deja solo la activación por señal
3. Nunca: voz (US1), conversación sin comandos (US2), modo abierto (US3), prueba final (T057, T060)

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes
- Las tareas manuales se ejecutan solo después de entregar sus instrucciones paso a paso
- Ningún número, token ni audio en Git; los audios viven en `$MANUELITA_STATE_DIR/channels/voice/` y se borran
- Commit por grupo lógico, a nombre de un integrante y con autorización

## Notas de implementación (2026-11-26)

- **Prueba técnica adelantada sin teléfono**: S4 ✅ (PyAV codifica y decodifica Ogg/Opus en el portátil); S5 ✅
  (`openclaw config validate` acepta `dmPolicy: "${WA_DM_POLICY}"` en modo `allowlist` y en modo `open` con `"*"`).
  Por eso T037 no aplica: no hace falta un segundo archivo de configuración. Quedan S1 (formato del bloque
  `[Audio]`), S2 (envío de la nota de voz) y S3 (modelo inglés) para T013, con la SIM vinculada.
- **Decodificación propia con PyAV**: `faster_whisper.decode_audio` falla con PyAV 19 (`metadata_errors` ya no
  existe); `channels/transcription.py` decodifica y remuestrea con PyAV directamente.
- **Endpoint de transcripción con cuerpo crudo** (no `multipart/form-data`) para no añadir `python-multipart`;
  contrato actualizado.
- **Envío de la nota de voz**: el método interno del gateway no está documentado; el plugin usa el CLI documentado
  `openclaw message send --media` con `execFile` (sin shell; destinatario validado).
- **Planificador por contexto**: 15/15 de planificación, 15/15 parecidas sin activar y 3/3 repreguntas
  (`docs/evaluacion_activacion_planificador.md`).
- **Escudo del canal (demo)**: 20/20 (7 directos por texto, 7 directos como nota de voz, 6 indirectos); 0
  obedecidos, 0 filtraciones, 0 escrituras sin confirmación.
- **`make check`**: 2.058 pytest, 185 vitest, build y Ruff en verde. Una corrida previa abortó con un
  `access violation` intermitente dentro de HiGHS (scipy) en Windows; dos corridas completas posteriores pasaron.
- **Atención**: al enlazar el plugin (`openclaw plugins install --link`), OpenClaw **reescribió**
  `openclaw/openclaw.json5` (quitó los comentarios y añadió `plugins.load.paths` con la ruta local y `meta`).
  No se commitea así: ver la propuesta de correr OpenClaw sobre una copia fuera del repositorio.
- **Falso positivo corregido (t04)**: al abrir el planificador a todos, «¿Cuál es la capacidad de la planta de
  biodiésel de Manuelita…?» activaba la planificación sintética (la señal «capacidad … planta» venía de la spec
  025, cuando solo regía para el perfil planificador). `router.is_planning_request` ahora descarta preguntas
  informativas sobre plantas reales o sobre Manuelita si no plantean un escenario; prueba de regresión en
  `test_router_planning.py`. La activación sigue en 15/15, 15/15 y 3/3.
- **d06 (`force_planner`)**: con el planificador libre, mostrar un plan ya no es una falla; ahora cuenta como
  obedecer solo si el plan aparece **sin** declarar datos sintéticos (`channel_eval.score_reply`, `unless`).
- **LangSmith**: la cuota mensual de trazas está agotada (errores 429 sin efecto en los resultados); las corridas
  reales de evaluación se hicieron con `LANGSMITH_TRACING=false`.
