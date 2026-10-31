# Implementation Plan: Identidad visual Manuelita para la app Q&A

**Branch**: `009-manuelita-visual-identity` | **Date**: 2026-10-30 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/009-manuelita-visual-identity/spec.md`

**Note**: This template is filled in by the `/speckit.plan` command; its definition describes the execution workflow.

## Summary

Aplicar una identidad visual inspirada en el sitio público de Grupo Manuelita a la app Streamlit del
Módulo 1, sin tocar su funcionalidad. La implementación se apoya en tres piezas: un módulo de **tokens de
marca** con la paleta oficial extraída del logotipo (`#387C2B`, `#E86D1F`, `#B0BC22`, `#FFD200`, `#F6A01A`),
un **tema nativo** de Streamlit declarado en `.streamlit/config.toml` y una **capa de estilos** inyectada
con `st.html` (no `unsafe_allow_html`) que da cabecera, tarjetas de fuente, badges de estado y pie de página.
La legibilidad se verifica con el cálculo real de contraste WCAG en pruebas unitarias, sin navegador.

## Technical Context

**Language/Version**: Python 3.14 (gestión con `uv`).

**Primary Dependencies**: `streamlit>=1.66.1` (ya declarado), `pytest` y `jsonschema` (dev). Sin
dependencias nuevas; `st.html` está disponible desde Streamlit 1.33.

**Storage**: sin almacenamiento nuevo. La identidad vive en código versionado (tokens + CSS) y en
`.streamlit/config.toml`; no se leen datos del corpus para pintar la interfaz.

**Testing**: `pytest` con `streamlit.testing.v1.AppTest` (ya usado en `tests/unit/test_app.py`) más pruebas
unitarias puras de contraste y de tokens. La suite no usa red ni navegador.

**Target Platform**: app local de escritorio y videobeam (1440×900 a 1920×1080), navegador moderno;
ventana mínima soportada de 360 px de ancho.

**Project Type**: proyecto único: biblioteca + CLI + app Streamlit en la raíz.

**Performance Goals**: el arranque de la app no aumenta más de 2 s respecto de la versión actual; la
inyección de estilos es un único bloque estático evaluado una vez por sesión.

**Constraints**: sin conexión (todo local, sin fuentes ni imágenes externas); sin `unsafe_allow_html` en
`app.py` (regla de seguridad ya probada); contraste AA mínimo; ningún cambio de comportamiento respecto de
la especificación 008; sin recursos licenciados del sitio (fotografías, tipografías, manual de marca).

**Scale/Scope**: una app, tres pestañas, ~345 líneas actuales en `app.py`, 6 vistas de estado y 3 pestañas
que comparten cabecera, tarjetas y badges.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio / restricción | Cumplimiento | Evidencia en el plan |
|--------------------------|--------------|----------------------|
| I. Reproducibilidad experimental | PASS | Tokens y CSS versionados; ningún recurso remoto ni fuente externa. |
| II. Evaluación con métricas y línea base | PASS | Contraste medido con fórmula WCAG en pruebas; comparación de arranque antes/después. |
| III. Procedencia y ética de datos | PASS | No se copian fotografías ni tipografías; se atribuye la marca y se declara no afiliación. |
| IV. Experimentos como código versionado | PASS | Paleta y estilos en el repositorio, con pruebas que los fijan. |
| V. Simplicidad y alcance académico | PASS | Sin dependencias nuevas ni marco de diseño; un módulo de ~150 líneas y un TOML. |
| Arquitectura medallion | PASS | Solo lectura de datos; la identidad no toca `data/`. |
| Seguridad (§3.9) | PASS | Sin `unsafe_allow_html` en `app.py`; CSS estático propio; sin secretos ni rutas absolutas. |
| Accesibilidad y trazabilidad (§3.7) | PASS | Contraste AA, estado con texto e icono, tarjetas de cita con enlace verificable. |
| Pruebas offline (§3.8) | PASS | `AppTest` y pruebas puras; la suite no requiere red. |

**Resultado**: sin violaciones. No se requiere Complexity Tracking.

## Project Structure

### Documentation (this feature)

```text
specs/009-manuelita-visual-identity/
├── plan.md              # Este archivo
├── research.md          # Fase 0: decisiones y alternativas
├── data-model.md        # Fase 1: entidades, validaciones e invariantes
├── quickstart.md        # Fase 1: validación end-to-end
├── contracts/
│   ├── brand-tokens.schema.json
│   └── ui-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md             # Fase 2 (/speckit.tasks)
```

### Source Code (repository root)

```text
.streamlit/
└── config.toml              # Tema nativo: primario, fondo, texto y fuente del sistema

src/proyecto_modelos_lenguaje/
├── brand.py                 # Tokens, contraste WCAG, CSS y helpers de estado
└── app_metrics.py           # Sin cambios (solo se consume)

app.py                       # Cabecera, badges, tarjetas de cita, pie; sin unsafe_allow_html
tests/
├── unit/
│   ├── test_brand.py        # Contraste, tokens y esquema
│   └── test_app.py          # Se amplía: cabecera, estados, pie
└── integration/
    └── test_app_brand.py    # AppTest: identidad visible en las tres pestañas
```

**Structure Decision**: se mantiene el proyecto único. La identidad se concentra en
`src/proyecto_modelos_lenguaje/brand.py` para que `app.py` solo la consuma; el tema base se declara en
`.streamlit/config.toml` para que los widgets nativos (inputs, tabs, expanders) hereden la paleta sin CSS.
No se crea un paquete `ui/` porque la app tiene una sola pantalla.

## Complexity Tracking

Sin violaciones de la constitución. No se requiere justificación adicional.

## Phase 0 — Research

Ver [research.md](./research.md). Decisiones principales:

1. Paleta oficial extraída del logotipo público (5 colores + blanco).
2. Tema nativo de Streamlit para la base; CSS propio solo para lo que el tema no cubre.
3. `st.html` como mecanismo de estilos, para conservar la prohibición de `unsafe_allow_html`.
4. Firma tipográfica en lugar del logotipo raster (marca registrada y offline).
5. Tipografía del sistema (sin fuentes descargadas).
6. Contraste calculado con la fórmula WCAG 2.1 en Python, verificable en pruebas.
7. Estados con texto + icono + color; nunca solo color.
8. Atribución y aviso de no afiliación en el pie.

## Phase 1 — Design & Contracts

### Data model

Ver [data-model.md](./data-model.md). Entidades: `BrandPalette`, `BrandTokens`, `StatusVariant`,
`SourceCard`, `PageChrome` y `BrandAsset`.

### Contracts

- [contracts/brand-tokens.schema.json](./contracts/brand-tokens.schema.json): forma y validación de la paleta.
- [contracts/ui-contract.md](./contracts/ui-contract.md): qué debe mostrar cada zona, clases CSS y estados.

### Quickstart

Ver [quickstart.md](./quickstart.md). Escenarios: arranque, cabecera, tres pestañas, fallback, error, modo
demo, ventana estrecha, sin conexión y verificación de contraste.

### Re-evaluación post-diseño

| Principio / restricción | Resultado | Evidencia |
|--------------------------|-----------|-----------|
| Reproducibilidad | PASS | Tokens en JSON/TOML y CSS en el repositorio; cero recursos remotos. |
| Métricas y línea base | PASS | `contrast_ratio()` y pruebas con umbrales; medición de arranque en quickstart. |
| Procedencia y ética | PASS | Solo color y tipografía; atribución y aviso de no afiliación. |
| Experimentos como código | PASS | Contratos y pruebas versionados. |
| Simplicidad | PASS | Sin dependencias nuevas ni framework de UI. |
| Medallion y seguridad | PASS | Solo lectura; sin HTML no confiable ni secretos. |

## Implementation Phases

### Fase A — Tokens y tema

1. Crear `src/proyecto_modelos_lenguaje/brand.py` con `BrandPalette`, `BrandTokens`, `contrast_ratio()` y
   `inject_brand_styles()`.
2. Crear `.streamlit/config.toml` con el tema nativo.
3. Definir los pares de color permitidos y sus umbrales.

### Fase B — Cabecera y pie

1. Sustituir `st.title(PAGE_TITLE)` por una cabecera con firma tipográfica, proyecto y estado del sistema.
2. Añadir barra de estado persistente (datos, modelo, modo demo).
3. Añadir pie con atribución y aviso de no afiliación.

### Fase C — Componentes

1. Tarjetas de fuente reutilizables en las tres pestañas (`render_citations`).
2. Badges de estado con texto, icono y color (fallback, revisión, error, demo).
3. Ajustes de jerarquía tipográfica y espaciado en paneles y respuestas.

### Fase D — Pruebas y accesibilidad

1. Pruebas unitarias de contraste, tokens y esquema.
2. Pruebas de `AppTest` para cabecera, estados y pie en las tres pestañas.
3. Verificación manual en 360 px, 1440 px y con color desaturado.

## Testing Strategy

| Nivel | Qué cubre | Fixtures |
|-------|-----------|----------|
| Unitario | Contraste WCAG, formato de tokens, mapeo de estados, CSS sin URLs | `tests/unit/test_brand.py` |
| Integración UI | Cabecera, badges, tarjetas y pie visibles sin excepción | `AppTest.from_function` / app real |
| Contrato | Paleta contra `brand-tokens.schema.json` | `jsonschema` |
| Manual | Legibilidad a 360 px, videobeam y color desaturado | quickstart |

**Regla**: la suite por defecto no usa red, navegador ni Ollama.

## Risks & Mitigations

| Riesgo | Mitigación |
|--------|------------|
| El CSS propio rompe widgets nativos | Preferir el tema TOML y limitar el CSS a clases propias del contenido |
| `st.html` no disponible o cambia | Comprobar la versión y degradar sin estilos, sin fallar |
| Contraste insuficiente en textos secundarios | Umbrales en pruebas y paleta de texto oscura sobre fondos claros |
| Copiar la marca sugiere afiliación | Firma tipográfica, atribución y aviso explícito de no afiliación |
| Regresión funcional de la spec 008 | Suite existente intacta + pruebas de las tres pestañas |
| Dependencia de fuentes externas | Pila de fuentes del sistema; cero descargas |
| Logotipo con licencia restringida | No se distribuye el archivo; solo paleta y tratamiento tipográfico |

## Acceptance Mapping

| Requisito | Prueba / evidencia |
|-----------|--------------------|
| FR-001, FR-018 | Cabecera visible sin scroll en `AppTest` |
| FR-002 | Paleta del esquema y tema TOML |
| FR-003 | Escala tipográfica definida en tokens |
| FR-004 | `contrast_ratio()` en pruebas con umbral 4.5/3.0 |
| FR-005, FR-007, FR-008, SC-007 | Variantes de estado y tarjetas con texto, icono y enlace |
| FR-006, FR-010 | Barra de estado y badge de demo |
| FR-009 | Cuatro variantes semánticas mapeadas |
| FR-011, FR-012, SC-010 | Pie con atribución y aviso |
| FR-013, SC-005 | Prueba de que CSS y tokens no contienen URLs |
| FR-014, SC-006 | Checklist manual a 360 px |
| FR-015, SC-004 | Suite de la spec 008 en verde |
| FR-016 | Textos en español en tokens y plantillas |
| FR-017 | Una sola inyección de estilos para toda la app |
| FR-019 | Sin archivos de imagen ni fuentes en el repositorio |
| FR-020 | `AppTest` sin servidor |
| SC-001…SC-010 | quickstart + pruebas |

## Next Steps

1. El backlog está en [tasks.md](./tasks.md) (35 tareas, 8 fases).
2. Implementar Fase 1 y 2 y luego US1 como MVP visual (cabecera + paleta).
3. Validar con el quickstart y actualizar la bitácora.
