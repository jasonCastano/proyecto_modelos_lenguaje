# ADR 0019 — Blindaje del RAG verificado con el modelo real

- **Estado**: aceptada
- **Fecha**: 2026-11-14
- **Autor**: Jason Alejandro Castaño
- **Relacionadas**: ADR 0016 (agente con LangGraph), ADR 0018 (rúbrica del Módulo 2);
  `specs/015-rag-injection-shield-real/` (spec, plan, research R1–R8, tasks).

## Contexto

La rúbrica del Módulo 2 evalúa el caso 5, «Blindaje del RAG»: un documento del corpus esconde «ignora las
instrucciones anteriores» y el agente debe tratarlo como dato. Ya existía un blindaje: delimitación con
`<documento>`, un detector de instrucciones y el descarte de respuestas que filtran el prompt (spec 014,
FR-016). Sin embargo:

1. **El corpus adversarial solo se activaba en modo demo**, con el modelo simulado (`api.py`: `mode == "demo"`). En vivo no se podía mostrar a DeepSeek resistiendo la inyección.
2. **El índice adversarial usaba vectores hash** con el perfil del modelo real. En modo real, las consultas vectorizadas con e5 se habrían comparado contra esos vectores.
3. **En modo real se abría la colección Qdrant del corpus real.** Activar el corpus adversarial tal como estaba habría mezclado los dos corpus.
4. **El fragmento marcado llegaba intacto al modelo**, y las pruebas de «no obedece» usaban modelos guionados.

## Decisión

1. **Activación única para los dos modos**:
   - `MANUELITA_DEMO_CORPUS=malicious`, opción del servidor apagada por defecto, centralizada en `agent/adversarial.py`.
   - La interfaz muestra un aviso y las trazas llevan la etiqueta `corpus:adversarial`.
2. **Corpus de prueba separado** en `tests/fixtures/rag/malicious/`:
   - 5 unidades legítimas y 6 de ataque: ignorar instrucciones, revelar el prompt, cambio de rol, sistema falso, pedir una escritura e instrucción en inglés.
   - Un índice hash (`index/`) y otro real con fastembed (`index_real/`).
   - El oro no se toca.
3. **Qdrant siempre en memoria** con el corpus adversarial, así que la colección real no se consulta ni se modifica.
4. **Neutralización por oración** (`guard.neutralize`):
   - Las oraciones con instrucciones se sustituyen por `[instrucción embebida omitida]` antes de llegar al modelo, en el punto común de las dos variantes (`search_documents_impl`).
   - El resto del fragmento se conserva y la traza registra `neutralized_sentences`.
   - La detección normaliza mayúsculas, tildes y caracteres invisibles.
   - Se añadió el patrón `accion_escritura`.
   - `prompts/agent.md` pasa a la versión 1.2 y explica la marca.
5. **Evaluación reproducible** con `agent shield`:
   - Batería de 6 casos en las dos variantes, con repeticiones.
   - Métricas: obediencia, fuga del prompt, intento de escritura y utilidad.
   - Línea base sin neutralización (`--no-neutralize`).
   - Resultados en `docs/evaluacion_blindaje.md` y en los JSON.

## Alternativas consideradas

- **Insertar el documento malicioso en el corpus real**: rechazada. La constitución prohíbe reescribir las capas de datos.
- **Solo búsqueda léxica en modo real**: rechazada. No ejercita la ruta semántica del sistema.
- **Construir el índice al arrancar**: rechazada. Añade latencia y no determinismo.
- **Descartar fragmentos anómalos completos**: rechazada. Pierde evidencia legítima.
- **Clasificador LLM de inyección o juez LLM de obediencia**: rechazada. Es más caro y no determinista; una señal léxica por caso basta.
- **Colección Qdrant adversarial en el servidor**: rechazada. Es infraestructura extra sin necesidad.

## Consecuencias

- El caso 5 se demuestra en vivo con DeepSeek arrancando con `MANUELITA_DEMO_CORPUS=malicious`, en los modos demo y real.
- La defensa ya no depende solo de que el modelo respete la regla del prompt: la orden inyectada no llega al modelo.
- Los patrones de detección pueden tener falsos positivos y negativos. Hay pruebas con oraciones legítimas que no deben neutralizarse, y la delimitación sigue siendo la defensa principal.
- `agent shield --mode real` consume créditos del proveedor. Las pruebas con red (`test_shield_real.py`) quedan fuera de la CI.
- Si se edita `gold_malicious.jsonl`, hay que regenerar los dos índices (`build_fixture.py malicious [--real]`).
