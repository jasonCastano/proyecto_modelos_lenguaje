# Implementation Plan: Capa Oro (Gold): Base de Conocimiento Consolidada y Citable

**Branch**: `004-gold-medallion-layer` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/004-gold-medallion-layer/spec.md`

## Summary

Construir una capa oro determinista y offline que consolide los 404 documentos canónicos y 3.810 fragmentos
de la plata en una base de conocimiento organizada por temas, con unidades citables, entidades, hechos,
conflictos, matriz de los 24 ítems y paquetes de contexto acotados por tokens para las tareas del Módulo 1.

La implementación es extractiva y basada en reglas: no resume, no responde, no traduce y no genera embeddings.
Cada unidad de conocimiento conserva su evidencia hasta el fragmento de plata y la URL pública. Los conflictos
se preservan y se resuelven con reglas de autoridad y vigencia, nunca promediando cifras.

## Technical Context

**Language/Version**: Python 3.14, gestionado con `uv`.

**Primary Dependencies**: biblioteca estándar (`re`, `json`, `hashlib`, `dataclasses`), `PyYAML` para
frontmatter y los módulos existentes de la capa plata (`silver.cleaning.estimate_tokens`,
`silver.models`, `silver.state`). No se añaden dependencias nuevas.

**Storage**: lectura de `data/silver/documents.jsonl` y `data/silver/chunks.jsonl`; salidas en `data/gold/`
(JSONL, Markdown y JSON); estado incremental en `data/gold/_meta/state.jsonl`. Sin base de datos nueva.

**Testing**: `pytest` con pruebas unitarias, de contrato (JSON Schema) e integración sobre un corpus plata
temporal; sin red. Ruff para lint y formato.

**Target Platform**: CLI multiplataforma; desarrollo en Windows 11 y CI en Linux.

**Project Type**: proyecto único de librería + CLI sobre `proyecto_modelos_lenguaje`.

**Performance Goals**: consolidar 404 documentos y 3.810 fragmentos en ≤10 minutos en 4 núcleos y 8 GB;
la reconstrucción incremental sin cambios debe tardar ≤2 minutos.

**Constraints**: 100% offline; sin LLM, embeddings, traducción ni OCR; solo documentos canónicos de plata; la
plata y el bronce son de solo lectura; presupuestos de contexto de 8.000 y 32.000 tokens con el proxy de plata;
salidas deterministas y auditables.

**Scale/Scope**: 404 documentos canónicos, 3.810 fragmentos, 24 ítems de cobertura, ~300–1.500 unidades de
conocimiento, ~12–20 temas, dos paquetes de contexto y un conjunto de preguntas semilla.

## Constitution Check

| Principio / restricción | Cumplimiento | Evidencia en el plan |
|--------------------------|--------------|----------------------|
| I. Reproducibilidad experimental | PASS | Reglas y taxonomía versionadas, IDs deterministas, sin red y regeneración desde plata. |
| II. Evaluación con métricas y línea base | PASS | Reporte de calidad, auditoría de 100 unidades, matriz de cobertura y pruebas de contrato. |
| III. Procedencia y ética de datos | PASS | Linaje unidad → chunk → documento → bronce → URL; solo contenido público. |
| IV. Experimentos como código versionado | PASS | `config/gold.toml`, `config/gold_taxonomy.toml`, contratos y reportes por ejecución. |
| V. Simplicidad y alcance académico | PASS | Sin dependencias nuevas, sin LLM y sin base de datos; solo consolidación extractiva. |
| Datos y capas medallion (§3.3) | PASS | Salidas en `data/gold/`, JSONL y Markdown con frontmatter, deduplicación por hash. |
| Pipeline y reproducibilidad (§3.4, §3.8) | PASS | Etapas visibles, idempotencia, pruebas offline y comando canónico. |
| Seguridad y datos no versionados (§3.9) | PASS | Sin credenciales ni red; `data/` fuera de Git; solo lectura de plata. |

**Resultado**: sin violaciones. No se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/004-gold-medallion-layer/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, campos y transiciones
├── quickstart.md        # Fase 1: validación end-to-end
├── contracts/           # Fase 1: esquemas de unidad, hecho, entidad, conflicto, cobertura, contexto y reporte
├── checklists/
│   └── requirements.md  # Validación de la especificación
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── cli.py                       # Nuevo subcomando `pml gold`
├── silver/                      # Entrada: cleaning.estimate_tokens, models, state
└── gold/
    ├── __init__.py
    ├── models.py                # Unidad, Tema, Entidad, Evidencia, Conflicto, Cobertura, Contexto
    ├── config.py                # config/gold.toml y hash de configuración
    ├── taxonomy.py              # Taxonomía de temas y mapeo a los 24 ítems
    ├── entities.py              # Vocabulario controlado, alias y detección de entidades
    ├── facts.py                 # Extracción determinista de cifras, fechas y atributos
    ├── units.py                 # Unidades extractivas, deduplicación y consolidación
    ├── conflicts.py             # Detección y resolución de contradicciones
    ├── coverage.py              # Matriz de los 24 ítems
    ├── faq.py                   # Preguntas semilla con evidencia
    ├── context_pack.py          # Selección por presupuesto de tokens y citas
    ├── store.py                 # Escritura atómica JSONL/Markdown y estado
    ├── reporting.py             # quality.json / quality.md
    └── pipeline.py              # Orquestador de las etapas

config/
├── gold.toml                    # Umbrales, presupuestos y rutas
└── gold_taxonomy.toml           # Temas, palabras clave, entidades y mapeo a 24 ítems

scripts/
└── build_gold.py                # Entrada canónica, delega en `pml gold build`

tests/
├── unit/gold/                   # Taxonomía, entidades, hechos, unidades, conflictos, contexto
├── contract/gold/               # Validación de los JSON Schema
└── integration/gold/            # Plata temporal, idempotencia, cobertura y auditoría
```

**Structure Decision**: se mantiene el proyecto único existente. La lógica vive en
`src/proyecto_modelos_lenguaje/gold/` y reutiliza `silver.cleaning.estimate_tokens` y el patrón de estado
JSONL atómico; los scripts son envoltorios operativos y las pruebas siguen la separación
unit/contract/integration.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. **Extracción extractiva, no generativa**: unidades construidas con oraciones del fragmento y reglas; no se
   inventan afirmaciones ni se usa un LLM.
2. **Clasificación por taxonomía controlada**: palabras clave, alias y entidades; sin embeddings.
3. **Hechos con patrones deterministas**: cifras, fechas, unidades y atributos explícitos; el resto queda como
   pasaje extractivo.
4. **Conflictos solo sobre hechos comparables**: mismo sujeto y atributo con valores distintos; autoridad y
   fecha deciden, y lo no resoluble se marca disputado.
5. **Contexto por knapsack greedy**: prioridad por cobertura, autoridad, vigencia y diversidad de temas.
6. **Sin dependencias nuevas**: biblioteca estándar + PyYAML; reutilización del proxy de tokens de plata.

## Phase 1 — Design & Contracts

- [data-model.md](./data-model.md): entidades, campos, invariantes y estados.
- [contracts/knowledge-unit.schema.json](./contracts/knowledge-unit.schema.json)
- [contracts/fact.schema.json](./contracts/fact.schema.json)
- [contracts/entity.schema.json](./contracts/entity.schema.json)
- [contracts/conflict.schema.json](./contracts/conflict.schema.json)
- [contracts/coverage.schema.json](./contracts/coverage.schema.json)
- [contracts/context-pack.schema.json](./contracts/context-pack.schema.json)
- [contracts/faq-seed.schema.json](./contracts/faq-seed.schema.json)
- [contracts/run-report.schema.json](./contracts/run-report.schema.json)
- [contracts/cli.md](./contracts/cli.md)
- [quickstart.md](./quickstart.md)

### Data flow

```text
data/silver/documents.jsonl + chunks.jsonl (solo canónicos)
        │
        ▼
[1] clasificar ──► tema, ítem de cobertura, entidades
        │
        ▼
[2] extraer ──► unidades extractivas + hechos + evidencias
        │
        ▼
[3] consolidar ──► deduplicación, entidades canónicas, conflictos
        │
        ▼
[4] cubrir ──► matriz de 24 ítems, vacíos y autoridad
        │
        ▼
[5] empaquetar ──► contexto 8k/32k, FAQ seeds, páginas de tema
        │
        ▼
data/gold/{knowledge_units,facts,entities,conflicts,faq_seeds}.jsonl
data/gold/{coverage.json,context_*.md,topics/*.md,glossary.md}
data/gold/reports/<run_id>/quality.{json,md}
```

### Delivery slices

| Slice | Alcance | Requisitos cubiertos | Validación |
|-------|---------|----------------------|------------|
| S1 | Unidades, entidades, hechos y evidencia | FR-001–FR-008, FR-012 | 100 unidades con linaje; 0 sin evidencia |
| S2 | Temas, páginas de tema y glosario | FR-003, FR-013, FR-014 | ≥12 temas; páginas con citas |
| S3 | Conflictos y estados | FR-009–FR-011, FR-029 | Dos fuentes contradictorias; disputa preservada |
| S4 | Cobertura de los 24 ítems | FR-015, FR-016, FR-032 | 24/24 evaluados; vacíos justificados |
| S5 | Context packs, FAQ seeds y reporte | FR-017–FR-024, FR-031, FR-033 | Presupuesto, citas, 100% auditoría |

Cada slice es demostrable por separado; S1 ya entrega conocimiento citable, S2–S3 lo ordenan y resuelven,
S4 demuestra cobertura y S5 lo prepara para el Módulo 1.

## Phase 1 Re-check — Constitution

| Principio | Re-evaluación | Resultado |
|-----------|---------------|-----------|
| Reproducibilidad | IDs, config hash, sin red | PASS |
| Métricas | Reporte, cobertura, auditoría | PASS |
| Procedencia | Evidencia por unidad y paquete | PASS |
| Simplicidad | Sin dependencias nuevas ni LLM | PASS |
| Datos/medallion | JSONL/Markdown, dedup, solo lectura | PASS |

Sin violaciones después del diseño.

## Risks and Mitigations

| Riesgo | Impacto | Mitigación |
|--------|---------|------------|
| Falsos positivos en hechos | Conflictos o cifras incorrectas | Solo patrones explícitos; lo dudoso queda como pasaje o ambiguo |
| Cobertura inflada por palabras clave | Métrica engañosa | Exigir unidad con evidencia y autoridad; revisión de muestra |
| División de oraciones en abreviaturas | Unidades cortadas | Reglas de abreviaturas y longitud mínima; prueba con corpus real |
| Contexto excede el presupuesto | El modelo no puede usarlo | Knapsack con `estimate_tokens` y verificación de tope |
| Conflictos falsos por atributos distintos | Ruido | Normalizar sujeto/atributo y limitar a valores comparables |
| Duplicados semánticos | Repetición en el contexto | Hash normalizado + Jaccard de shingles con umbral |
| Sesgo hacia fuentes oficiales | Se oculta un conflicto | La fuente oficial prevalece, pero la evidencia secundaria se conserva |
| Cambios en plata | IDs inestables | Estado por `doc_id + text_hash + config_hash` |

## Complexity Tracking

Sin violaciones de la constitución; no hay complejidad adicional que justificar.
