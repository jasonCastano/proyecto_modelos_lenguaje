"""Markdown and quality-report output for the silver layer."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from .models import RunReport, SilverDocument
from .state import atomic_write_json, atomic_write_text


def write_markdown(document: SilverDocument, markdown_dir: Path) -> str:
    markdown_dir.mkdir(parents=True, exist_ok=True)
    destination = markdown_dir / f"{document.doc_id}.md"
    frontmatter = {
        "doc_id": document.doc_id,
        "title": document.title,
        "url": document.url,
        "source_id": document.source_id,
        "published_at": document.published_at,
        "retrieved_at": document.retrieved_at,
        "language": document.language,
        "license": document.license_note,
    }
    header = yaml.safe_dump(frontmatter, sort_keys=False, allow_unicode=True).strip()
    body = f"# {document.title}\n\n{document.text}\n"
    atomic_write_text(destination, f"---\n{header}\n---\n\n{body}")
    return destination.as_posix()


def render_quality_markdown(report: RunReport) -> str:
    lines = [
        f"# Reporte de calidad — {report.run_id}",
        "",
        f"- Estado: **{report.status}**",
        f"- Artefactos de entrada: {report.input_artifacts}",
        f"- Procesados: {report.processed}",
        f"- Omitidos: {report.skipped}",
        f"- Fallidos: {report.failed}",
        f"- Documentos: {report.documents} "
        f"({report.canonical_documents} canónicos, {report.alias_documents} alias)",
        f"- Fragmentos: {report.chunks}",
        f"- Duplicados exactos: {report.duplicates_exact}",
        f"- Duplicados cercanos: {report.duplicates_near}",
        f"- Tokens de entrada: {report.tokens_in}",
        f"- Tokens de salida: {report.tokens_out}",
        f"- Bytes de salida: {report.bytes_out}",
        f"- Duración: {report.duration_seconds:.2f} s",
        "",
        "## Por fuente",
        "",
        "| Fuente | Artefactos |",
        "|--------|-----------:|",
    ]
    for key, value in sorted(report.by_source.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(["", "## Por formato", "", "| Formato | Artefactos |", "|---------|-----------:|"])
    for key, value in sorted(report.by_media_type.items()):
        lines.append(f"| {key} | {value} |")
    lines.extend(
        [
            "",
            "## Motivos de omisión",
            "",
            "| Motivo | Artefactos |",
            "|--------|-----------:|",
        ]
    )
    if report.skip_reasons:
        for key, value in sorted(report.skip_reasons.items()):
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("| — | 0 |")
    lines.extend(
        [
            "",
            "## Cobertura de secciones",
            "",
            f"- Con título: {report.section_coverage.get('with_title', 0)}",
            f"- Sin título: {report.section_coverage.get('without_title', 0)}",
            "",
            "## Flags de calidad",
            "",
            "| Flag | Documentos |",
            "|------|-----------:|",
        ]
    )
    if report.quality_flags:
        for key, value in sorted(report.quality_flags.items()):
            lines.append(f"| {key} | {value} |")
    else:
        lines.append("| — | 0 |")
    return "\n".join(lines) + "\n"


def write_report(report: RunReport, reports_dir: Path) -> list[str]:
    destination = reports_dir / report.run_id
    destination.mkdir(parents=True, exist_ok=True)
    json_path = destination / "quality.json"
    markdown_path = destination / "quality.md"
    atomic_write_json(json_path, report.to_dict())
    atomic_write_text(markdown_path, render_quality_markdown(report))
    return [json_path.as_posix(), markdown_path.as_posix()]


def report_payload(report: RunReport) -> dict[str, Any]:
    return report.to_dict()
