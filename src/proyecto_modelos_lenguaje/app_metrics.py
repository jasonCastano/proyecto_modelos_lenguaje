"""Read-only corpus metrics for the web experience."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT

LFS_POINTER = "version https://git-lfs.github.com/spec/v1"
REQUIRED_RUNS = {
    "silver": "2026-10-silver-01",
    "gold": "2026-10-gold-01",
}


@dataclass(frozen=True, slots=True)
class AppMetrics:
    active_artifacts: int
    canonical_documents: int
    aliases: int
    chunks: int
    units: int
    facts: int
    entities: int
    conflicts: int
    coverage_covered: int
    coverage_total: int
    silver_tokens: int
    gold_tokens: int
    skipped: int
    omissions: int
    silver_run: str
    gold_run: str
    data_status: str
    detail: str | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "active_artifacts": self.active_artifacts,
            "canonical_documents": self.canonical_documents,
            "aliases": self.aliases,
            "chunks": self.chunks,
            "units": self.units,
            "facts": self.facts,
            "entities": self.entities,
            "conflicts": self.conflicts,
            "coverage_covered": self.coverage_covered,
            "coverage_total": self.coverage_total,
            "silver_tokens": self.silver_tokens,
            "gold_tokens": self.gold_tokens,
            "skipped": self.skipped,
            "omissions": self.omissions,
            "silver_run": self.silver_run,
            "gold_run": self.gold_run,
            "data_status": self.data_status,
            "detail": self.detail,
        }


@dataclass(frozen=True, slots=True)
class PanelMetric:
    label: str
    value: str
    help: str | None = None
    status: str = "ok"


def _is_lfs_pointer(path: Path) -> bool:
    if not path.is_file():
        return False
    try:
        with path.open("rb") as handle:
            return LFS_POINTER.encode() in handle.read(128)
    except OSError:
        return False


def _latest_report(directory: Path, preferred: str) -> Path | None:
    preferred_path = directory / preferred / "quality.json"
    if preferred_path.is_file():
        return preferred_path
    candidates = sorted(directory.glob("*/quality.json"))
    return candidates[-1] if candidates else None


def _read_json(path: Path | None) -> dict[str, Any]:
    if path is None or not path.is_file() or _is_lfs_pointer(path):
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except OSError, json.JSONDecodeError:
        return {}
    return payload if isinstance(payload, dict) else {}


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file() or _is_lfs_pointer(path):
        return []
    records: list[dict[str, Any]] = []
    try:
        with path.open(encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if line:
                    records.append(json.loads(line))
    except OSError, json.JSONDecodeError:
        return []
    return records


def _active_artifacts(database: Path) -> tuple[int, str | None]:
    if not database.is_file():
        return 0, "bronze.sqlite3 no existe"
    if _is_lfs_pointer(database):
        return 0, "bronze.sqlite3 es un puntero LFS"
    try:
        connection = sqlite3.connect(f"file:{database.as_posix()}?mode=ro", uri=True)
        try:
            row = connection.execute("SELECT COUNT(*) FROM v_active_artifacts").fetchone()
        finally:
            connection.close()
    except sqlite3.Error as exc:
        return 0, f"no se pudo leer v_active_artifacts: {exc}"
    return int(row[0]) if row else 0, None


def _coverage_counts(gold: Path) -> tuple[int, int, str | None]:
    path = gold / "coverage.json"
    data = _read_json(path)
    items = data.get("items", []) if isinstance(data, dict) else []
    if not items:
        return 0, 24, "coverage.json no tiene ítems"
    covered = sum(1 for item in items if item.get("status") == "covered")
    return covered, 24, None if len(items) == 24 else f"coverage.json tiene {len(items)} ítems"


def _manifest_problem(gold: Path, expected_run: str) -> str | None:
    path = gold / "manifest.json"
    if not path.is_file() or _is_lfs_pointer(path):
        return None
    data = _read_json(path)
    if not data:
        return "manifest.json no se pudo leer"
    declared = str(data.get("run_id", ""))
    if declared != expected_run:
        return f"manifest.json declara el run {declared or 'desconocido'}"
    return None


def load_app_metrics(
    *,
    project_root: Path | None = None,
    gold_dir: Path | None = None,
    silver_dir: Path | None = None,
    bronze_dir: Path | None = None,
) -> AppMetrics:
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    gold = gold_dir or root / "data" / "gold"
    silver = silver_dir or root / "data" / "silver"
    bronze = bronze_dir or root / "data" / "bronze"

    required = {
        "knowledge_units.jsonl": gold / "knowledge_units.jsonl",
        "context_8000.json": gold / "context_8000.json",
        "faq_seeds.jsonl": gold / "faq_seeds.jsonl",
        "coverage.json": gold / "coverage.json",
        "manifest.json": gold / "manifest.json",
        "bronze.sqlite3": bronze / "_meta" / "bronze.sqlite3",
    }
    problems: list[str] = []
    for label, path in required.items():
        if not path.is_file():
            problems.append(f"falta {label}")
        elif _is_lfs_pointer(path):
            problems.append(f"{label} es un puntero LFS")

    silver_report = _latest_report(silver / "reports", REQUIRED_RUNS["silver"])
    gold_report = _latest_report(gold / "reports", REQUIRED_RUNS["gold"])
    if silver_report is None:
        problems.append("falta el reporte de plata")
    if gold_report is None:
        problems.append("falta el reporte de oro")

    silver_data = _read_json(silver_report)
    gold_data = _read_json(gold_report)
    manifest_error = _manifest_problem(gold, REQUIRED_RUNS["gold"])
    if manifest_error:
        problems.append(manifest_error)
    active, active_error = _active_artifacts(bronze / "_meta" / "bronze.sqlite3")
    if active_error:
        problems.append(active_error)
    covered, coverage_total, coverage_error = _coverage_counts(gold)
    if coverage_error:
        problems.append(coverage_error)

    skip_reasons = silver_data.get("skip_reasons", {})
    omissions = (
        sum(int(value) for value in skip_reasons.values()) if isinstance(skip_reasons, dict) else 0
    )
    status = "complete" if not problems else "incomplete"
    if active_error and "no se pudo leer" in active_error:
        status = "unknown"
    return AppMetrics(
        active_artifacts=active,
        canonical_documents=int(silver_data.get("canonical_documents", 0) or 0),
        aliases=int(silver_data.get("alias_documents", 0) or 0),
        chunks=int(silver_data.get("chunks", 0) or 0),
        units=int(gold_data.get("units", 0) or 0),
        facts=int(gold_data.get("facts", 0) or 0),
        entities=int(gold_data.get("entities", 0) or 0),
        conflicts=int(gold_data.get("conflicts", 0) or 0),
        coverage_covered=covered,
        coverage_total=coverage_total,
        silver_tokens=int(silver_data.get("tokens_out", 0) or 0),
        gold_tokens=int(gold_data.get("tokens", 0) or 0),
        skipped=int(silver_data.get("skipped", 0) or 0),
        omissions=omissions,
        silver_run=str(silver_data.get("run_id", "unknown")),
        gold_run=str(gold_data.get("run_id", "unknown")),
        data_status=status,
        detail="; ".join(problems) if problems else None,
    )


def format_metric(value: int | str) -> str:
    if isinstance(value, int):
        return f"{value:,}".replace(",", ".")
    return str(value)


def format_status(status: str) -> str:
    labels = {
        "complete": "Completo",
        "incomplete": "Incompleto",
        "unknown": "Desconocido",
        "provider_ready": "Proveedor listo",
        "missing_key": "Falta la clave",
        "auth_failed": "Clave inválida",
        "rate_limited": "Cuota agotada",
        "provider_timeout": "Sin respuesta",
        "provider_unavailable": "Proveedor no disponible",
        "provider_error": "Error del proveedor",
        "model_unavailable": "Modelo no disponible",
        "demo": "Modo demostración",
        "ok": "OK",
        "fallback": "Sin evidencia",
        "review": "Revisar",
        "error": "Error",
    }
    return labels.get(status, status)


def metric_rows(metrics: AppMetrics) -> list[PanelMetric]:
    return [
        PanelMetric("Artefactos activos", format_metric(metrics.active_artifacts)),
        PanelMetric("Documentos canónicos", format_metric(metrics.canonical_documents)),
        PanelMetric("Alias", format_metric(metrics.aliases)),
        PanelMetric("Fragmentos", format_metric(metrics.chunks)),
        PanelMetric("Unidades", format_metric(metrics.units)),
        PanelMetric("Hechos", format_metric(metrics.facts)),
        PanelMetric("Entidades", format_metric(metrics.entities)),
        PanelMetric("Conflictos", format_metric(metrics.conflicts)),
        PanelMetric(
            "Cobertura",
            f"{metrics.coverage_covered}/{metrics.coverage_total}",
            help="Ítems de cobertura con estado covered",
        ),
        PanelMetric("Tokens plata", format_metric(metrics.silver_tokens)),
        PanelMetric("Tokens oro", format_metric(metrics.gold_tokens)),
        PanelMetric("Omitidos", format_metric(metrics.omissions)),
        PanelMetric("Run plata", metrics.silver_run),
        PanelMetric("Run oro", metrics.gold_run),
    ]


def status_rows(
    metrics: AppMetrics,
    *,
    model_status: str = "unknown",
    demo_mode: bool = False,
) -> list[PanelMetric]:
    rows = [
        PanelMetric(
            "Datos",
            format_status(metrics.data_status),
            help=metrics.detail,
            status="ok" if metrics.data_status == "complete" else "warning",
        ),
        PanelMetric(
            "Modelo",
            format_status(model_status),
            status="ok" if model_status in {"provider_ready", "demo"} else "warning",
        ),
        PanelMetric(
            "Modo",
            "Demostración" if demo_mode else "API",
            status="ok",
        ),
    ]
    if metrics.skipped:
        rows.append(PanelMetric("Descartados", format_metric(metrics.skipped)))
    return rows


def response_rows(
    *,
    model: str,
    prompt_version: str,
    latency_seconds: float,
    citations: int,
    status: str,
    input_tokens: int = 0,
    output_tokens: int = 0,
) -> list[PanelMetric]:
    return [
        PanelMetric("Modelo", model),
        PanelMetric("Prompt", prompt_version),
        PanelMetric("Latencia", f"{latency_seconds:.2f} s"),
        PanelMetric("Citas", str(citations)),
        PanelMetric("Estado", format_status(status)),
        PanelMetric("Tokens entrada", format_metric(input_tokens)),
        PanelMetric("Tokens salida", format_metric(output_tokens)),
    ]
