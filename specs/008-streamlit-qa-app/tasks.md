# Tareas: App Streamlit — Resumen, FAQ y Q&A

**Entrada**: documentos de diseño de `/specs/008-streamlit-qa-app/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: incluidas porque el plan y la constitución exigen pruebas offline para la app y sus helpers.
Cada prueba debe fallar antes de la implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: app en `app.py`, helpers en `src/proyecto_modelos_lenguaje/`, pruebas en `tests/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: dependencia de Streamlit y esqueletos de prueba.

- [X] T001 [P] Añadir `streamlit` a las dependencias de ejecución en `pyproject.toml` y actualizar `uv.lock` con `uv add streamlit`.
- [X] T002 [P] Crear el esqueleto de pruebas de métricas en `tests/unit/test_app_metrics.py`.
- [X] T003 [P] Crear el esqueleto de pruebas de la app en `tests/unit/test_app.py`.
- [X] T004 [P] Crear el esqueleto de pruebas de integración con `AppTest` en `tests/integration/test_app_streamlit.py`.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: métricas, estado, shell de la app, citas y manejo de errores.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [X] T005 Crear `src/proyecto_modelos_lenguaje/app_metrics.py` con el dataclass `AppMetrics` y `load_app_metrics`: `active_artifacts`, `canonical_documents`, `aliases`, `chunks`, `units`, `facts`, `entities`, `conflicts`, `coverage_covered`, `coverage_total=24`, `silver_tokens`, `gold_tokens`, `skipped`, `omissions`, `silver_run`, `gold_run`, `data_status`, `detail`.
- [X] T006 Implementar en `src/proyecto_modelos_lenguaje/app_metrics.py` la lectura de `v_active_artifacts` en modo `mode=ro`, los reportes de plata/oro, `coverage.json` y `manifest.json`, con detección de archivos faltantes, vacíos o punteros LFS (`version https://git-lfs.github.com/spec/v1`).
- [X] T007 Implementar en `src/proyecto_modelos_lenguaje/app_metrics.py` los helpers de formato de métricas y estado: `format_metric`, `format_status`, `metric_rows` y `status_rows`.
- [X] T008 Crear `app.py` con `st.set_page_config`, título, layout ancho, tres pestañas (`Resumen`, `FAQ`, `Q&A`), barra lateral y estado de sesión para pregunta, resultados, FAQ, pack, límite y modo demostración.
- [X] T009 Implementar en `app.py` la selección de modelo Ollama/modelo falso, el control de modo demostración y el override `PML_DEMO=1`.
- [X] T010 Implementar en `app.py` el helper de citas: `[U#]`, título, URL clicable y sección/página/tiempo, sin HTML crudo ni `unsafe_allow_html`.
- [X] T011 Implementar en `app.py` el mapeo de errores a mensajes accionables para `TaskError`, `LLMUnavailableError`, `LLMModelMissingError`, `LLMResponseError` y excepciones inesperadas.
- [X] T012 [P] Añadir pruebas unitarias de `app_metrics.py` en `tests/unit/test_app_metrics.py`: métricas, `coverage_total=24`, suma de omisiones, datos completos/incompletos y punteros LFS.
- [X] T013 [P] Añadir pruebas unitarias de helpers de `app.py` en `tests/unit/test_app.py`: formato de citas, selección de modelo, `PML_DEMO=1`, mapeo de errores y validación.
- [X] T014 [P] Añadir prueba de contrato de `AppMetrics` en `tests/unit/test_app_metrics.py` con `contracts/app-metrics.schema.json` y una muestra válida.

**Punto de control**: métricas, shell, citas, modelo y errores listos; las historias pueden comenzar.

---

## Fase 3: Historia de Usuario 1 — Q&A citado (Prioridad: P1) 🎯 MVP

**Objetivo**: preguntar desde la app y recibir respuesta con citas o fallback, sin errores no controlados.

**Prueba independiente**: con `AppTest` y modo demostración, enviar 5 preguntas y verificar que cada resultado tiene cita visible o fallback, y que una pregunta vacía se rechaza.

### Pruebas de la Historia 1

- [X] T015 [US1] Añadir prueba unitaria de validación y render de Q&A en `tests/unit/test_app.py`: pregunta vacía, pregunta de más de 500 caracteres y formato de respuesta.
- [X] T016 [US1] Añadir prueba `AppTest` de Q&A en `tests/integration/test_app_streamlit.py`: modo demostración, pregunta, respuesta con cita o fallback y sin excepción.

### Implementación de la Historia 1

- [X] T017 [US1] Implementar en `app.py` la pestaña Q&A con formulario, campo de pregunta, botón **Preguntar**, validación y `st.spinner` para deshabilitar envíos duplicados.
- [X] T018 [US1] Implementar en `app.py` la llamada a `answer_question` con modelo real o falso, render de respuesta, citas `[U#]`, fuentes y fallback.
- [X] T019 [US1] Implementar en `app.py` el botón **Reintentar**, el estado de error y la conservación de la última respuesta en `st.session_state`.

**Punto de control**: Q&A funciona de extremo a extremo y es el MVP de M1-07.

---

## Fase 4: Historia de Usuario 2 — Resumen citado (Prioridad: P2)

**Objetivo**: generar el resumen desde la app con 8–12 citas y fuentes visibles.

**Prueba independiente**: con `AppTest` y modo demostración, generar el resumen, verificar 8–12 citas, fuentes y persistencia al cambiar de pestaña.

### Pruebas de la Historia 2

- [X] T020 [US2] Añadir prueba unitaria de resumen en `tests/unit/test_app.py`: selector de pack, render de citas y fallback con contexto vacío.
- [X] T021 [US2] Añadir prueba `AppTest` de resumen en `tests/integration/test_app_streamlit.py`: generar resumen, 8–12 citas y persistencia en sesión.

### Implementación de la Historia 2

- [X] T022 [US2] Implementar en `app.py` la pestaña Resumen con selector `8000`/`32000`, botón **Generar resumen**, estado de carga y llamada a `summarize_corpus`.
- [X] T023 [US2] Implementar en `app.py` el render Markdown del resumen, las citas, las fuentes y el fallback; conservar el resultado en `st.session_state`.

**Punto de control**: Resumen funciona con citas y fallback.

---

## Fase 5: Historia de Usuario 3 — FAQ con evidencia (Prioridad: P3)

**Objetivo**: generar y revisar 10–20 preguntas frecuentes con respuesta, citas y estado.

**Prueba independiente**: con `AppTest` y modo demostración, generar la FAQ, verificar 10–20 elementos y que cada uno tenga cita o `missing_evidence`.

### Pruebas de la Historia 3

- [X] T024 [US3] Añadir prueba unitaria de FAQ en `tests/unit/test_app.py`: formato, estado `ready|review|missing_evidence` y deduplicación visible.
- [X] T025 [US3] Añadir prueba `AppTest` de FAQ en `tests/integration/test_app_streamlit.py`: 10–20 preguntas, citas y persistencia en sesión.

### Implementación de la Historia 3

- [X] T026 [US3] Implementar en `app.py` la pestaña FAQ con selector 10–20, botón **Generar FAQ**, estado de carga y llamada a `generate_faq`.
- [X] T027 [US3] Implementar en `app.py` los `st.expander` por pregunta, respuesta, citas, estado y fallback `missing_evidence`; conservar la FAQ en `st.session_state`.

**Punto de control**: FAQ funciona y respeta evidencia y límites.

---

## Fase 6: Historia de Usuario 4 — Métricas, errores y auditoría (Prioridad: P4)

**Objetivo**: panel de métricas, estados de datos/modelo, mensajes accionables y seguridad de la salida.

**Prueba independiente**: abrir la app en modo demostración y verificar el panel, los estados de error, la ausencia de rutas absolutas y secretos, y la carga de datos incompletos.

### Pruebas de la Historia 4

- [X] T028 [US4] Añadir prueba unitaria del panel en `tests/unit/test_app_metrics.py`: al menos 8 métricas del corpus y 5 de la respuesta.
- [X] T029 [US4] Añadir prueba `AppTest` de panel y errores en `tests/integration/test_app_streamlit.py`: datos completos/incompletos, modelo no disponible y pregunta vacía.
- [X] T030 [US4] Añadir prueba unitaria de seguridad en `tests/unit/test_app.py`: sin claves, rutas absolutas, trazas ni HTML crudo.

### Implementación de la Historia 4

- [X] T031 [US4] Implementar en `app.py` el panel lateral con métricas del corpus, cobertura, tokens, descartes, runs, modelo, prompt, latencia, tokens y citas de la última respuesta.
- [X] T032 [US4] Implementar en `app.py` los estados de datos (`complete`, `incomplete`, `unknown`) y modelo (`ollama_ready`, `ollama_unavailable`, `model_missing`, `demo`) con mensajes y sugerencias.
- [X] T033 [US4] Implementar en `app.py` la accesibilidad y el layout responsive: etiquetas, contraste, textos alternativos, expanders y tablas legibles en pantallas estrechas.
- [X] T034 [US4] Verificar en `app.py` que no se usa `unsafe_allow_html`, no se muestran `.env`, claves, cookies, trazas ni rutas absolutas, y que la app no escribe en `data/`.

**Punto de control**: panel, estados y seguridad auditables.

---

## Fase 7: Pulido y aspectos transversales

**Propósito**: documentación, ADR, validación manual, CI y bitácora.

- [X] T035 Actualizar `README.md` con `uv run streamlit run app.py`, el modo demostración y el enlace a `specs/008-streamlit-qa-app/quickstart.md`.
- [X] T036 Crear `docs/decisions/0009-streamlit-app.md` con las decisiones de layout, estado, modo demostración, métricas de solo lectura y citas.
- [X] T037 Ejecutar `uv run ruff check .` y corregir hallazgos en `app.py`, `src/proyecto_modelos_lenguaje/app_metrics.py` y `tests/`.
- [X] T038 Ejecutar `uv run pytest -q` y corregir fallos en `tests/unit/test_app_metrics.py`, `tests/unit/test_app.py` y `tests/integration/test_app_streamlit.py`.
- [X] T039 Ejecutar `PML_DEMO=1 uv run pytest tests/integration/test_app_streamlit.py -q` y verificar las tres pestañas.
- [X] T040 Ejecutar `uv run streamlit run app.py` con Ollama real y validar Q&A, resumen, FAQ, panel y errores; anexar los resultados en `specs/008-streamlit-qa-app/quickstart.md`.
- [X] T041 Ejecutar `uv sync --frozen` y `uv build`; verificar que `streamlit` está en `pyproject.toml`/`uv.lock` y que el paquete se construye.
- [X] T042 Añadir los enlaces de especificación, plan, tareas y quickstart de M1-07 en `README.md`.
- [X] T043 Añadir al workflow `.github/workflows/ci.yml` un paso `PML_DEMO=1 uv run pytest tests/integration/test_app_streamlit.py -q`.
- [X] T044 Regenerar la bitácora con `uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py` y confirmar que M1-07 y G4 pasan a completadas.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; puede empezar de inmediato.
- **Fundamentos (Fase 2)**: depende de Fase 1; bloquea todas las historias.
- **US1 Q&A (Fase 3)**: depende de Fase 2; es el MVP.
- **US2 Resumen (Fase 4)**: depende de Fase 2 y de la shell; puede ejecutarse después de US1.
- **US3 FAQ (Fase 5)**: depende de Fase 2 y de la shell; puede ejecutarse después de US1.
- **US4 Panel/errores (Fase 6)**: depende de US1–US3 para mostrar métricas de la última respuesta.
- **Pulido (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1 (P1)**: no depende de otras historias; entrega el MVP.
- **US2 (P2)**: requiere Fase 2; se prueba sola.
- **US3 (P3)**: requiere Fase 2; se prueba sola.
- **US4 (P4)**: requiere US1–US3 para el panel y los estados.

### Dentro de cada historia

1. Pruebas primero; deben fallar antes de la implementación.
2. Helpers y estado antes de la interfaz.
3. Interfaz antes de la integración.
4. Cada historia debe dejar Ruff y pytest en verde.

### Oportunidades de paralelización

- T001–T004 pueden ejecutarse en paralelo (pyproject y archivos de prueba distintos).
- T012–T014 pueden ejecutarse en paralelo (pruebas en archivos distintos).
- T020/T021 y T024/T025 comparten archivos de prueba con otras historias; ejecutar en orden.
- Las implementaciones de US1–US3 comparten `app.py`; ejecutar secuencialmente.
- T028/T030 comparten `tests/unit/test_app_metrics.py`/`test_app.py`; ejecutar en orden.

---

## Ejemplo de paralelización: Fase 1

```text
Tarea: T001 Añadir streamlit a pyproject.toml y uv.lock
Tarea: T002 Crear tests/unit/test_app_metrics.py
Tarea: T003 Crear tests/unit/test_app.py
Tarea: T004 Crear tests/integration/test_app_streamlit.py
```

## Ejemplo de paralelización: Fundamentos

```text
Tarea: T012 Pruebas de app_metrics.py en tests/unit/test_app_metrics.py
Tarea: T013 Pruebas de helpers de app.py en tests/unit/test_app.py
Tarea: T014 Contrato de AppMetrics en tests/unit/test_app_metrics.py
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1: Preparación.
2. Completar Fase 2: Fundamentos.
3. Completar Fase 3: US1 Q&A.
4. Ejecutar `PML_DEMO=1 uv run pytest tests/integration/test_app_streamlit.py -q`.
5. Abrir la app en modo demostración y validar Q&A.
6. Detenerse y validar el MVP antes de US2–US4.

### Entrega incremental

1. Preparación + Fundamentos → shell y métricas.
2. US1 → Q&A citado (MVP).
3. US2 → Resumen citado.
4. US3 → FAQ con evidencia.
5. US4 → panel, errores y seguridad.
6. Pulido → README, ADR, quickstart, CI y bitácora.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 Q&A y US4 panel/errores.
3. Roberto: US2 Resumen y US3 FAQ.
4. Integrar en orden US1 → US2 → US3 → US4 y validar cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- La app es de solo lectura; no escribe en `data/`.
- La suite por defecto usa `PML_DEMO=1` y no requiere Ollama ni red.
- Las capturas para el README se toman después de validar el modo real y el modo demostración.
- La app no implementa evaluación, informe ni demo; eso es M1-08, M1-10 y M1-11.
