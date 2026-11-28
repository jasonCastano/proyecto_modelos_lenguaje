# Data Model: Pestaña «WhatsApp» (spec 032)

No hay almacenamiento nuevo. Estas son las estructuras que viajan del servidor a la web.

## WhatsAppLink (respuesta de `GET /api/channels/whatsapp`)

| Campo | Tipo | Regla |
|---|---|---|
| `available` | booleano | `true` solo si `VALERIA_WHATSAPP_NUMBER` existe y es E.164 válido |
| `mode` | `"open"` \| `"closed"` \| `"unknown"` | De `ops.channel_mode()`; `unknown` sin `.env` del gateway |
| `message` | texto | Mensaje sugerido: «Hola, Valer-IA» |
| `web_url` | texto o `null` | `https://web.whatsapp.com/send?phone=<dígitos>&text=<mensaje>`; `null` si no disponible |
| `app_url` | texto o `null` | `https://wa.me/<dígitos>?text=<mensaje>`; `null` si no disponible |
| `qr_svg` | texto o `null` | SVG del `app_url`; `null` si no disponible |

**Invariante**: si `available` es `false`, `web_url`, `app_url` y `qr_svg` son `null` (SC-004).

## Número del canal (solo en el servidor)

| Atributo | Regla |
|---|---|
| Origen | `VALERIA_WHATSAPP_NUMBER` en el `.env` del proyecto (fuera de Git) |
| Formato | `^\+[1-9]\d{7,14}$` tras quitar espacios; Colombia: `+57` y 10 dígitos |
| Inválido o vacío | `available = false`; se registra «formato inválido» o «sin configurar», nunca el valor |

## Estados de la página `/whatsapp`

```text
cargando ──▶ disponible (botón + QR + modo)
         ├─▶ no disponible (aviso + enlace al Agente)
         └─▶ error de red (aviso + enlace al Agente + «Reintentar»)
```
