"""Pruebas offline de la calificación humana a ciegas y de las repeticiones del Módulo 1."""

from __future__ import annotations

import csv
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje import module1_eval
from proyecto_modelos_lenguaje.module1_grading import (
    Grade,
    GradingError,
    aggregate_runs,
    agreement,
    cohen_kappa,
    consolidate,
    item_id,
    main,
    read_grades,
)
from tests.tasks_helpers import write_gold


@pytest.fixture
def run(tmp_path: Path) -> dict[str, Path]:
    """Ejecución real del evaluador con el modelo guionado (3 preguntas × 2 variantes)."""
    gold = write_gold(tmp_path)
    paths = {"gold": gold, "json": tmp_path / "eval.json", "md": tmp_path / "eval.md"}
    code = module1_eval.main(
        [
            "--fake",
            "--limit",
            "3",
            "--gold-dir",
            str(gold),
            "--out",
            str(paths["md"]),
            "--json-out",
            str(paths["json"]),
            "--run-id",
            "test-run",
        ]
    )
    assert code == 0
    return paths


def _export(run: dict[str, Path], tmp_path: Path) -> Path:
    out = tmp_path / "calif"
    code = main(
        [
            "export",
            "--run",
            str(run["json"]),
            "--graders",
            "ana",
            "beto",
            "--out-dir",
            str(out),
            "--gold-dir",
            str(run["gold"]),
        ]
    )
    assert code == 0
    return out


def _read(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        return list(csv.DictReader(handle))


def _fill(path: Path, grade: Callable[[dict[str, str]], tuple[str, str, str]]) -> None:
    rows = _read(path)
    for row in rows:
        row["correccion"], row["coherencia"], row["alucinacion"] = grade(row)
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def test_export_is_blind_shuffled_and_shows_cited_fragments(
    run: dict[str, Path], tmp_path: Path
) -> None:
    out = _export(run, tmp_path)
    ana, beto = _read(out / "plantilla_ana.csv"), _read(out / "plantilla_beto.csv")
    payload = json.loads(run["json"].read_text(encoding="utf-8"))

    assert len(ana) == len(beto) == 6
    assert {row["item"] for row in ana} == {row["item"] for row in beto}
    assert [row["item"] for row in ana] != [row["item"] for row in beto]  # orden distinto
    header = set(ana[0])
    assert "variante" not in header and "variant" not in header
    assert not any("zero_shot" in value or value == "final" for r in ana for value in r.values())
    ids = {item_id("test-run", r["question_id"], r["variant"]) for r in payload["rows"]}
    assert {row["item"] for row in ana} == ids
    cited = [row for row in ana if row["citas"]]
    assert cited and all(row["fragmentos_citados"].startswith("[U") for row in cited)
    assert all(row["fuente_esperada"] for row in ana)
    assert (out / "INSTRUCCIONES.md").read_text(encoding="utf-8").startswith("# Instrucciones")


def test_read_grades_reports_invalid_and_missing_items(
    run: dict[str, Path], tmp_path: Path
) -> None:
    out = _export(run, tmp_path)
    path = out / "plantilla_ana.csv"
    rows = _read(path)
    rows[0].update(correccion="3", coherencia="4", alucinacion="no")
    rows = rows[:-1]  # falta un ítem
    with path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    payload = json.loads(run["json"].read_text(encoding="utf-8"))
    expected = {item_id("test-run", r["question_id"], r["variant"]) for r in payload["rows"]}

    with pytest.raises(GradingError) as error:
        read_grades(path, expected)

    message = str(error.value)
    assert "correccion debe ser 0, 1 o 2" in message
    assert "faltan 1 ítems" in message


def test_kappa_matches_reference_values() -> None:
    # Acuerdo perfecto, acuerdo al azar y un caso de libro (kappa = 0,4)
    assert cohen_kappa([0, 1, 2, 2], [0, 1, 2, 2]) == 1.0
    assert cohen_kappa([True, False, True, False], [True, True, False, False]) == 0.0
    first = ["si"] * 20 + ["si"] * 5 + ["no"] * 10 + ["no"] * 15
    second = ["si"] * 20 + ["no"] * 5 + ["si"] * 10 + ["no"] * 15
    assert cohen_kappa(first, second) == 0.4
    weighted = cohen_kappa([0, 1, 2], [0, 2, 2], weights="quadratic")
    assert weighted > cohen_kappa([0, 1, 2], [0, 2, 2])


def test_consolidate_averages_coherence_and_flags_disagreements() -> None:
    first = {"a": Grade(2, 4, False), "b": Grade(1, 3, False), "c": Grade(0, 2, True)}
    second = {"a": Grade(2, 5, False), "b": Grade(2, 3, False), "c": Grade(0, 2, False)}

    final, unresolved, settled = consolidate(first, second)
    assert final == {"a": {"correccion": "2", "alucinacion": "no", "coherencia": "4.5"}}
    assert unresolved == ["b", "c"] and settled == 0

    consensus = {
        "b": {"correccion": "1", "alucinacion": "", "coherencia": ""},
        "c": {"correccion": "", "alucinacion": "sí", "coherencia": "3"},
    }
    final, unresolved, settled = consolidate(first, second, consensus)
    assert unresolved == [] and settled == 2
    assert final["b"]["correccion"] == "1"
    assert final["c"] == {"correccion": "0", "alucinacion": "sí", "coherencia": "3"}

    stats = agreement(first, second)
    assert stats["correctness"]["exact"] == round(2 / 3, 3)
    assert stats["coherence"]["within_one"] == 1.0


def test_merge_requires_consensus_then_fills_json_and_report(
    run: dict[str, Path], tmp_path: Path
) -> None:
    out = _export(run, tmp_path)
    _fill(out / "plantilla_ana.csv", lambda row: ("2", "4", "no"))
    _fill(
        out / "plantilla_beto.csv",
        lambda row: ("1" if row["pregunta_id"] == "P01" else "2", "5", "no"),
    )
    grades = [str(out / "plantilla_ana.csv"), str(out / "plantilla_beto.csv")]
    base = ["merge", "--run", str(run["json"]), "--report", str(run["md"]), "--grades", *grades]

    # 1) Desacuerdo en P01 (las dos variantes): pide consenso y no toca el registro
    assert main(base) == 3
    assert "human" not in json.loads(run["json"].read_text(encoding="utf-8"))
    pending = _read(run["json"].parent / "desacuerdos.csv")
    assert [row["pregunta_id"] for row in pending] == ["P01", "P01"]

    # 2) Con el consenso, escribe la calificación y llena el reporte
    for row in pending:
        row["correccion_consenso"] = "2"
    with (out / "consenso.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(pending[0]))
        writer.writeheader()
        writer.writerows(pending)
    assert main([*base, "--consensus", str(out / "consenso.csv")]) == 0

    payload = json.loads(run["json"].read_text(encoding="utf-8"))
    human = payload["human"]
    assert human["graders"] == ["ana", "beto"] and human["consensus_items"] == 2
    assert human["summary"]["final"]["correctness_mean"] == 2.0
    assert human["summary"]["final"]["coherence_mean"] == 4.5
    assert all(row["human"]["correccion"] == "2" for row in payload["rows"])
    report = run["md"].read_text(encoding="utf-8")
    assert "## Calificación humana" in report and "Kappa de Cohen" in report
    assert "| 2 | 4.5 | no |" in report
    assert "Ninguna respuesta quedó con corrección 0" in report


def test_aggregate_reports_mean_and_stdev(run: dict[str, Path], tmp_path: Path) -> None:
    first = json.loads(run["json"].read_text(encoding="utf-8"))
    second = json.loads(json.dumps(first))
    second["meta"]["run_id"] = "test-run-2"
    second["summary"]["final"]["latency_mean_s"] = first["summary"]["final"]["latency_mean_s"] + 2
    second["rows"][1]["fallback"] = not second["rows"][1]["fallback"]
    other = tmp_path / "eval2.json"
    other.write_text(json.dumps(second), encoding="utf-8")

    result = aggregate_runs([first, second])
    latency = result["variants"]["final"]["latency_mean_s"]
    assert latency["stdev"] == round(2**0.5, 3)
    assert result["variants"]["final"]["unstable_fallback"] == [second["rows"][1]["question_id"]]

    out = tmp_path / "rep.md"
    code = main(
        [
            "aggregate",
            "--runs",
            str(run["json"]),
            str(other),
            "--out",
            str(out),
            "--json-out",
            str(tmp_path / "rep.json"),
        ]
    )
    assert code == 0
    assert "± " in out.read_text(encoding="utf-8")
    with pytest.raises(GradingError):
        aggregate_runs([first])
