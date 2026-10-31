# Research — Verificación y ajuste del panel de Métricas

**Feature**: `010-metrics-panel-layout`
**Fecha**: 2026-10-31
**Alcance**: presentación de la pestaña **Métricas**; no se investigan cambios de datos ni de modelo.

## Contexto y línea base

La implementación actual de `render_metrics` en `app.py` usa dos filas de `st.columns(4)` para las ocho tarjetas, seguido de dos `st.bar_chart`, captions y tres `st.expander`. `st.columns` de Streamlit 1.66 apila columnas solo cuando el viewport mide 640 px o menos; entre 641 y 1199 px mantiene cuatro columnas, por lo que el contenido puede comprimirse aunque no llegue a solaparse. La identidad visual vive en `brand.py`, que ya inyecta CSS mediante `st.html` sin `unsafe_allow_html`.

La auditoría visual real se ejecutará en implementación; esta fase no declara hallazgos observados que aún no se hayan medido.

## Decisiones

### D1 — Cuadrícula adaptable con CSS y clave de contenedor

**Decisión**: envolver las dos filas de KPI en `st.container(key="metrics-kpis")` y aplicar una cuadrícula CSS con puntos de corte explícitos:

- `>=1200 px`: 4 columnas.
- `641–1199 px`: 2 columnas.
- `<=640 px`: 1 columna.

La regla se limita al contenedor `.st-key-metrics-kpis` para no afectar otras pestañas.

**Rationale**: Streamlit expone la clave como clase `st-key-<key>` y permite mantener `st.metric` (semántica, help y accesibilidad) sin introducir un componente nuevo. Los puntos de corte cubren la matriz de la especificación y el apilado nativo de 640 px.

**Alternativas consideradas**:

| Alternativa | Motivo para rechazarla |
|-------------|------------------------|
| Dejar `st.columns(4)` con el apilado nativo | A 1024 px y 768 px mantiene cuatro columnas y no cumple FR-002. |
| `st.columns(4, wrap=False)` | Mantiene una fila y añade desplazamiento horizontal; viola FR-006. |
| Contenedor horizontal con tarjetas de ancho fijo | El ancho depende del contenido y no garantiza 4/2/1 exactos. |
| Componente JavaScript a medida | Añade dependencia, complejidad y superficie de fallo; YAGNI. |
| Ancho del servidor o detección de viewport | Streamlit no expone el ancho del navegador al script; requeriría un componente. |

### D2 — Puntos de corte 1200/640

**Decisión**: usar 1200 px para pasar de 4 a 2 columnas y 640 px para pasar a 1.

**Rationale**: A 1024 px con barra lateral abierta el área útil ronda 700–800 px; dos columnas de ~350 px permiten leer cifras de siete dígitos. A 1440 px y 1920 px caben cuatro tarjetas cómodas. 640 px coincide con el comportamiento nativo de Streamlit y con el límite de móvil de la especificación.

**Alternativas consideradas**: 1024/768 (demasiado pronto para 2 columnas en escritorio), 1440/1024 (mantiene cuatro columnas en 1280 y 1024, incumpliendo el escenario de tableta).

### D3 — Valores y etiquetas que envuelven, nunca se truncan

**Decisión**: permitir `white-space: normal`, `overflow-wrap: anywhere`, `min-width: 0` y cifras tabulares en los valores; no usar `text-overflow: ellipsis` en `stMetricValue` ni `stMetricLabel`.

**Rationale**: Los valores reales incluyen 1.447.841 tokens y los identificadores de ejecución son largos. Envolver conserva la información; truncar viola FR-003 y SC-005.

**Alternativas consideradas**: reducir la fuente con `clamp()` (puede volverse ilegible), truncar con puntos suspensivos (oculta cifras), abreviar a “1,4 M” (pierde precisión y exige otra regla de formato).

### D4 — Gráficos con altura mínima y separación explícita

**Decisión**: mantener `st.bar_chart` y aplicar una altura mínima al contenedor del gráfico, con separación antes y después de títulos, leyendas y captions.

**Rationale**: Los gráficos nativos son responsivos en ancho; el riesgo está en alturas colapsadas y textos pegados. Una altura mínima evita que el gráfico se comprima y que la leyenda invada el caption.

**Alternativas consideradas**: fijar altura en píxeles (falla con zoom), sustituir por una librería de gráficos (dependencia nueva), eliminar gráficos (pierde valor de la pestaña).

### D5 — Verificación geométrica con Playwright

**Decisión**: crear `scripts/audit_metrics_layout.py` con Playwright para recorrer los seis perfiles, medir cajas delimitadoras, detectar intersecciones entre elementos hermanos, comprobar desbordamiento horizontal y recortes, y guardar un reporte JSON más capturas.

**Rationale**: `AppTest` valida estructura y textos, pero no calcula geometría ni CSS. Playwright usa un navegador real y permite repetir la matriz sin depender de revisión ocular.

**Alternativas consideradas**:

| Alternativa | Motivo para rechazarla |
|-------------|------------------------|
| Solo revisión manual | No es repetible ni medible; SC-001/SC-002 quedarían sin evidencia objetiva. |
| Solo `AppTest` | No renderiza CSS ni conoce posiciones. |
| Comparación de capturas pixel a pixel | Frágil ante fuentes, antialiasing y cambios de contenido; requiere baseline enorme. |
| Selenium | Playwright ya está en el lockfile y tiene mejor API de cajas y viewport. |

### D6 — Playwright como dependencia de desarrollo, no de ejecución

**Decisión**: declarar Playwright en el grupo `dev` y mantenerlo fuera de las dependencias de ejecución. La prueba visual se omite si no hay navegador instalado.

**Rationale**: La app no necesita Playwright para funcionar; la constitución exige justificar dependencias y mantener el runtime simple. La instalación de Chromium requiere red y no debe bloquear CI.

**Alternativas consideradas**: añadirlo a `dependencies` (contamina el runtime), no declararlo y confiar en la dependencia transitiva de `scrapling` (frágil), ejecutarlo siempre en CI (lento y dependiente de red).

### D7 — Estados de datos mediante app de fixture

**Decisión**: usar `tests/visual/metrics_fixture_app.py` para renderizar el panel con estados `complete`, `incomplete` y `unknown` sin alterar los datos reales ni la app principal.

**Rationale**: La app principal lee `PROJECT_ROOT/data`; renombrar archivos para simular estados es peligroso. Una app mínima reutiliza `sample_metrics` y `_data_warning` y permite auditar los tres estados con el mismo script.

**Alternativas consideradas**: modificar datos en disco (riesgoso), añadir una variable de entorno de test a la app principal (complejidad innecesaria), omitir estados incompletos (incumple FR-013).

### D8 — Artefactos de auditoría fuera de Git

**Decisión**: guardar reportes y capturas en `artifacts/metrics-layout/`, añadir esa ruta a `.gitignore` y validar el JSON contra `contracts/layout-audit.schema.json`.

**Rationale**: Las capturas son evidencia local y pueden variar por fuente/sistema; no deben inflar el repositorio ni confundirse con documentación curada. El JSON permite adjuntar resultados sin versionar binarios.

**Alternativas consideradas**: commitear capturas (peso y ruido), no guardar evidencia (pierde trazabilidad), guardar solo texto (no permite revisar visualmente).

### D9 — Zoom extremo mediante viewport efectivo

**Decisión**: emular 200 % de zoom con un viewport efectivo de 683×384 (la mitad de 1366×768) y `deviceScaleFactor=2`; documentar que es una aproximación de layout, no una prueba de rasterizado.

**Rationale**: El zoom del navegador reduce el espacio CSS disponible; duplicar la densidad de píxeles sin cambiar el layout no reproduce el efecto. La combinación elegida estresa el reflujo y la legibilidad.

**Alternativas consideradas**: `page.evaluate("document.body.style.zoom='200%'")` (no es el zoom real del navegador y puede falsear cajas), `Emulation.setPageScaleFactor` (escala visual, no layout), prueba manual (no repetible).

## Incógnitas resueltas

| Incógnita | Resolución |
|-----------|------------|
| ¿Streamlit permite apilar columnas? | Sí, `st.columns` apila a ≤640 px; no alcanza para 2 columnas a 1024 px, por eso se añade CSS. |
| ¿Cómo limitar el CSS a Métricas? | `st.container(key="metrics-kpis")` genera `.st-key-metrics-kpis`; las reglas se anidan ahí. |
| ¿Cómo verificar solapamientos? | Playwright + `bounding_box()` y comparación de intersecciones entre hermanos. |
| ¿Cómo verificar zoom? | Viewport efectivo reducido + `deviceScaleFactor=2`, documentado como aproximación. |
| ¿Cómo probar datos incompletos sin tocar datos? | App de fixture con `sample_metrics` y `_data_warning`. |
| ¿Playwright en CI? | No por defecto; prueba visual opcional que se omite sin navegador. |

## Referencias

- Streamlit, `st.columns` — `wrap` apila columnas a ≤640 px: https://docs.streamlit.io/develop/api-reference/layout/st.columns
- Streamlit, `st.container` — `key` como clase CSS y layout horizontal: https://docs.streamlit.io/develop/api-reference/layout/st.container
- Playwright Python, `bounding_box` y viewport: https://playwright.dev/python/docs/api/class-locator#locator-bounding-box
- WCAG 2.2, reflujo y contraste: https://www.w3.org/WAI/WCAG22/Understanding/reflow.html
