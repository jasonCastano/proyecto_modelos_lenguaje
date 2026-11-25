# Quickstart: validar la plataforma web (spec 026)

Esta guía de validación prueba de extremo a extremo que la funcionalidad cumple la spec. Los contratos están en
[`contracts/`](contracts/) y las entidades en [`data-model.md`](data-model.md).

## Prerrequisitos

```bash
make dev                                          # uv sync + npm ci + pre-commit
uv run python scripts/generate_planning_data.py --check   # datos sintéticos v1 presentes e idempotentes
```

Para la consola en la web, habilita el planificador solo durante la jornada. En PowerShell:
`$env:MANUELITA_PLANNER_WEB = "1"`.

## 1. Puerta de calidad (sin red ni claves)

```bash
make check
```

Debe salir todo en verde: Ruff, pytest, vitest y el build web. Entre las pruebas nuevas están:

- `tests/api/test_planning_api.py` y `tests/api/test_evidence_api.py`;
- `tests/integration/test_console_parity.py`;
- `tests/unit/test_planning_compare.py`;
- `tests/unit/test_scenario_prices.py`;
- en `web/src/test/`, las del enrutador, `CaneFlow`, `ScenarioForm` y `ProposalDialog`.

## 2. Paridad de cifras (SC-003)

```bash
uv run pytest tests/integration/test_console_parity.py -q
```

Resultado esperado: los 12 escenarios de `tests/fixtures/planning_scenarios.jsonl` dan las mismas cifras en el
endpoint `POST /api/v1/planning/plan`, en la herramienta `optimize_production_plan` y en
`agent planning --json`.

## 3. Regresión de la spec 025 (SC-007)

```bash
uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct
```

Resultado esperado: 10/10 escenarios con al menos el 99 % del óptimo de referencia y 2/2 sin solución detectados,
idéntico a `docs/evaluacion_planificacion_directa.md`.

## 4. Recorrido manual

```bash
make app        # http://127.0.0.1:8000
```

1. **Entrada** (`/`). Hay que ver:
   - el titular de la plataforma y la ilustración de productos;
   - los cinco perfiles como filas;
   - la declaración académica.

   «Hablar con el agente» abre `/agente`.
2. **Agente** (`/agente`):
   1. Elige «Cliente B2B» y pregunta «¿Qué certificaciones tienen?». Debe salir una respuesta citada, el chip del
      perfil y sugerencias del perfil.
   2. Cambia a «Proveedor» en el mismo hilo: el hilo debe conservarse.
3. **Planificación** (`/planificacion`):
   1. Pon caña en −15 % y pulsa «Calcular plan». En menos de 5 s debe aparecer:
      - el flujo de caña con azúcar, etanol y energía;
      - el libro de compromisos;
      - la restricción que limita el plan y la alternativa;
      - la etiqueta sintética y la frase de decisión.
   2. Pulsa «Comparar con el plan base»: deben verse las diferencias por producto y por compromiso.
   3. Pulsa «Guardar propuesta» y luego «No». No debe aparecer ninguna línea nueva en
      `<state_dir>/planning/proposals.jsonl`.
   4. Repite y responde «Sí, guardar»: debe salir el aviso «Propuesta guardada» y aparecer una línea nueva.
   5. «Explicar con el agente» debe llevar a `/agente`. La respuesta debe citar el mismo `plan_id` y las mismas
      cifras.
   6. Prueba un escenario sin solución, por ejemplo caña −50 % y vapor máximo 0. No debe dibujarse ningún flujo; deben
      aparecer los faltantes por prioridad.
4. **Sin autorización**: reinicia sin `MANUELITA_PLANNER_WEB`.
   - `/planificacion` debe mostrar el aviso de acceso.
   - `curl -s localhost:8000/api/v1/planning/state` debe responder 403 con `planner_forbidden`.
5. **Evidencia** (`/evidencia`):
   - el catálogo debe tener 26 herramientas;
   - la traza del turno anterior debe mostrar la ruta, los pasos y las duraciones;
   - el estado de servicios debe mostrar el gateway como `down` o `unknown`, con la acción a seguir, si no está
     corriendo;
   - las evaluaciones deben verse con su cifra honesta.

## 5. Responsive y accesibilidad (SC-006)

```bash
make e2e
```

Playwright recorre las cuatro rutas a 360, 768, 1440 y 1920 px. Se espera:

- sin desplazamiento horizontal;
- `axe-core` sin violaciones graves ni críticas;
- foco visible;
- con `reduced-motion`, sin transiciones.

## 6. Documentación (FR-033)

Hay que comprobar que estén actualizados:

- el README, con las capturas de las cuatro áreas en `docs/capturas/`;
- el ADR 0030;
- `CONSTITUTION.md` §3.7;
- `docs/rubrica_modulo3.md`;
- `docs/herramientas.md`, regenerado por los precios del escenario;
- Archify, con la arquitectura que suma la web v1, `finalize` y `visual-check` en verde.

## 7. Mediciones (2026-11-24, T075)

| Medida | Resultado | Meta |
|---|---|---|
| JS de la aplicación (`npm run build`), comprimido | 109 kB | ≤ 250 kB |
| Carga de la entrada en local (`loadEventEnd`, Playwright) | 56 ms | < 2 s (SC-009) |
| Paridad consola = herramienta = CLI | 12/12 escenarios | 12/12 (SC-003) |
| `planning-eval --mode direct` | 10/10 dentro de tolerancia, 0 violaciones, 2/2 sin solución | igual a la spec 025 |
| `make check` | 1.840 pruebas de Python y 180 web en verde | verde |
| `make e2e` | 33/33, con `axe-core` y las cuatro áreas en 360, 768, 1440 y 1920 px | verde |
