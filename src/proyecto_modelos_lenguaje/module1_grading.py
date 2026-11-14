"""Calificación humana y repeticiones de la evaluación del Módulo 1.

Tres comandos sobre el registro JSON de ``module1_eval``:

- ``export``: una planilla CSV por calificador, **a ciegas** (sin la variante) y en orden
  aleatorio, con la respuesta, las citas y el texto de los fragmentos citados para juzgar la
  alucinación. Escribe también las instrucciones de calificación.
- ``merge``: valida las planillas, mide el acuerdo entre calificadores (acuerdo exacto y kappa de
  Cohen), aplica el consenso de los desacuerdos y escribe la calificación en el JSON y en el reporte
  Markdown. Si quedan desacuerdos sin consenso, genera ``desacuerdos.csv`` y no toca el registro.
- ``aggregate``: media y desviación de las métricas automáticas en varias ejecuciones repetidas.

Uso::

    uv run python -m proyecto_modelos_lenguaje.module1_grading export --graders roberto jason
    uv run python -m proyecto_modelos_lenguaje.module1_grading merge \\
        --grades docs/calificacion_m1/plantilla_roberto.csv docs/calificacion_m1/plantilla_jason.csv
    uv run python -m proyecto_modelos_lenguaje.module1_grading aggregate \\
        --runs docs/evaluacion_modulo1.json docs/evaluacion_m1_r2.json docs/evaluacion_m1_r3.json
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
import statistics
import sys
import unicodedata
from collections import Counter
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .module1_eval import DEFAULT_JSON, DEFAULT_REPORT, EvalRow, render_report
from .module1_grading_guide import INSTRUCTIONS
from .retrieval import GoldUnit, RetrievalError, load_gold_units
from .tasks import _resolve_gold_dir

DEFAULT_GRADING_DIR = "docs/calificacion_m1"
DEFAULT_SEED = 2026
FRAGMENT_CHARS = 1200
GRADE_COLUMNS = ("correccion", "coherencia", "alucinacion")
TEMPLATE_COLUMNS = (
    "item",
    "pregunta_id",
    "pregunta",
    "esperado",
    "fuente_esperada",
    "respuesta",
    "citas",
    "fragmentos_citados",
    "fuentes",
    *GRADE_COLUMNS,
    "notas",
)
EXPECTED_LABELS = {
    "D": "respuesta directa",
    "P": "respuesta parcial (responder lo cubierto y declarar lo que falta)",
    "C": "comparación",
    "M": "meta-respuesta (sobre el propio corpus)",
    "S": "síntesis",
    "X": "sin evidencia: debe declarar que no hay información",
}


class GradingError(ValueError):
    """Invalid or incomplete grading input."""


@dataclass(frozen=True, slots=True)
class Grade:
    """One grader's marks for one item."""

    correctness: int
    coherence: int
    hallucination: bool


def item_id(run_id: str, question_id: str, variant: str) -> str:
    """Stable, opaque identifier: the same for both graders, without revealing the variant."""
    digest = hashlib.sha256(f"{run_id}|{question_id}|{variant}".encode()).hexdigest()
    return f"R{digest[:8]}"


def load_run(path: Path) -> tuple[dict[str, Any], list[EvalRow]]:
    """Read a ``module1_eval`` JSON record."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload, [EvalRow.from_dict(row) for row in payload["rows"]]


def _fragments(row: EvalRow, units: Mapping[str, GoldUnit]) -> str:
    blocks = []
    for label, unit_id in zip(row.citations, row.cited_units, strict=False):
        unit = units.get(unit_id)
        if unit is None:
            continue
        text = " ".join(unit.text.split())
        if len(text) > FRAGMENT_CHARS:
            text = text[: FRAGMENT_CHARS - 1] + "…"
        blocks.append(f"[{label}] {unit.title or unit.topic_title}: {text}")
    return "\n\n".join(blocks)


def export_templates(
    payload: Mapping[str, Any],
    rows: Sequence[EvalRow],
    graders: Sequence[str],
    out_dir: Path,
    *,
    units: Mapping[str, GoldUnit] | None = None,
    seed: int = DEFAULT_SEED,
) -> list[Path]:
    """Write one blinded, shuffled CSV template per grader plus the grading instructions."""
    if len(set(graders)) != len(graders) or not graders:
        raise GradingError("Indica calificadores distintos (p. ej. --graders roberto jason).")
    run_id = payload["meta"]["run_id"]
    units = units or {}
    records = []
    for row in rows:
        expected = row.expected
        label = "; ".join(EXPECTED_LABELS.get(code, code) for code in expected.split(","))
        records.append(
            {
                "item": item_id(run_id, row.question_id, row.variant),
                "pregunta_id": row.question_id,
                "pregunta": row.question,
                "esperado": f"{expected} ({label})",
                "fuente_esperada": row.expected_source,
                "respuesta": row.answer or f"[error: {row.error}]",
                "citas": " ".join(row.citations),
                "fragmentos_citados": _fragments(row, units),
                "fuentes": " ".join(row.sources),
                "correccion": "",
                "coherencia": "",
                "alucinacion": "",
                "notas": "",
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, grader in enumerate(graders):
        ordered = records[:]
        random.Random(seed + index).shuffle(ordered)
        path = out_dir / f"plantilla_{grader}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TEMPLATE_COLUMNS)
            writer.writeheader()
            writer.writerows(ordered)
        written.append(path)
    (out_dir / "INSTRUCCIONES.md").write_text(INSTRUCTIONS, encoding="utf-8")
    return written


def _plain(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value.strip().lower())
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch))


def parse_grade(raw: Mapping[str, str], where: str) -> Grade:
    """Validate one row of a filled template."""
    correctness, coherence, hallucination = (_plain(raw.get(key) or "") for key in GRADE_COLUMNS)
    if correctness not in {"0", "1", "2"}:
        raise GradingError(f"{where}: correccion debe ser 0, 1 o 2 (hay «{correctness}»).")
    if coherence not in {"1", "2", "3", "4", "5"}:
        raise GradingError(f"{where}: coherencia debe ser de 1 a 5 (hay «{coherence}»).")
    if hallucination not in {"si", "no"}:
        raise GradingError(f"{where}: alucinacion debe ser si o no (hay «{hallucination}»).")
    return Grade(int(correctness), int(coherence), hallucination == "si")


def read_csv(path: Path) -> list[dict[str, str]]:
    """Read a CSV saved by Excel or LibreOffice: comma or semicolon (Excel in Spanish)."""
    with path.open(encoding="utf-8-sig", newline="") as handle:
        header = handle.readline()
        handle.seek(0)
        delimiter = ";" if header.count(";") > header.count(",") else ","
        return list(csv.DictReader(handle, delimiter=delimiter))


def read_grades(path: Path, expected_items: set[str]) -> dict[str, Grade]:
    """Read and validate a filled template; every item must be graded exactly once."""
    rows = read_csv(path)
    errors: list[str] = []
    grades: dict[str, Grade] = {}
    seen: set[str] = set()
    for number, raw in enumerate(rows, start=2):
        item = (raw.get("item") or "").strip()
        where = f"{path.name}, fila {number} ({item or 'sin ítem'})"
        if item not in expected_items:
            errors.append(f"{where}: el ítem no pertenece a esta ejecución.")
            continue
        if item in seen:
            errors.append(f"{where}: ítem repetido.")
            continue
        seen.add(item)
        try:
            grades[item] = parse_grade(raw, where)
        except GradingError as exc:
            errors.append(str(exc))
    missing = expected_items - seen
    if missing:
        sample = ", ".join(sorted(missing)[:5])
        errors.append(f"{path.name}: faltan {len(missing)} ítems ({sample}…).")
    if errors:
        raise GradingError("\n".join(errors[:20]))
    return grades


def cohen_kappa(
    first: Sequence[Any], second: Sequence[Any], *, weights: str | None = None
) -> float:
    """Cohen's kappa (unweighted or quadratic-weighted) for two raters over the same items."""
    categories = sorted(set(first) | set(second))
    if len(categories) < 2:
        return 1.0
    index = {value: position for position, value in enumerate(categories)}
    size, total = len(categories), len(first)
    observed = [[0.0] * size for _ in range(size)]
    for a, b in zip(first, second, strict=True):
        observed[index[a]][index[b]] += 1
    rows = [sum(line) for line in observed]
    cols = [sum(observed[i][j] for i in range(size)) for j in range(size)]

    def weight(i: int, j: int) -> float:
        if weights == "quadratic":
            return ((i - j) ** 2) / ((size - 1) ** 2)
        return 0.0 if i == j else 1.0

    disagreement = sum(weight(i, j) * observed[i][j] for i in range(size) for j in range(size))
    expected = sum(
        weight(i, j) * rows[i] * cols[j] / total for i in range(size) for j in range(size)
    )
    return round(1 - disagreement / expected, 3) if expected else 1.0


def agreement(first: Mapping[str, Grade], second: Mapping[str, Grade]) -> dict[str, Any]:
    """Agreement between two graders before consensus."""
    items = sorted(first)
    a = [first[item] for item in items]
    b = [second[item] for item in items]
    total = len(items)

    def exact(values: Sequence[tuple[Any, Any]]) -> float:
        return round(sum(x == y for x, y in values) / total, 3)

    corr = [(x.correctness, y.correctness) for x, y in zip(a, b, strict=True)]
    coh = [(x.coherence, y.coherence) for x, y in zip(a, b, strict=True)]
    hal = [(x.hallucination, y.hallucination) for x, y in zip(a, b, strict=True)]
    return {
        "items": total,
        "correctness": {
            "exact": exact(corr),
            "kappa": cohen_kappa([x for x, _ in corr], [y for _, y in corr]),
            "weighted_kappa": cohen_kappa(
                [x for x, _ in corr], [y for _, y in corr], weights="quadratic"
            ),
        },
        "coherence": {
            "exact": exact(coh),
            "within_one": round(sum(abs(x - y) <= 1 for x, y in coh) / total, 3),
            "mean_abs_diff": round(statistics.fmean(abs(x - y) for x, y in coh), 3),
        },
        "hallucination": {
            "exact": exact(hal),
            "kappa": cohen_kappa([x for x, _ in hal], [y for _, y in hal]),
        },
    }


def read_consensus(path: Path) -> dict[str, dict[str, str]]:
    """Consensus values for disagreements (columns ``*_consenso``)."""
    return {
        (raw.get("item") or "").strip(): {
            key: (raw.get(f"{key}_consenso") or "").strip() for key in GRADE_COLUMNS
        }
        for raw in read_csv(path)
    }


def consolidate(
    first: Mapping[str, Grade],
    second: Mapping[str, Grade],
    consensus: Mapping[str, Mapping[str, str]] | None = None,
) -> tuple[dict[str, dict[str, str]], list[str], int]:
    """Final grade per item; returns (grades, unresolved items, items settled by consensus)."""
    consensus = consensus or {}
    final: dict[str, dict[str, str]] = {}
    unresolved: list[str] = []
    settled = 0
    for item in sorted(first):
        a, b = first[item], second[item]
        agreed = consensus.get(item, {})
        grade: dict[str, str] = {}
        used = False
        if a.correctness == b.correctness:
            grade["correccion"] = str(a.correctness)
        elif agreed.get("correccion", "") in {"0", "1", "2"}:
            grade["correccion"], used = agreed["correccion"], True
        if a.hallucination == b.hallucination:
            grade["alucinacion"] = "sí" if a.hallucination else "no"
        elif _plain(agreed.get("alucinacion", "")) in {"si", "no"}:
            grade["alucinacion"] = "sí" if _plain(agreed["alucinacion"]) == "si" else "no"
            used = True
        if agreed.get("coherencia", "") in {"1", "2", "3", "4", "5"}:
            grade["coherencia"], used = agreed["coherencia"], True
        else:
            mean = (a.coherence + b.coherence) / 2
            grade["coherencia"] = str(int(mean)) if mean.is_integer() else str(mean)
        if {"correccion", "alucinacion"} <= grade.keys():
            final[item] = grade
            settled += used
        else:
            unresolved.append(item)
    return final, unresolved, settled


def write_disagreements(
    path: Path,
    rows_by_item: Mapping[str, EvalRow],
    first: Mapping[str, Grade],
    second: Mapping[str, Grade],
    names: Sequence[str],
    unresolved: Sequence[str],
) -> None:
    """CSV with both marks and empty ``*_consenso`` columns for each unresolved item."""
    a_name, b_name = names
    fields = [
        "item",
        "pregunta_id",
        "pregunta",
        "respuesta",
        f"correccion_{a_name}",
        f"correccion_{b_name}",
        f"alucinacion_{a_name}",
        f"alucinacion_{b_name}",
        f"coherencia_{a_name}",
        f"coherencia_{b_name}",
        "correccion_consenso",
        "alucinacion_consenso",
        "coherencia_consenso",
    ]
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in unresolved:
            row, a, b = rows_by_item[item], first[item], second[item]
            writer.writerow(
                {
                    "item": item,
                    "pregunta_id": row.question_id,
                    "pregunta": row.question,
                    "respuesta": row.answer,
                    f"correccion_{a_name}": a.correctness,
                    f"correccion_{b_name}": b.correctness,
                    f"alucinacion_{a_name}": "si" if a.hallucination else "no",
                    f"alucinacion_{b_name}": "si" if b.hallucination else "no",
                    f"coherencia_{a_name}": a.coherence,
                    f"coherencia_{b_name}": b.coherence,
                    "correccion_consenso": "",
                    "alucinacion_consenso": "",
                    "coherencia_consenso": "",
                }
            )


def _round(value: float) -> float:
    return round(value, 3)


def human_summary(rows: Sequence[EvalRow]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Per-variant and per-expected-code metrics from the consolidated human grades."""

    def metrics(subset: Sequence[EvalRow]) -> dict[str, Any]:
        corr = [int(row.human["correccion"]) for row in subset]
        coh = [float(row.human["coherencia"]) for row in subset]
        hal = sum(row.human["alucinacion"] == "sí" for row in subset)
        counts = Counter(corr)
        return {
            "n": len(subset),
            "correctness_mean": _round(statistics.fmean(corr)),
            "correct": counts[2],
            "partial": counts[1],
            "incorrect": counts[0],
            "coherence_mean": _round(statistics.fmean(coh)),
            "coherence_stdev": _round(statistics.stdev(coh)) if len(coh) > 1 else None,
            "hallucinations": hal,
            "hallucination_rate": _round(hal / len(subset)),
        }

    summary: dict[str, Any] = {}
    by_expected: dict[str, Any] = {}
    for variant in dict.fromkeys(row.variant for row in rows):
        subset = [row for row in rows if row.variant == variant and row.human]
        summary[variant] = metrics(subset)
        groups: dict[str, Any] = {}
        for code in sorted({row.expected for row in subset}):
            group = metrics([row for row in subset if row.expected == code])
            groups[code] = {key: group[key] for key in ("n", "correctness_mean", "hallucinations")}
        by_expected[variant] = groups
    return summary, by_expected


def merge_grades(
    run_path: Path,
    grade_paths: Sequence[Path],
    *,
    report_path: Path,
    consensus_path: Path | None = None,
    disagreements_path: Path | None = None,
) -> dict[str, Any]:
    """Validate, measure agreement, consolidate and write the human grades into JSON and report.

    Raises ``GradingError`` on invalid templates. When disagreements remain without consensus, it
    writes ``disagreements_path`` and returns ``{"unresolved": [...]}`` without touching the run.
    """
    if len(grade_paths) != 2:
        raise GradingError("merge necesita exactamente dos planillas (--grades a.csv b.csv).")
    payload, rows = load_run(run_path)
    run_id = payload["meta"]["run_id"]
    rows_by_item = {item_id(run_id, row.question_id, row.variant): row for row in rows}
    expected = set(rows_by_item)
    first, second = (read_grades(path, expected) for path in grade_paths)
    names = [path.stem.removeprefix("plantilla_") for path in grade_paths]
    stats = agreement(first, second)
    consensus = read_consensus(consensus_path) if consensus_path else None
    final, unresolved, settled = consolidate(first, second, consensus)
    if unresolved:
        target = disagreements_path or run_path.parent / "desacuerdos.csv"
        write_disagreements(target, rows_by_item, first, second, names, unresolved)
        return {"agreement": stats, "unresolved": unresolved, "disagreements": str(target)}
    for item, grade in final.items():
        rows_by_item[item].human = grade
    summary, by_expected = human_summary(rows)
    human = {
        "graders": names,
        "consensus_items": settled,
        "agreement": stats,
        "summary": summary,
        "by_expected": by_expected,
    }
    payload["rows"] = [_row_dict(row) for row in rows]
    payload["human"] = human
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path.write_text(
        render_report(rows, payload["summary"], payload["meta"], human), encoding="utf-8"
    )
    return {"agreement": stats, "unresolved": [], "human": human}


def _row_dict(row: EvalRow) -> dict[str, Any]:
    data = {name: getattr(row, name) for name in row.__dataclass_fields__}
    data["fallback_matches"] = row.fallback_matches
    return data


AGGREGATED_METRICS = (
    ("ok", "Respuestas ok"),
    ("fallback", "Abstenciones"),
    ("with_citation", "Con cita"),
    ("fallback_agreement", "Acierto de fallback"),
    ("latency_mean_s", "Latencia media (s)"),
    ("input_tokens", "Tokens de entrada"),
    ("output_tokens", "Tokens de salida"),
)


def aggregate_runs(payloads: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    """Mean and standard deviation of the automatic metrics across repeated runs."""
    if len(payloads) < 2:
        raise GradingError("aggregate necesita al menos dos ejecuciones.")
    variants = list(payloads[0]["summary"])
    result: dict[str, Any] = {"runs": [p["meta"]["run_id"] for p in payloads], "variants": {}}
    for variant in variants:
        metrics: dict[str, Any] = {}
        for key, _label in AGGREGATED_METRICS:
            values = [p["summary"][variant][key] for p in payloads]
            values = [float(v) for v in values if v is not None]
            metrics[key] = {
                "mean": _round(statistics.fmean(values)) if values else None,
                "stdev": _round(statistics.stdev(values)) if len(values) > 1 else None,
                "values": values,
            }
        fallbacks: dict[str, set[bool]] = {}
        for p in payloads:
            for row in p["rows"]:
                if row["variant"] == variant:
                    fallbacks.setdefault(row["question_id"], set()).add(bool(row["fallback"]))
        unstable = sorted(qid for qid, states in fallbacks.items() if len(states) > 1)
        metrics["unstable_fallback"] = unstable
        result["variants"][variant] = metrics
    shas = {
        variant: sorted({p["meta"]["prompts"][variant]["sha256"] for p in payloads})
        for variant in variants
        if all("prompts" in p["meta"] for p in payloads)
    }
    result["prompt_sha256"] = shas
    result["models"] = sorted({p["meta"]["model"] for p in payloads})
    return result


def render_aggregate(result: Mapping[str, Any], command: str) -> str:
    """Markdown table of mean ± standard deviation per variant."""
    runs = ", ".join(f"`{run}`" for run in result["runs"])
    lines = [
        "# Evaluación del Módulo 1 — repeticiones",
        "",
        f"**Ejecuciones**: {runs} · **Modelo**: {', '.join(result['models'])}",
        "",
        f"**Comando**: `{command}`",
        "",
        "El modelo no es determinista (temperatura 0,1), así que las métricas automáticas se "
        "reportan como media ± desviación estándar de las ejecuciones repetidas sobre las mismas "
        "40 preguntas, el mismo corpus y los mismos prompts.",
        "",
        "| Métrica | " + " | ".join(result["variants"]) + " |",
        "|---|" + "---|" * len(result["variants"]),
    ]
    for key, label in AGGREGATED_METRICS:
        cells = []
        for metrics in result["variants"].values():
            data = metrics[key]
            cells.append("—" if data["mean"] is None else f"{data['mean']} ± {data['stdev']}")
        lines.append(f"| {label} | " + " | ".join(cells) + " |")
    lines += ["", "**Estabilidad de la abstención** (preguntas que cambian entre ejecuciones):", ""]
    for variant, metrics in result["variants"].items():
        unstable = metrics["unstable_fallback"]
        lines.append(f"- `{variant}`: {len(unstable)} ({', '.join(unstable) or 'ninguna'}).")
    shas = result.get("prompt_sha256") or {}
    if any(len(values) > 1 for values in shas.values()):
        lines += ["", "⚠ Las ejecuciones no usaron el mismo prompt en todas las variantes."]
    lines.append("")
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m proyecto_modelos_lenguaje.module1_grading",
        description="Calificación humana a ciegas y repeticiones de la evaluación del Módulo 1.",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="Planillas CSV a ciegas, una por calificador.")
    export.add_argument("--run", default=DEFAULT_JSON, help="Registro JSON de module1_eval.")
    export.add_argument("--graders", nargs="+", required=True, help="Nombres de los calificadores.")
    export.add_argument("--out-dir", default=DEFAULT_GRADING_DIR)
    export.add_argument("--gold-dir", help="Capa oro para el texto de los fragmentos citados.")
    export.add_argument("--seed", type=int, default=DEFAULT_SEED)
    merge = sub.add_parser("merge", help="Une las dos planillas y escribe la calificación.")
    merge.add_argument("--run", default=DEFAULT_JSON)
    merge.add_argument("--report", default=DEFAULT_REPORT)
    merge.add_argument("--grades", nargs=2, required=True, metavar="CSV")
    merge.add_argument("--consensus", help="desacuerdos.csv con las columnas *_consenso llenas.")
    merge.add_argument("--disagreements", help="Dónde escribir los desacuerdos sin resolver.")
    aggregate = sub.add_parser("aggregate", help="Media ± desviación de ejecuciones repetidas.")
    aggregate.add_argument("--runs", nargs="+", required=True, metavar="JSON")
    aggregate.add_argument("--out", default="docs/evaluacion_modulo1_repeticiones.md")
    aggregate.add_argument("--json-out", default="docs/evaluacion_modulo1_repeticiones.json")
    return parser


def main(argv: Sequence[str] | None = None, *, project_root: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    command = "uv run python -m proyecto_modelos_lenguaje.module1_grading " + " ".join(
        argv if argv is not None else sys.argv[1:]
    )
    try:
        if args.command == "export":
            payload, rows = load_run(root / args.run)
            try:
                units = {
                    unit.unit_id: unit
                    for unit in load_gold_units(_resolve_gold_dir(args.gold_dir, root))
                }
            except RetrievalError:
                units = {}
            paths = export_templates(
                payload, rows, args.graders, root / args.out_dir, units=units, seed=args.seed
            )
            for path in paths:
                print(f"Planilla: {path}")
            if not any(row.cited_units for row in rows):
                print(
                    "Aviso: este registro no guarda las unidades citadas; la columna "
                    "fragmentos_citados queda vacía (vuelve a ejecutar module1_eval).",
                    file=sys.stderr,
                )
            return 0
        if args.command == "merge":
            result = merge_grades(
                root / args.run,
                [root / path for path in args.grades],
                report_path=root / args.report,
                consensus_path=root / args.consensus if args.consensus else None,
                disagreements_path=root / args.disagreements if args.disagreements else None,
            )
            print(json.dumps(result["agreement"], ensure_ascii=False, indent=2))
            if result["unresolved"]:
                print(
                    f"{len(result['unresolved'])} desacuerdos sin consenso en "
                    f"{result['disagreements']}: llenen las columnas *_consenso y repitan con "
                    "--consensus.",
                    file=sys.stderr,
                )
                return 3
            print(json.dumps(result["human"]["summary"], ensure_ascii=False, indent=2))
            return 0
        payloads = [json.loads((root / path).read_text(encoding="utf-8")) for path in args.runs]
        result = aggregate_runs(payloads)
        (root / args.json_out).write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        (root / args.out).write_text(render_aggregate(result, command), encoding="utf-8")
        print(render_aggregate(result, command))
        return 0
    except (GradingError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
