# ADR 0007 — Tareas LangChain del Módulo 1: recuperación léxica, citas y prompts versionados

- **Fecha**: 2026-10-30
- **Estado**: Aceptada
- **Contexto**: M1-05 (spec `007-langchain-qa-tasks`). Resumen, FAQ y Q&A sobre la capa de oro, con
  un modelo local de Ollama y sin embeddings.

## Contexto

El Módulo 1 exige tres tareas (Resumen, FAQ y Q&A) con respuestas citadas y sin alucinaciones, sobre
15.211 unidades de oro. La constitución prohíbe embeddings y bases vectoriales, y obliga a registrar
prompt, modelo y resultados. Los datos de oro aún no se generan en este repositorio (`data/gold/` no
se versiona), por lo que la suite debe poder validarse sin corpus real.

## Decisión

1. **Recuperación léxica determinista** (`retrieval.py`): BM25 simplificado sobre tokens normalizados
   (minúsculas, sin acentos ni puntuación) más tema, entidades y señales de calidad. Selección con
   diversidad por tema (uno por tema, luego un segundo, etc.), presupuesto de tokens y etiquetas
   `U1..Un` consecutivas. Sin embeddings ni dependencias nuevas.
2. **Citas locales `[U#]`**: el contexto se entrega delimitado (`<context><unit id="U1">…</unit>`), el
   modelo cita la etiqueta y el sistema la resuelve a `unit_id`, URL y sección. Las citas fuera del
   contexto se descartan y marcan `review_required=True`; `status` pasa a `review`.
3. **Prompts versionados** (`prompts/{summary,faq,qa}.md`): seis secciones obligatorias (rol, tarea,
   contexto, reglas, formato, sin evidencia), marcador `<!-- prompt_version: 1.0 -->` y SHA-256 del
   contenido registrado en cada resultado.
4. **Fallback explícito**: sin evidencia no se llama al modelo; se devuelve `status=fallback`,
   `citations=[]` y «No hay evidencia suficiente en el corpus para responder.». Tras dos intentos sin
   citas (una reintento estricto) el resultado es `status=error`, `error=missing_citations`.
5. **Modelo falso por defecto en pruebas**: `ScriptedTaskModel` cita las unidades que recibe; `--fake`
   usa el mismo modelo. La suite no usa red ni consume tokens. La prueba real con Ollama es opcional
   (`OLLAMA_RUN_INTEGRATION=1`).
6. **Configuración externa** (`config/tasks.toml`): top-k 8, presupuesto 6.000 tokens, paquete de
   resumen 8.000 (32.000 solo si la ventana del modelo lo soporta), FAQ de 12 preguntas y máximo de
   500 caracteres por pregunta.
7. **Interfaz de biblioteca + CLI**: `answer_question`, `summarize_corpus` y `generate_faq` son la API
   que consumirán la app (M1-07) y la evaluación (M1-08). El CLI `python -m
   proyecto_modelos_lenguaje.tasks` sirve para validación y para alimentar el prompt log.

## Consecuencias

- **Positivas**: reproducible y auditable (hash de prompt, modelo, latencia y tokens en cada salida);
  explicable sin caja negra; sin coste de red en CI; el fallback evita respuestas inventadas.
- **Negativas**: la recuperación léxica puede perder paráfrasis; el corpus real aún no existe, así que
  la calidad debe medirse en M1-08 y ajustarse en M1-09.
- **Desviaciones documentadas**:
  - El contrato no define un campo para el paquete de contexto usado, y el esquema prohíbe propiedades
    adicionales: se declara en la primera línea de `answer` del resumen
    (`**Paquete de contexto:** 8000 tokens`).
  - Los errores de uso o configuración (`empty_question`, `question_too_long`, `invalid_config`) se
    emiten como la entidad `TaskError` del modelo de datos (código, mensaje, tarea, revisión), no como
    `TaskResult`, porque no existe prompt ni selección que registrar.
  - `PML_GOLD_DIR` permite apuntar a una capa de oro alternativa sin ampliar la superficie del CLI; se
    usa en pruebas y en CI mientras `data/gold/` no exista.
  - Si hay menos semillas disponibles que el límite, la FAQ devuelve las semillas existentes en lugar de
    inventar preguntas; el rango 10–20 se valida sobre el límite solicitado.

## Alternativas consideradas

| Alternativa | Por qué no |
|-------------|------------|
| Embeddings o base vectorial | Prohibidos por la constitución del Módulo 1 y añaden dependencias. |
| `rank_bm25` | Dependencia innecesaria para una puntuación explicable y testeable. |
| Prompts embebidos en Python | Dificultan la revisión y el versionado que exige la constitución. |
| Devolver la respuesta sin citas | Viola la trazabilidad y permite alucinaciones de fuente. |
| Confiar en el modelo para ignorar instrucciones del contexto | No es verificable; se delimita el contexto y se prueba la inyección. |

## Evidencia

- `tests/unit/test_retrieval.py`, `tests/unit/test_tasks.py`, `tests/contract/test_tasks_contract.py`,
  `tests/integration/test_tasks_fake.py` y `tests/integration/test_tasks_ollama.py`.
- `uv run ruff check .` limpio y `uv run pytest` en verde (suite offline).
- Validación manual con modelo real en `docs/prompt_log.md`.
