# Research: Perfiles abiertos en la web

Sin marcadores NEEDS CLARIFICATION en el contexto técnico. Las decisiones salen de leer el código actual
(`agent/profiles.py`, `agent/service.py`, `agent/graph.py`, `api_planning.py`, `channels/bridge.py` y las
páginas de `web/src`).

## R1. Dónde quitar el filtro

- **Decision**: cambiar la regla en un solo lugar, `profiles.is_authorized(user_id, channel)`. Con `channel ==
  "web"` devuelve `True` siempre. Para los demás canales mantiene `MANUELITA_PLANNER_OPEN` y `VALERIA_PLANNERS`.
- **Rationale**: todos los guardias usan esa función con el canal correcto, así que quedan abiertos sin tocar su
  lógica:
  - `effective_profile` (perfil del turno en `graph.py:513`).
  - `validate_profile` (403 `planner_not_authorized` en `/api/chat`).
  - `describe` (`/api/profiles`).
  - `require_planner` y `/access` (`api_planning.py`).

  El puente de WhatsApp pasa `channel=message.channel`, así que no cambia (FR-014). Un único punto de decisión
  evita que la web y el backend vuelvan a divergir.
- **Alternatives considered**:
  - Quitar `requires_authorization = true` de `config/profiles.toml`: también abriría WhatsApp, fuera de alcance.
  - Activar `MANUELITA_PLANNER_WEB=1` por defecto: depende de la configuración de cada equipo, que es el problema
    original.
  - Borrar las comprobaciones una por una: más cambios y más riesgo de dejar una viva.

## R2. Qué hacer con `MANUELITA_PLANNER_WEB`

- **Decision**: deja de leerse. Si existe en un `.env` viejo, no tiene efecto ni da error (FR-005). Se retira de
  `.env.example`, del README, de `tests/e2e/conftest.py` y de `agent/planning_eval.py`.
- **Rationale**: una variable sin efecto documentada confunde. Ignorarla en silencio es compatible con los
  equipos ya configurados.
- **Alternatives considered**: avisar en consola si está presente. Se descarta porque es ruido para algo que ya
  no importa.

## R3. API v1 de planificación: `require_planner` y `/access`

- **Decision**:
  - `require_planner` se queda como dependencia: sigue devolviendo el seudónimo para el registro (FR-011). Pero en
    la web ya no lanza `planner_forbidden`, porque `is_authorized(..., "web")` es verdadero.
  - Se renombra a `planner_user` para que su nombre diga lo que hace.
  - `/access` se conserva por compatibilidad: responde `authorized: true` y un `reason` que recuerda que los datos
    son sintéticos.
  - El código `planner_forbidden` y `FORBIDDEN_TEXT` se retiran del módulo, porque ninguna ruta web puede
    producirlos.
- **Rationale**:
  - Mantener la ruta evita romper clientes viejos y la prueba de contrato de la spec 026.
  - El registro por seudónimo es una salvaguarda que la spec conserva.
- **Alternatives considered**: eliminar `/access`. Rompe la forma de la API v1 sin beneficio para el usuario.

## R4. Cómo ayudar a elegir perfil (frontend-design)

- **Decision**: el selector deja de ser una fila de píldoras con solo el nombre. Pasa a ser un **registro de
  perfiles**: un grupo de radio donde cada opción muestra:
  - El glifo de producto.
  - El nombre.
  - Una línea de **para quién es** (dato nuevo `forWhom`).
  - Al enfocar o elegir, el ejemplo de pregunta.

  En teléfono, la opción activa se ve completa y las otras se compactan en una lista desplegable con la misma
  semántica de radio. Detalle en [design.md](design.md).
- **Rationale**:
  - FR-007 y SC-003 piden decidir con lo que se ve en menos de 30 s.
  - Reutiliza el lenguaje visual del `ProfileLedger` de la entrada (filas de un libro, no tarjetas iguales), así
    que la entrada y el agente cuentan lo mismo.
- **Alternatives considered**:
  - Tarjetas iguales en cuadrícula: el patrón genérico que el diseño de la spec 026 evitó.
  - Un tooltip por píldora: no funciona en táctil y esconde lo que ayuda a decidir.

## R5. Perfil activo y paso al área de planificación

- **Decision**:
  - Nuevo `ProfileNotice` debajo del selector. Dice «Te atiende como …».
  - Si el perfil es planificador, añade la advertencia de datos sintéticos y un enlace «Abrir la planificación».
  - Abrir `/planificacion` directamente fija el perfil activo en planificador (caso borde de la spec).
- **Rationale**: FR-008 y FR-009. Hoy el encabezado ya dice «Te atiende como …»; se conserva y se completa.
- **Alternatives considered**: redirigir automáticamente a `/planificacion` al elegir el planificador. Se descarta
  porque quita el control a la persona, que puede querer conversar primero.

## R6. Qué se retira de la interfaz

- **Decision**:
  - Se eliminan `PlannerGate.tsx` y su CSS.
  - Se eliminan el estado `plannerAuthorized` en `App`, `Home`, `PlatformHero` y `ProfileLedger`.
  - Se eliminan el `disabled` y el «(solo autorizados)» de `ProfilePicker` y del `<select>` de `ChatView`.
  - Se elimina el `FALLBACK` con `authorized: false` en `Agent.tsx`.
  - `Planning.tsx` deja de pedir `/access`: carga estado y rangos directamente. Si la API respondiera un error, se
    ve el error accionable de siempre.
- **Rationale**:
  - FR-006 y SC-004 piden cero indicios de bloqueo.
  - Una petición menos al abrir la consola.
- **Alternatives considered**: dejar el estado y forzarlo a `true`. Es código muerto.

## R7. Campo `requires_authorization` en `/api/profiles`

- **Decision**:
  - El campo se mantiene, pero se calcula **por canal**: en la web es `false` para los cinco perfiles y
    `authorized` es `true`.
  - Se añade `Profile.requires_authorization_in(channel)`.
  - `/perfil` en WhatsApp sigue mostrando «(solo autorizados)».
- **Rationale**: el contrato no cambia de forma y el dato dice la verdad para quien lo consulta.
- **Alternatives considered**: quitar el campo. Rompería `ProfileOption` y las pruebas de contrato sin necesidad.

## R8. Textos del agente

- **Decision**:
  - `PLANNER_ONLY_NOTE` solo puede aparecer fuera de la web, porque en la web `active == profile` siempre. Se
    reescribe para nombrar el canal: «Por WhatsApp, la planificación es solo para planificadores autorizados…».
  - `prompts/profiles.md` no cambia.
- **Rationale**: no hay cambio de prompt, así que no hace falta una entrada nueva en `prompt_log.md`. Los textos
  del grafo son mensajes de interfaz.
- **Alternatives considered**: ninguna relevante.

## R9. Salvaguardas y evaluación

- **Decision**:
  - No se toca: confirmación en dos pasos, vencimiento de 5 min, límite de 100 pendientes, registro en
    `console.jsonl` y `proposals.jsonl`, advertencia de datos sintéticos, paridad.
  - Se vuelven a correr `planning-eval --mode direct`, `test_console_parity.py` y `make e2e` **sin** variables de
    autorización.
- **Rationale**: SC-002, SC-005 y SC-001 se miden en una instalación sin configurar.
- **Alternatives considered**: añadir límite por usuario a las propuestas. Fuera de alcance: los datos son
  sintéticos y el límite global ya acota el archivo.
