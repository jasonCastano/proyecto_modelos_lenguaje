# Evaluación del Módulo 2 — recuperación semántica e híbrida

**Ejecución**: `m2-baseline-2026-11-10` · **Índice**: `intfloat/multilingual-e5-small` (384 d, 15211 fragmentos, troceo `unit+window` 400/60 tokens, construido 2026-11-11T00:30:25+00:00) · **Comando**: `uv run python -m proyecto_modelos_lenguaje.rag evaluate --questions <conjunto> --warmup 3`

Línea base de la spec 014 (T026), antes del agente. Evaluación de recuperación: no se invoca al LLM. Las repreguntas elípticas (`follow_up`) y las consultas sin unidades etiquetadas (saludos, ambiguas) no puntúan aquí; se miden en la evaluación conversacional.

## Lectura de la línea base (2026-11-10)

| Métrica | Léxico (Módulo 1) | Semántico | Híbrido |
|---------|------------------:|----------:|--------:|
| Recall@10 — 40 preguntas | 0,371 | 0,686 | 0,671 |
| nDCG@10 — 40 preguntas | 0,333 | 0,493 | 0,499 |
| Recall@10 — 30 consultas | 0,300 | 0,478 | 0,450 |
| nDCG@10 — 30 consultas | 0,342 | 0,437 | 0,434 |
| Abstención fuera de corpus (ambos conjuntos) | 0,000 | 0,000 | 0,000 |
| Latencia p95 — 40 preguntas | 1.564 ms | 14 ms | 1.648 ms |

1. **SC-001 se cumple frente a la línea base**: el semántico y el híbrido superan al léxico del Módulo 1
   en Recall@10 y nDCG@10 en los dos conjuntos.
2. **El híbrido no supera al semántico puro**: empata en nDCG@10 (±0,006) y queda algo por debajo en
   Recall@10. La fusión aporta en las preguntas con nombres propios y cifras, pero cuesta ~1,3 s por
   consulta porque la búsqueda léxica recorre las 15.211 unidades; el semántico tarda 8–14 ms.
3. **Ningún modo se abstiene** ante preguntas fuera de corpus (0 de 5 y 0 de 4). Confirma la revisión del
   PR #34: la abstención no puede depender del umbral de similitud y debe venir de la puerta de
   decisión de la US2 (FR-011).
4. La latencia ahora se mide tras 3 consultas de calentamiento y el p95 se interpola sobre la muestra
   ordenada, por eso p95 ≥ media (en la spec 013 aparecía p95 < media).
5. El conjunto de 30 consultas lo etiquetó Roberto José Guerrero buscando por palabras clave en el oro;
   está pendiente la revisión de Jason Alejandro Castaño (T018).

## Conjunto spec 013 — 40 preguntas

**Ejecución**: `m2-baseline-2026-11-10-q40` · **Preguntas**: 40 (35 con unidades etiquetadas) · **Línea base**: lexical · **Calentamiento**: 3 consultas descartadas por modo

### Métricas por modo

| Modo | Recall@1 | Recall@3 | Recall@5 | Recall@10 | nDCG@10 | MRR | Cobertura | Abstención | Latencia media | p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| semantic | 0.343 | 0.514 | 0.571 | 0.686 | 0.493 | 0.435 | 1.000 | 0.000 | 12.2 ms | 14.2 ms |
| lexical | 0.286 | 0.343 | 0.371 | 0.371 | 0.333 | 0.320 | 1.000 | 0.000 | 1219.6 ms | 1563.6 ms |
| hybrid | 0.343 | 0.514 | 0.600 | 0.671 | 0.499 | 0.450 | 1.000 | 0.000 | 1351.6 ms | 1648.0 ms |

**Veredicto**: hybrid >= baseline en Recall@10, nDCG@10 y MRR

*Recall@k* = fracción de unidades relevantes en el top-k; *nDCG@10* con relevancia binaria; *Abstención* = preguntas fuera de corpus sin evidencia devuelta.

### Consultas donde el híbrido empeora frente al léxico

| Pregunta | Tipo | nDCG@10 híbrido | nDCG@10 léxico |
|---|---|---|---|
| n04 | proper_noun | 0.000 | 1.000 |

### Análisis de errores

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
| o04 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o05 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| p01 | hybrid | paraphrase | la unidad esperada no apareció en el ranking |
| p02 | hybrid | paraphrase | la unidad esperada no apareció en el ranking |
| p05 | hybrid | paraphrase | la unidad esperada no apareció en el ranking |
| p06 | hybrid | paraphrase | la unidad esperada no apareció en el ranking |
| p11 | hybrid | paraphrase | la unidad esperada no apareció en el ranking |
| p12 | hybrid | paraphrase | la unidad esperada no apareció en el ranking |
| e01 | hybrid | english | la unidad esperada no apareció en el ranking |
| e04 | hybrid | english | la unidad esperada no apareció en el ranking |
| e05 | hybrid | english | la unidad esperada no apareció en el ranking |
| o01 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o02 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o03 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o04 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| o05 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
## Conjunto spec 014 — 30 consultas con ruta

**Ejecución**: `m2-baseline-2026-11-10-r30` · **Preguntas**: 36 (18 con unidades etiquetadas) · **Línea base**: lexical · **Calentamiento**: 3 consultas descartadas por modo

### Métricas por modo

| Modo | Recall@1 | Recall@3 | Recall@5 | Recall@10 | nDCG@10 | MRR | Cobertura | Abstención | Latencia media | p95 |
|---|---|---|---|---|---|---|---|---|---|---|
| semantic | 0.243 | 0.393 | 0.431 | 0.478 | 0.437 | 0.524 | 1.000 | 0.000 | 8.1 ms | 9.7 ms |
| lexical | 0.270 | 0.289 | 0.300 | 0.300 | 0.342 | 0.500 | 1.000 | 0.000 | 1173.4 ms | 1395.9 ms |
| hybrid | 0.270 | 0.348 | 0.431 | 0.450 | 0.434 | 0.547 | 1.000 | 0.000 | 1380.7 ms | 1574.3 ms |

**Veredicto**: hybrid >= baseline en Recall@10, nDCG@10 y MRR

*Recall@k* = fracción de unidades relevantes en el top-k; *nDCG@10* con relevancia binaria; *Abstención* = preguntas fuera de corpus sin evidencia devuelta.

### Consultas donde el híbrido empeora frente al léxico

| Pregunta | Tipo | nDCG@10 híbrido | nDCG@10 léxico |
|---|---|---|---|
| r12 | documental | 0.469 | 0.765 |

### Análisis de errores

| Pregunta | Modo | Tipo | Causa |
|---|---|---|---|
| r07 | semantic | documental | la unidad esperada no apareció en el ranking |
| r09 | semantic | documental | la unidad esperada no apareció en el ranking |
| r13 | semantic | documental | la unidad esperada no apareció en el ranking |
| r14 | semantic | documental | la unidad esperada no apareció en el ranking |
| r15 | semantic | documental | la unidad esperada no apareció en el ranking |
| r18 | semantic | documental | la unidad esperada no apareció en el ranking |
| r25 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r26 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r27 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r28 | semantic | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r07 | lexical | documental | la unidad esperada no apareció en el ranking |
| r09 | lexical | documental | la unidad esperada no apareció en el ranking |
| r10 | lexical | documental | la unidad esperada no apareció en el ranking |
| r13 | lexical | documental | la unidad esperada no apareció en el ranking |
| r14 | lexical | documental | la unidad esperada no apareció en el ranking |
| r15 | lexical | documental | la unidad esperada no apareció en el ranking |
| r18 | lexical | documental | la unidad esperada no apareció en el ranking |
| r21 | lexical | structured | la unidad esperada no apareció en el ranking |
| r23 | lexical | structured | la unidad esperada no apareció en el ranking |
| r25 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r26 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r27 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r28 | lexical | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r07 | hybrid | documental | la unidad esperada no apareció en el ranking |
| r09 | hybrid | documental | la unidad esperada no apareció en el ranking |
| r13 | hybrid | documental | la unidad esperada no apareció en el ranking |
| r14 | hybrid | documental | la unidad esperada no apareció en el ranking |
| r15 | hybrid | documental | la unidad esperada no apareció en el ranking |
| r18 | hybrid | documental | la unidad esperada no apareció en el ranking |
| r25 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r26 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r27 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |
| r28 | hybrid | out_of_corpus | devolvió evidencia para una pregunta fuera de corpus |

<!-- router:start -->
## Enrutador (US2)

**Ejecución**: `router-real-2026-11-10` · **Modo**: real · **Casos**: 36 (30 consultas + 6 repreguntas con su turno previo como historial)

| Métrica | Valor | Criterio |
|---|---:|---|
| Precisión del enrutador | 0.972 (35/36) | SC-002 ≥ 0,90 |
| Saludos y fuera de alcance sin búsqueda | 10/10 | SC-004 100 % |
| Llamadas al modelo | 26 | 0 en reglas |
| Latencia media por decisión | 1335 ms | — |

Matriz de confusión (filas: esperada; columnas: predicha):

| Esperada \ Predicha | direct | documental | structured | out_of_scope | clarify |
|---|---|---|---|---|---|
| direct | 6 | 0 | 0 | 0 | 0 |
| documental | 0 | 17 | 1 | 0 | 0 |
| structured | 0 | 0 | 6 | 0 | 0 |
| out_of_scope | 0 | 0 | 0 | 4 | 0 |
| clarify | 0 | 0 | 0 | 0 | 2 |

Errores:

| Consulta | Esperada | Predicha | Confianza | Decidió | Motivo |
|---|---|---|---:|---|---|
| r32 «¿Cuánto bioetanol produce allá al año?» | documental | structured | 0.90 | llm | pregunta por una cifra puntual de producción anual de bioetanol en Brasil |

Lectura:

- **Cumple SC-002 y SC-004**: 0,972 de precisión con DeepSeek (≥ 0,90) y 10/10 saludos y preguntas fuera
  de alcance resueltos por reglas, sin búsqueda ni llamadas al modelo.
- **Resuelve la abstención**: las 4 preguntas fuera de corpus se enrutan a `out_of_scope` antes de buscar.
  La recuperación sola no se abstenía en ningún modo (sección anterior).
- El único error (r32) es discutible: la repregunta pide una cifra («¿cuánto bioetanol produce allá al
  año?») y el modelo la mandó a `structured`; con la caída a documental cuando la tabla no tiene el dato,
  la respuesta sigue siendo correcta.
- El modo demo (heurística sin modelo) también acierta 35/36, pero esa heurística se escribió conociendo el
  conjunto: no es una medida independiente y solo garantiza un modo demo determinista.
- Costo: 26 llamadas al modelo (una por consulta no resuelta por reglas), 1,3 s de media por decisión.

<!-- router:end -->

<!-- variants:start -->
## Cadena vs. agente (T066)

**Ejecución**: `variants-real-2026-11-11` · **Modo**: real · **Consultas**: 36 (cada una en un hilo nuevo; las 6 repreguntas en el hilo de su pregunta previa; una consulta de calentamiento descartada)

| Métrica | chain | agent |
|---|---|---|
| Validez de citas (SC-003) | 100 % | 100 % |
| Respuestas factuales con cita | 100 % | 100 % |
| Abstención fuera de corpus | 100 % | 100 % |
| Repreguntas correctas (SC-006) | 50 % | 67 % |
| Evidencia esperada recuperada (documentales) | 50 % | 67 % |
| Latencia media (ms) | 3415 | 5168 |
| Latencia p95 (ms) | 7842 | 14674 |
| Respuestas < 10 s (SC-007) | 100 % | 94 % |
| Llamadas al modelo por consulta | 1.39 | 2.17 |
| Búsquedas por consulta | 0.67 | 1.31 |
| Tokens por consulta | 2695 | 5275 |
| Fidelidad (juez LLM) | 0.705 | 0.661 |
| Relevancia de la respuesta (juez LLM) | 0.885 | 0.825 |
| Precisión de contexto (con referencia) | 0.391 | 0.448 |

Respuestas evaluadas por el juez: chain 24, agent 24. El juez usa `prompts/judge.md` con las definiciones de Ragas (fidelidad = afirmaciones respaldadas / afirmaciones; relevancia = qué tan directamente responde); la precisión de contexto usa las unidades esperadas como referencia.

Repreguntas por variante:

| Consulta | chain | agent |
|---|---|---|
| r31 «¿Y a qué cliente le exporta esa uva?» | ❌ documental, 3 citas | ✅ documental, 5 citas |
| r32 «¿Cuánto bioetanol produce allá al año?» | ❌ structured, 6 citas | ❌ structured, 6 citas |
| r33 «¿A quién le compró las haciendas?» | ✅ documental, 3 citas | ❌ documental, 3 citas |
| r34 «¿Qué tan productivo es ese cultivo?» | ✅ documental, 3 citas | ✅ documental, 6 citas |
| r35 «¿Cómo se llama ese programa?» | ✅ documental, 3 citas | ✅ documental, 5 citas |
| r36 «¿Desde cuándo vende esa energía?» | ❌ structured, 2 citas | ✅ structured, 5 citas |

<!-- variants:end -->

### Lectura de la comparación (2026-11-11)

- **SC-003 (citas)**: 100 % en ambas variantes. Toda respuesta factual cita evidencia válida o declara falta de
  evidencia; la validación lo garantiza por construcción.
- **Abstención fuera de corpus**: 4/4 en ambas, resuelta por el enrutador sin buscar.
- **SC-006 (repreguntas ≥ 80 %)**: **no se cumple con la métrica automática** (cadena 3/6, agente 4/6). La
  métrica exige que la unidad etiquetada como esperada esté entre los fragmentos recuperados. Leyendo las seis
  respuestas, ambas variantes resuelven la referencia con el hilo en 5/6 casos, con otra evidencia válida:
  cadena r31 nombra a Walmart, r36 responde 2016; agente r32 responde por Brasil («allá») y declara que la
  producción anual no está en el corpus. Fallos por contenido: cadena r32 (responde con la capacidad de Colombia,
  no de Brasil) y agente r33 (no dice a quién se compraron las haciendas). Esta lectura es de Roberto José
  Guerrero y **requiere calificación humana del equipo** antes de darla por buena.
- **SC-007 (< 10 s)**: cadena 100 %, agente 94 % (p95 14,7 s). El agente hace 1,3 búsquedas y 2,2 llamadas al
  modelo por consulta frente a 0,7 y 1,4 de la cadena, y gasta casi el doble de tokens.
- **Fidelidad del juez: no válida en esta ejecución.** Para las filas estructuradas `[F#]` el juez recibió solo
  `sujeto · atributo = valor`, sin la frase de origen que el modelo sí vio, y marcó como no respaldadas
  afirmaciones que estaban en esa frase (r19–r23). El error está corregido en `agent/compare.py`; una segunda
  ejecución se detuvo por falta de memoria del equipo en la consulta 14 y queda **PENDIENTE**. La relevancia
  (cadena 0,885, agente 0,825) y la precisión de contexto (0,391 y 0,448) no dependen de ese error.
- **Elección**: la cadena es la variante por defecto (más rápida, más barata, cumple SC-007); el agente
  recupera mejor la evidencia esperada (67 % frente a 50 % en documentales) y resuelve más repreguntas con la
  métrica estricta.
