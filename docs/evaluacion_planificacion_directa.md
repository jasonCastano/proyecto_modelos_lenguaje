# Evaluación del agente de planificación industrial (spec 025, idea 7.4)

**Ejecución**: `planning-direct-20261124T190159Z` · **Modo**: direct · **Fecha**: 2026-11-24T19:01:59+00:00 · **Comando**: `uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct --write-docs`

> Datos **sintéticos** de demostración (`data/synthetic/planificacion/v1`). La batería (`tests/fixtures/agent/planning_scenarios.jsonl`) se fijó antes de evaluar, con el óptimo de referencia calculado por malla (`planning_reference.py`).

- **SC-001**: 10/10 escenarios factibles con margen ≥ 99 % del óptimo de referencia (mínimo 1.000016); violaciones de restricciones duras: **0**; sin solución detectados: **2/2**.
- Tiempo del optimizador p50 / p95: 4 / 4 ms.

Veredicto: ✅ cumple.

| Caso | Factible | Estado / ruta | Detalle |
|---|:-:|---|---|
| p01 | sí | optimal | margen/ref 1.00002 |
| p02 | sí | optimal | margen/ref 1.00004 |
| p03 | sí | optimal | margen/ref 1.00005 |
| p04 | sí | optimal | margen/ref 1.00002 |
| p05 | sí | optimal | margen/ref 1.00005 |
| p06 | sí | optimal | margen/ref 1.00004 |
| p07 | sí | optimal | margen/ref 1.00009 |
| p08 | sí | optimal | margen/ref 1.00048 |
| p09 | sí | optimal | margen/ref 1.00002 |
| p10 | sí | optimal | margen/ref 1.00012 |
| p11 | no | infeasible_relaxed | faltantes reportados |
| p12 | no | infeasible_relaxed | faltantes reportados |
