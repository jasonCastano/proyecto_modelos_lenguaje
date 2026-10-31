# Data Model — Verificación del panel de Métricas

**Feature**: `010-metrics-panel-layout`
**Fecha**: 2026-10-31

Este modelo describe las entidades de verificación y presentación. No introduce almacenamiento nuevo ni modifica las métricas del corpus.

## Entidades

### `MetricCard`

Una tarjeta de indicador dentro de la pestaña **Métricas**.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `id` | string | sí | Identificador estable; por ejemplo `documentos`, `fragmentos`, `unidades`. |
| `label` | string | sí | Etiqueta visible en español. |
| `value` | number \| string | sí | Valor original de la métrica. |
| `formatted_value` | string | sí | Representación visible con separador de miles y sin truncar. |
| `help` | string \| null | no | Texto de ayuda accesible. |
| `section` | enum | sí | `indicadores`, `volumen` o `tokens`. |
| `numeric` | boolean | sí | Indica si el valor es numérico. |

**Reglas de validación**:

- Deben existir exactamente ocho tarjetas en la pestaña: documentos, fragmentos, unidades, hechos, cobertura, conflictos, tokens de plata y tokens de oro.
- `formatted_value` no puede contener puntos suspensivos ni caracteres de truncamiento.
- Los valores de siete o más dígitos deben conservarse completos.
- `label` y `help` no pueden estar vacíos cuando `help` se muestra.

**Relaciones**:

- Cada `MetricCard` pertenece a una `MetricsSection`.
- Las tarjetas de `indicadores` forman la cuadrícula adaptable.

### `MetricsSection`

Agrupación visual de la pestaña.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `id` | string | sí | `indicadores`, `volumen`, `tokens` o `arquitectura`. |
| `title` | string | sí | Título visible. |
| `order` | integer | sí | Orden de lectura, de 1 a 4. |
| `elements` | array | sí | Tarjetas, gráficos, captions o expanders que contiene. |

**Reglas de validación**:

- El orden es `indicadores` → `volumen` → `tokens` → `arquitectura`.
- `volumen` contiene un gráfico; `tokens` contiene un gráfico; `arquitectura` contiene tres expanders.
- Ninguna sección puede superponerse con la siguiente.

### `ViewportProfile`

Combinación de tamaño y zoom usada en la auditoría.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `name` | string | sí | Nombre legible del perfil. |
| `width` | integer | sí | Ancho CSS en píxeles. |
| `height` | integer | sí | Alto CSS en píxeles. |
| `zoom` | number | sí | Zoom nominal: 1.0 o 2.0. |
| `expected_columns` | integer | sí | Columnas esperadas en la cuadrícula de indicadores. |
| `sidebar_open` | boolean | sí | Estado de la barra lateral. |

**Perfiles canónicos**:

| `name` | `width` | `height` | `zoom` | `expected_columns` | `sidebar_open` |
|--------|---------|----------|--------|--------------------|----------------|
| móvil-pequeño | 360 | 640 | 1.0 | 1 | false |
| móvil | 390 | 844 | 1.0 | 1 | false |
| tableta-vertical | 768 | 1024 | 1.0 | 2 | true |
| tableta-horizontal | 1024 | 768 | 1.0 | 2 | true |
| escritorio | 1440 | 900 | 1.0 | 4 | true |
| escritorio-amplio | 1920 | 1080 | 1.0 | 4 | true |
| zoom-200 | 683 | 384 | 2.0 | 2 | true |

**Reglas de validación**:

- `expected_columns` debe corresponder a los puntos de corte: 4 si `width >= 1200`, 2 si `641 <= width < 1200`, 1 si `width <= 640`.
- El perfil de zoom usa un viewport efectivo reducido y `deviceScaleFactor=2`; se documenta como aproximación de layout.

### `LayoutFinding`

Hallazgo de la auditoría.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `viewport` | string | sí | Nombre del `ViewportProfile`. |
| `kind` | enum | sí | `overlap`, `horizontal_scroll`, `clipping`, `missing_element` o `wrong_columns`. |
| `element_a` | string | sí | Selector o etiqueta del primer elemento. |
| `element_b` | string \| null | no | Segundo elemento en un solapamiento. |
| `area` | number \| null | no | Área de intersección en píxeles cuadrados. |
| `detail` | string | sí | Descripción legible del hallazgo. |
| `severity` | enum | sí | `error` o `warning`. |

**Reglas de validación**:

- Un `overlap` con `area > 0` es siempre `error`.
- Un `horizontal_scroll` es `error` en cualquier perfil.
- Un `clipping` de un valor numérico es `error`; de una etiqueta es `warning` si el texto sigue siendo legible.
- Un `wrong_columns` es `error` si difiere de `expected_columns`.
- `missing_element` es `error` cuando falta una tarjeta, gráfico o expander obligatorio.

### `AuditReport`

Resultado serializable de una ejecución.

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `schema_version` | string | sí | Versión del contrato; `1.0`. |
| `generated_at` | string (date-time) | sí | Fecha y hora UTC. |
| `app_url` | string | sí | URL auditada, sin credenciales. |
| `browser` | string | sí | Navegador y versión. |
| `viewports` | array de `ViewportResult` | sí | Resultados por perfil. |
| `data_states` | array de `DataStateResult` | sí | Resultados por estado de datos. |
| `findings` | array de `LayoutFinding` | sí | Hallazgos consolidados. |
| `passed` | boolean | sí | `true` solo si no hay hallazgos `error`. |

### `ViewportResult`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `name` | string | sí | Nombre del perfil. |
| `width` | integer | sí | Ancho aplicado. |
| `height` | integer | sí | Alto aplicado. |
| `zoom` | number | sí | Zoom nominal. |
| `columns` | integer | sí | Columnas detectadas. |
| `horizontal_scroll` | boolean | sí | Desbordamiento horizontal del documento. |
| `screenshots` | array de string | sí | Rutas relativas de las capturas. |
| `passed` | boolean | sí | Resultado del perfil. |

### `DataStateResult`

| Campo | Tipo | Obligatorio | Descripción |
|-------|------|-------------|-------------|
| `state` | enum | sí | `complete`, `incomplete` o `unknown`. |
| `warning_visible` | boolean | sí | Aviso de datos visible. |
| `warning_separate` | boolean | sí | El aviso no se superpone con la cuadrícula. |
| `passed` | boolean | sí | Resultado del estado. |

## Transiciones de estado

### Estado de datos

```text
complete  ──(archivo faltante / puntero LFS)──> incomplete
complete  ──(catálogo ilegible)────────────────> unknown
incomplete/unknown ──(git lfs pull / datos restaurados)──> complete
```

- En `complete`, el aviso no se muestra.
- En `incomplete` y `unknown`, el aviso aparece antes de las pestañas y fuera de la cuadrícula de KPI.
- La cuadrícula debe conservar su orden y legibilidad en los tres estados.

### Estado de layout

```text
sin_auditar ──(auditoría inicia)──> auditando
auditando ──(sin hallazgos error)──> aprobado
auditando ──(hallazgo error)───────> rechazado
rechazado ──(ajuste aplicado)──────> auditando
```

## Invariantes

1. Los valores y cálculos de `AppMetrics` no cambian.
2. La app no escribe en `data/` ni en el repositorio.
3. La cuadrícula no introduce desplazamiento horizontal desde 360 px.
4. Las tarjetas conservan etiquetas y valores completos.
5. El orden de lectura es indicadores → volumen → tokens → arquitectura.
6. El aviso de datos incompletos nunca forma parte de la cuadrícula de KPI.
7. La identidad visual y los contrastes aprobados se mantienen.
