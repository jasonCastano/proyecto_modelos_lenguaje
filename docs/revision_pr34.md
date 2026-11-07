# Revisión de alineación del PR #34 con la constitución v1.3.0

**PR**: [#34 «feat(rag): recuperación semántica para el chatbot (Módulo 2)»](https://github.com/jasonCastano/proyecto_modelos_lenguaje/pull/34)
· autor Roberto José Guerrero · fusionado 2026-11-07 (`748cc06`)

**Revisión**: 2026-11-07 · Jason Alejandro Castaño, con asistencia de Claude Code (declarada)

**Referencia**: `CONSTITUTION.md` v1.3.0, §5 Fase 2 (reglas 1–14 y puerta), y `specs/014-rag-agent-memory-router/`.

## 1. Cómo se verificó

Todas las cifras de este documento salen de ejecuciones reales en este equipo, sobre `main` con el PR fusionado:

| Comprobación | Comando | Resultado |
|--------------|---------|-----------|
| Calidad completa | `make check` | Verde: 385 pruebas Python (12 omitidas) + 17 web, Ruff limpio, build OK |
| Índice | `uv run python -m proyecto_modelos_lenguaje.rag index build` y `index verify` | 15.211 fragmentos de 384 d; `gold_sha256` `20794f61…` |
| Reproducción | `rag evaluate --questions tests/fixtures/rag/eval_questions.jsonl --top-k 10` | Recall@1/3/5/8 y MRR **idénticos** a `docs/evaluacion_modulo2.md` |
| Métricas de la Clase 7 | Script de revisión sobre `rag.evaluate._rankings` (top 10, presupuesto 6.000) | Ver §3 |

## 2. Resultado por regla de la Fase 2

| Regla v1.3.0 | Estado | Evidencia y observación |
|--------------|--------|-------------------------|
| 1. Embeddings justificados | 🟡 Parcial | `multilingual-e5-small`, 384 d, 512 tokens, prefijos y L2 documentados (ADR 0014). **Falta** la evidencia MTEB de *retrieval* en español que pide la Clase 6. |
| 2. Base vectorial persistente y derivada | ✅ con matices | `numpy` + SQLite + manifiesto, fuera de Git, reconstruible; alternativa a Chroma/FAISS justificada. **Falta** el filtro por metadatos y exponerlo como retriever de LangChain (lo necesita el agente de la spec 014). |
| 3. Chunking medido | 🟡 Parcial | Unidades oro como fragmentos; solo trocea las de más de 512 tokens (480 con 32 de solape, 6,7 % < 10–20 %). Sin medición del efecto. Búsqueda exacta: no hay parámetros ANN que calibrar. |
| 4. Recuperación híbrida | ✅ con matices | Léxica, semántica e híbrida comparadas. Los pesos 0,65/0,35 no se calibraron con el conjunto de consultas (Clase 6). |
| 5–7. Memoria, memoria larga, enrutador | ⏳ Fuera de su alcance | Pendiente en la spec 014. |
| 8. Chain vs. Agent | ⏳ | Pendiente en la spec 014. |
| 9. Blindaje e HITL | 🟡 | Los prompts conservan `<context>` y «dato no confiable» del Módulo 1; no hay prueba adversarial ni HITL. |
| 10. Evaluación de retrieval | 🟡 Parcial | 40 preguntas etiquetadas (35 en corpus + 5 fuera), 3 configuraciones. Reporta Recall@1/3/5/8 y MRR, **no** Recall@10 ni nDCG@10. No mide la abstención fuera de corpus (ver §3). |
| 11. Ragas y LangSmith | ⏳ | No incluido (Clase 10). |
| 12. Integración en la app | ✅ | Fragmentos con puntaje, modo y descartados en la UI; demo sin red con índice de prueba. |
| 13. Prompts nuevos | ✅ N/A | No añade prompts. |
| 14. Informe, demo y tag | ⏳ | Pendiente del cierre de la fase. |

**Proceso**: el PR se fusionó con **0 revisiones formales** en GitHub. Desde el 2026-11-07 `main` exige una
aprobación y los checks `test` y `web`. La ADR 0014 figura con autor «Jason Alejandro Castaño» aunque el PR lo
abrió Roberto; conviene confirmar la autoría.

## 3. Métricas adicionales (Clase 7)

Calculadas sobre las 35 preguntas con unidad esperada; top 10.

| Modo | Recall@10 | nDCG@10 | Fuera de corpus con evidencia |
|------|-----------|---------|-------------------------------|
| lexical | 0,371 | 0,333 | 5 de 5 |
| semantic | 0,686 | 0,493 | 5 de 5 |
| hybrid | 0,671 | 0,499 | 5 de 5 |

- La semántica y la híbrida superan con claridad a la línea base léxica: la conclusión del PR se mantiene.
- En Recall@10 la híbrida queda ligeramente **por debajo** de la semántica pura (0,671 vs. 0,686); en nDCG@10
  es la mejor (0,499). La fusión ordena mejor pero deja fuera alguna unidad en el top 10.

### Hallazgo principal: el umbral no abstiene

| Pregunta | Similitud top 1 |
|----------|-----------------|
| Mínima de las 35 en corpus | 0,839 |
| Media de las 35 en corpus | 0,886 |
| o01 receta de arepas | 0,830 |
| o02 mundial de fútbol | 0,837 |
| o03 tiquete a Marte | 0,825 |
| o04 capital de Mongolia | 0,801 |
| o05 auto eléctrico | 0,867 |

El umbral configurado (`min_similarity = 0.30`) no filtra nada: con e5 las similitudes coseno se concentran
entre 0,8 y 0,9, y las preguntas fuera de corpus puntúan igual que las válidas. **Ningún umbral de similitud
separa ambos grupos.** La abstención depende hoy solo del LLM («Sin evidencia» del prompt). Por eso la
puerta de decisión (screening de fuera de alcance) de la spec 014 es necesaria y no opcional.

La columna «Cobertura 1.000» del reporte se calcula solo sobre las preguntas en corpus; no indica abstención.
La latencia media de `semantic` (54–78 ms) supera a su p95 (8–41 ms) por el arranque en frío de la primera
consulta; conviene calentar el modelo antes de medir.

## 4. Acciones derivadas

| Acción | Dónde se registra |
|--------|-------------------|
| Añadir Recall@10, nDCG@10 y tasa de abstención fuera de corpus a `rag evaluate` | spec 014, FR-020 |
| Puerta de decisión que rechace fuera de alcance antes de buscar | spec 014, FR-011 |
| Citar evidencia MTEB-es en la ADR 0014 | spec 014, FR-004 |
| Filtro por metadatos y retriever de LangChain | spec 014, FR-001/FR-005 |
| Calibrar los pesos híbridos y medir el solapamiento del chunking | spec 014, FR-006 y FR-003 |
| Calentar el modelo antes de medir latencia | spec 014, FR-020 |
