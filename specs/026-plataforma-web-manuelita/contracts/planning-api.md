# Contrato: API v1 de planificación (`/api/v1/planning`)

**Router**: `src/proyecto_modelos_lenguaje/api_planning.py` · **Spec**: FR-011 a FR-019, FR-025 a FR-028

## Reglas comunes

- **Autorización**: todos los endpoints, salvo `GET /access`, exigen el perfil planificador autorizado en el canal
  web (`profiles.is_authorized`, R5). Sin autorización responden **403** y no devuelven ningún dato de planta.
- **Sobre de error**: `{"error": {"code": "<estable>", "message": "<qué pasó y qué hacer, en español>"}}`. Nunca
  trae trazas, rutas internas ni secretos.
- **Validación**: los cuerpos se validan con Pydantic (`extra="forbid"`). Un cuerpo inválido responde **422** con
  código `invalid_scenario` y lista los campos y rangos válidos.
- **Identidad**: el usuario es el mismo `user_id` anónimo que usa el chat (`^[A-Za-z0-9-]{1,64}$`). Viaja en la
  cabecera `X-User-Id`; si falta, se usa `anon`. No se piden datos personales.
- **Registro**: cada llamada añade un `ConsoleEvent` (data-model §6).
- **Datos sintéticos**: toda respuesta con datos de planta lleva `"synthetic": true` y
  `"label": "Datos sintéticos de demostración"`.

| Código | HTTP | Cuándo |
|---|---|---|
| `planner_forbidden` | 403 | La persona no está autorizada como planificadora |
| `invalid_scenario` | 422 | Un campo está fuera de rango o sobra |
| `plant_data_missing` | 503 | No están los datos sintéticos. El mensaje indica `uv run python scripts/generate_planning_data.py` |
| `proposal_not_found` | 404 | El `confirmation_id` no existe o ya se usó |
| `proposal_expired` | 410 | Pasaron más de 5 minutos |
| `planning_failed` | 500 | Error inesperado del optimizador. Se registra sin detalles en la respuesta |

## `GET /api/v1/planning/access`

Responde 200 a cualquiera:

```json
{ "authorized": true, "reason": "Planificación habilitada en la web para esta jornada." }
```

Si no está autorizado, `authorized` es `false` y `reason` explica que la planificación es solo para el equipo de
planta autorizado.

## `GET /api/v1/planning/state`

Responde 200 con un `PlantSnapshot` (data-model §3), incluidos los `ranges` de cada control del escenario.

## `POST /api/v1/planning/plan`

El cuerpo es un `Scenario` (data-model §1). Todos los campos son opcionales:

```json
{ "cane_delta_pct": -15, "price_ethanol_pct": 10, "prioritize": "margin" }
```

Responde 200 con `PlanResult.to_dict(card=True)`, más `label` y `decision_phrase`. Si no hay solución factible
(`status = "infeasible_relaxed"`), sigue respondiendo 200 y `shortfalls` trae el faltante de cada compromiso. La UI
no dibuja el flujo como factible.

## `POST /api/v1/planning/compare`

El cuerpo es un `Scenario`. Responde 200 con un `PlanComparison` (data-model §4), cuyo `base` es el plan del
escenario vacío.

## `POST /api/v1/planning/proposals`

El cuerpo lleva el escenario y una nota opcional:

```json
{ "scenario": { "cane_delta_pct": -15 }, "note": "Revisar con molienda" }
```

Responde **202**:

```json
{
  "confirmation_id": "…",
  "plan_id": "…",
  "summary": "Azúcar 54 %, etanol 31 %, energía 15 %; margen …",
  "expires_at": "2026-11-28T15:05:00Z",
  "question": "¿Guardar esta propuesta para revisión del equipo de planta?"
}
```

Este paso **no guarda nada**.

## `POST /api/v1/planning/proposals/{confirmation_id}`

El cuerpo es `{ "decision": "yes" }` o `{ "decision": "no" }`.

- Con `yes` responde 200 y guarda con `actions.save_proposal`:

  ```json
  { "status": "saved", "plan_id": "…", "message": "Propuesta guardada. El agente recomienda; el equipo de planta decide." }
  ```

- Con `no` responde 200 y no escribe nada en `proposals.jsonl`:

  ```json
  { "status": "discarded", "message": "Propuesta descartada. No se guardó nada." }
  ```

## Pruebas de contrato

Viven en `tests/api/test_planning_api.py` y cubren:

- los 403 de cada endpoint sin autorización;
- los 422 por rango;
- la paridad con la herramienta en un escenario;
- el flujo `yes`, `no`, vencido y repetido;
- que `proposals.jsonl` solo crece tras `yes`;
- que `console.jsonl` no contiene IP ni texto sin redactar.
