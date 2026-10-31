# Implementation Plan: Verificación y ajuste del panel de Métricas

**Branch**: `010-metrics-panel-layout` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-metrics-panel-layout/spec.md`

## Summary

Asegurar que la pestaña **Métricas** de la app Streamlit sea legible y no presente solapamientos en escritorio, tableta, móvil, zoom extremo y estados de datos incompletos. La solución combina una cuadrícula adaptable con puntos de corte explícitos, tipografía que envuelve valores largos, gráficos con altura mínima y una auditoría visual reproducible con Playwright que mide intersecciones, desbordamiento horizontal y recortes de texto.

El alcance es de presentación: no se cambian cálculos, datos ni la identidad visual. La app sigue siendo de solo lectura y sin dependencias nuevas de ejecución; Playwright se usa únicamente como herramienta de desarrollo y verificación.

## Technical Context

**Language/Version**: Python 3.14

**Primary Dependencies**: Streamlit 1.66.1, módulos existentes `app.py`, `src/proyecto_modelos_lenguaje/brand.py` y `src/proyecto_modelos_lenguaje/app_metrics.py`; Playwright 1.64.1 solo como dependencia de desarrollo para la auditoría visual.

**Storage**: Sin almacenamiento nuevo. Lectura de reportes y datos de oro por LFS; artefactos de auditoría en `artifacts/metrics-layout/` (ignorados por Git).

**Testing**: `pytest`, `streamlit.testing.v1.AppTest` para estructura y estados, pruebas de contrato CSS/DOM, y auditoría Playwright local para geometría real del navegador.

**Target Platform**: Navegadores actuales de escritorio y móvil (Chrome, Edge, Firefox) sobre la app Streamlit local.

**Project Type**: Aplicación web de un solo proyecto con paquete `src/`.

**Performance Goals**: La app debe seguir cargando en menos de 15 s; la auditoría de seis tamaños de ventana debe completarse en menos de 10 minutos; ninguna vista debe requerir desplazamiento horizontal desde 360 px.

**Constraints**: Sin dependencias nuevas de ejecución; sin JavaScript inyectado en producción; sin `unsafe_allow_html`; sin cambios en datos, métricas o prompts; la identidad visual aprobada se conserva; el diseño debe funcionar sin red una vez instalado el navegador de pruebas.

**Scale/Scope**: Una pestaña **Métricas**, ocho tarjetas de indicadores, dos gráficos, tres bloques desplegables, seis tamaños de ventana y tres estados de datos (completo, incompleto, desconocido).

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento | Evidencia del plan |
|-----------|--------------|--------------------|
| I. Reproducibilidad experimental | ✅ | Puntos de corte, matriz de ventanas y script de auditoría versionados; `uv sync --frozen` reconstruye el entorno; la auditoría produce JSON con fecha y parámetros. |
| II. Evaluación con métricas y línea base | ✅ | Criterios medibles: cero solapamientos, cero desbordamiento horizontal, ocho tarjetas legibles, seis ventanas y tres estados; se compara contra la geometría actual antes del ajuste. |
| III. Procedencia y ética de datos | ✅ | No se añaden datos ni fuentes; solo se leen los reportes existentes y no se versionan capturas con información sensible. |
| IV. Experimentos como código versionado | ✅ | El ajuste vive en `app.py`/`brand.py`; la auditoría es un script versionado; no hay pasos manuales no documentados. |
| V. Simplicidad y alcance académico | ✅ | Se resuelve con CSS y la API nativa de Streamlit; Playwright es solo de desarrollo; no se introduce un componente o servicio nuevo. |
| Restricciones técnicas | ✅ | Python 3.14, `src/`, Ruff/pytest, UTF-8, portabilidad Windows/Linux, sin secretos ni rutas absolutas. |
| Flujo y puertas de calidad | ✅ | La implementación comienza después de aprobar plan y tareas; cada cambio deja lint y pruebas en verde. |

**Resultado**: sin violaciones. No se requiere `Complexity Tracking`.

## Project Structure

### Documentation (this feature)

```text
specs/010-metrics-panel-layout/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones técnicas
├── data-model.md        # Fase 1: entidades de verificación
├── quickstart.md        # Fase 1: guía de validación
├── contracts/
│   ├── metrics-layout.md
│   └── layout-audit.schema.json
└── tasks.md             # Fase 2 (/speckit.tasks; no se crea aquí)
```

### Source Code (repository root)

```text
app.py                                      # Contenedor de KPI con clave y render de Métricas
src/proyecto_modelos_lenguaje/
├── app_metrics.py                          # Métricas y formateo existentes (sin cambios de cálculo)
├── brand.py                                # CSS de marca y reglas adaptables del panel
└── metrics_layout.py                       # Constantes de breakpoints, perfiles y columnas esperadas
scripts/
└── audit_metrics_layout.py                 # Auditoría Playwright: geometría, recortes y capturas
tests/
├── app_page_helpers.py                     # Fixtures de métricas para AppTest
├── contract/
│   └── test_metrics_layout_contract.py     # Contrato CSS/DOM y esquema del reporte
├── integration/
│   └── test_app_pages.py                   # Estructura de Métricas y estados
├── unit/
│   └── test_metrics_layout.py              # Puntos de corte, formateo y reglas de layout
└── visual/
    ├── metrics_fixture_app.py              # App mínima para estados completo/incompleto/desconocido
    └── test_metrics_layout_audit.py        # Auditoría opcional; se omite si no hay navegador
```

**Structure Decision**: Se mantiene la estructura de proyecto único existente. El ajuste visual se concentra en `app.py`, `brand.py` y el nuevo módulo de constantes `metrics_layout.py`; la auditoría y las pruebas viven en `scripts/` y `tests/` para no añadir infraestructura de ejecución.

### Re-evaluación post-diseño

Tras generar `research.md`, `data-model.md`, `contracts/` y `quickstart.md`, el diseño sigue cumpliendo la constitución: no hay dependencias nuevas de ejecución, no se tocan datos ni secretos, la verificación es reproducible y el alcance sigue limitado a la pestaña **Métricas**. No aparecen violaciones nuevas ni se requiere `Complexity Tracking`.

## Implementation Strategy

1. **Línea base**: ejecutar la auditoría sobre la app actual y guardar `artifacts/metrics-layout/baseline/report.json` para comparar antes/después.
2. **Contenedor y cuadrícula**: envolver las dos filas de KPI en `st.container(key="metrics-kpis")` y aplicar una cuadrícula CSS con puntos de corte `>=1200 px` (4 columnas), `641–1199 px` (2 columnas) y `<=640 px` (1 columna).
3. **Tipografía robusta**: permitir que etiquetas y valores envuelvan (`white-space: normal`, `overflow-wrap: anywhere`), usar cifras tabulares y evitar `text-overflow: ellipsis` en valores.
4. **Gráficos y secciones**: fijar una altura mínima legible, separar títulos, leyendas y captions, y mantener el orden de lectura actual.
5. **Estados**: conservar el aviso de datos incompletos fuera de la cuadrícula y verificar que no desplace ni tape elementos.
6. **Auditoría**: crear un script Playwright que recorra los seis tamaños, mida intersecciones entre bloques hermanos, detecte desbordamiento horizontal y recortes, y genere JSON + capturas.
7. **Pruebas**: añadir pruebas de contrato CSS/DOM, pruebas de estructura con `AppTest` y una prueba visual opcional que se omita si el navegador no está instalado.
8. **Cierre**: actualizar quickstart, README si cambia el comando de verificación y bitácora; ejecutar Ruff, pytest y la auditoría antes de integrar.

## Verification Strategy

### Matriz de ventanas

| Perfil | Ancho × alto | Zoom | Columnas esperadas | Barra lateral |
|--------|--------------|------|--------------------|---------------|
| Móvil pequeño | 360×640 | 100 % | 1 | Cerrada |
| Móvil | 390×844 | 100 % | 1 | Cerrada |
| Tableta vertical | 768×1024 | 100 % | 2 | Abierta |
| Tableta horizontal | 1024×768 | 100 % | 2 | Abierta |
| Escritorio | 1440×900 | 100 % | 4 | Abierta |
| Escritorio amplio | 1920×1080 | 100 % | 4 | Abierta |
| Zoom extremo | 683×384 efectivos | 200 % | 2 | Abierta |

### Comprobaciones automáticas

- Intersección de cajas delimitadoras entre tarjetas, títulos, gráficos, captions y expanders hermanos: área 0.
- `scrollWidth <= clientWidth + 1` en el documento y en cada tarjeta.
- `scrollWidth/scrollHeight` de etiquetas y valores dentro de su contenedor; sin `text-overflow: ellipsis`.
- Presencia de las ocho tarjetas, dos gráficos y tres expanders.
- Aviso de datos incompletos en un bloque separado.
- Capturas de página completa por perfil y estado.

### Pruebas en CI

- `ruff check .` y `pytest` con pruebas unitarias, de contrato y de integración.
- La prueba visual se omite automáticamente si Playwright o el navegador no están disponibles; no bloquea CI ni requiere red.
- La auditoría completa se ejecuta localmente o en un job opcional antes de la demo.

## Complexity Tracking

> No se identificaron violaciones constitucionales. La solución usa CSS y APIs existentes; Playwright es una herramienta de desarrollo, no una dependencia de ejecución.
