# Evaluación del agente de planificación industrial (spec 025, idea 7.4)

**Ejecución**: `planning-real-20261124T190134Z` · **Modo**: agente · **Fecha**: 2026-11-24T19:01:34+00:00 · **Comando**: `uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode real --write-docs`

> Datos **sintéticos** de demostración (`data/synthetic/planificacion/v1`). La batería (`tests/fixtures/agent/planning_scenarios.jsonl`) se fijó antes de evaluar, con el óptimo de referencia calculado por malla (`planning_reference.py`).

- Ruta `planning`: 12/12.
- **SC-002**: secuencia estado/compromisos → optimizar en **12/12** (meta ≥ 10); etiqueta sintética y decisión humana en **12/12** (meta 12).
- **SC-004**: latencia p50 / p95 5993 / **10785** ms (meta p95 ≤ 20000 ms); errores: 0.

Veredicto: ✅ cumple.

| Caso | Factible | Estado / ruta | Detalle |
|---|:-:|---|---|
| p01 | sí | planning | get_plant_state, get_commitments, optimize_production_plan, search_operating_procedures |
| p02 | sí | planning | get_plant_state, get_commitments, search_operating_procedures, optimize_production_plan |
| p03 | sí | planning | get_plant_state, get_commitments, optimize_production_plan |
| p04 | sí | planning | get_plant_state, get_commitments, optimize_production_plan |
| p05 | sí | planning | get_commitments, get_plant_state, optimize_production_plan |
| p06 | sí | planning | get_commitments, get_plant_state, optimize_production_plan |
| p07 | sí | planning | get_plant_state, get_commitments, optimize_production_plan |
| p08 | sí | planning | get_plant_state, get_commitments, optimize_production_plan, search_operating_procedures |
| p09 | sí | planning | get_plant_state, get_commitments, optimize_production_plan |
| p10 | sí | planning | get_plant_state, get_commitments, optimize_production_plan, search_operating_procedures |
| p11 | no | planning | get_commitments, get_plant_state, optimize_production_plan |
| p12 | no | planning | get_plant_state, get_commitments, optimize_production_plan |
