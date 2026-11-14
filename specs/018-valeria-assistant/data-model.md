# Data Model: Valer-IA Caña (spec 018)

## EmailFingerprint (`identity.py`)

| Campo | Regla |
|-------|-------|
| `normalized` | `email.strip().casefold()`; validado con el detector de correo de `privacy.py`. **Solo vive en memoria durante el turno.** |
| `fingerprint` | `hex(HMAC-SHA256(key, normalized))`, 64 caracteres. Es lo único que se guarda o se pasa al grafo. |
| `masked` | `a***@ejemplo.com`: primera letra, `***` y el dominio. Solo se muestra al propio visitante, en la respuesta del turno en que lo escribe. |

**Clave**:
- se toma de `MANUELITA_IDENTITY_KEY`, con un mínimo de 32 caracteres;
- si falta, se genera con `secrets.token_hex(32)` en `MANUELITA_STATE_DIR/identity.key` (permisos del usuario) y se
  reutiliza;
- si la clave cambia, los vínculos previos dejan de reconocerse; queda documentado.

## IdentityLink (Store, namespace `("identities",)`, key = `fingerprint`)

| Campo | Tipo | Regla |
|-------|------|-------|
| `user_id` | str | Cliente al que pertenece; patrón `^[A-Za-z0-9-]{1,64}$`. |
| `created_at` | ISO-8601 | |

- Una huella apunta a un solo cliente.
- Al olvidar (`forget_memory` aprobado), se borran todos los vínculos de ese `user_id`.

## IdentityFailures (Store, namespace `("identity_failures", fingerprint)`)

- Una entrada por fallo, con `at`.
- Si hay 5 o más fallos en la última hora, la huella queda bloqueada para el reconocimiento: se responde como si no
  existiera.

## Estado del hilo (`ChatState`, campos nuevos)

| Campo | Tipo | Uso |
|-------|------|-----|
| `identity` | `{stage, fingerprint?, attempts, offered, recognized_name?}` | Máquina de estados de [contracts/identity-flow.md](./contracts/identity-flow.md). `stage` ∈ `none \| awaiting_name_confirm \| awaiting_name_new \| recognized`. |
| `identity_event` | dict \| None | Lo calcula el servicio antes de redactar: `{kind: "email" \| "reset" \| "name_reply", fingerprint?, registered?, locked?}`. Solo vive durante un turno. |
| `pii_notice` | list[str] | Categorías redactadas en el mensaje del turno: `card`, `document`, `phone` o `email_in_text`. |
| `client` | `{user_id, recognized, name?}` | Resultado para la respuesta HTTP: el navegador adopta `user_id` si cambia. |

`user_id` del hilo **puede cambiar** dentro del mismo hilo cuando se reconoce al cliente (antes era fijo).

## RouteDecision (cambio compatible)

`scope_reason: Literal["off_topic", "abuse", "harmful", "third_party", "prompt_extraction", "advice", "identity"]
| None`:
- tiene valor solo si `route == "out_of_scope"`;
- en el caso `identity`, la ruta es `direct` y el nodo `identify` atiende.

## RememberClientArgs (acción HITL `remember_client`)

| Campo | Regla |
|-------|-------|
| `name` | 1 a 80 caracteres, con datos personales redactados; se guarda como `profile.name`. |
| `fingerprint` | No lo propone el modelo: el servidor lo toma del estado del hilo. |

Al aprobarla se guarda el nombre en el perfil y se crea el `IdentityLink`. Si se rechaza, no se guarda nada.

## Welcome (`prompts/welcome.md`, `GET /api/welcome`)

| Campo | Regla |
|-------|-------|
| `version` | `1.0`; se registra en `prompt_log.md`. |
| `text` | Presentación de Valer-IA, Manuelita en 2 o 3 frases, nota de transparencia e invitación; menos de 700 caracteres. |
| `citations` | Unidades del oro `[U#]` → `unit_id` y `url`; una prueba verifica que existen y contienen los datos citados. |

## ConductCase (`tests/fixtures/conduct/conduct_cases.jsonl`)

`{id, category, message, setup?: {registered_email?, registered_name?}, expected_reason?, must_contain_any: [..],
must_not_contain: [..]}`

Las categorías son: `off_topic`, `third_party`, `prompt_extraction`, `abuse`, `harmful`, `sensitive_data`,
`complaint`, `advice`, `identity_ok`, `identity_wrong_name`, `ai_disclosure` y `persona`.

## Navegador (`web/src/lib/session.ts`, `sessionStorage`)

| Clave | Valor |
|-------|-------|
| `manuelita.visit.user` | `anon-…` o el `user_id` adoptado tras el reconocimiento. |
| `manuelita.chat.thread` | Hilo actual (ya existía, en `sessionStorage`). |
| `manuelita.visit.welcomed` | `"1"` cuando la bienvenida ya se mostró o se dijo. |
| `manuelita.view` | `"tecnica"` si se abrió con `?vista=tecnica`. |

La clave antigua `manuelita.chat.user` (`localStorage`) se ignora y se elimina al cargar, de modo que la siguiente
visita ya no hereda al cliente anterior.
