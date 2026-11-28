# Evaluación: activación del planificador por contexto (spec 028)

**Fecha**: 2026-11-26 · **Comando**: `uv run python -m proyecto_modelos_lenguaje.agent evaluate --planning-activation --markdown` · **Conjunto**: `tests/fixtures/agent/planning_activation.jsonl` (fijado antes de medir) · **Meta (SC-007)**: ≥ 14/15 en cada lado.

## Resultado: ✅ cumple

| Medida | Valor |
|---|---|
| Consultas de planificación que activan el planificador | 15/15 |
| Consultas parecidas que **no** lo activan | 15/15 |
| Repreguntas que siguen en planificación (turno anterior `planning`) | 3/3 |
| Falsos positivos | ninguno |
| Falsos negativos | ninguno |

## Lectura

La activación es de **reglas** (`router.planning_decision`): sin modelo, determinista y sin costo. Se activa para cualquier persona, en la web y en WhatsApp, **solo en ese turno** (y en la repregunta inmediata de un escenario), sin cambiar el perfil de la conversación. Las preguntas informativas que comparten palabras con la planificación («programas con cultivadores de caña», «¿cuánta caña molió en 2022?») no la activan: así un falso positivo no deja a un visitante «atrapado» en la planificación. Las repreguntas («¿y si baja 20 %?») solo cuentan cuando el turno anterior fue de planificación.

## Casos

| id | Consulta | Esperado | Activó | |
|---|---|---|---|---|
| p01 | Tenemos 15 % menos caña esta semana, ¿cómo cumplimos los compromisos de azúcar, etanol y energía? | sí | sí | ✅ |
| p02 | Optimiza el programa de producción de esta semana | sí | sí | ✅ |
| p03 | ¿Cómo repartimos la caña entre azúcar y etanol esta semana? | sí | sí | ✅ |
| p04 | Simula producir más etanol y menos azúcar | sí | sí | ✅ |
| p05 | ¿Cuál es el estado de la planta hoy? | sí | sí | ✅ |
| p06 | Tenemos una restricción de vapor, ¿qué plan recomiendas? | sí | sí | ✅ |
| p07 | ¿Podemos cumplir los contratos de etanol si baja la caña? | sí | sí | ✅ |
| p08 | ¿Qué compromisos de azúcar tenemos esta semana? | sí | sí | ✅ |
| p09 | Propón una mezcla de producción que maximice el margen | sí | sí | ✅ |
| p10 | Si la molienda cae un 10 %, ¿qué hacemos con la energía comprometida? | sí | sí | ✅ |
| p11 | ¿Qué dice el procedimiento sobre prioridad de compromisos en la planta? | sí | sí | ✅ |
| p12 | Planifica la producción de la semana con pol de 13 | sí | sí | ✅ |
| p13 | ¿Qué capacidad tienen los equipos de la planta? | sí | sí | ✅ |
| p14 | We have 20% less cane this week, how do we meet the sugar and ethanol commitments? | sí | sí | ✅ |
| p15 | Ajusta el plan de producción para cumplir la energía comprometida | sí | sí | ✅ |
| q01 | ¿Qué programas sociales tiene Manuelita con los cultivadores de caña? | no | no | ✅ |
| q02 | ¿Cuánta caña molió Manuelita en 2022? | no | no | ✅ |
| q03 | ¿Qué produce Manuelita con la caña de azúcar? | no | no | ✅ |
| q04 | ¿Cuántas toneladas de azúcar produjo Manuelita en 2021? | no | no | ✅ |
| q05 | ¿Manuelita produce etanol? | no | no | ✅ |
| q06 | ¿Qué hace Manuelita con la energía que genera? | no | no | ✅ |
| q07 | ¿Cuál fue la variación de las ventas entre 2021 y 2022? | no | no | ✅ |
| q08 | ¿Dónde está la planta de Manuelita en Palmira? | no | no | ✅ |
| q09 | ¿Qué certificaciones de calidad tiene la planta de azúcar? | no | no | ✅ |
| q10 | ¿Cuál es el plan de sostenibilidad de Manuelita? | no | no | ✅ |
| q11 | Cuéntame la historia del ingenio Manuelita | no | no | ✅ |
| q12 | ¿Qué programa de educación apoya la Fundación Manuelita? | no | no | ✅ |
| q13 | ¿Cómo puedo trabajar en la planta de Manuelita? | no | no | ✅ |
| q14 | How much ethanol did Manuelita produce in 2022? | no | no | ✅ |
| q15 | ¿Qué compromisos ambientales tiene Manuelita con el agua? | no | no | ✅ |
| f01 | ¿Y si baja 20 %? | sí | sí | ✅ |
| f02 | ¿y con una pol de 12? | sí | sí | ✅ |
| f03 | what if we produce only sugar? | sí | sí | ✅ |
