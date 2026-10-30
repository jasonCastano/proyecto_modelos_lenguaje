# Quickstart: Capa Oro (Gold)

**Feature**: `004-gold-medallion-layer`

Guía de validación end-to-end. Los detalles de entidades y campos están en [data-model.md](./data-model.md) y
los contratos en [contracts/](./contracts/).

## 1. Prerrequisitos

- Python 3.14 y `uv`.
- Capa plata construida en `data/silver/` con al menos 400 documentos canónicos y 3.000 fragmentos.
- Sin acceso a internet durante la validación.

```bash
uv sync --frozen
uv run python -c "from pathlib import Path; print(Path('data/silver/documents.jsonl').exists(), Path('data/silver/chunks.jsonl').exists())"
```

## 2. Configuración

Revisar `config/gold.toml` y `config/gold_taxonomy.toml` (se crean en la implementación). Valores iniciales:

```toml
[units]
min_sentence_chars = 40
max_unit_chars = 700
dedup_threshold = 0.90
dedup_shingle_size = 5

[topics]
min_score = 1

[coverage]
covered_min_units = 3
covered_min_official = 1

[context]
budgets = [8000, 32000]
chars_per_token = 3.5

[output]
root = "data/gold"

[run]
fail_fast = false
```

La taxonomía declara temas, palabras clave, ítems de cobertura y entidades con alias.

## 3. Humo con diez documentos

```bash
uv run pml gold build --run 2026-10-gold-00 --limit 10 --json
```

**Esperado**:

- Código 0 o 1 (1 solo si algún documento falla y se reporta).
- `input_documents = 10`.
- Al menos una unidad por documento con tema y evidencia (o razón de omisión).
- Salidas en `data/gold/_meta/smoke/2026-10-gold-00/`.
- Reporte en `data/gold/reports/2026-10-gold-00/`.

## 4. Ejecución completa

```bash
uv run python scripts/build_gold.py --run 2026-10-gold-01 --json
```

o:

```bash
uv run pml gold build --config config/gold.toml --taxonomy config/gold_taxonomy.toml --run 2026-10-gold-01 --json
```

**Esperado**:

- `input_documents = 404` y `input_chunks = 3810` (o el corte vigente).
- `processed + skipped + failed = 404`.
- ≥300 unidades y ≥12 temas.
- 24 ítems evaluados.
- Dos paquetes de contexto (8k y 32k) con citas.
- Duración ≤10 minutos.

## 5. Validar contratos

```bash
uv run pml gold verify --run 2026-10-gold-01 --sample 50 --seed 1 --json
```

**Esperado**:

- 0 fallos de esquema.
- 100% de unidades con evidencia y linaje.
- 50/50 unidades rastreadas hasta URL.
- 24/24 ítems evaluados.
- Paquetes dentro del presupuesto y sin unidades repetidas.

## 6. Revisar cobertura

Abrir `data/gold/coverage.md` y comprobar:

- Estado de cada uno de los 24 ítems.
- Unidades y autoridad que lo respaldan.
- Conflictos asociados.
- Razón y recomendación de cada vacío.
- Porcentaje de ítems cubiertos y lista priorizada de faltantes.

## 7. Revisar contexto

Abrir `data/gold/context_8k.md` y `context_32k.md`:

- Cada bloque tiene cita con URL, sección y página/tiempo.
- El paquete de 32k contiene los temas del de 8k.
- No hay unidades repetidas.
- El tamaño en tokens no excede el presupuesto.

## 8. Revisar unidades y conflictos

- `knowledge_units.jsonl`: unidad, tema, texto, evidencia, estado y flags.
- `facts.jsonl`: hechos numéricos/fechados con sujeto, atributo, valor y año.
- `entities.jsonl`: entidad canónica, alias, tipo y unidades.
- `conflicts.jsonl`: valores contradictorios, fuente preferente y estado.
- `faq_seeds.jsonl`: preguntas semilla con evidencia.

## 9. Idempotencia

```bash
uv run pml gold build --run 2026-10-gold-01 --json
```

**Esperado**:

- La segunda ejecución reutiliza el estado y no crea unidades nuevas.
- Los archivos de salida son idénticos.
- No se reprocesan documentos sin cambios.

## 10. Auditoría de linaje

Para 50 unidades aleatorias:

1. Abrir `unit_id` en `knowledge_units.jsonl`.
2. Verificar `evidence[0].chunk_id`, `doc_id`, `content_hash` y `url`.
3. Comprobar que `unit.text` aparece en el texto del fragmento citado.
4. Confirmar que la URL responde al contenido original.

## 11. Integridad de plata y bronce

Antes y después:

```bash
uv run python scripts/verify_bronze.py --campaign 2026-10-silver-01 --sample 50 --seed 1 --json
```

**Esperado**:

- Hashes de plata y bronce sin cambios.
- Ninguna escritura fuera de `data/gold/`.

## 12. Criterios de aceptación

| Criterio | Comprobación |
|----------|--------------|
| SC-001 | 404 documentos evaluados |
| SC-002 | ≥300 unidades y ≥12 temas |
| SC-003 | 100% con evidencia y linaje |
| SC-004 | 0 afirmaciones inventadas en 100 |
| SC-005 | 24/24 ítems evaluados |
| SC-006 | Paquetes dentro del presupuesto y con citas |
| SC-007 | Conflictos con ≥2 evidencias |
| SC-008 | Segunda ejecución idéntica |
| SC-009 | ≤10 minutos y sin red |
| SC-010 | <5% duplicados |
| SC-011 | 50 unidades rastreadas en <2 min |
| SC-012 | Reporte automático |
| SC-013 | Hashes de bronce/plata sin cambios |
| SC-014 | Inglés conservado |
| SC-015 | ≥80% de ítems cubiertos por unidades verificables |

## 13. Problemas frecuentes

| Síntoma | Causa probable | Acción |
|---------|----------------|--------|
| `missing_evidence` masivo | Plata sin chunks o linaje roto | Revisar `data/silver/chunks.jsonl` |
| Cobertura inflada | Umbral de tema demasiado bajo | Subir `topics.min_score` y revisar muestra |
| Conflictos falsos | Atributos distintos comparados como uno | Ajustar normalización de atributos |
| Contexto excede presupuesto | Proxy de tokens mal calibrado | Ajustar `chars_per_token` |
| Unidades duplicadas | Umbral de dedup alto | Bajar `units.dedup_threshold` |
| Segunda ejecución reprocesa todo | `config_hash` distinto o estado ausente | Revisar `_meta/state.jsonl` |
