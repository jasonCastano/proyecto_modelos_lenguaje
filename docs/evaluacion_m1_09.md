# Evaluación del Módulo 1 — 40 preguntas

**Ejecución**: `m1-09-qa-v1.1` · **Fecha (UTC)**: 2026-11-10T22:36:48+00:00 · **Modelo**: `deepseek-flash` · **Modo**: real

**Comando**: `uv run python -m proyecto_modelos_lenguaje.module1_eval --ids P01 P06 P08 P09 P12 P13 P14 P15 P16 P17 P20 P21 P29 P31 P32 P35 P37 P38 --run-id m1-09-qa-v1.1 --out docs/evaluacion_m1_09.md --json-out docs/evaluacion_m1_09.json`

Las métricas automáticas salen de la ejecución registrada en `docs/evaluacion_m1_09.json`. Las columnas **Corrección** (0 incorrecta · 1 parcial · 2 correcta), **Coherencia** (1–5) y **Alucinación** (sí/no) las califica el equipo a mano; mientras estén vacías, el informe no puede citar esas cifras.

## Métricas automáticas por variante

| Variante | Preguntas | ok | review | fallback | error | Con cita | Acierto de fallback | Latencia media (s) | Desv. (s) | Tokens entrada | Tokens salida |
|---|---|---|---|---|---|---|---|---|---|---|---|
| zero_shot | 18 | 18 | 0 | 0 | 0 | 18 | 0.941 | 3.033 | 1.37 | 15635 | 6849 |
| final | 18 | 12 | 0 | 6 | 0 | 12 | 0.588 | 2.648 | 0.983 | 23815 | 5908 |

*Acierto de fallback*: proporción de respuestas cuyo *fallback* coincide con lo esperado en el alcance (`X` debe declarar falta de evidencia; el resto debe responder).

## Resultados por pregunta

| ID | Variante | Esperado | Estado | Citas | Respuesta | Corrección | Coherencia | Alucinación |
|---|---|---|---|---|---|---|---|---|
| P01 | zero_shot | D | ok | U3 U2 U1 | No hay en el contexto una declaración formal y completa de la misión y la visión de Manuelita. Lo que sí aparece es: - **Visión estratégica:** Manuelita “tiene… |  |  |  |
| P01 | final | D | ok | U3 U1 U2 | El corpus no contiene el enunciado formal de la misión ni de la visión de Manuelita. Solo aparecen contenidos cercanos, que no equivalen a esas declaraciones: … |  |  |  |
| P06 | zero_shot | D | ok | U2 U3 U5 U6 | El contexto no indica dónde tiene sedes, plantas y cultivos ni proporciona datos de contacto. Solo menciona certificaciones y tipos de cultivos, sin especifica… |  |  |  |
| P06 | final | D | ok | U5 U7 U2 U3 U6 | El corpus no contiene un listado de sedes ni de direcciones. Lo que sí puede afirmarse es lo siguiente: - Se mencionan cultivos de uva de mesa y de espárragos … |  |  |  |
| P08 | zero_shot | P | ok | U1 U2 U3 U8 U4 U5 U6 U7 | No encuentro en el contexto proporcionado información sobre fichas técnicas o especificaciones de productos. Las unidades disponibles tratan otros temas: perfi… |  |  |  |
| P08 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P09 | zero_shot | P | ok | U1 U2 U3 U5 U4 U6 U7 U8 | No, según el contexto disponible no hay evidencia de que Manuelita maneje precios, tarifas o planes públicos dirigidos a sus grupos de interés, ni de que publi… |  |  |  |
| P09 | final | P | ok | U1 | El corpus no permite afirmar que Manuelita maneje precios, tarifas o planes públicos. Solo menciona que los precios actuales están por debajo de los costos de … |  |  |  |
| P12 | zero_shot | P | ok | U7 U2 U1 | Las noticias y artículos más relevantes que se pueden identificar en el contexto son: - El incremento del 12% en el precio internacional del azúcar en el compa… |  |  |  |
| P12 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P13 | zero_shot | D | ok | U1 | El contexto disponible solo indica el canal de YouTube de Manuelita Agroindustria ([U1]), pero no incluye información sobre qué videos o transcripciones especí… |  |  |  |
| P13 | final | D | ok | U1 | El corpus solo aporta la dirección del canal de YouTube de Manuelita Agroindustria [U1]. No hay unidades que enumeren los videos ni las transcripciones publica… |  |  |  |
| P14 | zero_shot | X | ok | U8 U4 U5 | No se especifica qué entrevistas del gerente están disponibles. El contexto solo menciona un mensaje de Diego Salazar, gerente corporativo y de sostenibilidad … |  |  |  |
| P14 | final | X | ok | U8 U4 U3 | El corpus no contiene un listado de entrevistas disponibles del gerente. Lo único que aparece es la intervención de Diego Salazar, identificado como gerente co… |  |  |  |
| P15 | zero_shot | P,X | ok | U1 U3 U8 | Según el contexto, Manuelita publica en redes sociales información **de carácter institucional** cuando es titular de la cuenta **[U1]**. También contempla el … |  |  |  |
| P15 | final | P,X | ok | U1 U3 U8 U5 U7 U6 | Según el corpus, la información que se divulga en las redes sociales donde la Fundación Manuelita es titular de una cuenta es pública y de carácter exclusivame… |  |  |  |
| P16 | zero_shot | P | ok | U1 U3 U4 | El contexto disponible no contiene un listado de vacantes concretas ni un canal específico donde se publiquen. Lo que sí aparece es: - Existe una unidad titula… |  |  |  |
| P16 | final | P | ok | U3 U4 | El corpus no contiene un listado de vacantes concretas ni los lugares donde se publican. Solo hay referencias generales: - La contratación depende de las neces… |  |  |  |
| P17 | zero_shot | D | ok | U1 | No encuentro en el contexto proporcionado información sobre la ubicación o el lugar donde se encuentran los informes financieros y la memoria anual. Lo único r… |  |  |  |
| P17 | final | D | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P20 | zero_shot | P | ok | U2 U3 | No hay información en el contexto sobre precios públicos, datos abiertos ni rankings sectoriales. El contexto solo menciona una definición de datos públicos [U… |  |  |  |
| P20 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P21 | zero_shot | C | ok | U4 U2 | Según la información disponible en el contexto, no es posible detallar los tipos de azúcar que ofrece Manuelita ni sus principales diferencias, ya que las unid… |  |  |  |
| P21 | final | C | ok | U4 U2 | El contexto indica que Manuelita ofrece un portafolio de azúcar y derivados de valor agregado a las industrias de los sectores alimenticio y bebidas, químico y… |  |  |  |
| P29 | zero_shot | C | ok | U1 U4 U5 | La información disponible en el contexto no permite responder esa pregunta: no se mencionan certificaciones publicadas por Manuelita para la producción de azúc… |  |  |  |
| P29 | final | C | ok | U1 U4 | El corpus no menciona certificaciones otorgadas a Manuelita para la producción de azúcar en Palmira. Solo se registra una referencia a un «Alcance para planta … |  |  |  |
| P31 | zero_shot | M | ok | U2 U4 U6 | El contexto no identifica fuentes oficiales concretas (informes, entidades o documentos externos) que respalden la afirmación. Solo se apoya en afirmaciones co… |  |  |  |
| P31 | final | M | ok | U2 U4 U6 U8 | El corpus confirma la afirmación, aunque no identifica las fuentes documentales que la respaldan: - Manuelita Aceites y Energía aumentó durante 2014 la generac… |  |  |  |
| P32 | zero_shot | P | ok | U3 | Puedes consultar el **procedimiento para el uso de los canales de comunicación** y radicar la solicitud **a través de la página web**, diligenciando los campos… |  |  |  |
| P32 | final | P | ok | U3 | El corpus indica que existe un procedimiento para el uso de los canales de comunicación, mediante una solicitud a través de la página web, en la que se deben d… |  |  |  |
| P35 | zero_shot | P | ok | U4 | No hay información en el contexto sobre dónde publica Manuelita sus oportunidades laborales ni sobre las orientaciones para postularse; la única referencia a o… |  |  |  |
| P35 | final | P | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |
| P37 | zero_shot | D | ok | U2 U3 U4 U5 U7 U8 U6 | Con el contexto disponible no se puede reconstruir una cronología completa de Manuelita desde su origen en Palmira; sin embargo, se documentan estos elementos … |  |  |  |
| P37 | final | D | ok | U2 U3 U4 U5 U7 U8 | El corpus permite afirmar algunos rasgos de identidad y de continuidad, pero no ofrece un relato cronológico de la evolución de Manuelita ni una secuencia de h… |  |  |  |
| P38 | zero_shot | C | ok | U3 U1 U2 U4 U5 U6 U7 U8 | No puedo hacer esa comparación con la información disponible. El contexto proporcionado no contiene un catálogo de tipos de azúcar ni un listado de certificaci… |  |  |  |
| P38 | final | C | fallback | — | No hay evidencia suficiente en el corpus para responder. |  |  |  |

## Análisis de errores

Pendiente de la calificación humana (M1-09): clasificar los fallos en recuperación, redacción, cita inválida, alucinación o falta de corpus, y registrar los ajustes en `docs/prompt_log.md`.
