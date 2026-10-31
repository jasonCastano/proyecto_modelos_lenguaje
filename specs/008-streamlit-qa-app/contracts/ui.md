# Contrato de interfaz — App Streamlit del Módulo 1

**Feature**: `008-streamlit-qa-app`
**Versión**: 1.0
**Fecha**: 2026-10-30

## 1. Arranque

```bash
uv run streamlit run app.py
```

La app abre en el navegador local. No requiere claves de API. Si Ollama no está disponible, muestra el
estado y permite activar el modo demostración.

## 2. Layout

```text
┌─────────────────────────────────────────────────────────────┐
│ Encabezado: RAG Ingenio Manuelita — Módulo 1                 │
│ Estado: datos completos | modelo Ollama | modo demostración │
├───────────────────────────────────┬─────────────────────────┤
│ Pestañas: Resumen | FAQ | Q&A     │ Panel lateral           │
│                                   │ - Corpus                │
│ Contenido de la pestaña activa    │ - Cobertura             │
│ Respuesta + citas + fuentes       │ - Tokens / descartes    │
│                                   │ - Modelo / prompt       │
│                                   │ - Última respuesta      │
└───────────────────────────────────┴─────────────────────────┘
```

### 2.1 Pestaña Resumen

- Selector de paquete: `8000` (por defecto) o `32000`.
- Botón **Generar resumen**.
- Estado de carga mientras genera.
- Resultado en Markdown con secciones, citas `[U#]` y lista de fuentes.
- Si no hay evidencia: fallback explícito.
- El resultado se conserva en la sesión.

### 2.2 Pestaña FAQ

- Selector de cantidad: 10–20 (por defecto 12).
- Botón **Generar FAQ**.
- Lista de `st.expander` por pregunta.
- Cada elemento muestra respuesta, citas y estado `ready`, `review` o `missing_evidence`.
- Si no hay evidencia: estado `missing_evidence` y mensaje de fallback.
- El resultado se conserva en la sesión.

### 2.3 Pestaña Q&A

- Campo de pregunta y botón **Preguntar** dentro de un formulario.
- Validación de pregunta vacía o demasiado larga.
- Estado de carga y botón deshabilitado durante la generación.
- Respuesta, citas `[U#]` y lista de fuentes clicables.
- Fallback explícito si no hay evidencia.
- Botón **Reintentar** si hay error.

### 2.4 Panel lateral

Métricas del corpus:

- Artefactos activos.
- Documentos canónicos.
- Alias.
- Fragmentos.
- Unidades.
- Hechos, entidades y conflictos.
- Cobertura `24/24`.
- Tokens de plata y oro.
- Descartados/omitidos.
- Run de plata y oro.

Métricas de la última respuesta:

- Modelo.
- Versión de prompt.
- Latencia.
- Tokens de entrada/salida.
- Número de citas.
- Estado (`ok`, `fallback`, `review`, `error`).

Estado:

- Datos: completo/incompleto.
- Modelo: Ollama listo/no disponible/modelo faltante/demo.
- Último error controlado.

## 3. Modo demostración

- Control en la barra lateral: **Modo demostración (modelo falso)**.
- Al activarlo, las tres tareas usan el modelo falso y no requieren Ollama.
- La interfaz muestra un aviso visible: “Modo demostración: respuestas de prueba, no del modelo real.”
- El modo real se restaura desactivando el control.

## 4. Mensajes de error

| Situación | Mensaje |
|-----------|---------|
| Pregunta vacía | “Escribe una pregunta antes de enviar.” |
| Pregunta demasiado larga | “La pregunta supera el límite de 500 caracteres.” |
| Datos incompletos | “Los datos de oro no están materializados. Ejecuta `git lfs pull`.” |
| Ollama no responde | “Ollama no responde. Ejecuta `ollama serve` o activa el modo demostración.” |
| Modelo faltante | “El modelo llama3.1:8b no está descargado. Ejecuta `ollama pull llama3.1:8b`.” |
| Timeout | “El modelo superó el tiempo de espera. Reintenta o usa el modo demostración.” |
| Sin citas | “La respuesta no incluyó citas válidas; se marcó para revisión.” |
| Error inesperado | “Ocurrió un error controlado. Revisa el panel y reintenta.” |

Los mensajes no incluyen trazas, claves ni rutas absolutas.

## 5. Citas

Cada cita se muestra como:

```text
[U1] Título del documento — https://... (sección: Productos, p. 12)
```

- La URL es clicable.
- El texto completo de la URL queda disponible.
- No se usa HTML crudo ni `unsafe_allow_html`.
- Las citas de la última respuesta se muestran también en un `st.expander("Fuentes")`.

## 6. Estados de carga

- Mientras se genera una respuesta: `st.spinner("Generando respuesta…")`.
- El botón de envío se deshabilita durante la operación.
- Un doble clic no debe generar dos llamadas.
- Al terminar, el estado vuelve a disponible.

## 7. Datos y privacidad

- La app solo lee `data/gold/`, `data/silver/reports/` y `data/bronze/_meta/bronze.sqlite3`.
- No escribe en las capas medallion.
- No muestra claves, `.env`, cookies ni rutas absolutas.
- No usa servicios externos; solo Ollama local o el modelo falso.

## 8. Accesibilidad y respuesta visual

- Títulos y etiquetas en español.
- Contraste legible y texto alternativo en iconos.
- Las tablas y tarjetas se adaptan a pantallas estrechas.
- Los mensajes de error son texto, no solo color.
- La app funciona sin conexión a internet.

## 9. Fuera de contrato

- Autenticación, usuarios o permisos.
- Despliegue público.
- Edición de datos o curaduría.
- Evaluación automática de las 40 preguntas.
- Informe o guion de demo.
