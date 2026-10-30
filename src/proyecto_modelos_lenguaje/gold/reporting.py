"""Quality reporting for the gold layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import GoldReport
from .store import write_json, write_text


def render_quality_markdown(report: GoldReport) -> str:
    lines = [
        f"# Reporte de calidad — {report.run_id}",
        "",
        f"- Estado: **{report.status}**",
        f"- Documentos de plata: {report.input_documents}",
        f"- Fragmentos: {report.input_chunks}",
        f"- Procesados: {report.processed}",
        f"- Omitidos: {report.skipped}",
        f"- Fallidos: {report.failed}",
        f"- Unidades: {report.units}",
        f"- Hechos: {report.facts}",
        f"- Entidades: {report.entities}",
        f"- Conflictos: {report.conflicts}",
        f"- Cobertura: {report.coverage.get('covered', 0)} cubiertos, "
        f"{report.coverage.get('partial', 0)} parciales, "
        f"{report.coverage.get('missing', 0)} faltantes",
        f"- Paquetes de contexto: {report.context_packs}",
        f"- Tokens: {report.tokens}",
        f"- Duración: {report.duration_seconds:.2f} s",
        "",
        "## Flags de calidad",
        "",
        "| Flag | Unidades |",
        "|------|---------:|",
    ]
    if report.quality_flags:
        for key, value in sorted(report.quality_flags.items()):
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("| — | 0 |")
    lines.extend(["", "## Omisiones", "", "| Motivo | Documentos |", "|--------|-----------:|"])
    if report.skip_reasons:
        for key, value in sorted(report.skip_reasons.items()):
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("| — | 0 |")
    return "\n".join(lines) + "\n"


def write_report(report: GoldReport, reports_dir: Path) -> list[str]:
    destination = reports_dir / report.run_id
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "quality.json"
    md_path = destination / "quality.md"
    write_json(json_path, report.to_dict())
    write_text(md_path, render_quality_markdown(report))
    return [json_path.as_posix(), md_path.as_posix()]


def report_payload(report: GoldReport) -> dict[str, Any]:
    return report.to_dict()
