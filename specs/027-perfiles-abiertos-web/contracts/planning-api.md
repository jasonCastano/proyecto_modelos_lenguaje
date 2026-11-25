# Contrato: `/api/v1/planning` abierto en la web

Este contrato modifica `specs/026-plataforma-web-manuelita/contracts/planning-api.md` solo en lo que se indica.
Las formas de los cuerpos y las respuestas no cambian.

## `GET /api/v1/planning/access`

Se conserva por compatibilidad. Siempre responde 200:

```json
{"authorized": true, "reason": "Planificación abierta en la web. Los datos de planta son sintéticos."}
```

## Rutas que antes exigían el planificador

`GET /state` (incluye los rangos del escenario), `POST /plan`, `POST /compare`, `POST /proposals` (202) y
`POST /proposals/{confirmation_id}` (segundo paso):

| Situación | Antes | Ahora |
|---|---|---|
| Sin `X-User-Id` (`anon`) y sin variables | 403 `planner_forbidden` | 2xx (200; 202 al crear la propuesta), con el mismo cuerpo que recibía un autorizado |
| Con `X-User-Id` válido | 403 si no estaba autorizado | 2xx |
| `X-User-Id` con formato inválido | tratado como `anon` | igual (`anon`) |
| Escenario inválido | 422 `invalid_scenario` | igual |
| Propuesta vencida o desconocida | 404 o 410, como en la spec 026 | igual |

- El código de error `planner_forbidden` desaparece de la API v1.
- Cada llamada sigue dejando una línea en `<state>/planning/console.jsonl`, con el seudónimo (`anon` si no hay),
  el endpoint, el escenario, el `plan_id`, el estado y la duración.
- La propuesta se escribe solo tras el segundo paso (`POST /proposals/{confirmation_id}` con `yes`), como hoy.
