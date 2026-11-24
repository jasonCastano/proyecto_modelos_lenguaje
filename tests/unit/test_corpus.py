"""Spec 024 (US5, T065): ``pml corpus rebuild`` en un directorio de trabajo, sin tocar ``data/``."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from proyecto_modelos_lenguaje import cli
from proyecto_modelos_lenguaje.config import PROJECT_ROOT
from proyecto_modelos_lenguaje.corpus import (
    CorpusError,
    default_workdir,
    has_provenance,
    provenance_summary,
    rebuild,
)
from tests.gold_helpers import make_chunk, make_document, write_silver

SILVER_FIXTURES = PROJECT_ROOT / "tests" / "fixtures" / "silver"
CONFIGS = {
    "sources_config": PROJECT_ROOT / "config" / "sources.toml",
    "silver_config": PROJECT_ROOT / "config" / "silver.toml",
    "gold_config": PROJECT_ROOT / "config" / "gold.toml",
    "taxonomy": PROJECT_ROOT / "config" / "gold_taxonomy.toml",
    "retrieval_config": PROJECT_ROOT / "config" / "retrieval.toml",
}
TEXTS = (
    "Manuelita es una organización agroindustrial diversificada con sede en el Valle del Cauca. "
    "La compañía produce azúcar, etanol y biocombustibles para Colombia y otros países. "
    "Su misión es generar progreso y bienestar en las comunidades donde opera.",
    "En la plataforma palma, Manuelita logró eliminar los vertimientos de aguas residuales. "
    "Los efluentes se aprovechan como fertilizantes orgánicos en las plantaciones de palma. "
    "La empresa reporta indicadores de sostenibilidad en su informe anual de gestión.",
)


def _versioned_snapshot() -> dict[str, tuple[int, int]]:
    """mtime y tamaño de las salidas versionadas que la reconstrucción no debe tocar."""
    snapshot: dict[str, tuple[int, int]] = {}
    for folder in ("data/silver", "data/gold", "data/module2/index", "data/bronze/_meta"):
        directory = PROJECT_ROOT / folder
        if not directory.is_dir():
            continue
        for path in directory.iterdir():
            # -shm/-wal de SQLite cambian con cualquier lector; no son salidas versionadas.
            if path.is_file() and not path.name.endswith(("-shm", "-wal")):
                stat = path.stat()
                snapshot[path.as_posix()] = (stat.st_mtime_ns, stat.st_size)
    return snapshot


def _silver_fixture(root: Path) -> Path:
    documents = []
    chunks = []
    for number, text in enumerate(TEXTS):
        doc_id = f"doc_{number:016x}"
        url = f"https://www.manuelita.com/pagina-{number}"
        documents.append(
            make_document(doc_id, title=f"Manuelita {number}", url=url, text_hash=f"{number}" * 64)
        )
        chunks.append(
            make_chunk(
                doc_id,
                chunk_id=f"{doc_id}-s000-c0000",
                text=text,
                title=f"Manuelita {number}",
                url=url,
                section_title=f"Sección {number}",
            )
        )
    return write_silver(root, documents, chunks)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def test_rebuild_from_silver_writes_workdir_and_manifest(tmp_path: Path) -> None:
    silver = _silver_fixture(tmp_path / "input")
    silver_before = _sha(silver / "chunks.jsonl")
    versioned_before = _versioned_snapshot()
    workdir = tmp_path / "work"
    messages: list[str] = []

    manifest = rebuild(
        from_="silver",
        workdir=workdir,
        silver_input=silver,
        embedder="hash",
        project_root=tmp_path,
        progress=messages.append,
        **CONFIGS,
    )

    # Etapas en orden: plata → oro → índice → Qdrant.
    assert list(manifest["stages"]) == ["silver", "gold", "index", "qdrant"]
    assert [message.split(":")[0] for message in messages[:4]] == [
        "plata",
        "oro",
        "índice",
        "qdrant",
    ]
    assert manifest["status"] == "completed", manifest["verification"]
    assert manifest["from"] == "silver"
    assert Path(manifest["workdir"]) == workdir.resolve()
    for key in ("run_id", "started_at", "finished_at", "git_commit", "python_version"):
        assert key in manifest
    assert manifest["stages"]["silver"]["status"] == "reused"
    assert manifest["stages"]["gold"]["counts"]["units"] >= 3
    assert manifest["stages"]["index"]["counts"]["fragments"] >= 3
    assert manifest["stages"]["qdrant"]["status"] == "completed"
    assert manifest["fragments_total"] == manifest["stages"]["index"]["counts"]["fragments"]
    assert manifest["fragments_with_provenance"] == manifest["fragments_total"]

    # El manifiesto se escribe en el workdir y sus hashes corresponden a los archivos.
    written = json.loads((workdir / "manifest.json").read_text(encoding="utf-8"))
    assert written["run_id"] == manifest["run_id"]
    for stage in ("gold", "index"):
        files = written["stages"][stage]["files"]
        assert files
        for entry in files:
            assert _sha(workdir / entry["path"]) == entry["sha256"]
    assert (workdir / "gold" / "knowledge_units.jsonl").is_file()
    assert (workdir / "index" / "vectors.npy").is_file()
    assert (workdir / "qdrant").is_dir()

    # La plata de entrada y las capas versionadas no cambian.
    assert _sha(silver / "chunks.jsonl") == silver_before
    assert _versioned_snapshot() == versioned_before


def test_rebuild_from_bronze_builds_silver_in_workdir(silver_env, tmp_path: Path) -> None:
    html = (SILVER_FIXTURES / "sample.html").read_bytes()
    silver_env.add(html, media_type="text/html", url="https://www.manuelita.com/a", title="A")
    versioned_before = _versioned_snapshot()
    workdir = tmp_path / "work"

    manifest = rebuild(
        from_="bronze",
        workdir=workdir,
        embedder="hash",
        qdrant=False,
        project_root=silver_env.root,
        **CONFIGS,
    )

    silver_stage = manifest["stages"]["silver"]
    assert silver_stage["source"] == "bronze"
    assert silver_stage["counts"]["input_artifacts"] == 1
    assert (workdir / "silver" / "documents.jsonl").is_file()
    assert manifest["verification"]["silver"]["passed"], manifest["verification"]["silver"]
    assert manifest["stages"]["qdrant"] == {"status": "skipped"}
    # Nada se escribió en la plata del proyecto temporal ni en la versionada.
    assert not (silver_env.root / "data" / "silver").exists()
    assert _versioned_snapshot() == versioned_before


def test_in_place_requires_explicit_confirmation(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="--confirm"):
        rebuild(from_="silver", in_place=True, project_root=tmp_path, **CONFIGS)
    assert cli.main(["corpus", "rebuild", "--from", "silver", "--in-place"]) == 2


def test_rejects_workdir_inside_data_and_non_empty(tmp_path: Path) -> None:
    (tmp_path / "data").mkdir()
    with pytest.raises(CorpusError, match="dentro de"):
        rebuild(from_="silver", workdir=tmp_path / "data" / "x", project_root=tmp_path, **CONFIGS)
    busy = tmp_path / "busy"
    busy.mkdir()
    (busy / "f.txt").write_text("x", encoding="utf-8")
    with pytest.raises(CorpusError, match="no está vacío"):
        rebuild(from_="silver", workdir=busy, project_root=tmp_path, **CONFIGS)


def test_scrape_requires_campaign(tmp_path: Path) -> None:
    with pytest.raises(CorpusError, match="--campaign"):
        rebuild(from_="bronze", workdir=tmp_path / "w", scrape=True, project_root=tmp_path)


def test_default_workdir_is_in_temp() -> None:
    assert default_workdir("rebuild-20261123T000000Z").name == "pml-rebuild-20261123T000000Z"


def test_provenance_rules() -> None:
    web = {"unit_id": "unit_a", "url": "https://x", "section_path": ["Inicio"]}
    pdf = {"unit_id": "unit_b", "url": "https://x.pdf", "page_start": 3, "section_path": []}
    bare = {"unit_id": "unit_c", "url": "", "section_path": ["Inicio"]}
    assert has_provenance(web) and has_provenance(pdf)
    assert not has_provenance(bare) and not has_provenance(None)
    summary = provenance_summary(
        ["unit_a", "unit_b", "unit_c", "unit_z"],
        ["https://x", "https://x.pdf", "https://y", "https://z"],
        {"unit_a": web, "unit_b": pdf, "unit_c": bare},
    )
    assert summary == {
        "fragments_total": 4,
        "fragments_with_provenance": 2,
        "fragments_with_page_or_time": 1,
    }
