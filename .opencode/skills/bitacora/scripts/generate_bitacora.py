#!/usr/bin/env python3
"""Generate a dated project log (bitácora) for the Manuelita RAG project.

The script is intentionally dependency-free (standard library only) and is
meant to be run from the repository root through ``uv run python``.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

CHECK_ICONS = {"done": "✅", "partial": "🟡", "pending": "❌", "unknown": "⚠️"}


@dataclass
class Check:
    key: str
    label: str
    area: str
    status: str
    evidence: str
    action: str = ""
    critical: bool = False


@dataclass(frozen=True)
class TaskStep:
    id: str
    stage: int
    title: str
    depends_on: tuple[str, ...]
    deliverable: str
    acceptance: str
    checks: tuple[str, ...]
    owner: str
    estimate: str


@dataclass(frozen=True)
class QualityGate:
    id: str
    after: str
    criterion: str


CASCADE_STEPS: tuple[TaskStep, ...] = (
    TaskStep(
        "M1-01",
        1,
        "Definir alcance y las 20+ preguntas",
        (),
        "docs/alcance.md",
        "6–8 categorías; 20+ preguntas con ID, categoría, fuente esperada y mapeo a los 24 ítems.",
        ("alcance",),
        "Ambos",
        "1,5 h",
    ),
    TaskStep(
        "M1-02",
        2,
        "Crear la entrada canónica de scraping",
        (),
        "scripts/scrape_empresa.py",
        "`uv run python scripts/scrape_empresa.py --help` funciona y delega en run_campaign.py.",
        ("pipeline_entry",),
        "Jason",
        "0,5 h",
    ),
    TaskStep(
        "M1-03",
        2,
        "Documentar la ficha de datos",
        ("M1-02",),
        "docs/data_card.md",
        "Cifras trazables a reportes/catálogo; fuentes, licencias, fechas y limitaciones.",
        ("data_card",),
        "Jason",
        "1 h",
    ),
    TaskStep(
        "M1-04",
        3,
        "Configurar modelo y entorno",
        ("M1-01",),
        "config/llm.toml + .env.example + src/proyecto_modelos_lenguaje/llm.py",
        "Modelo, temperatura y límites declarados; clave solo por entorno; adaptador offline.",
        ("llm",),
        "Roberto",
        "1 h",
    ),
    TaskStep(
        "M1-05",
        3,
        "Implementar Resumen, FAQ y Q&A con LangChain",
        ("M1-04",),
        "prompts/*.md + src/proyecto_modelos_lenguaje/tasks.py",
        "Tres tareas con citas y fallback; Q&A sin embeddings y con 'no hay evidencia'.",
        ("llm",),
        "Roberto",
        "3 h",
    ),
    TaskStep(
        "M1-06",
        3,
        "Registrar prompts, parámetros y resultados",
        ("M1-05",),
        "docs/prompt_log.md",
        "Versiones, baseline zero-shot y variante final; salidas observadas, no inventadas.",
        ("prompt_log",),
        "Roberto",
        "1 h",
    ),
    TaskStep(
        "M1-07",
        4,
        "Implementar la app Streamlit",
        ("M1-05", "M1-06"),
        "app.py",
        "Resumen, FAQ y Q&A; citas; panel de URLs/tokens/descartes; errores y timeout controlados.",
        ("app", "ui_metrics"),
        "Roberto",
        "4 h",
    ),
    TaskStep(
        "M1-08",
        5,
        "Evaluar las 20 preguntas",
        ("M1-07",),
        "docs/evaluacion_modulo1.md",
        "20 filas con baseline y final, fuente, corrección, coherencia, alucinación y métricas.",
        ("evaluation",),
        "Ambos",
        "2,5 h",
    ),
    TaskStep(
        "M1-09",
        5,
        "Ajustar prompts con evidencia",
        ("M1-08",),
        "docs/prompt_log.md actualizado",
        "Fallos clasificados; cambios justificados con una nueva muestra ejecutada.",
        ("prompt_log", "evaluation"),
        "Ambos",
        "1 h",
    ),
    TaskStep(
        "M1-10",
        6,
        "Redactar el informe del Módulo 1",
        ("M1-09", "M1-03"),
        "docs/informe_modulo1.md",
        "Cinco secciones: problema, solución, datos, modelado y resultados.",
        ("report",),
        "Ambos",
        "2 h",
    ),
    TaskStep(
        "M1-11",
        6,
        "Escribir el guion de demo 12+3",
        ("M1-10", "M1-07"),
        "docs/demo.md",
        "Pasos cronometrados, qué mostrar en app/repo/IDE y plan B si falla el modelo.",
        ("demo",),
        "Ambos",
        "1 h",
    ),
    TaskStep(
        "M1-12",
        6,
        "Actualizar README y capturas",
        ("M1-11",),
        "README.md y capturas",
        "Comandos reales, estado del Módulo 1, capturas y limitaciones.",
        ("readme",),
        "Ambos",
        "0,5 h",
    ),
    TaskStep(
        "M1-13",
        7,
        "Añadir pruebas y CI",
        ("M1-12",),
        "tests/ y .github/workflows/ci.yml",
        "Pruebas de tareas con LLM falso, citas/fallback, importación de app; Ruff y CI verdes.",
        ("tests", "ruff", "ci"),
        "Ambos",
        "1,5 h",
    ),
    TaskStep(
        "M1-14",
        7,
        "Publicar por PR",
        ("M1-13",),
        "Rama feat/modulo1-app y PR",
        "PR con cambios, pruebas, capturas, riesgos y CI verde; revisión cruzada.",
        ("prs",),
        "Ambos",
        "1 h",
    ),
    TaskStep(
        "M1-15",
        7,
        "Etiquetar y ensayar",
        ("M1-14",),
        "Tag v0.1.0-modulo1",
        "Tag sobre main con CI verde y ensayo cronometrado 12+3 sin diapositivas.",
        ("tag",),
        "Ambos",
        "1 h",
    ),
)

QUALITY_GATES: tuple[QualityGate, ...] = (
    QualityGate("G1", "M1-01", "Preguntas revisadas y aprobadas por ambos."),
    QualityGate("G2", "M1-03", "Wrapper canónico y ficha de datos reproducibles."),
    QualityGate("G3", "M1-06", "Tres tareas LangChain con citas y fallback."),
    QualityGate("G4", "M1-07", "App ejecutable con tres funcionalidades y panel."),
    QualityGate("G5", "M1-09", "Evaluación completa y prompts ajustados con evidencia."),
    QualityGate("G6", "M1-12", "Informe, demo y README coherentes."),
    QualityGate("G7", "M1-15", "Tag publicado y demo ensayada."),
)

CASCADE_ICONS = {
    "done": "✅",
    "partial": "🟡",
    "pending": "❌",
    "blocked": "⛔",
}
CASCADE_LABELS = {
    "done": "completada",
    "partial": "parcial",
    "pending": "pendiente",
    "blocked": "bloqueada",
}


def find_project_root(start: Path) -> Path:
    for candidate in [start, *start.parents]:
        if (candidate / "CONSTITUTION.md").is_file() and (candidate / "pyproject.toml").is_file():
            return candidate
    return Path.cwd()


ROOT = find_project_root(Path(__file__).resolve().parent)


def run(command: list[str], *, timeout: int = 120) -> tuple[int, str, str]:
    env = {**os.environ, "GIT_TERMINAL_PROMPT": "0"}
    try:
        process = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
            env=env,
        )
        return process.returncode, process.stdout.strip(), process.stderr.strip()
    except FileNotFoundError:
        return 127, "", f"command not found: {command[0]}"
    except subprocess.TimeoutExpired:
        return 124, "", f"timeout after {timeout}s: {' '.join(command)}"


def git(*args: str, timeout: int = 30) -> tuple[int, str, str]:
    return run(["git", *args], timeout=timeout)


def gh_json(*args: str, timeout: int = 30) -> tuple[Any | None, str]:
    code, out, err = run(["gh", *args], timeout=timeout)
    if code != 0:
        return None, err or out
    try:
        return json.loads(out), ""
    except json.JSONDecodeError as exc:
        return None, f"invalid gh JSON: {exc}"


def read(path: str) -> str:
    candidate = ROOT / path
    if not candidate.is_file():
        return ""
    return candidate.read_text(encoding="utf-8", errors="replace")


def constitution_context() -> dict[str, str]:
    text = read("CONSTITUTION.md")
    version = re.search(r"\*\*Versión\*\*:\s*([0-9.]+)", text)
    ratified = re.search(r"\*\*Ratificada\*\*:\s*(\d{4}-\d{2}-\d{2})", text)
    amended = re.search(r"\*\*Última enmienda\*\*:\s*(\d{4}-\d{2}-\d{2})", text)
    return {
        "version": version.group(1) if version else "desconocida",
        "ratified": ratified.group(1) if ratified else "desconocida",
        "amended": amended.group(1) if amended else "desconocida",
        "text": text,
    }


def git_state(*, no_fetch: bool) -> dict[str, Any]:
    state: dict[str, Any] = {}
    state["branch"] = git("rev-parse", "--abbrev-ref", "HEAD")[1] or "(sin rama)"
    state["head"] = git("rev-parse", "--short", "HEAD")[1] or "(sin commit)"
    state["head_full"] = git("rev-parse", "HEAD")[1]
    state["subject"] = git("log", "-1", "--format=%s")[1]
    state["committed_at"] = git("log", "-1", "--format=%cI")[1]
    state["remote_url"] = git("remote", "get-url", "origin")[1] or "(sin remoto)"
    status_code, status_out, _ = git("status", "--porcelain")
    raw_status = status_out.splitlines() if status_code == 0 and status_out else []

    def _is_log_path(line: str) -> bool:
        parts = line.strip().split(maxsplit=1)
        path = parts[1] if len(parts) > 1 else ""
        return path == "bitacora/" or path.startswith("bitacora/")

    state["dirty_lines"] = [line for line in raw_status if not _is_log_path(line)]
    state["dirty"] = bool(state["dirty_lines"])
    state["recent_commits"] = (git("log", "--oneline", "-12")[1] or "").splitlines()
    state["tags"] = [
        tag for tag in (git("tag", "--sort=-creatordate")[1] or "").splitlines() if tag
    ]
    state["remote_branches"] = []
    state["remote_tags"] = []
    state["fetch_ok"] = False
    state["fetch_error"] = ""
    if no_fetch:
        state["fetch_error"] = "fetch omitido por --no-fetch"
    else:
        code, _, err = git("fetch", "--quiet", "origin", timeout=25)
        state["fetch_ok"] = code == 0
        state["fetch_error"] = "" if code == 0 else (err or "fetch falló")
    code, branches, _ = git("ls-remote", "--heads", "origin")
    if code == 0:
        state["remote_branches"] = [
            line.split("refs/heads/", 1)[-1]
            for line in branches.splitlines()
            if "refs/heads/" in line
        ]
    code, tags, _ = git("ls-remote", "--tags", "origin")
    if code == 0:
        state["remote_tags"] = [
            line.split("refs/tags/", 1)[-1].replace("^{}", "")
            for line in tags.splitlines()
            if "refs/tags/" in line
        ]
    state["origin_main"] = git("rev-parse", "--short", "origin/main")[1]
    state["origin_main_subject"] = git("log", "-1", "--format=%s", "origin/main")[1]
    state["origin_main_date"] = git("log", "-1", "--format=%cI", "origin/main")[1]
    upstream_code, upstream, _ = git(
        "rev-parse", "--abbrev-ref", "--symbolic-full-name", "@{upstream}"
    )
    state["upstream"] = upstream if upstream_code == 0 and upstream else ""
    reference = state["upstream"] or "origin/main"
    state["remote_ref"] = reference
    state["remote_commit"] = git("rev-parse", "--short", reference)[1]
    state["remote_subject"] = git("log", "-1", "--format=%s", reference)[1]
    state["remote_date"] = git("log", "-1", "--format=%cI", reference)[1]
    ahead = behind = None
    code, divergence, _ = git("rev-list", "--left-right", "--count", f"{reference}...HEAD")
    if code == 0 and divergence:
        parts = divergence.split()
        if len(parts) == 2:
            behind, ahead = int(parts[0]), int(parts[1])
    state["behind"] = behind
    state["ahead"] = ahead
    main_code, _, _ = git("merge-base", "--is-ancestor", "HEAD", "origin/main")
    state["merged_into_main"] = main_code == 0
    return state


def remote_state() -> dict[str, Any]:
    data: dict[str, Any] = {"available": False, "error": "", "repo": None, "prs": [], "merged": 0}
    repo, error = gh_json(
        "repo",
        "view",
        "--json",
        "nameWithOwner,visibility,isPrivate,defaultBranchRef,viewerPermission,pushedAt,url",
    )
    if repo is None:
        data["error"] = error
        return data
    data["available"] = True
    data["repo"] = repo
    prs, pr_error = gh_json(
        "pr",
        "list",
        "--state",
        "all",
        "--limit",
        "50",
        "--json",
        "number,title,state,mergedAt,url,headRefName,baseRefName,author",
    )
    if prs is not None:
        data["prs"] = prs
        data["merged"] = sum(1 for pr in prs if pr.get("state") == "MERGED")
    else:
        data["error"] = pr_error
    return data


def db_metrics() -> dict[str, Any]:
    db_path = ROOT / "data" / "bronze" / "_meta" / "bronze.sqlite3"
    metrics: dict[str, Any] = {
        "exists": db_path.is_file(),
        "artifacts": 0,
        "active": 0,
        "quarantined": 0,
        "columns": [],
        "error": "",
    }
    if not db_path.is_file():
        return metrics
    try:
        connection = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
        try:
            metrics["artifacts"] = connection.execute("SELECT COUNT(1) FROM artifacts").fetchone()[
                0
            ]
            metrics["active"] = connection.execute(
                "SELECT COUNT(1) FROM v_active_artifacts"
            ).fetchone()[0]
            metrics["quarantined"] = connection.execute(
                "SELECT COUNT(1) FROM quarantine_entries WHERE status='quarantined'"
            ).fetchone()[0]
            metrics["columns"] = [
                row[1] for row in connection.execute("PRAGMA table_info(artifacts)").fetchall()
            ]
        finally:
            connection.close()
    except sqlite3.Error as exc:
        metrics["error"] = str(exc)
    return metrics


def check_license() -> Check:
    content = read("LICENSE")
    pyproject = read("pyproject.toml")
    if not content:
        return Check(
            "license",
            "Licencia MIT",
            "Repositorio",
            "pending",
            "No existe LICENSE",
            "Crear LICENSE MIT 2026 y declararla en README y pyproject.toml",
            critical=True,
        )
    markers = [
        "MIT License" in content or "MIT" in content,
        "2026" in content,
        "Jason" in content,
        "Roberto" in content,
        "license" in pyproject.lower(),
    ]
    passed = sum(markers)
    evidence = f"LICENSE presente; {passed}/5 señales (MIT, 2026, Jason, Roberto, pyproject)"
    return Check(
        "license",
        "Licencia MIT",
        "Repositorio",
        "done" if passed == 5 else "partial",
        evidence,
        "" if passed == 5 else "Completar titulares, año y declaración en pyproject/README",
        critical=passed < 5,
    )


def check_readme() -> Check:
    content = read("README.md")
    if not content:
        return Check(
            "readme",
            "README profesional",
            "Repositorio",
            "pending",
            "No existe README.md",
            "Crear README con badges, problema, arquitectura, instalación y créditos",
            critical=True,
        )
    markers = {
        "badges": "shields.io" in content or "badge" in content.lower(),
        "problema": "problema" in content.lower(),
        "arquitectura": "arquitectura" in content.lower() or "architecture" in content.lower(),
        "instalación": "uv sync" in content,
        "uso": "uv run" in content,
        "estructura": "estructura" in content.lower() or "structure" in content.lower(),
        "capturas": "![" in content,
        "licencia": "licencia" in content.lower() or "license" in content.lower(),
        "créditos": "Jason" in content and "Roberto" in content,
        "datos": "data/" in content or "bronze" in content.lower(),
    }
    passed = sum(markers.values())
    missing = [key for key, value in markers.items() if not value]
    status = "done" if passed >= 8 else "partial"
    return Check(
        "readme",
        "README profesional",
        "Repositorio",
        status,
        f"{passed}/10 secciones; faltan: {', '.join(missing) or 'ninguna'}",
        ""
        if status == "done"
        else "Completar README con badges, arquitectura, capturas, créditos y licencia",
        critical=status != "done",
    )


def check_app() -> tuple[Check, Check]:
    app = read("app.py")
    pyproject = read("pyproject.toml")
    has_streamlit = "streamlit" in pyproject.lower()
    if not app:
        app_check = Check(
            "app",
            "App Streamlit/Gradio",
            "Aplicación",
            "pending",
            "No existe app.py",
            "Crear app.py con Resumen, FAQ y Q&A; ejecutar con uv run streamlit run app.py",
            critical=True,
        )
        ui_check = Check(
            "ui_metrics",
            "Panel de scraping en la UI",
            "Aplicación",
            "pending",
            "Sin app no hay panel de métricas",
            "Exponer URLs, páginas, tokens, descartes y citas en la app",
            critical=True,
        )
        return app_check, ui_check
    has_three = all(token in app.lower() for token in ("resumen", "faq", "pregunta"))
    has_metrics = all(token in app.lower() for token in ("url", "token", "descarte"))
    app_status = "done" if has_three and has_streamlit else "partial"
    app_evidence = (
        f"app.py presente; tres funciones={'sí' if has_three else 'no'}; "
        f"Streamlit={'sí' if has_streamlit else 'no'}"
    )
    app_check = Check(
        "app",
        "App Streamlit/Gradio",
        "Aplicación",
        app_status,
        app_evidence,
        ""
        if app_status == "done"
        else "Completar las tres funcionalidades y la dependencia Streamlit",
        critical=app_status != "done",
    )
    ui_check = Check(
        "ui_metrics",
        "Panel de scraping en la UI",
        "Aplicación",
        "done" if has_metrics else "pending",
        "Métricas visibles en app.py"
        if has_metrics
        else "No se detectan URLs/tokens/descartes en app.py",
        "" if has_metrics else "Mostrar URLs, páginas, tokens y descartes",
        critical=not has_metrics,
    )
    return app_check, ui_check


def check_llm() -> Check:
    pyproject = read("pyproject.toml")
    has_langchain = "langchain" in pyproject.lower()
    source_text = "\n".join(
        path.read_text(encoding="utf-8", errors="replace")
        for path in (ROOT / "src").rglob("*.py")
        if path.is_file()
    ).lower()
    tasks = [
        name for name in ("resumen", "summary", "faq", "pregunta", "qa") if name in source_text
    ]
    status = (
        "done" if has_langchain and len(tasks) >= 2 else "partial" if has_langchain else "pending"
    )
    return Check(
        "llm",
        "LangChain: Resumen, FAQ y Q&A",
        "Procesamiento LLM",
        status,
        f"LangChain={'sí' if has_langchain else 'no'}; señales de tareas={tasks or 'ninguna'}",
        "" if status == "done" else "Añadir LangChain y las tres tareas con prompts versionados",
        critical=status != "done",
    )


def check_data_layers() -> Check:
    silver = ROOT / "data" / "silver"
    gold = ROOT / "data" / "gold"
    silver_files = [p for p in silver.rglob("*") if p.is_file()] if silver.is_dir() else []
    gold_files = [p for p in gold.rglob("*") if p.is_file()] if gold.is_dir() else []
    status = (
        "done"
        if silver_files and gold_files
        else "partial"
        if silver_files or gold_files
        else "pending"
    )
    return Check(
        "data_layers",
        "Capas silver y gold",
        "Datos",
        status,
        f"silver={len(silver_files)} archivos; gold={len(gold_files)} archivos",
        ""
        if status == "done"
        else "Generar chunks en data/silver y base de conocimiento en data/gold",
        critical=status != "done",
    )


def check_corpus(metrics: dict[str, Any]) -> Check:
    if not metrics["exists"]:
        return Check(
            "corpus",
            "Corpus y metadata",
            "Datos",
            "pending",
            "No existe el catálogo bronze",
            "Ejecutar el pipeline y verificar metadata/hash",
            critical=True,
        )
    has_section = "section" in metrics["columns"]
    status = (
        "done"
        if metrics["active"] and has_section
        else "partial"
        if metrics["active"]
        else "pending"
    )
    evidence = (
        f"{metrics['active']} activos de {metrics['artifacts']} totales; "
        f"{metrics['quarantined']} en cuarentena; columna section={'sí' if has_section else 'no'}"
    )
    return Check(
        "corpus",
        "Corpus y metadata",
        "Datos",
        status,
        evidence,
        "" if status == "done" else "Enriquecer metadata con sección y documentar licencia/uso",
        critical=status != "done",
    )


def check_pipeline_entry() -> Check:
    if (ROOT / "scripts" / "scrape_empresa.py").is_file():
        return Check(
            "pipeline_entry",
            "Entrada canónica de scraping",
            "Pipeline",
            "done",
            "scripts/scrape_empresa.py presente",
            "",
        )
    if (ROOT / "scripts" / "run_campaign.py").is_file():
        return Check(
            "pipeline_entry",
            "Entrada canónica de scraping",
            "Pipeline",
            "partial",
            "Existe scripts/run_campaign.py, falta scripts/scrape_empresa.py",
            "Crear scripts/scrape_empresa.py como wrapper de run_campaign.py",
            critical=True,
        )
    return Check(
        "pipeline_entry",
        "Entrada canónica de scraping",
        "Pipeline",
        "pending",
        "No hay script de scraping canónico",
        "Crear scripts/scrape_empresa.py ejecutable con uv run",
        critical=True,
    )


def check_ci() -> Check:
    workflows = (
        list((ROOT / ".github" / "workflows").glob("*.yml"))
        if (ROOT / ".github" / "workflows").is_dir()
        else []
    )
    workflows += (
        list((ROOT / ".github" / "workflows").glob("*.yaml"))
        if (ROOT / ".github" / "workflows").is_dir()
        else []
    )
    if workflows:
        return Check(
            "ci",
            "CI con Ruff y pytest",
            "Repositorio",
            "done",
            f"{len(workflows)} workflow(s) en .github/workflows",
            "",
        )
    return Check(
        "ci",
        "CI con Ruff y pytest",
        "Repositorio",
        "pending",
        "No hay workflows de GitHub Actions",
        "Añadir workflow con uv sync --frozen, ruff check y pytest",
        critical=True,
    )


def check_prs(remote: dict[str, Any]) -> Check:
    if not remote["available"]:
        return Check(
            "prs",
            "Pull Requests fusionados",
            "Repositorio",
            "unknown",
            f"Sin verificar: {remote['error']}",
            "Verificar gh auth y acceso al repositorio",
            critical=True,
        )
    merged = remote["merged"]
    status = "done" if merged >= 2 else "partial" if merged == 1 else "pending"
    return Check(
        "prs",
        "Pull Requests fusionados",
        "Repositorio",
        status,
        f"{merged} PR(s) fusionados de {len(remote['prs'])} totales",
        "" if merged >= 2 else "Crear y fusionar al menos 2 PRs con revisión",
        critical=merged < 2,
    )


def check_commits(git_info: dict[str, Any]) -> Check:
    pattern = re.compile(r"^(feat|fix|docs|test|refactor|chore|style|perf|build|ci)(\(.+\))?: ")
    subjects = [
        line.split(" ", 1)[1] if " " in line else line for line in git_info["recent_commits"]
    ]
    subjects = [subject for subject in subjects if subject.strip().lower() != "initial commit"]
    total = len(subjects)
    conventional = sum(1 for subject in subjects if pattern.match(subject))
    status = "done" if total and conventional == total else "partial" if conventional else "pending"
    return Check(
        "commits",
        "Conventional Commits",
        "Repositorio",
        status,
        f"{conventional}/{total} commits recientes cumplen el formato",
        "" if status == "done" else "Normalizar los mensajes de commit",
    )


def check_specs() -> Check:
    specs = sorted((ROOT / "specs").glob("*/spec.md")) if (ROOT / "specs").is_dir() else []
    return Check(
        "specs",
        "Especificaciones versionadas",
        "Documentación",
        "done" if specs else "pending",
        f"{len(specs)} especificación(es) en specs/",
        "" if specs else "Crear specs por fase",
    )


def check_docs() -> list[Check]:
    docs = {
        "alcance": ("docs/alcance.md", "Alcance del Q&A"),
        "data_card": ("docs/data_card.md", "Ficha de datos"),
        "prompt_log": ("docs/prompt_log.md", "Prompt log"),
        "report": ("docs/informe_modulo1.md", "Informe del Módulo 1"),
        "demo": ("docs/demo.md", "Guion de demo"),
        "evaluation": ("docs/evaluacion_modulo1.md", "Evaluación de 20 preguntas"),
    }
    results: list[Check] = []
    for key, (path, label) in docs.items():
        exists = (ROOT / path).is_file()
        critical = key in {"report", "evaluation"}
        results.append(
            Check(
                key,
                label,
                "Documentación",
                "done" if exists else "pending",
                path if exists else f"Falta {path}",
                "" if exists else f"Crear {path}",
                critical=critical,
            )
        )
    return results


def check_tests(skip: bool) -> tuple[Check, Check]:
    if skip:
        unknown = "No ejecutado (--skip-checks)"
        return (
            Check(
                "tests", "Pruebas offline", "Calidad", "unknown", unknown, "Ejecutar uv run pytest"
            ),
            Check(
                "ruff", "Ruff limpio", "Calidad", "unknown", unknown, "Ejecutar uv run ruff check ."
            ),
        )
    code, out, err = run(["uv", "run", "pytest", "--disable-warnings"], timeout=240)
    combined = f"{out}\n{err}"
    passed = re.search(r"(\d+)\s+passed", combined)
    if passed:
        summary = f"{passed.group(1)} pruebas pasadas"
    elif code == 0:
        summary = "pytest completado sin errores"
    else:
        summary = combined.strip().splitlines()[-1] if combined.strip() else "pytest falló"
    tests = Check(
        "tests",
        "Pruebas offline",
        "Calidad",
        "done" if code == 0 else "pending",
        summary[:300],
        "" if code == 0 else "Corregir las pruebas fallidas",
        critical=code != 0,
    )
    ruff_code, ruff_out, ruff_err = run(["uv", "run", "ruff", "check", "."], timeout=120)
    ruff_summary = (
        (ruff_out or ruff_err).splitlines()[-1] if (ruff_out or ruff_err) else "sin salida"
    )
    ruff = Check(
        "ruff",
        "Ruff limpio",
        "Calidad",
        "done" if ruff_code == 0 else "pending",
        ruff_summary[:300],
        "" if ruff_code == 0 else "Corregir hallazgos de Ruff",
        critical=ruff_code != 0,
    )
    return tests, ruff


def check_secrets() -> Check:
    code, out, _ = git("ls-files")
    tracked = out.splitlines() if code == 0 else []
    offenders = [
        path
        for path in tracked
        if path == ".env" or path.startswith("data/") or ".pem" in path or path.endswith(".key")
    ]
    return Check(
        "secrets",
        "Sin secretos ni datos versionados",
        "Seguridad",
        "done" if not offenders else "pending",
        "Sin .env, data/ ni claves" if not offenders else f"Archivos sensibles: {offenders[:5]}",
        "" if not offenders else "Eliminar del historial y añadir a .gitignore",
        critical=bool(offenders),
    )


def check_tag(git_info: dict[str, Any]) -> Check:
    tag = "v0.1.0-modulo1"
    exists = tag in git_info["tags"] or tag in git_info["remote_tags"]
    return Check(
        "tag",
        "Tag de entrega",
        "Repositorio",
        "done" if exists else "pending",
        f"{tag} {'presente' if exists else 'ausente'}",
        "" if exists else f"Crear {tag} después de la demo",
        critical=True,
    )


def cascade_state(checks: list[Check]) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Return task rows and gate rows with dependency-aware states."""
    by_key = {check.key: check for check in checks}
    status_by_id: dict[str, str] = {}
    rows: list[dict[str, str]] = []
    for step in CASCADE_STEPS:
        own = [by_key[key].status if key in by_key else "unknown" for key in step.checks]
        dependencies_done = all(status_by_id.get(dep) == "done" for dep in step.depends_on)
        if not dependencies_done:
            status = "blocked"
        elif not own or any(value == "pending" for value in own):
            status = "pending"
        elif any(value in {"partial", "unknown"} for value in own):
            status = "partial"
        else:
            status = "done"
        status_by_id[step.id] = status
        rows.append(
            {
                "id": step.id,
                "stage": str(step.stage),
                "title": step.title,
                "depends_on": ", ".join(step.depends_on) or "—",
                "deliverable": step.deliverable,
                "acceptance": step.acceptance,
                "owner": step.owner,
                "estimate": step.estimate,
                "status": status,
            }
        )

    gates: list[dict[str, str]] = []
    for gate in QUALITY_GATES:
        index = next(
            (position for position, step in enumerate(CASCADE_STEPS) if step.id == gate.after), 0
        )
        statuses = [status_by_id.get(step.id, "pending") for step in CASCADE_STEPS[: index + 1]]
        if all(value == "done" for value in statuses):
            status = "done"
        elif any(value == "blocked" for value in statuses):
            status = "blocked"
        else:
            status = "pending"
        gates.append(
            {
                "id": gate.id,
                "after": gate.after,
                "criterion": gate.criterion,
                "status": status,
            }
        )
    return rows, gates


def phase_status(checks: list[Check]) -> tuple[str, str]:
    by_key = {check.key: check for check in checks}
    phase1_keys = [
        "license",
        "readme",
        "prs",
        "app",
        "llm",
        "data_layers",
        "corpus",
        "pipeline_entry",
        "ci",
        "evaluation",
        "report",
        "demo",
        "tag",
    ]
    phase1_done = all(by_key[key].status == "done" for key in phase1_keys if key in by_key)
    if phase1_done:
        return (
            "Fase 1 — Módulo 1 completa",
            "Cerrar la entrega y preparar la Fase 2 (embeddings y RAG).",
        )
    return "Fase 1 — Módulo 1 en curso", "Cerrar la ruta crítica del Módulo 1 antes del 31-oct."


def previous_log() -> Path | None:
    directory = ROOT / "bitacora"
    if not directory.is_dir():
        return None
    logs = sorted(directory.glob("*.md"))
    return logs[-1] if logs else None


def commits_since(previous: Path | None, limit: int = 20) -> list[str]:
    if previous is None:
        return git("log", f"-{limit}", "--format=%h %s")[1].splitlines()
    content = previous.read_text(encoding="utf-8", errors="replace")
    match = re.search(r"\*\*Commit local\*\*:\s*`([0-9a-f]{7,40})`", content)
    if not match:
        return git("log", f"-{limit}", "--format=%h %s")[1].splitlines()
    code, out, _ = git("log", f"{match.group(1)}..HEAD", "--format=%h %s", f"-{limit}")
    return out.splitlines() if code == 0 and out else []


def file_name(now: datetime) -> Path:
    directory = ROOT / "bitacora"
    directory.mkdir(parents=True, exist_ok=True)
    base = now.strftime("%Y-%m-%d")
    candidate = directory / f"{base}.md"
    if candidate.exists():
        candidate = directory / f"{base}-{now:%H%M}.md"
    if candidate.exists():
        candidate = directory / f"{base}-{now:%H%M%S}.md"
    return candidate


def build_report(
    *,
    now: datetime,
    constitution: dict[str, str],
    git_info: dict[str, Any],
    remote: dict[str, Any],
    metrics: dict[str, Any],
    checks: list[Check],
    previous: Path | None,
    output: Path,
) -> str:
    done = [check for check in checks if check.status == "done"]
    pending = [check for check in checks if check.status in {"pending", "partial", "unknown"}]
    cascade_rows, gates = cascade_state(checks)
    next_step = next((row for row in cascade_rows if row["status"] != "done"), None)
    next_priority = (
        f"{next_step['id']} — {next_step['title']} ({next_step['deliverable']})"
        if next_step
        else "avanzar a la Fase 2 (embeddings y RAG)."
    )
    progress = round(
        100 * (len(done) + 0.5 * len([c for c in pending if c.status == "partial"])) / len(checks)
    )
    phase, phase_note = phase_status(checks)
    spec_count = sum(1 for _ in (ROOT / "specs").glob("*/spec.md"))
    repo = remote.get("repo") or {}
    visibility = repo.get("visibility", "desconocida")
    permissions = repo.get("viewerPermission", "desconocido")
    origin_label = (
        f"`{git_info['origin_main'] or 'sin referencia'}` — "
        f"{git_info['origin_main_subject'] or 'sin referencia'}"
    )
    remote_label = (
        f"`{git_info['remote_commit'] or 'sin referencia'}` — "
        f"{git_info['remote_subject'] or 'sin referencia'}"
    )
    date_label = (
        f"{git_info['committed_at'] or 'sin fecha'} | {git_info['remote_date'] or 'sin fecha'}"
    )
    ahead = git_info["ahead"]
    behind = git_info["behind"]
    remote_ref = git_info["remote_ref"]
    if ahead is None or behind is None:
        sync = f"Sin referencia remota `{remote_ref}`"
    elif not git_info["upstream"]:
        sync = (
            f"Rama local sin upstream; {ahead} commit(s) por delante de `origin/main`"
            if ahead
            else "Rama local sin upstream"
        )
    elif ahead == 0 and behind == 0:
        sync = f"Sincronizado con `{remote_ref}`"
    elif ahead and behind:
        sync = f"Divergente: {ahead} local(es) por delante y {behind} por detrás de `{remote_ref}`"
    elif ahead:
        sync = f"{ahead} commit(s) locales por delante de `{remote_ref}`"
    else:
        sync = f"{behind} commit(s) por detrás de `{remote_ref}`"

    lines: list[str] = [
        "# Bitácora del Proyecto — RAG Ingenio Manuelita",
        "",
        f"**Fecha**: {now.strftime('%Y-%m-%d %H:%M %Z')}",
        f"**Archivo**: `{output.relative_to(ROOT).as_posix()}`",
        f"**Commit local**: `{git_info['head']}`",
        f"**Commit remoto**: `{git_info['remote_commit'] or 'sin referencia'}` · "
        f"**Rama remota**: `{remote_ref}`",
        "**Generada por**: skill `bitacora`",
        "",
        "## 1. Resumen ejecutivo",
        "",
        f"- **Fase actual**: {phase}.",
        f"- **Avance de la lista de verificación**: {progress}% "
        f"({len(done)} de {len(checks)} requisitos cerrados).",
        f"- **Repositorio**: rama `{git_info['branch']}`, commit `{git_info['head']}`; {sync}.",
        f"- **Corpus**: {metrics['active'] or 0} artefactos activos "
        f"de {metrics['artifacts'] or 0}; {metrics['quarantined'] or 0} en cuarentena.",
        f"- **Siguiente prioridad**: {next_priority}",
        "",
        "## 2. Contexto de la constitución",
        "",
        "| Campo | Valor |",
        "|-------|-------|",
        f"| Constitución | `CONSTITUTION.md` v{constitution['version']} |",
        f"| Ratificada | {constitution['ratified']} |",
        f"| Última enmienda | {constitution['amended']} |",
        f"| Fase | {phase} |",
        "| Reglas clave | LangChain para Resumen/FAQ/Q&A; 20 preguntas; app con citas; "
        "≥2 PRs; MIT; CI verde; demo 12+3 sin diapositivas |",
        "",
        f"> {phase_note}",
        "",
        "## 3. Estado del repositorio",
        "",
        "| Aspecto | Local | Remoto |",
        "|---------|-------|--------|",
        f"| Rama | `{git_info['branch']}` | `{remote_ref}` |",
        f"| Commit | `{git_info['head']}` — {git_info['subject']} | {remote_label} |",
        f"| Fecha | {date_label} |",
        f"| Estado | {'sucio' if git_info['dirty'] else 'limpio'} | {visibility} ({permissions}) |",
        f"| Main remoto | — | {origin_label} |",
        f"| PRs | — | {remote['merged']} fusionados de {len(remote['prs'])} |",
        f"| Tags | {', '.join(git_info['tags'][:3]) or 'ninguno'} | "
        f"{', '.join(git_info['remote_tags'][:3]) or 'ninguno'} |",
        "",
        f"**Sincronización**: {sync}.",
        "",
        f"**Remoto**: {git_info['remote_url']}",
        "",
        "## 4. Qué se ha hecho",
        "",
    ]
    if previous:
        lines.append(f"Desde la bitácora anterior (`{previous.name}`):")
        lines.append("")
    else:
        lines.append("Primera bitácora registrada. Commits recientes:")
        lines.append("")
    recent = commits_since(previous)
    if recent:
        lines.extend(f"- `{line}`" for line in recent)
    else:
        lines.append("- Sin commits nuevos desde la bitácora anterior.")
    lines.extend(
        [
            "",
            "**Evidencia acumulada**:",
            "",
            f"- Corpus bronze: {metrics['active'] or 0} artefactos activos, "
            f"{metrics['quarantined'] or 0} en cuarentena.",
            f"- Especificaciones: {spec_count} fases documentadas.",
            f"- Pruebas: {next((c.evidence for c in checks if c.key == 'tests'), 'sin dato')}.",
            "",
            "## 5. Avance por criterio",
            "",
            "| Área | Estado | Evidencia |",
            "|------|--------|-----------|",
        ]
    )
    areas: dict[str, list[Check]] = {}
    for check in checks:
        areas.setdefault(check.area, []).append(check)
    for area, area_checks in areas.items():
        area_done = sum(1 for check in area_checks if check.status == "done")
        area_status = "✅" if area_done == len(area_checks) else "🟡" if area_done else "❌"
        summary = f"{area_done}/{len(area_checks)} requisitos"
        lines.append(f"| {area} | {area_status} | {summary} |")

    lines.extend(["", "## 6. Objetivos y metas cumplidos", ""])
    if done:
        lines.extend(f"- ✅ {check.label}: {check.evidence}" for check in done)
    else:
        lines.append("- Aún no hay requisitos cerrados en la lista de verificación.")

    lines.extend(
        [
            "",
            "## 7. Pendientes y bloqueos",
            "",
            "| Prioridad | Pendiente | Estado | Siguiente acción |",
            "|-----------|-----------|--------|------------------|",
        ]
    )
    for check in sorted(pending, key=lambda item: (not item.critical, item.area, item.label)):
        priority = "Crítica" if check.critical else "Normal"
        lines.append(
            f"| {priority} | {check.label} | {CHECK_ICONS.get(check.status, '⚠️')} "
            f"{check.status} | {check.action or 'Revisar'} |"
        )
    if not pending:
        lines.append("| — | Sin pendientes en la lista | ✅ | Avanzar a la Fase 2 |")

    lines.extend(
        [
            "",
            "## 8. Cascada secuencial de tareas pendientes",
            "",
            "La secuencia respeta dependencias y puertas de calidad: no se debe avanzar sin "
            "cerrar la puerta anterior.",
            "",
            f"**Ruta crítica:** {' → '.join(step.id for step in CASCADE_STEPS)}",
            "",
            "| Etapa | ID | Tarea | Depende de | Entregable | Criterio de aceptación | "
            "Responsable | Tiempo | Estado |",
            "|-------|----|-------|------------|------------|------------------------|-------------|--------|--------|",
        ]
    )
    visible_steps = [row for row in cascade_rows if row["status"] != "done"]
    if visible_steps:
        for row in visible_steps:
            icon = CASCADE_ICONS.get(row["status"], "⚠️")
            label = CASCADE_LABELS.get(row["status"], row["status"])
            lines.append(
                f"| {row['stage']} | **{row['id']}** | {row['title']} | {row['depends_on']} | "
                f"{row['deliverable']} | {row['acceptance']} | {row['owner']} | "
                f"{row['estimate']} | {icon} {label} |"
            )
    else:
        lines.append("| — | — | Sin tareas pendientes | — | — | — | — | — | ✅ completada |")

    lines.extend(
        [
            "",
            "### Puertas de calidad",
            "",
            "| Puerta | Después de | Criterio | Estado |",
            "|--------|------------|----------|--------|",
        ]
    )
    for gate in gates:
        icon = CASCADE_ICONS.get(gate["status"], "⚠️")
        label = CASCADE_LABELS.get(gate["status"], gate["status"])
        lines.append(f"| {gate['id']} | {gate['after']} | {gate['criterion']} | {icon} {label} |")

    lines.extend(["", "## 9. Próximos pasos sugeridos", ""])
    steps: list[str] = []
    for row in cascade_rows:
        if row["status"] != "done":
            steps.append(f"{row['id']} — {row['title']}: {row['deliverable']}")
    if not steps:
        steps = [
            "Documentar la decisión de embeddings y base vectorial para la Fase 2.",
            "Diseñar el conjunto de evaluación de recuperación (Recall@k, MRR).",
            "Implementar memoria y RAG con citas, y actualizar la app.",
        ]
    for index, step in enumerate(steps[:8], start=1):
        lines.append(f"{index}. {step}")

    lines.extend(
        [
            "",
            "## 10. Riesgos y observaciones",
            "",
        ]
    )
    if git_info["dirty"]:
        lines.append(
            f"- Hay {len(git_info['dirty_lines'])} archivo(s) sin commit; "
            "la bitácora puede incluir cambios no publicados."
        )
    if not remote["available"]:
        lines.append(f"- El estado remoto no se pudo verificar: {remote['error']}")
    if not git_info["upstream"]:
        lines.append("- La rama local no tiene upstream; aún no está publicada.")
    elif not git_info["merged_into_main"]:
        lines.append(
            f"- La rama está publicada en `{remote_ref}` pero no fusionada en `main`; "
            "falta el Pull Request."
        )
    if git_info["fetch_error"] and not git_info["fetch_ok"]:
        lines.append(
            f"- `git fetch` no se completó: {git_info['fetch_error']}; "
            "la comparación remota puede estar desactualizada."
        )
    if metrics["error"]:
        lines.append(f"- Error al leer el catálogo: {metrics['error']}")
    if ahead:
        lines.append(f"- {ahead} commit(s) locales por delante de `{remote_ref}`; push pendiente.")
    if not lines[-1].startswith("-"):
        lines.append("- Sin riesgos adicionales detectados.")

    lines.extend(
        [
            "",
            "## 11. Evidencia de verificación",
            "",
            "```text",
            f"git rev-parse --abbrev-ref HEAD  -> {git_info['branch']}",
            f"git rev-parse --short HEAD       -> {git_info['head']}",
            f"git rev-parse --short {remote_ref} -> "
            f"{git_info['remote_commit'] or 'sin referencia'}",
            f"git rev-parse --short origin/main -> {git_info['origin_main'] or 'sin referencia'}",
            f"git status --porcelain           -> {len(git_info['dirty_lines'])} archivo(s)",
            f"git rev-list --left-right --count {remote_ref}...HEAD -> "
            f"{behind if behind is not None else '?'} {ahead if ahead is not None else '?'}",
            f"git merge-base --is-ancestor HEAD origin/main -> "
            f"{'sí' if git_info['merged_into_main'] else 'no'}",
            f"gh repo view                     -> {visibility}, {permissions}",
            "```",
            "",
            "---",
            "",
            f"Bitácora generada automáticamente el {now.strftime('%Y-%m-%d a las %H:%M')}. "
            "Las métricas provienen de Git, GitHub CLI, el catálogo SQLite "
            "y las comprobaciones locales.",
            "",
        ]
    )
    return "\n".join(lines)


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Genera una bitácora fechada del proyecto.")
    parser.add_argument("--skip-checks", action="store_true", help="No ejecutar pytest ni Ruff.")
    parser.add_argument("--no-fetch", action="store_true", help="No ejecutar git fetch.")
    parser.add_argument(
        "--dry-run", action="store_true", help="Imprimir el informe sin escribir el archivo."
    )
    args = parser.parse_args()

    if not (ROOT / "CONSTITUTION.md").is_file():
        print("ERROR: no se encontró CONSTITUTION.md en la raíz del proyecto.", file=sys.stderr)
        return 2

    now = datetime.now().astimezone()
    constitution = constitution_context()
    git_info = git_state(no_fetch=args.no_fetch)
    remote = remote_state()
    metrics = db_metrics()

    checks: list[Check] = [check_license(), check_readme()]
    app_check, ui_check = check_app()
    checks.extend([app_check, ui_check, check_llm(), check_data_layers(), check_corpus(metrics)])
    checks.extend([check_pipeline_entry(), check_ci(), check_prs(remote), check_commits(git_info)])
    checks.extend(check_docs())
    tests_check, ruff_check = check_tests(args.skip_checks)
    checks.extend([tests_check, ruff_check, check_secrets(), check_tag(git_info), check_specs()])

    previous = previous_log()
    output = file_name(now)
    report = build_report(
        now=now,
        constitution=constitution,
        git_info=git_info,
        remote=remote,
        metrics=metrics,
        checks=checks,
        previous=previous,
        output=output,
    )

    if args.dry_run:
        print(report)
        print(f"\n[DRY-RUN] Se habría creado: {output.relative_to(ROOT).as_posix()}")
        return 0

    output.write_text(report, encoding="utf-8", newline="\n")
    done = sum(1 for check in checks if check.status == "done")
    print(f"Bitácora creada: {output.relative_to(ROOT).as_posix()}")
    print(f"Progreso de la lista de verificación: {done}/{len(checks)} requisitos cerrados.")
    print(f"Fase: {phase_status(checks)[0]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
