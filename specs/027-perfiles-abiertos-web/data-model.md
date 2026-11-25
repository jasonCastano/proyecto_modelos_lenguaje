# Data Model: Perfiles abiertos en la web

No hay almacenamiento nuevo. Cambia cómo se calcula la autorización y se añade un dato de presentación.

## Perfil (`config/profiles.toml` → `agent.profiles.Profile`)

| Campo | Tipo | Cambio |
|---|---|---|
| `key` | `visitante \| cliente \| proveedor \| colaborador \| planificador` | — |
| `label` | str | — |
| `tools` | lista blanca del catálogo | — |
| `requires_authorization` | bool (archivo) | **Se interpreta por canal**: solo aplica fuera de la web. En el archivo sigue `true` para el planificador. |
| `requires_authorization_in(channel)` | método nuevo | `requires_authorization and channel != "web"` |

## Regla de autorización (`profiles.is_authorized(user_id, channel)`)

| Canal | Resultado |
|---|---|
| `web` | `True` siempre (**nuevo**) |
| `whatsapp` u otro | `MANUELITA_PLANNER_OPEN=1` → `True`; si no, `user_id in VALERIA_PLANNERS` (sin cambios) |

- `MANUELITA_PLANNER_WEB` deja de leerse.
- `effective_profile`, `validate_profile`, `describe`, `planner_user` (antes `require_planner`) y `/access` usan
  esta regla.

## Opción de perfil (`GET /api/profiles` → `ProfileOption` en la web)

| Campo | En la web, antes | En la web, ahora |
|---|---|---|
| `key`, `label` | — | — |
| `requires_authorization` | `true` para el planificador | `false` para los cinco |
| `authorized` | `false` para el planificador sin variable | `true` para los cinco |

## Tarjeta de público (`web/src/data/profileSuggestions.ts` → `AudienceCard`)

| Campo | Tipo | Cambio |
|---|---|---|
| `forWhom` | string, ≤ 40 caracteres, segunda persona | **nuevo**; textos en [design.md](design.md#copy) |
| `key`, `label`, `glyph`, `canAsk`, `example`, `suggestions` | — | — |

## Perfil activo (`web/src/lib/platform.ts`, `audience`)

| Evento | Transición |
|---|---|
| Elegir en el selector o en la entrada | `audience = key` (cualquiera de los cinco) |
| Abrir `/planificacion` | `audience = "planificador"` (**nuevo**) |
| Escribir «soy planificador» en el chat web | el grafo cambia a planificador (ya no se degrada a visitante) |

## Propuesta de producción (sin cambios)

Se guarda en `proposals.jsonl` con `user_id` seudónimo, `plan_id`, fecha y advertencia de datos sintéticos.
Requiere los dos pasos, vence a los 5 min en la consola (10 min en el chat) y admite como máximo 100 pendientes.
