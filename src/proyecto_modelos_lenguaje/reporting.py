"""Campaign and coverage reports (JSON + Markdown)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .catalog import Catalog
from .coverage import build_matrix, gaps, summarize
from .models import Campaign, CoverageRow
from .utils import utcnow


def _write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def coverage_payload(catalog: Catalog, campaign_id: str) -> dict:
    rows = build_matrix(catalog, campaign_id)
    items = []
    for row in rows:
        item = {
            "item_id": row.item_id,
            "category": row.category,
            "name": row.name,
            "status": row.status,
            "evidence_count": row.evidence_count,
            "artifact_refs": list(row.artifact_refs),
        }
        if row.gap_reason:
            item["gap_reason"] = row.gap_reason
        items.append(item)
    return {
        "schema_version": "1.0",
        "campaign_id": campaign_id,
        "generated_at": utcnow(),
        "summary": {**summarize(rows), "gaps": gaps(rows)},
        "items": items,
    }


def campaign_payload(
    catalog: Catalog,
    campaign: Campaign,
    *,
    storage_limit_bytes: int,
    outcomes_by_reason: dict[str, int],
) -> dict:
    counts = catalog.target_counts(campaign.campaign_id)
    rows = build_matrix(catalog, campaign.campaign_id)
    return {
        "schema_version": "1.0",
        "campaign_id": campaign.campaign_id,
        "status": campaign.status,
        "started_at": campaign.started_at,
        "finished_at": campaign.finished_at,
        "generated_at": utcnow(),
        "config_hash": campaign.config_hash,
        "git_commit": campaign.git_commit,
        "tool_version": campaign.tool_version,
        "counts": {
            "targets_discovered": sum(counts.values()),
            "attempted": sum(
                counts.get(state, 0) for state in ("stored", "deduped", "failed", "deferred")
            ),
            "stored": counts.get("stored", 0),
            "deduped": counts.get("deduped", 0),
            "excluded": counts.get("excluded", 0),
            "failed": counts.get("failed", 0),
            "deferred": counts.get("deferred", 0),
        },
        "bytes_stored": campaign.bytes_stored,
        "storage_limit_bytes": storage_limit_bytes,
        "coverage_summary": summarize(rows),
        "outcomes_by_reason": outcomes_by_reason,
    }


def write_coverage_report(catalog: Catalog, campaign_id: str, reports_dir: Path) -> dict:
    payload = coverage_payload(catalog, campaign_id)
    _write_json(reports_dir / "coverage.json", payload)
    lines = [
        f"# Cobertura de la campaña {campaign_id}",
        "",
        f"- Cubiertos: {payload['summary']['covered']}",
        f"- Parciales: {payload['summary']['partial']}",
        f"- Faltantes: {payload['summary']['missing']}",
        f"- Total: {payload['summary']['total']}",
        "",
        "| Ítem | Categoría | Estado | Evidencias |",
        "|------|-----------|--------|------------|",
    ]
    for row in payload["items"]:
        lines.append(
            f"| {row['item_id']} | {row['category']} | {row['status']} | {row['evidence_count']} |"
        )
    gaps_found = payload["summary"]["gaps"]
    if gaps_found:
        lines.extend(["", "## Vacíos", ""])
        lines.extend(f"- **{gap['item_id']}**: {gap['reason']}" for gap in gaps_found)
    (reports_dir / "coverage.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_campaign_report(
    catalog: Catalog,
    campaign_id: str,
    reports_dir: Path,
    *,
    storage_limit_bytes: int,
) -> dict:
    campaign = catalog.get_campaign(campaign_id)
    if campaign is None:
        raise KeyError(f"campaign not found: {campaign_id}")
    payload = campaign_payload(
        catalog,
        campaign,
        storage_limit_bytes=storage_limit_bytes,
        outcomes_by_reason=catalog.outcomes_by_reason(campaign_id),
    )
    _write_json(reports_dir / "campaign.json", payload)
    lines = [
        f"# Campaña {campaign_id}",
        "",
        f"- Estado: {payload['status']}",
        f"- Inicio: {payload['started_at']}",
        f"- Fin: {payload['finished_at'] or 'en curso'}",
        f"- Bytes almacenados: {payload['bytes_stored']} de {payload['storage_limit_bytes']}",
        f"- Artefactos: {payload['counts']['stored']} almacenados, "
        f"{payload['counts']['deduped']} deduplicados",
        f"- Cobertura: {payload['coverage_summary']['covered']} cubiertos, "
        f"{payload['coverage_summary']['partial']} parciales, "
        f"{payload['coverage_summary']['missing']} faltantes",
        "",
        "## Resultados por causa",
        "",
    ]
    if payload["outcomes_by_reason"]:
        lines.extend(
            f"- `{reason}`: {count}" for reason, count in payload["outcomes_by_reason"].items()
        )
    else:
        lines.append("- Sin exclusiones ni fallos registrados.")
    (reports_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return payload


def write_all_reports(
    catalog: Catalog,
    campaign_id: str,
    reports_dir: Path,
    *,
    storage_limit_bytes: int,
) -> list[str]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    write_coverage_report(catalog, campaign_id, reports_dir)
    write_campaign_report(
        catalog, campaign_id, reports_dir, storage_limit_bytes=storage_limit_bytes
    )
    return [
        str(reports_dir / "campaign.json"),
        str(reports_dir / "summary.md"),
        str(reports_dir / "coverage.json"),
        str(reports_dir / "coverage.md"),
    ]


def coverage_rows_to_dicts(rows: tuple[CoverageRow, ...]) -> list[dict]:
    return [
        {
            "item_id": row.item_id,
            "category": row.category,
            "name": row.name,
            "status": row.status,
            "evidence_count": row.evidence_count,
            "artifact_refs": list(row.artifact_refs),
            "gap_reason": row.gap_reason,
        }
        for row in rows
    ]


def write_curation_report(
    catalog: Catalog,
    run_id: str,
    reports_dir: Path,
    *,
    settings: Any,
) -> list[str]:
    """Write the JSON and Markdown curation reports for a run."""
    run = catalog.get_curation_run(run_id)
    if run is None:
        raise KeyError(f"curation run not found: {run_id}")
    counts = catalog.curation_counts(run_id)
    by_source = catalog.curation_by_source(run_id)
    connection = catalog.connection
    reviewed = connection.execute(
        """
        SELECT decision, COUNT(*) AS n FROM review_items
        WHERE run_id = ? AND status = 'decided' GROUP BY decision
        """,
        (run_id,),
    ).fetchall()
    reviewed_counts = {row["decision"]: int(row["n"]) for row in reviewed}
    pending = catalog.pending_review_count(run_id)

    def _samples(decision: str) -> list[dict]:
        rows = connection.execute(
            """
            SELECT a.artifact_id, a.url_canonical, e.score, e.explanation
            FROM relevance_evaluations e JOIN artifacts a ON a.artifact_id = e.artifact_id
            WHERE e.run_id = ? AND e.decision = ? ORDER BY e.score DESC LIMIT 10
            """,
            (run_id, decision),
        ).fetchall()
        return [
            {
                "artifact_id": row["artifact_id"],
                "url_canonical": row["url_canonical"],
                "score": row["score"],
                "reason": row["explanation"],
            }
            for row in rows
        ]

    warnings: list[str] = []
    if pending:
        warnings.append(f"{pending} artefactos siguen pendientes de revisión.")
    if int(run["bytes_quarantined"]) == 0 and int(run["bytes_freed"]) == 0:
        warnings.append(
            "Aún no se ha ejecutado la cuarentena ni la purga; no se ha liberado espacio."
        )
    if int(run["bytes_freed"]) > int(run["bytes_before"]):
        warnings.append("Los bytes liberados superan el tamaño inicial; revisar la contabilidad.")

    payload = {
        "schema_version": "1.0",
        "run_id": run_id,
        "status": run["status"],
        "generated_at": utcnow(),
        "config_hash": run["config_hash"],
        "thresholds": {
            "keep": settings.keep_threshold,
            "review": settings.review_threshold,
        },
        "counts": {
            "evaluated": int(run["artifacts_evaluated"]) or sum(counts.values()),
            "kept": counts.get("keep", 0),
            "removed": counts.get("remove", 0),
            "review": counts.get("review", 0),
            "reviewed_kept": reviewed_counts.get("keep", 0),
            "reviewed_removed": reviewed_counts.get("remove", 0),
        },
        "by_source": by_source,
        "bytes": {
            "before": int(run["bytes_before"]),
            "quarantined": int(run["bytes_quarantined"]),
            "freed": int(run["bytes_freed"]),
        },
        "samples": {"kept": _samples("keep"), "removed": _samples("remove")},
        "warnings": warnings,
    }
    _write_json(reports_dir / "curation.json", payload)

    lines = [
        f"# Curaduría {run_id}",
        "",
        f"- Estado: {payload['status']}",
        f"- Artefactos evaluados: {payload['counts']['evaluated']}",
        f"- Conservados: {payload['counts']['kept']}",
        f"- Eliminados: {payload['counts']['removed']}",
        f"- En revisión: {payload['counts']['review']} ({pending} pendientes)",
        f"- Bytes antes: {payload['bytes']['before']}",
        f"- Bytes en cuarentena: {payload['bytes']['quarantined']}",
        f"- Bytes liberados: {payload['bytes']['freed']}",
        "",
        "## Por fuente",
        "",
        "| Fuente | Total | Conservados | Eliminados | Revisión |",
        "|--------|------:|------------:|-----------:|---------:|",
    ]
    for row in by_source:
        lines.append(
            f"| {row['source_id']} | {row['total']} | {row['kept']} | "
            f"{row['removed']} | {row['review']} |"
        )
    if warnings:
        lines.extend(["", "## Advertencias", ""])
        lines.extend(f"- {warning}" for warning in warnings)
    (reports_dir / "summary.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return [
        str(reports_dir / "curation.json"),
        str(reports_dir / "summary.md"),
    ]
