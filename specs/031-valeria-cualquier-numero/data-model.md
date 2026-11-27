# Data Model: Valer-IA atiende a cualquier número (spec 031)

Todo el estado nuevo vive en el almacén del canal (`<estado>/channels.sqlite3`, fuera del repositorio) y en
variables de entorno. Nunca se guardan números completos.

## 1. Modo del canal (OpenClaw, `.env` externo)

| Clave | Valores | Regla |
|---|---|---|
| `WA_DM_POLICY` | `open` \| `allowlist` | `open` exige `WA_ALLOW_1="*"` (validación de OpenClaw). |
| `WA_ALLOW_1..3` | `*` o números E.164 | En `open`, `*`. En cerrado, los números de prueba. |
| `WA_TEST_1..3` | números E.164 | Copia de los números de prueba mientras el canal está abierto. |

Transiciones: `scripts/openclaw_env.ps1 -Mode open|closed`. El cambio reinicia el gateway; el modo persiste en el
archivo.

## 2. Operadores (backend, `.env` del repositorio, no versionado)

- `VALERIA_OPERATORS`: seudónimos `wa-<16 hex>` separados por comas. Nunca números.
- Los operadores:
  - no tienen límites;
  - son los únicos con atajos del operador cuando la lista no está vacía.

## 3. Uso por número (`channel_usage`)

| Campo | Tipo | Regla |
|---|---|---|
| `user_id` | texto (PK) | Seudónimo. |
| `window_start` | ISO-8601 UTC | Inicio de la ventana corta vigente. |
| `window_count` | entero | Mensajes en la ventana; se reinicia cuando `ahora − window_start ≥ rate_window_minutes`. |
| `window_notified` | bool | Ya recibió el aviso de esta ventana. |
| `day` | `YYYY-MM-DD` (hora local) | Día del contador diario. |
| `day_count` | entero | Mensajes del día; se reinicia al cambiar `day`. |
| `day_notified` | bool | Ya recibió el aviso del día. |

Decisión por mensaje (`limit_decision`), en este orden:

1. Operador → `allow`.
2. `day_count ≥ daily_max_messages` → `daily_capped`: aviso si `!day_notified`; si no, silencio.
3. `window_count ≥ rate_max_messages` → `rate_limited`: aviso si `!window_notified`; si no, silencio.
4. En otro caso, `allow`, y se incrementan ambos contadores.

Configuración (`[channels]` en `config/agent.toml`):

- `rate_window_minutes = 10`
- `rate_max_messages = 20`
- `daily_max_messages = 100`

## 4. Bloqueados (`channel_blocked`)

| Campo | Tipo | Regla |
|---|---|---|
| `user_id` | texto (PK) | Seudónimo. |
| `blocked_at` | ISO-8601 UTC | Momento del bloqueo. |

Un bloqueado recibe `status: "ignored"` y `event: "blocked"`; no hay mensaje ni llamada al modelo.

## 5. Registro del canal y estado

- **Eventos nuevos en `channels.jsonl`**: `rate_limited`, `daily_capped`, `blocked`. Sin texto ni números.
- **`GET /api/channels/status → channels`** suma, sobre el registro del día:
  - `people_today`: seudónimos distintos;
  - `limited_today`: `rate_limited` + `daily_capped`;
  - `blocked_today`.
- **`ops check`** suma `modo-canal`: `ABIERTO al público` o `cerrado (N números)`.
