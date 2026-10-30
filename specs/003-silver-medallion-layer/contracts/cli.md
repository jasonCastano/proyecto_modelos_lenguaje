# Contrato de CLI: `pml silver`

**Feature**: `003-silver-medallion-layer`

La etapa plata se expone por la CLI existente y por un envoltorio canónico en `scripts/`. Todos los comandos
son offline y leen el bronce en modo de solo lectura.

## 1. Comandos

### 1.1 `pml silver build`

Construye o actualiza la capa plata.

```bash
uv run pml silver build \
  --config config/silver.toml \
  --run 2026-10-silver-01 \
  [--limit N] \
  [--source official_site] \
  [--force] \
  [--json]
```

| Argumento | Obligatorio | Descripción |
|-----------|-------------|-------------|
| `--config` | no | Ruta de configuración; por defecto `config/silver.toml` |
| `--run` | sí | Identificador único con formato `YYYY-MM-silver-NN` |
| `--limit` | no | Procesa como máximo N artefactos (útil para pruebas) |
| `--source` | no | Filtra por `source_id` del bronce |
| `--force` | no | Ignora el estado incremental y reprocesa todo |
| `--json` | no | Emite un sobre JSON en lugar de texto |

**Efecto**: escribe `documents.jsonl`, `chunks.jsonl`, Markdown, estado y reportes bajo `data/silver/`.
**Idempotencia**: con el mismo `config_hash` y los mismos hashes de entrada, no crea documentos ni fragmentos
nuevos.

### 1.2 `pml silver verify`

Audita integridad, contratos y trazabilidad de una ejecución.

```bash
uv run pml silver verify --run 2026-10-silver-01 [--sample 50] [--seed 1] [--json]
```

Verifica:
1. Que cada registro cumpla su JSON Schema.
2. Que `processed + skipped + failed = input_artifacts`.
3. Que cada `chunk_id` apunte a un `doc_id` existente y a un artefacto bronce con el mismo `content_hash`.
4. Que `document.text[char_start:char_end]` contenga el texto del fragmento.
5. Que no haya secciones nulas, IDs duplicados ni chunks que crucen secciones.
6. Una muestra aleatoria de fragmentos rastreada hasta la URL pública correspondiente.

**Salida**: conteos y lista de fallos; código de salida 0 si todo pasa.

### 1.3 `pml silver report`

Regenera o muestra el reporte de calidad.

```bash
uv run pml silver report --run 2026-10-silver-01 [--format json|md]
```

**Salida**: `data/silver/reports/<run_id>/quality.json` y `quality.md`.

### 1.4 `pml silver status`

Muestra el estado de la última ejecución y el tamaño de las salidas.

```bash
uv run pml silver status [--run 2026-10-silver-01] [--json]
```

## 2. Envoltorio canónico

```bash
uv run python scripts/build_silver.py --run 2026-10-silver-01 --json
```

El script delega en `pml silver build` con la configuración por defecto y existe para cumplir la ruta canónica
del proyecto, igual que `scripts/scrape_empresa.py` para el bronce.

## 3. Sobre JSON

Todos los comandos con `--json` imprimen un objeto:

```json
{
  "command": "silver build",
  "run_id": "2026-10-silver-01",
  "status": "completed",
  "input_artifacts": 524,
  "processed": 510,
  "skipped": 12,
  "failed": 2,
  "documents": 497,
  "canonical_documents": 480,
  "alias_documents": 17,
  "chunks": 10234,
  "report_paths": [
    "data/silver/reports/2026-10-silver-01/quality.json",
    "data/silver/reports/2026-10-silver-01/quality.md"
  ]
}
```

## 4. Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Ejecución completada sin fallos |
| 1 | Ejecución completada con fallos parciales (`completed_with_failures`) |
| 2 | Error de configuración o de argumentos |
| 3 | Fallo global de la ejecución |

## 5. Restricciones

- No se permite acceso a red; cualquier intento se considera error de configuración.
- No se escribe en `data/bronze/` ni se modifican sus hashes.
- Si el espacio disponible es insuficiente, la ejecución se detiene antes de escribir y reporta el motivo.
- Los nombres de ejecución no se reutilizan: repetir un `run_id` existente exige `--force` o un nombre nuevo.
