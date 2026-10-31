# Quickstart — Verificación del panel de Métricas

**Feature**: `010-metrics-panel-layout`
**Fecha**: 2026-10-31

Guía para validar que la pestaña **Métricas** se ve correctamente en escritorio, tableta, móvil, zoom extremo y estados de datos incompletos.

## 1. Requisitos

```bash
uv sync
git lfs install
git lfs pull
```

- Datos de oro materializados para el estado `complete`.
- Navegador actual (Chrome, Edge o Firefox).
- Para la auditoría automatizada:

```bash
uv run playwright install chromium
```

La app funciona sin Playwright; la herramienta solo se usa para verificación visual.

## 2. Pruebas estructurales

```bash
uv run ruff check .
uv run pytest tests/unit/test_metrics_layout.py \
  tests/contract/test_metrics_layout_contract.py \
  tests/integration/test_app_pages.py -q
```

Resultado esperado:

- Ocho tarjetas de indicadores, dos gráficos y tres expanders.
- Contrato CSS/DOM con puntos de corte 1200/640.
- Aviso de datos incompletos separado de la cuadrícula.
- Sin regresiones en las demás pestañas.

## 3. Arranque de la app

```bash
uv run streamlit run app.py --server.headless true --server.port 8501
```

Abrir `http://localhost:8501` y seleccionar **Métricas**.

Para el modo demostración sin Ollama:

```powershell
$env:PML_DEMO="1"
uv run streamlit run app.py --server.headless true --server.port 8501
```

## 4. Matriz de verificación

| Perfil | Ventana | Zoom | Columnas esperadas | Barra lateral |
|--------|---------|------|--------------------|---------------|
| Móvil pequeño | 360×640 | 100 % | 1 | Cerrada |
| Móvil | 390×844 | 100 % | 1 | Cerrada |
| Tableta vertical | 768×1024 | 100 % | 2 | Abierta |
| Tableta horizontal | 1024×768 | 100 % | 2 | Abierta |
| Escritorio | 1440×900 | 100 % | 4 | Abierta |
| Escritorio amplio | 1920×1080 | 100 % | 4 | Abierta |
| Zoom 200 % | 683×384 efectivos | 200 % | 2 | Abierta |

En cada perfil comprobar:

1. Las ocho tarjetas se leen completas.
2. Ninguna etiqueta o valor invade una tarjeta vecina.
3. Los títulos, gráficos, leyendas y captions mantienen separación.
4. No aparece desplazamiento horizontal.
5. Los tres expanders se abren y su texto no se solapa.
6. La barra lateral no tapa el contenido.

## 5. Auditoría automatizada

Con la app corriendo:

```bash
uv run python scripts/audit_metrics_layout.py \
  --url http://localhost:8501 \
  --output artifacts/metrics-layout
```

El script:

- Recorre los siete perfiles de la matriz.
- Mide cajas delimitadoras y detecta intersecciones entre elementos hermanos.
- Comprueba desbordamiento horizontal y recortes de texto.
- Genera capturas de página completa.
- Escribe `report.json` conforme a `contracts/layout-audit.schema.json`.

Resultado esperado: `passed: true` y cero hallazgos con severidad `error`.

Los artefactos quedan en `artifacts/metrics-layout/` y no se versionan en Git.

## 6. Estados de datos

Para validar `incomplete` y `unknown` sin tocar los datos reales, usar la app de fixture:

```powershell
$env:PML_METRICS_STATE="incomplete"
uv run streamlit run tests/visual/metrics_fixture_app.py --server.headless true --server.port 8502
```

Repetir con `$env:PML_METRICS_STATE="unknown"` y luego con `"complete"`.

Resultado esperado:

- `complete`: no hay aviso.
- `incomplete` y `unknown`: aviso visible antes de las pestañas, fuera de la cuadrícula.
- La cuadrícula conserva el orden y no se superpone con el aviso.

También se puede auditar el fixture con el mismo script:

```bash
uv run python scripts/audit_metrics_layout.py \
  --url http://localhost:8502 \
  --output artifacts/metrics-layout/incomplete
```

## 7. Revisión manual rápida

Si no se dispone de Playwright:

1. Abrir DevTools del navegador.
2. Activar el modo responsive y probar 360, 390, 768, 1024, 1440 y 1920 px.
3. Aplicar zoom de 200 % en 1366×768.
4. Revisar que no haya scroll horizontal: `document.documentElement.scrollWidth <= document.documentElement.clientWidth`.
5. Abrir y cerrar la barra lateral en 1024 px.
6. Revisar los tres expanders.
7. Anotar cualquier solapamiento con perfil, elemento y captura.

## 8. Criterios de aceptación

| Escenario | Criterio |
|-----------|----------|
| Escritorio | 4 columnas en 1440 y 1920 px, sin solapamientos |
| Tableta | 2 columnas en 768 y 1024 px |
| Móvil | 1 columna en 360 y 390 px |
| Zoom 200 % | Contenido legible, sin solapamientos, con scroll vertical |
| Valores largos | Cifras completas, sin puntos suspensivos |
| Datos incompletos | Aviso separado y visible |
| Gráficos | Altura mínima y captions separados |
| Otras pestañas | Sin regresiones visuales |

## 9. Solución de problemas

| Problema | Causa probable | Acción |
|----------|----------------|--------|
| `playwright` no encuentra el navegador | Chromium no instalado | `uv run playwright install chromium` |
| La auditoría no conecta | La app no está corriendo o usa otro puerto | Verificar `--url` y el puerto de Streamlit |
| Faltan datos de oro | LFS no materializado | `git lfs pull` y recargar |
| El fixture no cambia de estado | Variable de entorno no aplicada | Reiniciar Streamlit con `PML_METRICS_STATE` |
| Aparece scroll horizontal | Regla CSS no aplicada o contenido más ancho | Revisar el perfil y el reporte de auditoría |

## 10. Evidencias

- `artifacts/metrics-layout/final/report.json`: resultado estructurado de los siete perfiles.
- `artifacts/metrics-layout/final/<perfil>.png`: captura por perfil.
- `artifacts/metrics-layout/final-state-complete/report.json`: estado completo.
- `artifacts/metrics-layout/final-state-incomplete/report.json`: estado incompleto.
- `artifacts/metrics-layout/final-state-unknown/report.json`: estado desconocido.
- Salida de `pytest`: pruebas estructurales y de contrato.
- Salida de `ruff check .`: lint.

No se inventan capturas ni resultados: las evidencias se generan al ejecutar la app y la auditoría en el entorno local.

## 11. Resultados de la validación

**Fecha**: 2026-10-31 · **Navegador**: Chrome · **Datos**: oro completo por LFS.

| Perfil | Ancho×alto | Columnas observadas | Scroll horizontal | Resultado |
|--------|------------|---------------------|-------------------|-----------|
| móvil-pequeño | 360×640 | 1 | No | ✅ |
| móvil | 390×844 | 1 | No | ✅ |
| tableta-vertical | 768×1024 | 2 | No | ✅ |
| tableta-horizontal | 1024×768 | 2 | No | ✅ |
| escritorio | 1440×900 | 4 | No | ✅ |
| escritorio-amplio | 1920×1080 | 4 | No | ✅ |
| zoom-200 | 683×384 efectivos | 2 | No | ✅ |

- **Solapamientos**: 0.
- **Recortes de valores**: 0.
- **Aviso de datos incompletos**: visible y separado en `incomplete` y `unknown`; ausente en `complete`.
- **Iconos Material**: el botón de barra lateral conserva su icono (`>>`) en móvil y zoom.
- **Pruebas**: `346 passed, 9 skipped` (las 7 pruebas visuales se omiten sin `PML_VISUAL_AUDIT=1`).
