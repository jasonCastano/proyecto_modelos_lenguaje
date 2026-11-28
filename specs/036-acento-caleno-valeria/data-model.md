# Data Model: estilo caleño (spec 036)

## 1. Léxico (`config/caleno.toml`)

```toml
[style]
enabled = true
max_written = 1           # expresiones por respuesta escrita (FR-003)
max_spoken = 2            # expresiones por guion hablado (FR-003)
suggestions = 3           # sugeridas por turno
memory = 3                # últimas expresiones recordadas (FR-004)
opt_out = ["habla normal", "habla normalito", "sin acento", "sin modismos", "no hables asi",
           "speak normally", "without slang"]
formal_markers = ["buenos dias", "buenas tardes", "usted", "quisiera", "solicito", "cordial", "estimado",
                  "estimada", "agradezco"]

[[approved]]
text = "ve"               # forma canónica, sin tildes al comparar
match = "interjection"    # "phrase" (por defecto) | "interjection" (solo «Ve, …» o «…, ve»)
meaning = "llamado de atención afectuoso, muy caleño"
levels = ["informal", "neutral"]
spoken = true
example = "¡Ve, qué buena pregunta!"

[[banned]]
text = "parce"
reason = "modismo paisa, no caleño"
```

**Validación al cargar**:

- `text` no vacío y único entre aprobadas y vetadas;
- `levels` ⊆ {`informal`, `neutral`, `formal`};
- al menos 8 aprobadas y 3 con nivel `formal`;
- toda forma de voseo en la lista vetada.

Un error de validación deja el estilo en `off` y se registra (el agente nunca falla por el léxico).

## 2. Nivel de estilo

`StyleLevel = Literal["off", "formal", "neutral", "informal"]`. Reglas en research R3. Matriz:

| Situación | Nivel |
|---|---|
| inglés u otro idioma | off |
| queja, molestia, angustia o crisis | off |
| texto fijo de conducta | off (no pasa por el modelo) |
| `style_opt_out` en el hilo | off |
| registro formal con marcas formales | formal |
| registro informal | informal |
| resto | neutral |

## 3. `TurnPlan` (`agent/plan.py`)

Campo nuevo, serializado en `to_state`/`from_state`:

| Campo | Tipo | Defecto | Uso |
|---|---|---|---|
| `style` | `str` (`StyleLevel`) | `"off"` | Nivel del turno. |
| `style_hints` | `tuple[str, ...]` | `()` | Expresiones sugeridas (texto canónico). |

`render()` no cambia. El bloque `<estilo>` lo genera `style.render_block(plan, glossary)` (contrato §3).

## 4. Memoria del hilo (`care.ConversationMemory`)

| Campo | Tipo | Defecto | Actualización |
|---|---|---|---|
| `style_opt_out` | `bool` | `False` | `True` si el mensaje cumple `opt_out`; no vuelve a `False` en el hilo. |
| `last_expressions` | `list[str]` | `[]` | Expresiones aprobadas encontradas en la respuesta mostrada; máximo `memory`. |

Compatibles con hilos existentes (valores por defecto en `copy_conversation`).

## 5. Verificación (`agent/review.py`)

`ReviewIssue` suma `style_banned`, `style_excess`, `style_repeat` y `style_off` (research R5). Las funciones puras
de `style.py` son:

- `find_expressions(text) -> list[str]`: aprobadas, en orden;
- `find_banned(text) -> list[str]`;

`review()` las usa según `plan.style`.

## 6. Voz

| Archivo | Clave | Cambio |
|---|---|---|
| `config/voice.toml` | `[voice].voice` | La voz elegida en la audición (por defecto se conserva «Rebeca»). |
| `config/caleno.toml` | `approved[].spoken` | `false` para las expresiones mal pronunciadas. |

Los audios de audición (WAV más `index.txt`) se escriben en `MANUELITA_STATE_DIR/voice_audition/`. No se versionan.

## 7. Evaluación (`converse_eval.py`)

- `STYLE_FILE = tests/fixtures/converse/caleno.jsonl`: mismo formato que `conversations.jsonl`, con claves
  `expect` nuevas (research R8) y `"voice": true` opcional por turno para medir el guion hablado.
- Informe `docs/evaluacion_caleno.{md,json}`:
  - por variante: totales por check, porcentaje de uso en los turnos informales o neutros, y expresiones más
    usadas;
  - juez (claridad y profesionalismo);
  - turnos marcados;
  - y una sección de prueba humana para llenar a mano.
