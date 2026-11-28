# Data Model: Saludo y presentación al iniciar una conversación (spec 032)

Todo vive en `<estado>/channels.sqlite3` (fuera del repositorio) y en el registro `logs/channels.jsonl`. No hay
números ni texto de mensajes.

## Hilo del canal (`channel_threads`, columna nueva)

| Campo | Tipo | Regla |
|---|---|---|
| `introduced` | `INTEGER NOT NULL DEFAULT 1` | `0` al crear un hilo (`ensure_user`, `new_thread`, inactividad); `1` cuando una respuesta atendida lleva la presentación (del bridge o del modelo). Los hilos anteriores a la migración quedan en `1`. |

**Transiciones**:

```text
[sin usuario] --primer mensaje--> hilo(introduced=0, motivo=first_contact)
hilo(introduced=0) --respuesta atendida--> hilo(introduced=1)
hilo(introduced=0) --error / atajo / aviso--> hilo(introduced=0)      (sin cambio)
hilo(cualquiera) --mensaje tras > conversation_idle_hours--> hilo nuevo(introduced=0, motivo=inactivity)
hilo(cualquiera) --«empecemos de nuevo»--> hilo nuevo(introduced=0, motivo=restart)
```

## Usuario del canal (`channel_users`, sin cambios de esquema)

- `last_seen` se lee **antes** de actualizarlo para decidir la inactividad.
- `active_thread_id` apunta al hilo nuevo cuando hay inactividad.

## Configuración (`[channels]` en `config/agent.toml`)

| Clave | Tipo | Defecto | Validación |
|---|---|---|---|
| `conversation_idle_hours` | int | 12 | 1 ≤ valor ≤ 720 |

## Presentación (`channels/greeting.py`, sin persistencia)

| Atributo | Regla |
|---|---|
| idioma | `es` o `en`, el del turno (spec 029) |
| variante | `hash(thread_id) % 3`, estable por hilo |
| nombre | el que reconoce el servicio (`client.name`), si existe; nunca el número |
| longitud | ≤ 2 frases; siempre menciona «Valer-IA», Manuelita y que acepta notas de voz |
| origen | `bridge` (antepuesta) o `agent` (la respuesta ya se presentaba) |

## Registro del canal (`ChannelLogRecord`, campos nuevos)

| Campo | Valores | Uso |
|---|---|---|
| `conversation_start` | `first_contact`, `inactivity`, `restart`, `null` | motivo por el que el hilo de este turno empezó (solo en el turno que lo abre) |
| `introduced` | `bridge`, `agent`, `null` | si esta respuesta llevó la presentación y quién la puso (SC-001, SC-003) |
