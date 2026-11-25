# Implementation Plan: Perfiles abiertos en la web, incluido el planificador

**Branch**: `027-perfiles-abiertos-web` | **Date**: 2026-11-25 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/027-perfiles-abiertos-web/spec.md`

## Summary

En la web, los cinco perfiles pasan a ser de libre elección, incluido el planificador industrial. El cambio de
backend es pequeño y está en un solo punto: la autorización del planificador pasa a depender del **canal**. En
`web` siempre está permitida; en `whatsapp` sigue la lista de autorizados (research R1). Todo lo que hoy consulta
esa regla queda abierto sin tocar su lógica: la API v1 de planificación, `/api/profiles`, el perfil del turno y la
detección «soy planificador».

En el frontend se retiran el candado, los rótulos «solo autorizados», las opciones deshabilitadas y la pantalla
`PlannerGate`. El selector de perfil se rediseña con la skill frontend-design para que la persona **elija** con
información (R4–R6, [design.md](design.md)): para quién es cada perfil, qué puede pedir y un ejemplo. Además, la
interfaz indica el perfil activo y, si es el planificador, ofrece abrir la consola con la advertencia de datos
sintéticos.

Se conservan todas las salvaguardas: dos pasos para guardar propuestas, vencimiento, límite, registro seudónimo,
cifras solo del servidor y paridad 12/12. La constitución sube a 2.2.0 (regla 20 y §3.7) con la aprobación de
jasonCastano.

## Technical Context

**Language/Version**: Python 3.14 (backend, `uv`); TypeScript 5 + React 19 + Vite (web), Node 24.

**Primary Dependencies**: FastAPI, Pydantic, LangGraph, como hoy. No se añade ninguna dependencia.

**Storage**: sin cambios. Las propuestas siguen en `$MANUELITA_STATE_DIR/planning/proposals.jsonl` y el registro
de la consola en `console.jsonl`.

**Testing**: pytest (unit, api, integration), Vitest + Testing Library, Playwright + axe-core (`make e2e`).

**Target Platform**: servidor local FastAPI que sirve `web/dist`, y navegadores de escritorio y teléfono (360–1920
px).

**Project Type**: aplicación web (backend Python + SPA React en el mismo repositorio).

**Performance Goals**: sin metas nuevas. Se mantienen las de la spec 026 (JS ≤ 120 kB gzip y entrada < 1 s en
local).

**Constraints**:
- Ningún cambio de forma en las rutas sin versión.
- `/api/v1/planning/access` se conserva por compatibilidad: siempre responde `authorized: true` en la web.
- WhatsApp y el MCP no cambian.

**Scale/Scope**:
- Backend: 4 módulos (`agent/profiles.py`, `agent/service.py`, `agent/graph.py` solo textos, `api_planning.py`).
- Web: 9 componentes o páginas.
- Unas 10 pruebas para actualizar, más la documentación.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Regla (CONSTITUTION.md) | Estado | Nota |
|---|---|---|
| §3.7 «Todo `/api/v1/planning/*`, salvo `/access`, DEBE exigir el planificador autorizado» | ⚠️ **Se enmienda** | La spec lo pide de forma explícita. La enmienda MINOR 2.2.0 cambia el texto a «la web abre el planificador a cualquiera; la autorización por canal vive en el backend». Requiere la aprobación de jasonCastano (FR-016). |
| Regla 20 «El perfil planificador es solo para usuarios autorizados» | ⚠️ **Se enmienda** | Pasa a «en WhatsApp, solo autorizados; en la web, libre elección». Se conservan los dos pasos, que ninguna herramienta toque sistemas reales y que el modo degradado no planifique. |
| Regla 18: datos sintéticos declarados y separados del corpus | ✅ | FR-012: cada pantalla y respuesta del planificador mantiene la advertencia. |
| Regla 19: cifras solo del optimizador | ✅ | FR-013: paridad 12/12 sin cambios (`tests/integration/test_console_parity.py`). |
| §3.7: cifras no calculadas en el navegador | ✅ | No se toca `CaneFlow` ni la consola. |
| §4.3 autoría (solo Robertto48 o jasonCastano, sin firmas de bot) | ✅ | Commit y PR a nombre de Roberto José Guerrero. |
| Cambios de arquitectura o proceso actualizan la constitución en el mismo commit | ✅ | Enmienda 2.2.0, ADR 0031 y fila del historial en el mismo commit. |
| Identidad visual de la spec 026 (colores por producto, Archivo, AA, sin desplazamiento horizontal) | ✅ | [design.md](design.md) reutiliza tokens y glifos; axe-core y 360/1440 px en E2E. |

**Resultado**: pasa con dos enmiendas justificadas por la spec (ver Complexity Tracking). No hay violaciones sin
justificar.

**Re-check post-design**: la misma tabla después de Phase 1. El diseño no añade otras desviaciones: solo cambia la
regla por canal, la interfaz y la documentación. ✅

## Project Structure

### Documentation (this feature)

```text
specs/027-perfiles-abiertos-web/
├── spec.md
├── plan.md              # este archivo
├── research.md          # R1–R9
├── design.md            # dirección visual del selector (frontend-design)
├── data-model.md        # Perfil por canal, opción de perfil, acceso
├── quickstart.md        # validación de punta a punta
├── contracts/
│   ├── profiles-api.md  # GET /api/profiles y ChatRequest.profile en la web
│   ├── planning-api.md  # /api/v1/planning sin 403 en la web
│   └── web-ui.md        # selector, entrada, consola y vista técnica
├── checklists/requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/proyecto_modelos_lenguaje/
├── agent/profiles.py        # is_authorized por canal; describe() con requires_authorization por canal
├── agent/service.py         # validate_profile: sin 403 en la web (cambia solo por la regla de canal)
├── agent/graph.py           # PLANNER_ONLY_NOTE solo aplica fuera de la web (texto)
├── api_planning.py          # require_planner → web_user (registra el seudónimo, sin 403); /access siempre true
├── agent/planning_eval.py   # deja de fijar MANUELITA_PLANNER_WEB
└── channels/bridge.py       # sin cambios de lógica (WhatsApp conserva la lista)

web/src/
├── components/agent/ProfilePicker.tsx       # rediseño: cinco opciones elegibles con «para quién» y ejemplo
├── components/agent/ProfileNotice.tsx       # nuevo: perfil activo y, si es planificador, aviso de datos sintéticos + abrir consola
├── components/home/ProfileLedger.tsx        # sin candado: las cinco filas con su ejemplo
├── components/home/PlatformHero.tsx         # «Abrir la planificación» siempre
├── components/planning/PlannerGate.tsx      # se elimina
├── components/ChatView.tsx                  # vista técnica: <option> sin disabled ni «solo autorizados»
├── data/profileSuggestions.ts               # campo nuevo forWhom («para quién es»)
├── pages/Agent.tsx, Planning.tsx, Home.tsx, App.tsx   # sin estado de autorización; /planificacion fija el perfil
└── styles/platform.css                      # estilos del selector rediseñado; se retiran .planner-gate y __locked

tests/
├── unit/agent/test_profiles.py              # web siempre autorizada; whatsapp con lista
├── unit/channels/test_bridge_profile.py     # sin cambios esperados (regresión de WhatsApp)
├── api/test_planning_api.py, test_planning_proposals.py, test_profiles_api.py, test_evidence_api.py
├── integration/agent/test_planning_flow.py, test_profile_flow.py, test_console_parity.py
└── e2e/conftest.py (sin MANUELITA_PLANNER_WEB), test_platform.py, test_accessibility.py

docs/decisions/0031-perfiles-abiertos-web.md, CONSTITUTION.md (2.2.0), README.md, .env.example,
docs/rubrica_modulo3.md, docs/prompt_log.md (si cambia un texto del prompt; no se prevé)
```

**Structure Decision**: es el mismo repositorio de la spec 026, con el backend en `src/proyecto_modelos_lenguaje/`
y la SPA en `web/`. No se crean módulos de backend. En la web solo se crea `ProfileNotice.tsx` y se elimina
`PlannerGate.tsx`.

## Prerrequisito de ramas

El arreglo «la web se compila al clonar» (rama local `fix-web-al-clonar`, todavía sin commit) toca `README.md`,
`.env.example` y `CONSTITUTION.md`, igual que esta spec. Orden propuesto:

1. Hacer commit del arreglo, abrir su PR y fusionarlo.
2. Crear `027-perfiles-abiertos-web` desde `main`.
3. Mover a esa rama los documentos de esta spec (archivos nuevos, sin conflicto).

Si el arreglo sigue abierto cuando se implemente, la rama 027 se crea desde `main` y se rebasa al fusionarse.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| Enmienda de §3.7: `/api/v1/planning/*` ya no exige el planificador autorizado en la web | La spec lo pide: cualquier cliente elige su perfil (FR-001, FR-002) | Activar `MANUELITA_PLANNER_WEB=1` por defecto en `.env.example` deja el control en una variable que cada equipo puede olvidar. Es justo lo que confundió al propietario del repositorio. |
| Enmienda de la regla 20: el planificador es de libre elección en la web | Misma razón. Los datos son sintéticos y las propuestas no se ejecutan en ninguna planta | Abrirlo también en WhatsApp amplía el riesgo a un número real y queda fuera de lo pedido (FR-014). |
