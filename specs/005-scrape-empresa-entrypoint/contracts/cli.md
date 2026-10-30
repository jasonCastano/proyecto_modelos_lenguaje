# Contrato de la interfaz — `scripts/scrape_empresa.py`

**Feature**: `005-scrape-empresa-entrypoint`
**Versión**: 1.0
**Fecha**: 2026-10-30

## 1. Sinopsis

```text
uv run python scripts/scrape_empresa.py [--config RUTA] --campaign ID
    [--resume] [--limit N] [--dry-run] [--json] [--help]
```

La entrada canónica delega en el pipeline de bronce existente. No implementa un crawler propio.

## 2. Opciones

| Opción | Tipo | Por defecto | Descripción |
|--------|------|-------------|-------------|
| `--config RUTA` | ruta | `config/sources.toml` | Configuración de fuentes. Las rutas relativas se resuelven contra la raíz del proyecto. |
| `--campaign ID` | texto | — | Identificador de campaña. Obligatorio para ejecutar. |
| `--resume` | bandera | `false` | Reanuda una campaña existente y reanudable. |
| `--limit N` | entero | sin límite | Máximo de objetivos a procesar. Debe ser `> 0`. |
| `--dry-run` | bandera | `false` | Descubre y reporta sin escribir en el bronce real. |
| `--json` | bandera | `false` | Emite un único objeto JSON validable. |
| `--help` | bandera | — | Muestra ayuda y ejemplos; sale con `0`. |

## 3. Matriz de estados

| Estado existente | Sin `--resume` | Con `--resume` | Código |
|------------------|----------------|----------------|-------:|
| No existe | Crea y ejecuta | Error: la campaña no existe | `2` |
| `planned` | Reanuda automáticamente | Reanuda | `0`/`4` |
| `paused` | Reanuda automáticamente | Reanuda | `0`/`4` |
| `failed` | Reanuda automáticamente | Reanuda | `0`/`4` |
| `running` | Rechaza por concurrencia | Rechaza por concurrencia | `2` |
| `completed` | Reporta completada, sin red | Reporta completada, sin red | `0` |
| `aborted` | Error: usar un ID nuevo | Error: usar un ID nuevo | `2` |

El modo efectivo (`new`, `resume`, `dry_run`, `already_completed`) se reporta antes de ejecutar y en la
salida.

## 4. Salida humana

```text
Campaña: 2026-10-m1-02-smoke
Configuración: config/sources.toml
Modo: dry-run
Límite: 3
Estado: completed
Descubiertos: 12
Almacenados: 0
Omitidos: 2 (excluidos 1, duplicados 1, diferidos 0)
Fallidos: 0
Bytes: 0
Duración: 1.8 s
Políticas: permitidas=1, bloqueadas=1, inalcanzables=0
Reportes: —
```

Reglas:

- Las rutas se muestran relativas al proyecto cuando sea posible.
- No se imprimen secretos, credenciales, cookies ni datos de sesión.
- En modo `--json` no se imprime esta tabla; se emite el objeto JSON.

## 5. Salida JSON

### 5.1 Éxito

```json
{
  "schema_version": "1.0",
  "campaign_id": "2026-10-m1-02-smoke",
  "status": "completed",
  "mode": "new",
  "effective": {
    "config": "config/sources.toml",
    "campaign": "2026-10-m1-02-smoke",
    "resume": false,
    "limit": 3,
    "dry_run": false
  },
  "summary": {
    "targets_discovered": 12,
    "artifacts_stored": 3,
    "deduplicated": 1,
    "excluded": 2,
    "failed": 0,
    "deferred": 0,
    "bytes_stored": 12345,
    "storage_limit_bytes": 10000000,
    "coverage": {"covered": 0, "partial": 0, "missing": 24},
    "report_paths": ["data/bronze/reports/2026-10-m1-02-smoke/coverage.md"]
  },
  "policy": {
    "allowed": 1,
    "disallowed": 1,
    "unreachable": 0,
    "by_reason": {"allowed_by_robots": 1, "disallowed_by_robots": 1}
  },
  "duration_seconds": 2.4,
  "exit_code": 0
}
```

Esquema: [scrape-summary.schema.json](./scrape-summary.schema.json).

### 5.2 Error

```json
{
  "schema_version": "1.0",
  "status": "error",
  "error": {
    "code": "invalid_campaign",
    "message": "El identificador de campaña no es válido: '../x'. Usa letras, números, punto, guion o guion bajo."
  },
  "exit_code": 2
}
```

Esquema: [error.schema.json](./error.schema.json).

Códigos de error:

| Código | Causa |
|--------|-------|
| `missing_config` | La configuración no existe o no se puede leer |
| `invalid_config` | La configuración es inválida |
| `invalid_campaign` | El identificador no cumple el formato |
| `invalid_limit` | El límite no es un entero positivo |
| `missing_campaign_for_resume` | Se pidió reanudar una campaña inexistente |
| `campaign_running` | Ya hay una campaña en ejecución |
| `campaign_aborted` | La campaña fue abortada; se requiere un ID nuevo |
| `pipeline_failure` | Fallo inesperado durante la ejecución |

## 6. Códigos de salida

| Código | Significado |
|-------:|-------------|
| `0` | Éxito, incluida una campaña ya completada que no se reejecuta |
| `1` | Fallo inesperado del pipeline |
| `2` | Error de uso, configuración, validación o concurrencia |
| `4` | Campaña pausada por límite de almacenamiento o interrupción |

## 7. Garantías

1. **Delegación**: el descubrimiento, la extracción, el almacenamiento y las políticas provienen del
   pipeline de bronce existente.
2. **Solo bronce**: no se escriben `data/silver` ni `data/gold`.
3. **Dry-run**: no deja artefactos, registros de catálogo ni estado en el bronce real.
4. **Idempotencia**: reanudar no duplica artefactos.
5. **Políticas**: `robots.txt`, términos de uso, rate limits y user agent se respetan; las decisiones se
   registran.
6. **Sin secretos**: no se usan cookies ni credenciales, y la salida no las contiene.
7. **Reproducibilidad**: la configuración, la campaña y los parámetros efectivos quedan en la salida.

## 8. Ejemplos

```bash
# Ayuda
uv run python scripts/scrape_empresa.py --help

# Sin argumentos: ayuda, sin red
uv run python scripts/scrape_empresa.py

# Prueba en seco
uv run python scripts/scrape_empresa.py \
  --campaign 2026-10-m1-02-smoke \
  --limit 3 \
  --dry-run \
  --json

# Campaña limitada
uv run python scripts/scrape_empresa.py \
  --campaign 2026-10-m1-02-smoke \
  --limit 3 \
  --json

# Reanudar
uv run python scripts/scrape_empresa.py \
  --campaign 2026-10-m1-02-smoke \
  --resume
```

## 9. Fuera de contrato

- No crea fuentes nuevas ni modifica el catálogo de fuentes.
- No cambia el esquema del bronce.
- No ejecuta plata, oro, LLM, embeddings ni la app.
- No programa ejecuciones ni ofrece interfaz web.
