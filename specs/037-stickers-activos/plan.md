# Implementation Plan: Stickers que sí llegan y se usan de forma activa

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–036; `setup-plan` reporta
`037-stickers-activos` por `.specify/feature.json`) | **Date**: 2026-11-28 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/037-stickers-activos/spec.md`

## Summary

Ningún sticker de la spec 034 ha llegado a WhatsApp, por dos causas:

- **la entrega**: el plugin `valeria-bridge` busca el listener activo de WhatsApp importando el componente por su
  cuenta. OpenClaw aísla el runtime por instancia de plugin, así que la búsqueda siempre devuelve «sin listener»
  (research R1);
- **la política**: solo cubre saludos, gracias, despedida, «ok» y acciones, con máximo 4 por conversación y nunca
  en respuestas seguidas. Hoy da un 5 % de respuestas con sticker.

Diseño:

1. **Entrega** (`openclaw/plugins/valeria-bridge`), con una cadena de vías y registro de cuál funcionó (R2):
   - el registro de contextos del runtime de canales que el gateway comparte con los plugins
     (`api.runtime.channel.runtimeContexts`, capacidad `connection-controller`);
   - si no basta, un parche versionado del componente (`openclaw/patches/whatsapp-sticker.mjs`, marcador
     `valeria-sticker v1`) que publica el runtime de canales en un símbolo global;
   - al final, la vía actual.

   El texto nunca depende del sticker.
2. **Registro y estado** (R3): el log del gateway dice «enviado» o «no enviado: motivo», y al arrancar, qué vía
   quedó lista. `ops check` muestra los stickers del día (elegidos, entregados y fallidos) y alerta si se eligen y no
   llega ninguno.
3. **Uso activo** (`config/stickers.toml`, `channels/stickers.py`; R4):
   - situación nueva `useful_answer` para las respuestas con citas: «¡Listo!» y el pulgar, alternando, en una de
     cada dos respuestas informativas;
   - respuestas seguidas con sticker si cambia la situación;
   - el mismo sticker no se repite seguido, salvo el pulgar y la despedida;
   - máximo 8 por conversación.
4. **Exclusiones y preferencia** (R5): las exclusiones de la spec 034, más el respaldo por evidencia insuficiente,
   la crisis y el malestar (léxico de la spec 036). Con «sin stickers», el hilo deja de recibirlos.
5. **Verificación** (R6):
   - pruebas de la política, el store, el plugin y el parche;
   - el conjunto `stickers.jsonl` ampliado, con la medición de SC-002 a SC-005;
   - la prueba en el teléfono.

## Technical Context

**Language/Version**: Python 3.14 (backend) y TypeScript sobre Node 24 (plugin de OpenClaw); scripts `.mjs` para
el parche.

**Primary Dependencies**:

- OpenClaw 2026.11.10 y `@openclaw/whatsapp` 2026.11.10 (Baileys 7.0.0-rc14, `sendSticker`);
- FastAPI y el puente de canales existente.

Sin dependencias nuevas.

**Storage**:

- `ChannelStore` (SQLite, fuera del repositorio): `channel_stickers` ya existe; se agrega la preferencia
  `stickers_off` por hilo.
- Los registros existentes (`logs/channels.jsonl` y el log diario del gateway) no guardan datos personales.

**Testing**:

- pytest: `tests/unit/channels/test_stickers*.py` (situaciones, cadencia, moderación y exclusiones),
  `test_store.py` (`stickers_off`), `tests/api/test_channels_stickers.py` (conjunto ampliado, SC-002 a SC-005) y
  `tests/unit/test_ops.py` (resumen de stickers);
- `node --test` o vitest del plugin (`openclaw/plugins/valeria-bridge/test/bridge.test.ts`): vías de entrega y log;
- pruebas del parche (`openclaw/patches/test/`);
- prueba manual en el teléfono.

**Target Platform**: PC servidor con Windows (gateway OpenClaw y backend como tareas programadas).

**Project Type**: servicio web y canal WhatsApp (plugin del gateway).

**Performance Goals**:

- el sticker «después» sale unos 1,5 s tras el texto, como hoy (`STICKER_AFTER_MS`);
- la búsqueda del listener no agrega más de 50 ms y se guarda en caché mientras la conexión siga viva.

**Constraints**:

- una sola sesión de WhatsApp (SIM única);
- el texto siempre llega;
- sin datos personales en registros ni fixtures;
- los nueve stickers aprobados no cambian;
- las reglas de las specs 019, 035 y 036 se mantienen.

**Scale/Scope**: el canal WhatsApp (plugin y política del puente). La web no tiene stickers.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| V. Evaluación empírica antes de afirmar | ✅ con tarea | La spec 034 cerró sin probar la entrega real. Aquí la prueba en vivo (T001) va primero y las metas se miden en el teléfono. |
| §10 Privacidad | ✅ | Los registros llevan solo el nombre del sticker y el motivo; los dígitos se enmascaran. |
| VII. Simplicidad | ✅ | Primero la vía sin parche. El parche, con el patrón ya aprobado en la spec 033 (ADR 0039), solo si hace falta. |
| VI. Trazabilidad | ✅ con tarea | Si se instala el parche, se documenta en el ADR 0039 (anexo) o en uno nuevo, con `ops check`. |
| §4.3 Proceso | ✅ | Spec Kit completo. Los pasos manuales (reinicios y teléfono) llevan instrucciones previas. |
| Cambios de arquitectura → CONSTITUTION.md | ✅ condicional | Sin parche no hay cambio de arquitectura. Con parche, se agrega una línea en la sección del canal de la constitución, junto a `whatsapp-lid`. |

**Resultado**: pasa.
**Re-check post-design**: igual. ✅

## Project Structure

### Documentation (this feature)

```text
specs/037-stickers-activos/
├── plan.md
├── research.md        # R1–R6
├── data-model.md
├── quickstart.md
├── contracts/
│   └── sticker-delivery.md   # vías de entrega, log, política y estado
├── checklists/requirements.md
└── tasks.md           # /speckit-tasks
```

### Source Code (repository root)

```text
openclaw/plugins/valeria-bridge/
├── index.ts                     # guarda api.runtime.channel; cadena de vías; log de arranque
├── src/bridge.ts                # log «enviado/no enviado: motivo» con nombre del sticker
└── test/bridge.test.ts          # vías de entrega y log
openclaw/patches/whatsapp-sticker.mjs    # respaldo: runtime de canales en símbolo global (solo si hace falta)
openclaw/patches/test/whatsapp-sticker.test.mjs
config/stickers.toml             # useful_answer en valeria-listo y valeria-pulgar
config/agent.toml                # stickers_per_conversation = 8
src/proyecto_modelos_lenguaje/channels/
├── stickers.py                  # situaciones, cadencia, moderación, exclusiones
├── store.py                     # stickers_off por hilo; uso con último sticker y situación
└── bridge.py                    # señales del turno (citas, respaldo, crisis), «sin stickers»
src/proyecto_modelos_lenguaje/ops.py     # resumen de stickers del día (elegidos/entregados/fallidos)
tests/unit/channels/..., tests/api/test_channels_stickers.py, tests/fixtures/channels/stickers.jsonl
docs/manual_whatsapp.md, docs/whatsapp/README.md, docs/despliegue.md (si cambia el arranque)
```

**Structure Decision**: la decisión sigue en el backend, que conoce el turno. La entrega sigue en el plugin, que
tiene la conexión. El gateway y su configuración no cambian, salvo el parche opcional, que es idempotente y
verificable.

## Complexity Tracking

| Riesgo o desviación | Por qué | Alternativa más simple descartada |
|---|---|---|
| Parche opcional del componente de WhatsApp | OpenClaw aísla el runtime por plugin. Si el registro compartido no expone el controlador, no hay otra vía para enviar un sticker nativo con la sesión única. | Enviar el `.webp` como medio: llega como documento. Una segunda sesión: requiere otra SIM o vinculación. |
