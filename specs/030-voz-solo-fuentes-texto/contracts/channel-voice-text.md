# Contrato: texto que acompaña a la nota de voz (spec 030)

Extiende `POST /api/channels/messages` (specs 024 y 028, `channel-api-v2`) y el formato del canal (spec 029,
`channel-format.md`).

## 1. Respuesta del backend

```json
{
  "status": "answered",
  "messages": ["<respuesta completa>\n\nFuentes:\n[1] … — https://…"],
  "sources_messages": ["Fuentes:\n[1] … — https://…"],
  "voice": {
    "audio_path": "…/channels/voice/<id>.ogg",
    "language": "es",
    "duration_ms": 21000,
    "mime": "audio/ogg; codecs=opus"
  },
  "thread_id": "…",
  "route": "documental",
  "tools": ["search_documents"],
  "latency_ms": 11405
}
```

- `sources_messages` es opcional: un cliente que no lo conoce sigue usando `messages`, igual que antes.
- Con `voice: null`, `sources_messages` es `[]`.
- Con voz y sin fuentes, `sources_messages` es `[]`: el turno se responde solo con la nota de voz.

## 2. Plugin `valeria-bridge`

1. Si `voice` está presente:
   - envía la nota de voz (adaptador del canal);
   - si la entrega se confirma, devuelve `sources_messages` unidos por línea en blanco;
   - si la lista está vacía, devuelve `{handled: true}` sin texto.
2. Si la entrega de la voz falla:
   - devuelve `messages` (respuesta completa);
   - registra `valeria-bridge: voz no entregada; texto completo`;
   - el CLI puede reintentar la voz en segundo plano.
3. Si `voice` es `null`, devuelve `messages`.

## 3. Formato del bloque de fuentes

- **Encabezado e idioma**: en el idioma del turno; las fuentes públicas y las sintéticas van en bloques separados.
- **Líneas**: una por fuente, `[n] Título[, p. X] — URL`. Los títulos siguen las reglas de la spec 029.
- **Mensajes**:
  - si el bloque no cabe en un mensaje, sigue en el siguiente con líneas completas;
  - el encabezado aparece una sola vez por bloque.

## 4. Guion de voz

Con fuentes, termina con:

- es: «Te dejo las fuentes por escrito.»
- en: «I've left the sources for you in writing.»
