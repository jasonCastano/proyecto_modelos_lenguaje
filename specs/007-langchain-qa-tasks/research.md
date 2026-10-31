# Fase 0 — Investigación: tareas LangChain del Módulo 1

**Feature**: `007-langchain-qa-tasks`
**Fecha**: 2026-10-30
**Estado**: decisiones cerradas; sin `NEEDS CLARIFICATION`.

## 1. Recuperación sin embeddings

- **Decisión**: seleccionar evidencia con una puntuación determinista tipo BM25 simplificada, usando
  tokens normalizados, tema, entidades y señales de calidad de las unidades de oro.
- **Racional**: el Módulo 1 prohíbe embeddings y base vectorial; una puntuación léxica es reproducible,
  explicable y suficiente para 15.211 unidades pequeñas. La selección se puede auditar y testear.
- **Alternativas consideradas**:
  - Solo coincidencia exacta de palabras clave: pierde paráfrasis y preguntas compuestas.
  - Jaccard de shingles: útil para duplicados, pero menos sensible a términos frecuentes.
  - Embeddings: fuera de alcance del Módulo 1.

## 2. Presupuesto y número de unidades para Q&A

- **Decisión**: recuperar hasta **8 unidades** dentro de un presupuesto de **6.000 tokens**, con diversidad
  por tema y penalización de unidades cortas, inciertas o conflictivas.
- **Racional**: 8 unidades cubren preguntas comparativas sin desbordar el contexto; 6.000 tokens dejan
  margen para el prompt y la respuesta en el paquete de 8k.
- **Alternativas consideradas**:
  - Una sola unidad: insuficiente para comparaciones y síntesis.
  - 20 unidades: contexto innecesario, más latencia y más ruido.
  - Todo el paquete de 8k en cada pregunta: desperdicia tokens y diluye la evidencia.

## 3. Protocolo de citas

- **Decisión**: etiquetar las unidades seleccionadas como `[U1]`, `[U2]`, … en el contexto; el modelo debe
  citar esas etiquetas. El sistema las mapea a `unit_id`, URL y sección, y descarta citas fuera del conjunto.
- **Racional**: las etiquetas cortas reducen errores del modelo y permiten validar cada cita contra las
  unidades realmente enviadas. Una cita global `unit_...` es más larga y propensa a errores.
- **Alternativas consideradas**:
  - Citar `unit_id` completo: más verboso y difícil de verificar.
  - Citar solo el título: ambiguo cuando hay varias secciones del mismo documento.
  - No validar citas: permite alucinaciones de fuente.

## 4. Estructura de prompts

- **Decisión**: tres plantillas Markdown versionadas (`prompts/summary.md`, `prompts/faq.md`,
  `prompts/qa.md`), cada una con seis secciones: rol, tarea, contexto delimitado, reglas, formato de cita y
  comportamiento sin evidencia. Se cargan como texto y se rellenan con marcadores explícitos.
- **Racional**: la constitución exige prompts versionados y auditables; Markdown es legible, diffeable y
  fácil de revisar. El hash del prompt se registra en cada resultado.
- **Alternativas consideradas**:
  - Prompts embebidos en Python: difíciles de auditar y versionar.
  - YAML/JSON: más estructura, pero peor legibilidad para revisión humana.
  - Un solo prompt para las tres tareas: mezcla instrucciones y degrada la calidad.

## 5. Resumen: paquete de contexto

- **Decisión**: usar `data/gold/context_8000.json` por defecto y `context_32000.json` solo si el modelo
  soporta la ventana. Los bloques ya incluyen cita, tema y autoridad.
- **Racional**: el paquete de oro ya seleccionó la evidencia por cobertura, autoridad, vigencia y diversidad;
  reconstruirla en M1-05 duplicaría lógica y rompería la reproducibilidad.
- **Alternativas consideradas**:
  - Re-recuperar unidades para el resumen: otra ruta y posibles diferencias.
  - Concatenar todas las unidades: excede el contexto y repite información.

## 6. FAQ: una llamada por pregunta semilla

- **Decisión**: generar la FAQ con una llamada por cada pregunta semilla seleccionada, hasta un máximo de
  12 (configurable), usando sus `evidence_unit_ids`.
- **Racional**: cada respuesta necesita sus propias citas y validación; una llamada por semilla es más
  controlable que un único JSON con 20 respuestas. El costo local es aceptable.
- **Alternativas consideradas**:
  - Una sola llamada para toda la FAQ: el modelo pierde citas y mezcla evidencia.
  - JSON estructurado con varias respuestas: frágil y difícil de validar.
  - Generar preguntas nuevas con el modelo: riesgo de inventar y duplicar; las semillas ya tienen evidencia.

## 7. Manejo de citas ausentes o inválidas

- **Decisión**: si la respuesta no contiene citas, reintentar una vez con una instrucción más estricta. Si
  vuelve a fallar, lanzar `TaskError` con código `missing_citations`. Si cita unidades fuera del contexto,
  descartar esas citas y marcar `review_required=True`.
- **Racional**: una respuesta sin cita no es publicable; una cita inventada es peor que un fallback. El
  reintento único evita bucles y costos.
- **Alternativas consideradas**:
  - Aceptar respuestas sin cita: viola la constitución.
  - Reintentar indefinidamente: costo y latencia impredecibles.
  - Eliminar la respuesta completa ante una cita inválida: pierde evidencia válida.

## 8. Inyección de instrucciones en el contexto

- **Decisión**: delimitar el contexto con etiquetas `<context>` y `<unit id="U1">`, y declarar que su
  contenido es dato no confiable. Las pruebas incluyen unidades con “ignora las instrucciones” y verifican
  que no se ejecuten.
- **Racional**: el corpus incluye PDFs y noticias de terceros; una instrucción embebida no debe cambiar el
  comportamiento del sistema.
- **Alternativas consideradas**:
  - Confiar en el modelo: no es verificable.
  - Eliminar manualmente texto sospechoso: no escala y puede borrar evidencia.

## 9. Modelo falso y pruebas

- **Decisión**: usar `build_fake_model()` de M1-04 con respuestas enlatadas que incluyan citas `[U1]`; las
  pruebas unitarias, de contrato y de integración no usan red. La prueba real con Ollama es opcional.
- **Racional**: la suite debe ser rápida, determinista y gratuita; el modelo real se reserva para la
  validación manual y M1-08.
- **Alternativas consideradas**:
  - Mockear el modelo con `unittest.mock`: menos realista que un `BaseChatModel`.
  - Usar Ollama en CI: lento, no determinista y dependiente de hardware.

## 10. Configuración de tareas

- **Decisión**: añadir `config/tasks.toml` con `[qa]`, `[summary]` y `[faq]`: top-k, presupuesto, límite de
  FAQ, mínimo de citas y umbral de evidencia. La configuración se versiona y se registra en el resultado.
- **Racional**: separa los parámetros de recuperación del modelo; permite ajustar sin tocar código y
  reproducir la evaluación.
- **Alternativas consideradas**:
  - Constantes en Python: cambios dispersos y menos auditables.
  - Variables de entorno: menos visibles y difíciles de versionar.

## 11. Interfaz de biblioteca y CLI

- **Decisión**: `tasks.py` expone `summarize_corpus`, `generate_faq` y `answer_question`, más un `main()` con
  subcomandos `summary`, `faq` y `qa` para validación manual. No depende de Streamlit.
- **Racional**: la app M1-07 y la evaluación M1-08 reutilizan la biblioteca; el CLI permite probar sin UI y
  alimentar el prompt log de M1-06.
- **Alternativas consideradas**:
  - Solo CLI: obliga a la app a invocar procesos.
  - Solo biblioteca: dificulta la demo y el prompt log.
  - Streamlit primero: mezcla interfaz con lógica.

## 12. Dependencias

- **Decisión**: no añadir dependencias nuevas. Se reutilizan LangChain, `llm.py`, la biblioteca estándar y
  los datos de oro. El tokenizado y la puntuación son propios.
- **Racional**: el proyecto ya tiene el modelo y los datos; una dependencia de búsqueda no aporta valor para
  este alcance.
- **Alternativas consideradas**:
  - `rank_bm25`: dependencia pequeña, pero innecesaria para una implementación explicable.
  - `scikit-learn`: pesada y fuera del alcance.
