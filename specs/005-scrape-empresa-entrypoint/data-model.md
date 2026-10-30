# Fase 1 — Modelo de datos: entrada canónica de scraping

**Feature**: `005-scrape-empresa-entrypoint`
**Fecha**: 2026-10-30

## 1. Entidades

### 1.1 ScrapeRequest

Intención del operador tal como llega por la línea de comandos.

| Campo | Tipo | Obligatorio | Validación |
|-------|------|-------------|------------|
| `config_path` | ruta | No | Por defecto `config/sources.toml`; debe existir y cargar |
| `campaign_id` | texto | Sí para ejecutar | `^[A-Za-z0-9][A-Za-z0-9._-]{0,63}$`; sin `/`, `\`, espacios ni `..` |
| `resume` | booleano | No | Por defecto `false` |
| `limit` | entero | No | Si se indica, `> 0`; se mapea a `max_targets` |
| `dry_run` | booleano | No | Por defecto `false` |
| `json_output` | booleano | No | Por defecto `false` |

**Invariante**: sin `campaign_id` no se ejecuta ninguna campaña; se muestra ayuda y se sale con `0`.

### 1.2 EffectiveParameters

Parámetros resueltos que se reportan antes de ejecutar.

| Campo | Tipo | Origen |
|-------|------|--------|
| `config` | texto | Ruta relativa al proyecto cuando sea posible |
| `campaign` | texto | `campaign_id` validado |
| `resume` | booleano | Solicitud + estado de la campaña |
| `limit` | entero o nulo | `limit` validado |
| `dry_run` | booleano | Solicitud |
| `mode` | texto | `new`, `resume`, `dry_run` o `already_completed` |

### 1.3 Campaign

Entidad existente del catálogo de bronce. No se modifica su esquema.

| Campo | Tipo | Notas |
|-------|------|-------|
| `campaign_id` | texto | Clave primaria |
| `status` | texto | `planned`, `running`, `paused`, `completed`, `aborted`, `failed` |
| `started_at` | texto ISO-8601 | UTC |
| `finished_at` | texto ISO-8601 o nulo | UTC |
| `config_hash` | texto | Hash de la configuración usada |
| `git_commit` | texto o nulo | Commit de la ejecución |
| `tool_version` | texto | Versión de la herramienta |
| `bytes_stored` | entero | Bytes acumulados |
| `artifact_count` | entero | Artefactos vinculados |
| `notes` | texto o nulo | Notas de la campaña |

### 1.4 CampaignStateAssessment

Resultado de evaluar el estado antes de ejecutar.

| Campo | Tipo | Valores |
|-------|------|---------|
| `exists` | booleano | — |
| `status` | texto o nulo | Estado actual |
| `action` | texto | `create`, `resume`, `refuse_running`, `refuse_aborted`, `noop_completed`, `error_missing_resume` |
| `reason` | texto | Explicación legible |
| `exit_code` | entero | `0`, `2` o `4` |

**Regla**: `action` y `exit_code` deben ser coherentes con la matriz de estados de `research.md` §3.

### 1.5 CampaignRun

Resultado interno de la orquestación compartida.

| Campo | Tipo | Notas |
|-------|------|-------|
| `summary` | RunSummary | Resumen del pipeline |
| `policy` | lista de PolicyOutcome | Comprobaciones de política de la campaña |
| `duration_seconds` | número | Medido alrededor de la ejecución |
| `resumed` | booleano | Si se reanudó |
| `dry_run` | booleano | Si fue en seco |

### 1.6 RunSummary

Resumen del pipeline de bronce, derivado de `CampaignSummary`.

| Campo | Tipo | Validación |
|-------|------|------------|
| `targets_discovered` | entero | `>= 0` |
| `artifacts_stored` | entero | `>= 0` |
| `deduplicated` | entero | `>= 0` |
| `excluded` | entero | `>= 0` |
| `failed` | entero | `>= 0` |
| `deferred` | entero | `>= 0` |
| `bytes_stored` | entero | `>= 0` |
| `storage_limit_bytes` | entero | `> 0` |
| `coverage` | mapa texto→entero | Conteos por estado de cobertura |
| `report_paths` | lista de texto | Rutas relativas al proyecto |

### 1.7 PolicyOutcome

Decisión registrada para una fuente o URL.

| Campo | Tipo | Notas |
|-------|------|-------|
| `source_id` | texto | Fuente evaluada |
| `decision` | texto | `allowed`, `disallowed` |
| `reason` | texto | `allowed_by_robots`, `disallowed_by_robots`, `robots_unreachable`, `unresolvable_host`, etc. |
| `checks` | entero | Número de comprobaciones agregadas |
| `checked_at` | texto ISO-8601 | Última comprobación |

**Invariante**: toda decisión tiene un `reason` no vacío.

### 1.8 ScrapeOutcome

Objeto de salida exitosa, humano o JSON.

| Campo | Tipo | Notas |
|-------|------|-------|
| `schema_version` | texto | `1.0` |
| `campaign_id` | texto | Identificador de la campaña |
| `status` | texto | Estado final del pipeline |
| `mode` | texto | `new`, `resume`, `dry_run`, `already_completed` |
| `effective` | EffectiveParameters | Parámetros resueltos |
| `summary` | RunSummary | Métricas |
| `policy` | mapa | Agregados de política |
| `duration_seconds` | número | `>= 0` |
| `exit_code` | entero | `0`, `1`, `2` o `4` |

### 1.9 EntryError

Objeto de salida de error.

| Campo | Tipo | Notas |
|-------|------|-------|
| `schema_version` | texto | `1.0` |
| `status` | texto | `error` |
| `error.code` | texto | `invalid_campaign`, `missing_config`, `invalid_limit`, `campaign_running`, `campaign_aborted`, `missing_campaign_for_resume`, `pipeline_failure` |
| `error.message` | texto | Mensaje accionable, sin secretos |
| `exit_code` | entero | `1` o `2` |

## 2. Relaciones

```text
ScrapeRequest
    │
    ├─ valida ──► EffectiveParameters
    │
    └─ consulta ──► CampaignStateAssessment ──► Campaign
                              │
                              └─ ejecuta ──► CampaignRun
                                                  ├─ RunSummary
                                                  └─ PolicyOutcome[]
                                                          │
                                                          └─ ScrapeOutcome
```

## 3. Transiciones de estado

| Estado inicial | Acción | Estado final | Efecto |
|----------------|--------|--------------|--------|
| No existe | Ejecutar | `running` → `completed` | Crea campaña, descubre, extrae y almacena |
| No existe | Ejecutar con interrupción | `running` → `paused` | Conserva progreso; se puede reanudar |
| `planned` | Ejecutar | `running` → `completed`/`paused` | Reanuda |
| `paused` | Ejecutar | `running` → `completed`/`paused` | Reanuda |
| `failed` | Ejecutar | `running` → `completed`/`paused` | Reanuda |
| `running` | Ejecutar | `running` | Rechaza por concurrencia |
| `completed` | Ejecutar | `completed` | No reejecuta; reporta |
| `aborted` | Ejecutar | `aborted` | Rechaza; exige identificador nuevo |
| Cualquiera | `--dry-run` | Sin cambio | Ejecuta en raíz temporal y descarta |

## 4. Invariantes

1. **Solo bronce**: ninguna operación escribe en `data/silver` o `data/gold`.
2. **Dry-run aislado**: al terminar un `--dry-run`, el bronce real no tiene artefactos, catálogo ni estado nuevo.
3. **Una campaña en ejecución**: el índice único del catálogo impide dos campañas `running`.
4. **Idempotencia**: reanudar no duplica artefactos; los hashes de contenido siguen siendo únicos.
5. **Trazabilidad de políticas**: cada comprobación tiene decisión, motivo y fecha.
6. **Sin secretos**: la salida no incluye credenciales, cookies ni datos de sesión.
7. **Rutas portables**: las rutas reportadas son relativas al proyecto cuando sea posible.
8. **Códigos coherentes**: `exit_code` coincide con el resultado reportado.
9. **Métricas no negativas**: todos los contadores y la duración son `>= 0`.
10. **Delegación**: el descubrimiento y la extracción provienen del pipeline existente, no de una segunda implementación.
