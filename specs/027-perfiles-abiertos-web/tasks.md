---

description: "Task list for spec 027: perfiles abiertos en la web, incluido el planificador"
---

# Tasks: Perfiles abiertos en la web, incluido el planificador

**Input**: Design documents from `/specs/027-perfiles-abiertos-web/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md),
[data-model.md](data-model.md), [design.md](design.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: se incluyen. La constitución exige `make check` en verde y la spec mide sus criterios de éxito con
pruebas (SC-001, SC-002, SC-004, SC-005 y SC-006). Las pruebas de cada historia se escriben primero y deben
fallar antes del cambio.

**Organization**: tareas agrupadas por historia de usuario. Backend en `src/proyecto_modelos_lenguaje/`, web en
`web/src/` y pruebas en `tests/` y `web/src/test/`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia de la spec (US1, US2, US3).

---

## Phase 1: Setup

**Purpose**: rama limpia sobre `main` y línea base medida antes del cambio.

- [X] T001 Confirmar que el arreglo `fix-web-al-clonar` ya tiene commit y PR. Después, crear la rama
  `027-perfiles-abiertos-web` desde `main` actualizado y llevar `specs/027-perfiles-abiertos-web/` y
  `.specify/feature.json` (plan.md, «Prerrequisito de ramas»).
- [X] T002 Con `MANUELITA_PLANNER_WEB`, `MANUELITA_PLANNER_OPEN` y `VALERIA_PLANNERS` fuera del entorno, registrar
  la línea base en `specs/027-perfiles-abiertos-web/quickstart.md` §7 (sección nueva):
  - `GET /api/v1/planning/state` → 403.
  - `GET /api/profiles` → planificador `authorized: false`.
  - `uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct` → 10/10.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: la regla de autorización por canal (research R1, R2 y R7). Todas las historias dependen de ella.

**⚠️ CRITICAL**: ninguna historia empieza antes de esta fase.

- [X] T003 Reescribir las pruebas de la regla en `tests/unit/agent/test_profiles.py`:
  - `is_authorized(any_user, "web")` es `True` sin variables, y también con `MANUELITA_PLANNER_WEB=0`.
  - `is_authorized("wa-x", "whatsapp")` es `False` sin variables, `True` si `wa-x` está en `VALERIA_PLANNERS` y
    `True` con `MANUELITA_PLANNER_OPEN=1`.
  - `MANUELITA_PLANNER_WEB=1` no afecta a `"whatsapp"`.
  - `effective_profile("planificador", "anon", "web") == "planificador"`.
  - `describe("anon", "web")`: los 5 perfiles con `authorized: True` y `requires_authorization: False`.
  - `describe("wa-x", "whatsapp")`: el planificador con `requires_authorization: True` y `authorized: False`.

  Deben fallar.
- [X] T004 En `src/proyecto_modelos_lenguaje/agent/profiles.py`:
  - `is_authorized` devuelve `True` si `channel == "web"`; fuera de la web conserva `MANUELITA_PLANNER_OPEN` y
    `VALERIA_PLANNERS`, y ya no lee `MANUELITA_PLANNER_WEB`.
  - Añadir `Profile.requires_authorization_in(channel) -> bool` (`requires_authorization and channel != "web"`).
  - `describe()` usa ese método para `requires_authorization` y `authorized` (ver `to_dict`).
  - Actualizar el docstring del módulo: «en la web, libre elección; en WhatsApp, lista de autorizados».

  T003 en verde.
- [X] T005 [P] Fijar la regresión de WhatsApp en `tests/unit/channels/test_bridge_profile.py`. Con los tres
  envs limpios, `/perfil planificador` responde `PLANNER_DENIED_TEXT` con el evento `planner_denied`, y `/perfil`
  lista «(solo autorizados)». Debe pasar sin tocar `src/proyecto_modelos_lenguaje/channels/bridge.py`.

**Checkpoint**: la regla por canal existe y WhatsApp no cambió.

---

## Phase 3: User Story 1 - Usar el planificador sin pedir permiso (Priority: P1) 🎯 MVP

**Goal**: sin configuración, la API v1 de planificación, `/api/profiles`, el chat con perfil planificador y
«soy planificador» funcionan para cualquier visitante web. La consola `/planificacion` carga sin pantalla de
acceso.

**Independent Test**: con los envs limpios, `make app`, abrir `/planificacion` → estado, escenario y plan. En
`/agente` con el planificador, «Tenemos 15 % menos caña…» → plan con la restricción y la advertencia de datos
sintéticos.

### Tests for User Story 1 ⚠️

- [X] T006 [P] [US1] En `tests/api/test_planning_api.py`:
  - Quitar los `setenv("MANUELITA_PLANNER_WEB", "1")` y las pruebas de 403.
  - Probar que, con los envs limpios y **sin** `X-User-Id`, `GET /access` es 200 `{"authorized": true}` con un
    `reason` que menciona «sintéticos», y `GET /state`, `POST /plan` y `POST /compare` son 200.
  - Probar que un `X-User-Id` inválido se registra como `anon` en `console.jsonl`.
  - Probar que la respuesta nunca contiene `planner_forbidden` (contracts/planning-api.md).
- [X] T007 [P] [US1] En `tests/api/test_planning_proposals.py`:
  - Quitar `setenv("MANUELITA_PLANNER_WEB", "1")`.
  - Probar que, sin envs, `POST /proposals` → 202 y `POST /proposals/{confirmation_id}` con `yes` escribe en
    `proposals.jsonl` con el `user_id` seudónimo.
  - Conservar las pruebas de vencimiento (410), desconocida (404) y límite de 100 pendientes (FR-010, FR-011).
- [X] T008 [P] [US1] En `tests/api/test_profiles_api.py`, quitar `setenv("MANUELITA_PLANNER_WEB", "1")` y probar:
  - `GET /api/profiles?user_id=anon` devuelve los 5 perfiles con `authorized: true` y `requires_authorization:
    false` (contracts/profiles-api.md).
  - `POST /api/chat` con `profile="planificador"` en modo demo no devuelve 403 `planner_not_authorized`.
  - Un perfil desconocido sigue devolviendo 400 `invalid_profile`.
- [X] T009 [P] [US1] En `tests/integration/agent/test_planning_flow.py`:
  - Quitar el `setenv` de la línea 88.
  - La prueba de la línea 154 (sin envs) pasa a esperar que el turno web con «Tenemos 15 % menos caña» corra
    con el perfil planificador y llame al optimizador, sin `PLANNER_ONLY_NOTE`.
  - Añadir el caso «soy planificador de planta, …» en la web: cambia de perfil y planifica.
- [X] T010 [P] [US1] En `tests/integration/agent/test_profile_flow.py`, cubrir el canal web: el planificador elegido
  en el turno no se degrada a visitante. Cubrir también el canal `whatsapp` sin lista: sí se degrada y aparece
  la nota de WhatsApp.
- [X] T011 [P] [US1] En `tests/integration/test_console_parity.py` (línea 33), quitar
  `mp.setenv("MANUELITA_PLANNER_WEB", "1")`. La paridad 12/12 debe seguir en verde sin envs (SC-005).
- [X] T012 [P] [US1] En `tests/api/test_evidence_api.py`, verificar que el catálogo sigue reportando
  `save_production_proposal` solo para el perfil planificador. Es una regla de herramientas, no de autorización.
  Ajustar solo si cambia el texto de perfiles.
- [X] T013 [P] [US1] En `web/src/test/PlanningPage.test.tsx`:
  - Retirar las pruebas de `PlannerGate` y de `getAccess` con `authorized: false`.
  - Probar que la página carga estado y escenario sin pedir `/access`.
  - Probar que no existe `[data-testid=planner-gate]`.
  - Probar que al montar llama a `setAudience("planificador")`.

### Implementation for User Story 1

- [X] T014 [US1] En `src/proyecto_modelos_lenguaje/api_planning.py`:
  - Renombrar `require_planner` a `planner_user`: devuelve `web_user(request)` sin lanzar `ApiV1Error`.
  - Actualizar los `Depends` de `/state`, `/plan`, `/compare`, `/proposals` y `/proposals/{confirmation_id}`.
  - Retirar `FORBIDDEN_TEXT` y el import de `is_authorized`.
  - `/access` devuelve `PlanningAccess(authorized=True, reason="Planificación abierta en la web. Los datos de
    planta son sintéticos.")`.
  - Actualizar el docstring del módulo (research R3).
- [X] T015 [US1] En `src/proyecto_modelos_lenguaje/agent/service.py`, ajustar el docstring de `validate_profile`
  (`planner_not_authorized` solo fuera de la web). El código no cambia, porque usa `profiles.is_authorized` con el
  canal (research R1).
- [X] T016 [US1] En `src/proyecto_modelos_lenguaje/agent/graph.py`, reescribir `PLANNER_ONLY_NOTE`: «Por WhatsApp,
  la planificación de producción es solo para planificadores autorizados; en la web puedes elegir el perfil
  planificador.» (research R8).
- [X] T017 [US1] En `src/proyecto_modelos_lenguaje/agent/planning_eval.py` (línea 363), retirar
  `os.environ.setdefault("MANUELITA_PLANNER_WEB", "1")`.
- [X] T018 [US1] Eliminar `web/src/components/planning/PlannerGate.tsx` y en `web/src/pages/Planning.tsx`:
  - Quitar `getAccess()`, el estado `access`, el `return <PlannerGate …/>` (línea 121) y la rama
    `planner_forbidden` (línea 64).
  - Al montar, llamar a `setAudience("planificador")` de `web/src/lib/platform.ts`.
- [X] T019 [US1] En `web/src/lib/planning.ts`, conservar `getAccess` (contrato compatible) sin usarla desde la UI.
  En `web/src/lib/types.ts`, quitar el código `planner_forbidden` de la unión de errores si existe.
- [X] T020 [US1] En `web/src/styles/platform.css`, retirar `.planner-gate*` (incluida la regla de `@media` cerca
  de la línea 1537).

**Checkpoint**: la US1 se puede demostrar sola con `make app` y los envs limpios. Pasan `uv run pytest
tests/api tests/integration -q` y `npx vitest run src/test/PlanningPage.test.tsx`.

---

## Phase 4: User Story 2 - Elegir el perfil que más le conviene (Priority: P2)

**Goal**: los cinco perfiles en igualdad visual, cada uno con «para quién es». El perfil activo siempre visible y,
si es el planificador, el aviso de datos sintéticos con «Abrir la planificación». Sin candados en ninguna parte
([design.md](design.md)).

**Independent Test**: en `/agente`, recorrer los cinco perfiles con las flechas, leer «para quién» y elegir el
planificador: aparece `[data-testid=profile-notice]` con el aviso y el enlace. En `/`, la fila del planificador
tiene su consulta de ejemplo.

### Tests for User Story 2 ⚠️

- [X] T021 [P] [US2] En `web/src/test/AgentPage.test.tsx`, según contracts/web-ui.md:
  - Probar 5 `[role=radio]` sin `disabled` ni `aria-disabled`, cada uno con su texto `forWhom`.
  - Probar que ArrowRight, ArrowLeft, Home y End recorren los cinco, con el planificador incluido.
  - Probar que el planificador elegido muestra `[data-testid=profile-notice]` con «Te atiende como Planificador
    industrial», el texto de datos sintéticos y un enlace «Abrir la planificación» a `/planificacion`.
  - Probar que otro perfil muestra solo «Te atiende como {perfil}».
- [X] T022 [P] [US2] En `web/src/test/HomePage.test.tsx`:
  - Probar que la fila `[data-profile=planificador]` tiene el botón de ejemplo y que no existe
    `.profile-ledger__locked`.
  - Probar que el héroe dice «Abrir la planificación».
  - Quitar la prop `plannerAuthorized` de los renders.
- [X] T023 [P] [US2] En `web/src/test/App.test.tsx`, quitar los mocks de `getAccess` y las aserciones de
  `plannerAuthorized`. Probar que la app no llama a `/api/v1/planning/access` al cargar.
- [X] T024 [P] [US2] En `web/src/test/ChatView.test.tsx`, probar que el `<select>` de la vista técnica tiene 5
  `<option>` habilitados y que ningún texto contiene «solo autorizados».

### Implementation for User Story 2

- [X] T025 [US2] En `web/src/data/profileSuggestions.ts`, añadir `forWhom: string` a `AudienceCard`. El texto
  debe tener «≤ 40 caracteres, segunda persona» (data-model.md). Los textos exactos son: «Quieres conocer
  Manuelita», «Compras para tu empresa», «Entregas caña al ingenio», «Trabajas en Manuelita» y «Planeas la
  producción de la semana» (design.md, Copy).
- [X] T026 [US2] Rediseñar `web/src/components/agent/ProfilePicker.tsx` como registro de cinco columnas
  (design.md, Layout):
  - Cada radio muestra el glifo de `PRODUCT_GLYPHS`, el nombre y `forWhom`.
  - Sin `disabled`, `title` ni «(solo autorizados)».
  - Teclado: flechas más Home y End sobre las cinco opciones.
  - Cada opción expone `data-product` para que el CSS pinte el filete del color de su producto.
  - Actualizar el comentario de cabecera.
- [X] T027 [P] [US2] Crear `web/src/components/agent/ProfileNotice.tsx` con `data-testid="profile-notice"` y
  `aria-live="polite"`:
  - Siempre: «Te atiende como {label}.»
  - Si el perfil es `planificador`, añadir «Los datos de planta son sintéticos, no la operación real de
    Manuelita.» y `<Link className="action action--quiet" to="/planificacion">Abrir la planificación</Link>`.
- [X] T028 [US2] En `web/src/pages/Agent.tsx`:
  - Eliminar `FALLBACK` con `authorized: false`, el cálculo `allowed` y el `effective` degradado a visitante.
    Usar `audience` directamente y un fallback de los 5 perfiles con `authorized: true`.
  - Renderizar `<ProfileNotice>` debajo de `<ProfilePicker>`.
  - Conservar el encabezado «Habla con Valer-IA» sin duplicar el «Te atiende como…» que ahora da el aviso.
- [X] T029 [P] [US2] En `web/src/components/home/ProfileLedger.tsx`, quitar la prop `plannerAuthorized`, la
  variable `locked` y el `<p className="profile-ledger__locked">`. Las cinco filas usan el botón de ejemplo.
- [X] T030 [P] [US2] En `web/src/components/home/PlatformHero.tsx`, quitar la prop `plannerAuthorized`. La acción
  dice siempre «Abrir la planificación».
- [X] T031 [US2] En `web/src/pages/Home.tsx` y `web/src/App.tsx`, quitar la prop y el estado `plannerAuthorized`,
  el `useEffect` con `getAccess()` y su import (research R6).
- [X] T032 [P] [US2] En `web/src/components/ChatView.tsx` (líneas ~918–920), quitar `disabled={!option.authorized}`
  y el sufijo «(solo autorizados)» del `<option>`.
- [X] T033 [US2] En `web/src/styles/platform.css`, aplicar design.md:
  - `.profile-picker` como grilla de 5 columnas con filetes `--rule` y sin sombras.
  - `[aria-checked=true]` con filete superior de 3 px del color de `data-product` (`--cane`, `--sugar`,
    `--molasses`, `--power`), fondo `--surface` y nombre en `--cane-deep`.
  - Bajo 720 px, lista vertical con filas de 48 px y `forWhom` con elipsis.
  - Estilos de `.profile-notice`.
  - Retirar `.profile-picker__pill:disabled` y `.profile-ledger__locked` (incluida su regla en `@media`, cerca de
    la línea 1460).
  - Foco con `--focus` y sin animación nueva.

**Checkpoint**: las US1 y US2 funcionan juntas. `cd web && npx vitest run` en verde.

---

## Phase 5: User Story 3 - Documentación y reglas coherentes (Priority: P3)

**Goal**: nada en la documentación vigente pide autorizar el planificador en la web. La constitución registra la
enmienda.

**Independent Test**: el `git grep` de quickstart.md §5 solo encuentra menciones históricas y de WhatsApp.

- [X] T034 [P] [US3] En `.env.example`, retirar `MANUELITA_PLANNER_WEB` y su comentario. Aclarar en el comentario
  de `VALERIA_PLANNERS` y `MANUELITA_PLANNER_OPEN` que solo aplican a WhatsApp, porque en la web los cinco perfiles
  son de libre elección.
- [X] T035 [P] [US3] En `README.md`:
  - Quitar el párrafo de «Primeros pasos» que pide `MANUELITA_PLANNER_WEB=1`.
  - Corregir la viñeta «Planificador industrial (solo autorizados…)» (~línea 912): libre en la web, lista de
    autorizados en WhatsApp.
  - Corregir la fila `/planificacion` de la tabla web (~línea 949) y la frase «responde 403 `planner_forbidden`»
    (~línea 952).
  - Añadir una fila de estado para la spec 027.
- [X] T036 [P] [US3] Crear `docs/decisions/0031-perfiles-abiertos-web.md` (contexto, decisión R1, alternativas y
  consecuencias). Enlazarla desde la sección de decisiones del README.
- [X] T037 [US3] En `CONSTITUTION.md`:
  - Versión 2.2.0 (MINOR) y última enmienda 2026-11-25, en la cabecera y el pie.
  - §3.7: reemplazar «Todo `/api/v1/planning/*`, salvo `/access`, DEBE exigir el planificador autorizado…» por
    «En la web, los cinco perfiles y `/api/v1/planning/*` son de libre elección; la autorización por canal vive en
    el backend (`profiles.is_authorized`) y la UI no la reemplaza».
  - Regla 20: «El perfil planificador es de libre elección en la web y solo para autorizados en WhatsApp (lista
    fuera del repositorio)».
  - Fila 2.2.0 en el historial con la spec 027 y el ADR 0031.
  - Nota en el PR: requiere la aprobación de jasonCastano.
- [X] T038 [P] [US3] En `docs/rubrica_modulo3.md`, actualizar las menciones de acceso al planificador en la web.
  Revisar también `docs/manual_whatsapp.md` solo para confirmar que no cambia.
- [ ] T039 [P] [US3] Si `docs/diagramas/planificacion.json` o `docs/arquitectura.json` dicen «403 sin permiso»
  para la web, cambiar el `tag` a «libre en la web». Regenerar con Archify (`finalize` + `visual-check`) y
  actualizar las capturas en `docs/capturas/`.

**Checkpoint**: las tres historias están completas y la documentación es coherente.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T040 Actualizar `tests/e2e/conftest.py`: quitar `MANUELITA_PLANNER_WEB=1` y limpiar los tres envs del
  servidor E2E. En `tests/e2e/test_platform.py`, añadir el recorrido: elegir el planificador en `/agente`, ver el
  aviso, abrir la planificación y obtener un plan.
- [X] T041 En `tests/e2e/test_accessibility.py` y `tests/e2e/test_responsive.py`:
  - Probar que el texto «solo autorizados» y «Solo equipo de planta autorizado» no aparece en `/`, `/agente`,
    `/planificacion` ni `/evidencia`, a 360 y 1440 px (SC-004).
  - Probar axe-core sin violaciones serias en el selector nuevo.
- [X] T042 Correr `make check` y `make e2e` con los envs limpios. Correr
  `uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct`. Registrar los resultados en
  `specs/027-perfiles-abiertos-web/quickstart.md` §7 frente a la línea base de T002. El planning-eval debe dar
  10/10, 0 violaciones y 2/2 sin solución.
- [X] T043 Hacer la autocrítica de diseño (frontend-design) con capturas a 360 y 1440 px de `/` y `/agente`.
  Anotar en la sección Notes de este archivo qué se ajustó y qué accesorio se retiró.
- [ ] T044 Correr el `git grep` de quickstart.md §5 y confirmar SC-007. Hacer el commit a nombre de Robertto48 (sin
  firmas de bot) con la constitución, el ADR y el código en el mismo commit. El PR hacia `main` lo revisa
  jasonCastano y su cuerpo termina con «Autor: Roberto José Guerrero».

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 antes que todo, porque define la rama. T002 mide antes del cambio.
- **Foundational (Phase 2)**: T003 → T004, y T005 en paralelo. Bloquea las historias.
- **US1 (Phase 3)**: depende de Phase 2. Es el MVP.
- **US2 (Phase 4)**: depende de Phase 2. Se puede hacer en paralelo con US1 salvo en `web/src/styles/platform.css`
  (T020 y T033, en serie) y en `web/src/lib/platform.ts`, que solo se lee.
- **US3 (Phase 5)**: el texto depende de que US1 y US2 estén decididas. Puede empezar en paralelo y cerrarse al
  final.
- **Polish (Phase 6)**: después de US1, US2 y US3.

### User Story Dependencies

- **US1 (P1)**: solo Phase 2.
- **US2 (P2)**: solo Phase 2. `ProfileNotice` enlaza a `/planificacion`, que sin US1 mostraría la pantalla de
  acceso. Para demostrar US2 sola, basta con que exista la ruta.
- **US3 (P3)**: describe US1 y US2, así que no tiene dependencia de código.

### Within Each User Story

- Las pruebas primero, y deben fallar.
- Backend antes que web dentro de US1 (T014 antes de T018).
- Datos (T025) → componentes (T026 y T027) → páginas (T028 y T031) → estilos (T033) en US2.

### Parallel Opportunities

- Phase 2: T005 junto con T003 y T004.
- US1: las pruebas T006–T013 en paralelo. T015, T016 y T017 son archivos distintos.
- US2: las pruebas T021–T024 en paralelo. T027, T029, T030 y T032 en paralelo tras T025.
- US3: T034, T035, T036, T038 y T039 en paralelo. T037 es un solo archivo.

---

## Parallel Example: User Story 1

```text
Task: "T006 pruebas de /api/v1/planning sin envs en tests/api/test_planning_api.py"
Task: "T007 propuestas sin envs en tests/api/test_planning_proposals.py"
Task: "T008 /api/profiles abierto en tests/api/test_profiles_api.py"
Task: "T011 paridad 12/12 sin envs en tests/integration/test_console_parity.py"
Task: "T013 consola sin PlannerGate en web/src/test/PlanningPage.test.tsx"
```

## Parallel Example: User Story 2

```text
Task: "T027 ProfileNotice en web/src/components/agent/ProfileNotice.tsx"
Task: "T029 ProfileLedger sin candado en web/src/components/home/ProfileLedger.tsx"
Task: "T030 PlatformHero sin prop en web/src/components/home/PlatformHero.tsx"
Task: "T032 <option> habilitados en web/src/components/ChatView.tsx"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Phase 1 → Phase 2: la regla por canal.
2. Phase 3 (US1): API, chat y consola abiertos.
3. **Validar**: quickstart §1–§3 con los envs limpios. Esto ya resuelve «no me deja usar el planificador».

### Incremental Delivery

1. US1: cualquiera usa el planificador (MVP).
2. US2: el selector ayuda a elegir y desaparece todo rastro de bloqueo.
3. US3: documentación, constitución 2.2.0 y ADR 0031.
4. Polish: E2E, autocrítica de diseño y un solo PR para revisión.

---

## Notes

- [P] = archivos distintos, sin dependencias pendientes.
- WhatsApp (`channels/bridge.py`) y el MCP no se modifican. T005 lo protege.
- `config/profiles.toml` no cambia: `requires_authorization = true` sigue rigiendo fuera de la web.
- No cambia ningún prompt, así que no hay entrada en `docs/prompt_log.md` (research R8).
- No hacer push ni abrir el PR sin una petición explícita del integrante.

### Implementación (2026-11-25)

- **Rama**: `027-perfiles-abiertos-web` se creó sobre el commit del arreglo `fix-web-al-clonar` (0cdf5d4), que
  todavía no tiene PR. Ese arreglo toca README, `.env.example` y la constitución. Si el arreglo se fusiona antes,
  esta rama se rebasa sobre `main`.
- **Cambio fuera de las tareas, necesario para FR-003**: el perfil planificador no tenía disparadores
  (`triggers = []`), así que «soy planificador» no cambiaba de perfil. Se añadieron tres en
  `config/profiles.toml`. En WhatsApp sin autorización, presentarse como planificador ya no anuncia «Te atiendo como
  Planificador» (`graph.py`).
- **`enable_planner_for_eval`** se eliminó de `planning_eval.py` y de sus tres llamadas en `cli_m3.py`: las
  evaluaciones corren por la web, donde el planificador es de libre elección.
- **T012**: sin cambios. `test_evidence_api.py` ya verificaba que `save_production_proposal` es solo del perfil
  planificador.
- **T039 (Archify)**: los diagramas fijan `revision` a un commit en el que existan las fuentes; se regeneran en un
  commit aparte después del commit principal, como en la spec 026.
- **Autocrítica de diseño (T043)**, con capturas a 360 y 1440 px de `/` y `/agente`:
  1. El encabezado del agente mezclaba «Elige con qué perfil…» con la descripción del perfil activo. Ahora es una
     instrucción fija, y «qué puede pedir» pasa al aviso del perfil activo.
  2. Con el planificador, el aviso repetía «datos sintéticos» dos veces. Queda solo la advertencia explícita.
  3. El aviso ya no se limita a 66 caracteres de ancho: en escritorio ocupa una o dos líneas, no tres.
  4. Se mantiene a propósito: los glifos van en verde caña y no en el color de cada producto. El amarillo azúcar
     sobre blanco no llega a contraste AA, así que el color del producto vive solo en el filete del perfil activo.
  5. Accesorio retirado en el diseño: el distintivo «Nuevo» del planificador.
- **Rastreo LangSmith**: con el `.env` local, las pruebas de integración enviaban trazas a LangSmith (límite
  mensual agotado, error 429). Las mediciones se corrieron con `LANGSMITH_TRACING=false`. No se cambia
  configuración en esta spec.
