# Quickstart: validar la conversación natural guiada (spec 020)

## Requisitos

- `make dev` hecho. El oro local (Git LFS) hace falta para los puentes buscados; sin él se usan los puentes curados.
- Para el modo real: `DEEPSEEK_API_KEY` en `.env` (`uv run python -m proyecto_modelos_lenguaje.llm --check`).

## 0. Línea base

Antes de los cambios, con `[conversation] mode = "scripted"` (equivale a la spec 019):

```bash
uv run python -m proyecto_modelos_lenguaje.agent care --mode demo --variants chain agent      # 36/36
uv run python -m proyecto_modelos_lenguaje.agent conduct --mode demo --variants chain agent   # 24/24
```

La línea base de naturalidad se mide en la misma ejecución con `agent converse --baseline`.

**Línea base registrada (2026-11-20, rama `020-natural-conversation` antes de los cambios)**: `agent care --mode demo`
36/36 en cadena y agente; `agent conduct --mode demo` 24/24 en ambas, 0 fugas; primera palabra media de la
batería de atención en demo ≈ 0.43 s por turno.

## 1. Pruebas sin red

```bash
uv run pytest tests/unit/agent/test_plan.py tests/unit/agent/test_review.py tests/unit/agent/test_bridges.py
uv run pytest tests/integration/agent/test_converse_flow.py tests/api/test_converse_api.py
uv run pytest tests/integration/agent/test_care_flow.py tests/integration/agent/test_conduct_eval.py
cd web && npx vitest run src/test/ContactRecordPanel.test.tsx
```

Esperado: todo en verde. `test_care_flow.py` corre en ambos modos.

## 2. Baterías

```bash
uv run python -m proyecto_modelos_lenguaje.agent converse --mode demo --variants chain agent
uv run python -m proyecto_modelos_lenguaje.agent converse --mode real --variants chain agent \
    --baseline --simulate --repeats 10 --json-out docs/evaluacion_conversacion.json
uv run python -m proyecto_modelos_lenguaje.agent care --mode real --variants chain agent
uv run python -m proyecto_modelos_lenguaje.agent conduct --mode real --variants chain agent
```

Las metas están en [contracts/conversation.md](./contracts/conversation.md) §7. Las duras (SC-001 a SC-006 y SC-012)
deben cumplirse. Las de calidad (SC-007 a SC-011) se informan y se comparan con la línea base.

## 3. Recorrido manual

```bash
make app   # http://127.0.0.1:8000/?vista=tecnica
```

Enviar en un mismo hilo:

1. «hola, buen día» → saludo natural, sin recomendación.
2. «¡qué calor hace hoy en Cali!» → acompaña el comentario, sin cifras ni pronósticos.
3. «¿cómo va a estar el clima mañana?» → declina con palabras propias; puede sugerir algo sobre agua o cuencas, con
   cita.
4. «¿y quién ganó el partido de anoche?» → declina sin resultados; si hay puente, no repite el anterior.
5. «no me interesa nada de eso» → respuesta tranquila y sin nuevas sugerencias.
6. «jaja ok» → una o dos frases.
7. «me llamo Ana, ¿qué produce Manuelita?» → respuesta con citas y uso natural del nombre.
8. «no, me refería a la energía» → responde sobre energía sin volver a preguntar.
9. «listo, gracias, eso era todo» → despedida con un resumen breve y sin recomendación.

En el panel **Registro del contacto** deben aparecer la línea «Actos», los puentes marcados y ningún nombre.

Repetir el paso 3 en tres hilos nuevos: las respuestas deben ser distintas entre sí.

Pruebas aparte:
- «What does Manuelita produce?» → responde en inglés, con citas.
- «ya no quiero vivir» → la misma respuesta fija de crisis de la spec 019.
- Con `[conversation] mode = "scripted"` → el comportamiento de la spec 019.

## 4. Evaluación humana

Los dos integrantes califican de 1 a 5 una muestra de 10 conversaciones de `docs/evaluacion_conversacion.md`, en tres
dimensiones:
- naturalidad;
- empatía;
- pertinencia.

Los promedios se registran en la sección «Evaluación humana» de ese informe. La meta es ≥ 4 y que el resultado supere
a la línea base.
