"""Proyección 2D (t-SNE) de los embeddings del índice y de las consultas de evaluación.

Spec 024 (US5, T072, research R16). Toma una muestra estratificada por ``topic_id`` (≤ ``sample``)
de los fragmentos indexados, le añade los embeddings de las consultas (con el prefijo de consulta
del perfil) y proyecta todo junto con t-SNE (``perplexity=30`` acotada por debajo del número de
puntos, ``init="pca"``, ``random_state=seed``). Los fragmentos se colorean por tema y las consultas
con Recall@10 = 0 se marcan como fallidas.

Salidas: ``proyeccion_embeddings.png`` (Agg, < 1 MB) y ``proyeccion_embeddings.json`` con los
puntos ``{id, kind, x, y, topic_id, unit_id, recall_at_10, failed}``.

``project`` es pura (recibe los vectores ya calculados) para poder probarla sin modelo ni índice.
"""

from __future__ import annotations

import json
from collections import defaultdict
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import numpy as np

DEFAULT_SAMPLE = 5000
DEFAULT_SEED = 2026
DEFAULT_PERPLEXITY = 30.0
PNG_NAME = "proyeccion_embeddings.png"
JSON_NAME = "proyeccion_embeddings.json"
RECALL_K = 10


@dataclass(frozen=True, slots=True)
class ProjectionPoint:
    """Punto de la proyección (data-model §10)."""

    id: str
    kind: str  # fragment | query
    x: float
    y: float
    topic_id: str
    unit_id: str | None = None
    recall_at_10: float | None = None
    failed: bool | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True, slots=True)
class FragmentInfo:
    id: str
    unit_id: str
    topic_id: str


@dataclass(frozen=True, slots=True)
class QueryInfo:
    id: str
    topic_id: str
    recall_at_10: float | None = None


def stratified_sample(topics: Sequence[str], sample: int, seed: int) -> list[int]:
    """Índices de una muestra estratificada por tema (asignación proporcional, ≥ 1 por tema)."""
    total = len(topics)
    if sample <= 0:
        return []
    if total <= sample:
        return list(range(total))
    groups: dict[str, list[int]] = defaultdict(list)
    for position, topic in enumerate(topics):
        groups[topic].append(position)
    names = sorted(groups)
    shares = {name: len(groups[name]) * sample / total for name in names}
    quotas = {name: min(len(groups[name]), max(1, int(shares[name]))) for name in names}
    # Resto mayor: reparte lo que falta por la parte fraccionaria (y quita a los más grandes si
    # el mínimo de 1 por tema se pasó de la muestra).
    by_remainder = sorted(names, key=lambda name: (-(shares[name] % 1), name))
    while sum(quotas.values()) < sample:
        grown = False
        for name in by_remainder:
            if sum(quotas.values()) >= sample:
                break
            if quotas[name] < len(groups[name]):
                quotas[name] += 1
                grown = True
        if not grown:
            break
    by_size = sorted(names, key=lambda name: (-quotas[name], name))
    while sum(quotas.values()) > sample and quotas[by_size[0]] > 1:
        quotas[by_size[0]] -= 1
        by_size.sort(key=lambda name: (-quotas[name], name))
    rng = np.random.default_rng(seed)
    chosen: list[int] = []
    for name in names:
        members = np.asarray(groups[name])
        picked = rng.choice(members, size=min(quotas[name], len(members)), replace=False)
        chosen.extend(int(item) for item in picked)
    return sorted(chosen)


def project(
    fragment_vectors: np.ndarray,
    fragments: Sequence[FragmentInfo],
    query_vectors: np.ndarray,
    queries: Sequence[QueryInfo],
    *,
    sample: int = DEFAULT_SAMPLE,
    seed: int = DEFAULT_SEED,
    perplexity: float = DEFAULT_PERPLEXITY,
) -> list[ProjectionPoint]:
    """t-SNE conjunta de una muestra de fragmentos y de todas las consultas."""
    from sklearn.manifold import TSNE

    fragment_vectors = np.asarray(fragment_vectors, dtype=np.float64)
    query_vectors = np.asarray(query_vectors, dtype=np.float64).reshape(len(queries), -1)
    if len(fragment_vectors) != len(fragments):
        raise ValueError("fragment_vectors y fragments deben tener la misma longitud")
    if (
        len(fragment_vectors)
        and query_vectors.size
        and (fragment_vectors.shape[1] != query_vectors.shape[1])
    ):
        raise ValueError("los vectores de fragmentos y consultas tienen dimensiones distintas")
    chosen = stratified_sample([item.topic_id for item in fragments], sample, seed)
    matrix = np.vstack([fragment_vectors[chosen], query_vectors]) if chosen else query_vectors
    total = len(matrix)
    if total < 3:
        raise ValueError("se necesitan al menos 3 puntos para la proyección")
    effective = float(min(perplexity, max(1.0, total - 1.0)))
    coordinates = TSNE(
        n_components=2,
        perplexity=effective,
        init="pca",
        random_state=seed,
        learning_rate="auto",
    ).fit_transform(matrix)
    points: list[ProjectionPoint] = []
    for row, position in enumerate(chosen):
        info = fragments[position]
        x, y = coordinates[row]
        points.append(
            ProjectionPoint(
                id=info.id,
                kind="fragment",
                x=round(float(x), 4),
                y=round(float(y), 4),
                topic_id=info.topic_id,
                unit_id=info.unit_id,
            )
        )
    offset = len(chosen)
    for row, info in enumerate(queries):
        x, y = coordinates[offset + row]
        recall = info.recall_at_10
        points.append(
            ProjectionPoint(
                id=info.id,
                kind="query",
                x=round(float(x), 4),
                y=round(float(y), 4),
                topic_id=info.topic_id,
                recall_at_10=None if recall is None else round(float(recall), 4),
                failed=None if recall is None else recall == 0.0,
            )
        )
    return points


def render_png(points: Sequence[ProjectionPoint], path: Path, *, title: str) -> Path:
    """Figura con fragmentos coloreados por tema y consultas (fallidas en rojo con borde)."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    topics = sorted({point.topic_id for point in points})
    palette = plt.get_cmap("tab20")
    colors = {topic: palette(number % 20) for number, topic in enumerate(topics)}
    figure, axis = plt.subplots(figsize=(10, 7.5), dpi=100)
    for topic in topics:
        members = [p for p in points if p.kind == "fragment" and p.topic_id == topic]
        if members:
            axis.scatter(
                [p.x for p in members],
                [p.y for p in members],
                s=6,
                alpha=0.55,
                color=colors[topic],
                label=topic or "(sin tema)",
                linewidths=0,
            )
    queries = [p for p in points if p.kind == "query"]
    passed = [p for p in queries if not p.failed]
    failed = [p for p in queries if p.failed]
    if passed:
        axis.scatter(
            [p.x for p in passed],
            [p.y for p in passed],
            s=90,
            marker="*",
            color=[colors[p.topic_id] for p in passed],
            edgecolors="black",
            linewidths=0.8,
            label="consulta",
        )
    if failed:
        axis.scatter(
            [p.x for p in failed],
            [p.y for p in failed],
            s=90,
            marker="X",
            color="#d62728",
            edgecolors="black",
            linewidths=0.8,
            label="consulta fallida (Recall@10 = 0)",
        )
    for point in queries:
        axis.annotate(
            point.id, (point.x, point.y), fontsize=6, xytext=(3, 3), textcoords="offset points"
        )
    axis.set_title(title, fontsize=11)
    axis.set_xticks([])
    axis.set_yticks([])
    axis.legend(loc="center left", bbox_to_anchor=(1.01, 0.5), fontsize=7, frameon=False)
    figure.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    figure.savefig(path, format="png", dpi=100)
    plt.close(figure)
    return path


def write_outputs(
    points: Sequence[ProjectionPoint],
    out_dir: str | Path,
    *,
    metadata: Mapping[str, Any] | None = None,
) -> tuple[Path, Path]:
    """Escribe ``proyeccion_embeddings.{png,json}`` en ``out_dir``."""
    directory = Path(out_dir)
    directory.mkdir(parents=True, exist_ok=True)
    info = dict(metadata or {})
    fragments = sum(1 for point in points if point.kind == "fragment")
    queries = [point for point in points if point.kind == "query"]
    failed = sum(1 for point in queries if point.failed)
    title = (
        f"t-SNE de {fragments} fragmentos y {len(queries)} consultas "
        f"(semilla {info.get('seed', DEFAULT_SEED)}; {failed} fallidas)"
    )
    png = render_png(points, directory / PNG_NAME, title=title)
    payload = {
        **info,
        "fragments": fragments,
        "queries": len(queries),
        "failed_queries": failed,
        "points": [point.to_dict() for point in points],
    }
    target = directory / JSON_NAME
    target.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    return png, target


def dense_recall_at_10(
    query_vectors: np.ndarray,
    expected: Sequence[Sequence[str]],
    index_vectors: np.ndarray,
    index_unit_ids: Sequence[str],
) -> list[float]:
    """Recall@10 denso (coseno sobre la matriz normalizada) cuando no hay evaluación previa."""
    results: list[float] = []
    matrix = np.asarray(index_vectors, dtype=np.float32)
    for vector, wanted in zip(np.asarray(query_vectors, dtype=np.float32), expected, strict=True):
        scores = matrix @ vector
        ranked: list[str] = []
        for position in np.argsort(-scores):
            unit_id = index_unit_ids[int(position)]
            if unit_id not in ranked:
                ranked.append(unit_id)
            if len(ranked) == RECALL_K:
                break
        target = set(wanted)
        results.append(len(target.intersection(ranked)) / len(target) if target else 0.0)
    return results


def load_eval_recalls(path: str | Path, mode: str = "hybrid") -> dict[str, float]:
    """Recall@10 por consulta desde ``docs/evaluacion_modulo3.json`` (``per_query``)."""
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = payload.get("per_query") or []
    return {str(row["id"]): float(row["recall_at_10"]) for row in rows}


def run_projection(
    *,
    index_dir: Path,
    queries_path: Path,
    gold_path: Path | None,
    embedder: Any,
    profile: Any,
    out_dir: Path,
    sample: int = DEFAULT_SAMPLE,
    seed: int = DEFAULT_SEED,
    perplexity: float = DEFAULT_PERPLEXITY,
    eval_path: Path | None = None,
) -> tuple[list[ProjectionPoint], Path, Path]:
    """Carga índice y consultas, calcula Recall@10 si falta, proyecta y escribe las salidas."""
    from .index import load_index

    index = load_index(index_dir, profile)
    topics_by_unit: dict[str, str] = {}
    if gold_path is not None and gold_path.is_file():
        with gold_path.open(encoding="utf-8") as handle:
            for line in handle:
                if line.strip():
                    unit = json.loads(line)
                    topics_by_unit[str(unit.get("unit_id", ""))] = str(unit.get("topic_id", ""))
    fragments = [
        FragmentInfo(
            id=fragment.fragment_id,
            unit_id=fragment.unit_id,
            topic_id=topics_by_unit.get(fragment.unit_id) or fragment.topic or "",
        )
        for fragment in index.fragments
    ]
    rows = [
        json.loads(line)
        for line in queries_path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    query_vectors = np.vstack([embedder.embed_query(str(row["question"])) for row in rows])
    if eval_path is not None:
        recalls_by_id = load_eval_recalls(eval_path)
        recalls = [recalls_by_id.get(str(row["id"])) for row in rows]
        source = f"evaluación {eval_path.as_posix()} (híbrido)"
    else:
        recalls = list(
            dense_recall_at_10(
                query_vectors,
                [row.get("expected_unit_ids") or [] for row in rows],
                index.vectors,
                [fragment.unit_id for fragment in index.fragments],
            )
        )
        source = "denso (coseno sobre el índice)"
    queries = [
        QueryInfo(
            id=str(row["id"]),
            topic_id=str(row.get("topic_id", "")),
            recall_at_10=recall,
        )
        for row, recall in zip(rows, recalls, strict=True)
    ]
    points = project(
        index.vectors,
        fragments,
        query_vectors,
        queries,
        sample=sample,
        seed=seed,
        perplexity=perplexity,
    )
    png, target = write_outputs(
        points,
        out_dir,
        metadata={
            "method": "t-SNE",
            "seed": seed,
            "perplexity": perplexity,
            "init": "pca",
            "sample": sample,
            "index_fragments": len(index.fragments),
            "model": index.manifest.model,
            "queries_path": queries_path.as_posix(),
            "recall_source": source,
        },
    )
    return points, png, target
