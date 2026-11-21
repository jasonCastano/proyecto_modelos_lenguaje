# Data Model: Gatekeeper System One (Jev)

**Feature**: `022-jev-router-gate` | **Fecha**: 2026-11-20

Todas las entidades viven en memoria durante el turno; lo único que persiste es el bloque `jev` del registro del turno
(`$MANUELITA_STATE_DIR/logs/turns.jsonl`) y los informes de evaluación en `docs/`.

## JevConfig (`config/agent.toml` → `[jev]`)

| Campo | Tipo | Valor por defecto | Validación |
|---|---|---|---|
| `enabled` | bool | `false` | `MANUELITA_JEV_ENABLED=1/0` lo sobrescribe |
| `base_url` | str | `https://api.typesafe.ai` | `https://`; sin barra final |
| `model` | str | `jev-1.14.0` | no vacío; MUST NOT terminar en `latest` (FR-012) |
| `route_threshold` | float | `0.75` | `0.5 ≤ x ≤ 1.0` |
| `crisis_threshold` | float | `0.5` | `0.1 ≤ x ≤ 0.9` |
| `timeout_seconds` | float | `2.0` | `0.2 ≤ x ≤ 10` |
| `max_input_chars` | int | `4000` | `500 ≤ x ≤ 30000` |
| `signals` | list[str] | `["route", "scope", "annoyance", "crisis"]` | subconjunto de esos cuatro; `route` obligatorio |

La clave (`TYPESAFE_API_KEY`) **no** forma parte de `JevConfig`: se lee del entorno al construir el cliente y nunca se
serializa (FR-019).

## GateQuestionSet (`prompts/jev.md`)

| Pregunta | Tipo Jev | Opciones / niveles |
|---|---|---|
| `route` | Choice | `direct`, `documental`, `structured`, `mixed`, `out_of_scope`, `clarify` |
| `scope` | Choice | `off_topic`, `abuse`, `harmful`, `third_party`, `prompt_extraction`, `advice` |
| `annoyance` | Score | 0 calmado · 1 inconforme · 2 molesto · 3 muy molesto |
| `crisis` | Noul | sí = riesgo para la vida o la integridad de alguien |

Cada pregunta tiene `instructions` y descripciones por opción, versionadas con hash en `docs/prompt_log.md`.

## GateDecision

Decisión de ruta derivada de la respuesta.

| Campo | Tipo | Regla |
|---|---|---|
| `route` | `Route` | opción con mayor probabilidad |
| `probabilities` | dict[Route, float] | las seis rutas; suma ≈ 1 (tolerancia 0,01) |
| `confidence` | float | `probabilities[route]` (R5) |
| `alternative` | `Route \| None` | segunda más probable |
| `scope_reason` | `ScopeReason \| None` | solo si `route == "out_of_scope"` y la señal `scope` está activa |

## GateSignals

| Campo | Tipo | Regla |
|---|---|---|
| `crisis_probability` | float \| None | P(sí) de la pregunta `crisis` |
| `annoyance` | float \| None | puntaje 0–3 (media ponderada que devuelve Score) |
| `annoyance_level` | int \| None | `round(annoyance)` |

## GateOutcome

Resultado de una consulta; es lo que recibe el resto del sistema.

| Campo | Tipo | Regla |
|---|---|---|
| `status` | `"ok" \| "failed" \| "skipped"` | `skipped`: desactivado, charla trivial o acción de escritura |
| `reason` | str \| None | si `failed`: `timeout`, `network`, `http_401`, `http_402`, `http_422`, `http_429`, `http_5xx`, `invalid_response`, `refusal`; si `skipped`: `disabled`, `no_key`, `smalltalk`, `write_intent` |
| `decision` | `GateDecision \| None` | presente si `status == "ok"` |
| `signals` | `GateSignals \| None` | presente si `status == "ok"` |
| `latency_ms` | int | ≥ 0 |
| `cost` | float \| None | `usage` informado por el proveedor; `None` si no lo informa |
| `model` | str \| None | versión que respondió |

**Transiciones**: `skipped` (sin llamada) · `ok` → la decisión se acepta si `confidence ≥ route_threshold`, si no se
delega · `failed` → se delega siempre.

## Cambios en modelos existentes

- `models.DecidedBy`: `Literal["rules", "llm", "demo", "jev"]`.
- `models.TurnMetrics`: campo `gate_calls: int = 0` (≥ 0). `model_calls` no cambia de significado.
- `RouterResult` (`agent/router.py`): campo `gate: GateOutcome | None` con el resultado usado o descartado.
- Registro del turno (`observability.turn_record`): bloque `jev` con `status`, `reason`, `route`, `confidence`,
  `alternative`, `accepted` (bool), `latency_ms`, `cost`, `model`. Sin texto del visitante ni clave.
- `web/src/lib/types.ts`: `decided_by` suma `"jev"`; `ChatView.tsx` añade la etiqueta.

## JevComparisonReport (`docs/evaluacion_jev.json`)

| Campo | Contenido |
|---|---|
| `meta` | `run_id`, fecha, `model`, umbrales, commit |
| `validation` | exactitud y cobertura por umbral sobre `validation_es.jsonl` |
| `router` | por configuración (`baseline`, `jev`): exactitud, llamadas LLM/consulta, latencia media y p95 de enrutamiento, % decisiones de Jev, costo |
| `care` | crisis detectadas/esperadas y aciertos de señales, con y sin gatekeeper |
| `end_to_end` | % < 10 s y p95 por variante (cadena, agente) con el gatekeeper, frente a `variants-real-2026-11-14` |
