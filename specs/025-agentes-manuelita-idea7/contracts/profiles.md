# Contrato — Perfiles: comandos, API y autorización

## Perfiles y herramientas

| Perfil | Herramientas de lectura ofrecidas (∩ ruta) | Notas |
|---|---|---|
| `visitante` | Las 15 de lectura de la spec 024 | Conducta actual; batería de herramientas sin cambios |
| `cliente` | `search_documents`, `list_company_entities`, `list_business_units`, `faq_lookup`, `get_official_channels`, `get_fragment`, `summarize_topic` | Cotización → `request_human_contact` con «SÍ»; nunca precios |
| `proveedor` | `search_documents`, `sustainability_lookup`, `faq_lookup`, `get_official_channels`, `get_fragment`, `summarize_topic` | Aclara que no reemplaza la asistencia técnica de campo |
| `colaborador` | `search_documents`, `faq_lookup`, `get_official_channels`, `get_fragment`, `summarize_topic`, `latest_news` | PTEE, línea ética, SST públicos |
| `planificador` | Las anteriores de `visitante` + 21–25 | Ruta `planning` solo para este perfil; requiere autorización |

Las cinco herramientas de escritura de la spec 024 se ofrecen en todos los perfiles. `save_production_proposal` se
ofrece solo en `planificador`. `calculate` y `get_my_profile` siguen disponibles en todos los perfiles según su ruta.

## WhatsApp (`channels/bridge.py`)

| Mensaje | Efecto | Respuesta |
|---|---|---|
| `/perfil` | Lista los perfiles y marca el activo | Lista de cinco líneas |
| `/perfil <key>` | Activa el perfil en el hilo (sin escritura persistente) | «Listo: ahora te atiendo como <label>. ¿Quieres que lo recuerde para próximas conversaciones?» |
| `/perfil planificador` (no autorizado) | Se niega; registra `planner_denied` | «La planificación industrial es solo para planificadores autorizados. Sigo como visitante.» |
| `/ayuda` | Suma la línea de `/perfil` | |

Los alias aceptados para `<key>` son los nombres sin tildes y sin mayúsculas, más `b2b` para `cliente`.

## Web y API

`POST /api/chat` añade un campo opcional:

```json
{"message": "…", "variant": "agent", "profile": "planificador"}
```

| Caso | Respuesta |
|---|---|
| `profile` inválido | 400 `invalid_profile` |
| `planificador` no autorizado | 403 `planner_not_authorized` |

`GET /api/profiles` devuelve `[{key, label, requires_authorization, authorized}]` para el usuario. La vista técnica
(`ChatView.tsx`) muestra un selector y un chip del perfil activo, y la traza muestra `profile`.

## Autorización (R14)

`is_authorized(user_id, channel)` es verdadero si se cumple alguna de estas condiciones:

- `user_id ∈ VALERIA_PLANNERS`;
- `MANUELITA_PLANNER_OPEN=1`;
- `channel == "web"` y `MANUELITA_PLANNER_WEB=1`.

Las variables viven en `.env` y se documentan vacías en `.env.example`.

## Traza

`Turn.profile`, `turns.jsonl.profile` y `/traza` (`Perfil: <label>`). `channels.jsonl` registra
`event: "planner_denied"` sin número ni texto.
