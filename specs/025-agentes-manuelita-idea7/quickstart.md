# Quickstart — Validar la spec 025

Guía de validación de extremo a extremo. Los contratos están en [`contracts/`](contracts/) y las entidades en
[data-model.md](data-model.md).

## 0. Requisitos previos

- `uv sync --frozen` y `make check` en verde en `main` (spec 024 integrada).
- Para los pasos con modelo real, `DEEPSEEK_API_KEY` en `.env`. En `.env` también van `VALERIA_PLANNERS` (los
  seudónimos `wa-…` del equipo) y `MANUELITA_PLANNER_WEB=1`.

## 1. Datos sintéticos reproducibles (FR-008)

```bash
uv run python scripts/generate_planning_data.py --seed 2026 --version v1 --check
```

Esperado: código 0 (regenerar no cambia ningún byte), y `DATA_CARD.md` con `synthetic: true` y las citas de
magnitud.

## 2. Optimizador sin LLM (FR-010, FR-011, SC-001)

```bash
uv run python -m proyecto_modelos_lenguaje.agent planning --scenario '{"cane_delta_pct": -15}'
uv run python -m proyecto_modelos_lenguaje.agent planning --scenario '{"cane_delta_pct": -35}'
uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct
```

Esperado:

- **−15 %:** `status: optimal`, con la restricción limitante, la alternativa y la etiqueta sintética.
- **−35 %:** `status: infeasible_relaxed`, con el compromiso que falta y su cantidad.
- **Batería directa:** ≥ 99 % del óptimo de referencia en 10/10 escenarios factibles, 0/12 violaciones y 2/2
  infactibles detectados.

## 3. Catálogo de 26 herramientas (FR-009)

```bash
uv run python -m proyecto_modelos_lenguaje.agent tools
```

Esperado: 26 herramientas. Las 21–25 están en la ruta `planning`; la 26 es de escritura con aprobación. Las 24 y 25
tienen `mcp: false`, y `docs/herramientas.md` se regenera igual al catálogo.

## 4. Perfiles en la web (FR-001 a FR-007)

```bash
make app   # http://127.0.0.1:8000, vista técnica
```

1. Elegir **Proveedor** y preguntar «¿Qué apoyo técnico dan a los proveedores de caña?». Esperado: citas `[U#]` y la
   traza con `Perfil: Proveedor` y solo herramientas del perfil.
2. Elegir **Cliente B2B** y pedir «una cotización de azúcar orgánica». Esperado: certificaciones citadas, ningún
   precio y la propuesta de contacto humano con «SÍ».
3. Elegir **Planificador** y escribir «Tenemos 15 % menos caña esta semana. ¿Cómo cumplimos azúcar, etanol y
   energía?». Esperado:
   - la traza con `get_plant_state → get_commitments → optimize_production_plan` (y quizá
     `simulate_production_scenario`);
   - el plan, la alternativa, los supuestos, «Datos sintéticos» y «el equipo de planta decide».
4. Escribir «guarda esta propuesta», luego «SÍ». Esperado: una línea nueva en
   `$MANUELITA_STATE_DIR/planning/proposals.jsonl`.

## 5. Canal WhatsApp sin teléfono, y luego con teléfono (FR-016, FR-004)

```bash
uv run pml channels simulate --profile planificador "Tenemos 15 % menos caña esta semana…"
```

Después, desde un teléfono autorizado: `/perfil` y `/perfil planificador`, la solicitud de ejemplo y `/traza`.
Desde un número no autorizado, `/perfil planificador` debe ser rechazado.

## 6. Modo degradado (FR-017)

Con el backend detenido, el agente nativo de OpenClaw lista por MCP `get_plant_state`, pero **no**
`optimize_production_plan` ni `simulate_production_scenario`. Ante una solicitud de planificación, responde que en
modo básico no planifica.

## 7. Evaluaciones finales (FR-020 a FR-022)

```bash
uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode real --write-docs
uv run python -m proyecto_modelos_lenguaje.agent profiles-eval --mode real --write-docs
uv run python -m proyecto_modelos_lenguaje.agent evaluate --tools --mode real   # batería vigente + 6 casos del planificador
uv run python -m proyecto_modelos_lenguaje.agent shield --channel        # incluye casos de FR-019
make check
```

Esperado:

- SC-002 (secuencia en ≥ 10/12, etiqueta en 12/12);
- SC-003 (perfil ≥ 90 %, subconjunto 100 %);
- SC-004 (p95 ≤ 20 s);
- SC-005 (herramientas ≥ 88,4 %, 0 búsquedas en triviales, blindaje sin fugas);
- SC-007 (`make check` verde).
