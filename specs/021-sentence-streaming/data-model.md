# Data Model: Respuesta progresiva por frases revisadas (spec 021)

Todas las entidades viven en el turno en curso, en el estado del hilo (checkpointer) o en los informes de evaluación.
Nada se escribe en `data/` ni en el Store por usuario.

## 1. SentenceGate (por nodo y por turno, no persistente)

Filtro incremental que recibe texto del modelo, arma frases, las revisa y decide qué se entrega.

| Campo | Tipo | Reglas |
|-------|------|--------|
| `mode` | `conversation \| retrieval` | `conversation` corta en la primera frase rechazada; `retrieval` descarta y sigue (R5) |
| `buffer` | `str` | Texto todavía sin frase cerrada |
| `held` | `list[str]` | Solo `retrieval`: frases sin cita esperando una frase citada (R6) |
| `delivered` | `list[str]` | Frases ya entregadas, en orden |
| `discarded` | `list[ReviewIssue]` | Motivos de las frases descartadas; nunca su texto |
| `stopped` | `bool` | Verdadero cuando `conversation` cortó el stream |
| `first_check_failed` | `bool` | La primera frase falló antes de entregar nada: regeneración o respaldo (R4) |

**Transiciones**:
- **Frase aprobada**:
  - si es la primera y repite una respuesta reciente, va a `first_check_failed`;
  - si no, se entrega (en `retrieval`, junto con las de `held` si trae cita).
- **Frase rechazada**:
  - si es la primera, va a `first_check_failed`;
  - en `conversation`, va a `stopped`;
  - en `retrieval`, se suma a `discarded` y se sigue.
- **Fin del modelo**: el búfer pasa como última frase. En `retrieval` sin ninguna frase citada no se entrega nada
  (el nodo emite el mensaje de evidencia insuficiente).

**Invariantes**:
- `"".join(delivered)` es prefijo del texto final del turno (FR-003).
- Ninguna frase llega a `delivered` sin pasar `review()` (FR-002).

## 2. DeliveredSentence (evento del flujo, no persistente)

| Campo | Tipo | Reglas |
|-------|------|--------|
| `text` | `str` | Frase o fragmento completo; nunca vacío |
| `index` | `int` | Orden en el turno, desde 0 |

Se emite como evento `sentence` del SSE ([contracts/streaming.md](./contracts/streaming.md)).

## 3. Cambios en `ChatState`

| Clave | Tipo | Reglas |
|-------|------|--------|
| `lead` | `list[str]` | Frases previas calculadas en `route` (hostilidad, datos sensibles, apertura en `scripted`). Se reinicia en `TURN_RESET` |
| `delivered` | `list[str]` | Frases entregadas por el nodo que genera. Se reinicia en `TURN_RESET` |
| `discarded` | `int` | Número de frases descartadas en el turno. Se reinicia en `TURN_RESET` |

`finalize` arma `answer = join(lead + delivered + tail)` y entrega `tail` (R8).

## 4. Cambios en entidades existentes

- **`ContactTurnModel`** (spec 020): campo nuevo `discarded: int = 0`, con `ge=0` y como máximo 20. Siempre es un
  conteo, sin texto.
- **`notices`**: valor nuevo `sentence_discarded`.
- **`ConversationConfig`** (spec 020), claves nuevas:

  | Clave | Tipo | Defecto | Validación |
  |-------|------|---------|------------|
  | `delivery` | `sentences \| complete` | `sentences` | enum |
  | `sentence_max_chars` | int | 220 | 80–600 |
  | `first_fragment_chars` | int | 160 | 40–400 y ≤ `sentence_max_chars` |
  | `stream_first_timeout_seconds` | float | 8 | 1–30 |
  | `stream_idle_timeout_seconds` | float | 6 | 1–30 |

- **`prompts/care.md`** 1.2: secciones nuevas `close.short` (cierre breve de conversación) y
  `required.valeria`, `required.ai`, `required.professional`, `required.manuelita` (frases exigidas que faltan, R3).

## 5. Medición (informes, no estado)

**DeliveryMeasurement** (por turno de evaluación):
- `turn_class`: `conversation` o `retrieval`;
- `first_sentence_ms` y `done_ms`;
- `sentences` y `discarded`;
- `retracted: bool`: el texto mostrado no es prefijo de la respuesta final, sin contar espacios.

**DeliveryReport** (por variante, dentro de `docs/evaluacion_conversacion.json`):
- `first_sentence_ms.p50` y `first_sentence_ms.p90` por clase;
- `done_ms.p50` y `done_ms.p90` por clase;
- `retracted_turns`;
- `discarded_rate`;
- `baseline`: la misma estructura en `delivery = "complete"`.
