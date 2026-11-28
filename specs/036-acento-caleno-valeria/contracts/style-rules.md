# Contract: estilo caleño del agente (spec 036)

## 1. `agent/style.py`

```python
StyleLevel = Literal["off", "formal", "neutral", "informal"]


@dataclass(frozen=True)
class Expression:
    text: str
    meaning: str
    levels: frozenset[str]
    spoken: bool
    example: str
    match: Literal["phrase", "interjection"] = "phrase"


@dataclass(frozen=True)
class Lexicon:
    approved: tuple[Expression, ...]
    banned: tuple[tuple[str, str], ...]  # (texto, motivo)
    max_written: int
    max_spoken: int
    suggestions: int
    memory: int
    opt_out: tuple[str, ...]
    formal_markers: tuple[str, ...]
    enabled: bool
    sha256: str


def load_lexicon(path: Path = CALENO_FILE) -> Lexicon: ...  # lru_cache; inválido ⇒ enabled=False
def level_for(plan: TurnPlan, memory: Mapping[str, Any], message: str) -> StyleLevel: ...
def suggest(
    level: StyleLevel, recent: Sequence[str], seed: int, *, spoken: bool = False
) -> tuple[str, ...]: ...
def wants_plain(message: str) -> bool: ...  # «habla normal»
def find_expressions(text: str) -> list[str]: ...
def find_banned(text: str) -> list[str]: ...
def render_block(
    level: StyleLevel, hints: Sequence[str], *, spoken: bool = False, glossary: Sequence[str] = ()
) -> str: ...  # "" si level == "off"
```

## 2. Plan y grafo

- `build_plan(...)` recibe `style` y `style_hints` (calculados en `_turn_plan` con `style.level_for` y
  `style.suggest`, semilla del hilo y del turno).
- `_converse_messages` y el nodo de respuesta con búsqueda (`_answer_node`, `_answer_by_sentences`) agregan
  `style.render_block(plan.style, plan.style_hints, glossary=...)` después del plan.
- `update_conversation(..., expressions=find_expressions(answer), plain=wants_plain(message))` actualiza la memoria.

## 3. Bloque `<estilo>`

```text
<estilo>
nivel: neutral
acento: caleño (Santiago de Cali), profesional y cordial; tuteo, nunca voseo
expresiones sugeridas (usa como máximo una, solo si encaja): «listo pues», «qué bueno, ve», «a la orden»
dónde: al inicio o al cierre; nunca dentro de una cifra, una cita o un nombre
prohibido: groserías, modismos de otras regiones («parce»), voseo («vos», «mirá»)
glosario: «ve» = llamado de atención afectuoso, muy caleño
</estilo>
```

Con `spoken=True`, el bloque cambia «como máximo una» por «como máximo dos» y añade «ritmo: frases cortas y
cálidas, como se habla en Cali».

## 4. Prompts

- `converse.md` 1.2 y `agent.md` 1.11: sección «Estilo caleño» (obedece `<estilo>`; sin bloque, español neutro).
  Incluye ejemplos de uso profesional y la regla para explicar una expresión.
- `voice_script.md` 1.1: regla de estilo hablado con el bloque `<estilo>`.
- `style_judge.md` 1.0: califica `clarity` y `professionalism` de 1 a 5 por respuesta, en JSON.

## 5. `agent/review.py`

```python
STYLE_CHECKS = ("style_banned", "style_excess", "style_repeat", "style_off")


def style_issues(
    text: str, plan: TurnPlan | None, recent_expressions: Sequence[str], *, spoken: bool = False
) -> list[tuple[str, str]]: ...
```

`review()` agrega estos checks cuando `plan` no es `None`. `RETRIEVAL_CHECKS` suma `style_banned` y `style_off`,
y la frase se quita como hoy. `NOTES` trae una nota en español por check.

## 6. Voz

- `channels/voice.py` pasa `style.render_block(level, suggest(..., spoken=True), spoken=True)` al prompt del
  guion. Si el guion supera `max_spoken` o trae una vetada, se regenera una vez. Si sigue mal, se quitan las
  frases con la expresión vetada o excedente.
- `python -m proyecto_modelos_lenguaje.voice --audition [--out DIR]`:
  - sintetiza la frase de prueba con cada voz candidata y cada expresión hablada;
  - escribe `index.txt`;
  - termina con código 0, o 2 si falta el modelo o el token.

## 7. Evaluación

- `check_turn` soporta `style_used`, `no_banned`, `max_expressions`, `style_off`, `no_style_repeat` y
  `citations_kept`.
- `agent converse --style [--mode demo|real]` corre `caleno.jsonl` y escribe `docs/evaluacion_caleno.{md,json}`.
  Termina con 0 si cumple SC-001 a SC-005 y SC-008, y con 1 si no.
