# Quickstart: Validación del Filtro de Relevancia

**Feature**: `002-manuelita-relevance-filter` | **Date**: 2026-10-28

Guía para validar de extremo a extremo la depuración del corpus. No contiene código de implementación; los
detalles están en [plan.md](./plan.md), [data-model.md](./data-model.md) y [contracts/](./contracts/).

## Prerequisites

- Corpus bronce poblado (`data/bronze/_meta/bronze.sqlite3` con 26.752 artefactos).
- Python 3.14 y `uv`; `uv sync --frozen` ejecutado.
- `config/relevance.toml` presente y válido.
- Responsable del proyecto disponible para revisar ambigüedades y aprobar la purga.
- Las pruebas no requieren red.

## Setup

```bash
uv sync --frozen
uv run ruff check .
uv run pytest
```

Resultado esperado: entorno reproducible, lint limpio y pruebas offline en verde.

## Scenario 1 — Análisis en seco (sin escrituras)

```bash
uv run pml curate analyze --config config/relevance.toml --json
```

Esperado:

- `dry_run: true` y `run_id: null`.
- `artifacts_evaluated` = 26.752 (o el total del alcance).
- `kept` cercano a 410, `removed` cercano a 26.300 y `review` menor a 100.
- No se crean filas en `relevance_evaluations`, `curation_runs` ni archivos nuevos.

Señal de fallo: cualquier escritura o un `kept` muy superior a 500.

## Scenario 2 — Aplicar el análisis

```bash
uv run pml curate analyze --config config/relevance.toml \
  --run 2026-10-curation-01 --apply --json
```

Esperado:

- `status: analyzed`.
- `evaluated = kept + removed + review`.
- Reporte en `data/bronze/reports/2026-10-curation-01/curation.json`.
- Todos los artefactos del dominio oficial en `keep` con puntuación 100.
- El corpus activo y la cobertura **no cambian** todavía: las evaluaciones son propuestas hasta la aprobación.

## Scenario 3 — Reporte y muestras

```bash
uv run pml curate report --run 2026-10-curation-01 --format json
```

Esperado: conteos por fuente, bytes antes, muestras de conservados y eliminados, y advertencias si hay
artefactos sin texto verificable.

## Scenario 4 — Revisión de ambiguos

```bash
uv run pml curate review list --run 2026-10-curation-01 --limit 20 --json
uv run pml curate review decide --artifact 12345 --decision remove \
  --reviewer "Jason Castaño" --note "Mención incidental en correo institucional"
```

Esperado:

- La lista muestra URL, título, fragmento, puntuación y motivo.
- La decisión manual queda con `method: manual`, `manual_override: true`, revisor y fecha.
- Re-ejecutar `analyze` no cambia esa decisión.

## Scenario 5 — Aprobación

```bash
uv run pml curate approve --run 2026-10-curation-01 --reviewer "Jason Castaño" --json
```

Esperado: `status: approved`.

Señal de fallo: exit `5` si queda algún `review` pendiente; la aprobación no debe forzarse sin revisarlos.

## Scenario 6 — Cuarentena y corpus activo

```bash
uv run pml curate quarantine --run 2026-10-curation-01 --confirm --json
```

Esperado:

- Archivos movidos a `data/quarantine/2026-10-curation-01/<artifact_id>/`.
- Una fila de auditoría por artefacto eliminado.
- Manifiestos y exportaciones activas sin artefactos eliminados.
- `pml curate status` muestra `quarantined` y los bytes en cuarentena.

Validación del corpus activo:

```bash
uv run pml catalog list --campaign 2026-10-baseline --active-only --limit 10 --json
uv run pml catalog export --campaign 2026-10-baseline --active-only \
  --format jsonl --output exports/curated.jsonl
```

Esperado: solo artefactos `keep`; los 397 oficiales presentes.

## Scenario 7 — Cobertura recalculada

```bash
uv run pml coverage --campaign 2026-10-baseline --active-only --json
```

Esperado: 24 ítems con estado honesto; los ítems que dependían de portales genéricos pasan a `missing` o
`partial` con `gap_reason`. Ya no debe reportarse 24/24 sin evidencia real.

## Scenario 8 — Purga y liberación de espacio

```bash
uv run pml curate purge --run 2026-10-curation-01 --expired --confirm --json
```

Para una validación inmediata (solo en entorno de prueba):

```bash
uv run pml curate purge --run 2026-10-curation-01 --now --confirm --json
```

Esperado:

- `bytes_freed` cercano a 9,5 GB.
- Tamaño total de `data/bronze/` ≤ 1,5 GB (SC-005).
- Archivos eliminados, auditoría intacta con URL, hash y motivo.
- Repetir la purga no vuelve a sumar bytes.

## Scenario 9 — Guarda del dominio oficial

Intento de eliminar un artefacto de `manuelita.com`:

```bash
uv run pml curate review decide --artifact 1 --decision remove --reviewer "test"
```

Esperado: exit `4`; la decisión no se aplica y se registra el bloqueo.

## Scenario 10 — Restauración e idempotencia

Antes de la purga:

```bash
uv run pml curate restore --artifact 12345 --json
```

Esperado: archivo devuelto a su ruta original, hash verificado y evaluación manual `keep`; vuelve al corpus
activo.

Repetir `analyze` y `quarantine`:

Esperado: mismas decisiones automáticas, sin duplicar evaluaciones, auditorías ni movimientos.

## Acceptance Map

| Scenario | Requirements | Success criteria |
|----------|--------------|------------------|
| 1 | FR-001, FR-002 | SC-001 |
| 2 | FR-003…FR-009 | SC-002 |
| 3 | FR-008, FR-018 | SC-012 |
| 4 | FR-007, FR-009, FR-017 | SC-011 |
| 5 | FR-013, FR-014 | SC-011 |
| 6 | FR-010, FR-011, FR-014 | SC-006, SC-007 |
| 7 | FR-015 | SC-008 |
| 8 | FR-012, FR-013 | SC-005, SC-010 |
| 9 | FR-004, FR-014 | SC-002 |
| 10 | FR-013, FR-016, FR-017 | SC-010, SC-011 |

## Troubleshooting

- **Exit `3`**: configuración inválida; revisar el JSONL de stderr.
- **Exit `4`**: guarda de dominio oficial o decisión manual `keep`; no forzar.
- **Exit `5`**: revisar la cola antes de aprobar.
- **Exit `6`**: el run no está aprobado o no está en el estado requerido.
- **Exit `7`**: hash distinto al esperado; no restaurar ni purgar ese artefacto y registrar el incidente.
- **Cobertura inesperadamente alta**: revisar que se esté usando `--active-only` y que la cuarentena haya
  excluido los eliminados.
