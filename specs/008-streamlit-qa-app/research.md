# Fase 0 — Investigación: app Streamlit del Módulo 1

**Feature**: `008-streamlit-qa-app`
**Fecha**: 2026-10-30
**Estado**: decisiones cerradas; sin `NEEDS CLARIFICATION`.

## 1. Framework de interfaz

- **Decisión**: Streamlit, con `app.py` en la raíz y `uv run streamlit run app.py`.
- **Racional**: es el framework exigido por la tarea y la constitución; permite construir la interfaz
  local sin autenticación ni despliegue y reutiliza directamente la biblioteca `tasks.py`.
- **Alternativas consideradas**:
  - Gradio: permitido por la constitución, pero la tarea pide Streamlit.
  - Dash/Flask: más infraestructura para una app académica local.
  - Notebook: no cumple el requisito de app ejecutable.

## 2. Layout: tres pestañas y panel lateral

- **Decisión**: tres pestañas visibles (`Resumen`, `FAQ`, `Q&A`) y un panel lateral persistente con las
  métricas del corpus y el estado del modelo.
- **Racional**: la especificación exige tres pestañas y un panel visible; el lateral no compite con las
  tareas y permanece accesible en todo momento.
- **Alternativas consideradas**:
  - Cuarta pestaña de métricas: incumple “tres pestañas”.
  - Panel inferior: se pierde al hacer scroll en respuestas largas.
  - Métricas dentro de cada pestaña: duplica información y desordena.

## 3. Estado de sesión y caché

- **Decisión**: `st.session_state` para la pregunta, la respuesta, el resumen, la FAQ y el modo de modelo;
  `st.cache_data` para métricas y `st.cache_resource` para unidades, semillas y modelo.
- **Racional**: evita regenerar contenido en cada interacción, conserva resultados al cambiar de pestaña y
  reduce la latencia y el costo local.
- **Alternativas consideradas**:
  - Regenerar en cada rerun: lento y costoso.
  - Persistir en archivos: escritura innecesaria y riesgo de contaminar `data/`.
  - Solo memoria del proceso: se pierde al recargar, pero es aceptable para una sesión.

## 4. Modelo real y modo demostración

- **Decisión**: selector en la barra lateral entre **Ollama local** y **Modo demostración** (modelo falso).
  Si Ollama falla, la app muestra el error y sugiere activar el modo demostración; no cambia de modelo
  automáticamente.
- **Racional**: el modo falso permite la demo y las pruebas sin red; el cambio automático ocultaría fallos
  reales del modelo.
- **Alternativas consideradas**:
  - Solo Ollama: la app falla si el servidor no está activo.
  - Fallback automático: confunde al evaluador y oculta el estado real.
  - Solo modelo falso: no demuestra la integración real.

## 5. Fuente de métricas

- **Decisión**: leer en modo de solo lectura el catálogo de bronce (`v_active_artifacts`), el reporte de
  plata `2026-10-silver-01`, el reporte de oro `2026-10-gold-01`, `coverage.json` y `manifest.json`.
  Descubrir el último run si los IDs de referencia no existen.
- **Racional**: las métricas ya están calculadas y auditadas; recalcularlas en la app duplicaría el pipeline
  y rompería la reproducibilidad.
- **Alternativas consideradas**:
  - Recalcular el corpus al abrir la app: lento y fuera de alcance.
  - Hardcodear las cifras: no se actualiza con nuevos runs.
  - Leer solo `docs/data_card.md`: no es machine-readable.

## 6. Detección de datos incompletos

- **Decisión**: verificar que los archivos requeridos existan, no estén vacíos y no sean punteros de Git LFS
  (cabecera `version https://git-lfs.github.com/spec/v1`). Si falta algo, mostrar `data_status=incomplete`.
- **Racional**: un clon sin `git lfs pull` deja punteros de texto que parecen archivos válidos; la app debe
  explicar cómo materializarlos en lugar de fallar con un JSON inválido.
- **Alternativas consideradas**:
  - Asumir que los datos siempre están: falla confusa.
  - Descargar LFS automáticamente: la app no debe ejecutar Git.

## 7. Citas y fuentes

- **Decisión**: renderizar la respuesta con `st.markdown` (sin HTML crudo) y una lista de fuentes con
  enlaces clicables; cada cita muestra `[U#]`, título, URL y sección/página/tiempo.
- **Racional**: mantiene la trazabilidad visible y evita inyección de HTML; las URLs completas quedan
  disponibles para copiar.
- **Alternativas consideradas**:
  - HTML personalizado: riesgo de XSS y dependencia de `unsafe_allow_html`.
  - Texto plano: no clickable y difícil de leer.

## 8. Manejo de errores

- **Decisión**: capturar `TaskError`, `LLMUnavailableError`, `LLMModelMissingError`, `LLMResponseError` y
  excepciones inesperadas; mostrar `st.error` con un mensaje accionable, un botón de reintento y el estado
  en el panel. No mostrar trazas ni rutas absolutas.
- **Racional**: la app debe seguir usable ante fallos de modelo, timeout o datos incompletos.
- **Alternativas consideradas**:
  - Dejar que Streamlit muestre la excepción: interfaz rota y posible filtración de rutas.
  - Ocultar el error: el evaluador no sabe qué falló.

## 9. Renderizado de Resumen y FAQ

- **Decisión**: Resumen en Markdown con secciones, citas y lista de fuentes; FAQ en `st.expander` por
  pregunta, con respuesta, citas y estado (`ready`, `review`, `missing_evidence`).
- **Racional**: el resumen se lee como un documento y la FAQ se explora sin saturar la pantalla. Los estados
  quedan visibles.
- **Alternativas consideradas**:
  - Tabla única de FAQ: difícil de leer con respuestas largas.
  - Tarjetas HTML: más control visual, pero más código y riesgo de inyección.

## 10. Pruebas de la app

- **Decisión**: pruebas unitarias de helpers (`load_app_metrics`, `format_citation`, validación, estado);
  prueba de importación de `app.py`; `AppTest` de Streamlit en modo demostración; prueba opcional con
  Ollama. La app acepta `PML_DEMO=1` para forzar el modelo falso en pruebas.
- **Racional**: permite validar la UI sin servidor ni red; el modo real se reserva para la demo y M1-08.
- **Alternativas consideradas**:
  - Solo prueba manual: no protege contra regresiones.
  - `AppTest` con Ollama: lento, no determinista y dependiente de hardware.

## 11. Dependencias

- **Decisión**: añadir `streamlit` como dependencia de ejecución. No se añaden otras dependencias; se
  reutilizan `tasks.py`, `llm.py` y los reportes.
- **Racional**: Streamlit es el framework exigido; las demás funciones ya existen.
- **Alternativas consideradas**:
  - Añadir una librería de componentes: innecesaria para tres pestañas.
  - Usar HTML/JS propio: más mantenimiento y riesgo.

## 12. Seguridad y datos

- **Decisión**: no mostrar claves, `.env`, rutas absolutas ni trazas; usar `unsafe_allow_html=False`; no
  escribir en `data/`; no ejecutar código del corpus.
- **Racional**: la app es una vitrina académica y el corpus es dato no confiable; la superficie de riesgo
  debe ser mínima.
- **Alternativas consideradas**:
  - Permitir HTML del modelo: riesgo de inyección.
  - Mostrar la configuración completa: puede exponer detalles internos.
