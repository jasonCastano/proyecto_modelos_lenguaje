# Quickstart — App Streamlit del Módulo 1

**Feature**: `008-streamlit-qa-app`
**Fecha**: 2026-10-30

Guía para validar la app con modelo real y con modo demostración.

## 1. Requisitos

```bash
uv sync
uv run python -m proyecto_modelos_lenguaje.llm --check
```

- `streamlit` debe estar en `pyproject.toml`.
- Ollama activo con `llama3.1:8b` para el modo real.
- Datos de oro materializados por Git LFS:

```bash
git lfs install
git lfs pull
```

Si `--check` falla, la app debe seguir abriendo en modo demostración.

## 2. Arranque

```bash
uv run streamlit run app.py
```

Resultado esperado:

- La app abre en el navegador local.
- Se ven las pestañas **Resumen**, **FAQ** y **Q&A**.
- El panel lateral muestra métricas del corpus y el estado del modelo.
- No hay claves, rutas absolutas ni trazas en pantalla.

## 3. Modo demostración

1. Activar **Modo demostración (modelo falso)** en la barra lateral.
2. Verificar el aviso visible de modo demostración.
3. Recorrer las tres pestañas.

Resultado esperado: las tres tareas funcionan sin Ollama y sin red.

## 4. Q&A

1. Abrir la pestaña **Q&A**.
2. Escribir: “¿Qué productos ofrece Manuelita?”
3. Pulsar **Preguntar**.

Resultado esperado:

- Respuesta con citas `[U#]`.
- Fuentes con título, URL y sección/página.
- Panel con modelo, prompt, latencia, tokens y número de citas.
- Sin excepciones no controladas.

Casos adicionales:

- Pregunta vacía: mensaje de validación, sin llamada al modelo.
- Pregunta sin evidencia: fallback explícito.
- Doble clic: una sola llamada, botón deshabilitado durante la carga.

## 5. Resumen

1. Abrir **Resumen**.
2. Dejar el paquete en `8000`.
3. Pulsar **Generar resumen**.

Resultado esperado:

- Síntesis con 8–12 citas.
- Fuentes visibles.
- Resultado conservado al cambiar de pestaña.
- Con `32000`, usar el paquete grande solo si el modelo lo soporta.

## 6. FAQ

1. Abrir **FAQ**.
2. Seleccionar 12 preguntas.
3. Pulsar **Generar FAQ**.

Resultado esperado:

- 10–20 preguntas expandibles.
- Cada una con respuesta, citas y estado.
- `missing_evidence` cuando no hay evidencia.
- Sin duplicados por pregunta normalizada.

## 7. Panel de métricas

Verificar que el panel muestra:

- Artefactos activos (557).
- Documentos canónicos (404).
- Alias (92).
- Fragmentos (3.810).
- Unidades (15.211).
- Hechos (381), entidades (15), conflictos (38).
- Cobertura 24/24.
- Tokens de plata (1.447.841) y oro (1.000.109).
- Descartados/omitidos (61).
- Run de plata y oro.

Y para la última respuesta:

- Modelo.
- Versión de prompt.
- Latencia.
- Tokens de entrada/salida.
- Número de citas.
- Estado.

## 8. Errores esperados

| Prueba | Resultado |
|--------|-----------|
| Detener Ollama y preguntar | Mensaje “Ollama no responde…”; sugerir modo demostración |
| Usar un modelo no descargado | Mensaje “Ejecuta `ollama pull …`” |
| Renombrar temporalmente un archivo de oro | Estado “datos incompletos”; sugerir `git lfs pull` |
| Pregunta vacía | Validación, sin modelo |
| Pregunta de más de 500 caracteres | Validación, sin modelo |
| Forzar timeout | Error controlado y botón de reintento |

La app no debe mostrar trazas, claves ni rutas absolutas.

## 9. Pruebas automatizadas

```bash
uv run pytest tests/unit/test_app_metrics.py tests/unit/test_app.py -q
PML_DEMO=1 uv run pytest tests/integration/test_app_streamlit.py -q
```

Resultado esperado:

- Helpers de métricas y citas verificados.
- `app.py` importable sin lanzar Streamlit.
- `AppTest` recorre las tres pestañas en modo demostración.
- Sin red y sin Ollama.

## 10. Criterios de aceptación

| Escenario | Criterio |
|-----------|----------|
| Arranque | `uv run streamlit run app.py` abre en < 15 s |
| Q&A | Respuesta con cita o fallback en el 100% de los casos |
| Resumen | 8–12 citas y fuentes visibles |
| FAQ | 10–20 preguntas con cita o `missing_evidence` |
| Panel | ≥ 8 métricas del corpus y ≥ 5 de la respuesta |
| Errores | Modelo, timeout, datos incompletos y pregunta vacía controlados |
| Seguridad | Sin claves, rutas absolutas ni trazas |
| Demo | Tres pestañas funcionan sin Ollama |
| Pruebas | Suite de app pasa sin red en < 2 min |

## 11. Notas

- La app no escribe en `data/`; solo lee reportes y datos de oro.
- Las capturas para el README se toman después de validar el modo real y el modo demostración.
- Si se cambia el modelo o el prompt, la app debe reflejar el nuevo `prompt_version` y `model` en el panel.

## 12. Validación ejecutada

**Fecha**: 2026-10-30 · **Modelo**: `llama3.1:8b` en Ollama local · **Datos**: oro completo por LFS.

La app se ejecutó con `AppTest` contra el modelo real, sin `PML_DEMO`, y arrancó sin excepciones con
las tres pestañas y el panel en estado **Datos: Completo**, **Modelo: Ollama listo** y **Modo: Ollama local**.
También se inició con `uv run streamlit run app.py --server.headless true --server.port 8507`; el endpoint
`/_stcore/health` respondió `200 ok`.

| Tarea | Resultado observado |
|-------|---------------------|
| Q&A | “¿Qué productos ofrece Manuelita?” respondió con citas `[U2]`, `[U4]` y `[U5]`, sin fallback |
| Resumen | 12 citas (`[U2]`, `[U4]`, `[U5]`, `[U36]`, `[U45]`, `[U48]`, `[U57]`, `[U62]`, `[U71]`, `[U72]`, `[U75]`, `[U76]`) y fuentes visibles |
| FAQ | 12 preguntas expandibles, con respuesta, citas y estado |
| Panel | 557 artefactos, 404 canónicos, 92 alias, 3.810 fragmentos, 15.211 unidades, 381 hechos, 15 entidades, 38 conflictos, cobertura 24/24, tokens 1.447.841/1.000.109 y runs de plata/oro |
| Datos incompletos | Estado “Datos incompletos” y aviso para ejecutar `git lfs pull` |
| Modelo no disponible | Estado “Ollama no disponible” con sugerencia de modo demostración |
| Pregunta vacía | Validación visible, sin llamada al modelo |

Las pruebas automatizadas cubren además el modo demostración, el contrato de métricas y la ausencia de
HTML crudo, claves y rutas absolutas.
