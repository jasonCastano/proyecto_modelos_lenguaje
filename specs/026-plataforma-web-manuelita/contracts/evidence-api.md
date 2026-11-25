# Contrato: API v1 de evidencia (`/api/v1/evidence`)

**Router**: `src/proyecto_modelos_lenguaje/api_evidence.py` · **Spec**: FR-020 a FR-024

Todos los endpoints son de solo lectura y no requieren autorización: no exponen datos de planta, claves ni datos
personales. Usan el mismo sobre de error que [`planning-api.md`](planning-api.md).

## `GET /api/v1/evidence/tools`

Responde 200:

```json
{
  "count": 26,
  "tools": [
    {
      "name": "optimize_production_plan",
      "description": "…",
      "kind": "read",
      "requires_approval": false,
      "routes": ["planning"],
      "profiles": ["planificador"],
      "mcp_allowed": false
    }
  ]
}
```

`count` coincide con `len(catalog.SPECS)`, y una prueba lo fija en 26.

## `GET /api/v1/evidence/traces/{thread_id}?turn=<n>`

Responde 200 con un `TurnTrace` (data-model §7). Por defecto es el último turno. Los argumentos de las herramientas
pasan por `redact_pii`, y los números de teléfono nunca aparecen.

| Código | HTTP | Cuándo |
|---|---|---|
| `thread_not_found` | 404 | El hilo no existe |
| `turn_not_found` | 404 | El turno pedido no existe |

## `GET /api/v1/evidence/services`

Responde 200:

```json
{
  "checked_at": "…",
  "services": [
    { "id": "model", "label": "Modelo DeepSeek", "status": "up", "reason": "Clave configurada; modelo deepseek-chat.", "action": "" },
    { "id": "gateway", "label": "Gateway OpenClaw", "status": "down", "reason": "Sin turnos del puente en 10 minutos.", "action": "Ejecuta openclaw gateway status en el PC servidor." }
  ]
}
```

- Cada comprobación tiene un tope de 2 s. Si no responde a tiempo, el estado es `unknown` y el `reason` lo dice.
- Nunca devuelve claves, tokens ni números de teléfono; el canal reporta conteos y seudónimos.

## `GET /api/v1/evidence/evaluations`

Responde 200 con la lista de `PublishedEvaluation` de `config/evaluations.toml`, en el orden del archivo.

Una prueba verifica tres cosas:

- que cada `report` exista en `docs/`;
- que `meets` sea coherente con `value` y `target` cuando ambos son numéricos;
- que estén al menos estas evaluaciones:
  - herramientas;
  - trivialidades;
  - planificación;
  - planificación directa;
  - perfiles;
  - RAG del Módulo 3;
  - blindaje.
