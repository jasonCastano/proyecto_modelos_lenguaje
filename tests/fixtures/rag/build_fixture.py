"""Regenera el índice de prueba del Módulo 2 con el embedder determinista.

Uso::

    uv run python tests/fixtures/rag/build_fixture.py            # índice general
    uv run python tests/fixtures/rag/build_fixture.py malicious  # adversarial (T052)

El índice resultante (``tests/fixtures/rag/index``) se versiona en Git: es pequeño y permite que la
suite y el modo demostración funcionen sin red ni descarga del modelo real.
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
)
from proyecto_modelos_lenguaje.rag.index import build_index  # noqa: E402

FIXTURE_DIR = Path(__file__).resolve().parent
GOLD_SAMPLE = FIXTURE_DIR / "gold_sample.jsonl"
INDEX_DIR = FIXTURE_DIR / "index"
FIXTURE_SETS = {
    "default": (GOLD_SAMPLE, INDEX_DIR),
    "malicious": (
        FIXTURE_DIR / "malicious" / "gold_malicious.jsonl",
        FIXTURE_DIR / "malicious" / "index",
    ),
}


def main(argv: list[str] | None = None) -> int:
    name = (argv if argv is not None else sys.argv[1:] or ["default"])[0]
    gold, index_dir = FIXTURE_SETS[name]
    config = load_retrieval_config(project_root=ROOT)
    profile = EmbeddingProfile.from_config(config.embedding, created_at="2026-11-06T00:00:00+00:00")
    manifest = build_index(
        gold,
        index_dir,
        HashEmbedder(profile),
        profile,
        force=True,
        command=f"uv run python tests/fixtures/rag/build_fixture.py {name}".strip(),
    )
    print(
        f"índice de prueba: {manifest.count} fragmentos · {manifest.dimension}d · "
        f"{manifest.model} · {index_dir}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
