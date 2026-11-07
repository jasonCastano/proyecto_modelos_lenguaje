# Tareas: Chatbot con recuperación semántica (RAG)

**Entrada**: documentos de diseño de `/specs/013-semantic-rag-chatbot/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Rama**: `013-semantic-rag-chatbot` — **prohibido mergear a `main`**; el cierre es un PR para revisión del
propietario.

**Pruebas**: incluidas. La especificación (FR-016, SC-008) y la constitución exigen una suite offline con
embedder falso y un índice de prueba versionado; el modelo real solo se usa al construir el índice y al
evaluar.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US5`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: configuración en `config/`, código en `src/proyecto_modelos_lenguaje/`, interfaz en `web/src/`,
pruebas en `tests/` y documentación en `docs/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: dependencias, configuración, exclusión del índice y esqueleto del paquete.

- [X] T001 Añadir las dependencias `fastembed` y `numpy` con `uv add fastembed numpy`; confirmar que `pyproject.toml` y `uv.lock` quedan actualizados y que `uv sync` termina sin errores.
- [X] T002 [P] Crear `config/retrieval.toml` con `[embedding]` (`model="intfloat/multilingual-e5-small"`, `dimension=384`, `normalize=true`, `max_tokens=512`, `query_prefix="query: "`, `passage_prefix="passage: "`), `[index]` (`path="data/module2/index"`, `batch_size=64`) y `[hybrid]` (`semantic_top_k=12`, `lexical_top_k=8`, `min_similarity=0.30`, `weight_semantic=0.65`, `weight_lexical=0.35`, `both_bonus=0.05`, `dedup_similarity=0.98`).
- [X] T003 [P] Añadir `data/module2/` a `.gitignore` junto a la entrada existente `data/module1/`, con un comentario que explique que el índice es un artefacto derivado no versionado.
- [X] T004 [P] Crear el paquete `src/proyecto_modelos_lenguaje/rag/__init__.py` con la API pública exportada (`EmbeddingProfile`, `HashEmbedder`, `FastEmbedEmbedder`, `build_index`, `load_index`, `verify_index`, `HybridRetriever`, `RetrievalTrace`).

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: perfil de embeddings, embedders, índice, manifiesto, CLI de índice y fixtures.

**⚠ CRÍTICO**: ninguna historia de usuario puede iniciar hasta completar esta fase.

- [X] T005 [P] Implementar `EmbeddingProfile` y `load_embedding_profile()` en `src/proyecto_modelos_lenguaje/rag/embeddings.py` con los campos de `data-model.md` (`model` no vacío, `dimension > 0`, `normalize` booleano, `max_tokens > 0`, prefijos de consulta y pasaje, `created_at` ISO-8601 UTC) y errores claros si `config/retrieval.toml` falta o es inválido.
- [X] T006 [P] Implementar `HashEmbedder` en `src/proyecto_modelos_lenguaje/rag/embeddings.py`: vectores deterministas de 384 dimensiones derivados de un hash estable del texto, normalizados L2, con `embed_passages(texts)` y `embed_query(text)`; no descarga nada ni usa red.
- [X] T007 Implementar `FastEmbedEmbedder` en `src/proyecto_modelos_lenguaje/rag/embeddings.py`: import perezoso de `fastembed`, registro del modelo personalizado con `PoolingType.MEAN`, `normalization=True`, `dim=384` y `model_file="onnx/model.onnx"` cuando el catálogo no lo incluya; aplicar `passage_prefix`/`query_prefix`, procesar por lotes de `batch_size=64` y rechazar textos que excedan `max_tokens=512` con delegación al troceador de T010.
- [X] T008 [P] Definir `Fragment` e `IndexManifest` en `src/proyecto_modelos_lenguaje/rag/index.py` respetando `data-model.md`: `fragment_id` único (`<unit_id>` o `<unit_id>#<chunk_index>`), `unit_id` obligatorio, `text` no vacío, `tokens > 0`, `1 <= chunk_index <= chunk_total`; manifiesto con `schema_version=1`, `model` no vacío, `dimension >= 1`, `count >= 0`, `gold_sha256` de 64 hex y `created_at` ISO-8601.
- [X] T009 [P] Crear el fixture de pruebas en `tests/fixtures/rag/gold_sample.jsonl` (50 unidades de oro reales recortadas, con `unit_id`, `doc_id`, `title`, `url`, `text`) y `tests/fixtures/rag/build_fixture.py` para generar el índice de prueba con `HashEmbedder`; el fixture debe versionarse y pesar menos de 1 MB.
- [X] T010 Implementar en `src/proyecto_modelos_lenguaje/rag/index.py` el troceo técnico: unidades de hasta 512 tokens se indexan enteras (`chunk_total=1`); las que excedan se parten en ventanas de 480 tokens con 32 de solape, cada ventana hereda el `unit_id` del padre y la concatenación reproduce el texto original salvo el solape declarado.
- [X] T011 Implementar `build_index()` en `src/proyecto_modelos_lenguaje/rag/index.py`: leer `data/gold/knowledge_units.jsonl` en solo lectura, embeber los pasajes por lotes, escribir `vectors.npy` (float32, `(n, 384)`, filas normalizadas), `index.sqlite3` y `manifest.json` en un directorio temporal de `data/module2/`, y publicar con renombrado atómico; calcular `gold_sha256` sobre el archivo de oro.
- [X] T012 Implementar `load_index()` y `verify_index()` en `src/proyecto_modelos_lenguaje/rag/index.py`: comprobar que `manifest.count` coincide con las filas de la matriz y de SQLite, que `dimension` coincide con el ancho de la matriz y con el perfil configurado, y que `gold_sha256` coincide con el corpus actual; devolver aviso de índice desactualizado sin borrar el índice.
- [X] T013 Implementar el CLI de índice en `src/proyecto_modelos_lenguaje/rag/__main__.py`: subcomandos `index build`, `index verify` e `index rebuild` con los códigos de salida del contrato (0 éxito, 2 ya existe sin `--force`, 3 oro ausente o vacío, 4 error del modelo, 5 manifiesto/dimensión/recuento/perfil inválido, 6 índice desactualizado).
- [X] T014 [P] Escribir `tests/unit/test_rag_embeddings.py`: perfil válido e inválido, determinismo del `HashEmbedder` (mismo texto ⇒ mismo vector byte a byte), norma L2 ≈ 1, dimensión 384, aplicación de prefijos de consulta y pasaje.
- [X] T015 [P] Escribir `tests/unit/test_rag_index.py`: construcción desde `tests/fixtures/rag/gold_sample.jsonl`, `count` coherente con matriz y SQLite, troceo de una unidad larga (480/32), rechazo por perfil distinto, aviso por `gold_sha256` desactualizado, publicación atómica y verificación de que `data/gold` no cambia (hashes y mtimes idénticos antes y después).
- [X] T016 [P] Escribir `tests/contract/test_rag_contract.py`: validar `manifest.json` contra `specs/013-semantic-rag-chatbot/contracts/index-manifest.schema.json` con `jsonschema`, incluyendo los casos inválidos (`schema_version` distinto, `gold_sha256` mal formado, `dimension=0`).

**Punto de control**: `rag index build` y `rag index verify` funcionan sobre datos reales y sobre el fixture; la suite base pasa sin red.

---

## Fase 3: Historia 1 — Respuestas con recuperación semántica (P1) 🎯 MVP

**Meta**: responder preguntas parafraseadas recuperando fragmentos por significado y conservando citas y
fallback.

**Prueba independiente**: 3 preguntas reformuladas contra el fixture obtienen fragmentos por encima del
umbral y una respuesta `ok` con al menos una cita; una pregunta fuera del corpus devuelve fallback.

### Pruebas de la Historia 1

- [X] T017 [P] [US1] Escribir `tests/unit/test_rag_hybrid.py` con los casos semánticos: top-k respeta `semantic_top_k=12`, los fragmentos se ordenan por `score` descendente, se descarta lo que queda por debajo de `min_similarity=0.30`, `origin="semantic"` y `semantic_score` presente; las pruebas deben fallar antes de T018–T020.
- [X] T018 [P] [US1] Escribir `tests/integration/test_rag_api.py` con el caso semántico: índice fixture, modelo guionizado y `POST /api/ask` ⇒ `status="ok"`, `citations` con al menos una unidad y `retrieval.mode` en `semantic` o `hybrid`; debe fallar antes de T021.

### Implementación de la Historia 1

- [X] T019 [US1] Crear en `src/proyecto_modelos_lenguaje/rag/hybrid.py` los dataclasses `RetrievedFragment` y `RetrievalTrace` con las restricciones de `data-model.md`: `score` en [0, 1], `origin` en `semantic|lexical|both`, `status` en `used|omitted_threshold|omitted_budget|omitted_duplicate`, `reason` obligatorio si `status != used`, `elapsed_ms >= 0` y `fragments` ordenados por `score` descendente.
- [X] T020 [US1] Implementar `SemanticRetriever` en `src/proyecto_modelos_lenguaje/rag/hybrid.py`: embeber la consulta con prefijo `query: `, calcular similitud coseno contra la matriz normalizada, devolver hasta `semantic_top_k` candidatos con `semantic_score` y aplicar `min_similarity`; si no hay índice válido, devolver lista vacía y `semantic_available=False` en la traza.
- [X] T021 [US1] Implementar en `src/proyecto_modelos_lenguaje/rag/hybrid.py` la conversión de traza a `EvidenceSelection`: mapear cada fragmento usado a `SelectedUnit` con etiquetas `U1..Un` en el mismo orden de la traza, de modo que `build_context` y el parseo de citas `[U#]` sigan funcionando sin cambios.
- [X] T022 [US1] Extender `answer_question()` en `src/proyecto_modelos_lenguaje/tasks.py` con el parámetro opcional `retrieval: HybridRetriever | None = None` y añadir `TaskResult.retrieval: RetrievalTrace | None = None` al final; con `retrieval=None` el comportamiento debe ser idéntico al actual (pruebas existentes en verde).
- [X] T023 [US1] Implementar el subcomando `rag search "<pregunta>" [--mode hybrid|semantic|lexical] [--k 8]` en `src/proyecto_modelos_lenguaje/rag/__main__.py`: imprime modo, umbral, candidatos y fragmentos con `score`, `origin` y `status` sin llamar al LLM; código de salida 5 si el índice falta o es inválido.
- [X] T024 [US1] Añadir a `tests/integration/test_rag_api.py` el caso fuera de corpus ("receta de arepas"): sin fragmentos sobre el umbral ⇒ `status="fallback"`, `citations=[]`, `fallback=true` y `retrieval.mode` en `lexical` o `none`, sin texto inventado.

**Punto de control**: la recuperación semántica responde con citas y declara fallback; US1 es demostrable sola.

---

## Fase 4: Historia 2 — Híbrida con respaldo léxico (P2)

**Meta**: no perder precisión en cifras, siglas y nombres propios, y deduplicar cuando ambas vías coinciden.

**Prueba independiente**: 10 preguntas con cifras, siglas y nombres propios conservan el fragmento correcto;
una pregunta cuyos candidatos semánticos están bajo el umbral responde con recuperación léxica
(`mode="lexical"`) y sin duplicados.

### Pruebas de la Historia 2

- [X] T025 [P] [US2] Ampliar `tests/unit/test_rag_hybrid.py` con la fusión: `score = 0.65*semántico + 0.35*léxico`, `+0.05` si el fragmento aparece en ambos modos, `origin="both"` cuando corresponde, orden final por `score` y ausencia de `unit_id` repetidos.
- [X] T026 [P] [US2] Añadir a `tests/unit/test_rag_hybrid.py` los casos exactos: pregunta con cifra, sigla y nombre propio conserva el fragmento léxico en el top-3 aunque la similitud semántica sea baja; y un caso con `min_similarity` no alcanzado ⇒ `mode="lexical"`.
- [X] T027 [P] [US2] Ampliar `tests/integration/test_rag_api.py`: misma unidad devuelta por semántica y léxica aparece una sola vez en `used_unit_ids` y en `retrieval.fragments`.

### Implementación de la Historia 2

- [X] T028 [US2] Implementar `HybridRetriever` en `src/proyecto_modelos_lenguaje/rag/hybrid.py`: ejecutar `SemanticRetriever` (top 12) y `retrieval.select_evidence` (top 8), unir por `unit_id`, calcular el score combinado con `weight_semantic=0.65`, `weight_lexical=0.35` y `both_bonus=0.05`, y ordenar de forma estable por score.
- [X] T029 [US2] Implementar en `src/proyecto_modelos_lenguaje/rag/hybrid.py` el umbral y el presupuesto: marcar `omitted_threshold` con motivo «Similitud por debajo de 0.30 y sin coincidencia léxica», `omitted_duplicate` con similitud > `dedup_similarity=0.98` conservando el de mayor score, y `omitted_budget` con motivo «Presupuesto de contexto agotado» respetando `qa_token_budget`.
- [X] T030 [US2] Implementar en `src/proyecto_modelos_lenguaje/rag/hybrid.py` la selección del modo de la traza: `hybrid` si hay candidatos de ambos orígenes, `semantic` si solo semántica, `lexical` si la semántica no supera el umbral, `none` si ambas vienen vacías; exponerlo en `RetrievalTrace.mode` y en `TaskResult.retrieval`.
- [X] T031 [US2] Conectar la selección híbrida en `src/proyecto_modelos_lenguaje/api.py` y `src/proyecto_modelos_lenguaje/tasks.py`: `/api/ask` construye el retriever con `config/retrieval.toml`, cae a léxico si el índice falta o es inválido (`semantic_available=false` y `notes`), y nunca responde 500 por un índice ausente.

**Punto de control**: el híbrido no pierde los aciertos léxicos del Módulo 1 y no duplica evidencia.

---

## Fase 5: Historia 3 — Ver los fragmentos que sustentan la respuesta (P3)

**Meta**: mostrar en la interfaz los fragmentos usados, su puntuación y los descartados con su motivo.

**Prueba independiente**: una respuesta en la interfaz muestra la insignia del modo, los fragmentos usados con
título y fuente, y un desplegable con los descartados y su motivo.

### Pruebas de la Historia 3

- [X] T032 [P] [US3] Ampliar `tests/contract/test_rag_contract.py` con las invariantes de `/api/ask`: `used_unit_ids` es exactamente `[f.unit_id for f in retrieval.fragments if f.status == "used"]`, sin repetidos; `retrieval` es opcional; `mode="none"` implica `status="fallback"` salvo pregunta inválida.
- [X] T033 [P] [US3] Escribir `web/src/test/RetrievedFragments.test.tsx`: renderiza fragmentos usados con título, fuente y `score`; los descartados aparecen solo al abrir el desplegable con su `reason`; sin fragmentos muestra «Sin evidencia recuperada».

### Implementación de la Historia 3

- [X] T034 [US3] Añadir a `src/proyecto_modelos_lenguaje/api_models.py` los modelos `RetrievalFragmentModel` y `RetrievalTraceModel` con los mismos enums y restricciones de `data-model.md`, y el campo opcional `retrieval` en `CitedAnswer`.
- [X] T035 [US3] Adjuntar la traza en `src/proyecto_modelos_lenguaje/api.py`: `POST /api/ask` devuelve `retrieval` tanto en modo `real` como `demo`, con `notes` legibles cuando el índice esté desactualizado o el modelo no coincida.
- [X] T036 [P] [US3] Extender `web/src/lib/types.ts` y `web/src/lib/api.ts` con los tipos `RetrievalTrace`/`RetrievalFragment` y su mapeo desde la respuesta de `/api/ask`, tolerando la ausencia de `retrieval`.
- [X] T037 [US3] Crear `web/src/components/RetrievedFragments.tsx`: insignia del modo (`Híbrida`, `Semántica`, `Léxica`, `Sin evidencia`), lista de usados con título, fuente y puntuación, y desplegable de descartados con `score` y `reason`.
- [X] T038 [US3] Integrar el componente en `web/src/components/AnswerPanel.tsx` debajo de la respuesta y encima de las fuentes, sin romper los estilos existentes de `web/src/styles/global.css`.

**Punto de control**: la respuesta es auditable de extremo a extremo desde la interfaz.

---

## Fase 6: Historia 4 — Modo demostración sin red (P4)

**Meta**: recorrer el chatbot sin conexión con el modelo guionizado y el índice de prueba.

**Prueba independiente**: con la red bloqueada, `mode="demo"` responde con fragmentos del índice de prueba y
la interfaz muestra el distintivo; ninguna llamada externa ocurre.

### Pruebas de la Historia 4

- [X] T039 [P] [US4] Escribir en `tests/integration/test_rag_api.py` el caso demo offline: bloquear `socket.socket.connect` durante la petición, `mode="demo"` ⇒ `status` distinto de `error`, `retrieval.fragments` no vacío desde `tests/fixtures/rag/` y ninguna conexión intentada.

### Implementación de la Historia 4

- [X] T040 [US4] Implementar en `src/proyecto_modelos_lenguaje/rag/index.py` la carga del índice de prueba cuando el índice real no exista y el modo sea `demo` (rutas `tests/fixtures/rag/`), sin intentar descargar el modelo real.
- [X] T041 [US4] Ajustar `src/proyecto_modelos_lenguaje/api.py` para que `mode="demo"` use siempre el `HashEmbedder` y el índice de prueba, y para que `mode="real"` nunca caiga silenciosamente al fixture.
- [X] T042 [US4] Actualizar `web/src/components/DemoBanner.tsx` para indicar que la recuperación usa el índice de prueba y el modelo guionizado cuando el modo es demo.
- [X] T043 [US4] Validar el escenario 6 de `specs/013-semantic-rag-chatbot/quickstart.md` con la red desconectada y registrar el resultado (fecha, comando, observación) en `docs/evaluacion_modulo2.md`.

**Punto de control**: la demo funciona sin red, sin costo y sin índice real.

---

## Fase 7: Historia 5 — Medir si el RAG mejoró (P5)

**Meta**: comparar semántica, léxica e híbrida con Recall@k y MRR, medir fidelidad y decidir con números.

**Prueba independiente**: `rag evaluate` produce Recall@1/3/5/8, MRR, cobertura y fidelidad por modo, y el
informe declara si el híbrido supera la línea base léxica.

### Pruebas de la Historia 5

- [X] T044 [P] [US5] Escribir `tests/unit/test_rag_evaluate.py` con el cálculo de métricas sobre un conjunto sintético conocido: Recall@k, MRR, agregación por modo, cobertura de citas y fidelidad; verificar los valores esperados a mano alzada.

### Implementación de la Historia 5

- [X] T045 [US5] Crear `tests/fixtures/rag/eval_questions.jsonl` con al menos 40 preguntas: 12 de paráfrasis, 10 con cifras, 8 con nombres propios o siglas, 5 en inglés y 5 fuera del corpus; cada registro con `question_id`, `question`, `expected_unit_ids`, `type` en `paraphrase|figure|proper_noun|english|out_of_corpus` y `notes`.
- [X] T046 [US5] Implementar `src/proyecto_modelos_lenguaje/rag/evaluate.py`: calcular Recall@k para `k in {1,3,5,8}`, MRR, cobertura de citas, fidelidad automática (toda cita `[U#]` existe en `used_unit_ids`) y latencia media/p95 por modo, con el formato de `EvaluationRun` de `data-model.md`.
- [X] T047 [US5] Implementar en `src/proyecto_modelos_lenguaje/rag/__main__.py` el subcomando `evaluate --questions <ruta> --out docs/evaluacion_modulo2.md [--json-out <ruta>]`, con umbrales y pesos sobrescribibles por CLI y veredicto explícito contra la línea base léxica.
- [X] T048 [US5] Ejecutar la evaluación con el modelo real y escribir `docs/evaluacion_modulo2.md`: tabla comparativa por modo, Recall@k, MRR, cobertura, fidelidad, latencia y veredicto (`hybrid >= baseline` en Recall@5 y MRR).
- [X] T049 [US5] Si el híbrido no supera la línea base, ajustar `min_similarity`, `weight_semantic` y `weight_lexical` en `config/retrieval.toml`, repetir T048 y registrar cada intento en el informe; si aun así no supera, dejar constancia y **no** proponer el merge.
- [X] T050 [US5] Añadir a `docs/evaluacion_modulo2.md` el análisis de errores por tipo de pregunta (`paraphrase`, `figure`, `proper_noun`, `english`, `out_of_corpus`) con 2 ejemplos reales por tipo y su causa.

**Punto de control**: la decisión de mantener el RAG está respaldada por números reproducibles.

---

## Fase 8: Pulido y aspectos transversales

**Propósito**: documentación, gobernanza, rendimiento y cierre por PR.

- [X] T051 [P] Escribir `docs/decisions/0014-semantic-rag.md` con la justificación de FR-017: modelo, dimensión 384, normalización L2, límite de 512 tokens, costo cero por consulta, latencia medida y alternativas descartadas (bge-m3, PyTorch, API de embeddings, Chroma/FAISS/pgvector).
- [X] T052 [P] Actualizar `README.md` con el modelo de embeddings, el comando de construcción del índice, el requisito de espacio y el enlace al quickstart.
- [X] T053 [P] Actualizar `CONSTITUTION.md` en la sección de la Fase 2 para registrar `fastembed`/`numpy` como parte del stack y el estado del RAG, en el mismo commit del cambio arquitectónico.
- [ ] T054 [P] Actualizar `docs/arquitectura.json` con el paquete `rag` (embeddings, índice, híbrida, evaluación) y regenerar `docs/arquitectura.html` con el flujo de Archify del proyecto. _(JSON actualizado con el nodo del índice semántico; el HTML sigue pendiente de regenerar con Archify.)_
- [X] T055 Medir la latencia extremo a extremo de 10 preguntas en modo `real` y compararla con la línea base del Módulo 1; registrar media y p95 en `docs/evaluacion_modulo2.md` y verificar SC-006 (≤ 1.2× la línea base).
- [X] T056 Ejecutar `uv run ruff check .`, `uv run pytest -q`, `cd web && npm run build` y `make check`; corregir lo que falle en `src/`, `tests/` o `web/` y confirmar que la suite completa tarda menos de 3 minutos sin red (SC-008).
- [X] T057 Verificar higiene del repositorio: `git status --short` sin `data/module2/`, sin `.env`, sin capturas temporales y con `.env.example` sin claves; confirmar con `git log --all -S "sk-" -- .env.example` que ninguna clave entró al historial.
- [X] T058 Abrir un PR en borrador desde `013-semantic-rag-chatbot` hacia `main` con resumen, evidencias de `specs/013-semantic-rag-chatbot/quickstart.md` y resultados de `docs/evaluacion_modulo2.md`; **no mergear**: la aprobación y el merge los hace el propietario.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; puede iniciar de inmediato.
- **Fundamentos (Fase 2)**: depende de la Fase 1 y **bloquea** todas las historias de usuario.
- **Historias de usuario (Fases 3–7)**: dependen de la Fase 2.
  - US1 debe ir primero: define `SemanticRetriever`, la traza y el parámetro `retrieval`.
  - US2 depende de US1 (reutiliza `SemanticRetriever` y la traza).
  - US3 depende de US1/US2 para tener `retrieval` en la API, pero su trabajo de UI es paralelizable tras T035.
  - US4 depende de US1 (índice de prueba) y de T035 (respuesta con traza).
  - US5 depende de US1, US2 y US3 (mide los tres modos y la cobertura de citas).
- **Pulido (Fase 8)**: depende de todas las historias deseadas.

### Dependencias entre historias

- **US1 (P1)**: sin dependencias de otras historias; es el MVP.
- **US2 (P2)**: requiere T019–T021 de US1 (traza y retriever semántico).
- **US3 (P3)**: requiere T030 (modo en la traza) para mostrar la insignia correcta.
- **US4 (P4)**: requiere el fixture de T009 y la traza de T019.
- **US5 (P5)**: requiere que US1, US2 y US3 estén completas para medir y citar.

### Dentro de cada historia

- Las pruebas se escriben antes y deben fallar antes de implementar.
- Modelos/dataclasses antes de servicios; servicios antes de endpoints y UI.
- Implementación base antes de la integración.

### Oportunidades de paralelización

- T002, T003 y T004 en paralelo tras T001.
- T005, T006, T008 y T009 en paralelo (archivos distintos).
- T014, T015 y T016 en paralelo una vez existan T008–T013.
- T017 y T018 en paralelo (pruebas de US1).
- T025, T026 y T027 en paralelo (pruebas de US2).
- T032 y T033 en paralelo (contrato y UI de US3).
- T036 y T037 pueden ir en paralelo con T034/T035 si los tipos se acuerdan primero.
- T051, T052, T053 y T054 en paralelo (documentación distinta).

---

## Ejemplo de paralelización: Historia 1

```bash
# Pruebas de US1 en paralelo:
Task: "tests/unit/test_rag_hybrid.py — top-k, umbral y orden de la traza"
Task: "tests/integration/test_rag_api.py — /api/ask semántico con índice fixture"

# Tras T021, implementación paralela:
Task: "SemanticRetriever en src/proyecto_modelos_lenguaje/rag/hybrid.py"
Task: "Subcomando search en src/proyecto_modelos_lenguaje/rag/__main__.py"
```

## Ejemplo de paralelización: Historia 3

```bash
# Contrato y UI en paralelo (archivos distintos):
Task: "Invariantes de /api/ask en tests/contract/test_rag_contract.py"
Task: "Prueba de componentes en web/src/test/RetrievedFragments.test.tsx"

# Tras T035:
Task: "Tipos en web/src/lib/types.ts y web/src/lib/api.ts"
Task: "Componente en web/src/components/RetrievedFragments.tsx"
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 (Preparación).
2. Completar Fase 2 (Fundamentos) — **crítico**: sin índice no hay semántica.
3. Completar Fase 3 (US1).
4. **DETENERSE Y VALIDAR**: `rag search` con 3 preguntas parafraseadas y `POST /api/ask` con citas.
5. Demostrar sin tocar la UI ni la evaluación.

### Entrega incremental

1. Preparación + Fundamentos ⇒ índice reproducible y verificado.
2. US1 ⇒ respuestas semánticas con citas (MVP).
3. US2 ⇒ híbrida con respaldo léxico, sin regresión en cifras.
4. US3 ⇒ trazabilidad visible en la interfaz.
5. US4 ⇒ demo offline con índice de prueba.
6. US5 ⇒ evaluación y veredicto contra la línea base.
7. Pulido ⇒ ADR, README, constitución, arquitectura, PR.

### Regla de corte

Si US5 no demuestra que el híbrido iguala o supera la línea base léxica en Recall@5 y MRR, el PR se queda
abierto con el hallazgo documentado; no se mergea a `main`.

---

## Notas

- `[P]` = archivos distintos, sin dependencias pendientes.
- `[US#]` traza cada tarea a su historia y a sus criterios de aceptación.
- Cada historia se completa y valida antes de pasar a la siguiente prioridad.
- Verificar que las pruebas fallan antes de implementar.
- Commit por tarea o grupo lógico, con Conventional Commits en español.
- **No hacer merge a `main`**: el cierre es un PR revisado por el propietario.
- Evitar: tareas vagas, dos tareas sobre el mismo archivo en paralelo, dependencias cruzadas que rompan la
  independencia de las historias.
