# Implementation Plan: Tareas LangChain — Resumen, FAQ y Q&A

**Branch**: `007-langchain-qa-tasks` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/007-langchain-qa-tasks/spec.md`

## Summary

Implementar las tres tareas del Módulo 1 con LangChain sobre la base de oro: **Resumen**, **FAQ** y **Q&A**.
Cada tarea usa el adaptador de modelo de M1-04 (Ollama local o modelo falso), prompts versionados y una
selección de evidencia determinista. Toda respuesta factual cita la unidad de oro y la URL; si no hay
evidencia, el sistema lo declara y no inventa.

La implementación separa la recuperación léxica (`retrieval.py`) de las tareas (`tasks.py`), expone una
interfaz de biblioteca para la app y un CLI para validación manual. No usa embeddings, base vectorial,
memoria ni servicios externos.

## Technical Context

**Language/Version**: Python 3.14, gestionado con `uv`.

**Primary Dependencies**: LangChain `1.4.7`, `langchain-core` `1.7.3`, `langchain-ollama` `1.1.0`, Ollama
`0.40.5` con `llama3.1:8b`, y los módulos existentes `llm.py`, `gold` y `silver.cleaning.estimate_tokens`.
Sin dependencias nuevas.

**Storage**: lectura de `data/gold/knowledge_units.jsonl`, `context_8000.json`, `context_32000.json`,
`faq_seeds.jsonl` y `coverage.json`. Salidas opcionales en `data/module1/`, nunca en las capas medallion.

**Testing**: `pytest` con modelo falso (`build_fake_model`) para unitarias, contrato e integración; prueba
opcional contra Ollama con `OLLAMA_RUN_INTEGRATION=1`. Ruff para lint y formato.

**Target Platform**: biblioteca + CLI multiplataforma; desarrollo en Windows 11 y CI en Linux.

**Project Type**: proyecto único de librería + CLI sobre `proyecto_modelos_lenguaje`.

**Performance Goals**: Q&A < 30 s por pregunta, resumen 8k < 120 s, FAQ de 12 < 5 min en el equipo de
referencia; suite con modelo falso < 2 min.

**Constraints**: sin embeddings ni base vectorial; sin conocimiento externo; solo lectura de oro; citas
obligatorias; fallback explícito; contexto no confiable; prompts versionados; sin secretos.

**Scale/Scope**: 15.211 unidades, 3.810 fragmentos, 53 preguntas semilla, paquetes de 8k/32k y 40 preguntas
de evaluación en M1-08.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cumplimiento | Evidencia en el plan |
|--------------------------|--------------|----------------------|
| I. Reproducibilidad experimental | PASS | Prompts y `config/tasks.toml` versionados, recuperación determinista y modelo falso. |
| II. Evaluación con métricas y línea base | PASS | Resultados con prompt, modelo, latencia y citas; M1-06 y M1-08 usarán esos metadatos. |
| III. Procedencia y ética de datos | PASS | Solo unidades de oro; cada respuesta cita URL y sección; sin fuentes externas. |
| IV. Experimentos como código versionado | PASS | Prompts, configuración y pruebas en Git; hash de prompt por resultado. |
| V. Simplicidad y alcance académico | PASS | Sin embeddings ni dependencias nuevas; recuperación léxica explicable. |
| Arquitectura medallion | PASS | Oro es de solo lectura; no se escribe en bronce, plata ni oro. |
| Prompt Engineering (§3.6) | PASS | Seis secciones por prompt, anti-alucinación, citas y fallback. |
| Pipeline y pruebas (§3.8) | PASS | Suite offline con modelo falso y prueba real opcional. |
| Seguridad y secretos (§4.3) | PASS | Contexto delimitado, sin ejecución de instrucciones, sin claves en salida. |

**Resultado**: sin violaciones. No se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/007-langchain-qa-tasks/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, validaciones e invariantes
├── quickstart.md        # Fase 1: validación end-to-end
├── contracts/
│   ├── cli.md
│   ├── task-result.schema.json
│   └── faq-item.schema.json
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

```text
prompts/
├── summary.md           # Prompt de resumen con citas
├── faq.md               # Prompt de FAQ con citas
└── qa.md                # Prompt de Q&A con citas y fallback

config/
└── tasks.toml           # Top-k, presupuestos, límites y mínimos de citas

src/proyecto_modelos_lenguaje/
├── retrieval.py         # Carga de unidades, normalización, puntuación y selección
├── tasks.py             # Resumen, FAQ, Q&A, modelos de resultado y CLI
├── llm.py               # Adaptador de modelo de M1-04 (sin cambios)
└── silver/cleaning.py   # estimate_tokens (reutilizado)

tests/
├── unit/
│   ├── test_retrieval.py
│   └── test_tasks.py
├── contract/
│   └── test_tasks_contract.py
└── integration/
    ├── test_tasks_fake.py
    └── test_tasks_ollama.py
```

**Structure Decision**: se mantiene el proyecto único. `retrieval.py` concentra la selección determinista y
`tasks.py` las tres tareas y el CLI; la app M1-07 y la evaluación M1-08 consumen `tasks.py` sin depender de
Streamlit.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. Recuperación léxica tipo BM25 simplificada, sin embeddings.
2. Hasta 8 unidades y 6.000 tokens por pregunta.
3. Citas locales `[U#]` mapeadas a unidades; validación estricta.
4. Tres prompts Markdown con seis secciones y hash versionado.
5. Resumen desde `context_8000.json` por defecto.
6. FAQ con una llamada por semilla, límite 12.
7. Reintento único si faltan citas; error controlado si persiste.
8. Contexto delimitado como dato no confiable y prueba de inyección.
9. Modelo falso para pruebas; Ollama real opcional.
10. Configuración `config/tasks.toml` y CLI de validación.

## Phase 1 — Design & Contracts

### Data model

Ver [data-model.md](./data-model.md). Entidades: `TaskConfig`, `PromptTemplate`, `GoldUnit`, `ContextPack`,
`FAQSeed`, `SelectedUnit`, `EvidenceSelection`, `Citation`, `TaskResult`, `FAQItem` y `TaskError`.

### Contracts

- [contracts/cli.md](./contracts/cli.md): comandos, opciones, salidas y códigos.
- [contracts/task-result.schema.json](./contracts/task-result.schema.json): resultado de las tres tareas.
- [contracts/faq-item.schema.json](./contracts/faq-item.schema.json): elemento de FAQ.

### Quickstart

Ver [quickstart.md](./quickstart.md). Escenarios: Q&A, resumen, FAQ, modelo real, citas, inyección, errores y
rendimiento.

### Re-evaluación post-diseño

| Principio / restricción | Resultado | Evidencia |
|--------------------------|-----------|-----------|
| Reproducibilidad | PASS | Contratos, prompts y configuración versionados; modelo falso. |
| Métricas y línea base | PASS | Resultado con latencia, tokens, prompt y citas. |
| Procedencia y ética | PASS | Citas obligatorias y fallback; solo oro. |
| Experimentos como código | PASS | Prompts y pruebas en Git. |
| Simplicidad | PASS | Sin dependencias nuevas ni base vectorial. |
| Medallion y seguridad | PASS | Solo lectura de oro; contexto delimitado. |

## Implementation Phases

### Fase A — Fundamentos

1. Crear `config/tasks.toml` con `[qa]`, `[summary]` y `[faq]`.
2. Crear los tres prompts en `prompts/` con las seis secciones y marcadores.
3. Crear `retrieval.py`: carga de unidades, normalización, puntuación, diversidad y presupuesto.
4. Crear los modelos de `tasks.py`: `TaskConfig`, `PromptTemplate`, `Citation`, `TaskResult`, `FAQItem`,
   `TaskError`.
5. Cargar prompts y verificar secciones + hash SHA-256.

### Fase B — Q&A (US1)

1. Implementar `answer_question(question, ...)`.
2. Recuperar evidencia, construir contexto `[U#]`, invocar el modelo y parsear citas.
3. Reintentar una vez si faltan citas; fallback si no hay evidencia.
4. Validar citas contra las unidades seleccionadas.
5. Responder en español, distinguir filiales y, si hay cifras contradictorias, mostrar ambas con su cita
   sin promediarlas.
6. Exponer resultado estructurado.

### Fase C — Resumen (US2)

1. Cargar el paquete de contexto de 8k o 32k.
2. Construir el prompt y solicitar un resumen con 8–12 citas.
3. Validar citas y estructura; fallback si el paquete está vacío.
4. Declarar el paquete usado.

### Fase D — FAQ (US3)

1. Cargar `faq_seeds.jsonl` y sus unidades de evidencia.
2. Seleccionar y deduplicar semillas.
3. Generar una respuesta por semilla con citas.
4. Marcar `missing_evidence` cuando falte evidencia.
5. Limitar a 10–20 elementos.

### Fase E — CLI y contratos

1. Implementar `main()` con `summary`, `faq` y `qa`.
2. Añadir `--fake`, `--json`, `--pack`, `--limit` y `--config`.
3. Validar las salidas con los esquemas JSON.
4. Documentar en README y enlazar el quickstart.

### Fase F — Pruebas y validación

1. Unitarias: recuperación, citas, fallback, inyección, deduplicación, errores.
2. Contrato: esquemas y estructura de prompts.
3. Integración: las tres tareas con modelo falso.
4. Integración opcional con Ollama.
5. Ruff, pytest, build y CI.

## Testing Strategy

| Nivel | Qué cubre | Fixtures |
|-------|-----------|----------|
| Unitario | Puntuación, selección, citas, fallback, inyección, deduplicación | Unidades de oro sintéticas y modelo falso |
| Contrato | Esquemas de resultado/FAQ y secciones de prompt | `jsonschema` |
| Integración | Q&A, resumen y FAQ con datos de oro y modelo falso | `data/gold/` real; `build_fake_model` |
| Opcional | Ollama real | `OLLAMA_RUN_INTEGRATION=1` |
| Manual | CLI y quickstart | `llama3.1:8b` |

**Regla**: la suite por defecto no usa red ni consume tokens.

## Risks & Mitigations

| Riesgo | Mitigación |
|--------|------------|
| El modelo no cita | Reintento único con instrucción estricta; error controlado si persiste |
| Cita inventada | Validación contra unidades seleccionadas; descarte y `review_required` |
| Respuesta con cifras no soportadas | Instrucción anti-alucinación y revisión muestral; M1-08 evalúa |
| Recuperación léxica pierde paráfrasis | Tema + entidades + tokens; evaluar y ajustar en M1-09 |
| FAQ lenta por 12 llamadas | Límite configurable; modelo local; medir en M1-06 |
| Contexto demasiado grande | 8k por defecto; top-k y presupuesto |
| Inyección de instrucciones | Delimitadores, reglas y prueba dedicada |
| Unidades con títulos largos o ruido | Truncar títulos, filtrar flags y unidades vacías |
| Preguntas ambiguas | Fallback o respuesta parcial con citas |
| Cifras contradictorias | Mostrar ambas con su cita; no promediar ni elegir por frecuencia |
| Pruebas dependientes del modelo real | Modelo falso por defecto; integración opcional |

## Acceptance Mapping

| Requisito | Prueba / evidencia |
|-----------|--------------------|
| FR-001, FR-002 | Prompts y tres tareas en unit/contract |
| FR-003 | Carga desde `data/gold/`; sin red |
| FR-004, FR-012 | Validación de citas en unit/integration |
| FR-005 | Fallback con contexto vacío |
| FR-006, FR-007 | Recuperación determinista y presupuesto |
| FR-008 | Resumen 8k/32k con citas |
| FR-009, FR-010 | FAQ 10–20 y deduplicación |
| FR-011 | Prueba de inyección |
| FR-013 | Esquema `task-result.schema.json` |
| FR-014, FR-015 | Preguntas inválidas y errores del modelo |
| FR-016 | Suite con modelo falso |
| FR-017 | Prueba opcional con Ollama |
| FR-018 | `prompt_version` y `prompt_sha256` en resultados |
| FR-019, FR-020, FR-021 | Casos de idioma, filiales y conflictos |
| FR-022 | CLI y biblioteca sin Streamlit |
| SC-001…SC-010 | Quickstart y pruebas de integración |

## Complexity Tracking

Sin violaciones de la constitución. No se requiere justificación adicional.

## Next Steps

1. Ejecutar `/speckit.tasks` para generar el backlog ejecutable de M1-05.
2. Implementar Fase A y US1 (Q&A) como MVP.
3. Validar con el quickstart y actualizar la bitácora.
