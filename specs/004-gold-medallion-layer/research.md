# Research: Capa Oro (Gold)

**Feature**: `004-gold-medallion-layer` | **Date**: 2026-10-30

Este documento resuelve las decisiones técnicas de la especificación. No quedan incógnitas pendientes.

---

## 1. Unidades extractivas en lugar de generación con LLM

- **Decision**: construir unidades de conocimiento con oraciones o pasajes literales del fragmento de plata,
  seleccionados y clasificados por reglas. No se resumen, parafrasean ni generan afirmaciones nuevas.
- **Rationale**: la constitución exige que toda respuesta factual sea verificable y que no se invente
  información. Una unidad extractiva puede auditarse contra el texto de origen; una unidad generada por un LLM
  requeriría otra evaluación de fidelidad y no es el objetivo de esta etapa.
- **Alternatives considered**:
  - LLM para extraer tripletas: mejor cobertura, pero introduce coste, variabilidad y riesgo de alucinación.
  - Resumen extractivo con TextRank: añade dependencia y no mejora la trazabilidad.
  - Unidades por fragmento completo: pierden granularidad y dificultan la cobertura por ítem.

## 2. Segmentación de oraciones

- **Decision**: dividir por signos de cierre (`.!?`) seguidos de espacio, con reglas para abreviaturas comunes
  (`S.A.`, `S.A.S.`, `No.`, `p.`, `pp.`, `vs.`, `Dr.`, `Ing.`) y para cifras decimales. Las oraciones de menos
  de 40 caracteres se unen a la anterior; las de más de 700 caracteres se dividen por punto y coma o por
  párrafo.
- **Rationale**: el corpus tiene informes y notas con abreviaturas; una segmentación ingenua corta “S.A.S.” y
  produce unidades sin sentido. El umbral evita unidades basura.
- **Alternatives considered**:
  - `nltk`/`spacy` con modelos: precisos, pero descargan modelos y rompen la reproducibilidad offline.
  - Segmentación por párrafo: demasiado gruesa para cobertura y citas.

## 3. Clasificación temática

- **Decision**: taxonomía versionada en `config/gold_taxonomy.toml` con temas, palabras clave, alias y mapeo a
  los 24 ítems. Cada unidad se asigna al tema con mayor puntuación; si no supera el umbral, va a `general` y se
  marca `topic_uncertain`.
- **Rationale**: el corpus es acotado y el dominio es conocido; una lista controlada es determinista,
  explicable y suficiente. Los embeddings no son necesarios y añadirían un modelo y una dependencia.
- **Alternatives considered**:
  - Embeddings + prototipos: mejor generalización, pero fuera de alcance y no reproducible sin modelo.
  - TF-IDF + clustering: no garantiza temas interpretables ni mapeo a los 24 ítems.
  - Clasificación manual: no escala a 3.810 fragmentos.

## 4. Entidades y alias

- **Decision**: vocabulario controlado de entidades (Manuelita, filiales, marcas, productos, sedes, personas y
  certificaciones) con alias y variantes en español/inglés. La detección usa límites de palabra, sin distinción
  de mayúsculas y normalización de acentos.
- **Rationale**: “Manuelita” es un nombre ambiguo; el vocabulario evita confundir la empresa con personas,
  canciones o lugares. Los alias resuelven filiales y marcas sin duplicar entidades.
- **Alternatives considered**:
  - `spaCy` con NER: excelente para personas/organizaciones, pero requiere modelo y no cubre marcas internas.
  - NER de un LLM: fuera de alcance y no determinista.

## 5. Hechos numéricos y fechados

- **Decision**: extraer hechos solo cuando el texto presenta un patrón explícito:
  - `<atributo> ... <número> <unidad>` (p. ej., “capacidad de 125.000 toneladas”),
  - `<sujeto> ... <año>` para hitos,
  - `<atributo> ... <porcentaje>`.
  El hecho guarda sujeto, atributo, valor, unidad, año y evidencia. Si falta el sujeto o el atributo, no se crea
  hecho; la unidad queda como pasaje.
- **Rationale**: los hechos incompletos son la principal fuente de errores y conflictos falsos. Es preferible
  una unidad extractiva sin tripleta que una tripleta inventada.
- **Alternatives considered**:
  - OpenIE: mayor cobertura, pero ruido y dependencia.
  - LLM para tripletas: fuera de alcance.

## 6. Detección y resolución de conflictos

- **Decision**: agrupar hechos por `(subject_id, attribute)`; si hay más de un valor normalizado distinto, se
  crea un conflicto. La preferencia es: `first_party` > `open_data` > `third_party`, luego la fecha más
  reciente, luego la unidad con más evidencia. Si persiste el empate, el conflicto queda `disputed`.
- **Rationale**: solo se comparan hechos con el mismo sujeto y atributo; así se evitan conflictos entre
  “capacidad de planta” y “producción anual”. La autoridad y la fecha son criterios explicables.
- **Alternatives considered**:
  - Resolver siempre por el valor más frecuente: puede elegir una fuente minoritaria.
  - No detectar conflictos: el RAG repetiría contradicciones.

## 7. Deduplicación de unidades y hechos

- **Decision**: hash SHA-256 del texto normalizado para duplicados exactos; para cercanos, Jaccard de shingles
  de 5 palabras con umbral 0,90 y unión de evidencias. Los hechos se deduplican por
  `(subject_id, attribute, normalized_value, unit)`.
- **Rationale**: 3.810 fragmentos y ~1.000 unidades permiten un cálculo acotado sin MinHash LSH; el umbral alto
  evita fusionar textos con matices distintos.
- **Alternatives considered**:
  - Reutilizar MinHash/LSH de plata: válido, pero para este volumen un Jaccard directo es suficiente.
  - SimHash: menos preciso para textos cortos.

## 8. Cobertura de los 24 ítems

- **Decision**: un ítem es `covered` si tiene al menos 3 unidades, al menos una de fuente oficial y ningún
  conflicto abierto; `partial` si tiene 1–2 unidades o solo fuentes de terceros; `missing` si no tiene unidades.
  Cada ítem incluye evidencia, autoridad, conflictos y razón de vacío.
- **Rationale**: una sola mención no demuestra cobertura; exigir tres unidades y una fuente oficial reduce
  falsos positivos. El umbral es configurable y se valida con una muestra.
- **Alternatives considered**:
  - Palabras clave del bronce: ya demostró falsos positivos.
  - Una sola unidad: infla la cobertura.

## 9. Paquetes de contexto

- **Decision**: selección greedy tipo knapsack con prioridad:
  1. ítems obligatorios cubiertos,
  2. autoridad oficial,
  3. vigencia (fecha más reciente),
  4. diversidad de temas,
  5. longitud.
  Se agregan unidades hasta el presupuesto (`8000` y `32000` tokens) usando `estimate_tokens` de plata. Cada
  bloque incluye cita y linaje; las omisiones se registran.
- **Rationale**: el presupuesto es la restricción dura; la prioridad garantiza representatividad y citas.
- **Alternatives considered**:
  - Orden alfabético: no garantiza cobertura.
  - Muestreo aleatorio: no reproducible ni priorizado.
  - Incluir todo: excede la ventana del modelo.

## 10. Preguntas semilla para FAQ

- **Decision**: generar preguntas deterministas a partir de:
  - el nombre de cada ítem de cobertura (“¿Qué información tiene Manuelita sobre ...?”),
  - los títulos de sección y tema,
  - entidades y productos.
  Cada pregunta incluye tema, unidades de evidencia y estado. No se genera la respuesta; eso corresponde a
  LangChain en el Módulo 1.
- **Rationale**: el Módulo 1 necesita un conjunto inicial de preguntas; generarlas desde la estructura evita
  inventar y mantiene la trazabilidad.
- **Alternatives considered**:
  - LLM para generar preguntas: fuera de alcance y no determinista.
  - Preguntas manuales: no escalan ni se regeneran.

## 11. Estado incremental

- **Decision**: `data/gold/_meta/state.jsonl` con una línea por documento de plata:
  `doc_id`, `text_hash`, `config_hash`, `status`, `units`, `facts`, `processed_at`. Caché de unidades por
  `doc_id + text_hash + config_hash`. Las salidas se reescriben de forma atómica en orden determinista.
- **Rationale**: 404 documentos son manejables; el estado evita reprocesar lo que no cambió y permite auditar
  qué documento produjo qué.
- **Alternatives considered**:
  - SQLite: más estructura, pero innecesaria para este volumen.
  - Reconstruir todo: simple, pero incumple FR-025.

## 12. Salidas y formatos

- **Decision**:
  - `knowledge_units.jsonl`, `facts.jsonl`, `entities.jsonl`, `conflicts.jsonl`, `faq_seeds.jsonl`.
  - `coverage.json` y `coverage.md`.
  - `context_8k.md`, `context_32k.md` y sus JSONL de bloques.
  - `topics/<topic_id>.md`, `glossary.md`, `manifest.json`.
  - `reports/<run_id>/quality.{json,md}`.
- **Rationale**: JSONL para consumo por la app y Markdown para revisión humana; cumple la constitución.
- **Alternatives considered**:
  - Un solo JSON gigante: difícil de revisar y consumir.
  - Solo Markdown: no apto para la app.

## 13. Identificadores

- **Decision**:
  - `unit_id = "unit_" + sha256(doc_id + ":" + chunk_id + ":" + sentence_index)[:16]`.
  - `fact_id = "fact_" + sha256(subject_id + ":" + attribute + ":" + value + ":" + unit_id)[:16]`.
  - `entity_id = "ent_" + sha256(canonical_name)[:16]`.
  - `topic_id` es un slug estable de la taxonomía.
  - `pack_id = "pack_" + task + "_" + budget`.
- **Rationale**: IDs estables y deterministas, independientes de rutas y del orden de ejecución.
- **Alternatives considered**:
  - UUID: rompe la idempotencia.
  - Índice secuencial: cambia si se agrega contenido.

## 14. Límites y marcas de calidad

- **Decision**: marcas `topic_uncertain`, `ambiguous_value`, `conflicting`, `no_evidence`, `short_unit`,
  `duplicate_unit`, `english_content`, `low_authority`.
- **Rationale**: permiten filtrar y revisar sin inventar; el reporte muestra su distribución.
- **Alternatives considered**:
  - Descartar todo lo dudoso: perdería contenido válido.
  - No marcar: el reporte no sería accionable.

## 15. Dependencias y licencias

| Dependencia | Licencia | Uso |
|-------------|----------|-----|
| Biblioteca estándar | PSF | Segmentación, hashing, JSON |
| `PyYAML` | MIT | Frontmatter |
| Módulos `silver` | MIT (proyecto) | Token proxy, estado y modelos |

No se añaden dependencias. `spaCy`, embeddings y LLM se descartaron por reproducibilidad y alcance.

## 16. Rendimiento

- **Decision**: medir la ejecución completa sobre 404 documentos/3.810 fragmentos y registrar duración, unidades
  y tokens. El objetivo es ≤10 minutos y ≤4 GB; la segunda ejecución con caché debe ser ≤2 minutos.
- **Rationale**: el volumen es pequeño; el coste principal es la segmentación y el Jaccard de unidades.
- **Criterio**: si se excede, limitar la comparación de duplicados por tema y usar bloqueo por shingles.

## 17. Riesgos residuales

- La extracción de hechos es conservadora y puede dejar cifras como pasajes; se prefiere eso a una tripleta
  incorrecta.
- La cobertura depende de la calidad de la plata; los vacíos se declaran.
- Los conflictos requieren sujeto y atributo explícitos; los conflictos implícitos no se detectan.
- El proxy de tokens se recalibrará con el modelo del Módulo 1.
