# Prompt log del Módulo 1

Registro de las versiones de prompt, sus parámetros y las salidas observadas en M1-05. Todas las cifras
provienen de ejecuciones reales; no se estiman a mano.

## 1. Prompts versionados

| Tarea | Archivo | Versión | SHA-256 (12 primeros) | Secciones |
|-------|---------|---------|-----------------------|-----------|
| Q&A | `prompts/qa.md` | 1.0 | `d09765504709` | rol, tarea, contexto, reglas, formato de cita, sin evidencia |
| Resumen | `prompts/summary.md` | 1.0 | `f6cd198ba529` | idem |
| FAQ | `prompts/faq.md` | 1.0 | `9bafea161abb` | idem |

El hash completo se registra en cada resultado (`prompt_sha256`) y se puede reproducir con
`uv run python -c "from proyecto_modelos_lenguaje.tasks import load_prompt; print(load_prompt('qa').sha256)"`.

## 2. Parámetros

| Parámetro | Valor | Origen |
|-----------|-------|--------|
| `qa.top_k` | 8 | `config/tasks.toml` |
| `qa.token_budget` | 6.000 | `config/tasks.toml` |
| `qa.min_score` | 0.0 | `config/tasks.toml` |
| `summary.pack` | `8000` | `config/tasks.toml` |
| `summary.min_citations` | 8 (máximo efectivo 12) | `config/tasks.toml` |
| `faq.limit` | 12 | `config/tasks.toml` |
| `faq.top_k` | 5 | `config/tasks.toml` |
| `faq.min_citations` | 1 | `config/tasks.toml` |
| `faq.question_max_chars` | 500 | `config/tasks.toml` |
| `llm.model` | `llama3.1:8b` | `config/llm.toml` |
| `llm.temperature` | 0.1 | `config/llm.toml` |
| `llm.max_output_tokens` | 1.024 | `config/llm.toml` |

## 3. Ejecuciones observadas

### 3.1 Modelo falso (offline, 2026-10-30)

| Tarea | Estado | Citas | Unidades usadas | Entrada (tok) | Salida (tok) | Modelo |
|-------|--------|-------|-----------------|---------------|--------------|--------|
| Q&A | ok | 2 | 8 | 894 | 24 | `scripted-fake` |
| Resumen 8k | ok | 10 | 12 | 872 | 163 | `scripted-fake` |
| FAQ (12) | 12 × ready | 12 × ≥1 | — | — | — | `scripted-fake` |

Comandos:

```bash
uv run python -m proyecto_modelos_lenguaje.tasks qa --question "¿Qué productos ofrece Manuelita?" --fake --json
uv run python -m proyecto_modelos_lenguaje.tasks summary --fake --json
uv run python -m proyecto_modelos_lenguaje.tasks faq --limit 12 --fake --json
```

### 3.2 Modelo real (Ollama, 2026-10-30)

Modelo disponible en el equipo: `qwen3.5:4b` (el `llama3.1:8b` de `config/llm.toml` no estaba
descargado). Se ejecutó con el razonamiento desactivado para que el presupuesto de salida no se
consumiera en el bloque de pensamiento.

| Tarea | Estado | Citas | Latencia | Respuesta observada (extracto) |
|-------|--------|-------|----------|-------------------------------|
| Q&A «¿Qué productos ofrece Manuelita?» | ok | 2 (`U5`, `U1`) | 2,91 s | «Manuelita produce azúcar, etanol y biocombustibles [U5]. Además, su línea de alimentos incluye azúcar refinada y productos derivados de la caña [U1].» |
| Resumen 8k | ok | 12 | 4,01 s | Encabezados por bloque (identidad, operación, casa matriz) con citas `[U#]` y paquete declarado. |

Hallazgo registrado: con un modelo de razonamiento y `max_output_tokens=1024` el modelo devolvió
contenido vacío con `done_reason=length`; el sistema lo reporta como `model_error` con instrucción
accionable (aumentar `llm.max_output_tokens` o usar un modelo sin razonamiento).

## 4. Pendiente

- Repetir las tres tareas con `llama3.1:8b` y con el corpus de oro real para completar la línea base de
  M1-06 y la comparación de M1-08.
- Registrar la variante final de prompts tras el ajuste con evidencia (M1-09).

## 5. Observaciones sobre el corpus real (15.211 unidades)

Primera ejecución sobre `data/gold` real (2026-10-30, modelo falso, sin ajuste de prompts):

- `¿Qué productos ofrece Manuelita?` devuelve 8 unidades; la primera es de tema `productos` pero su texto
  es una plantilla de formulario («Enviar información sobre ofertas…»). La segunda sí aporta catálogo.
- `¿Dónde está la casa matriz de Manuelita?` devuelve como primera unidad un texto literal sobre la
  localización de la casa matriz; el resto incluye ruido de fundación y certificaciones.
- `¿Qué certificaciones tiene Manuelita?` acierta el tema en la primera unidad («Manuelita obtiene
  certificación del IIA»).

Conclusión para M1-08/M1-09: la puntuación léxica ordena por tema, pero el corpus contiene páginas de
plantilla y navegación que compiten con el contenido sustantivo. Candidatos de ajuste, en este orden:
(1) penalizar unidades con `unit_type=passage` de baja densidad informativa y textos de formulario,
(2) exigir cobertura de varios términos de la pregunta además de la frecuencia, y (3) revisar el peso del
tema frente a la coincidencia léxica. No se ajusta todavía porque la decisión debe basarse en la
evaluación de 40 preguntas.

