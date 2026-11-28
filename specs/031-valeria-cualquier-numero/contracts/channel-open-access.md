# Contrato: acceso abierto del canal (spec 031)

Extiende el canal de las specs 024 y 028 (`channel-api-v2`). Sin cambios en `POST /api/channels/messages` para los
clientes: los límites se expresan con `status` y `messages` ya existentes.

## 1. Respuestas ante límites y bloqueo

| Situación | `status` | `messages` | `voice` |
|---|---|---|---|
| Número permitido | `answered` (como hoy) | respuesta | según specs 028–030 |
| Primer mensaje sobre el límite de la ventana | `busy` | 1 aviso en el idioma del mensaje | `null` |
| Primer mensaje sobre el tope diario | `busy` | 1 aviso en el idioma del mensaje | `null` |
| Siguientes mensajes limitados | `ignored` | `[]` | `null` |
| Número bloqueado | `ignored` | `[]` | `null` |

Avisos (sin comandos ni cifras del límite):

- **Límite de la ventana**:
  - es: «Recibí varios mensajes seguidos; dame unos minutos y seguimos conversando.»
  - en: «I got several messages in a row; give me a few minutes and we'll keep talking.»
- **Tope diario**:
  - es: «Por hoy llegamos al máximo de mensajes; mañana con gusto seguimos.»
  - en: «We've reached today's message limit; I'll be happy to continue tomorrow.»

## 2. `GET /api/channels/status` (campos nuevos en `channels`)

```json
{
  "channels": {
    "messages_last_hour": 12,
    "errors_last_hour": 0,
    "p90_ms": 15000,
    "people_today": 5,
    "limited_today": 1,
    "blocked_today": 0
  }
}
```

## 3. CLI del operador (`pml channels …`)

| Comando | Efecto | Salida |
|---|---|---|
| `pseudonym --sender <E.164>` | calcula el seudónimo | `wa-<16 hex>` (para `VALERIA_OPERATORS`) |
| `block --sender <E.164>` | bloquea el seudónimo | `bloqueado wa-…` |
| `unblock --sender <E.164>` | lo desbloquea | `desbloqueado wa-…` |
| `blocked` | lista los bloqueados | seudónimos y fecha |

Ninguno guarda ni imprime el número completo.

## 4. `ops check` (comprobación nueva)

```text
✅ modo-canal: ABIERTO al público (recuerda cerrarlo al terminar el proyecto)
✅ modo-canal: cerrado (3 números de prueba)
```

## 5. Modo del canal (sin cambios de interfaz)

```powershell
.\scripts\openclaw_env.ps1 -Mode open     # cualquier número; guarda los de prueba en WA_TEST_1..3
.\scripts\openclaw_env.ps1 -Mode closed   # solo los números de prueba
```
