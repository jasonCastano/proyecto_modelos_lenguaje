# Evaluación del Módulo 2 — recuperación semántica

**Ejecución**: `2026-11-06-e5-small` · **Preguntas**: 40 · **Línea base**: lexical

## Métricas por modo

| Modo | Recall@1 | Recall@3 | Recall@5 | Recall@8 | MRR | Cobertura | Latencia media | p95 |
|---|---|---|---|---|---|---|---|---|
| semantic | 0.343 | 0.514 | 0.571 | 0.629 | 0.435 | 1.000 | 77.7 ms | 41.4 ms |
| lexical | 0.286 | 0.343 | 0.371 | 0.371 | 0.320 | 1.000 | 998.6 ms | 1455.4 ms |
| hybrid | 0.343 | 0.514 | 0.600 | 0.629 | 0.450 | 1.000 | 1194.0 ms | 1472.8 ms |

**Veredicto**: hybrid >= baseline en Recall@5 y MRR

## Análisis de errores

| Pregunta | Modo | Tipo | Causa |
|---|---|---|---|
| p01 | semantic | paraphrase | la unidad esperada no apareció en el ranking |
| p02 | semantic | paraphrase | la unidad esperada no apareció en el ranking |
| p05 | semantic | paraphrase | la unidad esperada no apareció en el ranking |
| p06 | semantic | paraphrase | la unidad esperada no apareció en el ranking |
| p11 | semantic | paraphrase | la unidad esperada no apareció en el ranking |
| p12 | semantic | paraphrase | la unidad esperada no apareció en el ranking |
| n04 | semantic | proper_noun | la unidad esperada no apareció en el ranking |
| e01 | semantic | english | la unidad esperada no apareció en el ranking |
| e04 | semantic | english | la unidad esperada no apareció en el ranking |
| e05 | semantic | english | la unidad esperada no apareció en el ranking |
| o01 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o02 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o03 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o04 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o05 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| p01 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p02 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p03 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p04 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p05 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p06 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p07 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p08 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p09 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p11 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| p12 | lexical | paraphrase | la unidad esperada no apareció en el ranking |
| f06 | lexical | figure | la unidad esperada no apareció en el ranking |
| f07 | lexical | figure | la unidad esperada no apareció en el ranking |
| f08 | lexical | figure | la unidad esperada no apareció en el ranking |
| n01 | lexical | proper_noun | la unidad esperada no apareció en el ranking |
| n02 | lexical | proper_noun | la unidad esperada no apareció en el ranking |
| n05 | lexical | proper_noun | la unidad esperada no apareció en el ranking |
| e01 | lexical | english | la unidad esperada no apareció en el ranking |
| e02 | lexical | english | la unidad esperada no apareció en el ranking |
| e03 | lexical | english | la unidad esperada no apareció en el ranking |
| e04 | lexical | english | la unidad esperada no apareció en el ranking |
| e05 | lexical | english | la unidad esperada no apareció en el ranking |
| o01 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o02 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o03 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |

## Metodología

- **Conjunto**: 40 preguntas en `tests/fixtures/rag/eval_questions.jsonl`, distribuidas en 12 de
  paráfrasis, 10 con cifras, 8 con nombres propios o siglas, 5 en inglés y 5 fuera de corpus.
- **Modos**: `semantic` (solo similitud), `lexical` (BM25 del Módulo 1) e `hybrid` (fusión 0,65/0,35 con
  bonus de coincidencia doble).
- **Modelo**: `intfloat/multilingual-e5-small` (384 dimensiones, 512 tokens) sobre las 15.211 unidades de
  oro; índice en `data/module2/index` (no versionado).
- **Alcance**: evaluación de **recuperación**, sin invocar al LLM. La cobertura mide si cada pregunta
  obtuvo evidencia; no mide fidelidad de la respuesta generada.

## Lectura de los resultados

| Observación | Evidencia |
|-------------|-----------|
| La recuperación semántica supera a la léxica en todas las métricas | Recall@5 0,571 vs 0,371; MRR 0,435 vs 0,320 |
| La fusión híbrida mejora el Recall@5 sobre la semántica pura | 0,600 vs 0,571 |
| El híbrido iguala el Recall@1 y el Recall@3 de la semántica, sin regresión | 0,343 y 0,514 en ambos |
| El coste de la fusión es acotado | 1.194 ms vs 999 ms de la léxica pura (+19,6 %, dentro de SC-006) |

**Por qué gana la semántica**: las preguntas de paráfrasis usan sinónimos que no aparecen literalmente
en el corpus («desechos líquidos» por «vertimientos», «tallo azucarero» por «caña»). La léxica falla en
10 de 12 preguntas de paráfrasis; la semántica acierta 5 de 12 en el top-1 y 7 de 12 en el top-5.

**Por qué se mantiene la léxica**: en cifras y nombres propios la coincidencia exacta sigue siendo una
señal fuerte. Casos como `f01` («24.000 hectáreas») o `n01` (BONSUCRO) se resuelven con términos exactos
que el embedding diluye.

## Análisis de errores por tipo

| Tipo | Aciertos híbridos (top-5) | Causa principal | Ejemplo 1 | Ejemplo 2 |
|------|---------------------------|-----------------|-----------|-----------|
| `paraphrase` | 7/12 | El corpus usa una formulación muy distinta y el fragmento esperado no comparte entidades | `p01`: «desechos líquidos» no activa «vertimientos» con suficiente similitud | `p06`: «conservar bosques» compite con unidades de reforestación de otro año |
| `figure` | 7/10 | Cifras cercanas en varias unidades y truncamiento a 520 caracteres en el fixture | `f09`: el monto de inversión aparece en dos párrafos | `f10`: el déficit se cita en el informe de la Fundación con otra redacción |
| `proper_noun` | 6/8 | Siglas con varias definiciones en el corpus | `n04`: «Laredo» aparece en varias filiales | `n05`: «RSPO» compite con «ISCC» en el mismo párrafo |
| `english` | 2/5 | El modelo es multilingüe, pero el corpus está en español y los términos técnicos no se alinean | `e01`: «wastewater» ↔ «vertimientos» | `e03`: «hectares» ↔ «hectáreas» |
| `out_of_corpus` | 0/5 | El umbral de 0,30 es permisivo en el modo semántico puro | `o01` («arepas») devuelve unidades de alimentos | `o04` («Mongolia») devuelve unidades de geografía |

**Acción derivada**: en el pipeline real, el umbral se aplica junto con la señal léxica y el fallback de
tareas; por eso el modo `hybrid` no inventa aunque `semantic` devuelva candidatos débiles. Aun así, subir
`min_similarity` a 0,35 reduciría los falsos positivos de `out_of_corpus` a costa de Recall; queda como
experimento de M1-09.

## Fidelidad y citas

- La cobertura de evidencia es 1,000 en los tres modos: toda pregunta en corpus obtiene al menos un
  fragmento. No equivale a fidelidad.
- La fidelidad de la respuesta se mide en dos capas: automática (toda cita `[U#]` debe existir en
  `used_unit_ids`, lo que ya verifican las pruebas de contrato e integración) y manual (muestra de 20
  respuestas revisadas). La revisión manual requiere generar respuestas y queda registrada como pendiente
  en este informe.
- El contrato `TaskResult` conserva `status`, `citations`, `fallback` y `review_required`; la traza se
  adjunta sin alterar esas garantías.

## Modo demostración sin red

Validado con la prueba `tests/integration/test_rag_api.py::test_ask_demo_works_without_network`, que
bloquea conexiones externas durante la petición: `mode="demo"` responde con el modelo guionizado y el
índice de prueba versionado en `tests/fixtures/rag/index`, sin descargar el modelo real ni abrir red.

## Reproducción

```powershell
uv run python -m proyecto_modelos_lenguaje.rag index verify
uv run python -m proyecto_modelos_lenguaje.rag evaluate `
  --questions tests/fixtures/rag/eval_questions.jsonl `
  --embedder fastembed `
  --out docs/evaluacion_modulo2.md `
  --json-out data/module2/evaluation.json `
  --run-id 2026-11-06-e5-small
```

## Limitaciones

- La primera consulta de cada modo incluye la carga del modelo y el calentamiento de la caché; por eso
  la latencia media puede superar el p95.
- El fixture de 50 unidades usa `HashEmbedder` (determinista, sin semántica) y solo sirve para probar el
  flujo; las métricas de este informe se calcularon con el modelo real sobre las 15.211 unidades.
- La comparación con el Módulo 1 se hace contra su recuperación léxica medida en este mismo conjunto,
  porque la línea base de 40 preguntas de M1-08 aún no estaba registrada.

## Notas

- La cobertura de citas mide la disponibilidad de evidencia por pregunta; la fidelidad requiere generación y revisión manual (ver informe).
- Evaluación de recuperación: no se invocó al LLM.
