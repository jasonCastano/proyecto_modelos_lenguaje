# Contrato: entrega por frases (spec 021)

Contrato del flujo de eventos, del filtro de frases y de los cambios en la API y la web. Es la referencia de las
pruebas sin red de `tests/integration/agent/test_sentence_flow.py` y `tests/api/test_sentence_stream.py`.

## 1. Eventos del SSE (`POST /api/chat/stream`)

| Evento | Cuándo | Cuerpo |
|--------|--------|--------|
| `start` | Al abrir el flujo | `{thread_id}` (sin cambios) |
| `route` | Después de `route` | `{route}` (sin cambios) |
| `tool` / `retrieval` | Búsqueda | Sin cambios |
| `sentence` | **Nuevo**. Cada frase aprobada, en orden | `{text, index}` |
| `token` | Solo con `delivery = "complete"` | `{text}` (sin cambios) |
| `done` | Al terminar | `{response}` (sin cambios); `response.turn.answer` es igual a la unión de los `sentence` |
| `error` | Falla del flujo ya iniciado | Sin cambios |

**Garantías con `delivery = "sentences"`**:
- **G1**: no hay eventos `token`.
- **G2**: la unión de los `text` de los eventos `sentence` (separados por un espacio, o por un salto de línea si la
  frase lo trae) es igual a `done.response.turn.answer`, sin contar espacios. Así se verifica SC-003.
- **G3**: cada `sentence` pasó `review()` con las verificaciones locales (R3).
- **G4**: las respuestas fijas (seguridad, identidad, perfil y acciones) llegan como uno o varios `sentence` desde
  `finalize`, con el mismo texto que hoy.

## 2. Orden de entrega dentro de un turno

```text
lead (route)  →  delivered (converse | answer | agent)  →  tail (finalize)  →  done
```

- `lead`: límite por hostilidad y aviso de datos sensibles; en `scripted`, además, la apertura empática.
- `tail`:
  - el sufijo `best_guess`;
  - el aviso de solicitudes truncadas;
  - la oferta de recordar en el cierre;
  - las frases exigidas que falten;
  - el cierre breve si la conversación terminó a mitad de frase (R5).

## 3. Filtro de frases (`agent/sentences.py`)

```text
gate = SentenceGate(mode, review_sentence, max_chars, first_chars)
for chunk in model.stream(...):
    for decision in gate.push(chunk):
        if decision.kind == "deliver":  writer({"sentence": decision.text, "index": decision.index})
        if decision.kind == "retry":    break   # primera frase rechazada: regenerar o respaldo
        if decision.kind == "stop":     break   # conversación: se corta en la frase rechazada
for decision in gate.close(): ...           # resto del búfer; en retrieval, sin citas ⇒ evidencia insuficiente
```

| Situación | `conversation` (`converse`) | `retrieval` (`answer`, `agent`) |
|-----------|-----------------------------|----------------------------------|
| Primera frase rechazada | `retry`: regenerar (1 vez) y después respaldo; nada entregado | `retry`: reintento estricto de la cadena (1 vez) y después evidencia insuficiente |
| Frase posterior rechazada | `stop`; si hace falta, `close.short` en `tail` | Descartar y seguir |
| Frase sin cita | Se entrega (no se exigen citas en la charla, salvo el puente con `[U1]`) | Se retiene hasta una frase citada |
| Error o tiempo vencido antes de la primera frase | Respaldo por frases | `FALLBACK_ANSWER` |
| Error o tiempo vencido después | Se conservan las frases y `tail` cierra | Se conservan las frases entregadas |

## 4. Cambios en la API (`api_models.py`)

- `ContactTurnModel.discarded: int = Field(0, ge=0, le=20)`.
- `ChatResponse.notices`: valor nuevo `sentence_discarded`.
- Esquemas SSE de la web (`web/src/lib/types.ts`): `ChatStreamEvent` añade
  `{event: "sentence"; text: string; index: number}`.

## 5. Web

- `ChatView.liveStage`: ante `sentence`, agrega `text` al texto en vivo y muestra «Escribiendo…».
- `useVoice.pushSentence(text)`: encola la oración sin pasar por `SentenceSegmenter`. Al terminar el turno,
  `finishLive` no vuelve a leer lo que ya se encoló.
- `ContactRecordPanel`: la línea «Actos» marca `✂N` en los turnos con frases descartadas.
- Con `delivery = "complete"`, el cliente funciona igual que hoy (eventos `token`).

## 6. CLI y evaluación

- `agent converse --baseline-delivery`: repite los bloques con `delivery = "complete"` y agrega la sección
  «Entrega» al informe:

  | Métrica | Meta |
  |---------|------|
  | `first_sentence_ms.p90` (conversación) | < 3000 (SC-001) |
  | `first_sentence_ms.p90` (búsqueda) − línea base | ≤ 1000 (SC-002) |
  | `retracted_turns` | 0 (SC-003) |
  | `hard_violations` | 0 (SC-004) |
  | Metas duras de la spec 020 | Sin cambios (SC-005) |
  | `done_ms.p90` / línea base | ≤ 1.10 (SC-006) |
  | `fallback_on_error` con falla a mitad del stream | 100 % (SC-008) |

- El comando sale con código 1 si falla SC-003, SC-004, SC-005 o SC-008. SC-001, SC-002 y SC-006 son metas de
  latencia: se informan y, en `--mode real`, también deciden el código de salida.
