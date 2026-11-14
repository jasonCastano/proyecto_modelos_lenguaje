"""Barrido corto de top-k semántico y peso α de la fusión híbrida sobre Qdrant (rúbrica 4.2).

Uso::

    uv run python scripts/sweep_retrieval.py [--config config/retrieval.toml]

Para cada combinación de ``semantic_top_k`` ∈ {5, 8, 12} y ``weight_semantic`` (α) ∈ {0,5; 0,65;
0,8} escribe una copia temporal de la configuración y corre ``rag evaluate`` sobre las 40 preguntas
de ``tests/fixtures/rag/eval_questions.jsonl``. Guarda ``docs/barrido_retrieval.json`` con las
métricas del modo híbrido (Recall@10, nDCG@10, MRR y latencia).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TOP_K = (5, 8, 12)
ALPHAS = (0.5, 0.65, 0.8)


def _variant(base: str, top_k: int, alpha: float) -> str:
    text = re.sub(r"(?m)^semantic_top_k = \d+", f"semantic_top_k = {top_k}", base)
    text = re.sub(r"(?m)^weight_semantic = [\d.]+", f"weight_semantic = {alpha}", text)
    return re.sub(r"(?m)^weight_lexical = [\d.]+", f"weight_lexical = {round(1 - alpha, 2)}", text)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--config", default=str(ROOT / "config" / "retrieval.toml"))
    parser.add_argument("--out", default=str(ROOT / "docs" / "barrido_retrieval.json"))
    args = parser.parse_args()
    base = Path(args.config).read_text(encoding="utf-8")
    env = {**os.environ, "PYTHONIOENCODING": "utf-8"}
    rows = []
    with tempfile.TemporaryDirectory() as tmp:
        for top_k in TOP_K:
            for alpha in ALPHAS:
                config = Path(tmp) / f"retrieval_k{top_k}_a{alpha}.toml"
                config.write_text(_variant(base, top_k, alpha), encoding="utf-8")
                result = Path(tmp) / f"k{top_k}_a{alpha}.json"
                subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "proyecto_modelos_lenguaje.rag",
                        "--config",
                        str(config),
                        "evaluate",
                        "--questions",
                        str(ROOT / "tests/fixtures/rag/eval_questions.jsonl"),
                        "--vector-store",
                        "qdrant",
                        "--out",
                        str(Path(tmp) / "report.md"),
                        "--json-out",
                        str(result),
                        "--run-id",
                        f"sweep-k{top_k}-a{alpha}",
                    ],
                    check=True,
                    cwd=ROOT,
                    env=env,
                    capture_output=True,
                )
                hybrid = json.loads(result.read_text(encoding="utf-8"))["modes"]["hybrid"]
                row = {
                    "semantic_top_k": top_k,
                    "alpha": alpha,
                    "recall_at_10": hybrid["recall_at_k"]["10"],
                    "ndcg_at_10": hybrid["ndcg_at_10"],
                    "mrr": hybrid["mrr"],
                    "latency_ms_mean": hybrid["latency_ms"]["mean"],
                }
                rows.append(row)
                print(json.dumps(row), flush=True)
    Path(args.out).write_text(
        json.dumps({"questions": 40, "vector_store": "qdrant", "rows": rows}, indent=2) + "\n",
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
