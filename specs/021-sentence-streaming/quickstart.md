# Quickstart: validar la entrega por frases (spec 021)

## Requisitos

- `make dev` hecho. Para el modo real, `DEEPSEEK_API_KEY` en `.env` y **saldo**: `llm --check` no detecta la falta
  de saldo, así que conviene generar texto real antes (spec 020, nota de T060).
- La web compilada (`cd web && npm run build`). Verifica que `web/dist/assets` tenga el CSS, porque un build
  interrumpido deja la página sin estilos.

## 0. Línea base

Con `[conversation] delivery = "complete"` (equivale a la spec 020):

```bash
uv run python -m proyecto_modelos_lenguaje.agent converse --mode real --variants chain agent --repeats 10 \
    --json-out docs/evaluacion_conversacion_base.json
```

En la corrida de la spec 020, el p90 hasta la primera palabra en conversación fue de 5.9–6.3 s.

**Línea base registrada (2026-11-20, `docs/evaluacion_conversacion.json` de la spec 020)**:

| Variante | p90 primera palabra, turnos sin búsqueda | p90 primera palabra, todos los turnos |
|----------|-------------------------------------------|---------------------------------------|
| cadena | 5875 ms | 7447 ms |
| agente | 6300 ms | 12490 ms |

El tiempo hasta la respuesta completa no se midió en la spec 020; se mide en T032 con `--baseline-delivery`.
`make check` estaba en verde antes de los cambios (1183 pruebas de Python y 104 de Vitest).

## 1. Pruebas sin red

```bash
uv run pytest tests/unit/agent/test_sentences.py
uv run pytest tests/integration/agent/test_sentence_flow.py tests/api/test_sentence_stream.py
uv run pytest tests/integration/agent/test_converse_flow.py tests/integration/agent/test_care_eval.py
cd web && npx vitest run src/test/ChatView.test.tsx src/test/ChatViewVoice.test.tsx src/test/voice.test.ts \
    src/test/ContactRecordPanel.test.tsx
```

Esperado: todo en verde. Las pruebas del flujo verifican G1–G4 de
[contracts/streaming.md](./contracts/streaming.md) §1 en las dos variantes.

## 2. Evaluación

```bash
uv run python -m proyecto_modelos_lenguaje.agent converse --mode demo --variants chain agent
uv run python -m proyecto_modelos_lenguaje.agent converse --mode real --variants chain agent \
    --baseline --baseline-delivery --simulate --repeats 10 --json-out docs/evaluacion_conversacion.json
uv run python -m proyecto_modelos_lenguaje.agent care --mode real --variants chain agent
uv run python -m proyecto_modelos_lenguaje.agent conduct --mode real --variants chain agent
```

Las metas están en [contracts/streaming.md](./contracts/streaming.md) §6.

## 3. Recorrido manual

```bash
uv run uvicorn proyecto_modelos_lenguaje.api:app --port 8000   # web/dist ya compilada
```

En http://127.0.0.1:8000/?vista=tecnica:

1. «¡qué calor hace hoy en Cali!» → la primera frase aparece pronto y el resto llega frase por frase.
2. «¿qué produce Manuelita?» → frases con citas, una por una.
3. Con la voz activada, la lectura empieza con la primera frase.
4. «ya no quiero vivir» → la respuesta fija de crisis, igual que hoy.
5. La línea «Actos» del registro muestra `✂N` si hubo frases descartadas.

Con `[conversation] delivery = "complete"` vuelve el comportamiento de la spec 020.
