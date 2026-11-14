"""Regenera los índices de prueba del Módulo 2.

Uso::

    uv run python tests/fixtures/rag/build_fixture.py                   # índice general (hash)
    uv run python tests/fixtures/rag/build_fixture.py malicious         # adversarial, hash (demo)
    uv run python tests/fixtures/rag/build_fixture.py malicious --real  # adversarial, fastembed

Los índices hash (``index/``) usan el embedder determinista: son pequeños y permiten que la suite y
el modo demostración funcionen sin red ni descarga del modelo real. ``--real`` construye el índice
con el modelo de embeddings real (``index_real/``) para que el corpus adversarial funcione también
con el modelo de lenguaje real (spec 015, research R2). Todos se versionan en Git.
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))

from proyecto_modelos_lenguaje.rag.config import load_retrieval_config  # noqa: E402
from proyecto_modelos_lenguaje.rag.embeddings import (  # noqa: E402
    EmbeddingProfile,
    HashEmbedder,
    build_embedder,
)
from proyecto_modelos_lenguaje.rag.index import build_index  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent
GOLD_SAMPLE = FIXTURE_DIR / "gold_sample.jsonl"
INDEX_DIR = FIXTURE_DIR / "index"
MALICIOUS_DIR = FIXTURE_DIR / "malicious"
FIXTURE_SETS = {
    "default": (GOLD_SAMPLE, INDEX_DIR),
    "malicious": (MALICIOUS_DIR / "gold_malicious.jsonl", MALICIOUS_DIR / "index"),
}
REAL_INDEX_DIRS = {"malicious": MALICIOUS_DIR / "index_real"}


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    real = "--real" in args
    names = [arg for arg in args if arg != "--real"] or ["default"]
    name = names[0]
    gold, index_dir = FIXTURE_SETS[name]
    if real:
        if name not in REAL_INDEX_DIRS:
            print(f"--real solo está disponible para: {', '.join(REAL_INDEX_DIRS)}")
            return 2
        index_dir = REAL_INDEX_DIRS[name]
    config = load_retrieval_config(project_root=ROOT)
    profile = EmbeddingProfile.from_config(config.embedding, created_at="2026-11-06T00:00:00+00:00")
    embedder = build_embedder(profile, kind="fastembed") if real else HashEmbedder(profile)
    suffix = " --real" if real else ""
    manifest = build_index(
        gold,
        index_dir,
        embedder,
        profile,
        force=True,
        command=f"uv run python tests/fixtures/rag/build_fixture.py {name}{suffix}".strip(),
    )
    print(
        f"índice de prueba: {manifest.count} fragmentos · {manifest.dimension}d · "
        f"{manifest.model} · {'fastembed' if real else 'hash'} · {index_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
