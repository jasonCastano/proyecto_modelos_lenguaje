# Contrato: cambios de API y UI (spec 019)

Todos los cambios son **aditivos y opcionales**. Los clientes de la spec 018 siguen funcionando.

## `ChatResponse` (`/api/chat`, evento `done` de `/api/chat/stream`, `/resume`)

```jsonc
{
  "thread_id": "…",
  "turn": {
    "route": {
      "route": "out_of_scope",
      "scope_reason": "off_topic",     // + "crisis" | "unattainable"
      "topic": "clima",                // nuevo, opcional (saneado)
      "sentiment": "frustrated",       // nuevo, opcional
      "kind": null                     // nuevo: "pricing" | "commitment" | "human"
    },
    "answer": "…", "citations": [ … ]
  },
  "status": "answered",
  "client": null,
  "notices": ["empathy_opener"],       // + "empathy_opener" | "hostility_limit" | "best_guess" | "crisis"
  "contact": {                          // nuevo, opcional: ContactRecord (data-model.md)
    "version": "1.0",
    "turns": 2,
    "requests": [
      {"turn": 1, "category": "manuelita", "topic": "productos", "status": "resolved"},
      {"turn": 1, "category": "off_topic", "topic": "clima", "status": "out_of_scope"}
    ],
    "sentiments": ["frustrated", "satisfied"],
    "motive": ["productos", "clima"],
    "resolved": true,
    "hostile_turns": 0,
    "crisis": false,
    "opened_at": "…", "updated_at": "…"
  }
}
```

- `GET /api/chat/threads/{thread_id}` (`ThreadView`) gana `contact`, opcional, para restaurar la vista técnica.
- El esquema de contrato de la decisión de ruta (`tests/contract`, spec 014) añade `topic`, `sentiment`, `kind` y los
  motivos nuevos.

## Web

- `lib/types.ts`: `ContactRecord`, `ContactRequest`, `Sentiment` y los campos nuevos de la ruta.
- `components/ContactRecordPanel.tsx` (nuevo): solo en la vista técnica (`?vista=tecnica`). Muestra:
  - la lista de solicitudes con su categoría y estado (chips);
  - la evolución emocional en una línea («frustrado → satisfecho»);
  - el motivo;
  - si quedó resuelto;
  - los indicadores de hostilidad y crisis.
- Vista normal: **sin cambios visibles**. El registro no se renderiza (FR-023); las aperturas y declinaciones ya
  vienen en el texto de la respuesta y se leen con la voz.
- `ChatView.tsx`: guarda el último `contact` del hilo y lo pasa al panel; al reiniciar la visita lo limpia.
