# Ficha de datos — planificación industrial SINTÉTICA (v1)

- **Naturaleza**: datos **sintéticos** generados por
  `scripts/generate_planning_data.py --seed 2026 --version v1`. No describen la
  operación, los contratos, los precios ni las capacidades reales de Manuelita.
- **Uso permitido**: demostrar el agente de planificación industrial de la plataforma
  (spec 025, idea 7.4) y evaluarlo con `tests/fixtures/agent/planning_scenarios.jsonl`.
- **Uso prohibido**: citarlos como datos de Manuelita, mezclarlos con el corpus público
  (capa oro) o tomar decisiones reales con ellos (constitución 2.0.0, regla 18).
- **Contenido**: `plant_cana.json` (capacidades, rendimientos, precios y costos),
  `state.json` (semana 2026-W48, caña disponible, calidad, equipos, inventarios y mezcla
  actual), `commitments.json` (compromisos semanales con contrapartes genéricas) y
  `procedures/` (10 procedimientos operativos citables como `[S#]`).
- **Anclaje de magnitud**: la cogeneración pública de Manuelita (≈ 200.000 MWh/año; Informe
  de Sostenibilidad 2023-2024, p. 57 y 124) orienta el orden de magnitud semanal de la
  energía. Los demás valores son plausibles para un ingenio mediano y se perturban ±3 %.
- **Calibración**: compromisos = 97 % de la producción con 85 % de la caña a azúcar y
  15 % menos de caña.
- **Reproducibilidad**: `--check` falla si regenerar cambiaría algún byte.
- **Datos personales**: ninguno.
