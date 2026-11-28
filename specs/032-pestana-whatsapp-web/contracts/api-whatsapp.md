# Contrato: `GET /api/channels/whatsapp` (spec 032)

Público (sin `X-Channel-Token`), solo lectura, sin efectos secundarios. Respuesta `200` siempre que el servidor
funcione; la disponibilidad va en el cuerpo.

## Disponible

```json
{
  "available": true,
  "mode": "open",
  "message": "Hola, Valer-IA",
  "web_url": "https://web.whatsapp.com/send?phone=57XXXXXXXXXX&text=Hola%2C%20Valer-IA",
  "app_url": "https://wa.me/57XXXXXXXXXX?text=Hola%2C%20Valer-IA",
  "qr_svg": "<svg xmlns=\"http://www.w3.org/2000/svg\" ...>...</svg>"
}
```

## No disponible (variable vacía, ausente o inválida)

```json
{
  "available": false,
  "mode": "unknown",
  "message": "Hola, Valer-IA",
  "web_url": null,
  "app_url": null,
  "qr_svg": null
}
```

## Reglas

| Caso | Resultado |
|---|---|
| `VALERIA_WHATSAPP_NUMBER=+57` y 10 dígitos | `available: true`; los enlaces llevan los dígitos sin `+` |
| Con espacios (`+57 300 …`) | Se quitan; válido si queda E.164 |
| Sin `+`, con letras o guiones, o con menos de 8 dígitos | `available: false`; registro `whatsapp_link: formato inválido` sin el valor |
| Variable ausente o vacía | `available: false`; sin registro de error |
| `.env` del gateway con `WA_DM_POLICY=open` | `mode: "open"` |
| `.env` del gateway con otra política | `mode: "closed"` |
| Sin `.env` del gateway | `mode: "unknown"` |
| Encabezados | `Cache-Control: no-store` (el número puede cambiar) |

El ejemplo usa `57XXXXXXXXXX` como marcador; ningún número real va en el repositorio.
