# Tareas: Entrada canónica de scraping (`scrape_empresa.py`)

**Entrada**: documentos de diseño de `/specs/005-scrape-empresa-entrypoint/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: incluidas porque el plan define una estrategia de pruebas y la constitución exige pruebas
para cada módulo crítico. Cada prueba debe fallar antes de la implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: código en `src/proyecto_modelos_lenguaje/`, scripts en `scripts/`, pruebas en `tests/`,
documentación en `specs/005-scrape-empresa-entrypoint/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: dejar el entorno y los archivos de prueba listos sin añadir dependencias.

- [X] T001 [P] Crear el esqueleto de pruebas unitarias en `tests/unit/test_scrape_entrypoint.py` con docstring, imports de `argparse`, `pathlib`, `pytest` y los módulos que se crearán.
- [X] T002 [P] Crear el esqueleto de pruebas de contrato en `tests/contract/test_scrape_entrypoint_contract.py` con carga de `jsonschema.Draft202012Validator` y rutas a `specs/005-scrape-empresa-entrypoint/contracts/`.
- [X] T003 [P] Crear el esqueleto de pruebas de integración en `tests/integration/test_scrape_entrypoint.py` con imports de `tests.conftest`, `sqlite3` y `hashlib`.
- [X] T004 Verificar la línea base en `pyproject.toml` y `uv.lock`: `uv sync --frozen`, `uv run ruff check .` y `uv run pytest -q`; confirmar que no se añaden dependencias.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: servicio de orquestación, modelos de entrada/salida, parser, validación, matriz de estados y renderizado. Bloquea todas las historias.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [X] T005 Crear `src/proyecto_modelos_lenguaje/campaign_service.py` con `CampaignRun` (`summary`, `policy`, `duration_seconds`, `resumed`, `dry_run`) y `start_campaign(...)`, que construye catálogo, almacenamiento, fetcher y runner, ejecuta la campaña y captura `policy_checks` antes de cerrar el catálogo.
- [X] T006 Refactorizar `cmd_campaign_start` en `src/proyecto_modelos_lenguaje/cli.py` para usar `campaign_service.start_campaign` sin cambiar la salida ni el código de salida de `pml campaign start`.
- [X] T007 Añadir pruebas de regresión de `pml campaign start` en `tests/integration/test_campaign.py`: misma salida, mismo código y mismas métricas que antes del refactor.
- [X] T008 Crear en `src/proyecto_modelos_lenguaje/entrypoint.py` los dataclasses `ScrapeRequest`, `EffectiveParameters`, `CampaignStateAssessment`, `ScrapeOutcome` y `EntryError`, más las constantes de códigos de salida y la expresión regular de campaña `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`.
- [X] T009 Implementar `parse_request(argv)` en `src/proyecto_modelos_lenguaje/entrypoint.py` con `argparse`: `--config` (por defecto `config/sources.toml`), `--campaign`, `--resume`, `--limit` (entero positivo), `--dry-run`, `--json` y `--help`; sin argumentos debe imprimir ayuda y ejemplos y salir con `0`.
- [X] T010 Implementar `validate_request` en `src/proyecto_modelos_lenguaje/entrypoint.py`: verificar que la configuración existe y carga con `load_config`, que el `campaign_id` cumple la expresión regular y que `limit > 0`; devolver errores `missing_config`, `invalid_config`, `invalid_campaign` o `invalid_limit` antes de cualquier acceso a red.
- [X] T011 Implementar `assess_campaign_state` en `src/proyecto_modelos_lenguaje/entrypoint.py` con la matriz de `research.md` §3: crear si no existe, reanudar `planned`/`paused`/`failed`, rechazar `running` y `aborted`, y no-op en `completed`; devolver `CampaignStateAssessment` con `action`, `reason` y `exit_code`.
- [X] T012 Implementar `render_human` y `render_json` en `src/proyecto_modelos_lenguaje/entrypoint.py` para `ScrapeOutcome` y `EntryError`; el JSON debe validar contra `contracts/scrape-summary.schema.json` y `contracts/error.schema.json`.
- [X] T013 Implementar `main(argv, project_root=None)` en `src/proyecto_modelos_lenguaje/entrypoint.py` como preflight: parsear, validar, evaluar estado, imprimir parámetros efectivos, ejecutar y traducir el resultado a salida y código `0`, `1`, `2` o `4`.
- [X] T014 [P] Añadir pruebas unitarias de parser, validación, matriz de estados y renderizado en `tests/unit/test_scrape_entrypoint.py`: opciones válidas, sin campaña, límite cero/negativo/no entero, ID inválido, configuración inexistente y cada estado de campaña.
- [X] T015 [P] Añadir pruebas de contrato en `tests/contract/test_scrape_entrypoint_contract.py`: `--help` documenta todas las opciones, y las muestras de éxito/error validan contra los dos esquemas de `specs/005-scrape-empresa-entrypoint/contracts/`.

**Punto de control**: servicio compartido, parser, validación, estados, renderizado y preflight listos; las historias pueden comenzar.

---

## Fase 3: Historia de Usuario 1 — Ejecutar el comando canónico (Prioridad: P1) 🎯 MVP

**Objetivo**: una sola orden inicia una campaña nueva, delega en el pipeline y reporta estado y métricas.

**Prueba independiente**: ejecutar el comando contra una campaña desechable con límite bajo y verificar que el pipeline descubre, extrae y almacena, y que la salida contiene campaña, estado, métricas y código `0`.

### Pruebas de la Historia 1

- [X] T016 [US1] Añadir prueba unitaria del modo `new` en `tests/unit/test_scrape_entrypoint.py`: parámetros efectivos, `mode=new`, `status=completed` y código `0`.
- [X] T017 [US1] Añadir prueba de integración de campaña nueva en `tests/integration/test_scrape_entrypoint.py` con `server`, `write_config` y `app_config`: verificar artefactos almacenados, métricas y rutas de reporte.
- [X] T018 [US1] Añadir prueba de contrato de la salida de éxito en `tests/contract/test_scrape_entrypoint_contract.py`: el objeto de una campaña nueva valida contra `scrape-summary.schema.json`.

### Implementación de la Historia 1

- [X] T019 [US1] Implementar en `src/proyecto_modelos_lenguaje/entrypoint.py` la ruta `execute_new_campaign(request, config)`: llamar a `campaign_service.start_campaign`, construir `ScrapeOutcome` y medir la duración.
- [X] T020 [US1] Implementar en `src/proyecto_modelos_lenguaje/entrypoint.py` la salida humana y JSON del modo `new`, incluyendo configuración, campaña, límite, estado, descubiertos, almacenados, omitidos, fallidos, bytes, duración y políticas.
- [X] T021 [US1] Crear `scripts/scrape_empresa.py` como envoltorio fino que importe `proyecto_modelos_lenguaje.entrypoint.main` y ejecute `raise SystemExit(main(sys.argv[1:]))`.

**Punto de control**: el comando canónico ejecuta una campaña nueva y es el MVP de M1-02.

---

## Fase 4: Historia de Usuario 2 — Reanudar una campaña interrumpida (Prioridad: P2)

**Objetivo**: continuar una campaña pausada o fallida sin duplicar artefactos ni perder progreso, y no reabrir una completada.

**Prueba independiente**: interrumpir una campaña limitada, reejecutar el mismo ID con `--resume` y verificar que continúa, no duplica hashes y reporta `mode=resume`.

### Pruebas de la Historia 2

- [X] T022 [US2] Añadir prueba unitaria de la matriz de estados en `tests/unit/test_scrape_entrypoint.py`: `planned`, `paused`, `failed`, `running`, `completed`, `aborted` y ausente, con y sin `--resume`.
- [X] T023 [US2] Añadir prueba de integración de reanudación en `tests/integration/test_scrape_entrypoint.py`: campaña pausada, reejecución con `--resume`, sin duplicados y sin pérdida de artefactos.

### Implementación de la Historia 2

- [X] T024 [US2] Implementar en `src/proyecto_modelos_lenguaje/entrypoint.py` la reanudación automática de `planned`/`paused`/`failed`, el uso explícito de `--resume` y el no-op de `completed` con `mode=already_completed` y código `0`.
- [X] T025 [US2] Implementar en `src/proyecto_modelos_lenguaje/entrypoint.py` los errores accionables `campaign_running`, `campaign_aborted` y `missing_campaign_for_resume`, con código `2` y sin acceso a red.

**Punto de control**: la campaña se puede reanudar y las campañas terminadas no se reabren.

---

## Fase 5: Historia de Usuario 3 — Prueba segura antes de la campaña completa (Prioridad: P3)

**Objetivo**: validar configuración, conectividad y políticas con `--dry-run` sin dejar rastro en el bronce real.

**Prueba independiente**: ejecutar `--dry-run --limit 5` y verificar que el catálogo real no gana campañas, artefactos ni registros, mientras la salida reporta descubrimiento y políticas.

### Pruebas de la Historia 3

- [X] T026 [US3] Añadir prueba unitaria del aislamiento temporal en `tests/unit/test_scrape_entrypoint.py`: `dataclasses.replace` cambia `data_root`, el directorio temporal se elimina y la configuración original no se muta.
- [X] T027 [US3] Añadir prueba de integración de `--dry-run` en `tests/integration/test_scrape_entrypoint.py`: comparar el catálogo real antes/después, verificar cero campañas y cero artefactos nuevos.
- [X] T028 [US3] Añadir prueba de contrato de la salida `--dry-run` en `tests/contract/test_scrape_entrypoint_contract.py`: `effective.dry_run=true`, `summary.artifacts_stored=0` y esquema válido.

### Implementación de la Historia 3

- [X] T029 [US3] Implementar en `src/proyecto_modelos_lenguaje/entrypoint.py` el `--dry-run` con `tempfile.TemporaryDirectory` y `dataclasses.replace(config, settings=replace(config.settings, data_root=...))`, ejecutando el pipeline contra esa raíz y descartándola al final.

**Punto de control**: el operador puede probar sin contaminar el bronce.

---

## Fase 6: Historia de Usuario 4 — Auditar políticas y delegación (Prioridad: P4)

**Objetivo**: demostrar que la entrada canónica respeta `robots.txt`, registra cada decisión y produce las mismas métricas que la invocación directa.

**Prueba independiente**: ejecutar una campaña limitada con una fuente bloqueada, verificar que se registra como `disallowed` y no se captura, y comparar las métricas con `pml campaign start` para los mismos insumos.

### Pruebas de la Historia 4

- [X] T030 [US4] Añadir prueba de integración de política en `tests/integration/test_scrape_entrypoint.py`: fuente bloqueada por `robots.txt`, decisión `disallowed`, motivo no vacío y cero artefactos de esa fuente.
- [X] T031 [US4] Añadir prueba de integración de equivalencia en `tests/integration/test_scrape_entrypoint.py`: misma campaña lógica con la entrada canónica y con `pml campaign start`; comparar descubiertos, almacenados, excluidos, fallidos y bytes.
- [X] T032 [US4] Añadir prueba de integración de capas en `tests/integration/test_scrape_entrypoint.py`: hashes de `data/silver` y `data/gold` antes/después; cero cambios.

### Implementación de la Historia 4

- [X] T033 [US4] Extender `src/proyecto_modelos_lenguaje/campaign_service.py` para devolver `policy` agregado por `source_id`/`decision`/`reason` y la duración, sin duplicar la lógica de `PolicyEngine`.
- [X] T034 [US4] Extender `src/proyecto_modelos_lenguaje/entrypoint.py` para incluir en la salida humana y JSON los conteos `allowed`, `disallowed`, `unreachable` y `by_reason`, y para no exponer credenciales ni rutas absolutas.

**Punto de control**: la delegación y el cumplimiento de políticas son auditables.

---

## Fase 7: Pulido y aspectos transversales

**Propósito**: documentación, decisión de arquitectura, validación manual, CI y bitácora.

- [X] T035 Actualizar `README.md` con el comando canónico, las opciones, un ejemplo de `--dry-run` y otro de campaña limitada; enlazar `specs/005-scrape-empresa-entrypoint/quickstart.md`.
- [X] T036 Crear `docs/decisions/0005-scrape-entrypoint.md` con la decisión de fachada, la orquestación compartida, el dry-run aislado y los códigos de salida.
- [X] T037 Ejecutar `uv run ruff check .` y corregir hallazgos en `src/proyecto_modelos_lenguaje/entrypoint.py`, `src/proyecto_modelos_lenguaje/campaign_service.py`, `scripts/scrape_empresa.py` y `tests/`.
- [X] T038 Ejecutar `uv run pytest -q` y corregir fallos en `tests/unit/test_scrape_entrypoint.py`, `tests/contract/test_scrape_entrypoint_contract.py` y `tests/integration/test_scrape_entrypoint.py`.
- [X] T039 Ejecutar `uv build` y verificar que el sdist y el wheel se generan sin errores y que el entry point `pml` de `pyproject.toml` sigue funcionando; `scripts/scrape_empresa.py` se distribuye en el repositorio, no dentro del wheel.
- [X] T040 Ejecutar el quickstart manual de `specs/005-scrape-empresa-entrypoint/quickstart.md` con las campañas `2026-10-m1-02-*` y anexar los resultados observados en el mismo archivo.
- [X] T041 Verificar el workflow `.github/workflows/ci.yml`: Ruff, pytest y build en verde; añadir un paso específico para `tests/contract/test_scrape_entrypoint_contract.py` si el pipeline general no lo cubre.
- [X] T042 Regenerar la bitácora con `uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py` y confirmar que M1-02 pasa a completada en `bitacora/`.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; puede empezar de inmediato.
- **Fundamentos (Fase 2)**: depende de Fase 1; bloquea todas las historias.
- **US1 (Fase 3)**: depende de Fase 2; es el MVP.
- **US2 (Fase 4)**: depende de Fase 2 y de la ruta de ejecución de US1.
- **US3 (Fase 5)**: depende de Fase 2 y de la ruta de ejecución de US1.
- **US4 (Fase 6)**: depende de Fase 2 y de US1; comparte `entrypoint.py` con US2/US3, por lo que se ejecuta después.
- **Pulido (Fase 7)**: depende de todas las historias deseadas.

### Dependencias entre historias

- **US1 (P1)**: no depende de otras historias; entrega el MVP.
- **US2 (P2)**: requiere la ejecución de US1; añade reanudación y no-op.
- **US3 (P3)**: requiere la ejecución de US1; añade aislamiento temporal.
- **US4 (P4)**: requiere US1; añade auditoría de políticas y equivalencia.

### Dentro de cada historia

1. Pruebas primero; deben fallar antes de la implementación.
2. Modelos y validaciones antes de la ejecución.
3. Ejecución antes de la integración.
4. Cada historia debe dejar Ruff y pytest en verde.

### Oportunidades de paralelización

- T001, T002 y T003 pueden ejecutarse en paralelo (archivos de prueba distintos).
- T014 y T015 pueden ejecutarse en paralelo (unitarias y contrato).
- T005 y T008 pueden ejecutarse en paralelo (servicio y modelos), pero T006 depende de T005.
- T016, T017 y T018 pueden prepararse en paralelo, pero comparten archivos con tareas posteriores; ejecutar en el orden indicado.
- T030, T031 y T032 comparten `tests/integration/test_scrape_entrypoint.py`, por lo que no son paralelizables entre sí.

---

## Ejemplo de paralelización: Fase 1

```text
Tarea: T001 Crear esqueleto unitario en tests/unit/test_scrape_entrypoint.py
Tarea: T002 Crear esqueleto de contrato en tests/contract/test_scrape_entrypoint_contract.py
Tarea: T003 Crear esqueleto de integración en tests/integration/test_scrape_entrypoint.py
```

## Ejemplo de paralelización: Fundamentos

```text
Tarea: T014 Pruebas unitarias de parser/validación/estados en tests/unit/test_scrape_entrypoint.py
Tarea: T015 Pruebas de contrato de ayuda y esquemas en tests/contract/test_scrape_entrypoint_contract.py
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1: Preparación.
2. Completar Fase 2: Fundamentos.
3. Completar Fase 3: US1.
4. Ejecutar `uv run python scripts/scrape_empresa.py --help`.
5. Ejecutar una campaña limitada `2026-10-m1-02-smoke` y validar métricas.
6. Detenerse y validar el MVP antes de US2–US4.

### Entrega incremental

1. Preparación + Fundamentos → base lista.
2. US1 → comando canónico y campaña nueva (MVP).
3. US2 → reanudación y campañas completadas.
4. US3 → dry-run aislado.
5. US4 → auditoría de políticas y equivalencia.
6. Pulido → README, ADR, quickstart, CI y bitácora.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 y US2 (ejecución y reanudación).
3. Roberto: US3 y US4 (dry-run y auditoría).
4. Integrar en orden US1 → US2 → US3 → US4 y validar cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- No se versionan datos ni artefactos de `data/`; las campañas de prueba usan el prefijo `2026-10-m1-02-`.
- El bronce es la única capa que se escribe; plata y oro son de solo lectura.
- Las pruebas de integración usan el servidor local de `tests/conftest.py`; no hay red externa.
- La entrada canónica no duplica el crawler: toda la ejecución pasa por `campaign_service.start_campaign`.
