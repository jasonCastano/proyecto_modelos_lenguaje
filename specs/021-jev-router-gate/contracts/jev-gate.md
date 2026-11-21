# Contrato: gatekeeper Jev (spec 021)

## 1. Solicitud al proveedor (salida del proyecto)

`POST {base_url}/v1/systemone` con `Authorization: Bearer $TYPESAFE_API_KEY` y `Content-Type: application/json`.

```json
{
  "model": "jev-1.14.0",
  "state": {
    "mensaje": "¿Cuánto azúcar produjo Manuelita en 2021 frente a lo que dice el informe?",
    "historial": ["¿Qué produce Manuelita?"]
  },
  "questions": {
    "route": {"type": "choice", "instructions": "<prompts/jev.md#route>",
              "criteria": {"direct": "…", "documental": "…", "structured": "…",
                           "mixed": "…", "out_of_scope": "…", "clarify": "…"}},
    "scope": {"type": "choice", "instructions": "<prompts/jev.md#scope>", "criteria": {"off_topic": "…"}},
    "annoyance": {"type": "score", "instructions": "<prompts/jev.md#annoyance>",
                  "criteria": ["calmado", "inconforme", "molesto", "muy molesto"]},
    "crisis": {"type": "noul", "instructions": "<prompts/jev.md#crisis>"}
  }
}
```

- `state.mensaje` y `state.historial` llegan **enmascarados** (`redact_pii`) y recortados a `max_input_chars`.
- Solo se incluyen las preguntas listadas en `[jev].signals`.
- La forma exacta de la API se verifica en la validación preliminar (research R1); si difiere, se ajusta este
  contrato antes de implementar el cliente definitivo.

## 2. Respuesta esperada del proveedor

```json
{
  "model": "jev-1.14.0",
  "answers": {
    "route": {"type": "choice", "choice": "mixed",
              "probabilities": {"mixed": 0.82, "structured": 0.12, "documental": 0.06,
                                "direct": 0, "out_of_scope": 0, "clarify": 0}},
    "annoyance": {"type": "score", "score": 0.1, "probabilities": {"0": 0.9, "1": 0.1, "2": 0, "3": 0}},
    "crisis": {"type": "noul", "noul": 0.01}
  },
  "usage": {"input_tokens": 612, "output_tokens": 40}
}
```

Validación (Pydantic): una respuesta sin `answers.route`, con una opción fuera de la lista, con
`{"type": "refusal"}` o con probabilidades que no suman ≈ 1 ⇒ `GateOutcome(status="failed",
reason="invalid_response"|"refusal")`.

## 3. Interfaz interna (`agent/jev.py`)

```python
class JevGate(Protocol):
    def assess(self, message: str, history: Sequence[str]) -> GateOutcome: ...


def build_gate(config: JevConfig, *, demo: bool = False) -> JevGate | None: ...
def merge_signals(signals: CareSignals, outcome: GateOutcome, config: JevConfig) -> CareSignals: ...
```

- `build_gate` devuelve `None` si `enabled` es falso o falta la clave (registra el motivo una vez), y `FakeJevGate` en
  modo demo.
- `assess` **nunca** lanza excepciones; todo fallo se expresa en `GateOutcome`.
- `merge_signals` aplica research R6: la crisis es la unión; la molestia solo intensifica.

## 4. Orden de decisión en el nodo `route` (cambios marcados con ★)

1. Acción de escritura o pregunta de perfil (sin cambios) — el gatekeeper no se consulta.
2. `care.analyze()` (sin cambios).
3. ★ `gate.assess()` si hay gatekeeper y el mensaje no es charla trivial; ★ `merge_signals()`.
4. `rule_decision(message, signals)` — crisis primero, luego conducta, saludo, etc. **Si decide, gana.**
5. ★ Decisión del gatekeeper: si `status == "ok"` y `confidence ≥ route_threshold` ⇒
   `RouteDecision(decided_by="jev", confidence, alternative, scope_reason)`.
6. Clasificador LLM (sin cambios), o heurística en demo sin gatekeeper.
7. `RouteDecision.effective(min_confidence)` sobre la decisión final (FR-007).

## 5. CLI

| Comando | Qué hace | Salida | Código |
|---|---|---|---|
| `uv run python -m proyecto_modelos_lenguaje.agent jev --check` | Verifica clave, red y versión fijada (`GET /v1/models`) | JSON `{ok, model, base_url, latency_ms, detail}` | 0 disponible · 2 sin clave, sin red o versión ausente |
| `… agent jev --validate [--json]` | Validación preliminar en español (`tests/fixtures/jev/validation_es.jsonl`) | exactitud, cobertura por umbral, confusión | 0 · 2 sin clave |
| `… agent jev --compare [--json]` | Comparación sin/con gatekeeper (router, care, converse) | `docs/evaluacion_jev.{md,json}` y sección en `docs/evaluacion_modulo2.md` | 0 · 2 sin clave |

Ningún comando imprime la clave. Sin clave, el mensaje indica añadir `TYPESAFE_API_KEY` a `.env`.

## 6. API y web

- `POST /api/chat` y `/api/chat/stream`: sin cambios de forma; `route.decided_by` puede valer `"jev"`, cada turno
  trae `metrics.gate_calls` y el bloque `jev` (`status`, `reason`, `route`, `confidence`, `alternative`,
  `accepted`, `latency_ms`, `cost`, `model`), sin texto del visitante ni clave.
- `GET /api/observability`: campo `gatekeeper` con `state` (`disabled`, `simulated`, `no_key` o `active`),
  `model`, `route_threshold` y `signals`. Nunca incluye la clave ni indica su valor.
- Web (vista técnica):
  - chip «Jev: activo · jev-1.14.0» / «desactivado» / «sin clave (desactivado)» / «simulado (demo)»;
  - en la traza del turno: «Jev: <ruta> <confianza> · <ms>» si decidió, «Jev sugirió <ruta> (<confianza>) →
    decidió el LLM» si no alcanzó el umbral, y «Jev no disponible (<motivo>) → decidió el LLM» si falló;
  - `decided_by: "rules" | "llm" | "demo" | "jev"` con la etiqueta «Jev (System One)».
- La activación nunca se controla desde la web: solo `[jev].enabled` o `MANUELITA_JEV_ENABLED` en el servidor.
