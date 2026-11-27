# Implementation Plan: Respuestas de Valer-IA por WhatsApp en voz, en un solo idioma y bien ordenadas

**Branch**: `028-valeria-natural-voz-whatsapp` (mismo PR que la spec 028) | **Date**: 2026-11-27 |
**Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/029-voz-idioma-formato-whatsapp/spec.md`

## Summary

Corregir las cuatro fallas de las pruebas reales del 2026-11-27 antes de la sustentación:

1. **Las notas de voz llegaban marcadas como texto**, por eso no había voz.
   - El plugin `valeria-bridge` detecta el audio en cualquier parte del contenido del hook (`content` o `body`)
     y envía al backend solo la transcripción.
   - Una captura con dígitos enmascarados confirma el formato real.
2. **Aviso de seguridad falso y robótico.**
   - Lo disparaba un número de teléfono, casi seguro el del encabezado del gateway.
   - Ahora solo lo disparan tarjetas, documentos o contraseñas que la persona realmente comparte.
   - Una vez por conversación, en una frase natural, en su idioma y al final de la respuesta.
3. **Mezcla de idiomas.**
   - El idioma del turno viaja del puente al agente y al formateador.
   - Los textos fijos (encabezado de fuentes, respuesta abreviada, aviso, prefijos) existen en español e inglés.
4. **Fuentes desordenadas.**
   - Títulos limpios de una línea, con el nombre del documento como respaldo.
   - Dedupe por URL y página, con renumeración del texto.
   - Línea de formato fijo.

Una revisión automática (`channels/quality.py`) mide idioma único, formato de fuentes y aviso sin motivo, y se usa
en las pruebas, en el simulador y sobre las tres respuestas reales como regresión.

## Technical Context

**Language/Version**: Python 3.14 (backend); TypeScript sobre Node 24.22.1 (plugin `valeria-bridge`).

**Primary Dependencies**:
- Existentes, sin dependencias nuevas: FastAPI, LangGraph, OpenClaw 2026.11.10, `@openclaw/whatsapp`.
- Canal de la spec 028: `channels/bridge.py`, `intents.py`, `voice.py`, `format.py`.

**Storage**:
- Estado del hilo (checkpointer): nueva bandera `sensitive_notice_given`.
- Sin cambios en `channels.sqlite3`.

**Testing**:
- pytest sin red y `node --test`.
- Fixtures de regresión (tres respuestas reales) y conjunto de 20 + 3 consultas.
- Verificación final con el teléfono de prueba en modo cerrado.

**Target Platform**: el portátil servidor (gateway, backend y Qdrant ya en verde, SIM vinculada).

**Project Type**: servicio web + plugin de gateway.

**Performance Goals**: sin cambio de latencia apreciable; la detección y el formateo son deterministas.

**Constraints**:
- Ningún número de teléfono llega al texto del backend ni a los registros.
- La exactitud de herramientas (≥ 90,7 %) y el escudo del canal (20/20) no bajan (regla 21).
- Entrega antes del sábado 28 a las 8:00.

**Scale/Scope**:
- 4 historias P1.
- Archivos: plugin `bridge.ts`; `channels/format.py`, `bridge.py`, `quality.py` (nuevo) e `intents.py`;
  `agent/graph.py` y `service.py`; `prompts/conduct.md`.
- Fixtures y documentación.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §3.6 Prompts versionados y registrados | ✅ | `prompts/conduct.md` 1.2 → 1.3 (aviso natural en es/en); entrada en `docs/prompt_log.md`. |
| §IV Citas y trazabilidad | ✅ | Las fuentes se limpian y deduplican sin perder ninguna URL; el número de cita del texto sigue apuntando a la misma fuente. |
| Regla 10 / §3.9 Seudónimos, sin números ni texto | ✅ | El encabezado del gateway (con el número) deja de llegar al backend; la captura de depuración enmascara dígitos y no guarda texto completo. |
| Regla 22 (2.3.0) Conversación y voz | ✅ | La corrección la cumple: voz ante voz, sin comandos, audio temporal. |
| Regla 21 Evaluaciones publicadas no bajan | ✅ con verificación | Se repiten `agent evaluate --tools` y `agent shield --channel` en modo real tras los cambios. |
| §3.3 Capas medallion intactas | ✅ | Los títulos se limpian al presentarse, no en el oro. |
| §I / §4.3 Autoría | ✅ | Commits a nombre de un integrante, con autorización. |

**Resultado**: pasa sin enmiendas.
**Re-check post-design**: igual; el diseño solo toca presentación, detección del audio y el disparador del aviso. ✅

## Project Structure

### Documentation (this feature)

```text
specs/029-voz-idioma-formato-whatsapp/
├── spec.md
├── plan.md               # este archivo
├── research.md           # R1–R6
├── data-model.md
├── quickstart.md
├── contracts/
│   └── channel-format.md # formato de respuesta, idioma, aviso y entrada de voz
├── checklists/requirements.md
└── tasks.md              # /speckit-tasks
```

### Source Code (repository root)

```text
openclaw/plugins/valeria-bridge/src/bridge.ts   # detección de voz en content/body; solo transcripción; depuración enmascarada
openclaw/plugins/valeria-bridge/test/bridge.test.ts
src/proyecto_modelos_lenguaje/channels/
├── format.py      # clean_title, dedupe (URL, página), encabezados es/en, línea fija
├── quality.py     # NUEVO: review_reply (idioma único, fuentes, aviso sin motivo)
├── bridge.py      # idioma del turno hacia el agente y el formateador
└── __main__.py    # simulate --check
src/proyecto_modelos_lenguaje/agent/
├── graph.py       # aviso: disparador, una vez por hilo, al final, por idioma; prefijos por idioma
└── service.py     # language del turno en el estado; pii_notice sin «phone»
prompts/conduct.md # 1.3: sensitive_notice natural + sensitive_notice_en
tests/fixtures/channels/regression_2026-11-27.jsonl, language_format.jsonl
tests/unit/channels/test_format.py, test_quality.py; tests/unit/agent/test_sensitive_notice.py
docs/prompt_log.md, docs/manual_whatsapp.md (si cambia el comportamiento visible)
```

**Structure Decision**: se corrige en los mismos módulos de las specs 024 y 028 (puente, formateador, grafo). La
revisión automática es un módulo nuevo y pequeño del canal para que pruebas y simulador midan lo mismo.

## Complexity Tracking

Sin violaciones que justificar.
