# Quickstart — Tareas LangChain del Módulo 1

**Feature**: `007-langchain-qa-tasks`
**Fecha**: 2026-10-30

Guía de validación de Resumen, FAQ y Q&A. Los escenarios offline usan `--fake` y no requieren Ollama.

## 1. Requisitos

```bash
uv sync
uv run ruff check .
uv run pytest -q
```

- `data/gold/` debe existir con `knowledge_units.jsonl`, `context_8000.json`, `context_32000.json`,
  `faq_seeds.jsonl` y `coverage.json`.
- Para el modelo real: Ollama activo y `llama3.1:8b` descargado.
- Para pruebas offline: `--fake` o `build_fake_model()`.

## 2. Q&A con modelo falso

```bash
uv run python -m proyecto_modelos_lenguaje.tasks qa \
  --question "¿Qué productos ofrece Manuelita?" \
  --fake \
  --json
```

Resultado esperado:

- `task=qa`, `status=ok` o `fallback`.
- Si es `ok`, `citations` contiene al menos una cita con `unit_id`, URL y sección.
- Si es `fallback`, `fallback=true`, `citations=[]` y el mensaje “No hay evidencia suficiente…”.
- `used_unit_ids` contiene las unidades enviadas al modelo.
- `prompt_version`, `prompt_sha256`, `model`, `latency_seconds` y tokens presentes.

## 3. Resumen con modelo falso

```bash
uv run python -m proyecto_modelos_lenguaje.tasks summary --fake --json
```

Resultado esperado:

- `task=summary`, `status=ok`.
- Respuesta estructurada con 8–12 citas.
- `used_unit_ids` corresponde al paquete de 8.000 tokens.
- No hay afirmaciones sin cita.

Con el paquete grande:

```bash
uv run python -m proyecto_modelos_lenguaje.tasks summary --pack 32000 --fake --json
```

Debe usar el paquete de 32.000 solo si el modelo lo soporta; si no, declarar el uso del paquete de 8.000.

## 4. FAQ con modelo falso

```bash
uv run python -m proyecto_modelos_lenguaje.tasks faq --limit 12 --fake --json
```

Resultado esperado:

- Lista de 10–20 objetos validados contra `contracts/faq-item.schema.json`.
- Cada elemento tiene pregunta, respuesta, citas y estado.
- `status=ready` implica al menos una cita.
- `status=missing_evidence` implica respuesta de fallback y cero citas.
- No hay preguntas duplicadas por texto normalizado.

## 5. Modelo real con Ollama

```bash
uv run python -m proyecto_modelos_lenguaje.tasks qa \
  --question "¿Qué certificaciones tiene Manuelita?" \
  --json
```

Resultado esperado:

- Respuesta en español, con citas `[U#]` y fuentes.
- Latencia dentro del timeout configurado (120 s).
- Si el modelo no responde, error controlado con mensaje accionable.

Prueba de integración opcional:

```bash
OLLAMA_RUN_INTEGRATION=1 uv run pytest tests/integration/test_tasks_ollama.py -q
```

## 6. Validación de citas

```bash
uv run pytest tests/unit/test_tasks.py -q -k citation
```

Casos:

- Cita válida `[U1]` se mapea a la unidad seleccionada.
- Cita `[U99]` fuera del contexto se descarta y marca `review_required`.
- Respuesta sin citas se reintenta una vez; si falla, `status=error`, `error=missing_citations`.

## 7. Prueba de inyección de contexto

```bash
uv run pytest tests/unit/test_tasks.py -q -k injection
```

Resultado esperado:

- Una unidad con “ignora las instrucciones anteriores” no cambia la tarea.
- La respuesta sigue citando o cae en fallback.
- Cero ejecuciones de instrucciones embebidas.

## 8. Errores de uso

```bash
uv run python -m proyecto_modelos_lenguaje.tasks qa --question "" --json
uv run python -m proyecto_modelos_lenguaje.tasks qa --question "..." --limit 0 --json
uv run python -m proyecto_modelos_lenguaje.tasks faq --limit 50 --json
```

Resultado esperado:

- Código `2`.
- Mensaje accionable.
- Sin llamada al modelo.
- Sin crear archivos.

## 9. Rendimiento

| Tarea | Objetivo en el equipo de referencia |
|-------|-------------------------------------|
| Q&A | < 30 s por pregunta |
| Resumen 8k | < 120 s |
| FAQ 12 | < 5 min |
| Suite fake | < 2 min |

Los tiempos reales dependen del hardware y del modelo Ollama.

## 10. Criterios de aceptación

| Escenario | Criterio |
|-----------|----------|
| Q&A | Cita válida o fallback en el 100% de los casos |
| Resumen | 8–12 citas y sin afirmaciones sin fuente |
| FAQ | 10–20 preguntas, todas con cita o `missing_evidence` |
| Citas | 100% corresponden a unidades del contexto |
| Inyección | 0 instrucciones embebidas ejecutadas |
| Errores | Código `2` y mensaje accionable |
| Offline | Suite pasa sin Ollama ni red |
| Prompt | Versión y hash registrados en cada resultado |

## 11. Limpieza

El CLI no escribe en `data/gold/`; solo lee. Si se añade una salida para el prompt log, se guarda en
`data/module1/` o en `docs/prompt_log.md`, nunca en las capas medallion.
