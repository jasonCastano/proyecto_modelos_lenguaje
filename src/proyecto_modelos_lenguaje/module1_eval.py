"""Evaluación reproducible del Módulo 1: 40 preguntas, línea base zero-shot vs. prompt final.

Ejecuta cada pregunta aprobada de ``docs/alcance.md`` con dos prompts versionados y registra lo
que se puede medir de forma automática (estado, citas, *fallback*, latencia y tokens). La
calificación de corrección, coherencia y alucinación es humana: el reporte deja esas columnas
vacías para que el equipo las complete, de modo que ningún resultado se invente (Principios I y V
de la constitución).

Uso::

    uv run python -m proyecto_modelos_lenguaje.module1_eval --fake         # sin red (humo)
    uv run python -m proyecto_modelos_lenguaje.module1_eval                # DeepSeek real
    uv run python -m proyecto_modelos_lenguaje.module1_eval --ids P01 P07  # subconjunto
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from langchain_core.language_models import BaseChatModel

from .config import PROJECT_ROOT
from .retrieval import EntityIndex, GoldUnit, RetrievalError, load_entity_index, load_gold_units
from .tasks import (
    PromptTemplate,
    TaskError,
    TaskResult,
    _build_model,
    _resolve_gold_dir,
    answer_question,
    load_prompt,
    load_task_config,
)

DEFAULT_BANK = "docs/alcance.md"
DEFAULT_REPORT = "docs/evaluacion_modulo1.md"
DEFAULT_JSON = "docs/evaluacion_modulo1.json"
VARIANTS: dict[str, str | None] = {
    "zero_shot": "prompts/qa_zero_shot.md",
    "final": None,  # prompts/qa.md
}
ROW_PATTERN = re.compile(
    r"^\|\s*(P\d{2})\s*\|\s*(.+?)\s*\|\s*([A-Z, ]+?)\s*\|\s*([A-Z0-9\-, ]+?)\s*\|"
    r"\s*(.*?)\s*\|\s*([A-Z, ]+?)\s*\|\s*(.+?)\s*\|\s*$"
)


@dataclass(frozen=True, slots=True)
class BankQuestion:
    """One approved question of the scope bank."""

    question_id: str
    question: str
    kinds: tuple[str, ...]
    items: tuple[str, ...]
    expected: tuple[str, ...]

    @property
    def expects_fallback(self) -> bool:
        return self.expected == ("X",)


@dataclass(slots=True)
class EvalRow:
    """Automatic observations for one question and one prompt variant."""

    question_id: str
    variant: str
    question: str
    expected: str
    status: str
    answer: str
    citations: list[str]
    sources: list[str]
    fallback: bool
    latency_seconds: float
    input_tokens: int
    output_tokens: int
    prompt_version: str
    model: str
    error: str | None = None
    # Columnas humanas: se completan a mano en el reporte.
    human: dict[str, str] = field(default_factory=dict)

    @property
    def fallback_matches(self) -> bool | None:
        """Whether the fallback behaviour matches the expected result code."""
        codes = set(self.expected.split(","))
        if self.status == "error" or ("X" in codes and len(codes) > 1):
            return None  # error, o se aceptan ambas conductas (p. ej. «P, X»)
        return self.fallback == ("X" in codes)


def _split(value: str) -> tuple[str, ...]:
    return tuple(part.strip() for part in value.split(",") if part.strip())


def parse_question_bank(path: Path) -> list[BankQuestion]:
    """Parse the approved questions (P01–P40) from the scope document tables."""
    questions: dict[str, BankQuestion] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        match = ROW_PATTERN.match(line)
        if match is None or "Aprobada" not in match.group(7):
            continue
        qid = match.group(1)
        questions[qid] = BankQuestion(
            question_id=qid,
            question=match.group(2),
            kinds=_split(match.group(3)),
            items=_split(match.group(4)),
            expected=_split(match.group(6)),
        )
    return [questions[key] for key in sorted(questions)]


def _row(question: BankQuestion, variant: str, result: TaskResult) -> EvalRow:
    return EvalRow(
        question_id=question.question_id,
        variant=variant,
        question=question.question,
        expected=",".join(question.expected),
        status=result.status,
        answer=result.answer,
        citations=[citation.label for citation in result.citations],
        sources=sorted({citation.url for citation in result.citations if citation.url}),
        fallback=result.fallback,
        latency_seconds=result.latency_seconds,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        prompt_version=result.prompt_version,
        model=result.model,
        error=result.error,
    )


def run_evaluation(
    questions: Sequence[BankQuestion],
    *,
    model: BaseChatModel,
    prompts: dict[str, PromptTemplate],
    units: Sequence[GoldUnit],
    entity_index: EntityIndex,
    project_root: Path,
    progress: Callable[[str], None] | None = None,
) -> list[EvalRow]:
    """Answer every question with every prompt variant; errors are recorded, never hidden."""
    config = load_task_config(project_root=project_root)
    rows: list[EvalRow] = []
    for question in questions:
        for variant, template in prompts.items():
            try:
                result = answer_question(
                    question.question,
                    model=model,
                    config=config,
                    prompt=template,
                    units=units,
                    entity_index=entity_index,
                    project_root=project_root,
                )
                row = _row(question, variant, result)
            except TaskError as exc:
                row = EvalRow(
                    question_id=question.question_id,
                    variant=variant,
                    question=question.question,
                    expected=",".join(question.expected),
                    status="error",
                    answer="",
                    citations=[],
                    sources=[],
                    fallback=False,
                    latency_seconds=0.0,
                    input_tokens=0,
                    output_tokens=0,
                    prompt_version=template.version,
                    model=getattr(model, "model_name", "") or type(model).__name__,
                    error=exc.code,
                )
            rows.append(row)
            if progress is not None:
                progress(f"{row.question_id} {variant}: {row.status}")
    return rows


def summarize(rows: Sequence[EvalRow]) -> dict[str, dict[str, Any]]:
    """Aggregate the automatic metrics per variant."""
    summary: dict[str, dict[str, Any]] = {}
    for variant in dict.fromkeys(row.variant for row in rows):
        subset = [row for row in rows if row.variant == variant]
        latencies = [row.latency_seconds for row in subset if row.status != "error"]
        matches = [row.fallback_matches for row in subset if row.fallback_matches is not None]
        summary[variant] = {
            "questions": len(subset),
            "ok": sum(row.status == "ok" for row in subset),
            "review": sum(row.status == "review" for row in subset),
            "fallback": sum(row.fallback for row in subset),
            "error": sum(row.status == "error" for row in subset),
            "with_citation": sum(bool(row.citations) for row in subset),
            "fallback_agreement": round(sum(matches) / len(matches), 3) if matches else None,
            "latency_mean_s": round(statistics.fmean(latencies), 3) if latencies else None,
            "latency_stdev_s": round(statistics.stdev(latencies), 3)
            if len(latencies) > 1
            else None,
            "input_tokens": sum(row.input_tokens for row in subset),
            "output_tokens": sum(row.output_tokens for row in subset),
        }
    return summary


def _cell(text: str, limit: int = 160) -> str:
    flat = " ".join(text.split()).replace("|", "\\|")
    return flat if len(flat) <= limit else flat[: limit - 1] + "…"


def render_report(
    rows: Sequence[EvalRow], summary: dict[str, dict[str, Any]], meta: dict[str, Any]
) -> str:
    """Render the Markdown report with automatic metrics and empty human-grading columns."""
    lines = [
        "# Evaluación del Módulo 1 — 40 preguntas",
        "",
        f"**Ejecución**: `{meta['run_id']}` · **Fecha (UTC)**: {meta['created_at']} · "
        f"**Modelo**: `{meta['model']}` · **Modo**: {meta['mode']}",
        "",
        f"**Comando**: `{meta['command']}`",
        "",
        "Las métricas automáticas salen de la ejecución registrada en "
        f"`{meta['json_path']}`. Las columnas **Corrección** (0 incorrecta · 1 parcial · "
        "2 correcta), **Coherencia** (1–5) y **Alucinación** (sí/no) las califica el equipo a "
        "mano; mientras estén vacías, el informe no puede citar esas cifras.",
        "",
        "## Métricas automáticas por variante",
        "",
        "| Variante | Preguntas | ok | review | fallback | error | Con cita | Acierto de fallback "
        "| Latencia media (s) | Desv. (s) | Tokens entrada | Tokens salida |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for variant, data in summary.items():
        lines.append(
            f"| {variant} | {data['questions']} | {data['ok']} | {data['review']} | "
            f"{data['fallback']} | {data['error']} | {data['with_citation']} | "
            f"{data['fallback_agreement']} | {data['latency_mean_s']} | "
            f"{data['latency_stdev_s']} | "
            f"{data['input_tokens']} | {data['output_tokens']} |"
        )
    lines += [
        "",
        "*Acierto de fallback*: proporción de respuestas cuyo *fallback* coincide con lo "
        "esperado en el alcance (`X` debe declarar falta de evidencia; el resto debe responder).",
        "",
        "## Resultados por pregunta",
        "",
        "| ID | Variante | Esperado | Estado | Citas | Respuesta | Corrección | Coherencia "
        "| Alucinación |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for row in rows:
        citations = " ".join(row.citations) or "—"
        answer = _cell(row.answer) if row.answer else f"error: {row.error}"
        lines.append(
            f"| {row.question_id} | {row.variant} | {row.expected} | {row.status} | {citations} | "
            f"{answer} |  |  |  |"
        )
    lines += [
        "",
        "## Análisis de errores",
        "",
        "Pendiente de la calificación humana (M1-09): clasificar los fallos en recuperación, "
        "redacción, cita inválida, alucinación o falta de corpus, y registrar los ajustes en "
        "`docs/prompt_log.md`.",
        "",
    ]
    return "\n".join(lines)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m proyecto_modelos_lenguaje.module1_eval",
        description="Evalúa las 40 preguntas del Módulo 1 con línea base zero-shot y prompt final.",
    )
    parser.add_argument("--bank", default=DEFAULT_BANK, help="Banco de preguntas (Markdown).")
    parser.add_argument("--out", default=DEFAULT_REPORT, help="Reporte Markdown de salida.")
    parser.add_argument("--json-out", default=DEFAULT_JSON, help="Registro JSON de la ejecución.")
    parser.add_argument("--ids", nargs="*", help="Evalúa solo estos IDs (p. ej. P01 P07).")
    parser.add_argument("--limit", type=int, help="Evalúa solo las primeras N preguntas.")
    parser.add_argument("--fake", action="store_true", help="Modelo guionado, sin red ni clave.")
    parser.add_argument("--gold-dir", help="Directorio de la capa oro (por defecto data/gold).")
    parser.add_argument("--run-id", help="Identificador de la ejecución.")
    return parser


def main(argv: Sequence[str] | None = None, *, project_root: Path | None = None) -> int:
    args = build_parser().parse_args(argv)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    questions = parse_question_bank(root / args.bank)
    if args.ids:
        wanted = {qid.upper() for qid in args.ids}
        questions = [question for question in questions if question.question_id in wanted]
    if args.limit:
        questions = questions[: args.limit]
    if not questions:
        print("No hay preguntas que evaluar.", file=sys.stderr)
        return 2
    try:
        gold_dir = _resolve_gold_dir(args.gold_dir, root)
        units = load_gold_units(gold_dir)
        try:
            entity_index = load_entity_index(gold_dir)
        except RetrievalError:
            entity_index = EntityIndex()
        prompts = {
            name: load_prompt("qa", path=path, project_root=root) for name, path in VARIANTS.items()
        }
        model = _build_model(args.fake, "qa", root)
    except (TaskError, RetrievalError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1

    created = datetime.now(UTC).replace(microsecond=0)
    run_id = args.run_id or created.strftime("m1-eval-%Y%m%dT%H%M%SZ")
    rows = run_evaluation(
        questions,
        model=model,
        prompts=prompts,
        units=units,
        entity_index=entity_index,
        project_root=root,
        progress=lambda message: print(message, file=sys.stderr),
    )
    summary = summarize(rows)
    model_name = next((row.model for row in rows if row.model), "")
    meta = {
        "run_id": run_id,
        "created_at": created.isoformat(),
        "model": model_name,
        "mode": "demo (modelo guionado)" if args.fake else "real",
        "command": "uv run python -m proyecto_modelos_lenguaje.module1_eval "
        + " ".join(argv if argv is not None else sys.argv[1:]),
        "json_path": args.json_out,
        "prompts": {name: template.to_dict() for name, template in prompts.items()},
    }
    payload = {"meta": meta, "summary": summary, "rows": [_as_dict(row) for row in rows]}
    json_path = root / args.json_out
    json_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    report_path = root / args.out
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(render_report(rows, summary, meta), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


def _as_dict(row: EvalRow) -> dict[str, Any]:
    data = {name: getattr(row, name) for name in row.__dataclass_fields__}
    data["fallback_matches"] = row.fallback_matches
    return data


if __name__ == "__main__":
    raise SystemExit(main())
