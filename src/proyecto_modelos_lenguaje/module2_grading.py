"""Calificación humana de la comparación cadena vs. agente del Módulo 2.

Sobre el registro ``docs/evaluacion_variantes.json`` (``agent evaluate --compare --judge``):

- ``export``: planillas a ciegas (sin la variante) y en orden aleatorio con dos tipos de ítem:
  todas las **repreguntas** (SC-006: ¿resuelve la referencia al turno previo?) y una **muestra**
  de respuestas factuales, las mismas preguntas en ambas variantes, para contrastar al juez LLM.
- ``merge``: valida, mide el acuerdo entre calificadores, exige consenso en los desacuerdos y
  escribe la calificación (y el acuerdo persona–juez) en el JSON y en
  ``docs/evaluacion_modulo2.md``.

Uso::

    uv run python -m proyecto_modelos_lenguaje.module2_grading export --graders roberto jason
    uv run python -m proyecto_modelos_lenguaje.module2_grading merge \\
        --grades docs/calificacion_m2/plantilla_roberto.csv docs/calificacion_m2/plantilla_jason.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import random
import statistics
import sys
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT
from .module1_grading import GradingError, _plain, cohen_kappa, item_id, read_csv
from .module2_grading_guide import INSTRUCTIONS

DEFAULT_RUN = "docs/evaluacion_variantes.json"
DEFAULT_REPORT = "docs/evaluacion_modulo2.md"
DEFAULT_GRADING_DIR = "docs/calificacion_m2"
DEFAULT_SEED = 2026
DEFAULT_SAMPLE = 10
FACTUAL_TYPES = frozenset({"documental", "structured", "mixed"})
GRADE_COLUMNS = ("correccion", "fiel", "resuelve_referencia")
TEMPLATE_COLUMNS = (
    "item",
    "tipo",
    "consulta_id",
    "pregunta_previa",
    "respuesta_previa",
    "pregunta",
    "respuesta",
    "fragmentos",
    *GRADE_COLUMNS,
    "notas",
)
SECTION_START = "<!-- human-m2:start -->"
SECTION_END = "<!-- human-m2:end -->"


@dataclass(frozen=True, slots=True)
class Grade2:
    """One grader's marks for one Module 2 item (``reference`` is None for sample items)."""

    correctness: int
    faithful: bool
    reference: bool | None


def run_salt(payload: Mapping[str, Any]) -> str:
    """Identifier of the run used to derive opaque item ids."""
    return str((payload.get("meta") or {}).get("run_id") or "variants")


def select_items(
    payload: Mapping[str, Any], *, sample: int = DEFAULT_SAMPLE, seed: int = DEFAULT_SEED
) -> list[tuple[str, str, dict[str, Any]]]:
    """(kind, variant, result) for every follow-up and a paired sample of factual answers."""
    by_variant = {
        v["variant"]: {r["query_id"]: r for r in v["results"]} for v in payload["variants"]
    }
    variants = list(by_variant)
    first = by_variant[variants[0]]
    follow = sorted(qid for qid, r in first.items() if r["type"] == "follow_up")
    eligible = sorted(
        qid
        for qid, r in first.items()
        if r["type"] in FACTUAL_TYPES
        and all(
            qid in by_variant[v]
            and not by_variant[v][qid]["fallback"]
            and by_variant[v][qid].get("contexts")
            for v in variants
        )
    )
    chosen = sorted(random.Random(seed).sample(eligible, min(sample, len(eligible))))
    items = [("repregunta", v, by_variant[v][qid]) for qid in follow for v in variants]
    items += [("muestra", v, by_variant[v][qid]) for qid in chosen for v in variants]
    return items


def export_templates(
    payload: Mapping[str, Any],
    graders: Sequence[str],
    out_dir: Path,
    *,
    sample: int = DEFAULT_SAMPLE,
    seed: int = DEFAULT_SEED,
) -> list[Path]:
    """Write one blinded, shuffled CSV per grader plus the grading instructions."""
    if not graders or len(set(graders)) != len(graders):
        raise GradingError("Indica calificadores distintos (p. ej. --graders roberto jason).")
    salt = run_salt(payload)
    if not any(r.get("contexts") for v in payload["variants"] for r in v["results"]):
        raise GradingError(
            "El registro no guarda los fragmentos (contexts): repite "
            "`agent evaluate --compare --judge` con la versión actual."
        )
    records = []
    for kind, variant, result in select_items(payload, sample=sample, seed=seed):
        records.append(
            {
                "item": item_id(salt, result["query_id"], variant),
                "tipo": kind,
                "consulta_id": result["query_id"],
                "pregunta_previa": result.get("previous_question", ""),
                "respuesta_previa": result.get("previous_answer", ""),
                "pregunta": result["question"],
                "respuesta": result["answer"],
                "fragmentos": "\n\n".join(result.get("contexts") or []),
                "correccion": "",
                "fiel": "",
                "resuelve_referencia": "" if kind == "repregunta" else "na",
                "notas": "",
            }
        )
    out_dir.mkdir(parents=True, exist_ok=True)
    written = []
    for index, grader in enumerate(graders):
        ordered = records[:]
        random.Random(seed + 100 + index).shuffle(ordered)
        path = out_dir / f"plantilla_{grader}.csv"
        with path.open("w", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=TEMPLATE_COLUMNS)
            writer.writeheader()
            writer.writerows(ordered)
        written.append(path)
    (out_dir / "INSTRUCCIONES.md").write_text(INSTRUCTIONS, encoding="utf-8")
    return written


def _yes_no(value: str, column: str, where: str) -> bool:
    plain = _plain(value)
    if plain not in {"si", "no"}:
        raise GradingError(f"{where}: {column} debe ser si o no (hay «{value}»).")
    return plain == "si"


def parse_grade(raw: Mapping[str, str], kind: str, where: str) -> Grade2:
    """Validate one filled row; ``resuelve_referencia`` only applies to follow-ups."""
    correctness = _plain(raw.get("correccion") or "")
    if correctness not in {"0", "1", "2"}:
        raise GradingError(f"{where}: correccion debe ser 0, 1 o 2 (hay «{correctness}»).")
    faithful = _yes_no(raw.get("fiel") or "", "fiel", where)
    reference = None
    if kind == "repregunta":
        reference = _yes_no(raw.get("resuelve_referencia") or "", "resuelve_referencia", where)
    return Grade2(int(correctness), faithful, reference)


def read_grades(path: Path, kinds: Mapping[str, str]) -> dict[str, Grade2]:
    """Read and validate a filled template; every item must be graded exactly once."""
    errors: list[str] = []
    grades: dict[str, Grade2] = {}
    seen: set[str] = set()
    for number, raw in enumerate(read_csv(path), start=2):
        item = (raw.get("item") or "").strip()
        where = f"{path.name}, fila {number} ({item or 'sin ítem'})"
        if item not in kinds:
            errors.append(f"{where}: el ítem no pertenece a esta ejecución.")
            continue
        if item in seen:
            errors.append(f"{where}: ítem repetido.")
            continue
        seen.add(item)
        try:
            grades[item] = parse_grade(raw, kinds[item], where)
        except GradingError as exc:
            errors.append(str(exc))
    missing = set(kinds) - seen
    if missing:
        errors.append(f"{path.name}: faltan {len(missing)} ítems.")
    if errors:
        raise GradingError("\n".join(errors[:20]))
    return grades


def _exact(pairs: Sequence[tuple[Any, Any]]) -> float | None:
    return round(sum(a == b for a, b in pairs) / len(pairs), 3) if pairs else None


def _kappa(pairs: Sequence[tuple[Any, Any]], **kwargs: Any) -> float | None:
    if not pairs:
        return None
    return cohen_kappa([a for a, _ in pairs], [b for _, b in pairs], **kwargs)


def agreement(first: Mapping[str, Grade2], second: Mapping[str, Grade2]) -> dict[str, Any]:
    """Agreement between graders before consensus (reference only on follow-ups)."""
    items = sorted(first)
    corr = [(first[i].correctness, second[i].correctness) for i in items]
    faith = [(first[i].faithful, second[i].faithful) for i in items]
    ref = [
        (first[i].reference, second[i].reference) for i in items if first[i].reference is not None
    ]
    return {
        "items": len(items),
        "correctness": {
            "exact": _exact(corr),
            "kappa": _kappa(corr),
            "weighted_kappa": _kappa(corr, weights="quadratic"),
        },
        "faithful": {"exact": _exact(faith), "kappa": _kappa(faith)},
        "reference": {"exact": _exact(ref), "kappa": _kappa(ref), "items": len(ref)},
    }


def consolidate(
    first: Mapping[str, Grade2],
    second: Mapping[str, Grade2],
    consensus: Mapping[str, Mapping[str, str]] | None = None,
) -> tuple[dict[str, dict[str, Any]], list[str], int]:
    """Final grade per item; every criterion needs agreement or consensus."""
    consensus = consensus or {}
    final: dict[str, dict[str, Any]] = {}
    unresolved: list[str] = []
    settled = 0
    for item in sorted(first):
        a, b, agreed = first[item], second[item], consensus.get(item, {})
        grade: dict[str, Any] = {}
        used = False
        if a.correctness == b.correctness:
            grade["correccion"] = a.correctness
        elif (agreed.get("correccion") or "") in {"0", "1", "2"}:
            grade["correccion"], used = int(agreed["correccion"]), True
        for key, x, y in (
            ("fiel", a.faithful, b.faithful),
            ("resuelve_referencia", a.reference, b.reference),
        ):
            if x is None:
                continue
            if x == y:
                grade[key] = x
            elif _plain(agreed.get(key) or "") in {"si", "no"}:
                grade[key], used = _plain(agreed[key]) == "si", True
        needed = {"correccion", "fiel"} | (
            {"resuelve_referencia"} if a.reference is not None else set()
        )
        if needed <= grade.keys():
            final[item] = grade
            settled += used
        else:
            unresolved.append(item)
    return final, unresolved, settled


def write_disagreements(
    path: Path,
    info: Mapping[str, dict[str, Any]],
    first: Mapping[str, Grade2],
    second: Mapping[str, Grade2],
    names: Sequence[str],
    unresolved: Sequence[str],
) -> None:
    """Both marks per unresolved item and empty ``*_consenso`` columns."""
    a_name, b_name = names

    def show(value: bool | None) -> str:
        return "na" if value is None else ("si" if value else "no")

    fields = ["item", "tipo", "consulta_id", "pregunta", "respuesta"]
    for key in GRADE_COLUMNS:
        fields += [f"{key}_{a_name}", f"{key}_{b_name}"]
    fields += [f"{key}_consenso" for key in GRADE_COLUMNS]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for item in unresolved:
            a, b, row = first[item], second[item], info[item]
            writer.writerow(
                {
                    "item": item,
                    "tipo": row["kind"],
                    "consulta_id": row["result"]["query_id"],
                    "pregunta": row["result"]["question"],
                    "respuesta": row["result"]["answer"],
                    f"correccion_{a_name}": a.correctness,
                    f"correccion_{b_name}": b.correctness,
                    f"fiel_{a_name}": show(a.faithful),
                    f"fiel_{b_name}": show(b.faithful),
                    f"resuelve_referencia_{a_name}": show(a.reference),
                    f"resuelve_referencia_{b_name}": show(b.reference),
                    "correccion_consenso": "",
                    "fiel_consenso": "",
                    "resuelve_referencia_consenso": "",
                }
            )


def human_summary(info: Mapping[str, dict[str, Any]]) -> dict[str, Any]:
    """Per-variant human metrics and person–judge agreement on faithfulness."""
    summary: dict[str, Any] = {}
    for variant in dict.fromkeys(row["variant"] for row in info.values()):
        rows = [row for row in info.values() if row["variant"] == variant]
        follow = [row for row in rows if row["kind"] == "repregunta"]
        sample = [row for row in rows if row["kind"] == "muestra"]
        judged = [
            row
            for row in sample
            if (row["result"].get("judge") or {}).get("faithfulness") is not None
        ]
        pairs = [
            (row["grade"]["fiel"], row["result"]["judge"]["faithfulness"] >= 1.0) for row in judged
        ]

        def judge_mean(judged: list[dict[str, Any]], flag: bool) -> float | None:
            values = [
                row["result"]["judge"]["faithfulness"]
                for row in judged
                if row["grade"]["fiel"] is flag
            ]
            return round(statistics.fmean(values), 3) if values else None

        summary[variant] = {
            "follow_ups": len(follow),
            "follow_up_resolved": sum(row["grade"]["resuelve_referencia"] for row in follow),
            "follow_up_correct": sum(row["grade"]["correccion"] == 2 for row in follow),
            "follow_up_correctness_mean": round(
                statistics.fmean(row["grade"]["correccion"] for row in follow), 3
            )
            if follow
            else None,
            "sample": len(sample),
            "sample_correctness_mean": round(
                statistics.fmean(row["grade"]["correccion"] for row in sample), 3
            )
            if sample
            else None,
            "sample_faithful": sum(row["grade"]["fiel"] for row in sample),
            "judge_items": len(judged),
            "judge_human_agreement": _exact(pairs),
            "judge_human_kappa": _kappa(pairs),
            "judge_faithfulness_when_human_faithful": judge_mean(judged, True),
            "judge_faithfulness_when_human_unfaithful": judge_mean(judged, False),
        }
    return summary


def render_section(human: Mapping[str, Any]) -> str:
    """Markdown section for ``docs/evaluacion_modulo2.md``."""
    summary, agreement_ = human["summary"], human["agreement"]
    variants = list(summary)
    head = "| Métrica | " + " | ".join(variants) + " |"
    sep = "|---" * (len(variants) + 1) + "|"

    def row(label: str, render: Any) -> str:
        return f"| {label} | " + " | ".join(render(summary[v]) for v in variants) + " |"

    def ratio(a: Any, b: Any) -> str:
        return f"{a}/{b}"

    lines = [
        SECTION_START,
        "## Calificación humana: repreguntas y control del juez",
        "",
        f"**Ejecución calificada**: `{human['run_id']}` · **Calificadores**: "
        f"{' y '.join(human['graders'])} (planillas a ciegas, sin la variante, en orden aleatorio; "
        f"{human['consensus_items']} ítems resueltos por consenso). Instrucciones: "
        "`docs/calificacion_m2/INSTRUCCIONES.md`.",
        "",
        head,
        sep,
        row(
            "Repreguntas que resuelven la referencia (SC-006)",
            lambda s: ratio(s["follow_up_resolved"], s["follow_ups"]),
        ),
        row(
            "Repreguntas correctas (corrección 2)",
            lambda s: ratio(s["follow_up_correct"], s["follow_ups"]),
        ),
        row(
            "Corrección media en repreguntas (0–2)", lambda s: str(s["follow_up_correctness_mean"])
        ),
        row("Corrección media en la muestra (0–2)", lambda s: str(s["sample_correctness_mean"])),
        row(
            "Respuestas fieles en la muestra (persona)",
            lambda s: ratio(s["sample_faithful"], s["sample"]),
        ),
        row("Acuerdo persona–juez en fidelidad", lambda s: str(s["judge_human_agreement"])),
        row("Kappa persona–juez", lambda s: str(s["judge_human_kappa"])),
        row(
            "Fidelidad media del juez si la persona dice fiel",
            lambda s: str(s["judge_faithfulness_when_human_faithful"]),
        ),
        row(
            "Fidelidad media del juez si la persona dice no fiel",
            lambda s: str(s["judge_faithfulness_when_human_unfaithful"]),
        ),
        "",
        "El juez cuenta como «fiel» una respuesta con fidelidad 1,0 (todas las afirmaciones "
        "respaldadas), la misma definición que aplica la persona.",
        "",
        "**Acuerdo entre calificadores** (antes del consenso):",
        "",
        "| Criterio | Ítems | Acuerdo exacto | Kappa de Cohen |",
        "|---|---|---|---|",
        f"| Corrección | {agreement_['items']} | {agreement_['correctness']['exact']} | "
        f"{agreement_['correctness']['kappa']} "
        f"(ponderada {agreement_['correctness']['weighted_kappa']}) |",
        f"| Fidelidad | {agreement_['items']} | {agreement_['faithful']['exact']} | "
        f"{agreement_['faithful']['kappa']} |",
        f"| Resuelve la referencia | {agreement_['reference']['items']} | "
        f"{agreement_['reference']['exact']} | {agreement_['reference']['kappa']} |",
        "",
        SECTION_END,
    ]
    return "\n".join(lines)


def write_section(report_path: Path, section: str) -> None:
    text = report_path.read_text(encoding="utf-8") if report_path.is_file() else ""
    if SECTION_START in text and SECTION_END in text:
        before, rest = text.split(SECTION_START, 1)
        text = before + section + rest.split(SECTION_END, 1)[1]
    else:
        text = text.rstrip("\n") + "\n\n" + section + "\n"
    report_path.write_text(text, encoding="utf-8")


def merge_grades(
    run_path: Path,
    grade_paths: Sequence[Path],
    *,
    report_path: Path,
    consensus_path: Path | None = None,
    disagreements_path: Path | None = None,
    sample: int = DEFAULT_SAMPLE,
    seed: int = DEFAULT_SEED,
) -> dict[str, Any]:
    """Validate, measure agreement, consolidate and write the human grades."""
    if len(grade_paths) != 2:
        raise GradingError("merge necesita exactamente dos planillas (--grades a.csv b.csv).")
    payload = json.loads(run_path.read_text(encoding="utf-8"))
    salt = run_salt(payload)
    info = {
        item_id(salt, result["query_id"], variant): {
            "kind": kind,
            "variant": variant,
            "result": result,
        }
        for kind, variant, result in select_items(payload, sample=sample, seed=seed)
    }
    kinds = {item: row["kind"] for item, row in info.items()}
    first, second = (read_grades(path, kinds) for path in grade_paths)
    names = [path.stem.removeprefix("plantilla_") for path in grade_paths]
    stats = agreement(first, second)
    consensus = None
    if consensus_path is not None:
        consensus = {
            (raw.get("item") or "").strip(): {
                key: (raw.get(f"{key}_consenso") or "").strip() for key in GRADE_COLUMNS
            }
            for raw in read_csv(consensus_path)
        }
    final, unresolved, settled = consolidate(first, second, consensus)
    if unresolved:
        target = disagreements_path or run_path.parent / "calificacion_m2" / "desacuerdos.csv"
        write_disagreements(target, info, first, second, names, unresolved)
        return {"agreement": stats, "unresolved": unresolved, "disagreements": str(target)}
    for item, grade in final.items():
        info[item]["grade"] = grade
        info[item]["result"]["human"] = {
            "tipo": info[item]["kind"],
            "correccion": grade["correccion"],
            "fiel": grade["fiel"],
            "resuelve_referencia": grade.get("resuelve_referencia"),
        }
    human = {
        "run_id": salt,
        "graders": names,
        "consensus_items": settled,
        "agreement": stats,
        "summary": human_summary(info),
    }
    payload["human"] = human
    run_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_section(report_path, render_section(human))
    return {"agreement": stats, "unresolved": [], "human": human}


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m proyecto_modelos_lenguaje.module2_grading",
        description="Calificación humana a ciegas de la comparación cadena vs. agente (Módulo 2).",
    )
    sub = parser.add_subparsers(dest="command", required=True)
    export = sub.add_parser("export", help="Planillas CSV a ciegas, una por calificador.")
    export.add_argument("--run", default=DEFAULT_RUN)
    export.add_argument("--graders", nargs="+", required=True)
    export.add_argument("--out-dir", default=DEFAULT_GRADING_DIR)
    export.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    export.add_argument("--seed", type=int, default=DEFAULT_SEED)
    merge = sub.add_parser("merge", help="Une las dos planillas y escribe la calificación.")
    merge.add_argument("--run", default=DEFAULT_RUN)
    merge.add_argument("--report", default=DEFAULT_REPORT)
    merge.add_argument("--grades", nargs=2, required=True, metavar="CSV")
    merge.add_argument("--consensus")
    merge.add_argument("--disagreements")
    merge.add_argument("--sample", type=int, default=DEFAULT_SAMPLE)
    merge.add_argument("--seed", type=int, default=DEFAULT_SEED)
    return parser


def main(argv: Sequence[str] | None = None, *, project_root: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    try:
        if args.command == "export":
            payload = json.loads((root / args.run).read_text(encoding="utf-8"))
            for path in export_templates(
                payload, args.graders, root / args.out_dir, sample=args.sample, seed=args.seed
            ):
                print(f"Planilla: {path}")
            return 0
        result = merge_grades(
            root / args.run,
            [root / path for path in args.grades],
            report_path=root / args.report,
            consensus_path=root / args.consensus if args.consensus else None,
            disagreements_path=root / args.disagreements if args.disagreements else None,
            sample=args.sample,
            seed=args.seed,
        )
        print(json.dumps(result["agreement"], ensure_ascii=False, indent=2))
        if result["unresolved"]:
            print(
                f"{len(result['unresolved'])} desacuerdos sin consenso en "
                f"{result['disagreements']}: "
                "llenen las columnas *_consenso y repitan con --consensus.",
                file=sys.stderr,
            )
            return 3
        print(json.dumps(result["human"]["summary"], ensure_ascii=False, indent=2))
        return 0
    except (GradingError, OSError, KeyError, json.JSONDecodeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
