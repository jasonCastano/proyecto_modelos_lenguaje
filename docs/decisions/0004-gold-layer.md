# ADR 0004 — Capa oro (gold) del medallion

- **Estado**: aceptada
- **Fecha**: 2026-10-30
- **Autores**: Jason Alejandro Castaño, Roberto José Guerrero
- **Contexto**: Módulo 1 del curso, base de conocimiento de Manuelita

## Contexto

La plata contiene 404 documentos canónicos y 3.810 fragmentos con evidencia y linaje. El Módulo 1 necesita
un corpus consolidado, ordenado por temas y acotado por tokens para Resumen, FAQ y Q&A, sin que un modelo
invente afirmaciones ni pierda las citas.

## Decisiones

1. **Unidades extractivas**: cada unidad es una oración o pasaje literal del fragmento de plata. No se
   resumen ni se generan afirmaciones con un LLM.
2. **Taxonomía controlada**: `config/gold_taxonomy.toml` define 16 temas, palabras clave, alias y mapeo a los
   24 ítems. La clasificación es determinista y sin embeddings.
3. **Entidades**: vocabulario controlado con alias (Manuelita, filiales, marcas, certificaciones). Los nombres
   alternativos se agrupan bajo una entidad canónica.
4. **Hechos**: solo se crean cuando hay sujeto, atributo, valor y unidad explícitos. Las cifras sin contexto
   quedan como pasajes; no se inventan tripletas.
5. **Conflictos**: se comparan hechos con el mismo sujeto/atributo. La autoridad y la fecha eligen la versión
   principal; los empates quedan `disputed` con ambas evidencias. No se promedian cifras.
6. **Deduplicación**: hash del texto normalizado para exactos y Jaccard de shingles de 5 palabras (umbral 0.90)
   para cercanos; se fusionan evidencias.
7. **Cobertura**: un ítem es `covered` con ≥3 unidades y ≥1 fuente oficial; `partial` con 1–2 o solo terceros;
   `missing` sin unidades. La cobertura se mide por evidencia, no por palabras clave del bronce.
8. **Contexto**: selección greedy por cobertura, autoridad, vigencia y diversidad; presupuestos de 8.000 y
   32.000 tokens con el proxy de plata. El paquete mayor contiene al menor.
9. **FAQ seeds**: preguntas deterministas desde ítems, temas y entidades, con evidencia; las respuestas se
   generan en el Módulo 1.
10. **Estado**: JSONL incremental por `doc_id + text_hash + config_hash`; las salidas se reescriben de forma
    atómica.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| LLM para extraer tripletas o resumir | Fuera de alcance, no determinista y riesgo de alucinación |
| Embeddings para clasificar temas | No reproducibles sin modelo; la taxonomía es suficiente |
| `spaCy` para NER | Descarga de modelos y cobertura limitada de marcas internas |
| Promediar cifras contradictorias | Viola la procedencia y oculta el conflicto |
| Indexar todos los fragmentos en el contexto | Excede la ventana del modelo y repite información |
| Resolver conflictos por frecuencia | Puede elegir una fuente minoritaria |

## Consecuencias

- La capa oro es reproducible, offline y auditable.
- El contexto está acotado y cada bloque cita su fuente.
- La cobertura es más realista que la matriz por palabras clave, pero depende de la calidad de la plata.
- Los conflictos genéricos requieren revisión muestral antes de la evaluación final.

## Validación observada

Ejecución `2026-10-gold-01` (2026-10-30 UTC):

- 404 documentos de plata y 3.810 fragmentos; 404 procesados, 0 omitidos, 0 fallidos.
- 15.211 unidades, 381 hechos, 15 entidades y 38 conflictos.
- 24/24 ítems de cobertura evaluados; 8.000 y 32.000 tokens en los paquetes de contexto.
- 1.000.109 tokens de unidades; 54,5 s de duración.
- `pml gold verify --sample 100`: 100/100 unidades, 24/24 ítems, 0 fallos.

## Licencias

Sin dependencias nuevas. Se reutilizan la biblioteca estándar, `PyYAML` (MIT) y los módulos MIT del proyecto.
