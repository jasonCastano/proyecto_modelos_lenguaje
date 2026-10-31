# Tasks: Verificación y ajuste del panel de Métricas

**Input**: Design documents from `specs/010-metrics-panel-layout/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: incluidas porque el plan, la especificación y la constitución exigen verificación medible. Las pruebas deben escribirse primero y fallar antes de la implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US3`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: app en `app.py`, estilos en `src/proyecto_modelos_lenguaje/brand.py`, constantes en `src/proyecto_modelos_lenguaje/metrics_layout.py`, auditoría en `scripts/`, pruebas en `tests/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: dependencia de auditoría, artefactos ignorados y esqueleto del script.

- [X] T001 Añadir `playwright>=1.64` al grupo `dev` en `pyproject.toml` y actualizar `uv.lock` con `uv add --dev playwright`.
- [X] T002 Añadir `artifacts/metrics-layout/` a `.gitignore` para que reportes y capturas no se versionen.
- [X] T003 [P] Crear `scripts/audit_metrics_layout.py` con el esqueleto CLI (`--url`, `--output`, `--browser`, `--headed`, `--help`) y sin lógica de geometría todavía.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: constantes de layout, contenedor de KPI, contrato CSS/DOM y motor de auditoría.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [X] T004 [P] Crear pruebas unitarias de `src/proyecto_modelos_lenguaje/metrics_layout.py` en `tests/unit/test_metrics_layout.py`: `KPI_KEY`, breakpoints `1200`/`640`, siete `ViewportProfile`, `expected_columns(width)` con 4 para `>=1200`, 2 para `641–1199` y 1 para `<=640`.
- [X] T005 Implementar `src/proyecto_modelos_lenguaje/metrics_layout.py` con `KPI_KEY = "metrics-kpis"`, `METRICS_BREAKPOINTS`, `ViewportProfile` y `VIEWPORTS` de `data-model.md`.
- [X] T006 [P] Crear pruebas de contrato en `tests/contract/test_metrics_layout_contract.py`: selectores `.st-key-metrics-kpis`, `stMetric`, `stMetricValue`, `stMetricLabel`, gráficos y expanders; reglas de breakpoints; esquema `contracts/layout-audit.schema.json` válido y muestra aceptada.
- [X] T007 [P] Envolver las dos filas de KPI en `app.py` con `st.container(key="metrics-kpis")` sin cambiar etiquetas, valores ni orden de las ocho tarjetas.
- [X] T008 Implementar en `scripts/audit_metrics_layout.py` la carga de `VIEWPORTS`, apertura de Playwright, navegación a `--url`, espera de la pestaña **Métricas** y captura de página completa.
- [X] T009 Implementar en `scripts/audit_metrics_layout.py` las comprobaciones de geometría: intersección de cajas entre hermanos, `scrollWidth <= clientWidth + 1`, recortes de `stMetricLabel`/`stMetricValue`, columnas detectadas y presencia de 8 tarjetas, 2 gráficos y 3 expanders.
- [X] T010 Implementar en `scripts/audit_metrics_layout.py` la escritura de `report.json` conforme a `contracts/layout-audit.schema.json`, con perfiles, hallazgos, estados y `passed`.

**Punto de control**: constantes, contenedor, contrato y auditoría listos; las historias pueden comenzar.

---

## Fase 3: Historia de Usuario 1 — Lectura completa en escritorio (Prioridad: P1) 🎯 MVP

**Objetivo**: la pestaña **Métricas** se lee completa y sin solapamientos en 1440×900 y 1920×1080.

**Prueba independiente**: abrir la pestaña en 1440×900 y 1920×1080, verificar 4 columnas, 8 tarjetas, 2 gráficos, 3 expanders y cero solapamientos.

### Pruebas de la Historia 1

- [X] T011 [P] [US1] Añadir prueba de estructura en `tests/integration/test_app_pages.py`: contenedor `metrics-kpis`, ocho etiquetas de KPI, dos gráficos y tres expanders.
- [X] T012 [US1] Añadir prueba de contrato en `tests/contract/test_metrics_layout_contract.py` para la regla de 4 columnas en `>=1200 px` y `minmax(0, 1fr)`.

### Implementación de la Historia 1

- [X] T013 [US1] Añadir en `src/proyecto_modelos_lenguaje/brand.py` la cuadrícula base de 4 columnas para `.st-key-metrics-kpis [data-testid="stHorizontalBlock"]`, con `min-width: 0` en columnas y gap mínimo de 1 rem.
- [X] T014 [US1] Añadir en `src/proyecto_modelos_lenguaje/brand.py` la separación vertical de títulos, gráficos, captions y expanders para escritorio, sin cambiar el orden de lectura.
- [X] T015 [US1] Ejecutar la auditoría en 1440×900 y 1920×1080, guardar `artifacts/metrics-layout/baseline/` y `artifacts/metrics-layout/us1/`, y corregir en `app.py`/`brand.py` cualquier solapamiento o desbordamiento encontrado.

**Punto de control**: escritorio aprobado y sin regresiones en las demás pestañas.

---

## Fase 4: Historia de Usuario 2 — Reorganización en ventanas estrechas (Prioridad: P2)

**Objetivo**: la cuadrícula pasa a 2 columnas en 768/1024 px y a 1 columna en 360/390 px sin scroll horizontal.

**Prueba independiente**: auditar 360×640, 390×844, 768×1024 y 1024×768 y verificar las columnas esperadas, ausencia de scroll horizontal y textos legibles.

### Pruebas de la Historia 2

- [X] T016 [P] [US2] Añadir prueba unitaria en `tests/unit/test_metrics_layout.py` para `expected_columns(390) == 1`, `expected_columns(768) == 2`, `expected_columns(1024) == 2` y `expected_columns(1440) == 4`.
- [X] T017 [P] [US2] Añadir prueba de contrato en `tests/contract/test_metrics_layout_contract.py` para las reglas `641–1199 px` (2 columnas) y `<=640 px` (1 columna).
- [X] T018 [P] [US2] Añadir prueba visual parametrizada en `tests/visual/test_metrics_layout_audit.py` para los cuatro perfiles estrechos; debe omitirse si Playwright o Chromium no están disponibles.

### Implementación de la Historia 2

- [X] T019 [US2] Añadir en `src/proyecto_modelos_lenguaje/brand.py` la media query de `641–1199 px` con dos columnas y gap consistente.
- [X] T020 [US2] Añadir en `src/proyecto_modelos_lenguaje/brand.py` la media query de `<=640 px` con una columna y ancho completo de tarjetas.
- [X] T021 [US2] Ejecutar la auditoría en 360×640, 390×844, 768×1024 y 1024×768, guardar `artifacts/metrics-layout/us2/` y corregir en `brand.py`/`app.py` el scroll horizontal o la compresión de etiquetas.

**Punto de control**: tableta y móvil aprobados; escritorio sigue aprobado.

---

## Fase 5: Historia de Usuario 3 — Legibilidad con zoom y datos incompletos (Prioridad: P3)

**Objetivo**: valores largos, zoom 200 % y estados `incomplete`/`unknown` siguen siendo legibles y no se superponen.

**Prueba independiente**: auditar el perfil de zoom 200 %, valores de siete o más dígitos y los tres estados de datos con la app de fixture.

### Pruebas de la Historia 3

- [X] T022 [P] [US3] Añadir pruebas unitarias en `tests/unit/test_metrics_layout.py` para valores de siete o más dígitos y reglas CSS que prohíben `text-overflow: ellipsis` en valores y etiquetas.
- [X] T023 [P] [US3] Añadir pruebas `AppTest` en `tests/integration/test_app_pages.py` para los estados `incomplete` y `unknown`: aviso visible, separado de la cuadrícula y sin alterar las ocho tarjetas.
- [X] T024 [P] [US3] Añadir prueba visual en `tests/visual/test_metrics_layout_audit.py` para `zoom-200` y los estados de datos; debe omitirse sin navegador.

### Implementación de la Historia 3

- [X] T025 [US3] Añadir en `src/proyecto_modelos_lenguaje/brand.py` reglas de `white-space: normal`, `overflow-wrap: anywhere`, `min-width: 0` y cifras tabulares para `stMetricLabel` y `stMetricValue`.
- [X] T026 [US3] Añadir en `src/proyecto_modelos_lenguaje/brand.py` altura mínima de 260 px para gráficos y separación de captions, sin modificar los datos de los gráficos.
- [X] T027 [US3] Crear `tests/visual/metrics_fixture_app.py` que lea `PML_METRICS_STATE` (`complete`, `incomplete`, `unknown`) y renderice `render_metrics` y `_data_warning` con `sample_metrics`.
- [X] T028 [US3] Añadir el perfil `zoom-200` y el viewport efectivo 683×384 con `deviceScaleFactor=2` en `src/proyecto_modelos_lenguaje/metrics_layout.py` y `scripts/audit_metrics_layout.py`.
- [X] T029 [US3] Ejecutar la auditoría de zoom y estados, guardar `artifacts/metrics-layout/us3/` y corregir en `brand.py`/`app.py` cualquier recorte, solapamiento o aviso mal posicionado.

**Punto de control**: zoom y estados aprobados; las tres historias funcionan juntas.

---

## Fase 6: Pulido y aspectos transversales

**Propósito**: documentación, lint, pruebas completas, evidencia final y publicación.

- [X] T030 Actualizar `specs/010-metrics-panel-layout/quickstart.md` con los comandos definitivos, la matriz de resultados y las rutas de evidencia.
- [X] T031 Actualizar `README.md` con el comando de auditoría visual y el estado de la verificación, sin inventar capturas.
- [X] T032 Verificar que `artifacts/metrics-layout/` está ignorado y que no se añaden binarios, rutas absolutas ni secretos a Git.
- [X] T033 Ejecutar `uv run ruff check .` y corregir hallazgos en `app.py`, `src/proyecto_modelos_lenguaje/brand.py`, `src/proyecto_modelos_lenguaje/metrics_layout.py`, `scripts/audit_metrics_layout.py` y `tests/`.
- [X] T034 Ejecutar `uv run pytest -q` y corregir fallos en `tests/unit/test_metrics_layout.py`, `tests/contract/test_metrics_layout_contract.py`, `tests/integration/test_app_pages.py` y `tests/visual/test_metrics_layout_audit.py`.
- [X] T035 Ejecutar la auditoría final de los siete perfiles y los tres estados, guardar `artifacts/metrics-layout/final/report.json` y confirmar `passed: true`.
- [X] T036 Regenerar la bitácora con `uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py` y confirmar que el avance refleja la verificación.
- [X] T037 Crear una rama `010-metrics-panel-layout`, commit atómico y PR que incluya `specs/010-metrics-panel-layout/` y la evidencia de la auditoría; no fusionar hasta que CI esté verde.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; puede empezar de inmediato.
- **Fundamentos (Fase 2)**: depende de Fase 1; bloquea todas las historias.
- **US1 Escritorio (Fase 3)**: depende de Fase 2; entrega el MVP.
- **US2 Ventanas estrechas (Fase 4)**: depende de Fase 2 y de la cuadrícula base de US1.
- **US3 Zoom y estados (Fase 5)**: depende de Fase 2 y de US1/US2 para reutilizar la cuadrícula y la auditoría.
- **Pulido (Fase 6)**: depende de US1–US3.

### Dependencias entre historias

- **US1 (P1)**: no depende de otras historias; entrega el MVP de escritorio.
- **US2 (P2)**: requiere la cuadrícula base de US1; se prueba sola en ventanas estrechas.
- **US3 (P3)**: requiere US1/US2; añade tipografía robusta, zoom y estados.

### Dentro de cada historia

1. Pruebas primero; deben fallar antes de la implementación.
2. Constantes y contenedor antes de las reglas visuales.
3. Cuadrícula antes de espaciado y tipografía.
4. Auditoría antes de declarar la historia terminada.
5. Cada historia debe dejar Ruff y pytest en verde.

### Oportunidades de paralelización

- T003–T004 pueden ejecutarse en paralelo (script y pruebas unitarias).
- T006–T007 pueden ejecutarse en paralelo (contrato y contenedor en archivos distintos).
- T016–T018 pueden ejecutarse en paralelo (pruebas en archivos distintos).
- T022–T024 pueden ejecutarse en paralelo (pruebas en archivos distintos).
- Las implementaciones de US1–US3 comparten `brand.py`; ejecutar secuencialmente.
- T030–T032 pueden ejecutarse en paralelo (documentación y verificación de artefactos).

---

## Ejemplo de paralelización: Fundamentos

```text
Tarea: T004 Pruebas unitarias de metrics_layout.py en tests/unit/test_metrics_layout.py
Tarea: T006 Pruebas de contrato CSS/DOM en tests/contract/test_metrics_layout_contract.py
Tarea: T007 Contenedor de KPI en app.py
```

## Ejemplo de paralelización: US2

```text
Tarea: T016 Prueba de columnas esperadas en tests/unit/test_metrics_layout.py
Tarea: T017 Prueba de media queries en tests/contract/test_metrics_layout_contract.py
Tarea: T018 Prueba visual de perfiles estrechos en tests/visual/test_metrics_layout_audit.py
```

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1: Preparación.
2. Completar Fase 2: Fundamentos.
3. Completar Fase 3: US1 Escritorio.
4. Ejecutar la auditoría de 1440×900 y 1920×1080.
5. Detenerse y validar el MVP antes de US2–US3.

### Entrega incremental

1. Preparación + Fundamentos → constantes, contenedor y auditoría.
2. US1 → escritorio sin solapamientos (MVP).
3. US2 → tableta y móvil con 2/1 columnas.
4. US3 → valores largos, zoom y estados de datos.
5. Pulido → documentación, evidencia final y PR.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 escritorio y US3 zoom/estados.
3. Roberto: US2 ventanas estrechas y revisión de la matriz.
4. Integrar en orden US1 → US2 → US3 y validar cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- Los artefactos de auditoría viven en `artifacts/metrics-layout/` y no se versionan.
- La app sigue siendo de solo lectura; no se escribe en `data/`.
- No se inventan capturas ni resultados: la evidencia se genera al ejecutar la app y la auditoría.
- La verificación visual se omite en CI si Playwright o el navegador no están disponibles.
- Este feature no cambia cálculos, datos, prompts ni la identidad visual.
