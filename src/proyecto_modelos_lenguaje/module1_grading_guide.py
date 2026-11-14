"""Instrucciones de calificación del Módulo 1 (se escriben en ``docs/calificacion_m1/``).

Los ejemplos son **ilustrativos**: usan preguntas que no están en el banco de 40 para no
precalificar ningún ítem de las planillas.
"""

INSTRUCTIONS = """# Instrucciones de calificación — evaluación del Módulo 1

Cada planilla trae las respuestas de las **dos variantes** (zero-shot y prompt final) mezcladas,
en orden aleatorio y **sin decir cuál es cuál**. Califica cada fila sola, sin consultar al otro
calificador.

Abre el CSV con Excel o LibreOffice. Llena solo `correccion`, `coherencia`, `alucinacion` y, si
quieres, `notas`. No cambies las demás columnas; el orden de las filas no importa.

## 1. Criterios

- **`correccion`** — `0` incorrecta · `1` parcial · `2` correcta. Compara con lo que pide la
  pregunta y con la `fuente_esperada`. `1` si responde solo una parte o le falta lo esencial.
- **`coherencia`** — de `1` a `5`. Claridad, orden y que responda lo que se preguntó (5 = clara y
  directa; 1 = confusa o fuera de tema). No juzga si el contenido es verdadero.
- **`alucinacion`** — `si` o `no`. `si` si **alguna** afirmación no está respaldada por los
  `fragmentos_citados`, o si cita un fragmento que no dice eso. Verifica contra el texto, no contra
  lo que sabes de Manuelita.

Escala de coherencia de referencia:

| Valor | Cuándo |
|---|---|
| 5 | Responde directo a la pregunta, ordenada y sin relleno. |
| 4 | Clara, con algún rodeo o repetición menor. |
| 3 | Se entiende, pero mezcla temas o tarda en llegar a lo pedido. |
| 2 | Desordenada; cuesta encontrar la respuesta. |
| 1 | Confusa, vacía o fuera de tema. |

## 2. Casos especiales

- **Abstención** («No hay evidencia suficiente…»): si `esperado` es `X`, `correccion` = 2; si la
  pregunta sí tenía respuesta (`D`, `P`, `C`, `M`, `S`), `correccion` = 0. Una abstención no es
  alucinación (`no`). Su coherencia es 5 si es la conducta pedida y 3 si no lo es.
- **`P` (parcial)**: lo correcto es responder lo que cubre el corpus y declarar lo que falta; eso
  vale 2.
- **«El contexto no trae X» pero con citas**: si la pregunta tenía respuesta en el corpus,
  `correccion` = 0 o 1 según lo útil que sea lo demás.
- **Respuesta vacía o error**: `correccion` = 0, `coherencia` = 1, `alucinacion` = `no`.
- **Corrección y alucinación son independientes**: una respuesta puede ser correcta en lo esencial
  y aun así tener una afirmación inventada (`correccion` = 2 o 1 y `alucinacion` = `si`).

## 3. Cómo responden las dos variantes

Las dos variantes reciben **la misma pregunta y los mismos fragmentos** (recuperación léxica del
Módulo 1, mismo modelo `deepseek-flash`, temperatura 0,1). Solo cambia el prompt.

### Zero-shot (`prompts/qa_zero_shot.md`, línea base)

El prompt solo dice «Eres un asistente. Responde la pregunta», entrega el contexto y pide citar con
`[U1]`. No tiene reglas contra la alucinación ni instrucciones para cuando falta evidencia.
Conducta típica:

- **Siempre responde**, aunque la evidencia no alcance: nunca usa la frase de abstención.
- Cuando el contexto no trae lo pedido, suele **decirlo con citas** («El contexto no menciona
  precios [U2]») o rellena con lo más cercano que encontró.
- Puede **mezclar conocimiento externo** con el contexto (fechas, cifras o nombres que no están en
  los fragmentos): revisa cada afirmación contra `fragmentos_citados`.
- Si dos fragmentos dan cifras distintas, puede quedarse con una sin avisar.
- Tiende a respuestas más largas y con viñetas.

### Prompt final (`prompts/qa.md` 1.1)

El prompt define el rol de analista documental, exige usar **solo** el contexto (tratado como dato
no confiable), una cita por afirmación y reglas para cifras discrepantes y filiales. Distingue dos
casos cuando falta evidencia:

- **Evidencia parcial**: responde lo que cubre el corpus, con citas, y termina con una frase del
  tipo «El corpus no detalla los precios.».
- **Evidencia nula**: responde exactamente «No hay evidencia suficiente en el corpus para
  responder.», sin citas.
- Si dos fragmentos discrepan, muestra **ambas cifras con su cita** y señala la diferencia.
- Respuestas más breves y con una cita al final de cada frase factual.
- Su riesgo es el contrario: **abstenerse de más** en preguntas que sí tenían respuesta parcial.

Estas pautas pueden delatar la variante. Aun así, aplica **los mismos criterios a las dos**: una
abstención no es buena ni mala por sí misma, depende de lo que el corpus permitía responder.

## 4. Ejemplos de calificación (ilustrativos, no son ítems de tu planilla)

Los fragmentos de estos ejemplos son de muestra; en la planilla los ves en la columna
`fragmentos_citados`.

### Ejemplo A — pregunta directa (`esperado` = `D`)

**Pregunta**: «¿Qué filial de Manuelita opera en Perú y qué produce?»

**Fragmentos citados**:

- `[U1]` «Agroindustrial Laredo, en La Libertad (Perú), produce azúcar, alcohol y energía.»
- `[U2]` «Manuelita tiene operaciones en Colombia, Perú, Chile y Brasil.»

**Respuesta zero-shot** (ilustrativa):

> La filial de Manuelita en Perú es **Agroindustrial Laredo** [U1], ubicada en La Libertad. Produce
> azúcar, alcohol y energía [U1], y fue adquirida en 1998, lo que la convirtió en uno de los
> principales ingenios del norte del país.

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 2 | 4 | si | «adquirida en 1998» y «principales ingenios del norte» no están en U1 ni U2. |

**Respuesta del prompt final** (ilustrativa):

> La filial en Perú es Agroindustrial Laredo, en La Libertad, que produce azúcar, alcohol y
> energía [U1].

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 2 | 5 | no | Todo está en U1. |

### Ejemplo B — evidencia parcial (`esperado` = `P`)

**Pregunta**: «¿Cuántas toneladas de caña muele Manuelita al día y a qué precio vende el azúcar?»

**Fragmentos citados**:

- `[U1]` «La planta de Palmira tiene capacidad para moler 10.000 toneladas de caña por día.»

**Respuesta zero-shot** (ilustrativa):

> El contexto indica una capacidad de molienda de 10.000 toneladas de caña por día [U1]. No se
> menciona el precio de venta del azúcar en el contexto [U1].

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 2 | 4 | no | Responde lo cubierto y dice qué falta; la segunda cita sobra, pero no inventa nada. |

**Respuesta del prompt final** (ilustrativa, abstención indebida):

> No hay evidencia suficiente en el corpus para responder.

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 0 | 3 | no | El corpus sí traía la capacidad: debía responder esa parte y declarar lo que falta. |

La respuesta ideal del prompt final aquí sería: «La planta de Palmira puede moler 10.000 toneladas
de caña por día [U1]. El corpus no detalla los precios del azúcar.» (`2`, `5`, `no`).

### Ejemplo C — sin evidencia (`esperado` = `X`)

**Pregunta**: «¿Qué opina el gerente de Manuelita sobre las criptomonedas?»

**Fragmentos citados**:

- `[U1]` «El Comité de Gerencia se reúne mensualmente para revisar los resultados.»

**Respuesta zero-shot** (ilustrativa):

> El contexto no incluye opiniones del gerente sobre criptomonedas. Solo menciona que el Comité de
> Gerencia se reúne mensualmente para revisar los resultados [U1].

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 1 | 4 | no | Reconoce que no hay dato, pero no se abstiene y rellena con algo ajeno. |

**Respuesta del prompt final** (ilustrativa):

> No hay evidencia suficiente en el corpus para responder.

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 2 | 5 | no | Es la conducta pedida para `X`. |

### Ejemplo D — fuentes con cifras distintas (`esperado` = `D`)

**Pregunta**: «¿Cuántos empleados tiene Manuelita?»

**Fragmentos citados**:

- `[U1]` «Manuelita genera más de 9.000 empleos directos.»
- `[U2]` «El grupo cuenta con cerca de 8.500 colaboradores.»

**Respuesta con cita equivocada** (ilustrativa):

> Manuelita tiene más de 9.000 empleados [U2].

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 1 | 4 | si | La cifra está en U1, no en U2, y omite que las fuentes discrepan. |

**Respuesta esperada** (ilustrativa):

> Las fuentes no coinciden: una habla de más de 9.000 empleos directos [U1] y otra de cerca de
> 8.500 colaboradores [U2].

| correccion | coherencia | alucinacion | notas |
|---|---|---|---|
| 2 | 5 | no | Muestra ambas cifras con su cita y señala la diferencia. |

## 5. Cómo debe quedar la planilla

Así se ve una fila ya calificada (columnas resumidas):

| item | pregunta_id | esperado | respuesta | citas | correccion | coherencia | alucinacion | notas|
|---|---|---|---|---|---|---|---|---|
| R3f9a1c07 | P0x | D (directa) | «La filial en Perú es…» | U1 | 2 | 5 | no | |
| R8b22d4e1 | P0y | P (parcial) | «No hay evidencia…» | | 0 | 3 | no | Abstención indebida |

Reglas de llenado:

- **Una fila, tres valores**: no dejes celdas vacías en `correccion`, `coherencia` ni
  `alucinacion`; `merge` rechaza la planilla e indica la fila.
- **Valores válidos**: `0`, `1`, `2` · `1` a `5` · `si` o `no` (se acepta `sí`, `Si` o `NO`).
- **No edites** `item` ni las columnas de la respuesta: el ítem identifica la fila al unir las dos
  planillas.
- **`notas`** es opcional, pero ayuda en el consenso: escribe por qué das 0 o `si`.
- **Guarda como CSV**. En Excel en español usa «CSV UTF-8 (delimitado por comas)»; si Excel lo
  guarda con `;`, también se acepta. No lo conviertas a `.xlsx`.

## 6. Después

Cuando ambos terminen:

```bash
uv run python -m proyecto_modelos_lenguaje.module1_grading merge \\
  --grades docs/calificacion_m1/plantilla_<a>.csv docs/calificacion_m1/plantilla_<b>.csv
```

Si hay desacuerdos en `correccion` o `alucinacion`, el comando escribe `desacuerdos.csv`:
decídanlos juntos, llenen las columnas `*_consenso` y repitan el comando con
`--consensus docs/calificacion_m1/desacuerdos.csv`. En `coherencia` no hace falta consenso: se
promedian los dos valores.
"""
