# Quickstart: validar perfiles abiertos en la web

## Prerrequisitos

- Clon con `uv` y Node 24.
- **Sin** `MANUELITA_PLANNER_WEB`, `MANUELITA_PLANNER_OPEN` ni `VALERIA_PLANNERS` en `.env` ni en el entorno. Si
  existen, comentarlos para esta validación.

## 1. Backend sin autorización (SC-001, SC-002)

```bash
uv run pytest tests/unit/agent/test_profiles.py tests/api/test_profiles_api.py \
  tests/api/test_planning_api.py tests/api/test_planning_proposals.py -q
```

Resultado esperado:

- `/api/profiles` devuelve los 5 perfiles con `authorized: true`.
- Las rutas de `/api/v1/planning` responden 200 sin `X-User-Id`.
- Ninguna respuesta es 403.

## 2. Paridad y evaluación directa (SC-005)

```bash
uv run pytest tests/integration/test_console_parity.py -q
uv run python -m proyecto_modelos_lenguaje.agent planning-eval --mode direct
```

Resultado esperado:

- Paridad 12/12.
- Evaluación: 10/10 dentro de tolerancia, 0 violaciones y 2/2 sin solución detectados. Debe ser idéntico al
  resultado de la spec 026, ahora sin fijar ninguna variable.

## 3. WhatsApp sin cambios (SC-006)

```bash
uv run pytest tests/unit/channels/test_bridge_profile.py -q
uv run pml channels simulate --sender +570000000001 --profile planificador --text "Tenemos 15 % menos caña"
```

Resultado esperado: el simulador sin `VALERIA_PLANNERS` responde que el planificador es solo para autorizados.

## 4. Web (SC-003, SC-004)

```bash
make app        # o: uv run python -m proyecto_modelos_lenguaje.webbuild --serve
```

1. Abrir `http://127.0.0.1:8000/`. La fila «Planificador industrial» muestra su consulta de ejemplo, sin candado.
2. Ir a `/agente`. Los cinco perfiles son elegibles y cada uno muestra para quién es. Elegir «Planificador
   industrial»: aparece «Te atiende como Planificador industrial», el aviso de datos sintéticos y «Abrir la
   planificación».
3. Preguntar «Tenemos 15 % menos caña esta semana. ¿Cómo cumplimos azúcar, etanol y energía?». El agente responde
   con el plan, la restricción y la advertencia.
4. Abrir `/planificacion` en otra pestaña. Se ve la consola con estado, escenario y flujo de caña. Guardar una
   propuesta pide la confirmación en dos pasos.
5. Repetir los pasos 1 y 2 con el navegador a 360 px de ancho: sin desplazamiento horizontal.

Pruebas automáticas:

```bash
cd web && npx vitest run && cd ..
make e2e
```

Resultado esperado: todo en verde, con la variable de autorización ya retirada de `tests/e2e/conftest.py`.

## 5. Documentación (SC-007)

```bash
git grep -n "MANUELITA_PLANNER_WEB\|Solo equipo de planta autorizado\|solo autorizados" -- \
  README.md .env.example web/src src docs/rubrica_modulo3.md CONSTITUTION.md
```

Resultado esperado: solo aparecen menciones históricas (historial de la constitución o specs anteriores) y textos
de WhatsApp.

## 7. Mediciones

### Línea base (antes del cambio, 2026-11-25, sin variables de autorización)

| Medición | Resultado |
|---|---|
| `GET /api/v1/planning/state` sin `X-User-Id` | 403 `planner_forbidden` |
| `GET /api/profiles` | planificador `authorized: false`; los otros cuatro `true` |
| `planning-eval --mode direct` | 10/10 dentro de tolerancia, razón mínima 1,000016, 0 violaciones, 2/2 sin solución |

### Después del cambio (2026-11-25, sin variables de autorización)

| Medición | Resultado | Criterio |
|---|---|---|
| `GET /api/v1/planning/state` sin `X-User-Id` | 200 | SC-002 ✅ |
| `GET /api/profiles` | los 5 perfiles `authorized: true`, `requires_authorization: false` | SC-001 ✅ |
| `planning-eval --mode direct` | 10/10, razón mínima 1,000016, 0 violaciones, 2/2 sin solución (igual a la línea base) | SC-005 ✅ |
| Paridad consola = herramienta = CLI (`test_console_parity.py`, sin envs) | 12/12 | SC-005 ✅ |
| WhatsApp sin lista (`test_bridge_profile.py`) | planificador denegado; `MANUELITA_PLANNER_WEB=1` no lo abre | SC-006 ✅ |
| `make check` | 1.861 pruebas de Python y 184 web; Ruff y build en verde | ✅ |
| `make e2e` (incluye el recorrido nuevo y la ausencia de «solo autorizados» de 360 a 1920 px) | 34/34 | SC-004 ✅ |
| JS de producción | 109,05 kB gzip (antes 109,27 kB) | ≤ 120 kB ✅ |
