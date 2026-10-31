# Implementation Plan: App Streamlit — Resumen, FAQ y Q&A

**Branch**: `008-streamlit-qa-app` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/008-streamlit-qa-app/spec.md`

## Summary

Construir la app local del Módulo 1 en Streamlit: tres pestañas —**Resumen**, **FAQ** y **Q&A**— sobre las
tareas ya implementadas en `tasks.py`, con citas verificables, fallback explícito, panel de métricas y
manejo de errores. La app lee los datos de oro y los reportes en modo de solo lectura, funciona con Ollama
local o con un modo de demostración sin red, y se ejecuta con `uv run streamlit run app.py`.

La lógica de métricas se separa en un módulo testeable (`app_metrics.py`); `app.py` contiene la interfaz.
Las pruebas usan el modelo falso y `AppTest`, sin depender de Ollama.

## Technical Context

**Language/Version**: Python 3.14, gestionado con `uv`.

**Primary Dependencies**: Streamlit 1.x (última estable resuelta por `uv` al implementar), LangChain
`1.4.7`, `langchain-core` `1.7.3`, `langchain-ollama` `1.1.0`, Ollama `llama3.1:8b` y los módulos existentes
`tasks.py`, `retrieval.py` y `llm.py`. Solo se añade `streamlit` como dependencia nueva.

**Storage**: lectura de `data/gold/` (unidades, contexto, FAQ, cobertura, manifiesto),
`data/silver/reports/` (calidad), `data/bronze/_meta/bronze.sqlite3` (artefactos activos, en modo
`mode=ro`) y `docs/` para enlaces. La app no escribe en `data/`.

**Testing**: `pytest` con helpers unitarios, prueba de importación de `app.py` y `AppTest` de Streamlit en
modo demostración; prueba opcional con Ollama. Ruff para lint.

**Target Platform**: app local en navegador; desarrollo en Windows 11 y CI en Linux.

**Project Type**: proyecto único de librería + CLI + app local.

**Performance Goals**: arranque < 15 s; Q&A < 30 s; resumen 8k < 120 s; FAQ de 12 < 5 min en el equipo de
referencia; suite de app con modelo falso < 2 min.

**Constraints**: sin autenticación ni despliegue; solo lectura de datos; sin embeddings ni servicios
externos; sin claves ni rutas absolutas; modo demostración sin Ollama; citas obligatorias y fallback.

**Scale/Scope**: 557 artefactos activos, 404 documentos canónicos, 3.810 fragmentos, 15.211 unidades,
53 preguntas semilla, 24/24 ítems y 40 preguntas de evaluación en M1-08.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cumplimiento | Evidencia en el plan |
|--------------------------|--------------|----------------------|
| I. Reproducibilidad experimental | PASS | La app lee reportes y datos versionados; modo falso para pruebas; sin estado oculto. |
| II. Evaluación con métricas y línea base | PASS | Panel con métricas y metadatos; M1-08 usará la app para evaluar. |
| III. Procedencia y ética de datos | PASS | Citas y URLs visibles; solo lectura; sin datos privados. |
| IV. Experimentos como código | PASS | `app.py`, `app_metrics.py`, pruebas y contratos en Git. |
| V. Simplicidad y alcance académico | PASS | Una sola dependencia nueva; sin embeddings ni servicios externos. |
| Arquitectura medallion | PASS | Solo lectura de bronce, plata y oro; no escribe. |
| Prompt Engineering y citas | PASS | Reutiliza `tasks.py`; muestra citas y fallback. |
| Pruebas (§3.8) | PASS | Helpers, importación y `AppTest` con modelo falso. |
| Seguridad y secretos | PASS | Sin claves, rutas absolutas, HTML crudo ni trazas. |

**Resultado**: sin violaciones. No se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/008-streamlit-qa-app/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── ui.md
│   └── app-metrics.schema.json
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit.tasks, no se crea aquí)
```

### Source Code (repository root)

```text
app.py                               # Interfaz Streamlit: pestañas, panel, estado
src/proyecto_modelos_lenguaje/
├── app_metrics.py                   # Carga y formato de métricas de solo lectura
├── tasks.py                         # Resumen, FAQ, Q&A (sin cambios)
├── retrieval.py                     # Recuperación (sin cambios)
└── llm.py                           # Modelo Ollama y falso (sin cambios)

tests/
├── unit/
│   ├── test_app_metrics.py
│   └── test_app.py
└── integration/
    └── test_app_streamlit.py
```

**Structure Decision**: se mantiene el proyecto único. `app.py` es la entrada de la app; `app_metrics.py`
concentra la lectura y el formato de métricas para poder probarlo sin Streamlit. Las tareas de negocio
siguen en `tasks.py`.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. Streamlit como framework obligatorio.
2. Tres pestañas + panel lateral persistente.
3. `st.session_state` y caché para evitar regeneraciones.
4. Selector explícito Ollama/modo demostración; sin fallback automático silencioso.
5. Métricas desde reportes/catálogo en solo lectura, con detección de punteros LFS.
6. Citas con `st.markdown` y enlaces, sin HTML crudo.
7. Errores controlados con mensajes accionables y reintento.
8. Resumen en Markdown; FAQ en expanders con estado.
9. Pruebas con helpers, importación y `AppTest` en modo demostración.
10. Solo `streamlit` como dependencia nueva.

## Phase 1 — Design & Contracts

### Data model

Ver [data-model.md](./data-model.md). Entidades: `AppMetrics`, `AppStatus`, `AppSessionState`, `AnswerView`,
`FAQView`, `PanelMetric` y `SourceCitation`.

### Contracts

- [contracts/ui.md](./contracts/ui.md): layout, pestañas, panel, estados, errores y accesibilidad.
- [contracts/app-metrics.schema.json](./contracts/app-metrics.schema.json): métricas del panel.

### Quickstart

Ver [quickstart.md](./quickstart.md). Escenarios: arranque, modo demostración, Q&A, resumen, FAQ, panel,
errores y pruebas.

### Re-evaluación post-diseño

| Principio / restricción | Resultado | Evidencia |
|--------------------------|-----------|-----------|
| Reproducibilidad | PASS | Datos/reportes versionados, modo falso y tests. |
| Métricas y línea base | PASS | Panel con métricas y metadatos de respuesta. |
| Procedencia y ética | PASS | Citas y URLs; solo lectura; sin datos privados. |
| Experimentos como código | PASS | App, helpers, contratos y pruebas en Git. |
| Simplicidad | PASS | Una dependencia nueva y reutilización de tasks.py. |
| Medallion y seguridad | PASS | Sin escritura; sin secretos ni HTML crudo. |

## Implementation Phases

### Fase A — Métricas y estado

1. Crear `src/proyecto_modelos_lenguaje/app_metrics.py`.
2. Leer `v_active_artifacts` en modo `mode=ro`.
3. Leer reportes de plata/oro, `coverage.json` y `manifest.json`.
4. Detectar datos completos/incompletos y punteros LFS.
5. Formatear métricas y estado para la UI.
6. Añadir pruebas unitarias de métricas y detección.

### Fase B — Shell de la app

1. Añadir `streamlit` a `pyproject.toml`.
2. Crear `app.py` con `st.set_page_config`, título y layout ancho.
3. Implementar las tres pestañas y el panel lateral.
4. Implementar el selector de modelo real/demostración.
5. Implementar estado de datos y modelo.
6. Añadir prueba de importación de `app.py`.

### Fase C — Q&A

1. Formulario con pregunta y botón.
2. Validación de pregunta vacía/larga.
3. Llamada a `answer_question` con modelo real o falso.
4. Render de respuesta, citas y fuentes.
5. Fallback y error controlado con reintento.
6. Estado de carga y prevención de doble envío.
7. Pruebas con `AppTest` y modelo falso.

### Fase D — Resumen

1. Selector 8k/32k.
2. Botón de generación y estado de carga.
3. Llamada a `summarize_corpus`.
4. Render Markdown con citas y fuentes.
5. Fallback con contexto vacío.
6. Persistencia en sesión.
7. Pruebas de helper y `AppTest`.

### Fase E — FAQ

1. Selector 10–20.
2. Botón de generación.
3. Llamada a `generate_faq`.
4. Render en expanders con estado y citas.
5. `missing_evidence` y deduplicación visible.
6. Persistencia en sesión.
7. Pruebas de helper y `AppTest`.

### Fase F — Errores, seguridad y accesibilidad

1. Capturar errores de modelo, timeout, datos y pregunta.
2. Mensajes accionables y reintento.
3. Verificar que no se muestran claves, rutas absolutas ni trazas.
4. Revisar contraste, etiquetas y layout estrecho.
5. Pruebas de seguridad de la salida.

### Fase G — Validación y documentación

1. Ejecutar Ruff y pytest.
2. Ejecutar `AppTest` en modo demostración.
3. Ejecutar el quickstart manual con Ollama.
4. Actualizar README con el comando y capturas.
5. Añadir ADR 0009 de la app.
6. Actualizar la bitácora y marcar M1-07.

## Testing Strategy

| Nivel | Qué cubre | Herramientas |
|-------|-----------|--------------|
| Unitario | Métricas, detección de datos, formato de citas, validación | `pytest`, `tmp_path` |
| Importación | `import app` sin ejecutar Streamlit | `pytest` |
| Integración UI | Tres pestañas, Q&A, resumen y FAQ en modo demostración | `streamlit.testing.v1.AppTest` |
| Manual | Ollama real, panel, errores, responsive | `streamlit run app.py` |
| Seguridad | Sin secretos, rutas absolutas ni HTML crudo | Pruebas de texto |

**Regla**: la suite por defecto no usa red ni Ollama; `PML_DEMO=1` fuerza el modelo falso.

## Risks & Mitigations

| Riesgo | Mitigación |
|--------|------------|
| Ollama lento o caído | Modo demostración, timeout y mensaje accionable |
| Datos LFS no materializados | Estado `incomplete` y aviso `git lfs pull` |
| Reruns de Streamlit regeneran contenido | `session_state` y caché |
| FAQ lenta | Límite 12 y modo demostración |
| Citas largas o URLs enormes | Truncar vista previa, conservar enlace |
| HTML del modelo | `unsafe_allow_html=False` |
| Importar app ejecuta la UI | `if __name__ == "__main__": main()` |
| Métricas desactualizadas | Leer reportes vigentes y mostrar run IDs |
| Doble clic | Formulario y botón deshabilitado |
| Pantalla estrecha | Layout responsive y expanders |

## Acceptance Mapping

| Requisito | Prueba / evidencia |
|-----------|--------------------|
| FR-001, FR-019 | Arranque y `streamlit` en pyproject |
| FR-002 | Tres pestañas en `AppTest` |
| FR-003–FR-005 | Q&A, citas y fallback |
| FR-006, FR-007 | Resumen y FAQ |
| FR-008, FR-009 | Panel de métricas y metadatos |
| FR-010, FR-011 | Errores y validación |
| FR-012 | Persistencia en sesión |
| FR-013 | Modo demostración |
| FR-014, FR-015 | Seguridad y solo lectura |
| FR-016, FR-017 | Enlaces y español |
| FR-018 | Importación sin servidor |
| FR-020–FR-022 | Estados, carga y reintento |
| SC-001…SC-010 | Quickstart y pruebas |

## Complexity Tracking

Sin violaciones de la constitución. No se requiere justificación adicional.

## Next Steps

1. Ejecutar `/speckit.tasks` para generar el backlog de M1-07.
2. Implementar Fase A y B, luego Q&A como MVP.
3. Validar con el quickstart y actualizar la bitácora.
