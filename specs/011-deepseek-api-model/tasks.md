# Tareas: Modelo DeepSeek vía API en lugar de Ollama local

**Entrada**: documentos de diseño de `/specs/011-deepseek-api-model/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: incluidas porque la especificación las exige (FR-020, SC-005) y la constitución obliga a que la
suite sea offline. Cada prueba debe fallar antes de la implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US5`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: configuración en `config/`, código en `src/proyecto_modelos_lenguaje/`, app en `app.py`,
pruebas en `tests/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: dependencias, configuración versionada y esqueletos de prueba.

- [x] T001 [P] En `pyproject.toml`, retirar `langchain-ollama` y añadir `langchain-openai`; ejecutar `uv sync` y confirmar que `uv.lock` queda actualizado.
- [x] T002 [P] Reescribir `config/llm.toml` con `provider = "deepseek"`, `model = "deepseek-flash"`, `base_url = "https://api.deepseek.com/v1"`, `api_key_env = "DEEPSEEK_API_KEY"`, `timeout_seconds = 60`, `max_retries = 1`, `cost_per_1k_input`/`cost_per_1k_output` en `0.0` y sin claves `keep_alive` ni `seed`.
- [x] T003 [P] Actualizar `.env.example` con `DEEPSEEK_API_KEY=` (sin valor real), `DEEPSEEK_MODEL` y `DEEPSEEK_BASE_URL` opcionales, y retirar `OLLAMA_*`.
- [x] T004 [P] Crear los esqueletos `tests/unit/test_llm.py`, `tests/contract/test_llm_contract.py` y `tests/integration/test_llm_api.py`.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: configuración, errores, cliente y redacción.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [x] T005 Implementar en `src/proyecto_modelos_lenguaje/llm.py` el dataclass `ProviderConfig` con los campos de `data-model.md` §1.1 y `to_dict()` que expone `api_key_env` y `api_key_present`, nunca la clave.
- [x] T006 Implementar `load_llm_config` con las validaciones: `provider` en `{deepseek}`, `base_url` con prefijo `https://`, `api_key_env` con patrón `^[A-Z][A-Z0-9_]*$`, `temperature` 0–1, `top_p` 0.01–1, `max_output_tokens` 128–8192, `context_window` 2048–131072, `default_context_pack` en `{"8000","32000"}` y nunca mayor que `context_window`, `timeout_seconds` 5–300, `max_retries` 0–3, `retry_backoff_seconds` 0–30, tarifas `>= 0`, `language` en `{"es","en"}`.
- [x] T007 Implementar en `llm.py` el rechazo de claves prohibidas en la configuración (`api_key`, `token`, `secret`, `password`) con `LLMConfigError` que nombra el campo.
- [x] T008 Implementar en `llm.py` la jerarquía de errores `LLMAuthError`, `LLMRateLimitError`, `LLMTimeoutError`, conservando `LLMConfigError`, `LLMUnavailableError`, `LLMModelMissingError` y `LLMResponseError`.
- [x] T009 Implementar en `llm.py` el cliente OpenAI-compatible con `base_url`, `timeout_seconds`, `temperature`, `top_p`, `max_output_tokens` y la clave leída de `os.environ[api_key_env]`.
- [x] T010 Implementar en `llm.py` el mapeo de fallos al error del proyecto según `contracts/provider-errors.md` §1 (401/403 → `auth_failed`, 404 → `model_unavailable`, 429 → `rate_limited`, timeout → `timeout`, 5xx/red → `provider_unavailable`, vacío → `empty_response`, JSON inválido → `invalid_response`).
- [x] T011 Implementar en `llm.py` la política de reintentos: solo `rate_limited`, `timeout`, `provider_unavailable`, `empty_response` e `invalid_response`; nunca `auth_failed` ni `model_unavailable`.
- [x] T012 Implementar en `llm.py` la función que construye el mensaje accionable por error y garantiza que ninguna salida incluye la clave ni el encabezado `Authorization`.
- [x] T013 [P] Añadir en `tests/contract/test_llm_contract.py` la validación de `ProviderConfig.to_dict()` contra `specs/011-deepseek-api-model/contracts/provider-config.schema.json`, incluido `additionalProperties: false`.
- [x] T014 [P] Añadir en `tests/unit/test_llm.py` pruebas de: configuración válida, cada rango inválido, campo de secreto prohibido, `api_key_present` verdadero y falso, y ausencia de la clave en `to_dict()`.

**Punto de control**: configuración, errores, cliente y redacción listos.

---

## Fase 3: Historia de Usuario 1 — Respuestas con el modelo en la nube (Prioridad: P1) 🎯 MVP

**Objetivo**: las tres tareas generan con DeepSeek conservando citas, fallback y metadatos.

**Prueba independiente**: con un transporte simulado, Q&A y Resumen devuelven citas o fallback y declaran el modelo configurado.

### Pruebas de la Historia 1

- [x] T015 [US1] Añadir en `tests/integration/test_llm_api.py` un doble de transporte que devuelva una respuesta con `[U1]` y verificar que `answer_question` produce `status=ok` con al menos una cita.
- [x] T016 [US1] Añadir en `tests/integration/test_llm_api.py` la prueba de que una pregunta sin evidencia devuelve `status=fallback` **sin** invocar el transporte remoto.

### Implementación de la Historia 1

- [x] T017 [US1] Implementar en `llm.py` `build_chat_model(config)` con el cliente OpenAI-compatible, reemplazando la construcción de Ollama y conservando la firma que ya usan `tasks.py` y `app.py`.
- [x] T018 [US1] Actualizar en `llm.py` `invoke_with_retries` para usar la nueva política de errores y registrar latencia.
- [x] T019 [US1] Verificar en `src/proyecto_modelos_lenguaje/tasks.py` que no se requiere ningún cambio: las tres tareas reciben el `BaseChatModel` y conservan `TaskResult` con `model`, `input_tokens`, `output_tokens` y `latency_seconds`.
- [x] T020 [US1] Ejecutar la suite existente de tareas (`tests/unit/test_tasks.py`, `tests/integration/test_tasks_fake.py`, `tests/contract/test_tasks_contract.py`) y corregir cualquier regresión del contrato.

**Punto de control**: las tres tareas funcionan con el proveedor y con el modelo falso.

---

## Fase 4: Historia de Usuario 2 — Configurar sin exponer la clave (Prioridad: P2)

**Objetivo**: diagnóstico y configuración seguros, sin filtrar el secreto.

**Prueba independiente**: `--print-config` y `--check` muestran el estado y nunca el valor de la clave.

### Pruebas de la Historia 2

- [x] T021 [US2] Añadir en `tests/unit/test_llm.py` la prueba `-k secret` que recorre `config/llm.toml`, la salida de `--print-config`, un `TaskResult` serializado y el JSON de sesión, y falla si aparece el valor de `DEEPSEEK_API_KEY`.
- [x] T022 [US2] Añadir en `tests/contract/test_llm_contract.py` la validación de la salida de `--print-config` contra el esquema del proveedor.

### Implementación de la Historia 2

- [x] T023 [US2] Implementar en `llm.py` `main()` con `--print-config` que emita el JSON del esquema (incluido `api_key_present`) y `--check` con los códigos de salida `0`/`2` de `contracts/provider-errors.md` §3.
- [x] T024 [US2] Implementar el mensaje `config_missing_key` («Define `DEEPSEEK_API_KEY` en `.env` y recarga la app.») cuando la variable falte, vacía o contenga solo espacios.
- [x] T025 [US2] Documentar en `README.md` la variable de entorno, el comando de verificación y la advertencia de no versionar la clave.

**Punto de control**: el equipo configura y verifica el proveedor sin filtraciones.

---

## Fase 5: Historia de Usuario 3 — Trabajar sin red ni costo (Prioridad: P3)

**Objetivo**: el modo demostración es la única vía offline y está rotulado.

**Prueba independiente**: sin red y sin clave, las cuatro vistas responden con el modelo falso.

### Pruebas de la Historia 3

- [x] T026 [US3] Añadir en `tests/unit/test_llm.py` la prueba de que con `PML_DEMO=1` no se lee la clave ni se construye el cliente remoto.
- [x] T027 [US3] Añadir en `tests/integration/test_app_pages.py` la prueba de que el modo demo rotula «Modo demo» y permite preguntar sin transporte remoto.

### Implementación de la Historia 3

- [x] T028 [US3] Ajustar en `app.py` `model_for` y el panel para que el modo demo no toque la configuración del proveedor y muestre «modelo de demostración».
- [x] T029 [US3] Implementar en `app.py` el mensaje accionable cuando no hay red, no hay clave y el demo está desactivado, con la sugerencia explícita de activarlo.

**Punto de control**: demo y offline funcionan sin costo.

---

## Fase 6: Historia de Usuario 4 — Auditar uso y costo (Prioridad: P4)

**Objetivo**: modelo, tokens y costo visibles en resultados y panel.

**Prueba independiente**: una respuesta muestra tokens y costo (o «no configurado») y coincide con la tarifa.

### Pruebas de la Historia 4

- [x] T030 [US4] Añadir en `tests/unit/test_llm.py` pruebas de `estimate_cost(input_tokens, output_tokens, config)` con tarifas en cero y con tarifas positivas.
- [x] T031 [US4] Añadir en `tests/integration/test_llm_api.py` la prueba de que los tokens del proveedor se usan cuando llegan y se estiman cuando no.

### Implementación de la Historia 4

- [x] T032 [US4] Implementar en `llm.py` la extracción de `usage` del proveedor con respaldo en `silver.cleaning.estimate_tokens`.
- [x] T033 [US4] Implementar en `llm.py` el cálculo de costo estimado y el acumulado `UsageSummary` de la sesión.
- [x] T034 [US4] Mostrar en `app.py` proveedor, modelo, tokens de entrada/salida y costo estimado (o «costo no configurado» si la tarifa es cero).
- [x] T035 [US4] Incluir el `UsageSummary` en la descarga de sesión de `app.py`, sin claves ni encabezados.

**Punto de control**: el uso y el costo son auditables.

---

## Fase 7: Historia de Usuario 5 — Errores accionables del proveedor (Prioridad: P5)

**Objetivo**: cada fallo del servicio produce un mensaje claro y la app sigue usable.

**Prueba independiente**: simular 401, 429, timeout, 5xx y respuesta vacía; cada uno con mensaje propio y sin traza.

### Pruebas de la Historia 5

- [x] T036 [US5] Añadir en `tests/integration/test_llm_api.py` los casos 401, 403, 404, 429, 500, timeout, respuesta vacía y JSON inválido, verificando el error resultante y el mensaje.
- [x] T037 [US5] Añadir en `tests/integration/test_llm_api.py` la prueba de reintentos: 429 reintenta una vez; 401 no reintenta.

### Implementación de la Historia 5

- [x] T038 [US5] Mapear en `tasks.py` los errores del proveedor a los códigos de `TaskResult` (`model_timeout`, `model_error`, `invalid_config`) según `contracts/provider-errors.md` §2.
- [x] T039 [US5] Actualizar en `app.py` `error_message` con los mensajes nuevos y mantener el botón de reintento sin perder la sesión.

**Punto de control**: los fallos del proveedor son comprensibles y recuperables.

---

## Fase 8: Pulido y aspectos transversales

**Propósito**: retirada de Ollama, documentación, decisión y verificación final.

- [x] T040 Retirar de `README.md`, `.env.example`, `scripts/` y `config/llm.toml` toda referencia a Ollama, `llama3.1:8b`, `keep_alive` y `seed`, y confirmar que `uv tree` ya no muestra `langchain-ollama`.
- [x] T041 Crear `docs/decisions/0012-deepseek-api.md` con la justificación §3.5 (costo, latencia, calidad, idioma y disponibilidad), el mapeo de errores y la política de datos enviados.
- [x] T042 Actualizar `docs/prompt_log.md` con la nueva línea base: modelo, parámetros, prompts y una muestra observada.
- [x] T043 Ejecutar `uv run ruff check .` y `uv run ruff format --check .` y corregir hallazgos en `llm.py`, `app.py` y `tests/`.
- [x] T044 Ejecutar `uv run pytest` y corregir fallos, verificando que la suite termina en menos de 2 minutos y sin red.
- [ ] T045 Ejecutar los escenarios de `specs/011-deepseek-api-model/quickstart.md` con la clave real: `--print-config`, `--check`, Q&A, Resumen y FAQ; registrar latencia, tokens y citas. *(Bloqueada: no hay `DEEPSEEK_API_KEY` en el equipo.)*
- [ ] T046 Verificar en `specs/011-deepseek-api-model/quickstart.md` §7 los caminos de error: clave ausente, clave inválida y modo demo sin red. *(Bloqueada: requiere la clave real; la simulación de los mismos caminos está cubierta por `tests/integration/test_llm_api.py`.)*
- [x] T047 Regenerar la bitácora con `uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py`.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; puede empezar de inmediato.
- **Fundamentos (Fase 2)**: depende de Fase 1; bloquea todas las historias.
- **US1 (Fase 3)**: depende de Fase 2; es el MVP.
- **US2 (Fase 4)**: depende de Fase 2; puede ejecutarse en paralelo con US1 si se separan archivos (US1 toca el cliente, US2 el CLI y las pruebas de fuga).
- **US3 (Fase 5)**: depende de Fase 2; toca `app.py`, no depende de US1.
- **US4 (Fase 6)**: depende de US1 (necesita respuestas reales del cliente).
- **US5 (Fase 7)**: depende de Fase 2 y de US1 para el mapeo en `tasks.py`.
- **Pulido (Fase 8)**: depende de todas las historias.

### Dentro de cada historia

1. Pruebas primero; deben fallar antes de la implementación.
2. Configuración y errores antes del cliente.
3. Cliente antes de la integración con tareas.
4. Cada historia debe dejar Ruff y pytest en verde.

### Oportunidades de paralelización

- T001–T004 pueden ejecutarse en paralelo (archivos distintos).
- T013–T014 pueden ejecutarse en paralelo (archivos distintos).
- US2 (CLI y pruebas de fuga) y US3 (app y demo) pueden avanzar en paralelo tras la Fase 2.
- US4 y US5 comparten `llm.py` y `tests/integration/test_llm_api.py`: ejecutar en orden.

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 y Fase 2.
2. Completar US1 (cliente + tres tareas).
3. Ejecutar `uv run python -m proyecto_modelos_lenguaje.tasks qa --question "¿Qué productos ofrece Manuelita?" --json` con la clave real.
4. Detenerse y validar citas, fallback y metadatos antes de US2–US5.

### Entrega incremental

1. Preparación + Fundamentos → configuración y cliente listos.
2. US1 → respuestas con el proveedor (MVP).
3. US2 → configuración y verificación seguras.
4. US3 → offline sin costo.
5. US4 → auditoría de tokens y costo.
6. US5 → errores accionables.
7. Pulido → retirada de Ollama, ADR, prompt log, quickstart y bitácora.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 y US4 (cliente, tokens y costo).
3. Roberto: US2, US3 y US5 (configuración, demo y errores).
4. Integrar en orden US1 → US2 → US3 → US4 → US5 validando cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- Nunca se ejecutan pruebas contra el servicio real: la suite usa el modelo falso y un transporte simulado.
- La clave no se escribe en el repositorio, ni en logs, ni en la descarga de sesión.
- No se modifica el corpus ni se escribe en las capas medallion.
- El modo demostración es la única vía offline después de retirar Ollama.
