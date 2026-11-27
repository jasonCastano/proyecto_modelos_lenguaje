# Implementation Plan: Valer-IA natural y con voz por WhatsApp, abierta el día de la sustentación

**Branch**: `028-valeria-natural-voz-whatsapp` | **Date**: 2026-11-26 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/028-valeria-natural-voz-whatsapp/spec.md`

## Summary

Convertir el canal de WhatsApp de la spec 024 en una conversación natural, sin comandos, con notas de voz en
español e inglés y abierta a cualquier número durante el ensayo y la sustentación. El diseño mantiene **un solo
agente** y añade dos tramos de audio alrededor del puente existente:

```text
Nota de voz del invitado (SIM dedicada, dmPolicy open en la ventana)
   │ OpenClaw descarga el audio y llama un CLI de transcripción (tools.media.audio, type "cli")
   │   └─ CLI delgado → POST /api/channels/transcriptions (loopback + token) → faster-whisper (spec 023,
   │      idioma automático es/en, modelo ya cargado en el backend)
   ▼
before_dispatch (valeria-bridge) recibe el bloque [Audio] con la transcripción → kind "audio" + transcript
   ▼
POST /api/channels/messages ──▶ ChannelBridge
   intenciones naturales (empezar de nuevo, formato de respuesta, confirmaciones) · cola por usuario
   ChatService (variante agent): router con planificación por contexto · catálogo · citas
   │
   ├─ texto: respuesta + citas + «Fuentes:» (formato de la spec 024)
   └─ si la entrada fue voz (o la persona pidió audio): guion hablado (prompt voice_script, idioma de la
      pregunta, sin citas) → Phonon (es: Rebeca · en: modelo phonon-31m-en) → Ogg/Opus temporal
   ▼
valeria-bridge: envía primero la nota de voz (runtime del gateway, audio = PTT en WhatsApp) y devuelve el texto
como respuesta del hook (OpenClaw lo entrega como mensaje aparte)
```

Además: planificador abierto para todos y activado por contexto (por turno, con continuidad en la repregunta),
MCP de vuelta a 15 herramientas de lectura, nueva medición de herramientas y modo abierto/cerrado operable con
un script sin tocar el código. Antes de implementar la voz se corre una **prueba técnica** (research R1) que
confirma tres hechos del gateway real: formato del bloque `[Audio]` en `before_dispatch`, envío de audio desde
el plugin y sustitución de variables en `dmPolicy`.

## Technical Context

**Language/Version**: Python 3.14 (backend, `uv`); TypeScript sobre Node 24.22.1 (plugin `valeria-bridge`).

**Primary Dependencies**: existentes: FastAPI, LangChain/LangGraph, DeepSeek (cliente OpenAI-compatible),
`faster-whisper` (spec 023, trae `av`/PyAV), `ptts` (Phonon, spec 016), `openclaw` 2026.11.x y
`@openclaw/whatsapp`. **Nuevas**: ninguna dependencia Python. **Nuevo modelo**: `hf://gradium/phonon-31m-en`
(voz en inglés, misma licencia CC BY-NC 4.0 que el modelo en español). **Externas**: `ffmpeg` en el portátil
servidor (respaldo de transcodificación de OpenClaw) y **Qdrant v1.15.4 como binario nativo de Windows** (el
portátil no permite virtualización: sin Docker, research R12).

**Storage**: `channels.sqlite3` (WAL) existente: columna nueva `reply_format` en `channel_threads` y registro de
`last_route` por hilo; audios temporales en `$MANUELITA_STATE_DIR/channels/voice/` con limpieza a los 10 minutos.

**Testing**: pytest sin red (motores de voz y dictado simulados, modelo guionado); `node --test` del plugin;
conjuntos de evaluación nuevos (`planning_activation.jsonl`, guion de conversación natural); medición real de
herramientas (`agent evaluate --tools --mode real`) y prueba manual con teléfonos.

**Target Platform**: un portátil Windows 11 que hace de servidor (backend como tarea programada, gateway como
servicio), conectado a la corriente e internet.

**Project Type**: servicio web (FastAPI) + plugin de gateway + configuración operativa.

**Performance Goals**: respuesta a una nota de voz (primer mensaje) < 30 s en el 90 % de los casos (SC-003);
respuesta a texto sin cambios (p90 ≈ 7 s medido en la spec 024).

**Constraints**: sin números, tokens ni audios en Git; transcripción y voz locales; modelo de lenguaje en la
nube (regla 8); timeout del puente de 45 s → 90 s (cola por usuario + voz; enmienda de la regla 12); ninguna
evaluación publicada puede bajar de su último valor (regla 21).

**Scale/Scope**: ≤ 20 invitados simultáneos durante la sustentación; ~10 archivos de backend, plugin,
configuración, 2 prompts, documentación y enmienda constitucional.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §I / §4.3 Autoría: solo jasonCastano o Robertto48, sin firmas de bot | ✅ | Commits y PR a nombre de Jason; Claude prepara y no publica sin autorización. |
| §3.6 Prompts versionados y registrados | ✅ | `prompts/voice_script.md` 1.0 nuevo y `prompts/agent.md` 1.8 (presentación natural, sin comandos); entradas en `docs/prompt_log.md`. |
| §IV Generación anclada y citas | ✅ | El texto conserva citas y fuentes; el guion hablado deriva solo de la respuesta citada (no añade hechos) y lo verifica una prueba. |
| §3.9 / regla 10 Seudónimos, sin números ni texto en registros | ✅ | El audio no se registra ni se versiona; registros con seudónimo; el número de la SIM vive solo en `%USERPROFILE%\.openclaw-valeria\.env`. |
| Regla 8: modelo en la nube, nunca local en la demo | ✅ | Aplica al modelo de lenguaje; transcripción y síntesis locales ya existen (specs 016 y 023) y no son el modelo conversacional. Se aclara en la enmienda. |
| Regla 9: número de un integrante; `allowlist` y `pairing` en la jornada | ⚠️ **Se enmienda** | SIM dedicada; modo cerrado (lista de prueba) y modo abierto (`dmPolicy: "open"`, `allowFrom: ["*"]`) solo en el ensayo y la jornada; grupos deshabilitados; número desactivado después. |
| Regla 11: escrituras con «SÍ/NO» | ⚠️ **Se enmienda (texto)** | Se mantiene la confirmación humana con vencimiento de 10 min; acepta expresiones naturales y re-pregunta ante ambigüedad. |
| Regla 12: modo degradado si el backend cae o tarda > 45 s | ⚠️ **Se enmienda** | 90 s para cubrir cola por usuario y voz; el MCP vuelve a 15 herramientas (cumple «solo lectura» y «el modo degradado no planifica»). |
| Regla 16: el perfil se borra con `/olvidar` | ⚠️ **Se enmienda (texto)** | Se borra por intención natural («olvida lo que sabes de mí»); el atajo queda oculto. |
| Regla 20: planificador solo autorizado en WhatsApp | ⚠️ **Se enmienda** | Libre para todos en web y WhatsApp; se mantiene «ninguna herramienta toca sistemas reales» y «guardar exige confirmación». Reemplaza la ADR 0031 en ese punto. |
| Regla 14: sandbox Docker sin red | ⚠️ **Se enmienda** | Sin virtualización en el portátil (R12): `sandbox.mode: "off"` con `exec` denegado, `elevated` apagado, `fs.workspaceOnly` y `tools.deny` que deja solo el MCP de lectura; auditoría sin críticos o excepción documentada. |
| Regla 15 / rúbrica 2.2: Qdrant servidor | ✅ | Binario nativo de Qdrant (HNSW real) como tarea programada, solo en loopback; `make qdrant-up` (Docker) queda como alternativa. |
| Reglas 18–19: datos sintéticos declarados, cifras del optimizador | ✅ | Sin cambios; la activación automática conserva la advertencia y la paridad. |
| Regla 21: evaluaciones publicadas no bajan | ✅ con riesgo | La nueva medición de herramientas (88,4 % publicado) se corre antes de publicar; si baja, se corrige antes del merge (R10). La activación del planificador tiene su propio conjunto fijado antes de medir. |
| §3.1 Dependencias justificadas | ✅ | Ninguna dependencia Python nueva; el modelo inglés y `ffmpeg` se justifican en research (R3, R4). |
| Cambios de arquitectura actualizan la constitución en el mismo commit | ✅ | Enmienda MINOR 2.3.0 + ADR 0032 + historial en el mismo commit. |

**Resultado**: pasa con seis enmiendas (la regla 14 por la falta de virtualización del portátil) pedidas explícitamente por la spec (Complexity Tracking). No hay
violaciones sin justificar.

**Re-check post-design**: el diseño de Phase 1 no añade desviaciones: el audio es temporal y local, el texto
mantiene las citas, el catálogo sigue siendo único y la operación abierta/cerrada no toca archivos versionados.
✅

## Project Structure

### Documentation (this feature)

```text
specs/028-valeria-natural-voz-whatsapp/
├── spec.md
├── plan.md                    # este archivo
├── research.md                # R1–R11 (incluye la prueba técnica de voz)
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── channel-api-v2.md      # cambios a /api/channels/messages y nuevo /api/channels/transcriptions
│   ├── conversation.md        # intenciones naturales, confirmaciones y textos del canal
│   └── openclaw-ops.md        # instrucciones paso a paso para el equipo (SIM, voz, modo abierto/cerrado)
├── checklists/requirements.md
└── tasks.md                   # /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── channels/
│   ├── bridge.py              # intenciones naturales, cola por usuario, formato de respuesta, voz
│   ├── intents.py             # NUEVO: léxico es/en (empezar de nuevo, texto/voz, sí/no, ambigüedad)
│   ├── voice.py               # NUEVO: guion hablado + síntesis por idioma + Ogg/Opus temporal + limpieza
│   ├── transcribe_cli.py      # NUEVO: CLI delgado que OpenClaw llama con {{AttachmentPath}}
│   ├── store.py               # reply_format y last_route por hilo
│   └── format.py              # sin cambios de contrato
├── voice/engine.py, config.py # varias voces/modelos por idioma (es, en)
├── stt/config.py, engine.py   # idioma "auto" (es/en) para el canal
├── agent/router.py            # activación de planificación por contexto + continuidad
├── agent/graph.py             # ruta planning por turno sin cambiar el perfil del hilo
├── agent/catalog.py           # mcp_allowed=False en 3 lecturas de planificación
├── api.py, api_models.py      # contrato v2 del canal y endpoint de transcripción
config/profiles.toml           # planificador sin autorización
config/voice.toml              # [voice.languages.en]
config/agent.toml              # [channels] voice_notes, bridge_timeout_seconds=90, queue_wait_seconds
prompts/voice_script.md        # NUEVO (1.0)
prompts/agent.md               # 1.8: presentación natural, nunca sugerir comandos
openclaw/openclaw.json5        # dmPolicy/allowFrom por variables, tools.media.audio, timeout del puente
openclaw/plugins/valeria-bridge/src/bridge.ts, index.ts   # [Audio] → transcript; envío de la nota de voz
openclaw/workspace/AGENTS.md, SOUL.md, skills/…          # sin comandos; 15 herramientas MCP
scripts/openclaw_env.ps1       # -Mode open|closed
scripts/qdrant_native.ps1      # NUEVO: Qdrant nativo (-Install, -Register, -Status), sin Docker
Makefile                       # objetivo qdrant-native
tests/unit/channels/test_intents.py, test_voice.py, test_bridge.py (ampliado), test_transcribe_cli.py
tests/unit/agent/test_planning_activation.py, tests/fixtures/agent/planning_activation.jsonl
tests/fixtures/channels/natural_conversation.jsonl
docs/: despliegue.md, manual_whatsapp.md, herramientas.md, evaluacion_herramientas.*,
       evaluacion_activacion_planificador.md, rubrica_modulo3.md, decisions/0032-*.md, prompt_log.md
CONSTITUTION.md (2.3.0)
```

**Structure Decision**: se extiende la estructura de la spec 024 (`channels/` en el backend y el plugin en
`openclaw/plugins/valeria-bridge`). La lógica de voz vive en el backend porque ahí están los motores ya cargados
(spec 016 y 023), el texto citado y el idioma; el plugin solo transporta.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Regla 9 (acceso abierto, SIM dedicada) | La demo exige que cualquier invitado escriba sin preparación (spec, Historia 3) | `pairing` obliga a aprobar cada código a mano en plena demo |
| Regla 12 (90 s) | Cola por usuario + guion + síntesis sobre la respuesta normal | 45 s haría caer al modo degradado (sin voz) mensajes en cola |
| Regla 20 (planificador libre) | Decisión del equipo: misma experiencia que la web | Mantener autorización contradice la decisión D3 |
| Reglas 11 y 16 (texto) | Conversación sin comandos (Historia 2) | Mantener «SÍ/NO» y `/olvidar` como única vía contradice FR-009/FR-013 |
| Regla 14 (sandbox apagado) | El firmware del portátil tiene la virtualización deshabilitada; Docker no arranca | Backends `ssh`/`crabbox` exigen otra máquina o servicio en la nube; cambiar la BIOS de un equipo corporativo no depende del equipo |
| Endpoint nuevo de transcripción | Reutilizar el modelo ya cargado y cumplir < 30 s | Un CLI que cargue faster-whisper en cada audio tarda 5–10 s extra por arranque |
