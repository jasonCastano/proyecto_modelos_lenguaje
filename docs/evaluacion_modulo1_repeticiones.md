# Evaluación del Módulo 1 — repeticiones

**Ejecuciones**: `m1-final-2026-11-14-r1`, `m1-final-2026-11-14-r2`, `m1-final-2026-11-14-r3` · **Modelo**: deepseek-flash

**Comando**: `uv run python -m proyecto_modelos_lenguaje.module1_grading aggregate --runs docs/evaluacion_modulo1.json docs/evaluacion_m1_r2.json docs/evaluacion_m1_r3.json`

El modelo no es determinista (temperatura 0,1), así que las métricas automáticas se reportan como media ± desviación estándar de las ejecuciones repetidas sobre las mismas 40 preguntas, el mismo corpus y los mismos prompts.

| Métrica | zero_shot | final |
|---|---|---|
| Respuestas ok | 40.0 ± 0.0 | 35.667 ± 1.155 |
| Abstenciones | 0.0 ± 0.0 | 4.333 ± 1.155 |
| Con cita | 40.0 ± 0.0 | 35.667 ± 1.155 |
| Acierto de fallback | 0.974 ± 0.0 | 0.88 ± 0.029 |
| Latencia media (s) | 3.647 ± 0.091 | 3.65 ± 0.142 |
| Tokens de entrada | 34700.333 ± 26.558 | 52965.0 ± 0.0 |
| Tokens de salida | 21396.333 ± 884.707 | 21831.333 ± 1093.823 |

**Estabilidad de la abstención** (preguntas que cambian entre ejecuciones):

- `zero_shot`: 0 (ninguna).
- `final`: 7 (P08, P09, P12, P14, P17, P20, P38).
