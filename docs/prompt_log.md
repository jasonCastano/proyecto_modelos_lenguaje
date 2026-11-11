# Prompt log del Módulo 1

Registro de las versiones de prompt, sus parámetros y las salidas observadas en M1-05. Todas las cifras
provienen de ejecuciones reales; no se estiman a mano.

## 1. Prompts versionados

| Tarea | Archivo | Versión | SHA-256 (12 primeros) | Secciones |
|-------|---------|---------|-----------------------|-----------|
| Q&A | `prompts/qa.md` | 1.0 | `d09765504709` | rol, tarea, contexto, reglas, formato de cita, sin evidencia |
| Resumen | `prompts/summary.md` | 1.0 | `f6cd198ba529` | idem |
| FAQ | `prompts/faq.md` | 1.0 | `9bafea161abb` | idem |
| Q&A línea base (evaluación) | `prompts/qa_zero_shot.md` | 0.1-zero-shot | `474d712010c9` | idem, mínimas; sin reglas anti-alucinación |

El hash completo se registra en cada resultado (`prompt_sha256`) y se puede reproducir con
`uv run python -c "from proyecto_modelos_lenguaje.tasks import load_prompt; print(load_prompt('qa').sha256)"`.

## 2. Parámetros

| Parámetro | Valor | Origen |
|-----------|-------|--------|
| `qa.top_k` | 8 | `config/tasks.toml` |
| `qa.token_budget` | 6.000 | `config/tasks.toml` |
| `qa.min_score` | 0.0 | `config/tasks.toml` |
| `summary.pack` | `8000` | `config/tasks.toml` |
| `summary.min_citations` | 8 (máximo efectivo 12) | `config/tasks.toml` |
| `faq.limit` | 12 | `config/tasks.toml` |
| `faq.top_k` | 5 | `config/tasks.toml` |
| `faq.min_citations` | 1 | `config/tasks.toml` |
| `faq.question_max_chars` | 500 | `config/tasks.toml` |
| `llm.provider` / `llm.model` | `deepseek` / `deepseek-flash` (antes `llama3.1:8b`, hasta 2026-10-31) | `config/llm.toml` |
| `llm.top_p` | 0.9 | `config/llm.toml` |
| `llm.temperature` | 0.1 | `config/llm.toml` |
| `llm.max_output_tokens` | 1.024 | `config/llm.toml` |

## 3. Ejecuciones observadas

### 3.1 Modelo falso (offline, 2026-10-30)

| Tarea | Estado | Citas | Unidades usadas | Entrada (tok) | Salida (tok) | Modelo |
|-------|--------|-------|-----------------|---------------|--------------|--------|
| Q&A | ok | 2 | 8 | 894 | 24 | `scripted-fake` |
| Resumen 8k | ok | 10 | 12 | 872 | 163 | `scripted-fake` |
| FAQ (12) | 12 × ready | 12 × ≥1 | — | — | — | `scripted-fake` |

Comandos:

```bash
uv run python -m proyecto_modelos_lenguaje.tasks qa --question "¿Qué productos ofrece Manuelita?" --fake --json
uv run python -m proyecto_modelos_lenguaje.tasks summary --fake --json
uv run python -m proyecto_modelos_lenguaje.tasks faq --limit 12 --fake --json
```

### 3.2 Modelo configurado `llama3.1:8b` sobre el corpus real (2026-10-30)

Instalado con `ollama pull llama3.1:8b` (4,9 GB) y verificado con
`uv run python -m proyecto_modelos_lenguaje.tasks` (`--check` → `ok`). Corpus real: 15.211 unidades.

| Tarea | Estado | Citas | Latencia | Entrada (tok) | Salida (tok) | Respuesta observada |
|-------|--------|-------|----------|---------------|--------------|---------------------|
| Q&A «¿Qué productos ofrece Manuelita?» | ok | 3 | 26,84 s | 1.177 | 192 | Respuesta en español con tres fuentes citadas. |
| Q&A «¿Dónde está la casa matriz?» | ok | 1 | 4,46 s | — | — | Declara que el contexto no especifica la ubicación y cita la unidad disponible; no inventa. |
| Resumen 8k | ok | 8 | 27,45 s | 9.050 | 701 | Cinco bloques con citas y paquete declarado; 84 unidades en el paquete. |
| FAQ (10) | 7 × ready, 3 × review | 1–2 por ítem | — | — | — | 70% con citas; los 3 `review` no citaron y quedan para M1-09. |

Código de salida `0` en los cuatro comandos. El resumen usa 9.050 tokens de entrada (plantilla +
paquete de 8.000) sobre una ventana de 16.384: no hay desbordamiento.

Hallazgo: la primera ejecución del resumen falló al imprimir por consola de Windows (`cp1252`) porque la
respuesta del modelo contenía un acento combinado (`U+0301`). El CLI ahora reconfigura `stdout`/`stderr`
a UTF-8 con reemplazo, de modo que un carácter no representable nunca rompe la salida.

### 3.3 Modelo de respaldo `qwen3.5:4b` (2026-10-30)

Se ejecutó con el razonamiento desactivado para que el presupuesto de salida no se consumiera en el
bloque de pensamiento.

| Tarea | Estado | Citas | Latencia | Respuesta observada (extracto) |
|-------|--------|-------|----------|-------------------------------|
| Q&A «¿Qué productos ofrece Manuelita?» | ok | 2 (`U5`, `U1`) | 2,91 s | «Manuelita produce azúcar, etanol y biocombustibles [U5]. Además, su línea de alimentos incluye azúcar refinada y productos derivados de la caña [U1].» |
| Resumen 8k | ok | 12 | 4,01 s | Encabezados por bloque (identidad, operación, casa matriz) con citas `[U#]` y paquete declarado. |

Hallazgo registrado: con un modelo de razonamiento y `max_output_tokens=1024` el modelo devolvió
contenido vacío con `done_reason=length`; el sistema lo reporta como `model_error` con instrucción
accionable (aumentar `llm.max_output_tokens` o usar un modelo sin razonamiento).

### 3.3 Modelo DeepSeek por API (2026-10-31)

El proveedor pasa de Ollama local a **DeepSeek V4.1 Flash 1017** por API (spec 010). Configuración
versionada en `config/llm.toml`: `model = "deepseek-flash"`, `base_url = "https://api.deepseek.com/v1"`,
`timeout_seconds = 60`, `max_retries = 1`.

| Tarea | Estado | Citas | Latencia | Entrada / salida | Respuesta observada |
|-------|--------|-------|----------|------------------|---------------------|
| Q&A (simulada) | ok | ≥1 | 0,0 s (doble HTTP) | 120 / 30 tokens reportados | Cita `[U1]` mapeada a la unidad y a su URL |
| Resumen (simulada) | ok | 8–12 | 0,0 s (doble HTTP) | reportados | Paquete declarado y citas |
| Errores (simulados) | error controlado | — | — | — | 401, 404, 429, 500, timeout y respuesta vacía con mensaje propio |

**Estado de la línea base real: pendiente.** No hay clave del proveedor disponible en este equipo, así que
la validación con el servicio real (T045/T046) queda abierta. La suite cubre el comportamiento con un
transporte simulado: éxito, errores y tokens.

### 3.4 M1-08: 40 preguntas, zero-shot vs. final con DeepSeek (2026-11-10)

Ejecución `m1-eval-2026-11-10-deepseek`, modelo `deepseek-flash`, misma recuperación léxica para ambas variantes.
Registro: `docs/evaluacion_modulo1.{md,json}`.

| Variante | Prompt | ok | fallback | error | Con cita | Acierto de fallback | Latencia media | Entrada / salida (tok) |
|----------|--------|---:|---------:|------:|---------:|--------------------:|---------------:|-----------------------:|
| Zero-shot | `qa_zero_shot.md` 0.1-zero-shot | 40 | 0 | 0 | 40 | 0,974 | 3,77 s | 34.685 / 20.715 |
| Final | `qa.md` 1.0 | 23 | 17 | 0 | 23 | 0,590 | 3,65 s | 49.645 / 20.242 |

Hallazgos:

- La primera corrida marcó 17 respuestas del prompt final como `error=missing_citations`: el modelo respondía
  exactamente la frase de abstención y el código la trataba como falta de citas. Se corrigió en `tasks.py`
  (`is_model_fallback`) y se reejecutó; las cifras de arriba son de la segunda corrida.
- El zero-shot nunca se abstiene (tampoco en la pregunta `X`); el final se abstiene en 16 preguntas con
  respuesta esperada. Candidato de ajuste para M1-09: permitir una respuesta parcial con cita y reservar la
  abstención para la evidencia nula.
- Corrección, coherencia y alucinación: calificación humana pendiente.

### 3.5 M1-09: `qa.md` 1.1 — evidencia parcial vs. nula (2026-11-10)

Cambio único respecto a 1.0: la sección 6 distingue **evidencia parcial** (responder la parte cubierta con citas
y declarar lo que falta) de **evidencia nula** (frase de abstención exacta). Reevaluación
`m1-09-qa-v1.1` sobre las 16 preguntas que la 1.0 abstuvo indebidamente más P14 (`X`) y P15 (`P, X`) como
control. Registro: `docs/evaluacion_m1_09.{md,json}`.

| Métrica (18 preguntas) | `qa.md` 1.0 (M1-08) | `qa.md` 1.1 (M1-09) |
|------------------------|--------------------:|--------------------:|
| Respuestas `ok` con cita | 1 | 12 |
| Abstenciones | 17 | 6 |
| Abstenciones indebidas (de 16) | 16 | 6 |
| Abstención en P14 (`X`) | sí | **no** |
| Latencia media (s) | — | 2,65 |

Hallazgos:

- Se recuperan 10 respuestas (P01, P06, P09, P13, P16, P21, P29, P31, P32, P37). Siguen abstenidas P08, P12, P17,
  P20, P35 y P38: la recuperación léxica no trae unidades pertinentes (el zero-shot también declara que el
  contexto no tiene lo pedido).
- **Regresión en P14**: en lugar de abstenerse, responde que el corpus no tiene el listado y cita la única
  mención relacionada. No inventa, pero ya no cumple la conducta `X` esperada. Debe decidirlo la calificación
  humana.
- Varias respuestas parciales empiezan con «El corpus no contiene…» y luego citan algo cercano; la calificación
  humana dirá si son útiles o ruido.

### 3.6 Enrutador del agente: `router.md` 1.0 (2026-11-10, spec 014)

Prompt nuevo `prompts/router.md` (versión `1.0`, seis secciones). Clasifica en `direct`, `documental`,
`structured`, `out_of_scope` o `clarify` con confianza y motivo, en JSON; historial y mensaje van en
etiquetas XML como dato. Modelo `deepseek-flash`, temperatura 0. Solo se invoca cuando las reglas no
deciden (saludos y temas ajenos se resuelven sin modelo).

| Ejecución | Casos | Precisión | Sin búsqueda | Llamadas | Latencia media |
|-----------|------:|----------:|-------------:|---------:|---------------:|
| `router-real-2026-11-10` | 36 | 0,972 | 10/10 | 26 | 1,3 s |

Único error: r32 («¿Cuánto bioetanol produce allá al año?»), etiquetada `documental` y clasificada
`structured`. Detalle en `docs/evaluacion_modulo2.md` y `docs/evaluacion_enrutador.json`.

### 3.7 Agente conversacional: `agent.md` 1.0 y `memory_summary.md` 1.0 (2026-11-11, spec 014)

Prompts nuevos (seis secciones cada uno):

| Prompt | Archivo | Versión | SHA-256 (12 primeros) | Uso |
|--------|---------|---------|-----------------------|-----|
| Agente | `prompts/agent.md` | 1.0 | `a64cb34cd40f` | System prompt de ambas variantes (cadena y agente): solo `<documento>`, citas `[U#]`/`[F#]`, hasta tres búsquedas |
| Memoria | `prompts/memory_summary.md` | 1.0 | `e0f515ba64ec` | Resumen del hilo al superar `memory.summarize_after_tokens`; conserva entidades, cifras y URL de las fuentes |

Primera ejecución con `deepseek-flash` (CLI `agent chat --mode real`, 2026-11-11), conversación «¿Qué produce
Manuelita?» → «¿Y dónde lo produce?»:

| Variante | Turno | Ruta | Llamadas al modelo | Búsquedas | Tokens entrada/salida | Latencia |
|----------|------:|------|-------------------:|----------:|----------------------:|---------:|
| Cadena | 1 | documental | 2 | 1 | 3.191 / 482 | 20,5 s |
| Cadena | 2 | documental (0,85) | 2 | 1 | 3.308 / 614 | 19,8 s |
| Agente | 1 | documental | 3 | 1 | 5.930 / 348 | 14,8 s |
| Agente | 2 | documental (0,87) | 3 | 2 | 6.169 / 737 | 17,2 s |

Ambas variantes resuelven la repregunta elíptica con el hilo y citan cada afirmación. La latencia incluye cargar
el índice y el modelo de embeddings en un proceso nuevo de la CLI; la comparación formal cadena vs. agente queda
para T066.

## 4. Pendiente

- Ejecutar el quickstart con la clave real de DeepSeek y registrar latencia, tokens y citas (T045).
- Verificar con la clave real los caminos de error: ausente, inválida y sin red (T046).
- Confirmar el identificador `deepseek-flash` y las tarifas por token con la cuenta del proveedor.
- Calificar a mano corrección, coherencia y alucinación de M1-08 (§3.4) y M1-09 (§3.5); decidir si `qa.md` 1.1
  queda como final pese a la regresión en P14.
- Registrar la variante final de prompts tras el ajuste con evidencia (M1-09).

## 5. Observaciones sobre el corpus real (15.211 unidades)

Primera ejecución sobre `data/gold` real (2026-10-30, modelo falso, sin ajuste de prompts):

- `¿Qué productos ofrece Manuelita?` devuelve 8 unidades; la primera es de tema `productos` pero su texto
  es una plantilla de formulario («Enviar información sobre ofertas…»). La segunda sí aporta catálogo.
- `¿Dónde está la casa matriz de Manuelita?` devuelve como primera unidad un texto literal sobre la
  localización de la casa matriz; el resto incluye ruido de fundación y certificaciones.
- `¿Qué certificaciones tiene Manuelita?` acierta el tema en la primera unidad («Manuelita obtiene
  certificación del IIA»).

Conclusión para M1-08/M1-09: la puntuación léxica ordena por tema, pero el corpus contiene páginas de
plantilla y navegación que compiten con el contenido sustantivo. Candidatos de ajuste, en este orden:
(1) penalizar unidades con `unit_type=passage` de baja densidad informativa y textos de formulario,
(2) exigir cobertura de varios términos de la pregunta además de la frecuencia, y (3) revisar el peso del
tema frente a la coincidencia léxica. No se ajusta todavía porque la decisión debe basarse en la
evaluación de 40 preguntas.
