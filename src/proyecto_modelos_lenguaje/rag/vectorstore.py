"""Base vectorial Qdrant para la recuperación semántica (Módulo 2, ADR 0018).

El índice versionado de la spec 013 (``vectors.npy`` + ``index.sqlite3``) sigue siendo la fuente:
``build_collection`` lo carga en una colección de Qdrant con índice **HNSW** y *payload* por
fragmento (unidad, título, URL, tema, autoridad y tipo). La consulta usa ``query_points`` con
filtro por *payload* en una sola etapa (*single-stage filtering*), sin sobremuestrear.

Dos formas de conexión, sin cambiar el código:

- ``QDRANT_URL`` definido → servidor Qdrant (Docker o binario); usa el índice HNSW (ANN).
- Sin ``QDRANT_URL`` → modo local embebido en ``[qdrant] path`` (por defecto
  ``data/module2/qdrant``, fuera de Git). El modo local guarda la misma colección y filtros, pero
  busca de forma exacta; sirve para desarrollo y pruebas sin servidor.

Si la colección no existe o no coincide con el índice, la recuperación vuelve a la matriz
``numpy`` y lo deja anotado en la traza: la aplicación nunca falla por la base vectorial.
"""

from __future__ import annotations

import os
import tomllib
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any

import numpy as np

from ..config import PROJECT_ROOT
from .index import LoadedIndex

if TYPE_CHECKING:
    from qdrant_client import QdrantClient

    from ..retrieval import GoldUnit

URL_ENV = "QDRANT_URL"
API_KEY_ENV = "QDRANT_API_KEY"
PAYLOAD_INDEXES = ("unit_id", "topic_id", "authority", "unit_type")
UPLOAD_BATCH = 512


@dataclass(frozen=True, slots=True)
class QdrantSettings:
    """Sección ``[qdrant]`` de ``config/retrieval.toml``."""

    enabled: bool = True
    path: Path = PROJECT_ROOT / "data" / "module2" / "qdrant"
    collection: str = "manuelita_fragments"
    hnsw_m: int = 16
    hnsw_ef_construct: int = 128
    hnsw_ef: int = 128
    url: str | None = None

    @property
    def location(self) -> str:
        """Descripción legible de dónde vive la colección."""
        return self.url or f"local:{_display(self.path)}"


def _display(path: Path) -> str:
    try:
        return path.relative_to(PROJECT_ROOT).as_posix()
    except ValueError:
        return str(path)


def load_qdrant_settings(config_source: Path | None = None) -> QdrantSettings:
    """Lee ``[qdrant]`` (opcional) y ``QDRANT_URL``; lo ausente toma el valor por defecto."""
    raw: dict[str, Any] = {}
    if config_source is not None and config_source.is_file():
        raw = tomllib.loads(config_source.read_text(encoding="utf-8")).get("qdrant", {}) or {}
    defaults = QdrantSettings()
    path = Path(str(raw.get("path", defaults.path)))
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return QdrantSettings(
        enabled=bool(raw.get("enabled", defaults.enabled)),
        path=path,
        collection=str(raw.get("collection", defaults.collection)),
        hnsw_m=int(raw.get("hnsw_m", defaults.hnsw_m)),
        hnsw_ef_construct=int(raw.get("hnsw_ef_construct", defaults.hnsw_ef_construct)),
        hnsw_ef=int(raw.get("hnsw_ef", defaults.hnsw_ef)),
        url=os.environ.get(URL_ENV) or None,
    )


def open_client(settings: QdrantSettings, *, in_memory: bool = False) -> QdrantClient:
    """Cliente de Qdrant: servidor si hay ``QDRANT_URL``; si no, modo local embebido."""
    from qdrant_client import QdrantClient

    if in_memory:
        return QdrantClient(location=":memory:")
    if settings.url:
        return QdrantClient(url=settings.url, api_key=os.environ.get(API_KEY_ENV) or None)
    settings.path.mkdir(parents=True, exist_ok=True)
    return QdrantClient(path=str(settings.path))


def fragment_payload(
    position: int, index: LoadedIndex, units_by_id: Mapping[str, GoldUnit]
) -> dict[str, Any]:
    """Payload filtrable de un fragmento del índice."""
    fragment = index.fragments[position]
    unit = units_by_id.get(fragment.unit_id)
    return {
        "position": position,
        "fragment_id": fragment.fragment_id,
        "unit_id": fragment.unit_id,
        "title": fragment.title,
        "url": fragment.url,
        "topic_id": unit.topic_id if unit is not None else (fragment.topic or ""),
        "authority": unit.authority if unit is not None else "",
        "unit_type": unit.unit_type if unit is not None else "",
    }


def collection_matches(client: QdrantClient, settings: QdrantSettings, index: LoadedIndex) -> bool:
    """La colección existe y tiene tantos puntos y la misma dimensión que el índice."""
    if not client.collection_exists(settings.collection):
        return False
    info = client.get_collection(settings.collection)
    vectors = info.config.params.vectors
    size = getattr(vectors, "size", None)
    count = client.count(settings.collection, exact=True).count
    return size == index.manifest.dimension and count == index.manifest.count


def build_collection(
    client: QdrantClient,
    settings: QdrantSettings,
    index: LoadedIndex,
    units_by_id: Mapping[str, GoldUnit],
    *,
    force: bool = False,
    progress: Callable[[int, int], None] | None = None,
) -> int:
    """Crea (o recrea) la colección con HNSW, índices de *payload* y todos los fragmentos."""
    from qdrant_client import models

    if not force and collection_matches(client, settings, index):
        return 0
    if client.collection_exists(settings.collection):
        client.delete_collection(settings.collection)
    client.create_collection(
        settings.collection,
        vectors_config=models.VectorParams(
            size=index.manifest.dimension, distance=models.Distance.COSINE
        ),
        hnsw_config=models.HnswConfigDiff(
            m=settings.hnsw_m, ef_construct=settings.hnsw_ef_construct
        ),
    )
    # El modo local ignora los índices de payload (filtra igual); solo el servidor los usa.
    for field in PAYLOAD_INDEXES if settings.url else ():
        client.create_payload_index(
            settings.collection, field_name=field, field_schema=models.PayloadSchemaType.KEYWORD
        )
    total = len(index.fragments)
    for start in range(0, total, UPLOAD_BATCH):
        stop = min(start + UPLOAD_BATCH, total)
        client.upsert(
            settings.collection,
            points=models.Batch(
                ids=list(range(start, stop)),
                vectors=index.vectors[start:stop].tolist(),
                payloads=[fragment_payload(i, index, units_by_id) for i in range(start, stop)],
            ),
            wait=True,
        )
        if progress is not None:
            progress(stop, total)
    return total


@dataclass(frozen=True, slots=True)
class VectorHit:
    """Resultado de Qdrant: posición del fragmento en el índice y similitud coseno."""

    position: int
    unit_id: str
    score: float


class QdrantVectorStore:
    """Búsqueda top-k en Qdrant con filtro por *payload* en una sola etapa."""

    def __init__(self, client: QdrantClient, settings: QdrantSettings) -> None:
        self.client = client
        self.settings = settings

    def describe(self) -> str:
        mode = "HNSW" if self.settings.url else "local exacto"
        return f"Qdrant ({mode}) · colección {self.settings.collection}"

    def search(
        self,
        vector: np.ndarray,
        *,
        limit: int,
        topics: Sequence[str] = (),
        authorities: Sequence[str] = (),
        unit_types: Sequence[str] = (),
    ) -> list[VectorHit]:
        from qdrant_client import models

        must: list[models.Condition] = []
        for key, values in (
            ("topic_id", topics),
            ("authority", authorities),
            ("unit_type", unit_types),
        ):
            if values:
                must.append(
                    models.FieldCondition(key=key, match=models.MatchAny(any=sorted(values)))
                )
        response = self.client.query_points(
            self.settings.collection,
            query=np.asarray(vector, dtype=np.float32).tolist(),
            limit=limit,
            query_filter=models.Filter(must=must) if must else None,
            search_params=(
                models.SearchParams(hnsw_ef=self.settings.hnsw_ef) if self.settings.url else None
            ),
            with_payload=["position", "unit_id"],
        )
        return [
            VectorHit(
                position=int((point.payload or {}).get("position", point.id)),
                unit_id=str((point.payload or {}).get("unit_id", "")),
                score=float(point.score),
            )
            for point in response.points
        ]


def connect_vector_store(
    index: LoadedIndex | None,
    settings: QdrantSettings,
    *,
    units_by_id: Mapping[str, GoldUnit] | None = None,
    in_memory: bool = False,
) -> tuple[QdrantVectorStore | None, str]:
    """Abre la colección lista para consultar; devuelve ``(store, nota)``.

    ``in_memory`` (modo demo y pruebas) crea la colección en memoria a partir del índice. En los
    demás casos la colección debe existir (``rag qdrant build``); si no, ``store`` es ``None``.
    """
    if index is None or not settings.enabled:
        return None, ""
    try:
        client = open_client(settings, in_memory=in_memory)
        if in_memory:
            build_collection(client, settings, index, units_by_id or {}, force=True)
        elif not collection_matches(client, settings, index):
            client.close()
            return None, (
                f"Colección Qdrant {settings.collection} ausente o desactualizada en "
                f"{settings.location}; se usó la matriz numpy (`rag qdrant build`)."
            )
    except Exception as exc:
        return None, f"Qdrant no disponible ({type(exc).__name__}); se usó la matriz numpy."
    store = QdrantVectorStore(client, settings)
    return store, f"Búsqueda vectorial en {store.describe()}"


def attach_vector_store(
    index: LoadedIndex | None,
    config_source: Path | None,
    units: Sequence[GoldUnit],
    *,
    demo: bool = False,
) -> tuple[QdrantVectorStore | None, str]:
    """Atajo para las fábricas de recuperadores (API, CLI y agente).

    En modo demo la colección se crea en memoria a partir del índice de prueba; en modo real se
    abre la colección construida con ``rag qdrant build``.
    """
    settings = load_qdrant_settings(config_source)
    return connect_vector_store(
        index,
        settings,
        units_by_id={unit.unit_id: unit for unit in units},
        in_memory=demo,
    )
