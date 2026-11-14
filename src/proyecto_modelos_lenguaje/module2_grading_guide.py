"""Instrucciones de calificación del Módulo 2 (se escriben en ``docs/calificacion_m2/``).

Los ejemplos son **ilustrativos**: usan preguntas que no están en ``module2_queries.jsonl`` para no
precalificar ningún ítem de las planillas.
"""

INSTRUCTIONS = """# Instrucciones de calificación — evaluación del Módulo 2

La planilla trae respuestas de las **dos variantes del agente** (cadena y agente) mezcladas, en
orden aleatorio y **sin decir cuál es cuál**. Hay dos tipos de ítem (columna `tipo`):

- **`repregunta`**: una pregunta elíptica («¿Y cuánto produce allá?») que depende del turno
  anterior del mismo hilo. Las columnas `pregunta_previa` y `respuesta_previa` muestran ese turno.
- **`muestra`**: una pregunta factual (documental, estructurada o mixta) elegida al azar. Sirve
  para comprobar qué tan bien mide el juez LLM, que calificó las mismas respuestas.

Califica cada fila sola, sin consultar al otro calificador. Llena solo `correccion`, `fiel`,
`resuelve_referencia` y, si quieres, `notas`. No cambies las demás columnas.

## 1. Criterios

- **`correccion`** — `0` incorrecta · `1` parcial · `2` correcta. ¿Responde lo que se preguntó,
  con el dato correcto según los fragmentos? `1` si responde solo una parte o le falta lo esencial.
- **`fiel`** — `si` o `no`. `si` solo si **todas** las afirmaciones factuales de la respuesta se
  deducen de los `fragmentos` (columna con los `[U#]` y `[F#]` que recibió el modelo). Basta una
  cifra, fecha o nombre que no esté en los fragmentos para marcar `no`. Las etiquetas de cita no
  son afirmaciones. Es la misma definición que usa el juez LLM (fidelidad de Ragas).
- **`resuelve_referencia`** — `si` o `no`, **solo en las filas `repregunta`** (en las filas
  `muestra` viene `na`; déjalo así). `si` si la respuesta entiende a qué se refiere la repregunta
  («allá» = Brasil, «esa uva» = la uva de mesa de Perú) según `pregunta_previa`, aunque el dato
  final no sea correcto.

## 2. Casos especiales

- **Abstención** («No hay evidencia suficiente…»): en estas filas la pregunta tenía respuesta
  esperada, así que `correccion` = 0. Es fiel (`si`): no afirma nada. En una repregunta,
  `resuelve_referencia` = `si` si la abstención menciona el tema correcto, si no `no`.
- **Respuesta que declara lo que falta** («El corpus no detalla la producción anual»): es correcta
  (2) si de verdad no está en los fragmentos y responde lo demás.
- **Filas `[F#]`**: son datos de la tabla estructurada o de la serie anual (CSV curado). Una cifra
  calculada por la herramienta (suma, variación) cuenta como respaldada si aparece en el `[F#]`.
- **Corrección y fidelidad son independientes**: una respuesta puede ser correcta y no fiel (agrega
  un dato inventado) o fiel e incorrecta (responde con fragmentos ajenos a lo pedido).

## 3. Cómo responden las dos variantes

Las dos usan el mismo enrutador, el mismo system prompt (`prompts/agent.md`), el mismo modelo
(`deepseek-flash`), la misma recuperación (Qdrant + BM25, tabla SQLite y CSV de series) y la misma
validación de citas. Cambia **quién decide buscar**.

### Cadena (`build_chain_graph`)

- El grafo es fijo: `route` → `retrieve` → `answer`. Si la ruta es documental, estructurada o mixta,
  **siempre recupera una vez** y hace **una sola llamada** al modelo con todos los documentos.
- En una repregunta reescribe la búsqueda con la pregunta previa (`contextual_query`) y le pasa al
  modelo los turnos recientes del hilo.
- Conducta típica: respuestas consistentes y rápidas. Si la búsqueda inicial no trae el dato, no
  vuelve a intentarlo: responde con lo que tiene o se abstiene. En repreguntas puede responder con
  la entidad equivocada si la búsqueda reescrita trajo fragmentos de otro país o filial.

### Agente (`create_agent`)

- El modelo **decide** qué herramienta llamar (`search_documents`, `query_structured`,
  `aggregate_series`) y cuántas veces (hasta tres búsquedas). Recibe el historial del hilo como
  mensajes y la ruta del enrutador como pista.
- Conducta típica: puede hacer una segunda búsqueda más precisa y dar una respuesta más completa,
  pero también puede combinar fragmentos de búsquedas distintas, alargarse o llamar una herramienta
  que no hacía falta. Es más lento.

Estas pautas pueden delatar la variante. Aun así, aplica **los mismos criterios a las dos**.

## 4. Ejemplos de calificación (ilustrativos, no son ítems de tu planilla)

### Ejemplo A — repregunta resuelta pero con dato inventado

- **Pregunta previa**: «¿En qué país tiene Manuelita su operación de uva de mesa?»
- **Respuesta previa**: «En Perú, en el valle de Virú [U1].»
- **Repregunta**: «¿Y cuántas hectáreas siembra allá?»
- **Fragmentos**: `[U1]` «En el valle de Virú (Perú) Manuelita cultiva uva de mesa en 1.200
  hectáreas.»
- **Respuesta**: «En Perú siembra 1.200 hectáreas de uva de mesa [U1], con una producción de 30.000
  toneladas al año.»

| correccion | fiel | resuelve_referencia | notas |
|---|---|---|---|
| 2 | no | si | Entiende «allá» = Perú; las 30.000 toneladas no están en U1. |

### Ejemplo B — repregunta con la entidad equivocada

- **Pregunta previa**: «¿Qué produce Manuelita en Chile?» · **Respuesta previa**: «Mejillones
  [U2].»
- **Repregunta**: «¿Y cuántas personas trabajan allá?»
- **Fragmentos**: `[U1]` «Manuelita genera más de 9.000 empleos directos en Colombia.»
- **Respuesta**: «Trabajan más de 9.000 personas [U1].»

| correccion | fiel | resuelve_referencia | notas |
|---|---|---|---|
| 0 | si | no | Responde con el dato de Colombia como si fuera de Chile. La cifra sí está en U1. |

Una respuesta mejor: «El corpus no trae el número de empleados en Chile; solo indica más de 9.000
empleos directos en Colombia [U1].» (`2`, `si`, `si`).

### Ejemplo C — muestra con fila estructurada

- **Pregunta**: «¿Cuánta caña muele la planta de Palmira por día?»
- **Fragmentos**: `[F1]` «Planta Palmira · capacidad de molienda = 10.000 t/día.» y `[U1]` «La
  planta de Palmira fue modernizada en 2015.»
- **Respuesta**: «La planta de Palmira muele 10.000 toneladas de caña por día [F1].»

| correccion | fiel | resuelve_referencia | notas |
|---|---|---|---|
| 2 | si | na | Dato exacto de F1. |

### Ejemplo D — muestra fiel pero que no responde

- **Pregunta**: «¿Cuál fue la utilidad neta de Manuelita en 2021?»
- **Fragmentos**: `[U1]` «En 2021 Manuelita invirtió en una nueva caldera de biomasa.»
- **Respuesta**: «En 2021 Manuelita invirtió en una nueva caldera de biomasa [U1].»

| correccion | fiel | resuelve_referencia | notas |
|---|---|---|---|
| 0 | si | na | Todo está en U1, pero no responde la utilidad. |

## 5. Cómo debe quedar la planilla

| item | tipo | pregunta | correccion | fiel | resuelve_referencia | notas |
|---|---|---|---|---|---|---|
| R1a2b3c4d | repregunta | ¿Y … allá? | 2 | si | si | |
| R5e6f7a8b | muestra | ¿Cuál … ? | 1 | no | na | Cifra sin respaldo |

- No dejes vacías `correccion` ni `fiel`. En `repregunta`, `resuelve_referencia` es obligatoria
  (`si` o `no`); en `muestra` deja `na`.
- Valores: `0`, `1`, `2` · `si` o `no` (se acepta `sí`, `Si`, `NO`).
- No edites `item` ni las columnas de la respuesta.
- Guarda como CSV (en Excel en español, «CSV UTF-8»; también se acepta con `;`). No lo conviertas a
  `.xlsx`.

## 6. Después

```bash
uv run python -m proyecto_modelos_lenguaje.module2_grading merge \\
  --grades docs/calificacion_m2/plantilla_<a>.csv docs/calificacion_m2/plantilla_<b>.csv
```

Si hay desacuerdos, el comando escribe `docs/calificacion_m2/desacuerdos.csv`: decídanlos juntos,
llenen las columnas `*_consenso` y repitan con `--consensus docs/calificacion_m2/desacuerdos.csv`.
El resultado (repreguntas resueltas por la persona y acuerdo entre la persona y el juez) se escribe
en `docs/evaluacion_variantes.json` y en `docs/evaluacion_modulo2.md`.
"""
