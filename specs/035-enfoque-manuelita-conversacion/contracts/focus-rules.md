# Contract: reglas de enfoque en la conversación guiada (spec 035)

## 1. `agent/plan.py`

```python
FOCUS_ACTS = frozenset({"smalltalk", "off_topic", "minimal", "greeting"})


def needs_redirect(act: str, turn: int, assent_to_offer: bool) -> bool: ...
```

`build_plan(...)` fija `redirect`, `streak` y `topics`. Desde `streak >= 3`, la longitud es `short` y el plan
renderiza «máximo dos frases».

## 2. `agent/graph.py`

- `opening_hint(plan, seed)`: con `plan.redirect`, excluye las aperturas que son preguntas (la sexta de
  `OPENINGS` y «una pregunta muy breve» de `MINIMAL_OPENINGS`).
- `_turn_plan` pasa a `build_plan` la racha y los temas ya ofrecidos (memoria) y recibe los temas elegidos.

## 3. `agent/care.py`

`update_conversation(...)` actualiza `offtopic_streak` y `offered_topics` según el acto (data-model). La función
`pick_topics(playbook, offered, k=3)` devuelve los temas no ofrecidos, con rotación.

## 4. `agent/review.py`

```python
FOCUS_CHECKS = ("offtopic_question", "chat_invite", "no_redirect", "rejection", "closing_repeat")


def focus_issues(
    text: str, plan: TurnPlan | None, recent_answers: Sequence[str]
) -> list[tuple[str, str]]: ...
```

`review(...)` agrega estos checks cuando `plan.redirect`. `NOTES` lleva la nota en español de cada uno. El
reintento y el respaldo (`care.md`) no cambian.

## 5. `prompts/converse.md` 1.1

Sustituye el nivel social y las reglas de estilo por las de la spec:

- una frase de cortesía o empatía;
- regreso obligatorio a Manuelita;
- preguntas solo sobre Manuelita;
- ante la propuesta de charla, propósito más temas;
- sin rechazo;
- sin opinar.

Los ejemplos cubren la transcripción seudonimizada y retiran el que cerraba con un deseo sobre el equipo.

## 6. `agent/converse_eval.py`

`check_turn(expect, record, records, fixed)` soporta las claves nuevas. `agent converse --focus` corre
`tests/fixtures/converse/focus.jsonl` y escribe `docs/evaluacion_enfoque.{md,json}`, con los totales de cada
check, el juez de empatía y los turnos marcados (sin datos personales).
