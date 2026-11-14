# Instrucciones de calificación — evaluación del Módulo 1

Cada planilla trae las respuestas de las **dos variantes** (zero-shot y prompt final) mezcladas,
en orden aleatorio y **sin decir cuál es cuál**. Califica cada fila sola, sin consultar al otro
calificador.

Abre el CSV con Excel o LibreOffice (UTF-8). Llena solo `correccion`, `coherencia`, `alucinacion`
y, si quieres, `notas`. No cambies las demás columnas; el orden de las filas no importa.

## Criterios

- **`correccion`** — `0` incorrecta · `1` parcial · `2` correcta. Compara con lo que pide la
  pregunta y con la `fuente_esperada`. `1` si responde solo una parte o le falta lo esencial.
- **`coherencia`** — de `1` a `5`. Claridad, orden y que responda lo que se preguntó (5 = clara y
  directa; 1 = confusa o fuera de tema). No juzga si el contenido es verdadero.
- **`alucinacion`** — `si` o `no`. `si` si **alguna** afirmación no está respaldada por los
  `fragmentos_citados`, o si cita un fragmento que no dice eso. Verifica contra el texto, no contra
  lo que sabes de Manuelita.

## Casos especiales

- **Abstención** («No hay evidencia suficiente…»): si `esperado` es `X`, `correccion` = 2; si la
  pregunta sí tenía respuesta (`D`, `P`, `C`, `M`, `S`), `correccion` = 0. Una abstención no es
  alucinación (`no`).
- **`P` (parcial)**: lo correcto es responder lo que cubre el corpus y declarar lo que falta; eso
  vale 2.
- **«El contexto no trae X» pero con citas**: si la pregunta tenía respuesta en el corpus,
  `correccion` = 0 o 1 según lo útil que sea lo demás.
- **Respuesta vacía o error**: `correccion` = 0, `coherencia` = 1, `alucinacion` = `no`.

## Después

Cuando ambos terminen:

```bash
uv run python -m proyecto_modelos_lenguaje.module1_grading merge \
  --grades docs/calificacion_m1/plantilla_<a>.csv docs/calificacion_m1/plantilla_<b>.csv
```

Si hay desacuerdos en `correccion` o `alucinacion`, el comando escribe `desacuerdos.csv`:
decídanlos juntos, llenen las columnas `*_consenso` y repitan el comando con
`--consensus docs/calificacion_m1/desacuerdos.csv`.
