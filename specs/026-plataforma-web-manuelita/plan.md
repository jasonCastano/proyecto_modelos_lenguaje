# Implementation Plan: Plataforma web profesional de Valer-IA para Manuelita (idea 7) con planificación industrial

**Branch**: `026-plataforma-web-manuelita` | **Date**: 2026-11-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/026-plataforma-web-manuelita/spec.md`

**Autor**: Roberto José Guerrero

## Summary

La web pasa de ser la página editorial de los Módulos 1 y 2 a ser la **cara de la plataforma de agentes** de la
spec 025, en cuatro áreas con su propia dirección:

- `/`: entrada pública;
- `/agente`: espacio de trabajo por perfil;
- `/planificacion`: consola visual del planificador;
- `/evidencia`: panel técnico del Módulo 3.

**Frontend**. La SPA de React, Vite y TypeScript se conserva, sin Streamlit. Gana:

- un enrutador mínimo propio;
- un sistema visual nuevo hecho con la skill `frontend-design` ([`design.md`](design.md)): una sola familia
  tipográfica, Archivo variable, donde el ancho distingue el titular, el texto y las cifras; un color de Manuelita
  por producto; y el **flujo de caña** en SVG como elemento memorable.

Los componentes de chat, voz, dictado y aprobación se reubican sin cambiar su conducta.

**Backend**. Gana dos routers versionados bajo `/api/v1/`:

- **planificación**: estado, plan, comparación y propuesta en dos pasos;
- **evidencia**: herramientas, trazas, servicios y evaluaciones.

Ambos reutilizan `planning.optimize`, `profiles.is_authorized` y `actions.save_proposal`, así que consola, agente y
CLI dan las mismas cifras por construcción. Hay dos cambios de dominio menores:

- tres precios opcionales en `Scenario`;
- la función pura `planning.compare`.

## Technical Context

**Language/Version**: Python 3.14 (backend, `uv`); TypeScript 5.9 y React 19 (web, npm)

**Primary Dependencies**:

- **Backend**: FastAPI y Pydantic v2, ya presentes; `scipy` (HiGHS) para el LP de la spec 025.
- **Web**: React 19 y Vite 7.
- **Nuevas**:
  - `@fontsource-variable/archivo`, que reemplaza a Bricolage Grotesque y Public Sans;
  - `axe-core`, solo en desarrollo, para las pruebas de accesibilidad.

  No se añade ninguna dependencia de Python.

**Storage**:

- Sin base de datos nueva.
- Lectura de `data/synthetic/planificacion/v1/`.
- Escritura solo en el directorio de estado (`resolve_state_dir()`): `planning/proposals.jsonl`, el de la spec 025,
  y `planning/console.jsonl`, nuevo.
- `config/evaluations.toml` es nuevo y versionado, de solo lectura.

**Testing**:

- pytest: unidad, API e integración, sin red;
- vitest con Testing Library;
- Playwright (`make e2e`) con `axe-core`.

**Target Platform**:

- **Servidor**: el PC servidor Windows o Linux de la demo (`make app`, uvicorn).
- **Clientes**: navegadores de escritorio y móviles evergreen, y el proyector del salón.

**Project Type**: aplicación web, con el backend FastAPI en `src/` y la SPA en `web/`, servida por el mismo proceso.

**Performance Goals**:

- un plan en menos de 5 s de extremo a extremo (el LP tarda menos de 0,5 s; SC-002);
- la entrada se pinta en menos de 2 s (SC-009);
- el bundle de JS, comprimido, pesa 250 kB o menos.

**Constraints**:

- Sin red ni claves en las pruebas.
- Cero cambios de conducta en `/api/chat`, `/api/channels/*`, la voz y la memoria (FR-029).
- Contraste AA.
- De 360 a 1920 px sin desplazamiento horizontal.
- Ninguna cifra de planta se calcula en el navegador.

**Scale/Scope**:

- 4 rutas;
- unos 25 componentes nuevos o reubicados;
- 9 endpoints nuevos;
- 1 a 20 usuarios simultáneos en la demo.

Sin incógnitas abiertas: todas quedan resueltas en [`research.md`](research.md), R1 a R15.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.* Referencia: `CONSTITUTION.md` 2.0.0
(pendiente de aprobación en el PR #79) y `.specify/memory/constitution.md`.

| Regla | Cumplimiento del diseño | Estado |
|---|---|:-:|
| Autoría (§4.3, ADR 0017) | Commits y PR a nombre de Roberto José Guerrero (Robertto48), sin coautores ni firmas de herramientas | ✅ |
| I. Reproducibilidad | `uv sync --frozen` y `npm ci`; datos sintéticos con semilla; la paridad se prueba con la batería fija de 12 escenarios | ✅ |
| II. Evaluación con métricas y línea base | Regresión de las baterías de la spec 025 (SC-007); el panel publica las cifras vigentes sin ocultar las que no cumplen | ✅ |
| III. Procedencia y ética | Etiqueta sintética en cada vista de planta; seudónimos; `redact_pii` en trazas y notas; ilustraciones propias, sin piezas de la marca; declaración de no afiliación | ✅ |
| IV. Experimentos como código | Contratos versionados en `contracts/`; `config/evaluations.toml` versionado | ✅ |
| V. Simplicidad | Sin framework nuevo ni librería de gráficos ni de rutas; reutiliza `optimize`, `is_authorized` y `save_proposal` | ✅ |
| §3.7 Aplicación web | React y Vite servida por FastAPI; sin Streamlit. Se conservan Consulta, Resumen y FAQ, el modo demo, la voz, el dictado y la presentación de Valer-IA. §3.7 se actualiza con las cuatro áreas | ✅ (se enmienda en el mismo commit) |
| Fase 3, reglas 8–15 | Un solo agente; catálogo único (26, sin herramientas nuevas); MCP sin cambios; SQLite; hardening intacto | ✅ |
| Fase 3, regla 18 (datos sintéticos) | `synthetic: true` y etiqueta en las respuestas v1 y en la UI | ✅ |
| Fase 3, regla 19 (cifras de planificación) | Cifras solo del LP del servidor; sin relajar capacidades; `steam_limit` solo baja la capacidad; frase de decisión | ✅ |
| Fase 3, regla 20 (autorización) | El 403 del backend es la barrera; la UI solo refleja `access`; confirmación en dos pasos con vencimiento de 5 minutos | ✅ |
| Revisión cruzada | PR a `main` con revisión de Jason; sin fusionar por cuenta propia | ⏳ al PR |
| Transparencia de IA | Sin prompts nuevos; «Explicar con el agente» usa el prompt `planning` vigente, sin entrada nueva en `prompt_log.md` | ✅ |

**Re-check post-diseño (Fase 1)**: sin violaciones. Hay dos puntos que se justifican en *Complexity Tracking*:

- el prefijo `/api/v1` convive con las rutas sin versión;
- `Scenario` gana campos, lo que cambia el esquema de una herramienta.

## Project Structure

### Documentation (this feature)

```text
specs/026-plataforma-web-manuelita/
├── spec.md
├── plan.md              # este archivo
├── research.md          # R1–R15
├── design.md            # dirección visual (frontend-design)
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── planning-api.md
│   ├── evidence-api.md
│   └── web-ui.md
├── checklists/requirements.md
└── tasks.md             # lo genera /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── api.py                    # incluye los routers v1 (sin cambiar rutas existentes)
├── api_planning.py           # NUEVO: /api/v1/planning/* (R4, R5, R9, R12)
├── api_evidence.py           # NUEVO: /api/v1/evidence/* (R11)
├── api_models.py             # modelos v1: PlantSnapshot, PlanComparison, Pending/ProposalDecision, Evidence*
├── brand.py                  # pares de contraste nuevos (tinta sobre naranja, lima y amarillo)
└── agent/
    ├── planning.py           # Scenario con price_*_pct; resolve/objetivo; compare(); snapshot()
    └── tools_planning.py     # el esquema hereda los precios opcionales
config/evaluations.toml       # NUEVO: cifras publicadas (R11)

web/src/
├── App.tsx                   # AppShell + router
├── lib/router.ts             # NUEVO (R2)
├── lib/planning.ts           # NUEVO: cliente /api/v1/planning
├── lib/evidence.ts           # NUEVO: cliente /api/v1/evidence
├── styles/tokens.css         # tokens de design.md
├── styles/global.css         # reescrito por áreas
├── pages/                    # NUEVO: Home, Agent, Planning, Evidence
└── components/
    ├── shell/                # AppShell, CaneRail, TopBar, AcademicFooter
    ├── brand/ProductGlyphs.tsx   # pictogramas (reemplaza CaneField y ProductMotifs)
    ├── home/                 # PlatformHero, ProfileLedger, Guarantees
    ├── agent/                # ProfilePicker, SourcesPanel, MemoryPanel, ProfileSuggestions (+ ChatView actual)
    ├── planning/             # ScenarioForm, CaneFlow, CommitmentLedger, PlantStatePanel,
    │                         #   ComparisonView, ProposalDialog, PlannerGate
    └── evidence/             # ServiceStatusBar, ToolCatalogTable, TraceViewer, EvaluationsTable

tests/
├── api/test_planning_api.py, test_evidence_api.py              # NUEVOS
├── integration/test_console_parity.py                          # NUEVO (SC-003)
├── unit/test_planning_compare.py, test_scenario_prices.py      # NUEVOS
└── e2e/test_platform.py (NUEVO), test_responsive.py (4 rutas)
web/src/test/                 # router, CaneFlow, ScenarioForm, ProposalDialog, páginas
```

**Structure Decision**: se mantiene la estructura vigente: backend en `src/proyecto_modelos_lenguaje/` y SPA en
`web/`, servida por el mismo proceso. Lo nuevo del backend va en routers aparte para no seguir creciendo `api.py`.
El frontend se organiza por áreas (`pages/` y `components/<área>/`), y los componentes vigentes se mueven sin
cambiar su conducta:

- `ChatView`, `ApprovalCard`, `MicButton` y `VoiceControls` pasan a `/agente`;
- `RagConsole` y `TaskTabs` pasan a `/`.

## Orden de implementación (resumen para `/speckit-tasks`)

1. **Núcleo**:
   - `Scenario` con precios, más su regresión;
   - `compare` y `snapshot`;
   - los routers v1 con autorización, errores y registro;
   - `config/evaluations.toml`;
   - los tokens y la tipografía;
   - el enrutador y el `AppShell`.
2. **Historia 1 (P1)**:
   - la consola completa;
   - la prueba de paridad;
   - la propuesta en dos pasos;
   - «Explicar con el agente».
3. **Historia 2 (P1)**:
   - la entrada con el libro de perfiles y los pictogramas;
   - `/agente`, reubicando el chat, con los paneles de fuentes, memoria y sugerencias.
4. **Historia 3 (P2)**: el panel de evidencia.
5. **Historia 4 (P2)**:
   - responsive a 360 px;
   - `axe-core`;
   - movimiento reducido.
6. **Cierre**:
   - el README y sus capturas;
   - el ADR 0030;
   - `CONSTITUTION.md` §3.7;
   - la rúbrica;
   - `herramientas.md`;
   - Archify;
   - `make check` y `make e2e`.

## Complexity Tracking

| Violación o tensión | Por qué hace falta | Alternativa más simple descartada |
|---|---|---|
| Rutas `/api/v1/*` junto a `/api/*` sin versión | Hay que versionar los contratos nuevos (FR-025) sin romper el puente de WhatsApp ni las pruebas del Módulo 3 a días de la sustentación | Migrar todo a v1: es un riesgo alto para el canal en producción |
| `Scenario` gana 3 campos y cambia el esquema de `optimize_production_plan` | La historia 1 pide escenarios de precio; las cifras deben salir del mismo LP (R6, R7) | Precios solo en la consola: habría dos fuentes de verdad. La regresión fija que con `None` nada cambia |
| Propuestas pendientes en memoria del proceso | La confirmación en dos pasos necesita un estado breve; un solo proceso en la demo | Tabla en SQLite: más esquema para un estado de 5 minutos |
