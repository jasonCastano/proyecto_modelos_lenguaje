"""Reconstrucción del corpus con un comando (spec 024, US5, research R15).

``rebuild`` encadena plata → oro → índice denso → colección Qdrant **sobre un directorio de
trabajo** (por defecto ``$TMP/pml-rebuild-<run_id>``) y nunca reescribe ``data/silver|gold`` ni el
índice versionado, salvo ``in_place=True`` con confirmación explícita. Al final verifica cada capa
y escribe ``<workdir>/manifest.json`` (data-model §11) con conteos, duración y SHA-256 de cada
salida, la procedencia de los fragmentos, el commit de Git y la versión de Python.

Disposición del directorio de trabajo::

    <workdir>/silver/   documents.jsonl, chunks.jsonl, markdown/, reports/  (solo --from bronze)
    <workdir>/gold/     knowledge_units.jsonl, facts.jsonl, …, context_*.{md,json,jsonl}
    <workdir>/index/    manifest.json, vectors.npy, index.sqlite3
    <workdir>/qdrant/   colección local embebida (nunca el servidor de QDRANT_URL)
    <workdir>/manifest.json

``--from bronze`` lee el catálogo SQLite del bronce versionado (solo lectura); ``--from silver``
lee la plata versionada (``data/silver``) sin copiarla. ``scrape=True`` ejecuta antes la campaña
de adquisición (red; añade artefactos inmutables al bronce) y solo corre si se pide.
"""

from __future__ import annotations

import hashlib
import json
import platform
import re
import subprocess
import tempfile
import time
from collections.abc import Callable, Iterable
from dataclasses import replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .config import PROJECT_ROOT

SOURCES = ("bronze", "silver")
MANIFEST_NAME = "manifest.json"
SCHEMA_VERSION = "1.0"
SILVER_OUTPUTS = ("documents.jsonl", "chunks.jsonl")
GOLD_OUTPUTS = (
    "knowledge_units.jsonl",
    "facts.jsonl",
    "entities.jsonl",
    "conflicts.jsonl",
    "faq_seeds.jsonl",
    "coverage.json",
    "context_8000.json",
    "context_32000.json",
)
INDEX_OUTPUTS = ("manifest.json", "vectors.npy", "index.sqlite3")

ProgressFn = Callable[[str], None]


class CorpusError(RuntimeError):
    """Error controlado de la reconstrucción (código de salida en ``exit_code``)."""

    def __init__(self, message: str, exit_code: int = 2) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def new_run_id(moment: datetime | None = None) -> str:
    """Identificador de la reconstrucción: ``rebuild-AAAAMMDDTHHMMSSZ``."""
    moment = moment or datetime.now(UTC)
    return "rebuild-" + moment.strftime("%Y%m%dT%H%M%SZ")


def default_workdir(run_id: str) -> Path:
    """Directorio de trabajo por defecto: ``$TMP/pml-rebuild-<run_id>``."""
    return Path(tempfile.gettempdir()) / f"pml-{run_id}"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _file_entries(root: Path, names: Iterable[str], base: Path) -> list[dict[str, Any]]:
    entries = []
    for name in names:
        path = root / name
        if not path.is_file():
            continue
        try:
            shown = path.resolve().relative_to(base.resolve()).as_posix()
        except ValueError:
            shown = path.resolve().as_posix()
        entries.append({"path": shown, "bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return entries


def _count_lines(path: Path) -> int:
    if not path.is_file():
        return 0
    with path.open(encoding="utf-8") as handle:
        return sum(1 for line in handle if line.strip())


def _git_commit(project_root: Path) -> str | None:
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"],
            cwd=project_root,
            text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return None


def _next_run_id(reports_dir: Path, layer: str, moment: datetime) -> str:
    """Siguiente ``AAAA-MM-<capa>-NN`` libre en ``reports/`` (00 si no hay ninguno)."""
    prefix = moment.strftime("%Y-%m") + f"-{layer}-"
    used = []
    if reports_dir.is_dir():
        pattern = re.compile(rf"^{re.escape(prefix)}(\d{{2}})$")
        for child in reports_dir.iterdir():
            match = pattern.match(child.name)
            if match:
                used.append(int(match.group(1)))
    number = (max(used) + 1) if used else 1
    if number > 99:
        raise CorpusError(f"no quedan identificadores libres para {prefix}NN en {reports_dir}")
    return f"{prefix}{number:02d}"


def has_provenance(unit: dict[str, Any] | None) -> bool:
    """Procedencia completa: ``unit_id`` + URL + localizador (página, tiempo o sección).

    Los PDF se localizan por página y los videos por tiempo; las páginas web no tienen ninguno de
    los dos, así que su localizador es la ruta de secciones (``section_path``).
    """
    if not unit or not unit.get("unit_id") or not unit.get("url"):
        return False
    return (
        unit.get("page_start") is not None
        or unit.get("time_start") is not None
        or bool(unit.get("section_path"))
    )


def provenance_summary(
    fragment_unit_ids: Iterable[str], fragment_urls: Iterable[str], units: dict[str, dict]
) -> dict[str, int]:
    """Cuenta fragmentos con procedencia completa y, aparte, con página o tiempo."""
    total = 0
    complete = 0
    paged = 0
    for unit_id, url in zip(fragment_unit_ids, fragment_urls, strict=True):
        total += 1
        unit = units.get(unit_id)
        if unit is None or not url:
            continue
        if has_provenance(unit):
            complete += 1
        if unit.get("page_start") is not None or unit.get("time_start") is not None:
            paged += 1
    return {
        "fragments_total": total,
        "fragments_with_provenance": complete,
        "fragments_with_page_or_time": paged,
    }


def _read_units(path: Path) -> dict[str, dict[str, Any]]:
    units: dict[str, dict[str, Any]] = {}
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                payload = json.loads(line)
                units[str(payload.get("unit_id", ""))] = payload
    return units


def rebuild(
    *,
    from_: str = "bronze",
    workdir: str | Path | None = None,
    in_place: bool = False,
    confirm: bool = False,
    scrape: bool = False,
    campaign: str | None = None,
    limit: int | None = None,
    embedder: str = "fastembed",
    qdrant: bool = True,
    verify: bool = True,
    project_root: Path = PROJECT_ROOT,
    sources_config: str | Path = "config/sources.toml",
    silver_config: str | Path = "config/silver.toml",
    gold_config: str | Path = "config/gold.toml",
    taxonomy: str | Path = "config/gold_taxonomy.toml",
    retrieval_config: str | Path | None = None,
    silver_input: str | Path | None = None,
    run_id: str | None = None,
    progress: ProgressFn | None = None,
) -> dict[str, Any]:
    """Reconstruye plata → oro → índice → Qdrant y devuelve el manifiesto (data-model §11).

    ``silver_input`` (solo ``from_="silver"``) cambia la plata de entrada; por defecto la del
    proyecto (``data/silver``), que se lee sin modificarla.
    """
    from .gold.pipeline import GoldPipeline
    from .rag.config import load_retrieval_config
    from .rag.embeddings import EmbeddingProfile, build_embedder
    from .rag.index import build_index, load_index, verify_index
    from .rag.vectorstore import (
        build_collection,
        collection_matches,
        load_qdrant_settings,
        open_client,
    )
    from .retrieval import GoldUnit
    from .silver.pipeline import SilverPipeline

    if from_ not in SOURCES:
        raise CorpusError(f"--from debe ser uno de {', '.join(SOURCES)}", 2)
    if in_place and not confirm:
        raise CorpusError(
            "--in-place reescribe data/silver, data/gold y el índice versionados; "
            "repite con --confirm si de verdad quieres hacerlo",
            2,
        )
    if in_place and workdir is not None:
        raise CorpusError("--in-place y --workdir son excluyentes", 2)
    if scrape and not campaign:
        raise CorpusError("--scrape exige --campaign ID", 2)
    if limit is not None and limit < 1:
        raise CorpusError("--limit debe ser >= 1", 2)

    root = Path(project_root)
    say = progress or (lambda _message: None)
    moment = datetime.now(UTC)
    run_id = run_id or new_run_id(moment)
    started_at = _now()
    started = time.perf_counter()

    retrieval = load_retrieval_config(retrieval_config, project_root=root)
    qdrant_settings = load_qdrant_settings(retrieval.source)
    if in_place:
        base = root
        silver_out: Path | None = None  # la de config/silver.toml
        gold_out: Path | None = None  # la de config/gold.toml
        index_dir = retrieval.index_dir
    else:
        base = Path(workdir) if workdir is not None else default_workdir(run_id)
        base = base if base.is_absolute() else (Path.cwd() / base)
        base = base.resolve()
        data_dir = (root / "data").resolve()
        if base == data_dir or data_dir in base.parents:
            raise CorpusError(f"el directorio de trabajo no puede estar dentro de {data_dir}", 2)
        if base.exists() and any(base.iterdir()):
            raise CorpusError(f"el directorio de trabajo {base} no está vacío; usa otro", 2)
        base.mkdir(parents=True, exist_ok=True)
        silver_out = base / "silver"
        gold_out = base / "gold"
        index_dir = base / "index"
        qdrant_settings = replace(qdrant_settings, path=base / "qdrant", url=None)

    stages: dict[str, dict[str, Any]] = {}
    verification: dict[str, Any] = {}

    # 0. Adquisición (opcional, con red).
    if scrape:
        from .campaign_service import start_campaign
        from .config import load_config

        say(f"bronce: campaña {campaign} (red)")
        begin = time.perf_counter()
        run = start_campaign(
            load_config(sources_config, project_root=root),
            campaign_id=str(campaign),
            resume=True,
        )
        summary = run.summary.as_dict()
        stages["bronze"] = {
            "status": "completed" if run.summary.exit_code == 0 else "failed",
            "campaign": campaign,
            "summary": summary,
            "duration_seconds": round(time.perf_counter() - begin, 3),
        }
        if run.summary.exit_code != 0:
            raise CorpusError(f"la campaña {campaign} terminó con código {run.summary.exit_code}")

    # 1. Plata.
    begin = time.perf_counter()
    if from_ == "bronze":
        silver = SilverPipeline.from_paths(
            sources_config=sources_config,
            silver_config=silver_config,
            project_root=root,
            output_root=silver_out,
        )
        silver_root = silver.config.output.root
        silver_run = _next_run_id(silver_root / "reports", "silver", moment)
        say(f"plata: {silver_run} -> {silver_root}")
        report = silver.build(silver_run, limit=limit, force=in_place, smoke=False)
        stages["silver"] = {
            "status": report.get("status"),
            "run_id": silver_run,
            "source": "bronze",
            "output": str(silver_root),
            "counts": {
                "input_artifacts": report.get("input_artifacts"),
                "documents": report.get("canonical_documents"),
                "chunks": report.get("chunks"),
                "failed": report.get("failed"),
            },
        }
        if verify:
            verification["silver"] = silver.verify_run(silver_run)
    else:
        silver_root = Path(silver_input) if silver_input is not None else root / "data" / "silver"
        silver_root = silver_root if silver_root.is_absolute() else root / silver_root
        if not (silver_root / "documents.jsonl").is_file():
            raise CorpusError(f"no hay capa de plata en {silver_root}", 3)
        say(f"plata: se reutiliza {silver_root} (solo lectura)")
        stages["silver"] = {
            "status": "reused",
            "source": "silver",
            "output": str(silver_root),
            "counts": {
                "documents": _count_lines(silver_root / "documents.jsonl"),
                "chunks": _count_lines(silver_root / "chunks.jsonl"),
            },
        }
    stages["silver"]["files"] = _file_entries(silver_root, SILVER_OUTPUTS, base)
    stages["silver"]["duration_seconds"] = round(time.perf_counter() - begin, 3)

    # 2. Oro (sobre la plata recién construida o la reutilizada).
    begin = time.perf_counter()
    gold = GoldPipeline.from_paths(
        silver_dir=silver_root,
        config_path=gold_config,
        taxonomy_path=taxonomy,
        project_root=root,
        output_root=gold_out,
    )
    gold_root = gold.config.output.root
    gold_run = _next_run_id(gold_root / "reports", "gold", moment)
    gold_limit = limit if from_ == "silver" else None
    say(f"oro: {gold_run} -> {gold_root}")
    report = gold.build(gold_run, limit=gold_limit, force=in_place, smoke=False)
    stages["gold"] = {
        "status": report.get("status"),
        "run_id": gold_run,
        "output": str(gold_root),
        "counts": {
            "input_documents": report.get("input_documents"),
            "units": report.get("units"),
            "facts": report.get("facts"),
            "entities": report.get("entities"),
            "conflicts": report.get("conflicts"),
        },
        "files": _file_entries(gold_root, GOLD_OUTPUTS, base),
        "duration_seconds": round(time.perf_counter() - begin, 3),
    }
    if verify:
        verification["gold"] = gold.verify_run(gold_run)

    # 3. Índice denso.
    begin = time.perf_counter()
    profile = EmbeddingProfile.from_config(retrieval.embedding)
    gold_units_path = gold_root / "knowledge_units.jsonl"
    say(f"índice: {embedder} -> {index_dir}")
    manifest = build_index(
        gold_units_path,
        index_dir,
        build_embedder(profile, kind=embedder),
        profile,
        force=True,
        command=f"pml corpus rebuild --from {from_}",
    )
    stages["index"] = {
        "status": "completed",
        "output": str(index_dir),
        "embedder": embedder,
        "model": manifest.model,
        "counts": {"fragments": manifest.count, "dimension": manifest.dimension},
        "files": _file_entries(index_dir, INDEX_OUTPUTS, base),
        "duration_seconds": round(time.perf_counter() - begin, 3),
    }
    loaded = load_index(index_dir, profile)
    if verify:
        result = verify_index(index_dir, profile, gold_path=gold_units_path)
        verification["index"] = {"passed": result.ok, "messages": list(result.messages)}

    # 4. Colección Qdrant.
    raw_units = _read_units(gold_units_path)
    if qdrant:
        begin = time.perf_counter()
        say(f"qdrant: {qdrant_settings.collection} en {qdrant_settings.location}")
        units_by_id = {key: GoldUnit.from_dict(value) for key, value in raw_units.items()}
        client = open_client(qdrant_settings)
        try:
            written = build_collection(client, qdrant_settings, loaded, units_by_id, force=True)
            ready = collection_matches(client, qdrant_settings, loaded)
        finally:
            client.close()
        stages["qdrant"] = {
            "status": "completed" if ready else "failed",
            "location": qdrant_settings.location,
            "collection": qdrant_settings.collection,
            "hnsw": {
                "m": qdrant_settings.hnsw_m,
                "ef_construct": qdrant_settings.hnsw_ef_construct,
            },
            "counts": {"points": written},
            "duration_seconds": round(time.perf_counter() - begin, 3),
        }
        if verify:
            verification["qdrant"] = {"passed": ready}
    else:
        stages["qdrant"] = {"status": "skipped"}

    provenance = provenance_summary(
        (fragment.unit_id for fragment in loaded.fragments),
        (fragment.url for fragment in loaded.fragments),
        raw_units,
    )
    verification["provenance"] = {
        "passed": provenance["fragments_with_provenance"] == provenance["fragments_total"],
        **provenance,
    }
    passed = all(bool(item.get("passed")) for item in verification.values())
    payload: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "started_at": started_at,
        "finished_at": _now(),
        "duration_seconds": round(time.perf_counter() - started, 3),
        "from": from_,
        "workdir": str(base),
        "in_place": in_place,
        "limit": limit,
        "status": "completed" if passed else "completed_with_failures",
        "stages": stages,
        "verification": verification,
        "fragments_with_provenance": provenance["fragments_with_provenance"],
        "fragments_total": provenance["fragments_total"],
        "git_commit": _git_commit(root),
        "python_version": platform.python_version(),
    }
    manifest_path = base / MANIFEST_NAME if not in_place else gold_root / "rebuild_manifest.json"
    manifest_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    payload["manifest_path"] = str(manifest_path)
    say(f"manifiesto: {manifest_path}")
    return payload
