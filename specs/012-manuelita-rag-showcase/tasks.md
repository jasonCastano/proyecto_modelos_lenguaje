# Tasks: Frontend profesional y showcase del Módulo 1

**Input**: Design documents from `specs/012-manuelita-rag-showcase/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: incluidas porque el plan, la especificación y la constitución exigen verificación medible. Las pruebas deben escribirse primero y fallar antes de la implementación.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US4`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Aplicación web con backend Python y frontend en `web/`; pruebas de API/E2E en `tests/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: dependencias, toolchain web, configuración base y gobernanza.

- [X] T001 Añadir `fastapi`, `uvicorn[standard]` y `httpx` a `pyproject.toml` con `uv add fastapi "uvicorn[standard]"` y `uv add --dev httpx`.
- [X] T002 Crear `web/package.json` con React 19, Vite, TypeScript, `@fontsource-variable/bricolage-grotesque`, `@fontsource-variable/public-sans`, Vitest, React Testing Library y scripts `dev`, `test`, `build`, `preview`; generar `web/package-lock.json` con `npm install`.
- [X] T003 [P] Crear `web/tsconfig.json`, `web/vite.config.ts` (proxy `/api` a `http://localhost:8000`) y `web/index.html`.
- [X] T004 [P] Añadir a `.gitignore` `web/node_modules/`, `web/dist/`, `web/coverage/` y artefactos de Playwright.
- [X] T005 [P] Crear `docs/decisions/0013-web-frontend.md` con la decisión React/Vite + FastAPI, alternativa Jinja/HTMX y consecuencias.
- [X] T006 Añadir a `Makefile` los objetivos `web-install`, `web-dev`, `web-test`, `web-build`, `e2e` y `check-web`, y documentarlos en `make help`.
- [X] T007 Añadir a `.github/workflows/ci.yml` un job `web` con Node 24, `npm ci`, `npm run test` y `npm run build`; mantener Python.
- [X] T008 [P] Crear `web/vitest.config.ts` y `web/src/test/setup.ts` con jsdom, Testing Library y matchers de accesibilidad básicos.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: contratos, API base, tokens visuales, cliente HTTP y shell de la página.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [X] T009 [P] Crear pruebas de contrato en `tests/api/test_contracts.py`: validar `contracts/answer.schema.json` y `contracts/showcase.schema.json` con muestras `ok`, `fallback` y `error`.
- [X] T010 [P] Crear pruebas de API base en `tests/api/test_api.py`: `GET /api/health` responde sin clave, `GET /api/showcase` responde con métricas y `GET /` sirve la página.
- [X] T011 Implementar `src/proyecto_modelos_lenguaje/api_models.py` con `AskRequest` (question 1–500, mode `real|demo`), `SummaryRequest` (pack `8000|32000`), `FaqRequest` (limit 10–20), `CitedAnswer`, `Citation`, `ApiError` y `HealthStatus`.
- [X] T012 Implementar `src/proyecto_modelos_lenguaje/api.py` con FastAPI, `GET /api/health`, manejo de errores, CORS solo para desarrollo y servicio estático de `web/dist`.
- [X] T013 Implementar `src/proyecto_modelos_lenguaje/showcase.py` con secciones y métricas desde `load_app_metrics()`; no hardcodear cifras.
- [X] T014 Crear `web/src/styles/tokens.css` con la paleta corporativa `#387C2B`, `#E86D1F`, `#B0BC22`, `#FFD200`, `#F5F7F3`, `#14240F`, neutros derivados, escala tipográfica y espaciado.
- [X] T015 Crear `web/src/styles/global.css` con reset, tipografía, foco visible, `prefers-reduced-motion`, layout base y utilidades de sección.
- [X] T016 [P] Crear `web/src/lib/types.ts` y `web/src/lib/api.ts` con los tipos del contrato, `fetch` tipado, `AbortController` y mapeo de errores.
- [X] T017 [P] Crear `web/src/hooks/useRag.ts` con estado `idle|submitting|success|fallback|error`, modo real/demo, sesión en memoria y reintento.
- [X] T018 [P] Crear `web/src/App.tsx` y `web/src/main.tsx` con shell semántico, carga de fuentes y composición de secciones.
- [X] T019 Crear `tests/e2e/conftest.py` con fixtures de Playwright, arranque de API/build y helper de modo demo.
- [X] T020 Añadir `web/src/vite-env.d.ts`, `web/src/test/fixtures.ts` y configuración de `npm run test` para componentes.

**Punto de control**: API base, contratos, tokens, cliente y shell listos.

---

## Fase 3: Historia de Usuario 1 — Consultar el RAG (Prioridad: P1) 🎯 MVP

**Objetivo**: preguntar, resumir y generar FAQ con respuestas citadas, fallback y reintento.

**Prueba independiente**: enviar una pregunta real/demo y verificar respuesta con cita o fallback; cambiar a Resumen y FAQ sin perder la sesión.

### Pruebas de la Historia 1

- [X] T021 [P] [US1] Añadir en `tests/api/test_api_ask.py` pruebas de `POST /api/ask`: éxito con citas, fallback sin citas, pregunta vacía/larga, modo demo y ausencia de clave en la respuesta.
- [X] T022 [P] [US1] Añadir en `tests/api/test_api_tasks.py` pruebas de `POST /api/summary` y `POST /api/faq`: paquete válido, límite 10–20, fallback y metadatos.
- [X] T023 [P] [US1] Añadir en `web/src/test/RagConsole.test.tsx` pruebas de validación, carga, éxito, fallback, error y reintento.
- [X] T024 [P] [US1] Añadir en `tests/e2e/test_ask.py` el flujo de consulta real/demo, cambio a Resumen/FAQ y foco en la respuesta.

### Implementación de la Historia 1

- [X] T025 [US1] Implementar `POST /api/ask` en `src/proyecto_modelos_lenguaje/api.py` usando `answer_question`, `mode=demo` y el mapeo de `TaskResult` a `CitedAnswer`.
- [X] T026 [US1] Implementar `POST /api/summary` y `POST /api/faq` en `src/proyecto_modelos_lenguaje/api.py` reutilizando `summarize_corpus` y `generate_faq`.
- [X] T027 [US1] Implementar en `src/proyecto_modelos_lenguaje/api.py` el normalizador de errores a `ApiError` (`config_missing_key`, `auth_failed`, `rate_limited`, `timeout`, `provider_unavailable`, `empty_response`).
- [X] T028 [US1] Crear `web/src/components/Hero.tsx` con titular, explicación, CTA “Preguntar al corpus” y CTA “Recorrer el Módulo 1”.
- [X] T029 [US1] Crear `web/src/components/RagConsole.tsx` con tabs Consulta/Resumen/FAQ, campo, validación 500, estado de carga y `aria-live`.
- [X] T030 [US1] Crear `web/src/components/AnswerPanel.tsx` con respuesta segura, metadatos, fallback explícito y botón Reintentar.
- [X] T031 [US1] Crear `web/src/components/SourceList.tsx` con `[U#]`, título, sección/página/tiempo, autoridad y enlace externo seguro.
- [X] T032 [US1] Conectar `useRag` y la consola en `web/src/App.tsx`, conservar pregunta/respuesta y mover el foco al resultado.
- [X] T033 [US1] Crear `web/src/components/TaskTabs.tsx` con el selector Consulta/Resumen/FAQ, el cambio de tarea y el estado vacío de cada modo.

**Punto de control**: consulta, resumen y FAQ funcionan con citas o fallback.

---

## Fase 4: Historia de Usuario 2 — Recorrer el Módulo 1 (Prioridad: P2)

**Objetivo**: contar qué se construyó con datos reales, evidencia y límites.

**Prueba independiente**: recorrer la página y comprobar que un lector externo explica el Módulo 1 en menos de cinco minutos.

### Pruebas de la Historia 2

- [X] T034 [P] [US2] Añadir en `tests/api/test_showcase.py` pruebas de `GET /api/showcase`: 8 secciones ordenadas, métricas positivas, `data_status` y evidencia enlazada.
- [X] T035 [P] [US2] Añadir en `web/src/test/ShowcaseStory.test.tsx` pruebas de secciones, métricas, estados `partial|pending` y enlaces.
- [X] T036 [P] [US2] Añadir en `tests/e2e/test_showcase.py` recorrido por anclas, límites, fuentes y aviso académico.

### Implementación de la Historia 2

- [X] T037 [US2] Implementar `GET /api/showcase` en `src/proyecto_modelos_lenguaje/api.py` y completar `showcase.py` con secciones problema, datos, medallion, prompts, tareas, app, métricas y límites.
- [X] T038 [US2] Crear `web/src/data/showcase.ts` con la narrativa breve y los enlaces de evidencia, sin cifras hardcodeadas.
- [X] T039 [US2] Crear `web/src/components/ShowcaseStory.tsx` con el ledger vertical y los estados de sección.
- [X] T040 [US2] Crear `web/src/components/MetricsBand.tsx` con bandas de datos, cobertura, tokens y fuente; cifras desde la API.
- [X] T041 [US2] Crear `web/src/components/EvidenceLinks.tsx`, `LimitsNote.tsx` y `Footer.tsx` con specs, ADR, reportes, limitaciones y aviso de no afiliación.
- [X] T042 [US2] Añadir navegación por anclas y el rail de progreso en `web/src/App.tsx` y `global.css`, accesible por teclado.

**Punto de control**: el showcase se entiende sin conocer el repositorio.

---

## Fase 5: Historia de Usuario 3 — Identidad y productos (Prioridad: P3)

**Objetivo**: que la página se sienta Manuelita/Valle del Cauca y no una plantilla.

**Prueba independiente**: revisar la página a 360/768/1440/1920 y confirmar paleta, motivos y legibilidad.

### Pruebas de la Historia 3

- [X] T043 [P] [US3] Añadir en `tests/api/test_web_tokens.py` una prueba de paridad entre los hex de `BrandPalette` en `brand.py` y `web/src/styles/tokens.css`.
- [X] T044 [P] [US3] Añadir en `web/src/test/CaneField.test.tsx` y `ProductMotifs.test.tsx` pruebas de SVG decorativo/informativo, `aria-hidden` y textos alternativos.
- [X] T045 [P] [US3] Añadir en `tests/e2e/test_responsive.py` la matriz 360/768/1440/1920, ausencia de scroll horizontal, foco visible y reduced motion.

### Implementación de la Historia 3

- [X] T046 [US3] Crear `web/src/components/CaneField.tsx` con el gesto SVG de cañaveral y surcos, sin imágenes externas.
- [X] T047 [US3] Crear `web/src/components/ProductMotifs.tsx` con cristal de azúcar, palma y onda de energía como estructura informativa.
- [X] T048 [US3] Integrar Bricolage Grotesque y Public Sans en `web/src/main.tsx` y `tokens.css`; ajustar escala editorial y line-length.
- [X] T049 [US3] Componer el hero asimétrico y la veta visual en `Hero.tsx`/`global.css`, evitando la cuadrícula uniforme de cards.
- [X] T050 [US3] Implementar en `web/src/styles/global.css` responsive 360–1920, foco de alto contraste, contraste 4.5:1 y `prefers-reduced-motion`.
- [X] T051 [US3] Implementar una única secuencia de entrada en el hero y transición de respuesta en `Hero.tsx`/`AnswerPanel.tsx`.

**Punto de control**: identidad visual reconocible y accesible.

---

## Fase 6: Historia de Usuario 4 — Real, demo y errores (Prioridad: P4)

**Objetivo**: operar con proveedor real, demo o sin conexión sin fallos silenciosos.

**Prueba independiente**: abrir sin clave, activar demo, simular timeout y reintentar.

### Pruebas de la Historia 4

- [X] T052 [P] [US4] Añadir en `tests/api/test_api_health.py` pruebas de health con clave, sin clave, demo y proveedor caído.
- [X] T053 [P] [US4] Añadir en `web/src/test/DemoBanner.test.tsx` pruebas de banner, modo demo, falta de clave, timeout y reintento.
- [X] T054 [P] [US4] Añadir en `tests/e2e/test_demo.py` los flujos sin clave, demo y error recuperable.

### Implementación de la Historia 4

- [X] T055 [US4] Implementar `GET /api/health` en `api.py` con `configured`, `demo_available`, modelo y latencia; nunca devolver la clave.
- [X] T056 [US4] Extender `mode=demo` en `src/proyecto_modelos_lenguaje/api.py` a `ask`, `summary` y `faq` con `build_scripted_model` y metadatos `provider=demo`.
- [X] T057 [US4] Crear `web/src/components/DemoBanner.tsx` y el estado de salud en `App.tsx`; banner visible y CTA de demo.
- [X] T058 [US4] Completar el mapeo de errores, reintento, conservación de pregunta y sesión en `useRag.ts`/`AnswerPanel.tsx`.
- [X] T059 [US4] Documentar en `web/src/data/showcase.ts` o `Footer.tsx` el modo demo y el aviso académico.

**Punto de control**: real, demo y errores funcionan de forma explícita.

---

## Fase 7: Pulido y aspectos transversales

**Propósito**: retirar Streamlit, actualizar gobernanza, validar build y publicar.

- [X] T060 Retirar `app.py`, las pruebas específicas de Streamlit y la dependencia `streamlit` de `pyproject.toml`; migrar la cobertura útil a `tests/api` y `tests/e2e`.
- [X] T061 Limpiar de `src/proyecto_modelos_lenguaje/brand.py` las funciones exclusivas de Streamlit (`inject_brand_styles`, HTML de app) y conservar la paleta/contraste como fuente verificable.
- [X] T062 Actualizar `Makefile`: `app` ejecuta `uvicorn` + web build, `check` incluye Python y `check-web`, y `audit` se mantiene operativo.
- [X] T063 Actualizar `README.md`, `CONSTITUTION.md` y `docs/decisions/0013-web-frontend.md` con la nueva entrada, comandos y retiro de Streamlit.
- [X] T064 Actualizar `.github/workflows/ci.yml` para build web, tests y smoke de API; asegurar que CI no necesita clave real.
- [X] T065 Ejecutar `make check`, `npm run test`, `npm run build` y `uv run pytest tests/e2e -q`; corregir fallos.
- [X] T066 Ejecutar la matriz E2E 360/768/1440/1920, revisar foco, contraste, reduced motion y ausencia de scroll horizontal; guardar capturas en `docs/capturas/web/`.
- [X] T067 Verificar el bundle: JS inicial < 250 KB gzip, fuentes autohospedadas y cero claves/rutas absolutas; documentar medición.
- [X] T068 Regenerar la bitácora con `uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py`.
- [X] T069 Crear rama, commits atómicos y PR que incluya `specs/012-manuelita-rag-showcase/`, capturas, resultados y checklist de la constitución; no fusionar hasta CI verde.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias.
- **Fundamentos (Fase 2)**: depende de Fase 1; bloquea las historias.
- **US1 Consulta (Fase 3)**: depende de Fase 2; entrega el MVP.
- **US2 Showcase (Fase 4)**: depende de Fase 2 y de la shell de US1.
- **US3 Identidad (Fase 5)**: depende de Fase 2 y de Hero/consola de US1.
- **US4 Real/demo (Fase 6)**: depende de US1 y de la API base.
- **Pulido (Fase 7)**: depende de todas las historias.

### Dependencias entre historias

- **US1**: no depende de otras historias; entrega la consulta citada.
- **US2**: requiere shell y navegación; se prueba sola con `/api/showcase`.
- **US3**: requiere Hero y consola; se prueba con matriz visual.
- **US4**: requiere la API de tareas; añade estados y demo.

### Dentro de cada historia

1. Pruebas primero; deben fallar antes de la implementación.
2. Contratos/modelos antes de endpoints.
3. Componentes base antes de la composición.
4. Integración antes de la validación visual.
5. Cada historia deja lint y pruebas en verde.

### Oportunidades de paralelización

- T003–T005 y T008 pueden ejecutarse en paralelo.
- T009–T010 y T014–T018 pueden ejecutarse en paralelo (pruebas, tokens, cliente y shell).
- T021–T024 pueden ejecutarse en paralelo (pruebas de API, componentes y E2E).
- T034–T036 pueden ejecutarse en paralelo (showcase API, componentes y E2E).
- T043–T045 pueden ejecutarse en paralelo (tokens, SVG y responsive).
- T052–T054 pueden ejecutarse en paralelo (health, demo y E2E).
- T060–T063 comparten documentación/configuración; ejecutar con cuidado.

---

## Ejemplo de paralelización: Fundamentos

```text
Tarea: T009 Contratos JSON en tests/api/test_contracts.py
Tarea: T010 API base en tests/api/test_api.py
Tarea: T014 Tokens CSS en web/src/styles/tokens.css
Tarea: T016 Cliente API en web/src/lib/api.ts
Tarea: T017 Hook useRag en web/src/hooks/useRag.ts
```

## Ejemplo de paralelización: US1

```text
Tarea: T021 Pruebas de /api/ask en tests/api/test_api_ask.py
Tarea: T023 Pruebas de RagConsole en web/src/test/RagConsole.test.tsx
Tarea: T024 E2E de consulta en tests/e2e/test_ask.py
```

---

## Estrategia de implementación

### MVP primero (US1 + shell)

1. Completar Fase 1 y Fase 2.
2. Completar US1: hero, consola, respuesta, citas y fallback.
3. Validar con modo demo y con DeepSeek real.
4. Detenerse antes de US2–US4.

### Entrega incremental

1. Setup + Fundamentos → API, tokens y shell.
2. US1 → consulta citada (MVP).
3. US2 → showcase del Módulo 1.
4. US3 → identidad visual y responsive.
5. US4 → real/demo/errores.
6. Pulido → retiro de Streamlit, documentación, capturas y PR.

### Estrategia con dos integrantes

1. Ambos completan Setup + Fundamentos.
2. Jason: API, showcase y métricas.
3. Roberto: consola, identidad visual y estados.
4. Integrar en orden US1 → US2 → US3 → US4 y validar cada checkpoint.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente.
- Cada tarea debe dejar `make check` y `npm run test` en verde cuando aplique.
- La clave DeepSeek nunca se usa en pruebas de CI; el modo demo cubre los flujos.
- Las cifras del showcase provienen de la API, no de literales en React.
- Las capturas se generan de la página real; no se inventan.
- El retiro de Streamlit se hace al final, después de migrar la cobertura.
- No se cambia el corpus, los prompts ni la recuperación en esta feature.
