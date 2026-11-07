# ADR 0014 — Recuperación semántica local con fastembed y fusión híbrida

- **Estado**: aceptada
- **Fecha**: 2026-11-06
- **Autores**: Jason Alejandro Castaño
- **Contexto**: feature 013, Módulo 2 (embeddings, memoria y RAG)

## Contexto

El Módulo 1 responde con recuperación léxica (BM25 simplificada) sobre 15.211 unidades de oro. Es
determinista y gratuita, pero falla cuando la pregunta usa sinónimos o paráfrasis que no aparecen en el
texto. La constitución de la Fase 2 exige embeddings multilingües justificados por calidad, costo y
latencia, una base vectorial con persistencia reproducible, chunking documentado y métricas de
recuperación comparadas con la línea base.

## Decisión

1. **Modelo**: `intfloat/multilingual-e5-small`, 384 dimensiones, límite de 512 tokens, prefijos
   `query: ` y `passage: `, normalización L2.
2. **Runtime**: `fastembed` 0.9 sobre ONNX Runtime, con import perezoso y registro del modelo como
   personalizado cuando el catálogo no lo incluye.
3. **Base vectorial**: matriz `vectors.npy` (float32, filas normalizadas) + `index.sqlite3` con los
   metadatos de cada fragmento + `manifest.json` con modelo, dimensión, normalización, recuento, hash
   de la capa de oro y fecha. Búsqueda exacta por producto punto.
4. **Chunking**: se reutilizan las unidades de oro como fragmentos; solo se trocean las que exceden
   512 tokens (ventanas de 480 con 32 de solape), heredando el `unit_id` para conservar la cita.
5. **Fusión**: `0.65 × semántica + 0.35 × léxica + 0.05` si la unidad aparece en ambos modos, con
   umbral de similitud 0.30, deduplicación por `unit_id` y por similitud > 0.98, y presupuesto de
   contexto del Módulo 1.
6. **Artefacto**: `data/module2/index/` queda fuera de Git; se versiona un índice de prueba de 50
   unidades en `tests/fixtures/rag/` para la suite y el modo demostración.
7. **Degradación**: si el índice falta o no es válido, la app responde con recuperación léxica y lo
   declara en la traza; nunca falla la petición por el índice.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| `sentence-transformers` + PyTorch | Añade ~2 GB descomprimidos; el equipo ya tuvo restricciones de espacio. |
| `BAAI/bge-m3` (1024 d) | Mejor calidad, pero 2 GB y vectores 2,7× más grandes para 15k unidades. |
| API de embeddings de un tercero | Envía todo el corpus fuera, agrega costo por consulta y rompe la demo offline. |
| Chroma / FAISS / pgvector | Servicio o formato opaco para un índice de 23 MB que cabe en memoria. |
| Solo semántica | Regresión en cifras, siglas y nombres propios frente a la línea base léxica. |
| Reranking con cross-encoder | Fuera de alcance de la Fase 2; se anota como mejora futura. |

## Consecuencias

- Nuevas dependencias: `fastembed` y `numpy`; descarga única del modelo (~120 MB) cacheada por
  fastembed.
- El corpus no sale del equipo: los embeddings se calculan en local.
- La suite sigue sin red: usa `HashEmbedder` y el índice de prueba.
- La evaluación pasa a ser parte del flujo: `rag evaluate` produce Recall@k y MRR por modo.
- El índice debe reconstruirse si cambia el modelo, la dimensión o la capa de oro; el manifiesto lo
  detecta.

## Validación

- `uv run pytest -q` y `uv run ruff check .` en verde.
- `rag index build` + `rag index verify` sobre las 15.211 unidades.
- `docs/evaluacion_modulo2.md`: híbrido con Recall@5 0,600 y MRR 0,450 frente a 0,371 y 0,320 de la
  línea base léxica; sin regresión en Recall@1 ni Recall@3.
- `tests/integration/test_rag_api.py` cubre traza, citas, fallback, deduplicación y demo sin red.
