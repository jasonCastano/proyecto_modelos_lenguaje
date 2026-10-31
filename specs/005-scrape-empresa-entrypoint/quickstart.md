# Quickstart — Entrada canónica de scraping

**Feature**: `005-scrape-empresa-entrypoint`
**Fecha**: 2026-10-30

Guía de validación end-to-end para M1-02. Los escenarios manuales usan una campaña desechable con
prefijo `2026-10-m1-02-`. No se ejecuta el corpus completo.

## 1. Requisitos

```bash
uv sync --frozen
uv run ruff check .
uv run pytest -q
```

Resultado esperado: Ruff limpio y todas las pruebas en verde.

## 2. Ayuda y ausencia de argumentos

```bash
uv run python scripts/scrape_empresa.py --help
uv run python scripts/scrape_empresa.py
```

Resultado esperado:

- Salida `0`.
- Ayuda con todas las opciones, valores por defecto y al menos un ejemplo.
- Sin acceso a red.
- Sin campaña creada.

## 3. Dry-run aislado

```bash
uv run python scripts/scrape_empresa.py \
  --campaign 2026-10-m1-02-dry \
  --limit 3 \
  --dry-run \
  --json
```

Resultado esperado:

- `status` del objeto JSON: `completed` o `paused`.
- `effective.dry_run`: `true`.
- `summary.artifacts_stored`: `0`.
- El bronce real no gana campaña, artefactos ni registros.
- El directorio temporal se elimina al terminar.

Verificación:

```bash
uv run python -c "import sqlite3; c=sqlite3.connect('file:data/bronze/_meta/bronze.sqlite3?mode=ro', uri=True); print(c.execute(\"SELECT COUNT(*) FROM campaigns WHERE campaign_id='2026-10-m1-02-dry'\").fetchone()[0]); c.close()"
```

Resultado esperado: `0`.

## 4. Campaña limitada real

```bash
uv run python scripts/scrape_empresa.py \
  --campaign 2026-10-m1-02-smoke \
  --limit 3 \
  --json
```

Resultado esperado:

- `status`: `completed` o `paused`.
- `summary.targets_discovered` > 0.
- `summary.artifacts_stored` <= 3 objetivos procesados.
- `policy` con decisiones `allowed` y, si el sitio lo declara, `disallowed`.
- `duration_seconds` >= 0.
- `exit_code`: `0` o `4`.

Verificación:

```bash
uv run pml campaign status --campaign 2026-10-m1-02-smoke --json
uv run pml verify --campaign 2026-10-m1-02-smoke --sample 3 --json
```

## 5. Reanudación

**Opción manual**: iniciar una campaña con un límite bajo, interrumpirla con `Ctrl+C` y volver a ejecutar
el mismo comando con `--resume`.

```bash
uv run python scripts/scrape_empresa.py --campaign 2026-10-m1-02-resume --limit 5 --json
# Ctrl+C durante la ejecución
uv run python scripts/scrape_empresa.py --campaign 2026-10-m1-02-resume --resume --json
```

Resultado esperado:

- La primera ejecución queda `paused` y devuelve `4`.
- La segunda reporta `mode: resume`, continúa desde el estado y no duplica artefactos.
- Todos los `content_hash` del catálogo siguen siendo únicos.

**Opción automatizada**:

```bash
uv run pytest tests/integration/test_scrape_entrypoint.py -q -k resume
```

## 6. Políticas y fuentes bloqueadas

```bash
uv run python -c "import sqlite3; c=sqlite3.connect('file:data/bronze/_meta/bronze.sqlite3?mode=ro', uri=True); [print(r) for r in c.execute(\"SELECT source_id, decision, reason, COUNT(*) FROM policy_checks WHERE campaign_id='2026-10-m1-02-smoke' GROUP BY source_id, decision, reason\")]; c.close()"
```

Resultado esperado:

- Cada fila tiene `decision` y `reason`.
- Las fuentes bloqueadas por `robots.txt` aparecen como `disallowed` y no tienen artefactos.
- No hay decisiones sin motivo.

## 7. Errores de uso

```bash
uv run python scripts/scrape_empresa.py --campaign ../insegura --json
uv run python scripts/scrape_empresa.py --campaign 2026-10-m1-02-smoke --limit 0 --json
uv run python scripts/scrape_empresa.py --config config/no-existe.toml --campaign 2026-10-m1-02-smoke --json
uv run python scripts/scrape_empresa.py --campaign 2026-10-no-existe --resume --json
```

Resultado esperado en los cuatro casos:

- Código de salida `2`.
- Objeto JSON de error validable contra `contracts/error.schema.json`.
- Mensaje accionable, sin secretos ni rutas absolutas.
- Sin acceso a red y sin crear estado.

## 8. Campaña completada

```bash
uv run python scripts/scrape_empresa.py --campaign 2026-10-m1-02-smoke --json
```

Resultado esperado:

- `mode: already_completed`.
- `status: completed`.
- Código `0`.
- Sin red y sin reejecución.

## 9. Equivalencia con la invocación directa

```bash
uv run python scripts/scrape_empresa.py \
  --campaign 2026-10-m1-02-wrapper \
  --limit 3 \
  --json

uv run pml campaign start \
  --campaign 2026-10-m1-02-direct \
  --max-targets 3 \
  --json
```

Resultado esperado:

- Mismos `targets_discovered`, `artifacts_stored`, `excluded`, `failed` y `bytes_stored` para insumos
  equivalentes.
- Las rutas de reporte y el `campaign_id` difieren, como es esperado.
- Plata y oro no cambian.

## 10. Verificación de capas no modificadas

```bash
git status --short
uv run pytest tests/integration/test_scrape_entrypoint.py -q
```

Resultado esperado:

- `data/` no aparece en Git.
- La prueba de integración compara los hashes de `data/silver` y `data/gold` antes y después.
- Sin cambios en plata u oro.

## 11. Criterios de aceptación

| Escenario | Criterio |
|-----------|----------|
| Ayuda | `--help` y sin argumentos: `0`, ayuda completa, sin red |
| Dry-run | Cero artefactos y cero registros en el bronce real |
| Campaña limitada | No procesa más de `--limit` objetivos |
| Resume | Sin duplicados y sin pérdida de progreso |
| Políticas | Fuentes bloqueadas registradas y no capturadas |
| Errores | Código `2`, JSON válido y mensaje accionable |
| Completada | No se reejecuta; código `0` |
| Equivalencia | Mismas métricas que la invocación directa |
| Capas | Plata y oro sin cambios |

## 12. Limpieza

Las campañas de prueba permanecen en el catálogo por trazabilidad. Usa siempre el prefijo
`2026-10-m1-02-` y no reutilices identificadores. No borres registros del catálogo manualmente.

## 13. Resultados observados (2026-10-30)

| Escenario | Resultado |
|-----------|-----------|
| `--help` | Código `0`; todas las opciones y ejemplos visibles. |
| Sin argumentos | Código `0`; ayuda impresa; sin red ni estado. |
| `--dry-run --campaign 2026-10-m1-02-dry --limit 1 --json` | Código `0`; `status=completed`; `effective.dry_run=true`; `artifacts_stored=0`; `targets_discovered=1`; `policy.allowed=1`; sin campaña nueva en el bronce real. |
| Campaña limitada | Validada con el servidor local de `tests/conftest.py`; no se ejecutó contra el sitio real para evitar una corrida larga de red. |
| Reanudación | Validada en `tests/integration/test_scrape_entrypoint.py`: sin duplicados y sin pérdida de artefactos. |
| Fuente bloqueada | Validada: `disallowed_by_robots` con motivo y cero artefactos de la URL bloqueada. |
| Equivalencia | Métricas idénticas a `campaign_service.start_campaign` con los mismos insumos. |
| Capas | Hashes de `data/silver` y `data/gold` sin cambios. |
| Pruebas | `164 passed`; Ruff limpio; `uv build` genera sdist y wheel. |

**Nota**: el `--dry-run` real tardó 613 s por la latencia y el descubrimiento del sitio. Para demos,
usa un `--config` reducido o el servidor local; el `--limit` acota objetivos, no el descubrimiento.
