"""CLI del índice y la recuperación semántica.

Ejemplos::

    uv run python -m proyecto_modelos_lenguaje.rag index build
    uv run python -m proyecto_modelos_lenguaje.rag index verify
    uv run python -m proyecto_modelos_lenguaje.rag search "¿cómo cuida el agua?"
    uv run python -m proyecto_modelos_lenguaje.rag evaluate `
        --questions tests/fixtures/rag/eval_questions.jsonl
"""

from __future__ import annotations

import argparse
import json
from collections.abc import Sequence
from pathlib import Path

from ..config import PROJECT_ROOT
from ..retrieval import (
    RetrievalError,
    load_entity_index,
    load_gold_units,
)
from .config import load_retrieval_config
from .embeddings import EmbeddingProfile, build_embedder
from .errors import (
    EmbeddingError,
    GoldError,
    IndexExistsError,
    IndexInvalidError,
    IndexUnavailableError,
    RetrievalConfigError,
)
from .evaluate import DEFAULT_WARMUP, evaluate_questions, load_questions, render_markdown
from .hybrid import HybridRetriever, RetrievalTrace
from .index import build_index, load_index, verify_index
from .vectorstore import (
    attach_vector_store,
    build_collection,
    collection_matches,
    load_qdrant_settings,
    open_client,
)

GOLD_RELATIVE = Path("data") / "gold" / "knowledge_units.jsonl"


def _profile(config) -> EmbeddingProfile:
    return EmbeddingProfile.from_config(config.embedding)


def _retriever(args, root: Path) -> HybridRetriever:
    config = load_retrieval_config(args.config, project_root=root)
    profile = _profile(config)
    gold_dir = root / "data" / "gold"
    units = load_gold_units(gold_dir)
    try:
        entity_index = load_entity_index(gold_dir)
    except RetrievalError:
        entity_index = None
    notes: list[str] = []
    try:
        index = load_index(config.index_dir, profile)
    except (IndexUnavailableError, IndexInvalidError) as exc:
        index = None
        notes.append(f"Índice no utilizable: {exc}")
    vector_store = None
    if getattr(args, "vector_store", "qdrant") == "qdrant" and args.embedder == "fastembed":
        vector_store, note = attach_vector_store(index, config.source, units)
        if note:
            notes.append(note)
    embedder = build_embedder(profile, kind=args.embedder)
    return HybridRetriever(
        units,
        index=index,
        embedder=embedder,
        entity_index=entity_index,
        config=config,
        notes=tuple(notes),
        vector_store=vector_store,
    )


def _filter_mode(trace: RetrievalTrace, mode: str) -> RetrievalTrace:
    if mode == "hybrid":
        return trace
    if mode == "semantic":
        fragments = tuple(
            fragment for fragment in trace.fragments if fragment.semantic_score is not None
        )
    else:
        fragments = tuple(
            fragment for fragment in trace.fragments if fragment.lexical_score is not None
        )
    return RetrievalTrace(
        mode=mode if fragments else "none",
        semantic_available=trace.semantic_available,
        candidates=len(fragments),
        threshold=trace.threshold,
        fragments=fragments,
        notes=trace.notes,
        elapsed_ms=trace.elapsed_ms,
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="proyecto_modelos_lenguaje.rag")
    parser.add_argument("--config", default=None, help="Ruta a config/retrieval.toml")
    subparsers = parser.add_subparsers(dest="command", required=True)

    index_parser = subparsers.add_parser(
        "index", help="Construye, verifica o reconstruye el índice"
    )
    index_sub = index_parser.add_subparsers(dest="index_command", required=True)
    for name in ("build", "rebuild", "verify"):
        command = index_sub.add_parser(name)
        command.add_argument("--force", action="store_true")
        command.add_argument("--embedder", choices=("fastembed", "hash"), default="fastembed")
        command.add_argument("--json", action="store_true")

    qdrant_parser = subparsers.add_parser(
        "qdrant", help="Carga el índice en Qdrant (HNSW + payload) o muestra su estado"
    )
    qdrant_sub = qdrant_parser.add_subparsers(dest="qdrant_command", required=True)
    qdrant_build = qdrant_sub.add_parser("build")
    qdrant_build.add_argument("--force", action="store_true")
    qdrant_sub.add_parser("status")

    search_parser = subparsers.add_parser("search", help="Muestra la traza de recuperación")
    search_parser.add_argument("question")
    search_parser.add_argument(
        "--mode", choices=("hybrid", "semantic", "lexical"), default="hybrid"
    )
    search_parser.add_argument("--k", type=int, default=8)
    search_parser.add_argument("--embedder", choices=("fastembed", "hash"), default="fastembed")
    search_parser.add_argument(
        "--vector-store",
        choices=("qdrant", "numpy"),
        default="qdrant",
        help="Qdrant si la colección existe; numpy fuerza la matriz en memoria.",
    )
    search_parser.add_argument("--json", action="store_true")

    evaluate_parser = subparsers.add_parser("evaluate", help="Compara modos y escribe el informe")
    evaluate_parser.add_argument("--questions", required=True)
    evaluate_parser.add_argument("--out", default=None)
    evaluate_parser.add_argument("--json-out", default=None)
    evaluate_parser.add_argument("--embedder", choices=("fastembed", "hash"), default="fastembed")
    evaluate_parser.add_argument(
        "--vector-store",
        choices=("qdrant", "numpy"),
        default="qdrant",
        help="Qdrant si la colección existe; numpy fuerza la matriz en memoria.",
    )
    evaluate_parser.add_argument("--top-k", type=int, default=12)
    evaluate_parser.add_argument("--run-id", default="")
    evaluate_parser.add_argument(
        "--warmup",
        type=int,
        default=DEFAULT_WARMUP,
        help="Consultas descartadas por modo antes de medir latencia.",
    )
    return parser


def _print_trace(trace: RetrievalTrace, *, as_json: bool) -> None:
    payload = trace.to_dict()
    if as_json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        return
    print(f"modo: {trace.mode} · semántica disponible: {trace.semantic_available}")
    print(f"umbral: {trace.threshold:.2f} · candidatos: {trace.candidates}")
    for note in trace.notes:
        print(f"aviso: {note}")
    for fragment in trace.fragments:
        origin = fragment.origin
        score = fragment.score
        status = fragment.status
        reason = f" ({fragment.reason})" if fragment.reason else ""
        print(f"- {fragment.unit_id} [{status}] {score:.3f} {origin}{reason} · {fragment.title}")


def _probe_latency(client, settings, index) -> str:
    """Tiempo de una consulta top-10 y si el índice ANN (HNSW) está en juego."""
    import time

    from .vectorstore import QdrantVectorStore

    store = QdrantVectorStore(client, settings)
    store.search(index.vectors[0], limit=10)  # calentamiento
    runs = 5
    start = time.perf_counter()
    for row in range(runs):
        store.search(index.vectors[row], limit=10)
    elapsed = (time.perf_counter() - start) * 1000 / runs
    search = (
        f"HNSW (ANN) con hnsw_ef={settings.hnsw_ef}"
        if settings.url
        else "búsqueda exacta (modo local embebido; HNSW solo con QDRANT_URL)"
    )
    return f"consulta: {search} · {elapsed:.1f} ms por consulta top-10"


def _qdrant_command(args, config, root: Path) -> int:
    """``rag qdrant build|status``: la colección de Qdrant a partir del índice versionado."""
    settings = load_qdrant_settings(config.source)
    try:
        index = load_index(config.index_dir, _profile(config))
    except (IndexUnavailableError, IndexInvalidError) as exc:
        print(f"índice no utilizable: {exc}")
        return 5
    try:
        client = open_client(settings)
    except Exception as exc:
        print(f"Qdrant no disponible en {settings.location}: {exc}")
        return 6
    try:
        if args.qdrant_command == "status":
            ready = collection_matches(client, settings, index)
            state = "lista" if ready else "ausente o desactualizada"
            print(f"colección {settings.collection} en {settings.location}: {state}")
            if ready:
                info = client.get_collection(settings.collection)
                hnsw = info.config.hnsw_config
                print(
                    f"puntos: {index.manifest.count} · dimensión {index.manifest.dimension} · "
                    f"coseno · HNSW m={hnsw.m} ef_construct={hnsw.ef_construct}"
                )
                print(_probe_latency(client, settings, index))
            return 0 if ready else 2
        units = {unit.unit_id: unit for unit in load_gold_units(root / "data" / "gold")}

        def progress(done: int, total: int) -> None:
            print(f"\r  {done}/{total} fragmentos", end="", flush=True)

        written = build_collection(
            client, settings, index, units, force=args.force, progress=progress
        )
        if written:
            print()
            print(f"colección {settings.collection} lista en {settings.location}: {written} puntos")
        else:
            print(f"colección {settings.collection} ya estaba al día ({settings.location})")
        return 0
    finally:
        client.close()


def main(argv: Sequence[str] | None = None, *, project_root: Path | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(list(argv) if argv is not None else None)
    root = Path(project_root) if project_root is not None else PROJECT_ROOT
    gold_path = root / GOLD_RELATIVE

    try:
        config = load_retrieval_config(args.config, project_root=root)
    except RetrievalConfigError as exc:
        print(f"error de configuración: {exc}")
        return 5

    if args.command == "index":
        profile = _profile(config)
        if args.index_command == "verify":
            result = verify_index(config.index_dir, profile, gold_path=gold_path)
            for message in result.messages:
                print(message)
            return 0 if result.ok else result.code
        try:
            embedder = build_embedder(profile, kind=args.embedder)
            manifest = build_index(
                gold_path,
                config.index_dir,
                embedder,
                profile,
                force=args.index_command == "rebuild" or args.force,
                command=(
                    f"uv run python -m proyecto_modelos_lenguaje.rag index {args.index_command}"
                ),
            )
        except IndexExistsError as exc:
            print(str(exc))
            return 2
        except GoldError as exc:
            print(f"error de oro: {exc}")
            return 3
        except EmbeddingError as exc:
            print(f"error de embeddings: {exc}")
            return 4
        except IndexInvalidError as exc:
            print(f"índice inválido: {exc}")
            return 5
        if args.json:
            print(json.dumps(manifest.to_dict(), ensure_ascii=False, indent=2))
        else:
            print(
                f"índice listo en {config.index_dir} · {manifest.model} · "
                f"{manifest.dimension}d · {manifest.count} fragmentos"
            )
        return 0

    if args.command == "qdrant":
        return _qdrant_command(args, config, root)

    try:
        retriever = _retriever(args, root)
    except (IndexUnavailableError, IndexInvalidError) as exc:
        print(f"índice no utilizable: {exc}")
        return 5
    except (GoldError, RetrievalError) as exc:
        print(f"error de oro: {exc}")
        return 3

    if args.command == "search":
        trace = _filter_mode(retriever.retrieve(args.question, top_k=args.k), args.mode)
        _print_trace(trace, as_json=args.json)
        return 0

    try:
        questions = load_questions(args.questions)
    except (OSError, ValueError) as exc:
        print(f"error en el conjunto de evaluación: {exc}")
        return 3
    run = evaluate_questions(
        retriever,
        questions,
        top_k=args.top_k,
        run_id=args.run_id or "local",
        warmup=args.warmup,
    )
    notes = [
        "La cobertura de citas mide la disponibilidad de evidencia por pregunta; la fidelidad "
        "requiere generación y revisión manual (ver informe).",
        "Evaluación de recuperación: no se invocó al LLM.",
    ]
    markdown = render_markdown(run, extra_notes=notes)
    if args.out:
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(markdown, encoding="utf-8")
        print(f"informe escrito en {args.out}")
    if args.json_out:
        Path(args.json_out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.json_out).write_text(
            json.dumps(run.to_dict(), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
        print(f"JSON escrito en {args.json_out}")
    if not args.out and not args.json_out:
        print(markdown)
    print(run.verdict)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
