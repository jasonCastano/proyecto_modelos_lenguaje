# Data Model — Spec 025

**Fecha**: 2026-11-24 | **Spec**: [spec.md](spec.md) | **Decisiones**: [research.md](research.md)

## 1. Perfil (`config/profiles.toml`, `prompts/profiles.md`)

| Campo | Tipo | Regla |
|---|---|---|
| `key` | `visitante` \| `cliente` \| `proveedor` \| `colaborador` \| `planificador` | Única; `visitante` es el perfil por defecto |
| `label` | str (3–40) | Texto que ven el usuario y la traza |
| `tools` | lista de nombres del catálogo | Cada nombre existe en `catalog()`. Para `visitante`, es exactamente el catálogo de la spec 024 (20) |
| `requires_authorization` | bool | `true` solo para `planificador` |
| `triggers` | lista de patrones (regex sin mayúsculas ni tildes) | Autopresentación que hace proponer el perfil; puede estar vacía |
| foco (sección `## <key>` de `prompts/profiles.md`) | texto | Se añade al system prompt; versionado en `prompt_log.md` |

**Estado del perfil**:

- **Por hilo**: `ChatState.profile`. Lo fija `/perfil`, el selector de la web o la preferencia guardada al abrir el
  hilo.
- **Persistente**: la preferencia `audience` en `("users", id, "preferences")`. Solo se guarda con aprobación y se
  borra con `/olvidar`.

```text
(sin perfil) ──/perfil x o preferencia──▶ activo(x)
activo(x) ──/perfil y──▶ activo(y)
activo(x) ──/olvidar──▶ activo(x) solo en este hilo; la preferencia se borra
x = planificador y no autorizado ──▶ rechazo y activo(visitante)
```

## 2. Datos sintéticos de planta (`data/synthetic/planificacion/<versión>/`)

Todos los archivos llevan `synthetic: true`, `seed` y `version`.

**`plant_cana.json`**: `PlantModel`

| Campo | Unidad | Ejemplo de orden de magnitud |
|---|---|---|
| `mill_capacity` | t caña/semana | 60.000 |
| `distillery_capacity` | L etanol/semana | 2.000.000 |
| `boiler_capacity` | t vapor/semana | 40.000 |
| `turbine_capacity` | MWh/semana | 4.000 |
| `quality_ref` | pol % de referencia | 13,0 |
| `sugar_yield` | t azúcar / t caña (a calidad de referencia) | 0,115 |
| `molasses_yield` | t miel / t caña en la línea de azúcar | 0,035 |
| `ethanol_from_molasses` | L / t miel | 280 |
| `ethanol_from_juice` | L / t caña (a calidad de referencia) | 80 |
| `bagasse_yield` | t bagazo / t caña | 0,28 |
| `steam_per_bagasse` | t vapor / t bagazo | 2,2 |
| `steam_sugar` | t vapor / t caña en la línea de azúcar | 0,50 |
| `steam_ethanol` | t vapor / L etanol | 0,003 |
| `power_per_steam` | MWh / t vapor | 0,095 |
| `power_use` | MWh / t caña molida | 0,03 |
| `price_sugar`, `price_ethanol`, `price_power` | COP por t, L y MWh | márgenes netos sintéticos |
| `cost_cane` | COP / t caña | costo variable |
| `sources` | lista de citas públicas | Anclajes de magnitud (IS 2023-2024, p. 57 y 124) |

**`state.json`**: `PlantState`

| Campo | Regla |
|---|---|
| `week` | ISO (`2026-W48`) |
| `cane_available` | t ≥ 0 |
| `cane_quality` | pol %, en [9, 16] |
| `equipment` | lista de `{id, kind, status: "ok" \| "degradado" \| "fuera", capacity_factor ∈ [0, 1]}` |
| `inventories` | azúcar (t), etanol (L), miel (t) |
| `current_mix` | `x_s`, `x_e` actuales (para comparar alternativas) |

El `capacity_factor` de un equipo multiplica la capacidad del recurso que limita. Por ejemplo, una caldera
degradada reduce `boiler_capacity`.

**`commitments.json`**: lista de `Commitment`

| Campo | Regla |
|---|---|
| `id` | `c-azucar-1`, … |
| `product` | `sugar` \| `ethanol` \| `power` |
| `min_quantity` | t, L o MWh por semana, ≥ 0 |
| `priority` | 1 (máxima) a 3; pondera el faltante en el LP elástico |
| `counterparty` | genérico («Cliente industrial A»), nunca un nombre real |

**`procedures/*.md`**: procedimientos operativos sintéticos (frontmatter `id`, `title`, `synthetic: true`). Se citan
`[S#]`.

## 3. Escenario y resultados (herramientas)

**`Scenario`** (entrada del simulador y del optimizador; esquema Pydantic `extra="forbid"`):

| Campo | Tipo | Regla |
|---|---|---|
| `plant_id` | `"cana"` (y `"palma"` en P3) | |
| `cane_available` | float \| null | ≥ 0; null usa `state.json` |
| `cane_delta_pct` | float \| null | En [-50, 50]; alternativa relativa a la caña disponible |
| `cane_quality` | float \| null | En [9, 16] |
| `steam_limit` | float \| null | ≥ 0; restricción adicional de vapor |
| `sugar_share` | float \| null | En [0, 1]; solo para el simulador (reparto fijo) |
| `prioritize` | `"margin"` \| `"power"` | Por defecto, `margin` |

**`SimulationResult`**: balances (azúcar, etanol, bagazo, vapor generado y demandado, energía generada, consumida y
exportada), `margin`, `violations` (lista de `{constraint, excess, unit}`), `data_version`.

**`PlanResult`**:

| Campo | Contenido |
|---|---|
| `plan_id` | Hash corto del escenario y la versión de datos |
| `status` | `optimal` \| `infeasible_relaxed` |
| `mix` | `x_s`, `x_e`, `b`, `v`, `g` |
| `products` | Azúcar, etanol y energía exportada |
| `margin` | COP |
| `binding` | Restricción limitante, con su dual y su unidad |
| `sensitivity` | Lista de `{constraint, dual, unit}` activas |
| `shortfalls` | Solo si `infeasible_relaxed`: `{commitment_id, missing, unit}` |
| `alternatives` | Lista de `{name, margin, products, delta_vs_best}` |
| `assumptions` | Lista de textos |
| `plan_card` | Texto renderizado en código |
| `data_version`, `synthetic: true` | |

**`ProductionProposal`** (`$MANUELITA_STATE_DIR/planning/proposals.jsonl`): `plan_id`, `user_id` (seudónimo),
`created_at`, `note` (≤ 200), `plan` (el `PlanResult` sin `plan_card`), `approved_by: "user"`.

## 4. Modelo lineal de la planta de caña (R6)

Variables ≥ 0: `x_s`, `x_e` (t caña), `b` (t bagazo), `v` (t vapor), `g` (MWh exportados). Factor de calidad
`k = cane_quality / quality_ref`.

```text
azúcar  S = sugar_yield · k · x_s
etanol  E = ethanol_from_molasses · molasses_yield · x_s + ethanol_from_juice · k · x_e

max  price_sugar·S + price_ethanol·E + price_power·g − cost_cane·(x_s + x_e)

s.a. x_s + x_e ≤ min(cane_available, mill_capacity · f_molino)          [caña y molienda]
     E ≤ distillery_capacity · f_destilería                              [destilería]
     b ≤ bagasse_yield · (x_s + x_e)                                     [bagazo]
     v ≤ steam_per_bagasse · b                                           [vapor por bagazo]
     v ≤ min(boiler_capacity · f_caldera, steam_limit)                   [caldera]
     v ≥ steam_sugar · x_s + steam_ethanol · E                           [demanda de vapor]
     g + power_use · (x_s + x_e) ≤ power_per_steam · v                   [balance eléctrico]
     g + power_use · (x_s + x_e) ≤ turbine_capacity · f_turbo            [turbogenerador]
     S ≥ Σ min_quantity(sugar);  E ≥ Σ min_quantity(ethanol);  g ≥ Σ min_quantity(power)
```

Sin solución factible (R8), las tres últimas restricciones se reemplazan por `S + d_s ≥ …` (y lo mismo para `E` y
`g`), con `d ≥ 0` y una penalización `10³ · precio_unitario · prioridad⁻¹ · d` en el objetivo (R8).

## 5. Baterías de evaluación

**`tests/fixtures/agent/planning_scenarios.jsonl`** (12 líneas, generadas con semilla):

```json
{"id": "p01", "question": "…", "scenario": {"cane_delta_pct": -15}, "feasible": true,
 "reference_margin": 1.234e9, "reference_mix": {"x_s": 0, "x_e": 0}, "grid_step": 0.0005}
```

**`tests/fixtures/agent/profile_routing.jsonl`** (20 líneas, al menos 4 por perfil):

```json
{"id": "r01", "question": "Soy proveedor de caña, ¿qué apoyo técnico dan?", "expected_profile": "proveedor",
 "expected_tools_subset": ["search_documents", "sustainability_lookup"]}
```

## 6. Cambios a entidades existentes

| Entidad | Cambio |
|---|---|
| `Route` (`models.py`, `api_models.py`, `types.ts`) | Se añade `"planning"` |
| `ToolSpec` (`catalog.py`) | Nuevo campo `mcp_allowed: bool = True`; `mcp = kind == "read" and mcp_allowed` |
| `ChatState` (`graph.py`) | Nuevos campos `profile: str` y `last_plan: dict \| None` |
| `Turn`, `turns.jsonl` | Nuevo campo `profile` |
| `PREFERENCE_KEYS` (`memory.py`), `SavePreferenceArgs` | Se añade `audience` |
| `ChatRequest` (`api_models.py`) | Nuevo campo opcional `profile` |
| `WRITE_TOOLS` (`actions.py`) | Se añade `save_production_proposal` (número 26) |
