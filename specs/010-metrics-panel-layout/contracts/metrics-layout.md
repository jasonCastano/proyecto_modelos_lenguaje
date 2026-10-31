# UI Contract — Panel de Métricas

**Feature**: `010-metrics-panel-layout`
**Versión**: 1.0
**Fecha**: 2026-10-31

## 1. Alcance

Contrato de presentación para la pestaña **Métricas** de la app Streamlit. Define estructura, puntos de corte, reglas de texto, comportamiento de gráficos y criterios que la auditoría visual debe verificar.

No cubre cambios de datos, cálculos, prompts, identidad visual ni las demás pestañas.

## 2. Estructura obligatoria

La pestaña contiene, en este orden:

1. Título **Métricas del corpus** y caption introductorio.
2. Ocho tarjetas de indicadores:
   - Documentos
   - Fragmentos
   - Unidades
   - Hechos
   - Cobertura
   - Conflictos
   - Tokens plata
   - Tokens oro
3. Título **Volumen del corpus**, gráfico de barras y caption.
4. Título **Tokens por capa**, gráfico de barras y caption con las ejecuciones.
5. Título **Arquitectura medallion**, caption y tres expanders: Bronce, Plata y Oro.

El aviso de datos incompletos, cuando exista, aparece fuera de la pestaña y antes de las pestañas de navegación.

## 3. Contrato DOM

| Elemento | Selector estable | Uso |
|----------|------------------|-----|
| Contenedor de KPI | `.st-key-metrics-kpis` | Limita las reglas de cuadrícula a esta pestaña. |
| Fila de columnas | `.st-key-metrics-kpis [data-testid="stHorizontalBlock"]` | Contenedor de cada fila de tarjetas. |
| Columna | `.st-key-metrics-kpis [data-testid="stColumn"]` | Celda de la cuadrícula. |
| Tarjeta | `[data-testid="stMetric"]` | Tarjeta de indicador. |
| Etiqueta | `[data-testid="stMetricLabel"]` | Etiqueta visible. |
| Valor | `[data-testid="stMetricValue"]` | Valor visible. |
| Gráfico | `[data-testid="stVegaLiteChart"]` | Gráfico de barras. |
| Expander | `[data-testid="stExpander"]` | Bloques de arquitectura. |
| Caption | `[data-testid="stCaptionContainer"]` | Notas y ejecuciones. |

La app no debe depender de clases generadas aleatoriamente por Streamlit. Si un `data-testid` cambia en una actualización, el contrato y las pruebas deben actualizarse juntos.

## 4. Puntos de corte

| Ancho de viewport | Columnas de KPI | Regla |
|-------------------|-----------------|-------|
| `>= 1200 px` | 4 | Cuatro tarjetas por fila. |
| `641–1199 px` | 2 | Dos tarjetas por fila. |
| `<= 640 px` | 1 | Una tarjeta por fila. |

Requisitos:

- La cuadrícula usa `minmax(0, 1fr)` para permitir que las tarjetas se encojan sin desbordar.
- Las columnas tienen `min-width: 0` y `width: auto` para anular el ancho fijo de Streamlit.
- El gap horizontal y vertical es consistente (mínimo 1 rem).
- No se permite desplazamiento horizontal en ningún perfil.

## 5. Reglas de texto

- Los valores numéricos se muestran completos, con separador de miles y sin puntos suspensivos.
- Etiquetas y valores pueden ocupar varias líneas.
- Se prohíbe `text-overflow: ellipsis` en `stMetricValue` y `stMetricLabel`.
- Los valores usan cifras tabulares para evitar saltos de ancho.
- El tamaño de fuente no se reduce por debajo del tamaño de cuerpo de la identidad.
- El texto de ayuda (`help`) sigue disponible y no tapa el valor.

## 6. Gráficos y secciones

- Cada gráfico ocupa el ancho disponible y conserva una altura mínima de 260 px.
- El título, el gráfico, la leyenda y el caption mantienen separación vertical.
- Los captions no se superponen con el gráfico anterior ni con el siguiente bloque.
- Los expanders conservan su título completo y no se comprimen a una sola línea ilegible.

## 7. Estados de datos

| Estado | Aviso | Requisito visual |
|--------|-------|------------------|
| `complete` | No | La cuadrícula y los gráficos se muestran normalmente. |
| `incomplete` | Sí | El aviso aparece antes de las pestañas, separado de la cuadrícula, con acción `git lfs pull`. |
| `unknown` | Sí | El aviso aparece en el mismo bloque separado y no rompe el orden. |

El aviso no puede formar parte de `.st-key-metrics-kpis` ni compartir fila con una tarjeta.

## 8. Accesibilidad

- Cada tarjeta conserva su etiqueta textual; no se usan iconos como único indicador.
- Los encabezados mantienen una jerarquía comprensible.
- El foco visible se conserva en enlaces y botones.
- El contraste de texto y fondo cumple el contrato de marca existente.
- El contenido puede recorrerse con teclado y lector de pantalla en orden de lectura.

## 9. Contrato de auditoría

La auditoría produce un JSON conforme a `layout-audit.schema.json` con:

- Perfiles de la matriz de `data-model.md`.
- Resultado por perfil: columnas detectadas, desplazamiento horizontal, capturas y `passed`.
- Hallazgos con tipo, elementos, área y severidad.
- Resultado por estado de datos.
- `passed` global solo si no hay hallazgos `error`.

Una ejecución se considera aprobada cuando:

1. No hay solapamientos con área mayor que 0 entre elementos hermanos.
2. No hay desplazamiento horizontal en ningún perfil.
3. No hay valores truncados.
4. Las columnas detectadas coinciden con `expected_columns`.
5. Están presentes las ocho tarjetas, dos gráficos y tres expanders.

## 10. No objetivos

- Rediseñar la identidad visual.
- Cambiar las cifras o los cálculos de `AppMetrics`.
- Añadir nuevas pestañas o secciones.
- Implementar un sistema de temas.
- Garantizar compatibilidad con navegadores sin soporte de CSS Grid o media queries.
- Versionar capturas binarias en Git.
