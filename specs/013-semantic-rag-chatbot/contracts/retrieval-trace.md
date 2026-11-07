# Contract — Retrieval Trace y comandos del índice

**Feature**: `013-semantic-rag-chatbot` | **Date**: 2026-11-06

Este contrato define cómo la recuperación híbrida entra y sale del sistema. No cambia el contrato de
`TaskResult` del Módulo 1: lo **amplía** con una traza opcional y mantiene intactos `status`, `citations`,
`used_unit_ids` y los metadatos de modelo, tokens y latencia.

---

## 1. `POST /api/ask` — respuesta ampliada

### 1.1 Petición

Sin cambios respecto del Módulo 1:

```json
{
  "question": "¿Qué proyectos de agua tiene Manuelita?",
  "mode": "real"
}
```

`mode`: `real` | `demo`. `question`: 1–500 caracteres.

### 1.2 Respuesta

Se conservan todos los campos actuales y se añade `retrieval`.

```json
{
  "task": "qa",
  "status": "ok",
  "answer": "Manuelita desarrolla ... [U12]",
  "citations": [
    {
      "unit_id": "U12",
      "title": "Agua y comunidades",
      "url": "https://www.manuelita.com/...",
      "published_at": "2024-05-01"
    }
  ],
  "used_unit_ids": ["U12", "U31"],
  "omitted_unit_ids": ["U07"],
  "prompt_version": "qa-v3",
  "prompt_sha256": "…",
  "model": "deepseek-flash",
  "latency_seconds": 1.842,
  "input_tokens": 1830,
  "output_tokens": 210,
  "fallback": false,
  "review_required": false,
  "error": null,
  "retrieval": {
    "mode": "hybrid",
    "semantic_available": true,
    "candidates": 20,
    "threshold": 0.3,
    "elapsed_ms": 41.7,
    "notes": [],
    "fragments": [
      {
        "unit_id": "U12",
        "title": "Agua y comunidades",
        "url": "https://www.manuelita.com/...",
        "score": 0.87,
        "semantic_score": 0.91,
        "lexical_score": 0.78,
        "origin": "both",
        "status": "used",
        "reason": null
      },
      {
        "unit_id": "U07",
        "title": "Programa de reforestación",
        "url": "https://www.manuelita.com/...",
        "score": 0.55,
        "semantic_score": 0.71,
        "lexical_score": null,
        "origin": "semantic",
        "status": "omitted_budget",
        "reason": "Presupuesto de contexto agotado"
      },
      {
        "unit_id": "U88",
        "title": "Historia del ingenio",
        "url": "",
        "score": 0.19,
        "semantic_score": 0.19,
        "lexical_score": null,
        "origin": "semantic",
        "status": "omitted_threshold",
        "reason": "Similitud por debajo de 0.30 y sin coincidencia léxica"
      }
    ]
  }
}
```

### 1.3 Reglas

| Regla | Verificación |
|-------|--------------|
| `retrieval` es opcional en la respuesta: si la recuperación no se ejecutó, se omite | Contrato tolerante a ausencia |
| `used_unit_ids` == `[f.unit_id for f in retrieval.fragments if f.status == "used"]` | Prueba de contrato |
| `used_unit_ids` sin repetidos | Prueba unitaria (FR-005) |
| `retrieval.mode == "none"` ⇒ `status == "fallback"` (salvo pregunta inválida) | Prueba de integración |
| Índice ausente o inválido ⇒ `semantic_available=false` y `mode="lexical"`, sin error 500 | Prueba de integración |
| `mode="demo"` no requiere red ni índice real | Prueba de integración con fixture |

### 1.4 Errores

| Situación | HTTP | Cuerpo |
|-----------|------|--------|
| Pregunta vacía o > 500 caracteres | 422 | Validación estándar de FastAPI |
| Falla de generación con proveedor | 200 | `status="error"`, `error` con código, `retrieval` presente |
| Índice corrupto | 200 | `semantic_available=false`, `notes=["Índice ilegible; se usó recuperación léxica"]` |

---

## 2. CLI — `proyecto_modelos_lenguaje.rag`

### 2.1 `index build`

```bash
uv run python -m proyecto_modelos_lenguaje.rag index build [--force]
```

Construye el índice desde `data/gold/knowledge_units.jsonl` usando `config/retrieval.toml`.

| Salida | Significado |
|--------|-------------|
| `0` | Índice construido; imprime ruta, modelo, dimensión y recuento |
| `2` | Ya existe un índice con el mismo `gold_sha256` y perfil (sin `--force`) |
| `3` | No se encontró la capa de oro o está vacía |
| `4` | Error del modelo de embeddings (descarga, memoria) |

Garantías:

- No escribe en `data/bronze`, `data/silver` ni `data/gold`.
- Construye en directorio temporal y publica con renombrado atómico.
- Dos ejecuciones consecutivas con el mismo corpus y modelo producen el mismo `count` y
  `dimension` (SC-007).

### 2.2 `index verify`

```bash
uv run python -m proyecto_modelos_lenguaje.rag index verify
```

| Comprobación | Falla con |
|--------------|-----------|
| `manifest.json` cumple el esquema | `5` |
| `dimension` == ancho de `vectors.npy` | `5` |
| `count` == filas de la matriz == filas SQLite | `5` |
| `gold_sha256` del corpus actual == manifiesto | `6` (desactualizado, aviso) |
| Perfil configurado == perfil del manifiesto | `5` |

### 2.3 `index rebuild`

```bash
uv run python -m proyecto_modelos_lenguaje.rag index rebuild
```

Equivale a `build --force` con publicación atómica. Nunca elimina el índice anterior hasta que el nuevo
esté completo.

### 2.4 `search`

```bash
uv run python -m proyecto_modelos_lenguaje.rag search "¿cómo cuida Manuelita el agua?" [--mode hybrid|semantic|lexical] [--k 8]
```

Imprime la traza de recuperación **sin llamar al LLM**: modo, umbral, candidatos y fragmentos con
`score`, `origin` y `status`. Sirve para depurar la recuperación y para el quickstart.

| Salida | Significado |
|--------|-------------|
| `0` | Traza impresa (aunque no haya fragmentos sobre el umbral) |
| `5` | Índice ausente o inválido |

### 2.5 `evaluate`

```bash
uv run python -m proyecto_modelos_lenguaje.rag evaluate --questions tests/fixtures/rag/eval_questions.jsonl --out docs/evaluacion_modulo2.md
```

Salida JSON en `--json-out` (opcional) con:

```json
{
  "run_id": "2026-11-06-eval01",
  "k_values": [1, 3, 5, 8],
  "modes": {
    "semantic": {"recall_at_k": {"1": 0.62, "3": 0.78, "5": 0.85, "8": 0.89}, "mrr": 0.71},
    "lexical":  {"recall_at_k": {"1": 0.44, "3": 0.60, "5": 0.68, "8": 0.74}, "mrr": 0.53},
    "hybrid":   {"recall_at_k": {"1": 0.66, "3": 0.81, "5": 0.88, "8": 0.92}, "mrr": 0.74}
  },
  "citation_coverage": 1.0,
  "fidelity": 0.95,
  "baseline": "lexical",
  "verdict": "hybrid >= baseline en Recall@5 y MRR"
}
```

---

## 3. Contrato con las tareas existentes

`answer_question(...)` gana un parámetro opcional `retrieval: Retriever | None = None`:

- Si es `None`, se comporta exactamente como el Módulo 1 (selección léxica). Cero regresiones.
- Si se pasa, la `EvidenceSelection` proviene de la fusión híbrida y la traza se adjunta a
  `TaskResult`.
- `build_context`, `_parse_citations` y `_generate_with_citations` no cambian: siguen recibiendo
  `SelectedUnit` con `unit_id`, por lo que las citas `[U#]` siguen funcionando.

`TaskResult` gana un campo opcional `retrieval: RetrievalTrace | None = None` al final, con valor por
defecto `None` para no romper a los consumidores actuales (API, CLI, pruebas).

---

## 4. Contrato de la interfaz

La vista de respuesta muestra, bajo la respuesta:

1. Una insignia `Recuperación: híbrida / semántica / léxica / sin evidencia`.
2. La lista de fragmentos **usados** con título, fuente y `score`.
3. Un desplegable con los **descartados**, su `score` y su `reason`.
4. Avisos de `notes` cuando el índice esté desactualizado o el modelo no coincida.

Estados obligatorios: los fragmentos usados son visibles sin interacción; los descartados requieren
abrir el desplegable. En modo demostración, un distintivo persistente indica el modo.
