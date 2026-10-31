# Tareas: Tareas LangChain — Resumen, FAQ y Q&A

**Entrada**: documentos de diseño de `/specs/007-langchain-qa-tasks/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: incluidas porque el plan y la constitución exigen pruebas offline para cada módulo crítico. Cada
prueba debe fallar antes de la implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: prompts en `prompts/`, configuración en `config/`, código en
`src/proyecto_modelos_lenguaje/`, pruebas en `tests/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: configuración, prompts y esqueletos de prueba.

- [x] T001 [P] Crear `config/tasks.toml` con las secciones `[qa]` (`top_k=8`, `token_budget=6000`, `min_score=0.0`), `[summary]` (`pack="8000"`, `min_citations=8`) y `[faq]` (`limit=12`, `top_k=5`, `min_citations=1`, `question_max_chars=500`).
- [x] T002 [P] Crear `prompts/summary.md` con las seis secciones obligatorias: rol, tarea, contexto delimitado, reglas, formato de cita `[U#]` y comportamiento sin evidencia.
- [x] T003 [P] Crear `prompts/faq.md` con las seis secciones obligatorias y la instrucción de responder una sola pregunta con evidencia.
- [x] T004 [P] Crear `prompts/qa.md` con las seis secciones obligatorias, la prohibición de conocimiento externo y el fallback “No hay evidencia suficiente…”.
- [x] T005 [P] Crear el esqueleto de pruebas unitarias de recuperación en `tests/unit/test_retrieval.py`.
- [x] T006 [P] Crear el esqueleto de pruebas unitarias de tareas en `tests/unit/test_tasks.py`.
- [x] T007 [P] Crear el esqueleto de pruebas de contrato en `tests/contract/test_tasks_contract.py`.
- [x] T008 [P] Crear el esqueleto de pruebas de integración con modelo falso en `tests/integration/test_tasks_fake.py`.
- [x] T009 [P] Crear el esqueleto de pruebas opcionales con Ollama en `tests/integration/test_tasks_ollama.py`.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: configuración, prompts, modelos de resultado, carga de oro y recuperación determinista.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [x] T010 Implementar `TaskConfig` y `load_task_config` en `src/proyecto_modelos_lenguaje/tasks.py`: validar `qa_top_k` 1–20, `qa_token_budget` 1000–30000, `qa_min_score >= 0`, `summary_pack` `"8000"`/`"32000"`, `summary_min_citations` 1–30, `faq_limit` 10–20, `faq_top_k` 1–10, `faq_min_citations` 1–10 y `question_max_chars` 20–2000.
- [x] T011 Implementar en `src/proyecto_modelos_lenguaje/tasks.py` el cargador de `prompts/summary.md`, `prompts/faq.md` y `prompts/qa.md` como `PromptTemplate`, con validación de las seis secciones y `sha256` del contenido.
- [x] T012 Implementar en `src/proyecto_modelos_lenguaje/retrieval.py` la carga de `data/gold/knowledge_units.jsonl`, `context_8000.json`, `context_32000.json`, `faq_seeds.jsonl` y `coverage.json` en dataclasses de solo lectura.
- [x] T013 Implementar en `src/proyecto_modelos_lenguaje/retrieval.py` la normalización de texto, tokenización, eliminación de acentos y puntuación BM25 simplificada con tema, entidades y señales de calidad.
- [x] T014 Implementar en `src/proyecto_modelos_lenguaje/retrieval.py` `select_evidence(question, ...)` con `qa_top_k=8`, `qa_token_budget=6000`, diversidad por tema, etiquetas `U1..Un` y registro de unidades omitidas.
- [x] T015 Crear en `src/proyecto_modelos_lenguaje/tasks.py` los dataclasses `Citation`, `TaskResult`, `FAQItem` y `TaskError` con los campos y estados de `data-model.md`: `status` en `ok|fallback|review|error`, `fallback=True` implica `citations=[]`, `status=ok` implica al menos una cita.
- [x] T016 Implementar en `src/proyecto_modelos_lenguaje/tasks.py` el parseo de citas `[U#]`, el mapeo a `Citation` y la validación de que cada `unit_id` pertenece a `used_unit_ids`; las citas externas se descartan y marcan `review_required=True`.
- [x] T017 Implementar en `src/proyecto_modelos_lenguaje/tasks.py` la validación de preguntas: no vacías, sin caracteres de control y `<= question_max_chars=500`; devolver `TaskError` con `empty_question` o `question_too_long` antes de llamar al modelo.
- [x] T018 [P] Añadir pruebas unitarias de configuración y prompts en `tests/unit/test_tasks.py`: valores por defecto, rangos inválidos, seis secciones y hash SHA-256 estable.
- [x] T019 [P] Añadir pruebas unitarias de recuperación en `tests/unit/test_retrieval.py`: puntuación determinista, tema, entidades, top-k, presupuesto y diversidad.
- [x] T020 [P] Añadir pruebas de contrato de los prompts y esquemas en `tests/contract/test_tasks_contract.py`: secciones obligatorias y muestras válidas contra `contracts/task-result.schema.json` y `contracts/faq-item.schema.json`.

**Punto de control**: configuración, prompts, carga de oro, recuperación y modelos de resultado listos.

---

## Fase 3: Historia de Usuario 1 — Q&A citado con fallback (Prioridad: P1) 🎯 MVP

**Objetivo**: responder preguntas con evidencia de oro, citas verificables y fallback explícito.

**Prueba independiente**: 10 preguntas con el modelo falso; cada resultado debe ser una respuesta con al menos una cita válida o un fallback, sin texto ajeno al contexto.

### Pruebas de la Historia 1

- [x] T021 [US1] Añadir prueba unitaria de Q&A en `tests/unit/test_tasks.py`: respuesta con `[U1]`, cita mapeada a `unit_id`, `status=ok` y lista de fuentes.
- [x] T022 [US1] Añadir prueba unitaria de fallback y citas inválidas en `tests/unit/test_tasks.py`: sin evidencia devuelve `status=fallback`; `[U99]` se descarta y marca `review_required`.
- [x] T023 [US1] Añadir prueba de integración de Q&A con modelo falso en `tests/integration/test_tasks_fake.py`: 10 preguntas del alcance, cada una con cita o fallback.
- [x] T024 [US1] Añadir prueba unitaria de inyección de contexto en `tests/unit/test_tasks.py`: una unidad con “ignora las instrucciones” no cambia la tarea y la respuesta sigue citando o cae en fallback.

### Implementación de la Historia 1

- [x] T025 [US1] Implementar `answer_question(question, ...)` en `src/proyecto_modelos_lenguaje/tasks.py`: recuperar evidencia, construir contexto `<context><unit id="U1">…</unit></context>`, invocar el modelo y parsear citas.
- [x] T026 [US1] Implementar en `src/proyecto_modelos_lenguaje/tasks.py` el reintento único si faltan citas, el error controlado `missing_citations` si persiste y el fallback sin llamada al modelo cuando no hay evidencia.
- [x] T027 [US1] Implementar en `src/proyecto_modelos_lenguaje/tasks.py` la respuesta en español, la distinción de filiales y la regla de mostrar cifras contradictorias con su cita sin promediarlas.

**Punto de control**: Q&A funciona de extremo a extremo y es el MVP de M1-05.

---

## Fase 4: Historia de Usuario 2 — Resumen citado (Prioridad: P2)

**Objetivo**: generar un resumen estructurado del corpus con 8–12 citas y sin afirmaciones sin fuente.

**Prueba independiente**: generar el resumen con el paquete de 8k y el modelo falso; verificar estructura, 8–12 citas y fallback con contexto vacío.

### Pruebas de la Historia 2

- [x] T028 [US2] Añadir prueba unitaria de resumen en `tests/unit/test_tasks.py`: 8–12 citas, `task=summary`, `status=ok` y `used_unit_ids` del paquete de 8k.
- [x] T029 [US2] Añadir prueba de integración de resumen con modelo falso en `tests/integration/test_tasks_fake.py`: `context_8000.json` real y resultado con fuentes.
- [x] T030 [US2] Añadir prueba unitaria de contexto vacío en `tests/unit/test_tasks.py`: resumen devuelve `status=fallback` sin inventar secciones.

### Implementación de la Historia 2

- [x] T031 [US2] Implementar `summarize_corpus(...)` en `src/proyecto_modelos_lenguaje/tasks.py`: cargar `context_8000.json`, construir el prompt, invocar el modelo y validar 8–12 citas.
- [x] T032 [US2] Implementar en `src/proyecto_modelos_lenguaje/tasks.py` la selección del paquete de 32k solo si el modelo lo soporta y la declaración del paquete usado; si no, usar 8k.

**Punto de control**: Resumen funciona con citas y fallback.

---

## Fase 5: Historia de Usuario 3 — FAQ con evidencia (Prioridad: P3)

**Objetivo**: generar 10–20 preguntas frecuentes con respuesta, citas y estado de revisión a partir de las 53 semillas.

**Prueba independiente**: generar la FAQ con el modelo falso y verificar 10–20 elementos, citas y `missing_evidence` cuando falte evidencia.

### Pruebas de la Historia 3

- [x] T033 [US3] Añadir prueba unitaria de FAQ en `tests/unit/test_tasks.py`: 10–20 elementos, deduplicación por pregunta normalizada y `status=ready` con citas.
- [x] T034 [US3] Añadir prueba unitaria de semilla sin evidencia en `tests/unit/test_tasks.py`: `status=missing_evidence`, respuesta de fallback y cero citas.
- [x] T035 [US3] Añadir prueba de integración de FAQ con modelo falso en `tests/integration/test_tasks_fake.py`: `faq_seeds.jsonl` real, límite 12 y todas las entradas con cita o `missing_evidence`.

### Implementación de la Historia 3

- [x] T036 [US3] Implementar `generate_faq(...)` en `src/proyecto_modelos_lenguaje/tasks.py`: cargar semillas, seleccionar hasta `faq_limit=12`, recuperar sus `evidence_unit_ids` y generar una respuesta por semilla.
- [x] T037 [US3] Implementar en `src/proyecto_modelos_lenguaje/tasks.py` la deduplicación por texto normalizado, el estado `ready|review|missing_evidence` y el límite 10–20.

**Punto de control**: FAQ funciona y respeta evidencia y límites.

---

## Fase 6: Historia de Usuario 4 — Auditoría y CLI (Prioridad: P4)

**Objetivo**: prompts versionados, resultados con metadatos, citas auditables y CLI de validación.

**Prueba independiente**: revisar los tres prompts, ejecutar el CLI con `--fake` y verificar versión de prompt, hash, modelo, latencia y citas en cada resultado.

### Pruebas de la Historia 4

- [x] T038 [US4] Añadir prueba de contrato de `TaskResult` en `tests/contract/test_tasks_contract.py`: éxito, fallback y error validan contra `task-result.schema.json`.
- [x] T039 [US4] Añadir prueba de contrato de `FAQItem` en `tests/contract/test_tasks_contract.py`: `ready` con cita y `missing_evidence` sin citas validan contra `faq-item.schema.json`.
- [x] T040 [US4] Añadir prueba unitaria de metadatos en `tests/unit/test_tasks.py`: `prompt_version`, `prompt_sha256`, `model`, `latency_seconds`, `input_tokens` y `output_tokens` presentes.
- [x] T041 [US4] Añadir prueba de integración de integridad de citas en `tests/integration/test_tasks_fake.py`: todas las `citations.unit_id` pertenecen a `used_unit_ids`.
- [x] T042 [US4] Añadir prueba de CLI en `tests/unit/test_tasks.py`: `qa --fake --json`, `summary --fake --json` y `faq --fake --json` devuelven JSON válido y código `0`.

### Implementación de la Historia 4

- [x] T043 [US4] Implementar en `src/proyecto_modelos_lenguaje/tasks.py` el registro de `prompt_version`, `prompt_sha256`, `model`, latencia y tokens estimados con `silver.cleaning.estimate_tokens`.
- [x] T044 [US4] Implementar en `src/proyecto_modelos_lenguaje/tasks.py` `main()` con subcomandos `summary`, `faq` y `qa`, opciones `--pack`, `--limit`, `--config`, `--fake` y `--json`, y códigos `0`/`1`/`2`.
- [x] T045 [US4] Añadir prueba de integración opcional con Ollama en `tests/integration/test_tasks_ollama.py`: Q&A, resumen y FAQ reales, omitida por defecto salvo `OLLAMA_RUN_INTEGRATION=1`.

**Punto de control**: prompts, resultados, citas y CLI son auditables.

---

## Fase 7: Pulido y aspectos transversales

**Propósito**: documentación, decisión de arquitectura, validación manual, CI y bitácora.

- [x] T046 Actualizar `README.md` con los comandos de Resumen, FAQ y Q&A, la opción `--fake` y el enlace a `specs/007-langchain-qa-tasks/quickstart.md`.
- [x] T047 Crear `docs/decisions/0007-langchain-tasks.md` con la decisión de recuperación léxica, citas `[U#]`, prompts versionados, fallback y modelo falso.
- [x] T048 Ejecutar `uv run ruff check .` y corregir hallazgos en `src/proyecto_modelos_lenguaje/tasks.py`, `src/proyecto_modelos_lenguaje/retrieval.py` y `tests/`.
- [x] T049 Ejecutar `uv run pytest -q` y corregir fallos en `tests/unit/test_tasks.py`, `tests/unit/test_retrieval.py`, `tests/contract/test_tasks_contract.py`, `tests/integration/test_tasks_fake.py` y `tests/integration/test_tasks_ollama.py`.
- [x] T050 Ejecutar `uv build` y verificar que el paquete incluye `tasks.py` y `retrieval.py` y que el CLI `python -m proyecto_modelos_lenguaje.tasks` funciona.
- [x] T051 Ejecutar el quickstart con `--fake` para Q&A, resumen y FAQ, y anexar los resultados observados en `specs/007-langchain-qa-tasks/quickstart.md`.
- [ ] T052 Ejecutar una prueba real con `llama3.1:8b` para Q&A y resumen, y registrar latencia y citas en `docs/prompt_log.md` o en el quickstart.
- [x] T053 Regenerar la bitácora con `uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py` y confirmar que M1-05 y G3 pasan a completadas.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; puede empezar de inmediato.
- **Fundamentos (Fase 2)**: depende de Fase 1; bloquea todas las historias.
- **US1 Q&A (Fase 3)**: depende de Fase 2; es el MVP.
- **US2 Resumen (Fase 4)**: depende de Fase 2 y de la infraestructura de tareas; puede ejecutarse después de US1.
- **US3 FAQ (Fase 5)**: depende de Fase 2 y de la infraestructura de tareas; puede ejecutarse después de US1.
- **US4 Auditoría/CLI (Fase 6)**: depende de US1–US3 para validar los tres resultados.
- **Pulido (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1 (P1)**: no depende de otras historias; entrega el MVP.
- **US2 (P2)**: requiere Fase 2; puede integrarse con US1 pero se prueba sola.
- **US3 (P3)**: requiere Fase 2; puede integrarse con US1/US2 pero se prueba sola.
- **US4 (P4)**: requiere US1–US3; audita los resultados de las tres tareas.

### Dentro de cada historia

1. Pruebas primero; deben fallar antes de la implementación.
2. Modelos y validaciones antes de la ejecución.
3. Ejecución antes de la integración.
4. Cada historia debe dejar Ruff y pytest en verde.

### Oportunidades de paralelización

- T001–T009 pueden ejecutarse en paralelo (archivos distintos).
- T018–T020 pueden ejecutarse en paralelo (pruebas en archivos distintos).
- T028–T030 y T033–T035 comparten `tests/unit/test_tasks.py` o `tests/integration/test_tasks_fake.py`, por lo que no son paralelizables entre sí.
- T038–T042 comparten archivos de prueba; ejecutar en orden.
- Las implementaciones de US1–US3 comparten `src/proyecto_modelos_lenguaje/tasks.py`; ejecutar secuencialmente.

---

## Ejemplo de paralelización: Fase 1

```text
Tarea: T001 Crear config/tasks.toml
Tarea: T002 Crear prompts/summary.md
Tarea: T003 Crear prompts/faq.md
Tarea: T004 Crear prompts/qa.md
Tarea: T005 Crear tests/unit/test_retrieval.py
Tarea: T006 Crear tests/unit/test_tasks.py
Tarea: T007 Crear tests/contract/test_tasks_contract.py
Tarea: T008 Crear tests/integration/test_tasks_fake.py
Tarea: T009 Crear tests/integration/test_tasks_ollama.py
```

## Ejemplo de paralelización: Fundamentos

```text
Tarea: T018 Pruebas de configuración y prompts en tests/unit/test_tasks.py
Tarea: T019 Pruebas de recuperación en tests/unit/test_retrieval.py
Tarea: T020 Pruebas de contrato en tests/contract/test_tasks_contract.py
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1: Preparación.
2. Completar Fase 2: Fundamentos.
3. Completar Fase 3: US1 Q&A.
4. Ejecutar `uv run python -m proyecto_modelos_lenguaje.tasks qa --question "¿Qué productos ofrece Manuelita?" --fake --json`.
5. Validar citas y fallback.
6. Detenerse y validar el MVP antes de US2–US4.

### Entrega incremental

1. Preparación + Fundamentos → base lista.
2. US1 → Q&A citado (MVP).
3. US2 → Resumen citado.
4. US3 → FAQ con evidencia.
5. US4 → auditoría y CLI.
6. Pulido → README, ADR, quickstart, CI y bitácora.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 Q&A y US4 auditoría/CLI.
3. Roberto: US2 Resumen y US3 FAQ.
4. Integrar en orden US1 → US2 → US3 → US4 y validar cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- No se versionan datos ni artefactos de `data/gold/`; se leen en modo de solo lectura.
- La suite por defecto usa el modelo falso y no requiere Ollama ni red.
- La prueba real con Ollama es opcional y se ejecuta con `OLLAMA_RUN_INTEGRATION=1`.
- La app Streamlit y la evaluación de 40 preguntas son M1-07 y M1-08, no M1-05.
