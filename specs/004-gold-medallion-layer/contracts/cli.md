# Contrato de CLI: `pml gold`

**Feature**: `004-gold-medallion-layer`

La capa oro se expone por la CLI existente y por un envoltorio canónico. Todos los comandos son offline y leen
la plata en modo de solo lectura.

## 1. Comandos

### 1.1 `pml gold build`

Consolida la plata en la base de conocimiento oro.

```bash
uv run pml gold build \
  --config config/gold.toml \
  --taxonomy config/gold_taxonomy.toml \
  --run 2026-10-gold-01 \
  [--limit N] \
  [--topic TOPIC_ID] \
  [--force] \
  [--json]
```

| Argumento | Obligatorio | Descripción |
|-----------|-------------|-------------|
| `--config` | no | Configuración; por defecto `config/gold.toml` |
| `--taxonomy` | no | Taxonomía; por defecto `config/gold_taxonomy.toml` |
| `--run` | sí | `YYYY-MM-gold-NN` |
| `--limit` | no | Procesa como máximo N documentos (smoke aislado) |
| `--topic` | no | Filtra por tema para pruebas |
| `--force` | no | Ignora caché y reutiliza todo |
| `--json` | no | Sobre JSON |

**Salidas**: `knowledge_units.jsonl`, `facts.jsonl`, `entities.jsonl`, `conflicts.jsonl`, `faq_seeds.jsonl`,
`coverage.json`, `context_8k.md`, `context_32k.md`, `topics/*.md`, `glossary.md`, `manifest.json` y
`reports/<run_id>/quality.{json,md}` bajo `data/gold/`.

### 1.2 `pml gold verify`

Audita integridad, contratos y linaje.

```bash
uv run pml gold verify --run 2026-10-gold-01 [--sample 50] [--seed 1] [--json]
```

Verifica:
1. Esquemas de unidades, hechos, entidades, conflictos, cobertura, contexto y reporte.
2. Que toda unidad tenga evidencia y linaje.
3. Que el texto de la unidad aparezca en el fragmento citado.
4. Que los 24 ítems estén evaluados.
5. Que los paquetes respeten el presupuesto y no repitan unidades.
6. Una muestra de 50 unidades rastreada hasta la URL pública.

### 1.3 `pml gold report`

```bash
uv run pml gold report --run 2026-10-gold-01 [--format json|md]
```

### 1.4 `pml gold status`

```bash
uv run pml gold status [--run 2026-10-gold-01] [--json]
```

## 2. Envoltorio canónico

```bash
uv run python scripts/build_gold.py --run 2026-10-gold-01 --json
```

## 3. Códigos de salida

| Código | Significado |
|--------|-------------|
| 0 | Completado sin fallos |
| 1 | Completado con fallos parciales |
| 2 | Error de configuración o argumentos |
| 3 | Fallo global |

## 4. Restricciones

- Sin red; sin LLM, embeddings ni traducción.
- Solo lectura de `data/silver/` y `data/bronze/`.
- Las ejecuciones con `--limit` o `--topic` se aíslan en `data/gold/_meta/smoke/<run_id>/` para no sobrescribir
  la base completa.
- No se reutiliza un `run_id` existente sin `--force`.
