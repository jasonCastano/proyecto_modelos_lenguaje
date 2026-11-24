# Contrato — Herramientas de planificación (números 21–26)

Extiende `specs/024-module3-openclaw-whatsapp/contracts/tools-catalog.md`. Rigen las mismas invariantes de
`ToolSpec.validate()`:

- nombre `snake_case`;
- descripción de 20 a 300 caracteres;
- esquema Pydantic con `extra="forbid"`;
- `requires_approval ⇔ write`.

Ruta de todas: `planning`. Perfil: `planificador`.

| # | Nombre | Tipo | MCP | Fuente |
|--:|---|---|:-:|---|
| 21 | `get_plant_state` | lectura | sí | `data/synthetic/planificacion/<v>/state.json` + `plant_<id>.json` |
| 22 | `get_commitments` | lectura | sí | `…/commitments.json` |
| 23 | `search_operating_procedures` | lectura | sí | `…/procedures/*.md` (BM25 en memoria) |
| 24 | `simulate_production_scenario` | lectura (cálculo) | **no** | simulador lineal (`agent/planning.py`) |
| 25 | `optimize_production_plan` | lectura (cálculo) | **no** | `scipy.optimize.linprog` (HiGHS) |
| 26 | `save_production_proposal` | escritura (HITL) | no | `$MANUELITA_STATE_DIR/planning/proposals.jsonl` |

## Esquemas de argumentos

```text
GetPlantStateArgs        { plant_id: "cana" = "cana" }
GetCommitmentsArgs       { plant_id: "cana" = "cana", product: "sugar"|"ethanol"|"power"|null }
SearchProceduresArgs     { query: str (3–200) }
SimulateScenarioArgs     { plant_id, cane_available?, cane_delta_pct?, cane_quality?, steam_limit?,
                           sugar_share: float [0,1] (obligatorio) }
OptimizePlanArgs         { plant_id, cane_available?, cane_delta_pct?, cane_quality?, steam_limit?,
                           prioritize: "margin"|"power" = "margin" }
SaveProposalArgs         { plan_id: str (patrón ^p-[0-9a-f]{8}$), note: str (≤ 200) | null }
```

Rangos de validación: los de [data-model.md §3](../data-model.md). Un valor fuera de rango devuelve
`Error de la herramienta: Argumentos inválidos …`, y el agente pide un valor válido.

## Salida (texto para el modelo; JSON estructurado en la traza)

Toda salida empieza con `[Datos sintéticos de demostración · <versión>]`.

- **`get_plant_state`**: semana, caña disponible y calidad, equipos con estado y factor, inventarios y mezcla actual.
- **`get_commitments`**: compromisos con producto, cantidad mínima, prioridad y contraparte genérica.
- **`search_operating_procedures`**: hasta 4 fragmentos `[S#]` con título y procedimiento, neutralizados por
  `guard.neutralize`.
- **`simulate_production_scenario`**: balances, margen y lista de violaciones. Una violación no es un error: se
  reporta.
- **`optimize_production_plan`**: el `plan_card` (data-model §3), seguido de una línea `plan_id: p-xxxxxxxx`.
  - Si el escenario es infactible, `status: infeasible_relaxed` y los faltantes por compromiso.
  - Si el solver falla o pasan más de 5 s, devuelve `Error de la herramienta: no fue posible optimizar …`, sin plan.

## Garantías del turno de planificación (R12)

1. Cada número de la respuesta final aparece en las salidas de herramientas del turno. La comparación se hace sobre
   números normalizados: separadores de miles, coma decimal y redondeos a 0–2 decimales.
2. La respuesta contiene «Datos sintéticos» y «el equipo de planta decide».
3. Si (1) o (2) fallan, la respuesta se reemplaza por el último `plan_card`, y la traza marca
   `planning_guard: replaced`.

## `save_production_proposal`

- Se ofrece solo si hay `last_plan` en el hilo.
- La interrupción de aprobación muestra el resumen del plan («Guardar la propuesta p-… (margen …, azúcar …, etanol …,
  energía …)»).
- Tras «SÍ», escribe la `ProductionProposal`; tras «NO» o al vencer, no escribe nada.
- Si `plan_id` no coincide con `last_plan`, la respuesta es: «Esa propuesta ya no está en esta conversación; vuelve a
  calcularla».

## Calibración de los datos (generador)

- La semana base es factible, con al menos un 10 % de holgura en cada compromiso.
- Con −15 % de caña también es factible, y al menos un compromiso o recurso queda activo.
- La batería incluye 2 escenarios infactibles: −35 % de caña, y vapor limitado combinado con −25 % de caña.
