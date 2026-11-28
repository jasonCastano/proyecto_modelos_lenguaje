# Data Model: cuentas de WhatsApp identificadas solo por ID (spec 033)

Sin tablas nuevas. Nunca se guardan ni registran valores de ID o números (regla 10).

## Remitente normalizado (`channels/identity.py`)

| Entrada | Normalizado | Seudónimo | Máscara |
|---|---|---|---|
| `+573001234567`, `573001234567@s.whatsapp.net` | `+573001234567` | `wa-` + HMAC(sal, `+57…`) | `+57 ••• ••• 4567` |
| `12345678901234@lid`, `12345678901234@hosted.lid` | `lid:12345678901234` | `wa-` + HMAC(sal, `lid:…`) | `ID ••••1234` |

**Validación**: `^\d{5,20}@(lid|hosted\.lid)$` (sin sufijo de dispositivo; si llega `:N`, se quita). Cualquier
otro formato es un `SenderError`, como hoy.

## Registro del canal (`ChannelLogRecord`, campo nuevo)

| Campo | Valores | Uso |
|---|---|---|
| `sender_kind` | `phone`, `lid`, `telegram` | cuántas personas llegan solo con ID (FR-014); nunca el valor |

El evento nuevo `stale` (`status: "ignored"`) marca un mensaje descartado por antigüedad (FR-010).

## Configuración (`[channels]`)

| Clave | Tipo | Defecto | Validación |
|---|---|---|---|
| `stale_minutes` | int | 15 | 1 ≤ valor ≤ 1440 |

## Estado del soporte (`ops check` → `soporte-lid`)

| Estado | Condición | Resultado |
|---|---|---|
| `nativo` | el normalizador no contiene el `throw` de LID | ✅ «nativo del componente» |
| `parcheado` | la marca `valeria-lid v1` está en los dos archivos | ✅ «parche valeria-lid v1» |
| `ausente` | el `throw` sigue y falta la marca | ❌ «falta: ejecuta `scripts\openclaw_env.ps1 -Install`» |
| `sin plugin` | no se encuentra la instalación del componente | ❌ «componente de WhatsApp no instalado» |

## Archivos parcheados (fuera del repositorio)

`$OPENCLAW_STATE_DIR/npm/projects/openclaw-whatsapp-*/node_modules/@openclaw/whatsapp/dist/.setup/`:

- `monitor-*.mjs`: normalizador de entrada;
- `normalize-target-*.mjs`: destinos de salida.

Cada uno conserva una copia `*.orig` del original.
