# Implementation Plan: Respuesta por voz sin texto duplicado (solo fuentes por escrito)

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR que las specs 028 y 029; `setup-plan` reporta
`030-voz-solo-fuentes-texto` por `.specify/feature.json`) | **Date**: 2026-11-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/030-voz-solo-fuentes-texto/spec.md`

## Summary

Cuando Valer-IA responde con una nota de voz, el texto que la acompaña deja de repetir la respuesta y lleva solo el
bloque de fuentes. Diseño (research R1–R6):

1. **Backend**:
   - `ChannelBridge` devuelve, además de `messages` (respuesta completa, sin cambios), `sources_messages`: solo el
     bloque de fuentes en el idioma del turno, o lista vacía si no hay fuentes.
   - Lo arma `format.sources_only`, que reutiliza la numeración y deduplicación de la spec 029.
2. **Plugin `valeria-bridge`**:
   - envía la nota de voz por el adaptador del canal;
   - si la entrega se confirma, responde con `sources_messages` (o sin texto);
   - si falla, responde con `messages`, así que la persona nunca se queda solo con enlaces.
3. **Guion de voz**: con fuentes, cierra con «Te dejo las fuentes por escrito.» / «I've left the sources for you in
   writing.».
4. **Verificación**:
   - `quality.review_reply(..., voice=True)` marca `voice_text_duplicate`;
   - el registro del canal añade `written` (`full` / `sources` / `none`);
   - el simulador `--check` usa el texto real que se entregaría.

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript sobre Node 24.22.1 (plugin `valeria-bridge`).

**Primary Dependencies**: FastAPI y Pydantic (contrato del canal); OpenClaw 2026.11.10 (adaptador de salida del canal
para la voz, spec 029); Phonon/PyAV ya integrados para la voz. Sin dependencias nuevas.

**Storage**: ninguno nuevo. Campo `written` en `channels.jsonl` (registro diario, sin contenido).

**Testing**:

- pytest: `tests/unit/channels/{test_format,test_quality,test_bridge,test_voice}.py` y
  `tests/api/test_channels_api.py`;
- `node --test` del plugin;
- `pml channels simulate --check` en modo real;
- prueba manual con el teléfono.

**Target Platform**: el portátil servidor (gateway en el puerto 18790, backend en el 8000).

**Project Type**: servicio web + plugin de gateway.

**Performance Goals**: sin latencia nueva; el bloque de fuentes ya se calcula hoy.

**Constraints**:

- nunca dejar a la persona sin la respuesta si la voz falla;
- un solo idioma por respuesta (spec 029);
- sin números ni texto en los registros;
- el contrato sigue siendo compatible hacia atrás (campo opcional).

**Scale/Scope**: cambio de presentación en el canal; no toca el agente, la recuperación ni las capas de datos.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §IV Citas y trazabilidad | ✅ | Las fuentes siguen llegando por escrito, con los mismos números y URLs. Con la voz no se pierde ninguna cita. |
| Regla 22 (2.3.0) Conversación y voz | ✅ | Voz ante voz, más natural: sin texto duplicado. |
| Regla 10 / §3.9 Sin números ni texto en registros | ✅ | `written` es una etiqueta; el log del plugin no lleva contenido. |
| Regla 21 Evaluaciones publicadas no bajan | ✅ | El agente no cambia. Se corre `make check`; las evaluaciones de herramientas y blindaje no se ven afectadas. |
| §3.6 Prompts versionados | ✅ | Sin cambio de prompts: la frase de cierre es un texto fijo del canal (research R3), registrado en `channels/voice.py`. |
| §3.3 Capas medallion intactas | ✅ | No se tocan `data/`. |
| §I / §4.3 Autoría y proceso | ✅ | Spec Kit completo; commits y PR solo con autorización de un integrante. |

**Resultado**: pasa sin enmiendas.
**Re-check post-design**: igual. El contrato agrega un campo opcional y el plugin elige el texto según la entrega de la
voz. ✅

## Project Structure

### Documentation (this feature)

```text
specs/030-voz-solo-fuentes-texto/
├── spec.md
├── plan.md                       # este archivo
├── research.md                   # R1–R6
├── data-model.md                 # respuesta del canal, entrega del turno, registro, guion
├── quickstart.md                 # validación sin teléfono, falla de voz, prueba con el teléfono
├── contracts/
│   └── channel-voice-text.md     # sources_messages y decisión del plugin
├── checklists/requirements.md
└── tasks.md                      # /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── channels/format.py            # sources_only(): bloque de fuentes solo, partido por líneas
├── channels/bridge.py            # ChannelReply.sources_messages, written; _attach_voice
├── channels/voice.py             # frase de cierre cuando hay fuentes (es/en)
├── channels/quality.py           # review_reply(voice=True) → voice_text_duplicate
├── channels/journal.py           # campo written en el registro del canal
├── channels/__main__.py          # simulate --check con el texto que se entregaría
├── api_models.py                 # ChannelReplyModel.sources_messages
openclaw/plugins/valeria-bridge/
├── src/bridge.ts                 # dispatch elige sources_messages / messages según la entrega
├── index.ts                      # sendVoice devuelve si se entregó
└── test/bridge.test.ts
tests/
├── fixtures/channels/regression_2026-11-27b.jsonl
├── unit/channels/test_format.py, test_quality.py, test_bridge.py, test_voice.py
└── api/test_channels_api.py
docs/manual_whatsapp.md            # «si le hablas: nota de voz y las fuentes por escrito»
```

**Structure Decision**: se cambian los mismos módulos de las specs 024, 028 y 029. La decisión final del texto queda en
el plugin, que es quien conoce el resultado de la entrega de la voz.

## Complexity Tracking

Sin violaciones que justificar.
