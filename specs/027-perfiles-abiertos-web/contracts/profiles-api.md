# Contrato: perfiles en la web

## `GET /api/profiles?user_id=<seudónimo>`

Respuesta 200, con la misma forma de la spec 025. Para cualquier `user_id`, incluido `anon`, y sin variables de
autorización:

```json
[
  {"key": "visitante", "label": "Visitante", "requires_authorization": false, "authorized": true},
  {"key": "cliente", "label": "Cliente B2B", "requires_authorization": false, "authorized": true},
  {"key": "proveedor", "label": "Proveedor cañero", "requires_authorization": false, "authorized": true},
  {"key": "colaborador", "label": "Colaborador", "requires_authorization": false, "authorized": true},
  {"key": "planificador", "label": "Planificador industrial", "requires_authorization": false, "authorized": true}
]
```

Puede haber campos adicionales que ya existan hoy, con los mismos valores.

## `POST /api/chat` y `POST /api/chat/stream` con `profile`

| `profile` | Antes (sin variable) | Ahora |
|---|---|---|
| `"planificador"` | 403 `planner_not_authorized` | 200; el turno corre con el perfil planificador |
| alias («planificación», «planta») | 403 | 200 |
| desconocido | 400 `invalid_profile` | 400 `invalid_profile` (sin cambio) |

## Detección en el mensaje (web)

«Soy planificador de planta…» cambia el perfil del turno a planificador y responde con la nota de cambio de perfil
habitual. `PLANNER_ONLY_NOTE` nunca aparece en la web.

## WhatsApp (regresión, sin cambios)

- `/perfil` lista el planificador con «(solo autorizados)».
- `/perfil planificador` desde un seudónimo fuera de `VALERIA_PLANNERS`, y sin `MANUELITA_PLANNER_OPEN`, responde
  `PLANNER_DENIED_TEXT` con el evento `planner_denied`.
