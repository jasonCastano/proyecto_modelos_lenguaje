# Contrato HTTP: cambios de la spec 018

## `GET /api/welcome` → `200`

```json
{
  "assistant": "Valer-IA Caña",
  "version": "1.0",
  "text": "¡Hola! Soy Valer-IA Caña, la asistente virtual de Manuelita. … [U1] … [U2] …",
  "citations": [{ "label": "U1", "unit_id": "…", "url": "https://www.manuelita.com/…", "title": "…" }]
}
```

- No llama al modelo de lenguaje.
- Si la plantilla no carga, responde `503 welcome_unavailable` y la interfaz usa un saludo mínimo local.

## `ChatResponse` (en `/api/chat`, en el evento `done` de `/api/chat/stream` y en `/resume`)

Campos nuevos, opcionales y con valor por defecto:

```json
{
  "client": { "user_id": "anon-…", "recognized": false, "name": null, "reset": false, "masked_email": null },
  "notices": ["sensitive_data"]
}
```

- **`client.user_id`**: si difiere del enviado, el navegador lo adopta para los turnos siguientes (reconocimiento).
- **`client.reset = true`**: el navegador crea un `user_id` anónimo nuevo y abre otro hilo.
- **`client.masked_email`**: solo aparece en el turno en que el visitante escribió su correo.
- **`notices`**: `sensitive_data` cuando se redactaron tarjeta, documento o teléfono. El texto del aviso ya viene en
  `turn.answer`.

## `RouteDecision` (en `turn.route`)

Agrega `scope_reason`, que solo se muestra en la vista técnica.

## Sin cambios incompatibles

`POST /api/chat`, `/api/chat/stream`, `/resume` y `/api/memory/{user_id}` mantienen sus campos. `DELETE
/api/memory` también borra los vínculos de identidad del cliente.
