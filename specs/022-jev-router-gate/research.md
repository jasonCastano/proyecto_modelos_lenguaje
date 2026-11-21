# Research: Gatekeeper System One (Jev) para el enrutador de Valer-IA

**Feature**: `022-jev-router-gate` | **Fecha**: 2026-11-20 | **Spec**: [spec.md](./spec.md)

Las fuentes sobre la API de Jev son guías y blogs de terceros (septiembre–octubre de 2026); la documentación oficial
(`docs.typesafe.ai`) no se pudo leer. Cada decisión que depende de un detalle de la API se **verifica en la tarea de
validación preliminar** antes de escribir el cliente definitivo (R1, R2).

## R1 — Proveedor y transporte

- **Decisión**: TypeSafe directo, `POST https://api.typesafe.ai/v1/systemone`, cabecera
  `Authorization: Bearer $TYPESAFE_API_KEY`, cuerpo `{model, state, questions}`. Cliente propio con `httpx` (síncrono,
  un solo intento) en `agent/jev.py`. `httpx` pasa de dependencia de desarrollo a dependencia del proyecto; ya llega
  como transitiva de `langchain-openai`, así que no cambia el entorno.
- **Racional**: el SDK `typesafe-sdk` es otra dependencia en etapa temprana cuya forma de llamada difiere entre
  fuentes; el contrato HTTP es pequeño (una ruta, tres campos) y queda bajo control del proyecto (principio V). Un
  cliente propio permite timeout estricto y el mismo tratamiento de errores que el resto del agente.
- **Alternativas**: `typesafe-sdk` (descartado por dependencia nueva y forma no verificada); OpenRouter
  `/api/alpha/decisions` (bloqueó el registro por verificación antibots y es *alpha*); Vercel AI Gateway y Cloudflare
  Workers AI (pensados para JavaScript y Workers). El cliente acepta `base_url` en la configuración, así que cambiar de
  proveedor compatible no exige reescribir código.

## R2 — Versión del modelo

- **Decisión**: `model = "jev-1.14.0"` fijo en `config/agent.toml`. El chequeo (`agent jev --check`) consulta
  `GET /v1/models` y falla con mensaje accionable si la versión fijada no está disponible. Cada respuesta registra el
  campo `model` devuelto.
- **Racional**: FR-012 y principio I. `jev-latest` cambia sin aviso (las fuentes discrepan sobre a qué versión apunta).
- **Alternativas**: `jev-1.13.0` (si 1.14 no está disponible para la cuenta, se fija 1.13 y se registra en el ADR).

## R3 — Una sola solicitud por turno

- **Decisión**: cada turno hace como máximo **una** solicitud con todas las preguntas activas: `route` (Choice),
  `scope` (Choice), `annoyance` (Score) y `crisis` (Noul). La de `scope` se usa solo si la ruta elegida es
  `out_of_scope`.
- **Racional**: las preguntas de una solicitud se resuelven en paralelo y se factura la entrada, compartida por el
  estado; dos solicitudes duplicarían latencia y costo.
- **Alternativas**: solicitud de `scope` condicionada a la ruta (añade una segunda ida y vuelta); preguntas separadas
  por señal (más latencia).

## R4 — Dónde se consulta y quién gana

- **Decisión**: el nodo `route` (`agent/graph.py`) llama al gatekeeper **una vez**, justo después de `care.analyze()` y
  antes de `route_message()`, salvo que el mensaje sea charla trivial (solo palabras de `SMALLTALK`) o una acción de
  escritura o pregunta de perfil. Con la respuesta:
  1. fusiona `crisis` y `annoyance` en las señales de atención (R6);
  2. pasa la decisión de ruta a `route_message(..., gate=...)`, que la evalúa **después** de `rule_decision()` y
     **antes** del clasificador LLM.
- **Racional**: la segunda red de crisis (FR-017) debe estar lista antes de las reglas, que ya ponen la crisis
  primero. Llamar una sola vez evita pagar dos veces. Las reglas siguen ganando siempre (FR-001); en saludos no se
  consulta (spec US1, escenario 3).
- **Alternativas**: consultar solo cuando las reglas no deciden (pierde la segunda red de crisis en mensajes que las
  reglas de conducta capturan); dos llamadas (más costo y latencia).

## R5 — Confianza y umbral de ruta

- **Decisión**: la confianza es la **probabilidad de la ruta elegida** (máximo de `probabilities`), calculada por el
  proyecto; la alternativa es la segunda más probable. Umbral inicial `route_threshold = 0.75`, inclusivo, que se
  ajusta con la validación preliminar (R10) y se congela antes de la evaluación comparativa.
- **Racional**: la fórmula de `confidence` del proveedor no está publicada y los ejemplos de las guías no la
  reproducen; la probabilidad es interpretable y comparable con la del clasificador LLM. Fijar el umbral con un
  conjunto distinto del de evaluación respeta el principio II.
- **Alternativas**: usar `confidence` del proveedor (opaca); margen entre las dos primeras (más difícil de explicar).

## R6 — Señales de atención

- **Decisión**:
  - **Crisis**: `crisis = crisis_regex OR P(sí) ≥ crisis_threshold` con `crisis_threshold = 0.5`. Nunca se usa el
    gatekeeper para anular la detección determinista.
  - **Molestia**: Score de 4 niveles (calmado, inconforme, molesto, muy molesto). Nivel ≥ 2 y emoción neutral en
    `care.detect_sentiment` ⇒ emoción `frustrated`; nivel 3 ⇒ `angry`. Si el léxico ya detectó una emoción negativa,
    se conserva la más intensa.
  - **Motivo de fuera de alcance**: Choice entre `off_topic`, `abuse`, `harmful`, `third_party`,
    `prompt_extraction` y `advice`. Los motivos `crisis` y `unattainable` de la spec 019 no se delegan: los decide el
    sistema vigente.
- **Racional**: FR-015 a FR-018 y SC-004. El umbral de crisis es bajo porque el costo de un falso positivo (mostrar la
  Línea 106) es mucho menor que el de un falso negativo.
- **Alternativas**: dejar que el gatekeeper decida crisis solo (descartado por seguridad).

## R7 — Privacidad del texto enviado

- **Decisión**: el estado que se envía (mensaje actual e historial reciente) pasa antes por `privacy.redact_pii()`.
  El historial se limita a las mismas `ROUTER_HISTORY_TURNS` preguntas que recibe el clasificador; si el texto supera
  `max_input_chars` (4.000), se recorta primero el historial.
- **Racional**: FR-020. Reutiliza el detector que ya protege la memoria (spec 014) en lugar de crear otro.
- **Alternativas**: enviar el texto sin enmascarar (descartado); enmascarar solo correos (insuficiente).

## R8 — Fallos y tiempo de espera

- **Decisión**: timeout total de 2 s (configurable), **sin reintentos** dentro del turno. Cualquier fallo (red,
  timeout, HTTP 4xx/5xx, respuesta sin `answers`, opción desconocida, `refusal`) devuelve `GateOutcome(status="failed",
  reason=...)` y el turno sigue con el clasificador. Sin clave o con `enabled = false`, el gatekeeper no se construye y
  se registra una sola vez al iniciar.
- **Racional**: FR-010, FR-011 y SC-005: el peor caso añade como mucho 2 s al turno. Reintentar en el turno rompería
  ese límite.
- **Alternativas**: reintento con backoff (excede el presupuesto de latencia); circuito abierto tras N fallos (útil,
  pero se pospone: YAGNI hasta que la evaluación lo justifique).

## R9 — Configuración y activación

- **Decisión**: sección `[jev]` en `config/agent.toml`: `enabled = false`, `base_url`, `model`, `route_threshold`,
  `crisis_threshold`, `timeout_seconds`, `max_input_chars`, `signals = ["route", "scope", "annoyance", "crisis"]`.
  `MANUELITA_JEV_ENABLED=1|0` sobrescribe `enabled` para pruebas manuales. La clave solo se lee de
  `TYPESAFE_API_KEY` (entorno o `.env`, con el mismo `load_dotenv` del proyecto).
- **Racional**: FR-009, FR-018, FR-019; mismo patrón que `[care]` y `[conversation]`.
- **Alternativas**: archivo de configuración propio (más dispersión).

## R10 — Validación preliminar en español

- **Decisión**: conjunto nuevo `tests/fixtures/jev/validation_es.jsonl` con 24 consultas redactadas para esta spec
  (4 por ruta), **distintas** de las 44 consultas de evaluación. `agent jev --validate` las envía al gatekeeper y
  reporta exactitud, cobertura por umbral (0,6 a 0,9) y la matriz de confusión. Si la exactitud con el umbral elegido
  es < 80 % (SC-009), el ADR lo registra como descartado y `enabled` queda en `false`.
- **Racional**: principio II (el conjunto de evaluación no se usa para ajustar) y el soporte de español no publicado.
- **Alternativas**: validar con las 44 consultas (contamina la evaluación).

## R11 — Prompts del gatekeeper

- **Decisión**: `prompts/jev.md`, con secciones por pregunta (`route`, `scope`, `annoyance`, `crisis`) y las
  descripciones de cada opción, cargado con el mecanismo de `agent/prompts.py`. Las descripciones de rutas se redactan
  a partir de `prompts/router.md` para que ambas etapas compartan criterio. Versión y hash en `docs/prompt_log.md`.
- **Racional**: FR-008 y CONSTITUTION §3.6.
- **Alternativas**: descripciones en el TOML (no son configuración, son prompts).

## R12 — Simulación para demo y pruebas

- **Decisión**: `FakeJevGate`, determinista: deriva la ruta de `heuristic_decision()` con probabilidad configurable,
  la crisis de `care.detect_crisis()` y la molestia del léxico vigente. Permite inyectar respuestas y fallos en las
  pruebas. El modo demo (`PML_DEMO=1` o `mode="demo"`) nunca hace llamadas reales.
- **Racional**: FR-013, SC-006 y la regla del proyecto de pruebas sin red.

## R13 — Trazabilidad y métricas

- **Decisión**: `DecidedBy` suma `"jev"` (backend y `web/src/lib/types.ts`, etiqueta «Jev» en la vista técnica).
  `turn_record()` añade el bloque `jev` (`status`, `route`, `confidence`, `alternative`, `latency_ms`, `cost`,
  `model`, `reason`). `TurnMetrics` añade `gate_calls`; las llamadas al gatekeeper **no** cuentan como
  `model_calls`, que siguen midiendo el LLM.
- **Racional**: FR-005, FR-021 y FR-023; las métricas del Módulo 2 siguen siendo comparables.

## R14 — Evaluación comparativa

- **Decisión**: `agent jev --compare` reutiliza `evaluate_router()` con y sin gatekeeper sobre las 44 consultas
  (exactitud, llamadas al LLM, latencia de enrutamiento, costo, % de decisiones de Jev) y corre las baterías
  `agent care` (36 casos) y `agent converse` (12 conversaciones) con el gatekeeper para verificar las señales y las
  crisis. La latencia de extremo a extremo (SC-003) se mide con `agent evaluate --mode real --compare` con
  `MANUELITA_JEV_ENABLED=1`. Salida: `docs/evaluacion_jev.{md,json}` y una sección en `docs/evaluacion_modulo2.md`.
- **Racional**: FR-022 a FR-025 reutilizando las herramientas existentes (principio V).

## Resultado de la validación preliminar (T014, 2026-11-21)

- **API real**: `POST https://api.typesafe.ai/v1/systemone` con `{model, state, questions}` responde exactamente con la
  forma del contrato §2 (`answers.<pregunta>.type`, `choice`, `probabilities`, `score`, `legend`, `noul`, `usage`). La
  respuesta de Choice y Score trae además `confidence` del proveedor, que no se usa (R5). No trae `usage.cost`; el
  costo se estima con `input_tokens` × 0,042 USD/M.
- **Versión**: `GET /v1/models` solo lista los alias `jev-latest` y `jev-preview`, pero la versión fija `jev-1.14.0` se
  acepta y responde con `"model": "jev-1.14.0"`. Se mantiene fija (R2); `agent jev --check` la confirma con una
  pregunta mínima cuando no aparece en la lista.
- **Español**: 24/24 rutas correctas (100 %) en `validation_es.jsonl`; cobertura 100 % hasta el umbral 0,80 y 96 % en
  0,90. Latencia media 220 ms, p95 271 ms; costo de las 24 consultas 0,0013 USD (~1.250 tokens de entrada por
  consulta con las cuatro preguntas).
- **Umbral congelado**: `route_threshold = 0.75` (sin cambios). SC-009 se cumple; la integración continúa.
