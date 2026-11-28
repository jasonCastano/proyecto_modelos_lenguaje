# Implementation Plan: Stickers de Valer-IA en las conversaciones de WhatsApp

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR #89 que las specs 028–033; `setup-plan` reporta
`034-stickers-whatsapp` por `.specify/feature.json`) | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/034-stickers-whatsapp/spec.md`

## Summary

Valer-IA usará los nueve stickers aprobados de la spec 030 (`docs/whatsapp/stickers/`) en momentos sociales y
acciones completadas, con moderación. Diseño (research R1–R9):

1. **Decisión en el backend** (`channels/stickers.py`), determinista:
   - señales existentes del turno: `route.act`, `route.sentiment`, avisos, inicio de conversación y presentación
     (spec 032), aprobaciones, ruta `planning` e idioma;
   - un catálogo configurable `config/stickers.toml`;
   - moderación por hilo en una tabla aditiva `channel_stickers`.

   La respuesta del canal agrega `sticker: {name, path, position}`.
2. **Entrega en el plugin** `valeria-bridge`:
   - `sendSticker` del listener activo, obtenido con la exportación pública `getActiveWebListener` del componente
     instalado (R1);
   - `before` se envía antes del texto; `after`, 1,5 s después;
   - «Pensando» lo envía el plugin si el backend tarda más de 8 s (máximo uno cada 10 min por remitente);
   - cualquier fallo omite el sticker sin afectar la respuesta.
3. **Operación**:
   - interruptor `[channels] stickers = true` y máximo por conversación `stickers_per_conversation = 4`;
   - `ops check` agrega `stickers`;
   - el registro guarda el nombre del sticker.
4. **Verificación temprana**: confirmar en el gateway real que el listener es alcanzable y que el sticker llega
   como sticker. Si no, plan B: ampliar el parche de la spec 033 para `sendMedia` (R1).

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript del plugin (Node 24.22.1, tipos eliminados con
`node --test`).

**Primary Dependencies**: OpenClaw 2026.11.10 y `@openclaw/whatsapp` 2026.11.10 (API pública
`getActiveWebListener` → `sendSticker`); FastAPI; SQLite del canal; `tomllib`. Sin dependencias nuevas.

**Storage**:

- `config/stickers.toml` (versionado);
- tabla `channel_stickers` en `<estado>/channels.sqlite3` (aditiva; sin contenido);
- archivos en `docs/whatsapp/stickers/` (existentes, Git LFS si aplica; no se regeneran).

**Testing**:

- pytest: `tests/unit/channels/test_stickers.py` (nuevo: catálogo, situaciones, moderación, idioma,
  exclusiones), `test_bridge.py` (respuesta con `sticker`), `test_store.py` (`channel_stickers`), `test_ops.py`,
  `tests/api/test_channels_api.py` (campo `sticker` en el contrato);
- plugin (`npm test`): orden antes/después, «Pensando» con temporizador falso, fallo del listener sin afectar el
  texto y `maskDigits`;
- guion `tests/fixtures/channels/stickers.jsonl` para `simulate --check`;
- prueba manual en el teléfono.

**Target Platform**: el portátil servidor y el equipo de respaldo (Windows 11).

**Project Type**: servicio web, gateway de mensajería y plugin.

**Performance Goals**: la decisión no agrega llamadas al modelo (< 5 ms); el envío del sticker no retrasa la
respuesta (diferido o previo y sin esperar más de 3 s).

**Constraints**:

- máximo un sticker por respuesta; nunca en lugar de la respuesta;
- sin stickers con texto en inglés;
- sin datos personales en registros;
- la web no cambia;
- no se modifican los stickers aprobados.

**Scale/Scope**: chats individuales de WhatsApp; nueve stickers.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| Regla 8 Canal por OpenClaw, un solo agente | ✅ | El plugin usa una exportación pública del componente; no cambia el agente ni el contrato principal (se agrega un campo opcional). |
| Regla 22 Conversación natural y voz | ✅ | Los stickers acompañan sin comandos; la voz y las fuentes no cambian. |
| Regla 10 Seudónimos y registros sin contenido | ✅ | El registro guarda solo el nombre del sticker. |
| §10 Declaración de IA y canal no oficial | ✅ | Los stickers no la llevan; la presentación (spec 032) ya la cubre por escrito. Las piezas siguen sin marca de Manuelita (spec 030). |
| §3.5 Prompts versionados | ✅ | Sin prompts nuevos; la decisión es determinista. |
| §3.3 Capas medallion | ✅ | No se toca `data/`. |
| Cambios de arquitectura o tecnología → CONSTITUTION.md | ✅ sin enmienda | Comportamiento del canal dentro de las reglas 8 y 22; sin tecnología nueva. Si se activa el plan B (ampliar el parche), aplica la regla 8 ya enmendada en 2.10.0, sin otra enmienda. |

**Resultado**: pasa sin enmiendas.
**Re-check post-design**: igual. ✅

## Project Structure

### Documentation (this feature)

```text
specs/034-stickers-whatsapp/
├── plan.md
├── research.md        # R1–R9
├── data-model.md
├── quickstart.md
├── contracts/
│   └── stickers.md     # respuesta del canal, catálogo, plugin
├── checklists/requirements.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

```text
config/stickers.toml                                 # nuevo: situaciones → sticker, posición, texto, idioma
config/agent.toml                                    # [channels] stickers, stickers_per_conversation
src/proyecto_modelos_lenguaje/
├── agent/config.py                                  # ChannelsConfig: stickers, stickers_per_conversation
├── channels/stickers.py                             # nuevo: catálogo, situación, moderación, decisión
├── channels/store.py                                # channel_stickers (aditiva)
├── channels/bridge.py                               # ChannelReply.sticker; señales de aprobación
├── channels/journal.py                              # sticker
├── api_models.py                                    # campo opcional sticker en la respuesta
└── ops.py                                           # check «stickers»
openclaw/plugins/valeria-bridge/src/bridge.ts        # tipos, orden, «Pensando»
openclaw/plugins/valeria-bridge/index.ts             # stickerSender con getActiveWebListener
openclaw/openclaw.json5                              # config del plugin: stickersDir, stickerThinkingMs
docs/despliegue.md, docs/manual_whatsapp.md, docs/whatsapp/README.md (uso por el bot)
tests/unit/channels/test_stickers.py, tests/fixtures/channels/stickers.jsonl, …
```

**Structure Decision**: la decisión vive en `channels/`, junto a la presentación (spec 032) y los límites (spec
031). El plugin solo entrega y no tiene reglas propias, salvo «Pensando», que depende del tiempo de espera.

## Complexity Tracking

Sin violaciones que justificar.
