# ADR 0009 — App Streamlit del Módulo 1

- **Estado**: aceptada
- **Fecha**: 2026-10-30
- **Autores**: Jason Alejandro Castaño, Roberto José Guerrero
- **Contexto**: Módulo 1, tarea M1-07

## Contexto

Las tareas de Resumen, FAQ y Q&A ya existen en `tasks.py`, con citas, fallback y prompts versionados. Falta
una interfaz local que las exponga para la demo, la revisión académica y la evaluación de 40 preguntas.

La app debe ser local, sin autenticación, sin claves y sin escritura en las capas medallion. Debe funcionar
con Ollama o con un modelo falso cuando el modelo real no esté disponible.

## Decisión

Construir `app.py` con **Streamlit**, tres pestañas y un panel lateral:

1. **Resumen**: paquete de 8k/32k, 8–12 citas, fuentes y fallback.
2. **FAQ**: 10–20 preguntas en expanders, con respuesta, citas y estado.
3. **Q&A**: formulario, validación, citas, fallback y reintento.
4. **Panel lateral**: métricas del corpus, estado de datos/modelo y metadatos de la última respuesta.
5. **Modo demostración**: modelo falso, sin Ollama, claramente identificado.
6. **Solo lectura**: reportes, `coverage.json`, catálogo de bronce y datos de oro; no escribe.
7. **Citas seguras**: `st.markdown` con enlaces, sin HTML crudo ni `unsafe_allow_html`.
8. **Estado**: `st.session_state` y caché para no regenerar en cada rerun.
9. **Errores**: mensajes accionables para modelo, timeout, datos incompletos y pregunta vacía.
10. **Pruebas**: helpers, importación de `app.py` y `AppTest` con `PML_DEMO=1`.

## Alternativas rechazadas

| Alternativa | Motivo |
|-------------|--------|
| Gradio | Permitido, pero la tarea pide Streamlit |
| Cuarta pestaña de métricas | La especificación exige tres pestañas |
| Regenerar en cada interacción | Costo y latencia innecesarios |
| Fallback automático a falso | Ocultaría fallos del modelo real |
| HTML personalizado | Riesgo de inyección y dependencia de `unsafe_allow_html` |
| Escribir resultados en `data/` | Contaminaría las capas medallion |
| Despliegue público | Fuera de alcance y sin autenticación |

## Consecuencias

- La app es una vitrina local, no un servicio desplegado.
- El evaluador puede recorrer las tres tareas sin Ollama.
- El panel hace visible la procedencia, la cobertura y los descartes.
- La app reutiliza `tasks.py`; no duplica prompts ni recuperación.
- El clon requiere `streamlit` y `git lfs pull` para los datos.

## Validación observada

- `uv run streamlit run app.py` abre la app.
- `PML_DEMO=1 uv run pytest tests/integration/test_app_streamlit.py -q` pasa las tres pestañas.
- Q&A en modo demostración devuelve cita o fallback.
- Resumen y FAQ se generan y conservan en sesión.
- El panel muestra métricas y estados.
- No se usan claves, rutas absolutas ni HTML crudo.

## Licencias

Streamlit es software open source (Apache-2.0). No se añaden otras dependencias.
