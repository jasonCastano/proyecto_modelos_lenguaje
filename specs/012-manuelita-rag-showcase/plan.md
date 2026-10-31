# Implementation Plan: Frontend profesional y showcase del Módulo 1

**Branch**: `012-manuelita-rag-showcase` | **Date**: 2026-10-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/012-manuelita-rag-showcase/spec.md`

## Summary

Construir una experiencia web propia de Manuelita que sustituya la interfaz Streamlit por una página editorial de una sola ruta. La página combina un hero de marca, una consola RAG con respuestas citadas, las tres tareas del Módulo 1 (consulta, resumen y FAQ) y un recorrido narrativo por el problema, los datos, la arquitectura medallion, los prompts, la app y las métricas.

La propuesta visual se llama **“Cañaveral editorial”**: paleta corporativa, tipografía con carácter, líneas de surco y cristales de azúcar como estructura, y una sola metáfora visual que conecta el campo con la evidencia. El frontend consume una API Python que reutiliza el RAG existente; la clave del proveedor permanece en el servidor y el modo demostración sigue disponible.

## Technical Context

**Language/Version**: Python 3.14 en el backend; TypeScript 5.x + React 19 en el frontend; Node.js 24 para el toolchain de desarrollo.

**Primary Dependencies**: FastAPI + Uvicorn para la API; LangChain, DeepSeek y los módulos existentes `tasks.py`, `retrieval.py`, `app_metrics.py` para el RAG. Frontend: React, Vite, TypeScript, `@fontsource-variable/bricolage-grotesque` y `@fontsource-variable/public-sans`. Sin kit de UI, sin Tailwind y sin librería global de estado.

**Storage**: Sin almacenamiento nuevo. La API lee `data/gold/` y los reportes existentes; la sesión de la persona vive en memoria del navegador. No se escribe en `data/` ni se persisten claves.

**Testing**: `pytest` + `httpx`/`TestClient` para API y contratos; Vitest + React Testing Library para componentes; Playwright (Python) para E2E, accesibilidad básica y matriz responsive. La suite existente de Python se mantiene.

**Target Platform**: Navegadores actuales de escritorio y móvil. Desarrollo local con Vite y API en `localhost`; producción con FastAPI sirviendo el build estático de `web/dist` en el mismo origen.

**Performance Goals**: LCP < 3 s en banda ancha; bundle JS inicial < 250 KB gzip; respuesta RAG percibida con estado de carga y timeout de 90 s; página usable en red lenta; sin desplazamiento horizontal entre 360 y 1920 px.

**Constraints**: La interfaz Streamlit deja de ser la entrada del producto; no se expone la clave en el cliente; no se cambia el corpus, los prompts ni la recuperación; modo demostración explícito; español; paleta corporativa; sin fotos de producto no documentadas; accesibilidad WCAG AA; la página declara su carácter académico.

**Scale/Scope**: Una página principal con 7 bloques narrativos (hero, consola RAG, problema, datos/medallion, prompts/tareas, métricas/evaluación, límites/fuentes), tres tareas RAG y dos modos (real/demo). El banco de 40 preguntas sigue siendo M1-08.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principio | Cumplimiento | Evidencia del plan |
|-----------|--------------|--------------------|
| I. Reproducibilidad experimental | ✅ | `uv.lock` y `package-lock.json` versionados; `uv sync --frozen` + `npm ci`; build reproducible; sin claves en el repo. |
| II. Evaluación con métricas y línea base | ✅ | Criterios medibles de performance, accesibilidad, citas y contenido; pruebas API/E2E y matriz responsive. |
| III. Procedencia y ética de datos | ✅ | Se reutiliza el corpus público existente; cada cita conserva URL, sección y autoridad; no se inventan productos ni cifras. |
| IV. Experimentos como código versionado | ✅ | API, frontend y pruebas viven en el repositorio; la narrativa y las métricas se cargan desde código/datos versionados. |
| V. Simplicidad y alcance académico | ✅ | Una sola página, una API pequeña, sin kit de UI ni estado global; React/Vite se justifica por la interacción y la calidad visual. |
| Restricciones técnicas | ✅ | Python 3.14 y `uv` para el backend; Node solo para el frontend; UTF-8; sin rutas absolutas ni secretos. |
| Flujo y puertas de calidad | ✅ | Spec → plan → tareas → implementación; PR con CI, pruebas y revisión. |

**Resultado**: sin violaciones. La incorporación de un toolchain Node se registra en Complexity Tracking por ser una decisión nueva.

## Project Structure

### Documentation (this feature)

```text
specs/012-manuelita-rag-showcase/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── api.md
│   ├── ui.md
│   ├── answer.schema.json
│   └── showcase.schema.json
└── tasks.md             # Fase 2 (/speckit.tasks; no se crea aquí)
```

### Source Code (repository root)

```text
web/
├── package.json
├── package-lock.json
├── index.html
├── vite.config.ts
├── tsconfig.json
├── src/
│   ├── main.tsx
│   ├── App.tsx
│   ├── styles/
│   │   ├── tokens.css          # paleta, tipo, espacio, radios
│   │   └── global.css          # composición editorial y responsive
│   ├── components/
│   │   ├── Hero.tsx
│   │   ├── CaneField.tsx       # metáfora visual principal
│   │   ├── RagConsole.tsx
│   │   ├── AnswerPanel.tsx
│   │   ├── SourceList.tsx
│   │   ├── TaskTabs.tsx        # consulta, resumen, FAQ
│   │   ├── ShowcaseStory.tsx
│   │   ├── MetricsBand.tsx
│   │   ├── ProductMotifs.tsx
│   │   ├── DemoBanner.tsx
│   │   └── Footer.tsx
│   ├── data/
│   │   └── showcase.ts         # narrativa y orden de secciones
│   ├── hooks/
│   │   └── useRag.ts
│   ├── lib/
│   │   ├── api.ts
│   │   └── types.ts
│   └── test/
│       ├── AnswerPanel.test.tsx
│       ├── RagConsole.test.tsx
│       └── ShowcaseStory.test.tsx
└── public/
    └── (SVG propios; sin fotos de producto)

src/proyecto_modelos_lenguaje/
├── api.py                     # FastAPI: health, ask, summary, faq, showcase
├── api_models.py              # modelos Pydantic de request/response
├── showcase.py                # payload de métricas y secciones desde datos reales
├── app_metrics.py             # reutilizado
├── tasks.py                   # reutilizado
└── retrieval.py               # reutilizado

tests/
├── api/
│   ├── test_api.py
│   └── test_contracts.py
└── e2e/
    └── test_showcase.py       # Playwright: flujo, responsive, foco, demo
```

**Structure Decision**: Aplicación web de un solo repositorio con backend Python y frontend React separados por una API JSON. El frontend se compila a `web/dist` y FastAPI lo sirve en producción; en desarrollo Vite hace proxy a `/api`. `app.py` y Streamlit salen de la ruta del producto; la migración se hace en tareas de retiro controlado para no romper pruebas antiguas a mitad de camino.

### Re-evaluación post-diseño

Tras generar `research.md`, `data-model.md`, `contracts/` y `quickstart.md`, el diseño sigue cumpliendo la constitución:

- La API reutiliza el RAG y no cambia datos, prompts ni recuperación.
- La clave permanece en el servidor; el contrato de respuesta no la expone.
- La paleta corporativa y los motivos de producto están definidos en tokens y contrato UI.
- El build de producción es reproducible con `uv.lock` + `package-lock.json`.
- Las pruebas cubren API, componentes, E2E, seguridad y responsive.

No aparecen violaciones nuevas. La única decisión que requiere seguimiento es el retiro definitivo de Streamlit al final de la migración.

## Design Direction — “Cañaveral editorial”

### Paleta

| Token | Hex | Uso |
|-------|-----|-----|
| `--forest` | `#387C2B` | Base institucional, titulares y superficies profundas |
| `--orange` | `#E86D1F` | Acento de cosecha, CTA y trazas activas |
| `--lime` | `#B0BC22` | Datos, progreso y detalles vivos |
| `--gold` | `#FFD200` | Energía, cifras destacadas y foco |
| `--paper` | `#F5F7F3` | Fondo principal cálido |
| `--ink` | `#14240F` | Texto y contraste |

Se añaden neutros derivados (`--ink-muted`, `--line`, `--surface-raised`) sin introducir una paleta nueva.

### Tipografía

- **Display**: Bricolage Grotesque variable, autohospedada y subseteada; titulares con gesto orgánico, no una serif de plantilla.
- **Cuerpo**: Public Sans variable, autohospedada; lectura clara en párrafos y UI.
- **Datos**: Public Sans con cifras tabulares; no se usa monospace como decoración.
- Escala editorial con titulares de gran tamaño, cuerpo de 17–18 px y line-length < 80 caracteres.

### Composición

- **Hero asimétrico**: titular a la izquierda, campo de caña dibujado con líneas SVG a la derecha; la línea de surco baja y conecta con la consola RAG.
- **Consola RAG**: panel “cuaderno de campo” con borde editorial, no una card SaaS; la respuesta se despliega sobre una veta de papel.
- **Narrativa del Módulo 1**: ledger vertical con bandas de datos, no una cuadrícula de tarjetas idénticas.
- **Cristales de azúcar**: separadores geométricos que agrupan métricas; **ondas de energía** para la sección de resultados; **palma** como marca secundaria en el cierre.
- **Productos**: los motivos se usan como estructura informativa (caña = pipeline, cristal = unidad de conocimiento, energía = evaluación), nunca como fotos inventadas.

### Principios

1. Un solo gesto visual memorable: el cañaveral lineal que recorre la página.
2. El contenido manda: cada borde, número o trazo explica algo.
3. Nada de chrome de plantilla: sin eyebrows en mayúsculas, sin “01/02/03” decorativos, sin tarjetas idénticas con sombra suave.
4. Movimiento escaso: una entrada orquestada en el hero y transiciones que responden a acciones; `prefers-reduced-motion` desactiva todo.
5. La página debe sentirse del Valle del Cauca y de una empresa agroindustrial, no de un dashboard genérico.

## Implementation Strategy

1. **Contratos primero**: definir los esquemas de respuesta y el contrato UI; escribir pruebas de API y componentes que fallen.
2. **Backend API**: implementar FastAPI con health, ask, summary, faq y showcase; reutilizar `tasks.py`, `retrieval.py` y `app_metrics.py`; aislar errores y no exponer la clave.
3. **Fundamentos visuales**: tokens CSS, fuentes autohospedadas, layout, foco, reduced motion y primitives de botón/entrada.
4. **Hero y consola RAG**: maquetar el gesto del cañaveral, la consola, estados de carga, respuesta, citas y fallback.
5. **Showcase del Módulo 1**: narrativa, bandas de métricas, evidencias, limitaciones y enlaces a documentación.
6. **Tareas Resumen/FAQ**: integrar los otros dos modos sin competir con la consulta principal.
7. **Demo y errores**: modo demo visible, sin clave, timeout, reintento y sesión en memoria.
8. **Migración**: retirar `app.py` y `streamlit` del flujo documentado; actualizar Makefile, README, CI y pruebas; conservar compatibilidad temporal solo durante la migración.
9. **Validación**: Vitest, pytest, Playwright, matriz responsive, axe/contraste y build de producción.

## Verification Strategy

### Matriz de experiencia

| Perfil | Ancho | Comprobación |
|--------|-------|--------------|
| Móvil pequeño | 360×640 | Hero legible, consola usable, sin scroll horizontal |
| Móvil | 390×844 | CTA y teclado accesibles |
| Tableta | 768×1024 | Narrativa en una columna, métricas legibles |
| Escritorio | 1440×900 | Hero asimétrico, consola y narrativa completos |
| Escritorio amplio | 1920×1080 | Composición editorial sin estirarse en exceso |

### Pruebas automatizadas

- API: contrato de `/api/ask`, `/api/summary`, `/api/faq`, `/api/showcase` y `/api/health`.
- Respuesta: `ok` exige citas; `fallback` no las tiene; error tiene código accionable.
- Seguridad: la clave no aparece en payloads, logs, HTML ni bundle.
- Frontend: componentes, estados de carga/error, foco y navegación por teclado.
- E2E: pregunta real/demo, fallback, cambio de tarea, móvil, reduced motion y ausencia de scroll horizontal.
- Contenido: cifras del showcase contra `app_metrics`; enlaces de fuentes presentes.

### Puertas

- `make check` para Python; `npm run test` y `npm run build` para web.
- Playwright E2E sin red usando modo demo.
- Revisión visual en 360, 768, 1440 y 1920 con capturas propias.
- Contraste 4.5:1, foco visible y `prefers-reduced-motion`.
- Cero secretos o rutas absolutas en el build.

## Complexity Tracking

| Decisión | Por qué se necesita | Alternativa rechazada |
|----------|---------------------|------------------------|
| Añadir toolchain Node/React/Vite | La interfaz Streamlit se retira y se necesita una experiencia editorial interactiva, componentes comprobables y build estático. | Jinja/HTMX reduce herramientas, pero limita la composición rica, el estado de la consola y las pruebas de componentes que pide el diseño. |
| Añadir FastAPI/Uvicorn | El RAG ya vive en Python; una API pequeña expone las tareas sin reescribir la lógica ni exponer la clave. | Un cliente que llame directamente a DeepSeek expondría la clave; un backend Node duplicaría la lógica. |
| Autohospedar dos fuentes variables | La tipografía es parte de la identidad y no debe depender de una CDN. | Fuentes del sistema: legibles, pero genéricas y contrarias al encargo de identidad. |
