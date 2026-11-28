# Implementation Plan: Saludo y presentación al iniciar una conversación

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR que las specs 028–031; `setup-plan` reporta
`038-saludo-nueva-conversacion` por `.specify/feature.json`) | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/038-saludo-nueva-conversacion/spec.md`

## Summary

Hoy la presentación depende de que el modelo la escriba: `prompts/agent.md` le pide presentarse solo «si te saludan
o preguntan qué sabes hacer». Con una pregunta directa o una nota de voz el modelo no se presenta. Además, el canal
nunca abre un hilo nuevo por inactividad: `ChannelStore.ensure_user` devuelve siempre el hilo activo. Diseño
(research R1–R7):

1. **Inicio de conversación en el canal**:
   - columna nueva `introduced` en `channel_threads`;
   - la migración la crea con `DEFAULT 1`, así los hilos existentes no se presentan de golpe;
   - los hilos nuevos se crean con `introduced = 0`.

   `ChannelStore.open_conversation` reemplaza el uso de `ensure_user` en el bridge y devuelve el hilo y el motivo
   (`first_contact`, `inactivity` o `None`):
   - el motivo `inactivity` se da cuando el último mensaje es más viejo que `conversation_idle_hours`;
   - en ese caso cierra el hilo y abre otro, como `/nuevo`, conservando el perfil.

   El reinicio pedido por la persona ya abre un hilo nuevo (`intent == "restart"`) y queda con el motivo `restart`.
2. **Presentación determinista en el bridge**:
   - si el hilo de la respuesta tiene `introduced = 0` y el turno se atiende, el bridge antepone una presentación
     de dos frases como máximo, en el idioma del turno;
   - hay tres variantes por idioma, elegidas por el hilo, y usan el nombre de la persona si el servicio lo
     reconoce;
   - luego marca `introduced = 1`.

   No depende del modelo: así se cumple el 100 % (SC-001) también en modo demo y con el modelo caído. Si la
   respuesta del modelo ya se presenta (menciona a Valer-IA al inicio), no se agrega otra. Si solo abre con «¡Hola!»,
   ese saludo se reemplaza por la presentación para no saludar dos veces.
3. **Voz**: `ConversationVoice.for_answer(..., opening=...)` antepone la presentación hablada al guion, sin pasarla
   al modelo del guion para que no la reescriba ni la duplique. El texto que acompaña sigue siendo solo fuentes
   (spec 030). Las respuestas de texto fijo (`for_text`) ya leen la presentación porque va en `spoken`.
4. **Exclusiones**: no se presentan los avisos de límite y bloqueo (spec 031, antes del hilo), los atajos del
   operador ni la confirmación de «empecemos de nuevo» sin pregunta. En este último caso la presentación queda para
   la siguiente solicitud. Los errores del modelo llevan una frase de quién es Valer-IA, pero no marcan el hilo como
   presentado.
5. **Medición**: `ChannelLogRecord` agrega `conversation_start` (motivo o `null`) e `introduced` (`agent`,
   `bridge` o `null`), sin texto ni números. `pml channels simulate --check` cuenta presentaciones faltantes o
   repetidas.
6. **Modo degradado**: `openclaw/workspace/AGENTS.md` pide la misma presentación al inicio de una conversación,
   como regla de mejor esfuerzo (FR-015).

## Technical Context

**Language/Version**: Python 3.14 (backend). Markdown del workspace de OpenClaw. Sin cambios en el plugin
TypeScript.

**Primary Dependencies**: las existentes (FastAPI, LangGraph, SQLite del canal, Phonon y ffmpeg para la voz). Sin
dependencias nuevas.

**Storage**: `<estado>/channels.sqlite3`. Columna aditiva `channel_threads.introduced`, que la migración de
`ChannelStore._migrate` crea con `DEFAULT 1`. No se borra ni se reescribe nada. `channel_users.last_seen` ya existe
y es la base de la inactividad.

**Testing**:

- pytest: `tests/unit/channels/test_store.py`, `test_bridge.py`, `test_voice.py`, `test_journal.py`,
  `tests/unit/agent/test_config.py`;
- `tests/unit/channels/test_greeting.py` (nuevo): variantes, idioma, nombre y fusión con «¡Hola!»;
- guion `tests/fixtures/channels/conversation_start.jsonl` para `pml channels simulate --check`;
- prueba manual en el teléfono (quickstart).

**Target Platform**: el portátil servidor (backend 8000, gateway 18790) y el equipo de respaldo.

**Project Type**: servicio web y puente de mensajería.

**Performance Goals**:

- la decisión de inicio es una lectura y una escritura SQLite más por mensaje (< 5 ms);
- la presentación no agrega llamadas al modelo;
- en voz agrega unos 3 a 5 s de audio al inicio de la primera nota.

**Constraints**:

- presentación de dos frases como máximo (FR-013);
- sin comandos ni menús (regla 22);
- idioma del turno (spec 029);
- con voz, el texto lleva solo las fuentes (spec 030);
- límites y bloqueo antes de la cola (spec 031);
- nunca texto ni números en los registros.

**Scale/Scope**: solo el canal (WhatsApp/Telegram por el mismo puente). El grafo del agente, la recuperación y la
web no cambian.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| Regla 22 Conversación y voz | ✅ | Presentación natural, sin comandos; con voz, guion hablado y fuentes por escrito. |
| Regla 10 Seudónimos y registros sin contenido | ✅ | El registro agrega solo el motivo y el origen de la presentación. |
| §3.5 Prompts versionados (`docs/prompt_log.md`) | ✅ | No cambia `prompts/agent.md` ni `voice_script.md`. El cambio del workspace de OpenClaw se anota en el registro de prompts. |
| Regla 21 Evaluaciones publicadas no bajan | ✅ | El agente no cambia; `make check` en verde. La simulación del canal suma el guion de inicio de conversación. |
| §3.3 Capas medallion intactas | ✅ | No se toca `data/`. |
| §4.3 Autoría y proceso | ✅ | Spec Kit completo; commits y PR solo con autorización de un integrante. |
| Cambios de arquitectura, tecnología o proceso → CONSTITUTION.md | ✅ sin enmienda | Es comportamiento del canal dentro de la regla 22. No cambia arquitectura, tecnología ni proceso. |

**Resultado**: pasa sin enmiendas.
**Re-check post-design**: igual. La columna nueva y los campos del registro no contienen datos personales. ✅

## Project Structure

### Documentation (this feature)

```text
specs/038-saludo-nueva-conversacion/
├── plan.md              # este archivo
├── research.md          # R1–R7
├── data-model.md        # hilo, presentación, registro
├── quickstart.md        # pruebas sin teléfono y en el teléfono
├── contracts/
│   └── conversation-start.md
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
config/agent.toml                                  # [channels] conversation_idle_hours = 12
src/proyecto_modelos_lenguaje/
├── agent/config.py                                # ChannelsConfig.conversation_idle_hours (1–720)
└── channels/
    ├── store.py                                   # introduced, open_conversation, mark_introduced
    ├── greeting.py                                # nuevo: textos, variantes, nombre, fusión
    ├── bridge.py                                  # motivo de inicio, presentación, exclusiones
    ├── voice.py                                   # for_answer(opening=...)
    ├── journal.py                                 # conversation_start, introduced
    └── __main__.py                                # simulate --check: presentación faltante/repetida
openclaw/workspace/AGENTS.md                       # modo degradado (mejor esfuerzo)
docs/manual_whatsapp.md, docs/despliegue.md, docs/prompt_log.md
tests/unit/channels/{test_greeting,test_store,test_bridge,test_voice,test_journal}.py
tests/unit/agent/test_config.py
tests/fixtures/channels/conversation_start.jsonl
```

**Structure Decision**: proyecto único existente. La lógica nueva vive en `channels/`, donde ya están el idioma
del turno (spec 029), la voz solo con fuentes (spec 030) y los límites (spec 031). El grafo del agente no se toca.

## Complexity Tracking

Sin violaciones que justificar.
