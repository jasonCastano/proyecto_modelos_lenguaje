# Contrato de interfaz — identidad visual Manuelita

**Feature**: `009-manuelita-visual-identity`
**Versión**: 1.0
**Fecha**: 2026-10-30

## 1. Zonas de la app

La app tiene una sola pantalla con cinco zonas. Todas comparten la misma identidad.

| Zona | Contenido obligatorio | Clase CSS |
|------|-----------------------|-----------|
| `header` | Firma «Grupo Manuelita · Ingenio Manuelita», nombre del proyecto y lema corto | `pml-header` |
| `status_bar` | Tres indicadores: datos, modelo, modo demo; cada uno con icono y etiqueta | `pml-status` |
| `tabs` | Resumen, FAQ, Q&A (heredadas de la spec 008) | nativa de Streamlit |
| `content` | Respuestas, resumen, FAQ, panel | `pml-card`, `pml-source`, `pml-badge` |
| `footer` | Atribución de la marca y aviso de proyecto académico no afiliado | `pml-footer` |

## 2. Cabecera

```text
Grupo Manuelita · Ingenio Manuelita        [● Datos OK] [● Modelo listo] [● Modo demo]
RAG Ingenio Manuelita — Módulo 1
Cultivamos cosas buenas que generan progreso y bienestar
```

- La firma MUST usar la paleta institucional (verde bosque como color de texto/fondo principal).
- El nombre del proyecto MUST ser visible sin desplazarse.
- Los indicadores MUST incluir icono + etiqueta; el color es refuerzo, no el mensaje.

## 3. Tarjeta de fuente

```text
┌──────────────────────────────────────────────────────────────┐
│ [U1]  Manuelita — Productos                                  │
│       sección: Productos > Azúcar · p. 3                     │
│       https://www.manuelita.com/manuelita-productos  ↗      │
└──────────────────────────────────────────────────────────────┘
```

- `[U#]` MUST ir en el color de acento y con peso 600.
- El título MUST ser el del documento; la ubicación MUST declararse o decir «sin sección declarada».
- El enlace MUST ser clicable, con foco visible y apertura en pestaña nueva.

## 4. Badges de estado

| Variante | Color | Icono | Etiqueta |
|----------|-------|-------|----------|
| `ok` | success | ✓ | Correcta |
| `ready` | success | ✓ | Lista |
| `review` | warning | ! | Revisar |
| `fallback` | info | i | Sin evidencia |
| `error` | danger | × | Error |
| `demo` | orange | ● | Modo demo |

- Ningún badge MUST depender solo del color.
- El texto del badge MUST ser legible sobre su color de fondo (≥4.5:1).

## 5. Pie de página

```text
Proyecto académico de la Maestría en IA y Ciencia de Datos (UAO). No afiliado a Grupo Manuelita.
Marca y contenidos de Grupo Manuelita pertenecen a sus titulares; se usan con fines académicos.
```

## 6. Reglas transversales

1. Ningún recurso remoto: sin `@font-face`, `<img>` externo ni CDN.
2. Sin `unsafe_allow_html` en `app.py`; los estilos se inyectan con `st.html` desde `brand.py`.
3. Sin rutas absolutas ni secretos en el CSS ni en los textos.
4. El CSS se inyecta una sola vez por sesión.
5. El ancho mínimo soportado es 360 px sin scroll horizontal.
6. La identidad no altera el texto de las respuestas ni las citas.

## 7. Estados y errores

| Situación | Presentación |
|-----------|--------------|
| Sin evidencia | Badge `fallback` + mensaje informativo (no rojo) |
| Resultado con cita inválida | Badge `review` + nota de revisión |
| Modelo caído o timeout | Badge `error` + mensaje accionable + reintento |
| Datos no materializados | Indicador de datos + instrucción `git lfs pull` |
| Modo demo activo | Badge `demo` persistente en la barra de estado |

## 8. Fuera de contrato

- Nuevas pestañas o funciones.
- Tema oscuro dedicado.
- Cambios en el modelo, los prompts o los datos.
- Internacionalización.
