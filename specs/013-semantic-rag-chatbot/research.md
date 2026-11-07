# Phase 0 — Research: Chatbot con recuperación semántica (RAG)

**Feature**: `013-semantic-rag-chatbot` | **Date**: 2026-11-06

Este documento resuelve las incógnitas técnicas del plan. Cada decisión sigue el formato
Decisión / Justificación / Alternativas descartadas.

---

## R1. Modelo de embeddings

**Decisión**: `intfloat/multilingual-e5-small` (384 dimensiones, 512 tokens, prefijos `query: ` y
`passage: `), ejecutado en local con ONNX Runtime.

**Justificación**:

- Es **multilingüe y entrenado para recuperación**: la familia E5 se entrenó con pares
  pregunta/respuesta, no solo con similitud de frases, y rinde en español sin ajuste.
- **384 dimensiones**: 15.211 unidades × 384 × 4 bytes ≈ 23 MB. Cabe en memoria y la búsqueda es un
  producto punto vectorizado.
- **Costo**: cero por consulta; el corpus no sale del equipo. La descarga del modelo (~120 MB) se hace
  una sola vez y se cachea.
- **Latencia**: en CPU, embeber una pregunta es una inferencia de un texto corto (decenas de ms);
  embeber las 15.211 unidades es un proceso por lotes que se hace una vez al construir el índice.
- **Límite de 512 tokens**: suficiente para las unidades de oro (fragmentos ya atómicos); las que
  excedan se trocean (R3).

**Alternativas descartadas**:

| Alternativa | Motivo del descarte |
|-------------|---------------------|
| `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` | Buena similitud de frases, pero peor en recuperación pregunta→pasaje que E5; además arrastra PyTorch. |
| `BAAI/bge-m3` | Excelente calidad, pero 1024 dimensiones y ~2 GB: desproporcionado para 15k unidades y este equipo. |
| API de embeddings de un tercero | Enviaría todo el corpus fuera, añade costo por consulta y dependencia de red; el modo demostración dejaría de ser offline. |
| TF-IDF / BM25 "disfrazado de semántica" | Es lo que ya hace el Módulo 1; no resuelve sinónimos ni paráfrasis. |

---

## R2. Biblioteca de embeddings

**Decisión**: `fastembed` (ONNX Runtime), registrando el modelo como modelo personalizado cuando no
esté en el catálogo.

**Justificación**:

- ONNX Runtime pesa decenas de MB frente a ~2 GB de PyTorch descomprimido. El proyecto ya tuvo
  problemas de espacio en disco, así que **no introducir PyTorch es un requisito de facto**.
- `fastembed` expone `TextEmbedding.embed()` por lotes y `add_custom_model()` con `dim`, `pooling` y
  `normalization`, exactamente lo que exige la constitución (registrar dimensión y normalización).
- Sin GPU: usa CPU por defecto, que es el objetivo.

**Alternativas descartadas**: `sentence-transformers` (PyTorch, instalación pesada), `onnxruntime`
crudo con `tokenizers` (más código propio que mantener), `transformers` (mismo problema de tamaño).

**Verificación en la primera tarea**: confirmar que el modelo descarga y produce 384 dimensiones; si
el catálogo no lo trae, se registra con `add_custom_model` (el README de fastembed documenta ese
caso con este modelo exacto).

---

## R3. Chunking

**Decisión**: se reutilizan las **unidades de oro** como fragmentos. No se crea un chunking nuevo.

**Justificación**:

- Las unidades de oro ya son fragmentos extractivos, atómicos, con `unit_id`, `doc_id`, título, URL y
  fecha. Volver a trocearlas rompería la trazabilidad de citas `[U#]` que exige la constitución.
- Los fragmentos ya pasaron por el pipeline medallion (limpieza, deduplicación, control de calidad),
  así que su granularidad está validada por la línea base del Módulo 1.
- El único troceo necesario es técnico: si una unidad supera 512 tokens del modelo, se parte en
  ventanas de 480 tokens con 32 de solape y cada ventana hereda el `unit_id` del padre; la cita
  siempre apunta al `unit_id`.

**Alternativas descartadas**: chunking por párrafos con tamaño fijo (perdería la alineación con las
citas y con la evaluación del Módulo 1); chunking semántico por similitud (costo alto y ganancia
incierta en unidades que ya son cortas).

**Metadatos por fragmento**: `unit_id`, `doc_id`, `title`, `url`, `published_at`, `topic`, `tokens`,
`chunk_index`, `chunk_total`.

---

## R4. Base vectorial

**Decisión**: índice propio: una matriz `.npy` (float32, normalizada L2) + `index.sqlite3` con
metadatos de fragmentos y un `manifest.json`.

**Justificación**:

- Con 15.211 vectores × 384 dimensiones, la búsqueda exacta por producto punto tarda milisegundos: un
  índice aproximado (HNSW, IVF) no aporta y sí añade parámetros que ajustar.
- Un `.npy` + SQLite es **inspeccionable y reproducible**: se puede verificar el recuento, el hash y
  el modelo, y reconstruir con un comando.
- Sin servicio, sin puerto, sin base de datos que instalar: encaja con una app local de un solo
  usuario.
- La constitución permite "Chroma, FAISS, pgvector u otra" siempre que se justifique la persistencia
  reproducible; aquí se justifica.

**Alternativas descartadas**:

| Alternativa | Motivo del descarte |
|-------------|---------------------|
| Chroma | Añade un servicio/almacén propietario, dependencias y un formato que no se audita con un vistazo. |
| FAISS | Índice binario, requiere `faiss-cpu` y las actualizaciones parciales son incómodas. |
| pgvector | Necesita PostgreSQL: infraestructura desproporcionada para una app local de un usuario. |
| Qdrant | Igual que Chroma, pero además con servidor. |

**Persistencia**: `data/module2/index/` (ignorado por Git, igual que `data/module1/`). El manifiesto y
un índice de prueba reducido (`tests/fixtures/rag/`) sí se versionan.

---

## R5. Fusión híbrida

**Decisión**: recuperación semántica top-`k` (k=12, umbral de coseno 0.30) unida con la léxica
(`select_evidence`, top-8), deduplicada por `unit_id` y reordenada por un score combinado:

```text
score = 0.65 * sim_normalizada + 0.35 * score_léxico_normalizado  (+0.05 si aparece en ambos modos)
```

Si ningún candidato semántico supera el umbral, se responde con la selección léxica pura y la traza lo
declara (`mode="lexical"`). Si ambas vienen vacías, fallback explícito.

**Justificación**:

- La semántica gana en paráfrasis; la léxica gana en cifras, siglas y nombres propios (donde el
  embedding diluye la señal exacta). Unirlas conserva la línea base y agrega la mejora.
- El bonus por coincidencia doble es una señal barata de confianza.
- El umbral evita respuestas con fragmentos espurios (E5 produce similitudes ~0.7-0.9 en pares
  relevantes y ~0.1-0.4 en ruido), y su valor inicial se ajusta con la evaluación (R7).

**Alternativas descartadas**: solo semántica (regresión en términos exactos); solo léxica (no cumple
el objetivo); reranking con cross-encoder (fuera de alcance; se anota como mejora futura).

---

## R6. Presupuesto de contexto y trazabilidad

**Decisión**: el presupuesto de tokens del Módulo 1 (`qa_token_budget`) se mantiene. Los fragmentos se
agregan en orden de score hasta llenar el presupuesto; los restantes se registran como
`omitted` con motivo `budget`, y los que no superan el umbral como `omitted` con motivo `threshold`.
Se deduplican fragmentos con similitud > 0.98 entre sí y se conserva el de mayor score.

**Justificación**: mantiene el comportamiento y los costos del Módulo 1, y cumple FR-012/FR-013 y la
exigencia de la app de mostrar los fragmentos con su puntuación.

---

## R7. Evaluación

**Decisión**: `evaluate` calcula, sobre un conjunto de preguntas con unidad esperada:

- **Recall@k** para k ∈ {1, 3, 5, 8} por modo (semántica, léxica, híbrida).
- **MRR** por modo.
- **Cobertura de citas**: porcentaje de respuestas con al menos una cita válida.
- **Fidelidad**: porcentaje de respuestas `ok` cuyas afirmaciones se sostienen en los fragmentos
  citados. Se mide en dos capas: automática (toda cita `[U#]` existe en `used_unit_ids` y el texto de la
  unidad comparte términos con la afirmación) y manual (muestra de 20 respuestas revisadas por una
  persona, registrada en el informe).
- **Latencia** media y p95 de la recuperación y del extremo a extremo.
- **Análisis de errores** por tipo de pregunta (paráfrasis, cifra, nombre propio, multilingüe,
  fuera de corpus).

El conjunto de preguntas amplía las 40 del Módulo 1 y se versiona en
`tests/fixtures/rag/eval_questions.jsonl` (o `docs/evaluacion_modulo2.md` como tabla legible). El
informe se escribe en `docs/evaluacion_modulo2.md`.

**Justificación**: es literalmente lo que pide la constitución (Recall@k, MRR y calidad de citas,
comparadas con la línea base) y permite decidir con números si el RAG se mantiene.

**Criterio de aceptación**: el modo híbrido no puede quedar por debajo de la línea base léxica en
Recall@5 ni en MRR (SC-002, SC-003).

---

## R8. Pruebas sin red

**Decisión**: `HashEmbedder` determinista: vector de 384 dimensiones derivado de un hash estable del
texto (bolsa de hashes, normalizado L2). La suite usa este embedder y un índice de 50 unidades en
`tests/fixtures/rag/`. El modelo real solo se usa en `index build` y en la evaluación manual.

**Justificación**: sin descargas ni red en CI, resultados reproducibles byte a byte, y las pruebas
siguen ejerciendo el mismo código de fusión, umbral, deduplicación y contrato.

**Riesgo**: el `HashEmbedder` no mide calidad semántica. Mitigación: la calidad se mide en la
evaluación manual con el modelo real (R7), documentada en el informe.

---

## R9. Configuración

**Decisión**: nuevo `config/retrieval.toml`:

```toml
[embedding]
model = "intfloat/multilingual-e5-small"
dimension = 384
normalize = true
max_tokens = 512
query_prefix = "query: "
passage_prefix = "passage: "

[index]
path = "data/module2/index"
batch_size = 64

[hybrid]
semantic_top_k = 12
lexical_top_k = 8
min_similarity = 0.30
weight_semantic = 0.65
weight_lexical = 0.35
both_bonus = 0.05
dedup_similarity = 0.98
```

**Justificación**: un solo archivo, versionado, con los valores que la constitución exige registrar; el
código no lleva constantes mágicas y la evaluación puede sobrescribirlos por CLI.

---

## Resumen de decisiones

| Incógnita | Decisión | Alternativa principal descartada |
|-----------|----------|----------------------------------|
| Modelo | `intfloat/multilingual-e5-small` (384d) | `bge-m3` (1024d, pesado) |
| Runtime | `fastembed` (ONNX) | `sentence-transformers` (PyTorch) |
| Chunking | Unidades de oro; troceo solo por límite | Chunking fijo por párrafos |
| Base vectorial | `.npy` + SQLite + manifiesto | Chroma / FAISS / pgvector |
| Fusión | Híbrida ponderada con umbral y respaldo léxico | Solo semántica |
| Métricas | Recall@k + MRR + citas + latencia | Solo inspección manual |
| Pruebas | Embedder falso determinista | Descargar el modelo en CI |
