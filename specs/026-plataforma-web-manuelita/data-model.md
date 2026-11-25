# Data Model: Plataforma web profesional de Valer-IA (spec 026)

**Fecha**: 2026-11-24 · **Autor**: Roberto José Guerrero

Las entidades de planta (`PlantModel`, `PlantState`, `Commitment`, `PlanResult`) ya existen en
`agent/planning.py` (spec 025). Aquí solo se describen los campos que cambian y las entidades nuevas del backend v1
y de la web. Todo lo de planta lleva `synthetic: true`.

## 1. Scenario (extiende la spec 025)

| Campo | Tipo | Regla |
|---|---|---|
| `plant_id` | `"cana"` | Fijo mientras la palma está fuera de alcance |
| `cane_delta_pct` | número o nulo | De −50 a +50 (−15 significa 15 % menos caña) |
| `cane_available` | número o nulo | Mayor o igual a 0; si llega junto con `cane_delta_pct`, el delta se aplica sobre él |
| `cane_quality` | número o nulo | De 9 a 16 (pol %) |
| `steam_limit` | número o nulo | Mayor o igual a 0 (t/semana); solo puede **bajar** la capacidad de caldera, nunca subirla |
| `prioritize` | `"margin"` o `"power"` | Por defecto `"margin"` |
| **`price_sugar_pct`** (nuevo) | número o nulo | De −50 a +50, cambio porcentual sobre `PlantModel.price_sugar` |
| **`price_ethanol_pct`** (nuevo) | número o nulo | De −50 a +50 |
| **`price_power_pct`** (nuevo) | número o nulo | De −50 a +50 |

Otras reglas:

- Rechaza campos extra (`extra="forbid"`).
- Con los tres precios en `None`, `optimize()` devuelve exactamente el mismo `PlanResult` que en la spec 025; una
  prueba de regresión cubre los 12 escenarios de la batería.
- `plan_id_for` incluye los campos nuevos (vía `model_dump`). Un escenario con precios distintos tiene otro
  `plan_id`, y uno sin precios conserva el suyo.

## 2. PlanResult (sin cambios de forma)

`to_dict(card=True)` es el contrato de salida de la consola:

- `plan_id`;
- `status`: `optimal` o `infeasible_relaxed`;
- `scenario` y `resolved`;
- `mix` (t de caña por destino) y `products`;
- `margin`;
- `binding` y `sensitivity`;
- `shortfalls`;
- `alternatives` y `assumptions`;
- `week` y `data_version`;
- `synthetic: true`;
- `plan_card`.

La web **no recalcula** ninguno de estos campos. Solo los dibuja.

## 3. PlantSnapshot (nuevo, de lectura)

Es la vista del estado de planta para la consola. Se construye desde `PlantData`:

| Campo | Origen |
|---|---|
| `week`, `data_version`, `seed` | `PlantState.week`, `PlantData.version`, `PlantData.seed` |
| `cane_available`, `cane_quality` | `PlantState` |
| `capacities` | Lista con `area` (molino, destilería, caldera o turbogenerador), `nominal`, `factor`, `effective` y `unit` |
| `equipment` | Lista con `id`, `kind`, `status` y `capacity_factor` |
| `inventories` | `PlantState.inventories` |
| `current_mix` | `PlantState.current_mix` |
| `commitments` | Lista con `id`, `product`, `min_quantity`, `unit`, `priority` y `counterparty`; la contraparte es ficticia, porque los datos son sintéticos |
| `prices` | Precios de referencia de azúcar, etanol y energía |
| `ranges` | Límites válidos de cada control del escenario, tomados del esquema de `Scenario` para que la UI no los duplique |
| `synthetic` | `true` |

## 4. PlanComparison (nuevo)

Es el resultado de `planning.compare(base, scenario)`:

| Campo | Contenido |
|---|---|
| `base` y `scenario` | Dos `PlanResult.to_dict()` |
| `mix_delta` | Por destino: diferencia en toneladas y en puntos porcentuales |
| `products_delta` | Por producto: diferencia absoluta y su unidad |
| `commitments` | Por compromiso: `met_base`, `met_scenario`, `gap_base`, `gap_scenario` |
| `margin_delta` | Diferencia de margen |
| `synthetic` | `true` |

## 5. PendingProposal (nuevo, en memoria del proceso)

| Campo | Regla |
|---|---|
| `confirmation_id` | Token aleatorio de 128 bits (`secrets.token_urlsafe`) |
| `plan_id` | Del plan recalculado en el servidor |
| `plan` | `PlanResult.to_dict(card=False)` recalculado; **nunca** viene del cliente |
| `scenario` | Escenario validado |
| `user` | Seudónimo de sesión web |
| `note` | Texto opcional de hasta 280 caracteres, redactado con `redact_pii` |
| `created_at`, `expires_at` | La propuesta vence a los 5 minutos |

Transiciones de estado:

```text
pending ──"yes"──▶ saved      (actions.save_proposal → planning/proposals.jsonl)
pending ──"no"───▶ discarded  (solo se registra en console.jsonl)
pending ──vence──▶ expired    (al confirmar responde 410 proposal_expired)
```

Puede haber 100 pendientes como máximo. Al pasar el tope se descarta la más antigua. Confirmar dos veces la misma
propuesta responde 404, `proposal_not_found`.

## 6. ConsoleEvent (nuevo, registro)

Es una línea de `planning/console.jsonl` en el directorio de estado:

```text
{ts, endpoint, user, scenario, plan_id, status, duration_ms, synthetic: true}
```

No guarda IP, cabeceras ni texto libre sin redactar.

## 7. Entidades de evidencia (nuevas, de lectura)

- **ToolEvidence**: tiene estos campos:
  - `name`, `description`, `kind` (`read` o `write`) y `requires_approval`;
  - `routes`;
  - `profiles`, los perfiles cuya lista blanca la incluye;
  - `mcp_allowed`.

  Hay 26 en total.
- **TurnTrace**: tiene estos campos:
  - `thread_id`, `turn` y `profile`;
  - `route` y `plan_steps`;
  - `tools`, una lista con `name`, `args` (validados y redactados), `ok`, `duration_ms`, `summary` y `step`;
  - `duration_ms` del turno.
- **ServiceStatus**: tiene estos campos:
  - `id`: `model`, `qdrant`, `whatsapp`, `gateway`, `voice` o `stt`;
  - `label`;
  - `status`: `up`, `down`, `degraded` o `unknown`;
  - `reason`;
  - `action`, lo que debe hacer el equipo;
  - `checked_at`.
- **PublishedEvaluation**: tiene estos campos:
  - `id` y `name`;
  - `value` (texto con su unidad, por ejemplo «86,0 % y 90,7 %»);
  - `target`;
  - `meets`: `true`, `false` o `partial`;
  - `date` (ISO);
  - `report` (ruta en `docs/`);
  - `note`.

  Vive en `config/evaluations.toml`, que es versionado.

## 8. Estado de la web (cliente)

| Estado | Dónde vive | Regla |
|---|---|---|
| Ruta actual | `lib/router.ts` (History API) | `/`, `/agente`, `/planificacion` o `/evidencia`; las demás van a `/` |
| Perfil activo | `sessionStorage` y la preferencia `audience` del servidor (spec 025) | El planificador solo si `access.authorized` |
| Hilo | `lib/session.ts`, como hoy | Se conserva al cambiar de perfil y de área |
| Escenario y último plan | Estado del componente de la consola | No se persiste: el plan siempre se recalcula en el servidor |
