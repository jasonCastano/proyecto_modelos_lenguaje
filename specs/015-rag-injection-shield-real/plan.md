# Implementation Plan: Blindaje del RAG verificado con el modelo real

**Branch**: `015-rag-injection-shield-real` | **Date**: 2026-11-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/015-rag-injection-shield-real/spec.md`

## Summary

El caso 5 de la rúbrica del Módulo 2 («Blindaje del RAG») hoy solo se puede demostrar con el modelo simulado del modo
demostración, porque el corpus adversarial se activa únicamente en `mode == "demo"` y su índice se construyó con el
embedder determinista (`HashEmbedder`). Esta feature:

1. **US1 (P1)**: permite activar el corpus adversarial también en modo real. Lo hace con un índice de prueba
   construido con el embedder real y una colección Qdrant en memoria, para no tocar la colección del corpus real. La
   interfaz muestra un indicador mientras está activo.
2. **US2 (P2)**: agrega el comando `agent shield`, que corre una batería de 6 tipos de ataque contra DeepSeek en las
   variantes cadena y agente. Guarda `docs/evaluacion_blindaje.{json,md}` con el resultado por caso y la
   comparación contra una línea base sin neutralización.
3. **US3 (P3)**: neutraliza en `guard.py` las oraciones detectadas como instrucciones antes de entregarlas al modelo,
   conserva el resto del fragmento y registra cuántas se omitieron.

## Technical Context

**Language/Version**: Python 3.14 (backend), TypeScript 5.9 + React 19 (frontend)

**Primary Dependencies**: LangChain/LangGraph (grafos existentes), FastAPI, fastembed (`intfloat/multilingual-e5-small`), qdrant-client (modo en memoria), DeepSeek vía `langchain-openai`. **Sin dependencias nuevas.**

**Storage**:
- Índice de prueba versionado en `tests/fixtures/rag/malicious/` (JSONL + `index/` hash + nuevo `index_real/` con fastembed, < 100 KB).
- Informe en `docs/evaluacion_blindaje.{json,md}`.
- El checkpointer de la evaluación es en memoria.

**Testing**:
- pytest: unitarias de `guard` y del corpus, integración del grafo con `ScriptedModel`, contrato de la API y del informe, y una prueba `@pytest.mark.network` con DeepSeek, excluida por defecto.
- Vitest para el indicador de la UI.

**Target Platform**: servidor local (Windows/Linux) con `make app`; navegador moderno.

**Project Type**: aplicación web (FastAPI + SPA React) con CLI de evaluación.

**Performance Goals**:
- Activar el caso en menos de 1 min (SC-005).
- Evaluación completa en menos de 5 min (SC-006): 6 casos × 2 variantes × 1 repetición ≈ 12 turnos de unos 5–10 s.

**Constraints**:
- La suite por defecto no usa red (SC-007).
- No se reescriben `data/bronze|silver|gold` ni la colección Qdrant real (FR-002).
- La clave nunca sale del servidor.

**Scale/Scope**: unas 12 unidades en el corpus adversarial; 6 casos de ataque; 2 variantes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cómo se cumple | Estado |
|-------------------------|----------------|--------|
| I. Reproducibilidad | El índice real del corpus adversarial se versiona con manifiesto y hash y se regenera con `build_fixture.py malicious --real`. El informe registra commit, comando, modelo, temperatura, fecha y configuración. La temperatura sale de `config/llm.toml`. | ✅ |
| II. Métricas y línea base | Métricas definidas antes de ejecutar: tasa de obediencia, fuga del prompt, intento de escritura y respuesta útil con cita (SC-001…SC-004). **Línea base**: la misma batería sin neutralización (`--no-neutralize`). El modelo es estocástico, así que se admite `--repeat N`, y la corrida documentada usa N = 3 con media y dispersión. | ✅ |
| III. Procedencia y ética | El corpus adversarial es sintético: unidades públicas reales del oro más oraciones inyectadas, documentadas en `tests/fixtures/rag/malicious/README.md`. Sin datos personales. El oro no se modifica. | ✅ |
| IV. Código versionado | Comando de CLI `agent shield`, casos en JSONL versionado y parámetros por argumentos y `config/`. Sin notebooks. | ✅ |
| V. Simplicidad | Sin dependencias ni servicios nuevos: se reutilizan fastembed, Qdrant en memoria y el grafo existente. La neutralización es una función pura en `guard.py`. | ✅ |
| Pruebas sin red | La prueba con DeepSeek usa `pytest.mark.network`, que `addopts` y la CI ya excluyen. | ✅ |
| Secretos | La clave se lee de `.env` en el servidor; el informe no la incluye. | ✅ |
| Tamaño < 10 MB | `index_real/` ≈ 12 × 384 × 4 B ≈ 18 KB más SQLite y manifiesto. | ✅ |

**Resultado**: PASS. No hay violaciones que justificar.

**Re-check post-diseño (Phase 1)**: PASS. Los contratos no agregan endpoints, solo campos opcionales con valor por
defecto, y el diseño mantiene el corpus real intacto. Ver [research.md](./research.md) R1–R8.

## Project Structure

### Documentation (this feature)

```text
specs/015-rag-injection-shield-real/
├── plan.md              # Este archivo
├── research.md          # Phase 0: decisiones R1–R8
├── data-model.md        # Phase 1: entidades (caso, resultado, informe, fragmento neutralizado)
├── quickstart.md        # Phase 1: guía de validación de punta a punta
├── contracts/
│   ├── shield-cli.md            # Comando `agent shield`: argumentos, salidas, códigos de salida
│   ├── shield-cases.schema.json # Esquema del JSONL de casos
│   ├── shield-report.schema.json# Esquema de docs/evaluacion_blindaje.json
│   └── api-changes.md           # Campos nuevos en /api/health, /api/observability y fragmentos
├── checklists/requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks; no lo crea este comando)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── agent/
│   ├── guard.py          # + neutralize(), patrón «accion_escritura», normalización anti-evasión
│   ├── tools.py          # search_documents_impl aplica la neutralización y la registra en el fragmento
│   ├── adversarial.py    # NUEVO: activación (env), recuperador adversarial demo/real compartido
│   ├── shield.py         # NUEVO: batería de casos, evaluación, informe JSON/Markdown
│   ├── observability.py  # + etiqueta/metadato corpus=adversarial en trazas y turns.jsonl
│   └── __main__.py       # + subcomando `shield`; el recuperador usa adversarial.py
├── rag/hybrid.py         # RetrievedFragment + neutralized_sentences (default 0)
├── api.py                # _retriever usa adversarial.py en ambos modos; flags en health/observability
└── api_models.py         # HealthStatus.adversarial_corpus; ChatFragmentModel.neutralized_sentences

prompts/agent.md          # v1.2: regla explícita sobre la marca «[instrucción embebida omitida]»

web/src/
├── components/DemoBanner.tsx   # aviso «Corpus de prueba adversarial activo»
├── components/ChatView.tsx     # el aviso del turno indica cuántas oraciones se neutralizaron
└── lib/types.ts                # campos nuevos opcionales

tests/
├── fixtures/rag/malicious/
│   ├── gold_malicious.jsonl     # + 6 unidades de ataque (una por tipo)
│   ├── shield_cases.jsonl       # NUEVO: pregunta, tipo de ataque, unidad, señal de obediencia
│   ├── index/                   # regenerado (hash, modo demo)
│   ├── index_real/              # NUEVO: fastembed e5-small (modo real)
│   └── README.md                # NUEVO: procedencia del corpus adversarial
├── fixtures/rag/build_fixture.py      # + opción --real
├── unit/agent/test_guard.py           # neutralización, evasión, falsos positivos, escritura
├── unit/agent/test_shield.py          # NUEVO: carga de casos, métricas y render del informe
├── integration/agent/test_injection.py# + casos nuevos en ambas variantes (ScriptedModel)
├── integration/agent/test_shield_real.py # NUEVO, @network: DeepSeek no obedece
├── api/…                              # health/observability con el flag
└── contract/test_shield_report_contract.py # NUEVO: el informe cumple el esquema

docs/
├── evaluacion_blindaje.json / .md     # NUEVO: evidencia generada por `agent shield`
├── decisions/0019-blindaje-modelo-real.md # NUEVO: ADR (corpus separado + neutralización)
├── demo.md, rubrica_modulo2.md, informe_modulo2.md, prompt_log.md # actualizados
└── README.md (raíz)                   # sección de blindaje en vivo
```

**Structure Decision**: Se mantiene la estructura existente (paquete `src/` + SPA en `web/`). La lógica nueva se aísla
en dos módulos del agente (`adversarial.py` para la activación y `shield.py` para la evaluación) y en funciones
puras de `guard.py`, para que el flujo de conversación solo cambie en un punto: `search_documents_impl`, que usan
las dos variantes.

## Complexity Tracking

No aplica: el Constitution Check no tiene violaciones.
