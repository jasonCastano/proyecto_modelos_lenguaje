# Contrato — Comandos

| Comando | Qué hace | Salida |
|---|---|---|
| `uv run python scripts/generate_planning_data.py --seed 2026 --version v1 [--check]` | Genera o verifica los datos sintéticos (idempotente; `--check` falla si regenerar cambiaría algún byte) | `data/synthetic/planificacion/v1/` |
| `uv run python scripts/generate_planning_battery.py --seed 2026` | Genera los 12 escenarios con su óptimo de referencia por malla (R9) | `tests/fixtures/agent/planning_scenarios.jsonl` |
| `uv run python -m proyecto_modelos_lenguaje.agent planning --scenario '{"cane_delta_pct": -15}' [--json]` | Optimiza sin LLM e imprime el `plan_card` | stdout |
| `uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct\|real [--write-docs]` | SC-001 (`direct`) y SC-002/SC-004 (`real`, DeepSeek) | `docs/evaluacion_planificacion.{md,json}` |
| `uv run python -m proyecto_modelos_lenguaje.agent profiles-eval --mode demo\|real [--write-docs]` | SC-003 | `docs/evaluacion_perfiles.{md,json}` |
| `uv run python -m proyecto_modelos_lenguaje.agent tools --json` | Catálogo de 26 herramientas | stdout |
| `uv run pml channels simulate --profile planificador "…"` | Ensayo del canal sin teléfono | stdout |

Códigos de salida: 0 si cumple la meta; 1 si no la cumple; 2 si hay un error de datos o de configuración.
