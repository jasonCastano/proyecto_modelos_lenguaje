# Research: Plataforma web profesional de Valer-IA (spec 026)

**Fecha**: 2026-11-24 · **Autor**: Roberto José Guerrero

Cada decisión resuelve una incógnita del *Technical Context* de [`plan.md`](plan.md). Formato: decisión, razón y
alternativas descartadas.

## R1. Stack del frontend

- **Decisión**: se mantiene la SPA propia en `web/` con **React 19, Vite 7 y TypeScript**, servida por FastAPI como
  desde la spec 012. No se añade ningún framework de interfaz, de estado global ni de componentes.
- **Razón**: ya cumple FR-002 (sin Streamlit, Gradio ni notebooks), tiene 149 pruebas de vitest, un build en CI y el
  fallback de SPA en `api.py` (`/{path:path}`). Reescribir con otro stack a cuatro días de la sustentación no aporta
  puntos de rúbrica y sí riesgo.
- **Alternativas**:
  - Next.js o Remix: exigen un servidor Node aparte y rompen `make app`.
  - Una librería de componentes (MUI, Chakra, shadcn): impone su estética genérica, lo contrario de lo que pide la
    identidad de Manuelita.

## R2. Navegación entre las cuatro áreas (FR-001, FR-006)

- **Decisión**: un enrutador mínimo propio en `web/src/lib/router.ts`, de unas 60 líneas. Usa la History API
  (`pushState`, `popstate`) y tiene cuatro rutas fijas:
  - `/`: entrada;
  - `/agente`: espacio de trabajo;
  - `/planificacion`: consola;
  - `/evidencia`: panel.

  Las rutas desconocidas vuelven a `/` con un aviso. El fallback de SPA del backend ya sirve `index.html` en
  cualquier ruta, así que los enlaces directos funcionan sin tocar el servidor.
- **Razón**: cuatro rutas estáticas sin parámetros no justifican una dependencia (Principio V, simplicidad). El
  botón «atrás» y los enlaces directos quedan cubiertos.
- **Alternativas**:
  - `react-router`: unos 15 kB y una API más amplia de lo necesario.
  - Rutas con `#`: se ven peor en la proyección y rompen los anclajes internos que ya existen.

## R3. Gráficos de planificación (FR-013, FR-014)

- **Decisión**: SVG propio dibujado en componentes React, sin librería de gráficos. Son tres piezas:
  1. **Flujo de caña** (tipo Sankey simplificado): una banda que nace en «Caña» y se divide en azúcar, etanol y
     energía. El grosor es proporcional a las toneladas de cada destino (`mix`).
  2. **Libro de compromisos**: una barra horizontal por compromiso con su mínimo, lo producido y el margen o faltante.
  3. **Comparación**: dos flujos en paralelo y una tabla de diferencias.

  Cada SVG lleva `role="img"`, `<title>` y `<desc>` con las cifras (FR-030). Debajo va una tabla accesible con los
  mismos datos.
- **Razón**:
  - El Sankey es la forma natural de «cuánta caña va a cada producto» y es el elemento memorable de la plataforma
    (ver [`design.md`](design.md)).
  - Con tres destinos fijos, la geometría se calcula en pocas líneas.
  - Una librería (Recharts, D3, ECharts) añadiría entre 50 y 300 kB y su estética por defecto.
- **Alternativas**:
  - `d3-sankey`: resuelve redes generales, aquí sobra.
  - Gráficos de barras genéricos: no cuentan la historia de la caña repartida.

## R4. Versionado y forma de los servicios nuevos (FR-025, FR-026, FR-029)

- **Decisión**: los servicios nuevos viven bajo el prefijo **`/api/v1/`**, en dos routers de FastAPI separados del
  `api.py` actual (que ya pasa de 1.000 líneas):
  - `api_planning.py`: `/api/v1/planning/*`;
  - `api_evidence.py`: `/api/v1/evidence/*`.

  Los endpoints existentes (`/api/chat`, `/api/tools`, etc.) no cambian de ruta ni de forma. Los errores reutilizan
  el sobre actual `{"error": {"code", "message"}}` con códigos estables nuevos, listados en los contratos.
- **Razón**:
  - El prefijo hace explícito que el contrato es versionado sin romper a los clientes vigentes: la web, el puente de
    WhatsApp y las pruebas.
  - Los routers separados mantienen legible `api.py`.
- **Alternativas**:
  - Mover todo a `/api/v1`: rompe `valeria-bridge` y las pruebas del Módulo 3 a días de la sustentación.
  - GraphQL: es otra pila para una decena de consultas.

## R5. Autorización del planificador en la web (FR-019, SC-004)

- **Decisión**: cada endpoint de `/api/v1/planning/*` exige `profiles.is_authorized("planificador", channel="web",
  user_id=...)`, la misma regla de la spec 025. En la web se habilita con `MANUELITA_PLANNER_WEB=1` en la jornada; si
  no se cumple, responde **403** con `planner_forbidden` y ningún dato de planta.

  La UI consulta `GET /api/v1/planning/access`, que solo devuelve `{authorized: bool, reason}`, para decidir si
  muestra la consola o el aviso. El backend sigue siendo la barrera: ocultar la consola en la UI no basta.
- **Razón**: no añade cuentas ni contraseñas (fuera de alcance) y reutiliza la autorización ya evaluada.
- **Alternativas**:
  - Un token del planificador en el navegador: exige gestionar secretos en el cliente.
  - Un login básico: está fuera de alcance según la spec.

## R6. Una sola fuente de cifras (FR-016, SC-003)

- **Decisión**: la consola llama a `planning.optimize(Scenario, load_plant())`, la misma función que usa la
  herramienta `optimize_production_plan`. El endpoint devuelve `PlanResult.to_dict(card=True)` sin recalcular nada en
  el frontend: el SVG solo dibuja lo que recibe.

  La prueba `tests/integration/test_console_parity.py` recorre los 12 escenarios de
  `tests/fixtures/planning_scenarios.jsonl` y compara campo por campo la salida del endpoint, la de la herramienta y
  la del CLI `agent planning --scenario '<json>' --json`.
- **Razón**: la coincidencia queda garantizada por construcción y verificada por la prueba.
- **Alternativas**: replicar el cálculo en TypeScript. Habría dos fuentes de verdad y sería imposible garantizar
  SC-003.

## R7. Precios en el escenario (FR-012)

- **Decisión**: `Scenario` gana tres campos opcionales, **`price_sugar_pct`, `price_ethanol_pct` y
  `price_power_pct`**, con rango de −50 a +50, cambio porcentual sobre el precio de referencia y `None` por defecto.
  `resolve()` los aplica al objetivo del LP.
  - Con `None`, todo resultado vigente es idéntico, así que las baterías de la spec 025 no cambian (prueba de
    regresión).
  - El esquema de la herramienta `optimize_production_plan` hereda los campos opcionales; `docs/herramientas.md` se
    regenera.
- **Razón**: la historia 1 menciona un cambio de precio del etanol, y la sensibilidad de los precios es la pregunta
  natural del planificador.
- **Alternativas**:
  - Solo en la consola, con un modelo aparte: viola R6.
  - Capacidad editable por área: la UI la cubre con el límite de vapor y la calidad, que ya existen. Editar las
    capacidades físicas invita a «relajarlas», lo que la regla 19 de la Fase 3 prohíbe.

## R8. Comparación con el plan base (FR-014)

- **Decisión**: una función pura nueva, `planning.compare(base, scenario) -> dict`, que devuelve las diferencias:
  - por destino de caña (t y %);
  - por producto (t, MWh, m³);
  - por compromiso (cumplido o faltante);
  - en el margen.

  El endpoint `POST /api/v1/planning/compare` resuelve el plan base (escenario vacío) y el pedido en la misma
  llamada.
- **Razón**: una sola llamada evita estados intermedios en la UI, y la función pura se prueba sin red.
- **Alternativas**: comparar en el frontend. Es lógica de negocio fuera del backend y no queda cubierta por pytest.

## R9. Guardar propuesta desde la consola (FR-018, SC-005)

- **Decisión**: el guardado tiene dos pasos con confirmación explícita.
  1. `POST /api/v1/planning/proposals` con el escenario: el backend recalcula el plan (R6) y devuelve una propuesta
     **pendiente** con `confirmation_id`, el resumen y `expires_at` (5 minutos, el vencimiento de la spec 025). Aún
     no guarda nada.
  2. `POST /api/v1/planning/proposals/{confirmation_id}`, con `{"decision": "yes"|"no"}`:
     - con `yes`, llama a `actions.save_proposal(..., last_plan=plan_recalculado)` y escribe en el mismo
       `planning/proposals.jsonl` del directorio de estado;
     - con `no`, descarta la propuesta y lo registra.

  Las pendientes viven en memoria del proceso, con un tope de 100 y su vencimiento.
- **Razón**: es el mismo archivo y el mismo registro que la acción HITL del agente. La cifra guardada sale del
  servidor y nunca del navegador.
- **Alternativas**:
  - Un solo POST con `confirm=true`: la UI podría saltarse la confirmación.
  - Pasar por un hilo del agente: acopla la consola al LLM y a la red.

## R10. «Explicar con el agente» (FR-017)

- **Decisión**: el botón lleva a `/agente` con el perfil planificador y envía en el hilo actual un mensaje generado:
  «Explica el plan recomendado para este escenario: caña −15 %, calidad 12,5 …». Contiene los mismos parámetros del
  escenario.
  - El agente corre su ruta `planning`, que es determinista para el mismo escenario (`plan_id_for`).
  - El validador de cifras de la spec 025 garantiza que la explicación use las mismas cifras.
  - La consola muestra el `plan_id`, y la respuesta del agente lo cita.
- **Razón**: no crea un canal nuevo hacia el LLM y reutiliza el router, la traza y el blindaje evaluados.
- **Alternativas**: un endpoint `/explain` dedicado. Duplica el grafo y queda fuera de la traza.

## R11. Panel de evidencia (FR-020 a FR-024)

- **Decisión**: hay cuatro servicios de solo lectura.

  | Servicio | Fuente | Qué hace |
  |---|---|---|
  | `GET /api/v1/evidence/tools` | `catalog.SPECS` y `config/profiles.toml` | Añade a cada herramienta los perfiles que la incluyen y `mcp_allowed`. |
  | `GET /api/v1/evidence/traces/{thread_id}` | `GET /api/threads/{thread_id}` | Reduce el hilo a la última traza (o a la del turno pedido) y redacta lo personal con `redact_pii`. |
  | `GET /api/v1/evidence/services` | `health`, `voice`, `stt`, `channels/status` y un ping a Qdrant | Agrega cada dependencia con `status`, `reason` y `action`. Cada ping tiene un timeout de 2 s. |
  | `GET /api/v1/evidence/evaluations` | `config/evaluations.toml` (nuevo y versionado) | Devuelve nombre, cifra, meta, fecha, si cumple la meta y la ruta del informe. Una prueba verifica que cada informe exista en `docs/`. |
- **Razón**:
  - Reutiliza lo que ya existe.
  - Las evaluaciones publicadas son cifras curadas por el equipo, con su honestidad (por ejemplo, 86,0 % y 90,7 %
    frente a 88,4 %). Leerlas de los Markdown sería frágil.
- **Alternativas**:
  - Parsear los informes Markdown: frágil.
  - Correr evaluaciones en vivo: requiere red y claves, y tarda minutos.

## R12. Registro de uso de la consola (FR-028)

- **Decisión**: cada llamada a `/api/v1/planning/*` añade una línea a `planning/console.jsonl` en el directorio de
  estado (`resolve_state_dir()`, fuera de `data/` y del repositorio). Cada línea lleva:
  - `ts`;
  - `endpoint`;
  - `user` (seudónimo de sesión web);
  - `scenario`;
  - `plan_id`;
  - `status`;
  - `duration_ms`.

  No guarda IP ni texto libre sin redactar.
- **Razón**: auditoría sin datos personales, igual que `channels` y `proposals`. Respeta la regla de que la app no
  escribe en `data/` ni en el repositorio.

## R13. Dirección visual (FR-003, FR-004)

- **Decisión**: está en [`design.md`](design.md), hecha con la skill `frontend-design`. En resumen:
  - **tipografía**: Archivo variable, con el eje de ancho como sistema;
  - **color**: la paleta verificada de Manuelita, con un color por producto;
  - **elemento memorable**: el flujo de caña;
  - **ilustraciones**: pictogramas propios de los productos, en SVG en línea.
- **Razón y alternativas**: en el documento, incluida la revisión del plan frente a los defaults genéricos.

## R14. Pruebas (FR-032, SC-006, SC-007)

- **Decisión**:
  - **Backend**: pruebas de API en `tests/api/` para los contratos v1, de integración de paridad (R6) y unitarias de
    `compare` y de los precios del escenario.
  - **Frontend**: vitest para el enrutador, el flujo de caña (geometría y texto accesible), los controles del
    escenario (rangos) y la confirmación de guardado.
  - **Extremo a extremo**: Playwright en `tests/e2e/`, que ya existe y corre sin red con modo demo y
    `MANUELITA_PLANNER_WEB=1`. Cubre las historias 1 y 2, el responsive a 360, 768 y 1440 px (amplía
    `test_responsive.py`) y una revisión de accesibilidad con `axe-core`. `axe-core` es una dependencia de
    desarrollo nueva de `web/`, y la prueba inyecta su `axe.min.js` en la página. No hay dependencia nueva de Python.
- **Razón**: misma pila de pruebas que hoy. `make check` sigue siendo la puerta y `make e2e` el ensayo.

## R15. Riesgo de calendario

- **Decisión**: el orden de entrega es este:
  1. el núcleo (backend v1 de planificación, enrutador y tokens);
  2. la historia 1 (consola);
  3. la historia 2 (entrada y espacio de trabajo, reubicando componentes existentes);
  4. la historia 3 (panel);
  5. la historia 4 (pulido responsive y accesibilidad), que es transversal.

  Si el viernes 27 no está la historia 3, la evidencia se muestra con `/traza` y la terminal, como hoy.
- **Razón**: la consola es lo único que la web actual no puede mostrar. Lo demás reubica capacidades que ya existen.
