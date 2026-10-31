# Tareas: Identidad visual Manuelita para la app Q&A

**Entrada**: documentos de diseño de `/specs/009-manuelita-visual-identity/`

**Prerrequisitos**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Pruebas**: incluidas porque la especificación exige verificar contraste, estados y no regresión con
pruebas automáticas. Cada prueba debe fallar antes de la implementación correspondiente.

**Organización**: tareas agrupadas por historia de usuario para permitir implementación y validación
independientes.

## Formato: `[ID] [P?] [Story] Descripción`

- **[P]**: puede ejecutarse en paralelo (archivos distintos, sin dependencias pendientes)
- **[Story]**: historia de usuario (`US1`–`US5`)
- Todas las rutas son relativas a la raíz del repositorio

## Convenciones de rutas

Proyecto único: app en `app.py`, código en `src/proyecto_modelos_lenguaje/`, tema en `.streamlit/`,
pruebas en `tests/`.

---

## Fase 1: Preparación (infraestructura compartida)

**Propósito**: tema nativo y esqueleto del módulo de marca.

- [x] T001 [P] Crear `.streamlit/config.toml` con el tema nativo: `primaryColor="#387C2B"`, `backgroundColor="#FFFFFF"`, `secondaryBackgroundColor="#F5F7F3"`, `textColor="#14240F"` y `font="sans serif"`.
- [x] T002 [P] Crear `tests/contract/test_brand_contract.py` como esqueleto de validación de la paleta contra `specs/009-manuelita-visual-identity/contracts/brand-tokens.schema.json`.
- [x] T003 [P] Crear `tests/unit/test_brand.py` como esqueleto de pruebas de contraste, tokens y estados.
- [x] T004 [P] Crear `tests/integration/test_app_brand.py` como esqueleto de pruebas `AppTest` de cabecera, badges y pie.

---

## Fase 2: Fundamentos (prerrequisitos bloqueantes)

**Propósito**: tokens, contraste, CSS y mapeo de estados.

**⚠ CRÍTICO**: no iniciar una historia de usuario hasta completar esta fase.

- [x] T005 Implementar en `src/proyecto_modelos_lenguaje/brand.py` el dataclass `BrandPalette` con los trece colores de `data-model.md` y validación de formato `^#[0-9A-F]{6}$`.
- [x] T006 Implementar en `src/proyecto_modelos_lenguaje/brand.py` el dataclass `BrandTokens` con `palette`, `contrast_pairs`, `type_scale`, `font_stack`, `radius`, `spacing_unit`, `brand_name`, `project_name`, `tagline`, `attribution` y `affiliation_note`, más `to_dict()`.
- [x] T007 Implementar en `src/proyecto_modelos_lenguaje/brand.py` `contrast_ratio(text, background)` con la fórmula WCAG 2.1 y `validate_contrast(tokens)` que devuelve la lista de pares incumplidos.
- [x] T008 Implementar en `src/proyecto_modelos_lenguaje/brand.py` el CSS de marca como constante y `inject_brand_styles()` usando `st.html`, con inyección idempotente por sesión.
- [x] T009 Implementar en `src/proyecto_modelos_lenguaje/brand.py` `status_variant(key)` con el mapeo de `data-model.md` (color, icono, etiqueta) y `demo` como variante adicional.
- [x] T010 [P] Añadir pruebas de contrato en `tests/contract/test_brand_contract.py`: `BrandTokens().to_dict()` valida contra el esquema y todos los hex cumplen el patrón.
- [x] T011 [P] Añadir pruebas unitarias en `tests/unit/test_brand.py`: `contrast_ratio` con valores conocidos (negro/blanco = 21), todos los pares cumplen su mínimo, tokens sin URLs ni rutas absolutas y el CSS no contiene `http`.

**Punto de control**: tokens, contraste y CSS listos; las historias pueden empezar.

---

## Fase 3: Historia de Usuario 1 — Reconocer la marca al abrir (Prioridad: P1) 🎯 MVP

**Objetivo**: cabecera con firma institucional, nombre del proyecto y estado del sistema.

**Prueba independiente**: abrir la app y ver la cabecera con marca, proyecto y estado sin desplazarse.

### Pruebas de la Historia 1

- [x] T012 [US1] Añadir prueba `AppTest` en `tests/integration/test_app_brand.py`: la app no lanza excepción y renderiza `pml-header` con «Grupo Manuelita» y el nombre del proyecto.
- [x] T013 [US1] Añadir prueba unitaria en `tests/unit/test_brand.py`: `header_markdown()` incluye marca, proyecto y lema, y no contiene HTML ejecutable.

### Implementación de la Historia 1

- [x] T014 [US1] Implementar `header_markdown(tokens)` en `src/proyecto_modelos_lenguaje/brand.py` y `render_header()` con la firma tipográfica.
- [x] T015 [US1] Sustituir `st.title(PAGE_TITLE)` por `brand.render_header()` y `brand.inject_brand_styles()` en `app.py`, y ajustar `st.set_page_config` (título e icono) sin `unsafe_allow_html`.
- [x] T016 [US1] Añadir en `app.py` la barra de estado persistente con datos, modelo y modo demo, reutilizando `metrics`, `current_model_status` y `session_state.demo_mode`.

**Punto de control**: la app abre con identidad reconocible y estado visible.

---

## Fase 4: Historia de Usuario 2 — Jerarquía de lectura (Prioridad: P2)

**Objetivo**: escala tipográfica, espaciado y contraste aplicados al contenido.

**Prueba independiente**: leer tres respuestas y distinguir título, cuerpo, citas y metadatos en 1440 px y 360 px.

### Pruebas de la Historia 2

- [x] T017 [US2] Añadir prueba en `tests/unit/test_brand.py`: el CSS define las cuatro escalas (`display`, `heading`, `body`, `caption`) y un ancho mínimo fluido sin `min-width` fijo mayor a 320 px.
- [x] T018 [US2] Añadir prueba `AppTest` en `tests/integration/test_app_brand.py`: las respuestas se renderizan dentro de contenedores con clase `pml-card` y los metadatos usan la clase de texto secundario.

### Implementación de la Historia 2

- [x] T019 [US2] Implementar en `brand.py` las reglas CSS de jerarquía (tamaños, pesos, interlineado y espaciado basado en `spacing_unit`) y aplicarlas en `app.py` a respuestas, metadatos y panel.

**Punto de control**: la lectura es clara y sin scroll horizontal a 360 px.

---

## Fase 5: Historia de Usuario 3 — Tarjetas de fuente (Prioridad: P3)

**Objetivo**: cada cita se presenta como tarjeta verificable y consistente en las tres pestañas.

**Prueba independiente**: una respuesta con dos citas muestra dos tarjetas con etiqueta, título, ubicación y enlace.

### Pruebas de la Historia 3

- [x] T020 [US3] Añadir prueba unitaria en `tests/unit/test_brand.py`: `source_card_markdown(citation)` incluye etiqueta, título, ubicación y URL, y declara «sin sección declarada» cuando falta la ubicación.
- [x] T021 [US3] Añadir prueba en `tests/unit/test_app.py` (sin romper las existentes): `citation_markdown` conserva la etiqueta `[U#]` y el enlace es clicable.

### Implementación de la Historia 3

- [x] T022 [US3] Implementar `source_card_markdown()` en `brand.py` y refactorizar `render_citations` en `app.py` para usarla en Q&A, Resumen y FAQ.

**Punto de control**: las fuentes se leen como tarjetas en las tres pestañas.

---

## Fase 6: Historia de Usuario 4 — Estados sin depender del color (Prioridad: P4)

**Objetivo**: badges de fallback, revisión, error y demo con texto e icono.

**Prueba independiente**: desaturar la pantalla y comprobar que cada estado se distingue.

### Pruebas de la Historia 4

- [x] T023 [US4] Añadir prueba unitaria en `tests/unit/test_brand.py`: cada variante tiene `label` e `icon` no vacíos y el mapeo conserva `ready|review|missing_evidence` y `ok|fallback|review|error`.
- [x] T024 [US4] Añadir prueba `AppTest` en `tests/integration/test_app_brand.py`: un resultado en fallback muestra badge informativo con texto «Sin evidencia» y no un badge de error.

### Implementación de la Historia 4

- [x] T025 [US4] Implementar `badge_markdown(key, label=None)` en `brand.py` y aplicarlo en `app.py` a `faq_status_badge`, `render_result` y `render_error`, manteniendo los textos actuales.

**Punto de control**: los estados se entienden sin color.

---

## Fase 7: Historia de Usuario 5 — Trabajo académico declarado (Prioridad: P5)

**Objetivo**: pie con atribución de marca y aviso de no afiliación.

**Prueba independiente**: abrir la app y localizar la nota en menos de diez segundos.

### Pruebas de la Historia 5

- [x] T026 [US5] Añadir prueba unitaria en `tests/unit/test_brand.py`: `footer_markdown()` incluye «no afiliado» y la atribución a los titulares de la marca.
- [x] T027 [US5] Añadir prueba `AppTest` en `tests/integration/test_app_brand.py`: el pie se renderiza al final de la app con `pml-footer`.

### Implementación de la Historia 5

- [x] T028 [US5] Implementar `footer_markdown(tokens)` en `brand.py` y `render_footer()` en `app.py`.

**Punto de control**: la app declara su carácter académico.

---

## Fase 8: Pulido y aspectos transversales

**Propósito**: documentación, accesibilidad manual, decisión de arquitectura y bitácora.

- [x] T029 Crear `docs/decisions/0010-brand-identity.md` con la paleta, la decisión de firma tipográfica, el uso de `st.html` y el aviso de no afiliación.
- [x] T030 Actualizar `README.md` con una captura de la nueva identidad y una nota de la paleta.
- [x] T031 Ejecutar `uv run ruff check .` y `uv run ruff format --check .` y corregir hallazgos en `brand.py`, `app.py` y `tests/`.
- [x] T032 Ejecutar `uv run pytest` y corregir fallos de `test_brand.py`, `test_brand_contract.py`, `test_app_brand.py` y `test_app.py`.
- [ ] T033 Verificación manual del quickstart: 360 px sin scroll horizontal, escala de grises, videobeam y arranque con `PML_DEMO=1`. *(Pendiente: el arranque con `PML_DEMO=1` se midió —salud en 2 s— y `AppTest` cubre la estructura; falta la revisión perceptual en navegador.)*
- [x] T034 Medir el arranque con `uv run streamlit run app.py` y registrar el incremento respecto de la versión anterior (≤ 2 s).
- [x] T035 Regenerar la bitácora con `uv run python .opencode/skills/bitacora/scripts/generate_bitacora.py`.

---

## Dependencias y orden de ejecución

### Dependencias por fase

- **Preparación (Fase 1)**: sin dependencias; puede empezar de inmediato.
- **Fundamentos (Fase 2)**: depende de Fase 1; bloquea todas las historias.
- **US1 (Fase 3)**: depende de Fase 2; es el MVP visual.
- **US2 (Fase 4)**: depende de US1 para aplicarse sobre el contenido ya reencuadrado.
- **US3 (Fase 5)**: depende de Fase 2; puede hacerse en paralelo con US2 si se separan archivos.
- **US4 (Fase 6)**: depende de Fase 2; reutiliza las variantes de estado.
- **US5 (Fase 7)**: depende de Fase 2; independiente del resto.
- **Pulido (Fase 8)**: depende de todas las historias.

### Dentro de cada historia

1. Pruebas primero; deben fallar antes de la implementación.
2. Tokens y helpers antes de la vista.
3. Vista antes de la integración con `app.py`.
4. Cada historia debe dejar Ruff y pytest en verde.

### Oportunidades de paralelización

- T001–T004 pueden ejecutarse en paralelo (archivos distintos).
- T010–T011 pueden ejecutarse en paralelo (archivos distintos).
- US3 y US5 comparten `brand.py` con US1/US2: ejecutar secuencialmente dentro del mismo archivo.
- Las pruebas de una misma historia escriben en el mismo archivo: ejecutar en orden.

---

## Estrategia de implementación

### MVP primero (solo US1)

1. Completar Fase 1 y Fase 2.
2. Completar US1 (cabecera + estado).
3. Ejecutar `uv run streamlit run app.py` y validar reconocimiento de marca.
4. Detenerse y validar el MVP antes de US2–US5.

### Entrega incremental

1. Preparación + Fundamentos → tokens y tema listos.
2. US1 → cabecera reconocible (MVP).
3. US2 → jerarquía de lectura.
4. US3 → tarjetas de fuente.
5. US4 → estados accesibles.
6. US5 → aviso académico.
7. Pulido → ADR, README, verificación manual y bitácora.

### Estrategia con dos integrantes

1. Ambos completan Preparación + Fundamentos.
2. Jason: US1 y US4 (cabecera y estados).
3. Roberto: US2, US3 y US5 (jerarquía, tarjetas y pie).
4. Integrar en orden US1 → US2 → US3 → US4 → US5 validando cada punto de control.

---

## Notas

- `[P]` indica archivos distintos y sin dependencia pendiente; no implica que la historia esté terminada.
- Cada tarea debe dejar `uv run ruff check .` y `uv run pytest` en verde.
- No se versionan imágenes ni tipografías del sitio oficial: solo color y tratamiento tipográfico.
- El CSS se inyecta con `st.html`; `app.py` mantiene la prohibición de `unsafe_allow_html`.
- Ninguna variante de estado puede comunicarse solo con color.
- La identidad no modifica respuestas, citas ni datos del corpus.
