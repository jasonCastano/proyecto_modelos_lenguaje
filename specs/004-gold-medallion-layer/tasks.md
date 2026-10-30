# Tareas: Capa Oro (Gold) — Base de Conocimiento Consolidada y Citable

**Entrada**: documentos de diseño de `/specs/004-gold-medallion-layer/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: incluidas porque la constitución exige pruebas para cada módulo crítico (§3.8) y la especificación
define criterios verificables. Cada tarea de prueba debe fallar antes de la implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US5`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: código en `src/proyecto_modelos_lenguaje/`, pruebas en `tests/`, configuración en `config/`,
documentación en `specs/004-gold-medallion-layer/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: configuración, taxonomía, esqueleto y fixtures de la capa oro.

- [X] T001 Crear `config/gold.toml` con las secciones `[units]`, `[topics]`, `[coverage]`, `[context]`, `[output]` y `[run]` y los valores iniciales de `data-model.md` (`min_sentence_chars=40`, `max_unit_chars=700`, `dedup_threshold=0.90`, `covered_min_units=3`, `covered_min_official=1`, `budgets=[8000,32000]`, `chars_per_token=3.5`).
- [X] T002 Crear `config/gold_taxonomy.toml` con al menos 12 `[[topics]]` (`id`, `title`, `description`, `coverage_item_ids`, `keywords`) y las `[[entities]]` principales (`id`, `canonical_name`, `entity_type`, `aliases`, `coverage_item_ids`), incluyendo los 24 ítems de `config/coverage-items.toml`.
- [X] T003 Crear el esqueleto `src/proyecto_modelos_lenguaje/gold/__init__.py` y los directorios `tests/unit/gold/`, `tests/contract/gold/` y `tests/integration/gold/` con sus `__init__.py`.
- [X] T004 [P] Crear `tests/gold_helpers.py` con un helper que escriba un corpus plata temporal (`documents.jsonl` y `chunks.jsonl`) con documentos canónicos, alias, secciones, offsets y linaje para las pruebas de oro.
- [X] T005 [P] Crear `tests/contract/gold/conftest.py` con helpers para cargar los ocho esquemas de `specs/004-gold-medallion-layer/contracts/` y validar registros con `jsonschema.Draft202012Validator`.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: modelos, configuración, lectura de plata, texto, taxonomía y almacenamiento que bloquean todas las historias.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [X] T006 Crear `src/proyecto_modelos_lenguaje/gold/models.py` con dataclasses `KnowledgeUnit`, `Evidence`, `Fact`, `Entity`, `Topic`, `Conflict`, `ConflictValue`, `CoverageEntry`, `ContextPack`, `ContextBlock`, `FAQSeed`, `GoldManifest` y `GoldReport`, y enums de estado/calidad; validar `unit_id` `unit_[a-f0-9]{16}`, `fact_id` `fact_[a-f0-9]{16}`, `entity_id` `ent_[a-f0-9]{16}`, `conflict_id` `conf_[a-f0-9]{16}`, `seed_id` `faq_[a-f0-9]{16}`, `evidence` no vacío y `text` no vacío.
- [X] T007 Crear `src/proyecto_modelos_lenguaje/gold/config.py` para cargar `config/gold.toml` con `tomllib`, validar rangos (`0 < min_sentence_chars < max_unit_chars`, `0 < dedup_threshold <= 1`, `budgets` crecientes y positivos), exponer `GoldConfig` y calcular `config_hash` SHA-256 del TOML canónico más la versión de reglas.
- [X] T008 Crear `src/proyecto_modelos_lenguaje/gold/store.py` con escritura atómica de JSONL, JSON y Markdown (temporal + `os.replace`), lectura de JSONL, estado incremental en `data/gold/_meta/state.jsonl`, caché por `doc_id + text_hash + config_hash` y validación de `run_id` `YYYY-MM-gold-NN`.
- [X] T009 Crear `src/proyecto_modelos_lenguaje/gold/inputs.py` para leer `data/silver/documents.jsonl` y `chunks.jsonl`, conservar solo `status = canonical`, construir el mapa documento → fragmentos y verificar que cada fragmento tenga `doc_id`, `content_hash`, `url`, `section_path` y offsets válidos.
- [X] T010 Crear `src/proyecto_modelos_lenguaje/gold/text.py` con normalización de espacios, minúsculas y acentos, segmentación de oraciones con abreviaturas (`S.A.`, `S.A.S.`, `No.`, `p.`, `pp.`, `vs.`, `Dr.`, `Ing.`), unión de oraciones cortas y corte de oraciones largas.
- [X] T011 Crear `src/proyecto_modelos_lenguaje/gold/taxonomy.py` para cargar `config/gold_taxonomy.toml`, indexar temas por palabra clave/alias, asignar el tema de mayor puntuación, mapear a los 24 ítems y marcar `topic_uncertain` cuando no supere `topics.min_score`.
- [X] T012 Crear `tests/contract/gold/test_schemas.py` que valide registros de muestra de los ocho contratos y falle si un esquema o un campo obligatorio cambia.

**Punto de control**: modelos, configuración, lectura de plata, texto, taxonomía y almacenamiento listos; las historias pueden comenzar.

---

## Fase 3: Historia de Usuario 1 — Base consolidada y citable (Prioridad: P1) 🎯 MVP

**Objetivo**: convertir fragmentos canónicos en unidades extractivas con tema, evidencia, cita y linaje, y organizarlas en temas navegables.

**Prueba independiente**: construir la base desde el corpus plata temporal y verificar que cada unidad tiene tema, evidencia, URL y linaje; que no hay unidades sin evidencia; y que las páginas de tema citan sus fuentes.

### Pruebas de la Historia 1

- [X] T013 [P] [US1] Pruebas unitarias de unidades en `tests/unit/gold/test_units.py`: segmentación, unión de oraciones cortas, corte de largas, `unit_id` determinista, deduplicación exacta, `text` presente en el fragmento y `no_evidence` para fragmentos sin texto útil.
- [X] T014 [P] [US1] Pruebas unitarias de temas en `tests/unit/gold/test_topics.py`: asignación por palabra clave, `topic_uncertain` bajo el umbral, mapeo a ítems de cobertura y página Markdown con frontmatter y citas.
- [X] T015 [US1] Prueba de integración en `tests/integration/gold/test_build_us1.py`: corpus plata temporal con dos documentos y varios fragmentos; verificar `knowledge_units.jsonl`, `topics/*.md`, evidencia, linaje, hashes de plata sin cambios y cero unidades sin cita.

### Implementación de la Historia 1

- [X] T016 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/gold/units.py` para extraer unidades de cada fragmento con `text.split`/`text.py`, asignar tema, evidencia, autoridad, confianza, estado `current`, flags y `unit_id`.
- [X] T017 [US1] Implementar la deduplicación exacta (SHA-256 del texto normalizado) y cercana (Jaccard de shingles de 5 palabras, umbral 0.90) en `src/proyecto_modelos_lenguaje/gold/units.py`, fusionando evidencias sin perder citas.
- [X] T018 [P] [US1] Implementar `src/proyecto_modelos_lenguaje/gold/topics.py` para agrupar unidades por tema, calcular `unit_count` y renderizar `data/gold/topics/<topic_id>.md` con frontmatter y citas.
- [X] T019 [US1] Integrar la etapa de unidades y temas en `src/proyecto_modelos_lenguaje/gold/pipeline.py`, con aislamiento de errores por documento y registro de documentos sin unidades.
- [X] T020 [US1] Escribir `data/gold/knowledge_units.jsonl` y las páginas de tema con `store.py`, en orden determinista, y actualizar `_meta/state.jsonl` por documento.
- [X] T021 [US1] Implementar la validación de invariantes de unidad en `models.py`: evidencia no vacía, `text` no vacío, `topic_id` existente, `url`/`title`/`section_path` no nulos y `unit_id` único.
- [X] T022 [US1] Añadir el subcomando mínimo `pml gold build` en `src/proyecto_modelos_lenguaje/cli.py` con `--config`, `--taxonomy`, `--run`, `--limit`, `--topic`, `--force` y `--json`.

**Punto de control**: `pml gold build --limit 10` produce unidades y páginas de tema citables; la US1 es verificable de forma independiente.

---

## Fase 4: Historia de Usuario 2 — Entidades, hechos y conflictos (Prioridad: P2)

**Objetivo**: identificar entidades y hechos, resolver conflictos con autoridad/vigencia y conservar los disputados.

**Prueba independiente**: introducir dos fuentes con el mismo sujeto/atributo y valores distintos; verificar que el conflicto queda registrado, que la fuente oficial prevalece y que la versión anterior no se pierde.

### Pruebas de la Historia 2

- [X] T023 [P] [US2] Pruebas unitarias de entidades en `tests/unit/gold/test_entities.py`: alias, acentos, límites de palabra, entidad canónica única, `entity_id` estable y asociación a unidades.
- [X] T024 [P] [US2] Pruebas unitarias de hechos en `tests/unit/gold/test_facts.py`: número + unidad, porcentaje, año, sujeto/atributo explícitos, ausencia de hechos cuando falta un componente y `value_normalized` correcto.
- [X] T025 [P] [US2] Pruebas unitarias de conflictos en `tests/unit/gold/test_conflicts.py`: dos valores distintos, preferencia por `first_party`, preferencia por fecha, empate como `disputed`, y conservación de ambas evidencias.
- [X] T026 [US2] Prueba de integración en `tests/integration/gold/test_build_us2.py`: corpus temporal con entidades, hechos y conflicto; verificar `entities.jsonl`, `facts.jsonl`, `conflicts.jsonl` y el glosario.

### Implementación de la Historia 2

- [X] T027 [P] [US2] Implementar `src/proyecto_modelos_lenguaje/gold/entities.py` con el vocabulario controlado, alias, normalización de acentos, detección por límites de palabra, consolidación de entidades y `entity_id`.
- [X] T028 [P] [US2] Implementar `src/proyecto_modelos_lenguaje/gold/facts.py` con patrones de cifra+unidad, porcentaje y año; guardar sujeto, atributo, valor, unidad, año, evidencia y `value_normalized`; no crear hechos incompletos.
- [X] T029 [US2] Implementar `src/proyecto_modelos_lenguaje/gold/conflicts.py` para agrupar por `(subject_id, attribute)`, detectar valores distintos, elegir preferente por autoridad/fecha/evidencia y marcar `resolved`/`disputed`.
- [X] T030 [US2] Integrar entidades, hechos y conflictos en `src/proyecto_modelos_lenguaje/gold/pipeline.py`; actualizar unidades con `entity_ids`, `fact_id`, `status` y `conflicting`.
- [X] T031 [US2] Generar `data/gold/glossary.md` con entidades, alias, tipo y unidades de evidencia en `src/proyecto_modelos_lenguaje/gold/topics.py`.
- [X] T032 [US2] Escribir `data/gold/entities.jsonl`, `facts.jsonl` y `conflicts.jsonl` de forma atómica y añadir sus conteos al estado/reporte.

**Punto de control**: entidades, hechos y conflictos resueltos; la US2 es verificable de forma independiente.

---

## Fase 5: Historia de Usuario 3 — Cobertura de los 24 ítems (Prioridad: P3)

**Objetivo**: generar una matriz real de los 24 ítems con evidencia, autoridad, conflictos y vacíos justificados.

**Prueba independiente**: generar la matriz y verificar que cada ítem tiene estado y evidencia o razón de vacío; que un ítem sin unidades no aparece como cubierto.

### Pruebas de la Historia 3

- [X] T033 [P] [US3] Pruebas unitarias de cobertura en `tests/unit/gold/test_coverage.py`: `covered` con 3 unidades y 1 oficial, `partial` con 1–2 o solo terceros, `missing` sin unidades, conflicto asociado y razón de vacío obligatoria.
- [X] T034 [US3] Prueba de integración en `tests/integration/gold/test_build_us3.py`: corpus temporal que cubre unos ítems y deja otros vacíos; verificar exactamente 24 entradas, estados y `coverage.md`.

### Implementación de la Historia 3

- [X] T035 [US3] Implementar `src/proyecto_modelos_lenguaje/gold/coverage.py` para agrupar unidades por `coverage_item_ids`, contar autoridades y conflictos, y aplicar los umbrales de `config/gold.toml`.
- [X] T036 [US3] Generar `data/gold/coverage.json` y `data/gold/coverage.md` con las 24 entradas, porcentaje cubierto y lista priorizada de vacíos.
- [X] T037 [US3] Añadir razones de vacío y recomendaciones de fuente para cada ítem no cubierto en `src/proyecto_modelos_lenguaje/gold/coverage.py`, sin inventar evidencia.
- [X] T038 [US3] Extender el resumen `--json` de `pml gold build` en `src/proyecto_modelos_lenguaje/cli.py` con `coverage.covered`, `partial`, `missing` y `units`.

**Punto de control**: 24/24 ítems evaluados; la US3 es verificable de forma independiente.

---

## Fase 6: Historia de Usuario 4 — Contexto y preguntas semilla (Prioridad: P4)

**Objetivo**: generar paquetes de contexto 8k/32k con citas y preguntas semilla para FAQ.

**Prueba independiente**: generar ambos paquetes y verificar que respetan el presupuesto, no repiten unidades, incluyen citas y que el paquete de 32k contiene todos los temas del de 8k.

### Pruebas de la Historia 4

- [X] T039 [P] [US4] Pruebas unitarias de contexto en `tests/unit/gold/test_context_pack.py`: prioridad por cobertura/autoridad/vigencia, presupuesto, no duplicados, citas y omisiones registradas.
- [X] T040 [P] [US4] Pruebas unitarias de FAQ en `tests/unit/gold/test_faq.py`: preguntas desde ítems/temas, evidencia obligatoria, `missing_evidence` cuando no hay unidad y `seed_id` determinista.
- [X] T041 [US4] Prueba de integración en `tests/integration/gold/test_build_us4.py`: verificar `context_8k.md`, `context_32k.md`, sus JSONL, `faq_seeds.jsonl` y la relación de contención entre paquetes.

### Implementación de la Historia 4

- [X] T042 [US4] Implementar `src/proyecto_modelos_lenguaje/gold/context_pack.py` con selección greedy por cobertura, autoridad, vigencia y diversidad, usando `silver.cleaning.estimate_tokens` y los presupuestos configurados.
- [X] T043 [US4] Renderizar `data/gold/context_8k.md` y `context_32k.md` y sus JSONL de bloques con cita, `unit_id`, tokens y tema.
- [X] T044 [US4] Implementar `src/proyecto_modelos_lenguaje/gold/faq.py` para generar preguntas semilla desde ítems de cobertura, títulos de tema y entidades, con `evidence_unit_ids` y estado.
- [X] T045 [US4] Escribir `data/gold/faq_seeds.jsonl` y validar que ninguna pregunta queda sin evidencia o marcada `missing_evidence` cuando no hay unidad.

**Punto de control**: paquetes de contexto y FAQ seeds listos; la US4 es verificable de forma independiente.

---

## Fase 7: Historia de Usuario 5 — Calidad, incrementalidad y auditoría (Prioridad: P5)

**Objetivo**: reporte de calidad, estado incremental, auditoría de linaje y CLI completa.

**Prueba independiente**: dos ejecuciones sin cambios producen archivos idénticos; modificar un documento de plata actualiza solo sus unidades; 50 unidades se rastrean a la URL pública.

### Pruebas de la Historia 5

- [X] T046 [P] [US5] Pruebas de contrato en `tests/contract/gold/test_outputs.py`: validar unidades, hechos, entidades, conflictos, cobertura, contexto, FAQ y reporte contra los ocho esquemas.
- [X] T047 [P] [US5] Prueba de integración de idempotencia en `tests/integration/gold/test_idempotency.py`: dos ejecuciones sin cambios producen bytes idénticos; un documento modificado solo actualiza sus unidades.
- [X] T048 [P] [US5] Prueba de integración de auditoría en `tests/integration/gold/test_audit.py`: 50 unidades rastreadas a `chunk_id`, `doc_id`, `content_hash` y URL; hashes de bronce/plata sin cambios.
- [X] T049 [P] [US5] Pruebas unitarias del reporte en `tests/unit/gold/test_reporting.py`: conteos, cobertura, conflictos, tokens, flags y Markdown.

### Implementación de la Historia 5

- [X] T050 [US5] Implementar `src/proyecto_modelos_lenguaje/gold/reporting.py` con `data/gold/reports/<run_id>/quality.json` y `quality.md` según el contrato.
- [X] T051 [US5] Implementar la orquestación completa, el estado incremental y la caché en `src/proyecto_modelos_lenguaje/gold/pipeline.py`; cada etapa debe ser visible y los fallos aislarse por documento.
- [X] T052 [US5] Completar `pml gold build|verify|report|status` en `src/proyecto_modelos_lenguaje/cli.py`, con sobres JSON y códigos de salida 0/1/2/3.
- [X] T053 [US5] Crear `scripts/build_gold.py` como envoltorio canónico que delegue en `pml gold build`.
- [X] T054 [US5] Añadir verificación de offline y de inmutabilidad de bronce/plata en `src/proyecto_modelos_lenguaje/gold/pipeline.py`: sin red, hashes antes/después y ninguna escritura fuera de `data/gold/`.
- [X] T055 [US5] Implementar protección de `run_id` reutilizado, confirmación de `--force` y aislamiento de ejecuciones `--limit`/`--topic` en `data/gold/_meta/smoke/<run_id>/`.

**Punto de control**: CLI completa, estado incremental y reporte funcionando; la US5 es verificable de forma independiente.

---

## Fase 8: Pulido y preocupaciones transversales

**Propósito**: documentación, CI, rendimiento y validación final.

- [X] T056 [P] Documentar la capa oro en `README.md`: propósito, estructura de `data/gold/`, comandos, cobertura y limitaciones.
- [X] T057 [P] Crear `docs/decisions/0004-gold-layer.md` con las decisiones de extracción extractiva, taxonomía, hechos, conflictos, dedup y presupuestos de contexto.
- [X] T058 [P] Actualizar `.github/workflows/ci.yml` para ejecutar también las pruebas de contrato de oro.
- [X] T059 Ejecutar la construcción completa con `uv run python scripts/build_gold.py --run 2026-10-gold-01 --json`, confirmar 404 documentos / 3.810 fragmentos / 24 ítems y guardar el reporte en `data/gold/reports/2026-10-gold-01/`.
- [X] T060 Medir la ejecución completa contra el objetivo de 10 minutos/4 GB, registrar resultados en `docs/decisions/0004-gold-layer.md` y ajustar `config/gold.toml` si es necesario.
- [X] T061 Ejecutar todos los escenarios de `specs/004-gold-medallion-layer/quickstart.md` y registrar el resultado de SC-001 a SC-015 en `specs/004-gold-medallion-layer/checklists/requirements.md`.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; comienza de inmediato.
- **Fundamentos (Fase 2)**: depende de la preparación; bloquea todas las historias.
- **US1 (Fase 3)**: depende de los fundamentos; entrega el MVP.
- **US2 (Fase 4)**: depende de US1; añade entidades, hechos y conflictos.
- **US3 (Fase 5)**: depende de US2; usa las unidades y conflictos para la cobertura.
- **US4 (Fase 6)**: depende de US3; prioriza el contexto por cobertura.
- **US5 (Fase 7)**: depende de US1–US4; añade estado, reporte y CLI completa.
- **Pulido (Fase 8)**: depende de todas las historias.

### Dependencias entre historias

- **US1 (P1)**: independiente tras los fundamentos; produce unidades y temas.
- **US2 (P2)**: requiere US1; añade entidades, hechos y conflictos.
- **US3 (P3)**: requiere US2; genera la matriz de cobertura.
- **US4 (P4)**: requiere US3; empaqueta contexto y preguntas semilla.
- **US5 (P5)**: requiere US1–US4; mide, audita y expone la CLI.

### Dentro de cada historia

- Las pruebas se escriben primero y deben fallar antes de la implementación.
- Modelos y utilidades antes de los servicios.
- Etapas del pipeline antes del cableado de la CLI.
- La historia se completa y valida antes de pasar a la siguiente prioridad.

### Oportunidades de paralelización

- T004 y T005 pueden ejecutarse en paralelo tras T001–T003.
- T013–T014 pueden ejecutarse en paralelo; T016 y T018 también.
- T023–T025 pueden ejecutarse en paralelo; T027 y T028 también.
- T033 y T039–T040 pueden ejecutarse en paralelo con sus implementaciones.
- T046–T049 pueden ejecutarse en paralelo; T056–T058 también.

---

## Ejemplo paralelo: Historia 1

```text
Tarea: T013 Pruebas de unidades en tests/unit/gold/test_units.py
Tarea: T014 Pruebas de temas en tests/unit/gold/test_topics.py

Tarea: T016 Unidades en src/proyecto_modelos_lenguaje/gold/units.py
Tarea: T018 Temas en src/proyecto_modelos_lenguaje/gold/topics.py
```

## Ejemplo paralelo: Historia 2

```text
Tarea: T023 Pruebas de entidades en tests/unit/gold/test_entities.py
Tarea: T024 Pruebas de hechos en tests/unit/gold/test_facts.py
Tarea: T025 Pruebas de conflictos en tests/unit/gold/test_conflicts.py

Tarea: T027 Entidades en src/proyecto_modelos_lenguaje/gold/entities.py
Tarea: T028 Hechos en src/proyecto_modelos_lenguaje/gold/facts.py
```

## Ejemplo paralelo: Historia 3

```text
Tarea: T033 Pruebas de cobertura en tests/unit/gold/test_coverage.py
Tarea: T035 Cobertura en src/proyecto_modelos_lenguaje/gold/coverage.py
```

## Ejemplo paralelo: Historia 4

```text
Tarea: T039 Pruebas de contexto en tests/unit/gold/test_context_pack.py
Tarea: T040 Pruebas de FAQ en tests/unit/gold/test_faq.py

Tarea: T042 Contexto en src/proyecto_modelos_lenguaje/gold/context_pack.py
Tarea: T044 FAQ en src/proyecto_modelos_lenguaje/gold/faq.py
```

## Ejemplo paralelo: Historia 5

```text
Tarea: T046 Contratos en tests/contract/gold/test_outputs.py
Tarea: T047 Idempotencia en tests/integration/gold/test_idempotency.py
Tarea: T048 Auditoría en tests/integration/gold/test_audit.py
Tarea: T049 Reporte en tests/unit/gold/test_reporting.py
```

---

## Estrategia de implementación

### MVP primero (solo Historia 1)

1. Completar la Fase 1: Preparación.
2. Completar la Fase 2: Fundamentos.
3. Completar la Fase 3: US1.
4. Ejecutar `uv run pml gold build --run 2026-10-gold-00 --limit 10 --json`.
5. Validar unidades, temas, evidencia y linaje.

### Entrega incremental

1. Preparación + Fundamentos → base lista.
2. US1 → unidades y temas citables (MVP).
3. US2 → entidades, hechos y conflictos.
4. US3 → matriz de los 24 ítems.
5. US4 → contexto y preguntas semilla.
6. US5 → calidad, estado y CLI.
7. Pulido → documentación, CI y validación SC-001…SC-015.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 unidades/temas + US3 cobertura.
3. Roberto: US2 entidades/hechos/conflictos + US4 contexto/FAQ.
4. Integrar US1 → US2 → US3 → US4 → US5 y validar cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- No se versionan datos ni artefactos de `data/gold/`; se regeneran desde plata.
- La plata y el bronce son de solo lectura; cualquier escritura fuera de `data/gold/` es un defecto.
- Las tareas T059–T061 requieren el corpus de plata y no deben ejecutarse en CI.
