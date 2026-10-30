# Implementation Plan: Entrada canónica de scraping (`scrape_empresa.py`)

**Branch**: `005-scrape-empresa-entrypoint` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/005-scrape-empresa-entrypoint/spec.md`

## Summary

Crear una entrada canónica y estable para ejecutar el scraping de bronce sin duplicar el pipeline:
`scripts/scrape_empresa.py` valida los parámetros, resuelve el estado de la campaña, delega en el runner
existente y reporta un resumen humano o JSON con métricas, políticas, duración y código de salida.

La implementación extrae una función de orquestación compartida (`start_campaign`) para que la CLI `pml` y
la nueva entrada usen la misma ruta. El `--dry-run` se ejecuta contra una raíz temporal para no dejar
artefactos ni registros en el bronce real. La campaña es idempotente y reanudable, y nunca toca plata u oro.

## Technical Context

**Language/Version**: Python 3.14, gestionado con `uv`.

**Primary Dependencies**: biblioteca estándar (`argparse`, `dataclasses`, `pathlib`, `tempfile`, `time`,
`json`) y módulos existentes del proyecto: `catalog.Catalog`, `config.load_config`,
`config.load_coverage_items`, `config.PROJECT_ROOT`, `fetchers.http.build_http_fetcher`,
`pipeline.CampaignRunner`, `pipeline.CampaignSummary`, `storage.BronzeStorage`. Sin dependencias nuevas.

**Storage**: catálogo SQLite de bronce (`data/bronze/_meta/bronze.sqlite3`) y almacenamiento de artefactos
en `data/bronze/`. No se modifica el esquema. El `--dry-run` usa una raíz temporal y la descarta.

**Testing**: `pytest` con pruebas unitarias, de contrato (esquemas JSON) e integración contra el servidor
local de `tests/conftest.py`; sin red externa. Ruff para lint y formato.

**Target Platform**: CLI multiplataforma; desarrollo en Windows 11 y CI en Linux.

**Project Type**: proyecto único de librería + CLI sobre `proyecto_modelos_lenguaje`.

**Performance Goals**: preflight (validación, estado y ayuda) en < 2 s; sobrecarga de la fachada < 2 s
frente a una invocación directa del pipeline; `--dry-run --limit 5` en menos de 30 s en el servidor de
pruebas local.

**Constraints**: sin secretos ni credenciales; sin evasión de `robots.txt`; solo bronce; sin cambios en
plata u oro; salida determinista y validable; comportamiento consistente en Windows y Linux.

**Scale/Scope**: una campaña por invocación; el wrapper no procesa el corpus completo en pruebas. El
universo real es 557 artefactos activos y 26.905 artefactos catalogados, pero las pruebas usan fixtures
locales.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cumplimiento | Evidencia en el plan |
|--------------------------|--------------|----------------------|
| I. Reproducibilidad experimental | PASS | Configuración versionada, campaña explícita, comandos documentados, pruebas offline y raíz temporal para dry-run. |
| II. Evaluación con métricas y línea base | PASS | Resumen con métricas, comparación de equivalencia contra la invocación directa (SC-003) y pruebas de contrato. |
| III. Procedencia y ética de datos | PASS | Se delega en la política existente de `robots.txt`; no se usan cookies ni credenciales; cada decisión queda registrada. |
| IV. Experimentos como código versionado | PASS | `scripts/scrape_empresa.py`, contratos, pruebas y configuración en Git; sin estado oculto. |
| V. Simplicidad y alcance académico | PASS | Fachada fina, sin dependencias nuevas y sin un segundo crawler. |
| Arquitectura medallion | PASS | Solo escribe bronce; plata y oro quedan fuera y se verifican como no modificados. |
| Pipeline canónico y reanudable | PASS | Entrada canónica, idempotencia, reanudación y detección de concurrencia. |
| Seguridad y datos no versionados | PASS | Sin secretos en salida; `data/` fuera de Git; sin credenciales. |
| Puertas de calidad | PASS | Ruff, pytest, CI y checklist de requisitos. |

**Resultado**: sin violaciones. No se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/005-scrape-empresa-entrypoint/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, validaciones e invariantes
├── quickstart.md        # Fase 1: validación end-to-end
├── contracts/
│   ├── cli.md           # Contrato de la interfaz de línea de comandos
│   ├── scrape-summary.schema.json
│   └── error.schema.json
├── checklists/
│   └── requirements.md  # Validación de la especificación
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

```text
scripts/
└── scrape_empresa.py                  # Entrada canónica, fina, delega en entrypoint.main

src/proyecto_modelos_lenguaje/
├── cli.py                             # Refactor: cmd_campaign_start usa campaign_service
├── campaign_service.py                # Orquestación compartida: start_campaign(...)
├── entrypoint.py                      # Parseo, validación, estado, salida y códigos
├── catalog.py                         # Sin cambios de esquema; lectura de estado
├── config.py                          # Sin cambios; carga y raíz del proyecto
├── pipeline.py                        # Sin cambios; CampaignRunner y CampaignSummary
└── storage.py                         # Sin cambios; almacenamiento de bronce

tests/
├── unit/
│   └── test_scrape_entrypoint.py      # Parseo, validación, matriz de estados, render
├── contract/
│   └── test_scrape_entrypoint_contract.py  # Esquemas JSON y ayuda
└── integration/
    └── test_scrape_entrypoint.py      # Servidor local, dry-run, resume, equivalencia
```

**Structure Decision**: se mantiene el proyecto único existente. La lógica de presentación y validación
vive en `entrypoint.py`; la orquestación compartida en `campaign_service.py`; el script es un envoltorio
de una línea. Las pruebas siguen la separación unit/contract/integration ya usada por bronce, plata y oro.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. Fachada fina sobre `CampaignRunner`; prohibido duplicar el crawler.
2. `argparse` de la biblioteca estándar.
3. Matriz explícita de estados: crear, reanudar, rechazar o no-op.
4. `--dry-run` contra una raíz temporal y descarte al final.
5. `campaign_service.start_campaign` compartido con `pml campaign start`.
6. Un único objeto de salida con resumen, políticas, duración y código.
7. Códigos `0`, `2`, `4` y `1` con significados distintos.
8. Rutas relativas resueltas contra la raíz del proyecto.
9. Concurrencia delegada al índice único del catálogo.
10. Pruebas unitarias, de contrato y de integración con el servidor local.
11. Sin dependencias nuevas.

## Phase 1 — Design & Contracts

### Data model

Ver [data-model.md](./data-model.md). Entidades: `ScrapeRequest`, `EffectiveParameters`, `Campaign`,
`CampaignStateAssessment`, `CampaignRun`, `RunSummary`, `PolicyOutcome`, `ScrapeOutcome` y `EntryError`.

### Contracts

- [contracts/cli.md](./contracts/cli.md): sintaxis, opciones, matriz de estados, salidas y códigos.
- [contracts/scrape-summary.schema.json](./contracts/scrape-summary.schema.json): esquema de éxito.
- [contracts/error.schema.json](./contracts/error.schema.json): esquema de error.

### Quickstart

Ver [quickstart.md](./quickstart.md). Escenarios: ayuda, sin argumentos, dry-run, campaña limitada,
reanudación, políticas, errores de uso y comparación con la invocación directa.

### Re-evaluación post-diseño

Revisados `data-model.md`, `contracts/cli.md`, los dos esquemas JSON y `quickstart.md` el 2026-10-30:

| Principio / restricción | Resultado | Evidencia |
|--------------------------|-----------|-----------|
| I. Reproducibilidad | PASS | Contrato y quickstart fijan comandos y parámetros; dry-run aislado. |
| II. Métricas y línea base | PASS | El esquema exige métricas y el quickstart compara con la invocación directa. |
| III. Procedencia y ética | PASS | El contrato exige registrar políticas y prohíbe evadir `robots.txt`. |
| IV. Experimentos como código | PASS | Contratos y pruebas versionados; sin estado oculto. |
| V. Simplicidad | PASS | Un solo módulo de entrada y uno de servicio; sin dependencias nuevas. |
| Medallion y seguridad | PASS | Solo bronce; sin secretos; plata y oro fuera de escritura. |

**Resultado post-diseño**: sin violaciones. El plan sigue listo para `/speckit.tasks`.

## Implementation Phases

### Fase A — Servicio de orquestación compartido

1. Crear `campaign_service.py` con `CampaignRun` y `start_campaign(...)`.
2. Mover a `start_campaign` la construcción de catálogo, almacenamiento, fetcher y runner.
3. Hacer que `cmd_campaign_start` use `start_campaign` sin cambiar su salida ni su código de salida.
4. Capturar `policy_checks` y la duración antes de cerrar el catálogo.
5. Añadir pruebas de regresión para `pml campaign start`.

### Fase B — Entrada canónica

1. Crear `entrypoint.py` con `ScrapeRequest`, `parse_request`, `validate_request`,
   `assess_campaign_state`, `execute` y `main`.
2. Implementar la matriz de estados de `research.md` §3.
3. Implementar la validación de configuración, campaña y límite antes de la red.
4. Implementar `--dry-run` con raíz temporal.
5. Implementar salida humana y JSON, y el objeto de error.
6. Implementar los códigos de salida `0`, `2`, `4` y `1`.

### Fase C — Script y contratos

1. Crear `scripts/scrape_empresa.py` como envoltorio de `entrypoint.main`.
2. Publicar `contracts/cli.md`, `scrape-summary.schema.json` y `error.schema.json`.
3. Validar las muestras con `jsonschema`.
4. Actualizar `README.md` con el comando canónico y un ejemplo.
5. Actualizar la bitácora y marcar M1-02.

### Fase D — Pruebas y validación

1. Unitarias: parseo, validación, estados, render y errores.
2. Contrato: esquemas JSON y opciones de ayuda.
3. Integración: servidor local, dry-run aislado, campaña limitada, reanudación, fuente bloqueada,
   equivalencia con la invocación directa y verificación de que plata/oro no cambian.
4. Ruff, pytest y CI.
5. Ejecutar el quickstart manual.

## Testing Strategy

| Nivel | Qué cubre | Fixtures |
|-------|-----------|----------|
| Unitario | Parseo, validación, matriz de estados, render humano/JSON, errores | `tmp_path`, mocks mínimos |
| Contrato | Esquemas de éxito y error, opciones de `--help` | `jsonschema`, `Draft202012Validator` |
| Integración | Delegación real, dry-run, campaña limitada, resume, políticas, no escritura en plata/oro | `server`, `write_config`, `app_config`, `build_runner` |
| Manual | Quickstart end-to-end | Servidor local o sitio real con `--limit` |

**Regla**: ninguna prueba usa red externa ni credenciales. Las pruebas de integración usan el servidor
local de `tests/conftest.py`.

## Risks & Mitigations

| Riesgo | Mitigación |
|--------|------------|
| El `--dry-run` deja estado en el bronce real | Raíz temporal + prueba que compara el catálogo antes/después |
| El refactor de `cmd_campaign_start` cambia el comportamiento de `pml` | Pruebas de regresión y comparación de salida/código |
| La reanudación automática sorprende al operador | El modo `resume` se reporta antes de ejecutar y en el JSON |
| La detección de concurrencia depende de SQLite | Traducir el error a un mensaje accionable y probar dos campañas |
| Campañas completadas se reejecutan por error | No-op con estado `already_completed` y código `0` |
| Rutas distintas según el `cwd` | Resolver contra la raíz del proyecto y probar desde otro directorio |
| Windows y encoding | Pruebas de ayuda y salida JSON en CI Linux y ejecución local Windows |
| IDs de campaña inseguros | Validación estricta antes de crear estado |

## Acceptance Mapping

| Requisito | Prueba / evidencia |
|-----------|--------------------|
| FR-001, FR-004 | `--help` y presencia del script en unit/contract |
| FR-002, FR-015 | Configuración por defecto, inexistente e inválida |
| FR-003, FR-016, FR-017 | Sin campaña, ID inválido y creación con el ID exacto |
| FR-005, FR-006 | Matriz de estados y pruebas de resume |
| FR-007 | Límites válidos, cero, negativos y no enteros |
| FR-008 | Dry-run con catálogo real sin cambios |
| FR-009 | Salida JSON validada contra esquema |
| FR-010 | Comparación con la invocación directa |
| FR-011, FR-019, FR-025 | Servidor local con `robots.txt` y fuente bloqueada |
| FR-012 | Prueba de reanudación sin duplicados |
| FR-013 | Resumen con todos los campos |
| FR-014 | Códigos de salida en unit/integration |
| FR-018 | Dos campañas concurrentes |
| FR-020 | Hash de `data/silver` y `data/gold` antes/después |
| FR-021 | Salida sin secretos ni rutas absolutas |
| FR-022 | Parámetros efectivos antes de ejecutar |
| FR-023 | Pruebas en Windows local y CI Linux |
| FR-024 | Campaña completada no se reejecuta |
| SC-001…SC-010 | Quickstart y pruebas de integración |

## Complexity Tracking

Sin violaciones de la constitución. No se requiere justificación adicional.

## Next Steps

1. Ejecutar `/speckit.tasks` para generar las tareas ejecutables de M1-02.
2. Implementar Fase A (servicio compartido) y Fase B (entrada canónica).
3. Validar con el quickstart y marcar M1-02 en la bitácora.
