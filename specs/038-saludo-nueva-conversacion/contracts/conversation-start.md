# Contract: inicio de conversación en el canal (spec 038)

Interfaces internas del backend. El contrato HTTP `POST /api/channels/messages` y el plugin no cambian. La
presentación llega dentro de `messages`, de `sources_messages` y de la nota de voz que ya existen.

## 1. `ChannelStore`

```python
def open_conversation(
    self, user_id: str, channel: str, masked: str, *, idle_hours: int
) -> tuple[str, Literal["first_contact", "inactivity"] | None]:
    """Hilo activo y motivo si empieza ahora; con inactividad cierra el anterior y abre otro."""


def is_introduced(self, thread_id: str) -> bool: ...
def mark_introduced(self, thread_id: str) -> None: ...
```

- `new_thread` y `ensure_user` crean los hilos con `introduced = 0`.
- `adopt_thread`, que reemplaza el identificador provisional por el del servicio, conserva `introduced`.

## 2. `channels.greeting`

```python
def introduction(language: Language, thread_id: str, name: str | None = None) -> str
def identity_line(language: Language) -> str            # una frase, para errores
def already_introduced(answer: str) -> bool             # menciona Valer-IA/Valeria en las 2 primeras frases
def merge(intro: str, answer: str) -> str               # quita un «¡Hola!» inicial suelto y antepone
```

Ejemplo (es, sin nombre): «¡Hola! Soy Valer-IA, la asistente virtual de Manuelita. Te cuento de sus productos,
negocios, sostenibilidad y cifras, siempre con fuentes, y también puedes mandarme notas de voz.»

## 3. `ChannelBridge`

- `handle`: usa `open_conversation`. Guarda el motivo en `reply.conversation_start`.
- `_dispatch`, cuando `intent == "restart"` abre el hilo nuevo: motivo `restart`.
- **Después de armar una respuesta atendida** (`status == "answered"` o `unsupported`, nunca un atajo, un aviso,
  una aprobación ni la confirmación de reinicio sin pregunta), si `not store.is_introduced(thread_id)`:
  - **Si `already_introduced(spoken)`**: el origen es `agent` y no se agrega nada.
  - **Si no**:
    - el primer mensaje queda `merge(intro, messages[0])`;
    - `spoken` queda `merge(intro, spoken)`;
    - `reply.opening = intro`;
    - el origen es `bridge`.

  En los dos casos se llama `store.mark_introduced(thread_id)` y se fija `reply.introduced = origen`.
- **Errores** (`status == "error"`) en un hilo sin presentar: se antepone `identity_line`, sin marcar.

## 4. `ConversationVoice.for_answer`

```python
def for_answer(self, question, answer, language, *, with_sources=False, opening: str | None = None)
```

- `answer` llega **sin** la presentación. El guion se construye y valida como hoy.
- Con `opening`, el guion final queda `opening + " " + guion` y, con fuentes, termina en la frase de cierre de la
  spec 030.

## 5. Registro (`logs/channels.jsonl`)

Hay dos campos nuevos: `conversation_start` y `introduced` (ver `data-model.md`). Nunca llevan texto ni números.

## 6. `pml channels simulate --check`

Con un guion que marque `"new_conversation": true` en el primer mensaje, se reporta como hallazgo:

- una primera respuesta sin presentación;
- una presentación repetida en los turnos siguientes;
- una presentación de más de dos frases.
