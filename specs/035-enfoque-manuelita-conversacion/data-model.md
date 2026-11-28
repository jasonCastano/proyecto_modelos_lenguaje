# Data Model: conversación enfocada en Manuelita (spec 035)

Sin tablas ni archivos de datos nuevos. Todo vive en el estado del hilo o en los prompts.

## Memoria de conversación (`care.update_conversation`, campos nuevos)

| Campo | Tipo | Regla |
|---|---|---|
| `offtopic_streak` | int | +1 en turnos `smalltalk`, `off_topic`, `minimal` sin asentimiento a una oferta y `greeting` desde el segundo turno; vuelve a 0 con `manuelita`, `clarify`, `about_assistant`, `thanks` o `closing` |
| `offered_topics` | list[str] | claves de `offer.topics` ya ofrecidas en el hilo (máximo 8; se reinicia al agotarlas) |

## Plan del turno (`TurnPlan`, campos nuevos)

| Campo | Tipo | Regla |
|---|---|---|
| `redirect` | bool | `True` en los actos de enfoque (research R3) |
| `streak` | int | `offtopic_streak` después de contar este turno |
| `topics` | tuple[str, ...] | 2–3 temas de `offer.topics` no ofrecidos aún; vacío si hay puente |

`render()` agrega, cuando `redirect` es `True`:

```text
regreso a Manuelita: obligatorio (termina con el puente, un tema concreto o las opciones)
preguntas: solo sobre Manuelita; nada sobre el tema ajeno ni la vida personal
turnos ajenos seguidos: <streak>
temas sugeridos: <tema 1>, <tema 2>, <tema 3>
```

Desde `streak ≥ 3`, la longitud es «breve: máximo dos frases».

## Temas sugeridos (`prompts/care.md`, sección `offer.topics`)

Una línea por tema, `clave | texto`. Ejemplo: `historia | la historia de Manuelita desde 1864`. Sin cifras nuevas:
solo hechos ya presentes en los puentes o en la presentación.

## Verificador (`review.py`, checks nuevos)

| Check | Se marca cuando… | Nota para el reintento |
|---|---|---|
| `offtopic_question` | una oración interrogativa no menciona términos de Manuelita | «Haz preguntas solo sobre Manuelita.» |
| `chat_invite` | aparece una invitación a charlar de otros temas | «No ofrezcas ni aceptes charla libre; ofrece temas de Manuelita.» |
| `no_redirect` | la respuesta no menciona Manuelita (con `redirect`) | «Termina llevando la conversación a Manuelita.» |
| `rejection` | aparece una frase que rechaza lo que la persona comparte | «Recibe lo que comparte con amabilidad; el límite es sobre tu propósito.» |
| `closing_repeat` | la última oración repite (> 0,8) el cierre de una respuesta anterior | «Cambia la frase de cierre.» |

Los checks solo se aplican a los planes con `redirect`; los demás actos conservan los checks actuales.

## Conjunto de evaluación (`tests/fixtures/converse/focus.jsonl`)

El formato es el de `conversations.jsonl`, con las claves `expect` nuevas:

- `no_offtopic_question`, `no_chat_invite`, `redirects`, `no_rejection` y `no_closing_repeat` (booleanas);
- `max_sentences` (entera).
