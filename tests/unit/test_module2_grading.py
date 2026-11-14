"""Pruebas offline de la calificación humana a ciegas del Módulo 2 (cadena vs. agente)."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.module1_grading import GradingError
from proyecto_modelos_lenguaje.module2_grading import (
    INSTRUCTIONS,
    SECTION_START,
    export_templates,
    main,
    parse_grade,
    select_items,
)


def _result(qid: str, kind: str, *, fallback: bool = False, faith: float | None = 1.0) -> dict:
    return {
        "query_id": qid,
        "type": kind,
        "question": f"Pregunta {qid}",
        "answer": f"Respuesta {qid} [U1].",
        "fallback": fallback,
        "contexts": [f"[U1] Fragmento de {qid}."],
        "follow_up_of": "q01" if kind == "follow_up" else None,
        "previous_question": "Pregunta q01" if kind == "follow_up" else "",
        "previous_answer": "Respuesta q01 [U1]." if kind == "follow_up" else "",
        "judge": None if faith is None else {"faithfulness": faith, "answer_relevancy": 0.9},
    }


def _payload() -> dict:
    def results(faith: float) -> list[dict]:
        return [
            _result("q01", "documental", faith=faith),
            _result("q02", "structured", faith=faith),
            _result("q03", "mixed", faith=faith),
            _result("q04", "documental", fallback=True),
            _result("q05", "greeting", faith=None),
            _result("q06", "follow_up", faith=None),
            _result("q07", "follow_up", faith=None),
        ]

    return {
        "meta": {"run_id": "variants-test"},
        "variants": [
            {"variant": "chain", "results": results(1.0)},
            {"variant": "agent", "results": results(0.5)},
        ],
    }


@pytest.fixture
def run(tmp_path: Path) -> Path:
    path = tmp_path / "variantes.json"
    path.write_text(json.dumps(_payload()), encoding="utf-8")
    return path


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _write(path: Path, rows: list[dict[str, str]]) -> None:
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def _fill(path: Path, grade: Callable[[dict[str, str]], tuple[str, str, str]]) -> None:
    rows = _read(path)
    for row in rows:
        row["correccion"], row["fiel"], ref = grade(row)
        if row["tipo"] == "repregunta":
            row["resuelve_referencia"] = ref
    _write(path, rows)


def test_select_items_takes_every_follow_up_and_a_paired_factual_sample() -> None:
    items = select_items(_payload(), sample=2, seed=7)

    follow = [(v, r["query_id"]) for kind, v, r in items if kind == "repregunta"]
    sample = [(v, r["query_id"]) for kind, v, r in items if kind == "muestra"]
    assert sorted(follow) == sorted(
        [("chain", "q06"), ("agent", "q06"), ("chain", "q07"), ("agent", "q07")]
    )
    assert len(sample) == 4
    sampled = {qid for _, qid in sample}
    assert len(sampled) == 2 and sampled <= {"q01", "q02", "q03"}  # sin abstenciones ni saludos
    assert {v for v, _ in sample} == {"chain", "agent"}  # misma pregunta en ambas variantes


def test_export_is_blind_and_marks_reference_only_for_follow_ups(tmp_path: Path) -> None:
    out = tmp_path / "calif"
    paths = export_templates(_payload(), ["ana", "beto"], out, sample=2)
    ana, beto = _read(paths[0]), _read(paths[1])

    assert len(ana) == len(beto) == 8
    assert [r["item"] for r in ana] != [r["item"] for r in beto]
    assert not {"variant", "variante"} & set(ana[0])
    assert not any(v in {"chain", "agent"} for row in ana for v in row.values())
    follow = [r for r in ana if r["tipo"] == "repregunta"]
    assert all(
        r["pregunta_previa"] == "Pregunta q01" and r["resuelve_referencia"] == "" for r in follow
    )
    assert all(r["resuelve_referencia"] == "na" for r in ana if r["tipo"] == "muestra")
    assert all(r["fragmentos"].startswith("[U1]") for r in ana)
    assert (out / "INSTRUCCIONES.md").read_text(encoding="utf-8") == INSTRUCTIONS


def test_export_requires_contexts_in_the_record(tmp_path: Path) -> None:
    payload = _payload()
    for variant in payload["variants"]:
        for result in variant["results"]:
            result.pop("contexts")
    with pytest.raises(GradingError, match="contexts"):
        export_templates(payload, ["ana", "beto"], tmp_path)


def test_parse_grade_requires_reference_only_in_follow_ups() -> None:
    sample = parse_grade(
        {"correccion": "2", "fiel": "Sí", "resuelve_referencia": "na"}, "muestra", "x"
    )
    assert sample.reference is None and sample.faithful is True
    with pytest.raises(GradingError, match="resuelve_referencia"):
        parse_grade({"correccion": "2", "fiel": "no", "resuelve_referencia": ""}, "repregunta", "x")
    with pytest.raises(GradingError, match="correccion"):
        parse_grade({"correccion": "5", "fiel": "no"}, "muestra", "x")


def test_merge_needs_consensus_then_writes_human_metrics_and_judge_agreement(
    run: Path, tmp_path: Path
) -> None:
    out = tmp_path / "calif"
    assert (
        main(
            [
                "export",
                "--run",
                str(run),
                "--graders",
                "ana",
                "beto",
                "--out-dir",
                str(out),
                "--sample",
                "2",
            ]
        )
        == 0
    )
    # Ana: todo fiel y resuelto; Beto discrepa en la referencia de q07
    _fill(out / "plantilla_ana.csv", lambda row: ("2", "si", "si"))
    _fill(
        out / "plantilla_beto.csv",
        lambda row: ("2", "si", "no" if row["consulta_id"] == "q07" else "si"),
    )
    report = tmp_path / "eval.md"
    report.write_text("# Evaluación\n", encoding="utf-8")
    base = [
        "merge",
        "--run",
        str(run),
        "--report",
        str(report),
        "--grades",
        str(out / "plantilla_ana.csv"),
        str(out / "plantilla_beto.csv"),
        "--sample",
        "2",
        "--disagreements",
        str(out / "desacuerdos.csv"),
    ]

    assert main(base) == 3
    pending = _read(out / "desacuerdos.csv")
    assert {row["consulta_id"] for row in pending} == {"q07"} and len(pending) == 2
    assert "human" not in json.loads(run.read_text(encoding="utf-8"))

    for row in pending:
        row["resuelve_referencia_consenso"] = "no"
    _write(out / "consenso.csv", pending)
    assert main([*base, "--consensus", str(out / "consenso.csv")]) == 0

    payload = json.loads(run.read_text(encoding="utf-8"))
    summary = payload["human"]["summary"]
    assert payload["human"]["consensus_items"] == 2
    assert summary["chain"]["follow_up_resolved"] == 1 and summary["chain"]["follow_ups"] == 2
    # Persona: todo fiel. Juez: cadena 1,0 (coincide) y agente 0,5 (no coincide)
    assert summary["chain"]["judge_human_agreement"] == 1.0
    assert summary["agent"]["judge_human_agreement"] == 0.0
    assert summary["agent"]["judge_faithfulness_when_human_faithful"] == 0.5
    text = report.read_text(encoding="utf-8")
    assert text.startswith("# Evaluación") and SECTION_START in text
    assert "| Repreguntas que resuelven la referencia (SC-006) | 1/2 | 1/2 |" in text


def test_guide_examples_are_not_items_of_the_labeled_set() -> None:
    queries = (PROJECT_ROOT / "tests" / "fixtures" / "rag" / "module2_queries.jsonl").read_text(
        encoding="utf-8"
    )
    asked = [
        line.split("«")[1].split("»")[0]
        for line in INSTRUCTIONS.splitlines()
        if "**Pregunta**" in line or "**Repregunta**" in line
    ]
    assert len(asked) == 4
    assert not any(question in queries for question in asked)
    assert "merge \\\n" in INSTRUCTIONS
