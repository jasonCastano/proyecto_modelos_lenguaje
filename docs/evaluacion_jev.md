# Evaluación del gatekeeper System One (Jev)

Generado por `agent jev --compare` el 2026-11-21 (spec 022). Ejecución `jev-real-2026-11-21b`, commit `8f9d0b4`, modelo `jev-1.14.0`, umbral de ruta 0.75 y de crisis 0.5. Costo total de Jev: 0.0051 USD.

## Validación en español (SC-009)

24/24 rutas correctas (100,0 %) sobre `tests/fixtures/jev/validation_es.jsonl` (24 consultas nuevas, 4 por ruta). Latencia media 203.9 ms, p95 222.0 ms.

| Umbral | Cobertura | Exactitud cubierta |
|---:|---:|---:|
| 0.60 | 100,0 % | 100,0 % |
| 0.70 | 100,0 % | 100,0 % |
| 0.75 | 100,0 % | 100,0 % |
| 0.80 | 100,0 % | 100,0 % |
| 0.90 | 91,7 % | 100,0 % |

## Enrutador: reglas + LLM frente a reglas + Jev + LLM (SC-001, SC-002)

44 consultas etiquetadas del Módulo 2 con DeepSeek (`tests/fixtures/rag/module2_queries.jsonl`).

| Métrica | Sin Jev | Con Jev |
|---|---:|---:|
| Exactitud de ruta | 97,7 % (43/44) | 93,2 % (41/44) |
| Llamadas al LLM por consulta | 0.77 | 0.18 |
| Llamadas al LLM evitadas | — | 76,5 % |
| Decisiones de Jev | — | 26 (59,1 %) |
| Fallos de Jev | — | 0 |
| Latencia media de enrutamiento | 1321 ms | 500 ms |
| p95 de enrutamiento | 3072 ms | 2226 ms |
| Latencia media de Jev | — | 201 ms |
| Saludos y fuera de alcance sin búsqueda | 10/10 | 10/10 |

## Atención (SC-004)

Batería de 36 casos de la spec 019, variante `chain`.

| Métrica | Sin Jev | Con Jev |
|---|---:|---:|
| Casos que cumplen | 32/36 | 31/36 |
| Crisis atendidas (Línea 106 y 123) | 100,0 % | 100,0 % |
| Límite cordial ante insultos | 100,0 % | 100,0 % |
| Turnos decididos por Jev | — | 9 |
| Consultas a Jev / fallos | — | 36 / 0 |
| Primera palabra (media) | 3028 ms | 2971 ms |
| Casos que no cumplen (decidió) | a06 (rules), l03 (llm), m01 (llm), m02 (llm) | e05 (rules), l04 (jev), m01 (jev), m02 (jev), m03 (jev) |

## Extremo a extremo: cadena y agente (SC-003)

44 consultas por variante con DeepSeek, el mismo día y con el mismo código: `variants-real-sinjev-2026-11-21` (sin Jev) y `variants-real-jev-2026-11-21` (con Jev). Una ejecución por configuración; la latencia varía entre ejecuciones.

| Variante | Métrica | Sin Jev | Con Jev |
|---|---|---:|---:|
| Cadena | Respuestas < 10 s | 100,0 % | 97,7 % |
| Cadena | Latencia media / p95 | 3.96 s / 7.8 s | 3.50 s / 10.1 s |
| Cadena | Llamadas al LLM / tokens | 1.75 / 5010 | 1.20 / 3880 |
| Agente | Respuestas < 10 s | 90,9 % | 97,7 % |
| Agente | Latencia media / p95 | 5.70 s / 15.6 s | 4.67 s / 10.6 s |
| Agente | Llamadas al LLM / tokens | 2.73 / 11394 | 2.05 / 9681 |

Ejecuciones anteriores del enrutador con Jev (mismo código y umbral):

- `jev-real-2026-11-21`: exactitud 93,2 %, Jev decide 56,8 %, llamadas al LLM evitadas 73,5 %.

Errores de ruta con Jev:

| Consulta | Esperada | Predicha | Confianza | Decidió |
|---|---|---|---:|---|
| r10 | documental | structured | 0.77 | jev |
| r32 | documental | structured | 0.98 | jev |
| r36 | documental | structured | 0.80 | jev |
