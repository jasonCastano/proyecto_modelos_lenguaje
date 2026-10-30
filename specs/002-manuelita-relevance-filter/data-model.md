# Data Model: Filtro de Relevancia del Corpus de Manuelita

**Feature**: `002-manuelita-relevance-filter` | **Date**: 2026-10-28

La curaduría se guarda como metadata adicional en el catálogo SQLite existente. **No se modifican** las tablas
de adquisición (`artifacts`, `campaign_artifacts`, `coverage_evidence`); se añaden tablas de evaluación,
revisión, cuarentena y auditoría, más una vista que define el corpus activo.

## Entity Relationship Overview

```text
curation_runs 1──N relevance_evaluations N──1 artifacts
artifacts     1──N relevance_evidence
artifacts     1──1 review_items
artifacts     1──1 curation_audit
artifacts     1──1 quarantine_entries
v_active_artifacts = artifacts − remove/review − cuarentena activa
```

## Table: `curation_runs`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `run_id` | TEXT | PRIMARY KEY, `^[a-z0-9][a-z0-9-]{2,63}$` | Ej. `2026-10-curation-01` |
| `status` | TEXT | NOT NULL, CHECK in `planned,analyzing,analyzed,approved,quarantining,quarantined,purging,purged,aborted` | Exactly one active run per scope |
| `started_at` | TEXT | NOT NULL | UTC ISO 8601 |
| `finished_at` | TEXT | NULL | UTC |
| `config_hash` | TEXT | NOT NULL | Hash de `relevance.toml` |
| `git_commit` | TEXT | NULL | Commit del código |
| `tool_version` | TEXT | NOT NULL | Versión del paquete |
| `scope_campaign` | TEXT | NULL | NULL = todo el corpus |
| `artifacts_evaluated` | INTEGER | NOT NULL DEFAULT 0, CHECK ≥0 | |
| `kept` | INTEGER | NOT NULL DEFAULT 0, CHECK ≥0 | |
| `removed` | INTEGER | NOT NULL DEFAULT 0, CHECK ≥0 | |
| `review` | INTEGER | NOT NULL DEFAULT 0, CHECK ≥0 | |
| `bytes_before` | INTEGER | NOT NULL DEFAULT 0, CHECK ≥0 | Tamaño del corpus al iniciar |
| `bytes_quarantined` | INTEGER | NOT NULL DEFAULT 0, CHECK ≥0 | |
| `bytes_freed` | INTEGER | NOT NULL DEFAULT 0, CHECK ≥0 | Solo tras purga |
| `approved_by` | TEXT | NULL | Requerido para cuarentena/purga |
| `approved_at` | TEXT | NULL | UTC |
| `report_path` | TEXT | NULL | Reporte generado |
| `notes` | TEXT | NULL | |

**State transitions**: `planned → analyzing → analyzed → approved → quarantining → quarantined →
purging → purged`; `analyzed → aborted`; `quarantined → restored` se refleja en las entradas de cuarentena y
el run conserva su estado con `notes`.

## Table: `relevance_evaluations`

Una fila vigente por artefacto. El historial de acciones queda en `curation_audit`.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `artifact_id` | INTEGER | PRIMARY KEY, FK → `artifacts` | Un artefacto, una evaluación vigente |
| `run_id` | TEXT | NOT NULL, FK → `curation_runs` | Última ejecución que evaluó |
| `decision` | TEXT | NOT NULL, CHECK in `keep,remove,review` | FR-009 |
| `level` | TEXT | NOT NULL, CHECK in `direct,contextual,none` | FR-006 |
| `score` | INTEGER | NOT NULL, CHECK BETWEEN 0 AND 100 | |
| `method` | TEXT | NOT NULL, CHECK in `rule_based,manual` | |
| `explanation` | TEXT | NOT NULL, max 1000 | Resumen legible |
| `content_hash` | TEXT | NOT NULL, `^[a-f0-9]{64}$` | Snapshot para invalidar si cambia el contenido |
| `config_hash` | TEXT | NOT NULL | Reglas usadas |
| `manual_override` | INTEGER | NOT NULL DEFAULT 0, CHECK IN (0,1) | Protege la decisión humana |
| `reviewer` | TEXT | NULL | Requerido si `manual_override = 1` |
| `reviewed_at` | TEXT | NULL | UTC |
| `evaluated_at` | TEXT | NOT NULL | UTC |

**Invariants**:
- `source_id` del artefacto es `official_site`/dominio `manuelita.com` ⇒ `decision = keep` y `score = 100`.
- `manual_override = 1` ⇒ una re-ejecución automática no modifica la fila.
- `decision = review` ⇒ existe una fila pendiente en `review_items`.

## Table: `relevance_evidence`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `evidence_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `artifact_id` | INTEGER | NOT NULL, FK → `artifacts` | |
| `term` | TEXT | NOT NULL, max 200 | Término o alias detectado |
| `location` | TEXT | NOT NULL, CHECK in `title,body,url,metadata` | FR-008 |
| `snippet` | TEXT | NOT NULL, max 500 | Ventana de contexto |
| `weight` | INTEGER | NOT NULL, CHECK BETWEEN -100 AND 100 | Contribución a la puntuación |
| `created_at` | TEXT | NOT NULL | UTC |

**Uniqueness**: `(artifact_id, term, location)`.

## Table: `review_items`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `artifact_id` | INTEGER | PRIMARY KEY, FK → `artifacts` | |
| `run_id` | TEXT | NOT NULL, FK → `curation_runs` | |
| `reason` | TEXT | NOT NULL, max 500 | Motivo de ambigüedad |
| `snippet` | TEXT | NOT NULL, max 500 | Contexto para el revisor |
| `score` | INTEGER | NOT NULL, CHECK BETWEEN 0 AND 100 | |
| `status` | TEXT | NOT NULL, CHECK in `pending,decided` | |
| `decision` | TEXT | NULL, CHECK in `keep,remove` | |
| `reviewer` | TEXT | NULL | |
| `decided_at` | TEXT | NULL | UTC |
| `note` | TEXT | NULL | |

**Invariant**: `status = decided` ⇒ `decision`, `reviewer` y `decided_at` no nulos.

## Table: `curation_audit`

Registro permanente de artefactos retirados. Sobrevive a la purga.

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `audit_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `run_id` | TEXT | NOT NULL, FK → `curation_runs` | |
| `artifact_id` | INTEGER | UNIQUE NOT NULL, FK → `artifacts` | Una entrada por artefacto retirado |
| `url_canonical` | TEXT | NOT NULL | |
| `content_hash` | TEXT | NOT NULL, `^[a-f0-9]{64}$` | |
| `byte_size` | INTEGER | NOT NULL, CHECK > 0 | |
| `media_type` | TEXT | NOT NULL | |
| `source_id` | TEXT | NOT NULL, FK → `sources` | |
| `decision` | TEXT | NOT NULL, CHECK = `remove` | |
| `reason` | TEXT | NOT NULL, max 1000 | |
| `score` | INTEGER | NOT NULL, CHECK BETWEEN 0 AND 100 | |
| `evidence_json` | TEXT | NOT NULL | Evidencia serializada |
| `decided_at` | TEXT | NOT NULL | UTC |
| `quarantined_at` | TEXT | NULL | UTC |
| `purged_at` | TEXT | NULL | UTC |

**Invariant**: no se mueve un artefacto a cuarentena sin su fila de auditoría.

## Table: `quarantine_entries`

| Column | Type | Constraints | Notes |
|--------|------|-------------|-------|
| `quarantine_id` | INTEGER | PRIMARY KEY AUTOINCREMENT | |
| `artifact_id` | INTEGER | UNIQUE NOT NULL, FK → `artifacts` | |
| `run_id` | TEXT | NOT NULL, FK → `curation_runs` | |
| `original_path` | TEXT | NOT NULL | Relativa a `data/bronze/` |
| `quarantine_path` | TEXT | NOT NULL | Relativa a `data/quarantine/` |
| `byte_size` | INTEGER | NOT NULL, CHECK > 0 | |
| `moved_at` | TEXT | NOT NULL | UTC |
| `expires_at` | TEXT | NOT NULL | `moved_at + retention_days` |
| `status` | TEXT | NOT NULL, CHECK in `quarantined,restored,purged` | |
| `restored_at` | TEXT | NULL | UTC |
| `purged_at` | TEXT | NULL | UTC |

**Invariants**:
- `status = restored` ⇒ archivo devuelto a `original_path` y hash verificado.
- `status = purged` ⇒ archivo eliminado, `purged_at` no nulo y auditoría intacta.
- `quarantine_path` debe resolver dentro de `data/quarantine/`.

## View: `v_active_artifacts`

```sql
CREATE VIEW v_active_artifacts AS
SELECT a.*
FROM artifacts a
LEFT JOIN relevance_evaluations e ON e.artifact_id = a.artifact_id
LEFT JOIN curation_runs r ON r.run_id = e.run_id
LEFT JOIN quarantine_entries q
       ON q.artifact_id = a.artifact_id AND q.status = 'quarantined'
WHERE a.retracted_at IS NULL
  AND q.quarantine_id IS NULL
  AND (
        e.artifact_id IS NULL
        OR e.decision = 'keep'
        OR r.status NOT IN ('approved','quarantining','quarantined','purging','purged')
      );
```

- Artefactos sin evaluación (legado) siguen activos.
- Tras la aprobación, `remove` y `review` quedan fuera del corpus activo.
- Antes de la aprobación, las evaluaciones son propuestas y no alteran manifiestos ni cobertura.
- Cualquier artefacto en cuarentena activa queda fuera aunque su evaluación fuera `keep` (no debería ocurrir).
- Manifiestos, exportaciones, reportes y cobertura usan esta vista cuando se solicita modo curado.

## Validation Rules (from requirements)

1. **Cobertura total (FR-001)**: al finalizar `analyze --apply`, el número de evaluaciones es igual al número de
   artefactos del alcance.
2. **Dominio oficial (FR-004/FR-014)**: una evaluación de artefacto con fuente oficial solo puede ser `keep`;
   cualquier intento de `remove`/cuarentena se rechaza con código de guarda.
3. **Evidencia (FR-008)**: `keep` y `review` requieren al menos una fila en `relevance_evidence`; `review`
   además requiere `review_items.reason`.
4. **Umbrales (FR-006)**: `score ≥ 60 → keep`, `25 ≤ score < 60 → review`, `score < 25 → remove`, salvo las
   excepciones de dominio oficial y revisión manual.
5. **Auditoría previa (FR-011)**: no existe cuarentena sin `curation_audit`.
6. **Purga (FR-012/FR-013)**: solo `quarantined`, con run `approved`/`quarantined`, retención vencida o
   `--now`, y `--confirm`.
7. **Restauración (FR-013)**: solo `quarantined`, hash recalculado igual a `content_hash`; si no coincide, se
   rechaza.
8. **Idempotencia (FR-016)**: repetir `analyze` no crea evaluaciones duplicadas; repetir `quarantine`/`purge`
   no altera filas ya terminales ni vuelve a sumar bytes.
9. **Decisiones manuales (FR-017)**: `manual_override = 1` no se sobrescribe; se registra revisor y fecha.
10. **Corpus activo (FR-010)**: toda consulta curada usa `v_active_artifacts`; una vez aprobado el run, ningún
    `remove`/`review` aparece en manifiestos, exportaciones, reportes o cobertura. Antes de la aprobación, las
    evaluaciones no alteran el corpus.
11. **Integridad (FR-020)**: los bytes de artefactos `keep` no se escriben ni se mueven; se verifica el hash
    antes de mover y al restaurar.
12. **Espacio (FR-012/SC-005)**: `bytes_freed` se calcula como suma de tamaños de entradas `purged`; nunca
    supera el tamaño del corpus y no se cuenta dos veces.
13. **Configuración (FR-019)**: `config_hash` idéntico ⇒ mismas decisiones para el mismo contenido; un cambio de
    configuración se refleja en un nuevo run.
