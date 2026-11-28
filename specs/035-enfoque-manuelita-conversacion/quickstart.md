# Quickstart: validar el enfoque en Manuelita (spec 035)

## 1. Sin red

```powershell
uv run pytest tests/unit/agent -k "review or plan or converse or opening"
uv run python -m proyecto_modelos_lenguaje.agent converse --focus --mode demo
make check
```

**Esperado**:

- todo en verde;
- `--focus` en demo con 0 turnos marcados por `offtopic_question`, `chat_invite`, `no_redirect`, `rejection` o
  `closing_repeat`.

## 2. Con el modelo real (medición SC-001 a SC-006)

```powershell
uv run python -m proyecto_modelos_lenguaje.agent converse --focus --mode real
uv run python -m proyecto_modelos_lenguaje.agent converse --mode real   # regresión de empatía y naturalidad
```

**Esperado**:

- en las 16 conversaciones de `focus.jsonl`: 0 invitaciones a charlar, 0 preguntas ajenas, 100 % de las
  respuestas ajenas con regreso a Manuelita, 0 cierres repetidos y como máximo dos frases desde la racha 3;
- la empatía del juez no baja respecto a `docs/evaluacion_conversacion.json`.

## 3. En el teléfono (después de reiniciar el backend)

Repetir la conversación de la prueba: «Hola» → «Bien, ¿y tú?» → «Charlemos un rato» → «Hoy fui a un partido de
fútbol» → «Mi equipo no ganó» → «¿Quieres saber cuál es mi equipo?» → «Soy hincha de un equipo de fútbol».

**Esperado**:

- cortesía en una frase y regreso a Manuelita en cada turno, con temas concretos o un dato con fuente
  (por ejemplo, la Fundación Manuelita);
- sin preguntas sobre el partido ni el equipo;
- sin «charlar también se vale» ni «mejor no me cuentes»;
- sin repetir la frase de cierre.
