# Research — Spec 025: plataforma de agentes por perfil y planificación industrial

**Fecha**: 2026-11-24 | **Autor**: Roberto José Guerrero | **Spec**: [spec.md](spec.md)

Cada decisión resuelve una incógnita del contexto técnico del [plan](plan.md). Formato: decisión, razón y
alternativas descartadas.

## R1 — Dónde se declaran los perfiles

- **Decisión:**
  - `config/profiles.toml` declara los cinco perfiles con estos campos:
    - `key`;
    - `label`;
    - `tools`: lista blanca de nombres del catálogo;
    - `requires_authorization`;
    - `triggers`: frases de autopresentación.
  - `prompts/profiles.md` (versionado, con su entrada en `docs/prompt_log.md`) tiene una sección `##` por perfil con
    el foco que se añade al system prompt.
  - `agent/profiles.py` carga y valida ambos. Al cargar, falla si:
    - un nombre de herramienta no existe en el catálogo;
    - falta la sección de un perfil;
    - el perfil `visitante` no ofrece exactamente el catálogo actual.
  - `config/profiles.toml` incluye `[profiles] enabled = true`. Con `false`, solo existe `visitante` y la ruta
    `planning` no se activa: es el interruptor de respaldo para la demo.
- **Razón:** es el mismo patrón que `config/official_channels.toml` y los prompts por secciones (`load_agent_prompt`).
  Hay una sola fuente, auditable y probada (constitución, regla 16).
- **Alternativas:**
  - Perfiles en código Python: mezclan contenido editorial con lógica.
  - Un agente por perfil: rompe «un solo agente» (ADR 0028).

## R2 — Cómo se combinan perfil y ruta

- **Decisión:** las herramientas ofrecidas son la intersección `specs_for_route(route) ∩ profile.tools`. Las de
  escritura comunes (memoria, exportar, contacto) siguen en todos los perfiles. `catalog.build_catalog_tools` recibe
  un parámetro nuevo `profile`. La traza agrega `profile` al turno (`Turn.profile`, `turns.jsonl`, `/traza`).
- **Razón:** no cambia el router evaluado (reglas → Jev → LLM). El perfil solo restringe la oferta, y así no hay
  regresión en la batería de herramientas del perfil visitante.
- **Alternativa:** un router distinto por perfil, que obligaría a reevaluar todo.

## R3 — Ruta nueva `planning`

- **Decisión:**
  - Se añade `planning` al `Route` (`agent/models.py`, `api_models.py`, `catalog.ROUTES`, `web/src/lib/types.ts`) y a
    `PLAN_BY_ROUTE`, con este plan: consultar el estado y los compromisos, optimizar y simular la alternativa,
    comparar y explicar.
  - **Solo la deciden las reglas**: `tool_cue_decision` reconoce señales de planificación (programa de producción,
    escenario, menos caña, vapor, contratos de azúcar o etanol, energía comprometida), y solo si el perfil activo es
    `planificador`.
  - Jev y el clasificador LLM no conocen la ruta. Si devolvieran algo fuera de su lista, se aplica el respaldo
    actual.
  - Con un perfil distinto, las mismas señales llevan a una respuesta fija («la planificación es para planificadores
    autorizados»), sin herramientas.
- **Razón:** la ruta da un subconjunto de herramientas, un plan visible y límites propios, sin tocar el prompt ni la
  exactitud del clasificador. Las reglas son deterministas y gratuitas.
- **Alternativa:** reutilizar `structured`. Mezclaría herramientas de planta con las de datos públicos y ensuciaría
  la batería de herramientas.

## R4 — Límites de llamadas en la ruta `planning`

- **Decisión:** se crea la tabla `[agent.route_limits.planning]` en `config/agent.toml`, con `tool_call_limit = 5` y
  `model_call_limit = 6`. Las demás rutas conservan 3 y 5. `AGENTS.md` del workspace lo documenta («hasta cinco
  herramientas en planificación»).
- **Razón:** la secuencia mínima de la planificación son tres o cuatro invocaciones: estado, compromisos, optimización
  y, opcionalmente, una simulación de alternativa.

## R5 — Biblioteca de programación lineal

- **Decisión:** `scipy.optimize.linprog(method="highs")`. SciPy 1.18.1 ya está en `uv.lock` como dependencia de
  scikit-learn; se declara explícitamente `scipy>=1.14` en `pyproject.toml`, y no se descarga nada nuevo.
- **Razón:** HiGHS da el óptimo global, el estado de factibilidad y los **duales** (`res.ineqlin.marginals`) para la
  sensibilidad. Es determinista, offline y funciona con Python 3.14.
- **Alternativas:**
  - PuLP y CBC: binario externo y otra dependencia.
  - OR-Tools: pesado y con ruedas inciertas para Python 3.14.
  - cvxpy: excesivo para un problema lineal.
  - Un símplex propio: riesgo de errores con cuatro días de margen.

## R6 — Formulación del modelo de planta de caña

- **Decisión:** es un modelo lineal semanal con cinco variables:

  | Variable | Significado |
  |---|---|
  | `x_s` | t de caña a la línea de azúcar |
  | `x_e` | t de caña a jugo directo a destilería |
  | `b` | t de bagazo quemado en calderas |
  | `v` | t de vapor generado |
  | `g` | MWh exportados |

  Las ecuaciones están en [data-model.md §4](data-model.md). Hay rendimientos por calidad de caña, balance de
  bagazo, vapor y energía, capacidades (molienda, destilería, caldera, turbogenerador), contratos mínimos y la
  energía comprometida. La función objetivo es el margen total: precios netos menos costos variables.
- **Razón:** captura la decisión de mezcla azúcar-etanol-energía de la idea 7.4. Es explicable en dos minutos de la
  discusión técnica y lineal en las variables, por eso tiene óptimo global.
- **Alternativa:** un modelo no lineal o dinámico (gemelo digital), que queda fuera de alcance (idea 2).

## R7 — Sensibilidad y restricción limitante

- **Decisión:**
  - Las restricciones activas (holgura ≤ 1e-6 relativa, dual > 0) se ordenan con los **compromisos primero** y,
    dentro de cada grupo, por valor económico (dual × lado derecho). La primera es la que «limita»; el
    `plan_card` muestra las dos primeras. *Ajuste en la implementación*: comparar |dual| crudos mezclaba
    unidades (COP por L frente a COP por t) y escondía el contrato de etanol, que es la respuesta de negocio.
  - La sensibilidad reporta, para cada restricción activa, el dual como «margen adicional por unidad relajada», con
    su unidad (por ejemplo, COP por t de vapor).
  - Las alternativas son:
    1. el óptimo;
    2. «priorizar energía»: maximizar el margen con la exportación al máximo factible;
    3. la «mezcla actual» del estado de planta, evaluada con el simulador.
- **Razón:** responde «qué restricción limita» y «cuánto vale relajarla», que es la pregunta de negocio del ejemplo
  de la idea 7.4.

## R8 — Escenarios sin solución

- **Decisión:**
  - Si HiGHS devuelve infactible (estado 2), se resuelve un **LP elástico**: cada contrato y la energía comprometida
    reciben una variable de faltante ≥ 0, penalizada con **10³ × precio unitario ÷ prioridad** (cada unidad
    faltante cuesta mil veces su valor, así que el LP solo deja faltantes cuando no hay otra opción y
    respeta el orden de prioridad). *Ajuste en la implementación*: un factor fijo de 10⁶ por unidad no
    era comparable entre toneladas, litros y MWh.
  - La respuesta nombra el compromiso con faltante, su cantidad y el plan de menor incumplimiento.
  - Nunca se relajan capacidades físicas.
- **Razón:** es la regla 19 de la constitución: declarar el conflicto sin inventar capacidad.

## R9 — Óptimo de referencia independiente para la batería

- **Decisión:**
  - `agent/planning_reference.py` hace una búsqueda exhaustiva vectorizada con NumPy sobre una malla de 2001 × 2001
    valores de (`x_s`, `x_e`).
  - Para cada par, `b`, `v` y `g` salen en forma cerrada: se quema el bagazo justo para cubrir el vapor, hasta la
    capacidad de caldera, y se exporta el excedente.
  - El generador de la batería guarda el óptimo de referencia en el fixture.
  - La prueba exige que el margen del LP sea ≥ 99 % de la referencia y que la referencia no supere al LP en más de la
    resolución de la malla (SC-001).
- **Razón:** valida el optimizador con un método que no comparte código ni solver (principio V, FR-020).
- **Alternativa:** comparar con el mismo `linprog`, que sería circular.

## R10 — Datos sintéticos

- **Decisión:**
  - `scripts/generate_planning_data.py --seed 2026 --version v1` escribe en `data/synthetic/planificacion/v1/`:
    - `plant_cana.json`: capacidades, coeficientes y costos;
    - `state.json`: inventarios, equipos y caña disponible por semana;
    - `commitments.json`: contratos semanales de azúcar, etanol y energía;
    - `procedures/*.md`: 10 a 12 procedimientos operativos cortos;
    - `DATA_CARD.md`.
  - Son unos 50 KB, así que van en Git normal, no en LFS.
  - Cada archivo lleva `"synthetic": true`, la semilla y la versión.
  - Los órdenes de magnitud se anclan en cifras públicas citadas en la ficha. Por ejemplo, cogeneración de unos
    200.000 MWh/año y excedentes de 45.000–48.000 MWh/año (IS 2023-2024, p. 57 y 124) dan unos 3.800 MWh/semana
    generados.
- **Razón:** es la regla 18 de la constitución, reproducible y sin datos reales.
- **Alternativa:** valores a mano sin semilla, que no se pueden regenerar ni auditar.

## R11 — Procedimientos operativos y citas `[S#]`

- **Decisión:**
  - Los procedimientos sintéticos se indexan en memoria con BM25 (`retrieval.tokenize`). Son pocos documentos y no
    justifican una colección de Qdrant.
  - `search_operating_procedures` devuelve fragmentos etiquetados `S#`.
  - `collect_evidence` y `validate_answer` aceptan `S#` con `kind="synthetic"`.
  - WhatsApp los lista bajo «Fuentes sintéticas (demostración):», separados de las públicas.
  - Pasan por el mismo `guard.neutralize` que el corpus público.
- **Razón:** las citas se distinguen de `[U#]` y `[F#]` (regla 18) y conservan el blindaje.
- **Alternativa:** una colección de Qdrant aparte, que añade operación y nada de valor para unos 12 documentos.

## R12 — Garantías de la respuesta de planificación

- **Decisión:**
  - `optimize_production_plan` devuelve un **resultado estructurado** (JSON) y un `plan_card`: un texto corto
    renderizado en código con las cifras, la restricción limitante, la alternativa, los supuestos, la etiqueta
    «Datos sintéticos (demostración)» y la frase «El agente recomienda; el equipo de planta decide».
  - Un validador posterior (`planning.check_answer`) exige que cada número de la respuesta del modelo aparezca en las
    salidas de herramientas del turno (normalizados) y que estén la etiqueta y la frase.
  - Si algo falla, la respuesta se reemplaza por el `plan_card`.
  - El último resultado se guarda en el estado del hilo (`ChatState.last_plan`) con su id.
- **Razón:** las cifras salen de código (regla 19, FR-012) aunque el modelo parafrasee. El respaldo determinista
  protege la demo.
- **Alternativa:** confiar en el prompt, que no se puede verificar.

## R13 — Guardar la propuesta

- **Decisión:**
  - `save_production_proposal` es una herramienta de escritura en `actions.WRITE_TOOLS`, con aprobación humana como
    las demás. Su argumento es `plan_id`, el del `last_plan`, más una `note` opcional; el plan **no** viaja en los
    argumentos.
  - Al ejecutarse, toma el plan del estado del hilo y lo añade a `$MANUELITA_STATE_DIR/planning/proposals.jsonl`
    con el seudónimo, la fecha, la versión de datos y los supuestos.
  - Si no hay `last_plan` o el id no coincide, responde con un error controlado.
- **Razón:** el modelo no puede alterar las cifras guardadas. Ninguna escritura toca sistemas reales (regla 20).

## R14 — Autorización del planificador

- **Decisión:** `profiles.is_authorized(user_id)` admite a un usuario si se cumple alguna de estas condiciones:
  - el seudónimo está en `VALERIA_PLANNERS` (lista separada por comas en `.env`);
  - `MANUELITA_PLANNER_OPEN=1` está activo (solo para la jornada, igual que `pairing`);
  - el turno viene de la web con la vista técnica y `MANUELITA_PLANNER_WEB=1`.

  Los intentos denegados se registran en `channels.jsonl` como `planner_denied`, sin número ni texto.
- **Razón:** es la regla 20, sin datos de personas en el repositorio.

## R15 — Elegir y recordar el perfil

- **Decisión:**
  - `/perfil` lista los perfiles y `/perfil <key>` activa uno en el **hilo**, en `ChatState.profile`, sin escritura
    persistente. Es una acción explícita del usuario.
  - Para recordarlo entre hilos, el agente propone `save_preference(key="audience", value=<key>)`, con aprobación.
    Para eso, `audience` se añade a `PREFERENCE_KEYS`, y `/olvidar` lo borra.
  - Si el usuario se presenta («soy proveedor…»), los `triggers` del perfil activan esa propuesta.
  - En la web, `ChatRequest.profile` (opcional) y un selector en la vista técnica hacen lo mismo que `/perfil`.
- **Razón:** es la regla 16 (persistir solo con aprobación) y reutiliza la memoria de largo plazo existente.

## R16 — MCP y modo degradado

- **Decisión:**
  - `ToolSpec` gana `mcp_allowed: bool = True`.
  - `simulate_production_scenario` y `optimize_production_plan` se declaran con `mcp_allowed=False`.
  - El MCP sí expone `get_plant_state`, `get_commitments` y `search_operating_procedures`, que son de lectura y
    sintéticos.
  - `AGENTS.md`: «En modo degradado no se planifica».
- **Razón:** es FR-017 y la regla 20. El agente nativo no debe producir planes sin el validador de R12.

## R17 — Evaluaciones

- **Decisión:**
  - `agent planning-eval` corre la batería `tests/fixtures/agent/planning_scenarios.jsonl`: 12 escenarios generados
    con semilla, 2 de ellos infactibles. Hay dos modos:
    - **directo**, que llama al optimizador sin LLM y mide SC-001;
    - **agente**, con DeepSeek, que mide SC-002 y SC-004.
  - `agent profiles-eval` corre `tests/fixtures/agent/profile_routing.jsonl` (20 consultas) y mide SC-003.
  - Los informes son `docs/evaluacion_planificacion.{md,json}` y `docs/evaluacion_perfiles.{md,json}`.
  - La batería de herramientas (53 casos) se corre otra vez con el perfil visitante y se añaden 6 casos del
    planificador, reportados aparte para no mezclar la línea base (SC-005).
- **Razón:** son los principios V y II: baterías fijadas antes de evaluar y separadas de la línea base.

## R18 — Planta de palma (P3)

- **Decisión:** el mismo contrato de herramientas, con `plant_id ∈ {"cana", "palma"}`, y `plant_palma.json` con las
  variables aceite refinado, biodiésel y palmiste. Se implementa solo si las fases P1 están en verde el jueves 26 a
  mediodía. Si no, el esquema acepta solo `"cana"` y la spec lo registra como pendiente.
