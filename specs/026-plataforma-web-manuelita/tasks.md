# Tasks: Plataforma web profesional de Valer-IA para Manuelita (idea 7) con planificación industrial

**Input**: Design documents from `specs/026-plataforma-web-manuelita/`

**Prerequisites**:

- [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md);
- [design.md](design.md), la dirección visual de la skill `frontend-design`;
- [data-model.md](data-model.md), [contracts/](contracts/) y [quickstart.md](quickstart.md).

**Autor**: Roberto José Guerrero | **Fecha**: 2026-11-24

**Tests**: SÍ. La spec los exige:

- FR-032: pruebas de extremo a extremo sin red;
- SC-003: paridad de cifras;
- SC-004: rechazo del no autorizado;
- SC-005: confirmación de escritura;
- SC-006: accesibilidad y responsive;
- SC-007: sin regresión.

En cada historia, las pruebas se escriben primero y deben fallar.

**Diseño**: toda tarea de interfaz sigue [design.md](design.md). Las reglas que no se negocian:

- **Tipografía**: una sola familia, Archivo, donde el ancho marca el rol.
- **Color**: un color fijo por producto.
- **Elemento memorable**: el flujo de caña es el único momento animado.
- **Etiquetas**: sin mayúsculas espaciadas sobre los títulos y sin «A · B · C» decorativo.
- **Botones y datos**: sin «→» en los botones y sin monoespaciada para datos.
- **Forma**: radios con jerarquía (2, 10 y píldora) y sin sombra gris genérica.
- **Textos**: el verbo del botón se repite en el aviso.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: se puede hacer en paralelo (archivos distintos, sin dependencias pendientes).
- **[Story]**: historia de la spec.
  - US1: consola de planificación;
  - US2: plataforma y agente por perfil;
  - US3: panel de evidencia;
  - US4: responsive y accesibilidad.

## Path Conventions

- **Paquete**: `src/proyecto_modelos_lenguaje/`, abreviado `pkg/` en estas tareas.
- **Pruebas**: `tests/`. **Web**: `web/src/`. **Configuración**: `config/`.
- **Estado de ejecución**: `resolve_state_dir()` (`pkg/agent/config.py`). Nunca `data/` ni el repositorio.

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: dependencias, tipografía y esqueletos que todo lo demás usa.

- [X] T001 Instalar `@fontsource-variable/archivo` (dependencia) y `axe-core` (desarrollo) en `web/package.json` con `npm install --save-exact=false` y regenerar `web/package-lock.json`. Quitar `@fontsource-variable/bricolage-grotesque` y `@fontsource-variable/public-sans` solo cuando T010 deje de importarlas (`npm ci` debe seguir pasando)
- [X] T002 [P] Crear las carpetas `web/src/pages/` y `web/src/components/{shell,brand,home,agent,planning,evidence}/`, cada una con un `index.ts` de reexportación vacío
- [X] T003 [P] Crear `config/evaluations.toml`, con un `[[evaluation]]` por cifra publicada y los campos `id`, `name`, `value`, `target`, `meets` (`true`, `false` o `"partial"`), `date` (ISO), `report` (ruta en `docs/`) y `note`. Las entradas, copiando las cifras **tal como están publicadas**:
  - herramientas: «86,0 % y 90,7 %», meta 90 %, `partial`;
  - trivialidades: 0 búsquedas en 10;
  - planificación: 12/12, p95 10,8 s;
  - planificación directa: 10/10 ≥ 99 % y 2/2;
  - perfiles: 19/20 y 20/20;
  - RAG del Módulo 3: Recall@10 y nDCG@10 de `docs/evaluacion_modulo3.md`;
  - blindaje: la cifra de `docs/` vigente.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: dominio, routers v1, tokens, enrutador y marco. **Bloquea todas las historias.**

### Pruebas del núcleo (escribir primero y verlas fallar)

- [X] T004 [P] Escribir `tests/unit/test_scenario_prices.py`. Cubre:
  - `Scenario(price_sugar_pct=…, price_ethanol_pct=…, price_power_pct=…)` acepta de −50 a +50 y rechaza ±51 y los campos extra;
  - con los tres en `None`, `optimize()` da un `to_dict(card=False)` idéntico al de antes en los 12 escenarios de `tests/fixtures/planning_scenarios.jsonl` (fija los valores en un snapshot generado **antes** de T008);
  - `price_ethanol_pct=+30` no baja la caña asignada a etanol;
  - `plan_id_for` cambia con un precio y no cambia sin él.
- [X] T005 [P] Escribir `tests/unit/test_planning_compare.py`, que cubre `planning.compare(base, scenario)`:
  - devuelve `mix_delta` (t y puntos %), `products_delta` (con unidad), `commitments` (`met_base`, `met_scenario`, `gap_base`, `gap_scenario`), `margin_delta` y `synthetic: true`;
  - comparar un plan consigo mismo da todos los deltas en 0;
  - el caso sin solución reporta brechas.
- [X] T006 [P] Escribir `tests/unit/test_planning_snapshot.py`, que cubre `planning.snapshot(data)` (data-model §3):
  - incluye `capacities[]` con `nominal`, `factor`, `effective` y `unit`, `commitments[]` con `unit`, y `prices`;
  - `ranges` sale del `json_schema` de `Scenario`, sin duplicar números;
  - lleva `synthetic: true`.
- [X] T007 [P] Escribir `tests/unit/test_brand_contrast.py`, que amplía las verificaciones de `pkg/brand.py`:
  - tinta `#14240F` sobre `#E86D1F`, `#B0BC22` y `#FFD200` llega al menos a 4,5:1;
  - blanco sobre `#387C2B` y `#173512` llega al menos a 4,5:1;
  - blanco sobre `#E86D1F` **no** se acepta como par de texto.

### Dominio (backend)

- [X] T008 Extender `Scenario` en `pkg/agent/planning.py` con `price_sugar_pct`, `price_ethanol_pct` y `price_power_pct` (`float | None`, `ge=-50`, `le=50`, con descripción en español):
  - `resolve()` devuelve `price_sugar`, `price_ethanol` y `price_power` efectivos;
  - `_objective()` y `margin_of()` los usan en lugar de `data.model.price_*`;
  - con `None` el cálculo debe quedar idéntico (T004).
- [X] T009 Implementar en `pkg/agent/planning.py` las funciones puras `compare(base: PlanResult, scenario: PlanResult) -> dict` y `snapshot(data: PlantData) -> dict`, según data-model §3–§4 (T005 y T006 en verde)
- [X] T010 [P] Añadir los pares de contraste de T007 a `pkg/brand.py` (`ContrastPair`, mínimo 4.5)
- [X] T011 Regenerar el catálogo con `uv run python -m proyecto_modelos_lenguaje.agent tools --markdown docs/herramientas.md`: el esquema de `optimize_production_plan` y `simulate_scenario` hereda los precios opcionales. Ajustar `tests/unit/test_catalog*.py` si fijan el esquema, sin cambiar el conteo de 26

### Routers v1 (backend)

- [X] T012 Añadir a `pkg/api_models.py` los modelos v1:
  - `PlanningAccess`, `PlantSnapshotModel`, `PlanResponse` (`PlanResult` + `label` + `decision_phrase`) y `PlanComparisonModel`;
  - `ProposalRequest`, con `scenario: Scenario` y `note: str | None` de **280 caracteres como máximo**;
  - `PendingProposalModel` (`confirmation_id`, `plan_id`, `summary`, `expires_at`, `question`);
  - `ProposalDecision`, con `decision: Literal["yes","no"]`;
  - `ProposalOutcome`;
  - `ToolEvidence`, `TurnTraceModel`, `ServiceStatusModel` y `PublishedEvaluationModel`.

  Todos con `extra="forbid"`.
- [X] T013 Crear `pkg/api_planning.py`, con `APIRouter(prefix="/api/v1/planning")`:
  - una dependencia `require_planner(request)` que lee `X-User-Id` (patrón `^[A-Za-z0-9-]{1,64}$`; si falta, `anon`), llama a `profiles.is_authorized("planificador", channel="web", user_id=…)` y, si falla, lanza 403 `planner_forbidden` con el texto de `contracts/web-ui.md`;
  - un helper `_log_event(...)` que añade `{ts, endpoint, user, scenario, plan_id, status, duration_ms, synthetic: true}` a `resolve_state_dir()/planning/console.jsonl`, sin IP ni cabeceras;
  - un mapeo de `PlanningError` y de los datos ausentes a 503 `plant_data_missing`, con el comando de regeneración en el mensaje.
- [X] T014 Crear `pkg/api_evidence.py`, con `APIRouter(prefix="/api/v1/evidence")` vacío y el mismo sobre de error, e incluir ambos routers en `pkg/api.py` con `app.include_router(...)` **antes** del fallback de la SPA `/{path:path}`. Ninguna ruta existente cambia

### Base del frontend

- [X] T015 [P] Reescribir `web/src/styles/tokens.css` con los tokens de design.md §2:
  - **color**: `--cane`, `--cane-deep`, `--sugar`, `--ethanol`, `--power`, `--molasses`, `--field`, `--ink` y `--shortfall`;
  - **tipografía**: `--font: "Archivo Variable"`; `--wdth-display: 118`, `--wdth-text: 100`, `--wdth-data: 80`; escala 1,25 de `--step--1` a `--step-6` con `clamp(2.75rem, 6vw, 4.75rem)`;
  - **forma**: `--radius-data: 2px`, `--radius-panel: 10px`, `--radius-pill`;
  - **foco**: 2 px en `--ethanol`.

  Mantener alias temporales de los nombres viejos (`--forest`, `--orange`…) hasta T066.
- [X] T016 [P] Importar Archivo con sus ejes de ancho y peso en `web/src/main.tsx` (`@fontsource-variable/archivo/wdth.css`). En `web/src/styles/global.css` definir las clases de rol:
  - `.type-display`: `font-variation-settings: "wdth" 118`, peso 760;
  - `.type-data`: `"wdth" 80`, `tabular-nums`, peso 560;
  - el cuerpo a `wdth` 100, interlineado 1,55 y medida de 66 caracteres como máximo.
- [X] T017 [P] Escribir `web/src/test/router.test.ts`, que cubre:
  - `parseRoute("/planificacion")` y las otras tres rutas;
  - una ruta desconocida da `"/"` con `notFound: true`;
  - `navigate()` llama a `pushState`;
  - `popstate` actualiza la suscripción.
- [X] T018 Implementar `web/src/lib/router.ts` (unas 60 líneas, sin dependencias), con `Route = "/" | "/agente" | "/planificacion" | "/evidencia"`, `parseRoute`, `navigate`, el hook `useRoute()` y un `<Link>` que intercepta el clic izquierdo sin modificadores (T017 en verde)
- [X] T019 [P] Crear `web/src/components/brand/ProductGlyphs.tsx`, con pictogramas SVG propios de trazo 1,75 y `currentColor`:
  - `Cane` (tallo con tres nudos y hoja), `Sugar` (cristal facetado), `Ethanol` (gota con menisco), `Power` (rayo sobre haz de bagazo) y `Molasses`;
  - `Palm`, `Grape`, `Shrimp` y `Mussel`.

  Cada uno es `aria-hidden` por defecto, o lleva `title` si se pasa. No se copian piezas de la marca. Añadir `web/src/test/ProductGlyphs.test.tsx`, que verifica que los nueve renderizan y respetan `title`.
- [X] T020 Crear el marco en `web/src/components/shell/`:
  - **`CaneRail.tsx`**: es el rail `--cane-deep`. Lleva un tallo SVG vertical cuyos cuatro nudos son los enlaces a las áreas; el nudo activo se rellena de `--cane` y tiene `aria-current="page"`. En menos de 720 px pasa a una barra inferior de cuatro destinos.
  - **`TopBar.tsx`**: el nombre del área, el chip del perfil activo y el indicador de modo demo, con el texto de lo que significa.
  - **`AcademicFooter.tsx`**: la declaración de `contracts/web-ui.md`. Con `synthetic` añade «Datos sintéticos de demostración».
  - **`AppShell.tsx`**: compone los tres con un `skip-link` y un `<main id="contenido">`.
- [X] T021 Reescribir `web/src/App.tsx` como `AppShell` más el enrutador. Cada ruta renderiza su página:
  - `pages/Home.tsx`, al principio con el contenido actual (Hero, RagConsole, ShowcaseStory, MetricsBand y LimitsNote) para no perder funciones;
  - `pages/Agent.tsx`, `pages/Planning.tsx` y `pages/Evidence.tsx`, como esqueletos con su título.

  Una ruta desconocida muestra el aviso «Esa página no existe; te llevamos a la entrada». Crear `web/src/test/App.test.tsx` con las cuatro rutas y la desconocida.
- [X] T022 [P] Crear `web/src/lib/planning.ts`, el cliente de `/api/v1/planning`:
  - funciones `getAccess`, `getState`, `postPlan`, `postCompare`, `createProposal` y `decideProposal`;
  - cada llamada envía `X-User-Id` desde `lib/session.ts`;
  - un error del sobre se convierte en `PlanningApiError(code, message)`.

  Tipos en `web/src/lib/types.ts`, espejo de los modelos de T012.
- [X] T023 [P] Crear `web/src/lib/evidence.ts`, el cliente de `/api/v1/evidence`, con `getTools`, `getTrace(threadId, turn?)`, `getServices` y `getEvaluations`. Los tipos van en `web/src/lib/types.ts`.

**Checkpoint**:

- `make check` en verde;
- las cuatro rutas navegan con «atrás» y enlace directo;
- con precios en `None`, las baterías de la spec 025 son idénticas.

---

## Phase 3: User Story 1 - El planificador arma y compara un programa de producción en una consola visual (Priority: P1) 🎯 MVP

**Goal**: la consola `/planificacion` con:

- estado de planta;
- escenario;
- flujo de caña;
- libro de compromisos;
- restricción limitante;
- alternativa;
- comparación;
- propuesta en dos pasos;
- «Explicar con el agente».

**Independent Test**: con `MANUELITA_PLANNER_WEB=1`, aplicar «15 % menos caña» y verificar que el reparto, los compromisos, la restricción y la alternativa coinciden con la herramienta y el CLI. Sin la variable, verificar el 403 y el aviso.

### Pruebas de US1 (escribir primero)

- [X] T024 [P] [US1] Escribir `tests/api/test_planning_api.py`, siguiendo `contracts/planning-api.md`. Cubre:
  - **sin autorización**: `/state`, `/plan`, `/compare` y `/proposals` responden 403 `planner_forbidden` sin datos de planta, y `/access` responde 200 con `authorized: false`;
  - **validación**: un campo fuera de rango o extra responde 422 `invalid_scenario`;
  - **plan**: `/plan` con `cane_delta_pct=-15` es igual a `optimize(...).to_dict()` y trae `label` y `decision_phrase`;
  - **sin solución**: el escenario infactible da 200 con `status="infeasible_relaxed"` y `shortfalls` no vacío;
  - **datos ausentes**: con `load_plant` apuntando a un directorio vacío (`monkeypatch` sobre `root`) responde 503 `plant_data_missing`.
- [X] T025 [P] [US1] Escribir `tests/api/test_planning_proposals.py`, que cubre la propuesta en dos pasos:
  - **creación**: `POST /proposals` responde 202 y **no** escribe en `proposals.jsonl`;
  - **decisiones**: `yes` responde 200 `saved` y añade una línea con `plan_id`, `synthetic: true` y la nota redactada; `no` responde 200 `discarded` sin línea nueva;
  - **errores**: repetir da 404 `proposal_not_found`; vencida (reloj inyectado, más de 5 minutos) da 410 `proposal_expired`;
  - **límites**: con más de 100 pendientes se descarta la más antigua, y una nota de más de 280 caracteres da 422;
  - **registro**: `console.jsonl` existe, sin IP ni la nota sin redactar.
- [X] T026 [P] [US1] Escribir `tests/integration/test_console_parity.py` (SC-003). Para cada uno de los 12 escenarios de `tests/fixtures/planning_scenarios.jsonl` compara campo por campo `mix`, `products`, `margin`, `binding`, `shortfalls` y `alternatives` entre:
  1. `POST /api/v1/planning/plan` (TestClient con `MANUELITA_PLANNER_WEB=1`);
  2. la herramienta `optimize_production_plan` (su JSON);
  3. `agent planning --scenario '<json>' --json` (subprocess).

  Tolerancia 0, porque es la misma función.
- [X] T027 [P] [US1] Escribir `web/src/test/CaneFlow.test.tsx`, que cubre:
  - con `mix={sugar, ethanol, power}`, el grosor de cada banda es proporcional y suma la altura útil;
  - `role="img"` con `<title>` y `<desc>` que contienen las tres cifras;
  - la tabla equivalente dentro de `<details>`;
  - con `status="infeasible_relaxed"` no se dibuja ninguna banda y aparece el texto «No hay un plan que cumpla todos los compromisos…»;
  - con `reducedMotion`, sin clase de transición.
- [X] T028 [P] [US1] Escribir `web/src/test/ScenarioForm.test.tsx`, que cubre:
  - los controles toman sus rangos de `snapshot.ranges`;
  - un valor fuera de rango muestra «Usa un valor entre −50 % y 50 %» y deshabilita «Calcular plan»;
  - el envío emite el `Scenario` con solo los campos tocados.
- [X] T029 [P] [US1] Escribir `web/src/test/ProposalDialog.test.tsx`, que cubre:
  - «Guardar propuesta» abre el diálogo con la pregunta y el resumen;
  - el foco queda atrapado y vuelve al botón al cerrar;
  - «No» llama a `decideProposal("no")` y muestra «Propuesta descartada»;
  - «Sí, guardar» muestra «Propuesta guardada»;
  - un error 410 muestra «La propuesta venció; vuelve a calcular el plan».
- [X] T030 [P] [US1] Escribir `web/src/test/PlanningPage.test.tsx` con el cliente simulado:
  - sin acceso muestra `PlannerGate` y **no** llama a `getState`;
  - con acceso, el flujo calcular, comparar y explicar navega a `/agente` y envía el mensaje con el `plan_id`.

### Implementación de US1 (backend)

- [X] T031 [US1] Implementar en `pkg/api_planning.py` los endpoints `GET /access`, `GET /state` (`planning.snapshot`), `POST /plan` (`planning.optimize` + `label` + `decision_phrase`) y `POST /compare` (`optimize` del escenario vacío y del pedido, luego `planning.compare`). Cada uno pasa por `require_planner` (menos `/access`) y `_log_event` (T024 y T026 en verde)
- [X] T032 [US1] Implementar en `pkg/api_planning.py` la propuesta en dos pasos (R9):
  - un almacén en memoria `PendingProposals` con `confirmation_id = secrets.token_urlsafe(16)`, vencimiento de 5 minutos, un tope de 100 que descarta la más antigua y un `clock` inyectable;
  - `POST /proposals`: recalcula el plan en el servidor y responde 202 sin escribir;
  - `POST /proposals/{id}`: con `yes` llama a `actions.save_proposal({"plan_id": …, "note": …}, user_id=…, last_plan=plan)`; con `no` solo registra.

  T025 en verde.

### Implementación de US1 (frontend, siguiendo design.md)

- [X] T033 [P] [US1] Crear `web/src/components/planning/PlannerGate.tsx`, el aviso de acceso de `contracts/web-ui.md` con el pictograma `Cane` y un enlace «Hablar con el agente en otro perfil» a `/agente`. No muestra datos ni números
- [X] T034 [P] [US1] Crear `web/src/components/planning/PlantStatePanel.tsx`, con la semana, la versión y la etiqueta sintética en cabecera:
  - **caña**: disponible y calidad;
  - **capacidades**: barras finas `effective/nominal` en `.type-data`, con el estado del equipo en texto («molino al 92 %») y no solo en color;
  - **inventarios**.
- [X] T035 [P] [US1] Crear `web/src/components/planning/ScenarioForm.tsx`, con controles accesibles (`<label>` + `<input type="range">` + `<output>` y un campo numérico espejo):
  - caña %, calidad, los tres precios %, vapor máximo y prioridad (margen o energía, como grupo de radio);
  - botones «Calcular plan» y «Comparar con el plan base»;
  - errores por campo con el rango válido.

  T028 en verde.
- [X] T036 [US1] Crear `web/src/components/planning/CaneFlow.tsx`, el elemento memorable de design.md §3:
  - **geometría**: Sankey SVG propio de un origen, «Caña» con el pictograma `Cane`, a tres destinos coloreados `--sugar`, `--ethanol` y `--power`. Cada banda es una curva cúbica con grosor proporcional a las toneladas de `mix` y termina en su pictograma, con las cifras en `.type-data` (%, t, m³ o MWh).
  - **comparación**: con `compareTo`, el plan base se dibuja detrás en contorno de 1 px.
  - **animación**: las bandas crecen desde el origen en 600 ms solo al cambiar el plan y nunca con `prefers-reduced-motion`.
  - **teléfono**: en menos de 560 px la orientación es vertical (la caña cae desde arriba).
  - **sin solución**: no se dibujan bandas.
  - **accesibilidad**: `role="img"`, `<title>`, `<desc>` y la tabla en `<details>`.

  T027 en verde.
- [X] T037 [P] [US1] Crear `web/src/components/planning/CommitmentLedger.tsx`:
  - una fila por compromiso: producto (pictograma y color), contraparte ficticia, prioridad, una barra con una marca vertical en el mínimo contratado y el texto «cumple +4 %» o «falta 320 m³»;
  - lo que falta se dibuja en `--shortfall` con trama diagonal SVG (`<pattern>`), para no depender solo del color;
  - en el caso infactible, ordenado por prioridad.
- [X] T038 [P] [US1] Crear `web/src/components/planning/PlanSummary.tsx`:
  - la restricción que limita (`binding`) con su valor marginal en palabras («cada tonelada más de molienda vale 38»);
  - las alternativas;
  - los supuestos plegables;
  - el `plan_id`;
  - la frase de decisión.
- [X] T039 [P] [US1] Crear `web/src/components/planning/ComparisonView.tsx`, con una tabla de diferencias por destino, producto y compromiso, más el margen. Los signos y las palabras son explícitos («+2,1 puntos a etanol»), y no solo flechas o color
- [X] T040 [US1] Crear `web/src/components/planning/ProposalDialog.tsx`:
  - un `<dialog>` modal con la pregunta del backend, el resumen y los botones «Sí, guardar» y «No»;
  - foco atrapado y devuelto al cerrar;
  - avisos «Propuesta guardada» y «Propuesta descartada», y el error 410 con su texto.

  T029 en verde.
- [X] T041 [US1] Componer `web/src/pages/Planning.tsx`:
  - **acceso**: `getAccess()`; si no está autorizado, `PlannerGate`.
  - **escritorio**: retícula de design.md, con escenario y estado a la izquierda (4 de 12 columnas), y `CaneFlow`, `PlanSummary` y `CommitmentLedger` a la derecha (8 de 12).
  - **teléfono**: escenario, flujo, compromisos y estado, en ese orden.
  - **carga**: al entrar calcula el plan base; mientras calcula muestra «Calculando el plan…» sin bloquear la lectura.
  - **acciones**:
    - «Explicar con el agente» guarda en el estado del chat el mensaje «Explica el plan recomendado para este escenario: …» con los parámetros y el `plan_id`, selecciona el perfil planificador y navega a `/agente`.
    - «Guardar propuesta» abre `ProposalDialog`.

  T030 en verde.

**Checkpoint**:

- la consola completa funciona sola;
- la paridad da 12/12;
- el no autorizado recibe 403 por la UI y por `curl`.

---

## Phase 4: User Story 2 - Cada público entra a su agente desde una plataforma con la identidad de Manuelita (Priority: P1)

**Goal**:

- una entrada pública con hero, libro de perfiles y garantías;
- Consulta, Resumen y FAQ conservados;
- `/agente` con el selector de perfil, el chat actual y los paneles de fuentes, memoria y sugerencias.

**Independent Test**:

1. En un navegador limpio, elegir «Cliente B2B» desde la entrada y preguntar por certificaciones: debe salir una respuesta citada, el chip y las sugerencias.
2. Cambiar a «Proveedor» en el mismo hilo: el hilo debe conservarse.

### Pruebas de US2 (escribir primero)

- [X] T042 [P] [US2] Escribir `web/src/test/HomePage.test.tsx`, que cubre:
  - el titular de la plataforma y la declaración académica;
  - cinco filas de perfil, de las cuales el planificador solo es enlace si `access.authorized`;
  - el clic en la consulta de ejemplo de «Cliente B2B» navega a `/agente` con perfil `cliente` y el mensaje precargado;
  - `RagConsole` sigue presente (Consulta, Resumen y FAQ).
- [X] T043 [P] [US2] Escribir `web/src/test/AgentPage.test.tsx`, que cubre:
  - el `ProfilePicker` lista los perfiles de `getProfiles()`;
  - cambiar de perfil conserva `threadId`;
  - el `SourcesPanel` muestra las citas del último turno como enlaces;
  - el `MemoryPanel` muestra el perfil recordado y «Borrar» pide aprobación;
  - las `ProfileSuggestions` cambian con el perfil;
  - el mensaje pendiente de «Explicar con el agente» se envía una sola vez.
- [X] T044 [P] [US2] Verificar que las pruebas vigentes del chat (`web/src/test/ChatView*.test.tsx`, `ApprovalCard`, `MicButton`, `VoiceControls`) siguen pasando sin cambios de aserción tras la reubicación. Solo se ajustan los imports de ruta

### Implementación de US2

- [X] T045 [P] [US2] Crear `web/src/components/home/PlatformHero.tsx`. Sin cifra grande ni degradado (design.md §5):
  - **titular** en `.type-display`: «Un agente para cada persona que trabaja con Manuelita.»;
  - **párrafo**: qué es (un agente con perfiles, citas y aprobación) y qué no es (canal oficial);
  - **botones**: «Hablar con el agente» (`--ethanol` con tinta) y «Ver la planificación»;
  - **ilustración** SVG de composición propia: un tallo de caña que se abre en las cadenas de producto (azúcar, etanol, energía, palma, uva, camarón y mejillón) con `ProductGlyphs`.
- [X] T046 [P] [US2] Crear `web/src/components/home/ProfileLedger.tsx`, con los cinco perfiles como **filas de un libro de registro**, no como tarjetas iguales:
  - cada fila lleva el pictograma, el nombre en `.type-display` pequeño, «qué puede pedir» y una consulta de ejemplo como enlace;
  - los filetes de 1 px de `--ink` al 14 % separan las filas;
  - el planificador muestra «Solo equipo de planta autorizado» cuando no hay acceso.
- [X] T047 [P] [US2] Crear `web/src/components/home/Guarantees.tsx`, con las cuatro garantías (cita sus fuentes, calcula cifras en código, pide «Sí» antes de guardar y recuerda con permiso). Cada una enlaza a su evidencia en `/evidencia` o al informe. No se numeran porque no son una secuencia
- [X] T048 [US2] Recomponer `web/src/pages/Home.tsx`:
  - en este orden: `PlatformHero`, `ProfileLedger`, `Guarantees` y la sección «Módulos 1 y 2» con la `RagConsole` existente y `LimitsNote`;
  - retirar `Hero`, `ShowcaseStory`, `MetricsBand`, `ProductMotifs` y `CaneField` de la entrada; sus pruebas se borran o se reemplazan, sin perder funciones evaluadas;
  - mantener `/api/showcase` en el backend.

  T042 en verde.
- [X] T049 [P] [US2] Crear `web/src/components/agent/ProfilePicker.tsx`:
  - píldoras (el único uso del radio de píldora) con `role="radiogroup"`;
  - el planificador deshabilitado, con su motivo, si no hay acceso;
  - el cambio llama al callback sin reiniciar el hilo.
- [X] T050 [P] [US2] Crear `web/src/components/agent/SourcesPanel.tsx`, con las citas `[U#]`, `[F#]` y `[S#]` del último turno como enlaces a su fuente, separando las sintéticas `[S#]` con la etiqueta. Reutilizar `EvidenceLinks` si sirve
- [X] T051 [P] [US2] Crear `web/src/components/agent/MemoryPanel.tsx`, que usa `GET /api/memory/{user_id}` y `DELETE` (202, con aprobación). Muestra qué recuerda el agente y tiene el botón «Borrar mi memoria». El aviso es «Memoria borrada» solo tras la aprobación
- [X] T052 [P] [US2] Crear `web/src/components/agent/ProfileSuggestions.tsx`, con tres consultas de ejemplo por perfil en `web/src/data/profileSuggestions.ts`. El planificador tiene «Tenemos 15 % menos caña esta semana…»
- [X] T053 [US2] Componer `web/src/pages/Agent.tsx`:
  - `ProfilePicker` arriba, el `ChatView` actual en la columna principal y `SourcesPanel`, `MemoryPanel` y `ProfileSuggestions` a la derecha;
  - en menos de 900 px esos paneles van en un cajón «Fuentes y memoria»;
  - pasar el perfil activo a `ChatView` (prop existente de la spec 025) y consumir el mensaje pendiente de US1;
  - el chip del perfil va en `TopBar`.

  T043 y T044 en verde.
- [X] T054 [US2] Re-estilizar `web/src/components/ChatView.tsx` y `ApprovalCard.tsx` solo con clases y tokens nuevos (Archivo, radios con jerarquía, «Sí» y «No» con el verbo), **sin tocar la lógica** de streaming, voz, dictado ni HITL. El diff de lógica debe ser 0, salvo los imports

**Checkpoint**: la entrada y `/agente` funcionan solos, y el chat, la voz, el dictado y la aprobación siguen intactos.

---

## Phase 5: User Story 3 - El equipo muestra la evidencia técnica del Módulo 3 desde la web (Priority: P2)

**Goal**: `/evidencia` con el estado de servicios, el catálogo de 26, la traza del turno y las evaluaciones publicadas.

**Independent Test**: hacer una pregunta en `/agente`, abrir `/evidencia` y comprobar que la traza, el catálogo y el estado coinciden con `agent tools` y `/traza`.

### Pruebas de US3 (escribir primero)

- [X] T055 [P] [US3] Escribir `tests/api/test_evidence_api.py`, siguiendo `contracts/evidence-api.md`. Cubre:
  - **herramientas**: `/tools` da `count == 26 == len(SPECS)`, cada una con `profiles` según `config/profiles.toml`, y `mcp_allowed` es falso para simular y optimizar;
  - **trazas**: `/traces/{id}` de un hilo creado en modo demo trae `route`, `plan_steps` y `tools[]` con `duration_ms`; los argumentos van redactados (un teléfono en los argumentos no aparece); un hilo inexistente da 404 `thread_not_found`;
  - **servicios**: `/services` usa los pings simulados; un servicio que tarda más de 2 s queda `unknown` con su `reason`; ninguna respuesta contiene `sk-`, tokens ni números E.164;
  - **evaluaciones**: `/evaluations` lista `config/evaluations.toml`, y cada `report` existe en `docs/`.
- [X] T056 [P] [US3] Escribir `web/src/test/EvidencePage.test.tsx`, que cubre:
  - el filtro del catálogo (lectura, escritura o perfil);
  - la traza con los pasos numerados (sí son una secuencia);
  - el servicio caído con su `action` visible;
  - las evaluaciones `partial` visibles con su nota, no ocultas.

### Implementación de US3

- [X] T057 [US3] Implementar en `pkg/api_evidence.py` los cuatro endpoints:
  - **`/tools`**: une `catalog.SPECS` con `profiles.load_profiles()`;
  - **`/traces/{thread_id}`**: reutiliza la lectura del hilo de `GET /api/threads/{thread_id}`, toma el turno pedido y aplica `redact_pii` a los argumentos;
  - **`/services`**: agrega `health`, `voice`, `stt`, `channels/status` y Qdrant con un tope de 2 s por comprobación (`asyncio.wait_for`), cada uno con su `status`, `reason` y `action` en español;
  - **`/evaluations`**: lee `config/evaluations.toml` con `tomllib`.

  T055 en verde.
- [X] T058 [P] [US3] Crear `web/src/components/evidence/ServiceStatusBar.tsx`. Cada servicio lleva un indicador con forma y texto («disponible», «caído», «sin dato»), no solo color, y la razón y la acción se despliegan al enfocar o al hacer clic
- [X] T059 [P] [US3] Crear `web/src/components/evidence/ToolCatalogTable.tsx`:
  - una tabla densa en `.type-data` con nombre, tipo, aprobación, perfiles y MCP;
  - filtros por tipo y perfil;
  - el conteo «26 herramientas» en el título.
- [X] T060 [P] [US3] Crear `web/src/components/evidence/TraceViewer.tsx`:
  - la ruta, el perfil y los pasos numerados, cada uno con su herramienta, duración y resultado;
  - los argumentos plegables;
  - un selector de turno.

  Lee el `threadId` de `lib/session.ts`.
- [X] T061 [P] [US3] Crear `web/src/components/evidence/EvaluationsTable.tsx`, con la cifra, la meta, la fecha, el estado (texto «cumple», «parcial» o «no cumple», con color y forma) y el enlace al informe en GitHub
- [X] T062 [US3] Componer `web/src/pages/Evidence.tsx` según el wireframe de design.md: servicios arriba, catálogo y traza en dos columnas, evaluaciones abajo, y una columna en teléfono (T056 en verde)

**Checkpoint**: el panel completo se muestra sin abrir la terminal.

---

## Phase 6: User Story 4 - La plataforma se ve y se usa bien en cualquier pantalla (Priority: P2)

**Goal**:

- sin desplazamiento horizontal de 360 a 1920 px;
- AA en contraste;
- uso completo con teclado;
- movimiento reducido.

**Independent Test**: `make e2e` en verde en las cuatro rutas y los cuatro anchos.

- [X] T063 [P] [US4] Ampliar `tests/e2e/test_responsive.py` a `/`, `/agente`, `/planificacion` y `/evidencia` en 360, 768, 1440 y 1920 px, comprobando `document.documentElement.scrollWidth <= innerWidth`. El servidor e2e se lanza con `MANUELITA_PLANNER_WEB=1` y en modo demo
- [X] T064 [P] [US4] Crear `tests/e2e/test_accessibility.py`, que inyecta `web/node_modules/axe-core/axe.min.js` con `page.add_script_tag(path=…)`, corre `axe.run()` en las cuatro rutas y falla con violaciones `serious` o `critical`. También verifica, emulando `reduced_motion="reduce"`, que `CaneFlow` no tiene animaciones activas (`getAnimations().length == 0`)
- [X] T065 [P] [US4] Crear `tests/e2e/test_platform.py`, con los flujos de las historias 1 y 2 sin red:
  - **perfil**: desde la entrada, «Cliente B2B», preguntar en modo demo y ver el chip;
  - **consola**: `/planificacion`, caña −15 %, «Calcular plan», ver las tres bandas y el libro de compromisos;
  - **propuesta**: «Guardar propuesta», luego «No» y luego «Sí, guardar», con los avisos;
  - **teclado**: recorrer `/planificacion` con `Tab` y verificar el foco visible (`outline-width` ≥ 2 px) en cada control.
- [X] T066 [US4] Corregir lo que encuentren T063–T065 en `web/src/styles/global.css` y en los componentes, y retirar los alias temporales de tokens de T015. Antes de dar la historia por cerrada, sacar capturas a 360 y 1440 px de las cuatro rutas y hacer la **autocrítica de design.md**:
  1. ¿hay algún default genérico que se haya colado (tarjetas iguales, mayúsculas espaciadas, monoespaciada, flechas)?
  2. ¿la valentía está solo en el flujo de caña?
  3. quitar un accesorio (consejo de Chanel).

  Anotar lo cambiado en la sección *Notes*.

**Checkpoint**: `make e2e` en verde.

---

## Phase 7: Polish & Cross-Cutting Concerns

- [X] T067 [P] Escribir `docs/decisions/0030-plataforma-web-v1.md`:
  - **contexto**: la web era la página de los Módulos 1 y 2;
  - **decisión**: cuatro áreas, `/api/v1` aparte, enrutador propio, SVG propio, Archivo y un color por producto;
  - **alternativas**: Next.js, librerías de componentes y de gráficos, y migrar todo a v1;
  - **consecuencias**.

  Autor: Roberto José Guerrero.
- [X] T068 [P] Enmendar `CONSTITUTION.md` §3.7 en el mismo commit: la web tiene cuatro áreas (entrada, agente, planificación y evidencia); las rutas `/api/v1/planning` exigen el planificador autorizado; las cifras de planta nunca se calculan en el navegador; Archivo y la paleta por producto. Subir la versión (MINOR, 2.1.0) y registrar en el historial
- [X] T069 [P] Actualizar `docs/rubrica_modulo3.md` §7.1 y la tabla del §1 (ítems 1.1, 1.2, 1.3, 3.2, 4.1, 4.2 y 4.3) con la evidencia web, y el guion §7.2–§7.3: la demo de planificación desde `/planificacion` y la discusión técnica desde `/evidencia`
- [X] T070 Sacar capturas a 1440 px (tema claro) de las cuatro áreas en `docs/capturas/plataforma-{entrada,agente,planificacion,evidencia}.png` con Playwright (`make app` + `MANUELITA_PLANNER_WEB=1`, modo demo)
- [X] T071 Actualizar `README.md`:
  - **interfaz**: la sección con las cuatro áreas y sus capturas de T070;
  - **API**: la tabla con los endpoints `/api/v1/*` y el enlace a `contracts/`;
  - **badge de pruebas**: con el conteo nuevo;
  - **roadmap**: spec 026;
  - **documentación**: enlaces a la spec, el plan, `design.md` y el ADR 0030.
- [ ] T072 Actualizar Archify en `docs/arquitectura.json`:
  - un nodo «Web v1: cuatro áreas» y un nodo «API v1 planificación y evidencia», con flujos a `planning` y `profiles`;
  - fijar `revision` al commit de la feature;
  - `finalize --quality showcase`, borrar los `*.browser-check.json` viejos y `visual-check --summary --require-provenance`;
  - regenerar `docs/capturas/` del diagrama.
- [X] T073 [P] Registrar en `docs/prompt_log.md` que no hay prompts nuevos: «Explicar con el agente» reutiliza la ruta `planning` vigente. Si al implementar T041 hiciera falta texto de sistema nuevo, versionarlo ahí
- [X] T074 Correr la puerta completa:
  - `make check`;
  - `make e2e`;
  - `uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct`, que debe dar resultados idénticos a `docs/evaluacion_planificacion_directa.md`.

  Recorrer `quickstart.md` §4 a mano.
- [X] T075 Medir el bundle con `npm run build` (el JS comprimido debe pesar 250 kB o menos) y la carga de la entrada (menos de 2 s, SC-009) con Playwright `performance.timing`. Anotar los resultados en `quickstart.md`

---

## Dependencies & Execution Order

### Por fase

- **Setup (fase 1)**: sin dependencias.
- **Foundational (fase 2)**: depende de la fase 1. **Bloquea todas las historias.**
  - Las pruebas T004–T007 van antes que T008–T010.
  - T012 va antes que T013 y T014.
  - T015–T016 van antes que T019–T021.
  - T017 va antes que T018, y T018 antes que T021.
- **US1 (fase 3)**: depende de la fase 2. Es el MVP.
- **US2 (fase 4)**: depende de la fase 2. Se puede hacer en paralelo con US1. T053 consume el mensaje pendiente que produce T041, y con US1 sin terminar esa parte se prueba con un stub.
- **US3 (fase 5)**: depende de la fase 2. Es independiente de US1 y US2; solo usa el hilo de `lib/session.ts`.
- **US4 (fase 6)**: depende de las páginas que existan. Corre al final de US1 y US2, y otra vez tras US3.
- **Polish (fase 7)**: depende de las historias entregadas.

### Dentro de cada historia

Pruebas (fallan) → backend → componentes en paralelo → página que compone → checkpoint.

### Orden por calendario (R15)

1. Fase 1 y fase 2.
2. US1 antes del jueves 26 en la noche.
3. US2.
4. US4 sobre US1 y US2.
5. US3 si alcanza antes del ensayo del viernes 27.
6. Polish.

## Parallel Example: User Story 1

```text
# Pruebas en paralelo:
T024 tests/api/test_planning_api.py
T025 tests/api/test_planning_proposals.py
T026 tests/integration/test_console_parity.py
T027 web/src/test/CaneFlow.test.tsx
T028 web/src/test/ScenarioForm.test.tsx
T029 web/src/test/ProposalDialog.test.tsx

# Componentes en paralelo (tras T031–T032):
T033 PlannerGate · T034 PlantStatePanel · T035 ScenarioForm · T037 CommitmentLedger
T038 PlanSummary · T039 ComparisonView
```

## Parallel Example: User Story 2

```text
T045 PlatformHero · T046 ProfileLedger · T047 Guarantees
T049 ProfilePicker · T050 SourcesPanel · T051 MemoryPanel · T052 ProfileSuggestions
```

## Implementation Strategy

### MVP primero (US1)

1. Fases 1 y 2. Validar que las baterías de la spec 025 quedan idénticas.
2. Fase 3, la consola. **Parar y validar**: paridad 12/12, 403 y quickstart §4.3. Con esto ya hay demo de
   planificación visual para la discusión técnica.

### Entrega incremental

- Con US2, la web se presenta como plataforma. Sirve de respaldo del pitch si WhatsApp falla.
- Con US4, se garantiza en teléfono y proyector.
- Con US3, la evidencia se muestra sin terminal. Si no alcanza, se muestra con `/traza` y la terminal, como hoy.

### Reglas

- Commits por fase, a nombre de Robertto48, en Conventional Commits en español y sin coautores.
- El PR a `main` lo revisa Jason. No se fusiona por cuenta propia.
- La rama depende de `025-agentes-manuelita-idea7` (PR #79): se rebasa sobre `main` cuando se fusione.

## Notes

- **[P]**: archivos distintos, sin dependencias pendientes.
- **Lógica del chat**: T054 no cambia la lógica de `ChatView`. Si una prueba vigente del chat falla, se corrige el estilo o el import, nunca la aserción.
- **Cifras de planta**: ninguna se calcula en `web/`. Si un componente necesita un número derivado, se añade al backend con su prueba.
- **Autocrítica de diseño (T066)**: anotar aquí lo que se cambió en la revisión frente a design.md §5.

### Implementación (2026-11-24)

- **Pendiente T072 (Archify)**: el diagrama fija `revision` a un commit en el que existan las fuentes
  (`api_planning.py`, `api_evidence.py`, `web/src/pages/`). Se completa cuando el cambio tenga su commit.
- **Desviaciones menores, a propósito**:
  - **T002**: no se crearon `index.ts` vacíos; los componentes se importan por su ruta.
  - **T012**: los cuerpos de entrada y las respuestas pequeñas tienen modelo Pydantic. El plan, el estado y la
    comparación se devuelven como `dict` desde `planning.py`, que ya es el contrato probado.
  - **T015 y T066**: los alias de tokens viejos (`--forest`, `--orange`…) se conservan apuntando a los nuevos
    valores, porque `RagConsole` y `ChatView` los usan.
  - **T022**: los errores reutilizan `ApiClientError` en lugar de una clase `PlanningApiError` nueva.
- **Cambios fuera de las tareas, encontrados al probar**:
  - Las herramientas de escritura se reportan con los perfiles que de verdad las reciben (todas salvo
    `save_production_proposal`, solo del planificador), con la misma regla de `specs_for_route`.
  - `tests/e2e/test_chat.py` ya fallaba antes de esta spec: buscaba elementos que desde la spec 018 solo existen
    en la vista técnica. Ahora abre `?vista=tecnica`.
  - `tests/e2e/test_showcase.py` se retira junto con la página editorial.
- **Autocrítica de diseño (T066)**, con capturas a 360 y 1440 px:
  1. Las bandas del flujo salían casi rectas y no se leía el reparto: los destinos se separan a la derecha
     (`SPREAD`), y en teléfono la caña cae desde arriba.
  2. El rail quedaba flotando en las capturas de página completa: el verde del rail acompaña toda la página.
  3. `ChatView` heredaba texto claro de la consola oscura y el campo de mensaje no se veía: en `/agente` toma
     tinta sobre claro, y las etiquetas de cita usan naranja oscurecido para llegar a AA (lo detectó `axe-core`).
  4. En teléfono, el estado de planta aparecía antes del plan: ahora va al final, según `design.md`.
  5. Accesorio retirado: la página editorial completa (hero con cifra, recorrido de 11 bloques y banda de
     métricas) sale de la entrada.
  6. Queda, a propósito: la consola oscura de los Módulos 1 y 2 en la entrada conserva su estilo propio, porque
     es evidencia evaluada en los módulos anteriores.
