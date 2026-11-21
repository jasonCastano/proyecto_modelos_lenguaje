# Quickstart: validar el gatekeeper Jev (spec 021)

## Requisitos

- Entorno del proyecto: `make dev` (o `uv sync`).
- Para los pasos con red: una clave de TypeSafe en `.env` (nunca en el repositorio):

  ```bash
  TYPESAFE_API_KEY=sk-...
  ```

  Cada integrante usa su propia clave. Sin clave, los escenarios 1 y 2 funcionan igual.

## Escenario 1 — Pruebas sin red ni clave (US2, SC-006)

```bash
uv run pytest tests/unit -k "jev or router or care"
make check
```

**Esperado**: todo en verde; las pruebas usan `FakeJevGate`.

## Escenario 2 — La aplicación sin gatekeeper se comporta igual (US2, SC-005)

```bash
uv run python -m proyecto_modelos_lenguaje.agent chat "¿Qué produce Manuelita?" --mode demo --thread q1
```

**Esperado**: respuesta normal; en la línea de ruta, `decided_by` es `rules`, `llm` o `demo`, nunca un error.

## Escenario 3 — Chequeo del servicio (FR-014)

```bash
uv run python -m proyecto_modelos_lenguaje.agent jev --check
```

**Esperado**: JSON con `"ok": true` y la versión fijada (código 0). Sin clave: mensaje accionable y código 2.

## Escenario 4 — Validación preliminar en español (US4, SC-009)

```bash
uv run python -m proyecto_modelos_lenguaje.agent jev --validate
```

**Esperado**: exactitud ≥ 80 % con el umbral elegido y la tabla de cobertura por umbral. Si queda por debajo, el
gatekeeper se deja desactivado y se documenta en el ADR.

## Escenario 5 — Decisión con gatekeeper en una conversación real (US1)

```bash
MANUELITA_JEV_ENABLED=1 uv run python -m proyecto_modelos_lenguaje.agent chat --mode real --thread j1 \
  "¿Cuánto azúcar produjo Manuelita en 2021 frente a lo que dice el informe de sostenibilidad?"
```

**Esperado**: `ruta mixed (0.8x, jev)` y una llamada menos al modelo de lenguaje que sin gatekeeper. En
`$MANUELITA_STATE_DIR/logs/turns.jsonl`, el bloque `jev` con `status`, `confidence`, `accepted`, `latency_ms` y
`cost`, sin la clave ni datos personales.

## Escenario 6 — Fallo del servicio (US2)

```bash
TYPESAFE_API_KEY=sk-invalida MANUELITA_JEV_ENABLED=1 uv run python -m proyecto_modelos_lenguaje.agent chat \
  --mode real --thread j2 "¿Qué certificaciones tiene Manuelita?"
```

**Esperado**: respuesta normal decidida por `llm`; el registro anota `jev.status = "failed"` y `reason = "http_401"`.

## Escenario 7 — Señales de atención (US3, SC-004)

```bash
MANUELITA_JEV_ENABLED=1 uv run python -m proyecto_modelos_lenguaje.agent care --mode real
```

**Esperado**: todos los casos de crisis detectados (0 perdidos) y el informe de la batería con las señales del
gatekeeper.

## Escenario 8 — Evaluación comparativa (US4, SC-001 a SC-003, SC-007)

```bash
uv run python -m proyecto_modelos_lenguaje.agent jev --compare
MANUELITA_JEV_ENABLED=1 uv run python -m proyecto_modelos_lenguaje.agent evaluate --mode real --compare --skip-router
```

**Esperado**: `docs/evaluacion_jev.md` con exactitud (sin caer más de 2 puntos), ≥ 50 % de decisiones sin el LLM,
costo < 1 USD, y la comparación de extremo a extremo con ≥ 95 % de respuestas bajo 10 s en ambas variantes.

## Para Jason

1. `git pull` en `main` tras la fusión y `uv sync`.
2. Crear su clave en `https://console.typesafe.ai` (*API Keys*) y añadir `TYPESAFE_API_KEY` en **su** `.env`.
3. `uv run python -m proyecto_modelos_lenguaje.agent jev --check`.
4. Sin clave, todo sigue funcionando sin gatekeeper.
