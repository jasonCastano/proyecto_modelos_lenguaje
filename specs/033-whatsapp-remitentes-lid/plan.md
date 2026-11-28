# Implementation Plan: Respuesta automática a cuentas de WhatsApp identificadas solo por ID (LID)

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–032; `setup-plan` reporta
`033-whatsapp-remitentes-lid` por `.specify/feature.json`) | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/033-whatsapp-remitentes-lid/spec.md`

## Summary

El componente `@openclaw/whatsapp` 2026.11.10 descarta los mensajes cuyo remitente llega solo como `…@lid` sin
equivalencia con el número: lanza un error y los deja en reintentos. Además, su normalizador de destinos convierte
un `…@lid` en un número falso `+<lid>`. Diseño (research R1–R9):

1. **Parche versionado** `openclaw/patches/whatsapp-lid.mjs`, aplicado por `openclaw_env.ps1 -Install`, con dos
   cambios anclados, idempotentes y marcados (`valeria-lid v1`):
   - **entrada**: si no hay número, se intenta `remoteJidAlt` y, si tampoco hay, se usa el propio `…@lid` como
     identidad, en lugar de descartar el mensaje;
   - **salida**: `normalizeWhatsAppTarget` conserva `<lid>@lid`.

   `ops check` agrega `soporte-lid` (nativo, parcheado o ausente).
2. **Backend**:
   - `identity` acepta `…@lid` (normalizado a `lid:<dígitos>`), con seudónimo `wa-` estable y máscara `ID ••••1234`;
   - el registro agrega `sender_kind` (`phone` o `lid`);
   - descarta como `stale` los mensajes con más de 15 minutos (`stale_minutes`);
   - `pml channels block|unblock --pseudonym`.
3. **Puente**: el respaldo de voz por CLI acepta destinos `…@lid`. El texto ya vuelve al chat de origen.
4. **Gobierno**: ADR 0038 y enmienda MINOR 2.10.0. Las reglas 8 y 10 permiten un parche versionado y verificable
   sobre el componente de WhatsApp, y extienden los seudónimos a los ID de WhatsApp.
5. **Activación prudente**: primero las pruebas automáticas, luego la prueba real con la cuenta que falló. Se
   activa en el equipo principal solo si pasa; si no, se documenta la limitación para la sustentación.

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript del plugin `valeria-bridge` (Node 24.22.1); JavaScript
ESM sin dependencias para el parche; PowerShell 5.1 para `openclaw_env.ps1`.

**Primary Dependencies**: OpenClaw 2026.11.10 y `@openclaw/whatsapp` 2026.11.10 (Baileys 7.0.0-rc14); FastAPI;
SQLite del canal. Sin dependencias nuevas.

**Storage**:

- sin tablas nuevas; `channel_users` guarda el seudónimo y la máscara `ID ••••1234`;
- los archivos parcheados viven en `%USERPROFILE%\.openclaw-valeria\npm\…` (fuera del repo), con copia `.orig`.

**Testing**:

- **pytest**: `tests/unit/channels/test_identity.py`, `test_bridge.py`, `test_cli_operator.py` y `test_journal.py`;
  `tests/unit/test_ops.py` (`soporte-lid`); `tests/unit/agent/test_config.py` (`stale_minutes`);
  `tests/api/test_channels_api.py` (remitente `…@lid`);
- **`node --test`** del parche, sobre copias mínimas de los archivos con los anclajes reales: aplica, es
  idempotente, detecta la versión nativa y falla sin anclajes;
- **`npm test`** del puente (`voiceCommandArgs` con `@lid`);
- **prueba real** (quickstart §3) con la cuenta solo-ID.

**Target Platform**: el portátil servidor y el equipo de respaldo de Roberto (Windows 11).

**Project Type**: servicio web, gateway de mensajería y plugin.

**Performance Goals**: sin costo adicional; el parche quita una espera infinita.

**Constraints**:

- nunca valores de ID ni números en registros, pruebas ni el repo (regla 10);
- no tocar archivos del componente a mano;
- el parche no adivina: con anclajes distintos, falla con un mensaje claro;
- el modo cerrado conserva su comportamiento.

**Scale/Scope**: chats individuales de WhatsApp; grupos fuera de alcance.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| Regla 8 Canal por OpenClaw, un solo agente | ✅ con enmienda | Se mantiene OpenClaw. Se agrega que un parche versionado, anclado y verificable (`ops check`) puede corregir un defecto del componente de WhatsApp mientras no exista la corrección oficial (ADR 0038). |
| Regla 10 Seudónimos | ✅ con enmienda | Los ID de WhatsApp (`…@lid`) se tratan igual que un número: se convierten en `wa-<16 hex>` y nunca se registran. |
| Regla 9 Modo abierto con protecciones | ✅ | Límites, bloqueo (también por seudónimo) y modo cerrado intactos. |
| §3.3 Capas medallion | ✅ | No se toca `data/`. |
| Regla 21 Evaluaciones no bajan | ✅ | El agente no cambia; `make check` en verde. |
| §4.3 Autoría y proceso | ✅ | Spec Kit completo; commit y PR con autorización. La enmienda requiere a ambos integrantes. |
| Cambios de tecnología → CONSTITUTION.md en el mismo commit | ✅ con tarea | ADR 0038, enmienda 2.10.0 y fila de historial en el mismo cambio. |

**Resultado**: pasa con una enmienda MINOR justificada. Es una corrección acotada a un defecto de un tercero, con
salida limpia cuando exista la versión nativa.
**Re-check post-design**: igual. El parche es reversible (copia `.orig` y reinstalación del plugin) y está
verificado por `ops check`. ✅

## Project Structure

### Documentation (this feature)

```text
specs/033-whatsapp-remitentes-lid/
├── plan.md
├── research.md            # R1–R9
├── data-model.md
├── quickstart.md
├── contracts/
│   └── lid-support.md      # parche, identidad, CLI y ops check
├── checklists/requirements.md
└── tasks.md                # /speckit-tasks
```

### Source Code (repository root)

```text
openclaw/patches/whatsapp-lid.mjs              # nuevo: parche anclado, idempotente, --check
openclaw/patches/test/whatsapp-lid.test.mjs    # nuevo: node --test con fragmentos de los anclajes
scripts/openclaw_env.ps1                       # -Install aplica el parche antes de arrancar el gateway
openclaw/plugins/valeria-bridge/src/bridge.ts  # voiceCommandArgs acepta …@lid
src/proyecto_modelos_lenguaje/
├── channels/identity.py                       # …@lid → lid:<dígitos>; máscara ID ••••1234
├── channels/bridge.py                         # stale_minutes, sender_kind
├── channels/journal.py                        # sender_kind
├── channels/__main__.py                       # block/unblock --pseudonym
├── agent/config.py, config/agent.toml         # [channels] stale_minutes = 15
└── ops.py                                     # check «soporte-lid»
docs/decisions/0038-whatsapp-remitentes-lid.md
CONSTITUTION.md (2.10.0), docs/despliegue.md, docs/manual_whatsapp.md, guía de respaldo
tests/unit/channels/{test_identity,test_bridge,test_cli_operator,test_journal}.py, tests/unit/test_ops.py,
tests/api/test_channels_api.py, tests/unit/agent/test_config.py
```

**Structure Decision**: el parche vive con la configuración de OpenClaw (`openclaw/`), junto al plugin propio, y
lo aplica el mismo script que instala el gateway. El backend solo amplía la identidad y la antigüedad.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| Parche sobre un componente de terceros | El componente descarta los mensajes de cuentas solo-ID y no hay versión que lo corrija (ni la beta del 2026-11-27) | Guardar contactos a mano no escala; responder solo texto incumple FR-002; un fork del plugin es costoso y frágil antes de la sustentación |
