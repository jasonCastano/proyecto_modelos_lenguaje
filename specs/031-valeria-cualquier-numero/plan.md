# Implementation Plan: Valer-IA atiende a cualquier número de WhatsApp

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR que las specs 028–030; `setup-plan` reporta
`031-valeria-cualquier-numero` por `.specify/feature.json`) | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/031-valeria-cualquier-numero/spec.md`

## Summary

El número no habilitado no recibió respuesta porque el canal está en **modo cerrado** (`dmPolicy: "allowlist"` de
OpenClaw con tres números). El modo abierto de la spec 028 (`openclaw_env.ps1 -Mode open`) ya cumple la regla de
OpenClaw (`allowFrom` con `"*"`), pero no se había activado ni tenía protecciones. Diseño (research R1–R7):

1. **Apertura verificable**:
   - `-Mode open` sigue siendo el paso único;
   - `ops check` muestra `modo-canal` (abierto, con advertencia, o cerrado), leyendo solo `WA_DM_POLICY`;
   - la prueba con números nuevos queda en el quickstart.
2. **Operadores**: `VALERIA_OPERATORS` (seudónimos, como `VALERIA_PLANNERS`). Los operadores no tienen límites y son
   los únicos con atajos ocultos cuando la lista existe. `pml channels pseudonym` calcula el seudónimo sin guardar el
   número.
3. **Límites**:
   - 20 mensajes cada 10 min y 100 por día, por seudónimo;
   - se controlan en `ChannelBridge.handle`, antes de la cola y del agente;
   - al superarlos, un único aviso natural en el idioma del mensaje; luego silencio.
4. **Bloqueo**: `pml channels block|unblock|blocked`. Un bloqueado se ignora sin llamar al agente.
5. **Uso visible**: `GET /api/channels/status` añade `people_today`, `limited_today` y `blocked_today`, sin números ni
   contenido.

## Technical Context

**Language/Version**: Python 3.14 (backend); PowerShell 5.1 (script del gateway, sin cambios de interfaz).

**Primary Dependencies**: FastAPI; SQLite (almacén del canal ya existente); OpenClaw 2026.11.10 (`dmPolicy` y
`allowFrom` de WhatsApp). Sin dependencias nuevas.

**Storage**: tablas nuevas `channel_usage` y `channel_blocked` en `<estado>/channels.sqlite3`, fuera del repositorio.
Migración aditiva en `ChannelStore._migrate`.

**Testing**:

- pytest: `tests/unit/channels/test_limits.py` (nuevo), `test_bridge.py`, `test_store.py`,
  `tests/unit/test_ops.py`, `tests/api/test_channels_api.py`;
- prueba manual con 2 números nuevos.

**Target Platform**: el portátil servidor (gateway 18790, backend 8000, SIM dedicada vinculada).

**Project Type**: servicio web + gateway de mensajería.

**Performance Goals**: el control de límites es una lectura y escritura SQLite por mensaje (< 5 ms). Un número
limitado no ocupa la cola ni el modelo.

**Constraints**:

- nunca guardar ni imprimir números completos (regla 10);
- avisos sin comandos (conversación natural);
- grupos deshabilitados siempre;
- el modo cerrado sigue disponible.

**Scale/Scope**: decenas de personas el día de la sustentación; cambio solo en el canal (no en el agente, la
recuperación ni los prompts).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| Regla 10 Seudónimos | ✅ | Límites, bloqueo y operadores trabajan con `wa-<16 hex>`. Los comandos calculan el seudónimo y no guardan ni imprimen el número. |
| §3.9 Seguridad | ✅ | Canal abierto con límites por número, bloqueo, grupos deshabilitados y atajos del operador restringidos. `ops check` advierte cuando está abierto. |
| Regla 22 (2.8.0) Conversación natural | ✅ | Avisos de límite naturales, en el idioma del mensaje y sin comandos. |
| Regla 21 Evaluaciones publicadas no bajan | ✅ | El agente no cambia. Blindaje y herramientas no se tocan; `make check` debe pasar. |
| §3.3 Capas medallion intactas | ✅ | No se toca `data/`. El estado nuevo vive fuera del repo. |
| §4.3 Autoría y proceso | ✅ | Spec Kit completo; commits y PR solo con autorización de un integrante. |
| Cambios de proceso/tecnología → CONSTITUTION.md | ✅ con tarea | Se documenta el canal abierto con límites en la regla del canal (spec 028) en el mismo PR. |

**Resultado**: pasa sin enmiendas de principios. Hay una actualización documental de la regla del canal.
**Re-check post-design**: igual. Las tablas y comandos nuevos solo manejan seudónimos. ✅

## Project Structure

### Documentation (this feature)

```text
specs/031-valeria-cualquier-numero/
├── spec.md
├── plan.md                       # este archivo
├── research.md                   # R1–R7
├── data-model.md                 # modo, operadores, uso por número, bloqueados, estado
├── quickstart.md                 # sin teléfono, operadores, abrir/cerrar, prueba con números nuevos
├── contracts/
│   └── channel-open-access.md    # respuestas ante límites, estado, CLI del operador, ops check
├── checklists/requirements.md
└── tasks.md                      # /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── agent/config.py               # ChannelsConfig: rate_window_minutes, rate_max_messages, daily_max_messages
├── channels/limits.py            # nuevo: operators(), limit_decision() (lógica pura y probada)
├── channels/store.py             # channel_usage y channel_blocked (migración aditiva)
├── channels/bridge.py            # bloqueo y límites antes de la cola; atajos solo para operadores; textos es/en
├── channels/journal.py           # people_today, limited_today, blocked_today en recent_stats
├── channels/__main__.py          # pseudonym, block, unblock, blocked
├── ops.py                        # comprobación modo-canal (WA_DM_POLICY del .env externo)
config/agent.toml                 # límites por defecto
.env.example                      # VALERIA_OPERATORS
scripts/openclaw_env.ps1          # mensaje de modo abierto con la advertencia y el siguiente paso
docs/manual_whatsapp.md, docs/despliegue.md, CONSTITUTION.md
tests/unit/channels/test_limits.py, test_bridge.py, test_store.py; tests/unit/test_ops.py; tests/api/test_channels_api.py
```

**Structure Decision**:

- Los límites y el bloqueo van en el backend (`ChannelBridge`), que ya conoce el seudónimo, la cola y el registro.
- OpenClaw solo decide abierto o cerrado.
- La lógica de decisión queda en un módulo puro (`channels/limits.py`) para probarla sin red ni gateway.

## Complexity Tracking

Sin violaciones que justificar.
