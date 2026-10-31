# Contrato de interfaz — Tareas LangChain del Módulo 1

**Feature**: `007-langchain-qa-tasks`
**Versión**: 1.0
**Fecha**: 2026-10-30

## 1. Sinopsis

```text
uv run python -m proyecto_modelos_lenguaje.tasks summary [--pack 8000|32000] [--fake] [--json]
uv run python -m proyecto_modelos_lenguaje.tasks faq [--limit 10..20] [--fake] [--json]
uv run python -m proyecto_modelos_lenguaje.tasks qa --question "..." [--fake] [--json]
```

La interfaz de biblioteca es la misma que usa la app: `summarize_corpus`, `generate_faq` y
`answer_question`. El CLI es un medio de validación y de generación para el prompt log; no es la app.

## 2. Opciones

| Opción | Aplica a | Por defecto | Descripción |
|--------|----------|-------------|-------------|
| `--question TEXTO` | `qa` | — | Pregunta del usuario; obligatoria |
| `--pack 8000\|32000` | `summary` | `8000` | Paquete de contexto de oro |
| `--limit N` | `faq` | `12` | Número de preguntas frecuentes; entre 10 y 20 |
| `--config RUTA` | todas | `config/tasks.toml` | Configuración de tareas |
| `--fake` | todas | `false` | Usa el modelo falso, sin red |
| `--json` | todas | `false` | Emite un único objeto JSON |
| `--help` | todas | — | Muestra ayuda |

## 3. Salida humana

```text
Tarea: qa
Estado: ok
Respuesta: Manuelita produce azúcar, etanol y biocombustibles. [U1]
Fuentes:
  [U1] Manuelita — Productos — https://www.manuelita.com/... (sección: Productos)
Modelo: llama3.1:8b
Prompt: qa v1.0
Latencia: 8.4 s
Tokens: entrada=1200 salida=180
```

En `fallback`:

```text
Tarea: qa
Estado: fallback
Respuesta: No hay evidencia suficiente en el corpus para responder.
Fuentes: —
```

## 4. Salida JSON

### 4.1 Éxito

```json
{
  "schema_version": "1.0",
  "task": "qa",
  "status": "ok",
  "answer": "Manuelita produce azúcar, etanol y biocombustibles. [U1]",
  "citations": [
    {
      "label": "U1",
      "unit_id": "unit_0123456789abcdef",
      "title": "Manuelita — Productos",
      "url": "https://www.manuelita.com/manuelita-productos",
      "section_path": ["Productos"],
      "page_start": null,
      "page_end": null,
      "time_start": null,
      "time_end": null,
      "authority": "first_party",
      "citation": "Manuelita — Productos — https://www.manuelita.com/manuelita-productos (sección: Productos)"
    }
  ],
  "used_unit_ids": ["unit_0123456789abcdef"],
  "omitted_unit_ids": [],
  "prompt_version": "1.0",
  "prompt_sha256": "a1b2c3...",
  "model": "llama3.1:8b",
  "latency_seconds": 8.4,
  "input_tokens": 1200,
  "output_tokens": 180,
  "fallback": false,
  "review_required": false,
  "error": null
}
```

Esquema: [task-result.schema.json](./task-result.schema.json).

### 4.2 Fallback

```json
{
  "schema_version": "1.0",
  "task": "qa",
  "status": "fallback",
  "answer": "No hay evidencia suficiente en el corpus para responder.",
  "citations": [],
  "used_unit_ids": [],
  "omitted_unit_ids": [],
  "prompt_version": "1.0",
  "prompt_sha256": "a1b2c3...",
  "model": "llama3.1:8b",
  "latency_seconds": 0.0,
  "input_tokens": 0,
  "output_tokens": 0,
  "fallback": true,
  "review_required": false,
  "error": null
}
```

### 4.3 Error controlado

```json
{
  "schema_version": "1.0",
  "task": "qa",
  "status": "error",
  "answer": "No se pudo generar una respuesta con citas válidas.",
  "citations": [],
  "used_unit_ids": ["unit_0123456789abcdef"],
  "omitted_unit_ids": [],
  "prompt_version": "1.0",
  "prompt_sha256": "a1b2c3...",
  "model": "llama3.1:8b",
  "latency_seconds": 8.4,
  "input_tokens": 1200,
  "output_tokens": 0,
  "fallback": false,
  "review_required": true,
  "error": "missing_citations"
}
```

### 4.4 FAQ

La salida de `faq --json` es una lista de objetos validados contra
[faq-item.schema.json](./faq-item.schema.json).

## 5. Códigos de salida

| Código | Significado |
|-------:|-------------|
| `0` | Resultado generado, incluido `fallback` |
| `1` | Error controlado del modelo o de la tarea |
| `2` | Error de uso o configuración |

## 6. Garantías

1. **Solo oro**: las unidades y paquetes provienen de `data/gold/`; no se consultan fuentes externas.
2. **Citas verificables**: toda cita corresponde a una unidad seleccionada.
3. **Fallback**: sin evidencia, se declara y no se inventa.
4. **Contexto no confiable**: las instrucciones embebidas no se ejecutan.
5. **Sin embeddings**: la recuperación es léxica y determinista.
6. **Reproducibilidad**: versión y hash de prompt, modelo y configuración en cada resultado.
7. **Sin secretos**: la salida no incluye claves ni rutas absolutas.

## 7. Fuera de contrato

- No es la app Streamlit.
- No evalúa las 40 preguntas.
- No crea embeddings ni base vectorial.
- No modifica bronce, plata ni oro.
- No genera imágenes, audio ni traducciones.
